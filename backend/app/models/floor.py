import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.building import BuildingFootprint
    from app.models.unit import PropertyUnit
    from app.models.user import User


class Floor(Base, TimestampMixin):
    """Floor slab vertical cadastral structure within a building."""
    __tablename__ = "floors"
    __table_args__ = (
        UniqueConstraint("building_id", "floor_number", name="uq_floors_building_floor_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    floor_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        doc="0 for Ground, positive for upper floors (1, 2, 3...), negative for basements (-1, -2)",
    )
    floor_code: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        doc="Systematic identifier, e.g. BLD-W101-001-F0",
    )
    floor_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        doc="Descriptive name, e.g. Ground Floor, Level 1, Penthouse",
    )
    floor_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="RESIDENTIAL",  # RESIDENTIAL, COMMERCIAL, PARKING, MIXED_USE, SERVICE, ROOFTOP
        index=True,
    )
    elevation_min_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Lower elevation bound in meters above local base plane/datum",
    )
    elevation_max_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=3.0,
        doc="Upper elevation bound in meters above local base plane/datum",
    )
    height_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=3.0,
        doc="Floor slab vertical thickness (elevation_max_m - elevation_min_m)",
    )
    area_sqm: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Gross floor slab area in square meters",
    )
    geometry: Mapped[str] = mapped_column(
        SafeGeometry("POLYGON", 4326),
        nullable=False,
        doc="Horizontal floor boundary polygon in EPSG:4326",
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="WKT serialization of floor boundary",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        doc="Measurement confidence score between 0.0 and 1.0",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",  # ACTIVE, PLANNED, UNDER_CONSTRUCTION, DEMOLISHED
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="SURVEY",  # SURVEY, ARCHITECTURAL_PLAN, MANUAL, SYSTEM_GENERATED
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
    building: Mapped["BuildingFootprint"] = relationship(
        "BuildingFootprint",
        back_populates="floors",
    )
    units: Mapped[List["PropertyUnit"]] = relationship(
        "PropertyUnit",
        back_populates="floor",
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
