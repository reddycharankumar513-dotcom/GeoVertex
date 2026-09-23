import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_parcel(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Valid polygon inside Ward 500 (78.4800 to 78.5000, 17.3800 to 17.4000)
    payload = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-501",
        "parcel_code": "GV-W500-P501",
        "survey_number": "SY-501/A",
        "land_use": "RESIDENTIAL",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.4850, 17.3850],
                    [78.4870, 17.3850],
                    [78.4870, 17.3870],
                    [78.4850, 17.3870],
                    [78.4850, 17.3850],
                ]
            ],
        },
    }

    res = await client.post("/api/v1/parcels", json=payload, headers=headers)
    assert res.status_code == 201, f"Create parcel failed: {res.text}"
    data = res.json()
    assert data["parcel_number"] == "P-501"
    assert data["parcel_code"] == "GV-W500-P501"
    assert data["area"] > 0.0
    assert data["centroid_lon"] is not None
    assert data["centroid_lat"] is not None
    parcel_id = data["id"]

    # Retrieve parcel detail
    get_res = await client.get(f"/api/v1/parcels/{parcel_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["parcel_code"] == "GV-W500-P501"
    assert detail["jurisdiction_name"] == jur.name


@pytest.mark.asyncio
async def test_duplicate_parcel_number_rejected(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    payload1 = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-DUP-1",
        "parcel_code": "GV-W500-DUP1",
        "geometry": "POLYGON((78.4810 17.3810, 78.4830 17.3810, 78.4830 17.3830, 78.4810 17.3830, 78.4810 17.3810))",
    }
    res1 = await client.post("/api/v1/parcels", json=payload1, headers=headers)
    assert res1.status_code == 201

    payload2 = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-DUP-1",  # Duplicate number in same jurisdiction
        "parcel_code": "GV-W500-DUP2",
        "geometry": "POLYGON((78.4835 17.3810, 78.4855 17.3810, 78.4855 17.3830, 78.4835 17.3830, 78.4835 17.3810))",
    }
    res2 = await client.post("/api/v1/parcels", json=payload2, headers=headers)
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_parcel_code_rejected(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    payload1 = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-CODE-1",
        "parcel_code": "GV-UNIQUE-CODE-1",
        "geometry": "POLYGON((78.4810 17.3840, 78.4830 17.3840, 78.4830 17.3860, 78.4810 17.3860, 78.4810 17.3840))",
    }
    res1 = await client.post("/api/v1/parcels", json=payload1, headers=headers)
    assert res1.status_code == 201

    payload2 = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-CODE-2",
        "parcel_code": "GV-UNIQUE-CODE-1",  # Duplicate parcel_code
        "geometry": "POLYGON((78.4835 17.3840, 78.4855 17.3840, 78.4855 17.3860, 78.4835 17.3860, 78.4835 17.3840))",
    }
    res2 = await client.post("/api/v1/parcels", json=payload2, headers=headers)
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_invalid_self_intersecting_geometry_rejected(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Bowtie self-intersecting polygon
    bowtie_payload = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-BOWTIE",
        "parcel_code": "GV-W500-BOWTIE",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.4850, 17.3850],
                    [78.4870, 17.3870],
                    [78.4870, 17.3850],
                    [78.4850, 17.3870],
                    [78.4850, 17.3850],
                ]
            ],
        },
    }

    res = await client.post("/api/v1/parcels", json=bowtie_payload, headers=headers)
    assert res.status_code == 400
    err = res.json()["error"]
    assert err["code"] == "BAD_REQUEST"
    assert "details" in err
    errors = err["details"]["errors"]
    assert any("SELF_INTERSECTION" in e["code"] or "INVALID_GEOMETRY" in e["code"] for e in errors)


@pytest.mark.asyncio
async def test_empty_geometry_rejected(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    payload = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-EMPTY",
        "parcel_code": "GV-W500-EMPTY",
        "geometry": "POLYGON EMPTY",
    }
    res = await client.post("/api/v1/parcels", json=payload, headers=headers)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_parcel_outside_jurisdiction_rejected(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Far away polygon: lon 77.0, lat 12.0 (outside Ward 500's boundary of 78.48-78.50, 17.38-17.40)
    outside_payload = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-OUTSIDE",
        "parcel_code": "GV-W500-OUTSIDE",
        "geometry": "POLYGON((77.1000 12.1000, 77.1020 12.1000, 77.1020 12.1020, 77.1000 12.1020, 77.1000 12.1000))",
    }
    res = await client.post("/api/v1/parcels", json=outside_payload, headers=headers)
    assert res.status_code == 400
    err_codes = [e["code"] for e in res.json()["error"]["details"]["errors"]]
    assert "PARCEL_OUTSIDE_JURISDICTION" in err_codes


@pytest.mark.asyncio
async def test_update_parcel_attributes_and_geometry(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    create_payload = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-UPD-1",
        "parcel_code": "GV-W500-UPD1",
        "land_use": "RESIDENTIAL",
        "geometry": "POLYGON((78.4810 17.3870, 78.4830 17.3870, 78.4830 17.3890, 78.4810 17.3890, 78.4810 17.3870))",
    }
    create_res = await client.post("/api/v1/parcels", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    parcel_id = create_res.json()["id"]
    old_area = create_res.json()["area"]

    # Update land use and expand geometry
    update_payload = {
        "land_use": "COMMERCIAL",
        "geometry": "POLYGON((78.4810 17.3870, 78.4840 17.3870, 78.4840 17.3890, 78.4810 17.3890, 78.4810 17.3870))",
    }
    update_res = await client.patch(f"/api/v1/parcels/{parcel_id}", json=update_payload, headers=headers)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["land_use"] == "COMMERCIAL"
    assert updated_data["area"] > old_area


@pytest.mark.asyncio
async def test_delete_parcel(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    create_payload = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-DEL-1",
        "parcel_code": "GV-W500-DEL1",
        "geometry": "POLYGON((78.4810 17.3900, 78.4830 17.3900, 78.4830 17.3920, 78.4810 17.3920, 78.4810 17.3900))",
    }
    create_res = await client.post("/api/v1/parcels", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    parcel_id = create_res.json()["id"]

    del_res = await client.delete(f"/api/v1/parcels/{parcel_id}", headers=headers)
    assert del_res.status_code == 200

    # Ensure 404 on subsequent get
    get_res = await client.get(f"/api/v1/parcels/{parcel_id}", headers=headers)
    assert get_res.status_code == 404
