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
from app.models.survey import (
    SurveyProject,
    SurveyAssignment,
    SurveySession,
    SurveyObservation,
    SurveyEvidence,
    SurveySubmission,
)
from app.repositories.survey_repository import (
    survey_project_repository,
    survey_assignment_repository,
    survey_session_repository,
    survey_observation_repository,
    survey_evidence_repository,
    survey_submission_repository,
)
from datetime import datetime, timezone
import json
from shapely.geometry import box
from app.models.workflow import (
    ServiceType,
    CitizenPropertyLink,
    ServiceRequest,
    ServiceRequestEvent,
    WorkflowTask,
    RequestStatus,
    RequestPriority,
    TaskType,
    TaskStatus,
)
# Phase 12 — Technical 3D Identifier Engine
from app.models.identifier import IdentifierScheme
# Phase 13 — Audit, Versioning, Notifications & Governance
from app.models.versioning import EntityVersion, VersionStatus, VersionChangeType, VersionSourceType
from app.models.notification_preference import NotificationPreference
from app.models.workflow import Notification
from app.models.audit import AuditEvent, AuditCategory, AuditSeverity, AuditResult
from sqlalchemy import select as _select


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

        # 7. Seed Phase 5: Surveyor Field Workflow Demo Data
        logger.info("\n--- Seeding Phase 5: Surveyor Field Workflow Demo Data ---")
        surveyor_user = await user_repository.get_by_email(db, "surveyor@geovertex.local")
        officer_user = await user_repository.get_by_email(db, "officer@geovertex.local")

        if surveyor_user and officer_user:
            # 7a. Survey Projects
            project_configs = [
                {
                    "name": "Central Business District Cadastral Audit 2026",
                    "code": "PRJ-2026-CBD-AUDIT",
                    "description": "Annual cadastral survey and vertical height audit for Ward 101 commercial properties.",
                    "organization_id": org.id,
                    "jurisdiction_id": jur_map["JUR-W101"].id,
                    "status": "ACTIVE",
                    "start_date": datetime.now(timezone.utc),
                },
                {
                    "name": "Cyber City Vertical Expansion & Height Verification",
                    "code": "PRJ-2026-CYBER-EXT",
                    "description": "Field verification of high-rise IT corridor parcel boundaries and 3D structural heights.",
                    "organization_id": org.id,
                    "jurisdiction_id": jur_map["JUR-W102"].id,
                    "status": "ACTIVE",
                    "start_date": datetime.now(timezone.utc),
                },
            ]

            projects = {}
            for prj_cfg in project_configs:
                existing_prj = await survey_project_repository.get_by_code(db, prj_cfg["code"])
                if not existing_prj:
                    prj_data = {**prj_cfg, "created_by": officer_user.id}
                    created_prj = await survey_project_repository.create(db, prj_data)
                    projects[prj_cfg["code"]] = created_prj
                    logger.info(f"  +-- Seeded Survey Project: {created_prj.name} [{created_prj.code}]")
                else:
                    projects[prj_cfg["code"]] = existing_prj

            p101 = await parcel_repository.get_by_code(db, "GV-W101-P101")
            bld101 = await building_repository.get_by_reference(db, "BLD-W101-001")
            p102 = await parcel_repository.get_by_code(db, "GV-W101-P102")
            bld102 = await building_repository.get_by_reference(db, "BLD-W101-002")
            p104 = await parcel_repository.get_by_code(db, "GV-W102-P104")
            bld104 = await building_repository.get_by_reference(db, "BLD-W102-001")
            p105 = await parcel_repository.get_by_code(db, "GV-W102-P105")

            # 7b. Survey Assignment 1: ASSIGNED (Urgent peg audit)
            if "PRJ-2026-CBD-AUDIT" in projects and p101:
                asgn1_data = {
                    "survey_project_id": projects["PRJ-2026-CBD-AUDIT"].id,
                    "surveyor_id": surveyor_user.id,
                    "jurisdiction_id": jur_map["JUR-W101"].id,
                    "parcel_id": p101.id,
                    "priority": "URGENT",
                    "status": "ASSIGNED",
                    "notes": "DEMO DATA: Initial field survey dispatch for boundary peg audit.",
                }
                asgn1 = await survey_assignment_repository.create(db, asgn1_data)
                logger.info(f"  +-- Seeded Assignment 1 (ASSIGNED): {asgn1.id}")

            # 7c. Survey Assignment 2: IN_PROGRESS (Session active with measurements)
            if "PRJ-2026-CBD-AUDIT" in projects and bld101 and p101:
                asgn2_data = {
                    "survey_project_id": projects["PRJ-2026-CBD-AUDIT"].id,
                    "surveyor_id": surveyor_user.id,
                    "jurisdiction_id": jur_map["JUR-W101"].id,
                    "parcel_id": p101.id,
                    "building_id": bld101.id,
                    "priority": "HIGH",
                    "status": "IN_PROGRESS",
                    "started_at": datetime.now(timezone.utc),
                    "notes": "DEMO DATA: Active field survey session underway. Surveyor on-site.",
                }
                asgn2 = await survey_assignment_repository.create(db, asgn2_data)
                sess2 = await survey_session_repository.create(db, {
                    "assignment_id": asgn2.id,
                    "surveyor_id": surveyor_user.id,
                    "status": "ACTIVE",
                    "started_at": datetime.now(timezone.utc),
                    "sync_status": "SYNCED",
                })
                await survey_observation_repository.create(db, {
                    "session_id": sess2.id,
                    "observation_type": "BUILDING_HEIGHT",
                    "target_type": "BUILDING",
                    "target_id": str(bld101.id),
                    "value": "15.5",
                    "unit": "m",
                    "latitude": 17.3820,
                    "longitude": 78.4870,
                    "horizontal_accuracy": 3.5,
                    "source": "GPS",
                    "captured_by": surveyor_user.id,
                })
                await survey_observation_repository.create(db, {
                    "session_id": sess2.id,
                    "observation_type": "FLOOR_COUNT",
                    "target_type": "BUILDING",
                    "target_id": str(bld101.id),
                    "value": "4",
                    "unit": "floors",
                    "latitude": 17.3820,
                    "longitude": 78.4870,
                    "horizontal_accuracy": 3.5,
                    "source": "GPS",
                    "captured_by": surveyor_user.id,
                })
                await survey_evidence_repository.create(db, {
                    "session_id": sess2.id,
                    "target_type": "BUILDING",
                    "target_id": str(bld101.id),
                    "filename": "demo_facade_north.jpg",
                    "mime_type": "image/jpeg",
                    "file_size": 2048576,
                    "evidence_type": "BUILDING_FACADE",
                    "sha256_hash": "a3b1c2d3e4f5061728394a5b6c7d8e9f0123456789abcdef0123456789abcdef",
                    "storage_key": "uploads/evidence/demo_facade_north.jpg",
                    "latitude": 17.3820,
                    "longitude": 78.4870,
                    "accuracy": 3.5,
                    "description": "DEMO DATA: North facade elevation capture",
                })
                logger.info(f"  +-- Seeded Assignment 2 (IN_PROGRESS): {asgn2.id}")

            # 7d. Survey Assignment 3: SUBMITTED (Ready for Officer Review)
            if "PRJ-2026-CBD-AUDIT" in projects and bld102 and p102:
                asgn3_data = {
                    "survey_project_id": projects["PRJ-2026-CBD-AUDIT"].id,
                    "surveyor_id": surveyor_user.id,
                    "jurisdiction_id": jur_map["JUR-W101"].id,
                    "parcel_id": p102.id,
                    "building_id": bld102.id,
                    "priority": "MEDIUM",
                    "status": "SUBMITTED",
                    "started_at": datetime.now(timezone.utc),
                    "notes": "DEMO DATA: Field data collection completed and submitted for officer review.",
                }
                asgn3 = await survey_assignment_repository.create(db, asgn3_data)
                sess3 = await survey_session_repository.create(db, {
                    "assignment_id": asgn3.id,
                    "surveyor_id": surveyor_user.id,
                    "status": "SUBMITTED",
                    "started_at": datetime.now(timezone.utc),
                    "ended_at": datetime.now(timezone.utc),
                    "sync_status": "SYNCED",
                })
                obs3_1 = await survey_observation_repository.create(db, {
                    "session_id": sess3.id,
                    "observation_type": "BUILDING_HEIGHT",
                    "target_type": "BUILDING",
                    "target_id": str(bld102.id),
                    "value": "28.0",
                    "unit": "m",
                    "latitude": 17.3860,
                    "longitude": 78.4890,
                    "horizontal_accuracy": 4.0,
                    "source": "GPS",
                    "captured_by": surveyor_user.id,
                })
                obs3_2 = await survey_observation_repository.create(db, {
                    "session_id": sess3.id,
                    "observation_type": "FLOOR_COUNT",
                    "target_type": "BUILDING",
                    "target_id": str(bld102.id),
                    "value": "8",
                    "unit": "floors",
                    "latitude": 17.3860,
                    "longitude": 78.4890,
                    "horizontal_accuracy": 4.0,
                    "source": "GPS",
                    "captured_by": surveyor_user.id,
                })
                ev3 = await survey_evidence_repository.create(db, {
                    "session_id": sess3.id,
                    "target_type": "BUILDING",
                    "target_id": str(bld102.id),
                    "filename": "demo_tower_elevation.jpg",
                    "mime_type": "image/jpeg",
                    "file_size": 3145728,
                    "evidence_type": "BUILDING_FACADE",
                    "sha256_hash": "b4c2d3e4f5061728394a5b6c7d8e9f0123456789abcdef0123456789abcdef01",
                    "storage_key": "uploads/evidence/demo_tower_elevation.jpg",
                    "latitude": 17.3860,
                    "longitude": 78.4890,
                    "accuracy": 4.0,
                    "description": "DEMO DATA: Front elevation and entrance gate",
                })
                snapshot_data = {
                    "assignment_id": str(asgn3.id),
                    "session_id": str(sess3.id),
                    "version_number": 1,
                    "observations": [
                        {"id": str(obs3_1.id), "observation_type": "BUILDING_HEIGHT", "value": "28.0", "unit": "m"},
                        {"id": str(obs3_2.id), "observation_type": "FLOOR_COUNT", "value": "8", "unit": "floors"},
                    ],
                    "evidence": [
                        {"id": str(ev3.id), "evidence_type": "BUILDING_FACADE", "sha256_hash": ev3.sha256_hash},
                    ],
                    "validation_summary": {
                        "is_valid": True,
                        "can_submit": True,
                        "comparisons": [
                            {
                                "property": "Building Height",
                                "official_value": "28.0 m",
                                "survey_value": "28.0 m",
                                "difference": "0.0 m",
                                "status": "MATCH",
                            },
                            {
                                "property": "Floor Count",
                                "official_value": "8",
                                "survey_value": "8",
                                "difference": "0",
                                "status": "MATCH",
                            },
                        ],
                    },
                }
                sub3 = await survey_submission_repository.create(db, {
                    "assignment_id": asgn3.id,
                    "survey_session_id": sess3.id,
                    "version_number": 1,
                    "status": "SUBMITTED",
                    "snapshot_data": json.dumps(snapshot_data),
                    "submitted_by": surveyor_user.id,
                    "submitted_at": datetime.now(timezone.utc),
                })
                logger.info(f"  +-- Seeded Assignment 3 (SUBMITTED for Review): {asgn3.id} [Submission: {sub3.id}]")

            # 7e. Survey Assignment 4: REVISION_REQUIRED (Discrepancy returned to surveyor)
            if "PRJ-2026-CYBER-EXT" in projects and bld104 and p104:
                asgn4_data = {
                    "survey_project_id": projects["PRJ-2026-CYBER-EXT"].id,
                    "surveyor_id": surveyor_user.id,
                    "jurisdiction_id": jur_map["JUR-W102"].id,
                    "parcel_id": p104.id,
                    "building_id": bld104.id,
                    "priority": "HIGH",
                    "status": "REVISION_REQUIRED",
                    "started_at": datetime.now(timezone.utc),
                    "notes": "DEMO DATA: Height discrepancy flag. Surveyor instructed to re-verify parapet.",
                }
                asgn4 = await survey_assignment_repository.create(db, asgn4_data)
                sess4 = await survey_session_repository.create(db, {
                    "assignment_id": asgn4.id,
                    "surveyor_id": surveyor_user.id,
                    "status": "ACTIVE",
                    "started_at": datetime.now(timezone.utc),
                    "sync_status": "SYNCED",
                })
                sub4 = await survey_submission_repository.create(db, {
                    "assignment_id": asgn4.id,
                    "survey_session_id": sess4.id,
                    "version_number": 1,
                    "status": "REVISION_REQUIRED",
                    "snapshot_data": json.dumps({"assignment_id": str(asgn4.id)}),
                    "submitted_by": surveyor_user.id,
                    "submitted_at": datetime.now(timezone.utc),
                    "reviewed_by": officer_user.id,
                    "reviewed_at": datetime.now(timezone.utc),
                    "review_notes": "Discrepancy detected: Measured height 32.5m exceeds approved building height 26.0m. Re-verify whether rooftop antenna was included in total structure height.",
                })
                logger.info(f"  +-- Seeded Assignment 4 (REVISION_REQUIRED): {asgn4.id}")

            # 7f. Survey Assignment 5: APPROVED (Adjudicated official record)
            if "PRJ-2026-CYBER-EXT" in projects and p105:
                asgn5_data = {
                    "survey_project_id": projects["PRJ-2026-CYBER-EXT"].id,
                    "surveyor_id": surveyor_user.id,
                    "jurisdiction_id": jur_map["JUR-W102"].id,
                    "parcel_id": p105.id,
                    "priority": "LOW",
                    "status": "APPROVED",
                    "started_at": datetime.now(timezone.utc),
                    "completed_at": datetime.now(timezone.utc),
                    "notes": "DEMO DATA: Fully adjudicated cadastral survey.",
                }
                asgn5 = await survey_assignment_repository.create(db, asgn5_data)
                sess5 = await survey_session_repository.create(db, {
                    "assignment_id": asgn5.id,
                    "surveyor_id": surveyor_user.id,
                    "status": "COMPLETED",
                    "started_at": datetime.now(timezone.utc),
                    "ended_at": datetime.now(timezone.utc),
                    "sync_status": "SYNCED",
                })
                sub5 = await survey_submission_repository.create(db, {
                    "assignment_id": asgn5.id,
                    "survey_session_id": sess5.id,
                    "version_number": 1,
                    "status": "APPROVED",
                    "snapshot_data": json.dumps({"assignment_id": str(asgn5.id)}),
                    "submitted_by": surveyor_user.id,
                    "submitted_at": datetime.now(timezone.utc),
                    "reviewed_by": officer_user.id,
                    "reviewed_at": datetime.now(timezone.utc),
                    "review_notes": "Field measurements and boundary pegs verify cadastral integrity within municipal tolerances.",
                })
                logger.info(f"  +-- Seeded Assignment 5 (APPROVED): {asgn5.id}")

            # 8. Phase 11 Workflows & Citizen Public-Service Integration
            await seed_phase11_workflows(db)

        await db.commit()
    logger.info("Database seeding completed successfully with Phases 1-11!")


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


async def seed_phase11_workflows(db):
    """Seed configurable service types, citizen property authorizations, and demo service requests."""
    logger.info("  +-- Seeding Phase 11 Citizen & Government Workflow definitions...")
    from sqlalchemy import select

    service_types_data = [
        {
            "code": "PROPERTY_DATA_CORRECTION",
            "name": "Property Data Correction",
            "description": "Request correction of official address, property type, or administrative metadata.",
            "citizen_visible": True,
            "response_sla_hours": 24,
            "completion_sla_hours": 72,
            "required_documents": ["IDENTITY_SUPPORTING_DOCUMENT", "SALE_DEED"],
            "required_fields": ["description", "property_id"],
        },
        {
            "code": "PROPERTY_SURVEY_REQUEST",
            "name": "Property Field Survey Request",
            "description": "Commission a field survey to verify boundaries, building height, or property extensions.",
            "citizen_visible": True,
            "response_sla_hours": 48,
            "completion_sla_hours": 168,
            "required_documents": ["TITLE_DOCUMENT"],
            "required_fields": ["property_id", "description"],
        },
        {
            "code": "BUILDING_DATA_UPDATE",
            "name": "Building Footprint & Height Update",
            "description": "Report alterations to building height, structural footprint, or floor count.",
            "citizen_visible": True,
            "response_sla_hours": 24,
            "completion_sla_hours": 96,
            "required_documents": ["BUILDING_PLAN", "APPROVAL_DOCUMENT"],
            "required_fields": ["property_id", "description"],
        },
        {
            "code": "FLOOR_UNIT_UPDATE",
            "name": "Floor & Unit Information Update",
            "description": "Register or modify internal unit divisions, area splits, or vertical floor metadata.",
            "citizen_visible": True,
            "response_sla_hours": 24,
            "completion_sla_hours": 96,
            "required_documents": ["FLOOR_PLAN"],
            "required_fields": ["property_id", "description"],
        },
        {
            "code": "DOCUMENT_SUBMISSION",
            "name": "Official Document Submission",
            "description": "Submit property deeds, tax receipts, or encumbrance certificates for verification.",
            "citizen_visible": True,
            "response_sla_hours": 24,
            "completion_sla_hours": 48,
            "required_documents": ["PROPERTY_REGISTRATION"],
            "required_fields": ["property_id", "description"],
        },
        {
            "code": "PROPERTY_BOUNDARY_REVIEW",
            "name": "Cadastral Boundary Review",
            "description": "Request municipal boundary investigation for parcel overlaps or peg discrepancies.",
            "citizen_visible": True,
            "response_sla_hours": 48,
            "completion_sla_hours": 120,
            "required_documents": ["SURVEY_DOCUMENT"],
            "required_fields": ["property_id", "description"],
        },
        {
            "code": "SURVEY_DISCREPANCY",
            "name": "Survey Measurement Discrepancy",
            "description": "Report discrepancies between field survey observations and official registry values.",
            "citizen_visible": True,
            "response_sla_hours": 24,
            "completion_sla_hours": 72,
            "required_documents": ["SURVEY_DOCUMENT"],
            "required_fields": ["property_id", "description"],
        },
        {
            "code": "UTILITY_DATA_REPORT",
            "name": "Subsurface Utility Discrepancy Report",
            "description": "Report suspected inaccuracies or collisions in underground utility alignment.",
            "citizen_visible": True,
            "response_sla_hours": 24,
            "completion_sla_hours": 72,
            "required_documents": [],
            "required_fields": ["description"],
        },
        {
            "code": "PROPERTY_INFORMATION_REQUEST",
            "name": "Certified Property Information Request",
            "description": "Request certified extract of 2D/3D cadastral twin and verified spatial records.",
            "citizen_visible": True,
            "response_sla_hours": 12,
            "completion_sla_hours": 24,
            "required_documents": [],
            "required_fields": ["property_id"],
        },
        {
            "code": "OTHER",
            "name": "General Administrative Enquiry",
            "description": "General municipal cadastral enquiry or unclassified public request.",
            "citizen_visible": True,
            "response_sla_hours": 48,
            "completion_sla_hours": 120,
            "required_documents": [],
            "required_fields": ["description"],
        },
    ]

    for st in service_types_data:
        existing = (await db.execute(select(ServiceType).where(ServiceType.code == st["code"]))).scalar_one_or_none()
        if not existing:
            new_st = ServiceType(
                code=st["code"],
                name=st["name"],
                description=st["description"],
                active=True,
                citizen_visible=st["citizen_visible"],
                required_documents=st["required_documents"],
                required_fields=st["required_fields"],
                response_sla_hours=st["response_sla_hours"],
                completion_sla_hours=st["completion_sla_hours"],
                allowed_roles=["CITIZEN", "GOVERNMENT_OFFICER", "ADMIN"],
            )
            db.add(new_st)
            logger.info(f"    +-- Seeded ServiceType: {st['code']}")

    # Link demo citizen to demo property
    citizen_user = (await db.execute(select(User).where(User.username == "citizen"))).scalar_one_or_none()
    demo_property = (await db.execute(select(Property).limit(1))).scalar_one_or_none()
    officer_user = (await db.execute(select(User).where(User.username == "officer"))).scalar_one_or_none()

    if citizen_user and demo_property:
        existing_link = (await db.execute(
            select(CitizenPropertyLink).where(
                CitizenPropertyLink.citizen_id == citizen_user.id,
                CitizenPropertyLink.property_id == demo_property.id,
            )
        )).scalar_one_or_none()

        if not existing_link:
            link = CitizenPropertyLink(
                citizen_id=citizen_user.id,
                property_id=demo_property.id,
                authorization_type="OWNER",
                status="VERIFIED",
                verified_by=officer_user.id if officer_user else None,
                verified_at=datetime.now(timezone.utc),
            )
            db.add(link)
            logger.info(f"    +-- Linked Citizen '{citizen_user.username}' to Property '{demo_property.property_reference}'")

    # ── Phase 12: Seed default GV3D-V1 identifier scheme ─────────────────
    logger.info("[Phase 12] Seeding GV3D-V1 identifier scheme...")
    existing_scheme = (await db.execute(
        _select(IdentifierScheme).where(IdentifierScheme.scheme_code == "GV3D-V1")
    )).scalar_one_or_none()

    if not existing_scheme:
        scheme = IdentifierScheme(
            scheme_code="GV3D-V1",
            name="GeoVertex 3D Identifier Scheme Version 1",
            version=1,
            description=(
                "Default Technical 3D Property Identifier scheme for GeoVertex. "
                "Generates deterministic identifiers in format GV-{JUR}-{PARCEL}-{BUILDING}-{FLOOR}-{UNIT}. "
                "DISCLAIMER: NOT an official ULPIN or legal ownership identifier."
            ),
            prefix="GV",
            separator="-",
            jurisdiction_component="strip_prefix_code",
            parcel_component="strip_prefix_code",
            building_component="strip_prefix_ref",
            floor_component="strip_floor_suffix",
            unit_component="strip_unit_suffix",
            padding_rules={},
            checksum_enabled=False,
            active=True,
        )
        db.add(scheme)
    # ── Phase 13: Seed Entity Versions, Audit Events, Notifications ─────
    logger.info("[Phase 13] Seeding Phase 13 governance, versioning & notifications...")
    demo_parcel = (await db.execute(_select(Parcel).limit(1))).scalars().first()
    admin_user = (await db.execute(_select(User).where(User.username == "admin"))).scalars().first()

    if demo_parcel:
        existing_version = (await db.execute(
            _select(EntityVersion).where(EntityVersion.entity_id == str(demo_parcel.id))
        )).scalars().first()

    if not existing_version:
        # Version 1 of Demo Parcel
        v1_id = uuid.uuid4()
        v1 = EntityVersion(
            id=v1_id,
            entity_type="PARCEL",
            entity_id=str(demo_parcel.id),
            version_number=1,
            version_uuid=str(uuid.uuid4()),
            version_status=VersionStatus.SUPERSEDED.value,
            created_by=admin_user.id if admin_user else None,
            effective_from=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            effective_to=datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
            change_type=VersionChangeType.CREATE.value,
            change_reason="Initial cadastral parcel registration",
            source_type=VersionSourceType.MANUAL.value,
            source_id="REG-2026-001",
            snapshot_data={
                "parcel_code": demo_parcel.parcel_code,
                "parcel_number": demo_parcel.parcel_number,
                "land_use": demo_parcel.land_use,
                "area": 1200.50,
                "status": "ACTIVE",
            },
            geometry_wkt=demo_parcel.geometry_wkt or "POLYGON((83.30 17.70, 83.31 17.70, 83.31 17.71, 83.30 17.71, 83.30 17.70))",
            geometry_type="Polygon",
            geometry_metrics={
                "area": 1200.50,
                "length": 140.2,
                "centroid": {"x": 83.305, "y": 17.705},
                "bounding_box": {"min_x": 83.30, "min_y": 17.70, "max_x": 83.31, "max_y": 17.71},
            },
            geometry_hash="d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592",
            content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            metadata_json={"phase": "Phase 13 Seed Data"},
        )
        db.add(v1)

        # Version 2 of Demo Parcel (CURRENT)
        v2_id = uuid.uuid4()
        v2 = EntityVersion(
            id=v2_id,
            entity_type="PARCEL",
            entity_id=str(demo_parcel.id),
            version_number=2,
            version_uuid=str(uuid.uuid4()),
            version_status=VersionStatus.CURRENT.value,
            created_by=officer_user.id if officer_user else None,
            effective_from=datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
            change_type=VersionChangeType.GEOMETRY_UPDATE.value,
            change_reason="Field survey boundary realignment following total station observation",
            source_type=VersionSourceType.SURVEY.value,
            source_id="SURV-W101-001",
            parent_version_id=v1_id,
            supersedes_version_id=v1_id,
            snapshot_data={
                "parcel_code": demo_parcel.parcel_code,
                "parcel_number": demo_parcel.parcel_number,
                "land_use": demo_parcel.land_use,
                "area": 1243.20,
                "status": "ACTIVE",
            },
            geometry_wkt=demo_parcel.geometry_wkt or "POLYGON((83.30 17.70, 83.312 17.70, 83.312 17.712, 83.30 17.712, 83.30 17.70))",
            geometry_type="Polygon",
            geometry_metrics={
                "area": 1243.20,
                "length": 144.8,
                "centroid": {"x": 83.306, "y": 17.706},
                "bounding_box": {"min_x": 83.30, "min_y": 17.70, "max_x": 83.312, "max_y": 17.712},
            },
            geometry_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            content_hash="ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
            metadata_json={"phase": "Phase 13 Seed Data", "reviewer": "officer"},
        )
        db.add(v2)
        v1.superseded_by_version_id = v2_id
        logger.info(f"    +-- Seeded EntityVersions (v1, v2) for Parcel '{demo_parcel.parcel_code}'")

    # Seed Sample Notification Preferences
    if citizen_user:
        pref = (await db.execute(
            _select(NotificationPreference).where(
                NotificationPreference.user_id == citizen_user.id,
                NotificationPreference.notification_type == "ALL",
            )
        )).scalars().first()
        if not pref:
            db.add(NotificationPreference(
                user_id=citizen_user.id,
                notification_type="ALL",
                channel="IN_APP",
                enabled=True,
            ))
            db.add(NotificationPreference(
                user_id=citizen_user.id,
                notification_type="SURVEY_ASSIGNED",
                channel="EMAIL",
                enabled=True,
            ))
            logger.info("    +-- Seeded NotificationPreferences for Citizen")

    # Seed Sample In-App Notifications
    if officer_user:
        existing_notif = (await db.execute(
            _select(Notification).where(Notification.user_id == officer_user.id)
        )).scalars().first()
        if not existing_notif:
            db.add(Notification(
                user_id=officer_user.id,
                notification_type="CASE_ASSIGNMENT",
                title="Service Request Case Assigned",
                message="Case GV-CASE-2026-000123 has been assigned to your review queue.",
                related_entity_type="SERVICE_REQUEST",
                related_entity_id="GV-CASE-2026-000123",
                delivery_channel="IN_APP",
                status="SENT",
                severity="INFO",
            ))
            db.add(Notification(
                user_id=officer_user.id,
                notification_type="VALIDATION_ALERT",
                title="Topology Check Completed",
                message="Parcel boundary validation completed with 0 critical topological errors.",
                related_entity_type="PARCEL",
                related_entity_id=str(demo_parcel.id),
                delivery_channel="IN_APP",
                status="SENT",
                severity="INFO",
            ))
            logger.info("    +-- Seeded sample notifications for Officer")

    await db.commit()
    logger.info("Database seeding completed successfully with Phases 1-13!")


if __name__ == "__main__":
    asyncio.run(seed_database())


