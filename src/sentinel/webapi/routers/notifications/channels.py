"""Notification channel testing and management endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ....config.logging import get_logger
from ....events import NotificationSentEvent, get_event_bus
from ....services import NotificationService
from ...exceptions import ValidationException
from ...models.responses import StatusResponse

logger = get_logger(__name__)

# Create router for channel operations
router = APIRouter()


# Service dependencies
def get_notification_service() -> NotificationService:
    """Dependency to get notification service instance."""
    return NotificationService()


# Pydantic models
class TestNotificationRequest(BaseModel):
    """Request model for testing notifications."""

    channel: str = Field(..., description="Channel to test (telegram, email, webhook)")
    test_message: str = Field(
        "Test notification from Sentry Agents", description="Test message content"
    )


@router.post(
    "/test",
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
    "/status",
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
