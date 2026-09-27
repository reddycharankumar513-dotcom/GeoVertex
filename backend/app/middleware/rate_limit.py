"""Phase 14 — Configurable Lightweight Rate Limiting & Abuse Protection Middleware.

Protects sensitive endpoints (e.g., login, exports, uploads, AI jobs) against
brute force and excessive load using a memory-efficient sliding-window counter.
"""

import sys
import time
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.core.config import settings
from datetime import datetime, timezone


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 300, burst_limit: int = 600):
        super().__init__(app)
        self.default_rpm = requests_per_minute
        self.burst_limit = burst_limit
        # Client IP -> list of request timestamps (epoch float)
        self._history: Dict[str, List[float]] = defaultdict(list)
        # Sensitive endpoint limits: path prefix -> requests per minute
        self.sensitive_limits = {
            "/api/v1/auth/login": 60,
            "/api/v1/audit/export": 30,
            "/api/v1/documents/upload": 60,
            "/api/v1/ai/jobs": 60,
        }

    def _get_client_identifier(self, request: Request) -> str:
        # Check forward headers if reverse-proxied, else client host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        client = request.client
        return client.host if client else "127.0.0.1"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Bypass rate limiter in testing environment unless explicitly requested to test rate limits
        is_testing = getattr(settings, "ENVIRONMENT", "") in ("testing", "test") or "pytest" in sys.modules
        if is_testing and request.headers.get("X-Test-Enforce-Rate-Limit") != "true":
            return await call_next(request)

        # Allow health checks and static docs without rate limiting
        path = request.url.path
        if path.startswith("/health") or path in ("/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = self._get_client_identifier(request)
        now = time.time()
        window_start = now - 60.0

        # Determine limit for path
        limit = self.default_rpm
        for prefix, custom_limit in self.sensitive_limits.items():
            if path.startswith(prefix):
                limit = custom_limit
                break

        # Clean timestamps older than 60 seconds
        timestamps = self._history[client_ip]
        self._history[client_ip] = [ts for ts in timestamps if ts > window_start]

        if len(self._history[client_ip]) >= limit:
            retry_after = int(60.0 - (now - self._history[client_ip][0])) + 1
            request_id = getattr(request.state, "request_id", None) or "rate-limit"
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "TOO_MANY_REQUESTS",
                        "message": f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
                        "details": {"retry_after_seconds": retry_after, "limit": limit},
                        "request_id": request_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

        self._history[client_ip].append(now)
        return await call_next(request)
