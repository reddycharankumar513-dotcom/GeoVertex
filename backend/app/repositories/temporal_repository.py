from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.temporal import (
    CandidateStatus,
    ChangeCandidate,
    ChangeDetectionRun,
    ChangeRunStatus,
    PropertySnapshot,
    RasterObservation,
)


class TemporalRepository:
    """Data access layer for temporal snapshots, change detection runs, and change candidates."""

    # 1. Snapshots
    async def create_snapshot(self, db: AsyncSession, data: Dict[str, Any]) -> PropertySnapshot:
        snapshot = PropertySnapshot(**data)
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        return snapshot

    async def get_snapshot(self, db: AsyncSession, snapshot_id: uuid.UUID) -> Optional[PropertySnapshot]:
        stmt = select(PropertySnapshot).where(PropertySnapshot.id == snapshot_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_snapshots(
        self,
        db: AsyncSession,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        is_current: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PropertySnapshot]:
        stmt = select(PropertySnapshot)
        if entity_type:
            stmt = stmt.where(PropertySnapshot.entity_type == entity_type.upper())
        if entity_id:
            stmt = stmt.where(PropertySnapshot.entity_id == entity_id)
        if is_current is not None:
            stmt = stmt.where(PropertySnapshot.is_current == is_current)
        stmt = stmt.order_by(desc(PropertySnapshot.effective_from)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 2. Change Detection Runs
    async def create_run(self, db: AsyncSession, data: Dict[str, Any]) -> ChangeDetectionRun:
        run = ChangeDetectionRun(**data)
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run

    async def get_run(self, db: AsyncSession, run_id: uuid.UUID) -> Optional[ChangeDetectionRun]:
        stmt = select(ChangeDetectionRun).where(ChangeDetectionRun.id == run_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_runs(
        self,
        db: AsyncSession,
        target_type: Optional[str] = None,
        status: Optional[str] = None,
        detection_method: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ChangeDetectionRun]:
        stmt = select(ChangeDetectionRun)
        if target_type:
            stmt = stmt.where(ChangeDetectionRun.target_type == target_type.upper())
        if status:
            stmt = stmt.where(ChangeDetectionRun.status == status.upper())
        if detection_method:
            stmt = stmt.where(ChangeDetectionRun.detection_method == detection_method.upper())
        stmt = stmt.order_by(desc(ChangeDetectionRun.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_run(
        self, db: AsyncSession, run_id: uuid.UUID, update_dict: Dict[str, Any]
    ) -> Optional[ChangeDetectionRun]:
        run = await self.get_run(db, run_id)
        if not run:
            return None
        for key, val in update_dict.items():
            if hasattr(run, key):
                setattr(run, key, val)
        await db.commit()
        await db.refresh(run)
        return run

    # 3. Change Candidates
    async def create_candidate(self, db: AsyncSession, data: Dict[str, Any]) -> ChangeCandidate:
        candidate = ChangeCandidate(**data)
        db.add(candidate)
        await db.commit()
        await db.refresh(candidate)
        return candidate

    async def get_candidate(self, db: AsyncSession, candidate_id: uuid.UUID) -> Optional[ChangeCandidate]:
        stmt = select(ChangeCandidate).where(ChangeCandidate.id == candidate_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_candidates(
        self,
        db: AsyncSession,
        detection_run_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        change_type: Optional[str] = None,
        status: Optional[str] = None,
        significance: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ChangeCandidate]:
        stmt = select(ChangeCandidate)
        if detection_run_id:
            stmt = stmt.where(ChangeCandidate.detection_run_id == detection_run_id)
        if entity_type:
            stmt = stmt.where(ChangeCandidate.entity_type == entity_type.upper())
        if entity_id:
            stmt = stmt.where(ChangeCandidate.entity_id == entity_id)
        if change_type:
            stmt = stmt.where(ChangeCandidate.change_type == change_type.upper())
        if status:
            stmt = stmt.where(ChangeCandidate.status == status.upper())
        if significance:
            stmt = stmt.where(ChangeCandidate.significance == significance.upper())
        stmt = stmt.order_by(desc(ChangeCandidate.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_candidate(
        self, db: AsyncSession, candidate_id: uuid.UUID, update_dict: Dict[str, Any]
    ) -> Optional[ChangeCandidate]:
        cand = await self.get_candidate(db, candidate_id)
        if not cand:
            return None
        for key, val in update_dict.items():
            if hasattr(cand, key):
                setattr(cand, key, val)
        await db.commit()
        await db.refresh(cand)
        return cand

    # 4. Raster Observations
    async def create_raster_observation(
        self, db: AsyncSession, data: Dict[str, Any]
    ) -> RasterObservation:
        obs = RasterObservation(**data)
        db.add(obs)
        await db.commit()
        await db.refresh(obs)
        return obs

    async def list_raster_observations(
        self, db: AsyncSession, source: Optional[str] = None, skip: int = 0, limit: int = 50
    ) -> List[RasterObservation]:
        stmt = select(RasterObservation)
        if source:
            stmt = stmt.where(RasterObservation.source == source.upper())
        stmt = stmt.order_by(desc(RasterObservation.acquisition_date)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 5. Metrics
    async def get_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        total_runs = (await db.execute(select(func.count(ChangeDetectionRun.id)))).scalar() or 0
        total_candidates = (await db.execute(select(func.count(ChangeCandidate.id)))).scalar() or 0
        under_review = (
            await db.execute(
                select(func.count(ChangeCandidate.id)).where(ChangeCandidate.status == CandidateStatus.UNDER_REVIEW.value)
            )
        ).scalar() or 0
        confirmed = (
            await db.execute(
                select(func.count(ChangeCandidate.id)).where(ChangeCandidate.status == CandidateStatus.CONFIRMED.value)
            )
        ).scalar() or 0
        rejected = (
            await db.execute(
                select(func.count(ChangeCandidate.id)).where(ChangeCandidate.status == CandidateStatus.REJECTED.value)
            )
        ).scalar() or 0
        dismissed = (
            await db.execute(
                select(func.count(ChangeCandidate.id)).where(ChangeCandidate.status == CandidateStatus.DISMISSED.value)
            )
        ).scalar() or 0

        # Change type counts
        building_changes = (
            await db.execute(
                select(func.count(ChangeCandidate.id)).where(ChangeCandidate.change_type.like("BUILDING_%"))
            )
        ).scalar() or 0
        floor_changes = (
            await db.execute(
                select(func.count(ChangeCandidate.id)).where(ChangeCandidate.change_type.like("FLOOR_%"))
            )
        ).scalar() or 0
        parcel_changes = (
            await db.execute(
                select(func.count(ChangeCandidate.id)).where(ChangeCandidate.change_type.like("PARCEL_%"))
            )
        ).scalar() or 0

        return {
            "total_runs": total_runs,
            "total_candidates": total_candidates,
            "under_review": under_review,
            "confirmed": confirmed,
            "rejected": rejected,
            "dismissed": dismissed,
            "building_changes": building_changes,
            "floor_changes": floor_changes,
            "parcel_changes": parcel_changes,
        }


temporal_repository = TemporalRepository()
