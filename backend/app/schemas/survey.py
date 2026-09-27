import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Survey Projects
# ============================================================================

class SurveyProjectBase(BaseModel):
    organization_id: uuid.UUID
    jurisdiction_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=64)
    description: Optional[str] = None
    status: str = Field(default="DRAFT", max_length=32)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SurveyProjectCreate(SurveyProjectBase):
    pass


class SurveyProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=32)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SurveyProjectResponse(SurveyProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class SurveyProjectDetailResponse(SurveyProjectResponse):
    organization_name: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    assignments_count: int = 0
    active_assignments_count: int = 0
    completed_assignments_count: int = 0


# ============================================================================
# Survey Assignments
# ============================================================================

class SurveyAssignmentBase(BaseModel):
    survey_project_id: uuid.UUID
    surveyor_id: uuid.UUID
    jurisdiction_id: uuid.UUID
    parcel_id: Optional[uuid.UUID] = None
    property_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    floor_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    priority: str = Field(default="MEDIUM", max_length=32)
    status: str = Field(default="ASSIGNED", max_length=32)
    due_at: Optional[datetime] = None
    notes: Optional[str] = None


class SurveyAssignmentCreate(SurveyAssignmentBase):
    pass


class SurveyAssignmentUpdate(BaseModel):
    surveyor_id: Optional[uuid.UUID] = None
    parcel_id: Optional[uuid.UUID] = None
    property_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    floor_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_at: Optional[datetime] = None
    notes: Optional[str] = None


class SurveyAssignmentResponse(SurveyAssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class SurveyAssignmentDetailResponse(SurveyAssignmentResponse):
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    surveyor_name: Optional[str] = None
    surveyor_email: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    parcel_code: Optional[str] = None
    property_reference: Optional[str] = None
    building_reference: Optional[str] = None
    floor_code: Optional[str] = None
    unit_code: Optional[str] = None
    sessions_count: int = 0
    submissions_count: int = 0


# ============================================================================
# Survey Sessions
# ============================================================================

class SurveySessionBase(BaseModel):
    assignment_id: uuid.UUID
    status: str = Field(default="DRAFT", max_length=32)
    device_identifier: Optional[str] = Field(default=None, max_length=128)
    app_version: Optional[str] = Field(default="1.0.0", max_length=32)
    sync_status: str = Field(default="SYNCED", max_length=32)
    notes: Optional[str] = None


class SurveySessionCreate(SurveySessionBase):
    pass


class SurveySessionUpdate(BaseModel):
    status: Optional[str] = None
    device_identifier: Optional[str] = None
    app_version: Optional[str] = None
    sync_status: Optional[str] = None
    notes: Optional[str] = None
    ended_at: Optional[datetime] = None


class SurveySessionResponse(SurveySessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    surveyor_id: uuid.UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SurveySessionDetailResponse(SurveySessionResponse):
    assignment: Optional[SurveyAssignmentDetailResponse] = None
    observations_count: int = 0
    evidence_count: int = 0


# ============================================================================
# Survey Observations
# ============================================================================

class SurveyObservationBase(BaseModel):
    observation_type: str = Field(
        description="BUILDING_HEIGHT, FLOOR_COUNT, FLOOR_HEIGHT, UNIT_AREA, PARCEL_BOUNDARY, etc."
    )
    target_type: str = Field(
        description="PARCEL, PROPERTY, BUILDING, FLOOR, UNIT, SURVEY_SESSION"
    )
    target_id: str = Field(min_length=1, max_length=36)
    value: str = Field(min_length=1, max_length=255)
    unit: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    horizontal_accuracy: Optional[float] = None
    altitude: Optional[float] = None
    vertical_accuracy: Optional[float] = None
    source: str = Field(default="FIELD_OBSERVATION", max_length=64)


class SurveyObservationCreate(SurveyObservationBase):
    geometry: Optional[Union[Dict[str, Any], str]] = None


class SurveyObservationUpdate(BaseModel):
    observation_type: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    horizontal_accuracy: Optional[float] = None
    altitude: Optional[float] = None
    vertical_accuracy: Optional[float] = None
    source: Optional[str] = None
    geometry: Optional[Union[Dict[str, Any], str]] = None


class SurveyObservationResponse(SurveyObservationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    captured_at: datetime
    captured_by: Optional[uuid.UUID] = None
    geometry_wkt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Survey Evidence
# ============================================================================

class SurveyEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    observation_id: Optional[uuid.UUID] = None
    target_type: str
    target_id: str
    filename: str
    mime_type: str
    file_size: int
    evidence_type: str
    captured_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    description: Optional[str] = None
    sha256_hash: str
    uploaded_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Survey Submissions & Review
# ============================================================================

class SurveySubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assignment_id: uuid.UUID
    survey_session_id: uuid.UUID
    version_number: int
    status: str
    snapshot_data: str
    submitted_by: uuid.UUID
    submitted_at: datetime
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SurveySubmissionReviewRequest(BaseModel):
    review_notes: Optional[str] = Field(default=None, description="Notes justifying approval, revision, or rejection")


# ============================================================================
# Sync Operations
# ============================================================================

class SyncOperationItem(BaseModel):
    client_operation_id: str = Field(min_length=1, max_length=128)
    session_id: Optional[uuid.UUID] = None
    operation_type: str = Field(description="CREATE_OBSERVATION, UPDATE_OBSERVATION, ATTACH_EVIDENCE, UPDATE_SESSION")
    entity_type: str
    entity_id: str
    payload: Dict[str, Any]


class SyncOperationBatchRequest(BaseModel):
    operations: List[SyncOperationItem]


class SyncOperationItemResult(BaseModel):
    client_operation_id: str
    status: str  # SYNCED, CONFLICT, VALIDATION_ERROR, FAILED
    entity_id: Optional[str] = None
    server_id: Optional[str] = None
    error: Optional[str] = None


class SyncOperationBatchResponse(BaseModel):
    results: List[SyncOperationItemResult]
    total_processed: int
    synced_count: int
    conflict_count: int
    failed_count: int


# ============================================================================
# Validation Engine & Readiness
# ============================================================================

class SurveyValidationIssue(BaseModel):
    code: str
    severity: str  # ERROR, WARNING, INFO
    field: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None


class SurveyValidationSummary(BaseModel):
    is_valid: bool
    can_submit: bool
    total_errors: int
    total_warnings: int
    issues: List[SurveyValidationIssue]
    checklist: Dict[str, bool] = Field(
        default_factory=dict,
        description="Readiness flags: required_fields, coordinates_captured, evidence_attached, measurements_valid, geometry_valid",
    )
    comparisons: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Deterministic discrepancies against cadastral records (e.g. building height delta)",
    )


# ============================================================================
# Export
# ============================================================================

class SurveyExportData(BaseModel):
    assignment: SurveyAssignmentDetailResponse
    sessions: List[SurveySessionResponse]
    observations: List[SurveyObservationResponse]
    evidence_metadata: List[SurveyEvidenceResponse]
    submissions: List[SurveySubmissionResponse]
    validation_summary: Optional[SurveyValidationSummary] = None
