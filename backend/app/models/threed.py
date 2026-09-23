import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.models.building import BuildingFootprint
    from app.models.user import User


class Building3DRepresentation(Base, TimestampMixin):
    """Authoritative 3D representation and vertical spatial metadata for a building footprint.
    
    In Phase 3, this model maintains the 2.5D extrusion parameters (height, base elevation,
    vertical datum, and quality metrics) derived from Phase 2 building footprints.
    """
    __tablename__ = "building_3d_representations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("buildings.id", ondelete="CASCADE", name="fk_building_3d_building"),
        nullable=False,
        unique=True,
        index=True,
    )
    geometry_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="EXTRUSION",  # EXTRUSION, LOD1, LOD2, MESH
        index=True,
    )
    height: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=12.0,
        doc="Building height in specified height_unit (default meters, non-negative)",
    )
    height_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="ESTIMATED",  # MANUAL, SURVEY, GOVERNMENT_DATA, IMPORT, ESTIMATED, SYSTEM_GENERATED
        index=True,
    )
    height_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score between 0.0 and 1.0",
    )
    height_unit: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="METERS",
    )
    base_elevation: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Base ground elevation in meters relative to vertical_reference",
    )
    elevation_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="LOCAL_REFERENCE_PLANE",  # TERRAIN, SURVEY, MANUAL, DATASET, LOCAL_REFERENCE_PLANE, UNKNOWN
    )
    vertical_reference: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="METERS_ABOVE_GROUND",  # WGS84_ELLIPSOID, EGM96_GEOID, LOCAL_GROUND, METERS_ABOVE_GROUND
    )
    model_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="EXTRUDED_FOOTPRINT",
    )
    model_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",  # ACTIVE, SUPERSEDED, DRAFT
        index=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_building_3d_created_by"),
        nullable=True,
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_building_3d_updated_by"),
        nullable=True,
    )

    # Relationships
    building: Mapped["BuildingFootprint"] = relationship(
        "BuildingFootprint",
        back_populates="representation_3d",
    )
    assets: Mapped[List["ThreeDAsset"]] = relationship(
        "ThreeDAsset",
        back_populates="representation",
        cascade="all, delete-orphan",
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    updater: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
    )


class ThreeDAsset(Base, TimestampMixin):
    """Asset management entity for 3D geospatial payloads, geometry caches, and future 3D tile sets."""
    __tablename__ = "threed_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    building_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("buildings.id", ondelete="CASCADE", name="fk_threed_assets_building"),
        nullable=True,
        index=True,
    )
    representation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("building_3d_representations.id", ondelete="CASCADE", name="fk_threed_assets_representation"),
        nullable=True,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="EXTRUSION",  # EXTRUSION, GLTF, GLB, B3DM, TILES, IFC, CITYGML
        index=True,
    )
    storage_location: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        default="virtual://extrusions",
        doc="Internal storage key, URI, or virtual asset identifier",
    )
    format: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="JSON_EXTRUSION",  # JSON_EXTRUSION, GLTF_BINARY, B3DM, 3DTILES_JSON
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",  # ACTIVE, PROCESSING, ARCHIVED
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="SYSTEM_GENERATED",
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON serialization of 3D asset metadata, dimensions, and LOD settings",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_threed_assets_created_by"),
        nullable=True,
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_threed_assets_updated_by"),
        nullable=True,
    )

    # Relationships
    building: Mapped[Optional["BuildingFootprint"]] = relationship(
        "BuildingFootprint",
        back_populates="assets_3d",
    )
    representation: Mapped[Optional["Building3DRepresentation"]] = relationship(
        "Building3DRepresentation",
        back_populates="assets",
    )
