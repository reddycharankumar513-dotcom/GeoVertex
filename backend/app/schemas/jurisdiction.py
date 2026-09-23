import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class JurisdictionBase(BaseModel):
    organization_id: uuid.UUID
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=64)
    level: str = Field(default="WARD", max_length=64)
    parent_jurisdiction_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    srid: int = Field(default=4326)
    boundary_wkt: Optional[str] = None


class JurisdictionCreate(JurisdictionBase):
    boundary_geojson: Optional[dict] = None


class JurisdictionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    level: Optional[str] = None
    parent_jurisdiction_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    srid: Optional[int] = None
    boundary_wkt: Optional[str] = None
    boundary_geojson: Optional[dict] = None
    is_active: Optional[bool] = None


class JurisdictionResponse(JurisdictionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    status: str = "ACTIVE"
    default_crs: str = "EPSG:4326"
    created_at: datetime
    updated_at: datetime

