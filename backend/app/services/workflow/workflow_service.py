"""End-to-End Workflow Service Orchestrator for Citizen and Government Operations."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.workflow import (
    CaseMessage,
    CitizenPropertyLink,
    NotificationType,
    RequestPriority,
    RequestStatus,
    ServiceRequest,
    ServiceRequestEvent,
    ServiceType,
    TaskStatus,
    TaskType,
    WorkflowTask,
)
from app.models.user import User, UserRole
from app.models.property import Property
from app.models.parcel import Parcel
from app.models.audit import AuditEvent
from app.models.survey import SurveyProject, SurveyAssignment
from app.models.document import PropertyDocument, DocumentEntityLink
from app.models.validation import ValidationRun, ValidationIssue
from app.models.temporal import ChangeCandidate
from app.models.utility import UtilityClash

from app.repositories.workflow_repository import WorkflowRepository
from app.services.workflow.state_machine import WorkflowStateMachine, WorkflowStateError
from app.services.workflow.sla_engine import SLAEngine
from app.services.workflow.notification_service import NotificationService

logger = logging.getLogger(__name__)


class WorkflowAuthorizationError(Exception):
    pass


class WorkflowValidationError(Exception):
    pass


class WorkflowService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = WorkflowRepository(session)
        self.notif_service = NotificationService()

    # 1. Reference Generators
    @staticmethod
    def generate_service_reference(seq: int = 1) -> str:
        current_year = datetime.now(timezone.utc).year
        random_suffix = str(uuid.uuid4().hex[:6]).upper()
        return f"GV-SR-{current_year}-{random_suffix}"

    @staticmethod
    def generate_case_reference(seq: int = 1) -> str:
        current_year = datetime.now(timezone.utc).year
        random_suffix = str(uuid.uuid4().hex[:6]).upper()
        return f"GV-CASE-{current_year}-{random_suffix}"

    # 2. Service Request Creation
    async def create_service_request(
        self,
        citizen: User,
        data: Dict[str, Any],
    ) -> ServiceRequest:
        # Validate service type
        service_type = await self.repo.get_service_type(data["request_type"])
        if not service_type or not service_type.active:
            raise WorkflowValidationError(f"Invalid or inactive service type '{data['request_type']}'")

        # Object-level authorization: if property_id is provided, citizen must have verified authorization
        property_id = data.get("property_id")
        parcel_id = data.get("parcel_id")
        if property_id:
            has_access = await self.repo.verify_citizen_property_access(citizen.id, property_id)
            if not has_access and citizen.role == UserRole.CITIZEN.value:
                raise WorkflowAuthorizationError("Citizen is not authorized to submit requests for this property")

            # Link parcel_id from property if not explicitly set
            if not parcel_id:
                prop = await self.session.get(Property, property_id)
                if prop:
                    parcel_id = prop.parcel_id

        req_ref = self.generate_service_reference()
        case_ref = self.generate_case_reference()
        now = datetime.now(timezone.utc)

        # Compute SLA due date
        due_at = SLAEngine.calculate_due_date(now, service_type.completion_sla_hours)

        req = ServiceRequest(
            request_reference=req_ref,
            case_reference=case_ref,
            citizen_id=citizen.id,
            jurisdiction_id=data["jurisdiction_id"],
            property_id=property_id,
            parcel_id=parcel_id,
            building_id=data.get("building_id"),
            floor_id=data.get("floor_id"),
            unit_id=data.get("unit_id"),
            request_type=data["request_type"],
            title=data["title"],
            description=data["description"],
            status=RequestStatus.SUBMITTED.value,
            priority=data.get("priority", RequestPriority.NORMAL.value),
            submitted_at=now,
            due_at=due_at,
            metadata_json=data.get("metadata_json", {}),
        )

        saved = await self.repo.create_service_request(req)

        # Record initial creation event
        event = ServiceRequestEvent(
            service_request_id=saved.id,
            previous_status=None,
            new_status=RequestStatus.SUBMITTED.value,
            actor_id=citizen.id,
            actor_role=citizen.role,
            event_type="SUBMITTED",
            reason="Service request submitted by citizen",
            comment=data.get("description"),
            is_internal=False,
        )
        await self.repo.add_event(event)

        # Create triage task in Government work queue
        task = WorkflowTask(
            service_request_id=saved.id,
            task_type=TaskType.GENERAL_REQUEST.value,
            status=TaskStatus.OPEN.value,
            priority=saved.priority,
            due_at=SLAEngine.calculate_due_date(now, service_type.response_sla_hours),
            created_by=citizen.id,
        )
        await self.repo.create_task(task)

        # Notify citizen of successful submission
        await self.notif_service.create_notification(
            session=self.session,
            user_id=citizen.id,
            notification_type=NotificationType.REQUEST_SUBMITTED.value,
            title="Service Request Submitted",
            message=f"Your request '{saved.title}' has been submitted under reference {saved.request_reference}.",
            related_entity_type="SERVICE_REQUEST",
            related_entity_id=str(saved.id),
        )

        return saved

    # 3. Controlled State Transitions
    async def transition_request(
        self,
        request_id: uuid.UUID,
        actor: User,
        target_status_str: str,
        reason: Optional[str] = None,
        comment: Optional[str] = None,
        is_internal: bool = False,
    ) -> ServiceRequest:
        req = await self.repo.get_service_request(request_id)
        if not req:
            raise WorkflowValidationError(f"Service request {request_id} not found")

        # Object-level authorization
        if actor.role == UserRole.CITIZEN.value:
            if req.citizen_id != actor.id:
                raise WorkflowAuthorizationError("Citizens cannot modify service requests belonging to other users")
            is_internal = False  # Citizens can never create internal notes

        elif actor.role == UserRole.GOVERNMENT_OFFICER.value:
            # Check jurisdiction boundaries
            if actor.jurisdiction_id and req.jurisdiction_id != actor.jurisdiction_id:
                raise WorkflowAuthorizationError("Government officers can only manage cases within their assigned jurisdiction")

        current_status = RequestStatus(req.status)
        target_status = RequestStatus(target_status_str)

        # Validate transition using deterministic state machine
        WorkflowStateMachine.validate_transition(
            current_status=current_status,
            target_status=target_status,
            actor_role=actor.role,
            reason=reason,
        )

        now = datetime.now(timezone.utc)
        req.status = target_status.value

        if target_status == RequestStatus.ACKNOWLEDGED:
            req.acknowledged_at = now
        elif target_status in (RequestStatus.COMPLETED, RequestStatus.REJECTED, RequestStatus.CANCELLED):
            req.completed_at = now

        # Add timeline event
        event = ServiceRequestEvent(
            service_request_id=req.id,
            previous_status=current_status.value,
            new_status=target_status.value,
            actor_id=actor.id,
            actor_role=actor.role,
            event_type="STATUS_CHANGE",
            reason=reason,
            comment=comment,
            is_internal=is_internal,
        )
        await self.repo.add_event(event)

        # Notify citizen when status changes (unless it's an internal note)
        notif_msg_map = {
            RequestStatus.ACKNOWLEDGED: (NotificationType.REQUEST_ACKNOWLEDGED.value, "Your request has been acknowledged by cadastral authorities."),
            RequestStatus.REVISION_REQUIRED: (NotificationType.REVISION_REQUESTED.value, f"Revision requested: {reason}"),
            RequestStatus.APPROVED: (NotificationType.REQUEST_APPROVED.value, "Your service request has been approved by the cadastral officer."),
            RequestStatus.REJECTED: (NotificationType.REQUEST_REJECTED.value, f"Your service request was rejected. Reason: {reason}"),
            RequestStatus.COMPLETED: (NotificationType.REQUEST_COMPLETED.value, "Your service request has been completed."),
        }
        if target_status in notif_msg_map and not is_internal:
            ntype, nmsg = notif_msg_map[target_status]
            await self.notif_service.create_notification(
                session=self.session,
                user_id=req.citizen_id,
                notification_type=ntype,
                title=f"Request Status: {target_status.value}",
                message=f"[{req.request_reference}] {nmsg}",
                related_entity_type="SERVICE_REQUEST",
                related_entity_id=str(req.id),
            )

        return req

    # 4. Officer & Surveyor Assignment
    async def assign_case(
        self,
        request_id: uuid.UUID,
        actor: User,
        assigned_to: Optional[uuid.UUID] = None,
        assigned_team: Optional[str] = None,
        reason: str = "Assigned for official processing",
    ) -> ServiceRequest:
        if actor.role not in (UserRole.GOVERNMENT_OFFICER.value, UserRole.ADMIN.value):
            raise WorkflowAuthorizationError("Only government officers or administrators can assign cases")

        req = await self.repo.get_service_request(request_id)
        if not req:
            raise WorkflowValidationError("Service request not found")

        prev_assigned = req.assigned_to
        req.assigned_to = assigned_to
        req.assigned_team = assigned_team
        if req.status in (RequestStatus.SUBMITTED.value, RequestStatus.ACKNOWLEDGED.value):
            req.status = RequestStatus.ASSIGNED.value

        event = ServiceRequestEvent(
            service_request_id=req.id,
            previous_status=req.status,
            new_status=req.status,
            actor_id=actor.id,
            actor_role=actor.role,
            event_type="ASSIGNMENT",
            reason=reason,
            comment=f"Assigned to {assigned_to or assigned_team}",
            is_internal=True,
        )
        await self.repo.add_event(event)

        # Notify the assigned officer
        if assigned_to and assigned_to != actor.id:
            await self.notif_service.create_notification(
                session=self.session,
                user_id=assigned_to,
                notification_type=NotificationType.ASSIGNMENT.value,
                title="New Case Assignment",
                message=f"You have been assigned to case {req.case_reference} ({req.title}).",
                related_entity_type="SERVICE_REQUEST",
                related_entity_id=str(req.id),
            )

        return req

    # 5. Commissioning Field Survey (Phase 5 Integration)
    async def commission_survey(
        self,
        request_id: uuid.UUID,
        actor: User,
        surveyor_id: uuid.UUID,
        instructions: str,
        due_days: int = 7,
    ) -> ServiceRequest:
        if actor.role not in (UserRole.GOVERNMENT_OFFICER.value, UserRole.ADMIN.value):
            raise WorkflowAuthorizationError("Only government officers can commission field surveys")

        req = await self.repo.get_service_request(request_id)
        if not req:
            raise WorkflowValidationError("Service request not found")

        surveyor = await self.session.get(User, surveyor_id)
        if not surveyor or surveyor.role != UserRole.SURVEYOR.value:
            raise WorkflowValidationError("Target user is not an active surveyor")

        now = datetime.now(timezone.utc)
        # Create Phase 5 SurveyProject if not existing
        code = f"PRJ-{req.request_reference}"
        project = SurveyProject(
            organization_id=actor.organization_id or surveyor.organization_id,
            jurisdiction_id=req.jurisdiction_id,
            name=f"Survey for {req.request_reference}",
            code=code,
            description=instructions,
            status="ACTIVE",
            start_date=now,
            created_by=actor.id,
        )
        self.session.add(project)
        await self.session.flush()

        # Create Phase 5 SurveyAssignment
        assignment = SurveyAssignment(
            survey_project_id=project.id,
            surveyor_id=surveyor.id,
            jurisdiction_id=req.jurisdiction_id,
            parcel_id=req.parcel_id,
            building_id=req.building_id,
            notes=instructions,
            status="ASSIGNED",
            assigned_at=now,
            created_by=actor.id,
        )
        self.session.add(assignment)
        await self.session.flush()

        req.survey_project_id = project.id
        req.survey_assignment_id = assignment.id
        req.assigned_surveyor_id = surveyor.id
        req.status = RequestStatus.IN_PROGRESS.value

        event = ServiceRequestEvent(
            service_request_id=req.id,
            previous_status=RequestStatus.ASSIGNED.value,
            new_status=RequestStatus.IN_PROGRESS.value,
            actor_id=actor.id,
            actor_role=actor.role,
            event_type="SURVEY_COMMISSIONED",
            reason="Field survey commissioned",
            comment=f"Commissioned to surveyor {surveyor.username}: {instructions}",
            is_internal=False,
        )
        await self.repo.add_event(event)

        # Notify surveyor
        await self.notif_service.create_notification(
            session=self.session,
            user_id=surveyor.id,
            notification_type=NotificationType.SURVEY_SCHEDULED.value,
            title="Field Survey Assignment",
            message=f"You have been assigned a field survey for case {req.case_reference}.",
            related_entity_type="SURVEY_ASSIGNMENT",
            related_entity_id=str(assignment.id),
        )

        return req

    # 6. Case Escalation
    async def escalate_case(
        self,
        request_id: uuid.UUID,
        actor: User,
        escalate_to: uuid.UUID,
        reason: str,
    ) -> ServiceRequest:
        if actor.role not in (UserRole.GOVERNMENT_OFFICER.value, UserRole.ADMIN.value):
            raise WorkflowAuthorizationError("Only government officers or admins can escalate cases")

        req = await self.repo.get_service_request(request_id)
        if not req:
            raise WorkflowValidationError("Service request not found")

        now = datetime.now(timezone.utc)
        req.escalated_at = now
        req.escalation_reason = reason
        req.escalated_by = actor.id
        req.escalated_to = escalate_to
        req.priority = RequestPriority.CRITICAL.value

        event = ServiceRequestEvent(
            service_request_id=req.id,
            previous_status=req.status,
            new_status=req.status,
            actor_id=actor.id,
            actor_role=actor.role,
            event_type="CASE_ESCALATED",
            reason=reason,
            comment=f"Case escalated to supervisor {escalate_to}",
            is_internal=True,
        )
        await self.repo.add_event(event)

        await self.notif_service.create_notification(
            session=self.session,
            user_id=escalate_to,
            notification_type=NotificationType.CASE_ESCALATED.value,
            title="CRITICAL: Case Escalated",
            message=f"Case {req.case_reference} has been escalated to you: {reason}",
            related_entity_type="SERVICE_REQUEST",
            related_entity_id=str(req.id),
        )

        return req

    # 7. Case Messaging (Controlled Citizen-Officer Communication)
    async def post_message(
        self,
        request_id: uuid.UUID,
        sender: User,
        content: str,
        message_type: str = "PUBLIC_COMMENT",
        is_internal: bool = False,
        attachment_ids: Optional[List[str]] = None,
    ) -> CaseMessage:
        req = await self.repo.get_service_request(request_id)
        if not req:
            raise WorkflowValidationError("Service request not found")

        # Citizens can never post internal messages
        if sender.role == UserRole.CITIZEN.value:
            if req.citizen_id != sender.id:
                raise WorkflowAuthorizationError("Citizen cannot message on requests belonging to others")
            is_internal = False
            message_type = "CITIZEN_RESPONSE"

        msg = CaseMessage(
            service_request_id=req.id,
            sender_id=sender.id,
            sender_role=sender.role,
            message_type=message_type,
            content=content,
            attachment_ids=attachment_ids or [],
            is_internal=is_internal,
        )
        saved = await self.repo.add_message(msg)

        # Audit event for messages
        audit = AuditEvent(
            action="MESSAGE_POSTED",
            entity_type="SERVICE_REQUEST",
            entity_id=str(req.id),
            actor_user_id=sender.id,
            ip_address="127.0.0.1",
            details={"message_id": str(saved.id), "is_internal": is_internal, "type": message_type},
        )
        self.session.add(audit)

        return saved

    # 8. Controlled Official Data Update (Upon Approval)
    async def execute_controlled_property_update(
        self,
        request_id: uuid.UUID,
        officer: User,
        reason: str,
        source_reference: str,
        updates: Dict[str, Any],
    ) -> Property:
        if officer.role not in (UserRole.GOVERNMENT_OFFICER.value, UserRole.ADMIN.value):
            raise WorkflowAuthorizationError("Only government officers can execute official property updates")

        req = await self.repo.get_service_request(request_id)
        if not req or not req.property_id:
            raise WorkflowValidationError("Request does not reference an official property record")

        prop = await self.session.get(Property, req.property_id)
        if not prop:
            raise WorkflowValidationError("Referenced property record not found")

        # Capture previous state for immutable audit
        previous_state = {
            "address": prop.address,
            "locality": prop.locality,
            "property_type": prop.property_type,
            "status": prop.status,
            "description": prop.description,
        }

        # Apply allowed safe updates
        for field in ("address", "locality", "property_type", "status", "description"):
            if field in updates and updates[field] is not None:
                setattr(prop, field, updates[field])

        prop.updated_by = officer.id
        await self.session.flush()

        # Audit event recording previous vs new values
        audit = AuditEvent(
            action="CONTROLLED_OFFICIAL_PROPERTY_UPDATE",
            entity_type="PROPERTY",
            entity_id=str(prop.id),
            actor_user_id=officer.id,
            ip_address="127.0.0.1",
            details={
                "service_request_id": str(req.id),
                "request_reference": req.request_reference,
                "reason": reason,
                "source_reference": source_reference,
                "previous_state": previous_state,
                "new_state": {k: getattr(prop, k) for k in previous_state},
            },
        )
        self.session.add(audit)

        return prop

    # 9. Detailed Case Workspace Inspection (Cross-Phase Integrations)
    async def get_case_details(
        self,
        request_id: uuid.UUID,
        user: User,
    ) -> Dict[str, Any]:
        req = await self.repo.get_service_request(request_id)
        if not req:
            raise WorkflowValidationError("Service request not found")

        is_citizen = (user.role == UserRole.CITIZEN.value)
        if is_citizen and req.citizen_id != user.id:
            raise WorkflowAuthorizationError("Citizen cannot access service requests belonging to other users")

        if user.role == UserRole.GOVERNMENT_OFFICER.value and user.jurisdiction_id:
            if req.jurisdiction_id != user.jurisdiction_id:
                raise WorkflowAuthorizationError("Officer cannot access cases outside their assigned jurisdiction")

        # Filter internal items if citizen
        events = await self.repo.list_events(req.id, include_internal=not is_citizen)
        messages = await self.repo.list_messages(req.id, include_internal=not is_citizen)
        tasks = req.tasks if not is_citizen else []

        sla_eval = SLAEngine.evaluate_status(req.due_at, req.completed_at)

        # Cross-Phase 8: Documents
        doc_links_stmt = select(DocumentEntityLink).where(
            DocumentEntityLink.entity_type == "PROPERTY",
            DocumentEntityLink.entity_id == str(req.property_id),
        ) if req.property_id else None
        attached_docs = []
        if doc_links_stmt is not None:
            doc_links = (await self.session.execute(doc_links_stmt)).scalars().all()
            for dl in doc_links:
                doc = await self.session.get(PropertyDocument, dl.document_id)
                if doc:
                    attached_docs.append({
                        "id": str(doc.id),
                        "file_name": doc.original_filename,
                        "document_type": doc.document_type,
                        "status": doc.status,
                    })

        # Cross-Phase 5: Surveys
        linked_surveys = []
        if req.survey_assignment_id:
            assign = await self.session.get(SurveyAssignment, req.survey_assignment_id)
            if assign:
                linked_surveys.append({
                    "id": str(assign.id),
                    "status": assign.status,
                    "surveyor_id": str(assign.surveyor_id),
                    "notes": assign.assignment_notes,
                })

        # Cross-Phase 7: Topology Validation issues
        val_status = None
        if req.parcel_id:
            val_stmt = select(ValidationIssue).where(
                ValidationIssue.entity_type == "PARCEL",
                ValidationIssue.entity_id == str(req.parcel_id),
            ).limit(10)
            issues = (await self.session.execute(val_stmt)).scalars().all()
            if issues:
                val_status = {
                    "has_issues": True,
                    "issues_count": len(issues),
                    "details": [
                        {"rule_code": i.rule_code, "severity": i.severity, "message": i.message}
                        for i in issues
                    ] if not is_citizen else "Some property information requires verification.",
                }

        # Cross-Phase 9: Change Detection Candidates
        change_status = None
        entity_ids = [e for e in [req.parcel_id, req.building_id] if e is not None]
        if entity_ids:
            change_stmt = select(ChangeCandidate).where(
                ChangeCandidate.entity_id.in_(entity_ids),
            ).limit(5)
            changes = (await self.session.execute(change_stmt)).scalars().all()
            if changes:
                change_status = {
                    "has_candidates": True,
                    "candidates_count": len(changes),
                    "summary": (
                        f"{len(changes)} physical change candidates pending adjudication."
                        if not is_citizen
                        else "Physical property data differs between available observations and is under review."
                    ),
                }

        return {
            "request": req,
            "events": events,
            "messages": messages,
            "tasks": tasks,
            "sla": sla_eval,
            "attached_documents": attached_docs,
            "linked_surveys": linked_surveys,
            "validation_status": val_status,
            "change_status": change_status,
        }
