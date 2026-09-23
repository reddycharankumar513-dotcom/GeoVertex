import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_floor_and_unit_spatial_validation(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # 1. Setup parcel & building
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-VAL-01",
            "parcel_code": "GV-W500-PVAL01",
            "land_use": "MIXED_USE",
            "geometry": "POLYGON((78.4860 17.3820, 78.4890 17.3820, 78.4890 17.3850, 78.4860 17.3850, 78.4860 17.3820))",
        },
        headers=headers,
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-VAL-001",
            "building_type": "MIXED_USE",
            "status": "EXISTING",
            "geometry": "POLYGON((78.4865 17.3825, 78.4885 17.3825, 78.4885 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=headers,
    )
    assert b_res.status_code == 201
    bld_id = b_res.json()["id"]

    # 2. Create Floor 0 [0.0m - 3.5m]
    f0_res = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 0,
            "floor_code": "BLD-VAL-001-F0",
            "elevation_min_m": 0.0,
            "elevation_max_m": 3.5,
        },
        headers=headers,
    )
    assert f0_res.status_code == 201
    f0_id = f0_res.json()["id"]

    # 3. Test Vertical Elevation Clash: Floor with overlapping elevation [2.0m - 5.5m]
    clash_res = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 1,
            "floor_code": "BLD-VAL-001-F1-CLASH",
            "elevation_min_m": 2.0,
            "elevation_max_m": 5.5,
        },
        headers=headers,
    )
    assert clash_res.status_code == 400
    assert "FLOOR_ELEVATION_CLASH" in str(clash_res.json())

    # 4. Test Duplicate Floor Number
    dup_num_res = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 0,  # Floor 0 already exists
            "floor_code": "BLD-VAL-001-F0-DUP",
            "elevation_min_m": 3.5,
            "elevation_max_m": 7.0,
        },
        headers=headers,
    )
    assert dup_num_res.status_code == 400
    assert "DUPLICATE_FLOOR_NUMBER" in str(dup_num_res.json())

    # 5. Test Floor Outside Building Footprint
    outside_flr_res = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 2,
            "floor_code": "BLD-VAL-001-F2-OUTSIDE",
            "elevation_min_m": 7.0,
            "elevation_max_m": 10.5,
            # Extends outside building footprint (17.3825 to 17.3845)
            "geometry": "POLYGON((78.4865 17.3825, 78.4900 17.3825, 78.4900 17.3860, 78.4865 17.3860, 78.4865 17.3825))",
        },
        headers=headers,
    )
    assert outside_flr_res.status_code == 400
    assert "FLOOR_OUTSIDE_BUILDING" in str(outside_flr_res.json())

    # 6. Create valid Unit on Floor 0
    u1_res = await client.post(
        "/api/v1/units",
        json={
            "floor_id": f0_id,
            "building_id": bld_id,
            "unit_number": "G-01",
            "unit_code": "BLD-VAL-001-F0-UG01",
            "unit_type": "RETAIL",
            "elevation_min_m": 0.0,
            "elevation_max_m": 3.5,
            "geometry": "POLYGON((78.4865 17.3825, 78.4875 17.3825, 78.4875 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=headers,
    )
    assert u1_res.status_code == 201

    # 7. Test Unit Area Overlap Conflict on Same Floor
    # Overlaps significantly with Unit G-01 (from 78.4870 to 78.4880)
    overlap_unit_res = await client.post(
        "/api/v1/units",
        json={
            "floor_id": f0_id,
            "building_id": bld_id,
            "unit_number": "G-02-CONFLICT",
            "unit_code": "BLD-VAL-001-F0-UG02-CONF",
            "unit_type": "RETAIL",
            "elevation_min_m": 0.0,
            "elevation_max_m": 3.5,
            "geometry": "POLYGON((78.4870 17.3825, 78.4880 17.3825, 78.4880 17.3845, 78.4870 17.3845, 78.4870 17.3825))",
        },
        headers=headers,
    )
    assert overlap_unit_res.status_code == 400
    assert "UNIT_OVERLAP_CONFLICT" in str(overlap_unit_res.json())
