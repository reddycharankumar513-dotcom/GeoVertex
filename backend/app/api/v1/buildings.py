import math
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_editor, require_officer_or_admin
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.building import (
    BuildingCreate,
    BuildingDetailResponse,
    BuildingResponse,
    BuildingUpdate,
)
from app.schemas.common import PaginatedResponse
from app.schemas.floor import FloorDetailResponse
from app.services.building_service import building_service
from app.services.floor_service import floor_service

router = APIRouter(prefix="/buildings", tags=["Building Footprint Management"])


@router.get(
    "",
    response_model=PaginatedResponse[BuildingResponse],
    summary="List or search building footprints",
)
async def list_buildings(
    parcel_id: Optional[uuid.UUID] = Query(default=None, description="Filter by parcel"),
    building_type: Optional[str] = Query(default=None, description="Filter by building type"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status"),
    query: Optional[str] = Query(default=None, description="Search by building reference"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await building_service.list_buildings(
        db=db,
        parcel_id=parcel_id,
        building_type=building_type,
        status=status_filter,
        query=query,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[BuildingResponse](
        items=[BuildingResponse.model_validate(b) for b in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=BuildingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a building footprint with geometry validation (Authorized editor)",
)
async def create_building(
    data: BuildingCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    created = await building_service.create_building(
        db=db,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return BuildingResponse.model_validate(created)


@router.get(
    "/{id}",
    response_model=BuildingDetailResponse,
    summary="Retrieve building footprint details",
)
async def get_building(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bld = await building_service.get_building(db, id)
    res = BuildingDetailResponse.model_validate(bld)
    if bld.parcel:
        res.parcel_number = bld.parcel.parcel_number
        res.parcel_code = bld.parcel.parcel_code
    return res


@router.patch(
    "/{id}",
    response_model=BuildingResponse,
    summary="Update building footprint (Admin / Officer)",
)
async def update_building(
    id: uuid.UUID,
    data: BuildingUpdate,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    updated = await building_service.update_building(
        db=db,
        id=id,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return BuildingResponse.model_validate(updated)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete building footprint (Admin / Officer)",
)
async def delete_building(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await building_service.delete_building(
        db=db,
        id=id,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {"message": "Building footprint deleted successfully", "id": str(id)}


@router.get(
    "/{id}/floors",
    response_model=List[FloorDetailResponse],
    summary="Get all floor slabs for a building footprint",
)
async def get_building_floor_stack(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await floor_service.get_building_floors(db=db, building_id=id)

