import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from shapely import wkt
from shapely.geometry import mapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundException
from app.dependencies.auth import (
    get_current_user,
    require_editor,
    require_officer_or_admin,
    require_admin,
)
from app.dependencies.db import get_db
from app.models.user import User
from app.models.validation import ValidationIssue, ValidationRun
from app.schemas.validation import (
    EntityValidationSummaryResponse,
    ValidationIssueActionRequest,
    ValidationIssueResponse,
    ValidationRuleResponse,
    ValidationRunCreateRequest,
    ValidationRunResponse,
)
from app.services.validation_service import validation_service

router = APIRouter(prefix="/validation", tags=["Topology Validation & Spatial Consistency"])


def _format_issue(issue: ValidationIssue) -> Dict[str, Any]:
    geo_json = None
    if issue.geometry_wkt:
        try:
            geom = wkt.loads(issue.geometry_wkt)
            geo_json = mapping(geom)
        except Exception:
            pass
    return {
        "id": issue.id,
        "validation_run_id": issue.validation_run_id,
        "rule_id": issue.rule_id,
        "rule_version": issue.rule_version,
        "issue_code": issue.issue_code,
        "category": issue.category,
        "severity": issue.severity,
        "status": issue.status,
        "entity_type": issue.entity_type,
        "entity_id": issue.entity_id,
        "related_entity_type": issue.related_entity_type,
        "related_entity_id": issue.related_entity_id,
        "message": issue.message,
        "technical_explanation": issue.technical_explanation,
        "geometry_wkt": issue.geometry_wkt,
        "geometry_geojson": geo_json,
        "measured_value": issue.measured_value,
        "expected_value": issue.expected_value,
        "tolerance": issue.tolerance,
        "metadata_json": issue.metadata_json or {},
        "created_at": issue.created_at,
        "acknowledged_at": issue.acknowledged_at,
        "acknowledged_by": issue.acknowledged_by,
        "resolved_at": issue.resolved_at,
        "resolved_by": issue.resolved_by,
        "resolution_note": issue.resolution_note,
        "waived_at": issue.waived_at,
        "waived_by": issue.waived_by,
        "waiver_reason": issue.waiver_reason,
    }


# -------------------------------------------------------------
# Validation Runs
# -------------------------------------------------------------

@router.post(
    "/runs",
    response_model=ValidationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue a new topology validation run (Surveyor, Officer, Admin)",
)
async def create_validation_run(
    request: ValidationRunCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    return await validation_service.dispatch_validation_run(
        db=db,
        request=request,
        current_user=current_user,
        background_tasks=background_tasks,
    )


@router.get(
    "/runs",
    response_model=List[ValidationRunResponse],
    summary="List validation runs with status and scope filters",
)
async def list_validation_runs(
    status_filter: Optional[str] = Query(None, alias="status"),
    validation_type: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    runs, _ = await validation_service.list_runs(
        db=db,
        status=status_filter,
        validation_type=validation_type,
        target_type=target_type,
        target_id=target_id,
        skip=skip,
        limit=limit,
    )
    return runs


@router.get(
    "/runs/{run_id}",
    response_model=ValidationRunResponse,
    summary="Get details, stage, and summary of a validation run",
)
async def get_validation_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await validation_service.get_run(db, run_id)


@router.get(
    "/runs/{run_id}/issues",
    response_model=List[ValidationIssueResponse],
    summary="List all issues discovered by a specific validation run",
)
async def get_run_issues(
    run_id: uuid.UUID,
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issues, _ = await validation_service.list_issues(
        db=db,
        run_id=run_id,
        severity=severity,
        status=status_filter,
        category=category,
        skip=skip,
        limit=limit,
    )
    return [_format_issue(i) for i in issues]


@router.post(
    "/runs/{run_id}/cancel",
    response_model=ValidationRunResponse,
    summary="Cancel a queued or running validation run",
)
async def cancel_validation_run(
    run_id: uuid.UUID,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    return await validation_service.cancel_run(db, run_id, current_user)


# -------------------------------------------------------------
# Validation Issues & Review Actions
# -------------------------------------------------------------

@router.get(
    "/issues",
    response_model=List[ValidationIssueResponse],
    summary="Query cadastral validation issues with multi-dimensional filters",
)
async def list_validation_issues(
    run_id: Optional[uuid.UUID] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issues, _ = await validation_service.list_issues(
        db=db,
        run_id=run_id,
        severity=severity,
        status=status_filter,
        category=category,
        rule_id=rule_id,
        entity_type=entity_type,
        entity_id=entity_id,
        skip=skip,
        limit=limit,
    )
    return [_format_issue(i) for i in issues]


@router.get(
    "/issues/{issue_id}",
    response_model=ValidationIssueResponse,
    summary="Get single validation issue by ID with geometry and metrics",
)
async def get_validation_issue(
    issue_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issue = await validation_service.get_issue(db, issue_id)
    return _format_issue(issue)


@router.patch(
    "/issues/{issue_id}",
    response_model=ValidationIssueResponse,
    summary="Execute human review decision on an issue (Acknowledge, Resolve, Waive)",
)
async def review_validation_issue(
    issue_id: uuid.UUID,
    request: ValidationIssueActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    issue = await validation_service.review_issue(db, issue_id, request, current_user)
    return _format_issue(issue)


# -------------------------------------------------------------
# Entity-Level Targeted Validation & Aggregations
# -------------------------------------------------------------

@router.post(
    "/entities/{entity_type}/{entity_id}",
    response_model=ValidationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger immediate targeted topology validation on a specific entity",
)
async def validate_entity(
    entity_type: str,
    entity_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    req = ValidationRunCreateRequest(
        target_type=entity_type.upper(),
        target_id=entity_id,
        validation_type="SINGLE_ENTITY",
    )
    return await validation_service.dispatch_validation_run(
        db=db,
        request=req,
        current_user=current_user,
        background_tasks=background_tasks,
    )


@router.get(
    "/entities/{entity_type}/{entity_id}/summary",
    response_model=EntityValidationSummaryResponse,
    summary="Get aggregated topology validation health summary for an entity",
)
async def get_entity_validation_summary(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await validation_service.get_entity_validation_summary(db, entity_type, entity_id)


# -------------------------------------------------------------
# Rule Catalogue & Metadata
# -------------------------------------------------------------

@router.get(
    "/rules",
    response_model=List[ValidationRuleResponse],
    summary="List all registered deterministic validation rules",
)
async def list_rules(
    category: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    return validation_service.list_rules(category=category, target_type=target_type)


@router.get(
    "/rules/{rule_id}",
    response_model=ValidationRuleResponse,
    summary="Get specification and technical details of a validation rule",
)
async def get_rule_detail(
    rule_id: str,
    current_user: User = Depends(get_current_user),
):
    rule = validation_service.get_rule(rule_id)
    if not rule:
        raise NotFoundException(f"Rule with ID '{rule_id}' not found in registry.")
    return rule
