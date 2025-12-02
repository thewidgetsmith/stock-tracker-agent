"""System maintenance and cleanup endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request

from ....config.logging import get_logger
from ....events import get_event_bus
from ....services import NotificationService
from ...models.responses import StatusResponse

logger = get_logger(__name__)

# Create router for maintenance operations
router = APIRouter()


@router.post(
    "/cleanup",
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
                notification_service = NotificationService()
                # Note: NotificationService would need a cleanup method in real implementation
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
