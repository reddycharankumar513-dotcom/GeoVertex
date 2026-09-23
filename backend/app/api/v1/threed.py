import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundException
from app.dependencies.auth import get_current_user, require_editor
from app.dependencies.db import get_db
from app.models.user import User
from app.repositories.threed_repository import threed_repository
from app.schemas.threed import (
    Building3DHeightUpdateRequest,
    Building3DRepresentationResponse,
    ThreeDAssetCreateRequest,
    ThreeDAssetResponse,
    ThreeDIdentifyResponse,
    ThreeDSceneResponse,
)
from app.services.building_3d_service import building_3d_service

router = APIRouter(prefix="/3d", tags=["3D Digital Twin & Vertical GIS"])


@router.get(
    "/scene",
    response_model=ThreeDSceneResponse,
    summary="Get CesiumJS-ready 3D scene with extruded buildings and cadastral ground layers",
)
async def get_3d_scene(
    bbox: Optional[str] = Query(
        default=None,
        description="Bounding box 'minLon,minLat,maxLon,maxLat'",
    ),
    jurisdiction_id: Optional[uuid.UUID] = Query(
        default=None,
        description="Filter scene elements to a specific administrative jurisdiction",
    ),
    limit: int = Query(default=150, ge=1, le=500, description="Max building footprints to include"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve lightweight, CesiumJS-ready 3D digital twin payload.
    Buildings are extruded based on authoritative PostGIS heights or synthesized estimates.
    Parcels are returned as 2D ground wireframes.
    """
    return await building_3d_service.get_scene_data(
        db=db,
        bbox_str=bbox,
        jurisdiction_id=jurisdiction_id,
        limit=limit,
    )


@router.get(
    "/buildings/{id}",
    response_model=Dict[str, Any],
    summary="Get 3D representation and cadastral context for a building footprint",
)
async def get_building_3d(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch authoritative 3D representation, height datum, linked parcel,
    and associated property records for a single building.
    """
    return await building_3d_service.get_building_3d(db=db, building_id=id)


@router.patch(
    "/buildings/{id}/height",
    response_model=Building3DRepresentationResponse,
    summary="Update building vertical height and elevation (Editor or Admin)",
)
async def update_building_height(
    id: uuid.UUID,
    payload: Building3DHeightUpdateRequest,
    request: Request,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    """Update building height and base elevation with geometric validation
    and an immutable audit log trail.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await building_3d_service.update_building_height(
        db=db,
        building_id=id,
        data=payload,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get(
    "/parcels/{id}",
    response_model=Dict[str, Any],
    summary="Get 3D digital twin context for a parcel and its buildings",
)
async def get_parcel_3d(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve parcel boundary, all contained 3D building extrusions,
    associated properties, and recommended 3D camera presets.
    """
    return await building_3d_service.get_parcel_3d_context(db=db, parcel_id=id)


@router.get(
    "/identify",
    response_model=ThreeDIdentifyResponse,
    summary="Point-in-polygon 3D identify query",
)
async def identify_3d(
    lon: float = Query(..., description="Longitude in EPSG:4326"),
    lat: float = Query(..., description="Latitude in EPSG:4326"),
    height: Optional[float] = Query(None, description="Optional clicked altitude in meters"),
    radius: float = Query(default=30.0, ge=1.0, le=200.0, description="Search tolerance radius in meters"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Identify the 3D building, cadastral parcel, and primary property
    at clicked geographic coordinates.
    """
    return await building_3d_service.identify_3d(
        db=db,
        longitude=lon,
        latitude=lat,
        height=height,
        radius_meters=radius,
    )


@router.get(
    "/assets",
    response_model=List[ThreeDAssetResponse],
    summary="List 3D model assets and extrusion payloads",
)
async def list_3d_assets(
    building_id: Optional[uuid.UUID] = Query(default=None),
    asset_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List registered 3D models, glTF/GLB assets, and extrusion packages."""
    skip = (page - 1) * size
    items, _ = await threed_repository.list_assets(
        db=db,
        building_id=building_id,
        asset_type=asset_type,
        status=status,
        skip=skip,
        limit=size,
    )
    return [ThreeDAssetResponse.model_validate(item) for item in items]


@router.post(
    "/assets",
    response_model=ThreeDAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new 3D model or extrusion asset (Editor or Admin)",
)
async def create_3d_asset(
    payload: ThreeDAssetCreateRequest,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    """Register a new 3D asset record tied to a building or representation."""
    asset = await threed_repository.create_asset(
        db=db,
        asset_type=payload.asset_type,
        storage_location=payload.storage_location,
        format=payload.format,
        building_id=payload.building_id,
        representation_id=payload.representation_id,
        source=payload.source,
        status=payload.status,
        metadata_json=payload.metadata_json,
        user_id=current_user.id,
    )
    return ThreeDAssetResponse.model_validate(asset)


@router.delete(
    "/assets/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a 3D asset (Editor or Admin)",
)
async def delete_3d_asset(
    id: uuid.UUID,
    current_user: User = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
):
    deleted = await threed_repository.delete_asset_by_id(db, id)
    if not deleted:
        raise NotFoundException(f"3D asset with ID '{id}' not found")
    return None
