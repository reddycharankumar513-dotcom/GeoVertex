from datetime import datetime, timezone, timedelta
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import (
    RequestStatus,
    RequestPriority,
    AuthorizationType,
    LinkStatus,
    ServiceType,
    CitizenPropertyLink,
    ServiceRequest,
    DeliveryChannel,
)
from app.services.workflow.sla_engine import SLAEngine
from app.services.workflow.state_machine import WorkflowStateMachine, WorkflowStateError


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest_asyncio.fixture(scope="function")
async def seed_service_types(db_session: AsyncSession):
    codes = [
        ("PROPERTY_MUTATION", "Property Mutation & Boundary Correction"),
        ("SURVEY_DEMARCATION", "Field Demarcation & Boundary Pegging"),
        ("GENERAL_ENQUIRY", "General Cadastral Enquiry"),
    ]
    for code, name in codes:
        st = ServiceType(
            code=code,
            name=name,
            description=f"Description for {code}",
            active=True,
            citizen_visible=True,
            required_documents=[],
            required_fields=[],
            response_sla_hours=24,
            completion_sla_hours=120,
            allowed_roles=["CITIZEN", "GOVERNMENT_OFFICER", "ADMIN"],
        )
        db_session.add(st)
    await db_session.flush()


# ==============================================================================
# 1. Deterministic SLA & State Machine Tests
# ==============================================================================

def test_sla_engine_calculations():
    now = datetime.now(timezone.utc)
    due_future = now + timedelta(hours=48)
    status, hours = SLAEngine.get_sla_status(due_future)
    assert status == "ON_TRACK"
    assert hours > 0

    due_soon = now + timedelta(hours=12)
    status, hours = SLAEngine.get_sla_status(due_soon)
    assert status == "DUE_SOON"
    assert hours > 0

    due_past = now - timedelta(hours=5)
    status, hours = SLAEngine.get_sla_status(due_past)
    assert status == "OVERDUE"
    assert hours < 0

    assert SLAEngine.get_sla_status(None)[0] == "NOT_APPLICABLE"


def test_workflow_state_machine_transitions():
    sm = WorkflowStateMachine()

    # Valid Citizen transition
    assert sm.can_transition(RequestStatus.DRAFT, RequestStatus.SUBMITTED, "CITIZEN") is True
    # Invalid: Citizen cannot approve
    assert sm.can_transition(RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED, "CITIZEN") is False
    # Valid: Officer can approve from UNDER_REVIEW
    assert sm.can_transition(RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED, "GOVERNMENT_OFFICER") is True
    # Valid: Terminal state cannot transition
    assert sm.can_transition(RequestStatus.COMPLETED, RequestStatus.UNDER_REVIEW, "GOVERNMENT_OFFICER") is False

    # Validation requirements
    with pytest.raises(WorkflowStateError):
        sm.validate_transition(RequestStatus.UNDER_REVIEW, RequestStatus.REJECTED, "GOVERNMENT_OFFICER", reason=None)

    sm.validate_transition(RequestStatus.UNDER_REVIEW, RequestStatus.REJECTED, "GOVERNMENT_OFFICER", reason="Boundary overlap conflict")


# ==============================================================================
# 2. End-to-End API Integration Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_service_type_crud_and_listing(client: AsyncClient, auth_tokens: dict, seed_test_data):
    # 1. Officer creates a service type
    res = await client.post(
        "/api/v1/workflows/service-types",
        headers=auth_tokens["officer"],
        json={
            "code": "SRV-SPLIT-PARCEL",
            "name": "Parcel Subdivision Request",
            "description": "Citizen request to subdivide land parcel into separate cadastral titles",
            "citizen_visible": True,
            "required_documents": ["DEED", "DEPUTY_SURVEY_REPORT"],
            "required_fields": ["target_subdivisions"],
            "response_sla_hours": 24,
            "completion_sla_hours": 72,
            "allowed_roles": ["CITIZEN", "GOVERNMENT_OFFICER", "ADMIN"],
        },
    )
    assert res.status_code == 201
    st_id = res.json()["id"]

    # 2. Citizen lists service types - should see the active citizen-visible type
    res_citizen = await client.get("/api/v1/workflows/service-types", headers=auth_tokens["citizen"])
    assert res_citizen.status_code == 200
    types = res_citizen.json()
    assert any(t["code"] == "SRV-SPLIT-PARCEL" for t in types)


@pytest.mark.asyncio
async def test_citizen_property_linking_and_request_creation_abac(
    client: AsyncClient,
    auth_tokens: dict,
    seed_test_data,
    seed_service_types,
):
    jur_id = str(seed_test_data["jur"].id)
    citizen_id = str(seed_test_data["users"]["CITIZEN"].id)

    # 1. Create parcel & property via API
    p_res = await client.post(
        "/api/v1/parcels",
        headers=auth_tokens["officer"],
        json={
            "jurisdiction_id": jur_id,
            "parcel_number": f"P-{uuid.uuid4().hex[:6]}",
            "parcel_code": f"GV-W500-{uuid.uuid4().hex[:6]}",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        },
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    prop_res = await client.post(
        "/api/v1/properties",
        headers=auth_tokens["officer"],
        json={
            "parcel_id": parcel_id,
            "property_reference": f"PROP-{uuid.uuid4().hex[:6]}",
            "property_type": "FREEHOLD",
            "status": "ACTIVE",
            "address": "101 Jubilee Hills Rd",
        },
    )
    assert prop_res.status_code == 201
    prop_id = prop_res.json()["id"]

    # 2. Unlinked citizen attempt to create a service request for this property -> 403 Forbidden
    res_unauth = await client.post(
        "/api/v1/workflows/service-requests",
        headers=auth_tokens["citizen"],
        json={
            "request_type": "PROPERTY_MUTATION",
            "title": "Unauthorized Mutation Attempt",
            "description": "Attempting to file for unverified property without linking",
            "jurisdiction_id": jur_id,
            "property_id": str(prop_id),
        },
    )
    assert res_unauth.status_code == 403
    assert "not authorized" in res_unauth.json()["error"]["message"].lower()

    # 3. Officer verifies citizen property link
    res_link = await client.post(
        "/api/v1/workflows/citizen/properties",
        headers=auth_tokens["officer"],
        json={
            "citizen_id": citizen_id,
            "property_id": str(prop_id),
            "authorization_type": AuthorizationType.OWNER.value,
            "status": LinkStatus.VERIFIED.value,
        },
    )
    assert res_link.status_code == 201

    # 4. Citizen can now inspect their verified property
    res_my_props = await client.get("/api/v1/workflows/citizen/properties", headers=auth_tokens["citizen"])
    assert res_my_props.status_code == 200
    my_props = res_my_props.json()
    assert len(my_props) >= 1
    assert any(p["property_id"] == str(prop_id) for p in my_props)

    # 5. Citizen creates service request successfully for verified property
    res_req = await client.post(
        "/api/v1/workflows/service-requests",
        headers=auth_tokens["citizen"],
        json={
            "request_type": "PROPERTY_MUTATION",
            "title": "Title Deed Boundary Amendment",
            "description": "Requesting boundary re-survey following approved partition deed",
            "jurisdiction_id": jur_id,
            "property_id": str(prop_id),
            "parcel_id": str(parcel_id),
            "priority": "HIGH",
        },
    )
    assert res_req.status_code == 201
    req_data = res_req.json()
    assert req_data["status"] == RequestStatus.SUBMITTED.value
    assert req_data["request_reference"].startswith("GV-SR-")
    assert req_data["case_reference"].startswith("GV-CASE-")
    req_id = req_data["id"]

    # 6. List service requests for citizen
    res_list = await client.get("/api/v1/workflows/service-requests", headers=auth_tokens["citizen"])
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1


@pytest.mark.asyncio
async def test_government_officer_review_lifecycle_and_survey_commissioning(
    client: AsyncClient,
    auth_tokens: dict,
    seed_test_data,
    seed_service_types,
):
    jur_id = str(seed_test_data["jur"].id)
    citizen_id = str(seed_test_data["users"]["CITIZEN"].id)
    officer_id = str(seed_test_data["users"]["GOVERNMENT_OFFICER"].id)
    surveyor_id = str(seed_test_data["users"]["SURVEYOR"].id)

    # 1. Setup parcel & property
    p_res = await client.post(
        "/api/v1/parcels",
        headers=auth_tokens["officer"],
        json={
            "jurisdiction_id": jur_id,
            "parcel_number": f"P2-{uuid.uuid4().hex[:6]}",
            "parcel_code": f"GV-W500-2-{uuid.uuid4().hex[:6]}",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        },
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    prop_res = await client.post(
        "/api/v1/properties",
        headers=auth_tokens["officer"],
        json={
            "parcel_id": parcel_id,
            "property_reference": f"PROP2-{uuid.uuid4().hex[:6]}",
            "property_type": "FREEHOLD",
            "status": "ACTIVE",
            "address": "102 Jubilee Hills Rd",
        },
    )
    assert prop_res.status_code == 201
    prop_id = prop_res.json()["id"]

    # Link property to citizen
    link_res = await client.post(
        "/api/v1/workflows/citizen/properties",
        headers=auth_tokens["officer"],
        json={
            "citizen_id": citizen_id,
            "property_id": str(prop_id),
            "authorization_type": AuthorizationType.OWNER.value,
            "status": LinkStatus.VERIFIED.value,
        },
    )
    assert link_res.status_code == 201

    # Citizen files request
    create_res = await client.post(
        "/api/v1/workflows/service-requests",
        headers=auth_tokens["citizen"],
        json={
            "request_type": "SURVEY_DEMARCATION",
            "title": "On-Site Boundary Demarcation Request",
            "description": "Boundary pegging required for adjacent construction fence",
            "jurisdiction_id": jur_id,
            "property_id": str(prop_id),
            "parcel_id": str(parcel_id),
        },
    )
    assert create_res.status_code == 201
    req_id = create_res.json()["id"]

    # 2. Officer assigns case to self
    res_assign = await client.post(
        f"/api/v1/workflows/service-requests/{req_id}/assign",
        headers=auth_tokens["officer"],
        json={
            "assigned_to": officer_id,
            "assigned_team": "Land Records Review Team",
            "reason": "Official assignment to senior review officer",
        },
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["status"] == RequestStatus.ASSIGNED.value

    # 3. Officer commissions field survey directly (Phase 5 Surveyor Integration)
    res_survey = await client.post(
        f"/api/v1/workflows/service-requests/{req_id}/commission-survey",
        headers=auth_tokens["officer"],
        json={
            "surveyor_id": surveyor_id,
            "instructions": "Verify boundary monuments on site and capture GNSS points",
            "due_days": 7,
        },
    )
    assert res_survey.status_code == 200
    survey_data = res_survey.json()
    assert survey_data["status"] == RequestStatus.IN_PROGRESS.value
    assert survey_data["survey_project_id"] is not None
    assert survey_data["survey_assignment_id"] is not None

    # 4. Officer moves to UNDER_REVIEW
    res_review = await client.post(
        f"/api/v1/workflows/service-requests/{req_id}/transition",
        headers=auth_tokens["officer"],
        json={
            "target_status": RequestStatus.UNDER_REVIEW.value,
            "comment": "Field survey evidence verified and ready for determination",
        },
    )
    assert res_review.status_code == 200
    assert res_review.json()["status"] == RequestStatus.UNDER_REVIEW.value

    # 5. Officer applies Controlled Official Property Update
    res_update = await client.post(
        f"/api/v1/workflows/service-requests/{req_id}/controlled-property-update",
        headers=auth_tokens["officer"],
        json={
            "reason": "Official record updated following certified field demarcation report",
            "source_reference": f"SRV-COMM-{req_id[:8]}",
            "updates": {"description": "Updated following official certified field survey"},
        },
    )
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "SUCCESS"
    assert res_update.json()["property_id"] == str(prop_id)

    # 6. Officer approves the request
    res_approve = await client.post(
        f"/api/v1/workflows/service-requests/{req_id}/transition",
        headers=auth_tokens["officer"],
        json={
            "target_status": RequestStatus.APPROVED.value,
            "comment": "All requirements verified and field demarcation certified.",
        },
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == RequestStatus.APPROVED.value


@pytest.mark.asyncio
async def test_case_messaging_and_internal_note_secrecy(
    client: AsyncClient,
    auth_tokens: dict,
    seed_test_data,
    db_session: AsyncSession,
):
    jur = seed_test_data["jur"]
    users = seed_test_data["users"]
    citizen = users["CITIZEN"]

    # Direct request record
    sr = ServiceRequest(
        request_reference=f"GV-SR-{uuid.uuid4().hex[:8].upper()}",
        case_reference=f"GV-CASE-{uuid.uuid4().hex[:8].upper()}",
        citizen_id=citizen.id,
        jurisdiction_id=jur.id,
        request_type="GENERAL_ENQUIRY",
        title="Cadastral Query",
        description="Citizen message privacy test",
        status=RequestStatus.UNDER_REVIEW.value,
    )
    db_session.add(sr)
    await db_session.flush()

    # 1. Officer posts an INTERNAL NOTE
    res_int = await client.post(
        f"/api/v1/workflows/service-requests/{sr.id}/messages",
        headers=auth_tokens["officer"],
        json={
            "content": "Confidential internal officer assessment: Cross-check with registry deed archive.",
            "is_internal": True,
            "message_type": "INTERNAL_NOTE",
        },
    )
    assert res_int.status_code == 201
    assert res_int.json()["is_internal"] is True

    # 2. Officer posts a PUBLIC RESPONSE
    res_pub = await client.post(
        f"/api/v1/workflows/service-requests/{sr.id}/messages",
        headers=auth_tokens["officer"],
        json={
            "content": "Dear Citizen, your file is currently being processed by the cadastral team.",
            "is_internal": False,
            "message_type": "OFFICER_RESPONSE",
        },
    )
    assert res_pub.status_code == 201

    # 3. Officer lists messages -> Sees BOTH internal and public
    res_off_list = await client.get(f"/api/v1/workflows/service-requests/{sr.id}/messages", headers=auth_tokens["officer"])
    assert res_off_list.status_code == 200
    off_msgs = res_off_list.json()
    assert len(off_msgs) == 2
    assert any(m["is_internal"] is True for m in off_msgs)

    # 4. Citizen lists messages -> STRICT PRIVACY: Internal note is completely filtered out!
    res_cit_list = await client.get(f"/api/v1/workflows/service-requests/{sr.id}/messages", headers=auth_tokens["citizen"])
    assert res_cit_list.status_code == 200
    cit_msgs = res_cit_list.json()
    assert len(cit_msgs) == 1
    assert cit_msgs[0]["is_internal"] is False
    assert "Confidential" not in cit_msgs[0]["content"]

    # 5. Citizen cannot create an internal note
    res_cit_create = await client.post(
        f"/api/v1/workflows/service-requests/{sr.id}/messages",
        headers=auth_tokens["citizen"],
        json={"content": "Citizen message trying to set internal", "is_internal": True},
    )
    assert res_cit_create.status_code == 201
    assert res_cit_create.json()["is_internal"] is False  # Forcibly sanitized to False


@pytest.mark.asyncio
async def test_dashboards_and_in_app_notifications(
    client: AsyncClient,
    auth_tokens: dict,
    seed_test_data,
):
    # 1. Citizen Dashboard
    res_cit_dash = await client.get("/api/v1/workflows/citizen/dashboard", headers=auth_tokens["citizen"])
    assert res_cit_dash.status_code == 200
    cit_data = res_cit_dash.json()
    assert "active_requests" in cit_data
    assert "total_properties" in cit_data
    assert "pending_citizen_action" in cit_data
    assert "unread_notifications" in cit_data

    # 2. Government Dashboard
    res_gov_dash = await client.get("/api/v1/workflows/government/dashboard", headers=auth_tokens["officer"])
    assert res_gov_dash.status_code == 200
    gov_data = res_gov_dash.json()
    assert "total_received" in gov_data
    assert "pending_acknowledgement" in gov_data
    assert "in_progress" in gov_data
    assert "overdue" in gov_data
    assert "open_tasks" in gov_data

    # 3. Notification center
    notif_res = await client.get("/api/v1/workflows/notifications", headers=auth_tokens["citizen"])
    assert notif_res.status_code == 200
    assert isinstance(notif_res.json(), list)
