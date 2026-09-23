import pytest
from httpx import AsyncClient


async def get_token_for(client: AsyncClient, email: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": "TestPassword123!"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    response = await client.get("/api/v1/users")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_citizen_forbidden_from_admin_and_officer_routes(client: AsyncClient, seed_test_data):
    citizen_token = await get_token_for(client, "citizen@test.org")

    # Citizen cannot list users
    users_res = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert users_res.status_code == 403
    assert users_res.json()["error"]["code"] == "FORBIDDEN"

    # Citizen cannot query audit logs
    audit_res = await client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert audit_res.status_code == 403


@pytest.mark.asyncio
async def test_officer_can_view_users_but_cannot_modify_roles(client: AsyncClient, seed_test_data):
    officer_token = await get_token_for(client, "officer@test.org")
    target_user_id = str(seed_test_data["users"]["CITIZEN"].id)

    # Officer can view users
    list_res = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert list_res.status_code == 200

    # Officer cannot change role (Admin only)
    role_res = await client.patch(
        f"/api/v1/users/{target_user_id}/role",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"role": "SURVEYOR"},
    )
    assert role_res.status_code == 403

    # Officer cannot deactivate user (Admin only)
    status_res = await client.patch(
        f"/api/v1/users/{target_user_id}/status",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"is_active": False},
    )
    assert status_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_all_routes(client: AsyncClient, seed_test_data):
    admin_token = await get_token_for(client, "admin@test.org")

    # List users
    users_res = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert users_res.status_code == 200

    # Audit logs
    audit_res = await client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert audit_res.status_code == 200
