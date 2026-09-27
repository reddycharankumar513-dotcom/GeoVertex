import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.document.worker import document_processing_worker
from app.core.errors import BadRequestException, ForbiddenException, NotFoundException
from app.models.document import (
    DocumentEntityLink,
    DocumentExtractedField,
    DocumentOCRResult,
    DocumentPage,
    DocumentProcessingJob,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    FieldReviewStatus,
    PropertyDocument,
)
from app.models.user import User, UserRole
from app.repositories.audit_repository import audit_repository
from app.repositories.document_repository import document_repository
from app.services.document_storage_service import document_storage_service


class DocumentService:
    """Business service governing property documents, AI extraction, review lifecycles, and verification."""

    @staticmethod
    def _get_role_value(user: User) -> str:
        return user.role.value if hasattr(user.role, "value") else str(user.role)

    def _require_officer_or_admin(self, user: User) -> None:
        role = self._get_role_value(user)
        if role not in [UserRole.ADMIN.value, UserRole.GOVERNMENT_OFFICER.value]:
            raise ForbiddenException("Only Government Officers or Administrators can perform this document verification action.")

    def _require_editor(self, user: User) -> None:
        role = self._get_role_value(user)
        if role not in [UserRole.ADMIN.value, UserRole.GOVERNMENT_OFFICER.value, UserRole.SURVEYOR.value]:
            raise ForbiddenException("Insufficient permissions to upload or manage documents.")

    async def upload_document(
        self,
        db: AsyncSession,
        file: UploadFile,
        title: str,
        document_type: str,
        current_user: User,
        description: Optional[str] = None,
        jurisdiction_id: Optional[str] = None,
        property_id: Optional[str] = None,
        parcel_id: Optional[str] = None,
        building_id: Optional[str] = None,
        floor_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        document_date: Optional[datetime] = None,
        issuing_authority: Optional[str] = None,
        source_type: str = "MANUAL_UPLOAD",
    ) -> PropertyDocument:
        """Uploads a new property document, stores version 1, and enqueues processing."""
        doc_id = str(uuid.uuid4())
        ref_code = f"DOC-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"

        # Save file to object storage
        storage_key, filename, file_size, file_hash, mime_type = await document_storage_service.save_document_file(
            document_id=doc_id,
            version_number=1,
            file=file,
        )

        # Create Document record
        doc_data = {
            "id": doc_id,
            "document_reference": ref_code,
            "document_type": document_type or DocumentType.OTHER.value,
            "title": title,
            "description": description,
            "status": DocumentStatus.QUEUED.value,
            "source_type": source_type,
            "uploaded_by": str(current_user.id),
            "uploaded_at": datetime.now(timezone.utc),
            "jurisdiction_id": jurisdiction_id or str(getattr(current_user, "jurisdiction_id", None) or ""),
            "organization_id": str(getattr(current_user, "organization_id", None) or ""),
            "property_id": property_id,
            "parcel_id": parcel_id,
            "building_id": building_id,
            "floor_id": floor_id,
            "unit_id": unit_id,
            "document_date": document_date,
            "issuing_authority": issuing_authority,
            "page_count": 0,
            "metadata_json": {},
        }
        # Clean empty strings to None
        for k in ["jurisdiction_id", "organization_id", "property_id", "parcel_id", "building_id", "floor_id", "unit_id"]:
            if doc_data.get(k) == "":
                doc_data[k] = None

        doc = await document_repository.create_document(db, doc_data)

        # Create Version 1 record
        ver_id = str(uuid.uuid4())
        ver_data = {
            "id": ver_id,
            "document_id": doc_id,
            "version_number": 1,
            "storage_key": storage_key,
            "original_filename": filename,
            "mime_type": mime_type,
            "file_size": file_size,
            "file_hash": file_hash,
            "page_count": 0,
            "uploaded_by": str(current_user.id),
            "uploaded_at": datetime.now(timezone.utc),
            "processing_status": "QUEUED",
        }
        ver = await document_repository.create_version(db, ver_data)
        doc.current_version_id = ver_id

        # Create initial processing job
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "document_version_id": ver_id,
            "job_type": "FULL_PIPELINE",
            "status": "QUEUED",
            "current_stage": "QUEUED",
            "requested_by": str(current_user.id),
            "parameters": {},
        }
        await document_repository.create_processing_job(db, job_data)

        # Audit trail
        await audit_repository.log_event(
            db=db,
            action="DOCUMENT_UPLOADED",
            entity_type="PROPERTY_DOCUMENT",
            entity_id=doc_id,
            actor_user_id=str(current_user.id),
            details={
                "document_reference": ref_code,
                "document_type": doc.document_type,
                "filename": filename,
                "file_hash": file_hash,
                "file_size": file_size,
            },
        )
        await db.commit()

        # Fire async background processing worker
        asyncio.create_task(document_processing_worker.execute_job(job_id))

        return doc

    async def upload_new_version(
        self,
        db: AsyncSession,
        doc_id: str,
        file: UploadFile,
        current_user: User,
        source_notes: Optional[str] = None,
    ) -> DocumentVersion:
        """Uploads a revised document version, preserving all prior history."""
        self._require_editor(current_user)
        doc = await document_repository.get_document_by_id(db, doc_id)
        if not doc:
            raise NotFoundException(f"Property document not found: {doc_id}")

        existing_versions = await document_repository.get_versions(db, doc_id)
        next_ver_num = len(existing_versions) + 1

        storage_key, filename, file_size, file_hash, mime_type = await document_storage_service.save_document_file(
            document_id=doc_id,
            version_number=next_ver_num,
            file=file,
        )

        ver_id = str(uuid.uuid4())
        ver_data = {
            "id": ver_id,
            "document_id": doc_id,
            "version_number": next_ver_num,
            "storage_key": storage_key,
            "original_filename": filename,
            "mime_type": mime_type,
            "file_size": file_size,
            "file_hash": file_hash,
            "page_count": 0,
            "uploaded_by": str(current_user.id),
            "uploaded_at": datetime.now(timezone.utc),
            "processing_status": "QUEUED",
            "source_notes": source_notes,
        }
        version = await document_repository.create_version(db, ver_data)
        doc.current_version_id = ver_id
        doc.status = DocumentStatus.QUEUED.value

        # Create processing job for new version
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "document_version_id": ver_id,
            "job_type": "FULL_PIPELINE",
            "status": "QUEUED",
            "current_stage": "QUEUED",
            "requested_by": str(current_user.id),
            "parameters": {},
        }
        await document_repository.create_processing_job(db, job_data)

        await audit_repository.log_event(
            db=db,
            action="DOCUMENT_VERSION_CREATED",
            entity_type="PROPERTY_DOCUMENT",
            entity_id=doc_id,
            actor_user_id=str(current_user.id),
            details={"version_number": next_ver_num, "filename": filename, "file_hash": file_hash},
        )
        await db.commit()

        asyncio.create_task(document_processing_worker.execute_job(job_id))
        return version

    async def review_field(
        self,
        db: AsyncSession,
        doc_id: str,
        field_id: str,
        action: str,
        current_user: User,
        reviewed_value: Optional[str] = None,
        review_notes: Optional[str] = None,
    ) -> DocumentExtractedField:
        """Field-level review action (CONFIRM, CORRECT, REJECT) with full provenance."""
        self._require_officer_or_admin(current_user)

        field = await document_repository.get_field_by_id(db, field_id)
        if not field:
            raise NotFoundException(f"Extracted field not found: {field_id}")

        action_upper = action.upper()
        if action_upper not in ["CONFIRM", "CORRECT", "REJECT"]:
            raise BadRequestException("Invalid field review action. Must be CONFIRM, CORRECT, or REJECT.")

        if action_upper == "CORRECT" and (reviewed_value is None or len(reviewed_value.strip()) == 0):
            raise BadRequestException("reviewed_value is required when correcting a field.")

        status_map = {
            "CONFIRM": FieldReviewStatus.CONFIRMED.value,
            "CORRECT": FieldReviewStatus.CORRECTED.value,
            "REJECT": FieldReviewStatus.REJECTED.value,
        }

        update_dict = {
            "review_status": status_map[action_upper],
            "reviewed_value": reviewed_value.strip() if reviewed_value else None,
            "reviewed_by": str(current_user.id),
            "reviewed_at": datetime.now(timezone.utc),
            "review_notes": review_notes,
        }

        updated = await document_repository.update_extracted_field(db, field_id, update_dict)

        await audit_repository.log_event(
            db=db,
            action="DOCUMENT_FIELD_REVIEWED",
            entity_type="PROPERTY_DOCUMENT",
            entity_id=doc_id,
            actor_user_id=str(current_user.id),
            details={
                "field_id": field_id,
                "field_name": field.field_name,
                "original_value": field.field_value,
                "review_action": action_upper,
                "reviewed_value": reviewed_value,
            },
        )
        await db.commit()
        return updated

    async def verify_document(
        self,
        db: AsyncSession,
        doc_id: str,
        current_user: User,
        notes: Optional[str] = None,
    ) -> PropertyDocument:
        """Officially marks property document technical verification as complete."""
        self._require_officer_or_admin(current_user)
        doc = await document_repository.get_document_by_id(db, doc_id)
        if not doc:
            raise NotFoundException(f"Property document not found: {doc_id}")

        doc.status = DocumentStatus.VERIFIED.value
        doc.metadata_json["verified_by"] = str(current_user.id)
        doc.metadata_json["verified_at"] = datetime.now(timezone.utc).isoformat()
        if notes:
            doc.metadata_json["verification_notes"] = notes

        await audit_repository.log_event(
            db=db,
            action="DOCUMENT_VERIFIED",
            entity_type="PROPERTY_DOCUMENT",
            entity_id=doc_id,
            actor_user_id=str(current_user.id),
            details={"document_reference": doc.document_reference, "notes": notes},
        )
        await db.commit()
        return doc

    async def reject_document(
        self,
        db: AsyncSession,
        doc_id: str,
        current_user: User,
        reason: str,
    ) -> PropertyDocument:
        """Rejects property document verification with required explanation."""
        self._require_officer_or_admin(current_user)
        if not reason or len(reason.strip()) < 3:
            raise BadRequestException("A valid rejection reason is required.")

        doc = await document_repository.get_document_by_id(db, doc_id)
        if not doc:
            raise NotFoundException(f"Property document not found: {doc_id}")

        doc.status = DocumentStatus.REJECTED.value
        doc.metadata_json["rejection_reason"] = reason.strip()
        doc.metadata_json["rejected_by"] = str(current_user.id)
        doc.metadata_json["rejected_at"] = datetime.now(timezone.utc).isoformat()

        await audit_repository.log_event(
            db=db,
            action="DOCUMENT_REJECTED",
            entity_type="PROPERTY_DOCUMENT",
            entity_id=doc_id,
            actor_user_id=str(current_user.id),
            details={"document_reference": doc.document_reference, "reason": reason.strip()},
        )
        await db.commit()
        return doc

    async def request_correction(
        self,
        db: AsyncSession,
        doc_id: str,
        current_user: User,
        notes: str,
    ) -> PropertyDocument:
        """Flags document as requiring surveyor or applicant correction."""
        self._require_officer_or_admin(current_user)
        if not notes or len(notes.strip()) < 3:
            raise BadRequestException("Correction notes are required.")

        doc = await document_repository.get_document_by_id(db, doc_id)
        if not doc:
            raise NotFoundException(f"Property document not found: {doc_id}")

        doc.status = DocumentStatus.REQUIRES_CORRECTION.value
        doc.metadata_json["correction_notes"] = notes.strip()
        doc.metadata_json["correction_requested_by"] = str(current_user.id)
        doc.metadata_json["correction_requested_at"] = datetime.now(timezone.utc).isoformat()

        await audit_repository.log_event(
            db=db,
            action="DOCUMENT_CORRECTION_REQUESTED",
            entity_type="PROPERTY_DOCUMENT",
            entity_id=doc_id,
            actor_user_id=str(current_user.id),
            details={"document_reference": doc.document_reference, "notes": notes.strip()},
        )
        await db.commit()
        return doc

    async def add_entity_link(
        self,
        db: AsyncSession,
        doc_id: str,
        entity_type: str,
        entity_id: str,
        current_user: User,
        link_method: str = "MANUAL",
    ) -> DocumentEntityLink:
        """Links document to a cadastral parcel, property, building, floor, or unit."""
        self._require_editor(current_user)
        doc = await document_repository.get_document_by_id(db, doc_id)
        if not doc:
            raise NotFoundException(f"Property document not found: {doc_id}")

        link_data = {
            "id": str(uuid.uuid4()),
            "document_id": doc_id,
            "entity_type": entity_type.upper(),
            "entity_id": str(entity_id),
            "link_method": link_method,
            "match_score": 1.0 if link_method == "MANUAL" else 0.85,
            "status": "CONFIRMED",
            "confirmed_by": str(current_user.id),
            "confirmed_at": datetime.now(timezone.utc),
        }
        link = await document_repository.create_entity_link(db, link_data)

        # Update primary foreign key if not set
        if entity_type.upper() == "PARCEL" and not doc.parcel_id:
            doc.parcel_id = str(entity_id)
        elif entity_type.upper() == "PROPERTY" and not doc.property_id:
            doc.property_id = str(entity_id)
        elif entity_type.upper() == "BUILDING" and not doc.building_id:
            doc.building_id = str(entity_id)
        elif entity_type.upper() == "UNIT" and not doc.unit_id:
            doc.unit_id = str(entity_id)

        await audit_repository.log_event(
            db=db,
            action="DOCUMENT_LINKED",
            entity_type="PROPERTY_DOCUMENT",
            entity_id=doc_id,
            actor_user_id=str(current_user.id),
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        await db.commit()
        return link

    async def delete_entity_link(
        self,
        db: AsyncSession,
        doc_id: str,
        link_id: str,
        current_user: User,
    ) -> bool:
        """Removes a link between a document and a cadastral entity."""
        self._require_editor(current_user)
        success = await document_repository.delete_entity_link(db, link_id)
        if success:
            await audit_repository.log_event(
                db=db,
                action="DOCUMENT_UNLINKED",
                entity_type="PROPERTY_DOCUMENT",
                entity_id=doc_id,
                actor_user_id=str(current_user.id),
                details={"link_id": link_id},
            )
            await db.commit()
        return success


document_service = DocumentService()
