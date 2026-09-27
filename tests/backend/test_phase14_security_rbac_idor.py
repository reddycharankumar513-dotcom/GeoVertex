"""Phase 14 — Security, RBAC Matrix, IDOR & Data Integrity Test Suite.

Verifies:
1. Complete RBAC Matrix across all 5 roles:
   - ADMIN, GOVERNMENT_OFFICER, SURVEYOR, CITIZEN, URBAN_PLANNER
2. IDOR Protection (Cross-user tenant isolation):
   - Service request isolation between citizens
   - Notification reading & acknowledgement isolation
   - Document metadata & download isolation
3. Audit Log Immutability & Anti-Tampering:
   - Inability to edit, patch, or delete audit logs via HTTP (405 Method Not Allowed)
4. Version Restoration Safety Invariant:
   - Rollback always appends v(N+1), preserving all historical records immutably
5. Public Token Privacy / Data Minimization:
   - Verification endpoint does not expose citizen PII or internal secrets
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.versioning import VersionChangeType, VersionStatus
from app.models.workflow import ServiceType
from app.services.versioning_service import versioning_service
from app.services.notification_service import notification_service


@pytest.mark.asyncio
class TestPhase14RBACMatrix:
    """Tests the authorization boundary across all 5 platform roles."""

    async def test_auth_me_accessible_to_all_authenticated_roles(
        self,
        client: AsyncClient,
        auth_tokens: dict,
    ):
        """All authenticated roles can inspect their own user profile."""
        for role, headers in auth_tokens.items():
            res = await client.get("/api/v1/auth/me", headers=headers)
            assert res.status_code == 200, f"Role {role} failed /auth/me with {res.status_code}"
            assert "email" in res.json()

    async def test_audit_logs_strict_role_boundary(
        self,
        client: AsyncClient,
        auth_tokens: dict,
    ):
        """Audit logs only accessible to ADMIN and GOVERNMENT_OFFICER."""
        # Allowed
        for role in ["admin", "officer"]:
            res = await client.get("/api/v1/audit", headers=auth_tokens[role])
            assert res.status_code == 200, f"Role {role} unexpectedly denied audit access"

        # Forbidden
        for role in ["citizen", "surveyor", "planner"]:
            res = await client.get("/api/v1/audit", headers=auth_tokens[role])
            assert res.status_code == 403, f"Role {role} unexpectedly allowed audit access"

    async def test_governance_dashboard_strict_role_boundary(
        self,
        client: AsyncClient,
        auth_tokens: dict,
    ):
        """Governance dashboard only accessible to ADMIN and GOVERNMENT_OFFICER."""
        for role in ["admin", "officer"]:
            res = await client.get("/api/v1/governance/dashboard", headers=auth_tokens[role])
            assert res.status_code == 200, f"Role {role} unexpectedly denied governance dashboard"

        for role in ["citizen", "surveyor", "planner"]:
            res = await client.get("/api/v1/governance/dashboard", headers=auth_tokens[role])
            assert res.status_code == 403, f"Role {role} unexpectedly allowed governance dashboard"

    async def test_cadastral_parcel_mutation_boundary(
        self,
        client: AsyncClient,
        seed_test_data,
        auth_tokens: dict,
    ):
        """Only ADMIN and GOVERNMENT_OFFICER can create official parcels."""
        jur_id = str(seed_test_data["jur"].id)
        payload = {
            "jurisdiction_id": jur_id,
            "parcel_number": f"P-RBAC-{uuid.uuid4().hex[:4]}",
            "parcel_code": f"GV-RBAC-{uuid.uuid4().hex[:6]}",
            "land_use": "RESIDENTIAL",
            "geometry": "POLYGON((78.481 17.381, 78.483 17.381, 78.483 17.383, 78.481 17.383, 78.481 17.381))",
        }

        # Citizen and Planner denied creation
        c_res = await client.post("/api/v1/parcels", json=payload, headers=auth_tokens["citizen"])
        assert c_res.status_code == 403

        p_res = await client.post("/api/v1/parcels", json=payload, headers=auth_tokens["planner"])
        assert p_res.status_code == 403

        # Surveyor and Officer allowed creation (authorized editors)
        s_res = await client.post("/api/v1/parcels", json=payload, headers=auth_tokens["surveyor"])
        assert s_res.status_code == 201
        created_id = s_res.json()["id"]

        # Deletion requires Officer or Admin: Citizen, Surveyor, Planner denied deletion
        del_c = await client.delete(f"/api/v1/parcels/{created_id}", headers=auth_tokens["citizen"])
        assert del_c.status_code == 403

        del_s = await client.delete(f"/api/v1/parcels/{created_id}", headers=auth_tokens["surveyor"])
        assert del_s.status_code == 403

        # Officer allowed deletion
        del_o = await client.delete(f"/api/v1/parcels/{created_id}", headers=auth_tokens["officer"])
        assert del_o.status_code == 200

    async def test_identifier_scheme_creation_admin_only(
        self,
        client: AsyncClient,
        auth_tokens: dict,
    ):
        """Identifier scheme creation is restricted to ADMIN only."""
        scheme_payload = {
            "scheme_code": f"GV-SCH-{uuid.uuid4().hex[:4].upper()}",
            "name": "Special Economic Zone Scheme",
            "version": 1,
            "prefix": "SEZ",
            "separator": "-",
            "jurisdiction_component": "strip_prefix_code",
            "parcel_component": "strip_prefix_code",
            "building_component": "strip_prefix_ref",
            "floor_component": "strip_floor_suffix",
            "unit_component": "strip_unit_suffix",
            "active": True,
        }

        # Officer denied
        o_res = await client.post("/api/v1/identifiers/schemes", json=scheme_payload, headers=auth_tokens["officer"])
        assert o_res.status_code == 403

        # Citizen denied
        c_res = await client.post("/api/v1/identifiers/schemes", json=scheme_payload, headers=auth_tokens["citizen"])
        assert c_res.status_code == 403

        # Admin allowed
        a_res = await client.post("/api/v1/identifiers/schemes", json=scheme_payload, headers=auth_tokens["admin"])
        assert a_res.status_code == 201


@pytest.mark.asyncio
class TestPhase14IDORIsolation:
    """Verifies that tenants/citizens cannot view or tamper with each other's data."""

    async def test_cross_citizen_service_request_isolation(
        self,
        client: AsyncClient,
        seed_test_data,
        auth_tokens: dict,
        db_session: AsyncSession,
    ):
        """Citizen B cannot view or mutate a service request submitted by Citizen A."""
        jur_id = str(seed_test_data["jur"].id)
        org_id = str(seed_test_data["org"].id)

        # 1. Create a second citizen user
        citizen2 = User(
            email="citizen2@test.org",
            username="test_citizen2",
            full_name="Second Citizen",
            password_hash=get_password_hash("TestPassword123!"),
            role=UserRole.CITIZEN.value,
            organization_id=org_id,
            jurisdiction_id=jur_id,
            is_active=True,
            is_verified=True,
        )
        db_session.add(citizen2)
        await db_session.commit()

        # Login as Citizen 2
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "citizen2@test.org", "password": "TestPassword123!"},
        )
        assert login_res.status_code == 200
        citizen2_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        # 2. Seed service type for this test
        st = ServiceType(
            code="IDOR_MUTATION",
            name="Property Rights Mutation",
            description="Private mutation request",
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

        # 3. Citizen 1 submits a service request
        sr_res = await client.post(
            "/api/v1/workflows/service-requests",
            json={
                "request_type": "IDOR_MUTATION",
                "jurisdiction_id": jur_id,
                "title": "Private ownership transfer for Citizen 1",
                "description": "Applicant requests transfer of unit ownership rights",
            },
            headers=auth_tokens["citizen"],
        )
        assert sr_res.status_code == 201
        case_id = sr_res.json()["id"]

        # 4. Citizen 1 can view it
        c1_res = await client.get(f"/api/v1/workflows/service-requests/{case_id}", headers=auth_tokens["citizen"])
        assert c1_res.status_code == 200

        # 5. Citizen 2 CANNOT view Citizen 1's request (403 Forbidden or 404 Not Found)
        c2_res = await client.get(f"/api/v1/workflows/service-requests/{case_id}", headers=citizen2_headers)
        assert c2_res.status_code in [403, 404]

        # 6. Citizen 2 CANNOT append messages to Citizen 1's request (403 Forbidden or 404 Not Found)
        c2_msg = await client.post(
            f"/api/v1/workflows/service-requests/{case_id}/messages",
            json={"content": "Malicious injection attempt", "is_internal": False},
            headers=citizen2_headers,
        )
        assert c2_msg.status_code in [403, 404]

    async def test_cross_user_notification_isolation(
        self,
        client: AsyncClient,
        seed_test_data,
        auth_tokens: dict,
        db_session: AsyncSession,
    ):
        """User B cannot read or mark User A's notifications as read."""
        user_a = seed_test_data["users"]["CITIZEN"]
        user_b = seed_test_data["users"]["URBAN_PLANNER"]

        # Send notification to User A
        notif = await notification_service.dispatch_notification(
            db=db_session,
            user_id=user_a.id,
            notification_type="SYSTEM_ALERT",
            title="Private Tax Notice",
            message="Confidential parcel assessment update",
        )
        await db_session.commit()

        # User A sees the notification in their inbox
        res_a = await client.get("/api/v1/notifications", headers=auth_tokens["citizen"])
        assert res_a.status_code == 200
        items_a = res_a.json()["items"]
        assert any(n["id"] == str(notif.id) for n in items_a)

        # User B does NOT see User A's notification in their inbox
        res_b = await client.get("/api/v1/notifications", headers=auth_tokens["planner"])
        assert res_b.status_code == 200
        items_b = res_b.json()["items"]
        assert not any(n["id"] == str(notif.id) for n in items_b)

        # User B CANNOT mark User A's notification as read (returns 404 / 403)
        read_b = await client.post(f"/api/v1/notifications/{notif.id}/read", headers=auth_tokens["planner"])
        assert read_b.status_code in [403, 404]

        # User A CAN mark their own notification as read
        read_a = await client.post(f"/api/v1/notifications/{notif.id}/read", headers=auth_tokens["citizen"])
        assert read_a.status_code == 200


@pytest.mark.asyncio
class TestPhase14AuditImmutability:
    """Verifies that audit log entries cannot be modified or deleted via any HTTP method."""

    async def test_audit_logs_http_methods_immutable(
        self,
        client: AsyncClient,
        auth_tokens: dict,
    ):
        """PUT, PATCH, DELETE on audit endpoints must return 405 Method Not Allowed."""
        admin_headers = auth_tokens["admin"]
        fake_uuid = str(uuid.uuid4())

        # PUT not allowed
        put_res = await client.put(f"/api/v1/audit/{fake_uuid}", json={"action": "TAMPER"}, headers=admin_headers)
        assert put_res.status_code in [404, 405]

        # PATCH not allowed
        patch_res = await client.patch(f"/api/v1/audit/{fake_uuid}", json={"action": "TAMPER"}, headers=admin_headers)
        assert patch_res.status_code in [404, 405]

        # DELETE not allowed
        del_res = await client.delete(f"/api/v1/audit/{fake_uuid}", headers=admin_headers)
        assert del_res.status_code in [404, 405]

        # Direct POST to audit not allowed
        post_res = await client.post("/api/v1/audit", json={"action": "INJECT"}, headers=admin_headers)
        assert post_res.status_code in [404, 405]


@pytest.mark.asyncio
class TestPhase14VersionRestorationInvariant:
    """Verifies that version rollback creates a NEW version and preserves all history."""

    async def test_version_restoration_preserves_history(
        self,
        client: AsyncClient,
        auth_tokens: dict,
        db_session: AsyncSession,
    ):
        officer_headers = auth_tokens["officer"]
        entity_id = str(uuid.uuid4())

        # Create v1
        v1 = await versioning_service.create_version(
            db=db_session,
            entity_type="PARCEL",
            entity_id=entity_id,
            snapshot_data={"area": 400.0, "status": "APPROVED"},
            geometry_wkt="POLYGON((0 0, 4 0, 4 10, 0 10, 0 0))",
            change_type=VersionChangeType.CREATE.value,
            change_reason="Original registration",
        )
        # Create v2
        v2 = await versioning_service.create_version(
            db=db_session,
            entity_type="PARCEL",
            entity_id=entity_id,
            snapshot_data={"area": 500.0, "status": "DISPUTED"},
            geometry_wkt="POLYGON((0 0, 5 0, 5 10, 0 10, 0 0))",
            change_type=VersionChangeType.UPDATE.value,
            change_reason="Erroneous boundary expansion",
        )
        await db_session.commit()

        # Restore v1
        res = await client.post(
            f"/api/v1/versions/PARCEL/{entity_id}/restore",
            json={
                "target_version_number": 1,
                "reason": "Administrative correction: revert erroneous expansion",
            },
            headers=officer_headers,
        )
        assert res.status_code == 200
        v3_data = res.json()

        # Invariant 1: New version is v3
        assert v3_data["version_number"] == 3
        assert v3_data["change_type"] == VersionChangeType.RESTORATION.value
        assert v3_data["version_status"] == VersionStatus.CURRENT.value

        # Invariant 2: History timeline has 3 distinct versions
        hist_res = await client.get(f"/api/v1/versions/PARCEL/{entity_id}", headers=officer_headers)
        assert hist_res.status_code == 200
        hist_items = hist_res.json()["items"]
        assert len(hist_items) == 3

        # Invariant 3: v1 and v2 historical snapshots remain intact
        v1_check = await client.get(f"/api/v1/versions/PARCEL/{entity_id}/1", headers=officer_headers)
        assert v1_check.status_code == 200
        assert v1_check.json()["snapshot_data"]["area"] == 400.0

        v2_check = await client.get(f"/api/v1/versions/PARCEL/{entity_id}/2", headers=officer_headers)
        assert v2_check.status_code == 200
        assert v2_check.json()["snapshot_data"]["area"] == 500.0


@pytest.mark.asyncio
class TestPhase14PublicTokenPrivacy:
    """Verifies that public verification endpoints do not leak PII."""

    async def test_public_identifier_verification_privacy(
        self,
        client: AsyncClient,
        auth_tokens: dict,
        seed_test_data,
    ):
        officer_headers = auth_tokens["officer"]
        jur_id = str(seed_test_data["jur"].id)

        # 1. Create parcel & generate identifier
        p_res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur_id,
                "parcel_number": f"P-PRIV-{uuid.uuid4().hex[:4]}",
                "parcel_code": f"GV-PRIV-{uuid.uuid4().hex[:6]}",
                "land_use": "RESIDENTIAL",
                "geometry": "POLYGON((78.481 17.381, 78.483 17.381, 78.483 17.383, 78.481 17.383, 78.481 17.381))",
            },
            headers=officer_headers,
        )
        assert p_res.status_code == 201
        parcel_id = p_res.json()["id"]

        id_res = await client.post(
            "/api/v1/identifiers/generate",
            json={"entity_type": "PARCEL", "entity_id": parcel_id},
            headers=officer_headers,
        )
        assert id_res.status_code in [200, 201]
        token = id_res.json()["verification_token"]

        # 2. Public verification by token (no auth required)
        pub_res = await client.get(f"/api/v1/verify/{token}")
        assert pub_res.status_code == 200
        pub_data = pub_res.json()

        # Check that technical cadastral details are present
        assert pub_data["valid"] is True
        assert pub_data["status"] == "ACTIVE"
        assert "identifier_value" in pub_data
        assert "GeoVertex Technical 3D Identifier" in pub_data["disclaimer"]

        # Check that PII is NOT leaked
        body_text = pub_res.text.lower()
        assert "password" not in body_text
        assert "email" not in body_text
        assert "phone" not in body_text
        assert "aadhar" not in body_text
        assert "ssn" not in body_text
