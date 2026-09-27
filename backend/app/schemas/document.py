from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.document import (
    ConfidenceLevel,
    DocumentStatus,
    DocumentType,
    FieldReviewStatus,
    LinkMethod,
)


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    document_type: str = DocumentType.OTHER.value
    description: Optional[str] = None
    jurisdiction_id: Optional[str] = None
    property_id: Optional[str] = None
    parcel_id: Optional[str] = None
    building_id: Optional[str] = None
    floor_id: Optional[str] = None
    unit_id: Optional[str] = None
    document_date: Optional[datetime] = None
    issuing_authority: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    document_type: Optional[str] = None
    description: Optional[str] = None
    jurisdiction_id: Optional[str] = None
    property_id: Optional[str] = None
    parcel_id: Optional[str] = None
    building_id: Optional[str] = None
    floor_id: Optional[str] = None
    unit_id: Optional[str] = None
    document_date: Optional[datetime] = None
    issuing_authority: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_number: int
    storage_key: str
    original_filename: str
    mime_type: str
    file_size: int
    file_hash: str
    page_count: int
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    processing_status: str
    source_notes: Optional[str] = None
    created_at: datetime


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_version_id: str
    page_number: int
    image_reference: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    rotation: int
    processing_status: str
    extracted_text: Optional[str] = None
    created_at: datetime


class DocumentOCRResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_version_id: str
    page_id: Optional[str] = None
    engine: str
    engine_version: Optional[str] = None
    language: str
    text: str
    blocks_json: List[Any] = []
    confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime


class DocumentExtractedFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_version_id: str
    field_name: str
    field_value: str
    normalized_value: Optional[str] = None
    data_type: str
    page_number: Optional[int] = None
    bounding_box: Optional[Dict[str, Any]] = None
    extraction_method: str
    confidence: Optional[float] = None
    confidence_level: str
    evidence_text: Optional[str] = None
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    review_status: str
    reviewed_value: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FieldReviewAction(BaseModel):
    action: str = Field(..., description="CONFIRM, CORRECT, or REJECT")
    reviewed_value: Optional[str] = None
    review_notes: Optional[str] = None


class DocumentVerifyAction(BaseModel):
    notes: Optional[str] = None


class DocumentRejectAction(BaseModel):
    rejection_reason: str = Field(..., min_length=3, description="Mandatory rationale for rejection")


class DocumentRequireCorrectionAction(BaseModel):
    correction_notes: str = Field(..., min_length=3, description="Mandatory details of required correction")


class DocumentEntityLinkCreate(BaseModel):
    entity_type: str = Field(..., description="PARCEL, PROPERTY, BUILDING, FLOOR, UNIT, SURVEY")
    entity_id: str
    link_method: str = LinkMethod.MANUAL.value


class DocumentEntityLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    entity_type: str
    entity_id: str
    link_method: str
    match_score: Optional[float] = None
    match_reason: Optional[str] = None
    status: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class DocumentProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_version_id: str
    job_type: str
    status: str
    current_stage: str
    requested_by: Optional[str] = None
    parameters: Dict[str, Any] = {}
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class PropertyDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_reference: str
    document_type: str
    title: str
    description: Optional[str] = None
    status: str
    source_type: str
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    organization_id: Optional[str] = None
    jurisdiction_id: Optional[str] = None
    property_id: Optional[str] = None
    parcel_id: Optional[str] = None
    building_id: Optional[str] = None
    floor_id: Optional[str] = None
    unit_id: Optional[str] = None
    survey_id: Optional[str] = None
    current_version_id: Optional[str] = None
    page_count: int
    language: str
    document_date: Optional[datetime] = None
    issuing_authority: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: List[PropertyDocumentResponse]
    total: int
    page: int
    size: int


class DocumentDashboardMetricsResponse(BaseModel):
    total_documents: int
    processing: int
    under_review: int
    verified: int
    requires_correction: int
    rejected: int
    failed: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
