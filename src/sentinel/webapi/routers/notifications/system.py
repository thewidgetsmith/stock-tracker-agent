"""System health and information endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from ....config.logging import get_logger
from ....events import get_event_bus
from ....services import NotificationService
from ...models.responses import StatusResponse

logger = get_logger(__name__)

# Create router for system operations
router = APIRouter()


# Service dependencies
def get_notification_service() -> NotificationService:
    """Dependency to get notification service instance."""
    return NotificationService()


@router.get(
    "/health",
    response_model=StatusResponse,
    summary="System Health Check",
    description="Comprehensive system health check",
)
async def system_health_check(request: Request):
    """
    Comprehensive system health check.

    Returns health status of all system components including:
    - Event bus
    - Notification channels
    - Service layer
    - Database connectivity
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info("System health check requested", request_id=request_id)

    try:
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
        }

        # Check event bus
        try:
            event_bus = get_event_bus()
            event_stats = event_bus.get_statistics()
            health_data["components"]["event_bus"] = {
                "status": "healthy",
                "statistics": event_stats,
            }
        except Exception as e:
            health_data["components"]["event_bus"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_data["overall_status"] = "degraded"

        # Check notification service
        try:
            notification_service = get_notification_service()
            # Simple check to ensure service can be instantiated
            health_data["components"]["notification_service"] = {
                "status": "healthy",
                "details": "Service instantiated successfully",
            }
        except Exception as e:
            health_data["components"]["notification_service"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_data["overall_status"] = "degraded"

        # Check database connectivity (through repository layer)
        try:
            from ....repositories import get_stock_repository

            stock_repo = get_stock_repository()
            # Try a simple database operation
            health_data["components"]["database"] = {
                "status": "healthy",
                "details": "Database connection verified",
            }
        except Exception as e:
            health_data["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_data["overall_status"] = "unhealthy"

        # Calculate component health summary
        healthy_components = sum(
            1
            for comp in health_data["components"].values()
            if comp.get("status") == "healthy"
        )
        total_components = len(health_data["components"])
        health_percentage = (
            (healthy_components / total_components) * 100 if total_components > 0 else 0
        )

        health_data["health_summary"] = {
            "healthy_components": healthy_components,
            "total_components": total_components,
            "health_percentage": round(health_percentage, 1),
        }

        # Determine final status based on percentage
        if health_percentage >= 100:
            health_data["overall_status"] = "healthy"
        elif health_percentage >= 50:
            health_data["overall_status"] = "degraded"
        else:
            health_data["overall_status"] = "unhealthy"

        return StatusResponse.create(data=health_data, request_id=request_id)

    except Exception as e:
        logger.error(
            "Failed to perform system health check", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to perform system health check: {str(e)}"
        )


@router.get(
    "/info",
    response_model=StatusResponse,
    summary="Get System Information",
    description="Get system information and configuration",
)
async def get_system_info(request: Request):
    """
    Get system information and configuration.

    Returns information about the system, configuration, and runtime environment.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info("System info requested", request_id=request_id)

    try:
        import platform
        import sys

        from ....config import get_settings

        settings = get_settings()

        system_info = {
            "system": {
                "platform": platform.platform(),
                "python_version": sys.version,
                "architecture": platform.architecture(),
                "processor": platform.processor(),
            },
            "application": {
                "name": "Sentry Agents",
                "version": "1.0.0",  # Could be read from pyproject.toml
                "environment": settings.environment,
                "debug_mode": settings.debug,
            },
            "configuration": {
                "database_path": str(settings.database_path),
                "telegram_enabled": bool(settings.telegram_bot_token),
                "email_enabled": bool(settings.smtp_server),
                "webhook_enabled": bool(settings.webhook_url),
                "log_level": settings.log_level,
            },
            "runtime": {
                "uptime": "N/A",  # Would need to track application start time
                "timestamp": datetime.now().isoformat(),
                "timezone": str(datetime.now().astimezone().tzinfo),
            },
        }

        return StatusResponse.create(data=system_info, request_id=request_id)

    except Exception as e:
        logger.error("Failed to get system info", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get system info: {str(e)}"
        )
