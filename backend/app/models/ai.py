import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.building import BuildingFootprint
    from app.models.user import User


class AIModel(Base, TimestampMixin):
    """Registered AI/ML model metadata."""
    __tablename__ = "ai_models"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    model_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="e.g. building-segmentation-v1, floor-extraction-v1",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    model_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="BUILDING_EXTRACTION, FLOOR_EXTRACTION, HEIGHT_ESTIMATION",
    )
    framework: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="PYTORCH",
        doc="PYTORCH, OPENCV, BASELINE_HEURISTIC, UNCONFIGURED",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
        doc="ACTIVE, INACTIVE, UNCONFIGURED",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    versions: Mapped[List["AIModelVersion"]] = relationship(
        "AIModelVersion",
        back_populates="model",
        cascade="all, delete-orphan",
    )


class AIModelVersion(Base, TimestampMixin):
    """Versioned model checkpoint and execution configuration."""
    __tablename__ = "ai_model_versions"
    __table_args__ = (
        UniqueConstraint("model_id", "version", name="uq_model_versions_model_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("ai_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Semantic version e.g. 1.0.0",
    )
    weights_reference: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        doc="Object storage key or relative path to weights binary",
    )
    weights_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="SHA-256 cryptographic checksum of model weights",
    )
    configuration: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    model: Mapped["AIModel"] = relationship("AIModel", back_populates="versions")


class AIProcessingJob(Base, TimestampMixin):
    """Asynchronous AI inference job lifecycle tracker."""
    __tablename__ = "ai_processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    client_request_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        doc="Client-provided idempotency token",
    )
    job_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="BUILDING_EXTRACTION, FLOOR_EXTRACTION, HEIGHT_ESTIMATION, PREPROCESSING, POSTPROCESSING, VALIDATION",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="QUEUED",
        index=True,
        doc="QUEUED, PREPROCESSING, RUNNING, POSTPROCESSING, VALIDATING, COMPLETED, FAILED, CANCELLED",
    )
    stage: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="QUEUED",
        doc="QUEUED, PREPROCESSING, RUNNING_MODEL, POSTPROCESSING, VALIDATING, COMPLETED, FAILED, CANCELLED",
    )
    progress_pct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="0, 10, 25, 50, 75, 90, 100",
    )
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="BUILDING, PARCEL, SURVEY_SESSION, SURVEY_ASSIGNMENT",
    )
    target_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    input_reference: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Input provenance: survey evidence IDs, image hashes, AOI coordinates",
    )
    model_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="building-segmentation-v1",
    )
    model_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.0.0",
    )
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="MODEL_NOT_CONFIGURED, MODEL_WEIGHTS_UNAVAILABLE, INPUT_INVALID, INFERENCE_FAILED, OUTPUT_GEOMETRY_INVALID, TIMEOUT",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    requester: Mapped[Optional["User"]] = relationship("User", foreign_keys=[requested_by])
    building_results: Mapped[List["BuildingExtractionResult"]] = relationship(
        "BuildingExtractionResult",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    floor_results: Mapped[List["FloorExtractionResult"]] = relationship(
        "FloorExtractionResult",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class BuildingExtractionResult(Base, TimestampMixin):
    """Candidate building footprint extracted by AI."""
    __tablename__ = "building_extraction_results"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("ai_processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_target_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        doc="Target Building UUID or Parcel UUID",
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("POLYGON", 4326),
        nullable=True,
    )
    geometry_wkt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    raw_geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Pre-simplification candidate polygon",
    )
    estimated_height: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Composite confidence score 0.0 - 1.0",
    )
    confidence_components: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="model_confidence, geometry_quality, source_quality",
    )
    cadastral_comparison: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="iou, area_diff_sqm, boundary_diff_m, official_area_sqm, candidate_area_sqm",
    )
    evidence_linkage: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Traceability to survey session, evidence photos, EXIF coordinates",
    )
    model_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    model_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="CANDIDATE",
        index=True,
        doc="CANDIDATE, VALIDATING, REVIEW_REQUIRED, APPROVED, REJECTED",
    )
    validation_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="VALID",
        index=True,
        doc="VALID, INVALID, WARNING",
    )
    validation_details: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("ai_reviews.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    job: Mapped["AIProcessingJob"] = relationship("AIProcessingJob", back_populates="building_results")
    review: Mapped[Optional["AIReview"]] = relationship("AIReview", foreign_keys=[review_id])


class FloorExtractionResult(Base, TimestampMixin):
    """Candidate vertical floor level produced by AI/heuristic inference."""
    __tablename__ = "floor_extraction_results"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("ai_processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_floor_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    floor_label: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    base_elevation: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    top_elevation: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=3.0,
    )
    height: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=3.0,
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("POLYGON", 4326),
        nullable=True,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="AI_EXTRACTION",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="CANDIDATE",
        index=True,
        doc="CANDIDATE, VALIDATED, REVIEW_REQUIRED, APPROVED, REJECTED",
    )
    validation_details: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("ai_reviews.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    job: Mapped["AIProcessingJob"] = relationship("AIProcessingJob", back_populates="floor_results")
    building: Mapped["BuildingFootprint"] = relationship("BuildingFootprint")
    review: Mapped[Optional["AIReview"]] = relationship("AIReview", foreign_keys=[review_id])


class AIReview(Base, TimestampMixin):
    """Human-in-the-loop review record for AI candidate geometry."""
    __tablename__ = "ai_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    result_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="BUILDING, FLOOR",
    )
    result_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="APPROVE, REJECT, MODIFY_AND_APPROVE, REQUEST_REPROCESSING",
    )
    original_geometry_wkt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    edited_geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    applied_to_cadastre: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])


class AIDataset(Base, TimestampMixin):
    """Metadata for AI development, demo, and evaluation datasets."""
    __tablename__ = "ai_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    dataset_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="e.g. geovertex-demo-val-v1",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.0.0",
    )
    dataset_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="DEVELOPMENT_DATASET",
        doc="DEVELOPMENT_DATASET, BENCHMARK, GROUND_TRUTH",
    )
    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    label_schema: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )


class AIEvaluationRun(Base, TimestampMixin):
    """Evaluation experiment run comparing model predictions against ground truth dataset."""
    __tablename__ = "ai_evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("ai_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    model_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="iou, precision, recall, f1, mean_area_error, boundary_error",
    )
    executed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    dataset: Mapped["AIDataset"] = relationship("AIDataset")
    executor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[executed_by])
