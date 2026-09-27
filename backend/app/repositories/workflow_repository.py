"""Workflow & Service Request Repository with object-level isolation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import (
    CitizenPropertyLink,
    CaseMessage,
    Notification,
    RequestPriority,
    RequestStatus,
    ServiceRequest,
    ServiceRequestEvent,
    ServiceType,
    TaskStatus,
    WorkflowTask,
)
from app.models.property import Property
from app.models.parcel import Parcel
from app.models.building import BuildingFootprint


class WorkflowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # 1. Service Types
    async def get_service_type(self, code: str) -> Optional[ServiceType]:
        stmt = select(ServiceType).where(ServiceType.code == code)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_service_types(self, citizen_visible_only: bool = False) -> List[ServiceType]:
        stmt = select(ServiceType).where(ServiceType.active == True)
        if citizen_visible_only:
            stmt = stmt.where(ServiceType.citizen_visible == True)
        stmt = stmt.order_by(ServiceType.name)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_citizen_links(self, citizen_id: uuid.UUID) -> List[Tuple[CitizenPropertyLink, Property]]:
        stmt = (
            select(CitizenPropertyLink, Property)
            .join(Property, CitizenPropertyLink.property_id == Property.id)
            .where(
                CitizenPropertyLink.citizen_id == citizen_id,
                CitizenPropertyLink.status == "VERIFIED",
            )
            .options(
                selectinload(Property.parcel),
                selectinload(Property.units),
            )
            .order_by(CitizenPropertyLink.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.all())

    async def list_citizen_properties(self, citizen_id: uuid.UUID) -> List[Property]:
        stmt = (
            select(Property)
            .join(CitizenPropertyLink, CitizenPropertyLink.property_id == Property.id)
            .where(
                CitizenPropertyLink.citizen_id == citizen_id,
                CitizenPropertyLink.status == "VERIFIED",
            )
            .options(selectinload(Property.parcel), selectinload(Property.units))
            .order_by(Property.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def verify_citizen_property_access(self, citizen_id: uuid.UUID, property_id: uuid.UUID) -> bool:
        stmt = select(CitizenPropertyLink.id).where(
            CitizenPropertyLink.citizen_id == citizen_id,
            CitizenPropertyLink.property_id == property_id,
            CitizenPropertyLink.status == "VERIFIED",
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def link_citizen_property(
        self,
        citizen_id: uuid.UUID,
        property_id: uuid.UUID,
        authorization_type: str = "OWNER",
        status: str = "VERIFIED",
        verified_by: Optional[uuid.UUID] = None,
    ) -> CitizenPropertyLink:
        link = CitizenPropertyLink(
            citizen_id=citizen_id,
            property_id=property_id,
            authorization_type=authorization_type,
            status=status,
            verified_by=verified_by,
            verified_at=datetime.now(timezone.utc) if status == "VERIFIED" else None,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    # 3. Service Requests
    async def create_service_request(self, request: ServiceRequest) -> ServiceRequest:
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_service_request(self, request_id: uuid.UUID) -> Optional[ServiceRequest]:
        stmt = (
            select(ServiceRequest)
            .where(ServiceRequest.id == request_id)
            .options(
                selectinload(ServiceRequest.citizen),
                selectinload(ServiceRequest.jurisdiction),
                selectinload(ServiceRequest.property),
                selectinload(ServiceRequest.parcel),
                selectinload(ServiceRequest.building),
                selectinload(ServiceRequest.officer),
                selectinload(ServiceRequest.surveyor),
                selectinload(ServiceRequest.events),
                selectinload(ServiceRequest.tasks),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_service_requests(
        self,
        citizen_id: Optional[uuid.UUID] = None,
        jurisdiction_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        request_type: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[uuid.UUID] = None,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ServiceRequest], int]:
        stmt = select(ServiceRequest)
        count_stmt = select(func.count(ServiceRequest.id))

        filters = []
        if citizen_id:
            filters.append(ServiceRequest.citizen_id == citizen_id)
        if jurisdiction_id:
            filters.append(ServiceRequest.jurisdiction_id == jurisdiction_id)
        if status:
            filters.append(ServiceRequest.status == status)
        if request_type:
            filters.append(ServiceRequest.request_type == request_type)
        if priority:
            filters.append(ServiceRequest.priority == priority)
        if assigned_to:
            filters.append(ServiceRequest.assigned_to == assigned_to)
        if search_query:
            q = f"%{search_query}%"
            filters.append(
                or_(
                    ServiceRequest.request_reference.ilike(q),
                    ServiceRequest.case_reference.ilike(q),
                    ServiceRequest.title.ilike(q),
                    ServiceRequest.description.ilike(q),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            stmt.options(
                selectinload(ServiceRequest.citizen),
                selectinload(ServiceRequest.jurisdiction),
                selectinload(ServiceRequest.property),
                selectinload(ServiceRequest.officer),
            )
            .order_by(ServiceRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

    # 4. Events / Timeline
    async def add_event(self, event: ServiceRequestEvent) -> ServiceRequestEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events(
        self,
        service_request_id: uuid.UUID,
        include_internal: bool = False,
    ) -> List[ServiceRequestEvent]:
        stmt = select(ServiceRequestEvent).where(
            ServiceRequestEvent.service_request_id == service_request_id
        )
        if not include_internal:
            stmt = stmt.where(ServiceRequestEvent.is_internal == False)
        stmt = stmt.order_by(ServiceRequestEvent.created_at.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # 5. Case Messages
    async def add_message(self, message: CaseMessage) -> CaseMessage:
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_messages(
        self,
        service_request_id: uuid.UUID,
        include_internal: bool = False,
    ) -> List[CaseMessage]:
        stmt = (
            select(CaseMessage)
            .where(CaseMessage.service_request_id == service_request_id)
            .options(selectinload(CaseMessage.sender))
        )
        if not include_internal:
            stmt = stmt.where(CaseMessage.is_internal == False)
        stmt = stmt.order_by(CaseMessage.created_at.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # 6. Workflow Tasks
    async def create_task(self, task: WorkflowTask) -> WorkflowTask:
        self.session.add(task)
        await self.session.flush()
        return task

    async def list_tasks(
        self,
        assigned_to: Optional[uuid.UUID] = None,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[WorkflowTask]:
        stmt = select(WorkflowTask).options(
            selectinload(WorkflowTask.service_request),
            selectinload(WorkflowTask.assignee),
        )
        filters = []
        if assigned_to:
            filters.append(WorkflowTask.assigned_to == assigned_to)
        if task_type:
            filters.append(WorkflowTask.task_type == task_type)
        if status:
            filters.append(WorkflowTask.status == status)
        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(WorkflowTask.due_at.asc().nullslast()).offset(skip).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # 7. Notifications
    async def list_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def mark_notification_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        res = await self.session.execute(stmt)
        notif = res.scalar_one_or_none()
        if notif and not notif.read_at:
            notif.read_at = datetime.now(timezone.utc)
            await self.session.flush()
        return notif

    async def mark_all_notifications_read(self, user_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=now)
        )
        res = await self.session.execute(stmt)
        return res.rowcount

    # 8. Real-time Database-derived Dashboard Metrics
    async def get_citizen_metrics(self, citizen_id: uuid.UUID) -> Dict[str, Any]:
        # Properties count
        props_stmt = select(func.count(CitizenPropertyLink.id)).where(
            CitizenPropertyLink.citizen_id == citizen_id,
            CitizenPropertyLink.status == "VERIFIED",
        )
        props_res = await self.session.execute(props_stmt)
        total_properties = props_res.scalar_one()

        # Requests count
        req_stmt = select(
            func.count(ServiceRequest.id).label("total"),
            func.count(ServiceRequest.id).filter(
                ServiceRequest.status.in_([
                    RequestStatus.SUBMITTED.value,
                    RequestStatus.ACKNOWLEDGED.value,
                    RequestStatus.ASSIGNED.value,
                    RequestStatus.IN_PROGRESS.value,
                    RequestStatus.UNDER_REVIEW.value,
                    RequestStatus.RESUBMITTED.value,
                ])
            ).label("active"),
            func.count(ServiceRequest.id).filter(
                ServiceRequest.status.in_([
                    RequestStatus.WAITING_FOR_CITIZEN.value,
                    RequestStatus.REVISION_REQUIRED.value,
                ])
            ).label("pending_action"),
            func.count(ServiceRequest.id).filter(
                ServiceRequest.status == RequestStatus.COMPLETED.value
            ).label("completed"),
        ).where(ServiceRequest.citizen_id == citizen_id)

        req_res = await self.session.execute(req_stmt)
        req_row = req_res.one()

        # Unread notifications
        notif_stmt = select(func.count(Notification.id)).where(
            Notification.user_id == citizen_id,
            Notification.read_at.is_(None),
        )
        notif_res = await self.session.execute(notif_stmt)
        unread_notifs = notif_res.scalar_one()

        return {
            "total_properties": total_properties,
            "total_requests": req_row.total,
            "active_requests": req_row.active,
            "pending_citizen_action": req_row.pending_action,
            "completed_requests": req_row.completed,
            "unread_notifications": unread_notifs,
        }

    async def get_government_metrics(self, jurisdiction_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        filter_clause = [ServiceRequest.jurisdiction_id == jurisdiction_id] if jurisdiction_id else []

        stmt = select(
            func.count(ServiceRequest.id).label("total_received"),
            func.count(ServiceRequest.id).filter(ServiceRequest.status == RequestStatus.SUBMITTED.value).label("pending_acknowledgement"),
            func.count(ServiceRequest.id).filter(ServiceRequest.status == RequestStatus.ACKNOWLEDGED.value).label("acknowledged"),
            func.count(ServiceRequest.id).filter(ServiceRequest.status.in_([
                RequestStatus.ASSIGNED.value,
                RequestStatus.IN_PROGRESS.value,
                RequestStatus.UNDER_REVIEW.value,
                RequestStatus.RESUBMITTED.value,
            ])).label("in_progress"),
            func.count(ServiceRequest.id).filter(ServiceRequest.status.in_([
                RequestStatus.WAITING_FOR_CITIZEN.value,
                RequestStatus.REVISION_REQUIRED.value,
            ])).label("awaiting_citizen"),
            func.count(ServiceRequest.id).filter(ServiceRequest.status == RequestStatus.COMPLETED.value).label("completed"),
            func.count(ServiceRequest.id).filter(
                and_(
                    ServiceRequest.status.notin_([
                        RequestStatus.COMPLETED.value,
                        RequestStatus.REJECTED.value,
                        RequestStatus.CANCELLED.value,
                    ]),
                    ServiceRequest.due_at.is_not(None),
                    ServiceRequest.due_at < now,
                )
            ).label("overdue"),
        )
        if filter_clause:
            stmt = stmt.where(*filter_clause)

        res = await self.session.execute(stmt)
        row = res.one()

        # Open workflow tasks
        task_stmt = select(func.count(WorkflowTask.id)).where(
            WorkflowTask.status.in_([TaskStatus.OPEN.value, TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value])
        )
        task_res = await self.session.execute(task_stmt)
        open_tasks = task_res.scalar_one()

        return {
            "total_received": row.total_received,
            "pending_acknowledgement": row.pending_acknowledgement,
            "acknowledged": row.acknowledged,
            "in_progress": row.in_progress,
            "awaiting_citizen": row.awaiting_citizen,
            "completed": row.completed,
            "overdue": row.overdue,
            "open_tasks": open_tasks,
        }
