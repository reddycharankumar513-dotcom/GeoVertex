import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_property_unit_crud_and_lifecycle(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # 1. Create parcel & property
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-UNT-01",
            "parcel_code": "GV-W500-PUNT01",
            "land_use": "RESIDENTIAL",
            "geometry": "POLYGON((78.4860 17.3820, 78.4890 17.3820, 78.4890 17.3850, 78.4860 17.3850, 78.4860 17.3820))",
        },
        headers=headers,
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    prop_res = await client.post(
        "/api/v1/properties",
        json={
            "parcel_id": parcel_id,
            "property_reference": "PROP-UNT-001",
            "property_type": "FREEHOLD",
            "address": "Flat 101, Vertex Heights",
        },
        headers=headers,
    )
    assert prop_res.status_code == 201
    prop_id = prop_res.json()["id"]

    # 2. Create building & floor
    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-UNT-001",
            "building_type": "RESIDENTIAL",
            "status": "EXISTING",
            "geometry": "POLYGON((78.4865 17.3825, 78.4885 17.3825, 78.4885 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=headers,
    )
    assert b_res.status_code == 201
    bld_id = b_res.json()["id"]

    f_res = await client.post(
        "/api/v1/floors",
        json={
            "building_id": bld_id,
            "floor_number": 1,
            "floor_code": "BLD-UNT-001-F1",
            "floor_name": "Level 1",
            "floor_type": "RESIDENTIAL",
            "elevation_min_m": 3.0,
            "elevation_max_m": 6.0,
        },
        headers=headers,
    )
    assert f_res.status_code == 201
    flr_id = f_res.json()["id"]

    # 3. Create Unit 101 (West half of floor)
    u1_res = await client.post(
        "/api/v1/units",
        json={
            "floor_id": flr_id,
            "building_id": bld_id,
            "property_id": prop_id,
            "unit_number": "101",
            "unit_code": "BLD-UNT-001-F1-U101",
            "unit_type": "APARTMENT",
            "elevation_min_m": 3.0,
            "elevation_max_m": 6.0,
            "geometry": "POLYGON((78.4865 17.3825, 78.4875 17.3825, 78.4875 17.3845, 78.4865 17.3845, 78.4865 17.3825))",
        },
        headers=headers,
    )
    assert u1_res.status_code == 201
    u1_data = u1_res.json()
    assert u1_data["unit_code"] == "BLD-UNT-001-F1-U101"
    assert u1_data["unit_number"] == "101"
    assert u1_data["gross_area_sqm"] > 0
    assert u1_data["property_reference"] == "PROP-UNT-001"
    u1_id = u1_data["id"]

    # 4. Create Unit 102 (East half of floor - shared wall at 78.4875, no area overlap)
    u2_res = await client.post(
        "/api/v1/units",
        json={
            "floor_id": flr_id,
            "building_id": bld_id,
            "unit_number": "102",
            "unit_code": "BLD-UNT-001-F1-U102",
            "unit_type": "APARTMENT",
            "elevation_min_m": 3.0,
            "elevation_max_m": 6.0,
            "geometry": "POLYGON((78.4875 17.3825, 78.4885 17.3825, 78.4885 17.3845, 78.4875 17.3845, 78.4875 17.3825))",
        },
        headers=headers,
    )
    assert u2_res.status_code == 201
    assert u2_res.json()["unit_number"] == "102"

    # 5. List units by floor
    floor_units = await client.get(f"/api/v1/units/by-floor/{flr_id}", headers=headers)
    assert floor_units.status_code == 200
    assert len(floor_units.json()) == 2

    # 6. Update unit
    upd_res = await client.put(
        f"/api/v1/units/{u1_id}",
        json={
            "ownership_status": "OCCUPIED",
            "net_area_sqm": 85.5,
        },
        headers=headers,
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["ownership_status"] == "OCCUPIED"
    assert upd_res.json()["net_area_sqm"] == 85.5

    # 7. Delete unit
    del_res = await client.delete(f"/api/v1/units/{u1_id}", headers=headers)
    assert del_res.status_code == 204
