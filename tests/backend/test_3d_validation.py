import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.gis.geometry_3d import Geometry3DEngine
from app.services.spatial_validation_service import spatial_validation_service


@pytest.mark.asyncio
async def test_3d_geometry_engine():
    wkt = "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))"
    height = 30.0

    extrusion = Geometry3DEngine.generate_cesium_extrusion(
        building_id="test-bld-1",
        building_reference="BLD-001",
        building_type="COMMERCIAL",
        status="ACTIVE",
        footprint_geom_input=wkt,
        height=height,
        height_source="SURVEY",
        height_confidence=0.95,
        height_unit="METERS",
        base_elevation=10.0,
        elevation_source="LOCAL_REFERENCE_PLANE",
        vertical_reference="METERS_ABOVE_GROUND",
    )

    assert extrusion["building_id"] == "test-bld-1"
    assert extrusion["height"] == 30.0
    assert extrusion["base_elevation"] == 10.0
    assert extrusion["extruded_height"] == 40.0
    assert extrusion["footprint_area_sq_m"] > 0
    assert extrusion["volume_cu_m"] > 0
    assert len(extrusion["rings"]) == 1
    assert len(extrusion["rings"][0]["exterior"]) >= 4  # at least 4 polygon vertices
    assert len(extrusion["bbox_3d"]) == 6
    assert extrusion["bbox_3d"][2] == 10.0  # minAlt
    assert extrusion["bbox_3d"][5] == 40.0  # maxAlt


@pytest.mark.asyncio
async def test_validate_building_3d_candidate(db_session: AsyncSession):
    # Valid candidate
    v1 = await spatial_validation_service.validate_building_3d_candidate(
        db=db_session,
        height=25.0,
        base_elevation=0.0,
        height_confidence=0.9,
    )
    assert v1.valid is True
    assert len(v1.errors) == 0

    # Negative height
    v2 = await spatial_validation_service.validate_building_3d_candidate(
        db=db_session,
        height=-5.0,
        base_elevation=0.0,
    )
    assert v2.valid is False
    codes = [e.code for e in v2.errors]
    assert "INVALID_BUILDING_HEIGHT" in codes

    # Invalid confidence (> 1.0) produces warning
    v3 = await spatial_validation_service.validate_building_3d_candidate(
        db=db_session,
        height=20.0,
        height_confidence=1.5,
    )
    assert len(v3.warnings) > 0
    w_codes = [w.code for w in v3.warnings]
    assert "INVALID_CONFIDENCE_SCORE" in w_codes

    # Extreme base elevation produces warning
    v4 = await spatial_validation_service.validate_building_3d_candidate(
        db=db_session,
        height=20.0,
        base_elevation=15000.0,
    )
    assert len(v4.warnings) > 0
    w_codes = [w.code for w in v4.warnings]
    assert "EXTREME_BASE_ELEVATION" in w_codes
