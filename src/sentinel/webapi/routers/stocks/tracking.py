"""Stock tracking CRUD operations endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ....config.logging import get_logger
from ....events import (
    StockAddedToTrackingEvent,
    StockRemovedFromTrackingEvent,
    get_event_bus,
)
from ....services import StockTrackingService
from ...exceptions import ValidationException
from ...models.requests import StockSymbolRequest
from ...models.responses import StatusResponse

logger = get_logger(__name__)

# Create router for stock tracking operations
router = APIRouter()


# Service dependencies
def get_stock_tracking_service() -> StockTrackingService:
    """Dependency to get stock tracking service instance."""
    return StockTrackingService()


@router.post(
    "",
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
    "/{symbol}",
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
