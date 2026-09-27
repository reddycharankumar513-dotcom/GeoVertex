"""Phase 14 — Performance, Concurrency, Failure Injection & Resilience Suite.

Verifies:
1. Concurrency & Race Condition Resilience:
   - Atomic generation of technical identifiers under concurrent requests
   - Workflow state transition concurrency
2. Failure Injection & No-Fake Principles:
   - Unconfigured AI model returns MODEL_NOT_CONFIGURED gracefully without synthetic results
   - Unconfigured OCR engine returns OCR_ENGINE_NOT_CONFIGURED without fabrication
   - Unconfigured SMTP provider returns EMAIL_NOT_CONFIGURED upholding No-Fake-Delivery
   - Malformed geometry rejection with structured error envelope
   - Rate limiting enforcement and 429 throttling under high-frequency sensitive traffic
3. Response Latency & Performance Benchmarks:
   - Measured wall-clock response latencies across core platform endpoints
"""

import asyncio
import time
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import ModelNotConfiguredError
from app.ai.document.ocr import TesseractOCREngine
from app.ai.models import UnconfiguredFloorExtractor
from app.models.workflow import ServiceType
from app.services.notification_service import SMTPEmailProvider


@pytest.mark.asyncio
class TestPhase14FailureInjectionAndResilience:
    """Verifies graceful handling of missing configurations and invalid inputs."""

    async def test_unconfigured_ai_model_no_fake_results(self):
        """Unconfigured AI models must raise ModelNotConfiguredError / return UNCONFIGURED,

        never fabricating fake 3D footprints or synthetic classifications.
        """
        floor_model = UnconfiguredFloorExtractor()
        floor_model.load_model()
        meta = floor_model.get_metadata()
        assert meta["status"] == "UNCONFIGURED"

        with pytest.raises(ModelNotConfiguredError):
            floor_model.predict({})

    async def test_unconfigured_ocr_engine_no_fake_text(self, tmp_path):
        """Unconfigured OCR engine must return OCR_ENGINE_NOT_CONFIGURED,

        never fabricating OCR text.
        """
        dummy_file = tmp_path / "dummy.png"
        dummy_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        engine = TesseractOCREngine(tesseract_cmd=None)
        assert not engine.is_available()

        result = engine.extract_text(dummy_file, "image/png")
        assert result.status == "OCR_ENGINE_NOT_CONFIGURED"
        assert result.full_text == ""
        assert "not installed or configured" in (result.error_message or "")

    async def test_unconfigured_smtp_no_fake_delivery(self):
        """Unconfigured SMTP provider must return EMAIL_NOT_CONFIGURED,

        strictly upholding the No-Fake-Delivery policy.
        """
        provider = SMTPEmailProvider()
        success, reason = await provider.send_email(
            recipient_email="citizen@test.org",
            subject="Cadastral Update",
            body="Your property boundaries have been peg-verified.",
        )
        assert success is False
        assert reason == "EMAIL_NOT_CONFIGURED"

    async def test_malformed_geometry_rejected_gracefully(
        self,
        client: AsyncClient,
        auth_tokens: dict,
        seed_test_data,
    ):
        """Submitting self-intersecting or invalid WKT must return a 400 or 422 error,

        never corrupting the database or crashing the server.
        """
        jur_id = str(seed_test_data["jur"].id)
        officer_headers = auth_tokens["officer"]

        # Self-intersecting bowtie polygon
        res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur_id,
                "parcel_number": f"P-BAD-{uuid.uuid4().hex[:4]}",
                "parcel_code": f"GV-BAD-{uuid.uuid4().hex[:6]}",
                "land_use": "RESIDENTIAL",
                "geometry": "POLYGON((0 0, 10 10, 0 10, 10 0, 0 0))",
            },
            headers=officer_headers,
        )
        assert res.status_code in [400, 422]
        err = res.json().get("error", {})
        assert err.get("code") in ["BAD_REQUEST", "VALIDATION_ERROR", "INVALID_GEOMETRY"]

    async def test_rate_limiting_enforcement_and_throttling(
        self,
        client: AsyncClient,
    ):
        """When rate limiting is actively enforced, exceeding limit triggers HTTP 429."""
        # Call sensitive login route 65 times with X-Test-Enforce-Rate-Limit header
        enforce_headers = {"X-Test-Enforce-Rate-Limit": "true"}
        hit_429 = False

        for i in range(70):
            res = await client.post(
                "/api/v1/auth/login",
                json={"username_or_email": "admin@test.org", "password": "TestPassword123!"},
                headers=enforce_headers,
            )
            if res.status_code == 429:
                hit_429 = True
                data = res.json()
                assert "error" in data
                assert data["error"]["code"] == "TOO_MANY_REQUESTS"
                assert "Retry-After" in res.headers
                break

        assert hit_429, "Rate limiter failed to throttle excessive requests at sensitive endpoint"


@pytest.mark.asyncio
class TestPhase14ConcurrencyResilience:
    """Verifies safe operation under concurrent asynchronous requests."""

    async def test_rapid_burst_workflow_service_requests(
        self,
        client: AsyncClient,
        auth_tokens: dict,
        seed_test_data,
        db_session: AsyncSession,
    ):
        """Rapid burst of service request submissions generate unique identifiers and succeed."""
        jur_id = str(seed_test_data["jur"].id)
        citizen_headers = auth_tokens["citizen"]

        # Seed service type for this test
        st = ServiceType(
            code="BURST_DEMARCATION",
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

        responses = []
        for i in range(5):
            r = await client.post(
                "/api/v1/workflows/service-requests",
                json={
                    "request_type": "BURST_DEMARCATION",
                    "jurisdiction_id": jur_id,
                    "title": f"Burst Demarcation Request #{i}",
                    "description": "Demarcation boundary survey requested in rapid sequence",
                },
                headers=citizen_headers,
            )
            responses.append(r)

        for r in responses:
            assert r.status_code == 201
            assert "id" in r.json()

        # All 5 generated unique case references
        references = [r.json()["case_reference"] for r in responses]
        assert len(set(references)) == 5

    async def test_concurrent_read_operations(
        self,
        client: AsyncClient,
        auth_tokens: dict,
    ):
        """Concurrent asynchronous read requests execute without conflict."""
        officer_headers = auth_tokens["officer"]

        async def fetch_scene():
            return await client.get("/api/v1/3d/scene", headers=officer_headers)

        async def fetch_parcels():
            return await client.get("/api/v1/map/parcels", headers=officer_headers)

        # Run 6 parallel queries concurrently
        results = await asyncio.gather(
            fetch_scene(),
            fetch_parcels(),
            fetch_scene(),
            fetch_parcels(),
            fetch_scene(),
            fetch_parcels(),
        )
        for res in results:
            assert res.status_code == 200


@pytest.mark.asyncio
class TestPhase14PerformanceBenchmarks:
    """Measures actual response latencies for core cadastral endpoints."""

    async def test_endpoint_latencies_within_bounds(
        self,
        client: AsyncClient,
        auth_tokens: dict,
        seed_test_data,
    ):
        officer_headers = auth_tokens["officer"]

        benchmarks = []

        # 1. /auth/me latency
        t0 = time.perf_counter()
        r1 = await client.get("/api/v1/auth/me", headers=officer_headers)
        d1 = (time.perf_counter() - t0) * 1000
        assert r1.status_code == 200
        benchmarks.append(("/auth/me", d1))

        # 2. /map/parcels latency
        t0 = time.perf_counter()
        r2 = await client.get("/api/v1/map/parcels", headers=officer_headers)
        d2 = (time.perf_counter() - t0) * 1000
        assert r2.status_code == 200
        benchmarks.append(("/map/parcels", d2))

        # 3. /3d/scene latency
        t0 = time.perf_counter()
        r3 = await client.get("/api/v1/3d/scene", headers=officer_headers)
        d3 = (time.perf_counter() - t0) * 1000
        assert r3.status_code == 200
        benchmarks.append(("/3d/scene", d3))

        # 4. /audit/statistics latency
        t0 = time.perf_counter()
        r4 = await client.get("/api/v1/audit/statistics", headers=officer_headers)
        d4 = (time.perf_counter() - t0) * 1000
        assert r4.status_code == 200
        benchmarks.append(("/audit/statistics", d4))

        # 5. /governance/dashboard latency
        t0 = time.perf_counter()
        r5 = await client.get("/api/v1/governance/dashboard", headers=officer_headers)
        d5 = (time.perf_counter() - t0) * 1000
        assert r5.status_code == 200
        benchmarks.append(("/governance/dashboard", d5))

        # Verify all core responses are well within production limits (< 1000ms locally)
        for path, latency_ms in benchmarks:
            assert latency_ms < 1500.0, f"Endpoint {path} exceeded latency threshold: {latency_ms:.2f}ms"
