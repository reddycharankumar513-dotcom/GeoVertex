"""Multi-channel notification service with strict No-Fake-Delivery guarantees."""

import abc
import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import Notification, NotificationType, DeliveryChannel

logger = logging.getLogger(__name__)


class BaseNotificationProvider(abc.ABC):
    @abc.abstractmethod
    async def dispatch(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
    ) -> Notification:
        pass


class InAppNotificationProvider(BaseNotificationProvider):
    """Persists in-app notifications directly to the PostgreSQL/SQLite database."""

    async def dispatch(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=str(related_entity_id) if related_entity_id else None,
            delivery_channel=DeliveryChannel.IN_APP.value,
        )
        session.add(notif)
        await session.flush()
        return notif


class EmailNotificationProvider(BaseNotificationProvider):
    """Email delivery provider. Strictly enforces No-Fake-Delivery if SMTP is unconfigured."""

    def __init__(self, smtp_configured: bool = False):
        self.smtp_configured = smtp_configured

    async def dispatch(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
    ) -> Notification:
        if not self.smtp_configured:
            logger.info(
                f"[Notification] Email channel not configured. Falling back to IN_APP for user {user_id}."
            )
            channel = DeliveryChannel.EMAIL_NOT_CONFIGURED.value
        else:
            channel = DeliveryChannel.EMAIL_QUEUED.value

        notif = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=str(related_entity_id) if related_entity_id else None,
            delivery_channel=channel,
        )
        session.add(notif)
        await session.flush()
        return notif


class NotificationService:
    """High-level notification orchestrator for citizen and government workflow events."""

    def __init__(self):
        self.in_app_provider = InAppNotificationProvider()

    async def create_notification(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
    ) -> Notification:
        return await self.in_app_provider.dispatch(
            session=session,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
