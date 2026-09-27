"""REST API endpoints for Citizen Portal, Government Workflow & Public-Service Integration."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.errors import NotFoundException, ForbiddenException, BadRequestException
from app.dependencies.auth import get_current_user, require_role
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.models.property import Property
from app.models.workflow import ServiceType, RequestPriority, RequestStatus, CitizenPropertyLink
from app.schemas.workflow import (
    CaseAssignmentPayload,
    CaseEscalationPayload,
    CaseMessageCreate,
    CaseMessageResponse,
    CitizenDashboardMetricsResponse,
    CitizenPropertyLinkCreate,
    CitizenPropertyLinkResponse,
    CitizenPropertyResponse,
    ControlledPropertyUpdatePayload,
    GovernmentDashboardMetricsResponse,
    NotificationResponse,
    ServiceRequestCreate,
    ServiceRequestDetailResponse,
    ServiceRequestEventResponse,
    ServiceRequestResponse,
    ServiceRequestUpdate,
    ServiceTypeCreate,
    ServiceTypeResponse,
    SurveyCommissionPayload,
    WorkflowTaskCreate,
    WorkflowTaskResponse,
    WorkflowTaskUpdate,
    WorkflowTransitionPayload,
)
from app.services.workflow.workflow_service import (
    WorkflowService,
    WorkflowAuthorizationError,
    WorkflowValidationError,
)

router = APIRouter(prefix="/workflows", tags=["Citizen Portal & Government Workflows"])


# 1. Service Types
@router.get(
    "/service-types",
    response_model=List[ServiceTypeResponse],
    summary="List available service types",
)
async def list_service_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    is_citizen = (current_user.role == UserRole.CITIZEN.value)
    return await service.repo.list_service_types(citizen_visible_only=is_citizen)


@router.post(
    "/service-types",
    response_model=ServiceTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or register a new service request category",
)
async def create_service_type(
    payload: ServiceTypeCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    st = ServiceType(**payload.model_dump())
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st


# 2. Service Requests (Citizen + Government)
@router.post(
    "/service-requests",
    response_model=ServiceRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new citizen service request",
)
async def create_service_request(
    payload: ServiceRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        req = await service.create_service_request(
            citizen=current_user,
            data=payload.model_dump(),
        )
        await db.commit()
        return req
    except WorkflowAuthorizationError as e:
        raise ForbiddenException(str(e))
    except WorkflowValidationError as e:
        raise BadRequestException(str(e))
    except Exception as e:
        await db.rollback()
        raise BadRequestException(str(e))


@router.get(
    "/service-requests",
    response_model=Dict[str, Any],
    summary="List and filter service requests",
)
async def list_service_requests(
    status: Optional[str] = Query(None),
    request_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    jurisdiction_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)

    citizen_id_filter = None
    jurisdiction_filter = jurisdiction_id

    # Strict ABAC: Citizen only sees their own requests
    if current_user.role == UserRole.CITIZEN.value:
        citizen_id_filter = current_user.id
    elif current_user.role == UserRole.GOVERNMENT_OFFICER.value:
        if current_user.jurisdiction_id:
            jurisdiction_filter = current_user.jurisdiction_id

    requests, total = await service.repo.list_service_requests(
        citizen_id=citizen_id_filter,
        jurisdiction_id=jurisdiction_filter,
        status=status,
        request_type=request_type,
        priority=priority,
        search_query=search,
        skip=skip,
        limit=limit,
    )
    return {
        "items": [ServiceRequestResponse.model_validate(r) for r in requests],
        "total": total,
        "page": (skip // limit) + 1,
        "size": limit,
    }


@router.get(
    "/service-requests/{id}",
    response_model=ServiceRequestDetailResponse,
    summary="Get comprehensive service request and case workspace details",
)
async def get_service_request_detail(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        details = await service.get_case_details(request_id=id, user=current_user)
        req = details["request"]

        # If property attached, construct property_info
        prop_info = None
        if req.property:
            prop_info = CitizenPropertyResponse(
                id=req.property.id,
                property_reference=req.property.property_reference,
                parcel_id=req.property.parcel_id,
                parcel_number=req.property.parcel.parcel_number if req.property.parcel else None,
                property_type=req.property.property_type,
                status=req.property.status,
                address=req.property.address,
                locality=req.property.locality,
                postal_code=req.property.postal_code,
                description=req.property.description,
                created_at=req.property.created_at,
            )

        return ServiceRequestDetailResponse(
            request=ServiceRequestResponse.model_validate(req),
            events=[ServiceRequestEventResponse.model_validate(e) for e in details["events"]],
            messages=[CaseMessageResponse.model_validate(m) for m in details["messages"]],
            tasks=[WorkflowTaskResponse.model_validate(t) for t in details["tasks"]],
            sla=details["sla"],
            property_info=prop_info,
            attached_documents=details["attached_documents"],
            linked_surveys=details["linked_surveys"],
            validation_status=details["validation_status"],
            change_status=details["change_status"],
        )
    except WorkflowAuthorizationError as e:
        raise ForbiddenException(str(e))
    except WorkflowValidationError as e:
        raise NotFoundException(str(e))


@router.post(
    "/service-requests/{id}/transition",
    response_model=ServiceRequestResponse,
    summary="Execute a controlled state transition on a service request",
)
async def transition_service_request(
    id: uuid.UUID,
    payload: WorkflowTransitionPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        req = await service.transition_request(
            request_id=id,
            actor=current_user,
            target_status_str=payload.target_status,
            reason=payload.reason,
            comment=payload.comment,
            is_internal=payload.is_internal,
        )
        await db.commit()
        return req
    except WorkflowAuthorizationError as e:
        await db.rollback()
        raise ForbiddenException(str(e))
    except Exception as e:
        await db.rollback()
        raise BadRequestException(str(e))


@router.post(
    "/service-requests/{id}/assign",
    response_model=ServiceRequestResponse,
    summary="Assign a case to an officer or operational team",
)
async def assign_service_request(
    id: uuid.UUID,
    payload: CaseAssignmentPayload,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        req = await service.assign_case(
            request_id=id,
            actor=current_user,
            assigned_to=payload.assigned_to,
            assigned_team=payload.assigned_team,
            reason=payload.reason,
        )
        await db.commit()
        return req
    except Exception as e:
        await db.rollback()
        raise BadRequestException(str(e))


@router.post(
    "/service-requests/{id}/commission-survey",
    response_model=ServiceRequestResponse,
    summary="Commission an active field survey to a licensed surveyor (Phase 5 integration)",
)
async def commission_field_survey(
    id: uuid.UUID,
    payload: SurveyCommissionPayload,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        req = await service.commission_survey(
            request_id=id,
            actor=current_user,
            surveyor_id=payload.surveyor_id,
            instructions=payload.instructions,
            due_days=payload.due_days,
        )
        await db.commit()
        return req
    except Exception as e:
        await db.rollback()
        raise BadRequestException(str(e))


@router.post(
    "/service-requests/{id}/escalate",
    response_model=ServiceRequestResponse,
    summary="Escalate a case to supervisory hierarchy",
)
async def escalate_service_request(
    id: uuid.UUID,
    payload: CaseEscalationPayload,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        req = await service.escalate_case(
            request_id=id,
            actor=current_user,
            escalate_to=payload.escalate_to,
            reason=payload.reason,
        )
        await db.commit()
        return req
    except Exception as e:
        await db.rollback()
        raise BadRequestException(str(e))


@router.post(
    "/service-requests/{id}/controlled-update",
    summary="Execute an audit-logged controlled property record update upon request approval",
)
@router.post(
    "/service-requests/{id}/controlled-property-update",
    summary="Execute an audit-logged controlled property record update upon request approval",
)
async def controlled_property_update(
    id: uuid.UUID,
    payload: ControlledPropertyUpdatePayload,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        updated_prop = await service.execute_controlled_property_update(
            request_id=id,
            officer=current_user,
            reason=payload.reason,
            source_reference=payload.source_reference,
            updates=payload.updates,
        )
        await db.commit()
        return {
            "status": "SUCCESS",
            "property_id": str(updated_prop.id),
            "property_reference": updated_prop.property_reference,
            "message": "Controlled property update executed and recorded in audit log.",
        }
    except Exception as e:
        await db.rollback()
        raise BadRequestException(str(e))


# 3. Case Messages (Communication)
@router.post(
    "/service-requests/{id}/messages",
    response_model=CaseMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a message on the case communication thread",
)
async def post_case_message(
    id: uuid.UUID,
    payload: CaseMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    try:
        msg = await service.post_message(
            request_id=id,
            sender=current_user,
            content=payload.content,
            message_type=payload.message_type,
            is_internal=payload.is_internal,
            attachment_ids=payload.attachment_ids,
        )
        await db.commit()
        return msg
    except WorkflowAuthorizationError as e:
        await db.rollback()
        raise ForbiddenException(str(e))
    except Exception as e:
        await db.rollback()
        raise BadRequestException(str(e))


@router.get(
    "/service-requests/{id}/messages",
    response_model=List[CaseMessageResponse],
    summary="List messages on the case communication thread",
)
async def list_case_messages(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    include_internal = (current_user.role in (UserRole.ADMIN.value, UserRole.GOVERNMENT_OFFICER.value))
    messages = await service.repo.list_messages(id, include_internal=include_internal)
    return [CaseMessageResponse.model_validate(m) for m in messages]


# 4. Citizen Portal Endpoints
@router.post(
    "/citizen/properties",
    response_model=CitizenPropertyLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link or verify citizen property authorization",
)
async def link_citizen_property(
    payload: CitizenPropertyLinkCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    link = CitizenPropertyLink(
        citizen_id=payload.citizen_id,
        property_id=payload.property_id,
        authorization_type=payload.authorization_type,
        status=payload.status,
        verified_by=current_user.id,
        verified_at=now,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.get(
    "/citizen/properties",
    response_model=List[CitizenPropertyResponse],
    summary="List verified authorized properties for the logged-in citizen",
)
async def list_citizen_authorized_properties(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    rows = await service.repo.list_citizen_links(current_user.id)
    out = []
    for link, p in rows:
        if not p:
            continue
        out.append(
            CitizenPropertyResponse(
                id=p.id,
                property_id=p.id,
                property_reference=p.property_reference,
                parcel_id=p.parcel_id,
                parcel_number=p.parcel.parcel_number if p.parcel else None,
                property_type=p.property_type,
                status=p.status,
                address=p.address,
                locality=p.locality,
                postal_code=p.postal_code,
                description=p.description,
                authorization_type=link.authorization_type,
                link_status=link.status,
                units_count=len(p.units) if p.units else 0,
                created_at=p.created_at,
            )
        )
    return out


@router.get(
    "/citizen/dashboard",
    response_model=CitizenDashboardMetricsResponse,
    summary="Retrieve real-time database-derived citizen dashboard statistics",
)
async def get_citizen_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    return await service.repo.get_citizen_metrics(current_user.id)


# 5. Government Portal Endpoints
@router.get(
    "/government/dashboard",
    response_model=GovernmentDashboardMetricsResponse,
    summary="Retrieve real-time database-derived government operations dashboard statistics",
)
async def get_government_dashboard(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.URBAN_PLANNER)),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    jurisdiction_filter = current_user.jurisdiction_id if current_user.role == UserRole.GOVERNMENT_OFFICER.value else None
    return await service.repo.get_government_metrics(jurisdiction_id=jurisdiction_filter)


@router.get(
    "/government/queues",
    response_model=List[WorkflowTaskResponse],
    summary="List government officer workflow tasks",
)
async def list_government_tasks(
    task_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    my_tasks_only: bool = Query(False),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    assignee = current_user.id if my_tasks_only else None
    tasks = await service.repo.list_tasks(assigned_to=assignee, task_type=task_type, status=status)
    return [WorkflowTaskResponse.model_validate(t) for t in tasks]


# 6. Notifications Endpoints
@router.get(
    "/notifications",
    response_model=List[NotificationResponse],
    summary="List notifications for the current user",
)
async def list_user_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    notifs = await service.repo.list_notifications(current_user.id, unread_only=unread_only, limit=limit)
    return [NotificationResponse.model_validate(n) for n in notifs]


@router.post(
    "/notifications/{id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_notification_as_read(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    notif = await service.repo.mark_notification_read(id, current_user.id)
    if not notif:
        raise NotFoundException("Notification not found")
    await db.commit()
    return NotificationResponse.model_validate(notif)


@router.post(
    "/notifications/read-all",
    summary="Mark all unread notifications as read",
)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    count = await service.repo.mark_all_notifications_read(current_user.id)
    await db.commit()
    return {"marked_count": count, "message": f"{count} notifications marked as read."}
