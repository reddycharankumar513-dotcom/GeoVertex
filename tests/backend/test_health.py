import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_endpoints(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data

    live_res = await client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "database" in data
    assert data["database"]["connected"] is True
    assert "cache" in data
