"""Alert and event history endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ....config.logging import get_logger
from ....events import get_event_bus
from ....services import NotificationService
from ...models.responses import StatusResponse

logger = get_logger(__name__)

# Create router for history operations
router = APIRouter()


# Service dependencies
def get_notification_service() -> NotificationService:
    """Dependency to get notification service instance."""
    return NotificationService()


@router.get(
    "/alerts",
    response_model=StatusResponse,
    summary="Get Alert History",
    description="Get alert history for a symbol or all symbols",
)
async def get_alert_history(
    request: Request,
    symbol: Optional[str] = Query(None, description="Stock symbol to filter by"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """
    Get alert history.

    - **symbol**: Optional stock symbol to filter by
    - **days_back**: Number of days to look back (1-365)

    Returns historical alert data.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info(
        "Alert history requested",
        symbol=symbol,
        days_back=days_back,
        request_id=request_id,
    )

    try:
        history = await notification_service.get_alert_history(symbol, days_back)

        # Convert to serializable format
        history_data = [
            {
                "symbol": h.symbol,
                "alert_date": h.alert_date,
                "alert_type": h.alert_type,
                "message_content": h.message_content,
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ]

        return StatusResponse.create(
            data={
                "alert_history": history_data,
                "total_count": len(history_data),
                "days_back": days_back,
                "filtered_by_symbol": symbol,
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error("Failed to get alert history", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get alert history: {str(e)}"
        )


@router.get(
    "/events/statistics",
    response_model=StatusResponse,
    summary="Get Event Bus Statistics",
    description="Get event bus statistics and metrics",
)
async def get_event_statistics(request: Request):
    """
    Get event bus statistics and metrics.

    Returns information about event processing, handlers, and system activity.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info("Event statistics requested", request_id=request_id)

    try:
        event_bus = get_event_bus()
        stats = event_bus.get_statistics()

        return StatusResponse.create(
            data={"event_bus_statistics": stats, "event_bus_name": event_bus.name},
            request_id=request_id,
        )

    except Exception as e:
        logger.error("Failed to get event statistics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get event statistics: {str(e)}"
        )


@router.get(
    "/events/history",
    response_model=StatusResponse,
    summary="Get Event History",
    description="Get recent event history from the event bus",
)
async def get_event_history(
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Number of events to return"),
):
    """
    Get recent event history.

    - **limit**: Number of events to return (1-500)

    Returns recent domain events processed by the system.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info("Event history requested", limit=limit, request_id=request_id)

    try:
        event_bus = get_event_bus()
        history = event_bus.get_event_history(limit)

        return StatusResponse.create(
            data={
                "event_history": history,
                "returned_count": len(history),
                "requested_limit": limit,
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error("Failed to get event history", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get event history: {str(e)}"
        )
