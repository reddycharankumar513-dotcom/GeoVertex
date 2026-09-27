import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.document.classifier import document_classifier
from app.ai.document.extractor import document_field_extractor
from app.ai.document.matcher import document_cadastral_matcher
from app.ai.document.ocr import document_ocr_engine
from app.database.session import AsyncSessionLocal
from app.gis.validation.worker import validation_worker
from app.models.document import (
    ConfidenceLevel,
    DocumentExtractedField,
    DocumentOCRResult,
    DocumentPage,
    DocumentProcessingJob,
    DocumentStatus,
    DocumentVersion,
    FieldReviewStatus,
    PropertyDocument,
)
from app.models.validation import ValidationRun
from app.repositories.audit_repository import audit_repository
from app.repositories.validation_repository import validation_repository
from app.services.document_storage_service import document_storage_service

logger = logging.getLogger(__name__)


class DocumentProcessingWorker:
    """Asynchronous worker executing the full 10-stage Document Intelligence pipeline."""

    async def execute_job(
        self,
        job_id: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """Entrypoint for executing a queued document processing job."""
        if session is not None:
            await self._run_pipeline(session, job_id)
        else:
            async with AsyncSessionLocal() as db:
                await self._run_pipeline(db, job_id)

    async def _run_pipeline(self, db: AsyncSession, job_id: str) -> None:
        start_time = time.time()
        j_res = await db.execute(select(DocumentProcessingJob).where(DocumentProcessingJob.id == str(job_id)))
        job = j_res.scalar_one_or_none()
        if not job or job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            return

        # Load DocumentVersion and PropertyDocument
        v_res = await db.execute(select(DocumentVersion).where(DocumentVersion.id == job.document_version_id))
        version = v_res.scalar_one_or_none()
        if not version:
            job.status = "FAILED"
            job.error_code = "VERSION_NOT_FOUND"
            job.error_message = "Associated document version record was not found."
            await db.commit()
            return

        d_res = await db.execute(select(PropertyDocument).where(PropertyDocument.id == version.document_id))
        doc = d_res.scalar_one_or_none()
        if not doc:
            job.status = "FAILED"
            job.error_code = "DOCUMENT_NOT_FOUND"
            job.error_message = "Associated property document was not found."
            await db.commit()
            return

        try:
            job.status = "PROCESSING"
            job.started_at = datetime.now(timezone.utc)
            doc.status = DocumentStatus.PROCESSING.value
            version.processing_status = "PROCESSING"
            await db.commit()

            # -------------------------------------------------------------
            # Stage 1: FILE_VALIDATION
            # -------------------------------------------------------------
            job.current_stage = "FILE_VALIDATION"
            await db.commit()

            file_path = document_storage_service.get_file_path(version.storage_key)
            if not file_path.exists():
                raise FileNotFoundError(f"Document file missing at storage path {file_path}")

            # -------------------------------------------------------------
            # Stage 2: PAGE_EXTRACTION
            # -------------------------------------------------------------
            job.current_stage = "PAGE_EXTRACTION"
            await db.commit()

            page_count = 1
            if version.mime_type == "application/pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(file_path))
                    page_count = len(reader.pages)
                except Exception:
                    page_count = 1

            version.page_count = page_count
            doc.page_count = page_count
            await db.commit()

            # -------------------------------------------------------------
            # Stage 3: OCR / TEXT EXTRACTION
            # -------------------------------------------------------------
            job.current_stage = "OCR"
            await db.commit()

            ocr_res = document_ocr_engine.extract_text(file_path, version.mime_type)

            # Persist DocumentPages and DocumentOCRResult
            for p_data in ocr_res.pages:
                doc_page = DocumentPage(
                    id=str(uuid.uuid4()),
                    document_version_id=version.id,
                    page_number=p_data.page_number,
                    width=p_data.width,
                    height=p_data.height,
                    processing_status="COMPLETED" if p_data.text else "PENDING",
                    extracted_text=p_data.text,
                )
                db.add(doc_page)
                await db.flush()

                ocr_entry = DocumentOCRResult(
                    id=str(uuid.uuid4()),
                    document_version_id=version.id,
                    page_id=doc_page.id,
                    engine=ocr_res.engine,
                    engine_version=ocr_res.engine_version,
                    language=ocr_res.language,
                    text=p_data.text,
                    blocks_json=p_data.blocks,
                    confidence=p_data.confidence,
                    processing_time_ms=ocr_res.processing_time_ms,
                )
                db.add(ocr_entry)

            doc.status = DocumentStatus.OCR_COMPLETED.value
            await db.commit()

            # -------------------------------------------------------------
            # Stage 4: CLASSIFICATION
            # -------------------------------------------------------------
            job.current_stage = "CLASSIFICATION"
            await db.commit()

            if doc.document_type == "OTHER" or not doc.document_type:
                cls_res = document_classifier.classify(
                    text=ocr_res.full_text,
                    filename=version.original_filename,
                    title=doc.title,
                )
                if cls_res.status == "COMPLETED" and cls_res.predicted_type != "OTHER":
                    doc.document_type = cls_res.predicted_type
                    doc.metadata_json["classification_evidence"] = cls_res.evidence
                    doc.metadata_json["classification_confidence"] = cls_res.confidence

            # -------------------------------------------------------------
            # Stage 5: FIELD_EXTRACTION
            # -------------------------------------------------------------
            job.current_stage = "FIELD_EXTRACTION"
            await db.commit()

            field_drafts = document_field_extractor.extract_fields(ocr_res.full_text, ocr_res.pages)
            extracted_dict = {}

            for fd in field_drafts:
                f_model = DocumentExtractedField(
                    id=str(uuid.uuid4()),
                    document_version_id=version.id,
                    field_name=fd.field_name,
                    field_value=fd.field_value,
                    normalized_value=fd.normalized_value,
                    data_type=fd.data_type,
                    page_number=fd.page_number,
                    bounding_box=fd.bounding_box,
                    extraction_method=fd.extraction_method,
                    confidence=fd.confidence,
                    confidence_level=fd.confidence_level,
                    evidence_text=fd.evidence_text,
                    model_id=fd.model_id,
                    model_version=fd.model_version,
                    review_status=FieldReviewStatus.PENDING.value,
                )
                db.add(f_model)
                extracted_dict[fd.field_name] = fd.normalized_value or fd.field_value

            doc.status = DocumentStatus.EXTRACTION_COMPLETED.value
            await db.commit()

            # -------------------------------------------------------------
            # Stage 6: NORMALIZATION
            # -------------------------------------------------------------
            job.current_stage = "NORMALIZATION"
            await db.commit()

            # -------------------------------------------------------------
            # Stage 7: GEOREFERENCE_MATCHING
            # -------------------------------------------------------------
            job.current_stage = "GEOREFERENCE_MATCHING"
            await db.commit()

            candidate_links = await document_cadastral_matcher.find_candidate_links(
                db=db,
                document_id=str(doc.id),
                extracted_fields=extracted_dict,
                jurisdiction_id=str(doc.jurisdiction_id) if doc.jurisdiction_id else None,
            )
            for cl in candidate_links:
                db.add(cl)
                # If document is unlinked to parcel and an exact match candidate was found, link technically
                if not doc.parcel_id and cl.entity_type == "PARCEL" and cl.match_score == 1.0:
                    doc.parcel_id = cl.entity_id

            await db.commit()

            # -------------------------------------------------------------
            # Stage 8: VALIDATION (Phase 7 Integration)
            # -------------------------------------------------------------
            job.current_stage = "VALIDATION"
            await db.commit()

            # Create and execute Phase 7 validation run for this document
            val_run_data = {
                "id": uuid.uuid4(),
                "validation_type": "DOCUMENT_VERIFICATION",
                "target_type": "DOCUMENT",
                "target_id": str(doc.id),
                "status": "QUEUED",
                "stage": "QUEUED",
                "requested_by": job.requested_by,
                "ruleset_version": "1.0.0",
                "parameters": {},
                "summary": {},
            }
            val_run = await validation_repository.create_run(db, val_run_data)
            await db.commit()

            # Trigger Phase 7 validation worker on the document
            await validation_worker.execute_validation_run(val_run.id, session=db)
            doc.status = DocumentStatus.VALIDATION_COMPLETED.value
            await db.commit()

            # -------------------------------------------------------------
            # Stage 9: COMPLETED
            # -------------------------------------------------------------
            job.current_stage = "COMPLETED"
            job.status = "COMPLETED"
            end_time = datetime.now(timezone.utc)
            job.completed_at = end_time
            job.duration_ms = int((time.time() - start_time) * 1000)

            version.processing_status = "COMPLETED"
            doc.status = DocumentStatus.UNDER_REVIEW.value  # Human review is mandatory
            doc.updated_at = end_time

            # Log security audit trail
            await audit_repository.log_event(
                db=db,
                action="DOCUMENT_PROCESSED",
                entity_type="PROPERTY_DOCUMENT",
                entity_id=str(doc.id),
                actor_user_id=job.requested_by,
                details={
                    "document_reference": doc.document_reference,
                    "pages": doc.page_count,
                    "fields_extracted": len(field_drafts),
                    "candidate_links": len(candidate_links),
                    "duration_ms": job.duration_ms,
                },
            )

            await db.commit()
            logger.info(f"Document processing completed for {doc.document_reference} in {job.duration_ms}ms")

        except Exception as e:
            logger.exception(f"Document processing job {job_id} failed: {e}")
            job.status = "FAILED"
            job.current_stage = "FAILED"
            job.error_code = "PROCESSING_FAILED"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            doc.status = DocumentStatus.FAILED.value
            version.processing_status = "FAILED"
            await db.commit()


document_processing_worker = DocumentProcessingWorker()
