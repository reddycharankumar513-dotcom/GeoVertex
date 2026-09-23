import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PropertyBase(BaseModel):
    parcel_id: uuid.UUID
    property_reference: str = Field(min_length=1, max_length=128)
    property_type: str = Field(default="FREEHOLD", max_length=64)
    status: str = Field(default="ACTIVE", max_length=64)
    address: str = Field(min_length=3, max_length=512)
    locality: Optional[str] = Field(default=None, max_length=255)
    postal_code: Optional[str] = Field(default=None, max_length=32)
    description: Optional[str] = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    parcel_id: Optional[uuid.UUID] = None
    property_reference: Optional[str] = Field(default=None, min_length=1, max_length=128)
    property_type: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = Field(default=None, min_length=3, max_length=512)
    locality: Optional[str] = None
    postal_code: Optional[str] = None
    description: Optional[str] = None


class PropertyResponse(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PropertyDetailResponse(PropertyResponse):
    parcel_number: Optional[str] = None
    parcel_code: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    jurisdiction_code: Optional[str] = None
