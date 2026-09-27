import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import BackgroundTasks
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestException, ForbiddenException, NotFoundException, ValidationException
from app.gis.validation.registry import rule_registry
from app.gis.validation.worker import validation_worker
from app.models.user import User, UserRole
from app.models.validation import ValidationIssue, ValidationRun
from app.repositories.audit_repository import audit_repository
from app.repositories.validation_repository import validation_repository
from app.schemas.validation import (
    EntityValidationSummaryResponse,
    ValidationIssueActionRequest,
    ValidationRunCreateRequest,
)


class ValidationService:
    """Business logic service for topology validation runs, issue lifecycle, and rule querying."""

    async def dispatch_validation_run(
        self,
        db: AsyncSession,
        request: ValidationRunCreateRequest,
        current_user: User,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> ValidationRun:
        """Dispatches an asynchronous topology validation run."""
        # Citizen role is read-only
        if current_user.role == UserRole.CITIZEN:
            raise ForbiddenException("Citizens are not permitted to trigger cadastral validation jobs.")

        parameters = {
            "rules_filter": request.rules_filter,
            "tolerance_overrides": request.tolerance_overrides,
        }
        if request.geometry_wkt:
            parameters["geometry_wkt"] = request.geometry_wkt

        run_data = {
            "id": uuid.uuid4(),
            "validation_type": (request.validation_type or "SINGLE_ENTITY").upper(),
            "target_type": request.target_type.upper(),
            "target_id": request.target_id,
            "status": "QUEUED",
            "stage": "QUEUED",
            "requested_by": current_user.id,
            "ruleset_version": "1.0.0",
            "parameters": parameters,
            "summary": {},
        }

        run = await validation_repository.create_run(db, run_data)

        await audit_repository.log_event(
            db=db,
            action="VALIDATION_REQUESTED",
            entity_type="VALIDATION_RUN",
            entity_id=str(run.id),
            actor_user_id=current_user.id,
            details={
                "validation_type": run.validation_type,
                "target_type": run.target_type,
                "target_id": run.target_id,
            },
        )
        await db.commit()

        # Dispatch background execution
        if background_tasks:
            background_tasks.add_task(validation_worker.execute_validation_run, run.id)
        else:
            asyncio.create_task(validation_worker.execute_validation_run(run.id))

        return run

    async def get_run(self, db: AsyncSession, run_id: uuid.UUID) -> ValidationRun:
        run = await validation_repository.get_run_by_id(db, run_id)
        if not run:
            raise NotFoundException(f"Validation run with ID '{run_id}' not found.")
        return run

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
        return await validation_repository.list_runs(
            db=db,
            status=status,
            validation_type=validation_type,
            target_type=target_type,
            target_id=target_id,
            skip=skip,
            limit=limit,
        )

    async def cancel_run(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        current_user: User,
    ) -> ValidationRun:
        run = await self.get_run(db, run_id)
        if run.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            raise ValidationException(f"Cannot cancel run {run_id} in terminal state '{run.status}'.")

        updated = await validation_repository.update_run(
            db,
            run_id,
            {"status": "CANCELLED", "stage": "CANCELLED", "completed_at": datetime.now(timezone.utc)},
        )

        await audit_repository.log_event(
            db=db,
            action="VALIDATION_CANCELLED",
            entity_type="VALIDATION_RUN",
            entity_id=str(run_id),
            actor_user_id=current_user.id,
            details={"previous_status": run.status},
        )
        await db.commit()
        return updated or run

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
        return await validation_repository.list_issues(
            db=db,
            run_id=run_id,
            severity=severity,
            status=status,
            category=category,
            rule_id=rule_id,
            entity_type=entity_type,
            entity_id=entity_id,
            skip=skip,
            limit=limit,
        )

    async def get_issue(self, db: AsyncSession, issue_id: uuid.UUID) -> ValidationIssue:
        issue = await validation_repository.get_issue_by_id(db, issue_id)
        if not issue:
            raise NotFoundException(f"Validation issue with ID '{issue_id}' not found.")
        return issue

    async def review_issue(
        self,
        db: AsyncSession,
        issue_id: uuid.UUID,
        request: ValidationIssueActionRequest,
        current_user: User,
    ) -> ValidationIssue:
        """Executes human review on a validation issue (Acknowledge, Resolve, Waive)."""
        issue = await self.get_issue(db, issue_id)
        action = request.action.upper()
        now = datetime.now(timezone.utc)

        # RBAC Enforcement:
        # - Citizen: Forbidden
        # - Surveyor: May ACKNOWLEDGE
        # - Officer & Admin: May ACKNOWLEDGE, RESOLVE, WAIVE
        user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if user_role == UserRole.CITIZEN.value:
            raise ForbiddenException("Citizens cannot review cadastral validation issues.")

        if action in ["RESOLVE", "WAIVE"] and user_role not in [UserRole.ADMIN.value, UserRole.GOVERNMENT_OFFICER.value]:
            raise ForbiddenException(f"Role '{user_role}' is not authorized to {action.lower()} issues. Officer or Admin required.")

        update_fields: Dict[str, Any] = {}

        if action == "ACKNOWLEDGE":
            update_fields = {
                "status": "ACKNOWLEDGED",
                "acknowledged_at": now,
                "acknowledged_by": current_user.id,
            }
            audit_action = "ISSUE_ACKNOWLEDGED"

        elif action == "RESOLVE":
            if not request.note or not request.note.strip():
                raise ValidationException("A resolution note is required when resolving an issue.")
            update_fields = {
                "status": "RESOLVED",
                "resolved_at": now,
                "resolved_by": current_user.id,
                "resolution_note": request.note.strip(),
            }
            audit_action = "ISSUE_RESOLVED"

        elif action == "WAIVE":
            if not request.reason or not request.reason.strip():
                raise ValidationException("A waiver reason is required when waiving an issue.")
            update_fields = {
                "status": "WAIVED",
                "waived_at": now,
                "waived_by": current_user.id,
                "waiver_reason": request.reason.strip(),
            }
            audit_action = "ISSUE_WAIVED"

        else:
            raise ValidationException(f"Unsupported review action '{action}'. Use ACKNOWLEDGE, RESOLVE, or WAIVE.")

        updated_issue = await validation_repository.update_issue(db, issue_id, update_fields)

        # Update run summary counts if applicable
        if issue.validation_run_id:
            run = await validation_repository.get_run_by_id(db, issue.validation_run_id)
            if run and run.summary:
                summary = dict(run.summary)
                if action == "RESOLVE":
                    summary["resolved"] = summary.get("resolved", 0) + 1
                    summary["open"] = max(0, summary.get("open", 1) - 1)
                elif action == "WAIVE":
                    summary["waived"] = summary.get("waived", 0) + 1
                    summary["open"] = max(0, summary.get("open", 1) - 1)
                elif action == "ACKNOWLEDGE":
                    summary["acknowledged"] = summary.get("acknowledged", 0) + 1
                await validation_repository.update_run(db, run.id, {"summary": summary})

        await audit_repository.log_event(
            db=db,
            action=audit_action,
            entity_type="VALIDATION_ISSUE",
            entity_id=str(issue.id),
            actor_user_id=current_user.id,
            details={
                "rule_id": issue.rule_id,
                "previous_status": issue.status,
                "new_status": update_fields.get("status"),
                "note_or_reason": request.note or request.reason,
            },
        )
        await db.commit()
        return updated_issue or issue

    async def get_entity_validation_summary(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
    ) -> EntityValidationSummaryResponse:
        """Retrieves aggregated validation findings for a specific entity."""
        stmt = (
            select(ValidationIssue)
            .where(ValidationIssue.entity_type == entity_type.upper(), ValidationIssue.entity_id == entity_id)
        )
        result = await db.execute(stmt)
        issues = list(result.scalars().all())

        latest_run_stmt = (
            select(ValidationRun)
            .where(ValidationRun.target_type == entity_type.upper(), ValidationRun.target_id == entity_id)
            .order_by(desc(ValidationRun.created_at))
            .limit(1)
        )
        run_res = await db.execute(latest_run_stmt)
        latest_run = run_res.scalar_one_or_none()

        total = len(issues)
        critical = sum(1 for i in issues if i.severity == "CRITICAL" and i.status == "OPEN")
        errors = sum(1 for i in issues if i.severity == "ERROR" and i.status == "OPEN")
        warnings = sum(1 for i in issues if i.severity == "WARNING" and i.status == "OPEN")
        infos = sum(1 for i in issues if i.severity == "INFO" and i.status == "OPEN")
        open_count = sum(1 for i in issues if i.status == "OPEN")
        resolved = sum(1 for i in issues if i.status == "RESOLVED")
        waived = sum(1 for i in issues if i.status == "WAIVED")

        status_str = "VALID"
        if critical > 0:
            status_str = "CRITICAL_ISSUES"
        elif errors > 0:
            status_str = "ERROR_ISSUES"
        elif warnings > 0:
            status_str = "WARNING_ISSUES"
        elif total == 0:
            status_str = "UNVALIDATED"

        return EntityValidationSummaryResponse(
            entity_type=entity_type.upper(),
            entity_id=entity_id,
            latest_run_id=latest_run.id if latest_run else None,
            status=status_str,
            total_issues=total,
            critical_issues=critical,
            error_issues=errors,
            warning_issues=warnings,
            info_issues=infos,
            open_issues=open_count,
            resolved_issues=resolved,
            waived_issues=waived,
            last_validated_at=latest_run.completed_at if latest_run else None,
        )

    def list_rules(
        self,
        category: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        rules = rule_registry.list_rules(category=category, target_type=target_type)
        return [r.explain() for r in rules]

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        rule = rule_registry.get_rule(rule_id)
        return rule.explain() if rule else None


validation_service = ValidationService()
