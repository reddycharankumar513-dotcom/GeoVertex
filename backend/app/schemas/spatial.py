from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ValidationErrorSchema(BaseModel):
    code: str
    message: str


class ValidationWarningSchema(BaseModel):
    code: str
    message: str


class GeometryValidationRequest(BaseModel):
    geometry: Union[Dict[str, Any], str] = Field(description="GeoJSON geometry or WKT string")
    expected_type: Optional[str] = Field(default="POLYGON", description="POLYGON, MULTIPOLYGON, etc.")
    source_srid: int = Field(default=4326)


class GeometryValidationResponse(BaseModel):
    valid: bool
    area_sq_m: Optional[float] = None
    perimeter_m: Optional[float] = None
    centroid: Optional[List[float]] = None  # [lon, lat]
    bbox: Optional[List[float]] = None      # [min_lon, min_lat, max_lon, max_lat]
    errors: List[ValidationErrorSchema] = []
    warnings: List[ValidationWarningSchema] = []


class SpatialIdentifyPoint(BaseModel):
    longitude: float
    latitude: float


class IdentifiedFeature(BaseModel):
    id: str
    type: str  # "PARCEL", "BUILDING", "JURISDICTION"
    identifier: str  # parcel_code, building_reference, jurisdiction_code
    title: str
    status: Optional[str] = None
    area: Optional[float] = None
    distance_meters: Optional[float] = 0.0
    properties: Dict[str, Any] = {}


class SpatialIdentifyResponse(BaseModel):
    point: SpatialIdentifyPoint
    parcels: List[IdentifiedFeature] = []
    buildings: List[IdentifiedFeature] = []
    jurisdictions: List[IdentifiedFeature] = []


class OverlapCheckRequest(BaseModel):
    geometry: Union[Dict[str, Any], str]
    jurisdiction_id: Optional[str] = None
    exclude_parcel_id: Optional[str] = None


class OverlapConflict(BaseModel):
    parcel_id: str
    parcel_code: str
    parcel_number: str
    overlap_type: str  # "INVALID_AREA_OVERLAP" or "VALID_SHARED_BOUNDARY"
    overlap_area_sq_m: float


class OverlapCheckResponse(BaseModel):
    has_conflicts: bool
    conflicts: List[OverlapConflict] = []
