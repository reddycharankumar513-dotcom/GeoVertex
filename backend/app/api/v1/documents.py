from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException, ForbiddenException, NotFoundException
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.document import DocumentStatus, DocumentType
from app.models.user import User, UserRole
from app.repositories.document_repository import document_repository
from app.repositories.validation_repository import validation_repository
from app.schemas.document import (
    DocumentDashboardMetricsResponse,
    DocumentEntityLinkCreate,
    DocumentEntityLinkResponse,
    DocumentExtractedFieldResponse,
    DocumentListResponse,
    DocumentOCRResultResponse,
    DocumentPageResponse,
    DocumentProcessingJobResponse,
    DocumentRejectAction,
    DocumentRequireCorrectionAction,
    DocumentUpdate,
    DocumentVerifyAction,
    DocumentVersionResponse,
    FieldReviewAction,
    PropertyDocumentResponse,
)
from app.schemas.validation import ValidationIssueResponse
from app.services.document_service import document_service
from app.services.document_storage_service import document_storage_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=PropertyDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(DocumentType.OTHER.value),
    description: Optional[str] = Form(None),
    jurisdiction_id: Optional[str] = Form(None),
    property_id: Optional[str] = Form(None),
    parcel_id: Optional[str] = Form(None),
    building_id: Optional[str] = Form(None),
    floor_id: Optional[str] = Form(None),
    unit_id: Optional[str] = Form(None),
    document_date: Optional[str] = Form(None),
    issuing_authority: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Secure document upload, content hashing, version 1 creation, and pipeline queuing."""
    parsed_date = None
    if document_date:
        from app.ai.document.normalizer import document_normalizer
        _, parsed_date = document_normalizer.normalize_date(document_date)

    doc = await document_service.upload_document(
        db=db,
        file=file,
        title=title,
        document_type=document_type,
        current_user=current_user,
        description=description,
        jurisdiction_id=jurisdiction_id,
        property_id=property_id,
        parcel_id=parcel_id,
        building_id=building_id,
        floor_id=floor_id,
        unit_id=unit_id,
        document_date=parsed_date,
        issuing_authority=issuing_authority,
    )
    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    jurisdiction_id: Optional[str] = Query(None),
    parcel_id: Optional[str] = Query(None),
    property_id: Optional[str] = Query(None),
    building_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List property documents with role-aware filtering and pagination."""
    skip = (page - 1) * size
    items, total = await document_repository.list_documents(
        db=db,
        skip=skip,
        limit=size,
        status=status,
        document_type=document_type,
        jurisdiction_id=jurisdiction_id,
        parcel_id=parcel_id,
        property_id=property_id,
        building_id=building_id,
        search=search,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/metrics", response_model=DocumentDashboardMetricsResponse)
async def get_document_metrics(
    jurisdiction_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get authoritative document dashboard statistics derived directly from database."""
    metrics = await document_repository.get_dashboard_metrics(db, jurisdiction_id=jurisdiction_id)
    return metrics


@router.get("/{document_id}", response_model=PropertyDocumentResponse)
async def get_document_by_id(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single document details."""
    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")
    return doc


@router.patch("/{document_id}", response_model=PropertyDocumentResponse)
async def update_document(
    document_id: str,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update document metadata attributes."""
    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")

    update_dict = payload.model_dump(exclude_unset=True)
    updated = await document_repository.update_document(db, document_id, update_dict)
    await db.commit()
    return updated


@router.get("/{document_id}/file")
async def download_document_file(
    document_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Secure, authenticated file download. Blocks public or unauthorized access."""
    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")

    target_ver_id = version_id or doc.current_version_id
    if not target_ver_id:
        raise NotFoundException("No file version exists for this document.")

    version = await document_repository.get_version_by_id(db, target_ver_id)
    if not version:
        raise NotFoundException(f"Document version not found: {target_ver_id}")

    file_path = document_storage_service.get_file_path(version.storage_key)
    return FileResponse(
        path=file_path,
        media_type=version.mime_type,
        filename=version.original_filename,
    )


@router.post("/{document_id}/versions", response_model=DocumentVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_version(
    document_id: str,
    file: UploadFile = File(...),
    source_notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload revised version of existing document."""
    version = await document_service.upload_new_version(
        db=db,
        doc_id=document_id,
        file=file,
        current_user=current_user,
        source_notes=source_notes,
    )
    return version


@router.get("/{document_id}/versions", response_model=List[DocumentVersionResponse])
async def list_document_versions(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all versions of a document."""
    return await document_repository.get_versions(db, document_id)


@router.post("/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
async def trigger_document_processing(
    document_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-triggers document processing pipeline."""
    import asyncio
    from app.ai.document.worker import document_processing_worker

    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")

    target_ver_id = version_id or doc.current_version_id
    if not target_ver_id:
        raise BadRequestException("No version found to process.")

    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "document_version_id": target_ver_id,
        "job_type": "FULL_PIPELINE",
        "status": "QUEUED",
        "current_stage": "QUEUED",
        "requested_by": str(current_user.id),
        "parameters": {},
    }
    job = await document_repository.create_processing_job(db, job_data)
    doc.status = DocumentStatus.QUEUED.value
    await db.commit()

    asyncio.create_task(document_processing_worker.execute_job(job_id))
    return {"message": "Processing job enqueued", "job_id": job_id}


@router.get("/{document_id}/processing", response_model=List[DocumentProcessingJobResponse])
async def list_processing_jobs(
    document_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get processing history for document."""
    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")

    target_ver_id = version_id or doc.current_version_id
    if not target_ver_id:
        return []
    return await document_repository.get_jobs_for_version(db, target_ver_id)


@router.get("/{document_id}/pages", response_model=List[DocumentPageResponse])
async def list_document_pages(
    document_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get document page models."""
    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")

    target_ver_id = version_id or doc.current_version_id
    if not target_ver_id:
        return []
    return await document_repository.get_pages(db, target_ver_id)


@router.get("/{document_id}/ocr", response_model=List[DocumentOCRResultResponse])
async def list_ocr_results(
    document_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get OCR results."""
    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")

    target_ver_id = version_id or doc.current_version_id
    if not target_ver_id:
        return []
    return await document_repository.get_ocr_results(db, target_ver_id)


@router.get("/{document_id}/fields", response_model=List[DocumentExtractedFieldResponse])
async def list_extracted_fields(
    document_id: str,
    version_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get structured extracted fields."""
    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")

    target_ver_id = version_id or doc.current_version_id
    if not target_ver_id:
        return []
    return await document_repository.get_extracted_fields(db, target_ver_id)


@router.patch("/{document_id}/fields/{field_id}", response_model=DocumentExtractedFieldResponse)
async def review_extracted_field(
    document_id: str,
    field_id: str,
    payload: FieldReviewAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Perform field-level review: CONFIRM, CORRECT, or REJECT."""
    return await document_service.review_field(
        db=db,
        doc_id=document_id,
        field_id=field_id,
        action=payload.action,
        current_user=current_user,
        reviewed_value=payload.reviewed_value,
        review_notes=payload.review_notes,
    )


@router.post("/{document_id}/verify", response_model=PropertyDocumentResponse)
async def verify_document(
    document_id: str,
    payload: DocumentVerifyAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark document as formally VERIFIED (Officer/Admin only)."""
    return await document_service.verify_document(
        db=db,
        doc_id=document_id,
        current_user=current_user,
        notes=payload.notes,
    )


@router.post("/{document_id}/reject", response_model=PropertyDocumentResponse)
async def reject_document(
    document_id: str,
    payload: DocumentRejectAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject document with mandatory rationale (Officer/Admin only)."""
    return await document_service.reject_document(
        db=db,
        doc_id=document_id,
        current_user=current_user,
        reason=payload.rejection_reason,
    )


@router.post("/{document_id}/require-correction", response_model=PropertyDocumentResponse)
async def request_document_correction(
    document_id: str,
    payload: DocumentRequireCorrectionAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark document as requiring correction with mandatory notes (Officer/Admin only)."""
    return await document_service.request_correction(
        db=db,
        doc_id=document_id,
        current_user=current_user,
        notes=payload.correction_notes,
    )


@router.get("/{document_id}/validation", response_model=List[ValidationIssueResponse])
async def get_document_validation_issues(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Phase 7 validation issues and discrepancies found for this document."""
    doc = await document_repository.get_document_by_id(db, document_id)
    if not doc:
        raise NotFoundException(f"Property document not found: {document_id}")

    issues, _ = await validation_repository.list_issues(
        db=db,
        entity_type="DOCUMENT",
        entity_id=document_id,
        limit=50,
    )
    return issues


@router.get("/{document_id}/links", response_model=List[DocumentEntityLinkResponse])
async def list_document_links(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List entity links (parcels, buildings, units) for document."""
    return await document_repository.get_entity_links(db, document_id)


@router.post("/{document_id}/links", response_model=DocumentEntityLinkResponse, status_code=status.HTTP_201_CREATED)
async def add_document_link(
    document_id: str,
    payload: DocumentEntityLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Associate document with a cadastral parcel, property, building, floor, or unit."""
    return await document_service.add_entity_link(
        db=db,
        doc_id=document_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        current_user=current_user,
        link_method=payload.link_method,
    )


@router.delete("/{document_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_link(
    document_id: str,
    link_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove entity link."""
    await document_service.delete_entity_link(db, document_id, link_id, current_user)
    return None


@router.post("/{document_id}/links/{link_id}/confirm", response_model=DocumentEntityLinkResponse)
async def confirm_document_link(
    document_id: str,
    link_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirm a candidate link."""
    link = await document_repository.confirm_entity_link(db, link_id, str(current_user.id))
    if not link:
        raise NotFoundException(f"Entity link not found: {link_id}")
    await db.commit()
    return link
