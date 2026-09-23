from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.dependencies.db import get_db

router = APIRouter(tags=["Health & Observability"])


@router.get("/health/live", summary="Liveness Probe")
@router.get("/health", summary="Basic Health Check")
async def health_liveness():
    """Returns basic liveness state of the API process."""
    return {
        "status": "healthy",
        "service": "geovertex-backend",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready", summary="Readiness Probe")
@router.get("/api/v1/health", summary="System Readiness Verification")
async def health_readiness(db: AsyncSession = Depends(get_db)):
    """Verifies operational readiness including PostgreSQL, PostGIS, and Redis."""
    readiness_report: Dict[str, Any] = {
        "status": "ready",
        "service": "geovertex-backend",
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {"connected": False, "postgis_available": False},
        "cache": {"connected": False},
    }

    # 1. Check Database Connectivity
    try:
        db_res = await db.execute(text("SELECT 1"))
        if db_res.scalar() == 1:
            readiness_report["database"]["connected"] = True
    except Exception as e:
        readiness_report["status"] = "degraded"
        readiness_report["database"]["error"] = str(e)

    # 2. Check PostGIS Availability
    if readiness_report["database"]["connected"]:
        try:
            gis_res = await db.execute(text("SELECT PostGIS_Version()"))
            gis_version = gis_res.scalar()
            readiness_report["database"]["postgis_available"] = True
            readiness_report["database"]["postgis_version"] = str(gis_version)
        except Exception:
            # Not a fatal error if running in SQLite local development mode
            readiness_report["database"]["postgis_available"] = False
            readiness_report["database"]["note"] = "PostGIS not enabled on current engine (e.g. SQLite local development)"

    # 3. Check Redis
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        await client.aclose()
        readiness_report["cache"]["connected"] = True
    except Exception:
        # Cache degradation does not block basic Phase 1 readiness
        readiness_report["cache"]["connected"] = False
        readiness_report["cache"]["note"] = "Redis unavailable or not running"

    http_status = status.HTTP_200_OK if readiness_report["database"]["connected"] else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=readiness_report)
