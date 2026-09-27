"""Pydantic V2 schemas for underground infrastructure and subsurface utility intelligence."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# 1. Networks
class UtilityNetworkBase(BaseModel):
    name: str = Field(..., max_length=255)
    utility_type: str = Field("WATER", max_length=64)
    owner_organization: Optional[str] = Field(None, max_length=255)
    operator_organization: Optional[str] = Field(None, max_length=255)
    status: str = Field("ACTIVE", max_length=32)
    source: str = Field("OFFICIAL_RECORD", max_length=64)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class UtilityNetworkCreate(UtilityNetworkBase):
    jurisdiction_id: uuid.UUID


class UtilityNetworkUpdate(BaseModel):
    name: Optional[str] = None
    utility_type: Optional[str] = None
    owner_organization: Optional[str] = None
    operator_organization: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class UtilityNetworkResponse(UtilityNetworkBase):
    id: uuid.UUID
    jurisdiction_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 2. Assets
class UtilityAssetBase(BaseModel):
    asset_type: str = Field("PIPE", max_length=64)
    asset_reference: str = Field(..., max_length=128)
    status: str = Field("ACTIVE", max_length=32)
    review_status: str = Field("CANDIDATE", max_length=32)
    geometry_type: str = Field("LINESTRING", max_length=32)
    geometry_wkt: Optional[str] = None
    elevation_reference: str = Field("GROUND_RELATIVE", max_length=32)
    depth: Optional[float] = None
    depth_min: Optional[float] = None
    depth_max: Optional[float] = None
    ground_elevation: Optional[float] = None
    centerline_elevation: Optional[float] = None
    material: Optional[str] = None
    diameter: Optional[float] = None
    width: Optional[float] = None
    capacity: Optional[str] = None
    installation_date: Optional[datetime] = None
    commissioning_date: Optional[datetime] = None
    source_type: str = Field("OFFICIAL_RECORD", max_length=64)
    source_reference: Optional[str] = None
    confidence: str = Field("MEDIUM", max_length=32)
    parcel_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class UtilityAssetCreate(UtilityAssetBase):
    network_id: uuid.UUID


class UtilityAssetUpdate(BaseModel):
    asset_type: Optional[str] = None
    asset_reference: Optional[str] = None
    status: Optional[str] = None
    review_status: Optional[str] = None
    geometry_wkt: Optional[str] = None
    elevation_reference: Optional[str] = None
    depth: Optional[float] = None
    depth_min: Optional[float] = None
    depth_max: Optional[float] = None
    ground_elevation: Optional[float] = None
    centerline_elevation: Optional[float] = None
    material: Optional[str] = None
    diameter: Optional[float] = None
    width: Optional[float] = None
    capacity: Optional[str] = None
    confidence: Optional[str] = None
    parcel_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None


class UtilityAssetResponse(UtilityAssetBase):
    id: uuid.UUID
    network_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 3. Segments & Nodes
class UtilitySegmentCreate(BaseModel):
    utility_asset_id: uuid.UUID
    start_node_id: Optional[uuid.UUID] = None
    end_node_id: Optional[uuid.UUID] = None
    geometry_wkt: Optional[str] = None
    length_meters: float = 0.0
    depth_start: Optional[float] = None
    depth_end: Optional[float] = None
    elevation_start: Optional[float] = None
    elevation_end: Optional[float] = None
    slope_percentage: Optional[float] = None
    flow_direction: str = "UNKNOWN"
    status: str = "ACTIVE"


class UtilitySegmentResponse(UtilitySegmentCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UtilityNodeCreate(BaseModel):
    network_id: uuid.UUID
    node_type: str = Field("JUNCTION", max_length=64)
    asset_reference: str = Field(..., max_length=128)
    geometry_wkt: Optional[str] = None
    elevation: Optional[float] = None
    depth: Optional[float] = None
    status: str = Field("ACTIVE", max_length=32)
    source: str = Field("OFFICIAL_RECORD", max_length=64)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class UtilityNodeResponse(UtilityNodeCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 4. Structures & Corridors
class UtilityStructureCreate(BaseModel):
    utility_asset_id: uuid.UUID
    structure_type: str = "VAULT"
    geometry_wkt: Optional[str] = None
    top_elevation: Optional[float] = None
    bottom_elevation: Optional[float] = None
    depth: Optional[float] = None
    width_m: Optional[float] = None
    length_m: Optional[float] = None
    height_m: Optional[float] = None
    source: str = "OFFICIAL_RECORD"
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class UtilityStructureResponse(UtilityStructureCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UtilityCorridorCreate(BaseModel):
    corridor_reference: str = Field(..., max_length=128)
    jurisdiction_id: uuid.UUID
    geometry_wkt: Optional[str] = None
    width_meters: float = 5.0
    depth_range_json: Dict[str, Any] = Field(default_factory=dict)
    utility_types: List[str] = Field(default_factory=list)
    source: str = "OFFICIAL_RECORD"
    status: str = "ACTIVE"


class UtilityCorridorResponse(UtilityCorridorCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 5. Separation Rules
class UtilitySeparationRuleCreate(BaseModel):
    rule_code: str = Field(..., max_length=64)
    utility_type_a: str = Field(..., max_length=64)
    utility_type_b: str = Field(..., max_length=64)
    required_horizontal_separation_m: float = 1.0
    required_vertical_separation_m: float = 0.3
    jurisdiction_id: Optional[uuid.UUID] = None
    source: str = "MUNICIPAL_STANDARD"
    version: str = "1.0"
    effective_date: Optional[datetime] = None
    status: str = "ACTIVE"


class UtilitySeparationRuleResponse(UtilitySeparationRuleCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 6. Clashes
class UtilityClashResponse(BaseModel):
    id: uuid.UUID
    asset_a_id: uuid.UUID
    asset_b_id: uuid.UUID
    horizontal_relationship: str
    vertical_relationship: str
    measured_horizontal_separation_m: float
    measured_vertical_separation_m: float
    required_horizontal_separation_m: float
    required_vertical_separation_m: float
    clash_geometry_wkt: Optional[str] = None
    severity: str
    status: str
    resolution_notes: Optional[str] = None
    resolved_by: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UtilityClashReviewPayload(BaseModel):
    action: str = Field(..., pattern="^(ACKNOWLEDGE|RESOLVE|WAIVE)$")
    resolution_notes: str = Field(..., min_length=3)


# 7. Inspections & Maintenance
class UtilityInspectionCreate(BaseModel):
    inspection_date: datetime
    condition: str = "GOOD"
    depth_measurement: Optional[float] = None
    observations: Optional[str] = None
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "PASS"


class UtilityInspectionResponse(UtilityInspectionCreate):
    id: uuid.UUID
    utility_asset_id: uuid.UUID
    inspector_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UtilityMaintenanceCreate(BaseModel):
    event_type: str = "INSPECTION"
    event_date: datetime
    description: str
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)


class UtilityMaintenanceResponse(UtilityMaintenanceCreate):
    id: uuid.UUID
    utility_asset_id: uuid.UUID
    performed_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 8. Human Review & Controlled Official Update
class UtilityReviewActionPayload(BaseModel):
    action: str = Field(..., pattern="^(VERIFY|REJECT|REVISION_REQUIRED)$")
    review_notes: str = Field(..., min_length=3)


class ControlledOfficialUpdatePayload(BaseModel):
    reason: str = Field(..., min_length=5)
    source_reference: str = Field(..., min_length=3)
    updates: Dict[str, Any]


# 9. GeoJSON & 3D Spatial Responses
class UtilityGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Optional[Dict[str, Any]] = None
    properties: Dict[str, Any]


class UtilityGeoJSONCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[UtilityGeoJSONFeature]


class Utility3DFeature(BaseModel):
    asset_id: str
    asset_reference: str
    network_id: str
    utility_type: str
    asset_type: str
    geometry_type: str
    coordinates: List[Any]
    depth: Optional[float] = None
    ground_elevation: Optional[float] = None
    centerline_elevation: Optional[float] = None
    diameter_m: float = 0.3
    material: Optional[str] = None
    status: str
    color_hex: str


class Utility3DSceneResponse(BaseModel):
    total_features: int
    features: List[Utility3DFeature]


# 10. Dashboard Metrics
class UtilityMetricsResponse(BaseModel):
    total_networks: int
    total_assets: int
    active_assets: int
    candidates_requiring_review: int
    verified_assets: int
    total_clashes: int
    open_clashes: int
    unknown_depth_assets: int
    low_confidence_assets: int
