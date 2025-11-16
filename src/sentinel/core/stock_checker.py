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


# 📈 Scaling Considerations
# 1. Performance Optimizations
# - Database Indexing: Add composite indexes for frequent queries
# - Caching Layer: Redis for stock prices, API responses
# - Connection Pooling: Optimize database connections
# - Async Optimization: Batch operations, connection pooling
#
# 2. Monitoring & Observability
# Health Checks: Deep health checks for external dependencies
# Metrics: Custom metrics for tracking performance
# Alerting: System alerts for application health
# Distributed Tracing: Request tracing across services
#
# 3. Security Enhancements
# API Rate Limiting: Prevent abuse with rate limiting
# Input Validation: Comprehensive request validation
# Secrets Management: External secrets management
# HTTPS Everywhere: Force HTTPS in production
# 🎉 Standout Features
# Multi-Agent AI System: Sophisticated agent orchestration with specialized roles
# Natural Language Interface: Intuitive Telegram commands with NLP
# Comprehensive Testing: Exceptional test coverage and patterns
# Production-Ready: Docker, health checks, webhook management
# Clean Architecture: Excellent separation of concerns and modularity
# 🚀 Next Development Priorities
# Based on your TODO list and current architecture:

# 🏛️ Political Trader Tracking - Perfect fit for current architecture
# ₿ Cryptocurrency Support - Extend stock tracking patterns
# 🎲 Penny Stock Speculation - Add risk analysis features
# 📊 Advanced Analytics - Historical analysis, patterns, predictions
# 👥 Multi-User Support - User management, personalized tracking
