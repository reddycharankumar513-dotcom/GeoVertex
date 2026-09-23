import pytest
from httpx import AsyncClient


async def get_token_for(client: AsyncClient, email: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": "TestPassword123!"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_audit_logs_recorded(client: AsyncClient, seed_test_data):
    admin_token = await get_token_for(client, "admin@test.org")

    # Perform action: create a user
    create_res = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "audit_test_user@domain.com",
            "username": "audit_user",
            "full_name": "Audit Test User",
            "password": "SecurePassword123!",
            "role": "CITIZEN",
        },
    )
    assert create_res.status_code == 201

    # Query audit logs
    audit_res = await client.get(
        "/api/v1/audit?action=USER_CREATED",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert audit_res.status_code == 200
    data = audit_res.json()
    assert data["total"] >= 1
    assert any(item["action"] == "USER_CREATED" for item in data["items"])
