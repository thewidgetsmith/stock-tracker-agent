"""
Stock-related API routers.

This module provides modular stock API endpoints organized by functionality:
- prices: Stock price fetching and movement analysis
- tracking: Stock tracking CRUD operations
- portfolio: Portfolio viewing and management
- bulk_operations: Bulk analysis and tracking operations
- history: Alert and event history
"""

from fastapi import APIRouter

from . import bulk_operations, history, portfolio, prices, tracking

# Create main stocks router
router = APIRouter()

# Include all sub-routers with appropriate prefixes and tags

# Price and analysis endpoints: /stocks/{symbol}, /stocks/{symbol}/analyze
router.include_router(prices.router, prefix="/stocks", tags=["Stock Prices"])

# Tracking endpoints: /tracking/stocks, /tracking/stocks/{symbol}
router.include_router(
    tracking.router, prefix="/tracking/stocks", tags=["Stock Tracking"]
)

# Portfolio endpoints: /tracking/portfolio, /tracking/portfolio/summary
router.include_router(
    portfolio.router, prefix="/tracking/portfolio", tags=["Portfolio Management"]
)

# Bulk operations: /tracking/analyze-all
router.include_router(
    bulk_operations.router, prefix="/tracking", tags=["Bulk Operations"]
)

# History endpoints: /alerts/history, /events/statistics, /events/history
router.include_router(history.router, tags=["History & Events"])

__all__ = ["router"]
