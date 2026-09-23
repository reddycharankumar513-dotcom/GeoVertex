import pytest
from httpx import AsyncClient


async def get_token_for(client: AsyncClient, email: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": "TestPassword123!"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_list_and_create_organization(client: AsyncClient, seed_test_data):
    admin_token = await get_token_for(client, "admin@test.org")

    # List
    list_res = await client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # Create new
    payload = {
        "name": "State Spatial Survey Commission",
        "code": "SSSC-02",
        "type": "SURVEY_AGENCY",
    }
    create_res = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert create_res.status_code == 201
    assert create_res.json()["code"] == "SSSC-02"


@pytest.mark.asyncio
async def test_list_and_create_jurisdiction(client: AsyncClient, seed_test_data):
    admin_token = await get_token_for(client, "admin@test.org")
    org_id = str(seed_test_data["org"].id)

    # List
    list_res = await client.get(
        "/api/v1/jurisdictions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # Create new
    payload = {
        "organization_id": org_id,
        "name": "District Zone 4 - Urban Sector",
        "code": "JUR-DZ04",
        "level": "DISTRICT",
        "srid": 4326,
        "boundary_wkt": "MULTIPOLYGON(((77.10 28.50, 77.20 28.50, 77.20 28.60, 77.10 28.60, 77.10 28.50)))",
    }
    create_res = await client.post(
        "/api/v1/jurisdictions",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert create_res.status_code == 201
    assert create_res.json()["code"] == "JUR-DZ04"
    assert create_res.json()["srid"] == 4326
