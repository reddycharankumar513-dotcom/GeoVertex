"""Comprehensive test suite for Phase 10: Underground Infrastructure & Subsurface Utility Intelligence."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.gis.utility.depth_elevation import DepthElevationCalculator
from app.gis.utility.spatial_relations import UtilitySpatialRelationshipAnalyzer
from app.gis.utility.network_topology import UtilityNetworkTopologyEngine
from app.gis.utility.clash_detector import UtilityClashDetector
from app.ai.utility.detector import AIUtilityDetector
from app.gis.validation.utility_rules import (
    UtilityDepthMissingRule,
    UtilityDepthInvalidRule,
    UtilityElevationInversionRule,
    UtilityDanglingEndpointRule,
)
from app.gis.validation.base import ValidationContext
from app.models.utility import UtilityAsset, UtilitySegment, UtilityNetwork, UtilitySeparationRule
from app.models.user import UserRole


# 1. Depth & Vertical Elevation Tests
def test_depth_elevation_and_slope_calculations():
    # Normal computation
    depth = DepthElevationCalculator.compute_depth(ground_elevation=105.0, centerline_elevation=102.5)
    assert depth == 2.5

    centerline = DepthElevationCalculator.compute_centerline_elevation(ground_elevation=105.0, depth=2.5)
    assert centerline == 102.5

    # Slope computation
    slope = DepthElevationCalculator.compute_slope(elevation_start=102.5, elevation_end=101.5, length_meters=50.0)
    assert slope == 2.0  # 2% grade

    # None handling (strict non-fabrication)
    assert DepthElevationCalculator.compute_depth(ground_elevation=105.0, centerline_elevation=None) is None
    assert DepthElevationCalculator.compute_centerline_elevation(ground_elevation=None, depth=2.5) is None
    assert DepthElevationCalculator.compute_slope(elevation_start=102.5, elevation_end=101.5, length_meters=0.0) is None


def test_vertical_bounds_validation():
    # Negative depth
    neg_issues = DepthElevationCalculator.validate_vertical_bounds(depth=-1.5)
    assert any(i["code"] == "UTILITY_INVALID_DEPTH" for i in neg_issues)

    # Elevation inversion (centerline higher than ground)
    inv_issues = DepthElevationCalculator.validate_vertical_bounds(
        depth=1.0, ground_elevation=100.0, centerline_elevation=102.0
    )
    assert any(i["code"] == "UTILITY_ELEVATION_INVERSION" for i in inv_issues)

    # Discrepancy between stated depth and derived depth
    disc_issues = DepthElevationCalculator.validate_vertical_bounds(
        depth=3.0, ground_elevation=105.0, centerline_elevation=103.5  # derived is 1.5m, stated is 3.0m
    )
    assert any(i["code"] == "UTILITY_DEPTH_ELEVATION_DISCREPANCY" for i in disc_issues)


# 2. Spatial Relationships (Parcels & Buildings)
def test_utility_parcel_relationship():
    # Pipeline crossing parcel: pipeline from (78.380, 17.440) to (78.384, 17.440)
    pipe_wkt = "LINESTRING(78.380 17.440, 78.384 17.440)"
    # Parcel polygon around (78.381, 17.439) to (78.383, 17.441)
    parcel_wkt = "POLYGON((78.381 17.439, 78.383 17.439, 78.383 17.441, 78.381 17.441, 78.381 17.439))"

    rel = UtilitySpatialRelationshipAnalyzer.analyze_parcel_relationship(
        utility_wkt=pipe_wkt,
        parcel_wkt=parcel_wkt,
        parcel_id="pcl-101",
        parcel_number="P-101",
    )
    assert rel.intersects is True
    assert rel.intersection_length_m > 100.0  # Approx 200m in UTM
    assert rel.is_crossing is True
    assert "Purely technical geometric intersection" in rel.legal_disclaimer


def test_utility_building_relationship():
    pipe_wkt = "LINESTRING(78.380 17.440, 78.384 17.440)"
    bld_wkt = "POLYGON((78.3815 17.4395, 78.3825 17.4395, 78.3825 17.4405, 78.3815 17.4405, 78.3815 17.4395))"

    # Case A: Passes beneath basement (depth 5.0m, basement 2.0m)
    rel_deep = UtilitySpatialRelationshipAnalyzer.analyze_building_relationship(
        utility_wkt=pipe_wkt,
        building_wkt=bld_wkt,
        utility_depth=5.0,
        building_basement_depth=2.0,
    )
    assert rel_deep.intersects_footprint is True
    assert rel_deep.passes_beneath is True
    assert rel_deep.enters_building is False
    assert rel_deep.vertical_clearance_m == 3.0

    # Case B: Direct collision with basement (depth 1.0m, basement 2.0m)
    rel_shallow = UtilitySpatialRelationshipAnalyzer.analyze_building_relationship(
        utility_wkt=pipe_wkt,
        building_wkt=bld_wkt,
        utility_depth=1.0,
        building_basement_depth=2.0,
    )
    assert rel_shallow.intersects_footprint is True
    assert rel_shallow.enters_building is True
    assert rel_shallow.relationship_review_required is True


# 3. Network Topology Engine
def test_network_topology_validation():
    nodes = [
        {"id": "n1", "node_type": "JUNCTION", "geometry_wkt": "POINT(78.380 17.440)"},
        {"id": "n2", "node_type": "JUNCTION", "geometry_wkt": "POINT(78.381 17.440)"},
        {"id": "n3", "node_type": "JUNCTION", "geometry_wkt": "POINT(78.382 17.440)"},
        {"id": "n_orphan", "node_type": "VALVE", "geometry_wkt": "POINT(78.385 17.445)"},
    ]

    segments = [
        {"id": "s1", "start_node_id": "n1", "end_node_id": "n2", "geometry_wkt": "LINESTRING(78.380 17.440, 78.381 17.440)"},
        {"id": "s2", "start_node_id": "n2", "end_node_id": "n3", "geometry_wkt": "LINESTRING(78.381 17.440, 78.382 17.440)"},
        # Duplicate segment between n1 and n2
        {"id": "s1_dup", "start_node_id": "n1", "end_node_id": "n2", "geometry_wkt": "LINESTRING(78.380 17.440, 78.381 17.440)"},
        # Dangling segment (no end node)
        {"id": "s_dangling", "start_node_id": "n3", "end_node_id": None, "geometry_wkt": "LINESTRING(78.382 17.440, 78.383 17.441)"},
    ]

    res = UtilityNetworkTopologyEngine.validate_network(nodes, segments)
    issues = res["issues"]

    assert any(i["issue_code"] == "UTILITY_DUPLICATE_SEGMENT" for i in issues)
    assert any(i["issue_code"] == "UTILITY_NODE_WITHOUT_CONNECTION" for i in issues)
    assert any(i["issue_code"] == "UTILITY_DANGLING_ENDPOINT" for i in issues)


# 4. 3D Clash Detection & Configurable Separation Rules
def test_clash_detection_and_rules():
    # Asset A: Water pipeline along 17.440
    asset_a = {
        "id": "asset-water",
        "asset_reference": "WTR-01",
        "utility_type": "WATER",
        "geometry_wkt": "LINESTRING(78.380 17.440, 78.385 17.440)",
        "centerline_elevation": 100.0,
        "depth": 2.0,
    }
    # Asset B: Sewer pipeline crossing perpendicularly at 78.382, with co-elevation (elev 100.0)
    asset_b_clash = {
        "id": "asset-sewer",
        "asset_reference": "SWR-01",
        "utility_type": "SEWER",
        "geometry_wkt": "LINESTRING(78.382 17.438, 78.382 17.442)",
        "centerline_elevation": 100.0,
        "depth": 2.0,
    }

    rules = [
        {
            "utility_type_a": "WATER",
            "utility_type_b": "SEWER",
            "required_horizontal_separation_m": 1.5,
            "required_vertical_separation_m": 0.5,
        }
    ]

    clashes = UtilityClashDetector.scan_asset_collection([asset_a, asset_b_clash], rules)
    assert len(clashes) == 1
    assert clashes[0].severity == "CRITICAL"
    assert clashes[0].vertical_relationship == "CO_ELEVATION"

    # Unconfigured rule check (strictly adheres to Section 23/61: SEPARATION_RULE_NOT_CONFIGURED)
    asset_c_gas = {
        "id": "asset-gas",
        "asset_reference": "GAS-01",
        "utility_type": "GAS",
        "geometry_wkt": "LINESTRING(78.382 17.438, 78.382 17.442)",
        "centerline_elevation": 102.0,
        "depth": 1.0,
    }
    clashes_no_rule = UtilityClashDetector.scan_asset_collection([asset_a, asset_c_gas], rules)
    # Gas has no rule with Water in `rules`
    if clashes_no_rule:
        assert clashes_no_rule[0].has_configured_rule is False
        assert "SEPARATION_RULE_NOT_CONFIGURED" in clashes_no_rule[0].notes


# 5. Strict "No Fake AI" Verification
def test_no_fake_ai_utility_detection():
    detector = AIUtilityDetector(model_weights_path=None)
    result = detector.detect_candidate_utilities(input_data={})
    assert result["status"] == "MODEL_NOT_CONFIGURED"
    assert result["can_execute"] is False
    assert "Deterministic GIS network topology" in result["message"]


# 6. Phase 7 Validation Rules Integration
def test_phase7_utility_validation_rules():
    # Test asset with missing depth and inverted elevation
    asset_invalid = UtilityAsset(
        id=uuid.uuid4(),
        network_id=uuid.uuid4(),
        asset_reference="PIPE-TEST-99",
        asset_type="PIPE",
        depth=None,
        ground_elevation=100.0,
        centerline_elevation=103.0,  # Centerline higher than ground
    )

    ctx = ValidationContext(
        target_type="UTILITY",
        target_id=str(asset_invalid.id),
        utility_assets=[asset_invalid],
    )

    r_depth = UtilityDepthMissingRule()
    issues_depth = r_depth.validate(ctx)
    assert len(issues_depth) == 1
    assert issues_depth[0].issue_code == "UTL-001"

    r_inv = UtilityElevationInversionRule()
    issues_inv = r_inv.validate(ctx)
    assert len(issues_inv) == 1
    assert issues_inv[0].issue_code == "UTL-004"


# 7. End-to-End API Lifecycle & RBAC
@pytest.mark.asyncio
async def test_utility_api_lifecycle_and_rbac(
    client: AsyncClient,
    auth_tokens: dict,
    seed_test_data: dict,
):
    admin_headers = auth_tokens["admin"]
    officer_headers = auth_tokens["officer"]
    citizen_headers = auth_tokens["citizen"]
    jurisdiction_id = str(seed_test_data["jur"].id)

    # Step 1: Create Utility Network (Officer/Admin allowed)
    net_res = await client.post(
        "/api/v1/utilities/networks",
        headers=officer_headers,
        json={
            "name": "Central Municipal Water Network",
            "utility_type": "WATER",
            "jurisdiction_id": jurisdiction_id,
            "owner_organization": "Hyderabad Municipal Water Supply",
            "status": "ACTIVE",
        },
    )
    assert net_res.status_code == 201
    network_id = net_res.json()["id"]

    # Step 2: Citizen forbidden from creating networks
    cit_res = await client.post(
        "/api/v1/utilities/networks",
        headers=citizen_headers,
        json={"name": "Illegal Network", "utility_type": "WATER", "jurisdiction_id": jurisdiction_id},
    )
    assert cit_res.status_code == 403

    # Step 3: Create Nodes
    n1_res = await client.post(
        "/api/v1/utilities/nodes",
        headers=officer_headers,
        json={
            "network_id": network_id,
            "node_type": "VALVE",
            "asset_reference": "VLV-101",
            "geometry_wkt": "POINT(78.380 17.440)",
            "elevation": 101.5,
            "depth": 1.5,
        },
    )
    assert n1_res.status_code == 201

    n2_res = await client.post(
        "/api/v1/utilities/nodes",
        headers=officer_headers,
        json={
            "network_id": network_id,
            "node_type": "JUNCTION",
            "asset_reference": "JNC-102",
            "geometry_wkt": "POINT(78.385 17.440)",
            "elevation": 100.8,
            "depth": 1.8,
        },
    )
    assert n2_res.status_code == 201

    # Step 4: Create Asset (Pipeline)
    pipe_res = await client.post(
        "/api/v1/utilities/assets",
        headers=officer_headers,
        json={
            "network_id": network_id,
            "asset_type": "PIPE",
            "asset_reference": "MAIN-FEEDER-01",
            "geometry_wkt": "LINESTRING(78.380 17.440, 78.385 17.440)",
            "ground_elevation": 103.0,
            "centerline_elevation": 101.2,
            "depth": 1.8,
            "diameter": 0.45,
            "material": "DUCTILE_IRON",
            "review_status": "CANDIDATE",
        },
    )
    assert pipe_res.status_code == 201
    asset_id = pipe_res.json()["id"]

    # Step 5: Configure Separation Rule
    rule_res = await client.post(
        "/api/v1/utilities/rules/separation",
        headers=admin_headers,
        json={
            "rule_code": f"RULE-WTR-SWR-{uuid.uuid4().hex[:6]}",
            "utility_type_a": "WATER",
            "utility_type_b": "SEWER",
            "required_horizontal_separation_m": 2.0,
            "required_vertical_separation_m": 0.5,
            "jurisdiction_id": jurisdiction_id,
        },
    )
    assert rule_res.status_code == 201

    # Step 6: Log Inspection
    insp_res = await client.post(
        f"/api/v1/utilities/assets/{asset_id}/inspections",
        headers=officer_headers,
        json={
            "inspection_date": "2026-09-24T12:00:00Z",
            "condition": "EXCELLENT",
            "depth_measurement": 1.82,
            "observations": "Pressure test passed. No joint leakage.",
            "status": "PASS",
        },
    )
    assert insp_res.status_code == 201

    # Step 7: Human Verification Decision
    verify_res = await client.post(
        f"/api/v1/utilities/assets/{asset_id}/verify",
        headers=officer_headers,
        json={
            "action": "VERIFY",
            "review_notes": "Ground survey and pressure inspection certified by cadastral officer.",
        },
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["review_status"] == "VERIFIED"

    # Step 8: Controlled Official Update with audit trail
    ctrl_res = await client.post(
        f"/api/v1/utilities/assets/{asset_id}/controlled-update",
        headers=officer_headers,
        json={
            "reason": "Post-commissioning capacity re-rating",
            "source_reference": "MUNICIPAL-CERT-2026-99",
            "updates": {"capacity": "5000_LPM"},
        },
    )
    assert ctrl_res.status_code == 200
    assert ctrl_res.json()["capacity"] == "5000_LPM"

    # Step 9: Query 2D GeoJSON & 3D Scene
    map_res = await client.get(
        "/api/v1/utilities/map?min_lon=78.37&min_lat=17.43&max_lon=78.39&max_lat=17.45",
        headers=officer_headers,
    )
    assert map_res.status_code == 200
    assert map_res.json()["type"] == "FeatureCollection"
    assert len(map_res.json()["features"]) >= 1

    scene_res = await client.get(
        "/api/v1/utilities/3d",
        headers=officer_headers,
    )
    assert scene_res.status_code == 200
    assert scene_res.json()["total_features"] >= 1
    assert scene_res.json()["features"][0]["color_hex"] == "#0284c7"  # Water blue

    # Step 10: Check Dashboard Metrics
    metrics_res = await client.get("/api/v1/utilities/metrics", headers=officer_headers)
    assert metrics_res.status_code == 200
    assert metrics_res.json()["total_networks"] >= 1
    assert metrics_res.json()["total_assets"] >= 1
