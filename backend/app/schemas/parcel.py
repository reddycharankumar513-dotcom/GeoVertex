import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class ParcelBase(BaseModel):
    jurisdiction_id: uuid.UUID
    parcel_number: str = Field(min_length=1, max_length=64)
    parcel_code: str = Field(min_length=1, max_length=128)
    survey_number: Optional[str] = Field(default=None, max_length=64)
    subdivision_number: Optional[str] = Field(default=None, max_length=64)
    land_use: str = Field(default="RESIDENTIAL", max_length=64)
    status: str = Field(default="ACTIVE", max_length=64)
    ownership_status: str = Field(default="RECORDED", max_length=64)
    area_unit: str = Field(default="SQ_METER", max_length=32)
    source: str = Field(default="MANUAL", max_length=64)
    source_reference: Optional[str] = Field(default=None, max_length=255)


class ParcelCreate(ParcelBase):
    geometry: Union[Dict[str, Any], str] = Field(
        description="GeoJSON geometry dictionary or WKT string representing parcel polygon"
    )
    source_srid: int = Field(default=4326, description="Source Coordinate Reference System (SRID)")


class ParcelUpdate(BaseModel):
    parcel_number: Optional[str] = Field(default=None, min_length=1, max_length=64)
    parcel_code: Optional[str] = Field(default=None, min_length=1, max_length=128)
    survey_number: Optional[str] = None
    subdivision_number: Optional[str] = None
    land_use: Optional[str] = None
    status: Optional[str] = None
    ownership_status: Optional[str] = None
    source_reference: Optional[str] = None
    geometry: Optional[Union[Dict[str, Any], str]] = None
    source_srid: Optional[int] = 4326


class ParcelResponse(ParcelBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    area: float
    centroid_lon: Optional[float] = None
    centroid_lat: Optional[float] = None
    geometry_wkt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PropertySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_reference: str
    property_type: str
    status: str
    address: str


class BuildingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    building_reference: str
    building_type: str
    status: str
    area: float
    height_estimate: Optional[float] = None


class ParcelDetailResponse(ParcelResponse):
    properties: List[PropertySummary] = []
    buildings: List[BuildingSummary] = []
    jurisdiction_name: Optional[str] = None
    jurisdiction_code: Optional[str] = None
