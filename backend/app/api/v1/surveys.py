import math
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import (
    get_current_user,
    require_admin,
    require_officer_or_admin,
    require_surveyor_or_admin,
    require_editor,
)
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.survey import (
    SurveyProjectCreate,
    SurveyProjectResponse,
    SurveyProjectDetailResponse,
    SurveyAssignmentCreate,
    SurveyAssignmentResponse,
    SurveyAssignmentDetailResponse,
    SurveySessionResponse,
    SurveySessionDetailResponse,
    SurveyObservationCreate,
    SurveyObservationResponse,
    SurveyEvidenceResponse,
    SurveySubmissionResponse,
    SurveySubmissionReviewRequest,
    SurveyValidationSummary,
    SurveyExportData,
    SyncOperationBatchRequest,
    SyncOperationBatchResponse,
)
from app.services.survey_service import survey_service
from app.services.survey_sync_service import survey_sync_service

router = APIRouter(tags=["Surveyor Field Workflow & Data Collection"])


# ============================================================================
# Survey Projects
# ============================================================================

@router.post(
    "/survey-projects",
    response_model=SurveyProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new survey project (Government Officer / Admin)",
)
async def create_survey_project(
    data: SurveyProjectCreate,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.create_project(
        db=db,
        data=data,
        current_user=current_user,
        request=request,
    )


@router.get(
    "/survey-projects",
    response_model=PaginatedResponse[SurveyProjectDetailResponse],
    summary="List all survey projects",
)
async def list_survey_projects(
    jurisdiction_id: Optional[uuid.UUID] = Query(default=None, description="Filter by jurisdiction"),
    organization_id: Optional[uuid.UUID] = Query(default=None, description="Filter by organization"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by project status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await survey_service.list_projects(
        db=db,
        jurisdiction_id=jurisdiction_id,
        organization_id=organization_id,
        status=status_filter,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[SurveyProjectDetailResponse](
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get(
    "/survey-projects/{id}",
    response_model=SurveyProjectDetailResponse,
    summary="Retrieve survey project details with assignment progress",
)
async def get_survey_project(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.get_project(db=db, project_id=id)


@router.post(
    "/survey-projects/{id}/assignments",
    response_model=SurveyAssignmentDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a survey assignment under a project (Government Officer / Admin)",
)
async def create_survey_assignment(
    id: uuid.UUID,
    data: SurveyAssignmentCreate,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.create_assignment(
        db=db,
        project_id=id,
        data=data,
        current_user=current_user,
        request=request,
    )


# ============================================================================
# Survey Assignments
# ============================================================================

@router.get(
    "/survey-assignments",
    response_model=PaginatedResponse[SurveyAssignmentDetailResponse],
    summary="List survey assignments (Surveyor views own; Officer/Admin views all)",
)
async def list_survey_assignments(
    surveyor_id: Optional[uuid.UUID] = Query(default=None, description="Filter by surveyor"),
    survey_project_id: Optional[uuid.UUID] = Query(default=None, description="Filter by survey project"),
    jurisdiction_id: Optional[uuid.UUID] = Query(default=None, description="Filter by jurisdiction"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by assignment status"),
    priority: Optional[str] = Query(default=None, description="Filter by priority"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await survey_service.list_assignments(
        db=db,
        current_user=current_user,
        surveyor_id=surveyor_id,
        survey_project_id=survey_project_id,
        jurisdiction_id=jurisdiction_id,
        status=status_filter,
        priority=priority,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[SurveyAssignmentDetailResponse](
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get(
    "/survey-assignments/{id}",
    response_model=SurveyAssignmentDetailResponse,
    summary="Retrieve survey assignment details and target context",
)
async def get_survey_assignment(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.get_assignment(db=db, assignment_id=id, current_user=current_user)


@router.post(
    "/survey-assignments/{id}/accept",
    response_model=SurveyAssignmentDetailResponse,
    summary="Accept an assigned survey (Surveyor)",
)
async def accept_survey_assignment(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.accept_assignment(
        db=db,
        assignment_id=id,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/survey-assignments/{id}/start",
    response_model=SurveySessionDetailResponse,
    summary="Start or resume field survey session (Surveyor)",
)
async def start_survey_session(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.start_survey(
        db=db,
        assignment_id=id,
        current_user=current_user,
        request=request,
    )


@router.get(
    "/survey-assignments/{id}/export",
    response_model=SurveyExportData,
    summary="Export survey assignment package (Observations, measurements, evidence metadata)",
)
async def export_survey_assignment(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.export_assignment(db=db, assignment_id=id, current_user=current_user)


# ============================================================================
# Survey Sessions & Observations
# ============================================================================

@router.get(
    "/survey-sessions/{id}",
    response_model=SurveySessionDetailResponse,
    summary="Get survey session state and collected items",
)
async def get_survey_session(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.get_session(db=db, session_id=id, current_user=current_user)


@router.post(
    "/survey-sessions/{id}/pause",
    response_model=SurveySessionDetailResponse,
    summary="Pause active field survey session (Surveyor)",
)
async def pause_survey_session(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.pause_session(
        db=db,
        session_id=id,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/survey-sessions/{id}/resume",
    response_model=SurveySessionDetailResponse,
    summary="Resume paused field survey session (Surveyor)",
)
async def resume_survey_session(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.resume_session(
        db=db,
        session_id=id,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/survey-sessions/{id}/observations",
    response_model=SurveyObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a field observation or measurement (Surveyor)",
)
async def create_survey_observation(
    id: uuid.UUID,
    data: SurveyObservationCreate,
    request: Request,
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.create_observation(
        db=db,
        session_id=id,
        data=data,
        current_user=current_user,
        request=request,
    )


@router.get(
    "/survey-sessions/{id}/observations",
    response_model=List[SurveyObservationResponse],
    summary="List all observations recorded in a survey session",
)
async def list_survey_observations(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.list_observations(db=db, session_id=id, current_user=current_user)


@router.post(
    "/survey-sessions/{id}/evidence",
    response_model=SurveyEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload photo or document evidence with SHA-256 hash calculation (Surveyor)",
)
async def upload_survey_evidence(
    id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    evidence_type: str = Form(default="BUILDING_FRONT"),
    target_type: str = Form(default="BUILDING"),
    target_id: str = Form(...),
    description: Optional[str] = Form(default=None),
    latitude: Optional[float] = Form(default=None),
    longitude: Optional[float] = Form(default=None),
    accuracy: Optional[float] = Form(default=None),
    observation_id: Optional[uuid.UUID] = Form(default=None),
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.upload_evidence(
        db=db,
        session_id=id,
        file=file,
        evidence_type=evidence_type,
        target_type=target_type,
        target_id=target_id,
        description=description,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        observation_id=observation_id,
        current_user=current_user,
        request=request,
    )


@router.get(
    "/survey-sessions/{id}/evidence",
    response_model=List[SurveyEvidenceResponse],
    summary="List all photo and document evidence attached to a survey session",
)
async def list_survey_evidence(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.list_evidence(db=db, session_id=id, current_user=current_user)


@router.get(
    "/survey-evidence/{id}/file",
    summary="Retrieve protected survey photo or evidence document",
)
async def get_survey_evidence_file(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_path, mime_type, filename = await survey_service.get_evidence_file_info(
        db=db,
        evidence_id=id,
        current_user=current_user,
    )
    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=filename,
    )


@router.post(
    "/survey-sessions/{id}/validate",
    response_model=SurveyValidationSummary,
    summary="Run deterministic validation engine and comparison against official cadastre",
)
async def validate_survey_session(
    id: uuid.UUID,
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.validate_session(db=db, session_id=id, current_user=current_user)


@router.post(
    "/survey-sessions/{id}/submit",
    response_model=SurveySubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Freeze snapshot, increment submission version, and submit survey for review (Surveyor)",
)
async def submit_survey_session(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.submit_survey(
        db=db,
        session_id=id,
        current_user=current_user,
        request=request,
    )


# ============================================================================
# Officer Review & Submissions
# ============================================================================

@router.get(
    "/survey-submissions",
    response_model=PaginatedResponse[SurveySubmissionResponse],
    summary="List survey submissions for officer review queue (Government Officer / Admin)",
)
async def list_survey_submissions(
    assignment_id: Optional[uuid.UUID] = Query(default=None, description="Filter by assignment"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await survey_service.list_submissions(
        db=db,
        current_user=current_user,
        assignment_id=assignment_id,
        status=status_filter,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[SurveySubmissionResponse](
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get(
    "/survey-submissions/{id}",
    response_model=SurveySubmissionResponse,
    summary="Retrieve survey submission details and frozen snapshot",
)
async def get_survey_submission(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.get_submission(db=db, submission_id=id, current_user=current_user)


@router.post(
    "/survey-submissions/{id}/approve",
    response_model=SurveySubmissionResponse,
    summary="Approve survey submission (Government Officer / Admin)",
)
async def approve_survey_submission(
    id: uuid.UUID,
    body: Optional[SurveySubmissionReviewRequest] = None,
    request: Request = None,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    notes = body.review_notes if body else None
    return await survey_service.review_submission(
        db=db,
        submission_id=id,
        action="approve",
        review_notes=notes,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/survey-submissions/{id}/request-revision",
    response_model=SurveySubmissionResponse,
    summary="Request survey revision with mandatory feedback notes (Government Officer / Admin)",
)
async def request_survey_revision(
    id: uuid.UUID,
    body: SurveySubmissionReviewRequest,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.review_submission(
        db=db,
        submission_id=id,
        action="request-revision",
        review_notes=body.review_notes,
        current_user=current_user,
        request=request,
    )


@router.post(
    "/survey-submissions/{id}/reject",
    response_model=SurveySubmissionResponse,
    summary="Reject survey submission with mandatory justification notes (Government Officer / Admin)",
)
async def reject_survey_submission(
    id: uuid.UUID,
    body: SurveySubmissionReviewRequest,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_service.review_submission(
        db=db,
        submission_id=id,
        action="reject",
        review_notes=body.review_notes,
        current_user=current_user,
        request=request,
    )


# ============================================================================
# Offline Batch Synchronization
# ============================================================================

@router.post(
    "/sync/batch",
    response_model=SyncOperationBatchResponse,
    summary="Batch synchronize offline field survey mutations with idempotency and conflict detection",
)
async def sync_batch_operations(
    batch: SyncOperationBatchRequest,
    current_user: User = Depends(require_surveyor_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await survey_sync_service.process_batch(
        db=db,
        batch_request=batch,
        surveyor_id=current_user.id,
    )


@router.get(
    "/sync/status",
    summary="Get offline sync system status",
)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
):
    return {
        "status": "ready",
        "supported_operations": [
            "CREATE_OBSERVATION",
            "UPDATE_OBSERVATION",
            "UPDATE_SESSION",
        ],
        "idempotency_enabled": True,
        "max_batch_size": 100,
    }
