import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_officer_and_surveyor_can_create_parcel(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]

    # 1. Officer creates parcel
    res_officer = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-RBAC-OFF",
            "parcel_code": "GV-W500-OFF1",
            "geometry": "POLYGON((78.4810 17.3810, 78.4820 17.3810, 78.4820 17.3820, 78.4810 17.3820, 78.4810 17.3810))",
        },
        headers=auth_tokens["officer"],
    )
    assert res_officer.status_code == 201

    # 2. Surveyor creates parcel
    res_surveyor = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-RBAC-SURV",
            "parcel_code": "GV-W500-SURV1",
            "geometry": "POLYGON((78.4825 17.3810, 78.4835 17.3810, 78.4835 17.3820, 78.4825 17.3820, 78.4825 17.3810))",
        },
        headers=auth_tokens["surveyor"],
    )
    assert res_surveyor.status_code == 201


@pytest.mark.asyncio
async def test_citizen_forbidden_from_parcel_mutations(client: AsyncClient, seed_test_data, auth_tokens):
    jur = seed_test_data["jur"]
    cit_headers = auth_tokens["citizen"]
    off_headers = auth_tokens["officer"]

    # 1. Citizen CAN view parcels
    get_res = await client.get("/api/v1/parcels", headers=cit_headers)
    assert get_res.status_code == 200

    # 2. Citizen CAN view map parcels
    map_res = await client.get("/api/v1/map/parcels", headers=cit_headers)
    assert map_res.status_code == 200

    # 3. Citizen CANNOT create parcel (403 Forbidden)
    post_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-UNAUTH",
            "parcel_code": "GV-W500-UNAUTH",
            "geometry": "POLYGON((78.4850 17.3850, 78.4860 17.3850, 78.4860 17.3860, 78.4850 17.3860, 78.4850 17.3850))",
        },
        headers=cit_headers,
    )
    assert post_res.status_code == 403
    assert post_res.json()["error"]["code"] == "FORBIDDEN"

    # Officer creates a test parcel
    create_res = await client.post(
        "/api/v1/parcels",
        json={
            "jurisdiction_id": str(jur.id),
            "parcel_number": "P-PROTECTED",
            "parcel_code": "GV-W500-PROT",
            "geometry": "POLYGON((78.4850 17.3850, 78.4860 17.3850, 78.4860 17.3860, 78.4850 17.3860, 78.4850 17.3850))",
        },
        headers=off_headers,
    )
    parcel_id = create_res.json()["id"]

    # 4. Citizen CANNOT update parcel (403 Forbidden)
    patch_res = await client.patch(
        f"/api/v1/parcels/{parcel_id}",
        json={"land_use": "COMMERCIAL"},
        headers=cit_headers,
    )
    assert patch_res.status_code == 403

    # 5. Citizen CANNOT delete parcel (403 Forbidden)
    del_res = await client.delete(f"/api/v1/parcels/{parcel_id}", headers=cit_headers)
    assert del_res.status_code == 403

    # 6. Citizen CANNOT import GIS data (403 Forbidden)
    imp_res = await client.post(
        f"/api/v1/gis/import?jurisdiction_id={jur.id}",
        json={"type": "FeatureCollection", "features": []},
        headers=cit_headers,
    )
    assert imp_res.status_code == 403
