import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, SafeGeometry, TimestampMixin

if TYPE_CHECKING:
    from app.models.jurisdiction import Jurisdiction
    from app.models.property import Property
    from app.models.building import BuildingFootprint
    from app.models.user import User


class Parcel(Base, TimestampMixin):
    """Core cadastral parcel entity storing 2D polygon boundaries and authoritative metadata."""
    __tablename__ = "parcels"
    __table_args__ = (
        UniqueConstraint("jurisdiction_id", "parcel_number", name="uq_parcels_jurisdiction_parcel_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parcel_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    parcel_code: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    survey_number: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    subdivision_number: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    land_use: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="RESIDENTIAL",  # RESIDENTIAL, COMMERCIAL, INDUSTRIAL, AGRICULTURAL, MIXED, PUBLIC, OTHER
        index=True,
    )
    area: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Authoritative geodesic area in square meters",
    )
    area_unit: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SQ_METER",
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="ACTIVE",  # ACTIVE, DRAFT, PENDING_SURVEY, RETIRED, DISPUTED
        index=True,
    )
    ownership_status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="RECORDED",  # RECORDED, MUNICIPAL, PRIVATE, GOVERNMENT, UNASSIGNED
    )
    # PostGIS Polygon / MultiPolygon in EPSG:4326
    geometry: Mapped[str] = mapped_column(
        SafeGeometry("GEOMETRY", 4326),
        nullable=False,
    )
    geometry_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="WKT serialization of parcel boundary",
    )
    centroid_lon: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    centroid_lat: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="MANUAL",  # MANUAL, IMPORT, SURVEY, GOVERNMENT_DATA, EXTERNAL_DATASET, SYSTEM_GENERATED
    )
    source_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    source_file: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    source_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
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
    jurisdiction: Mapped["Jurisdiction"] = relationship(
        "Jurisdiction",
        back_populates="parcels",
    )
    properties: Mapped[List["Property"]] = relationship(
        "Property",
        back_populates="parcel",
        cascade="all, delete-orphan",
    )
    buildings: Mapped[List["BuildingFootprint"]] = relationship(
        "BuildingFootprint",
        back_populates="parcel",
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
