import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_citizen_success(client: AsyncClient, seed_test_data):
    payload = {
        "email": "new_citizen@domain.com",
        "username": "new_citizen",
        "full_name": "New Citizen User",
        "password": "StrongPassword123!",
        "phone": "+919876543210",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new_citizen@domain.com"
    assert data["role"] == "CITIZEN"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client: AsyncClient, seed_test_data):
    payload = {
        "email": "citizen@test.org",  # Already seeded
        "username": "unique_username_999",
        "full_name": "Duplicate User",
        "password": "StrongPassword123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seed_test_data):
    payload = {
        "username_or_email": "admin@test.org",
        "password": "TestPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@test.org"
    assert data["user"]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_login_invalid_password_rejected(client: AsyncClient, seed_test_data):
    payload = {
        "username_or_email": "admin@test.org",
        "password": "WrongPassword!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(client: AsyncClient, seed_test_data):
    payload = {
        "username_or_email": "inactive@test.org",
        "password": "TestPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_get_current_user_me(client: AsyncClient, seed_test_data):
    # 1. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "surveyor@test.org", "password": "TestPassword123!"},
    )
    token = login_res.json()["access_token"]

    # 2. Query /me
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == "surveyor@test.org"
    assert user_data["role"] == "SURVEYOR"


@pytest.mark.asyncio
async def test_token_refresh_rotation(client: AsyncClient, seed_test_data):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "citizen@test.org", "password": "TestPassword123!"},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Refresh
    ref_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_res.status_code == 200
    new_tokens = ref_res.json()
    assert "access_token" in new_tokens
    assert new_tokens["refresh_token"] != refresh_token

    # Reusing the old refresh token must be rejected (Token Rotation)
    reuse_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reuse_res.status_code == 401


@pytest.mark.asyncio
async def test_logout_revocation(client: AsyncClient, seed_test_data):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "officer@test.org", "password": "TestPassword123!"},
    )
    access_token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    # Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Refresh after logout should fail
    ref_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_res.status_code == 401
