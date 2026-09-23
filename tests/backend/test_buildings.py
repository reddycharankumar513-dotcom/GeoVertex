import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_building(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # 1. Create parcel
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-BLD-1",
            "parcel_code": "GV-W500-PBLD1",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        },
        headers=headers,
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    # 2. Create building footprint situated inside the parcel
    bld_payload = {
        "parcel_id": parcel_id,
        "building_reference": "BLD-TEST-001",
        "building_type": "COMMERCIAL",
        "status": "EXISTING",
        "height_estimate": 42.5,
        "geometry": "POLYGON((78.4863 17.3823, 78.4877 17.3823, 78.4877 17.3837, 78.4863 17.3837, 78.4863 17.3823))",
    }
    b_res = await client.post("/api/v1/buildings", json=bld_payload, headers=headers)
    assert b_res.status_code == 201, f"Create building failed: {b_res.text}"
    bld_data = b_res.json()
    assert bld_data["building_reference"] == "BLD-TEST-001"
    assert bld_data["area"] > 0.0
    assert bld_data["height_estimate"] == 42.5
    bld_id = bld_data["id"]

    # 3. Retrieve building detail
    get_res = await client.get(f"/api/v1/buildings/{bld_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["parcel_number"] == "P-BLD-1"
    assert detail["parcel_code"] == "GV-W500-PBLD1"


@pytest.mark.asyncio
async def test_building_invalid_geometry_rejected(client: AsyncClient, seed_test_data, auth_tokens):
    headers = auth_tokens["officer"]

    bowtie_payload = {
        "building_reference": "BLD-INVALID",
        "building_type": "RESIDENTIAL",
        "geometry": "POLYGON((0 0, 0 2, 2 0, 2 2, 0 0))",
    }
    res = await client.post("/api/v1/buildings", json=bowtie_payload, headers=headers)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_update_and_delete_building(client: AsyncClient, seed_test_data, auth_tokens):
    headers = auth_tokens["officer"]

    # Create standalone building
    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "building_reference": "BLD-TEST-002",
            "building_type": "RESIDENTIAL",
            "geometry": "POLYGON((78.4860 17.3850, 78.4870 17.3850, 78.4870 17.3860, 78.4860 17.3860, 78.4860 17.3850))",
        },
        headers=headers,
    )
    assert b_res.status_code == 201
    bld_id = b_res.json()["id"]

    # Update building
    patch_res = await client.patch(
        f"/api/v1/buildings/{bld_id}",
        json={"status": "UNDER_CONSTRUCTION", "height_estimate": 15.0},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "UNDER_CONSTRUCTION"
    assert patch_res.json()["height_estimate"] == 15.0

    # Delete building
    del_res = await client.delete(f"/api/v1/buildings/{bld_id}", headers=headers)
    assert del_res.status_code == 200
    assert (await client.get(f"/api/v1/buildings/{bld_id}", headers=headers)).status_code == 404
