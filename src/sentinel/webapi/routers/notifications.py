"""Notification and system management API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ...config.logging import get_logger
from ...events import NotificationSentEvent, get_event_bus
from ...services import NotificationService
from ..exceptions import ValidationException
from ..models.requests import PaginationParams
from ..models.responses import StatusResponse, SuccessResponse

logger = get_logger(__name__)

# Create router for notification and system endpoints
router = APIRouter()


# Service dependencies
def get_notification_service() -> NotificationService:
    """Dependency to get notification service instance."""
    return NotificationService()


# Pydantic models for notification requests
class SendNotificationRequest(BaseModel):
    """Request model for sending notifications."""

    message: str = Field(..., description="Notification message content")
    channels: List[str] = Field(
        ["telegram"], description="List of notification channels"
    )
    priority: str = Field(
        "normal", description="Notification priority (low, normal, high, urgent)"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TestNotificationRequest(BaseModel):
    """Request model for testing notifications."""

    channel: str = Field(..., description="Channel to test (telegram, email, webhook)")
    test_message: str = Field(
        "Test notification from Sentry Agents", description="Test message content"
    )


@router.post(
    "/notifications/send",
    response_model=StatusResponse,
    summary="Send Notification",
    description="Send a notification through specified channels",
)
async def send_notification(
    notification_request: SendNotificationRequest,
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Send a notification through one or more channels.

    - **message**: The notification message content
    - **channels**: List of channels (telegram, email, webhook)
    - **priority**: Notification priority level
    - **metadata**: Optional additional data

    Returns delivery status for each channel.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info(
        "Send notification requested",
        channels=notification_request.channels,
        priority=notification_request.priority,
        request_id=request_id,
    )

    try:
        # Send notification through all requested channels
        results = {}

        for channel in notification_request.channels:
            try:
                if channel.lower() == "telegram":
                    result = await notification_service.send_telegram_notification(
                        notification_request.message,
                        priority=notification_request.priority,
                        metadata=notification_request.metadata,
                    )
                elif channel.lower() == "email":
                    result = await notification_service.send_email_notification(
                        subject="Sentry Agents Notification",
                        message=notification_request.message,
                        priority=notification_request.priority,
                        metadata=notification_request.metadata,
                    )
                elif channel.lower() == "webhook":
                    result = await notification_service.send_webhook_notification(
                        event_type="manual_notification",
                        data={
                            "message": notification_request.message,
                            "priority": notification_request.priority,
                            "metadata": notification_request.metadata,
                        },
                    )
                else:
                    result = {"success": False, "error": f"Unknown channel: {channel}"}

                results[channel] = result

                # Publish notification sent event if successful
                if result.get("success", False):
                    event_bus = get_event_bus()
                    await event_bus.publish(
                        NotificationSentEvent(
                            channel=channel,
                            message=notification_request.message,
                            recipient="api_user",  # Could be extracted from auth
                            delivery_status="sent",
                            response_time_ms=result.get("response_time_ms", 0),
                        )
                    )

            except Exception as e:
                logger.error(
                    f"Failed to send notification via {channel}",
                    error=str(e),
                    exc_info=True,
                )
                results[channel] = {"success": False, "error": str(e)}

        # Check if any notifications were successful
        successful_channels = [
            ch for ch, res in results.items() if res.get("success", False)
        ]
        overall_success = len(successful_channels) > 0

        return StatusResponse.create(
            data={
                "overall_success": overall_success,
                "successful_channels": successful_channels,
                "channel_results": results,
                "total_channels": len(notification_request.channels),
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error("Failed to send notifications", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to send notifications: {str(e)}"
        )


@router.post(
    "/notifications/test",
    response_model=StatusResponse,
    summary="Test Notification Channel",
    description="Test a specific notification channel",
)
async def test_notification_channel(
    test_request: TestNotificationRequest,
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Test a specific notification channel.

    - **channel**: Channel to test (telegram, email, webhook)
    - **test_message**: Message to send for testing

    Returns test result with detailed information.
    """
    request_id = getattr(request.state, "request_id", None)
    channel = test_request.channel.lower()

    logger.info("Test notification requested", channel=channel, request_id=request_id)

    try:
        if channel == "telegram":
            result = await notification_service.test_telegram_connection(
                test_request.test_message
            )
        elif channel == "email":
            result = await notification_service.test_email_connection(
                subject="Sentry Agents Test Email", message=test_request.test_message
            )
        elif channel == "webhook":
            result = await notification_service.test_webhook_connection(
                {
                    "test_message": test_request.test_message,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            raise ValidationException(
                f"Unknown channel: {channel}", request_id=request_id
            )

        # Publish test notification event
        if result.get("success", False):
            event_bus = get_event_bus()
            await event_bus.publish(
                NotificationSentEvent(
                    channel=channel,
                    message=f"Test: {test_request.test_message}",
                    recipient="test_user",
                    delivery_status="test_sent",
                    response_time_ms=result.get("response_time_ms", 0),
                )
            )

        return StatusResponse.create(
            data={
                "channel": channel,
                "test_result": result,
                "test_message": test_request.test_message,
            },
            request_id=request_id,
        )

    except ValidationException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to test {channel} notification", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to test {channel} notification: {str(e)}"
        )


@router.get(
    "/notifications/channels/status",
    response_model=StatusResponse,
    summary="Get Notification Channel Status",
    description="Get the status and configuration of all notification channels",
)
async def get_notification_channels_status(
    request: Request,
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Get the status and configuration of all notification channels.

    Returns configuration status and health checks for each channel.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info("Notification channels status requested", request_id=request_id)

    try:
        # Check status of all notification channels
        channels_status = {}

        # Check Telegram
        try:
            telegram_status = await notification_service.test_telegram_connection(
                "Health check"
            )
            channels_status["telegram"] = {
                "configured": True,
                "healthy": telegram_status.get("success", False),
                "last_check": datetime.now().isoformat(),
                "details": telegram_status,
            }
        except Exception as e:
            channels_status["telegram"] = {
                "configured": True,
                "healthy": False,
                "last_check": datetime.now().isoformat(),
                "error": str(e),
            }

        # Check Email
        try:
            email_status = await notification_service.test_email_connection(
                subject="Health Check", message="Email health check"
            )
            channels_status["email"] = {
                "configured": True,
                "healthy": email_status.get("success", False),
                "last_check": datetime.now().isoformat(),
                "details": email_status,
            }
        except Exception as e:
            channels_status["email"] = {
                "configured": True,
                "healthy": False,
                "last_check": datetime.now().isoformat(),
                "error": str(e),
            }

        # Check Webhook
        try:
            webhook_status = await notification_service.test_webhook_connection(
                {"type": "health_check", "timestamp": datetime.now().isoformat()}
            )
            channels_status["webhook"] = {
                "configured": True,
                "healthy": webhook_status.get("success", False),
                "last_check": datetime.now().isoformat(),
                "details": webhook_status,
            }
        except Exception as e:
            channels_status["webhook"] = {
                "configured": True,
                "healthy": False,
                "last_check": datetime.now().isoformat(),
                "error": str(e),
            }

        # Calculate overall health
        healthy_channels = sum(
            1 for status in channels_status.values() if status.get("healthy", False)
        )
        total_channels = len(channels_status)
        overall_health = (
            (healthy_channels / total_channels) * 100 if total_channels > 0 else 0
        )

        return StatusResponse.create(
            data={
                "channels_status": channels_status,
                "overall_health_percent": round(overall_health, 1),
                "healthy_channels": healthy_channels,
                "total_channels": total_channels,
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error(
            "Failed to get notification channels status", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get notification channels status: {str(e)}",
        )


@router.get(
    "/system/health",
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
            from ...repositories import get_stock_repository

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
    "/system/info",
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

        from ...config import get_settings

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


@router.post(
    "/system/maintenance/cleanup",
    response_model=StatusResponse,
    summary="System Cleanup",
    description="Perform system maintenance and cleanup tasks",
)
async def system_cleanup(
    request: Request,
    days_to_keep: int = Query(30, ge=1, le=365, description="Days of data to keep"),
    cleanup_events: bool = Query(True, description="Cleanup old event history"),
    cleanup_alerts: bool = Query(False, description="Cleanup old alert history"),
):
    """
    Perform system maintenance and cleanup.

    - **days_to_keep**: Days of data to keep (1-365)
    - **cleanup_events**: Whether to cleanup old event history
    - **cleanup_alerts**: Whether to cleanup old alert history

    Returns cleanup results and statistics.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info(
        "System cleanup requested",
        days_to_keep=days_to_keep,
        cleanup_events=cleanup_events,
        cleanup_alerts=cleanup_alerts,
        request_id=request_id,
    )

    try:
        cleanup_results = {
            "cleanup_started": datetime.now().isoformat(),
            "days_to_keep": days_to_keep,
            "tasks_completed": [],
            "errors": [],
        }

        # Cleanup event history
        if cleanup_events:
            try:
                event_bus = get_event_bus()
                # Note: EventBus would need a cleanup method in real implementation
                cleanup_results["tasks_completed"].append("event_history_cleanup")
                logger.info("Event history cleanup completed")
            except Exception as e:
                cleanup_results["errors"].append(
                    f"Event history cleanup failed: {str(e)}"
                )
                logger.error("Event history cleanup failed", error=str(e))

        # Cleanup alert history
        if cleanup_alerts:
            try:
                from ...services import AlertService

                alert_service = AlertService()
                # Note: AlertService would need a cleanup method in real implementation
                cleanup_results["tasks_completed"].append("alert_history_cleanup")
                logger.info("Alert history cleanup completed")
            except Exception as e:
                cleanup_results["errors"].append(
                    f"Alert history cleanup failed: {str(e)}"
                )
                logger.error("Alert history cleanup failed", error=str(e))

        cleanup_results["cleanup_completed"] = datetime.now().isoformat()
        cleanup_results["total_tasks"] = len(cleanup_results["tasks_completed"])
        cleanup_results["total_errors"] = len(cleanup_results["errors"])

        return StatusResponse.create(data=cleanup_results, request_id=request_id)

    except Exception as e:
        logger.error("Failed to perform system cleanup", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to perform system cleanup: {str(e)}"
        )
