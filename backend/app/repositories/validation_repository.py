import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.validation import ValidationIssue, ValidationRun


class ValidationRepository:
    """Repository handling database persistence and querying for validation runs and issues."""

    # -------------------------------------------------------------
    # Validation Runs
    # -------------------------------------------------------------

    async def create_run(self, db: AsyncSession, data: Dict[str, Any]) -> ValidationRun:
        run = ValidationRun(**data)
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run

    async def get_run_by_id(self, db: AsyncSession, run_id: uuid.UUID) -> Optional[ValidationRun]:
        stmt = (
            select(ValidationRun)
            .where(ValidationRun.id == run_id)
            .options(selectinload(ValidationRun.issues))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        validation_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ValidationRun], int]:
        stmt = select(ValidationRun)
        if status:
            stmt = stmt.where(ValidationRun.status == status.upper())
        if validation_type:
            stmt = stmt.where(ValidationRun.validation_type == validation_type.upper())
        if target_type:
            stmt = stmt.where(ValidationRun.target_type == target_type.upper())
        if target_id:
            stmt = stmt.where(ValidationRun.target_id == target_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(ValidationRun.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_run(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        update_data: Dict[str, Any],
    ) -> Optional[ValidationRun]:
        run = await self.get_run_by_id(db, run_id)
        if not run:
            return None
        for key, value in update_data.items():
            if hasattr(run, key):
                setattr(run, key, value)
        await db.commit()
        await db.refresh(run)
        return run

    # -------------------------------------------------------------
    # Validation Issues
    # -------------------------------------------------------------

    async def create_issues(
        self,
        db: AsyncSession,
        issues: List[Dict[str, Any]],
    ) -> List[ValidationIssue]:
        issue_objs = [ValidationIssue(**item) for item in issues]
        db.add_all(issue_objs)
        await db.commit()
        return issue_objs

    async def get_issue_by_id(
        self,
        db: AsyncSession,
        issue_id: uuid.UUID,
    ) -> Optional[ValidationIssue]:
        stmt = select(ValidationIssue).where(ValidationIssue.id == issue_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_issues(
        self,
        db: AsyncSession,
        run_id: Optional[uuid.UUID] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        rule_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ValidationIssue], int]:
        stmt = select(ValidationIssue)
        if run_id:
            stmt = stmt.where(ValidationIssue.validation_run_id == run_id)
        if severity:
            stmt = stmt.where(ValidationIssue.severity == severity.upper())
        if status:
            stmt = stmt.where(ValidationIssue.status == status.upper())
        if category:
            stmt = stmt.where(ValidationIssue.category == category.upper())
        if rule_id:
            stmt = stmt.where(ValidationIssue.rule_id == rule_id)
        if entity_type:
            stmt = stmt.where(ValidationIssue.entity_type == entity_type.upper())
        if entity_id:
            stmt = stmt.where(ValidationIssue.entity_id == entity_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(ValidationIssue.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_issue(
        self,
        db: AsyncSession,
        issue_id: uuid.UUID,
        update_data: Dict[str, Any],
    ) -> Optional[ValidationIssue]:
        issue = await self.get_issue_by_id(db, issue_id)
        if not issue:
            return None
        for key, value in update_data.items():
            if hasattr(issue, key):
                setattr(issue, key, value)
        await db.commit()
        await db.refresh(issue)
        return issue


validation_repository = ValidationRepository()
