from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, or_, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import (
    DocumentEntityLink,
    DocumentExtractedField,
    DocumentOCRResult,
    DocumentPage,
    DocumentProcessingJob,
    DocumentStatus,
    DocumentVersion,
    FieldReviewStatus,
    PropertyDocument,
)


class DocumentRepository:
    """Data access repository for property documents, versions, OCR, and extracted fields."""

    async def create_document(self, db: AsyncSession, doc_data: Dict[str, Any]) -> PropertyDocument:
        doc = PropertyDocument(**doc_data)
        db.add(doc)
        await db.flush()
        return doc

    async def get_document_by_id(self, db: AsyncSession, doc_id: str) -> Optional[PropertyDocument]:
        res = await db.execute(select(PropertyDocument).where(PropertyDocument.id == str(doc_id)))
        return res.scalar_one_or_none()

    async def get_document_by_ref(self, db: AsyncSession, doc_ref: str) -> Optional[PropertyDocument]:
        res = await db.execute(select(PropertyDocument).where(PropertyDocument.document_reference == doc_ref))
        return res.scalar_one_or_none()

    async def list_documents(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        jurisdiction_id: Optional[str] = None,
        parcel_id: Optional[str] = None,
        property_id: Optional[str] = None,
        building_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[PropertyDocument], int]:
        query = select(PropertyDocument)

        filters = []
        if status:
            filters.append(PropertyDocument.status == status)
        if document_type:
            filters.append(PropertyDocument.document_type == document_type)
        if jurisdiction_id:
            filters.append(PropertyDocument.jurisdiction_id == jurisdiction_id)
        if parcel_id:
            filters.append(PropertyDocument.parcel_id == parcel_id)
        if property_id:
            filters.append(PropertyDocument.property_id == property_id)
        if building_id:
            filters.append(PropertyDocument.building_id == building_id)

        if search:
            s = f"%{search.strip()}%"
            filters.append(
                or_(
                    PropertyDocument.document_reference.ilike(s),
                    PropertyDocument.title.ilike(s),
                    PropertyDocument.description.ilike(s),
                    PropertyDocument.issuing_authority.ilike(s),
                )
            )

        if filters:
            query = query.where(and_(*filters))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        query = query.order_by(PropertyDocument.created_at.desc()).offset(skip).limit(limit)
        items = (await db.execute(query)).scalars().all()

        return list(items), total

    async def update_document(
        self,
        db: AsyncSession,
        doc_id: str,
        update_data: Dict[str, Any],
    ) -> Optional[PropertyDocument]:
        doc = await self.get_document_by_id(db, doc_id)
        if not doc:
            return None
        for k, v in update_data.items():
            if hasattr(doc, k):
                setattr(doc, k, v)
        doc.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return doc

    # -------------------------------------------------------------
    # Versioning
    # -------------------------------------------------------------
    async def create_version(self, db: AsyncSession, version_data: Dict[str, Any]) -> DocumentVersion:
        ver = DocumentVersion(**version_data)
        db.add(ver)
        await db.flush()
        return ver

    async def get_version_by_id(self, db: AsyncSession, version_id: str) -> Optional[DocumentVersion]:
        res = await db.execute(select(DocumentVersion).where(DocumentVersion.id == str(version_id)))
        return res.scalar_one_or_none()

    async def get_versions(self, db: AsyncSession, doc_id: str) -> List[DocumentVersion]:
        res = await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == str(doc_id))
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(res.scalars().all())

    # -------------------------------------------------------------
    # Pages & OCR Results
    # -------------------------------------------------------------
    async def get_pages(self, db: AsyncSession, version_id: str) -> List[DocumentPage]:
        res = await db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_version_id == str(version_id))
            .order_by(DocumentPage.page_number.asc())
        )
        return list(res.scalars().all())

    async def get_ocr_results(self, db: AsyncSession, version_id: str) -> List[DocumentOCRResult]:
        res = await db.execute(
            select(DocumentOCRResult)
            .where(DocumentOCRResult.document_version_id == str(version_id))
            .order_by(DocumentOCRResult.created_at.asc())
        )
        return list(res.scalars().all())

    # -------------------------------------------------------------
    # Extracted Fields & Review Actions
    # -------------------------------------------------------------
    async def get_extracted_fields(self, db: AsyncSession, version_id: str) -> List[DocumentExtractedField]:
        res = await db.execute(
            select(DocumentExtractedField)
            .where(DocumentExtractedField.document_version_id == str(version_id))
            .order_by(DocumentExtractedField.field_name.asc())
        )
        return list(res.scalars().all())

    async def get_field_by_id(self, db: AsyncSession, field_id: str) -> Optional[DocumentExtractedField]:
        res = await db.execute(select(DocumentExtractedField).where(DocumentExtractedField.id == str(field_id)))
        return res.scalar_one_or_none()

    async def update_extracted_field(
        self,
        db: AsyncSession,
        field_id: str,
        update_data: Dict[str, Any],
    ) -> Optional[DocumentExtractedField]:
        f = await self.get_field_by_id(db, field_id)
        if not f:
            return None
        for k, v in update_data.items():
            if hasattr(f, k):
                setattr(f, k, v)
        f.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return f

    # -------------------------------------------------------------
    # Processing Jobs
    # -------------------------------------------------------------
    async def create_processing_job(self, db: AsyncSession, job_data: Dict[str, Any]) -> DocumentProcessingJob:
        job = DocumentProcessingJob(**job_data)
        db.add(job)
        await db.flush()
        return job

    async def get_job_by_id(self, db: AsyncSession, job_id: str) -> Optional[DocumentProcessingJob]:
        res = await db.execute(select(DocumentProcessingJob).where(DocumentProcessingJob.id == str(job_id)))
        return res.scalar_one_or_none()

    async def get_jobs_for_version(self, db: AsyncSession, version_id: str) -> List[DocumentProcessingJob]:
        res = await db.execute(
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.document_version_id == str(version_id))
            .order_by(DocumentProcessingJob.created_at.desc())
        )
        return list(res.scalars().all())

    # -------------------------------------------------------------
    # Entity Links
    # -------------------------------------------------------------
    async def get_entity_links(self, db: AsyncSession, doc_id: str) -> List[DocumentEntityLink]:
        res = await db.execute(
            select(DocumentEntityLink)
            .where(DocumentEntityLink.document_id == str(doc_id))
            .order_by(DocumentEntityLink.match_score.desc())
        )
        return list(res.scalars().all())

    async def create_entity_link(self, db: AsyncSession, link_data: Dict[str, Any]) -> DocumentEntityLink:
        link = DocumentEntityLink(**link_data)
        db.add(link)
        await db.flush()
        return link

    async def delete_entity_link(self, db: AsyncSession, link_id: str) -> bool:
        res = await db.execute(select(DocumentEntityLink).where(DocumentEntityLink.id == str(link_id)))
        link = res.scalar_one_or_none()
        if link:
            await db.delete(link)
            return True
        return False

    async def confirm_entity_link(
        self,
        db: AsyncSession,
        link_id: str,
        user_id: str,
    ) -> Optional[DocumentEntityLink]:
        res = await db.execute(select(DocumentEntityLink).where(DocumentEntityLink.id == str(link_id)))
        link = res.scalar_one_or_none()
        if not link:
            return None
        link.status = "CONFIRMED"
        link.confirmed_by = user_id
        link.confirmed_at = datetime.now(timezone.utc)
        await db.flush()
        return link

    # -------------------------------------------------------------
    # Dashboard Metrics (Section 55)
    # -------------------------------------------------------------
    async def get_dashboard_metrics(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        filters = []
        if jurisdiction_id:
            filters.append(PropertyDocument.jurisdiction_id == jurisdiction_id)

        base_q = select(PropertyDocument)
        if filters:
            base_q = base_q.where(and_(*filters))

        total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()

        # Count by status
        status_q = select(PropertyDocument.status, func.count(PropertyDocument.id)).group_by(PropertyDocument.status)
        if filters:
            status_q = status_q.where(and_(*filters))
        status_counts = dict((await db.execute(status_q)).all())

        # Count by type
        type_q = select(PropertyDocument.document_type, func.count(PropertyDocument.id)).group_by(PropertyDocument.document_type)
        if filters:
            type_q = type_q.where(and_(*filters))
        type_counts = dict((await db.execute(type_q)).all())

        return {
            "total_documents": total,
            "processing": status_counts.get(DocumentStatus.PROCESSING.value, 0) + status_counts.get(DocumentStatus.QUEUED.value, 0),
            "under_review": status_counts.get(DocumentStatus.UNDER_REVIEW.value, 0),
            "verified": status_counts.get(DocumentStatus.VERIFIED.value, 0),
            "requires_correction": status_counts.get(DocumentStatus.REQUIRES_CORRECTION.value, 0),
            "rejected": status_counts.get(DocumentStatus.REJECTED.value, 0),
            "failed": status_counts.get(DocumentStatus.FAILED.value, 0),
            "by_status": status_counts,
            "by_type": type_counts,
        }


document_repository = DocumentRepository()
