import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_and_update_building_3d(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # 1. Create parcel
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-3D-01",
            "parcel_code": "GV-W500-P3D01",
            "land_use": "COMMERCIAL",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        },
        headers=headers,
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    # 2. Create building footprint
    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-3D-001",
            "building_type": "COMMERCIAL",
            "status": "EXISTING",
            "height_estimate": 35.0,
            "geometry": "POLYGON((78.4863 17.3823, 78.4877 17.3823, 78.4877 17.3837, 78.4863 17.3837, 78.4863 17.3823))",
        },
        headers=headers,
    )
    assert b_res.status_code == 201
    bld_id = b_res.json()["id"]

    # 3. Retrieve building 3D detail
    get_3d = await client.get(f"/api/v1/3d/buildings/{bld_id}", headers=headers)
    assert get_3d.status_code == 200
    data_3d = get_3d.json()
    assert data_3d["building"]["building_reference"] == "BLD-3D-001"
    assert data_3d["representation_3d"]["height"] == 35.0
    assert data_3d["representation_3d"]["geometry_type"] == "EXTRUSION"
    assert data_3d["parcel"]["parcel_code"] == "GV-W500-P3D01"
    assert "cesium_extrusion" in data_3d
    ext = data_3d["cesium_extrusion"]
    assert ext["volume_cu_m"] > 0
    assert ext["height"] == 35.0
    assert len(ext["rings"]) > 0

    # 4. Update vertical height and base elevation
    patch_res = await client.patch(
        f"/api/v1/3d/buildings/{bld_id}/height",
        json={
            "height": 48.5,
            "base_elevation": 2.0,
            "height_source": "SURVEY",
            "height_confidence": 0.98,
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated_rep = patch_res.json()
    assert updated_rep["height"] == 48.5
    assert updated_rep["base_elevation"] == 2.0
    assert updated_rep["height_source"] == "SURVEY"

    # 5. Check audit logs for height update
    audit_res = await client.get(f"/api/v1/audit?entity_type=BUILDING_3D", headers=auth_tokens["admin"])
    assert audit_res.status_code == 200
    events = audit_res.json()["items"]
    actions = [e["action"] for e in events]
    assert "BUILDING_HEIGHT_UPDATED" in actions

    # 6. Retrieve parcel 3D context
    parcel_3d = await client.get(f"/api/v1/3d/parcels/{parcel_id}", headers=headers)
    assert parcel_3d.status_code == 200
    p_data = parcel_3d.json()
    assert p_data["parcel"]["parcel_code"] == "GV-W500-P3D01"
    assert len(p_data["buildings"]) == 1
    assert p_data["buildings"][0]["height"] == 48.5


@pytest.mark.asyncio
async def test_update_building_height_validation_error(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Create parcel & building
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-3D-VAL",
            "parcel_code": "GV-W500-PVAL",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        },
        headers=headers,
    )
    parcel_id = p_res.json()["id"]

    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-3D-VAL",
            "geometry": "POLYGON((78.4863 17.3823, 78.4877 17.3823, 78.4877 17.3837, 78.4863 17.3837, 78.4863 17.3823))",
        },
        headers=headers,
    )
    bld_id = b_res.json()["id"]

    # Attempt to set negative height -> rejected 422/400
    res_neg = await client.patch(
        f"/api/v1/3d/buildings/{bld_id}/height",
        json={"height": -10.0},
        headers=headers,
    )
    assert res_neg.status_code in [400, 422]
