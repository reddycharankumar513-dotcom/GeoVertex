import time
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_spatial_performance_benchmarks(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Seed 15 test parcels in loop
    for i in range(15):
        lon1 = 78.4800 + (i * 0.0010)
        lon2 = lon1 + 0.0008
        payload = {
            "jurisdiction_id": str(jur.id),
            "parcel_number": f"P-PERF-{i:03d}",
            "parcel_code": f"GV-W500-PERF-{i:03d}",
            "geometry": f"POLYGON(({lon1:.4f} 17.3810, {lon2:.4f} 17.3810, {lon2:.4f} 17.3820, {lon1:.4f} 17.3820, {lon1:.4f} 17.3810))",
        }
        res = await client.post("/api/v1/parcels", json=payload, headers=headers)
        assert res.status_code == 201

    # 1. Benchmark Bounding Box query
    start_time = time.perf_counter()
    bbox_res = await client.get(
        "/api/v1/map/parcels?bbox=78.4800,17.3800,78.4900,17.3850",
        headers=auth_tokens["citizen"],
    )
    bbox_duration_ms = (time.perf_counter() - start_time) * 1000
    assert bbox_res.status_code == 200
    assert bbox_duration_ms < 500.0, f"Bbox query too slow: {bbox_duration_ms:.2f}ms"

    # 2. Benchmark Search query
    start_time = time.perf_counter()
    search_res = await client.get(
        "/api/v1/parcels?query=PERF",
        headers=auth_tokens["citizen"],
    )
    search_duration_ms = (time.perf_counter() - start_time) * 1000
    assert search_res.status_code == 200
    assert search_duration_ms < 500.0, f"Search query too slow: {search_duration_ms:.2f}ms"

    # 3. Benchmark Spatial Identify query
    start_time = time.perf_counter()
    id_res = await client.get(
        "/api/v1/spatial/identify?longitude=78.4804&latitude=17.3815&radius_meters=30",
        headers=auth_tokens["citizen"],
    )
    id_duration_ms = (time.perf_counter() - start_time) * 1000
    assert id_res.status_code == 200
    assert id_duration_ms < 500.0, f"Identify query too slow: {id_duration_ms:.2f}ms"
