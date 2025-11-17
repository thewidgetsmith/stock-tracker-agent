"""Agent tools for application data and tracking operations."""

from typing import List, Optional

from agents import function_tool

from ..config.logging import get_logger
from ..ormdb.repositories import (
    AlertHistoryRepository,
    PoliticianActivityRepository,
    PoliticianProfileRepository,
    TrackedPoliticianRepository,
    TrackedStockRepository,
)
from .stock_query import StockPriceResponse, get_stock_price

logger = get_logger(__name__)

# Business logic functions for tools separated for easier testing


async def add_alert_to_history_impl(
    symbol: str, alert_date: str, message_content: str = ""
) -> str:
    """Add an alert to the history for tracking purposes - implementation."""
    with AlertHistoryRepository() as repo:
        if repo.has_alert_been_sent(symbol, alert_date):
            return f"Alert for {symbol.upper()} on {alert_date} already exists"

        alert = repo.add_alert(
            symbol, alert_date, message_content=message_content or None
        )
        return f"Added alert for {symbol.upper()} on {alert_date}"


async def add_politician_to_tracker_impl(
    name: str, chamber: Optional[str] = None
) -> str:
    """Add a politician to the tracking list - implementation."""
    with TrackedPoliticianRepository() as repo:
        # Check if politician is already tracked
        if repo.is_politician_tracked(name):
            return f"{name} is already being tracked"

        # Auto-detect chamber if not provided (simplified logic)
        if chamber is None:
            chamber = "House"  # Default to House, could be enhanced with lookup

        politician = repo.add_tracked_politician(name, chamber)
        return f"Added {politician.politician.name} to politician tracker list"


async def add_stock_to_tracker_impl(symbol: str) -> str:
    """Add a stock symbol to the tracking list - implementation."""
    with TrackedStockRepository() as repo:
        existing_stock = repo.get_stock_by_symbol(symbol)

        if existing_stock is not None and bool(existing_stock.is_active):
            return f"{symbol.upper()} is already being tracked"

        stock = repo.add_stock(symbol)
        return f"Added {stock.symbol} to tracker list"


async def check_alert_history_impl(symbol: str) -> List[str]:
    """Get alert history for a specific stock symbol - implementation."""
    with AlertHistoryRepository() as repo:
        alert_dates = repo.get_alert_dates_for_stock(symbol)
        return alert_dates


async def get_politician_activity_info_impl(
    name: str, fetch_latest: bool = False
) -> List[str]:
    """Get trade activity for a specific politician - implementation."""
    # If requested, fetch latest data from API first
    if fetch_latest:
        try:
            # Import here to avoid circular imports
            from ..config.settings import get_settings
            from ..services.congressional_service import CongressionalService

            settings = get_settings()
            if hasattr(settings, "quiver_api_token") and settings.quiver_api_token:
                service = CongressionalService(settings.quiver_api_token)
                await service.get_congressional_trades(
                    representative=name, days_back=30, save_to_db=True
                )
                logger.info(f"Fetched latest data for {name} from Quiver API")
            else:
                logger.warning(
                    "Quiver API token not configured, using database data only"
                )
        except Exception as e:
            logger.error(f"Failed to fetch latest data for {name}: {e}")

    # Get activities from database
    with PoliticianActivityRepository() as activity_repo:
        activities = activity_repo.get_activities_by_politician(name)

    if not activities:
        return [f"No trading activity found for {name}"]

    activity_summaries = []
    for activity in activities[:10]:  # Show latest 10
        date_str = activity.activity_date.strftime("%Y-%m-%d")
        summary = f"{activity.activity_type} {activity.ticker} ({activity.amount_range}) on {date_str}"
        activity_summaries.append(summary)

    if len(activities) > 10:
        activity_summaries.append(f"... and {len(activities) - 10} more activities")

    return activity_summaries


async def get_stock_price_info_impl(symbol: str) -> StockPriceResponse:
    """Get current price information for a stock symbol - implementation."""
    return get_stock_price(symbol)


async def get_tracked_politicians_list_impl() -> List[str]:
    """Get the current list of tracked politicians - implementation."""
    try:
        with TrackedPoliticianRepository() as repo:
            tracked_politicians = repo.get_all_tracked_politicians()

        names = []
        for tracked in tracked_politicians:
            # Access the politician name through the relationship
            if hasattr(tracked, "politician") and tracked.politician:
                names.append(tracked.politician.name)

        logger.info("Getting politician tracker list", names=names)
        return names
    except Exception as e:
        logger.error(f"Error getting tracked politicians: {e}")
        return []


async def get_tracked_stocks_list_impl() -> List[str]:
    """Get the current list of tracked stocks - implementation."""
    with TrackedStockRepository() as repo:
        symbols = repo.get_stock_symbols()
        logger.info("Getting tracker list", symbols=symbols)
        return symbols


async def remove_politician_from_tracker_impl(name: str) -> str:
    """Remove a politician from the tracking list - implementation."""
    with TrackedPoliticianRepository() as repo:
        if repo.remove_tracked_politician(name):
            return f"Removed {name} from politician tracker list"
        else:
            return f"{name} is not in tracker list or already removed"


async def remove_stock_from_tracker_impl(symbol: str) -> str:
    """Remove a stock symbol from the tracking list - implementation."""
    with TrackedStockRepository() as repo:
        if repo.remove_stock(symbol):
            return f"Removed {symbol.upper()} from tracker list"
        else:
            return f"{symbol.upper()} is not in tracker list or already removed"


# Agent tool functions (thin wrappers around business logic)


@function_tool
async def add_alert_to_history(
    symbol: str, alert_date: str, message_content: str = ""
) -> str:
    """Add an alert to the history for tracking purposes."""
    return await add_alert_to_history_impl(symbol, alert_date, message_content)


@function_tool
async def add_politician_to_tracker(name: str) -> str:
    """Add a politician to the tracking list."""
    return await add_politician_to_tracker_impl(name)


@function_tool
async def add_stock_to_tracker(symbol: str) -> str:
    """Add a stock symbol to the tracking list."""
    return await add_stock_to_tracker_impl(symbol)


@function_tool
async def check_alert_history(symbol: str) -> List[str]:
    """Get alert history for a specific stock symbol."""
    return await check_alert_history_impl(symbol)


@function_tool
async def get_politician_activity_info(
    name: str, fetch_latest: bool = False
) -> List[str]:
    """Get trade activity for a specific politician."""
    return await get_politician_activity_info_impl(name, fetch_latest)


@function_tool
async def get_stock_price_info(symbol: str) -> StockPriceResponse:
    """Get current price information for a stock symbol."""
    return await get_stock_price_info_impl(symbol)


@function_tool
async def get_tracked_politicians_list() -> List[str]:
    """Get the current list of tracked politicians."""
    return await get_tracked_politicians_list_impl()


@function_tool
async def get_tracked_stocks_list() -> List[str]:
    """Get the current list of tracked stocks."""
    return await get_tracked_stocks_list_impl()


@function_tool
async def remove_politician_from_tracker(name: str) -> str:
    """Remove a politician from the tracking list."""
    return await remove_politician_from_tracker_impl(name)


@function_tool
async def remove_stock_from_tracker(symbol: str) -> str:
    """Remove a stock symbol from the tracking list."""
    return await remove_stock_from_tracker_impl(symbol)
