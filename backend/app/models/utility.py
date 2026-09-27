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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.jurisdiction import Jurisdiction
    from app.models.parcel import Parcel
    from app.models.building import BuildingFootprint
    from app.models.user import User


class UtilityType(str, Enum):
    WATER = "WATER"
    SEWER = "SEWER"
    STORMWATER = "STORMWATER"
    GAS = "GAS"
    ELECTRICITY = "ELECTRICITY"
    TELECOM = "TELECOM"
    FIBER = "FIBER"
    DRAINAGE = "DRAINAGE"
    OTHER = "OTHER"


class UtilityAssetType(str, Enum):
    PIPE = "PIPE"
    CABLE = "CABLE"
    DUCT = "DUCT"
    CONDUIT = "CONDUIT"
    MANHOLE = "MANHOLE"
    VALVE = "VALVE"
    METER = "METER"
    TRANSFORMER = "TRANSFORMER"
    POLE_BASE = "POLE_BASE"
    CHAMBER = "CHAMBER"
    HANDHOLE = "HANDHOLE"
    DRAIN = "DRAIN"
    CULVERT = "CULVERT"
    PUMP = "PUMP"
    TANK = "TANK"
    UTILITY_STRUCTURE = "UTILITY_STRUCTURE"
    OTHER = "OTHER"


class UtilityStatus(str, Enum):
    PLANNED = "PLANNED"
    PROPOSED = "PROPOSED"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ABANDONED = "ABANDONED"
    REMOVED = "REMOVED"
    UNKNOWN = "UNKNOWN"


class ElevationReference(str, Enum):
    GROUND_RELATIVE = "GROUND_RELATIVE"
    LOCAL_MSL = "LOCAL_MSL"
    WGS84_ELLIPSOID = "WGS84_ELLIPSOID"
    EGM96_GEOID = "EGM96_GEOID"


class UtilitySourceType(str, Enum):
    OFFICIAL_RECORD = "OFFICIAL_RECORD"
    SURVEY = "SURVEY"
    DOCUMENT = "DOCUMENT"
    AI_CANDIDATE = "AI_CANDIDATE"
    MANUAL = "MANUAL"
    REMOTE_SENSING = "REMOTE_SENSING"
    OTHER = "OTHER"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class FlowDirection(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    INFERRED = "INFERRED"


class ClashSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ClashStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    WAIVED = "WAIVED"


class UtilityReviewStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"


class UtilityNetwork(Base, TimestampMixin):
    """Subsurface utility network grouping contiguous functional assets."""
    __tablename__ = "utility_networks"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    utility_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="WATER",
        index=True,
    )
    owner_organization: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    operator_organization: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="OFFICIAL_RECORD",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    jurisdiction: Mapped["Jurisdiction"] = relationship("Jurisdiction")
    assets: Mapped[List["UtilityAsset"]] = relationship(
        "UtilityAsset",
        back_populates="network",
        cascade="all, delete-orphan",
    )
    nodes: Mapped[List["UtilityNode"]] = relationship(
        "UtilityNode",
        back_populates="network",
        cascade="all, delete-orphan",
    )


class UtilityAsset(Base, TimestampMixin):
    """Generic underground infrastructure asset."""
    __tablename__ = "utility_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    network_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("utility_networks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="PIPE",
        index=True,
    )
    asset_reference: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
    )
    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="CANDIDATE",
        index=True,
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("GEOMETRY", 4326),
        nullable=True,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    geometry_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="LINESTRING",
        index=True,
    )
    elevation_reference: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="GROUND_RELATIVE",
    )
    depth: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        index=True,
        doc="Depth in meters below ground. NULL indicates UNKNOWN.",
    )
    depth_min: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    depth_max: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    ground_elevation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    centerline_elevation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    material: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    diameter: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Nominal diameter in meters",
    )
    width: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Width/dimension in meters",
    )
    capacity: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    installation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    commissioning_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="OFFICIAL_RECORD",
        index=True,
    )
    source_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    confidence: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="MEDIUM",
        index=True,
    )
    parcel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("parcels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    building_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("buildings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    network: Mapped["UtilityNetwork"] = relationship("UtilityNetwork", back_populates="assets")
    parcel: Mapped[Optional["Parcel"]] = relationship("Parcel")
    building: Mapped[Optional["BuildingFootprint"]] = relationship("BuildingFootprint")
    segment: Mapped[Optional["UtilitySegment"]] = relationship(
        "UtilitySegment",
        back_populates="asset",
        uselist=False,
        cascade="all, delete-orphan",
    )
    structures: Mapped[List["UtilityStructure"]] = relationship(
        "UtilityStructure",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    inspections: Mapped[List["UtilityInspection"]] = relationship(
        "UtilityInspection",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    maintenance_events: Mapped[List["UtilityMaintenanceEvent"]] = relationship(
        "UtilityMaintenanceEvent",
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class UtilitySegment(Base, TimestampMixin):
    """Linear asset representation connecting start and end nodes."""
    __tablename__ = "utility_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    utility_asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("utility_assets.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    start_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("utility_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    end_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("utility_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("LINESTRING", 4326),
        nullable=True,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    length_meters: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    depth_start: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    depth_end: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    elevation_start: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    elevation_end: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    slope_percentage: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    flow_direction: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="UNKNOWN",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
    )

    # Relationships
    asset: Mapped["UtilityAsset"] = relationship("UtilityAsset", back_populates="segment")
    start_node: Mapped[Optional["UtilityNode"]] = relationship("UtilityNode", foreign_keys=[start_node_id])
    end_node: Mapped[Optional["UtilityNode"]] = relationship("UtilityNode", foreign_keys=[end_node_id])


class UtilityNode(Base, TimestampMixin):
    """Point connection node (manhole, valve, junction, transformer, access point)."""
    __tablename__ = "utility_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    network_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("utility_networks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="JUNCTION",
        index=True,
    )
    asset_reference: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("POINT", 4326),
        nullable=True,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    elevation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    depth: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="OFFICIAL_RECORD",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    network: Mapped["UtilityNetwork"] = relationship("UtilityNetwork", back_populates="nodes")


class UtilityStructure(Base, TimestampMixin):
    """Vertical or subterranean enclosure asset (vault, chamber, duct bank)."""
    __tablename__ = "utility_structures"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    utility_asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("utility_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    structure_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="VAULT",
        index=True,
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("GEOMETRY", 4326),
        nullable=True,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    top_elevation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    bottom_elevation: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    depth: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    width_m: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    length_m: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    height_m: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="OFFICIAL_RECORD",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    asset: Mapped["UtilityAsset"] = relationship("UtilityAsset", back_populates="structures")


class UtilityCorridor(Base, TimestampMixin):
    """Designated multi-utility easement or right-of-way corridor."""
    __tablename__ = "utility_corridors"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    corridor_reference: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    geometry: Mapped[Optional[str]] = mapped_column(
        SafeGeometry("GEOMETRY", 4326),
        nullable=True,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    width_meters: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5.0,
    )
    depth_range_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    utility_types: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="OFFICIAL_RECORD",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
    )


class UtilitySeparationRule(Base, TimestampMixin):
    """Configurable engineering horizontal/vertical separation requirements between utility types."""
    __tablename__ = "utility_separation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    rule_code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    utility_type_a: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    utility_type_b: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    required_horizontal_separation_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    required_vertical_separation_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.3,
    )
    jurisdiction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="MUNICIPAL_STANDARD",
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.0",
    )
    effective_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
    )


class UtilityClash(Base, TimestampMixin):
    """Spatial 3D clash between two underground assets or asset and building."""
    __tablename__ = "utility_clashes"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    asset_a_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("utility_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_b_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("utility_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    horizontal_relationship: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="CROSSING",
    )
    vertical_relationship: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="INSUFFICIENT_CLEARANCE",
    )
    measured_horizontal_separation_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    measured_vertical_separation_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    required_horizontal_separation_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    required_vertical_separation_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.3,
    )
    clash_geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ERROR",
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="OPEN",
        index=True,
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    asset_a: Mapped["UtilityAsset"] = relationship("UtilityAsset", foreign_keys=[asset_a_id])
    asset_b: Mapped["UtilityAsset"] = relationship("UtilityAsset", foreign_keys=[asset_b_id])
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by])


class UtilityInspection(Base, TimestampMixin):
    """Field inspection record for a utility asset."""
    __tablename__ = "utility_inspections"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    utility_asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("utility_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inspection_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    inspector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    condition: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="GOOD",
    )
    depth_measurement: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    observations: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    evidence_references: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PASS",
    )

    # Relationships
    asset: Mapped["UtilityAsset"] = relationship("UtilityAsset", back_populates="inspections")
    inspector: Mapped[Optional["User"]] = relationship("User", foreign_keys=[inspector_id])


class UtilityMaintenanceEvent(Base, TimestampMixin):
    """Historical maintenance log for a utility asset."""
    __tablename__ = "utility_maintenance_events"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    utility_asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("utility_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="INSPECTION",
        index=True,
    )
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence_references: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    asset: Mapped["UtilityAsset"] = relationship("UtilityAsset", back_populates="maintenance_events")
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[performed_by])


class SubsurfaceObservation(Base, TimestampMixin):
    """Subsurface sensor, GPR, or borehole empirical observation record."""
    __tablename__ = "subsurface_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    source_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="GPR",
        index=True,
    )
    acquisition_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    depth_meters: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    signal_reference: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    processing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="RAW",
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
