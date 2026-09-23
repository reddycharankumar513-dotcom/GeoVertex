import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_editor, require_officer_or_admin
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.parcel import (
    ParcelCreate,
    ParcelDetailResponse,
    ParcelResponse,
    ParcelUpdate,
    PropertySummary,
    BuildingSummary,
)
from app.services.parcel_service import parcel_service

router = APIRouter(prefix="/parcels", tags=["Parcel Management"])


@router.get(
    "",
    response_model=PaginatedResponse[ParcelResponse],
    summary="List or search cadastral parcels",
)
async def list_parcels(
    jurisdiction_id: Optional[uuid.UUID] = Query(default=None, description="Filter by jurisdiction"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (ACTIVE, DRAFT, etc.)"),
    land_use: Optional[str] = Query(default=None, description="Filter by land use classification"),
    query: Optional[str] = Query(default=None, description="Search query by parcel number, code, or survey number"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await parcel_service.search_parcels(
        db=db,
        jurisdiction_id=jurisdiction_id,
        status=status_filter,
        land_use=land_use,
        query=query,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[ParcelResponse](
        items=[ParcelResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=ParcelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new parcel with geometry validation (Authorized editor)",
)
async def create_parcel(
    data: ParcelCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    created = await parcel_service.create_parcel(
        db=db,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return ParcelResponse.model_validate(created)


@router.get(
    "/{id}",
    response_model=ParcelDetailResponse,
    summary="Retrieve detailed parcel record with related properties and buildings",
)
async def get_parcel(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parcel = await parcel_service.get_parcel(db, id)
    res = ParcelDetailResponse.model_validate(parcel)
    if parcel.jurisdiction:
        res.jurisdiction_name = parcel.jurisdiction.name
        res.jurisdiction_code = parcel.jurisdiction.code
    res.properties = [PropertySummary.model_validate(p) for p in parcel.properties]
    res.buildings = [BuildingSummary.model_validate(b) for b in parcel.buildings]
    return res


@router.patch(
    "/{id}",
    response_model=ParcelResponse,
    summary="Update parcel attributes or geometry (Admin / Officer)",
)
async def update_parcel(
    id: uuid.UUID,
    data: ParcelUpdate,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    updated = await parcel_service.update_parcel(
        db=db,
        id=id,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return ParcelResponse.model_validate(updated)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a parcel (Admin / Officer)",
)
async def delete_parcel(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await parcel_service.delete_parcel(
        db=db,
        id=id,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {"message": "Parcel deleted successfully", "id": str(id)}
