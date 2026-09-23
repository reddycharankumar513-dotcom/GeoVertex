import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_property(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # 1. Create a parent parcel
    parcel_payload = {
        "jurisdiction_id": str(jur.id),
        "parcel_number": "P-PROP-1",
        "parcel_code": "GV-W500-PPROP1",
        "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
    }
    p_res = await client.post("/api/v1/parcels", json=parcel_payload, headers=headers)
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    # 2. Create Property linked to parcel
    prop_payload = {
        "parcel_id": parcel_id,
        "property_reference": "PROP-TEST-001",
        "property_type": "FREEHOLD",
        "status": "ACTIVE",
        "address": "123 Sovereign Court, Gachibowli",
        "locality": "Financial Core",
        "postal_code": "500032",
        "description": "High-tech software lab",
    }
    create_res = await client.post("/api/v1/properties", json=prop_payload, headers=headers)
    assert create_res.status_code == 201
    prop_id = create_res.json()["id"]

    # 3. Retrieve property and verify parcel relation
    get_res = await client.get(f"/api/v1/properties/{prop_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["property_reference"] == "PROP-TEST-001"
    assert detail["parcel_number"] == "P-PROP-1"
    assert detail["parcel_code"] == "GV-W500-PPROP1"


@pytest.mark.asyncio
async def test_create_property_invalid_parcel_rejected(client: AsyncClient, seed_test_data, auth_tokens):
    headers = auth_tokens["officer"]
    fake_parcel_id = str(uuid.uuid4())

    prop_payload = {
        "parcel_id": fake_parcel_id,
        "property_reference": "PROP-FAIL-001",
        "address": "404 Void Lane",
    }
    res = await client.post("/api/v1/properties", json=prop_payload, headers=headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_and_delete_property(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Create parcel
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-PROP-2",
            "parcel_code": "GV-W500-PPROP2",
            "geometry": "POLYGON((78.4890 17.3820, 78.4910 17.3820, 78.4910 17.3840, 78.4890 17.3840, 78.4890 17.3820))",
        },
        headers=headers,
    )
    parcel_id = p_res.json()["id"]

    # Create property
    prop_res = await client.post(
        "/api/v1/properties",
        json={
            "parcel_id": parcel_id,
            "property_reference": "PROP-TEST-002",
            "address": "55 Main Road",
        },
        headers=headers,
    )
    prop_id = prop_res.json()["id"]

    # Update address
    patch_res = await client.patch(
        f"/api/v1/properties/{prop_id}",
        json={"address": "55 Main Road North Wing", "status": "REGISTERED"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["address"] == "55 Main Road North Wing"
    assert patch_res.json()["status"] == "REGISTERED"

    # Delete property
    del_res = await client.delete(f"/api/v1/properties/{prop_id}", headers=headers)
    assert del_res.status_code == 200
    assert (await client.get(f"/api/v1/properties/{prop_id}", headers=headers)).status_code == 404
