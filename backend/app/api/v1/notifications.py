"""Phase 13 — Notifications API.

Provides user notification inbox, unread counts, batch read transitions,
user preference configuration, and administrative test triggers.
"""

import math
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenException
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.governance import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    TestNotificationRequest,
)
from app.services.notification_preference_service import notification_preference_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications & User Alerts"])


@router.get(
    "/unread-count",
    summary="Get unread notification count for the current user",
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.get_unread_count(db, current_user.id)
    return {"unread_count": count}


@router.get(
    "/preferences",
    response_model=List[NotificationPreferenceResponse],
    summary="Get notification delivery preferences for the current user",
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await notification_preference_service.get_preferences(db, current_user.id)
    return [NotificationPreferenceResponse.model_validate(p) for p in prefs]


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update notification channel preference (protects mandatory alerts)",
)
async def update_notification_preference(
    req: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = await notification_preference_service.update_preference(
        db=db,
        user_id=current_user.id,
        notification_type=req.notification_type,
        channel=req.channel,
        enabled=req.enabled,
        digest_frequency=req.digest_frequency,
    )
    return NotificationPreferenceResponse.model_validate(pref)


@router.post(
    "/read-all",
    summary="Mark all unread notifications as read for current user",
)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.mark_all_as_read(db, current_user.id)
    return {"marked_read": count}


@router.post(
    "/test",
    response_model=NotificationResponse,
    summary="Administrative test notification trigger (Admin only)",
)
async def trigger_test_notification(
    req: TestNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Test notifications restricted to Administrators.")

    notif = await notification_service.dispatch_notification(
        db=db,
        user_id=current_user.id,
        notification_type=req.notification_type,
        title=req.title,
        message=req.message,
        severity=req.severity,
        channel=req.channel,
    )
    return NotificationResponse.model_validate(notif)


@router.post(
    "/{id}/read",
    response_model=NotificationResponse,
    summary="Mark a specific notification as read",
)
async def mark_notification_read(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notif = await notification_service.mark_as_read(db, id, current_user.id)
    return NotificationResponse.model_validate(notif)


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
    summary="List notifications for the current user",
)
async def list_notifications(
    unread_only: bool = Query(default=False, description="Filter for unread only"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await notification_service.list_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        severity=severity,
        skip=skip,
        limit=size,
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[NotificationResponse](
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )
