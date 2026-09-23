import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID

if TYPE_CHECKING:
    from app.models.user import User


class AuditEvent(Base):
    """Immutable audit trail recording security, operational, and administrative actions."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    actor: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="audit_logs",
    )
