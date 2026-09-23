import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_gis_import_valid_geojson(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    geojson_payload = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [78.4810, 17.3810],
                            [78.4820, 17.3810],
                            [78.4820, 17.3820],
                            [78.4810, 17.3820],
                            [78.4810, 17.3810],
                        ]
                    ],
                },
                "properties": {
                    "parcel_number": "P-IMP-01",
                    "land_use": "COMMERCIAL",
                },
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [78.4825, 17.3810],
                            [78.4835, 17.3810],
                            [78.4835, 17.3820],
                            [78.4825, 17.3820],
                            [78.4825, 17.3810],
                        ]
                    ],
                },
                "properties": {
                    "parcel_number": "P-IMP-02",
                    "land_use": "RESIDENTIAL",
                },
            },
        ],
    }

    res = await client.post(
        f"/api/v1/gis/import?jurisdiction_id={jur.id}",
        json=geojson_payload,
        headers=headers,
    )
    assert res.status_code == 200, f"Import failed: {res.text}"
    summary = res.json()
    assert summary["records_received"] == 2
    assert summary["records_accepted"] == 2
    assert summary["records_rejected"] == 0


@pytest.mark.asyncio
async def test_gis_import_with_invalid_and_duplicate_features(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    geojson_payload = {
        "type": "FeatureCollection",
        "features": [
            # 1. Valid feature
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [78.4840, 17.3810],
                            [78.4850, 17.3810],
                            [78.4850, 17.3820],
                            [78.4840, 17.3820],
                            [78.4840, 17.3810],
                        ]
                    ],
                },
                "properties": {"parcel_number": "P-MIX-01"},
            },
            # 2. Self-intersecting invalid geometry
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [78.4855, 17.3810],
                            [78.4865, 17.3820],
                            [78.4865, 17.3810],
                            [78.4855, 17.3820],
                            [78.4855, 17.3810],
                        ]
                    ],
                },
                "properties": {"parcel_number": "P-MIX-02"},
            },
            # 3. Duplicate of feature 1 in same batch
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [78.4870, 17.3810],
                            [78.4880, 17.3810],
                            [78.4880, 17.3820],
                            [78.4870, 17.3820],
                            [78.4870, 17.3810],
                        ]
                    ],
                },
                "properties": {"parcel_number": "P-MIX-01"},  # duplicate
            },
        ],
    }

    res = await client.post(
        f"/api/v1/gis/import?jurisdiction_id={jur.id}",
        json=geojson_payload,
        headers=headers,
    )
    assert res.status_code == 200
    summary = res.json()
    assert summary["records_received"] == 3
    assert summary["records_accepted"] == 1
    assert summary["records_rejected"] == 2
    assert len(summary["errors"]) == 2


@pytest.mark.asyncio
async def test_gis_export_geojson(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    headers = auth_tokens["officer"]

    # Create parcel to export
    await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-EXP-1",
            "parcel_code": "GV-W500-PEXP1",
            "geometry": "POLYGON((78.4850 17.3850, 78.4860 17.3850, 78.4860 17.3860, 78.4850 17.3860, 78.4850 17.3850))",
        },
        headers=headers,
    )

    # Export by jurisdiction
    exp_res = await client.get(
        f"/api/v1/gis/export?jurisdiction_id={jur.id}",
        headers=auth_tokens["citizen"],
    )
    assert exp_res.status_code == 200
    fc = exp_res.json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 1
    codes = [f["properties"]["parcel_code"] for f in fc["features"]]
    assert "GV-W500-PEXP1" in codes
