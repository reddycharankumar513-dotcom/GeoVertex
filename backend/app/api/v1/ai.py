import math
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from shapely import wkt
from shapely.geometry import mapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas.ai_schemas import (
    AIDatasetResponse,
    AIEvaluationRunRequest,
    AIEvaluationRunResponse,
    AIJobCreateRequest,
    AIJobListResponse,
    AIJobResponse,
    AIModelResponse,
    AIReviewDecisionRequest,
    BuildingResultResponse,
    FloorResultResponse,
)
from app.dependencies.auth import (
    get_current_user,
    require_admin,
    require_officer_or_admin,
    require_surveyor_or_admin,
    require_editor,
)
from app.dependencies.db import get_db
from app.models.user import User
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI Building & Floor Extraction Pipeline"])


# -------------------------------------------------------------
# AI Jobs
# -------------------------------------------------------------

@router.post(
    "/jobs",
    response_model=AIJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue a new AI extraction job (Surveyor, Officer, Admin)",
)
async def create_ai_job(
    data: AIJobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    job = await ai_service.create_job(
        db=db,
        data=data,
        current_user=current_user,
        background_tasks=background_tasks,
    )
    return job


@router.get(
    "/jobs",
    response_model=AIJobListResponse,
    summary="List AI processing jobs with filtering and pagination",
)
async def list_ai_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    job_type: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await ai_service.list_jobs(
        db=db,
        status=status_filter,
        job_type=job_type,
        target_type=target_type,
        target_id=target_id,
        skip=skip,
        limit=size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get(
    "/jobs/{job_id}",
    response_model=AIJobResponse,
    summary="Get details and stage progress for an AI job",
)
async def get_ai_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.get_job(db, job_id)


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=AIJobResponse,
    summary="Cancel an active AI processing job",
)
async def cancel_ai_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.cancel_job(db, job_id, current_user)


# -------------------------------------------------------------
# Candidate Extraction Results
# -------------------------------------------------------------

def _format_building_result(r) -> Dict[str, Any]:
    geo_json = None
    if r.geometry_wkt:
        try:
            poly = wkt.loads(r.geometry_wkt)
            geo_json = mapping(poly)
        except Exception:
            pass

    return {
        "id": r.id,
        "job_id": r.job_id,
        "source_target_id": r.source_target_id,
        "geometry_wkt": r.geometry_wkt,
        "geometry_geojson": geo_json,
        "raw_geometry_wkt": r.raw_geometry_wkt,
        "estimated_height": r.estimated_height,
        "confidence": r.confidence,
        "confidence_components": r.confidence_components,
        "cadastral_comparison": r.cadastral_comparison,
        "evidence_linkage": r.evidence_linkage,
        "model_id": r.model_id,
        "model_version": r.model_version,
        "status": r.status,
        "validation_status": r.validation_status,
        "validation_details": r.validation_details,
        "review_id": r.review_id,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


@router.get(
    "/building-results",
    summary="List candidate building footprint results",
)
async def list_building_results(
    target_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    model_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await ai_service.list_building_results(
        db=db,
        target_id=target_id,
        status=status_filter,
        model_id=model_id,
        skip=skip,
        limit=size,
    )
    formatted = [_format_building_result(r) for r in items]
    return {
        "items": formatted,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get(
    "/building-results/{result_id}",
    summary="Get candidate building footprint result by ID",
)
async def get_building_result(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await ai_service.get_building_result(db, result_id)
    return _format_building_result(res)


@router.get(
    "/floor-results",
    response_model=List[FloorResultResponse],
    summary="List candidate floor extraction results",
)
async def list_floor_results(
    building_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, _ = await ai_service.list_floor_results(db=db, building_id=building_id, status=status_filter)
    res = []
    for f in items:
        geo_json = None
        if f.geometry_wkt:
            try:
                poly = wkt.loads(f.geometry_wkt)
                geo_json = mapping(poly)
            except Exception:
                pass
        res.append({
            "id": f.id,
            "job_id": f.job_id,
            "building_id": f.building_id,
            "candidate_floor_number": f.candidate_floor_number,
            "floor_label": f.floor_label,
            "base_elevation": f.base_elevation,
            "top_elevation": f.top_elevation,
            "height": f.height,
            "geometry_wkt": f.geometry_wkt,
            "geometry_geojson": geo_json,
            "confidence": f.confidence,
            "source": f.source,
            "status": f.status,
            "validation_details": f.validation_details,
            "review_id": f.review_id,
            "created_at": f.created_at,
            "updated_at": f.updated_at,
        })
    return res


# -------------------------------------------------------------
# Validation & Human Review
# -------------------------------------------------------------

@router.post(
    "/results/{result_id}/validate",
    summary="Trigger deterministic PostGIS geometry validation on candidate result",
)
async def validate_candidate_result(
    result_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.validate_candidate_result(db, result_id, current_user)


@router.post(
    "/results/{result_id}/approve",
    summary="Approve candidate geometry and trigger controlled cadastral update (Officer / Admin)",
)
async def approve_candidate_result(
    result_id: uuid.UUID,
    notes: Optional[str] = Query(None),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    data = AIReviewDecisionRequest(action="APPROVE", notes=notes)
    return await ai_service.review_result(db, result_id, data, current_user)


@router.post(
    "/results/{result_id}/reject",
    summary="Reject candidate geometry with mandatory justification (Officer / Admin)",
)
async def reject_candidate_result(
    result_id: uuid.UUID,
    notes: str = Query(..., description="Mandatory rejection rationale"),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    data = AIReviewDecisionRequest(action="REJECT", notes=notes)
    return await ai_service.review_result(db, result_id, data, current_user)


@router.post(
    "/results/{result_id}/request-reprocessing",
    summary="Request worker to re-run extraction pipeline with notes (Officer / Admin)",
)
async def request_reprocessing(
    result_id: uuid.UUID,
    notes: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    data = AIReviewDecisionRequest(action="REQUEST_REPROCESSING", notes=notes)
    return await ai_service.review_result(db, result_id, data, current_user, background_tasks)


@router.post(
    "/results/{result_id}/modify",
    summary="Modify candidate geometry vertices and approve controlled update (Officer / Admin)",
)
async def modify_and_approve_result(
    result_id: uuid.UUID,
    data: AIReviewDecisionRequest,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    data.action = "MODIFY_AND_APPROVE"
    return await ai_service.review_result(db, result_id, data, current_user)


# -------------------------------------------------------------
# Model Registry & Evaluation Endpoints
# -------------------------------------------------------------

@router.get(
    "/models",
    response_model=List[AIModelResponse],
    summary="List all registered AI/ML models and versions",
)
async def list_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.list_registered_models(db)


@router.get(
    "/datasets",
    response_model=List[AIDatasetResponse],
    summary="List evaluation benchmarks and sample datasets",
)
async def list_datasets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.list_datasets(db)


@router.post(
    "/evaluations/run",
    response_model=AIEvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute evaluation experiment run against labeled benchmark dataset",
)
async def run_evaluation(
    data: AIEvaluationRunRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.execute_evaluation_run(
        db=db,
        dataset_id=data.dataset_id,
        model_id=data.model_id,
        model_version=data.model_version,
        current_user=current_user,
        notes=data.notes,
    )
