import math
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_admin
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.organization import OrganizationCreate, OrganizationResponse
from app.services.organization_service import organization_service

router = APIRouter(prefix="/organizations", tags=["Organization Management"])


@router.get(
    "",
    response_model=PaginatedResponse[OrganizationResponse],
    summary="List registered cadastral and municipal organizations",
)
async def list_organizations(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await organization_service.list_organizations(db=db, skip=skip, limit=size)
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[OrganizationResponse](
        items=[OrganizationResponse.model_validate(o) for o in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new cadastral organization (Admin only)",
)
async def create_organization(
    data: OrganizationCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    org = await organization_service.create_organization(
        db=db,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return org
