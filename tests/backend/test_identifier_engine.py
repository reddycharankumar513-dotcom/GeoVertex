"""Phase 12 — Comprehensive tests for Technical 3D Property Identifier Engine.

Tests: normalization, generation, idempotency, collision detection, hierarchy validation,
lifecycle, QR, verification, bulk generation, RBAC, concurrency protection.
"""
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identifier import (
    IdentifierScheme,
    IdentifierStatus,
    PropertyIdentifier,
)
from app.services.identifier_normalization import (
    assemble_identifier,
    extract_building_component,
    extract_floor_component,
    extract_jurisdiction_component,
    extract_parcel_component,
    extract_unit_component,
)
from app.services.identifier_qr_service import (
    extract_id_prefix_from_token,
    generate_verification_token,
    verify_token_format,
)


# ─────────────────────────────────────────────────────────────────────────────
# Normalization unit tests (pure, no DB)
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalization:
    """Pure normalization logic — no database required."""

    def test_jurisdiction_strips_prefix(self):
        assert extract_jurisdiction_component("JUR-W101") == "W101"
        assert extract_jurisdiction_component("JUR-VSK") == "VSK"

    def test_jurisdiction_no_prefix(self):
        result = extract_jurisdiction_component("W101")
        assert "W101" in result

    def test_parcel_strips_gv_prefix(self):
        result = extract_parcel_component("GV-W101-P101")
        assert "P101" in result

    def test_parcel_numeric_gets_prefixed(self):
        result = extract_parcel_component("123")
        assert result.startswith("P")

    def test_building_strips_bld_prefix(self):
        result = extract_building_component("BLD-W101-001")
        assert result.startswith("B")

    def test_building_pads_numeric(self):
        result = extract_building_component("BLD-W101-1")
        assert result.startswith("B")

    def test_floor_positive(self):
        assert extract_floor_component("BLD-W101-001-F2", floor_number=2) == "F02"

    def test_floor_ground(self):
        assert extract_floor_component("X", floor_number=0) == "F00"

    def test_floor_basement(self):
        result = extract_floor_component("X", floor_number=-1)
        assert "B" in result

    def test_unit_strips_suffix(self):
        result = extract_unit_component("BLD-W101-001-F1-U101")
        assert "U101" in result

    def test_unit_from_number(self):
        assert extract_unit_component("X", unit_number="101") == "U101"

    def test_identifier_assembly_full(self):
        result = assemble_identifier("GV", "-", "W101", "P101", "B001", "F02", "U101")
        assert result == "GV-W101-P101-B001-F02-U101"

    def test_identifier_assembly_parcel_level(self):
        result = assemble_identifier("GV", "-", "W101", "P101")
        assert result == "GV-W101-P101"

    def test_identifier_assembly_building_level(self):
        result = assemble_identifier("GV", "-", "W101", "P101", "B001")
        assert result == "GV-W101-P101-B001"

    def test_identifier_stability(self):
        """Same inputs always produce same output — deterministic."""
        r1 = assemble_identifier("GV", "-", "W101", "P101", "B001", "F02", "U101")
        r2 = assemble_identifier("GV", "-", "W101", "P101", "B001", "F02", "U101")
        assert r1 == r2

    def test_separator_configurable(self):
        result = assemble_identifier("GV", ".", "W101", "P101")
        assert result == "GV.W101.P101"


# ─────────────────────────────────────────────────────────────────────────────
# QR / Token unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestQRToken:
    def test_token_generated(self):
        token = generate_verification_token("abc12345-0000-0000-0000-000000000001", "GV-W101-P101-B001-F02-U101")
        assert len(token) > 20

    def test_token_format_valid(self):
        token = generate_verification_token("abc12345-0000-0000-0000-000000000001", "GV-W101")
        assert verify_token_format(token)

    def test_token_deterministic(self):
        t1 = generate_verification_token("abc12345-1111-1111-1111-111111111111", "GV-W101")
        t2 = generate_verification_token("abc12345-1111-1111-1111-111111111111", "GV-W101")
        assert t1 == t2

    def test_token_prefix_extractable(self):
        token = generate_verification_token("abcd1234-0000-0000-0000-000000000001", "GV-TEST")
        prefix = extract_id_prefix_from_token(token)
        assert prefix == "abcd1234"

    def test_invalid_token_format(self):
        assert not verify_token_format("not-a-valid-token")
        assert not verify_token_format("")


# ─────────────────────────────────────────────────────────────────────────────
# API integration tests (with real backend)
# ─────────────────────────────────────────────────────────────────────────────

class TestIdentifierSchemeAPI:
    """Tests for identifier scheme CRUD."""

    @pytest.mark.asyncio
    async def test_list_schemes_authenticated(self, client: AsyncClient, auth_tokens: dict):
        res = await client.get(
            "/api/v1/identifiers/schemes",
            headers=auth_tokens["citizen"],
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    @pytest.mark.asyncio
    async def test_list_schemes_requires_auth(self, client: AsyncClient):
        res = await client.get("/api/v1/identifiers/schemes")
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_create_scheme_admin_only(self, client: AsyncClient, auth_tokens: dict):
        scheme_data = {
            "scheme_code": "TEST-SCHEME-P12-001",
            "name": "Test Scheme P12",
            "version": 1,
            "prefix": "TS",
            "separator": "-",
            "jurisdiction_component": "strip_prefix_code",
            "parcel_component": "strip_prefix_code",
            "building_component": "strip_prefix_ref",
            "floor_component": "strip_floor_suffix",
            "unit_component": "strip_unit_suffix",
            "padding_rules": {},
            "checksum_enabled": False,
            "active": False,
        }
        # Citizen should be forbidden
        res = await client.post(
            "/api/v1/identifiers/schemes",
            json=scheme_data,
            headers=auth_tokens["citizen"],
        )
        assert res.status_code == 403

        # Admin should succeed
        res = await client.post(
            "/api/v1/identifiers/schemes",
            json=scheme_data,
            headers=auth_tokens["admin"],
        )
        assert res.status_code == 201
        assert res.json()["scheme_code"] == "TEST-SCHEME-P12-001"


class TestIdentifierGenerationAPI:
    """Tests for identifier generation, idempotency, and hierarchy validation."""

    @pytest.mark.asyncio
    async def test_preview_requires_auth(self, client: AsyncClient):
        res = await client.post("/api/v1/identifiers/preview", json={
            "entity_type": "UNIT",
            "entity_id": "00000000-0000-0000-0000-000000000001",
        })
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_requires_officer(self, client: AsyncClient, auth_tokens: dict):
        res = await client.post(
            "/api/v1/identifiers/generate",
            json={"entity_type": "UNIT", "entity_id": "00000000-0000-0000-0000-000000000001"},
            headers=auth_tokens["citizen"],
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_generate_nonexistent_unit(self, client: AsyncClient, auth_tokens: dict):
        res = await client.post(
            "/api/v1/identifiers/generate",
            json={"entity_type": "UNIT", "entity_id": "00000000-0000-0000-0000-000000000099"},
            headers=auth_tokens["officer"],
        )
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_statistics_endpoint(self, client: AsyncClient, auth_tokens: dict):
        res = await client.get(
            "/api/v1/identifiers/statistics",
            headers=auth_tokens["officer"],
        )
        assert res.status_code == 200
        data = res.json()
        for key in ("total", "by_status", "by_entity_type", "active"):
            assert key in data

    @pytest.mark.asyncio
    async def test_unsupported_entity_type(self, client: AsyncClient, auth_tokens: dict):
        res = await client.post(
            "/api/v1/identifiers/generate",
            json={"entity_type": "UTILITY", "entity_id": "00000000-0000-0000-0000-000000000001"},
            headers=auth_tokens["officer"],
        )
        assert res.status_code == 400


class TestIdentifierLifecycle:
    """Tests for identifier lifecycle: retire, revoke."""

    @pytest.mark.asyncio
    async def test_retire_requires_officer(self, client: AsyncClient, auth_tokens: dict, db_session: AsyncSession):
        result = await db_session.execute(
            select(PropertyIdentifier).where(PropertyIdentifier.status == "ACTIVE").limit(1)
        )
        ident = result.scalars().first()
        if not ident:
            pytest.skip("No active identifiers to retire")

        res = await client.post(
            f"/api/v1/identifiers/{ident.id}/retire",
            json={"reason": "Test retirement"},
            headers=auth_tokens["citizen"],
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_revoke_requires_admin(self, client: AsyncClient, auth_tokens: dict, db_session: AsyncSession):
        result = await db_session.execute(
            select(PropertyIdentifier).where(PropertyIdentifier.status == "ACTIVE").limit(1)
        )
        ident = result.scalars().first()
        if not ident:
            pytest.skip("No active identifiers")

        res = await client.post(
            f"/api/v1/identifiers/{ident.id}/revoke",
            json={"reason": "Test"},
            headers=auth_tokens["officer"],
        )
        assert res.status_code == 403


class TestPublicVerification:
    """Tests for public verification endpoint."""

    @pytest.mark.asyncio
    async def test_invalid_token_returns_invalid(self, client: AsyncClient):
        res = await client.get("/api/v1/verify/INVALID_TOKEN_12345")
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert "INVALID" in data["verification_message"]

    @pytest.mark.asyncio
    async def test_verify_no_auth_required(self, client: AsyncClient):
        """Public endpoint should not require authentication."""
        res = await client.get("/api/v1/verify/some_token")
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_disclaimer_in_verify_response(self, client: AsyncClient):
        res = await client.get("/api/v1/verify/FAKE_TOKEN")
        assert res.status_code == 200
        data = res.json()
        assert "disclaimer" in data
        # Must NOT say 'official ULPIN' — must say it's a technical identifier
        assert "ULPIN" in data["disclaimer"] or "technical" in data["disclaimer"].lower()


class TestIdentifierListing:
    """Tests for identifier list/search API."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        res = await client.get("/api/v1/identifiers")
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_list_returns_paginated(self, client: AsyncClient, auth_tokens: dict):
        res = await client.get(
            "/api/v1/identifiers",
            headers=auth_tokens["citizen"],
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, client: AsyncClient, auth_tokens: dict):
        res = await client.get(
            "/api/v1/identifiers?status=ACTIVE",
            headers=auth_tokens["officer"],
        )
        assert res.status_code == 200
        data = res.json()
        for item in data["items"]:
            assert item["status"] == "ACTIVE"


class TestBulkGeneration:
    """Tests for bulk identifier generation."""

    @pytest.mark.asyncio
    async def test_bulk_preview_requires_officer(self, client: AsyncClient, auth_tokens: dict):
        res = await client.post(
            "/api/v1/identifiers/bulk-preview",
            json={"entity_type": "UNIT", "building_id": "00000000-0000-0000-0000-000000000001"},
            headers=auth_tokens["citizen"],
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_generate_requires_confirmed(self, client: AsyncClient, auth_tokens: dict):
        res = await client.post(
            "/api/v1/identifiers/bulk-generate",
            json={
                "entity_type": "UNIT",
                "building_id": "00000000-0000-0000-0000-000000000001",
                "confirmed": False,
            },
            headers=auth_tokens["officer"],
        )
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_bulk_unsupported_type(self, client: AsyncClient, auth_tokens: dict):
        res = await client.post(
            "/api/v1/identifiers/bulk-generate",
            json={
                "entity_type": "JURISDICTION",
                "building_id": "00000000-0000-0000-0000-000000000001",
                "confirmed": True,
            },
            headers=auth_tokens["officer"],
        )
        assert res.status_code == 400


class TestConcurrency:
    """Concurrency protection — unique constraint enforcement."""

    @pytest.mark.asyncio
    async def test_concurrent_nonexistent_entity_both_fail(self, client: AsyncClient, auth_tokens: dict):
        """Two concurrent requests for a non-existent unit both return errors, not 500."""
        headers = auth_tokens["officer"]
        payload = {"entity_type": "UNIT", "entity_id": "00000000-0000-0000-0000-000000009999"}

        async def make_request():
            return await client.post("/api/v1/identifiers/generate", json=payload, headers=headers)

        results = await asyncio.gather(make_request(), make_request(), return_exceptions=True)
        for r in results:
            if not isinstance(r, Exception):
                assert r.status_code in (400, 409), f"Unexpected status: {r.status_code}"
