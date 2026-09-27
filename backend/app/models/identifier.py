"""Phase 12 — Technical 3D Property Identifier Engine: SQLAlchemy ORM models.

IMPORTANT: GeoVertex Technical 3D Identifiers are deterministic technical system identifiers.
They are NOT official ULPINs, legal ownership identifiers, or government cadastral
registration numbers unless explicitly integrated with an authoritative external system.
"""
import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.jurisdiction import Jurisdiction
    from app.models.parcel import Parcel
    from app.models.building import BuildingFootprint
    from app.models.floor import Floor
    from app.models.unit import PropertyUnit


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierEntityType(str, enum.Enum):
    JURISDICTION = "JURISDICTION"
    PARCEL = "PARCEL"
    BUILDING = "BUILDING"
    FLOOR = "FLOOR"
    UNIT = "UNIT"


class IdentifierType(str, enum.Enum):
    JURISDICTION_ID = "JURISDICTION_ID"
    PARCEL_ID = "PARCEL_ID"
    BUILDING_ID = "BUILDING_ID"
    FLOOR_ID = "FLOOR_ID"
    UNIT_ID = "UNIT_ID"
    PROPERTY_3D_ID = "PROPERTY_3D_ID"


class IdentifierStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"
    REVOKED = "REVOKED"


class IdentifierLineageRelationship(str, enum.Enum):
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    CORRECTION = "CORRECTION"
    MIGRATION = "MIGRATION"
    REPLACEMENT = "REPLACEMENT"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ─────────────────────────────────────────────────────────────────────────────
# IdentifierScheme
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierScheme(Base, TimestampMixin):
    """Configurable scheme defining identifier structure, components, and rules.

    A scheme is the authoritative template for producing GeoVertex Technical 3D Identifiers.
    Multiple versions may coexist; only one should be active at a time for new generation.
    """
    __tablename__ = "identifier_schemes"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)

    scheme_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
        doc="Unique code for this scheme version, e.g. GV3D-V1",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structural format
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, default="GV")
    separator: Mapped[str] = mapped_column(String(4), nullable=False, default="-")

    # Component extraction patterns (regex or simple rule names)
    jurisdiction_component: Mapped[str] = mapped_column(
        String(128), nullable=False, default="strip_prefix_code",
        doc="Rule for extracting jurisdiction component from jurisdiction.code",
    )
    parcel_component: Mapped[str] = mapped_column(
        String(128), nullable=False, default="strip_prefix_code",
        doc="Rule for extracting parcel component from parcel.parcel_code",
    )
    building_component: Mapped[str] = mapped_column(
        String(128), nullable=False, default="strip_prefix_ref",
        doc="Rule for extracting building component from building.building_reference",
    )
    floor_component: Mapped[str] = mapped_column(
        String(128), nullable=False, default="strip_floor_suffix",
        doc="Rule for extracting floor component from floor.floor_code",
    )
    unit_component: Mapped[str] = mapped_column(
        String(128), nullable=False, default="strip_unit_suffix",
        doc="Rule for extracting unit component from unit.unit_code",
    )

    # Padding and format rules stored as JSON
    padding_rules: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    checksum_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    identifiers: Mapped[List["PropertyIdentifier"]] = relationship(
        "PropertyIdentifier", back_populates="scheme",
    )


# ─────────────────────────────────────────────────────────────────────────────
# PropertyIdentifier
# ─────────────────────────────────────────────────────────────────────────────

class PropertyIdentifier(Base, TimestampMixin):
    """Technical 3D Property Identifier — deterministic spatial entity identifier.

    DISCLAIMER: This is a GeoVertex Technical 3D Identifier (a deterministic
    technical system identifier). It is NOT an official ULPIN, legal ownership
    identifier, or government cadastral registration number.
    """
    __tablename__ = "property_identifiers"
    __table_args__ = (
        UniqueConstraint("identifier_value", name="uq_property_identifiers_value"),
        UniqueConstraint(
            "entity_type", "entity_id", "scheme_id", "status",
            name="uq_property_identifiers_entity_scheme_active",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)

    identifier_value: Mapped[str] = mapped_column(
        String(256), nullable=False, unique=True,
        doc="The full technical identifier string, e.g. GV-W101-P101-B001-F01-U101",
    )
    identifier_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PROPERTY_3D_ID",
        doc="IdentifierType enum value",
    )

    # Scheme reference
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("identifier_schemes.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )

    # Entity reference (polymorphic — stores entity_type + entity_id as string UUID)
    entity_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        doc="IdentifierEntityType enum value",
    )
    entity_id: Mapped[str] = mapped_column(
        String(36), nullable=False,
        doc="UUID of the spatial entity this identifier refers to",
    )

    # Hierarchy context (nullable depending on entity level)
    jurisdiction_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
        doc="Jurisdiction UUID string (not a FK to allow cross-entity flexibility)",
    )
    parcel_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    building_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    floor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    unit_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Component breakdown (for searchability and audit)
    jurisdiction_component: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parcel_component: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    building_component: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    floor_component: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    unit_component: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE",
        doc="IdentifierStatus enum value",
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Issuance
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_by: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
        doc="UUID string of user who issued/generated this identifier",
    )

    # Supersession chain
    supersedes_identifier_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
        doc="ID of old identifier that this one replaces",
    )
    superseded_by_identifier_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
        doc="ID of new identifier that supersedes this one",
    )

    # Verification token (opaque, signed)
    verification_token: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, index=True,
        doc="Opaque signed verification token for QR/public verification",
    )

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict, nullable=False,
    )

    # Relationships
    scheme: Mapped["IdentifierScheme"] = relationship("IdentifierScheme", back_populates="identifiers")


# ─────────────────────────────────────────────────────────────────────────────
# IdentifierLineage
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierLineage(Base):
    """Records lineage relationships between identifiers (split, merge, migration, etc.).

    Does NOT imply legal ownership. Purely technical provenance tracking.
    """
    __tablename__ = "identifier_lineages"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)

    source_identifier_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
        doc="UUID of source (predecessor) identifier",
    )
    target_identifier_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True,
        doc="UUID of target (successor) identifier",
    )
    relationship_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        doc="IdentifierLineageRelationship enum value",
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        nullable=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# IdentifierGenerationJob
# ─────────────────────────────────────────────────────────────────────────────

class IdentifierGenerationJob(Base, TimestampMixin):
    """Tracks bulk identifier generation jobs for authorized controlled batch issuance."""
    __tablename__ = "identifier_generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("identifier_schemes.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )

    # Scope descriptor (JSON: entity_type, filters, etc.)
    scope: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict, nullable=False,
    )

    requested_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="QUEUED",
        doc="JobStatus enum value",
    )

    # Progress counters
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflicts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_summary: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict, nullable=False,
    )
