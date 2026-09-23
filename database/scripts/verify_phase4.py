"""End-to-end Phase 4 Building, Floor & Unit Hierarchy validation script:
Verifies Parcel -> Property -> Building -> Floor -> Unit hierarchy,
vertical elevation slicing (Zmin...Zmax), 2D/3D topological validations,
floor stacking, unit disjointness, Cesium 3D scene integration,
RBAC enforcement, and vertical audit trails.
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from httpx import AsyncClient, ASGITransport
from app.main import app


async def run_phase4_verification():
    print("=" * 80)
    print("GEOVERTEX PHASE 4: BUILDING, FLOOR & UNIT HIERARCHY VERIFICATION")
    print("=" * 80)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # Step 1: Health Check
        print("\n1. Testing System Health & PostgreSQL/PostGIS Engine...")
        h_res = await client.get("/health")
        assert h_res.status_code == 200
        print(f"   [OK] /health: {h_res.json()['status']} (Version {h_res.json()['version']})")

        # Step 2: Authenticate Personas
        print("\n2. Authenticating Multi-Role Actors (Admin, Officer, Surveyor, Citizen)...")
        roles = ["admin", "officer", "surveyor", "citizen"]
        tokens = {}
        for role in roles:
            login_res = await client.post(
                "/api/v1/auth/login",
                json={
                    "username_or_email": f"{role}@geovertex.local",
                    "password": f"GeoVertex{role.capitalize()}2026!",
                },
            )
            assert login_res.status_code == 200, f"Login failed for {role}: {login_res.text}"
            tokens[role] = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
            print(f"   [OK] Authenticated {role.upper()} ({login_res.json()['user']['role']})")

        admin_headers = tokens["admin"]
        officer_headers = tokens["officer"]
        surveyor_headers = tokens["surveyor"]
        citizen_headers = tokens["citizen"]

        # Step 3: Establish Cadastral Parcel & Building Context
        print("\n3. Setting Up Cadastral Context: Jurisdiction -> Parcel -> Property -> Building...")
        # Pre-cleanup any previous test parcels with GV-P4- prefix
        existing_p_res = await client.get("/api/v1/parcels?size=100", headers=admin_headers)
        if existing_p_res.status_code == 200:
            for p in existing_p_res.json().get("items", []):
                if p.get("parcel_code", "").startswith("GV-P4-"):
                    await client.delete(f"/api/v1/parcels/{p['id']}", headers=admin_headers)

        jur_res = await client.get("/api/v1/jurisdictions?limit=1", headers=officer_headers)
        assert jur_res.status_code == 200
        jurs = jur_res.json()
        jur_id = jurs[0]["id"] if isinstance(jurs, list) and len(jurs) > 0 else jurs["items"][0]["id"]

        p_uid = uuid.uuid4().hex[:6].upper()
        # Non-overlapping coordinates inside Ward 101 boundary (78.4850-78.4950, 17.3800-17.3950)
        p_res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur_id,
                "parcel_number": f"P-VERIF4-{p_uid}",
                "parcel_code": f"GV-P4-{p_uid}",
                "land_use": "COMMERCIAL",
                "geometry": "POLYGON((78.4870 17.3910, 78.4900 17.3910, 78.4900 17.3940, 78.4870 17.3940, 78.4870 17.3910))",
            },
            headers=officer_headers,
        )
        assert p_res.status_code == 201, f"Parcel creation failed: {p_res.text}"
        parcel_id = p_res.json()["id"]

        # Legal Property
        pr_res = await client.post(
            "/api/v1/properties",
            json={
                "parcel_id": parcel_id,
                "property_reference": f"PROP-P4-{p_uid}",
                "property_type": "COMMERCIAL",
                "address": "400 Silicon Corridor, HiTech City",
                "status": "REGISTERED",
            },
            headers=officer_headers,
        )
        assert pr_res.status_code == 201
        property_id = pr_res.json()["id"]

        # Building Footprint
        b_res = await client.post(
            "/api/v1/buildings",
            json={
                "parcel_id": parcel_id,
                "building_reference": f"BLD-P4-{p_uid}",
                "building_type": "COMMERCIAL",
                "status": "EXISTING",
                "height_estimate": 25.0,
                "geometry": "POLYGON((78.4875 17.3915, 78.4895 17.3915, 78.4895 17.3935, 78.4875 17.3935, 78.4875 17.3915))",
            },
            headers=officer_headers,
        )
        assert b_res.status_code == 201
        building_id = b_res.json()["id"]
        print(f"   [OK] Created Cadastral Root: Parcel {parcel_id[:8]} -> Property {property_id[:8]} -> Building {building_id[:8]}")

        # Step 4: Floor Creation & Stacking Validation
        print("\n4. Testing Vertical Floor Slicing & Elevation Stacking...")
        # 4a. Ground Floor (0.0m - 3.5m)
        f0_res = await client.post(
            "/api/v1/floors",
            json={
                "building_id": building_id,
                "floor_number": 0,
                "floor_code": f"BLD-P4-{p_uid}-F0",
                "floor_name": "Ground Floor Lobby & Retail",
                "floor_type": "COMMERCIAL",
                "elevation_min_m": 0.0,
                "elevation_max_m": 3.5,
                "status": "ACTIVE",
            },
            headers=officer_headers,
        )
        assert f0_res.status_code == 201
        f0_id = f0_res.json()["id"]
        print(f"   [OK] Ground Floor created: {f0_res.json()['floor_code']} (Z: 0.0m - 3.5m, Height: {f0_res.json()['height_m']}m)")

        # 4b. Level 1 (3.5m - 7.0m)
        f1_res = await client.post(
            "/api/v1/floors",
            json={
                "building_id": building_id,
                "floor_number": 1,
                "floor_code": f"BLD-P4-{p_uid}-F1",
                "floor_name": "Level 1 Corporate Offices",
                "floor_type": "COMMERCIAL",
                "elevation_min_m": 3.5,
                "elevation_max_m": 7.0,
                "status": "ACTIVE",
            },
            headers=officer_headers,
        )
        assert f1_res.status_code == 201
        f1_id = f1_res.json()["id"]
        print(f"   [OK] Level 1 Floor created: {f1_res.json()['floor_code']} (Z: 3.5m - 7.0m, Stacked continuously)")

        # 4c. Reject Vertical Elevation Clash
        print("\n5. Testing Floor Vertical Topological Validation...")
        clash_res = await client.post(
            "/api/v1/floors",
            json={
                "building_id": building_id,
                "floor_number": 2,
                "floor_code": f"BLD-P4-{p_uid}-FCLASH",
                "floor_name": "Clashing Floor",
                "floor_type": "COMMERCIAL",
                "elevation_min_m": 2.0,  # Clashes with Level 0 and Level 1
                "elevation_max_m": 5.0,
                "status": "ACTIVE",
            },
            headers=officer_headers,
        )
        assert clash_res.status_code == 400
        clash_err = clash_res.json().get('message') or clash_res.json().get('error', {}).get('message', 'Rejected')
        print(f"   [OK] Vertical clash correctly rejected: {clash_err}")

        # 4d. Reject Invalid / Negative Height Floor
        neg_res = await client.post(
            "/api/v1/floors",
            json={
                "building_id": building_id,
                "floor_number": 2,
                "floor_code": f"BLD-P4-{p_uid}-FNEG",
                "floor_name": "Zero Height Floor",
                "floor_type": "COMMERCIAL",
                "elevation_min_m": 7.0,
                "elevation_max_m": 7.0,
                "status": "ACTIVE",
            },
            headers=officer_headers,
        )
        assert neg_res.status_code == 400
        neg_err = neg_res.json().get('message') or neg_res.json().get('error', {}).get('message', 'Rejected')
        print(f"   [OK] Zero-height floor correctly rejected: {neg_err}")

        # Step 6: Property Unit Spatial Subdivisions
        print("\n6. Creating Property Unit Subdivisions & Topological Disjointness...")
        # Unit 101 - West Half of Level 1
        u1_res = await client.post(
            "/api/v1/units",
            json={
                "floor_id": f1_id,
                "property_id": property_id,
                "unit_number": "Suite 101",
                "unit_code": f"BLD-P4-{p_uid}-U101",
                "unit_type": "COMMERCIAL",
                "use_category": "OFFICE",
                "ownership_status": "OCCUPIED",
                "gross_area_sqm": 250.0,
                "net_area_sqm": 210.0,
                "elevation_min_m": 3.5,
                "elevation_max_m": 7.0,
                "geometry": "POLYGON((78.4875 17.3915, 78.4885 17.3915, 78.4885 17.3935, 78.4875 17.3935, 78.4875 17.3915))",
                "status": "ACTIVE",
            },
            headers=surveyor_headers,
        )
        assert u1_res.status_code == 201, f"Unit 101 creation failed: {u1_res.text}"
        u1_id = u1_res.json()["id"]
        print(f"   [OK] Unit 101 created: Suite 101 (Gross: 250m², Net: 210m², Z: 3.5m - 7.0m, Linked to Property {property_id[:8]})")

        # Unit 102 - East Half of Level 1
        u2_res = await client.post(
            "/api/v1/units",
            json={
                "floor_id": f1_id,
                "unit_number": "Suite 102",
                "unit_code": f"BLD-P4-{p_uid}-U102",
                "unit_type": "COMMERCIAL",
                "use_category": "OFFICE",
                "ownership_status": "VACANT",
                "gross_area_sqm": 250.0,
                "net_area_sqm": 205.0,
                "elevation_min_m": 3.5,
                "elevation_max_m": 7.0,
                "geometry": "POLYGON((78.4885 17.3915, 78.4895 17.3915, 78.4895 17.3935, 78.4885 17.3935, 78.4885 17.3915))",
                "status": "ACTIVE",
            },
            headers=surveyor_headers,
        )
        assert u2_res.status_code == 201, f"Unit 102 creation failed: {u2_res.text}"
        u2_id = u2_res.json()["id"]
        print(f"   [OK] Unit 102 created: Suite 102 (Gross: 250m², Net: 205m², Z: 3.5m - 7.0m, Status: VACANT)")

        # Unit Overlap Rejection
        print("\n7. Testing Unit Polygonal Interior Overlap Rejection...")
        u_clash_res = await client.post(
            "/api/v1/units",
            json={
                "floor_id": f1_id,
                "unit_number": "Suite CLASH",
                "unit_code": f"BLD-P4-{p_uid}-UCLASH",
                "gross_area_sqm": 100.0,
                "elevation_min_m": 3.5,
                "elevation_max_m": 7.0,
                "geometry": "POLYGON((78.4880 17.3920, 78.4890 17.3920, 78.4890 17.3930, 78.4880 17.3930, 78.4880 17.3920))",
            },
            headers=surveyor_headers,
        )
        assert u_clash_res.status_code == 400
        u_err = u_clash_res.json().get('message') or u_clash_res.json().get('error', {}).get('message', 'Rejected')
        print(f"   [OK] Unit interior overlap correctly rejected: {u_err}")

        # Step 8: Building Floors Listing Endpoint
        print("\n8. Verifying Hierarchy Query Endpoints...")
        b_floors_res = await client.get(f"/api/v1/buildings/{building_id}/floors", headers=officer_headers)
        assert b_floors_res.status_code == 200
        b_floors = b_floors_res.json()
        assert len(b_floors) == 2
        print(f"   [OK] GET /buildings/{building_id[:8]}/floors returned {len(b_floors)} stacked floors")

        # Step 9: 3D Digital Twin Integration
        print("\n9. Testing 3D Digital Twin Hierarchy Integration (/3d/buildings and /3d/scene)...")
        b3d_res = await client.get(f"/api/v1/3d/buildings/{building_id}", headers=officer_headers)
        assert b3d_res.status_code == 200
        b3d = b3d_res.json()
        assert "floors" in b3d
        assert len(b3d["floors"]) == 2
        f1_detail = next(f for f in b3d["floors"] if f["floor_number"] == 1)
        assert len(f1_detail["units"]) == 2
        print(f"   [OK] /api/v1/3d/buildings returned full tree:")
        print(f"        - Building: {b3d['building']['building_reference']}")
        print(f"        - Floors: {len(b3d['floors'])}")
        print(f"        - Level 1 Units: {[u['unit_number'] for u in f1_detail['units']]}")

        # 3D Scene Payload
        scene_res = await client.get("/api/v1/3d/scene?limit=100", headers=officer_headers)
        assert scene_res.status_code == 200
        scene = scene_res.json()
        assert "floors" in scene
        assert "units" in scene
        assert len(scene["floors"]) >= 2
        assert len(scene["units"]) >= 2
        print(f"   [OK] /api/v1/3d/scene payload includes:")
        print(f"        - Total 3D Floors: {len(scene['floors'])}")
        print(f"        - Total 3D Property Units: {len(scene['units'])}")
        print(f"        - Format: {scene['metadata']['representation_format']}")

        # 3D Identify Query
        identify_res = await client.get(
            "/api/v1/3d/identify?lon=78.4880&lat=17.3925&height=5.0",
            headers=officer_headers,
        )
        assert identify_res.status_code == 200
        id_data = identify_res.json()
        assert id_data.get("building") is not None
        assert id_data.get("floor") is not None
        assert id_data.get("unit") is not None
        print(f"   [OK] 3D Spatial Identify at (78.4880, 17.3925, Z=5.0m):")
        print(f"        - Identified Building: {id_data['building']['building_reference']}")
        print(f"        - Identified Floor: {id_data['floor']['floor_name']} (L{id_data['floor']['floor_number']})")
        print(f"        - Identified Unit: {id_data['unit']['unit_number']} ({id_data['unit']['unit_type']})")

        # Step 10: RBAC Enforcement
        print("\n10. Testing RBAC Access Control Enforcement...")
        # Citizen cannot create floors
        c_floor_res = await client.post(
            "/api/v1/floors",
            json={
                "building_id": building_id,
                "floor_number": 99,
                "floor_code": "ILLEGAL-F99",
                "elevation_min_m": 90.0,
                "elevation_max_m": 93.5,
            },
            headers=citizen_headers,
        )
        assert c_floor_res.status_code == 403
        print(f"   [OK] Citizen denied from POST /api/v1/floors (403 Forbidden)")

        # Citizen cannot create units
        c_unit_res = await client.post(
            "/api/v1/units",
            json={
                "floor_id": f1_id,
                "unit_number": "ILLEGAL-U99",
                "unit_code": "ILLEGAL-U99",
                "gross_area_sqm": 50.0,
                "elevation_min_m": 3.5,
                "elevation_max_m": 7.0,
            },
            headers=citizen_headers,
        )
        assert c_unit_res.status_code == 403
        print(f"   [OK] Citizen denied from POST /api/v1/units (403 Forbidden)")

        # Citizen can view floors and units
        c_view_res = await client.get(f"/api/v1/floors/{f0_id}", headers=citizen_headers)
        assert c_view_res.status_code == 200
        print(f"   [OK] Citizen allowed to read GET /api/v1/floors/{f0_id[:8]} (200 OK)")

        # Step 11: Audit Logging Verification
        print("\n11. Verifying Vertical Audit Trail...")
        audit_res = await client.get("/api/v1/audit?size=20", headers=admin_headers)
        assert audit_res.status_code == 200
        events = audit_res.json()["items"]
        actions = [e["action"] for e in events]
        assert "FLOOR_CREATED" in actions or "UNIT_CREATED" in actions
        print(f"   [OK] Vertical audit events found: {[a for a in actions if 'FLOOR' in a or 'UNIT' in a][:5]}")

    print("\n" + "=" * 80)
    print("ALL PHASE 4 VERIFICATION CHECKS PASSED (11/11 SUITES OK)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_phase4_verification())
