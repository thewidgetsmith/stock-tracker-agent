"""Agent tools for stock tracking operations."""

from agents import function_tool
import json
from typing import List
from .stock_checker import StockPriceResponse, get_stock_price


@function_tool
async def add_stock_to_tracker(symbol: str) -> str:
    """Add a stock symbol to the tracking list."""
    with open("resources/tracker_list.json", "r") as f:
        tracker_list = json.load(f)

    if symbol not in tracker_list:
        tracker_list.append(symbol.upper())

        with open("resources/tracker_list.json", "w") as f:
            json.dump(tracker_list, f)

        return f"Added {symbol.upper()} to tracker list"
    else:
        return f"{symbol.upper()} is already being tracked"


@function_tool
async def remove_stock_from_tracker(symbol: str) -> str:
    """Remove a stock symbol from the tracking list."""
    with open("resources/tracker_list.json", "r") as f:
        tracker_list = json.load(f)

    symbol_upper = symbol.upper()
    if symbol_upper in tracker_list:
        tracker_list.remove(symbol_upper)

        with open("resources/tracker_list.json", "w") as f:
            json.dump(tracker_list, f)

        return f"Removed {symbol_upper} from tracker list"
    else:
        return f"{symbol_upper} is not in tracker list"


@function_tool
async def get_stock_tracker_list() -> List[str]:
    """Get the current list of tracked stocks."""
    with open("resources/tracker_list.json", "r") as f:
        tracker_list = json.load(f)
        print('Getting tracker list:', tracker_list)
    return tracker_list


@function_tool
async def get_stock_price_info(symbol: str) -> StockPriceResponse:
    """Get current price information for a stock symbol."""
    return get_stock_price(symbol)
