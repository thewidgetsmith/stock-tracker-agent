"""API routes for penny stock speculation features."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ...config.logging import get_logger
from ...services.penny_stock import PennyStockService, ScreeningCriteria
from ...services.speculation import SpeculationService, TradeRequest
from ..models.responses import StatusResponse, SuccessResponse

logger = get_logger(__name__)

# Create router for penny stock endpoints
router = APIRouter(prefix="/penny-stocks", tags=["Penny Stocks"])


# Request/Response Models


class ScreeningRequest(BaseModel):
    """Request model for penny stock screening."""

    max_price: float = 5.00
    min_volume: int = 100000
    min_volatility_score: int = 1
    max_volatility_score: int = 10
    sector: Optional[str] = None
    max_results: int = 20


class PennyStockResponse(BaseModel):
    """Response model for penny stock data."""

    symbol: str
    current_price: float
    volatility_score: int
    volume_surge_ratio: float
    sector: Optional[str]
    market_cap: Optional[float]
    exchange: Optional[str]


class PortfolioCreateRequest(BaseModel):
    """Request model for creating a speculation portfolio."""

    user_id: str
    portfolio_name: str
    starting_balance: float = 10000.0
    strategy_type: Optional[str] = None
    description: Optional[str] = None


class TradeExecuteRequest(BaseModel):
    """Request model for executing trades."""

    portfolio_id: int
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: int


# Service Dependencies


def get_penny_stock_service() -> PennyStockService:
    """Dependency to get penny stock service instance."""
    return PennyStockService()


def get_speculation_service() -> SpeculationService:
    """Dependency to get speculation service instance."""
    return SpeculationService()


# Discovery Endpoints


@router.get(
    "/discover",
    response_model=StatusResponse,
    summary="Discover Trending Penny Stocks",
    description="Find trending penny stocks based on volatility and volume metrics",
)
async def discover_penny_stocks(
    request: Request,
    max_results: int = Query(20, description="Maximum number of results to return"),
    min_volatility: int = Query(1, description="Minimum volatility score (1-10)"),
    max_volatility: int = Query(10, description="Maximum volatility score (1-10)"),
    penny_service: PennyStockService = Depends(get_penny_stock_service),
):
    """
    Discover trending penny stocks with high volatility and volume.

    Returns a list of penny stocks sorted by interest score (volatility + volume surge).
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.info(
            "Discovering penny stocks", request_id=request_id, max_results=max_results
        )

        criteria = ScreeningCriteria(
            max_price=5.00,
            min_volatility_score=min_volatility,
            max_volatility_score=max_volatility,
            min_volume=50000,
        )

        candidates = await penny_service.discover_penny_stocks(criteria, max_results)

        # Convert to response format
        penny_stocks = []
        for candidate in candidates:
            penny_stocks.append(
                {
                    "symbol": candidate.symbol,
                    "current_price": candidate.current_price,
                    "volatility_score": candidate.volatility_score,
                    "volume_surge_ratio": candidate.volume_surge_ratio,
                    "sector": candidate.sector,
                    "market_cap": candidate.market_cap,
                    "exchange": candidate.exchange,
                    "price_change_24h": candidate.price_change_24h,
                }
            )

        return StatusResponse.create(
            data={
                "penny_stocks": penny_stocks,
                "total_found": len(penny_stocks),
                "criteria": {
                    "max_price": criteria.max_price,
                    "min_volatility": min_volatility,
                    "max_volatility": max_volatility,
                },
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error("Failed to discover penny stocks", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.post(
    "/screen",
    response_model=StatusResponse,
    summary="Screen Penny Stocks by Criteria",
    description="Screen penny stocks using custom filtering criteria",
)
async def screen_penny_stocks(
    screening_request: ScreeningRequest,
    request: Request,
    penny_service: PennyStockService = Depends(get_penny_stock_service),
):
    """
    Screen penny stocks by specific criteria.

    Allows detailed filtering by price, volume, volatility, sector, etc.
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.info("Screening penny stocks", request_id=request_id)

        criteria = ScreeningCriteria(
            max_price=screening_request.max_price,
            min_volume=screening_request.min_volume,
            min_volatility_score=screening_request.min_volatility_score,
            max_volatility_score=screening_request.max_volatility_score,
            sectors=[screening_request.sector] if screening_request.sector else None,
        )

        candidates = await penny_service.screen_by_criteria(criteria)
        candidates = candidates[: screening_request.max_results]

        # Convert to response format
        results = []
        for candidate in candidates:
            results.append(
                {
                    "symbol": candidate.symbol,
                    "current_price": candidate.current_price,
                    "volatility_score": candidate.volatility_score,
                    "volume_surge_ratio": candidate.volume_surge_ratio,
                    "sector": candidate.sector,
                    "market_cap": candidate.market_cap,
                }
            )

        return StatusResponse.create(
            data={
                "results": results,
                "total_found": len(results),
                "criteria_used": screening_request.dict(),
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error("Failed to screen penny stocks", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}")


@router.get(
    "/{symbol}/analysis",
    response_model=StatusResponse,
    summary="Get Penny Stock Analysis",
    description="Get detailed volatility and risk analysis for a specific penny stock",
)
async def get_penny_stock_analysis(
    symbol: str,
    request: Request,
    penny_service: PennyStockService = Depends(get_penny_stock_service),
):
    """
    Get comprehensive analysis for a specific penny stock.

    Returns volatility metrics, price ranges, recent news, and risk assessment.
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.info(f"Analyzing penny stock {symbol}", request_id=request_id)

        # Get volatility metrics
        volatility = await penny_service.get_volatility_metrics(symbol)
        if not volatility:
            raise HTTPException(
                status_code=404, detail=f"Analysis not available for {symbol}"
            )

        # Get recent news
        news = await penny_service.get_penny_stock_news(symbol, max_articles=5)

        analysis_data = {
            "symbol": volatility.symbol,
            "current_price": volatility.current_price,
            "volatility_metrics": {
                "volatility_30d": volatility.volatility_30d,
                "volatility_score": volatility.volatility_score,
                "avg_daily_move": volatility.avg_daily_move,
                "volume_volatility": volatility.volume_volatility,
                "price_range_30d": {
                    "min": volatility.price_range_30d[0],
                    "max": volatility.price_range_30d[1],
                },
                "last_spike_date": (
                    volatility.last_spike_date.isoformat()
                    if volatility.last_spike_date
                    else None
                ),
            },
            "recent_news": news,
            "analysis_timestamp": datetime.now().isoformat(),
        }

        return StatusResponse.create(data=analysis_data, request_id=request_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze {symbol}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# Virtual Trading Endpoints


@router.post(
    "/speculation/portfolio",
    response_model=StatusResponse,
    summary="Create Speculation Portfolio",
    description="Create a new virtual trading portfolio for penny stock speculation",
)
async def create_speculation_portfolio(
    portfolio_request: PortfolioCreateRequest,
    request: Request,
    speculation_service: SpeculationService = Depends(get_speculation_service),
):
    """
    Create a new virtual trading portfolio.

    Portfolios start with virtual money for risk-free penny stock trading simulation.
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.info("Creating speculation portfolio", request_id=request_id)

        portfolio_id = await speculation_service.create_virtual_portfolio(
            user_id=portfolio_request.user_id,
            portfolio_name=portfolio_request.portfolio_name,
            starting_balance=Decimal(str(portfolio_request.starting_balance)),
            strategy_type=portfolio_request.strategy_type,
            description=portfolio_request.description,
        )

        return StatusResponse.create(
            data={
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio_request.portfolio_name,
                "starting_balance": portfolio_request.starting_balance,
                "message": f"Portfolio '{portfolio_request.portfolio_name}' created successfully",
            },
            request_id=request_id,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create portfolio", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Portfolio creation failed: {str(e)}"
        )


@router.post(
    "/speculation/trade",
    response_model=StatusResponse,
    summary="Execute Virtual Trade",
    description="Execute a virtual buy or sell order in a speculation portfolio",
)
async def execute_virtual_trade(
    trade_request: TradeExecuteRequest,
    request: Request,
    speculation_service: SpeculationService = Depends(get_speculation_service),
):
    """
    Execute a virtual trade (buy or sell) in a speculation portfolio.

    All trades use current market prices with simulated transaction fees.
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.info("Executing virtual trade", request_id=request_id)

        trade_req = TradeRequest(
            portfolio_id=trade_request.portfolio_id,
            symbol=trade_request.symbol.upper(),
            action=trade_request.action.upper(),
            quantity=trade_request.quantity,
        )

        result = await speculation_service.execute_virtual_trade(trade_req)

        if result.success:
            return StatusResponse.create(
                data={
                    "trade_id": result.trade_id,
                    "symbol": trade_request.symbol.upper(),
                    "action": trade_request.action.upper(),
                    "quantity": trade_request.quantity,
                    "executed_price": (
                        float(result.executed_price) if result.executed_price else None
                    ),
                    "total_amount": (
                        float(result.total_amount) if result.total_amount else None
                    ),
                    "portfolio_balance": float(result.portfolio_balance),
                    "message": f"{trade_request.action.upper()} order executed successfully",
                },
                request_id=request_id,
            )
        else:
            raise HTTPException(status_code=400, detail=result.error_message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to execute trade", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")


@router.get(
    "/speculation/portfolio/{portfolio_id}",
    response_model=StatusResponse,
    summary="Get Portfolio Performance",
    description="Get detailed performance report for a speculation portfolio",
)
async def get_portfolio_performance(
    portfolio_id: int,
    request: Request,
    speculation_service: SpeculationService = Depends(get_speculation_service),
):
    """
    Get comprehensive portfolio performance report.

    Returns current positions, performance metrics, recent trades, and risk analysis.
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.info(
            f"Getting portfolio performance for {portfolio_id}", request_id=request_id
        )

        performance = await speculation_service.get_portfolio_performance(portfolio_id)

        if not performance:
            raise HTTPException(
                status_code=404, detail=f"Portfolio {portfolio_id} not found"
            )

        # Convert to response format
        portfolio_data = {
            "portfolio_summary": {
                "portfolio_id": performance.portfolio_summary.portfolio_id,
                "portfolio_name": performance.portfolio_summary.portfolio_name,
                "total_value": float(performance.portfolio_summary.total_value),
                "cash_balance": float(performance.portfolio_summary.cash_balance),
                "invested_amount": float(performance.portfolio_summary.invested_amount),
                "total_return_pct": performance.portfolio_summary.total_return_pct,
                "num_positions": performance.portfolio_summary.num_positions,
                "largest_position_pct": performance.portfolio_summary.largest_position_pct,
                "risk_score": performance.portfolio_summary.risk_score,
            },
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_cost_basis": float(pos.avg_cost_basis),
                    "current_price": float(pos.current_price),
                    "current_value": float(pos.current_value),
                    "unrealized_pnl": float(pos.unrealized_pnl),
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                    "position_pct": pos.position_pct,
                }
                for pos in performance.positions
            ],
            "recent_trades": performance.recent_trades,
            "risk_metrics": performance.risk_metrics,
        }

        return StatusResponse.create(data=portfolio_data, request_id=request_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get portfolio performance", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Performance retrieval failed: {str(e)}"
        )


@router.get(
    "/speculation/leaderboard",
    response_model=StatusResponse,
    summary="Get Speculation Leaderboard",
    description="Get top performing speculation portfolios leaderboard",
)
async def get_speculation_leaderboard(
    request: Request,
    limit: int = Query(10, description="Number of top performers to return"),
    period: str = Query("all_time", description="Time period for rankings"),
    speculation_service: SpeculationService = Depends(get_speculation_service),
):
    """
    Get leaderboard of top performing speculation portfolios.

    Rankings based on total return percentage with risk-adjusted metrics.
    """
    request_id = getattr(request.state, "request_id", None)

    try:
        logger.info("Getting speculation leaderboard", request_id=request_id)

        rankings = await speculation_service.get_leaderboard(period=period, limit=limit)

        leaderboard_data = {
            "rankings": [
                {
                    "rank": ranking.rank,
                    "user_id": ranking.user_id,
                    "portfolio_name": ranking.portfolio_name,
                    "total_return_pct": ranking.total_return_pct,
                    "total_value": float(ranking.total_value),
                    "risk_adjusted_return": ranking.risk_adjusted_return,
                    "num_trades": ranking.num_trades,
                    "win_rate": ranking.win_rate,
                }
                for ranking in rankings
            ],
            "period": period,
            "total_entries": len(rankings),
        }

        return StatusResponse.create(data=leaderboard_data, request_id=request_id)

    except Exception as e:
        logger.error("Failed to get leaderboard", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Leaderboard retrieval failed: {str(e)}"
        )


# Import required for Decimal usage
from decimal import Decimal
