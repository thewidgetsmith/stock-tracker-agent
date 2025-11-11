"""Stock tracking functionality and automated monitoring."""

import json
import asyncio
from datetime import date
from typing import List

from .stock_checker import get_stock_price
from ..agents.handlers import run_research_pipeline


def get_tracked_stocks() -> List[str]:
    """Get the current list of tracked stocks."""
    try:
        with open("resources/tracker_list.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def update_alert_history(symbol: str) -> bool:
    """
    Update alert history for a symbol and return True if alert should be sent.

    Returns False if already alerted today, True if new alert should be sent.
    """
    try:
        with open("resources/alert_history.json", "r") as f:
            alert_history = json.load(f)
    except FileNotFoundError:
        alert_history = {}

    if symbol not in alert_history:
        alert_history[symbol] = []

    today = str(date.today())

    # Check if we have already alerted the user today
    if alert_history[symbol] and alert_history[symbol][-1] == today:
        print(f"Already alerted user about {symbol} today.")
        return False

    # Add today's alert
    alert_history[symbol].append(today)

    with open("resources/alert_history.json", "w") as f:
        json.dump(alert_history, f)

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
                    asyncio.run(run_research_pipeline(
                        symbol,
                        stock_info.current_price,
                        stock_info.previous_close
                    ))

        except Exception as e:
            print(f"Error tracking {symbol}: {e}")
