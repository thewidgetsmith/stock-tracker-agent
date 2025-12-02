"""Stock portfolio viewing and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from ....config.logging import get_logger
from ....services import StockTrackingService
from ...models.responses import StatusResponse

logger = get_logger(__name__)

# Create router for portfolio operations
router = APIRouter()


# Service dependencies
def get_stock_tracking_service() -> StockTrackingService:
    """Dependency to get stock tracking service instance."""
    return StockTrackingService()


@router.get(
    "",
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
    "/summary",
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
