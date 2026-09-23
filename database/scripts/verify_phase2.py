"""End-to-end Phase 2 Cadastral GIS validation script:
Verifies cadastral parcels, properties, building footprints, spatial validation,
GIS GeoJSON import/export, RBAC permissions, and security audit trail.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from httpx import AsyncClient, ASGITransport
from app.main import app

async def run_phase2_verification():
    print("=" * 70)
    print("GEOVERTEX PHASE 2: CADASTRAL GIS END-TO-END VERIFICATION")
    print("=" * 70)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # 1. Health Probe
        print("\n1. Testing System Health & Database Connectivity...")
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

        # Clean up any residual test parcels from previous runs
        cleanup_res = await client.get("/api/v1/parcels?query=DEMO&size=50", headers=admin_headers)
        if cleanup_res.status_code == 200:
            for p in cleanup_res.json()["items"]:
                await client.delete(f"/api/v1/parcels/{p['id']}", headers=admin_headers)
        cleanup_imp = await client.get("/api/v1/parcels?query=IMP&size=50", headers=admin_headers)
        if cleanup_imp.status_code == 200:
            for p in cleanup_imp.json()["items"]:
                await client.delete(f"/api/v1/parcels/{p['id']}", headers=admin_headers)

        # 3. Verify Seed Jurisdictions
        print("\n3. Verifying Seed Jurisdictions...")
        jur_res = await client.get("/api/v1/jurisdictions", headers=admin_headers)
        assert jur_res.status_code == 200
        jurisdictions = jur_res.json()["items"]
        assert len(jurisdictions) >= 2, f"Expected at least 2 jurisdictions, got {len(jurisdictions)}"
        jur101 = next((j for j in jurisdictions if j["code"] == "JUR-W101"), jurisdictions[0])
        jur101_id = jur101["id"]
        print(f"   [OK] Jurisdictions verified: found {len(jurisdictions)} (e.g. {jur101['name']} [{jur101['code']}])")

        # 4. Verify Seed Parcels, Properties, Buildings
        print("\n4. Verifying Existing Cadastral Records from Database...")
        parcels_res = await client.get("/api/v1/parcels", headers=admin_headers)
        assert parcels_res.status_code == 200
        initial_parcels = parcels_res.json()["items"]
        print(f"   [OK] Total Parcels: {parcels_res.json()['total']} loaded")

        props_res = await client.get("/api/v1/properties", headers=admin_headers)
        assert props_res.status_code == 200
        print(f"   [OK] Total Properties: {props_res.json()['total']} loaded")

        bldgs_res = await client.get("/api/v1/buildings", headers=admin_headers)
        assert bldgs_res.status_code == 200
        print(f"   [OK] Total Building Footprints: {bldgs_res.json()['total']} loaded")

        # 5. Spatial Validation Endpoint (Valid vs Bowtie)
        print("\n5. Testing Spatial Validation Engine (Authoritative WGS84 Geodesy)...")
        valid_poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.4890, 17.3870],
                    [78.4900, 17.3870],
                    [78.4900, 17.3880],
                    [78.4890, 17.3880],
                    [78.4890, 17.3870],
                ]
            ],
        }
        val_res = await client.post(
            "/api/v1/spatial/validate",
            json={"geometry": valid_poly, "expected_type": "POLYGON"},
            headers=admin_headers
        )
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert val_data["valid"] is True
        print(f"   [OK] Valid Polygon: area = {val_data['area_sq_m']:.2f} sq m, centroid = {val_data['centroid']}")

        # Test self-intersecting bowtie polygon
        bowtie_poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.4890, 17.3870],
                    [78.4900, 17.3880],
                    [78.4900, 17.3870],
                    [78.4890, 17.3880],
                    [78.4890, 17.3870],
                ]
            ],
        }
        bowtie_res = await client.post(
            "/api/v1/spatial/validate",
            json={"geometry": bowtie_poly, "expected_type": "POLYGON"},
            headers=admin_headers
        )
        assert bowtie_res.status_code == 200
        assert bowtie_res.json()["valid"] is False
        print(f"   [OK] Self-Intersecting Bowtie Polygon: correctly detected as invalid ({bowtie_res.json()['errors'][0]['message']})")
        import uuid
        test_suffix = uuid.uuid4().hex[:6].upper()
        p_num = f"P-DEMO-{test_suffix}"
        p_code = f"W101-P{test_suffix}"
        # 6. Create New Cadastral Parcel
        print(f"\n6. Registering New Cadastral Parcel ({p_code})...")
        demo_parcel_poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.4881, 17.3871],
                    [78.4886, 17.3871],
                    [78.4886, 17.3876],
                    [78.4881, 17.3876],
                    [78.4881, 17.3871],
                ]
            ],
        }
        create_p_res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur101_id,
                "parcel_number": p_num,
                "parcel_code": p_code,
                "survey_number": f"SY-{test_suffix}",
                "land_use": "COMMERCIAL",
                "geometry": demo_parcel_poly,
                "source": "FIELD_SURVEY",
            },
            headers=admin_headers
        )
        assert create_p_res.status_code == 201, f"Parcel creation failed: {create_p_res.text}"
        new_parcel = create_p_res.json()
        new_parcel_id = new_parcel["id"]
        print(f"   [OK] Parcel Registered: {new_parcel['parcel_code']} (ID: {new_parcel_id[:8]}...)")
        print(f"        Computed Geodesic Area: {new_parcel['area']:.2f} sq m")
        print(f"        Computed Centroid: ({new_parcel['centroid_lon']:.5f}, {new_parcel['centroid_lat']:.5f})")

        # 7. Reject Overlapping Parcel
        print("\n7. Verifying Overlap Rejection for Duplicate/Overlapping Parcel...")
        overlap_res = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur101_id,
                "parcel_number": "P-DEMO-OVERLAP",
                "parcel_code": "W101-OVERLAP",
                "land_use": "RESIDENTIAL",
                "geometry": demo_parcel_poly,  # Identical geometry
                "source": "DIGITIZED",
            },
            headers=admin_headers
        )
        assert overlap_res.status_code in (400, 422), f"Expected 400 or 422 for overlapping parcel, got {overlap_res.status_code}"
        print(f"   [OK] Overlapping Parcel Rejected: HTTP {overlap_res.status_code} ({overlap_res.json().get('detail')})")

        # 8. Create Property Linked to Parcel
        print("\n8. Registering Legal Property on Parcel...")
        prop_res = await client.post(
            "/api/v1/properties",
            json={
                "parcel_id": new_parcel_id,
                "property_reference": f"PROP-DEMO-{test_suffix}",
                "property_type": "COMMERCIAL_RETAIL",
                "address": "99 Commercial Boulevard, Sector 1",
                "locality": "Central Ward",
                "postal_code": "500001",
                "description": "Premium Retail Plot",
            },
            headers=admin_headers
        )
        assert prop_res.status_code == 201, f"Property creation failed: {prop_res.text}"
        new_property = prop_res.json()
        new_property_id = new_property["id"]
        print(f"   [OK] Property Created: {new_property['property_reference']} on Parcel {new_parcel['parcel_code']}")

        # 9. Create Building Footprint Contained in Parcel
        print("\n9. Registering Building Footprint within Parcel Boundaries...")
        bldg_poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [78.4882, 17.3872],
                    [78.4885, 17.3872],
                    [78.4885, 17.3875],
                    [78.4882, 17.3875],
                    [78.4882, 17.3872],
                ]
            ],
        }
        bldg_create_res = await client.post(
            "/api/v1/buildings",
            json={
                "parcel_id": new_parcel_id,
                "building_reference": f"BLDG-DEMO-{test_suffix}",
                "building_type": "COMMERCIAL",
                "height_estimate": 24.5,
                "geometry": bldg_poly,
                "source": "FIELD_SURVEY",
            },
            headers=admin_headers
        )
        assert bldg_create_res.status_code == 201, f"Building creation failed: {bldg_create_res.text}"
        new_building = bldg_create_res.json()
        print(f"   [OK] Building Footprint Created: {new_building['building_reference']}")
        print(f"        Footprint Area: {new_building['area']:.2f} sq m, Est. Height: {new_building['height_estimate']}m")

        # 10. Query Parcel with Nested Properties & Buildings
        print("\n10. Fetching Parcel Detailed View with Relationships...")
        get_p_res = await client.get(f"/api/v1/parcels/{new_parcel_id}", headers=admin_headers)
        assert get_p_res.status_code == 200
        p_details = get_p_res.json()
        assert len(p_details["properties"]) >= 1, "Expected linked property"
        assert len(p_details["buildings"]) >= 1, "Expected linked building"
        print(f"   [OK] Parcel details verified with {len(p_details['properties'])} property and {len(p_details['buildings'])} footprint")

        # 11. Viewport Map Feature Queries
        print("\n11. Querying 2D Map Viewport Endpoints...")
        map_p_res = await client.get("/api/v1/map/parcels", headers=admin_headers)
        assert map_p_res.status_code == 200
        map_parcels = map_p_res.json()
        assert map_parcels["type"] == "FeatureCollection"
        print(f"   [OK] /map/parcels: returned {len(map_parcels['features'])} GeoJSON features")

        map_b_res = await client.get("/api/v1/map/buildings", headers=admin_headers)
        assert map_b_res.status_code == 200
        print(f"   [OK] /map/buildings: returned {len(map_b_res.json()['features'])} GeoJSON features")

        map_bound_res = await client.get("/api/v1/map/boundaries", headers=admin_headers)
        assert map_bound_res.status_code == 200
        print(f"   [OK] /map/boundaries: returned {len(map_bound_res.json()['features'])} administrative polygons")

        # 12. Spatial Identify Tool
        print("\n12. Testing Spatial Identify Tool (Point Query: 78.4883, 17.3873)...")
        ident_res = await client.get(
            "/api/v1/spatial/identify?longitude=78.4883&latitude=17.3873&radius_meters=30",
            headers=admin_headers
        )
        assert ident_res.status_code == 200
        ident_data = ident_res.json()
        assert len(ident_data["parcels"]) > 0, "Expected parcel to be identified at coordinate"
        print(f"   [OK] Identified: {ident_data['parcels'][0]['identifier']} ({ident_data['parcels'][0]['title']})")
        if ident_data["buildings"]:
            print(f"   [OK] Identified Building: {ident_data['buildings'][0]['identifier']}")

        # 13. GIS Batch Import
        print("\n13. Testing GIS GeoJSON Batch Ingestion Service...")
        import_payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [78.4860, 17.3910],
                                [78.4870, 17.3910],
                                [78.4870, 17.3920],
                                [78.4860, 17.3920],
                                [78.4860, 17.3910],
                            ]
                        ],
                    },
                    "properties": {
                        "parcel_number": f"P-IMP-{test_suffix}",
                        "land_use": "RESIDENTIAL",
                        "survey_number": f"SY-IMP-{test_suffix}",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": bowtie_poly,  # Intentionally invalid
                    "properties": {
                        "parcel_number": "P-IMPORT-BAD",
                        "land_use": "RESIDENTIAL",
                    },
                },
            ],
        }
        import_res = await client.post(
            f"/api/v1/gis/import?jurisdiction_id={jur101_id}",
            json=import_payload,
            headers=admin_headers
        )
        assert import_res.status_code == 200, f"GIS import failed: {import_res.text}"
        imp_summary = import_res.json()
        assert imp_summary["records_accepted"] == 1
        assert imp_summary["records_rejected"] == 1
        print(f"   [OK] GIS Ingest Complete: {imp_summary['records_accepted']} accepted, {imp_summary['records_rejected']} rejected")
        print(f"        Rejection Reason: Feature #{imp_summary['errors'][0]['feature_index']} -> {imp_summary['errors'][0]['message']}")

        # 14. GIS GeoJSON Export
        print("\n14. Testing GIS Cadastre Export Service...")
        export_res = await client.get(
            f"/api/v1/gis/export?jurisdiction_id={jur101_id}&status=ACTIVE",
            headers=admin_headers
        )
        assert export_res.status_code == 200
        export_fc = export_res.json()
        assert export_fc["type"] == "FeatureCollection"
        print(f"   [OK] Export Generated: {len(export_fc['features'])} valid WGS84 GeoJSON features")

        # 15. RBAC Enforcement (Citizen vs Admin)
        print("\n15. Testing Role-Based Access Control (RBAC)...")
        cit_login = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "citizen@geovertex.local", "password": "GeoVertexCitizen2026!"}
        )
        assert cit_login.status_code == 200
        cit_token = cit_login.json()["access_token"]
        cit_headers = {"Authorization": f"Bearer {cit_token}"}

        # Citizen can view parcels
        cit_read = await client.get("/api/v1/parcels", headers=cit_headers)
        assert cit_read.status_code == 200
        print(f"   [OK] CITIZEN: Read permissions verified (200 OK)")

        # Citizen CANNOT create parcels
        cit_create = await client.post(
            "/api/v1/parcels",
            json={
                "jurisdiction_id": jur101_id,
                "parcel_number": "P-FORBIDDEN",
                "geometry": valid_poly,
            },
            headers=cit_headers
        )
        assert cit_create.status_code == 403, f"Expected 403, got {cit_create.status_code}"
        print(f"   [OK] CITIZEN: Write forbidden verified (403 Forbidden)")

        # Citizen CANNOT delete parcels
        cit_del = await client.delete(f"/api/v1/parcels/{new_parcel_id}", headers=cit_headers)
        assert cit_del.status_code == 403, f"Expected 403, got {cit_del.status_code}"
        print(f"   [OK] CITIZEN: Delete forbidden verified (403 Forbidden)")

        # 16. Security Audit Trail
        print("\n16. Verifying Security Audit Trail for Phase 2 Operations...")
        audit_res = await client.get("/api/v1/audit?size=20", headers=admin_headers)
        assert audit_res.status_code == 200
        audit_events = audit_res.json()["items"]
        actions = [a["action"] for a in audit_events]
        assert "PARCEL_CREATED" in actions, "Missing PARCEL_CREATED in audit trail"
        assert "PROPERTY_CREATED" in actions, "Missing PROPERTY_CREATED in audit trail"
        assert "BUILDING_CREATED" in actions, "Missing BUILDING_CREATED in audit trail"
        print(f"   [OK] Audit Trail Verified: Logged actions: {set(actions)}")

        # 17. Cleanup Test Parcel
        print("\n17. Cleaning Up Test Artifacts...")
        del_res = await client.delete(f"/api/v1/parcels/{new_parcel_id}", headers=admin_headers)
        assert del_res.status_code == 200
        print(f"   [OK] Test Parcel {new_parcel['parcel_code']} Deleted Successfully")

    print("\n" + "=" * 70)
    print("ALL PHASE 2 VERIFICATION CHECKS PASSED SUCCESSFULLY (17/17)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_phase2_verification())
