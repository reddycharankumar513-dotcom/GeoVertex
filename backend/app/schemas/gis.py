from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    id: Optional[str] = None
    geometry: Dict[str, Any]
    properties: Dict[str, Any] = {}


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = []
    total_features: Optional[int] = None
    crs: Optional[Dict[str, Any]] = None


class GISImportErrorItem(BaseModel):
    feature_index: int
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class GISImportSummary(BaseModel):
    records_received: int
    records_accepted: int
    records_rejected: int
    entity_type: str = "PARCEL"
    errors: List[GISImportErrorItem] = []
    warnings: List[str] = []
    jurisdiction_id: Optional[str] = None
