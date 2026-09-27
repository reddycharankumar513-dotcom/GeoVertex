"""Phase 13 — Entity Versioning & Restoration API.

Provides endpoints for timeline inspection, historical snapshots, version comparison,
controlled restoration, and cross-entity lineage graphs.
"""

import math
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenException, NotFoundException
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.governance import (
    EntityLineageResponse,
    EntityVersionResponse,
    RestoreVersionRequest,
    VersionComparisonResponse,
)
from app.services.lineage_service import lineage_service
from app.services.restoration_service import restoration_service
from app.services.version_comparison_service import version_comparison_service
from app.services.versioning_service import versioning_service

router = APIRouter(prefix="/versions", tags=["Entity Versioning & Governance"])


@router.get(
    "/compare/{version_a_id}/{version_b_id}",
    response_model=VersionComparisonResponse,
    summary="Compare two historical entity versions (scalar diffs + geometric variance)",
)
async def compare_versions(
    version_a_id: uuid.UUID,
    version_b_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await version_comparison_service.compare_versions(
        db=db, version_a_id=version_a_id, version_b_id=version_b_id
    )


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=PaginatedResponse[EntityVersionResponse],
    summary="Get version history timeline for an entity",
)
async def get_entity_versions(
    entity_type: str,
    entity_id: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    skip = (page - 1) * size
    items, total = await versioning_service.get_version_history(
        db=db, entity_type=entity_type, entity_id=entity_id, skip=skip, limit=size
    )
    total_pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedResponse[EntityVersionResponse](
        items=[EntityVersionResponse.model_validate(v) for v in items],
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


@router.get(
    "/{entity_type}/{entity_id}/lineage",
    response_model=List[EntityLineageResponse],
    summary="Get lineage records (splits, merges, replacements) for an entity",
)
async def get_entity_lineage(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lineages = await lineage_service.get_lineage(db=db, entity_type=entity_type, entity_id=entity_id)
    return [EntityLineageResponse.model_validate(l) for l in lineages]


@router.get(
    "/{entity_type}/{entity_id}/{version_number}",
    response_model=EntityVersionResponse,
    summary="Get a specific historical version snapshot",
)
async def get_entity_version_by_number(
    entity_type: str,
    entity_id: str,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version = await versioning_service.get_version_by_number(
        db=db, entity_type=entity_type, entity_id=entity_id, version_number=version_number
    )
    if not version:
        raise NotFoundException(
            f"Version {version_number} of {entity_type} {entity_id} not found."
        )
    return EntityVersionResponse.model_validate(version)


@router.post(
    "/{entity_type}/{entity_id}/restore",
    response_model=EntityVersionResponse,
    summary="Controlled rollback: restores historical version by creating a NEW version (Officer/Admin only)",
)
async def restore_entity_version(
    entity_type: str,
    entity_id: str,
    request: RestoreVersionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await restoration_service.restore_entity_version(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        target_version_number=request.target_version_number,
        reason=request.reason,
        current_user=current_user,
        workflow_id=request.workflow_id,
        case_id=request.case_id,
    )
