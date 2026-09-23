import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator
from geoalchemy2 import Geometry
from app.database.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.parcel import Parcel


class SafeMultiPolygon(TypeDecorator):
    """Platform-independent MultiPolygon spatial type.
    Uses PostGIS Geometry('MULTIPOLYGON', 4326) on PostgreSQL.
    Falls back to Text on SQLite without requiring spatialite DLLs.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


class Jurisdiction(Base, TimestampMixin):
    """Defines an administrative territory (e.g. Ward, Tehsil, District) governing cadastral parcels."""
    __tablename__ = "jurisdictions"

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
    parent_jurisdiction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="SET NULL"),
        nullable=True,
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
    )
    level: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="WARD",  # COUNTRY, STATE, DISTRICT, MUNICIPALITY, CITY, WARD, VILLAGE, ZONE, OTHER
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    srid: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4326,
    )
    # PostGIS MultiPolygon boundary
    boundary: Mapped[Optional[str]] = mapped_column(
        SafeMultiPolygon,
        nullable=True,
    )
    boundary_wkt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="WKT serialization of administrative boundary",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    @property
    def type(self) -> str:
        return self.level

    @property
    def status(self) -> str:
        return "ACTIVE" if self.is_active else "INACTIVE"

    @property
    def default_crs(self) -> str:
        return f"EPSG:{self.srid}"

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="jurisdictions",
    )
    parent: Mapped[Optional["Jurisdiction"]] = relationship(
        "Jurisdiction",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[List["Jurisdiction"]] = relationship(
        "Jurisdiction",
        back_populates="parent",
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="jurisdiction",
    )
    parcels: Mapped[List["Parcel"]] = relationship(
        "Parcel",
        back_populates="jurisdiction",
        cascade="all, delete-orphan",
    )
