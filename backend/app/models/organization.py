import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.models.jurisdiction import Jurisdiction
    from app.models.user import User


class Organization(Base, TimestampMixin):
    """Represents a municipal council, survey department, or land administration agency."""
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="MUNICIPALITY",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    jurisdictions: Mapped[List["Jurisdiction"]] = relationship(
        "Jurisdiction",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organization",
    )
