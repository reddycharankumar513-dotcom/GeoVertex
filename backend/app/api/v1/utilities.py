"""REST API endpoints for underground infrastructure and subsurface utility intelligence."""

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundException, ForbiddenException
from app.dependencies.auth import get_current_user, require_role
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.schemas.utility import (
    ControlledOfficialUpdatePayload,
    Utility3DSceneResponse,
    UtilityAssetCreate,
    UtilityAssetResponse,
    UtilityAssetUpdate,
    UtilityClashResponse,
    UtilityClashReviewPayload,
    UtilityCorridorCreate,
    UtilityCorridorResponse,
    UtilityGeoJSONCollection,
    UtilityInspectionCreate,
    UtilityInspectionResponse,
    UtilityMaintenanceCreate,
    UtilityMaintenanceResponse,
    UtilityMetricsResponse,
    UtilityNetworkCreate,
    UtilityNetworkResponse,
    UtilityNetworkUpdate,
    UtilityNodeCreate,
    UtilityNodeResponse,
    UtilityReviewActionPayload,
    UtilitySegmentCreate,
    UtilitySegmentResponse,
    UtilitySeparationRuleCreate,
    UtilitySeparationRuleResponse,
    UtilityStructureCreate,
    UtilityStructureResponse,
)
from app.services.utility_service import UtilityService

router = APIRouter(prefix="/utilities", tags=["Underground Infrastructure & Subsurface Utility Intelligence"])
service = UtilityService()


# 1. Networks
@router.post("/networks", response_model=UtilityNetworkResponse, status_code=status.HTTP_201_CREATED)
async def create_network(
    payload: UtilityNetworkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.SURVEYOR)),
):
    """Creates a new utility network."""
    return await service.create_network(db, payload.model_dump(), actor_id=current_user.id)


@router.get("/networks", response_model=List[UtilityNetworkResponse])
async def list_networks(
    jurisdiction_id: Optional[uuid.UUID] = None,
    utility_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists utility networks with filtering."""
    return await service.list_networks(db, jurisdiction_id, utility_type, status_filter, skip, limit)


@router.get("/networks/{id}", response_model=UtilityNetworkResponse)
async def get_network(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a utility network by ID."""
    net = await service.get_network(db, id)
    if not net:
        raise NotFoundException("Utility network not found")
    return net


@router.get("/networks/{id}/topology")
async def get_network_topology(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Runs deterministic topological analysis and connectivity graph validation on a network."""
    return await service.get_network_topology(db, id)


# 2. Assets
@router.post("/assets", response_model=UtilityAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    payload: UtilityAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.SURVEYOR)),
):
    """Creates an underground utility asset (pipe, cable, duct, manhole, etc.)."""
    return await service.create_asset(db, payload.model_dump(), actor_id=current_user.id)


@router.get("/assets", response_model=List[UtilityAssetResponse])
async def list_assets(
    network_id: Optional[uuid.UUID] = None,
    asset_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    review_status: Optional[str] = None,
    parcel_id: Optional[uuid.UUID] = None,
    building_id: Optional[uuid.UUID] = None,
    min_depth: Optional[float] = None,
    max_depth: Optional[float] = None,
    confidence: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists underground utility assets with multi-criteria filtering."""
    return await service.repo.list_assets(
        db,
        network_id=network_id,
        asset_type=asset_type,
        status=status_filter,
        review_status=review_status,
        parcel_id=parcel_id,
        building_id=building_id,
        min_depth=min_depth,
        max_depth=max_depth,
        confidence=confidence,
        skip=skip,
        limit=limit,
    )


@router.get("/assets/{id}")
async def get_asset_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full details of a utility asset including spatial parcel/building relations and history."""
    details = await service.get_asset_details(db, id)
    if not details:
        raise NotFoundException("Utility asset not found")
    return details


@router.patch("/assets/{id}", response_model=UtilityAssetResponse)
async def update_asset(
    id: uuid.UUID,
    payload: UtilityAssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
):
    """Updates attributes of an existing utility asset."""
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = await service.update_asset(db, id, updates, actor_id=current_user.id)
    if not updated:
        raise NotFoundException("Utility asset not found")
    return updated


@router.post("/assets/{id}/verify", response_model=UtilityAssetResponse)
async def review_candidate(
    id: uuid.UUID,
    payload: UtilityReviewActionPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
):
    """Human cadastral officer review action to verify, reject, or request revision on a candidate utility."""
    reviewed = await service.review_candidate(
        db, id, action=payload.action, review_notes=payload.review_notes, actor_id=current_user.id
    )
    if not reviewed:
        raise NotFoundException("Utility asset not found")
    return reviewed


@router.post("/assets/{id}/controlled-update", response_model=UtilityAssetResponse)
async def controlled_official_update(
    id: uuid.UUID,
    payload: ControlledOfficialUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
):
    """Audited controlled update modifying official technical parameters with source and justification."""
    updated = await service.controlled_official_update(
        db,
        id,
        reason=payload.reason,
        source_reference=payload.source_reference,
        updates=payload.updates,
        actor_id=current_user.id,
    )
    if not updated:
        raise NotFoundException("Utility asset not found")
    return updated


# 3. Segments & Nodes
@router.post("/segments", response_model=UtilitySegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
    payload: UtilitySegmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.SURVEYOR)),
):
    """Creates a linear segment connecting two nodes for a utility asset."""
    return await service.repo.create_segment(db, payload.model_dump())


@router.post("/nodes", response_model=UtilityNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    payload: UtilityNodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.SURVEYOR)),
):
    """Creates a utility connection node (manhole, valve, junction, transformer)."""
    return await service.repo.create_node(db, payload.model_dump())


@router.get("/networks/{id}/nodes", response_model=List[UtilityNodeResponse])
async def list_network_nodes(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all nodes in a utility network."""
    return await service.repo.list_nodes_by_network(db, id)


@router.get("/networks/{id}/segments", response_model=List[UtilitySegmentResponse])
async def list_network_segments(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all segments in a utility network."""
    return await service.repo.list_segments_by_network(db, id)


# 4. Structures & Corridors
@router.post("/structures", response_model=UtilityStructureResponse, status_code=status.HTTP_201_CREATED)
async def create_structure(
    payload: UtilityStructureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.SURVEYOR)),
):
    """Creates an underground structure (vault, chamber, duct bank)."""
    return await service.repo.create_structure(db, payload.model_dump())


@router.post("/corridors", response_model=UtilityCorridorResponse, status_code=status.HTTP_201_CREATED)
async def create_corridor(
    payload: UtilityCorridorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
):
    """Creates a designated utility corridor."""
    return await service.repo.create_corridor(db, payload.model_dump())


@router.get("/corridors", response_model=List[UtilityCorridorResponse])
async def list_corridors(
    jurisdiction_id: Optional[uuid.UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists utility corridors."""
    return await service.repo.list_corridors(db, jurisdiction_id, skip, limit)


# 5. Separation Rules
@router.post("/rules/separation", response_model=UtilitySeparationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_separation_rule(
    payload: UtilitySeparationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Configures a municipal horizontal/vertical separation requirement between two utility types."""
    return await service.repo.create_separation_rule(db, payload.model_dump())


@router.get("/rules/separation", response_model=List[UtilitySeparationRuleResponse])
async def list_separation_rules(
    jurisdiction_id: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = Query("ACTIVE", alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists configured utility separation rules."""
    return await service.repo.list_separation_rules(db, jurisdiction_id, status_filter)


# 6. Clashes
@router.post("/clashes/detect", response_model=List[UtilityClashResponse])
async def run_clash_detection(
    jurisdiction_id: Optional[uuid.UUID] = None,
    network_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.SURVEYOR)),
):
    """Runs deterministic 3D clash detection across utility assets using configured separation rules."""
    return await service.run_clash_detection(db, jurisdiction_id, network_id, actor_id=current_user.id)


@router.get("/clashes", response_model=List[UtilityClashResponse])
async def list_clashes(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = None,
    asset_id: Optional[uuid.UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists 3D utility clashes with status and severity filters."""
    return await service.repo.list_clashes(db, status_filter, severity, asset_id, skip, limit)


@router.post("/clashes/{id}/review", response_model=UtilityClashResponse)
async def review_clash(
    id: uuid.UUID,
    payload: UtilityClashReviewPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
):
    """Reviews and resolves, acknowledges, or waives a detected 3D clash."""
    reviewed = await service.review_clash(
        db, id, action=payload.action, resolution_notes=payload.resolution_notes, actor_id=current_user.id
    )
    if not reviewed:
        raise NotFoundException("Utility clash not found")
    return reviewed


# 7. Inspections & Maintenance
@router.post("/assets/{id}/inspections", response_model=UtilityInspectionResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    id: uuid.UUID,
    payload: UtilityInspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.SURVEYOR)),
):
    """Records an on-site field inspection with depth measurement and condition rating."""
    data = payload.model_dump()
    data["utility_asset_id"] = id
    data["inspector_id"] = current_user.id
    return await service.repo.create_inspection(db, data)


@router.get("/assets/{id}/inspections", response_model=List[UtilityInspectionResponse])
async def list_inspections(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists historical field inspections for a utility asset."""
    return await service.repo.list_inspections_by_asset(db, id)


@router.post("/assets/{id}/maintenance", response_model=UtilityMaintenanceResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance_event(
    id: uuid.UUID,
    payload: UtilityMaintenanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
):
    """Logs a maintenance, repair, or replacement event for a utility asset."""
    data = payload.model_dump()
    data["utility_asset_id"] = id
    data["performed_by"] = current_user.id
    return await service.repo.create_maintenance_event(db, data)


@router.get("/assets/{id}/maintenance", response_model=List[UtilityMaintenanceResponse])
async def list_maintenance_events(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists maintenance event history for a utility asset."""
    return await service.repo.list_maintenance_events_by_asset(db, id)


# 8. 2D Map & 3D Underground Streaming
@router.get("/map", response_model=UtilityGeoJSONCollection)
async def get_map_geojson(
    min_lon: float = Query(..., ge=-180, le=180),
    min_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    network_id: Optional[uuid.UUID] = None,
    utility_type: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GeoJSON endpoint for 2D GIS subsurface layers with bounding box envelope filtering."""
    return await service.get_map_geojson(db, min_lon, min_lat, max_lon, max_lat, network_id, utility_type, limit)


@router.get("/3d", response_model=Utility3DSceneResponse)
async def get_3d_scene(
    network_id: Optional[uuid.UUID] = None,
    utility_type: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Streams 3D subsurface pipes, tubes, and nodes with true depth and elevation coordinates for Cesium."""
    return await service.get_3d_scene(db, network_id, utility_type, limit)


# 9. Dashboard Metrics
@router.get("/metrics", response_model=UtilityMetricsResponse)
async def get_metrics(
    jurisdiction_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Database-derived KPI metrics for the Underground Infrastructure dashboard."""
    return await service.repo.get_metrics(db, jurisdiction_id)
