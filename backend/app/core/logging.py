import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from app.core.config import settings

# Sensitive keys that must be redacted from log payloads
SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "jwt_secret",
    "authorization",
}


def sanitize_data(data: Any) -> Any:
    """Recursively scrub sensitive keys from dictionaries or data objects."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = sanitize_data(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "geovertex-backend",
        }

        # Attach extra contextual properties if present
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "extra_data"):
            log_entry["details"] = sanitize_data(record.extra_data)

        if record.exc_info and settings.DEBUG:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging() -> logging.Logger:
    """Configures application logger based on environment."""
    logger = logging.getLogger("geovertex")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if settings.ENVIRONMENT == "production":
        handler.setFormatter(StructuredJsonFormatter())
    else:
        # Development readable console formatter
        dev_formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(dev_formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logging()
