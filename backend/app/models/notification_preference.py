"""Phase 13 — Notification Preferences Model.

Manages per-user notification preferences across channels (IN_APP, EMAIL)
and notification types with support for mandatory security/system overrides.
"""

import enum
import uuid
from typing import Optional
from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class DigestFrequency(str, enum.Enum):
    IMMEDIATE = "IMMEDIATE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class NotificationPreference(Base, TimestampMixin):
    """User preferences for receiving notifications by type and delivery channel."""
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="NotificationType enum or 'ALL'",
    )
    channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=NotificationChannel.IN_APP.value,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    digest_frequency: Mapped[str] = mapped_column(
        String(32),
        default=DigestFrequency.IMMEDIATE.value,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "notification_type", "channel", name="uq_user_notif_pref_channel"),
    )
