import json
import uuid
from typing import Any, Dict, Optional, Union
from fastapi import APIRouter, Body, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException
from app.dependencies.auth import get_current_user, require_officer_or_admin
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.gis import GISImportSummary, GeoJSONFeatureCollection
from app.services.gis_import_export_service import gis_import_export_service

router = APIRouter(prefix="/gis", tags=["GIS Import & Export"])


@router.post(
    "/import",
    response_model=GISImportSummary,
    status_code=status.HTTP_200_OK,
    summary="Import GeoJSON cadastral dataset with validation summary (Admin / Officer)",
)
async def import_gis_dataset(
    request: Request,
    jurisdiction_id: uuid.UUID = Query(..., description="Target jurisdiction for imported parcels"),
    payload: Optional[Dict[str, Any]] = Body(default=None, description="GeoJSON FeatureCollection JSON body"),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    if not payload:
        raise BadRequestException("Missing GeoJSON FeatureCollection payload in request body")

    summary = await gis_import_export_service.import_geojson(
        db=db,
        geojson_data=payload,
        jurisdiction_id=jurisdiction_id,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return summary


@router.get(
    "/export",
    response_model=GeoJSONFeatureCollection,
    summary="Export cadastral data as GeoJSON with optional filtering",
)
async def export_gis_dataset(
    request: Request,
    jurisdiction_id: Optional[uuid.UUID] = Query(default=None, description="Filter by jurisdiction"),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    bbox: Optional[str] = Query(default=None, description="'minLon,minLat,maxLon,maxLat'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    parsed_bbox = None
    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) == 4:
                parsed_bbox = (parts[0], parts[1], parts[2], parts[3])
        except Exception:
            pass

    return await gis_import_export_service.export_parcels_geojson(
        db=db,
        jurisdiction_id=jurisdiction_id,
        status=status_filter,
        bbox=parsed_bbox,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
