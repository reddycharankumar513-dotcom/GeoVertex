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

__all__ = ["api_v1_router"]

