import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.jurisdiction import Jurisdiction
    from app.models.user import User
    from app.models.parcel import Parcel
    from app.models.property import Property
    from app.models.building import BuildingFootprint
    from app.models.floor import Floor
    from app.models.unit import PropertyUnit


class SurveyProject(Base, TimestampMixin):
    """Survey project grouping related field data collection assignments."""
    __tablename__ = "survey_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="Systematic survey project code, e.g. PRJ-W101-2026-01",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="DRAFT",  # DRAFT, ACTIVE, PAUSED, COMPLETED, CANCELLED
        index=True,
    )
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    jurisdiction: Mapped["Jurisdiction"] = relationship("Jurisdiction")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    assignments: Mapped[List["SurveyAssignment"]] = relationship(
        "SurveyAssignment",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class SurveyAssignment(Base, TimestampMixin):
    """Specific field collection task assigned to a licensed surveyor."""
    __tablename__ = "survey_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    survey_project_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("survey_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    surveyor_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parcel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("parcels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    building_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("buildings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    floor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("floors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("property_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="MEDIUM",  # LOW, MEDIUM, HIGH, URGENT
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ASSIGNED",  # ASSIGNED, ACCEPTED, IN_PROGRESS, SUBMITTED, UNDER_REVIEW, REVISION_REQUIRED, APPROVED, REJECTED, CANCELLED
        index=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
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
    due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    project: Mapped["SurveyProject"] = relationship("SurveyProject", back_populates="assignments")
    surveyor: Mapped["User"] = relationship("User", foreign_keys=[surveyor_id])
    jurisdiction: Mapped["Jurisdiction"] = relationship("Jurisdiction")
    parcel: Mapped[Optional["Parcel"]] = relationship("Parcel")
    property: Mapped[Optional["Property"]] = relationship("Property")
    building: Mapped[Optional["BuildingFootprint"]] = relationship("BuildingFootprint")
    floor: Mapped[Optional["Floor"]] = relationship("Floor")
    unit: Mapped[Optional["PropertyUnit"]] = relationship("PropertyUnit")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    sessions: Mapped[List["SurveySession"]] = relationship(
        "SurveySession",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[List["SurveySubmission"]] = relationship(
        "SurveySubmission",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class SurveySession(Base, TimestampMixin):
    """An active or completed field data collection session by a surveyor."""
    __tablename__ = "survey_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("survey_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    surveyor_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="DRAFT",  # DRAFT, ACTIVE, PAUSED, COMPLETED, SYNC_PENDING, SYNCED, SUBMITTED
        index=True,
    )
    device_identifier: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    app_version: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        default="1.0.0",
    )
    sync_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SYNCED",  # SYNCED, PENDING, CONFLICT
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    assignment: Mapped["SurveyAssignment"] = relationship("SurveyAssignment", back_populates="sessions")
    surveyor: Mapped["User"] = relationship("User", foreign_keys=[surveyor_id])
    observations: Mapped[List["SurveyObservation"]] = relationship(
        "SurveyObservation",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    evidence: Mapped[List["SurveyEvidence"]] = relationship(
        "SurveyEvidence",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[List["SurveySubmission"]] = relationship(
        "SurveySubmission",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class SurveyObservation(Base, TimestampMixin):
    """Discrete geospatial or architectural measurement captured during a survey session."""
    __tablename__ = "survey_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("survey_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="BUILDING_HEIGHT, FLOOR_COUNT, FLOOR_HEIGHT, UNIT_AREA, PARCEL_BOUNDARY, BUILDING_BOUNDARY, etc.",
    )
    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="PARCEL, PROPERTY, BUILDING, FLOOR, UNIT, SURVEY_SESSION",
    )
    target_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Observed value, e.g. '14.5', '4', 'RESIDENTIAL'",
    )
    unit: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        doc="Measurement unit, e.g. 'm', 'sq_m', 'count'",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    captured_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    latitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    longitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    horizontal_accuracy: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Reported horizontal positioning accuracy in meters (e.g. 4.8)",
    )
    altitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    vertical_accuracy: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="FIELD_OBSERVATION",  # FIELD_OBSERVATION, DEVICE_GPS, GNSS, MANUAL_MEASUREMENT, PHOTO, EXISTING_CADASTRAL_DATA, IMPORTED_DATA
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("GEOMETRY", 4326),
        nullable=True,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    session: Mapped["SurveySession"] = relationship("SurveySession", back_populates="observations")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[captured_by])
    evidence: Mapped[List["SurveyEvidence"]] = relationship(
        "SurveyEvidence",
        back_populates="observation",
    )


class SurveyEvidence(Base, TimestampMixin):
    """Cryptographically hashed photo or document evidence captured during a survey session."""
    __tablename__ = "survey_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("survey_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("survey_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="BUILDING",
    )
    target_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Internal relative storage path / object key in object storage",
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="image/jpeg",
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="BUILDING_FRONT",  # BUILDING_FRONT, BUILDING_SIDE, PARCEL_MARKER, UNIT, FLOOR, ADDRESS, DOCUMENT, GENERAL, OTHER
        index=True,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    latitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    longitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    accuracy: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="SHA-256 cryptographic digest of the file for content integrity & duplicate detection",
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    session: Mapped["SurveySession"] = relationship("SurveySession", back_populates="evidence")
    observation: Mapped[Optional["SurveyObservation"]] = relationship("SurveyObservation", back_populates="evidence")
    uploader: Mapped[Optional["User"]] = relationship("User", foreign_keys=[uploaded_by])


class SurveySubmission(Base, TimestampMixin):
    """Immutable versioned submission snapshot of a survey session submitted for officer review."""
    __tablename__ = "survey_submissions"
    __table_args__ = (
        UniqueConstraint("survey_session_id", "version_number", name="uq_submissions_session_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("survey_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    survey_session_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("survey_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SUBMITTED",  # SUBMITTED, UNDER_REVIEW, APPROVED, REVISION_REQUIRED, REJECTED
        index=True,
    )
    snapshot_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Immutable JSON snapshot of observations, measurements, coordinates, and evidence references",
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    assignment: Mapped["SurveyAssignment"] = relationship("SurveyAssignment", back_populates="submissions")
    session: Mapped["SurveySession"] = relationship("SurveySession", back_populates="submissions")
    submitter: Mapped["User"] = relationship("User", foreign_keys=[submitted_by])
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])


class SyncOperation(Base, TimestampMixin):
    """Synchronization queue item for offline field data mutations with idempotency."""
    __tablename__ = "sync_operations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    client_operation_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        doc="Client-generated unique ID for idempotency deduplication",
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("survey_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    operation_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="CREATE_OBSERVATION, UPDATE_OBSERVATION, ATTACH_EVIDENCE, UPDATE_SESSION",
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    entity_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Serialized JSON payload of mutation",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",  # PENDING, SYNCING, SYNCED, CONFLICT, FAILED
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
