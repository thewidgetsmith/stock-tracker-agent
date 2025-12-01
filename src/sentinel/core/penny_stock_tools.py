"""Agent tools for penny stock discovery and virtual trading."""

from typing import List, Optional

from pydantic import BaseModel

from ..config.logging import get_logger
from ..services.penny_stock import PennyStockService, ScreeningCriteria
from ..services.speculation import SpeculationService, TradeRequest
from .tools import function_tool

logger = get_logger(__name__)


class PennyStockResult(BaseModel):
    """Result model for penny stock discovery."""

    symbol: str
    current_price: float
    volatility_score: int
    volume_surge_ratio: float
    sector: str
    market_cap: Optional[int]


class PortfolioInfo(BaseModel):
    """Portfolio information model."""

    portfolio_id: int
    name: str
    total_value: float
    cash_balance: float
    total_return_pct: float
    num_positions: int


class TradeInfo(BaseModel):
    """Trade execution result model."""

    success: bool
    message: str
    executed_price: Optional[float]
    new_balance: float


# Penny Stock Discovery Tools


@function_tool
async def discover_trending_penny_stocks(
    max_results: int = 20, min_volatility: int = 1, max_volatility: int = 10
) -> List[str]:
    """
    Discover trending penny stocks with high volatility and volume.

    Args:
        max_results: Maximum number of stocks to return (default 20)
        min_volatility: Minimum volatility score 1-10 (default 1)
        max_volatility: Maximum volatility score 1-10 (default 10)

    Returns:
        List of trending penny stock information
    """
    try:
        service = PennyStockService()

        criteria = ScreeningCriteria(
            max_price=5.00,
            min_volatility_score=min_volatility,
            max_volatility_score=max_volatility,
            min_volume=50000,
        )

        candidates = await service.discover_penny_stocks(criteria, max_results)

        if not candidates:
            return ["No trending penny stocks found matching criteria."]

        results = []
        for candidate in candidates:
            result = (
                f"{candidate.symbol}: ${candidate.current_price:.4f} "
                f"(Volatility: {candidate.volatility_score}/10, "
                f"Volume surge: {candidate.volume_surge_ratio:.1f}x, "
                f"Sector: {candidate.sector})"
            )
            results.append(result)

        logger.info(f"Discovered {len(results)} trending penny stocks")
        return results

    except Exception as e:
        logger.error(f"Failed to discover penny stocks: {e}")
        return [f"Error discovering penny stocks: {str(e)}"]


@function_tool
async def screen_penny_stocks(
    sector: Optional[str] = None,
    max_price: float = 5.00,
    min_volume: int = 100000,
    min_volatility: int = 3,
) -> List[str]:
    """
    Screen penny stocks by specific criteria.

    Args:
        sector: Industry sector to focus on (optional)
        max_price: Maximum stock price (default $5.00)
        min_volume: Minimum daily volume (default 100,000)
        min_volatility: Minimum volatility score 1-10 (default 3)

    Returns:
        List of penny stocks matching criteria
    """
    try:
        service = PennyStockService()

        criteria = ScreeningCriteria(
            max_price=max_price,
            min_volume=min_volume,
            min_volatility_score=min_volatility,
            sectors=[sector] if sector else None,
        )

        candidates = await service.screen_by_criteria(criteria)

        if not candidates:
            return [
                f"No penny stocks found matching criteria (sector={sector}, max_price=${max_price}, min_volume={min_volume})."
            ]

        results = []
        for candidate in candidates:
            result = (
                f"{candidate.symbol}: ${candidate.current_price:.4f} "
                f"({candidate.sector}, Vol: {candidate.volatility_score}/10)"
            )
            results.append(result)

        logger.info(f"Screened {len(results)} penny stocks")
        return results

    except Exception as e:
        logger.error(f"Failed to screen penny stocks: {e}")
        return [f"Error screening penny stocks: {str(e)}"]


@function_tool
async def get_penny_stock_analysis(symbol: str) -> List[str]:
    """
    Get detailed analysis for a specific penny stock.

    Args:
        symbol: Stock symbol to analyze

    Returns:
        Detailed analysis information
    """
    try:
        service = PennyStockService()

        # Get volatility metrics
        volatility = await service.get_volatility_metrics(symbol)
        if not volatility:
            return [
                f"Unable to analyze {symbol} - insufficient data or not a penny stock."
            ]

        # Get news
        news = await service.get_penny_stock_news(symbol, max_articles=3)

        results = [
            f"=== {symbol} Analysis ===",
            f"Current Price: ${volatility.current_price:.4f}",
            f"30-Day Volatility: {volatility.volatility_30d:.1%}",
            f"Excitement Score: {volatility.volatility_score}/10",
            f"Average Daily Move: {volatility.avg_daily_move:.1%}",
            f"30-Day Price Range: ${volatility.price_range_30d[0]:.4f} - ${volatility.price_range_30d[1]:.4f}",
        ]

        if volatility.last_spike_date:
            results.append(
                f"Last Major Move: {volatility.last_spike_date.strftime('%Y-%m-%d')}"
            )

        if news:
            results.append("\n=== Recent News ===")
            for article in news:
                results.append(f"• {article['title']} ({article['source']})")

        logger.info(f"Generated analysis for {symbol}")
        return results

    except Exception as e:
        logger.error(f"Failed to analyze {symbol}: {e}")
        return [f"Error analyzing {symbol}: {str(e)}"]


# Virtual Trading Tools


@function_tool
async def create_speculation_portfolio(
    user_id: str,
    portfolio_name: str,
    starting_balance: float = 10000.0,
    strategy_type: Optional[str] = None,
) -> str:
    """
    Create a new virtual trading portfolio for penny stock speculation.

    Args:
        user_id: User identifier
        portfolio_name: Name for the portfolio
        starting_balance: Starting virtual balance in dollars (default $10,000)
        strategy_type: Portfolio strategy type (optional)

    Returns:
        Success message with portfolio ID
    """
    try:
        service = SpeculationService()

        portfolio_id = await service.create_virtual_portfolio(
            user_id=user_id,
            portfolio_name=portfolio_name,
            starting_balance=Decimal(str(starting_balance)),
            strategy_type=strategy_type,
        )

        logger.info(f"Created portfolio for {user_id}: {portfolio_name}")
        return f"✅ Created portfolio '{portfolio_name}' (ID: {portfolio_id}) with ${starting_balance:,.2f} virtual dollars!"

    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        logger.error(f"Failed to create portfolio: {e}")
        return f"❌ Error creating portfolio: {str(e)}"


@function_tool
async def virtual_buy_stock(portfolio_id: int, symbol: str, quantity: int) -> str:
    """
    Execute a virtual buy order for a stock.

    Args:
        portfolio_id: Portfolio ID to trade in
        symbol: Stock symbol to buy
        quantity: Number of shares to buy

    Returns:
        Trade execution result
    """
    try:
        service = SpeculationService()

        trade_request = TradeRequest(
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            action="BUY",
            quantity=quantity,
        )

        result = await service.execute_virtual_trade(trade_request)

        if result.success:
            return (
                f"✅ BUY ORDER FILLED\n"
                f"Symbol: {symbol.upper()}\n"
                f"Quantity: {quantity:,} shares\n"
                f"Price: ${result.executed_price:.4f}\n"
                f"Total Cost: ${result.total_amount:.2f}\n"
                f"Remaining Balance: ${result.portfolio_balance:.2f}"
            )
        else:
            return f"❌ Buy order failed: {result.error_message}"

    except Exception as e:
        logger.error(f"Failed to execute buy order: {e}")
        return f"❌ Error executing buy order: {str(e)}"


@function_tool
async def virtual_sell_stock(portfolio_id: int, symbol: str, quantity: int) -> str:
    """
    Execute a virtual sell order for a stock.

    Args:
        portfolio_id: Portfolio ID to trade in
        symbol: Stock symbol to sell
        quantity: Number of shares to sell

    Returns:
        Trade execution result
    """
    try:
        service = SpeculationService()

        trade_request = TradeRequest(
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            action="SELL",
            quantity=quantity,
        )

        result = await service.execute_virtual_trade(trade_request)

        if result.success:
            return (
                f"✅ SELL ORDER FILLED\n"
                f"Symbol: {symbol.upper()}\n"
                f"Quantity: {quantity:,} shares\n"
                f"Price: ${result.executed_price:.4f}\n"
                f"Proceeds: ${result.total_amount:.2f}\n"
                f"New Balance: ${result.portfolio_balance:.2f}"
            )
        else:
            return f"❌ Sell order failed: {result.error_message}"

    except Exception as e:
        logger.error(f"Failed to execute sell order: {e}")
        return f"❌ Error executing sell order: {str(e)}"


@function_tool
async def get_portfolio_status(portfolio_id: int) -> List[str]:
    """
    Get current portfolio status and performance.

    Args:
        portfolio_id: Portfolio ID to check

    Returns:
        Portfolio status information
    """
    try:
        service = SpeculationService()

        performance = await service.get_portfolio_performance(portfolio_id)

        if not performance:
            return [f"Portfolio {portfolio_id} not found."]

        portfolio = performance.portfolio_summary

        results = [
            f"=== {portfolio.portfolio_name} ===",
            f"Total Value: ${portfolio.total_value:,.2f}",
            f"Cash Balance: ${portfolio.cash_balance:,.2f}",
            f"Invested: ${portfolio.invested_amount:,.2f}",
            f"Total Return: {portfolio.total_return_pct:+.2f}%",
            f"Positions: {portfolio.num_positions}",
            f"Risk Score: {portfolio.risk_score}/10",
        ]

        if performance.positions:
            results.append("\n=== Current Positions ===")
            for position in performance.positions:
                pnl_indicator = (
                    "📈"
                    if position.unrealized_pnl > 0
                    else "📉" if position.unrealized_pnl < 0 else "➡️"
                )
                results.append(
                    f"{pnl_indicator} {position.symbol}: {position.quantity:,} shares @ ${position.avg_cost_basis:.4f} "
                    f"(Current: ${position.current_price:.4f}, P&L: {position.unrealized_pnl_pct:+.1f}%)"
                )

        if performance.recent_trades:
            results.append("\n=== Recent Trades ===")
            for trade in performance.recent_trades[:3]:
                action_icon = "🟢" if trade["action"] == "BUY" else "🔴"
                results.append(
                    f"{action_icon} {trade['action']} {trade['quantity']:,} {trade['symbol']} "
                    f"@ ${trade['price_per_share']:.4f}"
                )

        logger.info(f"Generated portfolio status for portfolio {portfolio_id}")
        return results

    except Exception as e:
        logger.error(f"Failed to get portfolio status: {e}")
        return [f"Error getting portfolio status: {str(e)}"]


@function_tool
async def get_speculation_leaderboard(limit: int = 10) -> List[str]:
    """
    Get the penny stock speculation leaderboard.

    Args:
        limit: Number of top performers to show (default 10)

    Returns:
        Leaderboard rankings
    """
    try:
        service = SpeculationService()

        rankings = await service.get_leaderboard(period="all_time", limit=limit)

        if not rankings:
            return ["No portfolios found for leaderboard."]

        results = ["🏆 === PENNY STOCK LEADERBOARD ===", ""]

        for ranking in rankings:
            rank_icon = (
                "🥇"
                if ranking.rank == 1
                else (
                    "🥈"
                    if ranking.rank == 2
                    else "🥉" if ranking.rank == 3 else f"{ranking.rank}."
                )
            )

            results.append(
                f"{rank_icon} {ranking.portfolio_name} "
                f"({ranking.user_id[:8]}...): {ranking.total_return_pct:+.1f}% "
                f"(${ranking.total_value:,.0f})"
            )

        logger.info(f"Generated leaderboard with {len(rankings)} entries")
        return results

    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        return [f"Error getting leaderboard: {str(e)}"]


@function_tool
async def get_user_portfolios(user_id: str) -> List[str]:
    """
    Get all portfolios for a user.

    Args:
        user_id: User identifier

    Returns:
        List of user's portfolios
    """
    try:
        service = SpeculationService()

        portfolios = await service.get_user_portfolios(user_id)

        if not portfolios:
            return [
                f"No portfolios found for user {user_id}. Use 'create_speculation_portfolio' to get started!"
            ]

        results = [f"=== Your Portfolios ==="]

        for portfolio in portfolios:
            return_indicator = (
                "📈"
                if portfolio.total_return_pct > 0
                else "📉" if portfolio.total_return_pct < 0 else "➡️"
            )
            results.append(
                f"{return_indicator} {portfolio.portfolio_name} (ID: {portfolio.portfolio_id}): "
                f"${portfolio.total_value:,.2f} ({portfolio.total_return_pct:+.1f}%) "
                f"- {portfolio.num_positions} positions"
            )

        return results

    except Exception as e:
        logger.error(f"Failed to get user portfolios: {e}")
        return [f"Error getting portfolios: {str(e)}"]


# Implementation helpers (not exposed as agent tools)

from decimal import Decimal
