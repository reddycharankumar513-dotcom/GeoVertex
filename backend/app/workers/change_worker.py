from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.change.detector import DeterministicChangeDetector, AIChangeDetector
from app.ai.change.image_registration import ImageRegistrationValidator
from app.gis.validation.base import ValidationContext
from app.gis.validation.engine import ValidationEngine
from app.models.building import BuildingFootprint
from app.models.document import PropertyDocument, DocumentExtractedField
from app.models.parcel import Parcel
from app.models.survey import SurveyObservation
from app.models.temporal import (
    CandidateStatus,
    ChangeCandidate,
    ChangeDetectionRun,
    ChangeRunStatus,
    PropertySnapshot,
)
from app.repositories.temporal_repository import temporal_repository

logger = logging.getLogger(__name__)


class ChangeDetectionWorker:
    """Orchestrates asynchronous 8-stage change detection and cross-phase validation pipeline."""

    def __init__(self):
        self.deterministic_detector = DeterministicChangeDetector()
        self.ai_detector = AIChangeDetector()
        self.validation_engine = ValidationEngine()

    async def execute_run(self, db: AsyncSession, run_id: uuid.UUID) -> ChangeDetectionRun:
        run = await temporal_repository.get_run(db, run_id)
        if not run:
            raise ValueError(f"Change detection run {run_id} not found")

        try:
            # Stage 1: Input Validation
            await temporal_repository.update_run(
                db, run_id, {"status": ChangeRunStatus.RUNNING.value, "started_at": datetime.now(timezone.utc)}
            )

            # Stage 2: Preprocessing - Load Baseline and Comparison States
            baseline_data: Dict[str, Any] = {}
            comparison_data: Dict[str, Any] = {}

            params = run.parameters or {}

            # 1. Try loading baseline snapshot if referenced
            base_snap = None
            try:
                base_uuid = uuid.UUID(run.baseline_reference)
                base_snap = await temporal_repository.get_snapshot(db, base_uuid)
            except (ValueError, TypeError):
                pass

            # 2. Try loading comparison snapshot if referenced
            comp_snap = None
            try:
                comp_uuid = uuid.UUID(run.comparison_reference)
                comp_snap = await temporal_repository.get_snapshot(db, comp_uuid)
            except (ValueError, TypeError):
                pass

            baseline_data = {
                "entity_type": (base_snap.entity_type if base_snap else run.target_type),
                "entity_id": (base_snap.entity_id if base_snap else run.target_id),
                "geometry_wkt": params.get("baseline_geometry_wkt") or (base_snap.geometry_wkt if base_snap else None),
                "attributes": params.get("baseline_attributes") or (base_snap.attributes_json if base_snap else {}),
                "snapshot_id": (base_snap.id if base_snap else None),
                "date": (base_snap.observation_date or base_snap.effective_from) if base_snap else None,
            }

            comparison_data = {
                "entity_type": (comp_snap.entity_type if comp_snap else run.target_type),
                "entity_id": (comp_snap.entity_id if comp_snap else run.target_id),
                "geometry_wkt": params.get("comparison_geometry_wkt") or (comp_snap.geometry_wkt if comp_snap else None),
                "attributes": params.get("comparison_attributes") or (comp_snap.attributes_json if comp_snap else {}),
                "snapshot_id": (comp_snap.id if comp_snap else None),
                "date": (comp_snap.observation_date or comp_snap.effective_from) if comp_snap else None,
            }

            # If entity_id given and missing comparison, fallback to current database entity
            if not comparison_data.get("geometry_wkt") and run.target_id:
                    if run.target_type == "BUILDING":
                        stmt = select(BuildingFootprint).where(BuildingFootprint.id == run.target_id)
                        res = await db.execute(stmt)
                        bldg = res.scalars().first()
                        if bldg:
                            comparison_data = {
                                "entity_type": "BUILDING",
                                "entity_id": bldg.id,
                                "geometry_wkt": bldg.geometry_wkt,
                                "attributes": {
                                    "building_type": bldg.building_type,
                                    "building_reference": bldg.building_reference,
                                    "status": bldg.status,
                                    "height_estimate": bldg.height_estimate,
                                    "area": bldg.area,
                                },
                                "snapshot_id": None,
                                "date": bldg.updated_at or bldg.created_at,
                            }
                    elif run.target_type == "PARCEL":
                        stmt = select(Parcel).where(Parcel.id == run.target_id)
                        res = await db.execute(stmt)
                        pcl = res.scalars().first()
                        if pcl:
                            comparison_data = {
                                "entity_type": "PARCEL",
                                "entity_id": pcl.id,
                                "geometry_wkt": pcl.geometry_wkt,
                                "attributes": {
                                    "parcel_number": pcl.parcel_number,
                                    "parcel_code": pcl.parcel_code,
                                    "land_use": pcl.land_use,
                                    "ownership_status": pcl.ownership_status,
                                    "area": pcl.area,
                                },
                                "snapshot_id": None,
                                "date": pcl.updated_at or pcl.created_at,
                            }

            # Stage 3: Alignment Check (if raster or imagery references)
            if run.detection_method == "IMAGE_AI":
                align_res = ImageRegistrationValidator.validate_and_register(
                    params.get("baseline_raster_meta", {}),
                    params.get("comparison_raster_meta", {}),
                )
                if not align_res.get("is_aligned"):
                    await temporal_repository.update_run(
                        db,
                        run_id,
                        {
                            "status": ChangeRunStatus.FAILED.value,
                            "completed_at": datetime.now(timezone.utc),
                            "summary": {"error": align_res.get("status"), "message": align_res.get("message")},
                        },
                    )
                    return await temporal_repository.get_run(db, run_id)

            # Stage 4: Detection
            candidates_raw: List[Dict[str, Any]] = []

            if run.detection_method in ["GEOMETRY_DIFF", "ATTRIBUTE_DIFF", "COMPOSITE"]:
                candidates_raw.extend(
                    self.deterministic_detector.detect_changes(baseline_data, comparison_data, params)
                )

            if run.detection_method == "IMAGE_AI":
                candidates_raw.extend(
                    self.ai_detector.detect_changes(baseline_data, comparison_data, params)
                )

            # Stage 5 & 6: Postprocessing & Phase 7 Topology Validation Integration
            created_candidates: List[ChangeCandidate] = []
            for c_data in candidates_raw:
                # If change has a modified/new geometry, validate through Phase 7
                validation_issues_list: List[Dict[str, Any]] = []
                geom_wkt = c_data.get("geometry_wkt")

                if geom_wkt:
                    try:
                        ctx = ValidationContext(
                            target_type=c_data.get("entity_type", "BUILDING"),
                            target_id=str(c_data.get("entity_id") or "CANDIDATE"),
                            raw_geometries={"geometry": geom_wkt},
                        )
                        val_res = self.validation_engine.execute_validation(ctx)
                        for issue in val_res.get("issues", []):
                            validation_issues_list.append({
                                "rule_id": issue.rule_id,
                                "issue_code": issue.issue_code,
                                "severity": issue.severity,
                                "message": issue.message,
                                "technical_explanation": issue.technical_explanation,
                            })
                    except Exception as e:
                        logger.warning(f"Validation engine skipped on candidate: {e}")

                # Stage 7: Evidence Enrichment (Phase 8 Documents & Phase 5 Surveys)
                evidence_list = c_data.get("evidence", []) or []
                target_entity_id = c_data.get("entity_id")

                if target_entity_id:
                    # Query Phase 8 Documents
                    try:
                        doc_stmt = (
                            select(PropertyDocument)
                            .where(
                                (PropertyDocument.building_id == target_entity_id)
                                | (PropertyDocument.parcel_id == target_entity_id)
                            )
                            .limit(5)
                        )
                        doc_res = await db.execute(doc_stmt)
                        related_docs = doc_res.scalars().all()
                        for rdoc in related_docs:
                            evidence_list.append({
                                "source_type": "PROPERTY_DOCUMENT",
                                "source_id": str(rdoc.id),
                                "document_type": rdoc.document_type,
                                "document_number": rdoc.document_number,
                                "document_date": rdoc.document_date.isoformat() if rdoc.document_date else None,
                                "description": f"Related {rdoc.document_type} doc #{rdoc.document_number or 'N/A'}",
                            })
                    except Exception as e:
                        logger.debug(f"Document evidence query error: {e}")

                    # Query Phase 5 Surveys
                    try:
                        surv_stmt = (
                            select(SurveyObservation)
                            .where(
                                (SurveyObservation.target_type == c_data.get("entity_type"))
                                & (SurveyObservation.target_id == target_entity_id)
                            )
                            .limit(5)
                        )
                        surv_res = await db.execute(surv_stmt)
                        related_surveys = surv_res.scalars().all()
                        for rsurv in related_surveys:
                            evidence_list.append({
                                "source_type": "SURVEY_OBSERVATION",
                                "source_id": str(rsurv.id),
                                "observation_date": rsurv.observation_timestamp.isoformat() if rsurv.observation_timestamp else None,
                                "description": f"Field measurement: Height {rsurv.height_m}m, Floors {rsurv.floor_count}",
                            })
                    except Exception as e:
                        logger.debug(f"Survey evidence query error: {e}")

                # Persist candidate
                cand_record = await temporal_repository.create_candidate(
                    db,
                    {
                        "id": uuid.uuid4(),
                        "detection_run_id": run_id,
                        "change_type": c_data.get("change_type"),
                        "entity_type": c_data.get("entity_type", "BUILDING"),
                        "entity_id": c_data.get("entity_id"),
                        "baseline_snapshot_id": baseline_data.get("snapshot_id"),
                        "comparison_snapshot_id": comparison_data.get("snapshot_id"),
                        "baseline_date": baseline_data.get("date"),
                        "comparison_date": comparison_data.get("date"),
                        "geometry_wkt": c_data.get("geometry_wkt"),
                        "baseline_geometry_wkt": c_data.get("baseline_geometry_wkt"),
                        "comparison_geometry_wkt": c_data.get("comparison_geometry_wkt"),
                        "magnitude": c_data.get("magnitude", {}),
                        "significance": c_data.get("significance", "MINOR"),
                        "confidence": c_data.get("confidence", 1.0),
                        "evidence": evidence_list,
                        "validation_issues": validation_issues_list,
                        "status": CandidateStatus.NEW.value,
                    },
                )
                created_candidates.append(cand_record)

            # Stage 8: Completed
            summary = {
                "total_candidates_detected": len(created_candidates),
                "by_significance": {
                    "MAJOR": sum(1 for c in created_candidates if c.significance == "MAJOR"),
                    "MODERATE": sum(1 for c in created_candidates if c.significance == "MODERATE"),
                    "MINOR": sum(1 for c in created_candidates if c.significance == "MINOR"),
                },
                "by_type": {},
            }
            for c in created_candidates:
                summary["by_type"][c.change_type] = summary["by_type"].get(c.change_type, 0) + 1

            await temporal_repository.update_run(
                db,
                run_id,
                {
                    "status": ChangeRunStatus.COMPLETED.value,
                    "completed_at": datetime.now(timezone.utc),
                    "summary": summary,
                },
            )

            return await temporal_repository.get_run(db, run_id)

        except Exception as e:
            logger.error(f"Change detection run {run_id} failed: {e}", exc_info=True)
            await temporal_repository.update_run(
                db,
                run_id,
                {
                    "status": ChangeRunStatus.FAILED.value,
                    "completed_at": datetime.now(timezone.utc),
                    "summary": {"error": "EXECUTION_EXCEPTION", "message": str(e)},
                },
            )
            return await temporal_repository.get_run(db, run_id)


change_worker = ChangeDetectionWorker()
