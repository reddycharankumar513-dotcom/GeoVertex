"""End-to-end Phase 1 validation script: verifies auth, RBAC, admin actions, and audit trail."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from httpx import AsyncClient, ASGITransport
from app.main import app

async def run_verification():
    print("=" * 60)
    print("GEOVERTEX PHASE 1: END-TO-END DEMO FLOW VERIFICATION")
    print("=" * 60)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # 1. Health Probe
        print("\n1. Testing Health Endpoints...")
        h_res = await client.get("/health")
        assert h_res.status_code == 200, f"Health check failed: {h_res.text}"
        print(f"   [OK] /health: {h_res.json()['status']} (Version {h_res.json()['version']})")

        r_res = await client.get("/health/ready")
        assert r_res.status_code == 200, f"Readiness check failed: {r_res.text}"
        print(f"   [OK] /health/ready: Database connected = {r_res.json()['database']['connected']}")

        # 2. Login as Admin
        print("\n2. Authenticating as System Administrator...")
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "admin@geovertex.local", "password": "GeoVertexAdmin2026!"}
        )
        assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
        admin_data = login_res.json()
        admin_token = admin_data["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"   [OK] Admin Login Success: Role = {admin_data['user']['role']}")
        print(f"   [OK] Access Token Issued: {admin_token[:20]}...")

        # 3. Query /me
        print("\n3. Testing Current User Profile (/me)...")
        me_res = await client.get("/api/v1/auth/me", headers=admin_headers)
        assert me_res.status_code == 200
        print(f"   [OK] Current User: {me_res.json()['full_name']} ({me_res.json()['email']})")

        # 4. Admin lists users
        print("\n4. Admin Querying User Directory...")
        users_res = await client.get("/api/v1/users", headers=admin_headers)
        assert users_res.status_code == 200
        users = users_res.json()["items"]
        print(f"   [OK] Retrieved {len(users)} registered users from database")

        citizen_user = next((u for u in users if u["email"] == "citizen@geovertex.local"), None)
        assert citizen_user is not None, "Citizen user not found in seed"
        citizen_id = citizen_user["id"]

        # 5. Admin updates Citizen role to SURVEYOR
        print(f"\n5. Admin Modifying Role for User {citizen_user['email']}...")
        role_res = await client.patch(
            f"/api/v1/users/{citizen_id}/role",
            headers=admin_headers,
            json={"role": "SURVEYOR"}
        )
        assert role_res.status_code == 200
        print(f"   [OK] Role updated to: {role_res.json()['role']}")

        # Revert role back to CITIZEN
        await client.patch(
            f"/api/v1/users/{citizen_id}/role",
            headers=admin_headers,
            json={"role": "CITIZEN"}
        )
        print("   [OK] Reverted role back to CITIZEN")

        # 6. Admin deactivates user and verifies rejection
        print(f"\n6. Testing User Deactivation and Blocking...")
        deact_res = await client.patch(
            f"/api/v1/users/{citizen_id}/status",
            headers=admin_headers,
            json={"is_active": False}
        )
        assert deact_res.status_code == 200
        print("   [OK] Account marked is_active = False")

        # Attempt to login with deactivated citizen
        blocked_login = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "citizen@geovertex.local", "password": "GeoVertexCitizen2026!"}
        )
        assert blocked_login.status_code == 403
        print(f"   [OK] Deactivated login rejected: HTTP {blocked_login.status_code} [{blocked_login.json()['error']['code']}]")

        # Reactivate citizen
        await client.patch(
            f"/api/v1/users/{citizen_id}/status",
            headers=admin_headers,
            json={"is_active": True}
        )
        print("   [OK] Reactivated user account")

        # 7. Authenticate as Citizen and test RBAC rejection
        print("\n7. Testing Citizen RBAC Enforcement...")
        cit_login = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "citizen@geovertex.local", "password": "GeoVertexCitizen2026!"}
        )
        assert cit_login.status_code == 200
        citizen_token = cit_login.json()["access_token"]
        cit_headers = {"Authorization": f"Bearer {citizen_token}"}

        # Citizen tries to access Admin User Directory
        forbidden_res = await client.get("/api/v1/users", headers=cit_headers)
        assert forbidden_res.status_code == 403
        print(f"   [OK] Citizen access to /api/v1/users rejected: HTTP {forbidden_res.status_code} [{forbidden_res.json()['error']['code']}]")

        # 8. Check Audit Logs
        print("\n8. Verifying Immutable Audit Trail...")
        audit_res = await client.get("/api/v1/audit", headers=admin_headers)
        assert audit_res.status_code == 200
        audit_items = audit_res.json()["items"]
        print(f"   [OK] Total Audit Records: {audit_res.json()['total']}")
        actions = [a["action"] for a in audit_items[:5]]
        print(f"   [OK] Recent Actions Logged: {', '.join(actions)}")

    print("\n" + "=" * 60)
    print("ALL PHASE 1 DEMO FLOW CHECKS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_verification())
