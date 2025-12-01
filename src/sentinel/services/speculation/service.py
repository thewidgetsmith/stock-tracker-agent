"""Main speculation service orchestration."""

from decimal import Decimal
from typing import List, Optional

from ...config.logging import get_logger
from .leaderboard import LeaderboardManager
from .models import (
    PerformanceReport,
    PortfolioRanking,
    PortfolioSummary,
    TradeRequest,
    TradeResult,
)
from .performance_analyzer import PerformanceAnalyzer
from .portfolio_manager import PortfolioManager
from .trade_executor import TradeExecutor

logger = get_logger(__name__)


class SpeculationService:
    """Service for virtual trading and speculation portfolio management."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.default_starting_balance = Decimal("10000.00")
        self.transaction_fee = Decimal("0.50")  # Per trade fee

        # Initialize component managers
        self.portfolio_manager = PortfolioManager(self.default_starting_balance)
        self.trade_executor = TradeExecutor(self.transaction_fee)
        self.performance_analyzer = PerformanceAnalyzer(self.default_starting_balance)
        self.leaderboard_manager = LeaderboardManager()

    async def create_virtual_portfolio(
        self,
        user_id: str,
        portfolio_name: str,
        starting_balance: Optional[Decimal] = None,
        strategy_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> int:
        """
        Create a new virtual trading portfolio.

        Args:
            user_id: User identifier (chat ID, etc.)
            portfolio_name: Name for the portfolio
            starting_balance: Starting virtual balance (default $10,000)
            strategy_type: Portfolio strategy ("aggressive", "conservative", etc.)
            description: Portfolio description

        Returns:
            Portfolio ID
        """
        return await self.portfolio_manager.create_virtual_portfolio(
            user_id, portfolio_name, starting_balance, strategy_type, description
        )

    async def execute_virtual_trade(self, trade_request: TradeRequest) -> TradeResult:
        """
        Execute a virtual trade (buy or sell).

        Args:
            trade_request: Trade request details

        Returns:
            TradeResult with execution details
        """
        result = await self.trade_executor.execute_virtual_trade(trade_request)

        # Update portfolio metrics after successful trade
        if result.success:
            await self.performance_analyzer.update_portfolio_metrics(
                trade_request.portfolio_id
            )

        return result

    async def get_portfolio_performance(
        self, portfolio_id: int
    ) -> Optional[PerformanceReport]:
        """
        Get comprehensive portfolio performance report.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            PerformanceReport or None if portfolio not found
        """
        return await self.performance_analyzer.get_portfolio_performance(portfolio_id)

    async def get_leaderboard(
        self, period: str = "all_time", limit: int = 10
    ) -> List[PortfolioRanking]:
        """
        Get performance leaderboard.

        Args:
            period: Time period ("daily", "weekly", "monthly", "all_time")
            limit: Maximum number of entries to return

        Returns:
            List of portfolio rankings
        """
        return await self.leaderboard_manager.get_leaderboard(period, limit)

    async def get_user_portfolios(self, user_id: str) -> List[PortfolioSummary]:
        """
        Get all portfolios for a user.

        Args:
            user_id: User identifier

        Returns:
            List of portfolio summaries
        """
        return await self.portfolio_manager.get_user_portfolios(user_id)
