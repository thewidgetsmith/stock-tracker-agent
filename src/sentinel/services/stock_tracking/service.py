"""Main stock tracking service orchestration."""

from typing import List

from ...config.logging import get_logger
from ...core.stock_query import StockPriceResponse
from .models import (
    MovementThreshold,
    StockAnalysis,
    StockTrackingResult,
    TrackingPortfolio,
)
from .portfolio_manager import PortfolioManager
from .stock_operations import StockOperations
from .tracker import StockTracker

logger = get_logger(__name__)


class StockTrackingService:
    """Unified service for stock operations and portfolio tracking."""

    def __init__(self):
        self.logger = logger.bind(service="stock_tracking_service")

        # Initialize components
        self.stock_ops = StockOperations()
        self.portfolio_mgr = PortfolioManager()
        self.tracker = StockTracker(self.stock_ops, self.portfolio_mgr)

    # Stock Operations Methods
    async def get_stock_price(self, symbol: str) -> StockPriceResponse:
        """Get current stock price information."""
        return await self.stock_ops.get_stock_price(symbol)

    async def analyze_stock_movement(
        self, symbol: str, threshold: MovementThreshold = MovementThreshold.MODERATE
    ) -> StockAnalysis:
        """Analyze stock price movement and determine significance."""
        return await self.stock_ops.analyze_stock_movement(symbol, threshold)

    async def get_multiple_stock_prices(
        self, symbols: List[str]
    ) -> List[StockPriceResponse]:
        """Get stock prices for multiple symbols."""
        return await self.stock_ops.get_multiple_stock_prices(symbols)

    async def validate_stock_symbol(self, symbol: str) -> bool:
        """Validate if a stock symbol exists and is tradeable."""
        return await self.stock_ops.validate_stock_symbol(symbol)

    async def get_stock_performance_summary(self, symbol: str) -> dict:
        """Get comprehensive stock performance summary."""
        return await self.stock_ops.get_stock_performance_summary(symbol)

    # Portfolio Management Methods
    async def add_stock_to_tracking(self, symbol: str) -> dict:
        """Add a stock to the tracking portfolio."""
        return await self.portfolio_mgr.add_stock(
            symbol, self.stock_ops.validate_stock_symbol
        )

    async def remove_stock_from_tracking(self, symbol: str) -> dict:
        """Remove a stock from tracking portfolio."""
        return await self.portfolio_mgr.remove_stock(symbol)

    async def get_tracking_portfolio(self) -> TrackingPortfolio:
        """Get the current tracking portfolio."""
        return await self.portfolio_mgr.get_portfolio()

    # Tracking Methods
    async def track_all_stocks(
        self, movement_threshold: MovementThreshold = MovementThreshold.MODERATE
    ) -> List[StockTrackingResult]:
        """Track all stocks in portfolio for significant movements."""
        return await self.tracker.track_all_stocks(movement_threshold)

    async def get_portfolio_summary(self) -> dict:
        """Get comprehensive portfolio tracking summary."""
        return await self.tracker.get_portfolio_summary()
