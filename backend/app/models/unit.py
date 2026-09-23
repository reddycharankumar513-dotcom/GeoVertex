import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.building import BuildingFootprint
    from app.models.floor import Floor
    from app.models.property import Property
    from app.models.user import User


class PropertyUnit(Base, TimestampMixin):
    """Property unit spatial entity within a floor slab, optionally linked to a legal property title."""
    __tablename__ = "property_units"
    __table_args__ = (
        UniqueConstraint("floor_id", "unit_number", name="uq_units_floor_unit_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    floor_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("floors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional link to a legal cadastral property record",
    )
    unit_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Unit number / designation, e.g. 101, 102, 204B, PH-1",
    )
    unit_code: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        doc="Systematic identifier, e.g. BLD-W101-001-F1-U101",
    )
    unit_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="APARTMENT",  # APARTMENT, OFFICE, RETAIL, PARKING_BAY, STORAGE, COMMON_AREA
        index=True,
    )
    gross_area_sqm: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Gross unit boundary footprint area in square meters",
    )
    net_area_sqm: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Net usable / carpet area in square meters",
    )
    elevation_min_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Lower elevation bound of unit in meters above local base plane",
    )
    elevation_max_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=3.0,
        doc="Upper elevation bound of unit in meters above local base plane",
    )
    height_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=3.0,
        doc="Vertical unit clearance height (elevation_max_m - elevation_min_m)",
    )
    geometry: Mapped[str] = mapped_column(
        SafeGeometry("POLYGON", 4326),
        nullable=False,
        doc="Horizontal unit footprint boundary polygon in EPSG:4326",
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="WKT serialization of unit boundary",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",  # ACTIVE, OCCUPIED, VACANT, UNDER_CONSTRUCTION, PENDING_REVIEW
        index=True,
    )
    ownership_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="PRIVATE",  # PRIVATE, COMMON_PROPERTY, STATE, MUNICIPAL, UNASSIGNED
        index=True,
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
    floor: Mapped["Floor"] = relationship(
        "Floor",
        back_populates="units",
    )
    building: Mapped["BuildingFootprint"] = relationship(
        "BuildingFootprint",
        back_populates="units",
    )
    property: Mapped[Optional["Property"]] = relationship(
        "Property",
        back_populates="units",
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    updater: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
    )
