from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.temporal import (
    CandidateStatus,
    ChangeRunStatus,
    ChangeSignificance,
    ChangeType,
    DatePrecision,
    DetectionMethod,
    ReviewReason,
    SnapshotEntityType,
    SnapshotType,
)


class PropertySnapshotCreate(BaseModel):
    entity_type: SnapshotEntityType
    entity_id: uuid.UUID
    snapshot_type: SnapshotType = SnapshotType.OFFICIAL_RECORD
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    observation_date: Optional[datetime] = None
    document_date: Optional[datetime] = None
    date_precision: DatePrecision = DatePrecision.EXACT
    source_type: str = "OFFICIAL_RECORD"
    source_id: Optional[str] = None
    geometry_wkt: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    version_number: int = 1
    is_current: bool = False


class PropertySnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    snapshot_type: str
    effective_from: datetime
    effective_to: Optional[datetime] = None
    observation_date: Optional[datetime] = None
    document_date: Optional[datetime] = None
    date_precision: str
    source_type: str
    source_id: Optional[str] = None
    geometry_wkt: Optional[str] = None
    attributes_json: Dict[str, Any] = Field(default_factory=dict)
    version_number: int
    is_current: bool
    created_at: datetime


class ChangeDetectionRunCreate(BaseModel):
    target_type: str = "BUILDING"  # PARCEL, BUILDING, FLOOR, UNIT, JURISDICTION
    target_id: Optional[uuid.UUID] = None
    baseline_reference: str  # snapshot UUID or dataset reference
    comparison_reference: str  # snapshot UUID or dataset reference
    detection_method: DetectionMethod = DetectionMethod.GEOMETRY_DIFF
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ChangeCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    detection_run_id: uuid.UUID
    change_type: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    baseline_snapshot_id: Optional[uuid.UUID] = None
    comparison_snapshot_id: Optional[uuid.UUID] = None
    baseline_date: Optional[datetime] = None
    comparison_date: Optional[datetime] = None
    geometry_wkt: Optional[str] = None
    baseline_geometry_wkt: Optional[str] = None
    comparison_geometry_wkt: Optional[str] = None
    magnitude: Dict[str, Any] = Field(default_factory=dict)
    significance: str
    confidence: Optional[float] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    validation_issues: List[Dict[str, Any]] = Field(default_factory=list)
    status: str
    review_reason: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class ChangeDetectionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_type: str
    target_id: Optional[uuid.UUID] = None
    jurisdiction_id: Optional[uuid.UUID] = None
    baseline_reference: str
    comparison_reference: str
    detection_method: str
    status: str
    requested_by: Optional[uuid.UUID] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    ruleset_version: str
    model_id: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChangeCandidateReviewRequest(BaseModel):
    action: str  # CONFIRM, REJECT, DISMISS
    review_reason: Optional[ReviewReason] = None
    review_notes: Optional[str] = None


class RasterObservationCreate(BaseModel):
    source: str = "ORTHOPHOTO"
    acquisition_date: datetime
    date_precision: DatePrecision = DatePrecision.EXACT
    file_reference: str
    footprint_wkt: Optional[str] = None
    crs: str = "EPSG:4326"
    resolution_meters: Optional[float] = None
    checksum_sha256: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class RasterObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    acquisition_date: datetime
    date_precision: str
    file_reference: str
    footprint_wkt: Optional[str] = None
    crs: str
    resolution_meters: Optional[float] = None
    checksum_sha256: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TemporalMetricsResponse(BaseModel):
    total_runs: int
    total_candidates: int
    under_review: int
    confirmed: int
    rejected: int
    dismissed: int
    building_changes: int
    floor_changes: int
    parcel_changes: int


class TimelineEntryResponse(BaseModel):
    entry_id: str
    entry_type: str
    date: Optional[str] = None
    date_precision: str
    source: str
    title: str
    description: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    geometry_wkt: Optional[str] = None
    status: Optional[str] = None
