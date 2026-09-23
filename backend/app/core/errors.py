from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.logging import logger


class GeoVertexException(HTTPException):
    """Base application exception producing standard error envelopes."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.details = details or {}


class BadRequestException(GeoVertexException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message=message,
            details=details,
        )


class UnauthorizedException(GeoVertexException):
    def __init__(self, message: str = "Authentication required or invalid token", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(GeoVertexException):
    def __init__(self, message: str = "Insufficient permissions for this resource", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
            details=details,
        )


class NotFoundException(GeoVertexException):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message=message,
            details=details,
        )


class ConflictException(GeoVertexException):
    def __init__(self, message: str = "Resource conflict or duplicate key", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message=message,
            details=details,
        )


class InactiveUserException(ForbiddenException):
    def __init__(self, message: str = "User account has been deactivated"):
        super().__init__(
            message=message,
            details={"status": "inactive"},
        )


async def geovertex_exception_handler(request: Request, exc: GeoVertexException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        f"Handled error: {exc.code} - {exc.message}",
        extra={"request_id": request_id, "extra_data": exc.details},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    errors = exc.errors()
    simplified_errors = [
        {
            "loc": err.get("loc"),
            "msg": err.get("msg"),
            "type": err.get("type"),
        }
        for err in errors
    ]
    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={"request_id": request_id, "extra_data": {"validation_errors": simplified_errors}},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request payload validation failed",
                "details": {"fields": simplified_errors},
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please contact system support.",
                "details": {"request_id": request_id},
            }
        },
    )
