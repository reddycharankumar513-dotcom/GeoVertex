import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_admin, require_officer_or_admin
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserRoleUpdate, UserStatusUpdate
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["User Administration"])


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List users with filtering (Admin & Officer access)",
)
async def list_users(
    role: Optional[UserRole] = Query(default=None, description="Filter by role"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    role_str = role.value if role else None
    items, total = await user_service.list_users(
        db=db,
        role=role_str,
        is_active=is_active,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[UserResponse](
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a new user account (Admin only)",
)
async def create_user(
    data: UserCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    user = await user_service.create_user(
        db=db,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user details by ID (Admin & Officer access)",
)
async def get_user_by_id(
    user_id: uuid.UUID,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user_by_id(db, user_id)
    return user


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Change user role assignment (Admin only)",
)
async def update_user_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    updated = await user_service.update_role(
        db=db,
        user_id=user_id,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return updated


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Activate or deactivate a user account (Admin only)",
)
async def update_user_status(
    user_id: uuid.UUID,
    data: UserStatusUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    updated = await user_service.update_status(
        db=db,
        user_id=user_id,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return updated
