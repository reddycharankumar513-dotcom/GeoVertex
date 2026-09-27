import os
import uuid
from pathlib import Path
from PIL import Image
import pytest
from httpx import AsyncClient
from shapely.geometry import Polygon

from app.ai.base import (
    ModelIntegrityError,
    ModelNotConfiguredError,
    OutputGeometryInvalidError,
)
from app.ai.evaluation.metrics import compute_evaluation_metrics, compute_iou
from app.ai.models import DevelopmentBaselineBuildingExtractor, UnconfiguredFloorExtractor
from app.ai.postprocessing.polygonizer import BuildingPolygonizer, polygonizer
from app.ai.preprocessing.geo_processor import geo_preprocessor
from app.ai.preprocessing.image_processor import image_preprocessor
from app.ai.registry.model_registry import ModelRegistry, model_registry
from app.ai.validation.comparison import cadastral_comparator
from app.ai.validation.geo_validator import deterministic_validator
from app.ai.workers.job_worker import job_worker
from app.models.ai import AIProcessingJob, BuildingExtractionResult
from app.models.building import BuildingFootprint


# ============================================================================
# 1. Model Abstraction & Registry Tests
# ============================================================================

def test_model_abstraction_and_baseline_building_extractor():
    extractor = DevelopmentBaselineBuildingExtractor()
    extractor.load_model()
    meta = extractor.get_metadata()
    assert meta["model_id"] == "building-segmentation-v1"
    assert meta["status"] == "ACTIVE"

    # Preprocess
    prep = extractor.preprocess({
        "target_geometry": "POLYGON((78.381 17.441, 78.383 17.441, 78.383 17.443, 78.381 17.443, 78.381 17.441))"
    })
    assert "aoi" in prep

    # Predict
    pred = extractor.predict(prep)
    assert "raw_polygon" in pred

    # Postprocess
    res = extractor.postprocess(pred)
    assert res.model_name == "building-segmentation-v1"
    assert res.confidence_score > 0.0
    assert res.confidence_components.model_confidence > 0.0
    assert res.geometry_wkt.startswith("POLYGON")


def test_unconfigured_floor_extractor_enforces_critical_rule():
    floor_model = UnconfiguredFloorExtractor()
    floor_model.load_model()  # No weights provided
    meta = floor_model.get_metadata()
    assert meta["status"] == "UNCONFIGURED"

    # Calling predict without weights must strictly raise ModelNotConfiguredError
    with pytest.raises(ModelNotConfiguredError) as exc_info:
        floor_model.preprocess({"target_id": "dummy-bld-1"})
    assert "MODEL_NOT_CONFIGURED" in str(exc_info.value)


def test_model_registry_integrity_and_caching(tmp_path):
    registry = ModelRegistry()
    registry.register_model_class("building-test-v1", DevelopmentBaselineBuildingExtractor)
    assert registry.is_registered("building-test-v1")

    # Instance loading & reuse
    m1 = registry.get_or_load_model("building-test-v1", "1.0.0")
    m2 = registry.get_or_load_model("building-test-v1", "1.0.0")
    assert m1 is m2  # Reused from cache

    # Unregistered model raises ModelNotConfiguredError
    with pytest.raises(ModelNotConfiguredError):
        registry.get_or_load_model("non-existent-model")

    # Weights checksum integrity test
    dummy_weights = tmp_path / "weights.bin"
    dummy_weights.write_bytes(b"MODEL_WEIGHTS_CONTENT_12345")

    import hashlib
    correct_hash = hashlib.sha256(b"MODEL_WEIGHTS_CONTENT_12345").hexdigest()
    wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    assert registry.verify_weights_integrity(str(dummy_weights), correct_hash) is True

    with pytest.raises(ModelIntegrityError):
        registry.verify_weights_integrity(str(dummy_weights), wrong_hash)


# ============================================================================
# 2. Preprocessing & Postprocessing Tests
# ============================================================================

def test_image_preprocessor_and_derived_artifacts(tmp_path):
    # Create test image
    test_img_path = tmp_path / "survey_test.jpg"
    img = Image.new("RGB", (800, 600), color=(120, 160, 200))
    img.save(test_img_path, format="JPEG")

    # Extract metadata
    meta = image_preprocessor.extract_metadata(test_img_path)
    assert meta["dimensions"]["width"] == 800
    assert meta["dimensions"]["height"] == 600
    assert meta["format"] == "JPEG"

    # Preprocess image into derived artifact
    derived_path, proc_meta = image_preprocessor.preprocess_image(
        test_img_path, target_size=(512, 512)
    )
    assert derived_path.exists()
    assert proc_meta["target_size"] == (512, 512)
    assert test_img_path.exists()  # Original evidence preserved intact!


def test_geospatial_preprocessor_and_aoi():
    test_wkt = "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))"
    aoi = geo_preprocessor.compute_aoi(test_wkt, buffer_meters=20.0)
    assert aoi["target_srid"] == 4326
    assert aoi["target_area_sqm"] > 0
    assert len(aoi["bounds"]) == 4


def test_polygonizer_repair_and_simplification():
    poly = Polygon([(0, 0), (0, 2), (2, 0), (2, 2), (0, 0)])  # Bowtie self-intersecting polygon
    assert not poly.is_valid

    repaired, meta = polygonizer.postprocess_polygon(poly, min_area=0.01)
    assert repaired.is_valid
    assert meta["was_repaired"] is True

    # Test small area rejection
    small_poly = Polygon([(0, 0), (0, 0.00001), (0.00001, 0.00001), (0.00001, 0), (0, 0)])
    p = BuildingPolygonizer(min_area_sqm=500.0)
    with pytest.raises(OutputGeometryInvalidError):
        p.postprocess_polygon(small_poly)


# ============================================================================
# 3. Deterministic GIS Validation & Comparison Tests
# ============================================================================

def test_deterministic_geometry_validator():
    valid_wkt = "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))"
    val = deterministic_validator.validate_candidate_polygon(valid_wkt)
    assert val["status"] == "VALID"
    assert val["is_valid"] is True
    assert val["area_sqm"] > 0
    assert val["geometry_quality_score"] > 0.5

    # Invalid geometry
    bowtie_wkt = "POLYGON((0 0, 0 2, 2 0, 2 2, 0 0))"
    val_bad = deterministic_validator.validate_candidate_polygon(bowtie_wkt)
    assert val_bad["status"] == "INVALID"


def test_cadastral_comparison_and_confidence_framework():
    wkt1 = "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))"
    comp = cadastral_comparator.compare_geometries(wkt1, wkt1)
    assert comp["iou"] == 1.0
    assert comp["area_diff_sqm"] == 0.0

    # Composite confidence decomposition
    conf = cadastral_comparator.compute_composite_confidence(
        model_confidence=0.80,
        geometry_quality=0.90,
        source_quality=0.70,
    )
    # 0.5*0.8 + 0.3*0.9 + 0.2*0.7 = 0.40 + 0.27 + 0.14 = 0.81
    assert conf["composite_confidence"] == 0.81
    assert conf["components"]["model_confidence"] == 0.80
    assert conf["components"]["geometry_quality"] == 0.90
    assert conf["components"]["source_quality"] == 0.70


def test_evaluation_metrics_calculation():
    box1 = "POLYGON((78.381 17.441, 78.382 17.441, 78.382 17.442, 78.381 17.442, 78.381 17.441))"
    metrics = compute_evaluation_metrics([box1], [box1])
    assert metrics["mean_iou"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["mean_area_error_sqm"] == 0.0


# ============================================================================
# 4. REST API, RBAC & End-to-End Controlled Update Tests
# ============================================================================

@pytest.mark.asyncio
async def test_ai_job_rbac_and_dispatch(client: AsyncClient, seed_test_data, auth_tokens, db_session):
    jur = seed_test_data["jur"]

    # 1. Create a parcel and official building
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-AI-1",
            "parcel_code": "GV-AI-01",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        },
        headers=auth_tokens["officer"],
    )
    assert p_res.status_code == 201
    parcel_id = p_res.json()["id"]

    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-AI-001",
            "building_type": "COMMERCIAL",
            "status": "EXISTING",
            "height_estimate": 30.0,
            "geometry": "POLYGON((78.4863 17.3823, 78.4877 17.3823, 78.4877 17.3837, 78.4863 17.3837, 78.4863 17.3823))",
        },
        headers=auth_tokens["officer"],
    )
    assert b_res.status_code == 201
    building_id = b_res.json()["id"]
    original_area = b_res.json()["area"]

    # 2. Citizen cannot dispatch AI job (RBAC 403)
    c_res = await client.post(
        "/api/v1/ai/jobs",
        json={
            "job_type": "BUILDING_EXTRACTION",
            "target_type": "BUILDING",
            "target_id": building_id,
        },
        headers=auth_tokens["citizen"],
    )
    assert c_res.status_code == 403

    # 3. Surveyor dispatches AI job (HTTP 201)
    req_id = f"test-req-{uuid.uuid4().hex[:8]}"
    job_payload = {
        "client_request_id": req_id,
        "job_type": "BUILDING_EXTRACTION",
        "target_type": "BUILDING",
        "target_id": building_id,
        "model_id": "building-segmentation-v1",
        "model_version": "1.0.0",
    }
    s_res = await client.post("/api/v1/ai/jobs", json=job_payload, headers=auth_tokens["surveyor"])
    assert s_res.status_code == 201
    job_data = s_res.json()
    assert job_data["status"] == "QUEUED"
    assert job_data["client_request_id"] == req_id
    job_id = uuid.UUID(job_data["id"])

    # 4. Idempotency test: repeating same request returns same job
    dup_res = await client.post("/api/v1/ai/jobs", json=job_payload, headers=auth_tokens["surveyor"])
    assert dup_res.status_code == 201
    assert dup_res.json()["id"] == str(job_id)

    # 5. Worker processes job directly with test database session
    await job_worker.execute_job(job_id, session=db_session)

    # 6. Verify job status updated to COMPLETED
    job_check = await client.get(f"/api/v1/ai/jobs/{job_id}", headers=auth_tokens["officer"])
    assert job_check.status_code == 200
    assert job_check.json()["status"] == "COMPLETED"
    assert job_check.json()["progress_pct"] == 100

    # 7. Check candidate extraction result generated
    cand_res = await client.get(f"/api/v1/ai/building-results?target_id={building_id}", headers=auth_tokens["officer"])
    assert cand_res.status_code == 200
    results_list = cand_res.json()["items"]
    assert len(results_list) >= 1
    cand_item = results_list[0]
    assert cand_item["status"] == "REVIEW_REQUIRED"
    assert cand_item["validation_status"] == "VALID"
    assert cand_item["confidence"] > 0
    candidate_id = cand_item["id"]

    # 8. Human Review Gate: Surveyor cannot approve (HTTP 403)
    surv_app = await client.post(f"/api/v1/ai/results/{candidate_id}/approve", headers=auth_tokens["surveyor"])
    assert surv_app.status_code == 403

    # 9. Verify Official Building remains UNCHANGED before approval (Mandatory Rule)
    bld_check = await client.get(f"/api/v1/buildings/{building_id}", headers=auth_tokens["officer"])
    assert bld_check.json()["area"] == original_area

    # 10. Officer reviews & approves controlled update (HTTP 200)
    officer_app = await client.post(
        f"/api/v1/ai/results/{candidate_id}/approve?notes=Approved+by+Chief+Cadastral+Officer",
        headers=auth_tokens["officer"],
    )
    assert officer_app.status_code == 200
    app_data = officer_app.json()
    assert app_data["action"] == "APPROVE"
    assert app_data["applied_to_cadastre"] is True

    # 11. Verify Candidate status is now APPROVED
    cand_after = await client.get(f"/api/v1/ai/building-results/{candidate_id}", headers=auth_tokens["officer"])
    assert cand_after.json()["status"] == "APPROVED"

    # 12. Verify Official Building record has been updated through the approved workflow
    bld_after = await client.get(f"/api/v1/buildings/{building_id}", headers=auth_tokens["officer"])
    assert bld_after.status_code == 200
    assert bld_after.json()["geometry_wkt"] == cand_item["geometry_wkt"]


@pytest.mark.asyncio
async def test_unconfigured_floor_extraction_job_fails_gracefully(client: AsyncClient, seed_test_data, auth_tokens, db_session):
    # Enqueue a floor extraction job (unconfigured model)
    res = await client.post(
        "/api/v1/ai/jobs",
        json={
            "job_type": "FLOOR_EXTRACTION",
            "target_type": "BUILDING",
            "target_id": str(uuid.uuid4()),
            "model_id": "floor-extraction-v1",
        },
        headers=auth_tokens["officer"],
    )
    assert res.status_code == 201
    job_id = uuid.UUID(res.json()["id"])

    # Worker executes job
    await job_worker.execute_job(job_id, session=db_session)

    # Job must stop at FAILED with MODEL_NOT_CONFIGURED error code, without fake floors
    job_check = await client.get(f"/api/v1/ai/jobs/{job_id}", headers=auth_tokens["officer"])
    assert job_check.status_code == 200
    assert job_check.json()["status"] == "FAILED"
    assert job_check.json()["error_code"] == "MODEL_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_candidate_geometry_modification_and_controlled_approval(client: AsyncClient, seed_test_data, auth_tokens, db_session):
    jur = seed_test_data["jur"]

    # 1. Create parcel and building
    p_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-AI-2",
            "parcel_code": "GV-AI-02",
            "geometry": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        },
        headers=auth_tokens["officer"],
    )
    parcel_id = p_res.json()["id"]

    b_res = await client.post(
        "/api/v1/buildings",
        json={
            "parcel_id": parcel_id,
            "building_reference": "BLD-AI-002",
            "building_type": "RESIDENTIAL",
            "status": "EXISTING",
            "geometry": "POLYGON((78.4862 17.3822, 78.4872 17.3822, 78.4872 17.3832, 78.4862 17.3832, 78.4862 17.3822))",
        },
        headers=auth_tokens["officer"],
    )
    bld_id = b_res.json()["id"]

    # 2. Dispatch extraction job and run worker
    j_res = await client.post(
        "/api/v1/ai/jobs",
        json={
            "job_type": "BUILDING_EXTRACTION",
            "target_type": "BUILDING",
            "target_id": bld_id,
        },
        headers=auth_tokens["officer"],
    )
    job_id = uuid.UUID(j_res.json()["id"])
    await job_worker.execute_job(job_id, session=db_session)

    cand_res = await client.get(f"/api/v1/ai/building-results?target_id={bld_id}", headers=auth_tokens["officer"])
    candidate_id = cand_res.json()["items"][0]["id"]

    # 3. Officer refines vertices: MODIFY_AND_APPROVE
    refined_wkt = "POLYGON((78.4863 17.3823, 78.4875 17.3823, 78.4875 17.3835, 78.4863 17.3835, 78.4863 17.3823))"
    mod_res = await client.post(
        f"/api/v1/ai/results/{candidate_id}/modify",
        json={
            "action": "MODIFY_AND_APPROVE",
            "edited_geometry_wkt": refined_wkt,
            "notes": "Refined east corner to align with boundary wall",
        },
        headers=auth_tokens["officer"],
    )
    assert mod_res.status_code == 200
    assert mod_res.json()["action"] == "MODIFY_AND_APPROVE"
    assert mod_res.json()["applied_to_cadastre"] is True

    # 4. Verify candidate and official building both reflect refined geometry
    cand_after = await client.get(f"/api/v1/ai/building-results/{candidate_id}", headers=auth_tokens["officer"])
    assert cand_after.json()["geometry_wkt"] == refined_wkt

    bld_after = await client.get(f"/api/v1/buildings/{bld_id}", headers=auth_tokens["officer"])
    assert bld_after.json()["geometry_wkt"] == refined_wkt
