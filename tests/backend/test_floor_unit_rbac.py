import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_floor_unit_rbac_permissions(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    officer_headers = auth_tokens["officer"]
    citizen_headers = auth_tokens["citizen"]
    surveyor_headers = auth_tokens["surveyor"]

    # 1. Officer creates building & floor
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-RBAC-FLR",
            "parcel_code": "GV-W500-PRBACFLR",
            "land_use": "RESIDENTIAL",
            "geometry": "POLYGON((78.4860 17.3820, 78.4890 17.3820, 78.4890 17.3850, 78.4860 17.3850, 78.4860 17.3820))",
        },
        headers=officer_headers,
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-RBAC-001",
            "building_type": "RESIDENTIAL",
            "status": "EXISTING",
            "geometry": "POLYGON((78.4865 17.3825, 78.4885 17.3825, 78.4885 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=officer_headers,
    )
    assert b_res.status_code == 201
    bld_id = b_res.json()["id"]

    # 2. Citizen can read floors
    get_floors = await client.get(f"/api/v1/buildings/{bld_id}/floors", headers=citizen_headers)
    assert get_floors.status_code == 200

    # 3. Citizen cannot create floor (403 Forbidden)
    cit_create_flr = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 0,
            "floor_code": "BLD-RBAC-001-F0-CIT",
            "elevation_min_m": 0.0,
            "elevation_max_m": 3.0,
        },
        headers=citizen_headers,
    )
    assert cit_create_flr.status_code == 403

    # 4. Surveyor can create floor
    surv_create_flr = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 0,
            "floor_code": "BLD-RBAC-001-F0",
            "elevation_min_m": 0.0,
            "elevation_max_m": 3.0,
        },
        headers=surveyor_headers,
    )
    assert surv_create_flr.status_code == 201
    flr_id = surv_create_flr.json()["id"]

    # 5. Citizen cannot create unit (403 Forbidden)
    cit_create_unit = await client.post(
        "/api/v1/units",
        json={
            "floor_id": flr_id,
            "building_id": bld_id,
            "unit_number": "101",
            "unit_code": "BLD-RBAC-001-F0-U101",
            "geometry": "POLYGON((78.4865 17.3825, 78.4875 17.3825, 78.4875 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=citizen_headers,
    )
    assert cit_create_unit.status_code == 403

    # 6. Surveyor can create unit
    surv_create_unit = await client.post(
        "/api/v1/units",
        json={
            "floor_id": flr_id,
            "building_id": bld_id,
            "unit_number": "101",
            "unit_code": "BLD-RBAC-001-F0-U101",
            "geometry": "POLYGON((78.4865 17.3825, 78.4875 17.3825, 78.4875 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=surveyor_headers,
    )
    assert surv_create_unit.status_code == 201
    unit_id = surv_create_unit.json()["id"]

    # 7. Citizen can read unit
    cit_get_unit = await client.get(f"/api/v1/units/{unit_id}", headers=citizen_headers)
    assert cit_get_unit.status_code == 200

    # 8. Citizen cannot delete unit
    cit_del = await client.delete(f"/api/v1/units/{unit_id}", headers=citizen_headers)
    assert cit_del.status_code == 403
