import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_officer_or_admin
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.property import (
    PropertyCreate,
    PropertyDetailResponse,
    PropertyResponse,
    PropertyUpdate,
)
from app.services.property_service import property_service

router = APIRouter(prefix="/properties", tags=["Property Management"])


@router.get(
    "",
    response_model=PaginatedResponse[PropertyResponse],
    summary="List or search property records",
)
async def list_properties(
    parcel_id: Optional[uuid.UUID] = Query(default=None, description="Filter by parent parcel"),
    property_type: Optional[str] = Query(default=None, description="Filter by property type"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status"),
    query: Optional[str] = Query(default=None, description="Search query by reference or address"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await property_service.list_properties(
        db=db,
        parcel_id=parcel_id,
        property_type=property_type,
        status=status_filter,
        query=query,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[PropertyResponse](
        items=[PropertyResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new property record (Admin / Officer)",
)
async def create_property(
    data: PropertyCreate,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    created = await property_service.create_property(
        db=db,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return PropertyResponse.model_validate(created)


@router.get(
    "/{id}",
    response_model=PropertyDetailResponse,
    summary="Retrieve property record details with parent parcel",
)
async def get_property(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prop = await property_service.get_property(db, id)
    res = PropertyDetailResponse.model_validate(prop)
    if prop.parcel:
        res.parcel_number = prop.parcel.parcel_number
        res.parcel_code = prop.parcel.parcel_code
        if prop.parcel.jurisdiction:
            res.jurisdiction_name = prop.parcel.jurisdiction.name
            res.jurisdiction_code = prop.parcel.jurisdiction.code
    return res


@router.patch(
    "/{id}",
    response_model=PropertyResponse,
    summary="Update property record (Admin / Officer)",
)
async def update_property(
    id: uuid.UUID,
    data: PropertyUpdate,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    updated = await property_service.update_property(
        db=db,
        id=id,
        data=data,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return PropertyResponse.model_validate(updated)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete property record (Admin / Officer)",
)
async def delete_property(
    id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await property_service.delete_property(
        db=db,
        id=id,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {"message": "Property deleted successfully", "id": str(id)}
