import enum
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.jurisdiction import Jurisdiction
    from app.models.token import RefreshToken
    from app.models.audit import AuditEvent


class UserRole(str, enum.Enum):
    CITIZEN = "CITIZEN"
    SURVEYOR = "SURVEYOR"
    GOVERNMENT_OFFICER = "GOVERNMENT_OFFICER"
    ADMIN = "ADMIN"
    URBAN_PLANNER = "URBAN_PLANNER"


class User(Base, TimestampMixin):
    """User account entity across Citizen, Surveyor, Officer, and Admin tiers."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=UserRole.CITIZEN.value,
        index=True,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    jurisdiction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("jurisdictions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization",
        back_populates="users",
    )
    jurisdiction: Mapped[Optional["Jurisdiction"]] = relationship(
        "Jurisdiction",
        back_populates="users",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[List["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="actor",
    )
