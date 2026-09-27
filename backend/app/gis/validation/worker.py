import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.gis.validation.base import ValidationContext
from app.gis.validation.engine import validation_engine
from app.gis.validation.tolerances import ValidationToleranceConfig, default_tolerances
from app.models.ai import BuildingExtractionResult
from app.models.building import BuildingFootprint
from app.models.floor import Floor
from app.models.jurisdiction import Jurisdiction
from app.models.parcel import Parcel
from app.models.survey import SurveyObservation, SurveySubmission
from app.models.unit import PropertyUnit
from app.models.validation import ValidationIssue, ValidationRun
from app.models.document import PropertyDocument, DocumentExtractedField
from app.repositories.audit_repository import audit_repository
from app.repositories.validation_repository import validation_repository

logger = logging.getLogger(__name__)


class ValidationWorker:
    """Asynchronous worker executing deterministic cadastral and topology validation runs."""

    async def execute_validation_run(
        self,
        run_id: uuid.UUID,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Entrypoint for executing a queued validation run."""
        if session is not None:
            await self._run_with_db(session, run_id)
        else:
            async with AsyncSessionLocal() as db:
                await self._run_with_db(db, run_id)

    async def _run_with_db(self, db: AsyncSession, run_id: uuid.UUID) -> None:
        run = await validation_repository.get_run_by_id(db, run_id)
        if not run or run.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            return

        start_time = datetime.now(timezone.utc)
        run.status = "RUNNING"
        run.stage = "PREPARING_DATA"
        run.started_at = start_time
        await db.commit()

        try:
            # 1. Prepare Validation Context
            params = run.parameters or {}
            tol_overrides = params.get("tolerance_overrides")
            tolerances = ValidationToleranceConfig.from_overrides(tol_overrides) if tol_overrides else default_tolerances

            context = ValidationContext(
                target_type=run.target_type,
                target_id=run.target_id,
                tolerances=tolerances,
                parameters=params,
            )

            if "geometry_wkt" in params and params["geometry_wkt"]:
                context.raw_geometries["ad_hoc_target"] = params["geometry_wkt"]

            # Load relevant entities based on target scope
            await self._load_context_data(db, context)

            # 2. Stage: Running Rules
            run.stage = "RUNNING_RULES"
            await db.commit()

            rules_filter = params.get("rules_filter")
            result = validation_engine.execute_validation(context, rule_ids_filter=rules_filter)

            # 3. Stage: Generating & Persisting Issues
            run.stage = "GENERATING_ISSUES"
            await db.commit()

            issues_to_create = []
            for d in result["issues"]:
                issues_to_create.append({
                    "id": uuid.uuid4(),
                    "validation_run_id": run.id,
                    "rule_id": d.rule_id,
                    "rule_version": d.rule_version,
                    "issue_code": d.issue_code,
                    "category": d.category,
                    "severity": d.severity,
                    "status": "OPEN",
                    "entity_type": d.entity_type,
                    "entity_id": d.entity_id,
                    "related_entity_type": d.related_entity_type,
                    "related_entity_id": d.related_entity_id,
                    "message": d.message,
                    "technical_explanation": d.technical_explanation,
                    "geometry": None,
                    "geometry_wkt": d.geometry_wkt,
                    "measured_value": d.measured_value,
                    "expected_value": d.expected_value,
                    "tolerance": d.tolerance,
                    "metadata_json": d.metadata_json,
                })

            if issues_to_create:
                await validation_repository.create_issues(db, issues_to_create)

            # 4. Stage: Summarizing
            run.stage = "SUMMARIZING"
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            run.summary = result["summary"]
            run.duration_ms = duration_ms
            run.status = "COMPLETED"
            run.stage = "COMPLETED"
            run.completed_at = end_time

            await audit_repository.log_event(
                db=db,
                action="VALIDATION_COMPLETED",
                entity_type="VALIDATION_RUN",
                entity_id=str(run.id),
                actor_user_id=run.requested_by,
                details={
                    "target_type": run.target_type,
                    "target_id": run.target_id,
                    "total_issues": result["summary"]["total_issues"],
                    "critical": result["summary"]["critical"],
                    "errors": result["summary"]["errors"],
                    "warnings": result["summary"]["warnings"],
                    "duration_ms": duration_ms,
                },
            )

            await db.commit()
            logger.info(f"ValidationRun {run.id} completed: {result['summary']['total_issues']} issues found in {duration_ms}ms")

        except Exception as e:
            logger.exception(f"ValidationRun {run.id} failed: {str(e)}")
            run.status = "FAILED"
            run.stage = "FAILED"
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

    async def _load_context_data(self, db: AsyncSession, context: ValidationContext) -> None:
        """Loads bounded entity sets into ValidationContext for rule evaluation."""
        target_type = context.target_type.upper()
        target_id = context.target_id

        # Always load jurisdictions for spatial context
        jur_res = await db.execute(select(Jurisdiction))
        context.jurisdictions = list(jur_res.scalars().all())

        if target_type == "PARCEL" and target_id:
            # Load specific parcel and its immediate spatial context
            p_res = await db.execute(select(Parcel).where((Parcel.id == target_id) | (Parcel.parcel_number == target_id)))
            target_parcel = p_res.scalar_one_or_none()
            if target_parcel:
                context.parcels.append(target_parcel)
                # Load buildings on parcel
                b_res = await db.execute(select(BuildingFootprint).where(BuildingFootprint.parcel_id == target_parcel.id))
                context.buildings = list(b_res.scalars().all())
                # Load floors and units for these buildings
                if context.buildings:
                    bld_ids = [b.id for b in context.buildings]
                    f_res = await db.execute(select(Floor).where(Floor.building_id.in_(bld_ids)))
                    context.floors = list(f_res.scalars().all())
                    u_res = await db.execute(select(PropertyUnit).where(PropertyUnit.building_id.in_(bld_ids)))
                    context.units = list(u_res.scalars().all())
                # Also load other parcels in same jurisdiction for overlap detection
                if target_parcel.jurisdiction_id:
                    adj_p = await db.execute(select(Parcel).where(Parcel.jurisdiction_id == target_parcel.jurisdiction_id).limit(20))
                    for p in adj_p.scalars().all():
                        if p.id != target_parcel.id:
                            context.parcels.append(p)

        elif target_type == "BUILDING" and target_id:
            b_res = await db.execute(select(BuildingFootprint).where((BuildingFootprint.id == target_id) | (BuildingFootprint.building_reference == target_id)))
            target_bld = b_res.scalar_one_or_none()
            if target_bld:
                context.buildings.append(target_bld)
                # Load parent parcel
                if target_bld.parcel_id:
                    p_res = await db.execute(select(Parcel).where(Parcel.id == target_bld.parcel_id))
                    p = p_res.scalar_one_or_none()
                    if p:
                        context.parcels.append(p)
                # Load floors and units
                f_res = await db.execute(select(Floor).where(Floor.building_id == target_bld.id))
                context.floors = list(f_res.scalars().all())
                u_res = await db.execute(select(PropertyUnit).where(PropertyUnit.building_id == target_bld.id))
                context.units = list(u_res.scalars().all())
                # Load neighboring buildings for overlap
                other_b = await db.execute(select(BuildingFootprint).where(BuildingFootprint.id != target_bld.id).limit(10))
                for ob in other_b.scalars().all():
                    context.buildings.append(ob)

        elif target_type == "FLOOR" and target_id:
            f_res = await db.execute(select(Floor).where(Floor.id == target_id))
            target_floor = f_res.scalar_one_or_none()
            if target_floor:
                context.floors.append(target_floor)
                # Load sibling floors and parent building
                b_res = await db.execute(select(BuildingFootprint).where(BuildingFootprint.id == target_floor.building_id))
                b = b_res.scalar_one_or_none()
                if b:
                    context.buildings.append(b)
                all_f = await db.execute(select(Floor).where(Floor.building_id == target_floor.building_id))
                context.floors = list(all_f.scalars().all())
                u_res = await db.execute(select(PropertyUnit).where(PropertyUnit.floor_id == target_floor.id))
                context.units = list(u_res.scalars().all())

        elif target_type == "UNIT" and target_id:
            u_res = await db.execute(select(PropertyUnit).where(PropertyUnit.id == target_id))
            target_unit = u_res.scalar_one_or_none()
            if target_unit:
                context.units.append(target_unit)
                if target_unit.floor_id:
                    f_res = await db.execute(select(Floor).where(Floor.id == target_unit.floor_id))
                    fl = f_res.scalar_one_or_none()
                    if fl:
                        context.floors.append(fl)
                        # Load co-planar sibling units
                        sib_u = await db.execute(select(PropertyUnit).where(PropertyUnit.floor_id == fl.id))
                        context.units = list(sib_u.scalars().all())
                if target_unit.building_id:
                    b_res = await db.execute(select(BuildingFootprint).where(BuildingFootprint.id == target_unit.building_id))
                    b = b_res.scalar_one_or_none()
                    if b:
                        context.buildings.append(b)

        elif target_type == "AI_RESULT" and target_id:
            c_res = await db.execute(select(BuildingExtractionResult).where(BuildingExtractionResult.id == target_id))
            cand = c_res.scalar_one_or_none()
            if cand:
                context.ai_building_candidates.append(cand)
                # Load target building or parcel
                if cand.source_target_id:
                    b_res = await db.execute(select(BuildingFootprint).where(BuildingFootprint.id == cand.source_target_id))
                    b = b_res.scalar_one_or_none()
                    if b:
                        context.buildings.append(b)
                        if b.parcel_id:
                            p_res = await db.execute(select(Parcel).where(Parcel.id == b.parcel_id))
                            p = p_res.scalar_one_or_none()
                            if p:
                                context.parcels.append(p)
                    else:
                        p_res = await db.execute(select(Parcel).where(Parcel.id == cand.source_target_id))
                        p = p_res.scalar_one_or_none()
                        if p:
                            context.parcels.append(p)

        elif target_type == "SURVEY_SUBMISSION" and target_id:
            sub_res = await db.execute(select(SurveySubmission).where(SurveySubmission.id == target_id))
            sub = sub_res.scalar_one_or_none()
            if sub:
                context.survey_submissions.append(sub)
                obs_res = await db.execute(select(SurveyObservation).where(SurveyObservation.session_id == sub.survey_session_id))
                context.survey_observations = list(obs_res.scalars().all())
                # Load buildings and parcels in observations
                for obs in context.survey_observations:
                    if obs.target_type == "BUILDING" and obs.target_id:
                        b_res = await db.execute(select(BuildingFootprint).where(BuildingFootprint.id == obs.target_id))
                        b = b_res.scalar_one_or_none()
                        if b and b not in context.buildings:
                            context.buildings.append(b)

        elif target_type in ["DOCUMENT", "PROPERTY_DOCUMENT"] and target_id:
            d_res = await db.execute(select(PropertyDocument).where((PropertyDocument.id == target_id) | (PropertyDocument.document_reference == target_id)))
            doc = d_res.scalar_one_or_none()
            if doc:
                context.property_documents.append(doc)
                if doc.current_version_id:
                    fld_res = await db.execute(select(DocumentExtractedField).where(DocumentExtractedField.document_version_id == doc.current_version_id))
                    doc.extracted_fields = list(fld_res.scalars().all())
                    context.document_fields.extend(doc.extracted_fields)
                if doc.parcel_id:
                    p_res = await db.execute(select(Parcel).where(Parcel.id == doc.parcel_id))
                    p = p_res.scalar_one_or_none()
                    if p:
                        context.parcels.append(p)
                if doc.building_id:
                    b_res = await db.execute(select(BuildingFootprint).where(BuildingFootprint.id == doc.building_id))
                    b = b_res.scalar_one_or_none()
                    if b:
                        context.buildings.append(b)
                if doc.unit_id:
                    u_res = await db.execute(select(PropertyUnit).where(PropertyUnit.id == doc.unit_id))
                    u = u_res.scalar_one_or_none()
                    if u:
                        context.units.append(u)

        else:
            # Systemic or broad scope: load sample/active entities
            p_res = await db.execute(select(Parcel).limit(50))
            context.parcels = list(p_res.scalars().all())
            b_res = await db.execute(select(BuildingFootprint).limit(50))
            context.buildings = list(b_res.scalars().all())
            f_res = await db.execute(select(Floor).limit(50))
            context.floors = list(f_res.scalars().all())
            u_res = await db.execute(select(PropertyUnit).limit(50))
            context.units = list(u_res.scalars().all())
            c_res = await db.execute(select(BuildingExtractionResult).limit(20))
            context.ai_building_candidates = list(c_res.scalars().all())
            doc_res = await db.execute(select(PropertyDocument).limit(20))
            context.property_documents = list(doc_res.scalars().all())


validation_worker = ValidationWorker()
