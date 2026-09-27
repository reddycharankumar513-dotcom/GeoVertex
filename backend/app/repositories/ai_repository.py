import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai import (
    AIDataset,
    AIEvaluationRun,
    AIModel,
    AIModelVersion,
    AIProcessingJob,
    AIReview,
    BuildingExtractionResult,
    FloorExtractionResult,
)
from app.repositories.base import BaseRepository


class AIJobRepository(BaseRepository[AIProcessingJob]):
    def __init__(self):
        super().__init__(AIProcessingJob)

    async def get_by_client_request_id(
        self,
        db: AsyncSession,
        client_request_id: str,
    ) -> Optional[AIProcessingJob]:
        stmt = select(AIProcessingJob).where(AIProcessingJob.client_request_id == client_request_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_jobs(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        requested_by: Optional[uuid.UUID] = None,
        model_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AIProcessingJob], int]:
        stmt = select(AIProcessingJob)
        count_stmt = select(func.count(AIProcessingJob.id))

        if status:
            stmt = stmt.where(AIProcessingJob.status == status)
            count_stmt = count_stmt.where(AIProcessingJob.status == status)
        if job_type:
            stmt = stmt.where(AIProcessingJob.job_type == job_type)
            count_stmt = count_stmt.where(AIProcessingJob.job_type == job_type)
        if target_type:
            stmt = stmt.where(AIProcessingJob.target_type == target_type)
            count_stmt = count_stmt.where(AIProcessingJob.target_type == target_type)
        if target_id:
            stmt = stmt.where(AIProcessingJob.target_id == target_id)
            count_stmt = count_stmt.where(AIProcessingJob.target_id == target_id)
        if requested_by:
            stmt = stmt.where(AIProcessingJob.requested_by == requested_by)
            count_stmt = count_stmt.where(AIProcessingJob.requested_by == requested_by)
        if model_id:
            stmt = stmt.where(AIProcessingJob.model_id == model_id)
            count_stmt = count_stmt.where(AIProcessingJob.model_id == model_id)

        stmt = stmt.order_by(desc(AIProcessingJob.created_at)).offset(skip).limit(limit)

        items_res = await db.execute(stmt)
        count_res = await db.execute(count_stmt)

        return list(items_res.scalars().all()), int(count_res.scalar() or 0)


class BuildingExtractionResultRepository(BaseRepository[BuildingExtractionResult]):
    def __init__(self):
        super().__init__(BuildingExtractionResult)

    async def get_by_job_id(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
    ) -> List[BuildingExtractionResult]:
        stmt = select(BuildingExtractionResult).where(BuildingExtractionResult.job_id == job_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_results(
        self,
        db: AsyncSession,
        target_id: Optional[str] = None,
        status: Optional[str] = None,
        model_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BuildingExtractionResult], int]:
        stmt = select(BuildingExtractionResult)
        count_stmt = select(func.count(BuildingExtractionResult.id))

        if target_id:
            stmt = stmt.where(BuildingExtractionResult.source_target_id == target_id)
            count_stmt = count_stmt.where(BuildingExtractionResult.source_target_id == target_id)
        if status:
            stmt = stmt.where(BuildingExtractionResult.status == status)
            count_stmt = count_stmt.where(BuildingExtractionResult.status == status)
        if model_id:
            stmt = stmt.where(BuildingExtractionResult.model_id == model_id)
            count_stmt = count_stmt.where(BuildingExtractionResult.model_id == model_id)

        stmt = stmt.order_by(desc(BuildingExtractionResult.created_at)).offset(skip).limit(limit)

        items_res = await db.execute(stmt)
        count_res = await db.execute(count_stmt)

        return list(items_res.scalars().all()), int(count_res.scalar() or 0)


class FloorExtractionResultRepository(BaseRepository[FloorExtractionResult]):
    def __init__(self):
        super().__init__(FloorExtractionResult)

    async def get_by_job_id(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
    ) -> List[FloorExtractionResult]:
        stmt = select(FloorExtractionResult).where(FloorExtractionResult.job_id == job_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_results(
        self,
        db: AsyncSession,
        building_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[FloorExtractionResult], int]:
        stmt = select(FloorExtractionResult)
        count_stmt = select(func.count(FloorExtractionResult.id))

        if building_id:
            stmt = stmt.where(FloorExtractionResult.building_id == building_id)
            count_stmt = count_stmt.where(FloorExtractionResult.building_id == building_id)
        if status:
            stmt = stmt.where(FloorExtractionResult.status == status)
            count_stmt = count_stmt.where(FloorExtractionResult.status == status)

        stmt = stmt.order_by(FloorExtractionResult.candidate_floor_number).offset(skip).limit(limit)

        items_res = await db.execute(stmt)
        count_res = await db.execute(count_stmt)

        return list(items_res.scalars().all()), int(count_res.scalar() or 0)


class AIReviewRepository(BaseRepository[AIReview]):
    def __init__(self):
        super().__init__(AIReview)

    async def get_by_result(
        self,
        db: AsyncSession,
        result_type: str,
        result_id: uuid.UUID,
    ) -> Optional[AIReview]:
        stmt = select(AIReview).where(
            AIReview.result_type == result_type,
            AIReview.result_id == result_id,
        ).order_by(desc(AIReview.created_at))
        result = await db.execute(stmt)
        return result.scalars().first()


class AIModelRepository(BaseRepository[AIModel]):
    def __init__(self):
        super().__init__(AIModel)

    async def get_by_model_id(
        self,
        db: AsyncSession,
        model_id: str,
    ) -> Optional[AIModel]:
        stmt = (
            select(AIModel)
            .options(selectinload(AIModel.versions))
            .where(AIModel.model_id == model_id)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_models(
        self,
        db: AsyncSession,
    ) -> List[AIModel]:
        stmt = select(AIModel).options(selectinload(AIModel.versions)).order_by(AIModel.model_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())


class AIDatasetRepository(BaseRepository[AIDataset]):
    def __init__(self):
        super().__init__(AIDataset)

    async def get_by_dataset_id(
        self,
        db: AsyncSession,
        dataset_id: str,
    ) -> Optional[AIDataset]:
        stmt = select(AIDataset).where(AIDataset.dataset_id == dataset_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_datasets(
        self,
        db: AsyncSession,
    ) -> List[AIDataset]:
        stmt = select(AIDataset).order_by(AIDataset.created_at)
        result = await db.execute(stmt)
        return list(result.scalars().all())


class AIEvaluationRunRepository(BaseRepository[AIEvaluationRun]):
    def __init__(self):
        super().__init__(AIEvaluationRun)

    async def list_runs(
        self,
        db: AsyncSession,
        dataset_id: Optional[uuid.UUID] = None,
        model_id: Optional[str] = None,
    ) -> List[AIEvaluationRun]:
        stmt = select(AIEvaluationRun)
        if dataset_id:
            stmt = stmt.where(AIEvaluationRun.dataset_id == dataset_id)
        if model_id:
            stmt = stmt.where(AIEvaluationRun.model_id == model_id)
        stmt = stmt.order_by(desc(AIEvaluationRun.created_at))
        result = await db.execute(stmt)
        return list(result.scalars().all())


ai_job_repository = AIJobRepository()
building_result_repository = BuildingExtractionResultRepository()
floor_result_repository = FloorExtractionResultRepository()
ai_review_repository = AIReviewRepository()
ai_model_repository = AIModelRepository()
ai_dataset_repository = AIDatasetRepository()
ai_evaluation_repository = AIEvaluationRunRepository()
