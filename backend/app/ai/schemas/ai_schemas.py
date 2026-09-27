import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Base Prediction Results
# -------------------------------------------------------------

class ConfidenceComponents(BaseModel):
    model_confidence: float = Field(0.0, ge=0.0, le=1.0)
    geometry_quality: float = Field(0.0, ge=0.0, le=1.0)
    source_quality: float = Field(0.0, ge=0.0, le=1.0)


class CadastralComparisonMetrics(BaseModel):
    iou: float = Field(0.0, ge=0.0, le=1.0)
    intersection_area_sqm: float = 0.0
    union_area_sqm: float = 0.0
    area_diff_sqm: float = 0.0
    boundary_diff_m: float = 0.0
    official_area_sqm: float = 0.0
    candidate_area_sqm: float = 0.0


class BuildingPredictionResult(BaseModel):
    model_name: str
    model_version: str
    geometry_geojson: Dict[str, Any]
    geometry_wkt: str
    raw_geometry_wkt: Optional[str] = None
    estimated_height: Optional[float] = None
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    confidence_components: ConfidenceComponents
    cadastral_comparison: Optional[CadastralComparisonMetrics] = None
    evidence_linkage: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateFloorItem(BaseModel):
    candidate_floor_number: int
    floor_label: str
    base_elevation: float
    top_elevation: float
    height: float
    geometry_geojson: Optional[Dict[str, Any]] = None
    geometry_wkt: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class FloorPredictionResult(BaseModel):
    model_name: str
    model_version: str
    building_id: str
    estimated_floor_count: int
    floor_candidates: List[CandidateFloorItem]
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    evidence_linkage: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------
# AI Processing Job Schemas
# -------------------------------------------------------------

class AIJobCreateRequest(BaseModel):
    client_request_id: Optional[str] = None
    job_type: str = Field(
        "BUILDING_EXTRACTION",
        description="BUILDING_EXTRACTION, FLOOR_EXTRACTION, HEIGHT_ESTIMATION, PREPROCESSING, POSTPROCESSING, VALIDATION",
    )
    target_type: str = Field("BUILDING", description="BUILDING, PARCEL, SURVEY_SESSION")
    target_id: str = Field(..., description="Target UUID string")
    model_id: Optional[str] = "building-segmentation-v1"
    model_version: Optional[str] = "1.0.0"
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    survey_evidence_ids: Optional[List[str]] = Field(default_factory=list)


class AIJobResponse(BaseModel):
    id: uuid.UUID
    client_request_id: Optional[str] = None
    job_type: str
    status: str
    stage: str
    progress_pct: int
    requested_by: Optional[uuid.UUID] = None
    target_type: str
    target_id: str
    model_id: str
    model_version: str
    parameters: Dict[str, Any]
    input_reference: Dict[str, Any]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AIJobListResponse(BaseModel):
    items: List[AIJobResponse]
    total: int
    page: int
    size: int


# -------------------------------------------------------------
# Candidate Results & Review Schemas
# -------------------------------------------------------------

class BuildingResultResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    source_target_id: str
    geometry_wkt: str
    geometry_geojson: Optional[Dict[str, Any]] = None
    raw_geometry_wkt: Optional[str] = None
    estimated_height: Optional[float] = None
    confidence: float
    confidence_components: Dict[str, Any]
    cadastral_comparison: Dict[str, Any]
    evidence_linkage: Dict[str, Any]
    model_id: str
    model_version: str
    status: str
    validation_status: str
    validation_details: Dict[str, Any]
    review_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class FloorResultResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    building_id: uuid.UUID
    candidate_floor_number: int
    floor_label: str
    base_elevation: float
    top_elevation: float
    height: float
    geometry_wkt: Optional[str] = None
    geometry_geojson: Optional[Dict[str, Any]] = None
    confidence: float
    source: str
    status: str
    validation_details: Dict[str, Any]
    review_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class AIReviewDecisionRequest(BaseModel):
    action: str = Field(..., description="APPROVE, REJECT, MODIFY_AND_APPROVE, REQUEST_REPROCESSING")
    edited_geometry_wkt: Optional[str] = None
    notes: Optional[str] = None


class AIReviewResponse(BaseModel):
    id: uuid.UUID
    result_type: str
    result_id: uuid.UUID
    reviewer_id: uuid.UUID
    action: str
    original_geometry_wkt: str
    edited_geometry_wkt: Optional[str] = None
    notes: Optional[str] = None
    applied_to_cadastre: bool
    applied_at: Optional[datetime] = None
    created_at: datetime


# -------------------------------------------------------------
# AI Model & Version Schemas
# -------------------------------------------------------------

class AIModelVersionResponse(BaseModel):
    id: uuid.UUID
    model_id: uuid.UUID
    version: str
    weights_reference: Optional[str] = None
    weights_hash: Optional[str] = None
    configuration: Dict[str, Any]
    metrics: Dict[str, Any]
    is_active: bool
    created_at: datetime


class AIModelResponse(BaseModel):
    id: uuid.UUID
    model_id: str
    name: str
    model_type: str
    framework: str
    description: Optional[str] = None
    status: str
    metadata_json: Dict[str, Any]
    versions: List[AIModelVersionResponse] = Field(default_factory=list)
    created_at: datetime


class AIModelRegisterRequest(BaseModel):
    model_id: str
    name: str
    model_type: str
    framework: Optional[str] = "PYTORCH"
    description: Optional[str] = None
    initial_version: Optional[str] = "1.0.0"
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict)


# -------------------------------------------------------------
# AI Evaluation Schemas
# -------------------------------------------------------------

class AIDatasetResponse(BaseModel):
    id: uuid.UUID
    dataset_id: str
    name: str
    version: str
    dataset_type: str
    source: str
    sample_count: int
    label_schema: Dict[str, Any]
    description: Optional[str] = None
    created_at: datetime


class AIEvaluationRunRequest(BaseModel):
    dataset_id: uuid.UUID
    model_id: str
    model_version: str
    notes: Optional[str] = None


class AIEvaluationRunResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    model_id: str
    model_version: str
    metrics: Dict[str, Any]
    executed_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime
