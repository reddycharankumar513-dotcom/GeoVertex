from datetime import datetime, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.change.detector import DeterministicChangeDetector, AIChangeDetector
from app.ai.change.evaluator import ChangeDetectionEvaluator
from app.ai.change.image_registration import ImageRegistrationValidator
from app.gis.temporal.attribute_diff import AttributeComparator
from app.gis.temporal.geometry_diff import DeterministicGeometryComparator
from app.gis.temporal.matching import TemporalEntityMatcher
from app.gis.temporal.significance import SignificanceEvaluator
from app.gis.temporal.timeline import EntityTimelineBuilder
from app.models.temporal import (
    CandidateStatus,
    ChangeCandidate,
    ChangeDetectionRun,
    ChangeRunStatus,
    ChangeSignificance,
    ChangeType,
    PropertySnapshot,
)


# 1. Deterministic Geometry Difference Test
def test_deterministic_geometry_difference_and_metrics():
    # Baseline: 10m x 10m square in WGS84 coordinates (~0.0001 deg)
    base_wkt = "POLYGON((78.486671 17.385044, 78.486771 17.385044, 78.486771 17.385144, 78.486671 17.385144, 78.486671 17.385044))"
    # Current: 10m x 12.5m expanded rectangle (25% expansion)
    curr_wkt = "POLYGON((78.486671 17.385044, 78.486796 17.385044, 78.486796 17.385144, 78.486671 17.385144, 78.486671 17.385044))"

    res = DeterministicGeometryComparator.compare_geometries(base_wkt, curr_wkt)

    assert res.baseline_area > 0
    assert res.current_area > res.baseline_area
    assert res.area_difference > 0
    assert res.area_change_percentage > 20.0
    assert res.iou > 0.70
    assert res.iou < 1.0
    assert res.added_geometry_wkt is not None
    assert res.removed_geometry_wkt is None
    assert res.symmetric_diff_wkt is not None

    mag = res.to_magnitude_dict()
    assert "area_difference_sqm" in mag
    assert "iou" in mag
    assert "boundary_displacement_m" in mag


# 2. Building Expansion, Height & Floor Count Change Detection
def test_building_temporal_changes():
    detector = DeterministicChangeDetector()
    base_wkt = "POLYGON((78.486671 17.385044, 78.486771 17.385044, 78.486771 17.385144, 78.486671 17.385144, 78.486671 17.385044))"
    curr_wkt = "POLYGON((78.486671 17.385044, 78.486800 17.385044, 78.486800 17.385144, 78.486671 17.385144, 78.486671 17.385044))"

    baseline_data = {
        "entity_type": "BUILDING",
        "entity_id": uuid.uuid4(),
        "geometry_wkt": base_wkt,
        "attributes": {"height": 10.0, "floor_count": 3, "building_type": "RESIDENTIAL"},
    }
    comparison_data = {
        "entity_type": "BUILDING",
        "entity_id": baseline_data["entity_id"],
        "geometry_wkt": curr_wkt,
        "attributes": {"height": 14.5, "floor_count": 4, "building_type": "COMMERCIAL"},
    }

    changes = detector.detect_changes(baseline_data, comparison_data)
    change_types = [c["change_type"] for c in changes]

    # Must detect footprint expansion, height increase, and floor addition
    assert ChangeType.BUILDING_EXPANDED.value in change_types
    assert ChangeType.BUILDING_HEIGHT_CHANGED.value in change_types
    assert ChangeType.FLOOR_COUNT_CHANGED.value in change_types

    # Verify height difference magnitude
    height_change = next(c for c in changes if c["change_type"] == ChangeType.BUILDING_HEIGHT_CHANGED.value)
    assert height_change["magnitude"]["height_difference_m"] == 4.5
    assert height_change["significance"] == ChangeSignificance.MAJOR.value

    # Verify floor count difference magnitude
    floor_change = next(c for c in changes if c["change_type"] == ChangeType.FLOOR_COUNT_CHANGED.value)
    assert floor_change["magnitude"]["floor_count_difference"] == 1


# 3. Significance Classification
def test_significance_evaluator():
    # Minor: 2 sqm change
    sig_minor = SignificanceEvaluator.evaluate(
        ChangeType.BUILDING_AREA_CHANGED.value,
        {"area_difference_sqm": 2.0, "area_change_percentage": 2.0, "boundary_displacement_m": 0.2},
    )
    assert sig_minor == ChangeSignificance.MINOR

    # Moderate: 40 sqm change (12%)
    sig_mod = SignificanceEvaluator.evaluate(
        ChangeType.BUILDING_AREA_CHANGED.value,
        {"area_difference_sqm": 40.0, "area_change_percentage": 12.0, "boundary_displacement_m": 1.2},
    )
    assert sig_mod == ChangeSignificance.MODERATE

    # Major: 150 sqm change or added building
    sig_major = SignificanceEvaluator.evaluate(
        ChangeType.BUILDING_EXPANDED.value,
        {"area_difference_sqm": 150.0, "area_change_percentage": 35.0, "boundary_displacement_m": 5.0},
    )
    assert sig_major == ChangeSignificance.MAJOR

    sig_added = SignificanceEvaluator.evaluate(ChangeType.BUILDING_ADDED.value, {})
    assert sig_added == ChangeSignificance.MAJOR


# 4. Strict "No Fake AI" Enforcement
def test_no_fake_ai_model_and_evaluation_unconfigured():
    # AI Change detector with no weights must return MODEL_NOT_CONFIGURED
    ai_detector = AIChangeDetector(weights_path="/nonexistent/weights.pt")
    assert not ai_detector.is_configured()

    results = ai_detector.detect_changes({}, {})
    assert len(results) == 1
    assert results[0]["status"] == "MODEL_NOT_CONFIGURED"
    assert "MODEL_NOT_CONFIGURED" in results[0]["message"]
    assert results[0]["confidence"] == 0.0

    # Evaluator without ground truth dataset must return EVALUATION_DATASET_NOT_CONFIGURED
    eval_res = ChangeDetectionEvaluator.evaluate(predictions=[], ground_truth=None)
    assert eval_res["status"] == "EVALUATION_DATASET_NOT_CONFIGURED"
    assert eval_res["precision"] is None
    assert eval_res["recall"] is None


# 5. Image Registration Validation
def test_image_registration_validation():
    # 1. Aligned case
    meta_base = {"crs": "EPSG:4326", "resolution_meters": 0.5, "bounds": [78.48, 17.38, 78.49, 17.39]}
    meta_curr = {"crs": "EPSG:4326", "resolution_meters": 0.5, "bounds": [78.48, 17.38, 78.49, 17.39]}
    res_aligned = ImageRegistrationValidator.validate_and_register(meta_base, meta_curr)
    assert res_aligned["is_aligned"] is True

    # 2. CRS mismatch
    meta_crs_diff = {"crs": "EPSG:32644", "resolution_meters": 0.5, "bounds": [78.48, 17.38, 78.49, 17.39]}
    res_crs = ImageRegistrationValidator.validate_and_register(meta_base, meta_crs_diff)
    assert res_crs["is_aligned"] is False
    assert res_crs["status"] == "CRS_MISMATCH"

    # 3. Low spatial overlap
    meta_no_overlap = {"crs": "EPSG:4326", "resolution_meters": 0.5, "bounds": [79.48, 18.38, 79.49, 18.39]}
    res_overlap = ImageRegistrationValidator.validate_and_register(meta_base, meta_no_overlap)
    assert res_overlap["is_aligned"] is False
    assert res_overlap["status"] == "LOW_SPATIAL_OVERLAP"


# 6. Historical Entity Matcher
def test_temporal_entity_matcher():
    wkt1 = "POLYGON((78.486671 17.385044, 78.486771 17.385044, 78.486771 17.385144, 78.486671 17.385144, 78.486671 17.385044))"
    wkt_similar = "POLYGON((78.486672 17.385045, 78.486772 17.385045, 78.486772 17.385145, 78.486672 17.385145, 78.486672 17.385045))"

    historical = [{"id": "hist-b01", "reference": "BLDG-OLD-01", "geometry_wkt": wkt1}]
    current = [{"id": "curr-b99", "reference": "BLDG-NEW-99", "geometry_wkt": wkt_similar}]

    matches = TemporalEntityMatcher.match_entities(historical, current)
    assert len(matches) == 1
    assert matches[0].historical_id == "hist-b01"
    assert matches[0].current_id == "curr-b99"
    assert matches[0].match_score > 0.85
    assert matches[0].match_method == "SPATIAL_OVERLAP"


# 7. End-to-End API Lifecycle Test: Snapshot -> Detection Run -> Review -> Timeline
@pytest.mark.asyncio
async def test_change_detection_api_lifecycle(client: AsyncClient, auth_tokens: dict):
    officer_headers = auth_tokens["officer"]
    citizen_headers = auth_tokens["citizen"]
    bldg_id = str(uuid.uuid4())

    base_wkt = "POLYGON((78.486671 17.385044, 78.486771 17.385044, 78.486771 17.385144, 78.486671 17.385144, 78.486671 17.385044))"
    curr_wkt = "POLYGON((78.486671 17.385044, 78.486800 17.385044, 78.486800 17.385144, 78.486671 17.385144, 78.486671 17.385044))"

    # Step 1: Create Baseline Snapshot
    snap_payload = {
        "entity_type": "BUILDING",
        "entity_id": bldg_id,
        "snapshot_type": "OFFICIAL_RECORD",
        "effective_from": "2024-01-01T00:00:00Z",
        "observation_date": "2023-12-15T00:00:00Z",
        "geometry_wkt": base_wkt,
        "attributes": {"height": 10.0, "floor_count": 3, "area": 100.0},
        "version_number": 1,
        "is_current": False,
    }
    snap_res = await client.post("/api/v1/change-detection/snapshots", json=snap_payload, headers=officer_headers)
    assert snap_res.status_code == 201
    snap_data = snap_res.json()
    snapshot_id = snap_data["id"]

    # Step 2: Trigger Change Detection Run
    run_payload = {
        "target_type": "BUILDING",
        "target_id": bldg_id,
        "baseline_reference": snapshot_id,
        "comparison_reference": "2026-LIVE",
        "detection_method": "GEOMETRY_DIFF",
        "parameters": {
            "comparison_geometry_wkt": curr_wkt,
            "comparison_attributes": {"height": 14.0, "floor_count": 4, "area": 130.0},
        },
    }
    run_res = await client.post("/api/v1/change-detection/runs", json=run_payload, headers=officer_headers)
    assert run_res.status_code == 201
    run_data = run_res.json()
    run_id = run_data["id"]
    assert run_data["status"] == ChangeRunStatus.COMPLETED.value
    assert run_data["summary"]["total_candidates_detected"] >= 1

    # Step 3: Fetch Created Change Candidates
    changes_res = await client.get(f"/api/v1/change-detection/runs/{run_id}/changes", headers=officer_headers)
    assert changes_res.status_code == 200
    candidates = changes_res.json()
    assert len(candidates) >= 1

    exp_cand = next(c for c in candidates if c["change_type"] == ChangeType.BUILDING_EXPANDED.value)
    cand_id = exp_cand["id"]
    assert exp_cand["status"] == CandidateStatus.NEW.value
    assert exp_cand["magnitude"]["area_difference_sqm"] > 0

    # Step 4: Citizen Forbidden from Review
    review_payload = {
        "action": "CONFIRM",
        "review_reason": "CONFIRMED_FIELD_SURVEY",
        "review_notes": "Ground-truth verified against 2026 survey evidence",
    }
    cit_res = await client.post(f"/api/v1/change-detection/changes/{cand_id}/confirm", json=review_payload, headers=citizen_headers)
    assert cit_res.status_code == 403

    # Step 5: Officer Confirms Candidate
    conf_res = await client.post(f"/api/v1/change-detection/changes/{cand_id}/confirm", json=review_payload, headers=officer_headers)
    assert conf_res.status_code == 200
    conf_data = conf_res.json()
    assert conf_data["status"] == CandidateStatus.CONFIRMED.value
    assert conf_data["review_reason"] == "CONFIRMED_FIELD_SURVEY"

    # Step 6: Test Rejection with Mandatory Reason
    cand2 = candidates[1] if len(candidates) > 1 else exp_cand
    rej_payload = {
        "action": "REJECT",
        "review_reason": "FALSE_POSITIVE",
        "review_notes": "Temporary canopy structure detected, not permanent expansion",
    }
    rej_res = await client.post(f"/api/v1/change-detection/changes/{cand2['id']}/reject", json=rej_payload, headers=officer_headers)
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == CandidateStatus.REJECTED.value

    # Step 7: Retrieve Historical Timeline
    timeline_res = await client.get(f"/api/v1/change-detection/entities/BUILDING/{bldg_id}/timeline", headers=officer_headers)
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert len(timeline) >= 2  # Snapshot + Change Candidate

    # Step 8: Dashboard Metrics
    metrics_res = await client.get("/api/v1/change-detection/metrics", headers=officer_headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["total_runs"] >= 1
    assert metrics["total_candidates"] >= 1
