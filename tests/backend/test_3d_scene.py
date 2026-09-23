import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_3d_scene_and_identify(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # 1. Create parcel
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-SCENE-01",
            "parcel_code": "GV-W500-PSCENE1",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
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
            "building_reference": "BLD-SCENE-001",
            "building_type": "COMMERCIAL",
            "status": "EXISTING",
            "height_estimate": 40.0,
            "geometry": "POLYGON((78.4863 17.3823, 78.4877 17.3823, 78.4877 17.3837, 78.4863 17.3837, 78.4863 17.3823))",
        },
        headers=headers,
    )
    assert b_res.status_code == 201

    # 3. Retrieve 3D scene
    scene_res = await client.get("/api/v1/3d/scene", headers=headers)
    assert scene_res.status_code == 200
    scene = scene_res.json()
    assert scene["scene"]["crs"] == "EPSG:4326"
    assert scene["scene"]["vertical_reference"] == "METERS_ABOVE_GROUND"
    assert len(scene["buildings"]) >= 1
    assert len(scene["parcels"]) >= 1
    assert "camera_preset" in scene["scene"]

    # 4. Point-in-polygon 3D identify query
    # Point inside BLD-SCENE-001 (78.4870, 17.3830)
    identify_res = await client.get(
        "/api/v1/3d/identify?lon=78.4870&lat=17.3830&height=15.0",
        headers=headers,
    )
    assert identify_res.status_code == 200
    id_data = identify_res.json()
    assert id_data["building"] is not None
    assert id_data["building"]["building_reference"] == "BLD-SCENE-001"
    assert id_data["building"]["height"] == 40.0
    assert id_data["parcel"] is not None
    assert id_data["parcel"]["parcel_code"] == "GV-W500-PSCENE1"
