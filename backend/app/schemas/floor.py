import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class FloorBase(BaseModel):
    building_id: uuid.UUID
    floor_number: int = Field(
        description="Floor level index: 0 for Ground, 1 for Level 1, -1 for Basement"
    )
    floor_code: str = Field(min_length=1, max_length=128)
    floor_name: Optional[str] = Field(default=None, max_length=128)
    floor_type: str = Field(default="RESIDENTIAL", max_length=64)
    elevation_min_m: float = Field(default=0.0, description="Base elevation in meters above local base plane")
    elevation_max_m: float = Field(default=3.0, description="Top elevation in meters above local base plane")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="ACTIVE", max_length=32)
    source: str = Field(default="SURVEY", max_length=64)


class FloorCreate(FloorBase):
    geometry: Optional[Union[Dict[str, Any], str]] = Field(
        default=None,
        description="GeoJSON geometry dictionary or WKT string representing floor slab boundary. Defaults to parent building footprint if omitted.",
    )
    source_srid: int = Field(default=4326, description="Source Coordinate Reference System (SRID)")


class FloorUpdate(BaseModel):
    floor_number: Optional[int] = None
    floor_code: Optional[str] = Field(default=None, min_length=1, max_length=128)
    floor_name: Optional[str] = None
    floor_type: Optional[str] = None
    elevation_min_m: Optional[float] = None
    elevation_max_m: Optional[float] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Optional[str] = None
    source: Optional[str] = None
    geometry: Optional[Union[Dict[str, Any], str]] = None
    source_srid: Optional[int] = 4326


class FloorResponse(FloorBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    height_m: float
    area_sqm: float
    geometry_wkt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FloorDetailResponse(FloorResponse):
    building_reference: Optional[str] = None
    parcel_code: Optional[str] = None
    units_count: int = 0
