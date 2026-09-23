from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_v1_router
from app.api.v1.health import router as root_health_router
from app.core.config import settings
from app.core.errors import (
    GeoVertexException,
    geovertex_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import logger
from app.database.base import Base
from app.database.session import async_engine
from app.middleware.logging_middleware import RequestTracingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    # Initialize database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema verified and active")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
    await async_engine.dispose()


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Authoritative API for 3D Cadastral Intelligence, Vertical Property Mapping, and Spatial Verification.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )

    # 2. Request Tracing & Structured Logging Middleware
    app.add_middleware(RequestTracingMiddleware)

    # 3. Standardized Error Handlers
    app.add_exception_handler(GeoVertexException, geovertex_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 4. Include Routers
    # Direct root health probes
    app.include_router(root_health_router)
    # Versioned API
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
