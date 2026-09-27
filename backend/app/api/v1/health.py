import time
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.dependencies.db import get_db
from app.services.document_storage_service import document_storage_service

router = APIRouter(tags=["Health & Observability"])

APP_START_TIME = time.time()


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
        "uptime_seconds": round(time.time() - APP_START_TIME, 2),
    }


@router.get("/health/ready", summary="Readiness Probe")
@router.get("/api/v1/health", summary="System Readiness Verification")
async def health_readiness(db: AsyncSession = Depends(get_db)):
    """Verifies operational readiness including PostgreSQL, PostGIS, Redis, and Object Storage."""
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
        readiness_report["cache"]["connected"] = False
        readiness_report["cache"]["note"] = "Redis unavailable or not running"

    # 4. Check Storage Directory / S3 Access
    try:
        storage_status = document_storage_service.get_storage_status()
        readiness_report["storage"] = {
            "available": storage_status.get("writable", False) or storage_status.get("backend") in ("s3", "minio"),
            **storage_status,
        }
    except Exception as e:
        readiness_report["storage"] = {"available": False, "error": str(e)}

    # 5. Check Subsystems Status (Accurate, No-Fake status)
    readiness_report["subsystems"] = {
        "ai_engine": {
            "configured": False,
            "status": "MODEL_NOT_CONFIGURED",
            "note": "AI models run in CPU fallback / rule-assisted demo mode without unverified external weights",
        },
        "ocr_engine": {
            "configured": False,
            "status": "OCR_ENGINE_NOT_CONFIGURED",
            "note": "OCR pipeline active with mock/rule fallback for local development",
        },
        "notification_delivery": {
            "configured": bool(settings.SMTP_HOST),
            "status": "SMTP_CONFIGURED" if settings.SMTP_HOST else "CONSOLE_LOG_PROVIDER",
            "note": f"Provider: {'SMTP (' + settings.SMTP_HOST + ')' if settings.SMTP_HOST else 'ConsoleEmailProvider'}",
        },
    }

    http_status = status.HTTP_200_OK if readiness_report["database"]["connected"] else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=readiness_report)


@router.get("/metrics", summary="Prometheus Metrics", response_class=PlainTextResponse)
@router.get("/api/v1/metrics", summary="Prometheus Metrics API", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Outputs system and runtime metrics formatted according to Prometheus exposition standard."""
    uptime = round(time.time() - APP_START_TIME, 2)
    pool_size = settings.DB_POOL_SIZE if "sqlite" not in settings.DATABASE_URL else 1
    max_overflow = settings.DB_MAX_OVERFLOW if "sqlite" not in settings.DATABASE_URL else 0

    lines = [
        "# HELP geovertex_build_info Build information about the GeoVertex application.",
        "# TYPE geovertex_build_info gauge",
        f'geovertex_build_info{{version="{settings.VERSION}",environment="{settings.ENVIRONMENT}"}} 1',
        "",
        "# HELP geovertex_uptime_seconds Total runtime uptime of the API server process.",
        "# TYPE geovertex_uptime_seconds gauge",
        f"geovertex_uptime_seconds {uptime}",
        "",
        "# HELP geovertex_db_pool_size Configured database connection pool size.",
        "# TYPE geovertex_db_pool_size gauge",
        f"geovertex_db_pool_size {pool_size}",
        "",
        "# HELP geovertex_db_max_overflow Configured database pool max overflow.",
        "# TYPE geovertex_db_max_overflow gauge",
        f"geovertex_db_max_overflow {max_overflow}",
        "",
        "# HELP geovertex_storage_backend_type Configured storage backend (1=active).",
        "# TYPE geovertex_storage_backend_type gauge",
        f'geovertex_storage_backend_type{{backend="{settings.STORAGE_BACKEND}"}} 1',
        "",
    ]
    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4; charset=utf-8")
