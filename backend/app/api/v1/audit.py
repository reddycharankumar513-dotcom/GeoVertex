"""Phase 13 — Audit Trail API.

Provides search, drill-down, statistics, and compliance export for immutable audit records.
Access restricted to authorized officers and administrators.
"""

import csv
import io
import json
import math
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenException, NotFoundException
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.repositories.audit_repository import audit_repository
from app.schemas.common import PaginatedResponse
from app.schemas.governance import AuditEventResponse, AuditStatisticsResponse

router = APIRouter(prefix="/audit", tags=["Security & Compliance Audit"])


def require_officer_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER]:
        raise ForbiddenException("Access to audit records requires Government Officer or Admin role.")
    return current_user


@router.get(
    "/statistics",
    response_model=AuditStatisticsResponse,
    summary="Get aggregated audit statistics",
)
async def get_audit_statistics(
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    stats = await audit_repository.get_statistics(db)
    return AuditStatisticsResponse(**stats)


@router.get(
    "/export",
    summary="Export audit log records to CSV or JSON",
)
async def export_audit_events(
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    entity_type: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    limit: int = Query(default=1000, le=5000),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    events, _ = await audit_repository.get_events_filtered(
        db=db,
        entity_type=entity_type,
        action=action,
        category=category,
        severity=severity,
        skip=0,
        limit=limit,
    )

    # Log the export event
    await audit_repository.log_event(
        db=db,
        action="AUDIT_EXPORT_CREATED",
        category="GOVERNANCE",
        severity="INFO",
        entity_type="AUDIT_EXPORT",
        entity_id=str(uuid.uuid4()),
        actor_user_id=current_user.id,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        details={"format": format, "count": len(events)},
    )

    if format == "json":
        data = [AuditEventResponse.model_validate(e).model_dump(mode="json") for e in events]
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=geovertex_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"},
        )

    # CSV output
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Timestamp", "Category", "Action", "Severity", "Result",
        "EntityType", "EntityID", "ActorUserID", "ActorRole", "SourceType",
        "WorkflowID", "CorrelationID", "Reason"
    ])
    for e in events:
        writer.writerow([
            str(e.id),
            e.timestamp.isoformat() if e.timestamp else "",
            e.category,
            e.action,
            e.severity,
            e.result,
            e.entity_type,
            e.entity_id,
            str(e.actor_user_id) if e.actor_user_id else "SYSTEM",
            e.actor_role or "",
            e.source_type or "",
            str(e.workflow_id) if e.workflow_id else "",
            e.correlation_id or "",
            e.reason or "",
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=geovertex_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"},
    )


@router.get(
    "/{id}",
    response_model=AuditEventResponse,
    summary="Get single audit event details",
)
async def get_audit_event(
    id: uuid.UUID,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    event = await audit_repository.get_by_id(db, id)
    if not event:
        raise NotFoundException(f"Audit event {id} not found.")
    return AuditEventResponse.model_validate(event)


@router.get(
    "",
    response_model=PaginatedResponse[AuditEventResponse],
    summary="Query audit log trail with multi-criteria filters",
)
async def list_audit_events(
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type (e.g. PARCEL, USER)"),
    entity_id: Optional[str] = Query(default=None, description="Filter by entity ID"),
    action: Optional[str] = Query(default=None, description="Filter by action name"),
    category: Optional[str] = Query(default=None, description="Filter by audit category (e.g. PROPERTY, GIS, SURVEY)"),
    actor_user_id: Optional[uuid.UUID] = Query(default=None, description="Filter by actor ID"),
    source_type: Optional[str] = Query(default=None, description="Filter by source type"),
    workflow_id: Optional[uuid.UUID] = Query(default=None, description="Filter by workflow ID"),
    correlation_id: Optional[str] = Query(default=None, description="Filter by correlation ID"),
    case_id: Optional[str] = Query(default=None, description="Filter by case ID"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (INFO, WARNING, ERROR, CRITICAL)"),
    result: Optional[str] = Query(default=None, description="Filter by result (SUCCESS, FAILURE)"),
    date_from: Optional[datetime] = Query(default=None, description="Start date (ISO)"),
    date_to: Optional[datetime] = Query(default=None, description="End date (ISO)"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await audit_repository.get_events_filtered(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        category=category,
        actor_user_id=actor_user_id,
        source_type=source_type,
        workflow_id=workflow_id,
        correlation_id=correlation_id,
        case_id=case_id,
        severity=severity,
        result=result,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[AuditEventResponse](
        items=[AuditEventResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )
