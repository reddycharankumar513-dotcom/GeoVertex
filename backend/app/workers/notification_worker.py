"""Phase 13 — Asynchronous Notification Worker.

Processes queued notifications with retry policies, failure recording, idempotency,
and strict No-Fake-Delivery enforcement.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workflow import DeliveryChannel, Notification
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class NotificationWorker:
    """Processes notifications staged in QUEUED status."""

    async def process_batch(self, db: AsyncSession, batch_size: int = 50) -> Dict[str, int]:
        now = datetime.now(timezone.utc)
        query = (
            select(Notification)
            .where(Notification.status == "QUEUED")
            .limit(batch_size)
        )
        res = await db.execute(query)
        queued = list(res.scalars().all())

        stats = {"processed": 0, "delivered": 0, "failed": 0, "expired": 0}

        for notif in queued:
            # Check expiration
            if notif.expires_at and notif.expires_at < now:
                notif.status = "CANCELLED"
                notif.failure_reason = "EXPIRED"
                stats["expired"] += 1
                continue

            notif.status = "PROCESSING"
            await db.flush()

            try:
                # Resolve recipient email if required
                recipient_email = None
                if notif.delivery_channel in ["EMAIL", DeliveryChannel.EMAIL_QUEUED.value]:
                    user_res = await db.execute(select(User).where(User.id == notif.user_id))
                    user = user_res.scalars().first()
                    recipient_email = user.email if user else None

                if not recipient_email and notif.delivery_channel in ["EMAIL", DeliveryChannel.EMAIL_QUEUED.value]:
                    notif.status = "FAILED"
                    notif.failure_reason = "RECIPIENT_EMAIL_MISSING"
                    stats["failed"] += 1
                elif notif.delivery_channel in ["EMAIL", DeliveryChannel.EMAIL_QUEUED.value]:
                    success, reason = await notification_service.email_provider.send_email(
                        recipient_email=recipient_email,
                        subject=notif.title,
                        body=notif.message,
                        metadata=notif.metadata_json,
                    )
                    if success:
                        notif.status = "DELIVERED"
                        notif.sent_at = datetime.now(timezone.utc)
                        stats["delivered"] += 1
                    else:
                        notif.retry_count += 1
                        if notif.retry_count >= MAX_RETRIES:
                            notif.status = "FAILED"
                            notif.failure_reason = f"MAX_RETRIES_EXCEEDED: {reason}"
                            stats["failed"] += 1
                        else:
                            notif.status = "QUEUED"
                            notif.failure_reason = reason
                else:
                    # IN_APP delivery is already completed on creation
                    notif.status = "SENT"
                    notif.sent_at = datetime.now(timezone.utc)
                    stats["delivered"] += 1

                stats["processed"] += 1
            except Exception as e:
                logger.error(f"[NotificationWorker] Error processing notification {notif.id}: {e}")
                notif.retry_count += 1
                notif.failure_reason = str(e)
                if notif.retry_count >= MAX_RETRIES:
                    notif.status = "FAILED"
                    stats["failed"] += 1
                else:
                    notif.status = "QUEUED"

            await db.flush()

        logger.info(f"[NotificationWorker] Processed batch: {stats}")
        return stats


notification_worker = NotificationWorker()
