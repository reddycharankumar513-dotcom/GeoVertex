import asyncio
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import BackgroundTasks
from shapely.geometry import mapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import (
    AIException,
    ModelNotConfiguredError,
    OutputGeometryInvalidError,
)
from app.ai.evaluation.evaluator import model_evaluator
from app.ai.preprocessing.geo_processor import GEOD, geo_preprocessor
from app.ai.registry.model_registry import model_registry
from app.ai.schemas.ai_schemas import (
    AIJobCreateRequest,
    AIReviewDecisionRequest,
)
from app.ai.validation.comparison import cadastral_comparator
from app.ai.validation.geo_validator import deterministic_validator
from app.ai.workers.job_worker import job_worker
from app.core.errors import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.ai import (
    AIDataset,
    AIEvaluationRun,
    AIModel,
    AIModelVersion,
    AIProcessingJob,
    AIReview,
    BuildingExtractionResult,
    FloorExtractionResult,
)
from app.models.user import User, UserRole
from app.repositories.ai_repository import (
    ai_dataset_repository,
    ai_evaluation_repository,
    ai_job_repository,
    ai_model_repository,
    ai_review_repository,
    building_result_repository,
    floor_result_repository,
)
from app.repositories.audit_repository import audit_repository
from app.repositories.building_repository import building_repository
from app.repositories.threed_repository import threed_repository


class AIService:
    """Core domain orchestration service for AI inference jobs, results, validation, and controlled human review."""

    # -------------------------------------------------------------
    # AI Jobs
    # -------------------------------------------------------------

    async def create_job(
        self,
        db: AsyncSession,
        data: AIJobCreateRequest,
        current_user: User,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> AIProcessingJob:
        # Check idempotency
        if data.client_request_id:
            existing_job = await ai_job_repository.get_by_client_request_id(db, data.client_request_id)
            if existing_job:
                return existing_job

        # Ensure requested model is recognized
        model_id = data.model_id or "building-segmentation-v1"
        model_ver = data.model_version or "1.0.0"

        # Prepare input reference
        input_ref = {
            "target_type": data.target_type,
            "target_id": data.target_id,
            "survey_evidence_ids": data.survey_evidence_ids or [],
        }

        # If target is building, fetch official geometry
        if data.target_type == "BUILDING":
            try:
                bld = await building_repository.get_by_id(db, uuid.UUID(data.target_id))
                if bld:
                    input_ref["target_geometry"] = bld.geometry_wkt
                    input_ref["building_reference"] = bld.building_reference
            except Exception:
                pass

        job = AIProcessingJob(
            client_request_id=data.client_request_id,
            job_type=data.job_type,
            status="QUEUED",
            stage="QUEUED",
            progress_pct=0,
            requested_by=current_user.id,
            target_type=data.target_type,
            target_id=data.target_id,
            input_reference=input_ref,
            model_id=model_id,
            model_version=model_ver,
            parameters=data.parameters or {},
        )
        db.add(job)
        await db.flush()

        await audit_repository.log_event(
            db=db,
            action="AI_JOB_CREATED",
            entity_type="AI_JOB",
            entity_id=str(job.id),
            actor_user_id=current_user.id,
            details={"job_type": job.job_type, "target_id": job.target_id, "model_id": model_id},
        )
        await db.commit()
        await db.refresh(job)

        # Dispatch background worker
        if background_tasks:
            background_tasks.add_task(job_worker.execute_job, job.id)
        else:
            asyncio.create_task(job_worker.execute_job(job.id))

        return job

    async def get_job(self, db: AsyncSession, job_id: uuid.UUID) -> AIProcessingJob:
        job = await ai_job_repository.get_by_id(db, job_id)
        if not job:
            raise NotFoundException(f"AI job with ID '{job_id}' not found")
        return job

    async def list_jobs(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AIProcessingJob], int]:
        return await ai_job_repository.list_jobs(
            db=db,
            status=status,
            job_type=job_type,
            target_type=target_type,
            target_id=target_id,
            skip=skip,
            limit=limit,
        )

    async def cancel_job(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        current_user: User,
    ) -> AIProcessingJob:
        job = await self.get_job(db, job_id)
        if job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            raise BadRequestException(f"Cannot cancel job in terminal state '{job.status}'")

        job.status = "CANCELLED"
        job.stage = "CANCELLED"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(job)
        return job

    # -------------------------------------------------------------
    # Candidate Results & Review
    # -------------------------------------------------------------

    async def list_building_results(
        self,
        db: AsyncSession,
        target_id: Optional[str] = None,
        status: Optional[str] = None,
        model_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BuildingExtractionResult], int]:
        return await building_result_repository.list_results(
            db=db,
            target_id=target_id,
            status=status,
            model_id=model_id,
            skip=skip,
            limit=limit,
        )

    async def get_building_result(
        self,
        db: AsyncSession,
        result_id: uuid.UUID,
    ) -> BuildingExtractionResult:
        result = await building_result_repository.get_by_id(db, result_id)
        if not result:
            raise NotFoundException(f"Building extraction result '{result_id}' not found")
        return result

    async def list_floor_results(
        self,
        db: AsyncSession,
        building_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[FloorExtractionResult], int]:
        return await floor_result_repository.list_results(
            db=db,
            building_id=building_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    async def validate_candidate_result(
        self,
        db: AsyncSession,
        result_id: uuid.UUID,
        current_user: User,
    ) -> Dict[str, Any]:
        """Re-runs deterministic GIS validation and cadastral comparison on candidate result."""
        result = await self.get_building_result(db, result_id)
        val_report = deterministic_validator.validate_candidate_polygon(result.geometry_wkt)

        # Cadastral comparison if target building exists
        try:
            bld = await building_repository.get_by_id(db, uuid.UUID(result.source_target_id))
            if bld and bld.geometry_wkt:
                cadastral_metrics = cadastral_comparator.compare_geometries(result.geometry_wkt, bld.geometry_wkt)
                result.cadastral_comparison = cadastral_metrics
        except Exception:
            pass

        result.validation_status = val_report["status"]
        result.validation_details = val_report
        await db.commit()
        await db.refresh(result)

        await audit_repository.log_event(
            db=db,
            action="AI_RESULT_VALIDATED",
            entity_type="BUILDING_EXTRACTION_RESULT",
            entity_id=str(result.id),
            actor_user_id=current_user.id,
            details={"validation_status": result.validation_status},
        )
        await db.commit()

        return val_report

    async def review_result(
        self,
        db: AsyncSession,
        result_id: uuid.UUID,
        review_data: AIReviewDecisionRequest,
        current_user: User,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Dict[str, Any]:
        """Human-in-the-loop adjudication gate.
        
        Actions:
            APPROVE: Applies controlled update to official Building record.
            MODIFY_AND_APPROVE: Validates reviewer-edited geometry, updates candidate, and applies update.
            REJECT: Marks candidate as REJECTED with notes.
            REQUEST_REPROCESSING: Requests worker to re-run pipeline.
        """
        # RBAC Check: Only Admin or Government Officer
        if current_user.role not in [UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER]:
            raise ForbiddenException("Only Government Officers and Administrators can approve or reject AI results")

        result = await self.get_building_result(db, result_id)
        action = review_data.action.upper()

        if action not in ["APPROVE", "REJECT", "MODIFY_AND_APPROVE", "REQUEST_REPROCESSING"]:
            raise BadRequestException(f"Unsupported review action '{review_data.action}'")

        orig_wkt = result.geometry_wkt
        edited_wkt = review_data.edited_geometry_wkt
        applied = False
        applied_at = None

        if action == "MODIFY_AND_APPROVE":
            if not edited_wkt:
                raise BadRequestException("Field 'edited_geometry_wkt' is mandatory for MODIFY_AND_APPROVE action")

            # Validate edited geometry
            val = deterministic_validator.validate_candidate_polygon(edited_wkt)
            if val["status"] == "INVALID":
                raise BadRequestException("Edited geometry failed deterministic validation", details=val)

            # Update candidate geometry
            result.geometry_wkt = edited_wkt
            result.geometry = edited_wkt
            result.status = "APPROVED"

            await audit_repository.log_event(
                db=db,
                action="AI_RESULT_MODIFIED",
                entity_type="BUILDING_EXTRACTION_RESULT",
                entity_id=str(result.id),
                actor_user_id=current_user.id,
                details={"original_geometry_wkt": orig_wkt, "edited_geometry_wkt": edited_wkt},
            )

        elif action == "APPROVE":
            result.status = "APPROVED"

        elif action == "REJECT":
            result.status = "REJECTED"

        elif action == "REQUEST_REPROCESSING":
            result.status = "CANDIDATE"
            # Re-dispatch job
            if background_tasks:
                background_tasks.add_task(job_worker.execute_job, result.job_id)
            else:
                asyncio.create_task(job_worker.execute_job(result.job_id))

            await audit_repository.log_event(
                db=db,
                action="AI_REPROCESS_REQUESTED",
                entity_type="BUILDING_EXTRACTION_RESULT",
                entity_id=str(result.id),
                actor_user_id=current_user.id,
                details={"job_id": str(result.job_id), "notes": review_data.notes},
            )

        # Create Review Record
        review = AIReview(
            result_type="BUILDING",
            result_id=result.id,
            reviewer_id=current_user.id,
            action=action,
            original_geometry_wkt=orig_wkt,
            edited_geometry_wkt=edited_wkt,
            notes=review_data.notes,
            applied_to_cadastre=False,
        )
        db.add(review)
        await db.flush()
        result.review_id = review.id

        # ---------------------------------------------------------
        # CONTROLLED CADASTRAL UPDATE (Section 29, 61, 62)
        # ---------------------------------------------------------
        if action in ["APPROVE", "MODIFY_AND_APPROVE"]:
            try:
                target_bld_id = uuid.UUID(result.source_target_id)
                target_bld = await building_repository.get_by_id(db, target_bld_id)
                if target_bld:
                    approved_poly = geo_preprocessor.parse_geometry(result.geometry_wkt)
                    approved_area, _ = GEOD.geometry_area_perimeter(approved_poly)

                    # Update official building record
                    target_bld.geometry = result.geometry_wkt
                    target_bld.geometry_wkt = result.geometry_wkt
                    target_bld.area = abs(round(approved_area, 2))

                    if result.estimated_height is not None and result.estimated_height > 0:
                        target_bld.height_estimate = result.estimated_height
                        # Update 3D representation
                        await threed_repository.save_representation(
                            db=db,
                            building_id=target_bld.id,
                            height=result.estimated_height,
                            height_source="SURVEY_AI_APPROVED",
                            height_confidence=result.confidence,
                        )

                    review.applied_to_cadastre = True
                    review.applied_at = datetime.now(timezone.utc)
                    applied = True
                    applied_at = review.applied_at

                    # Audit Controlled Cadastral Update
                    await audit_repository.log_event(
                        db=db,
                        action="AI_RESULT_APPROVED",
                        entity_type="BUILDING_EXTRACTION_RESULT",
                        entity_id=str(result.id),
                        actor_user_id=current_user.id,
                        details={
                            "building_id": str(target_bld.id),
                            "action": action,
                            "new_area_sqm": target_bld.area,
                        },
                    )
                    await audit_repository.log_event(
                        db=db,
                        action="BUILDING_UPDATED",
                        entity_type="BUILDING",
                        entity_id=str(target_bld.id),
                        actor_user_id=current_user.id,
                        details={
                            "update_source": "CONTROLLED_AI_APPROVAL",
                            "review_id": str(review.id),
                            "geometry_wkt": target_bld.geometry_wkt,
                        },
                    )
            except Exception as e:
                logger.error(f"Failed controlled update for building {result.source_target_id}: {e}")

        elif action == "REJECT":
            await audit_repository.log_event(
                db=db,
                action="AI_RESULT_REJECTED",
                entity_type="BUILDING_EXTRACTION_RESULT",
                entity_id=str(result.id),
                actor_user_id=current_user.id,
                details={"reason": review_data.notes},
            )

        await db.commit()
        await db.refresh(result)
        await db.refresh(review)

        return {
            "result_id": result.id,
            "review_id": review.id,
            "action": action,
            "status": result.status,
            "applied_to_cadastre": applied,
            "applied_at": applied_at,
        }

    # -------------------------------------------------------------
    # AI Models & Registry
    # -------------------------------------------------------------

    async def list_registered_models(self, db: AsyncSession) -> List[Dict[str, Any]]:
        models = await ai_model_repository.list_models(db)
        if not models:
            # Seed default models into DB if empty
            m1 = AIModel(
                model_id="building-segmentation-v1",
                name="Building Segmentation Baseline",
                model_type="BUILDING_EXTRACTION",
                framework="BASELINE_HEURISTIC",
                description="Development baseline extractor utilizing surveyed evidence context and AOI clipping",
                status="ACTIVE",
                metadata_json={"supported_modalities": ["imagery", "survey_observations", "aoi"]},
            )
            m2 = AIModel(
                model_id="floor-extraction-v1",
                name="Floor Extraction Neural Model",
                model_type="FLOOR_EXTRACTION",
                framework="UNCONFIGURED",
                description="Floor stack neural extractor (Section 24: Unconfigured/weights unavailable)",
                status="UNCONFIGURED",
                metadata_json={"supported_modalities": ["building_height", "facade_imagery"]},
            )
            db.add(m1)
            db.add(m2)
            await db.flush()

            v1 = AIModelVersion(
                model_id=m1.id,
                version="1.0.0",
                configuration={"confidence_threshold": 0.65, "min_building_area": 10.0},
                metrics={"sample_iou": 1.0, "dataset": "geovertex-demo-val-v1"},
                is_active=True,
            )
            v2 = AIModelVersion(
                model_id=m2.id,
                version="1.0.0",
                configuration={},
                metrics={},
                is_active=False,
            )
            db.add(v1)
            db.add(v2)
            await db.commit()
            models = await ai_model_repository.list_models(db)

        res = []
        for m in models:
            res.append({
                "id": m.id,
                "model_id": m.model_id,
                "name": m.name,
                "model_type": m.model_type,
                "framework": m.framework,
                "description": m.description,
                "status": m.status,
                "metadata_json": m.metadata_json,
                "versions": [
                    {
                        "id": v.id,
                        "model_id": v.model_id,
                        "version": v.version,
                        "weights_reference": v.weights_reference,
                        "weights_hash": v.weights_hash,
                        "configuration": v.configuration,
                        "metrics": v.metrics,
                        "is_active": v.is_active,
                        "created_at": v.created_at,
                    }
                    for v in m.versions
                ],
                "created_at": m.created_at,
            })
        return res

    # -------------------------------------------------------------
    # Evaluation & Benchmarks
    # -------------------------------------------------------------

    async def list_datasets(self, db: AsyncSession) -> List[AIDataset]:
        datasets = await ai_dataset_repository.list_datasets(db)
        if not datasets:
            demo_ds = AIDataset(
                dataset_id="geovertex-demo-val-v1",
                name="GeoVertex Cadastral Demo Benchmark",
                version="1.0.0",
                dataset_type="DEMO / DEVELOPMENT DATASET",
                source="Phase 5 Survey & CBD Footprints",
                sample_count=2,
                label_schema={"format": "WKT", "geometry_type": "Polygon", "crs": "EPSG:4326"},
                description="Development evaluation dataset for building footprint candidate extraction.",
            )
            db.add(demo_ds)
            await db.commit()
            datasets = [demo_ds]
        return datasets

    async def execute_evaluation_run(
        self,
        db: AsyncSession,
        dataset_id: uuid.UUID,
        model_id: str,
        model_version: str,
        current_user: User,
        notes: Optional[str] = None,
    ) -> AIEvaluationRun:
        dataset = await ai_dataset_repository.get_by_id(db, dataset_id)
        if not dataset:
            raise NotFoundException(f"Evaluation dataset with ID '{dataset_id}' not found")

        eval_report = model_evaluator.evaluate_model(
            model_id=model_id,
            model_version=model_version,
        )

        run = AIEvaluationRun(
            dataset_id=dataset.id,
            model_id=model_id,
            model_version=model_version,
            metrics=eval_report["metrics"],
            executed_by=current_user.id,
            notes=notes,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run


ai_service = AIService()
