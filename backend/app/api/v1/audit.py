import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import require_admin
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.audit import AuditEventResponse
from app.schemas.common import PaginatedResponse
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Security & Compliance Audit"])


@router.get(
    "",
    response_model=PaginatedResponse[AuditEventResponse],
    summary="Query audit log trail (Admin only)",
)
async def list_audit_events(
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type (e.g. USER)"),
    action: Optional[str] = Query(default=None, description="Filter by action name (e.g. LOGIN_SUCCESS)"),
    actor_user_id: Optional[uuid.UUID] = Query(default=None, description="Filter by actor ID"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await audit_service.list_events(
        db=db,
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
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
