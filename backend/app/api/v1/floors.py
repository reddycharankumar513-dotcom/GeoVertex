import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_editor
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.floor import FloorCreate, FloorDetailResponse, FloorResponse, FloorUpdate
from app.services.floor_service import floor_service

router = APIRouter(prefix="/floors", tags=["Floors & Vertical Slabs"])


@router.get(
    "",
    response_model=List[FloorDetailResponse],
    summary="List building floors with optional filtering",
)
async def list_floors(
    building_id: Optional[uuid.UUID] = Query(default=None, description="Filter by parent building ID"),
    floor_type: Optional[str] = Query(default=None, description="Filter by floor type"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    floors, _ = await floor_service.list_floors(
        db=db,
        building_id=building_id,
        floor_type=floor_type,
        status=status,
        skip=skip,
        limit=limit,
    )
    return floors


@router.get(
    "/{id}",
    response_model=FloorDetailResponse,
    summary="Get detailed floor slab information by ID",
)
async def get_floor(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await floor_service.get_floor(db=db, id=id)


@router.get(
    "/by-building/{building_id}",
    response_model=List[FloorDetailResponse],
    summary="Get all floor slabs for a specific building ordered by floor number",
)
async def get_building_floors(
    building_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await floor_service.get_building_floors(db=db, building_id=building_id)


@router.post(
    "",
    response_model=FloorDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new floor slab (Editor role required)",
)
async def create_floor(
    data: FloorCreate,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    return await floor_service.create_floor(
        db=db,
        data=data,
        current_user=current_user,
        request=request,
    )


@router.put(
    "/{id}",
    response_model=FloorDetailResponse,
    summary="Update floor attributes and vertical bounds (Editor role required)",
)
async def update_floor(
    id: uuid.UUID,
    data: FloorUpdate,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    return await floor_service.update_floor(
        db=db,
        id=id,
        data=data,
        current_user=current_user,
        request=request,
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete floor and its contained units (Editor role required)",
)
async def delete_floor(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    await floor_service.delete_floor(
        db=db,
        id=id,
        current_user=current_user,
        request=request,
    )
