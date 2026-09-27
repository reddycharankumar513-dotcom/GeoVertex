"""Phase 1 & Phase 13 — Request & Correlation Tracing Middleware.

Centralizes request ID and correlation ID lifecycle tracking across the API pipeline.
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import logger


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        start_time = time.time()
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={"request_id": request_id, "correlation_id": correlation_id},
        )

        try:
            response = await call_next(request)
            duration = round((time.time() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time-Ms"] = str(duration)

            logger.info(
                f"Completed: {request.method} {request.url.path} -> {response.status_code} in {duration}ms",
                extra={"request_id": request_id, "correlation_id": correlation_id},
            )
            return response
        except Exception as e:
            duration = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"Failed: {request.method} {request.url.path} after {duration}ms: {str(e)}",
                extra={"request_id": request_id, "correlation_id": correlation_id},
            )
            raise e
