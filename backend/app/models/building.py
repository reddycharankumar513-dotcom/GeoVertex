import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.parcel import Parcel
    from app.models.user import User
    from app.models.threed import Building3DRepresentation, ThreeDAsset
    from app.models.floor import Floor
    from app.models.unit import PropertyUnit


class BuildingFootprint(Base, TimestampMixin):
    """Building footprint 2D GIS entity spatially associated with cadastral parcels."""
    __tablename__ = "buildings"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    parcel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("parcels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    building_reference: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    building_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="RESIDENTIAL",  # RESIDENTIAL, COMMERCIAL, MIXED_USE, INDUSTRIAL, PUBLIC
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="EXISTING",  # EXISTING, UNDER_CONSTRUCTION, DEMOLISHED, PLANNED
        index=True,
    )
    area: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Footprint area in square meters",
    )
    height_estimate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Height estimate in meters if available from source data",
    )
    # PostGIS Polygon / MultiPolygon in EPSG:4326
    geometry: Mapped[str] = mapped_column(
        SafeGeometry("GEOMETRY", 4326),
        nullable=False,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="WKT serialization of building footprint",
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="SURVEY",  # MANUAL, IMPORT, SURVEY, GOVERNMENT_DATA
    )
    source_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    parcel: Mapped[Optional["Parcel"]] = relationship(
        "Parcel",
        back_populates="buildings",
    )
    representation_3d: Mapped[Optional["Building3DRepresentation"]] = relationship(
        "Building3DRepresentation",
        back_populates="building",
        uselist=False,
        cascade="all, delete-orphan",
    )
    assets_3d: Mapped[List["ThreeDAsset"]] = relationship(
        "ThreeDAsset",
        back_populates="building",
        cascade="all, delete-orphan",
    )
    floors: Mapped[List["Floor"]] = relationship(
        "Floor",
        back_populates="building",
        cascade="all, delete-orphan",
        order_by="Floor.floor_number",
    )
    units: Mapped[List["PropertyUnit"]] = relationship(
        "PropertyUnit",
        back_populates="building",
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
