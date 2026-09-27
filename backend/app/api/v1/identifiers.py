"""Phase 12 — REST API for Technical 3D Property Identifier Engine.

DISCLAIMER: These endpoints generate/manage GeoVertex Technical 3D Identifiers.
They are NOT official ULPINs or legal ownership identifiers.
"""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import logger
from app.dependencies.auth import get_current_user, require_role, require_officer_or_admin
from app.dependencies.db import get_db
from app.models.identifier import IdentifierEntityType, IdentifierStatus
from app.models.user import User, UserRole
from app.repositories.audit_repository import audit_repository
from app.repositories.identifier_repository import (
    identifier_job_repository,
    identifier_lineage_repository,
    identifier_scheme_repository,
    property_identifier_repository,
)
from app.schemas.identifier import (
    BulkGenerateRequest,
    BulkGenerateResponse,
    BulkPreviewRequest,
    GenerateIdentifierRequest,
    IdentifierJobResponse,
    IdentifierLineageResponse,
    IdentifierSchemeCreate,
    IdentifierSchemePatch,
    IdentifierSchemeResponse,
    IdentifierStatisticsResponse,
    PreviewIdentifierRequest,
    PreviewIdentifierResponse,
    PropertyIdentifierResponse,
    RetireRequest,
    RevokeRequest,
    SupersedeRequest,
    SupersedeResponse,
    VerificationResult,
)
from app.services.identifier_generation_service import (
    IdentifierError,
    IdentifierCollisionError,
    identifier_generation_service,
)
from app.services.identifier_qr_service import (
    generate_qr_png,
    generate_qr_svg,
    get_verify_url,
)

router = APIRouter(prefix="/identifiers", tags=["Technical 3D Identifier Engine"])
verify_router = APIRouter(tags=["Technical 3D Identifier Verification"])


# ─────────────────────────────────────────────────────────────────────────────
# Scheme endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/schemes",
    response_model=List[IdentifierSchemeResponse],
    summary="List all identifier schemes",
)
async def list_schemes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    schemes = await identifier_scheme_repository.list_all(db)
    return schemes


@router.post(
    "/schemes",
    response_model=IdentifierSchemeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new identifier scheme (Admin only)",
)
async def create_scheme(
    payload: IdentifierSchemeCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    existing = await identifier_scheme_repository.get_by_code(db, payload.scheme_code)
    if existing:
        raise BadRequestException(f"Scheme with code '{payload.scheme_code}' already exists")

    from app.models.identifier import IdentifierScheme
    scheme = IdentifierScheme(**payload.model_dump())
    db.add(scheme)
    await db.flush()
    await db.refresh(scheme)

    await audit_repository.log_event(
        db, action="IDENTIFIER_SCHEME_CREATED", entity_type="identifier_scheme",
        entity_id=str(scheme.id), actor_user_id=current_user.id,
        details={"scheme_code": scheme.scheme_code},
    )
    await db.commit()
    return scheme


@router.patch(
    "/schemes/{scheme_id}",
    response_model=IdentifierSchemeResponse,
    summary="Update an identifier scheme (Admin only)",
)
async def patch_scheme(
    scheme_id: uuid.UUID,
    payload: IdentifierSchemePatch,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    scheme = await identifier_scheme_repository.get_by_id(db, scheme_id)
    if not scheme:
        raise NotFoundException(f"Scheme {scheme_id} not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(scheme, field, value)
    await db.flush()
    await db.refresh(scheme)

    await audit_repository.log_event(
        db, action="IDENTIFIER_SCHEME_MODIFIED", entity_type="identifier_scheme",
        entity_id=str(scheme.id), actor_user_id=current_user.id,
        details=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return scheme


# ─────────────────────────────────────────────────────────────────────────────
# Preview endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/preview",
    response_model=PreviewIdentifierResponse,
    summary="Preview what identifier would be generated (no persist)",
)
async def preview_identifier(
    payload: PreviewIdentifierRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entity_type = payload.entity_type.upper()
    if entity_type not in ("UNIT", "BUILDING", "PARCEL", "FLOOR"):
        raise BadRequestException(f"Unsupported entity_type for preview: {entity_type}")

    if entity_type == "UNIT":
        result = await identifier_generation_service.preview_for_unit(db, payload.entity_id, payload.scheme_id)
    else:
        raise BadRequestException(f"Preview currently supported for UNIT only")

    return PreviewIdentifierResponse(**result)


# ─────────────────────────────────────────────────────────────────────────────
# Generate endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=PropertyIdentifierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a GeoVertex Technical 3D Identifier for a spatial entity",
)
async def generate_identifier(
    payload: GenerateIdentifierRequest,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a deterministic Technical 3D Identifier.

    **Disclaimer**: This generates a GeoVertex Technical 3D Identifier (a deterministic
    technical system identifier). It is NOT an official ULPIN or legal property identifier.
    """
    entity_type = payload.entity_type.upper()
    try:
        if entity_type == "UNIT":
            record = await identifier_generation_service.generate_for_unit(
                db, payload.entity_id, current_user.id, payload.scheme_id, payload.force_new
            )
        elif entity_type == "BUILDING":
            record = await identifier_generation_service.generate_for_building(
                db, payload.entity_id, current_user.id, payload.scheme_id
            )
        elif entity_type == "PARCEL":
            record = await identifier_generation_service.generate_for_parcel(
                db, payload.entity_id, current_user.id, payload.scheme_id
            )
        elif entity_type == "FLOOR":
            record = await identifier_generation_service.generate_for_floor(
                db, payload.entity_id, current_user.id, payload.scheme_id
            )
        else:
            raise BadRequestException(f"Unsupported entity_type: {entity_type}")
    except IdentifierCollisionError as e:
        raise
    except IdentifierError as e:
        raise

    await db.commit()
    scheme = await identifier_scheme_repository.get_by_id(db, record.scheme_id)
    return PropertyIdentifierResponse.from_orm_with_hierarchy(record, scheme.scheme_code if scheme else None)


# ─────────────────────────────────────────────────────────────────────────────
# List/Search identifiers
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=Dict[str, Any],
    summary="List/search Technical 3D Identifiers",
)
async def list_identifiers(
    status_filter: Optional[str] = Query(None, alias="status"),
    entity_type: Optional[str] = Query(None),
    scheme_id: Optional[uuid.UUID] = Query(None),
    jurisdiction_id: Optional[uuid.UUID] = Query(None),
    parcel_id: Optional[uuid.UUID] = Query(None),
    building_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None, description="Identifier value search"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    records, total = await property_identifier_repository.list_filtered(
        db,
        status=status_filter,
        entity_type=entity_type,
        scheme_id=str(scheme_id) if scheme_id else None,
        jurisdiction_id=str(jurisdiction_id) if jurisdiction_id else None,
        parcel_id=str(parcel_id) if parcel_id else None,
        building_id=str(building_id) if building_id else None,
        search=search,
        skip=skip,
        limit=limit,
    )
    items = [PropertyIdentifierResponse.from_orm_with_hierarchy(r) for r in records]
    return {
        "items": items,
        "total": total,
        "page": skip // limit + 1,
        "size": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@router.get(
    "/statistics",
    response_model=IdentifierStatisticsResponse,
    summary="Identifier engine statistics",
)
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    by_status = await property_identifier_repository.count_by_status(db)
    by_entity = await property_identifier_repository.count_by_entity_type(db)
    total = sum(by_status.values())
    return IdentifierStatisticsResponse(
        total=total,
        by_status=by_status,
        by_entity_type=by_entity,
        active=by_status.get("ACTIVE", 0),
        superseded=by_status.get("SUPERSEDED", 0),
        retired=by_status.get("RETIRED", 0),
        revoked=by_status.get("REVOKED", 0),
        draft=by_status.get("DRAFT", 0),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Individual identifier endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{identifier_id}",
    response_model=PropertyIdentifierResponse,
    summary="Get a Technical 3D Identifier by UUID",
)
async def get_identifier(
    identifier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await property_identifier_repository.get_by_id(db, identifier_id)
    if not record:
        raise NotFoundException(f"Identifier {identifier_id} not found")
    scheme = await identifier_scheme_repository.get_by_id(db, record.scheme_id)
    return PropertyIdentifierResponse.from_orm_with_hierarchy(record, scheme.scheme_code if scheme else None)


@router.get(
    "/{identifier_id}/history",
    response_model=List[PropertyIdentifierResponse],
    summary="Get full identifier history for the same entity",
)
async def get_identifier_history(
    identifier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await property_identifier_repository.get_by_id(db, identifier_id)
    if not record:
        raise NotFoundException(f"Identifier {identifier_id} not found")
    history = await property_identifier_repository.list_for_entity(db, record.entity_type, record.entity_id)
    return [PropertyIdentifierResponse.from_orm_with_hierarchy(r) for r in history]


@router.get(
    "/{identifier_id}/qr",
    summary="Get QR code for a Technical 3D Identifier",
)
async def get_identifier_qr(
    identifier_id: uuid.UUID,
    fmt: str = Query("png", description="png or svg"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await property_identifier_repository.get_by_id(db, identifier_id)
    if not record:
        raise NotFoundException(f"Identifier {identifier_id} not found")
    if record.status in (IdentifierStatus.REVOKED.value, IdentifierStatus.RETIRED.value):
        raise BadRequestException(f"Cannot generate QR for {record.status} identifier")
    if not record.verification_token:
        raise BadRequestException("No verification token for this identifier")

    await audit_repository.log_event(
        db, action="IDENTIFIER_QR_GENERATED", entity_type="property_identifier",
        entity_id=str(identifier_id), actor_user_id=current_user.id,
        details={"format": fmt},
    )
    await db.commit()

    if fmt.lower() == "svg":
        svg_content, ct = generate_qr_svg(record.verification_token)
        return Response(content=svg_content, media_type=ct)
    else:
        png_bytes, ct = generate_qr_png(record.verification_token)
        return Response(content=png_bytes, media_type=ct)


@router.get(
    "/{identifier_id}/verify",
    response_model=VerificationResult,
    summary="Verify a Technical 3D Identifier",
)
async def verify_identifier(
    identifier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await property_identifier_repository.get_by_id(db, identifier_id)
    if not record:
        return VerificationResult(valid=False, verification_message="IDENTIFIER_NOT_FOUND")
    scheme = await identifier_scheme_repository.get_by_id(db, record.scheme_id)
    return _build_verification_result(record, scheme)


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{identifier_id}/supersede",
    response_model=SupersedeResponse,
    summary="Supersede a Technical 3D Identifier (Officer/Admin)",
)
async def supersede_identifier(
    identifier_id: uuid.UUID,
    payload: SupersedeRequest,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    old, new = await identifier_generation_service.supersede(
        db, identifier_id, payload.reason, current_user.id,
        new_entity_id=payload.new_entity_id,
    )
    await db.commit()
    old_scheme = await identifier_scheme_repository.get_by_id(db, old.scheme_id)
    new_scheme = await identifier_scheme_repository.get_by_id(db, new.scheme_id)
    return SupersedeResponse(
        old_identifier=PropertyIdentifierResponse.from_orm_with_hierarchy(old, old_scheme.scheme_code if old_scheme else None),
        new_identifier=PropertyIdentifierResponse.from_orm_with_hierarchy(new, new_scheme.scheme_code if new_scheme else None),
    )


@router.post(
    "/{identifier_id}/retire",
    response_model=PropertyIdentifierResponse,
    summary="Retire a Technical 3D Identifier (Officer/Admin)",
)
async def retire_identifier(
    identifier_id: uuid.UUID,
    payload: RetireRequest,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    record = await identifier_generation_service.retire(db, identifier_id, payload.reason, current_user.id)
    await db.commit()
    return PropertyIdentifierResponse.from_orm_with_hierarchy(record)


@router.post(
    "/{identifier_id}/revoke",
    response_model=PropertyIdentifierResponse,
    summary="Revoke a Technical 3D Identifier (Admin only)",
)
async def revoke_identifier(
    identifier_id: uuid.UUID,
    payload: RevokeRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    record = await identifier_generation_service.revoke(db, identifier_id, payload.reason, current_user.id)
    await db.commit()
    return PropertyIdentifierResponse.from_orm_with_hierarchy(record)


# ─────────────────────────────────────────────────────────────────────────────
# Lineage
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{identifier_id}/lineage",
    response_model=List[IdentifierLineageResponse],
    summary="Get lineage records for an identifier",
)
async def get_identifier_lineage(
    identifier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await property_identifier_repository.get_by_id(db, identifier_id)
    if not record:
        raise NotFoundException(f"Identifier {identifier_id} not found")
    lineages = await identifier_lineage_repository.list_for_identifier(db, str(identifier_id))
    return lineages


# ─────────────────────────────────────────────────────────────────────────────
# Bulk Generation
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/bulk-preview",
    response_model=Dict[str, Any],
    summary="Preview bulk generation for all units in a building",
)
async def bulk_preview(
    payload: BulkPreviewRequest,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    if payload.entity_type.upper() != "UNIT":
        raise BadRequestException("Bulk generation currently supports UNIT entity type only")
    return await identifier_generation_service.bulk_preview_building(db, payload.building_id, payload.scheme_id)


@router.post(
    "/bulk-generate",
    response_model=BulkGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk generate identifiers for all eligible units in a building",
)
async def bulk_generate(
    payload: BulkGenerateRequest,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    if payload.entity_type.upper() != "UNIT":
        raise BadRequestException("Bulk generation currently supports UNIT entity type only")
    if not payload.confirmed:
        raise BadRequestException("Set 'confirmed: true' to proceed with bulk generation")

    result = await identifier_generation_service.bulk_generate_building(
        db, payload.building_id, current_user.id, payload.scheme_id
    )
    await db.commit()
    return BulkGenerateResponse(**result)


# ─────────────────────────────────────────────────────────────────────────────
# Jobs
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/jobs",
    response_model=Dict[str, Any],
    summary="List bulk generation jobs",
)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    jobs, total = await identifier_job_repository.list_recent(db, skip, limit)
    return {
        "items": [IdentifierJobResponse.model_validate(j) for j in jobs],
        "total": total,
    }


@router.get(
    "/jobs/{job_id}",
    response_model=IdentifierJobResponse,
    summary="Get a bulk generation job by ID",
)
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    job = await identifier_job_repository.get_by_id(db, job_id)
    if not job:
        raise NotFoundException(f"Job {job_id} not found")
    return job


# ─────────────────────────────────────────────────────────────────────────────
# Public token-based verification endpoint
# ─────────────────────────────────────────────────────────────────────────────

@verify_router.get(
    "/verify/{token}",
    response_model=VerificationResult,
    summary="Public verification of a GeoVertex Technical 3D Identifier by token",
)
async def public_verify(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — no authentication required.
    Returns only non-sensitive verification information.
    Does NOT return citizen personal data, private documents, or confidential notes.
    """
    record = await property_identifier_repository.get_by_token(db, token)
    if not record:
        return VerificationResult(valid=False, verification_message="INVALID_IDENTIFIER")
    scheme = await identifier_scheme_repository.get_by_id(db, record.scheme_id)
    return _build_verification_result(record, scheme)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _build_verification_result(record: Any, scheme: Any) -> VerificationResult:
    from app.models.identifier import IdentifierStatus as IS
    status_val = record.status

    if status_val == IS.REVOKED.value:
        msg = "IDENTIFIER_REVOKED"
        valid = False
    elif status_val == IS.RETIRED.value:
        msg = "IDENTIFIER_RETIRED"
        valid = False
    elif status_val == IS.SUPERSEDED.value:
        msg = "IDENTIFIER_SUPERSEDED"
        valid = False
    elif status_val == IS.ACTIVE.value:
        msg = "VALID"
        valid = True
    else:
        msg = f"IDENTIFIER_STATUS_{status_val}"
        valid = False

    from app.schemas.identifier import IdentifierHierarchy
    return VerificationResult(
        valid=valid,
        identifier_value=record.identifier_value,
        identifier_type=record.identifier_type,
        status=status_val,
        entity_type=record.entity_type,
        scheme_code=scheme.scheme_code if scheme else None,
        issued_at=record.issued_at,
        hierarchy=IdentifierHierarchy(
            jurisdiction_id=record.jurisdiction_id,
            jurisdiction_component=record.jurisdiction_component,
            parcel_id=record.parcel_id,
            parcel_component=record.parcel_component,
            building_id=record.building_id,
            building_component=record.building_component,
            floor_id=record.floor_id,
            floor_component=record.floor_component,
            unit_id=record.unit_id,
            unit_component=record.unit_component,
        ),
        verification_message=msg,
    )
