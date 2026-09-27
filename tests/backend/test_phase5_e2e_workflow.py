import hashlib
import io
import uuid
from httpx import AsyncClient
import pytest
from app.models.user import UserRole

pytestmark = pytest.mark.asyncio


async def test_complete_phase5_cadastral_survey_workflow_e2e(
    client: AsyncClient,
    seed_test_data,
    auth_tokens,
):
    """
    End-to-End Comprehensive Verification of Phase 5:
    Officer Project & Assignment Dispatch -> Surveyor GPS & Multi-type Observations
    -> Cryptographic Photo Evidence Capture -> Offline Batch Sync & Idempotency
    -> Cadastral Discrepancy Validation -> Officer Revision Request -> Surveyor Resubmission
    -> Officer Final Approval -> Full Audit Trail & Official Cadastre Immutability Verification.
    """
    admin_auth_headers = auth_tokens["admin"]
    officer_auth_headers = auth_tokens["officer"]
    surveyor_auth_headers = auth_tokens["surveyor"]
    citizen_auth_headers = auth_tokens["citizen"]

    jur_id = str(seed_test_data["jur"].id)
    org_id = str(seed_test_data["org"].id)
    surveyor_id = str(seed_test_data["users"]["SURVEYOR"].id)

    # 1. Prerequisite: Create Parcel and Building in test jurisdiction
    parcel_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": jur_id,
            "parcel_number": f"P-{uuid.uuid4().hex[:4]}",
            "parcel_code": f"GV-E2E-{uuid.uuid4().hex[:6]}",
            "land_use": "COMMERCIAL",
            "geometry": "POLYGON((78.4860 17.3820, 78.4890 17.3820, 78.4890 17.3850, 78.4860 17.3850, 78.4860 17.3820))",
        },
        headers=officer_auth_headers,
    )
    assert parcel_res.status_code == 201
    parcel_id = parcel_res.json()["id"]

    bld_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": f"BLD-E2E-{uuid.uuid4().hex[:6]}",
            "building_type": "COMMERCIAL",
            "height_estimate": 26.0,
            "geometry": "POLYGON((78.4865 17.3825, 78.4885 17.3825, 78.4885 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=officer_auth_headers,
    )
    assert bld_res.status_code == 201
    bld_id = bld_res.json()["id"]

    # ------------------------------------------------------------------------
    # Step 1: Cadastral Officer creates Survey Project
    # ------------------------------------------------------------------------
    proj_code = f"PRJ-E2E-{uuid.uuid4().hex[:6]}"
    proj_res = await client.post(
        "/api/v1/survey-projects",
        json={
            "organization_id": org_id,
            "jurisdiction_id": jur_id,
            "name": "E2E Field Verification Project",
            "code": proj_code,
            "description": "Verifying high-density commercial parcel and vertical building attributes.",
        },
        headers=officer_auth_headers,
    )
    assert proj_res.status_code == 201
    project_data = proj_res.json()
    project_id = project_data["id"]
    assert project_data["code"] == proj_code
    assert project_data["status"] == "DRAFT"

    # ------------------------------------------------------------------------
    # Step 2: Cadastral Officer dispatches Survey Assignment to Surveyor
    # ------------------------------------------------------------------------
    asgn_res = await client.post(
        f"/api/v1/survey-projects/{project_id}/assignments",
        json={
            "survey_project_id": project_id,
            "surveyor_id": surveyor_id,
            "jurisdiction_id": jur_id,
            "parcel_id": parcel_id,
            "building_id": bld_id,
            "priority": "HIGH",
            "notes": "Verify height of roof structures and confirm ground floor commercial occupancy.",
        },
        headers=officer_auth_headers,
    )
    assert asgn_res.status_code == 201
    asgn_data = asgn_res.json()
    assignment_id = asgn_data["id"]
    assert asgn_data["status"] == "ASSIGNED"
    assert asgn_data["priority"] == "HIGH"

    # Step 3: RBAC check - Citizen forbidden from accepting survey assignments
    cit_accept = await client.post(
        f"/api/v1/survey-assignments/{assignment_id}/accept",
        headers=citizen_auth_headers,
    )
    assert cit_accept.status_code == 403

    # ------------------------------------------------------------------------
    # Step 4: Surveyor Accepts Assignment
    # ------------------------------------------------------------------------
    accept_res = await client.post(
        f"/api/v1/survey-assignments/{assignment_id}/accept",
        headers=surveyor_auth_headers,
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "ACCEPTED"

    # ------------------------------------------------------------------------
    # Step 5: Surveyor Starts Field Session (Assignment -> IN_PROGRESS)
    # ------------------------------------------------------------------------
    start_res = await client.post(
        f"/api/v1/survey-assignments/{assignment_id}/start",
        headers=surveyor_auth_headers,
    )
    assert start_res.status_code == 200
    session_data = start_res.json()
    session_id = session_data["id"]
    assert session_data["status"] == "ACTIVE"

    asgn_check = await client.get(
        f"/api/v1/survey-assignments/{assignment_id}",
        headers=surveyor_auth_headers,
    )
    assert asgn_check.json()["status"] == "IN_PROGRESS"

    # ------------------------------------------------------------------------
    # Step 6: Surveyor Captures Field Observations with GPS Coordinates
    # ------------------------------------------------------------------------
    # Obs 1: Building Height (discrepant initial measurement: 31.5m vs 26.0m official)
    obs1_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/observations",
        json={
            "observation_type": "BUILDING_HEIGHT",
            "target_type": "BUILDING",
            "target_id": bld_id,
            "value": "31.5",
            "unit": "m",
            "latitude": 17.3835,
            "longitude": 78.4835,
            "horizontal_accuracy": 3.8,
            "source": "GPS",
            "notes": "Laser rangefinder measurement from south street curb.",
        },
        headers=surveyor_auth_headers,
    )
    assert obs1_res.status_code == 201
    obs1_id = obs1_res.json()["id"]

    # Obs 2: Floor Count
    obs2_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/observations",
        json={
            "observation_type": "FLOOR_COUNT",
            "target_type": "BUILDING",
            "target_id": bld_id,
            "value": "8",
            "unit": "floors",
            "latitude": 17.3835,
            "longitude": 78.4835,
            "horizontal_accuracy": 3.8,
            "source": "GPS",
        },
        headers=surveyor_auth_headers,
    )
    assert obs2_res.status_code == 201

    # ------------------------------------------------------------------------
    # Step 7: Cryptographic Photo Evidence Upload with SHA-256 Hashing
    # ------------------------------------------------------------------------
    photo_bytes = b"GEODETIC_SURVEY_RAW_IMAGE_DATA_WITH_METADATA_AND_EXIF_COORDINATES_STAMP"
    expected_hash = hashlib.sha256(photo_bytes).hexdigest()

    upload_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/evidence",
        files={"file": ("building_south_facade.jpg", io.BytesIO(photo_bytes), "image/jpeg")},
        data={
            "evidence_type": "BUILDING_FACADE",
            "target_type": "BUILDING",
            "target_id": bld_id,
            "observation_id": obs1_id,
            "latitude": "17.3835",
            "longitude": "78.4835",
            "accuracy": "3.8",
            "description": "South facade elevation showing upper mechanical level.",
        },
        headers=surveyor_auth_headers,
    )
    assert upload_res.status_code == 201
    evidence_data = upload_res.json()
    assert evidence_data["sha256_hash"] == expected_hash
    evidence_id = evidence_data["id"]

    # Step 8: Verify Evidence file download and integrity
    file_res = await client.get(
        f"/api/v1/survey-evidence/{evidence_id}/file",
        headers=surveyor_auth_headers,
    )
    assert file_res.status_code == 200
    assert file_res.content == photo_bytes

    # ------------------------------------------------------------------------
    # Step 9: Pause and Resume Session Lifecycle
    # ------------------------------------------------------------------------
    pause_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/pause",
        headers=surveyor_auth_headers,
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    resume_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/resume",
        headers=surveyor_auth_headers,
    )
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "ACTIVE"

    # ------------------------------------------------------------------------
    # Step 10: Offline Batch Synchronization & Idempotency Engine
    # ------------------------------------------------------------------------
    client_op_id = f"op_offline_{uuid.uuid4().hex[:8]}"
    sync_payload = {
        "operations": [
            {
                "client_operation_id": client_op_id,
                "session_id": session_id,
                "operation_type": "CREATE_OBSERVATION",
                "entity_type": "SURVEY_OBSERVATION",
                "entity_id": str(uuid.uuid4()),
                "payload": {
                    "observation_type": "LAND_USE",
                    "target_type": "PARCEL",
                    "target_id": parcel_id,
                    "value": "COMMERCIAL",
                    "notes": "Verified active ground-level commercial usage.",
                    "latitude": 17.3835,
                    "longitude": 78.4835,
                    "horizontal_accuracy": 3.2,
                    "source": "FIELD_OBSERVATION",
                },
            }
        ]
    }

    # First sync run
    sync_res = await client.post(
        "/api/v1/sync/batch",
        json=sync_payload,
        headers=surveyor_auth_headers,
    )
    assert sync_res.status_code == 200
    sync_result = sync_res.json()
    assert sync_result["total_processed"] == 1
    assert sync_result["synced_count"] == 1
    assert sync_result["results"][0]["status"] == "SYNCED"

    # Idempotent replay of exact same operation
    replay_res = await client.post(
        "/api/v1/sync/batch",
        json=sync_payload,
        headers=surveyor_auth_headers,
    )
    assert replay_res.status_code == 200
    assert replay_res.json()["results"][0]["status"] == "SYNCED"

    # ------------------------------------------------------------------------
    # Step 11: Pre-Submission Cadastral Validation Engine
    # ------------------------------------------------------------------------
    val_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/validate",
        headers=surveyor_auth_headers,
    )
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["can_submit"] is True
    assert val_data["checklist"]["required_fields"] is True
    assert val_data["checklist"]["evidence_attached"] is True

    # ------------------------------------------------------------------------
    # Step 12: Surveyor Submits Survey for Officer Review
    # ------------------------------------------------------------------------
    submit_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/submit",
        headers=surveyor_auth_headers,
    )
    assert submit_res.status_code == 201
    submission_data = submit_res.json()
    assert submission_data["version_number"] == 1
    assert submission_data["status"] == "SUBMITTED"
    submission_id = submission_data["id"]

    # Verify assignment status is now SUBMITTED
    asgn_check = await client.get(
        f"/api/v1/survey-assignments/{assignment_id}",
        headers=surveyor_auth_headers,
    )
    assert asgn_check.json()["status"] == "SUBMITTED"

    # ------------------------------------------------------------------------
    # Step 13: RBAC Enforcement - Surveyor cannot approve their own survey
    # ------------------------------------------------------------------------
    self_approve = await client.post(
        f"/api/v1/survey-submissions/{submission_id}/approve",
        json={"review_notes": "Attempting self-approval"},
        headers=surveyor_auth_headers,
    )
    assert self_approve.status_code == 403

    # ------------------------------------------------------------------------
    # Step 14: Cadastral Officer Requests Revision (Mandatory Review Notes)
    # ------------------------------------------------------------------------
    # Attempting revision without review notes must fail (400 Bad Request)
    empty_rev = await client.post(
        f"/api/v1/survey-submissions/{submission_id}/request-revision",
        json={"review_notes": "   "},
        headers=officer_auth_headers,
    )
    assert empty_rev.status_code == 400

    # Revision with proper notes
    revision_res = await client.post(
        f"/api/v1/survey-submissions/{submission_id}/request-revision",
        json={
            "review_notes": "Building height 31.5m appears to include roof telecommunication antenna. Official permit is 26.0m. Please remeasure building roof parapet line."
        },
        headers=officer_auth_headers,
    )
    assert revision_res.status_code == 200
    rev_data = revision_res.json()
    assert rev_data["status"] == "REVISION_REQUIRED"

    # Verify assignment transitioned to REVISION_REQUIRED
    asgn_rev = await client.get(
        f"/api/v1/survey-assignments/{assignment_id}",
        headers=officer_auth_headers,
    )
    assert asgn_rev.json()["status"] == "REVISION_REQUIRED"

    # ------------------------------------------------------------------------
    # Step 15: Surveyor Remeasures and Submits Version 2
    # ------------------------------------------------------------------------
    # Start revision session
    re_start = await client.post(
        f"/api/v1/survey-assignments/{assignment_id}/start",
        headers=surveyor_auth_headers,
    )
    assert re_start.status_code == 200
    sess2_id = re_start.json()["id"]

    # Record corrected measurement: 26.0m (matching official cadastre)
    await client.post(
        f"/api/v1/survey-sessions/{sess2_id}/observations",
        json={
            "observation_type": "BUILDING_HEIGHT",
            "target_type": "BUILDING",
            "target_id": bld_id,
            "value": "26.0",
            "unit": "m",
            "latitude": 17.3835,
            "longitude": 78.4835,
            "horizontal_accuracy": 2.1,
            "source": "GPS",
            "notes": "Parapet structural top measured excluding auxiliary radio mast.",
        },
        headers=surveyor_auth_headers,
    )

    # Attach verified evidence
    corr_bytes = b"CORRECTED_PARAPET_EVIDENCE_PHOTO_DATA"
    await client.post(
        f"/api/v1/survey-sessions/{sess2_id}/evidence",
        files={"file": ("parapet_line.jpg", io.BytesIO(corr_bytes), "image/jpeg")},
        data={
            "evidence_type": "ROOF_STRUCTURE",
            "target_type": "BUILDING",
            "target_id": bld_id,
            "description": "Roof parapet edge detail.",
        },
        headers=surveyor_auth_headers,
    )

    # Submit Version 2
    sub2_res = await client.post(
        f"/api/v1/survey-sessions/{sess2_id}/submit",
        headers=surveyor_auth_headers,
    )
    assert sub2_res.status_code == 201
    sub2_data = sub2_res.json()
    assert sub2_data["version_number"] == 2
    assert sub2_data["status"] == "SUBMITTED"
    sub2_id = sub2_data["id"]

    # ------------------------------------------------------------------------
    # Step 16: Cadastral Officer Approves Final Submission
    # ------------------------------------------------------------------------
    approve_res = await client.post(
        f"/api/v1/survey-submissions/{sub2_id}/approve",
        json={"review_notes": "Parapet height of 26.0m verified against spatial cadastre. All checks pass."},
        headers=officer_auth_headers,
    )
    assert approve_res.status_code == 200
    app_data = approve_res.json()
    assert app_data["status"] == "APPROVED"

    # Verify assignment is now APPROVED
    asgn_final = await client.get(
        f"/api/v1/survey-assignments/{assignment_id}",
        headers=officer_auth_headers,
    )
    assert asgn_final.json()["status"] == "APPROVED"
    assert asgn_final.json()["completed_at"] is not None

    # ------------------------------------------------------------------------
    # Step 17: Official Cadastre Record Invariance Verification
    # (Surveys are evidence records only - official cadastre is NOT overwritten)
    # ------------------------------------------------------------------------
    bld_check = await client.get(
        f"/api/v1/buildings/{bld_id}",
        headers=officer_auth_headers,
    )
    assert bld_check.status_code == 200
    # Official building record remains exactly what it was created as (26.0m)
    assert bld_check.json()["height_estimate"] == 26.0

    # ------------------------------------------------------------------------
    # Step 18: Audit Trail Verification
    # ------------------------------------------------------------------------
    audit_res = await client.get(
        "/api/v1/audit?limit=100",
        headers=admin_auth_headers,
    )
    assert audit_res.status_code == 200
    audit_items = audit_res.json()["items"]
    audit_actions = [a["action"] for a in audit_items]

    assert "SURVEY_PROJECT_CREATED" in audit_actions
    assert "SURVEY_ASSIGNED" in audit_actions
    assert "SURVEY_ACCEPTED" in audit_actions
    assert "SURVEY_STARTED" in audit_actions
    assert "SURVEY_PAUSED" in audit_actions
    assert "SURVEY_RESUMED" in audit_actions
    assert "OBSERVATION_CREATED" in audit_actions
    assert "EVIDENCE_UPLOADED" in audit_actions
    assert "SURVEY_SUBMITTED" in audit_actions
    assert "SURVEY_REVISION_REQUESTED" in audit_actions
    assert "SURVEY_APPROVED" in audit_actions
