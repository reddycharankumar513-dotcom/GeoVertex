"""Phase 13 — Governance Dashboard & Integrity Verification API.

Provides system-wide governance metrics, version health analytics, and automated
cadastral integrity verification reports.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenException
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.schemas.governance import DataIntegrityResponse, GovernanceDashboardResponse
from app.services.governance_service import governance_service

router = APIRouter(prefix="/governance", tags=["System Governance & Data Integrity"])


def require_officer_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER]:
        raise ForbiddenException("Governance console restricted to Officers and Administrators.")
    return current_user


@router.get(
    "/dashboard",
    response_model=GovernanceDashboardResponse,
    summary="Get aggregated platform governance metrics and health analytics",
)
async def get_governance_dashboard(
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    metrics = await governance_service.get_dashboard_metrics(db)
    return GovernanceDashboardResponse(**metrics)


@router.get(
    "/integrity",
    response_model=DataIntegrityResponse,
    summary="Run automated platform data integrity checks",
)
async def check_data_integrity(
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    report = await governance_service.verify_data_integrity(db)
    return DataIntegrityResponse(**report)
