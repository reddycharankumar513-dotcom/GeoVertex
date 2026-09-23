import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_floor_crud_and_lifecycle(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # 1. Create parcel
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-FLR-01",
            "parcel_code": "GV-W500-PFLR01",
            "land_use": "COMMERCIAL",
            "geometry": "POLYGON((78.4860 17.3820, 78.4890 17.3820, 78.4890 17.3850, 78.4860 17.3850, 78.4860 17.3820))",
        },
        headers=headers,
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    # 2. Create building
    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-FLR-001",
            "building_type": "COMMERCIAL",
            "status": "EXISTING",
            "height_estimate": 20.0,
            "geometry": "POLYGON((78.4865 17.3825, 78.4885 17.3825, 78.4885 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=headers,
    )
    assert b_res.status_code == 201
    bld_id = b_res.json()["id"]

    # 3. Create Ground Floor inheriting building geometry
    f0_res = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 0,
            "floor_code": "BLD-FLR-001-F0",
            "floor_name": "Ground Floor",
            "floor_type": "COMMERCIAL",
            "elevation_min_m": 0.0,
            "elevation_max_m": 3.5,
            "status": "ACTIVE",
        },
        headers=headers,
    )
    assert f0_res.status_code == 201
    f0_data = f0_res.json()
    assert f0_data["floor_code"] == "BLD-FLR-001-F0"
    assert f0_data["floor_number"] == 0
    assert f0_data["height_m"] == 3.5
    assert f0_data["area_sqm"] > 0
    f0_id = f0_data["id"]

    # 4. Create Level 1 stacked above Ground Floor
    f1_res = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 1,
            "floor_code": "BLD-FLR-001-F1",
            "floor_name": "Level 1 Offices",
            "floor_type": "COMMERCIAL",
            "elevation_min_m": 3.5,
            "elevation_max_m": 7.0,
            "status": "ACTIVE",
        },
        headers=headers,
    )
    assert f1_res.status_code == 201
    assert f1_res.json()["height_m"] == 3.5

    # 5. List floors by building
    list_res = await client.get(f"/api/v1/buildings/{bld_id}/floors", headers=headers)
    assert list_res.status_code == 200
    floors = list_res.json()
    assert len(floors) == 2
    assert floors[0]["floor_number"] == 0
    assert floors[1]["floor_number"] == 1

    # 6. Update floor
    upd_res = await client.put(
        f"/api/v1/floors/{f0_id}",
        json={
            "floor_name": "Ground Level Reception & Lobby",
            "floor_type": "RETAIL",
        },
        headers=headers,
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["floor_name"] == "Ground Level Reception & Lobby"
    assert upd_res.json()["floor_type"] == "RETAIL"

    # 7. Delete floor
    del_res = await client.delete(f"/api/v1/floors/{f0_id}", headers=headers)
    assert del_res.status_code == 204

    # 8. Verify floor removed
    get_res = await client.get(f"/api/v1/floors/{f0_id}", headers=headers)
    assert get_res.status_code == 404
