"""Main service orchestration for congressional tracking."""

from typing import Any, Dict, List, Optional

from ...config.logging import get_logger
from ..stock_tracking import StockTrackingService
from .congressional_operations import CongressionalOperations
from .models import (
    CongressionalActivity,
    CongressionalBranch,
    CongressionalTrackingPortfolio,
    CongressionalTrackingResult,
    CongressionalTrade,
    TradeType,
)
from .portfolio_manager import CongressionalPortfolioManager
from .tracker import CongressionalTracker

logger = get_logger(__name__)


class CongressionalTrackingService:
    """
    Unified service for congressional trading tracking and monitoring operations.

    Combines congressional trading data fetching, analysis, and portfolio tracking
    into a single comprehensive service.
    """

    def __init__(
        self,
        api_token: str,
        congressional_operations: Optional[CongressionalOperations] = None,
        stock_service: Optional[StockTrackingService] = None,
    ):
        """
        Initialize congressional tracking service.

        Args:
            api_token: Quiver API token
            congressional_operations: Congressional operations instance (optional)
            stock_service: Stock service for additional analysis (optional)
        """
        self.api_token = api_token
        self.congressional_operations = (
            congressional_operations or CongressionalOperations(api_token)
        )
        self.portfolio_manager = CongressionalPortfolioManager()
        self.stock_service = stock_service or StockTrackingService()
        self.tracker = CongressionalTracker(self.congressional_operations)
        self.logger = logger.bind(service="congressional_tracking_service")

    # Core congressional trading operations (from CongressionalService)

    async def get_congressional_trades(
        self,
        representative: Optional[str] = None,
        ticker: Optional[str] = None,
        branch: CongressionalBranch = CongressionalBranch.BOTH,
        days_back: int = 30,
        save_to_db: bool = True,
    ) -> List[CongressionalTrade]:
        """Get congressional trading data."""
        return await self.congressional_operations.get_congressional_trades(
            representative, ticker, branch, days_back, save_to_db
        )

    async def analyze_congressional_activity(
        self, representative: str, days_back: int = 90
    ) -> CongressionalActivity:
        """Analyze trading activity for a specific congressional member."""
        return await self.congressional_operations.analyze_congressional_activity(
            representative, days_back
        )

    async def get_ticker_congressional_activity(
        self, ticker: str, days_back: int = 30
    ) -> List[CongressionalTrade]:
        """Get all congressional trading activity for a specific ticker."""
        return await self.congressional_operations.get_ticker_congressional_activity(
            ticker, days_back
        )

    async def get_recent_congressional_trades(
        self, days_back: int = 7
    ) -> List[CongressionalTrade]:
        """Get all recent congressional trades across both chambers."""
        return await self.congressional_operations.get_recent_congressional_trades(
            days_back
        )

    def format_trade_summary(self, trade: CongressionalTrade) -> str:
        """Format a congressional trade for display."""
        return self.congressional_operations.format_trade_summary(trade)

    def get_notable_trades(
        self, trades: List[CongressionalTrade], min_amount_threshold: str = "$50,000"
    ) -> List[CongressionalTrade]:
        """Filter trades for notable/large transactions."""
        return self.congressional_operations.get_notable_trades(
            trades, min_amount_threshold
        )

    async def get_member_recent_trades_from_db(
        self, member_name: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get recent trades for a member from the database."""
        return await self.congressional_operations.get_member_recent_trades_from_db(
            member_name, days
        )

    async def get_ticker_congressional_activity_from_db(
        self, ticker: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get congressional activity for a ticker from database."""
        return await self.congressional_operations.get_ticker_congressional_activity_from_db(
            ticker, days
        )

    async def sync_recent_trades(self, days_back: int = 7) -> Dict[str, int]:
        """Sync recent trades from API to database."""
        return await self.congressional_operations.sync_recent_trades(days_back)

    # Portfolio tracking operations (from CongressionalTrackingService)

    async def add_member_to_tracking(
        self, member_name: str, chamber: str, alert_preferences: Optional[Dict] = None
    ) -> dict:
        """Add a congressional member to the tracking portfolio."""
        return await self.portfolio_manager.add_member_to_tracking(
            member_name, chamber, alert_preferences
        )

    async def remove_member_from_tracking(self, member_name: str) -> dict:
        """Remove a congressional member from tracking portfolio."""
        return await self.portfolio_manager.remove_member_from_tracking(member_name)

    async def get_tracking_portfolio(self) -> CongressionalTrackingPortfolio:
        """Get the current congressional tracking portfolio."""
        return await self.portfolio_manager.get_tracking_portfolio()

    async def track_all_members(
        self, days_back: int = 7
    ) -> List[CongressionalTrackingResult]:
        """Track all congressional members in portfolio for new trades."""
        portfolio = await self.get_tracking_portfolio()
        return await self.tracker.track_all_members(
            portfolio.tracked_members, days_back
        )

    async def sync_all_tracked_members(self, days_back: int = 30) -> Dict[str, int]:
        """Sync all tracked members' trades from API to database."""
        portfolio = await self.get_tracking_portfolio()
        return await self.tracker.sync_all_tracked_members(
            portfolio.tracked_members, days_back
        )

    async def get_portfolio_summary(self) -> dict:
        """Get comprehensive congressional tracking portfolio summary."""
        portfolio = await self.get_tracking_portfolio()

        # Get recent activity for all tracked members
        member_activities = self.tracker.get_member_activity(portfolio.tracked_members)

        # Calculate portfolio metrics
        portfolio_metrics = self._calculate_portfolio_metrics(member_activities)

        return {
            "portfolio": {
                "total_members": portfolio.total_count,
                "active_members": portfolio.active_count,
                "tracked_members": portfolio.tracked_members,
                "last_updated": portfolio.last_updated.isoformat(),
            },
            "activity": portfolio_metrics,
            "member_details": member_activities,
        }

    def _calculate_portfolio_metrics(self, activities: List[dict]) -> dict:
        """Calculate aggregate portfolio metrics."""
        if not activities:
            return {
                "total_trades": 0,
                "recent_trades": 0,
                "active_members": 0,
                "average_trades_per_member": 0.0,
                "unique_tickers": 0,
            }

        total_trades = sum(a["total_trades"] for a in activities)
        recent_trades = sum(a["recent_trades"] for a in activities)
        active_members = sum(1 for a in activities if a["recent_trades"] > 0)
        avg_trades = total_trades / len(activities) if activities else 0

        return {
            "total_trades": total_trades,
            "recent_trades": recent_trades,
            "active_members": active_members,
            "average_trades_per_member": round(avg_trades, 2),
            "total_analyzed": len(activities),
        }
