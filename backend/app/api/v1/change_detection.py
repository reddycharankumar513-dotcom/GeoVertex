from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundException
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.temporal import CandidateStatus, ChangeRunStatus, ChangeSignificance, ChangeType
from app.models.user import User, UserRole
from app.repositories.temporal_repository import temporal_repository
from app.schemas.temporal import (
    ChangeCandidateResponse,
    ChangeCandidateReviewRequest,
    ChangeDetectionRunCreate,
    ChangeDetectionRunResponse,
    PropertySnapshotCreate,
    PropertySnapshotResponse,
    RasterObservationCreate,
    RasterObservationResponse,
    TemporalMetricsResponse,
    TimelineEntryResponse,
)
from app.services.change_detection_service import change_detection_service

router = APIRouter(prefix="/change-detection", tags=["AI Change Detection & Temporal Intelligence"])


# 1. Snapshots
@router.post("/snapshots", response_model=PropertySnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    payload: PropertySnapshotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates an authoritative or survey temporal snapshot for a cadastral entity."""
    data = payload.model_dump()
    attrs = data.pop("attributes", {})
    data["attributes_json"] = attrs
    return await change_detection_service.create_snapshot(db, data, current_user)


@router.get("/snapshots", response_model=List[PropertySnapshotResponse])
async def list_snapshots(
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    is_current: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists temporal property snapshots with optional entity filters."""
    return await temporal_repository.list_snapshots(
        db, entity_type=entity_type, entity_id=entity_id, is_current=is_current, skip=skip, limit=limit
    )


# 2. Change Detection Runs
@router.post("/runs", response_model=ChangeDetectionRunResponse, status_code=status.HTTP_201_CREATED)
async def dispatch_run(
    payload: ChangeDetectionRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Triggers an AI/deterministic change detection job across temporal snapshots."""
    return await change_detection_service.dispatch_run(
        db=db,
        target_type=payload.target_type,
        target_id=payload.target_id,
        baseline_reference=payload.baseline_reference,
        comparison_reference=payload.comparison_reference,
        detection_method=payload.detection_method.value,
        parameters=payload.parameters,
        current_user=current_user,
        background_tasks=background_tasks,
    )


@router.get("/runs", response_model=List[ChangeDetectionRunResponse])
async def list_runs(
    target_type: Optional[str] = None,
    status: Optional[str] = None,
    detection_method: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists change detection runs with stage and status filters."""
    return await temporal_repository.list_runs(
        db, target_type=target_type, status=status, detection_method=detection_method, skip=skip, limit=limit
    )


@router.get("/runs/{run_id}", response_model=ChangeDetectionRunResponse)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches detailed status and candidate summary for a change detection run."""
    run = await temporal_repository.get_run(db, run_id)
    if not run:
        raise NotFoundException(f"Run {run_id} not found")
    return run


@router.post("/runs/{run_id}/cancel", response_model=ChangeDetectionRunResponse)
async def cancel_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancels a pending or active change detection run."""
    return await change_detection_service.cancel_run(db, run_id, current_user)


@router.get("/runs/{run_id}/changes", response_model=List[ChangeCandidateResponse])
async def get_run_changes(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists change candidates specifically produced by a change detection run."""
    return await temporal_repository.list_candidates(db, detection_run_id=run_id, limit=200)


# 3. Change Candidates & Human Review
@router.get("/changes", response_model=List[ChangeCandidateResponse])
async def list_candidates(
    detection_run_id: Optional[uuid.UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    change_type: Optional[str] = None,
    status: Optional[str] = None,
    significance: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Searches and filters change candidates across entities and jurisdictions."""
    return await temporal_repository.list_candidates(
        db,
        detection_run_id=detection_run_id,
        entity_type=entity_type,
        entity_id=entity_id,
        change_type=change_type,
        status=status,
        significance=significance,
        skip=skip,
        limit=limit,
    )


@router.get("/changes/{candidate_id}", response_model=ChangeCandidateResponse)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Inspects detailed candidate metrics, difference geometry, evidence, and validation findings."""
    candidate = await temporal_repository.get_candidate(db, candidate_id)
    if not candidate:
        raise NotFoundException(f"Change candidate {candidate_id} not found")
    return candidate


@router.post("/changes/{candidate_id}/confirm", response_model=ChangeCandidateResponse)
async def confirm_candidate(
    candidate_id: uuid.UUID,
    payload: ChangeCandidateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirms candidate change as verified physical or record modification (Cadastral Officer)."""
    return await change_detection_service.review_candidate(
        db=db,
        candidate_id=candidate_id,
        action="CONFIRM",
        review_reason=payload.review_reason.value if payload.review_reason else "CONFIRMED_FIELD_SURVEY",
        review_notes=payload.review_notes,
        current_user=current_user,
    )


@router.post("/changes/{candidate_id}/reject", response_model=ChangeCandidateResponse)
async def reject_candidate(
    candidate_id: uuid.UUID,
    payload: ChangeCandidateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rejects candidate change with mandatory reason code (e.g. FALSE_POSITIVE, DATA_ALIGNMENT_ERROR)."""
    return await change_detection_service.review_candidate(
        db=db,
        candidate_id=candidate_id,
        action="REJECT",
        review_reason=payload.review_reason.value if payload.review_reason else None,
        review_notes=payload.review_notes,
        current_user=current_user,
    )


@router.post("/changes/{candidate_id}/dismiss", response_model=ChangeCandidateResponse)
async def dismiss_candidate(
    candidate_id: uuid.UUID,
    payload: ChangeCandidateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismisses candidate change as non-actionable or trivial."""
    return await change_detection_service.review_candidate(
        db=db,
        candidate_id=candidate_id,
        action="DISMISS",
        review_reason=payload.review_reason.value if payload.review_reason else None,
        review_notes=payload.review_notes,
        current_user=current_user,
    )


# 4. Temporal Timeline
@router.get("/entities/{entity_type}/{entity_id}/timeline", response_model=List[TimelineEntryResponse])
async def get_entity_timeline(
    entity_type: str,
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Builds a complete historical timeline across snapshots, surveys, documents, and detected changes."""
    return await change_detection_service.get_entity_timeline(db, entity_type.upper(), entity_id)


# 5. Metrics & Analytics
@router.get("/metrics", response_model=TemporalMetricsResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns dashboard metrics and totals across all change detection operations."""
    return await temporal_repository.get_metrics(db)


# 6. Raster Observations
@router.post("/raster-observations", response_model=RasterObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_raster_observation(
    payload: RasterObservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registers an orthophoto, drone, or satellite raster observation."""
    data = payload.model_dump()
    data["id"] = uuid.uuid4()
    return await temporal_repository.create_raster_observation(db, data)


@router.get("/raster-observations", response_model=List[RasterObservationResponse])
async def list_raster_observations(
    source: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists registered raster imagery observations."""
    return await temporal_repository.list_raster_observations(db, source=source, skip=skip, limit=limit)
