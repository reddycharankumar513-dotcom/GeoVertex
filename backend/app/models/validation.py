import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ValidationRun(Base, TimestampMixin):
    """Orchestration record for a deterministic topology validation run."""
    __tablename__ = "validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    validation_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        default="SINGLE_ENTITY",
        doc="SINGLE_ENTITY, PARCEL, BUILDING, FLOOR, UNIT, AI_CANDIDATE, SURVEY_SUBMISSION, CROSS_DATASET, JURISDICTION, SYSTEM",
    )
    target_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="PARCEL, BUILDING, FLOOR, UNIT, AI_RESULT, SURVEY_SUBMISSION, JURISDICTION, SYSTEM",
    )
    target_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="QUEUED",
        index=True,
        doc="QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED",
    )
    stage: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="QUEUED",
        doc="QUEUED, PREPARING_DATA, RUNNING_RULES, GENERATING_ISSUES, SUMMARIZING, COMPLETED, FAILED, CANCELLED",
    )
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    ruleset_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.0.0",
    )
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Run configuration: active rule IDs, tolerances, scope bounds",
    )
    summary: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Deterministic results summary: total_issues, critical, errors, warnings, info, resolved, open, rules_executed, entities_checked",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    requester: Mapped[Optional["User"]] = relationship("User", foreign_keys=[requested_by])
    issues: Mapped[List["ValidationIssue"]] = relationship(
        "ValidationIssue",
        back_populates="validation_run",
        cascade="all, delete-orphan",
        order_by="ValidationIssue.created_at.desc()",
    )


class ValidationIssue(Base):
    """An individual deterministic spatial or cadastral validation finding."""
    __tablename__ = "validation_issues"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("validation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="e.g. BUILDING_PARTIAL_OUTSIDE_PARCEL, FLOOR_VERTICAL_OVERLAP, GEOM_SELF_INTERSECTION",
    )
    rule_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.0.0",
    )
    issue_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Deterministic issue code (e.g. BLD-002, FLR-004)",
    )
    category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="GEOMETRY, PARCEL, BUILDING, FLOOR, UNIT, VERTICAL, CROSS_DATASET, AI, SURVEY, CRS",
    )
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="INFO, WARNING, ERROR, CRITICAL",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="OPEN",
        index=True,
        doc="OPEN, ACKNOWLEDGED, RESOLVED, WAIVED",
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="PARCEL, BUILDING, FLOOR, UNIT, AI_RESULT, SURVEY_SUBMISSION, SURVEY_OBSERVATION",
    )
    entity_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    related_entity_type: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    related_entity_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable technical summary of the validation finding",
    )
    technical_explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed topological formula and measurement analysis",
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("GEOMETRY", 4326),
        nullable=True,
        doc="Conflicting geometry slice or boundary discrepancy",
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    measured_value: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="Observed geometric/numerical measurement (e.g. 14.52 m2, 0.42 IoU)",
    )
    expected_value: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="Target cadastral standard or tolerance threshold (e.g. 0.00 m2, >= 0.85)",
    )
    tolerance: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="Applied tolerance value (e.g. 0.05 m2, 0.05 m)",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Structured calculation details: intersection_area, outside_ratio, centroid_distance, coordinates",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Resolution & Review fields
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    waived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    waived_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    waiver_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    validation_run: Mapped["ValidationRun"] = relationship("ValidationRun", back_populates="issues")
    acknowledger: Mapped[Optional["User"]] = relationship("User", foreign_keys=[acknowledged_by])
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by])
    waiver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[waived_by])
