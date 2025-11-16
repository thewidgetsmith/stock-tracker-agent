"""Health check endpoints for the Sentinel API."""

import time
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..config.logging import get_logger
from ..config.settings import get_settings
from ..db.database import check_database_health
from .models.requests import HealthCheckRequest
from .models.responses import HealthResponse, HealthStatus

logger = get_logger(__name__)
router = APIRouter()

# Track application start time for uptime calculation
_app_start_time = time.time()


def get_system_info() -> Dict[str, Any]:
    """Get basic system information."""
    try:
        import platform

        import psutil

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
    except ImportError:
        # psutil not available, return basic info
        import platform

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }


def check_configuration_health() -> Dict[str, Any]:
    """Check application configuration health."""
    try:
        settings = get_settings()

        # Basic configuration checks
        checks = {
            "database_url_configured": bool(settings.database_url),
            "log_level_valid": settings.log_level
            in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        }

        # Check optional configurations
        optional_checks = {
            "telegram_configured": bool(getattr(settings, "telegram_bot_token", None)),
            "redis_configured": bool(getattr(settings, "redis_url", None)),
        }

        all_checks = {**checks, **optional_checks}

        status = "healthy" if all(checks.values()) else "degraded"

        return {
            "status": status,
            "checks": all_checks,
            "required_checks_passed": all(checks.values()),
            "optional_checks_passed": all(optional_checks.values()),
        }

    except Exception as e:
        logger.error("Configuration health check failed", error=str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_external_services_health() -> Dict[str, Any]:
    """Check external service dependencies."""
    services = {}

    # Check internet connectivity (basic)
    try:
        import urllib.request

        urllib.request.urlopen("http://www.google.com", timeout=5)
        services["internet"] = {"status": "healthy", "response_time_ms": None}
    except Exception as e:
        services["internet"] = {"status": "unhealthy", "error": str(e)}

    # Check stock data API (if configured)
    try:
        # This would check your actual stock data provider
        # For now, just mark as not configured
        services["stock_api"] = {
            "status": "not_configured",
            "message": "Stock API not configured",
        }
    except Exception as e:
        services["stock_api"] = {"status": "unhealthy", "error": str(e)}

    # Determine overall status
    statuses = [service["status"] for service in services.values()]
    if "unhealthy" in statuses:
        overall_status = "unhealthy"
    elif "degraded" in statuses or "not_configured" in statuses:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "services": services,
    }


@router.get("/health", response_model=HealthResponse, summary="Basic Health Check")
async def basic_health_check():
    """
    Perform a basic health check.

    Returns basic application health status including:
    - Overall status
    - Database connectivity
    - Application uptime
    - Basic system information
    """
    try:
        uptime_seconds = time.time() - _app_start_time

        # Check database health
        db_health = check_database_health()

        # Determine overall status
        if db_health["status"] == "healthy":
            overall_status = "healthy"
        elif db_health["status"] == "degraded":
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        services = {
            "database": db_health,
        }

        health_status = HealthStatus(
            status=overall_status,
            services=services,
            uptime_seconds=uptime_seconds,
            version=getattr(get_settings(), "app_version", "unknown"),
        )

        response = HealthResponse(success=True, health=health_status)

        logger.debug("Basic health check completed", status=overall_status)
        return response

    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)

        # Return unhealthy status
        health_status = HealthStatus(
            status="unhealthy",
            services={"error": {"status": "unhealthy", "error": str(e)}},
            uptime_seconds=time.time() - _app_start_time,
        )

        return HealthResponse(
            success=True, health=health_status  # The health endpoint itself succeeded
        )


@router.post(
    "/health/detailed", response_model=HealthResponse, summary="Detailed Health Check"
)
async def detailed_health_check(request: HealthCheckRequest):
    """
    Perform a detailed health check with comprehensive service status.

    Includes:
    - Database connectivity and pool status
    - Configuration validation
    - External service dependencies
    - System resource utilization
    - Application metrics
    """
    try:
        uptime_seconds = time.time() - _app_start_time

        services = {}

        # Database health
        if request.include_services:
            services["database"] = check_database_health()

        # Configuration health
        services["configuration"] = check_configuration_health()

        # External services
        if request.include_services:
            external_services = check_external_services_health()
            services.update(external_services["services"])

        # System information (if detailed)
        if request.detailed:
            services["system"] = {"status": "healthy", **get_system_info()}

        # Determine overall status
        service_statuses = [s.get("status", "unknown") for s in services.values()]

        if "unhealthy" in service_statuses:
            overall_status = "unhealthy"
        elif "degraded" in service_statuses or "not_configured" in service_statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        health_status = HealthStatus(
            status=overall_status,
            services=services,
            uptime_seconds=uptime_seconds,
            version=getattr(get_settings(), "app_version", "unknown"),
        )

        response = HealthResponse(success=True, health=health_status)

        logger.info(
            "Detailed health check completed",
            status=overall_status,
            services_checked=len(services),
            detailed=request.detailed,
        )

        return response

    except Exception as e:
        logger.error("Detailed health check failed", error=str(e), exc_info=True)

        health_status = HealthStatus(
            status="unhealthy",
            services={"error": {"status": "unhealthy", "error": str(e)}},
            uptime_seconds=time.time() - _app_start_time,
        )

        return HealthResponse(success=True, health=health_status)


@router.get("/health/live", summary="Liveness Probe")
async def liveness_probe():
    """
    Kubernetes/Docker liveness probe endpoint.

    Returns 200 if the application is running and can serve requests.
    This is a lightweight check that doesn't verify external dependencies.
    """
    try:
        uptime_seconds = time.time() - _app_start_time

        # Just check that the application is running and can respond
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": uptime_seconds,
        }
    except Exception as e:
        logger.error("Liveness probe failed", error=str(e), exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


@router.get("/health/ready", summary="Readiness Probe")
async def readiness_probe():
    """
    Kubernetes/Docker readiness probe endpoint.

    Returns 200 if the application is ready to serve requests.
    Checks critical dependencies like database connectivity.
    """
    try:
        # Check database connectivity
        db_health = check_database_health()

        if db_health["status"] != "healthy":
            return {
                "status": "not_ready",
                "reason": "Database not healthy",
                "database_status": db_health["status"],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": time.time() - _app_start_time,
        }

    except Exception as e:
        logger.error("Readiness probe failed", error=str(e), exc_info=True)
        return {
            "status": "not_ready",
            "reason": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
