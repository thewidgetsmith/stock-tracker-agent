"""Main congressional trading service."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ...config.logging import get_logger
from .api_client import QuiverAPIClient
from .data_processor import CongressionalDataProcessor
from .database import CongressionalDatabase
from .models import CongressionalActivity, CongressionalBranch, CongressionalTrade

logger = get_logger(__name__)


class CongressionalService:
    """Service for congressional trading operations."""

    def __init__(self, api_token: str):
        """
        Initialize congressional service with Quiver API token.

        Args:
            api_token: Quiver Quantitative API token
        """
        self.api_token = api_token
        self.api_client = QuiverAPIClient(api_token)
        self.data_processor = CongressionalDataProcessor()
        self.database = CongressionalDatabase()
        self.logger = logger.bind(service="congressional_service")

    async def get_congressional_trades(
        self,
        representative: Optional[str] = None,
        ticker: Optional[str] = None,
        branch: CongressionalBranch = CongressionalBranch.BOTH,
        days_back: int = 30,
        save_to_db: bool = True,
    ) -> List[CongressionalTrade]:
        """
        Get congressional trading data.

        Args:
            representative: Specific representative name (optional)
            ticker: Specific stock ticker (optional)
            branch: Congressional branch to query
            days_back: Number of days to look back
            save_to_db: Whether to save trades to database

        Returns:
            List of CongressionalTrade objects
        """
        trades = []
        start_date = datetime.now() - timedelta(days=days_back)

        self.logger.info(
            "Fetching congressional trades",
            representative=representative,
            ticker=ticker,
            branch=branch.value,
            days_back=days_back,
        )

        try:
            if branch in [CongressionalBranch.HOUSE, CongressionalBranch.BOTH]:
                house_trades = await self.api_client.get_house_trades(
                    representative, ticker, start_date
                )
                trades.extend(house_trades)

            if branch in [CongressionalBranch.SENATE, CongressionalBranch.BOTH]:
                senate_trades = await self.api_client.get_senate_trades(
                    representative, ticker, start_date
                )
                trades.extend(senate_trades)

            # Save trades to database if requested
            if save_to_db and trades:
                await self.database.save_trades(trades)
            elif save_to_db and representative:
                # Even if no trades found, update last_trade_check for the specific politician
                await self.database.update_last_trade_check(representative)

            self.logger.info(
                "Congressional trades fetched successfully",
                total_trades=len(trades),
                representative=representative,
                ticker=ticker,
            )

            return trades

        except Exception as e:
            self.logger.error(
                "Failed to fetch congressional trades",
                representative=representative,
                ticker=ticker,
                error=str(e),
                exc_info=True,
            )
            raise

    async def analyze_congressional_activity(
        self, representative: str, days_back: int = 90
    ) -> CongressionalActivity:
        """
        Analyze trading activity for a specific congressional member.

        Args:
            representative: Name of the congressional member
            days_back: Number of days to analyze

        Returns:
            CongressionalActivity analysis
        """
        trades = await self.get_congressional_trades(
            representative=representative, days_back=days_back
        )

        activity = self.data_processor.analyze_activity(
            representative, trades, days_back
        )

        return activity

    async def get_ticker_congressional_activity(
        self, ticker: str, days_back: int = 30
    ) -> List[CongressionalTrade]:
        """
        Get all congressional trading activity for a specific ticker.

        Args:
            ticker: Stock ticker symbol
            days_back: Number of days to look back

        Returns:
            List of CongressionalTrade objects for the ticker
        """
        trades = await self.get_congressional_trades(ticker=ticker, days_back=days_back)

        self.logger.info(
            "Ticker congressional activity retrieved",
            ticker=ticker,
            trade_count=len(trades),
            days_back=days_back,
        )

        return trades

    async def get_recent_congressional_trades(
        self, days_back: int = 7
    ) -> List[CongressionalTrade]:
        """
        Get all recent congressional trades across both chambers.

        Args:
            days_back: Number of days to look back

        Returns:
            List of recent CongressionalTrade objects
        """
        trades = await self.get_congressional_trades(days_back=days_back)

        # Sort by transaction date, most recent first
        trades.sort(key=lambda x: x.transaction_date, reverse=True)

        self.logger.info(
            "Recent congressional trades retrieved",
            trade_count=len(trades),
            days_back=days_back,
        )

        return trades

    def format_trade_summary(self, trade: CongressionalTrade) -> str:
        """
        Format a congressional trade for display.

        Args:
            trade: CongressionalTrade object

        Returns:
            Formatted string summary
        """
        return self.data_processor.format_trade_summary(trade)

    def get_notable_trades(
        self, trades: List[CongressionalTrade], min_amount_threshold: str = "$50,000"
    ) -> List[CongressionalTrade]:
        """
        Filter trades for notable/large transactions.

        Args:
            trades: List of trades to filter
            min_amount_threshold: Minimum amount to be considered notable

        Returns:
            List of notable trades
        """
        return self.data_processor.get_notable_trades(trades, min_amount_threshold)

    async def add_tracked_member(
        self,
        member_name: str,
        chamber: str,
        alert_preferences: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a congressional member to the tracking list."""
        return await self.database.add_tracked_member(
            member_name, chamber, alert_preferences
        )

    async def remove_tracked_member(self, member_name: str) -> bool:
        """Remove a congressional member from tracking."""
        return await self.database.remove_tracked_member(member_name)

    async def get_tracked_members(self) -> List[str]:
        """Get list of all tracked congressional members."""
        return await self.database.get_tracked_members()

    async def get_member_recent_trades_from_db(
        self, member_name: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get recent trades for a member from the database."""
        return await self.database.get_member_recent_trades(member_name, days)

    async def get_ticker_congressional_activity_from_db(
        self, ticker: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get congressional activity for a ticker from database."""
        return await self.database.get_ticker_activity(ticker, days)

    async def sync_recent_trades(self, days_back: int = 7) -> Dict[str, int]:
        """
        Sync recent trades from API to database.

        Returns:
            Dictionary with sync statistics
        """
        try:
            # Fetch recent trades from API
            api_trades = await self.get_congressional_trades(
                days_back=days_back, save_to_db=True
            )

            stats = {
                "api_trades_fetched": len(api_trades),
                "trades_saved": len(api_trades),  # Simplified for now
                "new_members_discovered": 0,  # Could be enhanced
            }

            self.logger.info(
                "Congressional trades sync completed",
                **stats,
            )

            return stats

        except Exception as e:
            self.logger.error(
                "Failed to sync congressional trades",
                days_back=days_back,
                error=str(e),
                exc_info=True,
            )
            raise
