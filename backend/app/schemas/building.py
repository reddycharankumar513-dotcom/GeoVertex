import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class BuildingBase(BaseModel):
    parcel_id: Optional[uuid.UUID] = None
    building_reference: str = Field(min_length=1, max_length=128)
    building_type: str = Field(default="RESIDENTIAL", max_length=64)
    status: str = Field(default="EXISTING", max_length=64)
    height_estimate: Optional[float] = None
    source: str = Field(default="SURVEY", max_length=64)
    source_reference: Optional[str] = Field(default=None, max_length=255)


class BuildingCreate(BuildingBase):
    geometry: Union[Dict[str, Any], str] = Field(
        description="GeoJSON geometry dictionary or WKT string representing building footprint"
    )
    source_srid: int = Field(default=4326, description="Source Coordinate Reference System (SRID)")


class BuildingUpdate(BaseModel):
    parcel_id: Optional[uuid.UUID] = None
    building_reference: Optional[str] = Field(default=None, min_length=1, max_length=128)
    building_type: Optional[str] = None
    status: Optional[str] = None
    height_estimate: Optional[float] = None
    source_reference: Optional[str] = None
    geometry: Optional[Union[Dict[str, Any], str]] = None
    source_srid: Optional[int] = 4326


class BuildingResponse(BuildingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    area: float
    geometry_wkt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BuildingDetailResponse(BuildingResponse):
    parcel_number: Optional[str] = None
    parcel_code: Optional[str] = None
