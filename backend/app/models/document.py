from datetime import datetime, timezone
import enum
import uuid
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    BigInteger,
    Float,
    ForeignKey,
    JSON,
    Enum,
    Index,
)
from sqlalchemy.orm import relationship
from app.database.base import Base


class DocumentType(str, enum.Enum):
    SALE_DEED = "SALE_DEED"
    TITLE_DOCUMENT = "TITLE_DOCUMENT"
    PROPERTY_TAX_RECORD = "PROPERTY_TAX_RECORD"
    PROPERTY_REGISTRATION = "PROPERTY_REGISTRATION"
    BUILDING_PLAN = "BUILDING_PLAN"
    FLOOR_PLAN = "FLOOR_PLAN"
    APPROVAL_DOCUMENT = "APPROVAL_DOCUMENT"
    OCCUPANCY_DOCUMENT = "OCCUPANCY_DOCUMENT"
    SURVEY_DOCUMENT = "SURVEY_DOCUMENT"
    LAND_RECORD = "LAND_RECORD"
    ENCUMBRANCE_RECORD = "ENCUMBRANCE_RECORD"
    UTILITY_DOCUMENT = "UTILITY_DOCUMENT"
    IDENTITY_SUPPORTING_DOCUMENT = "IDENTITY_SUPPORTING_DOCUMENT"
    OTHER = "OTHER"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    OCR_COMPLETED = "OCR_COMPLETED"
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REQUIRES_CORRECTION = "REQUIRES_CORRECTION"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


class FieldReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class LinkMethod(str, enum.Enum):
    MANUAL = "MANUAL"
    RULE_BASED = "RULE_BASED"
    AI_SUGGESTED = "AI_SUGGESTED"


class PropertyDocument(Base):
    __tablename__ = "property_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_reference = Column(String(100), unique=True, nullable=False, index=True)
    document_type = Column(String(50), nullable=False, default=DocumentType.OTHER.value, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default=DocumentStatus.UPLOADED.value, index=True)
    source_type = Column(String(50), nullable=False, default="MANUAL_UPLOAD")

    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="SET NULL"), nullable=True, index=True)

    # Core cadastral spatial entity associations
    property_id = Column(String(36), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)
    parcel_id = Column(String(36), ForeignKey("parcels.id", ondelete="SET NULL"), nullable=True, index=True)
    building_id = Column(String(36), ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True)
    floor_id = Column(String(36), ForeignKey("floors.id", ondelete="SET NULL"), nullable=True, index=True)
    unit_id = Column(String(36), ForeignKey("property_units.id", ondelete="SET NULL"), nullable=True, index=True)
    survey_id = Column(String(36), nullable=True, index=True)

    current_version_id = Column(String(36), nullable=True)
    page_count = Column(Integer, default=0, nullable=False)
    language = Column(String(20), default="en", nullable=False)
    document_date = Column(DateTime(timezone=True), nullable=True)
    issuing_authority = Column(String(255), nullable=True)

    metadata_json = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", foreign_keys="[DocumentVersion.document_id]")
    entity_links = relationship("DocumentEntityLink", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("property_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)
    storage_key = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    page_count = Column(Integer, default=0, nullable=False)

    uploaded_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    processing_status = Column(String(50), default="PENDING", nullable=False)
    source_notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    document = relationship("PropertyDocument", back_populates="versions", foreign_keys=[document_id])
    pages = relationship("DocumentPage", back_populates="version", cascade="all, delete-orphan")
    ocr_results = relationship("DocumentOCRResult", back_populates="version", cascade="all, delete-orphan")
    extracted_fields = relationship("DocumentExtractedField", back_populates="version", cascade="all, delete-orphan")
    processing_jobs = relationship("DocumentProcessingJob", back_populates="version", cascade="all, delete-orphan")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    image_reference = Column(String(500), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    rotation = Column(Integer, default=0, nullable=False)
    processing_status = Column(String(50), default="PENDING", nullable=False)
    extracted_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    version = relationship("DocumentVersion", back_populates="pages")
    ocr_results = relationship("DocumentOCRResult", back_populates="page", cascade="all, delete-orphan")


class DocumentOCRResult(Base):
    __tablename__ = "document_ocr_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id = Column(String(36), ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=True, index=True)
    engine = Column(String(100), nullable=False)
    engine_version = Column(String(50), nullable=True)
    language = Column(String(20), default="en", nullable=False)
    text = Column(Text, nullable=False)
    blocks_json = Column(JSON, default=list, nullable=False)
    confidence = Column(Float, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    version = relationship("DocumentVersion", back_populates="ocr_results")
    page = relationship("DocumentPage", back_populates="ocr_results")


class DocumentExtractedField(Base):
    __tablename__ = "document_extracted_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    field_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=True)
    data_type = Column(String(50), default="STRING", nullable=False)
    page_number = Column(Integer, nullable=True)
    bounding_box = Column(JSON, nullable=True)
    extraction_method = Column(String(50), default="RULE_BASED", nullable=False)
    confidence = Column(Float, nullable=True)
    confidence_level = Column(String(20), default=ConfidenceLevel.UNKNOWN.value, nullable=False)
    evidence_text = Column(Text, nullable=True)
    model_id = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)

    # Human Review Workflow
    review_status = Column(String(50), default=FieldReviewStatus.PENDING.value, nullable=False)
    reviewed_value = Column(Text, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    version = relationship("DocumentVersion", back_populates="extracted_fields")


class DocumentProcessingJob(Base):
    __tablename__ = "document_processing_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(50), default="FULL_PIPELINE", nullable=False)
    status = Column(String(50), default="QUEUED", nullable=False, index=True)
    current_stage = Column(String(50), default="QUEUED", nullable=False)
    requested_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    parameters = Column(JSON, default=dict, nullable=False)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    version = relationship("DocumentVersion", back_populates="processing_jobs")


class DocumentEntityLink(Base):
    __tablename__ = "document_entity_links"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("property_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # PARCEL, PROPERTY, BUILDING, FLOOR, UNIT, SURVEY
    entity_id = Column(String(36), nullable=False, index=True)
    link_method = Column(String(50), default=LinkMethod.MANUAL.value, nullable=False)
    match_score = Column(Float, nullable=True)
    match_reason = Column(Text, nullable=True)
    status = Column(String(50), default="CONFIRMED", nullable=False)  # CANDIDATE, CONFIRMED, REJECTED
    confirmed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("PropertyDocument", back_populates="entity_links")


# Create composite indices
Index("idx_doc_jurisdiction_status", PropertyDocument.jurisdiction_id, PropertyDocument.status)
Index("idx_doc_parcel", PropertyDocument.parcel_id)
Index("idx_doc_property", PropertyDocument.property_id)
Index("idx_doc_version_hash", DocumentVersion.file_hash)
Index("idx_doc_fields_name", DocumentExtractedField.document_version_id, DocumentExtractedField.field_name)
Index("idx_doc_link_entity", DocumentEntityLink.entity_type, DocumentEntityLink.entity_id)
