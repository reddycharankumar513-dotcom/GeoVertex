import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from shapely import wkt
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import (
    AIException,
    ModelNotConfiguredError,
    ModelWeightsUnavailableError,
    OutputGeometryInvalidError,
)
from app.ai.models import DevelopmentBaselineBuildingExtractor, UnconfiguredFloorExtractor
from app.ai.registry.model_registry import model_registry
from app.ai.validation.comparison import cadastral_comparator
from app.ai.validation.geo_validator import deterministic_validator
from app.database.session import AsyncSessionLocal
from app.models.ai import AIProcessingJob, BuildingExtractionResult, FloorExtractionResult
from app.repositories.ai_repository import (
    ai_job_repository,
    building_result_repository,
    floor_result_repository,
)
from app.repositories.audit_repository import audit_repository
from app.repositories.building_repository import building_repository
from app.repositories.survey_repository import (
    survey_evidence_repository,
    survey_observation_repository,
)
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class AIJobWorker:
    """Asynchronous background worker executing AI inference jobs."""

    async def execute_job(self, job_id: uuid.UUID, session: Optional[AsyncSession] = None) -> None:
        """Entrypoint executed by background worker for a queued job."""
        if session is not None:
            await self._run_job_with_db(session, job_id)
        else:
            async with AsyncSessionLocal() as db:
                await self._run_job_with_db(db, job_id)

    async def _run_job_with_db(self, db: AsyncSession, job_id: uuid.UUID) -> None:
        job = await ai_job_repository.get_by_id(db, job_id)
        if not job or job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            return

        try:
            # Mark started
            job.status = "RUNNING"
            job.stage = "PREPROCESSING"
            job.progress_pct = 10
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            await audit_repository.log_event(
                db=db,
                action="AI_JOB_STARTED",
                entity_type="AI_JOB",
                entity_id=str(job.id),
                actor_user_id=job.requested_by,
                details={"job_type": job.job_type, "model_id": job.model_id},
            )
            await db.commit()

            if job.job_type == "BUILDING_EXTRACTION":
                await self._process_building_extraction(db, job)
            elif job.job_type == "FLOOR_EXTRACTION":
                await self._process_floor_extraction(db, job)
            else:
                raise AIException(f"Unsupported job type: {job.job_type}", "UNSUPPORTED_JOB_TYPE")

            # Mark Completed
            job.status = "COMPLETED"
            job.stage = "COMPLETED"
            job.progress_pct = 100
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            await audit_repository.log_event(
                db=db,
                action="AI_JOB_COMPLETED",
                entity_type="AI_JOB",
                entity_id=str(job.id),
                actor_user_id=job.requested_by,
                details={"job_type": job.job_type, "status": "COMPLETED"},
            )
            await db.commit()

        except Exception as e:
            error_code = getattr(e, "error_code", "INFERENCE_FAILED")
            error_msg = str(e)
            logger.error(f"AI job {job_id} failed with error {error_code}: {error_msg}")

            job.status = "FAILED"
            job.stage = "FAILED"
            job.error_code = error_code
            job.error_message = error_msg
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            await audit_repository.log_event(
                db=db,
                action="AI_JOB_FAILED",
                entity_type="AI_JOB",
                entity_id=str(job.id),
                actor_user_id=job.requested_by,
                details={"error_code": error_code, "error_message": error_msg},
            )
            await db.commit()


    async def _process_building_extraction(self, db: AsyncSession, job: AIProcessingJob) -> None:
        """Pipeline: Ingestion -> Preprocessing -> Inference -> Postprocessing -> PostGIS Validation -> Cadastral Comparison -> Candidate Storage."""
        # 1. Fetch Target Building
        target_building = None
        try:
            target_building_id = uuid.UUID(job.target_id)
            target_building = await building_repository.get_by_id(db, target_building_id)
        except Exception:
            pass

        official_geom_wkt = target_building.geometry_wkt if target_building else None
        if not official_geom_wkt:
            # Check if input_reference provides geometry
            official_geom_wkt = job.input_reference.get("target_geometry")

        if not official_geom_wkt:
            raise AIException("No valid geometry found for target building", "INPUT_INVALID")

        # 2. Gather Evidence (Photos & Observations)
        evidence_items = []
        image_path = None
        survey_evidence_ids = job.input_reference.get("survey_evidence_ids", [])
        for ev_id_str in survey_evidence_ids:
            try:
                ev_id = uuid.UUID(ev_id_str)
                ev = await survey_evidence_repository.get_by_id(db, ev_id)
                if ev:
                    evidence_items.append({
                        "evidence_id": str(ev.id),
                        "filename": ev.filename,
                        "storage_key": ev.storage_key,
                        "mime_type": ev.mime_type,
                    })
                    if not image_path and ev.mime_type.startswith("image/"):
                        image_path = str(storage_service.get_file_path(ev.storage_key))
            except Exception:
                pass

        # 3. Running Model Inference (Stage 2: 40%)
        job.stage = "RUNNING_MODEL"
        job.progress_pct = 40
        await db.commit()

        # Load Model from Registry
        model = model_registry.get_or_load_model(
            model_id=job.model_id,
            model_version=job.model_version,
            configuration=job.parameters,
        )

        input_payload = {
            "target_geometry": official_geom_wkt,
            "image_path": image_path,
            "survey_observations": job.input_reference.get("observations", []),
            "survey_height": target_building.height_estimate if target_building else None,
        }

        preprocessed = model.preprocess(input_payload)
        prediction = model.predict(preprocessed)

        # 4. Postprocessing (Stage 3: 70%)
        job.stage = "POSTPROCESSING"
        job.progress_pct = 70
        await db.commit()

        prediction_result = model.postprocess(prediction)

        # 5. Deterministic GIS Validation (Stage 4: 90%)
        job.stage = "VALIDATING"
        job.progress_pct = 90
        await db.commit()

        val_report = deterministic_validator.validate_candidate_polygon(prediction_result.geometry_wkt)
        cadastral_metrics = cadastral_comparator.compare_geometries(
            candidate_geom=prediction_result.geometry_wkt,
            official_geom=official_geom_wkt,
        )

        # Composite Confidence
        conf_breakdown = cadastral_comparator.compute_composite_confidence(
            model_confidence=prediction_result.confidence_components.model_confidence,
            geometry_quality=val_report.get("geometry_quality_score", 0.75),
            source_quality=prediction_result.confidence_components.source_quality,
        )

        # 6. Save Candidate Result (Status: REVIEW_REQUIRED)
        candidate_result = BuildingExtractionResult(
            job_id=job.id,
            source_target_id=job.target_id,
            geometry=prediction_result.geometry_wkt,
            geometry_wkt=prediction_result.geometry_wkt,
            raw_geometry_wkt=prediction_result.raw_geometry_wkt,
            estimated_height=prediction_result.estimated_height,
            confidence=conf_breakdown["composite_confidence"],
            confidence_components=conf_breakdown["components"],
            cadastral_comparison=cadastral_metrics,
            evidence_linkage={
                "evidence_items": evidence_items,
                "input_provenance": job.input_reference,
            },
            model_id=job.model_id,
            model_version=job.model_version,
            status="REVIEW_REQUIRED",
            validation_status=val_report["status"],
            validation_details=val_report,
        )
        db.add(candidate_result)
        await db.flush()

        await audit_repository.log_event(
            db=db,
            action="AI_RESULT_CREATED",
            entity_type="BUILDING_EXTRACTION_RESULT",
            entity_id=str(candidate_result.id),
            actor_user_id=job.requested_by,
            details={
                "job_id": str(job.id),
                "confidence": candidate_result.confidence,
                "validation_status": candidate_result.validation_status,
                "iou": cadastral_metrics.get("iou"),
            },
        )
        await db.commit()

    async def _process_floor_extraction(self, db: AsyncSession, job: AIProcessingJob) -> None:
        """Pipeline for candidate floor extraction. Enforces Section 24: MODEL_NOT_CONFIGURED if weights unavailable."""
        # Load Model from Registry
        model = model_registry.get_or_load_model(
            model_id=job.model_id,
            model_version=job.model_version,
            configuration=job.parameters,
        )

        # Calling preprocess or predict on unconfigured model will raise ModelNotConfiguredError
        preprocessed = model.preprocess({"target_id": job.target_id})
        prediction = model.predict(preprocessed)
        result = model.postprocess(prediction)
        # If ever configured, persist candidate floor records


job_worker = AIJobWorker()
