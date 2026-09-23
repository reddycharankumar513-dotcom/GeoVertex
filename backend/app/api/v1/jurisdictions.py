import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_admin
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.jurisdiction import JurisdictionCreate, JurisdictionResponse, JurisdictionUpdate
from app.services.organization_service import organization_service

router = APIRouter(prefix="/jurisdictions", tags=["Jurisdiction Management"])


@router.get(
    "",
    response_model=PaginatedResponse[JurisdictionResponse],
    summary="List administrative jurisdictions (wards, districts)",
)
async def list_jurisdictions(
    organization_id: Optional[uuid.UUID] = Query(default=None, description="Filter by parent organization"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await organization_service.list_jurisdictions(
        db=db,
        organization_id=organization_id,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[JurisdictionResponse](
        items=[JurisdictionResponse.model_validate(j) for j in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=JurisdictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an administrative jurisdiction with native SRID (Admin only)",
)
async def create_jurisdiction(
    data: JurisdictionCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    jur = await organization_service.create_jurisdiction(
        db=db,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return jur


@router.get(
    "/{id}",
    response_model=JurisdictionResponse,
    summary="Retrieve an administrative jurisdiction by ID",
)
async def get_jurisdiction(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    jur = await organization_service.get_jurisdiction(db, id)
    return JurisdictionResponse.model_validate(jur)


@router.patch(
    "/{id}",
    response_model=JurisdictionResponse,
    summary="Update jurisdiction details or boundary (Admin only)",
)
async def update_jurisdiction(
    id: uuid.UUID,
    data: JurisdictionUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    updated = await organization_service.update_jurisdiction(
        db=db,
        id=id,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return JurisdictionResponse.model_validate(updated)

