"""Agent tools for stock tracking operations."""

from typing import List

from agents import function_tool

from ..db.repositories import AlertHistoryRepository, TrackedStockRepository
from .stock_checker import StockPriceResponse, get_stock_price


@function_tool
async def add_stock_to_tracker(symbol: str) -> str:
    """Add a stock symbol to the tracking list."""
    with TrackedStockRepository() as repo:
        existing_stock = repo.get_stock_by_symbol(symbol)

        if existing_stock is not None and bool(existing_stock.is_active):
            return f"{symbol.upper()} is already being tracked"

        stock = repo.add_stock(symbol)
        return f"Added {stock.symbol} to tracker list"


@function_tool
async def remove_stock_from_tracker(symbol: str) -> str:
    """Remove a stock symbol from the tracking list."""
    with TrackedStockRepository() as repo:
        if repo.remove_stock(symbol):
            return f"Removed {symbol.upper()} from tracker list"
        else:
            return f"{symbol.upper()} is not in tracker list or already removed"


@function_tool
async def get_tracked_stocks_list() -> List[str]:
    """Get the current list of tracked stocks."""
    with TrackedStockRepository() as repo:
        symbols = repo.get_stock_symbols()
        print("Getting tracker list:", symbols)
        return symbols


@function_tool
async def get_stock_price_info(symbol: str) -> StockPriceResponse:
    """Get current price information for a stock symbol."""
    return get_stock_price(symbol)


@function_tool
async def check_alert_history(symbol: str) -> List[str]:
    """Get alert history for a specific stock symbol."""
    with AlertHistoryRepository() as repo:
        alert_dates = repo.get_alert_dates_for_stock(symbol)
        return alert_dates


@function_tool
async def add_alert_to_history(
    symbol: str, alert_date: str, message_content: str = ""
) -> str:
    """Add an alert to the history for tracking purposes."""
    with AlertHistoryRepository() as repo:
        if repo.has_alert_been_sent(symbol, alert_date):
            return f"Alert for {symbol.upper()} on {alert_date} already exists"

        alert = repo.add_alert(
            symbol, alert_date, message_content=message_content or None
        )
        return f"Added alert for {symbol.upper()} on {alert_date}"
