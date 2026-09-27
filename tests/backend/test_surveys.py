import io
import json
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_survey_project_and_assignment_lifecycle(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    org = seed_test_data["org"]
    surveyor_user = seed_test_data["users"]["SURVEYOR"]
    officer_headers = auth_tokens["officer"]
    surveyor_headers = auth_tokens["surveyor"]

    # 1. Officer creates a cadastral parcel and building
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-SRV-01",
            "parcel_code": "GV-W500-PSRV01",
            "land_use": "COMMERCIAL",
            "geometry": "POLYGON((78.4860 17.3820, 78.4890 17.3820, 78.4890 17.3850, 78.4860 17.3850, 78.4860 17.3820))",
        },
        headers=officer_headers,
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-SRV-001",
            "building_type": "COMMERCIAL",
            "height_estimate": 15.0,
            "geometry": "POLYGON((78.4865 17.3825, 78.4885 17.3825, 78.4885 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=officer_headers,
    )
    assert b_res.status_code == 201
    building_id = b_res.json()["id"]

    # 2. Officer creates Survey Project
    proj_res = await client.post(
        "/api/v1/survey-projects",
        json={
            "organization_id": str(org.id),
            "jurisdiction_id": str(jur.id),
            "name": "Ward 500 Cadastral Audit",
            "code": "PRJ-W500-2026-01",
            "description": "Field verification of high-density commercial properties",
            "status": "ACTIVE",
        },
        headers=officer_headers,
    )
    assert proj_res.status_code == 201
    proj_data = proj_res.json()
    assert proj_data["code"] == "PRJ-W500-2026-01"
    project_id = proj_data["id"]

    # 3. Officer assigns surveyor to target building and parcel
    assign_res = await client.post(
        f"/api/v1/survey-projects/{project_id}/assignments",
        json={
            "survey_project_id": project_id,
            "surveyor_id": str(surveyor_user.id),
            "jurisdiction_id": str(jur.id),
            "parcel_id": parcel_id,
            "building_id": building_id,
            "priority": "HIGH",
            "status": "ASSIGNED",
            "notes": "Verify height and floor count",
        },
        headers=officer_headers,
    )
    assert assign_res.status_code == 201
    assign_data = assign_res.json()
    assert assign_data["status"] == "ASSIGNED"
    assert assign_data["priority"] == "HIGH"
    assignment_id = assign_data["id"]

    # 4. Surveyor lists assignments and sees newly assigned task
    list_res = await client.get("/api/v1/survey-assignments", headers=surveyor_headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(a["id"] == assignment_id for a in items)

    # 5. Surveyor accepts assignment
    accept_res = await client.post(f"/api/v1/survey-assignments/{assignment_id}/accept", headers=surveyor_headers)
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "ACCEPTED"

    # 6. Surveyor starts field survey session
    start_res = await client.post(f"/api/v1/survey-assignments/{assignment_id}/start", headers=surveyor_headers)
    assert start_res.status_code == 200
    session_data = start_res.json()
    assert session_data["status"] == "ACTIVE"
    session_id = session_data["id"]

    # 7. Pause and Resume session
    pause_res = await client.post(f"/api/v1/survey-sessions/{session_id}/pause", headers=surveyor_headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    resume_res = await client.post(f"/api/v1/survey-sessions/{session_id}/resume", headers=surveyor_headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_survey_observation_and_evidence_capture(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    org = seed_test_data["org"]
    surveyor_user = seed_test_data["users"]["SURVEYOR"]
    officer_headers = auth_tokens["officer"]
    surveyor_headers = auth_tokens["surveyor"]

    # Create project and assignment
    proj_res = await client.post(
        "/api/v1/survey-projects",
        json={
            "organization_id": str(org.id),
            "jurisdiction_id": str(jur.id),
            "name": "Observation Test Project",
            "code": "PRJ-OBS-01",
            "status": "ACTIVE",
        },
        headers=officer_headers,
    )
    project_id = proj_res.json()["id"]

    assign_res = await client.post(
        f"/api/v1/survey-projects/{project_id}/assignments",
        json={
            "survey_project_id": project_id,
            "surveyor_id": str(surveyor_user.id),
            "jurisdiction_id": str(jur.id),
            "status": "ASSIGNED",
        },
        headers=officer_headers,
    )
    assignment_id = assign_res.json()["id"]

    # Start session
    start_res = await client.post(f"/api/v1/survey-assignments/{assignment_id}/start", headers=surveyor_headers)
    session_id = start_res.json()["id"]

    # 1. Record Field Observation (Building Height with GNSS Coordinates)
    obs_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/observations",
        json={
            "observation_type": "BUILDING_HEIGHT",
            "target_type": "BUILDING",
            "target_id": "BLD-TEST-001",
            "value": "18.5",
            "unit": "m",
            "latitude": 17.3828,
            "longitude": 78.4875,
            "horizontal_accuracy": 3.2,
            "source": "LASER",
            "notes": "Laser rangefinder measurement from southern boundary",
        },
        headers=surveyor_headers,
    )
    assert obs_res.status_code == 201
    obs_data = obs_res.json()
    assert obs_data["value"] == "18.5"
    assert obs_data["horizontal_accuracy"] == 3.2
    obs_id = obs_data["id"]

    # 2. Upload Photo Evidence
    fake_image_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00" + (b"\x00" * 100)
    upload_res = await client.post(
        f"/api/v1/survey-sessions/{session_id}/evidence",
        files={"file": ("front_facade.jpg", io.BytesIO(fake_image_bytes), "image/jpeg")},
        data={
            "evidence_type": "BUILDING_FRONT",
            "target_type": "BUILDING",
            "target_id": "BLD-TEST-001",
            "observation_id": obs_id,
            "description": "Front facade elevation photograph",
            "latitude": "17.3828",
            "longitude": "78.4875",
            "accuracy": "3.5",
        },
        headers=surveyor_headers,
    )
    assert upload_res.status_code == 201
    evidence_data = upload_res.json()
    assert evidence_data["filename"] == "front_facade.jpg"
    assert len(evidence_data["sha256_hash"]) == 64
    evidence_id = evidence_data["id"]

    # 3. Retrieve Protected Photo File
    file_res = await client.get(f"/api/v1/survey-evidence/{evidence_id}/file", headers=surveyor_headers)
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "image/jpeg"
    assert len(file_res.content) == len(fake_image_bytes)

    # 4. Run Deterministic Validation Engine
    val_res = await client.post(f"/api/v1/survey-sessions/{session_id}/validate", headers=surveyor_headers)
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is True
    assert val_data["can_submit"] is True
    assert val_data["checklist"]["required_fields"] is True
    assert val_data["checklist"]["location_captured"] is True
    assert val_data["checklist"]["evidence_attached"] is True


@pytest.mark.asyncio
async def test_survey_submission_and_officer_review_workflow(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    org = seed_test_data["org"]
    surveyor_user = seed_test_data["users"]["SURVEYOR"]
    officer_headers = auth_tokens["officer"]
    surveyor_headers = auth_tokens["surveyor"]

    # Create Cadastral Building with recorded height 15.0m
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-REV-01",
            "parcel_code": "GV-W500-PREV01",
            "land_use": "COMMERCIAL",
            "geometry": "POLYGON((78.4860 17.3820, 78.4890 17.3820, 78.4890 17.3850, 78.4860 17.3850, 78.4860 17.3820))",
        },
        headers=officer_headers,
    )
    parcel_id = p_res.json()["id"]

    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-REV-001",
            "building_type": "COMMERCIAL",
            "height_estimate": 15.0,
            "geometry": "POLYGON((78.4865 17.3825, 78.4885 17.3825, 78.4885 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=officer_headers,
    )
    bld_id = b_res.json()["id"]

    # Project and assignment
    proj_res = await client.post(
        "/api/v1/survey-projects",
        json={
            "organization_id": str(org.id),
            "jurisdiction_id": str(jur.id),
            "name": "Review Workflow Project",
            "code": "PRJ-REV-01",
            "status": "ACTIVE",
        },
        headers=officer_headers,
    )
    project_id = proj_res.json()["id"]

    assign_res = await client.post(
        f"/api/v1/survey-projects/{project_id}/assignments",
        json={
            "survey_project_id": project_id,
            "surveyor_id": str(surveyor_user.id),
            "jurisdiction_id": str(jur.id),
            "parcel_id": parcel_id,
            "building_id": bld_id,
            "status": "ASSIGNED",
        },
        headers=officer_headers,
    )
    assignment_id = assign_res.json()["id"]

    # Surveyor starts survey
    start_res = await client.post(f"/api/v1/survey-assignments/{assignment_id}/start", headers=surveyor_headers)
    session_id = start_res.json()["id"]

    # Record observation with height 18.0m (differs by +3.0m from official 15.0m)
    await client.post(
        f"/api/v1/survey-sessions/{session_id}/observations",
        json={
            "observation_type": "BUILDING_HEIGHT",
            "target_type": "BUILDING",
            "target_id": bld_id,
            "value": "18.0",
            "unit": "m",
            "latitude": 17.383,
            "longitude": 78.487,
            "horizontal_accuracy": 2.5,
            "source": "GNSS",
        },
        headers=surveyor_headers,
    )

    # Upload evidence
    fake_img = b"\xFF\xD8\xFF\xE0" + (b"\x01" * 80)
    await client.post(
        f"/api/v1/survey-sessions/{session_id}/evidence",
        files={"file": ("photo.jpg", io.BytesIO(fake_img), "image/jpeg")},
        data={"evidence_type": "BUILDING_FRONT", "target_type": "BUILDING", "target_id": bld_id},
        headers=surveyor_headers,
    )

    # 1. Surveyor Submits Survey
    sub_res = await client.post(f"/api/v1/survey-sessions/{session_id}/submit", headers=surveyor_headers)
    assert sub_res.status_code == 201
    sub_data = sub_res.json()
    assert sub_data["version_number"] == 1
    assert sub_data["status"] == "SUBMITTED"
    submission_id = sub_data["id"]

    # Verify assignment is SUBMITTED
    assign_check = await client.get(f"/api/v1/survey-assignments/{assignment_id}", headers=officer_headers)
    assert assign_check.json()["status"] == "SUBMITTED"

    # 2. Officer Reviews Submission and Requests Revision
    rev_res = await client.post(
        f"/api/v1/survey-submissions/{submission_id}/request-revision",
        json={"review_notes": "Please verify if the rooftop parapet was included in the 18.0m height measurement."},
        headers=officer_headers,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "REVISION_REQUIRED"

    # Verify assignment became REVISION_REQUIRED
    assign_check = await client.get(f"/api/v1/survey-assignments/{assignment_id}", headers=officer_headers)
    assert assign_check.json()["status"] == "REVISION_REQUIRED"

    # 3. Surveyor Re-starts / edits and Resubmits
    reopen_res = await client.post(f"/api/v1/survey-assignments/{assignment_id}/start", headers=surveyor_headers)
    assert reopen_res.status_code == 200
    resumed_session_id = reopen_res.json()["id"]

    # Surveyor corrects measurement to 15.2m (excluding parapet)
    await client.post(
        f"/api/v1/survey-sessions/{resumed_session_id}/observations",
        json={
            "observation_type": "BUILDING_HEIGHT",
            "target_type": "BUILDING",
            "target_id": bld_id,
            "value": "15.2",
            "unit": "m",
            "latitude": 17.383,
            "longitude": 78.487,
            "horizontal_accuracy": 1.8,
            "source": "LASER",
            "notes": "Parapet excluded, measuring strictly to roof slab line",
        },
        headers=surveyor_headers,
    )

    resub_res = await client.post(f"/api/v1/survey-sessions/{resumed_session_id}/submit", headers=surveyor_headers)
    assert resub_res.status_code == 201
    assert resub_res.json()["version_number"] == 2
    resub_id = resub_res.json()["id"]

    # 4. Officer Approves Resubmission
    appr_res = await client.post(
        f"/api/v1/survey-submissions/{resub_id}/approve",
        json={"review_notes": "Approved. Height 15.2m verified against architectural plan."},
        headers=officer_headers,
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED"

    # 5. Verify Cadastral Invariant: Official building footprint record is NOT changed!
    bld_check = await client.get(f"/api/v1/buildings/{bld_id}", headers=officer_headers)
    assert bld_check.status_code == 200
    assert bld_check.json()["height_estimate"] == 15.0  # Remains original 15.0m; survey is recorded evidence


@pytest.mark.asyncio
async def test_offline_batch_sync_and_idempotency(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    org = seed_test_data["org"]
    surveyor_user = seed_test_data["users"]["SURVEYOR"]
    officer_headers = auth_tokens["officer"]
    surveyor_headers = auth_tokens["surveyor"]

    # Project and assignment
    proj_res = await client.post(
        "/api/v1/survey-projects",
        json={
            "organization_id": str(org.id),
            "jurisdiction_id": str(jur.id),
            "name": "Sync Test Project",
            "code": "PRJ-SYNC-01",
            "status": "ACTIVE",
        },
        headers=officer_headers,
    )
    project_id = proj_res.json()["id"]

    assign_res = await client.post(
        f"/api/v1/survey-projects/{project_id}/assignments",
        json={
            "survey_project_id": project_id,
            "surveyor_id": str(surveyor_user.id),
            "jurisdiction_id": str(jur.id),
            "status": "ASSIGNED",
        },
        headers=officer_headers,
    )
    assignment_id = assign_res.json()["id"]

    start_res = await client.post(f"/api/v1/survey-assignments/{assignment_id}/start", headers=surveyor_headers)
    session_id = start_res.json()["id"]

    # 1. Post Batch Sync with 2 queued offline operations
    batch_payload = {
        "operations": [
            {
                "client_operation_id": "offline-op-001",
                "session_id": session_id,
                "operation_type": "CREATE_OBSERVATION",
                "entity_type": "survey_observation",
                "entity_id": "temp-obs-1",
                "payload": {
                    "observation_type": "BUILDING_HEIGHT",
                    "target_type": "BUILDING",
                    "target_id": "BLD-OFFLINE-01",
                    "value": "24.0",
                    "unit": "m",
                    "latitude": 17.384,
                    "longitude": 78.488,
                    "horizontal_accuracy": 3.8,
                    "source": "FIELD_OBSERVATION",
                },
            },
            {
                "client_operation_id": "offline-op-002",
                "session_id": session_id,
                "operation_type": "CREATE_OBSERVATION",
                "entity_type": "survey_observation",
                "entity_id": "temp-obs-2",
                "payload": {
                    "observation_type": "FLOOR_COUNT",
                    "target_type": "BUILDING",
                    "target_id": "BLD-OFFLINE-01",
                    "value": "6",
                    "unit": "count",
                    "source": "FIELD_OBSERVATION",
                },
            },
        ]
    }

    sync_res = await client.post("/api/v1/sync/batch", json=batch_payload, headers=surveyor_headers)
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["total_processed"] == 2
    assert sync_data["synced_count"] == 2
    assert sync_data["conflict_count"] == 0

    # 2. Idempotency Check: Resend identical batch
    sync_res2 = await client.post("/api/v1/sync/batch", json=batch_payload, headers=surveyor_headers)
    assert sync_res2.status_code == 200
    sync_data2 = sync_res2.json()
    assert sync_data2["total_processed"] == 2
    assert sync_data2["synced_count"] == 2

    # Verify no duplicate observations created (only 2 exist)
    obs_res = await client.get(f"/api/v1/survey-sessions/{session_id}/observations", headers=surveyor_headers)
    assert len(obs_res.json()) == 2


@pytest.mark.asyncio
async def test_survey_rbac_enforcement(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    org = seed_test_data["org"]
    citizen_headers = auth_tokens["citizen"]
    surveyor_headers = auth_tokens["surveyor"]

    # 1. Citizen cannot create survey project
    proj_res = await client.post(
        "/api/v1/survey-projects",
        json={
            "organization_id": str(org.id),
            "jurisdiction_id": str(jur.id),
            "name": "Citizen Hack Project",
            "code": "PRJ-CIT-01",
        },
        headers=citizen_headers,
    )
    assert proj_res.status_code == 403

    # 2. Citizen cannot list review submissions
    sub_res = await client.get("/api/v1/survey-submissions", headers=citizen_headers)
    assert sub_res.status_code == 403

    # 3. Surveyor cannot approve a submission
    fake_sub_id = "00000000-0000-0000-0000-000000000001"
    appr_res = await client.post(
        f"/api/v1/survey-submissions/{fake_sub_id}/approve",
        json={"review_notes": "Attempted surveyor self-approval"},
        headers=surveyor_headers,
    )
    assert appr_res.status_code == 403
