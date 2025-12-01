"""Main orchestration service for penny stock operations."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ...config.logging import get_logger
from .analyzer import VolatilityAnalyzer
from .discovery import PennyStockDiscovery
from .models import PennyStockCandidate, ScreeningCriteria, VolatilityMetrics
from .watchlist_manager import WatchlistManager

logger = get_logger(__name__)


class PennyStockService:
    """Service for penny stock discovery, analysis, and management."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.analyzer = VolatilityAnalyzer()
        self.discovery = PennyStockDiscovery(self.analyzer)
        self.watchlist_manager = WatchlistManager()

    async def discover_penny_stocks(
        self, criteria: Optional[ScreeningCriteria] = None, max_stocks: int = 50
    ) -> List[PennyStockCandidate]:
        """
        Discover trending penny stocks based on criteria.

        Args:
            criteria: Screening criteria (default applied if None)
            max_stocks: Maximum number of stocks to return

        Returns:
            List of penny stock candidates sorted by interest score
        """
        # Get existing symbols from watchlist
        existing_symbols = await self.watchlist_manager.get_existing_symbols()

        # Discover candidates
        candidates = await self.discovery.discover_penny_stocks(
            criteria, max_stocks, existing_symbols
        )

        # Update database with findings
        await self.watchlist_manager.update_watchlist(candidates)

        return candidates

    async def get_volatility_metrics(self, symbol: str) -> Optional[VolatilityMetrics]:
        """
        Get comprehensive volatility analysis for a symbol.

        Args:
            symbol: Stock symbol to analyze

        Returns:
            VolatilityMetrics or None if analysis fails
        """
        return await self.analyzer.get_volatility_metrics(symbol)

    async def screen_by_criteria(
        self, criteria: ScreeningCriteria
    ) -> List[PennyStockCandidate]:
        """
        Screen stocks by specific criteria.

        Args:
            criteria: Detailed screening criteria

        Returns:
            List of matching penny stock candidates
        """
        existing_symbols = await self.watchlist_manager.get_existing_symbols()
        return await self.discovery.screen_by_criteria(criteria, existing_symbols)

    async def get_penny_stock_news(
        self, symbol: str, max_articles: int = 5
    ) -> List[Dict]:
        """
        Get recent news for a penny stock (placeholder - would integrate with news API).

        Args:
            symbol: Stock symbol
            max_articles: Maximum number of articles to return

        Returns:
            List of news article dictionaries
        """
        # Placeholder implementation - in production, would integrate with news API
        # like Alpha Vantage, Polygon, or free alternatives

        self.logger.info(f"Fetching news for penny stock {symbol}")

        # Mock news data for now
        mock_news = [
            {
                "title": f"{symbol} Shows Unusual Trading Volume",
                "summary": f"Trading volume for {symbol} exceeded 300% of average today.",
                "published_at": datetime.now() - timedelta(hours=2),
                "source": "MarketWatch",
                "sentiment": "neutral",
            },
            {
                "title": f"Analyst Upgrade for {symbol}",
                "summary": f"Small-cap analyst raises price target for {symbol}.",
                "published_at": datetime.now() - timedelta(hours=8),
                "source": "Seeking Alpha",
                "sentiment": "positive",
            },
        ]

        return mock_news[:max_articles]

    async def add_to_watch_list(self, symbol: str) -> bool:
        """
        Add a symbol to the penny stock watch list.

        Args:
            symbol: Stock symbol to add

        Returns:
            True if added successfully
        """
        try:
            # First evaluate if it qualifies as penny stock
            criteria = ScreeningCriteria()
            candidate = await self.discovery.evaluate_candidate(symbol, criteria)

            if not candidate:
                self.logger.warning(f"{symbol} does not qualify as penny stock")
                return False

            # Add to database
            await self.watchlist_manager.update_watchlist([candidate])

            self.logger.info(f"Added {symbol} to penny stock watch list")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add {symbol} to watch list: {e}")
            return False
