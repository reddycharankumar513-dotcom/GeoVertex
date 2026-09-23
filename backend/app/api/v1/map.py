import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.gis.geometry import GeometryEngine
from app.models.user import User
from app.repositories.jurisdiction_repository import jurisdiction_repository
from app.schemas.gis import GeoJSONFeature, GeoJSONFeatureCollection
from app.services.building_service import building_service
from app.services.parcel_service import parcel_service

router = APIRouter(prefix="/map", tags=["Map Visualization APIs"])


@router.get(
    "/parcels",
    response_model=GeoJSONFeatureCollection,
    summary="Get parcels for map visualization (viewport bounded)",
)
async def get_map_parcels(
    bbox: Optional[str] = Query(
        default=None,
        description="Bounding box in 'minLon,minLat,maxLon,maxLat' format (EPSG:4326)",
    ),
    jurisdiction_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=500, ge=1, le=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError("BBox requires 4 float coordinates")
            min_lon, min_lat, max_lon, max_lat = parts
        except Exception:
            min_lon, min_lat, max_lon, max_lat = -180.0, -90.0, 180.0, 90.0
        parcels = await parcel_service.get_parcels_in_bbox(
            db=db,
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            jurisdiction_id=jurisdiction_id,
            status=status_filter,
            limit=limit,
        )
    else:
        parcels, _ = await parcel_service.search_parcels(
            db=db,
            jurisdiction_id=jurisdiction_id,
            status=status_filter,
            skip=0,
            limit=limit,
        )

    features: List[GeoJSONFeature] = []
    for p in parcels:
        if not p.geometry_wkt:
            continue
        try:
            geom = GeometryEngine.parse_geometry(p.geometry_wkt)
            features.append(
                GeoJSONFeature(
                    type="Feature",
                    id=str(p.id),
                    geometry=GeometryEngine.to_geojson(geom),
                    properties={
                        "id": str(p.id),
                        "parcel_number": p.parcel_number,
                        "parcel_code": p.parcel_code,
                        "survey_number": p.survey_number,
                        "land_use": p.land_use,
                        "area_sq_m": p.area,
                        "status": p.status,
                        "ownership_status": p.ownership_status,
                        "centroid": [p.centroid_lon, p.centroid_lat] if p.centroid_lon else None,
                        "jurisdiction_id": str(p.jurisdiction_id),
                    },
                )
            )
        except Exception:
            continue

    return GeoJSONFeatureCollection(
        type="FeatureCollection",
        features=features,
        total_features=len(features),
        crs={"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
    )


@router.get(
    "/buildings",
    response_model=GeoJSONFeatureCollection,
    summary="Get building footprints for map visualization (viewport bounded)",
)
async def get_map_buildings(
    bbox: Optional[str] = Query(default=None, description="'minLon,minLat,maxLon,maxLat'"),
    parcel_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            min_lon, min_lat, max_lon, max_lat = parts
        except Exception:
            min_lon, min_lat, max_lon, max_lat = -180.0, -90.0, 180.0, 90.0
        buildings = await building_service.get_buildings_in_bbox(
            db=db,
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            parcel_id=parcel_id,
            limit=limit,
        )
    else:
        buildings, _ = await building_service.list_buildings(
            db=db,
            parcel_id=parcel_id,
            skip=0,
            limit=limit,
        )

    features: List[GeoJSONFeature] = []
    for b in buildings:
        if not b.geometry_wkt:
            continue
        try:
            geom = GeometryEngine.parse_geometry(b.geometry_wkt)
            features.append(
                GeoJSONFeature(
                    type="Feature",
                    id=str(b.id),
                    geometry=GeometryEngine.to_geojson(geom),
                    properties={
                        "id": str(b.id),
                        "building_reference": b.building_reference,
                        "building_type": b.building_type,
                        "status": b.status,
                        "area_sq_m": b.area,
                        "height_estimate": b.height_estimate,
                        "parcel_id": str(b.parcel_id) if b.parcel_id else None,
                    },
                )
            )
        except Exception:
            continue

    return GeoJSONFeatureCollection(
        type="FeatureCollection",
        features=features,
        total_features=len(features),
        crs={"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
    )


@router.get(
    "/boundaries",
    response_model=GeoJSONFeatureCollection,
    summary="Get administrative boundaries for map display",
)
async def get_map_boundaries(
    jurisdiction_id: Optional[uuid.UUID] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if jurisdiction_id:
        jur = await jurisdiction_repository.get_by_id(db, jurisdiction_id)
        jurisdictions = [jur] if jur else []
    else:
        jurisdictions = await jurisdiction_repository.get_all(db, skip=0, limit=100)

    features: List[GeoJSONFeature] = []
    for j in jurisdictions:
        if not j.boundary_wkt:
            continue
        try:
            geom = GeometryEngine.parse_geometry(j.boundary_wkt, source_srid=j.srid)
            features.append(
                GeoJSONFeature(
                    type="Feature",
                    id=str(j.id),
                    geometry=GeometryEngine.to_geojson(geom),
                    properties={
                        "id": str(j.id),
                        "name": j.name,
                        "code": j.code,
                        "level": j.level,
                        "srid": j.srid,
                        "is_active": j.is_active,
                    },
                )
            )
        except Exception:
            continue

    return GeoJSONFeatureCollection(
        type="FeatureCollection",
        features=features,
        total_features=len(features),
        crs={"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
    )
