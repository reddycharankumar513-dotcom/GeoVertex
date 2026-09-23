import pytest
from httpx import AsyncClient
from app.gis.geometry import GeometryEngine


def test_geometry_engine_geodesic_area_and_centroid():
    # 0.001 degree ~ 111m east-west, ~110m north-south => ~12,000 sq meters
    wkt = "POLYGON((78.4850 17.3850, 78.4860 17.3850, 78.4860 17.3860, 78.4850 17.3860, 78.4850 17.3850))"
    geom = GeometryEngine.parse_geometry(wkt)
    area = GeometryEngine.calculate_geodesic_area(geom)
    assert 10000.0 < area < 15000.0

    lon, lat = GeometryEngine.calculate_centroid(geom)
    assert round(lon, 4) == 78.4855
    assert round(lat, 4) == 17.3855


@pytest.mark.asyncio
async def test_spatial_validate_endpoint(client: AsyncClient, seed_test_data, auth_tokens):
    headers = auth_tokens["citizen"]

    # Valid polygon
    valid_req = {
        "geometry": "POLYGON((78.4850 17.3850, 78.4870 17.3850, 78.4870 17.3870, 78.4850 17.3870, 78.4850 17.3850))",
        "expected_type": "POLYGON",
    }
    res = await client.post("/api/v1/spatial/validate", json=valid_req, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["area_sq_m"] > 0
    assert len(data["centroid"]) == 2
    assert len(data["bbox"]) == 4

    # Invalid bowtie polygon
    invalid_req = {
        "geometry": "POLYGON((0 0, 0 2, 2 0, 2 2, 0 0))",
        "expected_type": "POLYGON",
    }
    res_inv = await client.post("/api/v1/spatial/validate", json=invalid_req, headers=headers)
    assert res_inv.status_code == 200
    data_inv = res_inv.json()
    assert data_inv["valid"] is False
    assert len(data_inv["errors"]) > 0


@pytest.mark.asyncio
async def test_spatial_identify_endpoint(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # 1. Create a parcel
    p_payload = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-ID-1",
        "parcel_code": "GV-W500-PID1",
        "geometry": "POLYGON((78.4850 17.3850, 78.4870 17.3850, 78.4870 17.3870, 78.4850 17.3870, 78.4850 17.3850))",
    }
    await client.post("/api/v1/parcels", json=p_payload, headers=headers)

    # 2. Click inside the parcel: lon 78.4860, lat 17.3860
    id_res = await client.get(
        "/api/v1/spatial/identify?longitude=78.4860&latitude=17.3860&radius_meters=30",
        headers=auth_tokens["citizen"],
    )
    assert id_res.status_code == 200
    id_data = id_res.json()
    assert len(id_data["parcels"]) >= 1
    assert id_data["parcels"][0]["identifier"] == "GV-W500-PID1"
    assert id_data["parcels"][0]["distance_meters"] == 0.0


@pytest.mark.asyncio
async def test_map_parcels_bbox_query(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Create parcel inside bbox
    await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-BBOX-IN",
            "parcel_code": "GV-W500-BBOXIN",
            "geometry": "POLYGON((78.4850 17.3850, 78.4860 17.3850, 78.4860 17.3860, 78.4850 17.3860, 78.4850 17.3850))",
        },
        headers=headers,
    )

    # Create parcel outside bbox
    await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-BBOX-OUT",
            "parcel_code": "GV-W500-BBOXOUT",
            "geometry": "POLYGON((78.4950 17.3950, 78.4960 17.3950, 78.4960 17.3960, 78.4950 17.3960, 78.4950 17.3950))",
        },
        headers=headers,
    )

    # Query with bbox covering only the first parcel
    res = await client.get(
        "/api/v1/map/parcels?bbox=78.4840,17.3840,78.4870,17.3870",
        headers=auth_tokens["citizen"],
    )
    assert res.status_code == 200
    fc = res.json()
    assert fc["type"] == "FeatureCollection"
    feat_codes = [f["properties"]["parcel_code"] for f in fc["features"]]
    assert "GV-W500-BBOXIN" in feat_codes
    assert "GV-W500-BBOXOUT" not in feat_codes


@pytest.mark.asyncio
async def test_overlap_check_valid_shared_boundary_vs_area_overlap(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Base parcel
    await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-BASE-1",
            "parcel_code": "GV-W500-BASE1",
            "geometry": "POLYGON((78.4850 17.3850, 78.4870 17.3850, 78.4870 17.3870, 78.4850 17.3870, 78.4850 17.3850))",
        },
        headers=headers,
    )

    # 1. Adjacent parcel touching ONLY at the shared boundary (lon 78.4870)
    touching_req = {
        "geometry": "POLYGON((78.4870 17.3850, 78.4890 17.3850, 78.4890 17.3870, 78.4870 17.3870, 78.4870 17.3850))",
        "jurisdiction_id": str(jur.id),
    }
    t_res = await client.post("/api/v1/spatial/check-overlap", json=touching_req, headers=headers)
    assert t_res.status_code == 200
    t_data = t_res.json()
    assert t_data["has_conflicts"] is False  # Shared boundary is NOT a conflict!

    # 2. Candidate overlapping deeply inside P-BASE-1
    overlapping_req = {
        "geometry": "POLYGON((78.4860 17.3860, 78.4880 17.3860, 78.4880 17.3880, 78.4860 17.3880, 78.4860 17.3860))",
        "jurisdiction_id": str(jur.id),
    }
    o_res = await client.post("/api/v1/spatial/check-overlap", json=overlapping_req, headers=headers)
    assert o_res.status_code == 200
    o_data = o_res.json()
    assert o_data["has_conflicts"] is True  # Real area overlap
    assert any(c["overlap_type"] == "INVALID_AREA_OVERLAP" for c in o_data["conflicts"])
