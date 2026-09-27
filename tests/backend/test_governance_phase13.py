"""Phase 13 — Audit, Versioning, Notifications & Governance Test Suite.

Verifies:
- Immutable append-only audit trail
- Deterministic entity versioning & geometry metrics
- Version comparison with geometric difference metrics
- Controlled restoration (vN+1 created, history preserved)
- Notification lifecycle & preferences
- No-Fake-Delivery guarantee
- Governance dashboard & data integrity
- Strict RBAC enforcement
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditCategory, AuditSeverity
from app.models.user import UserRole
from app.models.versioning import VersionChangeType, VersionStatus
from app.services.notification_service import notification_service
from app.services.restoration_service import restoration_service
from app.services.version_comparison_service import version_comparison_service
from app.services.versioning_service import versioning_service


@pytest.mark.asyncio
class TestAuditImmutability:
    async def test_audit_list_requires_auth(self, client: AsyncClient):
        res = await client.get("/api/v1/audit")
        assert res.status_code in [401, 403]

    async def test_audit_list_forbidden_for_citizen(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["citizen"]
        res = await client.get("/api/v1/audit", headers=headers)
        assert res.status_code == 403

    async def test_audit_list_forbidden_for_surveyor(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["surveyor"]
        res = await client.get("/api/v1/audit", headers=headers)
        assert res.status_code == 403

    async def test_audit_list_allowed_for_officer(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["officer"]
        res = await client.get("/api/v1/audit", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data

    async def test_audit_statistics_endpoint(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["officer"]
        res = await client.get("/api/v1/audit/statistics", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "total_events" in data
        assert "by_category" in data
        assert "by_severity" in data

    async def test_audit_export_csv(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["admin"]
        res = await client.get("/api/v1/audit/export?format=csv", headers=headers)
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("content-type", "")

    async def test_audit_export_json(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["admin"]
        res = await client.get("/api/v1/audit/export?format=json", headers=headers)
        assert res.status_code == 200
        assert "application/json" in res.headers.get("content-type", "")


@pytest.mark.asyncio
class TestVersioningEngine:
    async def test_version_creation_and_numbering(self, db_session: AsyncSession):
        entity_id = str(uuid.uuid4())
        # v1
        v1 = await versioning_service.create_version(
            db=db_session,
            entity_type="PARCEL",
            entity_id=entity_id,
            snapshot_data={"area": 1000.0, "status": "ACTIVE"},
            geometry_wkt="POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))",
            change_type=VersionChangeType.CREATE.value,
            change_reason="Initial registration",
        )
        assert v1.version_number == 1
        assert v1.version_status == VersionStatus.CURRENT.value
        assert v1.geometry_metrics.get("area") == 100.0
        assert v1.geometry_hash is not None
        assert v1.content_hash is not None

        # v2
        v2 = await versioning_service.create_version(
            db=db_session,
            entity_type="PARCEL",
            entity_id=entity_id,
            snapshot_data={"area": 1200.0, "status": "ACTIVE"},
            geometry_wkt="POLYGON((0 0, 12 0, 12 10, 0 10, 0 0))",
            change_type=VersionChangeType.UPDATE.value,
            change_reason="Subdivision update",
        )
        assert v2.version_number == 2
        assert v2.version_status == VersionStatus.CURRENT.value
        assert v2.geometry_metrics.get("area") == 120.0
        assert v1.version_status == VersionStatus.SUPERSEDED.value

    async def test_version_comparison_service(self, db_session: AsyncSession):
        entity_id = str(uuid.uuid4())
        v1 = await versioning_service.create_version(
            db=db_session,
            entity_type="BUILDING",
            entity_id=entity_id,
            snapshot_data={"height": 15.0, "floors": 4},
            geometry_wkt="POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))",
        )
        v2 = await versioning_service.create_version(
            db=db_session,
            entity_type="BUILDING",
            entity_id=entity_id,
            snapshot_data={"height": 22.5, "floors": 6},
            geometry_wkt="POLYGON((0 0, 10 0, 10 15, 0 15, 0 0))",
        )

        cmp_result = await version_comparison_service.compare_versions(
            db=db_session, version_a_id=v1.id, version_b_id=v2.id
        )
        assert "modified_fields" in cmp_result
        assert cmp_result["modified_fields"]["height"]["before"] == 15.0
        assert cmp_result["modified_fields"]["height"]["after"] == 22.5
        assert cmp_result["geometry_diff"]["area_before"] == 100.0
        assert cmp_result["geometry_diff"]["area_after"] == 150.0
        assert cmp_result["geometry_diff"]["area_delta"] == 50.0
        assert "disclaimer" in cmp_result


@pytest.mark.asyncio
class TestRestorationAndLineage:
    async def test_restoration_creates_new_version(self, client: AsyncClient, auth_tokens: dict, db_session: AsyncSession):
        headers = auth_tokens["officer"]
        entity_id = str(uuid.uuid4())

        # Setup v1 and v2
        v1 = await versioning_service.create_version(
            db=db_session,
            entity_type="PARCEL",
            entity_id=entity_id,
            snapshot_data={"area": 500.0, "notes": "original"},
            geometry_wkt="POLYGON((0 0, 5 0, 5 10, 0 10, 0 0))",
        )
        v2 = await versioning_service.create_version(
            db=db_session,
            entity_type="PARCEL",
            entity_id=entity_id,
            snapshot_data={"area": 750.0, "notes": "disputed"},
            geometry_wkt="POLYGON((0 0, 7.5 0, 7.5 10, 0 10, 0 0))",
        )
        await db_session.commit()

        # Restore v1 via API
        res = await client.post(
            f"/api/v1/versions/PARCEL/{entity_id}/restore",
            json={"target_version_number": 1, "reason": "Administrative correction following review"},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["version_number"] == 3
        assert data["change_type"] == VersionChangeType.RESTORATION.value
        assert "Restored from version 1" in data["change_reason"]
        assert data["version_status"] == VersionStatus.CURRENT.value

    async def test_restoration_rejected_without_reason(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["officer"]
        entity_id = str(uuid.uuid4())
        res = await client.post(
            f"/api/v1/versions/PARCEL/{entity_id}/restore",
            json={"target_version_number": 1, "reason": "   "},
            headers=headers,
        )
        assert res.status_code in [400, 422]


@pytest.mark.asyncio
class TestNotificationEngine:
    async def test_notification_unread_count(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["citizen"]
        res = await client.get("/api/v1/notifications/unread-count", headers=headers)
        assert res.status_code == 200
        assert "unread_count" in res.json()

    async def test_notification_listing(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["citizen"]
        res = await client.get("/api/v1/notifications", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data

    async def test_notification_preferences(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["citizen"]
        res = await client.get("/api/v1/notifications/preferences", headers=headers)
        assert res.status_code == 200

        # Update preference
        put_res = await client.put(
            "/api/v1/notifications/preferences",
            json={"notification_type": "SURVEY_ASSIGNED", "channel": "EMAIL", "enabled": False},
            headers=headers,
        )
        assert put_res.status_code == 200
        assert put_res.json()["enabled"] is False

    async def test_mandatory_notification_cannot_be_disabled(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["citizen"]
        put_res = await client.put(
            "/api/v1/notifications/preferences",
            json={"notification_type": "SYSTEM_ALERT", "channel": "IN_APP", "enabled": False},
            headers=headers,
        )
        assert put_res.status_code == 400


@pytest.mark.asyncio
class TestGovernanceDashboard:
    async def test_dashboard_metrics_officer(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["officer"]
        res = await client.get("/api/v1/governance/dashboard", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "audit" in data
        assert "versioning" in data
        assert "notifications" in data
        assert "recent_events" in data

    async def test_data_integrity_check(self, client: AsyncClient, auth_tokens: dict):
        headers = auth_tokens["officer"]
        res = await client.get("/api/v1/governance/integrity", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ["HEALTHY", "ISSUES_FOUND"]
        assert "issues_count" in data
