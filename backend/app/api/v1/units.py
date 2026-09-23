import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_editor
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.unit import UnitCreate, UnitDetailResponse, UnitResponse, UnitUpdate
from app.services.unit_service import unit_service

router = APIRouter(prefix="/units", tags=["Property Units & Vertical Spaces"])


@router.get(
    "",
    response_model=List[UnitDetailResponse],
    summary="List property units with optional filtering",
)
async def list_units(
    floor_id: Optional[uuid.UUID] = Query(default=None, description="Filter by parent floor ID"),
    building_id: Optional[uuid.UUID] = Query(default=None, description="Filter by parent building ID"),
    property_id: Optional[uuid.UUID] = Query(default=None, description="Filter by linked legal property ID"),
    unit_type: Optional[str] = Query(default=None, description="Filter by unit type"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    units, _ = await unit_service.list_units(
        db=db,
        floor_id=floor_id,
        building_id=building_id,
        property_id=property_id,
        unit_type=unit_type,
        status=status,
        skip=skip,
        limit=limit,
    )
    return units


@router.get(
    "/{id}",
    response_model=UnitDetailResponse,
    summary="Get detailed unit information by ID",
)
async def get_unit(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await unit_service.get_unit(db=db, id=id)


@router.get(
    "/by-floor/{floor_id}",
    response_model=List[UnitDetailResponse],
    summary="Get all property units belonging to a specific floor slab",
)
async def get_floor_units(
    floor_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await unit_service.get_floor_units(db=db, floor_id=floor_id)


@router.post(
    "",
    response_model=UnitDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new property unit within a floor slab (Editor role required)",
)
async def create_unit(
    data: UnitCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    return await unit_service.create_unit(
        db=db,
        data=data,
        current_user=current_user,
        request=request,
    )


@router.put(
    "/{id}",
    response_model=UnitDetailResponse,
    summary="Update property unit attributes or boundary (Editor role required)",
)
async def update_unit(
    id: uuid.UUID,
    data: UnitUpdate,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    return await unit_service.update_unit(
        db=db,
        id=id,
        data=data,
        current_user=current_user,
        request=request,
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete property unit (Editor role required)",
)
async def delete_unit(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    await unit_service.delete_unit(
        db=db,
        id=id,
        current_user=current_user,
        request=request,
    )
