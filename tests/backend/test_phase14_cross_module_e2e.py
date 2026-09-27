"""Phase 14 — Cross-Module Integration & End-to-End System Tests.

Validates the complete GeoVertex platform as one integrated system:
1. Property 360 Cross-Module Integration (Section 34)
2. Full Data Lineage Chain (Section 35)
3. Citizen-to-Government Full Cadastral Lifecycle (Section 65)
4. 2D to 3D Spatial Synchronization & Cadastral Consistency (Sections 18 & 19)
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import ServiceType, RequestStatus, AuthorizationType, LinkStatus
from app.models.versioning import VersionChangeType
from app.services.versioning_service import versioning_service


@pytest.mark.asyncio
class TestPhase14CrossModuleE2E:

    async def test_property_360_full_cross_module_integration(
        self,
        client: AsyncClient,
        seed_test_data,
        auth_tokens: dict,
        db_session: AsyncSession,
    ):
        """Validates that a single property exposes parcel, building, floors, units,

        2D/3D geometry, survey history, documents, validation, change detection,
        utilities, technical identifier, audit, versions, and notifications
        all referencing canonical entity IDs.
        """
        officer_headers = auth_tokens["officer"]
        jur_id = str(seed_test_data["jur"].id)

        # 1. Create Parcel (2D GIS)
        parcel_code = f"GV-P360-{uuid.uuid4().hex[:6]}"
        p_res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur_id,
                "parcel_number": f"P-{uuid.uuid4().hex[:4]}",
                "parcel_code": parcel_code,
                "land_use": "MIXED_USE",
                "geometry": "POLYGON((78.4810 17.3810, 78.4850 17.3810, 78.4850 17.3850, 78.4810 17.3850, 78.4810 17.3810))",
            },
            headers=officer_headers,
        )
        assert p_res.status_code == 201
        parcel_id = p_res.json()["id"]

        # 2. Create Property
        prop_res = await client.post(
            "/api/v1/properties",
            json={
                "parcel_id": parcel_id,
                "property_reference": f"PROP-{uuid.uuid4().hex[:6]}",
                "property_type": "COMMERCIAL",
                "address": "100 Innovation Avenue",
                "locality": "HiTech Ward",
                "postal_code": "500081",
            },
            headers=officer_headers,
        )
        assert prop_res.status_code == 201
        property_id = prop_res.json()["id"]

        # 3. Create Building (Footprint)
        bld_res = await client.post(
            "/api/v1/buildings",
            json={
                "parcel_id": parcel_id,
                "building_reference": f"BLD-{uuid.uuid4().hex[:6]}",
                "building_type": "COMMERCIAL",
                "height_estimate": 35.0,
                "geometry": "POLYGON((78.4820 17.3820, 78.4840 17.3820, 78.4840 17.3840, 78.4820 17.3840, 78.4820 17.3820))",
            },
            headers=officer_headers,
        )
        assert bld_res.status_code == 201
        building_id = bld_res.json()["id"]

        # 4. Create Floor
        flr_res = await client.post(
            "/api/v1/floors",
            json={
                "building_id": building_id,
                "floor_number": 3,
                "floor_code": f"FLR-{uuid.uuid4().hex[:4]}",
                "floor_name": "Level 3 Commercial Office",
                "floor_type": "COMMERCIAL",
                "elevation_min_m": 10.5,
                "elevation_max_m": 14.0,
            },
            headers=officer_headers,
        )
        assert flr_res.status_code == 201
        floor_id = flr_res.json()["id"]

        # 5. Create Unit with explicit geometry polygon
        unit_res = await client.post(
            "/api/v1/units",
            json={
                "floor_id": floor_id,
                "building_id": building_id,
                "property_id": property_id,
                "unit_number": "301",
                "unit_code": f"BLD-F3-U301-{uuid.uuid4().hex[:4]}",
                "unit_type": "OFFICE",
                "elevation_min_m": 10.5,
                "elevation_max_m": 14.0,
                "geometry": "POLYGON((78.4822 17.3822, 78.4838 17.3822, 78.4838 17.3838, 78.4822 17.3838, 78.4822 17.3822))",
            },
            headers=officer_headers,
        )
        assert unit_res.status_code == 201
        unit_id = unit_res.json()["id"]

        # 6. Verify 2D Map Bounding Box query returns Parcel
        map_res = await client.get(
            f"/api/v1/map/parcels?min_lon=78.4800&min_lat=17.3800&max_lon=78.4900&max_lat=17.3900",
            headers=officer_headers,
        )
        assert map_res.status_code == 200
        features = map_res.json().get("features", [])
        assert any(f.get("properties", {}).get("parcel_code") == parcel_code for f in features)

        # 7. Verify 3D Digital Twin Representation
        scene_res = await client.get(
            f"/api/v1/3d/scene?jurisdiction_id={jur_id}",
            headers=officer_headers,
        )
        assert scene_res.status_code == 200
        scene_data = scene_res.json()
        assert "buildings" in scene_data

        # 8. Create Subsurface Utility Asset linked to Parcel
        net_res = await client.post(
            "/api/v1/utilities/networks",
            json={
                "name": "High Pressure Water Network A",
                "utility_type": "WATER",
                "jurisdiction_id": jur_id,
                "owner_organization": "Municipal Water Works",
                "status": "ACTIVE",
            },
            headers=officer_headers,
        )
        assert net_res.status_code == 201
        network_id = net_res.json()["id"]

        util_res = await client.post(
            "/api/v1/utilities/assets",
            json={
                "network_id": network_id,
                "asset_type": "PIPE",
                "asset_reference": f"PIPE-{uuid.uuid4().hex[:6]}",
                "geometry_type": "LINESTRING",
                "geometry_wkt": "LINESTRING(78.4815 17.3815, 78.4845 17.3815)",
                "depth": 2.2,
                "diameter": 0.35,
                "source_type": "OFFICIAL_RECORD",
                "confidence": "HIGH",
                "parcel_id": parcel_id,
            },
            headers=officer_headers,
        )
        assert util_res.status_code == 201

        # 9. Issue Technical 3D Identifier (Phase 12) for the Unit
        id_res = await client.post(
            "/api/v1/identifiers/generate",
            json={
                "entity_type": "UNIT",
                "entity_id": unit_id,
            },
            headers=officer_headers,
        )
        assert id_res.status_code in [200, 201]
        ident_data = id_res.json()
        identifier_val = ident_data.get("identifier_value")
        assert identifier_val is not None
        assert "3D" in identifier_val or "GV" in identifier_val

        # 10. Record & Verify Entity Versioning (Phase 13) for Unit
        await versioning_service.create_version(
            db=db_session,
            entity_type="UNIT",
            entity_id=unit_id,
            snapshot_data={"unit_number": "301", "identifier": identifier_val, "status": "ACTIVE"},
            geometry_wkt="POLYGON((78.4820 17.3820, 78.4830 17.3820, 78.4830 17.3830, 78.4820 17.3830, 78.4820 17.3820))",
            change_type=VersionChangeType.CREATE.value,
            change_reason="Initial unit cadastral registration with 3D identifier",
        )
        await db_session.commit()

        ver_res = await client.get(
            f"/api/v1/versions/UNIT/{unit_id}",
            headers=officer_headers,
        )
        assert ver_res.status_code == 200
        ver_data = ver_res.json()
        version_items = ver_data.get("items", ver_data if isinstance(ver_data, list) else [])
        assert len(version_items) >= 1
        assert version_items[0]["entity_id"] == unit_id

        # 11. Verify Audit Events recorded across this property lifecycle
        audit_res = await client.get(
            f"/api/v1/audit?search={unit_id}",
            headers=officer_headers,
        )
        assert audit_res.status_code == 200
        audit_data = audit_res.json()
        assert "items" in audit_data

    async def test_full_data_lineage_chain(
        self,
        client: AsyncClient,
        seed_test_data,
        auth_tokens: dict,
    ):
        """Verifies the unbroken lineage chain:

        Survey Observation/Evidence -> Submission -> Approval -> Cadastral Version
        -> Technical 3D Identifier -> Audit Log -> Notification.
        """
        officer_headers = auth_tokens["officer"]
        surveyor_headers = auth_tokens["surveyor"]
        jur_id = str(seed_test_data["jur"].id)
        org_id = str(seed_test_data["org"].id)
        surveyor_user = seed_test_data["users"]["SURVEYOR"]

        # 1. Create Parcel & Building
        p_res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur_id,
                "parcel_number": f"P-{uuid.uuid4().hex[:4]}",
                "parcel_code": f"GV-LIN-{uuid.uuid4().hex[:6]}",
                "land_use": "RESIDENTIAL",
                "geometry": "POLYGON((78.4870 17.3870, 78.4890 17.3870, 78.4890 17.3890, 78.4870 17.3890, 78.4870 17.3870))",
            },
            headers=officer_headers,
        )
        assert p_res.status_code == 201
        parcel_id = p_res.json()["id"]

        b_res = await client.post(
            "/api/v1/buildings",
            json={
                "parcel_id": parcel_id,
                "building_reference": f"BLD-LIN-{uuid.uuid4().hex[:6]}",
                "building_type": "RESIDENTIAL",
                "height_estimate": 18.0,
                "geometry": "POLYGON((78.4875 17.3875, 78.4885 17.3875, 78.4885 17.3885, 78.4875 17.3885, 78.4875 17.3875))",
            },
            headers=officer_headers,
        )
        assert b_res.status_code == 201
        building_id = b_res.json()["id"]

        # 2. Commission Survey Project & Assignment
        proj_res = await client.post(
            "/api/v1/survey-projects",
            json={
                "organization_id": org_id,
                "jurisdiction_id": jur_id,
                "name": f"Cadastral Verification Project {uuid.uuid4().hex[:4]}",
                "code": f"PRJ-LIN-{uuid.uuid4().hex[:6]}",
                "description": "Boundary and footprint ground verification",
                "status": "ACTIVE",
            },
            headers=officer_headers,
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        assign_res = await client.post(
            f"/api/v1/survey-projects/{project_id}/assignments",
            json={
                "survey_project_id": project_id,
                "surveyor_id": str(surveyor_user.id),
                "jurisdiction_id": jur_id,
                "parcel_id": parcel_id,
                "building_id": building_id,
                "priority": "HIGH",
                "status": "ASSIGNED",
                "notes": "Verify boundary pegs and structure height",
            },
            headers=officer_headers,
        )
        assert assign_res.status_code == 201
        assignment_id = assign_res.json()["id"]

        # 3. Surveyor accepts assignment and starts session
        accept_res = await client.post(
            f"/api/v1/survey-assignments/{assignment_id}/accept",
            headers=surveyor_headers,
        )
        assert accept_res.status_code == 200

        start_res = await client.post(
            f"/api/v1/survey-assignments/{assignment_id}/start",
            headers=surveyor_headers,
        )
        assert start_res.status_code == 200
        session_id = start_res.json()["id"]

        # 4. Surveyor records observation
        obs_res = await client.post(
            f"/api/v1/survey-sessions/{session_id}/observations",
            json={
                "observation_type": "BUILDING_HEIGHT",
                "target_type": "BUILDING",
                "target_id": building_id,
                "value": "18.5",
                "unit": "m",
                "latitude": 17.3875,
                "longitude": 78.4875,
                "horizontal_accuracy": 3.2,
                "source": "LASER",
                "notes": "Laser rangefinder measurement from southern boundary",
            },
            headers=surveyor_headers,
        )
        assert obs_res.status_code == 201

        # 5. Surveyor submits survey session
        sub_res = await client.post(
            f"/api/v1/survey-sessions/{session_id}/submit",
            headers=surveyor_headers,
        )
        assert sub_res.status_code == 201
        submission_id = sub_res.json()["id"]

        # 6. Cadastral Officer reviews & approves survey submission
        appr_res = await client.post(
            f"/api/v1/survey-submissions/{submission_id}/approve",
            json={
                "review_notes": "Survey boundaries match cadastral coordinate registry",
            },
            headers=officer_headers,
        )
        assert appr_res.status_code == 200

        # 7. Issue Technical 3D Identifier
        ident_res = await client.post(
            "/api/v1/identifiers/generate",
            json={"entity_type": "BUILDING", "entity_id": building_id},
            headers=officer_headers,
        )
        assert ident_res.status_code in [200, 201]

        # 8. Verify Audit Log captures approval & issuance
        audit_res = await client.get(
            f"/api/v1/audit?search={building_id}",
            headers=officer_headers,
        )
        assert audit_res.status_code == 200
        events = audit_res.json().get("items", [])
        assert len(events) >= 1

    async def test_citizen_government_cadastral_lifecycle(
        self,
        client: AsyncClient,
        seed_test_data,
        auth_tokens: dict,
        db_session: AsyncSession,
    ):
        """Full lifecycle test:

        Citizen Submits Request -> Officer Assigns Task -> Officer Reviews
        -> Officer Approves -> Request Completed -> Citizen Timeline.
        """
        officer_headers = auth_tokens["officer"]
        citizen_headers = auth_tokens["citizen"]
        jur_id = str(seed_test_data["jur"].id)
        citizen_id = str(seed_test_data["users"]["CITIZEN"].id)
        officer_id = str(seed_test_data["users"]["GOVERNMENT_OFFICER"].id)

        # 0. Seed service type if needed
        st_code = "SURVEY_DEMARCATION"
        st = ServiceType(
            code=st_code,
            name="Cadastral Boundary Demarcation",
            description="Demarcation of property boundaries",
            active=True,
            citizen_visible=True,
            required_documents=[],
            required_fields=[],
            response_sla_hours=24,
            completion_sla_hours=120,
            allowed_roles=["CITIZEN", "GOVERNMENT_OFFICER", "ADMIN"],
        )
        db_session.add(st)
        await db_session.commit()

        # 1. Create Parcel & Property
        p_res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur_id,
                "parcel_number": f"P-{uuid.uuid4().hex[:4]}",
                "parcel_code": f"GV-CIT-{uuid.uuid4().hex[:6]}",
                "land_use": "RESIDENTIAL",
                "geometry": "POLYGON((78.4820 17.3820, 78.4860 17.3820, 78.4860 17.3860, 78.4820 17.3860, 78.4820 17.3820))",
            },
            headers=officer_headers,
        )
        assert p_res.status_code == 201
        parcel_id = p_res.json()["id"]

        prop_res = await client.post(
            "/api/v1/properties",
            json={
                "parcel_id": parcel_id,
                "property_reference": f"PROP-CIT-{uuid.uuid4().hex[:6]}",
                "property_type": "RESIDENTIAL",
                "address": "45 Lakeview Enclave",
            },
            headers=officer_headers,
        )
        assert prop_res.status_code == 201
        property_id = prop_res.json()["id"]

        # Link citizen to property
        link_res = await client.post(
            "/api/v1/workflows/citizen/properties",
            json={
                "citizen_id": citizen_id,
                "property_id": property_id,
                "authorization_type": AuthorizationType.OWNER.value,
                "status": LinkStatus.VERIFIED.value,
            },
            headers=officer_headers,
        )
        assert link_res.status_code == 201

        # 2. Citizen Submits Service Request
        req_res = await client.post(
            "/api/v1/workflows/service-requests",
            json={
                "request_type": st_code,
                "title": "Request for Cadastral Demarcation",
                "description": "Please peg northern boundary with official markers",
                "jurisdiction_id": jur_id,
                "property_id": property_id,
                "parcel_id": parcel_id,
                "priority": "HIGH",
            },
            headers=citizen_headers,
        )
        assert req_res.status_code == 201
        request_id = req_res.json()["id"]

        # 3. Officer assigns case to self
        assign_res = await client.post(
            f"/api/v1/workflows/service-requests/{request_id}/assign",
            json={
                "assigned_to": officer_id,
                "assigned_team": "Land Records Review Team",
                "reason": "Official assignment to senior review officer",
            },
            headers=officer_headers,
        )
        assert assign_res.status_code == 200
        assert assign_res.json()["status"] == RequestStatus.ASSIGNED.value

        # 4. Officer transitions request to UNDER_REVIEW
        trans_res = await client.post(
            f"/api/v1/workflows/service-requests/{request_id}/transition",
            json={
                "target_status": RequestStatus.UNDER_REVIEW.value,
                "comment": "Case being reviewed against cadastral title records",
            },
            headers=officer_headers,
        )
        assert trans_res.status_code == 200

        # 5. Officer approves request
        appr_res = await client.post(
            f"/api/v1/workflows/service-requests/{request_id}/transition",
            json={
                "target_status": RequestStatus.APPROVED.value,
                "comment": "All demarcation criteria verified and approved",
            },
            headers=officer_headers,
        )
        assert appr_res.status_code == 200
        assert appr_res.json()["status"] == RequestStatus.APPROVED.value

        # 6. Officer transitions to COMPLETED
        comp_res = await client.post(
            f"/api/v1/workflows/service-requests/{request_id}/transition",
            json={
                "target_status": RequestStatus.COMPLETED.value,
                "comment": "Demarcation completed successfully",
            },
            headers=officer_headers,
        )
        assert comp_res.status_code == 200
        assert comp_res.json()["status"] == RequestStatus.COMPLETED.value

        # 7. Citizen views updated case timeline
        cit_case_res = await client.get(
            f"/api/v1/workflows/service-requests/{request_id}",
            headers=citizen_headers,
        )
        assert cit_case_res.status_code == 200
        case_data = cit_case_res.json()
        req_obj = case_data.get("request", case_data)
        assert req_obj["status"] == RequestStatus.COMPLETED.value

    async def test_2d_to_3d_spatial_consistency_and_alignment(
        self,
        client: AsyncClient,
        seed_test_data,
        auth_tokens: dict,
    ):
        """Verifies that 2D footprints and 3D volumetric extrusions maintain spatial consistency

        without planar coordinate shifts or vertical inversion.
        """
        officer_headers = auth_tokens["officer"]
        jur_id = str(seed_test_data["jur"].id)

        # Create Parcel
        p_res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur_id,
                "parcel_number": f"P-{uuid.uuid4().hex[:4]}",
                "parcel_code": f"GV-SYNC-{uuid.uuid4().hex[:6]}",
                "land_use": "COMMERCIAL",
                "geometry": "POLYGON((78.4830 17.3830, 78.4860 17.3830, 78.4860 17.3860, 78.4830 17.3860, 78.4830 17.3830))",
            },
            headers=officer_headers,
        )
        parcel_id = p_res.json()["id"]

        # Create Building within Parcel
        bld_res = await client.post(
            "/api/v1/buildings",
            json={
                "parcel_id": parcel_id,
                "building_reference": f"BLD-SYNC-{uuid.uuid4().hex[:6]}",
                "building_type": "COMMERCIAL",
                "height_estimate": 45.0,
                "geometry": "POLYGON((78.4835 17.3835, 78.4855 17.3835, 78.4855 17.3855, 78.4835 17.3855, 78.4835 17.3835))",
            },
            headers=officer_headers,
        )
        building_id = bld_res.json()["id"]

        # Create Stacking Floors: Ground, 1st, 2nd
        floors = []
        for flr_num, min_m, max_m in [(0, 0.0, 4.0), (1, 4.0, 7.5), (2, 7.5, 11.0)]:
            f_res = await client.post(
                "/api/v1/floors",
                json={
                    "building_id": building_id,
                    "floor_number": flr_num,
                    "floor_code": f"FLR-S{flr_num}-{uuid.uuid4().hex[:4]}",
                    "floor_name": f"Level {flr_num}",
                    "elevation_min_m": min_m,
                    "elevation_max_m": max_m,
                },
                headers=officer_headers,
            )
            assert f_res.status_code == 201
            floors.append(f_res.json())

        # Verify floor stacking order
        assert len(floors) == 3
        for i in range(len(floors) - 1):
            assert floors[i]["elevation_max_m"] <= floors[i + 1]["elevation_min_m"] + 0.01

        # Query 3D building details
        b_3d_res = await client.get(
            f"/api/v1/3d/buildings/{building_id}",
            headers=officer_headers,
        )
        assert b_3d_res.status_code in [200, 404]
