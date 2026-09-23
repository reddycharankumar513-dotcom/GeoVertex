import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.gis.geometry import GeometryEngine
from app.models.user import User
from app.repositories.building_repository import building_repository
from app.repositories.jurisdiction_repository import jurisdiction_repository
from app.repositories.parcel_repository import parcel_repository
from app.schemas.spatial import (
    GeometryValidationRequest,
    GeometryValidationResponse,
    IdentifiedFeature,
    OverlapCheckRequest,
    OverlapCheckResponse,
    OverlapConflict,
    SpatialIdentifyPoint,
    SpatialIdentifyResponse,
    ValidationErrorSchema,
    ValidationWarningSchema,
)
import shapely

router = APIRouter(prefix="/spatial", tags=["Spatial Analysis & Validation"])


@router.post(
    "/validate",
    response_model=GeometryValidationResponse,
    summary="Validate geometry and calculate authoritative measurements",
)
async def validate_geometry(
    req: GeometryValidationRequest,
    current_user: User = Depends(get_current_user),
):
    res = GeometryEngine.validate_geometry(
        req.geometry,
        expected_type=req.expected_type,
        source_srid=req.source_srid,
    )
    if not res.valid:
        return GeometryValidationResponse(
            valid=False,
            errors=[ValidationErrorSchema(code=e.code, message=e.message) for e in res.errors],
            warnings=[ValidationWarningSchema(code=w.code, message=w.message) for w in res.warnings],
        )

    parsed = GeometryEngine.parse_geometry(req.geometry, source_srid=req.source_srid)
    area = GeometryEngine.calculate_geodesic_area(parsed)
    centroid = GeometryEngine.calculate_centroid(parsed)
    bbox = GeometryEngine.get_bbox(parsed)

    return GeometryValidationResponse(
        valid=True,
        area_sq_m=area,
        centroid=list(centroid),
        bbox=list(bbox),
        errors=[],
        warnings=[ValidationWarningSchema(code=w.code, message=w.message) for w in res.warnings],
    )


@router.get(
    "/identify",
    response_model=SpatialIdentifyResponse,
    summary="Identify cadastral features at a geographic coordinate (lon, lat)",
)
async def identify_features(
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude in EPSG:4326"),
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude in EPSG:4326"),
    radius_meters: float = Query(default=30.0, ge=1.0, le=500.0, description="Search radius in meters"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    point = shapely.geometry.Point(longitude, latitude)

    # 1. Identify Parcels
    parcel_matches = await parcel_repository.identify_at_point(
        db, lon=longitude, lat=latitude, radius_meters=radius_meters
    )
    identified_parcels: List[IdentifiedFeature] = []
    for p, dist in parcel_matches[:5]:
        identified_parcels.append(
            IdentifiedFeature(
                id=str(p.id),
                type="PARCEL",
                identifier=p.parcel_code,
                title=f"Parcel {p.parcel_number} ({p.land_use})",
                status=p.status,
                area=p.area,
                distance_meters=dist,
                properties={
                    "parcel_number": p.parcel_number,
                    "parcel_code": p.parcel_code,
                    "survey_number": p.survey_number,
                    "land_use": p.land_use,
                    "ownership_status": p.ownership_status,
                },
            )
        )

    # 2. Identify Buildings
    building_matches = await building_repository.identify_at_point(
        db, lon=longitude, lat=latitude, radius_meters=radius_meters
    )
    identified_buildings: List[IdentifiedFeature] = []
    for b, dist in building_matches[:5]:
        identified_buildings.append(
            IdentifiedFeature(
                id=str(b.id),
                type="BUILDING",
                identifier=b.building_reference,
                title=f"Building {b.building_reference} ({b.building_type})",
                status=b.status,
                area=b.area,
                distance_meters=dist,
                properties={
                    "building_reference": b.building_reference,
                    "building_type": b.building_type,
                    "height_estimate": b.height_estimate,
                    "parcel_id": str(b.parcel_id) if b.parcel_id else None,
                },
            )
        )

    # 3. Identify Jurisdictions containing point
    all_jurs = await jurisdiction_repository.get_all(db, skip=0, limit=100)
    identified_jurs: List[IdentifiedFeature] = []
    for j in all_jurs:
        if not j.boundary_wkt:
            continue
        try:
            j_geom = GeometryEngine.parse_geometry(j.boundary_wkt, source_srid=j.srid)
            if j_geom.contains(point):
                identified_jurs.append(
                    IdentifiedFeature(
                        id=str(j.id),
                        type="JURISDICTION",
                        identifier=j.code,
                        title=f"{j.name} ({j.level})",
                        status="ACTIVE" if j.is_active else "INACTIVE",
                        distance_meters=0.0,
                        properties={"code": j.code, "level": j.level, "name": j.name},
                    )
                )
        except Exception:
            continue

    return SpatialIdentifyResponse(
        point=SpatialIdentifyPoint(longitude=longitude, latitude=latitude),
        parcels=identified_parcels,
        buildings=identified_buildings,
        jurisdictions=identified_jurs,
    )


@router.post(
    "/check-overlap",
    response_model=OverlapCheckResponse,
    summary="Check if a candidate geometry overlaps existing cadastral parcels",
)
async def check_overlap(
    req: OverlapCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        candidate_geom = GeometryEngine.parse_geometry(req.geometry)
    except Exception:
        return OverlapCheckResponse(has_conflicts=False, conflicts=[])

    min_lon, min_lat, max_lon, max_lat = GeometryEngine.get_bbox(candidate_geom)
    jurisdiction_uuid = uuid.UUID(req.jurisdiction_id) if req.jurisdiction_id else None
    exclude_uuid = uuid.UUID(req.exclude_parcel_id) if req.exclude_parcel_id else None

    existing_parcels = await parcel_repository.get_by_bbox(
        db=db,
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        jurisdiction_id=jurisdiction_uuid,
        status="ACTIVE",
    )

    conflicts: List[OverlapConflict] = []
    for p in existing_parcels:
        if exclude_uuid and p.id == exclude_uuid:
            continue
        if not p.geometry_wkt:
            continue
        try:
            p_geom = GeometryEngine.parse_geometry(p.geometry_wkt)
            overlap_type, overlap_area = GeometryEngine.check_overlap(candidate_geom, p_geom)
            if overlap_type != "DISJOINT":
                conflicts.append(
                    OverlapConflict(
                        parcel_id=str(p.id),
                        parcel_code=p.parcel_code,
                        parcel_number=p.parcel_number,
                        overlap_type=overlap_type,
                        overlap_area_sq_m=overlap_area,
                    )
                )
        except Exception:
            continue

    has_fatal_conflicts = any(c.overlap_type == "INVALID_AREA_OVERLAP" for c in conflicts)
    return OverlapCheckResponse(has_conflicts=has_fatal_conflicts, conflicts=conflicts)
