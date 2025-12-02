"""Notification sending endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ....config.logging import get_logger
from ....events import NotificationSentEvent, get_event_bus
from ....services import NotificationService
from ...models.responses import StatusResponse

logger = get_logger(__name__)

# Create router for notification sending operations
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


@router.post(
    "",
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
