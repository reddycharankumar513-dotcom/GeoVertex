import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Building3DRepresentationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    building_id: uuid.UUID
    geometry_type: str
    height: float
    height_source: str
    height_confidence: Optional[float] = None
    height_unit: str = "METERS"
    base_elevation: float = 0.0
    elevation_source: str
    vertical_reference: str
    model_source: str
    model_version: int
    status: str
    created_at: datetime
    updated_at: datetime


class Building3DHeightUpdateRequest(BaseModel):
    height: float = Field(..., ge=0.0, description="Building height in meters (non-negative)")
    height_source: Optional[str] = Field("MANUAL", description="Source of height measurement")
    height_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    base_elevation: Optional[float] = Field(0.0, description="Ground elevation relative to datum")
    elevation_source: Optional[str] = Field("LOCAL_REFERENCE_PLANE")
    vertical_reference: Optional[str] = Field("METERS_ABOVE_GROUND")


class CesiumExtrusionFeature(BaseModel):
    building_id: str
    building_reference: str
    building_type: str
    status: str
    parcel_id: Optional[str] = None
    parcel_code: Optional[str] = None
    footprint_area_sq_m: float
    volume_cu_m: float
    height: float
    height_source: str
    height_confidence: Optional[float] = None
    height_unit: str = "METERS"
    base_elevation: float = 0.0
    elevation_source: str
    vertical_reference: str
    extruded_height: float
    centroid: List[float]
    bbox_3d: List[float]
    rings: List[Dict[str, Any]]
    floors_count: int = 0
    units_count: int = 0


class SceneMetadata(BaseModel):
    crs: str = "EPSG:4326"
    vertical_reference: str = "METERS_ABOVE_GROUND"
    center: List[float]
    bounds: List[float]
    jurisdiction_id: Optional[str] = None
    camera_preset: Dict[str, Any] = Field(default_factory=dict)


class ThreeDSceneResponse(BaseModel):
    scene: SceneMetadata
    buildings: List[CesiumExtrusionFeature]
    parcels: List[Dict[str, Any]]
    floors: List[Dict[str, Any]] = Field(default_factory=list)
    units: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ThreeDIdentifyResponse(BaseModel):
    unit: Optional[Dict[str, Any]] = None
    floor: Optional[Dict[str, Any]] = None
    building: Optional[Dict[str, Any]] = None
    parcel: Optional[Dict[str, Any]] = None
    property: Optional[Dict[str, Any]] = None
    jurisdiction: Optional[Dict[str, Any]] = None


class ThreeDAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    building_id: Optional[uuid.UUID] = None
    representation_id: Optional[uuid.UUID] = None
    asset_type: str
    storage_location: str
    format: str
    version: int
    status: str
    source: str
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ThreeDAssetCreateRequest(BaseModel):
    building_id: Optional[uuid.UUID] = None
    representation_id: Optional[uuid.UUID] = None
    asset_type: str = "EXTRUSION"
    storage_location: str = "virtual://extrusions"
    format: str = "JSON_EXTRUSION"
    source: str = "MANUAL"
    status: str = "ACTIVE"
    metadata_json: Optional[str] = None
