"""Stock price and analysis endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ....config.logging import get_logger
from ....events import StockPriceChangedEvent, get_event_bus
from ....services import StockTrackingService
from ....services.stock_tracking.service import MovementThreshold
from ...exceptions import ValidationException
from ...models.responses import StatusResponse, StockDataResponse

logger = get_logger(__name__)

# Create router for stock price operations
router = APIRouter()


# Service dependencies
def get_stock_tracking_service() -> StockTrackingService:
    """Dependency to get stock tracking service instance."""
    return StockTrackingService()


@router.get(
    "/{symbol}",
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
    "/{symbol}/analyze",
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
