import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root project directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SQLITE_DB_PATH = os.path.join(ROOT_DIR, "geovertex.db").replace("\\", "/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
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

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"
    DATABASE_URL_SYNC: str = f"sqlite:///{SQLITE_DB_PATH}"

    # Redis Cache & Message Broker
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

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


settings = Settings()
