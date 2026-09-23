import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic asynchronous repository defining CRUD interactions."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalars().first()

    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count(self, db: AsyncSession) -> int:
        result = await db.execute(select(func.count(self.model.id)))
        return result.scalar_one()

    async def create(self, db: AsyncSession, obj: ModelType) -> ModelType:
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def delete_by_id(self, db: AsyncSession, id: uuid.UUID) -> bool:
        result = await db.execute(delete(self.model).where(self.model.id == id))
        await db.flush()
        return result.rowcount > 0
