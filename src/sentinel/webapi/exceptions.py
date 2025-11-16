"""Custom exception classes and error handling for the Sentinel API."""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ..config.logging import get_logger
from .models.responses import ErrorResponse

logger = get_logger(__name__)


class SentinelException(Exception):
    """Base exception for Sentinel application."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id


class ValidationException(SentinelException):
    """Exception for validation errors."""

    def __init__(
        self,
        message: str = "Validation failed",
        field_errors: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            status_code=422,
            details={"field_errors": field_errors or {}},
            request_id=request_id,
        )


class NotFoundError(SentinelException):
    """Exception for resource not found errors."""

    def __init__(
        self, resource: str, identifier: str, request_id: Optional[str] = None
    ):
        message = f"{resource} with identifier '{identifier}' not found"
        super().__init__(
            message=message,
            status_code=404,
            details={"resource": resource, "identifier": identifier},
            request_id=request_id,
        )


class DatabaseError(SentinelException):
    """Exception for database operation errors."""

    def __init__(self, operation: str, message: str, request_id: Optional[str] = None):
        super().__init__(
            message=f"Database {operation} failed: {message}",
            status_code=500,
            details={"operation": operation},
            request_id=request_id,
        )


class ExternalServiceError(SentinelException):
    """Exception for external service errors."""

    def __init__(
        self,
        service: str,
        operation: str,
        message: str,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"{service} service error during {operation}: {message}",
            status_code=503,
            details={"service": service, "operation": operation},
            request_id=request_id,
        )


class RateLimitError(SentinelException):
    """Exception for rate limiting errors."""

    def __init__(
        self, resource: str, limit: int, window: str, request_id: Optional[str] = None
    ):
        message = f"Rate limit exceeded for {resource}: {limit} requests per {window}"
        super().__init__(
            message=message,
            status_code=429,
            details={"resource": resource, "limit": limit, "window": window},
            request_id=request_id,
        )


class ConfigurationError(SentinelException):
    """Exception for configuration errors."""

    def __init__(self, setting: str, message: str, request_id: Optional[str] = None):
        super().__init__(
            message=f"Configuration error for '{setting}': {message}",
            status_code=500,
            details={"setting": setting},
            request_id=request_id,
        )


async def sentinel_exception_handler(
    request: Request, exc: SentinelException
) -> JSONResponse:
    """Handle Sentinel custom exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "Sentinel exception occurred",
        exception_type=type(exc).__name__,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    error_response = ErrorResponse(
        success=False,
        error={
            "type": type(exc).__name__,
            "message": exc.message,
            "details": exc.details,
            "status_code": exc.status_code,
        },
        request_id=request_id,
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation exceptions."""
    request_id = getattr(request.state, "request_id", None)

    # Extract field errors from Pydantic validation error
    field_errors = {}
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        field_errors[field_path] = error["msg"]

    logger.warning(
        "Validation error occurred",
        field_errors=field_errors,
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    error_response = ErrorResponse(
        success=False,
        error={
            "type": "ValidationError",
            "message": "Request validation failed",
            "details": {"field_errors": field_errors},
            "status_code": 422,
        },
        request_id=request_id,
    )

    return JSONResponse(status_code=422, content=error_response.model_dump())


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    error_response = ErrorResponse(
        success=False,
        error={
            "type": "HTTPException",
            "message": str(exc.detail),
            "status_code": exc.status_code,
        },
        request_id=request_id,
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "Unexpected exception occurred",
        exception_type=type(exc).__name__,
        message=str(exc),
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    # Don't expose internal error details in production
    error_response = ErrorResponse(
        success=False,
        error={
            "type": "InternalServerError",
            "message": "An unexpected error occurred",
            "status_code": 500,
        },
        request_id=request_id,
    )

    return JSONResponse(status_code=500, content=error_response.model_dump())


def setup_exception_handlers(app):
    """Register exception handlers with FastAPI app."""
    app.add_exception_handler(SentinelException, sentinel_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers registered")
