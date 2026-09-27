"""Phase 13 — Notification Preference Repository.

Manages persistent notification preferences per user and channel.
"""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification_preference import NotificationPreference, NotificationChannel, DigestFrequency
from app.repositories.base import BaseRepository


class NotificationPreferenceRepository(BaseRepository[NotificationPreference]):
    def __init__(self):
        super().__init__(NotificationPreference)

    async def get_preferences_for_user(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> List[NotificationPreference]:
        query = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_preference(
        self, db: AsyncSession, user_id: uuid.UUID, notification_type: str, channel: str
    ) -> Optional[NotificationPreference]:
        query = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type,
            NotificationPreference.channel == channel,
        )
        result = await db.execute(query)
        return result.scalars().first()

    async def set_preference(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        channel: str,
        enabled: bool,
        digest_frequency: str = DigestFrequency.IMMEDIATE.value,
    ) -> NotificationPreference:
        existing = await self.get_preference(db, user_id, notification_type, channel)
        if existing:
            existing.enabled = enabled
            existing.digest_frequency = digest_frequency
            await db.flush()
            return existing

        pref = NotificationPreference(
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            enabled=enabled,
            digest_frequency=digest_frequency,
        )
        db.add(pref)
        await db.flush()
        return pref


notification_preference_repository = NotificationPreferenceRepository()
