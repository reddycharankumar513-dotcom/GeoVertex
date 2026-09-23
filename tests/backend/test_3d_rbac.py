import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_3d_rbac_permissions(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    officer_headers = auth_tokens["officer"]
    citizen_headers = auth_tokens["citizen"]

    # 1. Create parcel & building as officer
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-RBAC-01",
            "parcel_code": "GV-W500-PRBAC1",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        },
        headers=officer_headers,
    )
    parcel_id = p_res.json()["id"]

    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-RBAC-001",
            "height_estimate": 25.0,
            "geometry": "POLYGON((78.4863 17.3823, 78.4877 17.3823, 78.4877 17.3837, 78.4863 17.3837, 78.4863 17.3823))",
        },
        headers=officer_headers,
    )
    bld_id = b_res.json()["id"]

    # 2. Citizen tries to update building height -> 403 Forbidden
    res_citizen = await client.patch(
        f"/api/v1/3d/buildings/{bld_id}/height",
        json={"height": 55.0},
        headers=citizen_headers,
    )
    assert res_citizen.status_code == 403

    # 3. Citizen tries to create 3D asset -> 403 Forbidden
    res_asset_citizen = await client.post(
        "/api/v1/3d/assets",
        json={
            "building_id": bld_id,
            "asset_type": "EXTRUSION",
            "storage_location": "virtual://test",
            "format": "JSON_EXTRUSION",
        },
        headers=citizen_headers,
    )
    assert res_asset_citizen.status_code == 403

    # 4. Officer can create 3D asset -> 201 Created
    res_asset_officer = await client.post(
        "/api/v1/3d/assets",
        json={
            "building_id": bld_id,
            "asset_type": "EXTRUSION",
            "storage_location": "virtual://test",
            "format": "JSON_EXTRUSION",
        },
        headers=officer_headers,
    )
    assert res_asset_officer.status_code == 201
    asset_id = res_asset_officer.json()["id"]

    # 5. List assets
    list_assets = await client.get("/api/v1/3d/assets", headers=officer_headers)
    assert list_assets.status_code == 200
    assert len(list_assets.json()) >= 1
