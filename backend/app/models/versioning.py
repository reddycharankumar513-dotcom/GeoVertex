"""Phase 13 — Entity Versioning and Lineage Models.

Provides an immutable, deterministic versioning architecture for cadastral and
spatial entities across the GeoVertex platform.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin


class VersionStatus(str, enum.Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"
    REVOKED = "REVOKED"
    ARCHIVED = "ARCHIVED"
    DRAFT = "DRAFT"


class VersionChangeType(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    GEOMETRY_UPDATE = "GEOMETRY_UPDATE"
    STATUS_CHANGE = "STATUS_CHANGE"
    APPROVAL = "APPROVAL"
    REJECTION = "REJECTION"
    REVISION = "REVISION"
    SUPERSESSION = "SUPERSESSION"
    RETIREMENT = "RETIREMENT"
    REVOCATION = "REVOCATION"
    RESTORATION = "RESTORATION"
    MERGE = "MERGE"
    SPLIT = "SPLIT"
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    AI_PROPOSAL = "AI_PROPOSAL"
    SURVEY_UPDATE = "SURVEY_UPDATE"
    DOCUMENT_UPDATE = "DOCUMENT_UPDATE"
    VALIDATION_UPDATE = "VALIDATION_UPDATE"
    IDENTIFIER_ISSUED = "IDENTIFIER_ISSUED"
    IDENTIFIER_REPLACED = "IDENTIFIER_REPLACED"
    UTILITY_UPDATE = "UTILITY_UPDATE"


class VersionSourceType(str, enum.Enum):
    MANUAL = "MANUAL"
    SURVEY = "SURVEY"
    AI = "AI"
    DOCUMENT = "DOCUMENT"
    GIS_IMPORT = "GIS_IMPORT"
    SYSTEM = "SYSTEM"
    WORKFLOW = "WORKFLOW"
    ADMIN = "ADMIN"
    EXTERNAL_INTEGRATION = "EXTERNAL_INTEGRATION"


class LineageRelationship(str, enum.Enum):
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    REPLACEMENT = "REPLACEMENT"
    CORRECTION = "CORRECTION"
    MIGRATION = "MIGRATION"
    RESTORATION = "RESTORATION"


class EntityVersion(Base, TimestampMixin):
    """Immutable snapshot of a spatial or cadastral entity at a specific point in time."""
    __tablename__ = "entity_versions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Entity type e.g. PARCEL, PROPERTY, BUILDING, FLOOR, UNIT, SURVEY_SUBMISSION",
    )
    entity_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Primary UUID string of the entity",
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Deterministic monotonically increasing version counter (1, 2, 3...)",
    )
    version_uuid: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
        doc="Unique reference identifier for this specific version instance",
    )
    version_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VersionStatus.CURRENT.value,
        index=True,
    )

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
        index=True,
        doc="Actor user ID who triggered this version creation",
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    effective_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    change_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VersionChangeType.UPDATE.value,
        doc="Standardized change type enum value",
    )
    change_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Required human or system rationale for this modification",
    )

    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VersionSourceType.SYSTEM.value,
        doc="Provenance source type",
    )
    source_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="Reference ID of originating survey, AI job, document, or case",
    )

    # Lineage links within versions
    parent_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
        doc="Direct predecessor version ID",
    )
    supersedes_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
    )
    superseded_by_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
    )

    # Complete reconstructable state
    snapshot_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Full scalar and relational attributes captured at this version",
    )

    # Geometry preservation
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="WKT representation of entity geometry at this version",
    )
    geometry_srid: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=4326,
        nullable=True,
    )
    geometry_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    geometry_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="SHA-256 hash of canonical geometry WKT",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="SHA-256 hash of canonical snapshot payload",
    )

    # Deterministic spatial metrics
    geometry_metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Calculated metrics: area, perimeter, centroid, bounding_box",
    )

    # Contextual references
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        nullable=True,
        index=True,
    )
    case_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    review_status: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "version_number", name="uq_entity_version_number"),
    )


class EntityLineage(Base, TimestampMixin):
    """Tracks split, merge, replacement, correction, and migration across entities."""
    __tablename__ = "entity_lineages"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    source_entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)

    target_entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)

    relationship_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=LineageRelationship.REPLACEMENT.value,
        index=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
