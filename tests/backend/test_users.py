import pytest
from httpx import AsyncClient


async def get_token_for(client: AsyncClient, email: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": "TestPassword123!"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_create_user(client: AsyncClient, seed_test_data):
    admin_token = await get_token_for(client, "admin@test.org")
    payload = {
        "email": "field_surveyor_2@domain.com",
        "username": "surveyor_2",
        "full_name": "Field Surveyor 2",
        "password": "SecurePassword123!",
        "role": "SURVEYOR",
        "phone": "+919876543219",
    }
    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "field_surveyor_2@domain.com"
    assert data["role"] == "SURVEYOR"


@pytest.mark.asyncio
async def test_admin_update_user_role(client: AsyncClient, seed_test_data):
    admin_token = await get_token_for(client, "admin@test.org")
    target_user_id = str(seed_test_data["users"]["CITIZEN"].id)

    # Elevate Citizen to Surveyor
    response = await client.patch(
        f"/api/v1/users/{target_user_id}/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "SURVEYOR"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "SURVEYOR"


@pytest.mark.asyncio
async def test_admin_deactivate_and_block_user(client: AsyncClient, seed_test_data):
    admin_token = await get_token_for(client, "admin@test.org")
    planner_user = seed_test_data["users"]["URBAN_PLANNER"]
    planner_id = str(planner_user.id)

    # 1. Login as planner to get token before deactivation
    planner_token = await get_token_for(client, planner_user.email)

    # 2. Deactivate Planner
    deact_res = await client.patch(
        f"/api/v1/users/{planner_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False

    # 3. Using existing token now returns 403 Forbidden / Inactive
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert me_res.status_code == 403
    assert me_res.json()["error"]["code"] == "FORBIDDEN"

    # 4. Attempting new login fails with 403
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": planner_user.email, "password": "TestPassword123!"},
    )
    assert login_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(client: AsyncClient, seed_test_data):
    admin_user = seed_test_data["users"]["ADMIN"]
    admin_token = await get_token_for(client, admin_user.email)

    response = await client.patch(
        f"/api/v1/users/{str(admin_user.id)}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
