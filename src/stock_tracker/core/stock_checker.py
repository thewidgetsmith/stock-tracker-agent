"""Stock price checking and data models."""

import yfinance as yf
from pydantic import BaseModel


class StockPriceResponse(BaseModel):
    """Response model for stock price information."""

    current_price: float
    previous_close: float


def get_stock_price(symbol: str) -> StockPriceResponse:
    """
    Get the current stock price and previous close for a given symbol.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        StockPriceResponse with current price and previous close
    """
    stock = yf.Ticker(symbol)
    # Get the current stock price and the previous close price
    data = stock.history(period="1d", interval="1m")

    if not data.empty:
        current_price = data["Close"].iloc[-1]  # most recent minute
    else:
        current_price = stock.fast_info.last_price  # fallback

    previous_close = stock.history(period="5d")["Close"].dropna().iloc[-2]

    return StockPriceResponse(
        current_price=current_price, previous_close=previous_close
    )


# TODO: Add handling for invalid stock symbols and API errors
# TODO: Add functionality for cryptocurrency price checking
# TODO: Add functionality for following specific people
