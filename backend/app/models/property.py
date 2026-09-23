import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.models.parcel import Parcel
    from app.models.user import User
    from app.models.unit import PropertyUnit


class Property(Base, TimestampMixin):
    """Property record associated with a cadastral parcel."""
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("parcels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_reference: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )
    property_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="FREEHOLD",  # FREEHOLD, LEASEHOLD, MUNICIPAL, RESIDENTIAL, COMMERCIAL, INDUSTRIAL
    )
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="ACTIVE",  # ACTIVE, REGISTERED, PENDING, INACTIVE
        index=True,
    )
    address: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    locality: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    postal_code: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
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
    parcel: Mapped["Parcel"] = relationship(
        "Parcel",
        back_populates="properties",
    )
    units: Mapped[List["PropertyUnit"]] = relationship(
        "PropertyUnit",
        back_populates="property",
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    updater: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by],
    )
