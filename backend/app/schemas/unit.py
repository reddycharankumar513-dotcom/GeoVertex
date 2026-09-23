import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class UnitBase(BaseModel):
    floor_id: uuid.UUID
    building_id: Optional[uuid.UUID] = None
    property_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional attachment to legal cadastral property record",
    )
    unit_number: str = Field(min_length=1, max_length=64, description="Unit designation e.g. 101, 102")
    unit_code: str = Field(min_length=1, max_length=128, description="Systematic unit code")
    unit_type: str = Field(default="APARTMENT", max_length=64)
    gross_area_sqm: float = Field(default=0.0, ge=0.0)
    net_area_sqm: float = Field(default=0.0, ge=0.0)
    elevation_min_m: float = Field(default=0.0)
    elevation_max_m: float = Field(default=3.0)
    status: str = Field(default="ACTIVE", max_length=32)
    ownership_status: str = Field(default="PRIVATE", max_length=64)


class UnitCreate(UnitBase):
    geometry: Union[Dict[str, Any], str] = Field(
        description="GeoJSON geometry dictionary or WKT string representing unit boundary polygon",
    )
    source_srid: int = Field(default=4326, description="Source Coordinate Reference System (SRID)")


class UnitUpdate(BaseModel):
    property_id: Optional[uuid.UUID] = None
    unit_number: Optional[str] = Field(default=None, min_length=1, max_length=64)
    unit_code: Optional[str] = Field(default=None, min_length=1, max_length=128)
    unit_type: Optional[str] = None
    gross_area_sqm: Optional[float] = Field(default=None, ge=0.0)
    net_area_sqm: Optional[float] = Field(default=None, ge=0.0)
    elevation_min_m: Optional[float] = None
    elevation_max_m: Optional[float] = None
    status: Optional[str] = None
    ownership_status: Optional[str] = None
    geometry: Optional[Union[Dict[str, Any], str]] = None
    source_srid: Optional[int] = 4326


class UnitResponse(UnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    height_m: float
    geometry_wkt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UnitDetailResponse(UnitResponse):
    floor_code: Optional[str] = None
    floor_number: Optional[int] = None
    building_reference: Optional[str] = None
    property_reference: Optional[str] = None
    parcel_code: Optional[str] = None
