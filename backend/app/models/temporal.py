import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class SnapshotEntityType(str, Enum):
    PARCEL = "PARCEL"
    BUILDING = "BUILDING"
    FLOOR = "FLOOR"
    UNIT = "UNIT"
    PROPERTY = "PROPERTY"


class SnapshotType(str, Enum):
    OFFICIAL_RECORD = "OFFICIAL_RECORD"
    SURVEY = "SURVEY"
    REMOTE_SENSING = "REMOTE_SENSING"
    AI_DERIVED = "AI_DERIVED"
    DOCUMENT_DERIVED = "DOCUMENT_DERIVED"
    MANUAL = "MANUAL"


class DatePrecision(str, Enum):
    EXACT = "EXACT"
    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"
    UNKNOWN = "UNKNOWN"


class DetectionMethod(str, Enum):
    GEOMETRY_DIFF = "GEOMETRY_DIFF"
    ATTRIBUTE_DIFF = "ATTRIBUTE_DIFF"
    IMAGE_AI = "IMAGE_AI"
    SURVEY_COMPARISON = "SURVEY_COMPARISON"
    DOCUMENT_COMPARISON = "DOCUMENT_COMPARISON"
    COMPOSITE = "COMPOSITE"


class ChangeRunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ChangeType(str, Enum):
    BUILDING_ADDED = "BUILDING_ADDED"
    BUILDING_REMOVED = "BUILDING_REMOVED"
    BUILDING_EXPANDED = "BUILDING_EXPANDED"
    BUILDING_REDUCED = "BUILDING_REDUCED"
    BUILDING_GEOMETRY_CHANGED = "BUILDING_GEOMETRY_CHANGED"
    BUILDING_HEIGHT_CHANGED = "BUILDING_HEIGHT_CHANGED"
    BUILDING_AREA_CHANGED = "BUILDING_AREA_CHANGED"
    BUILDING_COUNT_CHANGED = "BUILDING_COUNT_CHANGED"
    FLOOR_ADDED = "FLOOR_ADDED"
    FLOOR_REMOVED = "FLOOR_REMOVED"
    FLOOR_GEOMETRY_CHANGED = "FLOOR_GEOMETRY_CHANGED"
    FLOOR_COUNT_CHANGED = "FLOOR_COUNT_CHANGED"
    UNIT_GEOMETRY_CHANGED = "UNIT_GEOMETRY_CHANGED"
    PARCEL_GEOMETRY_CHANGED = "PARCEL_GEOMETRY_CHANGED"
    PARCEL_ATTRIBUTE_CHANGED = "PARCEL_ATTRIBUTE_CHANGED"
    PROPERTY_ATTRIBUTE_CHANGED = "PROPERTY_ATTRIBUTE_CHANGED"
    SURVEY_DISCREPANCY = "SURVEY_DISCREPANCY"
    DOCUMENT_RECORD_CHANGE = "DOCUMENT_RECORD_CHANGE"
    UNKNOWN_CHANGE = "UNKNOWN_CHANGE"


class ChangeSignificance(str, Enum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    UNKNOWN = "UNKNOWN"


class CandidateStatus(str, Enum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    DISMISSED = "DISMISSED"


class ReviewReason(str, Enum):
    CONFIRMED_FIELD_SURVEY = "CONFIRMED_FIELD_SURVEY"
    CONFIRMED_PERMIT_APPROVED = "CONFIRMED_PERMIT_APPROVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    TEMPORARY_STRUCTURE = "TEMPORARY_STRUCTURE"
    DATA_ALIGNMENT_ERROR = "DATA_ALIGNMENT_ERROR"
    SURVEY_CORRECTION = "SURVEY_CORRECTION"
    DUPLICATE_DETECTION = "DUPLICATE_DETECTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    OTHER = "OTHER"


class PropertySnapshot(Base, TimestampMixin):
    """Represents a frozen temporal state of a cadastral entity at a specific point in time."""

    __tablename__ = "property_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SnapshotType.OFFICIAL_RECORD.value, index=True
    )

    # Distinct Temporal Dates (Observation vs Document vs System Creation)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    observation_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    document_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    date_precision: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DatePrecision.EXACT.value
    )

    # Provenance
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="OFFICIAL_RECORD")
    source_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Spatial Geometry
    geometry: Mapped[Optional[str]] = mapped_column(SafeGeometry("GEOMETRY", 4326), nullable=True)
    geometry_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured Snapshot Attributes
    attributes_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("ix_property_snapshots_entity_time", "entity_type", "entity_id", "effective_from"),
        Index("ix_property_snapshots_obs_date", "observation_date"),
    )


class ChangeDetectionRun(Base, TimestampMixin):
    """Tracks an asynchronous change detection job across temporal snapshots."""

    __tablename__ = "change_detection_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True, index=True)
    jurisdiction_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True, index=True)

    baseline_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    comparison_reference: Mapped[str] = mapped_column(String(128), nullable=False)

    detection_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DetectionMethod.GEOMETRY_DIFF.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ChangeRunStatus.QUEUED.value, index=True
    )

    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    ruleset_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    model_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    summary: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    requester: Mapped[Optional["User"]] = relationship("User", foreign_keys=[requested_by])
    candidates: Mapped[List["ChangeCandidate"]] = relationship(
        "ChangeCandidate", back_populates="detection_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_change_runs_status_time", "status", "created_at"),
    )


class ChangeCandidate(Base, TimestampMixin):
    """Candidate change detected between two temporal states awaiting human verification."""

    __tablename__ = "change_candidates"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    detection_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("change_detection_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    change_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True, index=True)

    baseline_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("property_snapshots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    comparison_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("property_snapshots.id", ondelete="SET NULL"), nullable=True, index=True
    )

    baseline_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    comparison_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Derived Change Geometry (e.g. Added Area / Reduced Area / Shifted Polygon)
    geometry: Mapped[Optional[str]] = mapped_column(SafeGeometry("GEOMETRY", 4326), nullable=True)
    geometry_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    baseline_geometry_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comparison_geometry_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Standardized Magnitude & Metrics
    magnitude: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    significance: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ChangeSignificance.MINOR.value, index=True
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Provenance & Cross-Phase Validation
    evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    validation_issues: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    # Human-in-the-Loop Review State
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CandidateStatus.NEW.value, index=True
    )
    review_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    detection_run: Mapped["ChangeDetectionRun"] = relationship("ChangeDetectionRun", back_populates="candidates")
    baseline_snapshot: Mapped[Optional["PropertySnapshot"]] = relationship(
        "PropertySnapshot", foreign_keys=[baseline_snapshot_id]
    )
    comparison_snapshot: Mapped[Optional["PropertySnapshot"]] = relationship(
        "PropertySnapshot", foreign_keys=[comparison_snapshot_id]
    )
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_change_candidates_entity", "entity_type", "entity_id"),
        Index("ix_change_candidates_status_sig", "status", "significance"),
    )


class RasterObservation(Base, TimestampMixin):
    """Represents aerial, satellite, or drone imagery temporal observations."""

    __tablename__ = "raster_observations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="ORTHOPHOTO", index=True)
    acquisition_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    date_precision: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DatePrecision.EXACT.value
    )
    file_reference: Mapped[str] = mapped_column(String(512), nullable=False)

    footprint: Mapped[Optional[str]] = mapped_column(SafeGeometry("GEOMETRY", 4326), nullable=True)
    footprint_wkt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    crs: Mapped[str] = mapped_column(String(32), nullable=False, default="EPSG:4326")
    resolution_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
