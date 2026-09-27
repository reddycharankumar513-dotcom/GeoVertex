from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.errors import BadRequestException, ForbiddenException, NotFoundException
from app.gis.temporal.timeline import EntityTimelineBuilder
from app.models.building import BuildingFootprint
from app.models.document import PropertyDocument
from app.models.parcel import Parcel
from app.models.survey import SurveyObservation
from app.models.temporal import (
    CandidateStatus,
    ChangeCandidate,
    ChangeDetectionRun,
    ChangeRunStatus,
    PropertySnapshot,
    ReviewReason,
)
from app.models.user import User, UserRole
from app.repositories.audit_repository import audit_repository
from app.repositories.temporal_repository import temporal_repository
from app.workers.change_worker import change_worker


class ChangeDetectionService:
    """Service managing temporal snapshots, change detection runs, human reviews, and audit logs."""

    # 1. Snapshots
    async def create_snapshot(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
        current_user: User,
    ) -> PropertySnapshot:
        if current_user.role == UserRole.CITIZEN:
            raise ForbiddenException("Citizens are not permitted to create snapshots directly.")

        data["id"] = data.get("id") or uuid.uuid4()
        data["created_by"] = current_user.id
        if "effective_from" not in data:
            data["effective_from"] = datetime.now(timezone.utc)

        snapshot = await temporal_repository.create_snapshot(db, data)

        await audit_repository.log_event(
            db=db,
            action="PROPERTY_SNAPSHOT_CREATED",
            entity_type=snapshot.entity_type,
            entity_id=str(snapshot.entity_id),
            actor_user_id=current_user.id,
            details={
                "snapshot_id": str(snapshot.id),
                "snapshot_type": snapshot.snapshot_type,
                "version_number": snapshot.version_number,
            },
        )
        return snapshot

    # 2. Runs
    async def dispatch_run(
        self,
        db: AsyncSession,
        target_type: str,
        target_id: Optional[uuid.UUID],
        baseline_reference: str,
        comparison_reference: str,
        detection_method: str,
        parameters: Dict[str, Any],
        current_user: User,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> ChangeDetectionRun:
        if current_user.role == UserRole.CITIZEN:
            raise ForbiddenException("Citizens are not permitted to trigger change detection jobs.")

        run_id = uuid.uuid4()
        run_data = {
            "id": run_id,
            "target_type": target_type.upper(),
            "target_id": target_id,
            "jurisdiction_id": parameters.get("jurisdiction_id"),
            "baseline_reference": baseline_reference,
            "comparison_reference": comparison_reference,
            "detection_method": detection_method.upper(),
            "status": ChangeRunStatus.QUEUED.value,
            "requested_by": current_user.id,
            "parameters": parameters,
            "ruleset_version": "1.0.0",
            "summary": {},
        }

        run = await temporal_repository.create_run(db, run_data)

        await audit_repository.log_event(
            db=db,
            action="CHANGE_DETECTION_REQUESTED",
            entity_type=target_type,
            entity_id=str(target_id or run_id),
            actor_user_id=current_user.id,
            details={
                "run_id": str(run_id),
                "detection_method": detection_method,
                "baseline_reference": baseline_reference,
                "comparison_reference": comparison_reference,
            },
        )

        # Execute worker inline or background
        if background_tasks:
            # Let worker run in background task
            # For testing and fast execution, run directly
            return await change_worker.execute_run(db, run_id)
        else:
            return await change_worker.execute_run(db, run_id)

    async def cancel_run(self, db: AsyncSession, run_id: uuid.UUID, current_user: User) -> ChangeDetectionRun:
        run = await temporal_repository.get_run(db, run_id)
        if not run:
            raise NotFoundException(f"Run {run_id} not found")
        if run.status in [ChangeRunStatus.COMPLETED.value, ChangeRunStatus.FAILED.value]:
            raise BadRequestException(f"Cannot cancel run in terminal state '{run.status}'")

        updated = await temporal_repository.update_run(
            db, run_id, {"status": ChangeRunStatus.CANCELLED.value, "completed_at": datetime.now(timezone.utc)}
        )
        await audit_repository.log_event(
            db=db,
            action="CHANGE_DETECTION_CANCELLED",
            entity_type="CHANGE_DETECTION_RUN",
            entity_id=str(run_id),
            actor_user_id=current_user.id,
            details={"run_id": str(run_id)},
        )
        return updated

    # 3. Candidates and Human Review
    async def review_candidate(
        self,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        action: str,  # CONFIRM, REJECT, DISMISS
        review_reason: Optional[str],
        review_notes: Optional[str],
        current_user: User,
    ) -> ChangeCandidate:
        if current_user.role == UserRole.CITIZEN:
            raise ForbiddenException("Citizens cannot review change candidates.")

        candidate = await temporal_repository.get_candidate(db, candidate_id)
        if not candidate:
            raise NotFoundException(f"Change candidate {candidate_id} not found")

        action_upper = action.upper()
        if action_upper not in ["CONFIRM", "REJECT", "DISMISS"]:
            raise BadRequestException(f"Invalid review action: '{action}'. Must be CONFIRM, REJECT, or DISMISS.")

        if action_upper in ["REJECT", "DISMISS"] and not review_reason:
            raise BadRequestException("A valid review reason is mandatory when rejecting or dismissing a change candidate.")

        status_map = {
            "CONFIRM": CandidateStatus.CONFIRMED.value,
            "REJECT": CandidateStatus.REJECTED.value,
            "DISMISS": CandidateStatus.DISMISSED.value,
        }
        new_status = status_map[action_upper]

        updated = await temporal_repository.update_candidate(
            db,
            candidate_id,
            {
                "status": new_status,
                "review_reason": review_reason,
                "review_notes": review_notes,
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.now(timezone.utc),
            },
        )

        audit_action = f"CHANGE_CANDIDATE_{new_status}"
        await audit_repository.log_event(
            db=db,
            action=audit_action,
            entity_type=candidate.entity_type,
            entity_id=str(candidate.entity_id or candidate.id),
            actor_user_id=current_user.id,
            details={
                "candidate_id": str(candidate_id),
                "change_type": candidate.change_type,
                "status": new_status,
                "review_reason": review_reason,
                "review_notes": review_notes,
            },
        )
        return updated

    # 4. Timeline
    async def get_entity_timeline(
        self, db: AsyncSession, entity_type: str, entity_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        # Fetch snapshots
        snapshots = await temporal_repository.list_snapshots(
            db, entity_type=entity_type, entity_id=entity_id, limit=100
        )
        # Fetch changes
        changes = await temporal_repository.list_candidates(
            db, entity_type=entity_type, entity_id=entity_id, limit=100
        )

        # Fetch surveys
        surv_stmt = select(SurveyObservation).where(
            (SurveyObservation.target_type == entity_type) & (SurveyObservation.target_id == entity_id)
        )
        surveys = (await db.execute(surv_stmt)).scalars().all()

        # Fetch documents
        doc_stmt = select(PropertyDocument)
        if entity_type == "BUILDING":
            doc_stmt = doc_stmt.where(PropertyDocument.building_id == entity_id)
        elif entity_type == "PARCEL":
            doc_stmt = doc_stmt.where(PropertyDocument.parcel_id == entity_id)
        documents = (await db.execute(doc_stmt)).scalars().all()

        return EntityTimelineBuilder.build_timeline(
            snapshots=snapshots, changes=changes, surveys=surveys, documents=documents
        )


change_detection_service = ChangeDetectionService()
