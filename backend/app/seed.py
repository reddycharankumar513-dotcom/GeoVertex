import asyncio
import uuid
from typing import Optional
from app.core.logging import logger
from app.core.security import get_password_hash
from app.database.base import Base
from app.database.session import AsyncSessionLocal, async_engine
from app.gis.geometry import GeometryEngine
from app.models.audit import AuditEvent
from app.models.building import BuildingFootprint
from app.models.jurisdiction import Jurisdiction
from app.models.organization import Organization
from app.models.parcel import Parcel
from app.models.property import Property
from app.models.user import User, UserRole
from app.models.floor import Floor
from app.models.unit import PropertyUnit
from app.repositories.building_repository import building_repository
from app.repositories.floor_repository import floor_repository
from app.repositories.organization_repository import organization_repository, jurisdiction_repository
from app.repositories.parcel_repository import parcel_repository
from app.repositories.property_repository import property_repository
from app.repositories.threed_repository import threed_repository
from app.repositories.unit_repository import unit_repository
from app.repositories.user_repository import user_repository
from shapely.geometry import box


DEMO_USERS = [
    {
        "email": "admin@geovertex.local",
        "username": "admin",
        "full_name": "System Administrator",
        "password": "GeoVertexAdmin2026!",
        "role": UserRole.ADMIN.value,
        "phone": "+919000000001",
    },
    {
        "email": "officer@geovertex.local",
        "username": "officer",
        "full_name": "Senior Cadastral Review Officer",
        "password": "GeoVertexOfficer2026!",
        "role": UserRole.GOVERNMENT_OFFICER.value,
        "phone": "+919000000002",
    },
    {
        "email": "surveyor@geovertex.local",
        "username": "surveyor",
        "full_name": "Licensed Field Surveyor",
        "password": "GeoVertexSurveyor2026!",
        "role": UserRole.SURVEYOR.value,
        "phone": "+919000000003",
    },
    {
        "email": "citizen@geovertex.local",
        "username": "citizen",
        "full_name": "Ananya Sharma (Citizen)",
        "password": "GeoVertexCitizen2026!",
        "role": UserRole.CITIZEN.value,
        "phone": "+919000000004",
    },
    {
        "email": "planner@geovertex.local",
        "username": "planner",
        "full_name": "Urban Planning Director",
        "password": "GeoVertexPlanner2026!",
        "role": UserRole.URBAN_PLANNER.value,
        "phone": "+919000000005",
    },
]

DEMO_JURISDICTIONS = [
    {
        "code": "JUR-W101",
        "name": "Pilot Ward 101 - Central Business District",
        "level": "WARD",
        "description": "Commercial and financial center with dense multi-storey land parcels",
        "srid": 4326,
        "boundary_wkt": "MULTIPOLYGON(((78.4850 17.3800, 78.4950 17.3800, 78.4950 17.3950, 78.4850 17.3950, 78.4850 17.3800)))",
    },
    {
        "code": "JUR-W102",
        "name": "Pilot Ward 102 - Cyber City Financial District",
        "level": "WARD",
        "description": "Modern IT corridor and high-rise commercial technology zone",
        "srid": 4326,
        "boundary_wkt": "MULTIPOLYGON(((78.4700 17.3800, 78.4840 17.3800, 78.4840 17.3950, 78.4700 17.3950, 78.4700 17.3800)))",
    },
]

DEMO_PARCELS = [
    # --- Ward 101 Parcels ---
    {
        "jur_code": "JUR-W101",
        "parcel_number": "P-101",
        "parcel_code": "GV-W101-P101",
        "survey_number": "SY-101/A",
        "subdivision_number": "1",
        "land_use": "COMMERCIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4860 17.3820, 78.4880 17.3820, 78.4880 17.3840, 78.4860 17.3840, 78.4860 17.3820))",
        "property": {
            "ref": "PROP-W101-001",
            "type": "FREEHOLD",
            "address": "101 High Street, Central Business District",
            "locality": "CBD Core",
            "postal_code": "500001",
            "description": "Multi-tenant prime commercial retail parcel",
        },
        "building": {
            "ref": "BLD-W101-001",
            "type": "COMMERCIAL",
            "height": 45.0,
            "wkt": "POLYGON((78.4863 17.3823, 78.4877 17.3823, 78.4877 17.3837, 78.4863 17.3837, 78.4863 17.3823))",
        },
    },
    {
        "jur_code": "JUR-W101",
        "parcel_number": "P-102",
        "parcel_code": "GV-W101-P102",
        "survey_number": "SY-101/B",
        "subdivision_number": "2",
        "land_use": "COMMERCIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4885 17.3820, 78.4905 17.3820, 78.4905 17.3840, 78.4885 17.3840, 78.4885 17.3820))",
        "property": {
            "ref": "PROP-W101-002",
            "type": "COMMERCIAL",
            "address": "102 High Street, Central Business District",
            "locality": "CBD Core",
            "postal_code": "500001",
            "description": "Corporate headquarters office tower",
        },
        "building": {
            "ref": "BLD-W101-002",
            "type": "COMMERCIAL",
            "height": 60.0,
            "wkt": "POLYGON((78.4888 17.3823, 78.4902 17.3823, 78.4902 17.3837, 78.4888 17.3837, 78.4888 17.3823))",
        },
    },
    {
        "jur_code": "JUR-W101",
        "parcel_number": "P-103",
        "parcel_code": "GV-W101-P103",
        "survey_number": "SY-102/1",
        "subdivision_number": "1",
        "land_use": "MIXED",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4910 17.3820, 78.4930 17.3820, 78.4930 17.3840, 78.4910 17.3840, 78.4910 17.3820))",
        "property": {
            "ref": "PROP-W101-003",
            "type": "FREEHOLD",
            "address": "103 High Street, Central Business District",
            "locality": "CBD East",
            "postal_code": "500001",
            "description": "Mixed commercial retail and residential apartments",
        },
        "building": {
            "ref": "BLD-W101-003",
            "type": "MIXED_USE",
            "height": 38.0,
            "wkt": "POLYGON((78.4913 17.3823, 78.4927 17.3823, 78.4927 17.3837, 78.4913 17.3837, 78.4913 17.3823))",
        },
    },
    {
        "jur_code": "JUR-W101",
        "parcel_number": "P-104",
        "parcel_code": "GV-W101-P104",
        "survey_number": "SY-103/A",
        "subdivision_number": "1",
        "land_use": "RESIDENTIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4860 17.3850, 78.4880 17.3850, 78.4880 17.3870, 78.4860 17.3870, 78.4860 17.3850))",
        "property": {
            "ref": "PROP-W101-004",
            "type": "RESIDENTIAL",
            "address": "201 Market Square, Central Business District",
            "locality": "CBD Residential Sector",
            "postal_code": "500001",
            "description": "Multi-family residential complex",
        },
        "building": {
            "ref": "BLD-W101-004",
            "type": "RESIDENTIAL",
            "height": 28.0,
            "wkt": "POLYGON((78.4863 17.3853, 78.4877 17.3853, 78.4877 17.3867, 78.4863 17.3867, 78.4863 17.3853))",
        },
    },
    {
        "jur_code": "JUR-W101",
        "parcel_number": "P-105",
        "parcel_code": "GV-W101-P105",
        "survey_number": "SY-103/B",
        "subdivision_number": "2",
        "land_use": "RESIDENTIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4885 17.3850, 78.4905 17.3850, 78.4905 17.3870, 78.4885 17.3870, 78.4885 17.3850))",
        "property": {
            "ref": "PROP-W101-005",
            "type": "RESIDENTIAL",
            "address": "202 Market Square, Central Business District",
            "locality": "CBD Residential Sector",
            "postal_code": "500001",
            "description": "Residential condominiums",
        },
        "building": {
            "ref": "BLD-W101-005",
            "type": "RESIDENTIAL",
            "height": 32.0,
            "wkt": "POLYGON((78.4888 17.3853, 78.4902 17.3853, 78.4902 17.3867, 78.4888 17.3867, 78.4888 17.3853))",
        },
    },
    {
        "jur_code": "JUR-W101",
        "parcel_number": "P-106",
        "parcel_code": "GV-W101-P106",
        "survey_number": "SY-104/1",
        "subdivision_number": None,
        "land_use": "PUBLIC",
        "status": "ACTIVE",
        "ownership_status": "MUNICIPAL",
        "wkt": "POLYGON((78.4910 17.3850, 78.4930 17.3850, 78.4930 17.3870, 78.4910 17.3870, 78.4910 17.3850))",
    },
    {
        "jur_code": "JUR-W101",
        "parcel_number": "P-107",
        "parcel_code": "GV-W101-P107",
        "survey_number": "SY-105/A",
        "subdivision_number": "1",
        "land_use": "COMMERCIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4860 17.3880, 78.4880 17.3880, 78.4880 17.3900, 78.4860 17.3900, 78.4860 17.3880))",
    },
    {
        "jur_code": "JUR-W101",
        "parcel_number": "P-108",
        "parcel_code": "GV-W101-P108",
        "survey_number": "SY-105/B",
        "subdivision_number": "2",
        "land_use": "COMMERCIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4885 17.3880, 78.4905 17.3880, 78.4905 17.3900, 78.4885 17.3900, 78.4885 17.3880))",
    },
    # --- Ward 102 Parcels (Cyber City) ---
    {
        "jur_code": "JUR-W102",
        "parcel_number": "P-201",
        "parcel_code": "GV-W102-P201",
        "survey_number": "SY-201/1",
        "subdivision_number": "A",
        "land_use": "COMMERCIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4720 17.3820, 78.4740 17.3820, 78.4740 17.3840, 78.4720 17.3840, 78.4720 17.3820))",
        "property": {
            "ref": "PROP-W102-001",
            "type": "FREEHOLD",
            "address": "1 Innovation Way, Cyber City",
            "locality": "Tech Park Phase 1",
            "postal_code": "500081",
            "description": "Cyber Gateway Software Campus",
        },
        "building": {
            "ref": "BLD-W102-001",
            "type": "COMMERCIAL",
            "height": 52.0,
            "wkt": "POLYGON((78.4723 17.3823, 78.4737 17.3823, 78.4737 17.3837, 78.4723 17.3837, 78.4723 17.3823))",
        },
    },
    {
        "jur_code": "JUR-W102",
        "parcel_number": "P-202",
        "parcel_code": "GV-W102-P202",
        "survey_number": "SY-201/2",
        "subdivision_number": "B",
        "land_use": "COMMERCIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4745 17.3820, 78.4765 17.3820, 78.4765 17.3840, 78.4745 17.3840, 78.4745 17.3820))",
        "property": {
            "ref": "PROP-W102-002",
            "type": "COMMERCIAL",
            "address": "2 Innovation Way, Cyber City",
            "locality": "Tech Park Phase 1",
            "postal_code": "500081",
            "description": "Cloud Infrastructure Data Center & Offices",
        },
        "building": {
            "ref": "BLD-W102-002",
            "type": "COMMERCIAL",
            "height": 40.0,
            "wkt": "POLYGON((78.4748 17.3823, 78.4762 17.3823, 78.4762 17.3837, 78.4748 17.3837, 78.4748 17.3823))",
        },
    },
    {
        "jur_code": "JUR-W102",
        "parcel_number": "P-203",
        "parcel_code": "GV-W102-P203",
        "survey_number": "SY-202/A",
        "subdivision_number": "1",
        "land_use": "MIXED",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4770 17.3820, 78.4790 17.3820, 78.4790 17.3840, 78.4770 17.3840, 78.4770 17.3820))",
        "property": {
            "ref": "PROP-W102-003",
            "type": "LEASEHOLD",
            "address": "3 Innovation Way, Cyber City",
            "locality": "Tech Park Phase 2",
            "postal_code": "500081",
            "description": "Tech Incubator and Service Apartments",
        },
        "building": {
            "ref": "BLD-W102-003",
            "type": "MIXED_USE",
            "height": 48.0,
            "wkt": "POLYGON((78.4773 17.3823, 78.4787 17.3823, 78.4787 17.3837, 78.4773 17.3837, 78.4773 17.3823))",
        },
    },
    {
        "jur_code": "JUR-W102",
        "parcel_number": "P-204",
        "parcel_code": "GV-W102-P204",
        "survey_number": "SY-203/1",
        "subdivision_number": None,
        "land_use": "INDUSTRIAL",
        "status": "ACTIVE",
        "ownership_status": "RECORDED",
        "wkt": "POLYGON((78.4720 17.3850, 78.4740 17.3850, 78.4740 17.3870, 78.4720 17.3870, 78.4720 17.3850))",
    },
]


async def seed_database():
    logger.info("Initializing database schema for seeding...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Seed Demo Organization
        org = await organization_repository.get_by_code(db, "SDLR-HQ")
        if not org:
            org = Organization(
                name="State Department of Land Records & Cadastre",
                code="SDLR-HQ",
                type="STATE_DEPARTMENT",
                is_active=True,
            )
            org = await organization_repository.create(db, org)
            logger.info(f"Seeded Organization: {org.name} [{org.code}]")
        else:
            logger.info(f"Organization exists: {org.name}")

        # 2. Seed Demo Jurisdictions
        jur_map = {}
        for jur_data in DEMO_JURISDICTIONS:
            jur = await jurisdiction_repository.get_by_code(db, jur_data["code"])
            if not jur:
                jur = Jurisdiction(
                    organization_id=org.id,
                    name=jur_data["name"],
                    code=jur_data["code"],
                    level=jur_data["level"],
                    description=jur_data["description"],
                    srid=jur_data["srid"],
                    boundary=jur_data["boundary_wkt"],
                    boundary_wkt=jur_data["boundary_wkt"],
                    is_active=True,
                )
                jur = await jurisdiction_repository.create(db, jur)
                logger.info(f"Seeded Jurisdiction: {jur.name} [{jur.code}]")
            else:
                logger.info(f"Jurisdiction exists: {jur.name}")
            jur_map[jur_data["code"]] = jur

        # 3. Seed Demo Users
        for user_data in DEMO_USERS:
            existing = await user_repository.get_by_email(db, user_data["email"])
            if not existing:
                user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    phone=user_data["phone"],
                    password_hash=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    organization_id=org.id if user_data["role"] in [UserRole.ADMIN.value, UserRole.GOVERNMENT_OFFICER.value] else None,
                    jurisdiction_id=jur_map["JUR-W101"].id if user_data["role"] in [UserRole.SURVEYOR.value, UserRole.GOVERNMENT_OFFICER.value] else None,
                    is_active=True,
                    is_verified=True,
                )
                created = await user_repository.create(db, user)
                logger.info(f"Seeded User: {created.email} [{created.role}]")
            else:
                logger.info(f"User exists: {existing.email} [{existing.role}]")

        # 4. Seed Phase 2 Cadastral Parcels, Properties, and Building Footprints
        for p_data in DEMO_PARCELS:
            jur = jur_map.get(p_data["jur_code"])
            if not jur:
                continue

            existing_parcel = await parcel_repository.get_by_code(db, p_data["parcel_code"])
            if not existing_parcel:
                parsed_geom = GeometryEngine.parse_geometry(p_data["wkt"])
                area_m2 = GeometryEngine.calculate_geodesic_area(parsed_geom)
                c_lon, c_lat = GeometryEngine.calculate_centroid(parsed_geom)

                parcel = Parcel(
                    jurisdiction_id=jur.id,
                    parcel_number=p_data["parcel_number"],
                    parcel_code=p_data["parcel_code"],
                    survey_number=p_data.get("survey_number"),
                    subdivision_number=p_data.get("subdivision_number"),
                    land_use=p_data["land_use"],
                    area=area_m2,
                    area_unit="SQ_METER",
                    status=p_data["status"],
                    ownership_status=p_data["ownership_status"],
                    geometry=p_data["wkt"],
                    geometry_wkt=p_data["wkt"],
                    centroid_lon=c_lon,
                    centroid_lat=c_lat,
                    source="DEVELOPMENT_SEED_DATA",
                    source_reference="CADASTRAL-SURVEY-DEMO-2026",
                )
                parcel = await parcel_repository.create(db, parcel)
                logger.info(f"Seeded Parcel: {parcel.parcel_code} ({area_m2} sq m)")

                # Seed associated Property if configured
                prop_data = p_data.get("property")
                if prop_data:
                    existing_prop = await property_repository.get_by_reference(db, prop_data["ref"])
                    if not existing_prop:
                        prop = Property(
                            parcel_id=parcel.id,
                            property_reference=prop_data["ref"],
                            property_type=prop_data["type"],
                            status="ACTIVE",
                            address=prop_data["address"],
                            locality=prop_data.get("locality"),
                            postal_code=prop_data.get("postal_code"),
                            description=prop_data.get("description"),
                        )
                        prop = await property_repository.create(db, prop)
                        logger.info(f"  +-- Seeded Property: {prop.property_reference}")

                # Seed associated Building Footprint if configured
                bld_data = p_data.get("building")
                if bld_data:
                    existing_bld = await building_repository.get_by_reference(db, bld_data["ref"])
                    if not existing_bld:
                        b_parsed = GeometryEngine.parse_geometry(bld_data["wkt"])
                        b_area = GeometryEngine.calculate_geodesic_area(b_parsed)
                        bld = BuildingFootprint(
                            parcel_id=parcel.id,
                            building_reference=bld_data["ref"],
                            building_type=bld_data["type"],
                            status="EXISTING",
                            area=b_area,
                            height_estimate=bld_data.get("height"),
                            geometry=bld_data["wkt"],
                            geometry_wkt=bld_data["wkt"],
                            source="DEVELOPMENT_SEED_DATA",
                            source_reference="FIELD-SURVEY-DEMO-2026",
                        )
                        bld = await building_repository.create(db, bld)
                        logger.info(f"  +-- Seeded Building: {bld.building_reference} ({b_area} sq m)")
                    else:
                        bld = existing_bld

                    # Seed Phase 3 3D Representation
                    rep_3d = await threed_repository.save_representation(
                        db=db,
                        building_id=bld.id,
                        height=bld.height_estimate or 18.0,
                        height_source="SURVEY" if bld.height_estimate else "ESTIMATED",
                        height_confidence=0.92 if bld.height_estimate else 0.70,
                        height_unit="METERS",
                        base_elevation=0.0,
                        elevation_source="LOCAL_REFERENCE_PLANE",
                        vertical_reference="METERS_ABOVE_GROUND",
                        geometry_type="EXTRUSION",
                        model_source="EXTRUDED_FOOTPRINT",
                        status="ACTIVE",
                    )
                    logger.info(f"    +-- Seeded 3D Extrusion: {rep_3d.height}m ({rep_3d.height_source})")

                    # Seed Phase 4 Floors & Units
                    await seed_floors_and_units_for_building(db, bld, property_obj.id if property_obj else None)
            else:
                logger.info(f"Parcel exists: {existing_parcel.parcel_code}")
                # Ensure existing buildings have 3D representations, floors, and units
                bld_data = p_data.get("building")
                if bld_data:
                    existing_bld = await building_repository.get_by_reference(db, bld_data["ref"])
                    if existing_bld:
                        rep_3d = await threed_repository.save_representation(
                            db=db,
                            building_id=existing_bld.id,
                            height=existing_bld.height_estimate or 18.0,
                            height_source="SURVEY" if existing_bld.height_estimate else "ESTIMATED",
                            height_confidence=0.92 if existing_bld.height_estimate else 0.70,
                            height_unit="METERS",
                            base_elevation=0.0,
                            elevation_source="LOCAL_REFERENCE_PLANE",
                            vertical_reference="METERS_ABOVE_GROUND",
                            geometry_type="EXTRUSION",
                            model_source="EXTRUDED_FOOTPRINT",
                            status="ACTIVE",
                        )
                        logger.info(f"    +-- Verified 3D Extrusion: {existing_bld.building_reference} -> {rep_3d.height}m")

                        # Seed Phase 4 Floors & Units
                        prop = await property_repository.get_by_reference(db, p_data.get("property", {}).get("ref", ""))
                        await seed_floors_and_units_for_building(db, existing_bld, prop.id if prop else None)

        await db.commit()
    logger.info("Database seeding completed successfully with Phase 2 Cadastre, Phase 3 3D Twin & Phase 4 Floor/Unit Data!")


async def seed_floors_and_units_for_building(db, building: BuildingFootprint, property_id: Optional[uuid.UUID] = None):
    """Seed authoritative multi-level floor stack and subdivided property units for a building."""
    if not building.geometry_wkt:
        return

    b_geom = GeometryEngine.parse_geometry(building.geometry_wkt)
    min_x, min_y, max_x, max_y = b_geom.bounds
    mid_x = (min_x + max_x) / 2.0

    # East and West sub-boxes for disjoint unit geometries
    west_box = box(min_x, min_y, mid_x, max_y)
    east_box = box(mid_x, min_y, max_x, max_y)

    u1_geom = b_geom.intersection(west_box)
    u2_geom = b_geom.intersection(east_box)

    u1_wkt = GeometryEngine.to_wkt(u1_geom) if not u1_geom.is_empty else building.geometry_wkt
    u2_wkt = GeometryEngine.to_wkt(u2_geom) if not u2_geom.is_empty else building.geometry_wkt

    u1_area = GeometryEngine.calculate_geodesic_area(u1_geom) if not u1_geom.is_empty else 100.0
    u2_area = GeometryEngine.calculate_geodesic_area(u2_geom) if not u2_geom.is_empty else 100.0

    floor_configs = [
        {"num": 0, "name": "Ground Floor", "type": "COMMERCIAL", "elev_min": 0.0, "elev_max": 4.0, "u_type": "RETAIL"},
        {"num": 1, "name": "Level 1", "type": "COMMERCIAL", "elev_min": 4.0, "elev_max": 7.5, "u_type": "OFFICE"},
        {"num": 2, "name": "Level 2", "type": "COMMERCIAL", "elev_min": 7.5, "elev_max": 11.0, "u_type": "OFFICE"},
        {"num": 3, "name": "Level 3", "type": "RESIDENTIAL", "elev_min": 11.0, "elev_max": 15.0, "u_type": "APARTMENT"},
    ]

    for fc in floor_configs:
        f_code = f"{building.building_reference}-F{fc['num']}"
        existing_floor = await floor_repository.get_by_code(db, f_code)
        if not existing_floor:
            f_data = {
                "building_id": building.id,
                "floor_number": fc["num"],
                "floor_code": f_code,
                "floor_name": fc["name"],
                "floor_type": fc["type"],
                "elevation_min_m": fc["elev_min"],
                "elevation_max_m": fc["elev_max"],
                "height_m": round(fc["elev_max"] - fc["elev_min"], 2),
                "area_sqm": building.area,
                "geometry": building.geometry_wkt,
                "geometry_wkt": building.geometry_wkt,
                "confidence": 1.0,
                "status": "ACTIVE",
                "source": "DEVELOPMENT_SEED_DATA",
            }
            floor = await floor_repository.create(db, f_data)
            logger.info(f"      +-- Seeded Floor: {floor.floor_code} ({floor.height_m}m)")
        else:
            floor = existing_floor

        # Seed 2 units per floor
        u1_code = f"{f_code}-U{fc['num']}01"
        existing_u1 = await unit_repository.get_by_code(db, u1_code)
        if not existing_u1:
            u1_data = {
                "floor_id": floor.id,
                "building_id": building.id,
                "property_id": property_id,
                "unit_number": f"{fc['num']}01",
                "unit_code": u1_code,
                "unit_type": fc["u_type"],
                "gross_area_sqm": u1_area,
                "net_area_sqm": round(u1_area * 0.85, 2),
                "elevation_min_m": fc["elev_min"],
                "elevation_max_m": fc["elev_max"],
                "height_m": round(fc["elev_max"] - fc["elev_min"], 2),
                "geometry": u1_wkt,
                "geometry_wkt": u1_wkt,
                "status": "ACTIVE",
                "ownership_status": "PRIVATE",
            }
            await unit_repository.create(db, u1_data)

        u2_code = f"{f_code}-U{fc['num']}02"
        existing_u2 = await unit_repository.get_by_code(db, u2_code)
        if not existing_u2:
            u2_data = {
                "floor_id": floor.id,
                "building_id": building.id,
                "property_id": property_id,
                "unit_number": f"{fc['num']}02",
                "unit_code": u2_code,
                "unit_type": fc["u_type"],
                "gross_area_sqm": u2_area,
                "net_area_sqm": round(u2_area * 0.85, 2),
                "elevation_min_m": fc["elev_min"],
                "elevation_max_m": fc["elev_max"],
                "height_m": round(fc["elev_max"] - fc["elev_min"], 2),
                "geometry": u2_wkt,
                "geometry_wkt": u2_wkt,
                "status": "ACTIVE",
                "ownership_status": "PRIVATE",
            }
            await unit_repository.create(db, u2_data)


if __name__ == "__main__":
    asyncio.run(seed_database())
