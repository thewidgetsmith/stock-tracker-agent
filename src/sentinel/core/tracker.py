"""Stock tracking functionality and automated monitoring."""

import asyncio
from datetime import date
from typing import List

from ..agents.handlers import run_research_pipeline
from ..ormdb.repositories import AlertHistoryRepository, TrackedStockRepository
from .stock_query import get_stock_price


def get_tracked_stocks() -> List[str]:
    """Get the current list of tracked stocks."""
    with TrackedStockRepository() as repo:
        return repo.get_stock_symbols()


def update_alert_history(symbol: str) -> bool:
    """
    Update alert history for a symbol and return True if alert should be sent.

    Returns False if already alerted today, True if new alert should be sent.
    """
    today_str = str(date.today())

    with AlertHistoryRepository() as repo:
        # Check if we have already alerted the user today
        if repo.has_alert_been_sent(symbol, today_str):
            print(f"Already alerted user about {symbol} today.")
            return False

        # Add today's alert
        repo.add_alert(
            symbol,
            today_str,
            alert_type="daily",
            message_content=f"Daily alert for {symbol}",
        )
        return True


def track_stocks() -> None:
    """
    Main stock tracking function that checks for significant price movements.

    Checks all tracked stocks and triggers research pipeline for stocks that
    have moved more than 1% from previous close.
    """
    print("Starting stock tracking...")

    tracker_list = get_tracked_stocks()
    print("Tracking stocks:", tracker_list)

    for symbol in tracker_list:
        try:
            stock_info = get_stock_price(symbol)

            # Calculate percentage change
            change_percent = (stock_info.current_price / stock_info.previous_close) - 1

            # If the stock price is 1% + or - from the previous close, run the research pipeline
            if abs(change_percent) >= 0.01:
                print(f"{symbol} moved {change_percent:.2%} - triggering alert")

                # Check if we should send an alert (not already sent today)
                if update_alert_history(symbol):
                    asyncio.run(
                        run_research_pipeline(
                            symbol, stock_info.current_price, stock_info.previous_close
                        )
                    )

        except Exception as e:
            print(f"Error tracking {symbol}: {e}")
