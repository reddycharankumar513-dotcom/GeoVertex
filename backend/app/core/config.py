import os
from typing import List, Optional, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root project directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SQLITE_DB_PATH = os.path.join(ROOT_DIR, "geovertex.db").replace("\\", "/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Project Information
    PROJECT_NAME: str = "GeoVertex Cadastral Intelligence Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"

    # Security & Tokens
    JWT_SECRET: str = "geovertex-super-secret-jwt-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database Connection
    DATABASE_URL: str = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"
    DATABASE_URL_SYNC: str = f"sqlite:///{SQLITE_DB_PATH}"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = "postgresql+psycopg://" + v[len("postgres://"):]
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def normalize_database_url_sync(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = "postgresql+psycopg://" + v[len("postgres://"):]
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v


    # Database Connection Pooling (PostgreSQL)
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_PRE_PING: bool = True

    # Redis Cache & Message Broker
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # Object Storage (Local / S3 / MinIO)
    STORAGE_BACKEND: str = "local"  # "local", "s3", "minio"
    STORAGE_LOCAL_DIR: str = "uploads"
    S3_ENDPOINT_URL: Optional[str] = None
    S3_BUCKET_NAME: str = "geovertex-documents"
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = True

    # Monitoring & Metrics
    METRICS_ENABLED: bool = True
    PROMETHEUS_METRICS_PATH: str = "/metrics"

    # Email & Notifications (Phase 13 / 15)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "notifications@geovertex.gov"
    SMTP_TLS: bool = True

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = (
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS

    # Default Admin Seed Account
    DEFAULT_ADMIN_EMAIL: str = "admin@geovertex.local"
    DEFAULT_ADMIN_PASSWORD: str = "GeoVertexAdmin2026!"
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_FULL_NAME: str = "System Administrator"

    # Password Policy
    MIN_PASSWORD_LENGTH: int = 8

    @model_validator(mode="after")
    def validate_production_settings(self):
        """Fails fast on application startup if insecure configurations are detected in production."""
        if self.ENVIRONMENT.lower() == "production":
            errors = []
            if self.DEBUG:
                errors.append("DEBUG must be False in production mode")
            if "geovertex-super-secret" in self.JWT_SECRET or len(self.JWT_SECRET) < 32:
                errors.append(
                    "JWT_SECRET must be configured with a cryptographically secure key of at least 32 characters (default placeholder forbidden)"
                )
            if "sqlite" in self.DATABASE_URL.lower():
                errors.append(
                    "SQLite is not supported for production; configure PostgreSQL with PostGIS in DATABASE_URL"
                )
            if errors:
                raise ValueError("Production configuration validation failed:\n - " + "\n - ".join(errors))
        return self


settings = Settings()
