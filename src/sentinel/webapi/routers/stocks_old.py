"""Enhanced API endpoints using service layer and event-driven architecture."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...config.logging import get_logger
from ...events import (
    StockAddedToTrackingEvent,
    StockPriceChangedEvent,
    StockRemovedFromTrackingEvent,
    get_event_bus,
)
from ...services import NotificationService, StockTrackingService
from ...services.stock_tracking.service import MovementThreshold
from ..exceptions import NotFoundError, ValidationException
from ..models.requests import PaginationParams, StockSymbolRequest
from ..models.responses import StatusResponse, StockDataResponse, SuccessResponse

logger = get_logger(__name__)

# Create router for stock-related endpoints
router = APIRouter()


# Service dependencies
def get_stock_tracking_service() -> StockTrackingService:
    """Dependency to get stock tracking service instance."""
    return StockTrackingService()


def get_notification_service() -> NotificationService:
    """Dependency to get notification service instance."""
    return NotificationService()


@router.get(
    "/stocks/{symbol}",
    response_model=StockDataResponse,
    summary="Get Stock Price",
    description="Get current price information for a stock symbol",
)
async def get_stock_price(
    symbol: str,
    request: Request,
    stock_service: StockTrackingService = Depends(get_stock_tracking_service),
):
    """
    Get current stock price information.

    - **symbol**: Stock symbol (e.g., AAPL, GOOGL, MSFT)

    Returns current price, previous close, change amount, and percentage change.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info("Stock price requested", symbol=symbol, request_id=request_id)

    try:
        stock_data = await stock_service.get_stock_price(symbol)

        # Publish price fetched event (could be useful for caching, analytics)
        event_bus = get_event_bus()
        await event_bus.publish(
            StockPriceChangedEvent(
                symbol=symbol,
                previous_price=stock_data.previous_close or 0,
                current_price=stock_data.current_price,
                price_change=stock_data.current_price
                - (stock_data.previous_close or 0),
                price_change_percent=(
                    (stock_data.current_price / (stock_data.previous_close or 1)) - 1
                ),
                volume=stock_data.volume,
                market_cap=stock_data.market_cap,
                is_significant_movement=False,  # Just a price fetch, not a movement alert
            )
        )

        return StockDataResponse(success=True, data=stock_data, request_id=request_id)

    except ValueError as e:
        raise ValidationException(str(e), request_id=request_id)
    except Exception as e:
        logger.error(
            "Failed to fetch stock price", symbol=symbol, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch stock price: {str(e)}"
        )


@router.post(
    "/stocks/{symbol}/analyze",
    response_model=StatusResponse,
    summary="Analyze Stock Movement",
    description="Analyze stock price movement and trigger alerts if significant",
)
async def analyze_stock_movement(
    symbol: str,
    request: Request,
    threshold: Optional[str] = Query(
        "moderate",
        description="Movement threshold: minor, moderate, significant, major",
    ),
    stock_service: StockTrackingService = Depends(get_stock_tracking_service),
):
    """
    Analyze stock price movement and determine significance.

    - **symbol**: Stock symbol to analyze
    - **threshold**: Movement threshold for significance detection

    Triggers alerts and events if movement is significant.
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
        "Stock movement analysis requested",
        symbol=symbol,
        threshold=threshold,
        request_id=request_id,
    )

    try:
        analysis = await stock_service.analyze_stock_movement(
            symbol, movement_threshold
        )

        # Publish stock price changed event if movement is significant
        if analysis.is_significant_movement:
            event_bus = get_event_bus()
            await event_bus.publish(
                StockPriceChangedEvent(
                    symbol=analysis.symbol,
                    previous_price=analysis.previous_close,
                    current_price=analysis.current_price,
                    price_change=analysis.price_change,
                    price_change_percent=analysis.price_change_percent,
                    volume=analysis.volume,
                    market_cap=analysis.market_cap,
                    is_significant_movement=True,
                    movement_threshold=movement_threshold.value,
                )
            )

        return StatusResponse.create(
            data={
                "symbol": analysis.symbol,
                "current_price": analysis.current_price,
                "previous_close": analysis.previous_close,
                "price_change": analysis.price_change,
                "price_change_percent": analysis.price_change_percent,
                "is_significant_movement": analysis.is_significant_movement,
                "movement_threshold": movement_threshold.value,
                "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
            },
            request_id=request_id,
        )

    except ValueError as e:
        raise ValidationException(str(e), request_id=request_id)
    except Exception as e:
        logger.error(
            "Failed to analyze stock movement",
            symbol=symbol,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze stock movement: {str(e)}"
        )


@router.post(
    "/tracking/stocks",
    response_model=StatusResponse,
    summary="Add Stock to Tracking",
    description="Add a stock symbol to the tracking portfolio",
)
async def add_stock_to_tracking(
    stock_request: StockSymbolRequest,
    request: Request,
    stock_service: StockTrackingService = Depends(get_stock_tracking_service),
):
    """
    Add a stock to the tracking portfolio.

    - **symbol**: Stock symbol to add to tracking

    Validates the symbol and adds it to the portfolio if valid.
    """
    request_id = getattr(request.state, "request_id", None)
    symbol = stock_request.symbol

    logger.info("Add stock to tracking requested", symbol=symbol, request_id=request_id)

    try:
        result = await stock_service.add_stock_to_tracking(symbol)

        if result["success"]:
            # Publish stock added event
            event_bus = get_event_bus()
            await event_bus.publish(
                StockAddedToTrackingEvent(
                    symbol=symbol,
                    added_by="api",  # Could be extracted from auth context
                    validation_passed=True,
                )
            )

        return StatusResponse.create(data=result, request_id=request_id)

    except ValueError as e:
        raise ValidationException(str(e), request_id=request_id)
    except Exception as e:
        logger.error(
            "Failed to add stock to tracking",
            symbol=symbol,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to add stock to tracking: {str(e)}"
        )


@router.delete(
    "/tracking/stocks/{symbol}",
    response_model=StatusResponse,
    summary="Remove Stock from Tracking",
    description="Remove a stock symbol from the tracking portfolio",
)
async def remove_stock_from_tracking(
    symbol: str,
    request: Request,
    stock_service: StockTrackingService = Depends(get_stock_tracking_service),
):
    """
    Remove a stock from the tracking portfolio.

    - **symbol**: Stock symbol to remove from tracking

    Deactivates the stock in the tracking portfolio.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info(
        "Remove stock from tracking requested", symbol=symbol, request_id=request_id
    )

    try:
        result = await stock_service.remove_stock_from_tracking(symbol)

        if result["success"]:
            # Publish stock removed event
            event_bus = get_event_bus()
            await event_bus.publish(
                StockRemovedFromTrackingEvent(
                    symbol=symbol,
                    removed_by="api",  # Could be extracted from auth context
                    was_active=True,
                )
            )

        return StatusResponse.create(data=result, request_id=request_id)

    except ValueError as e:
        raise ValidationException(str(e), request_id=request_id)
    except Exception as e:
        logger.error(
            "Failed to remove stock from tracking",
            symbol=symbol,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to remove stock from tracking: {str(e)}"
        )


@router.get(
    "/tracking/portfolio",
    response_model=StatusResponse,
    summary="Get Tracking Portfolio",
    description="Get the current tracking portfolio with all tracked stocks",
)
async def get_tracking_portfolio(
    request: Request,
    stock_service: StockTrackingService = Depends(get_stock_tracking_service),
):
    """
    Get the current tracking portfolio.

    Returns list of tracked stocks with portfolio metadata.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info("Tracking portfolio requested", request_id=request_id)

    try:
        portfolio = await stock_service.get_tracking_portfolio()

        return StatusResponse.create(
            data={
                "tracked_stocks": portfolio.tracked_stocks,
                "total_count": portfolio.total_count,
                "active_count": portfolio.active_count,
                "last_updated": portfolio.last_updated.isoformat(),
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error("Failed to get tracking portfolio", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get tracking portfolio: {str(e)}"
        )


@router.get(
    "/tracking/portfolio/summary",
    response_model=StatusResponse,
    summary="Get Portfolio Summary",
    description="Get comprehensive portfolio summary with performance metrics",
)
async def get_portfolio_summary(
    request: Request,
    stock_service: StockTrackingService = Depends(get_stock_tracking_service),
):
    """
    Get comprehensive portfolio tracking summary.

    Returns portfolio metrics, performance data, and individual stock details.
    """
    request_id = getattr(request.state, "request_id", None)

    logger.info("Portfolio summary requested", request_id=request_id)

    try:
        summary = await stock_service.get_portfolio_summary()

        return StatusResponse.create(data=summary, request_id=request_id)

    except Exception as e:
        logger.error("Failed to get portfolio summary", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get portfolio summary: {str(e)}"
        )


@router.post(
    "/tracking/analyze-all",
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


@router.get(
    "/alerts/history",
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
