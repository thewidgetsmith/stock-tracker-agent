"""Bulk stock tracking operations endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ....config.logging import get_logger
from ....events import StockPriceChangedEvent, get_event_bus
from ....services import StockTrackingService
from ....services.stock_tracking.service import MovementThreshold
from ...models.responses import StatusResponse

logger = get_logger(__name__)

# Create router for bulk operations
router = APIRouter()


# Service dependencies
def get_stock_tracking_service() -> StockTrackingService:
    """Dependency to get stock tracking service instance."""
    return StockTrackingService()


@router.post(
    "/analyze-all",
    response_model=StatusResponse,
    summary="Analyze All Tracked Stocks",
    description="Analyze all stocks in tracking portfolio for significant movements",
)
async def analyze_all_tracked_stocks(
    request: Request,
    threshold: Optional[str] = Query("moderate", description="Movement threshold"),
    stock_service: StockTrackingService = Depends(get_stock_tracking_service),
):
    """
    Analyze all stocks in the tracking portfolio.

    - **threshold**: Movement threshold for significance detection

    Returns analysis results and triggers alerts for significant movements.
    """
    request_id = getattr(request.state, "request_id", None)

    # Map threshold string to enum
    threshold_map = {
        "minor": MovementThreshold.MINOR,
        "moderate": MovementThreshold.MODERATE,
        "significant": MovementThreshold.SIGNIFICANT,
        "major": MovementThreshold.MAJOR,
    }

    movement_threshold = threshold_map.get(
        threshold.lower(), MovementThreshold.MODERATE
    )

    logger.info(
        "Portfolio analysis requested", threshold=threshold, request_id=request_id
    )

    try:
        results = await stock_service.track_all_stocks(movement_threshold)

        # Process results and trigger events for significant movements
        event_bus = get_event_bus()
        significant_movements = 0

        for result in results:
            if result.alert_triggered and result.analysis:
                significant_movements += 1

                # Publish stock price changed event
                await event_bus.publish(
                    StockPriceChangedEvent(
                        symbol=result.analysis.symbol,
                        previous_price=result.analysis.previous_close,
                        current_price=result.analysis.current_price,
                        price_change=result.analysis.price_change,
                        price_change_percent=result.analysis.price_change_percent,
                        volume=result.analysis.volume,
                        market_cap=result.analysis.market_cap,
                        is_significant_movement=True,
                        movement_threshold=movement_threshold.value,
                    )
                )

        # Prepare response data
        response_data = {
            "total_stocks_analyzed": len(results),
            "significant_movements": significant_movements,
            "movement_threshold": movement_threshold.value,
            "analysis_results": [
                {
                    "symbol": result.symbol,
                    "alert_triggered": result.alert_triggered,
                    "processing_time_ms": result.processing_time_ms,
                    "error": result.error,
                    "analysis": (
                        {
                            "current_price": result.analysis.current_price,
                            "price_change_percent": result.analysis.price_change_percent,
                            "is_significant_movement": result.analysis.is_significant_movement,
                        }
                        if result.analysis
                        else None
                    ),
                }
                for result in results
            ],
        }

        return StatusResponse.create(data=response_data, request_id=request_id)

    except Exception as e:
        logger.error("Failed to analyze tracked stocks", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze tracked stocks: {str(e)}"
        )
