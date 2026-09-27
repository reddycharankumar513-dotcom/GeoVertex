"""Phase 13 — Notification Preference Service.

Enforces rules for enabling/disabling notification channels and protects mandatory
system/security alerts from being disabled.
"""

import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException
from app.models.notification_preference import NotificationPreference, NotificationChannel, DigestFrequency
from app.repositories.notification_preference_repository import notification_preference_repository
from app.services.notification_service import MANDATORY_NOTIFICATION_TYPES


class NotificationPreferenceService:
    async def get_preferences(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> List[NotificationPreference]:
        return await notification_preference_repository.get_preferences_for_user(db, user_id)

    async def update_preference(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        channel: str,
        enabled: bool,
        digest_frequency: str = DigestFrequency.IMMEDIATE.value,
    ) -> NotificationPreference:
        if notification_type in MANDATORY_NOTIFICATION_TYPES and not enabled:
            raise BadRequestException(
                f"Notification type '{notification_type}' is mandatory for platform security and compliance, and cannot be disabled."
            )

        return await notification_preference_repository.set_preference(
            db=db,
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            enabled=enabled,
            digest_frequency=digest_frequency,
        )


notification_preference_service = NotificationPreferenceService()
