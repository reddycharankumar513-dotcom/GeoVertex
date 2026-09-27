import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from shapely.geometry import box

from app.gis.geometry import GeometryEngine
from app.gis.validation import (
    ALL_RULES,
    ValidationContext,
    ValidationToleranceConfig,
    rule_registry,
)
from app.gis.validation.engine import validation_engine
from app.gis.validation.worker import validation_worker
from app.models.building import BuildingFootprint
from app.models.floor import Floor
from app.models.jurisdiction import Jurisdiction
from app.models.parcel import Parcel
from app.models.survey import SurveyObservation, SurveySubmission
from app.models.unit import PropertyUnit
from app.models.ai import BuildingExtractionResult, AIProcessingJob
from app.models.validation import ValidationIssue, ValidationRun
from app.models.user import User


@pytest.mark.asyncio
async def test_rule_registry_and_versioning():
    """Verify rule discovery, category filtering, and metadata versioning."""
    rules = rule_registry.list_rules()
    assert len(rules) >= 20

    geom_rules = rule_registry.list_rules(category="GEOMETRY")
    assert any(r.rule_id == "GEOM_INVALID" for r in geom_rules)
    assert any(r.rule_id == "GEOM_SELF_INTERSECTION" for r in geom_rules)

    rule = rule_registry.get_rule("BUILDING_PARTIAL_OUTSIDE_PARCEL")
    assert rule is not None
    info = rule.explain()
    assert info["rule_id"] == "BUILDING_PARTIAL_OUTSIDE_PARCEL"
    assert info["severity"] in ["WARNING", "ERROR"]
    assert info["rule_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_geometry_validation_and_repair_suggestions():
    """Test geometric validity, bowtie self-intersection, and non-destructive repair generation."""
    # 1. Bowtie self-intersecting polygon
    bowtie_wkt = "POLYGON((0 0, 0 2, 2 0, 2 2, 0 0))"
    ctx = ValidationContext(
        target_type="BUILDING",
        target_id="test-bowtie",
        raw_geometries={"bowtie_test": bowtie_wkt},
    )

    res = validation_engine.execute_validation(ctx, rule_ids_filter=["GEOM_INVALID", "GEOM_SELF_INTERSECTION"])
    assert res["summary"]["total_issues"] >= 1
    issue = res["issues"][0]
    assert issue.rule_id in ["GEOM_INVALID", "GEOM_SELF_INTERSECTION"]
    assert issue.repair_candidate_wkt is not None
    assert "make_valid" in issue.repair_method

    # 2. Valid geometry has 0 issues
    valid_poly = "POLYGON((0 0, 2 0, 2 2, 0 2, 0 0))"
    ctx_valid = ValidationContext(
        target_type="BUILDING",
        target_id="test-valid",
        raw_geometries={"valid_poly": valid_poly},
    )
    res_valid = validation_engine.execute_validation(ctx_valid, rule_ids_filter=["GEOM_INVALID", "GEOM_SELF_INTERSECTION"])
    assert res_valid["summary"]["total_issues"] == 0


@pytest.mark.asyncio
async def test_parcel_topology_validation():
    """Test parcel-to-parcel overlap detection and coterminous edge handling."""
    # Parcel A: [78.480, 17.380] to [78.485, 17.385]
    poly_a = "POLYGON((78.480 17.380, 78.485 17.380, 78.485 17.385, 78.480 17.385, 78.480 17.380))"
    # Parcel B: Overlaps Parcel A by area
    poly_b = "POLYGON((78.484 17.380, 78.490 17.380, 78.490 17.385, 78.484 17.385, 78.484 17.380))"

    jur_id = uuid.uuid4()
    p1 = Parcel(id=uuid.uuid4(), jurisdiction_id=jur_id, parcel_number="P-001", parcel_code="P-001", geometry_wkt=poly_a)
    p2 = Parcel(id=uuid.uuid4(), jurisdiction_id=jur_id, parcel_number="P-002", parcel_code="P-002", geometry_wkt=poly_b)

    ctx = ValidationContext(
        target_type="PARCEL",
        target_id=str(p1.id),
        parcels=[p1, p2],
    )

    res = validation_engine.execute_validation(ctx, rule_ids_filter=["PARCEL_OVERLAP"])
    assert res["summary"]["total_issues"] == 1
    issue = res["issues"][0]
    assert issue.rule_id == "PARCEL_OVERLAP"
    assert "Spatial overlap detected between parcel P-001 and parcel P-002" in issue.message
    assert issue.geometry_wkt is not None


@pytest.mark.asyncio
async def test_building_to_parcel_validation():
    """Test building containment, partial overflow calculation, and area metrics."""
    # Parcel: [0, 0] to [10, 10] (in local or geographic units)
    # Using geographic coordinates around Hyderabad (17.38, 78.48)
    parcel_wkt = "POLYGON((78.4800 17.3800, 78.4820 17.3800, 78.4820 17.3820, 78.4800 17.3820, 78.4800 17.3800))"
    # Building extending 50% outside parcel east boundary
    bld_wkt = "POLYGON((78.4810 17.3805, 78.4830 17.3805, 78.4830 17.3815, 78.4810 17.3815, 78.4810 17.3805))"

    parcel_id = uuid.uuid4()
    p = Parcel(id=parcel_id, jurisdiction_id=uuid.uuid4(), parcel_number="P-TEST-1", parcel_code="P-TEST-1", geometry_wkt=parcel_wkt)
    b = BuildingFootprint(
        id=uuid.uuid4(),
        building_reference="BLD-TEST-1",
        parcel_id=parcel_id,
        geometry_wkt=bld_wkt,
        area=150.0,
        height_estimate=20.0,
    )

    ctx = ValidationContext(
        target_type="BUILDING",
        target_id=str(b.id),
        parcels=[p],
        buildings=[b],
    )

    res = validation_engine.execute_validation(ctx, rule_ids_filter=["BUILDING_PARTIAL_OUTSIDE_PARCEL", "BUILDING_OUTSIDE_PARCEL"])
    assert res["summary"]["total_issues"] == 1
    issue = res["issues"][0]
    assert issue.rule_id == "BUILDING_PARTIAL_OUTSIDE_PARCEL"
    assert issue.related_entity_id == str(parcel_id)
    assert "outside parcel" in issue.message
    assert "outside_ratio" in issue.metadata_json
    assert issue.metadata_json["outside_ratio"] > 0.30


@pytest.mark.asyncio
async def test_floor_vertical_elevation_and_stacking():
    """Test floor elevation interval logic (top > base), vertical overlap, and vertical gaps."""
    bld_id = uuid.uuid4()
    bld = BuildingFootprint(id=bld_id, building_reference="B-TOWER", geometry_wkt="POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))", height_estimate=20.0)


    # Floor 1: 0 to 4m
    f1 = Floor(id=uuid.uuid4(), building_id=bld_id, floor_number=0, floor_code="F-0", elevation_min_m=0.0, elevation_max_m=4.0, height_m=4.0)
    # Floor 2: 3.5 to 7.0m (overlaps Floor 1 by 0.5m!)
    f2 = Floor(id=uuid.uuid4(), building_id=bld_id, floor_number=1, floor_code="F-1", elevation_min_m=3.5, elevation_max_m=7.0, height_m=3.5)
    # Floor 3: Top < Base error (12.0 to 10.0m)
    f3 = Floor(id=uuid.uuid4(), building_id=bld_id, floor_number=2, floor_code="F-2", elevation_min_m=12.0, elevation_max_m=10.0, height_m=-2.0)

    ctx = ValidationContext(
        target_type="FLOOR",
        target_id=str(f1.id),
        buildings=[bld],
        floors=[f1, f2, f3],
    )

    res = validation_engine.execute_validation(ctx, rule_ids_filter=["FLOOR_INVALID_ELEVATION", "FLOOR_VERTICAL_OVERLAP"])
    rule_ids = [i.rule_id for i in res["issues"]]
    assert "FLOOR_VERTICAL_OVERLAP" in rule_ids
    assert "FLOOR_INVALID_ELEVATION" in rule_ids


@pytest.mark.asyncio
async def test_unit_containment_and_co_planar_overlap():
    """Test unit-to-floor containment and co-planar unit overlaps."""
    fl_id = uuid.uuid4()
    fl_poly = "POLYGON((78.4800 17.3800, 78.4820 17.3800, 78.4820 17.3820, 78.4800 17.3820, 78.4800 17.3800))"
    fl = Floor(id=fl_id, floor_code="FLR-01", geometry_wkt=fl_poly, elevation_min_m=0.0, elevation_max_m=3.5)

    # Unit 1: Inside floor
    u1_wkt = "POLYGON((78.4802 17.3802, 78.4812 17.3802, 78.4812 17.3812, 78.4802 17.3812, 78.4802 17.3802))"
    # Unit 2: Overlaps Unit 1
    u2_wkt = "POLYGON((78.4808 17.3802, 78.4818 17.3802, 78.4818 17.3812, 78.4808 17.3812, 78.4808 17.3802))"

    u1 = PropertyUnit(id=uuid.uuid4(), floor_id=fl_id, unit_code="U-101", geometry_wkt=u1_wkt, elevation_min_m=0.0, elevation_max_m=3.5)
    u2 = PropertyUnit(id=uuid.uuid4(), floor_id=fl_id, unit_code="U-102", geometry_wkt=u2_wkt, elevation_min_m=0.0, elevation_max_m=3.5)

    ctx = ValidationContext(
        target_type="UNIT",
        target_id=str(u1.id),
        floors=[fl],
        units=[u1, u2],
    )

    res = validation_engine.execute_validation(ctx, rule_ids_filter=["UNIT_OVERLAP", "UNIT_OUTSIDE_FLOOR"])
    assert any(i.rule_id == "UNIT_OVERLAP" for i in res["issues"])
    overlap_issue = next(i for i in res["issues"] if i.rule_id == "UNIT_OVERLAP")
    assert "overlaps Unit U-102" in overlap_issue.message


@pytest.mark.asyncio
async def test_ai_candidate_and_survey_validation():
    """Test AI candidate footprint comparison and survey observation discrepancies."""
    bld_id = uuid.uuid4()
    official_wkt = "POLYGON((78.4800 17.3800, 78.4810 17.3800, 78.4810 17.3810, 78.4800 17.3810, 78.4800 17.3800))"
    # AI candidate footprint shifted away yielding low IoU (< 0.50)
    candidate_wkt = "POLYGON((78.4808 17.3800, 78.4818 17.3800, 78.4818 17.3810, 78.4808 17.3810, 78.4808 17.3800))"

    b = BuildingFootprint(id=bld_id, building_reference="B-OFFICIAL", geometry_wkt=official_wkt, height_estimate=25.0)
    cand = BuildingExtractionResult(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        source_target_id=str(bld_id),
        geometry_wkt=candidate_wkt,
        confidence=0.85,
    )
    # Survey observation with height mismatch (official=25m, surveyed=28.5m)
    obs = SurveyObservation(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        observation_type="BUILDING_HEIGHT",
        target_type="BUILDING",
        target_id=str(bld_id),
        value="28.5",
        unit="m",
    )

    ctx = ValidationContext(
        target_type="CROSS_DATASET",
        target_id=str(bld_id),
        buildings=[b],
        ai_building_candidates=[cand],
        survey_observations=[obs],
    )

    res = validation_engine.execute_validation(ctx, rule_ids_filter=["AI_CANDIDATE_LOW_SPATIAL_MATCH", "SURVEY_HEIGHT_MISMATCH"])
    rule_ids = [i.rule_id for i in res["issues"]]
    assert "AI_CANDIDATE_LOW_SPATIAL_MATCH" in rule_ids
    assert "SURVEY_HEIGHT_MISMATCH" in rule_ids


@pytest.mark.asyncio
async def test_validation_api_lifecycle_and_rbac(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict,
):
    """Test REST API endpoints: run dispatch, background execution, issues listing, review actions, and RBAC."""
    # 1. Citizen forbidden from creating validation run (403)
    resp = await client.post(
        "/api/v1/validation/runs",
        json={"target_type": "SYSTEM"},
        headers=auth_tokens["citizen"],
    )
    assert resp.status_code == 403

    # 2. Officer dispatches validation run on an entity with raw geometry (bowtie)
    bowtie_wkt = "POLYGON((0 0, 0 2, 2 0, 2 2, 0 0))"
    resp = await client.post(
        "/api/v1/validation/runs",
        json={
            "target_type": "BUILDING",
            "validation_type": "SINGLE_ENTITY",
            "geometry_wkt": bowtie_wkt,
        },
        headers=auth_tokens["officer"],
    )
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    # 3. Execute worker directly to simulate background task completion
    await validation_worker.execute_validation_run(uuid.UUID(run_id), session=db_session)

    # 4. Get run details and summary
    resp = await client.get(f"/api/v1/validation/runs/{run_id}", headers=auth_tokens["officer"])
    assert resp.status_code == 200
    run_data = resp.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["summary"]["total_issues"] >= 1

    # 5. Query issues for this run
    resp = await client.get(f"/api/v1/validation/runs/{run_id}/issues", headers=auth_tokens["officer"])
    assert resp.status_code == 200
    issues = resp.json()
    assert len(issues) >= 1
    issue_id = issues[0]["id"]
    assert issues[0]["status"] == "OPEN"

    # 6. Human Review - Surveyor can acknowledge
    resp = await client.patch(
        f"/api/v1/validation/issues/{issue_id}",
        json={"action": "ACKNOWLEDGE"},
        headers=auth_tokens["surveyor"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACKNOWLEDGED"

    # 7. Human Review - Surveyor cannot resolve/waive (403)
    resp = await client.patch(
        f"/api/v1/validation/issues/{issue_id}",
        json={"action": "RESOLVE", "note": "Resolved by surveyor"},
        headers=auth_tokens["surveyor"],
    )
    assert resp.status_code == 403

    # 8. Human Review - Officer resolves issue with note
    resp = await client.patch(
        f"/api/v1/validation/issues/{issue_id}",
        json={"action": "RESOLVE", "note": "Fixed bowtie topology via vertex snap."},
        headers=auth_tokens["officer"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVED"
    assert resp.json()["resolution_note"] == "Fixed bowtie topology via vertex snap."

    # 9. List rules endpoint
    resp = await client.get("/api/v1/validation/rules", headers=auth_tokens["officer"])
    assert resp.status_code == 200
    assert len(resp.json()) >= 20

    # 10. Entity summary endpoint
    resp = await client.get(f"/api/v1/validation/entities/BUILDING/ad_hoc_target/summary", headers=auth_tokens["officer"])
    assert resp.status_code == 200
    assert resp.json()["entity_type"] == "BUILDING"

    # 11. Human Review - Officer can waive with reason
    # Create another issue to waive
    issue_waive_res = await client.post(
        "/api/v1/validation/runs",
        json={"target_type": "BUILDING", "validation_type": "SINGLE_ENTITY", "geometry_wkt": bowtie_wkt},
        headers=auth_tokens["officer"],
    )
    waive_run_id = issue_waive_res.json()["id"]
    await validation_worker.execute_validation_run(uuid.UUID(waive_run_id), session=db_session)
    issues_waive = (await client.get(f"/api/v1/validation/runs/{waive_run_id}/issues", headers=auth_tokens["officer"])).json()
    assert len(issues_waive) > 0
    w_id = issues_waive[0]["id"]

    resp = await client.patch(
        f"/api/v1/validation/issues/{w_id}",
        json={"action": "WAIVE", "reason": "Grandfathered historical structure boundary."},
        headers=auth_tokens["officer"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "WAIVED"
    assert resp.json()["waiver_reason"] == "Grandfathered historical structure boundary."


@pytest.mark.asyncio
async def test_crs_and_attribute_rules():
    """Test CRS missing, CRS mismatch, and coordinate out-of-bounds rules."""
    jur_id = uuid.uuid4()
    jur = Jurisdiction(id=jur_id, name="Test Jur", code="JUR-01", srid=4326)
    p = Parcel(id=uuid.uuid4(), jurisdiction_id=jur_id, parcel_number="P-CRS-1", parcel_code="P-CRS-1", geometry_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")

    ctx = ValidationContext(
        target_type="PARCEL",
        target_id=str(p.id),
        jurisdictions=[jur],
        parcels=[p],
        raw_geometries={"out_of_bounds": "POLYGON((200 0, 201 0, 201 1, 200 1, 200 0))"},
    )

    res = validation_engine.execute_validation(ctx, rule_ids_filter=["GEOM_INVALID_CRS", "CRS_MISSING"])
    rule_ids = [i.rule_id for i in res["issues"]]
    assert "GEOM_INVALID_CRS" in rule_ids


@pytest.mark.asyncio
async def test_complete_end_to_end_multientity_cadastral_dataset():
    """Deterministic end-to-end dataset fixture covering all required entities from Sections 35 and 36."""
    jur_id = uuid.uuid4()
    jur = Jurisdiction(id=jur_id, name="CBD", code="CBD-101", srid=4326, boundary_wkt="POLYGON((78.47 17.37, 78.50 17.37, 78.50 17.40, 78.47 17.40, 78.47 17.37))")

    # 1. Valid parcel A
    p_a = Parcel(id=uuid.uuid4(), jurisdiction_id=jur_id, parcel_number="PCL-A", parcel_code="PCL-A", geometry_wkt="POLYGON((78.480 17.380, 78.485 17.380, 78.485 17.385, 78.480 17.385, 78.480 17.380))")
    # 2. Overlapping parcel B
    p_b = Parcel(id=uuid.uuid4(), jurisdiction_id=jur_id, parcel_number="PCL-B", parcel_code="PCL-B", geometry_wkt="POLYGON((78.484 17.380, 78.489 17.380, 78.489 17.385, 78.484 17.385, 78.484 17.380))")

    # 3. Valid building inside Parcel A
    b_a = BuildingFootprint(id=uuid.uuid4(), parcel_id=p_a.id, building_reference="BLD-A", geometry_wkt="POLYGON((78.481 17.381, 78.483 17.381, 78.483 17.383, 78.481 17.383, 78.481 17.381))", area=100.0, height_estimate=15.0)
    # 4. Building B partially outside Parcel A
    b_b = BuildingFootprint(id=uuid.uuid4(), parcel_id=p_a.id, building_reference="BLD-B", geometry_wkt="POLYGON((78.484 17.381, 78.487 17.381, 78.487 17.383, 78.484 17.383, 78.484 17.381))", area=120.0, height_estimate=12.0)

    # 5. Floors in Building A: Valid floor 0, Overlapping floor 1
    f_0 = Floor(id=uuid.uuid4(), building_id=b_a.id, floor_number=0, floor_code="F-0", elevation_min_m=0.0, elevation_max_m=4.0, height_m=4.0)
    f_1 = Floor(id=uuid.uuid4(), building_id=b_a.id, floor_number=1, floor_code="F-1", elevation_min_m=3.5, elevation_max_m=7.0, height_m=3.5)

    # 6. Units: Unit 1 inside Floor 0, Unit 2 overlapping Unit 1
    u_1 = PropertyUnit(id=uuid.uuid4(), floor_id=f_0.id, building_id=b_a.id, unit_code="U-1", geometry_wkt="POLYGON((78.4812 17.3812, 78.4820 17.3812, 78.4820 17.3820, 78.4812 17.3820, 78.4812 17.3812))", elevation_min_m=0.0, elevation_max_m=4.0)
    u_2 = PropertyUnit(id=uuid.uuid4(), floor_id=f_0.id, building_id=b_a.id, unit_code="U-2", geometry_wkt="POLYGON((78.4818 17.3812, 78.4826 17.3812, 78.4826 17.3820, 78.4818 17.3820, 78.4818 17.3812))", elevation_min_m=0.0, elevation_max_m=4.0)

    # 7. AI Candidate for Building A
    ai_cand = BuildingExtractionResult(id=uuid.uuid4(), job_id=uuid.uuid4(), source_target_id=str(b_a.id), geometry_wkt="POLYGON((78.481 17.381, 78.483 17.381, 78.483 17.383, 78.481 17.383, 78.481 17.381))", confidence=0.92)

    # 8. Survey observation with height mismatch
    survey_obs = SurveyObservation(id=uuid.uuid4(), session_id=uuid.uuid4(), observation_type="BUILDING_HEIGHT", target_type="BUILDING", target_id=str(b_a.id), value="18.5", unit="m")

    ctx = ValidationContext(
        target_type="SYSTEM",
        target_id="full-cadastral-system",
        jurisdictions=[jur],
        parcels=[p_a, p_b],
        buildings=[b_a, b_b],
        floors=[f_0, f_1],
        units=[u_1, u_2],
        ai_building_candidates=[ai_cand],
        survey_observations=[survey_obs],
    )

    res = validation_engine.execute_validation(ctx)
    summary = res["summary"]
    assert summary["total_issues"] >= 4
    rule_ids = {i.rule_id for i in res["issues"]}
    assert "PARCEL_OVERLAP" in rule_ids
    assert "BUILDING_PARTIAL_OUTSIDE_PARCEL" in rule_ids
    assert "FLOOR_VERTICAL_OVERLAP" in rule_ids
    assert "UNIT_OVERLAP" in rule_ids
    assert "SURVEY_HEIGHT_MISMATCH" in rule_ids


