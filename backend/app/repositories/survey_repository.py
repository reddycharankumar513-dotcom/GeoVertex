import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.survey import (
    SurveyProject,
    SurveyAssignment,
    SurveySession,
    SurveyObservation,
    SurveyEvidence,
    SurveySubmission,
    SyncOperation,
)


class SurveyProjectRepository:
    """Data access repository for SurveyProject entities."""

    async def get_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> Optional[SurveyProject]:
        stmt = select(SurveyProject).where(SurveyProject.id == id).options(
            selectinload(SurveyProject.organization),
            selectinload(SurveyProject.jurisdiction),
            selectinload(SurveyProject.creator),
            selectinload(SurveyProject.assignments),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[SurveyProject]:
        stmt = select(SurveyProject).where(SurveyProject.code == code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        organization_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SurveyProject], int]:
        stmt = select(SurveyProject).options(
            selectinload(SurveyProject.organization),
            selectinload(SurveyProject.jurisdiction),
            selectinload(SurveyProject.assignments),
        )
        count_stmt = select(func.count(SurveyProject.id))

        if jurisdiction_id:
            stmt = stmt.where(SurveyProject.jurisdiction_id == jurisdiction_id)
            count_stmt = count_stmt.where(SurveyProject.jurisdiction_id == jurisdiction_id)
        if organization_id:
            stmt = stmt.where(SurveyProject.organization_id == organization_id)
            count_stmt = count_stmt.where(SurveyProject.organization_id == organization_id)
        if status:
            stmt = stmt.where(SurveyProject.status == status)
            count_stmt = count_stmt.where(SurveyProject.status == status)

        stmt = stmt.order_by(SurveyProject.created_at.desc()).offset(skip).limit(limit)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await db.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def create(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
        created_by: Optional[uuid.UUID] = None,
    ) -> SurveyProject:
        if created_by:
            data["created_by"] = created_by
        project = SurveyProject(**data)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: Dict[str, Any],
    ) -> Optional[SurveyProject]:
        project = await self.get_by_id(db, id)
        if not project:
            return None
        for key, val in data.items():
            if hasattr(project, key) and val is not None:
                setattr(project, key, val)
        await db.commit()
        await db.refresh(project)
        return project


class SurveyAssignmentRepository:
    """Data access repository for SurveyAssignment entities."""

    async def get_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> Optional[SurveyAssignment]:
        stmt = (
            select(SurveyAssignment)
            .where(SurveyAssignment.id == id)
            .options(
                selectinload(SurveyAssignment.project),
                selectinload(SurveyAssignment.surveyor),
                selectinload(SurveyAssignment.jurisdiction),
                selectinload(SurveyAssignment.parcel),
                selectinload(SurveyAssignment.property),
                selectinload(SurveyAssignment.building),
                selectinload(SurveyAssignment.floor),
                selectinload(SurveyAssignment.unit),
                selectinload(SurveyAssignment.sessions),
                selectinload(SurveyAssignment.submissions),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        surveyor_id: Optional[uuid.UUID] = None,
        survey_project_id: Optional[uuid.UUID] = None,
        jurisdiction_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SurveyAssignment], int]:
        stmt = (
            select(SurveyAssignment)
            .options(
                selectinload(SurveyAssignment.project),
                selectinload(SurveyAssignment.surveyor),
                selectinload(SurveyAssignment.jurisdiction),
                selectinload(SurveyAssignment.parcel),
                selectinload(SurveyAssignment.property),
                selectinload(SurveyAssignment.building),
                selectinload(SurveyAssignment.floor),
                selectinload(SurveyAssignment.unit),
                selectinload(SurveyAssignment.sessions),
                selectinload(SurveyAssignment.submissions),
            )
        )
        count_stmt = select(func.count(SurveyAssignment.id))

        if surveyor_id:
            stmt = stmt.where(SurveyAssignment.surveyor_id == surveyor_id)
            count_stmt = count_stmt.where(SurveyAssignment.surveyor_id == surveyor_id)
        if survey_project_id:
            stmt = stmt.where(SurveyAssignment.survey_project_id == survey_project_id)
            count_stmt = count_stmt.where(SurveyAssignment.survey_project_id == survey_project_id)
        if jurisdiction_id:
            stmt = stmt.where(SurveyAssignment.jurisdiction_id == jurisdiction_id)
            count_stmt = count_stmt.where(SurveyAssignment.jurisdiction_id == jurisdiction_id)
        if status:
            stmt = stmt.where(SurveyAssignment.status == status)
            count_stmt = count_stmt.where(SurveyAssignment.status == status)
        if priority:
            stmt = stmt.where(SurveyAssignment.priority == priority)
            count_stmt = count_stmt.where(SurveyAssignment.priority == priority)

        stmt = stmt.order_by(SurveyAssignment.assigned_at.desc()).offset(skip).limit(limit)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await db.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def create(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
        created_by: Optional[uuid.UUID] = None,
    ) -> SurveyAssignment:
        if created_by:
            data["created_by"] = created_by
        assignment = SurveyAssignment(**data)
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        return assignment

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: Dict[str, Any],
    ) -> Optional[SurveyAssignment]:
        assignment = await self.get_by_id(db, id)
        if not assignment:
            return None
        for key, val in data.items():
            if hasattr(assignment, key) and val is not None:
                setattr(assignment, key, val)
        await db.commit()
        await db.refresh(assignment)
        return assignment


class SurveySessionRepository:
    """Data access repository for SurveySession entities."""

    async def get_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> Optional[SurveySession]:
        stmt = (
            select(SurveySession)
            .where(SurveySession.id == id)
            .options(
                selectinload(SurveySession.assignment).selectinload(SurveyAssignment.project),
                selectinload(SurveySession.assignment).selectinload(SurveyAssignment.parcel),
                selectinload(SurveySession.assignment).selectinload(SurveyAssignment.building),
                selectinload(SurveySession.assignment).selectinload(SurveyAssignment.floor),
                selectinload(SurveySession.assignment).selectinload(SurveyAssignment.unit),
                selectinload(SurveySession.assignment).selectinload(SurveyAssignment.sessions),
                selectinload(SurveySession.assignment).selectinload(SurveyAssignment.submissions),
                selectinload(SurveySession.surveyor),
                selectinload(SurveySession.observations),
                selectinload(SurveySession.evidence),
                selectinload(SurveySession.submissions),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_assignment(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
    ) -> List[SurveySession]:
        stmt = (
            select(SurveySession)
            .where(SurveySession.assignment_id == assignment_id)
            .options(
                selectinload(SurveySession.observations),
                selectinload(SurveySession.evidence),
                selectinload(SurveySession.submissions),
            )
            .order_by(SurveySession.started_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_session_for_assignment(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
    ) -> Optional[SurveySession]:
        stmt = (
            select(SurveySession)
            .where(
                SurveySession.assignment_id == assignment_id,
                SurveySession.status.in_(["DRAFT", "ACTIVE", "PAUSED", "SYNC_PENDING"]),
            )
            .order_by(SurveySession.started_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
    ) -> SurveySession:
        session = SurveySession(**data)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: Dict[str, Any],
    ) -> Optional[SurveySession]:
        session = await self.get_by_id(db, id)
        if not session:
            return None
        for key, val in data.items():
            if hasattr(session, key) and val is not None:
                setattr(session, key, val)
        await db.commit()
        await db.refresh(session)
        return session


class SurveyObservationRepository:
    """Data access repository for SurveyObservation entities."""

    async def get_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> Optional[SurveyObservation]:
        stmt = select(SurveyObservation).where(SurveyObservation.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> List[SurveyObservation]:
        stmt = (
            select(SurveyObservation)
            .where(SurveyObservation.session_id == session_id)
            .order_by(SurveyObservation.captured_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
        captured_by: Optional[uuid.UUID] = None,
    ) -> SurveyObservation:
        if captured_by:
            data["captured_by"] = captured_by
        obs = SurveyObservation(**data)
        db.add(obs)
        await db.commit()
        await db.refresh(obs)
        return obs

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: Dict[str, Any],
    ) -> Optional[SurveyObservation]:
        obs = await self.get_by_id(db, id)
        if not obs:
            return None
        for key, val in data.items():
            if hasattr(obs, key) and val is not None:
                setattr(obs, key, val)
        await db.commit()
        await db.refresh(obs)
        return obs

    async def delete(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> bool:
        obs = await self.get_by_id(db, id)
        if not obs:
            return False
        await db.delete(obs)
        await db.commit()
        return True


class SurveyEvidenceRepository:
    """Data access repository for SurveyEvidence entities."""

    async def get_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> Optional[SurveyEvidence]:
        stmt = select(SurveyEvidence).where(SurveyEvidence.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        sha256_hash: str,
    ) -> Optional[SurveyEvidence]:
        stmt = select(SurveyEvidence).where(
            SurveyEvidence.session_id == session_id,
            SurveyEvidence.sha256_hash == sha256_hash,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> List[SurveyEvidence]:
        stmt = (
            select(SurveyEvidence)
            .where(SurveyEvidence.session_id == session_id)
            .order_by(SurveyEvidence.captured_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
        uploaded_by: Optional[uuid.UUID] = None,
    ) -> SurveyEvidence:
        if uploaded_by:
            data["uploaded_by"] = uploaded_by
        evidence = SurveyEvidence(**data)
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)
        return evidence

    async def delete(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> bool:
        evidence = await self.get_by_id(db, id)
        if not evidence:
            return False
        await db.delete(evidence)
        await db.commit()
        return True


class SurveySubmissionRepository:
    """Data access repository for SurveySubmission entities."""

    async def get_by_id(
        self,
        db: AsyncSession,
        id: uuid.UUID,
    ) -> Optional[SurveySubmission]:
        stmt = (
            select(SurveySubmission)
            .where(SurveySubmission.id == id)
            .options(
                selectinload(SurveySubmission.assignment).selectinload(SurveyAssignment.project),
                selectinload(SurveySubmission.assignment).selectinload(SurveyAssignment.surveyor),
                selectinload(SurveySubmission.assignment).selectinload(SurveyAssignment.parcel),
                selectinload(SurveySubmission.assignment).selectinload(SurveyAssignment.building),
                selectinload(SurveySubmission.session),
                selectinload(SurveySubmission.submitter),
                selectinload(SurveySubmission.reviewer),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_session(
        self,
        db: AsyncSession,
        survey_session_id: uuid.UUID,
    ) -> Optional[SurveySubmission]:
        stmt = (
            select(SurveySubmission)
            .where(SurveySubmission.survey_session_id == survey_session_id)
            .order_by(SurveySubmission.version_number.desc())
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_assignment(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
    ) -> Optional[SurveySubmission]:
        stmt = (
            select(SurveySubmission)
            .where(SurveySubmission.assignment_id == assignment_id)
            .order_by(SurveySubmission.version_number.desc())
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        assignment_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SurveySubmission], int]:
        stmt = (
            select(SurveySubmission)
            .options(
                selectinload(SurveySubmission.assignment).selectinload(SurveyAssignment.project),
                selectinload(SurveySubmission.assignment).selectinload(SurveyAssignment.surveyor),
                selectinload(SurveySubmission.assignment).selectinload(SurveyAssignment.parcel),
                selectinload(SurveySubmission.assignment).selectinload(SurveyAssignment.building),
                selectinload(SurveySubmission.submitter),
                selectinload(SurveySubmission.reviewer),
            )
        )
        count_stmt = select(func.count(SurveySubmission.id))

        if assignment_id:
            stmt = stmt.where(SurveySubmission.assignment_id == assignment_id)
            count_stmt = count_stmt.where(SurveySubmission.assignment_id == assignment_id)
        if status:
            stmt = stmt.where(SurveySubmission.status == status)
            count_stmt = count_stmt.where(SurveySubmission.status == status)

        stmt = stmt.order_by(SurveySubmission.submitted_at.desc()).offset(skip).limit(limit)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await db.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def create(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
    ) -> SurveySubmission:
        submission = SurveySubmission(**data)
        db.add(submission)
        await db.commit()
        await db.refresh(submission)
        return submission

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: Dict[str, Any],
    ) -> Optional[SurveySubmission]:
        sub = await self.get_by_id(db, id)
        if not sub:
            return None
        for key, val in data.items():
            if hasattr(sub, key) and val is not None:
                setattr(sub, key, val)
        await db.commit()
        await db.refresh(sub)
        return sub


class SyncOperationRepository:
    """Data access repository for offline SyncOperation queue items."""

    async def get_by_client_id(
        self,
        db: AsyncSession,
        client_operation_id: str,
    ) -> Optional[SyncOperation]:
        stmt = select(SyncOperation).where(SyncOperation.client_operation_id == client_operation_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
    ) -> SyncOperation:
        sync_op = SyncOperation(**data)
        db.add(sync_op)
        await db.commit()
        await db.refresh(sync_op)
        return sync_op

    async def update(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: Dict[str, Any],
    ) -> Optional[SyncOperation]:
        stmt = select(SyncOperation).where(SyncOperation.id == id)
        result = await db.execute(stmt)
        sync_op = result.scalar_one_or_none()
        if not sync_op:
            return None
        for key, val in data.items():
            if hasattr(sync_op, key) and val is not None:
                setattr(sync_op, key, val)
        await db.commit()
        await db.refresh(sync_op)
        return sync_op


survey_project_repository = SurveyProjectRepository()
survey_assignment_repository = SurveyAssignmentRepository()
survey_session_repository = SurveySessionRepository()
survey_observation_repository = SurveyObservationRepository()
survey_evidence_repository = SurveyEvidenceRepository()
survey_submission_repository = SurveySubmissionRepository()
sync_operation_repository = SyncOperationRepository()
