from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.jurisdictions import router as jurisdictions_router
from app.api.v1.audit import router as audit_router
from app.api.v1.parcels import router as parcels_router
from app.api.v1.properties import router as properties_router
from app.api.v1.buildings import router as buildings_router
from app.api.v1.map import router as map_router
from app.api.v1.spatial import router as spatial_router
from app.api.v1.gis import router as gis_router
from app.api.v1.threed import router as threed_router
from app.api.v1.floors import router as floors_router
from app.api.v1.units import router as units_router
from app.api.v1.surveys import router as surveys_router
from app.api.v1.ai import router as ai_router
from app.api.v1.validation import router as validation_router
from app.api.v1.documents import router as documents_router
from app.api.v1.change_detection import router as change_detection_router
from app.api.v1.utilities import router as utilities_router
from app.api.v1.workflows import router as workflows_router
# Phase 12 — Technical 3D Property Identifier Engine
from app.api.v1.identifiers import router as identifiers_router, verify_router
# Phase 13 — Audit, Versioning, Notifications & System Governance
from app.api.v1.versions import router as versions_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.governance import router as governance_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(jurisdictions_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(parcels_router)
api_v1_router.include_router(properties_router)
api_v1_router.include_router(buildings_router)
api_v1_router.include_router(map_router)
api_v1_router.include_router(spatial_router)
api_v1_router.include_router(gis_router)
api_v1_router.include_router(threed_router)
api_v1_router.include_router(floors_router)
api_v1_router.include_router(units_router)
api_v1_router.include_router(surveys_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(validation_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(change_detection_router)
api_v1_router.include_router(utilities_router)
api_v1_router.include_router(workflows_router)
api_v1_router.include_router(identifiers_router)
api_v1_router.include_router(verify_router)
api_v1_router.include_router(versions_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(governance_router)

__all__ = ["api_v1_router"]





