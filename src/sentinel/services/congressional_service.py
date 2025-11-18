"""Congressional trading service for monitoring congressional member trading activity."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd
from quiverquant import quiver

from ..config.logging import get_logger
from ..ormdb.database import get_session
from ..ormdb.repositories import (
    PoliticianActivityRepository,
    PoliticianProfileRepository,
    TrackedPoliticianRepository,
)

logger = get_logger(__name__)


@dataclass
class CongressionalTrade:
    """Congressional trade data container."""

    representative: str
    transaction_date: datetime
    ticker: str
    transaction_type: str  # "Buy" or "Sale"
    amount: str  # Usually a range like "$1,001 - $15,000"
    source: str  # "House" or "Senate"
    report_date: Optional[datetime] = None
    asset_description: Optional[str] = None


@dataclass
class CongressionalActivity:
    """Congressional member activity analysis."""

    representative: str
    recent_trades: List[CongressionalTrade]
    total_transactions: int
    buy_count: int
    sale_count: int
    active_tickers: List[str]
    analysis_period: str
    last_activity_date: Optional[datetime]


class TradeType(Enum):
    """Trade type classification."""

    BUY = "Buy"
    SALE = "Sale"
    BOTH = "Both"


class CongressionalBranch(Enum):
    """Congressional branch."""

    HOUSE = "house"
    SENATE = "senate"
    BOTH = "both"


class CongressionalService:
    """Service for congressional trading operations."""

    def __init__(self, api_token: str):
        """
        Initialize congressional service with Quiver API token.

        Args:
            api_token: Quiver Quantitative API token
        """
        self.api_token = api_token
        self.quiver_client = quiver(api_token)
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
                house_trades = await self._get_house_trades(
                    representative, ticker, start_date
                )
                trades.extend(house_trades)

            if branch in [CongressionalBranch.SENATE, CongressionalBranch.BOTH]:
                senate_trades = await self._get_senate_trades(
                    representative, ticker, start_date
                )
                trades.extend(senate_trades)

            # Save trades to database if requested
            if save_to_db and trades:
                await self._save_trades_to_db(trades)
            elif save_to_db and representative:
                # Even if no trades found, update last_trade_check for the specific politician
                with PoliticianProfileRepository() as profile_repo:
                    profile_repo.update_last_trade_check(representative)

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

    async def _get_house_trades(
        self,
        representative: Optional[str],
        ticker: Optional[str],
        start_date: datetime,
    ) -> List[CongressionalTrade]:
        """Get House trading data."""
        try:
            # Get House trading data
            house_data = self.quiver_client.house_trading()

            if house_data is not None and not house_data.empty:
                trades = self._parse_trading_data(house_data, "House", start_date)

                # Filter by representative if specified
                if representative:
                    trades = [
                        t
                        for t in trades
                        if representative.lower() in t.representative.lower()
                    ]

                # Filter by ticker if specified
                if ticker:
                    trades = [t for t in trades if t.ticker.upper() == ticker.upper()]

                return trades

            return []

        except Exception as e:
            self.logger.warning("Failed to fetch House trades", error=str(e))
            return []

    async def _get_senate_trades(
        self,
        representative: Optional[str],
        ticker: Optional[str],
        start_date: datetime,
    ) -> List[CongressionalTrade]:
        """Get Senate trading data."""
        try:
            # Get Senate trading data
            senate_data = self.quiver_client.senate_trading()

            if senate_data is not None and not senate_data.empty:
                trades = self._parse_trading_data(senate_data, "Senate", start_date)

                # Filter by representative if specified
                if representative:
                    trades = [
                        t
                        for t in trades
                        if representative.lower() in t.representative.lower()
                    ]

                # Filter by ticker if specified
                if ticker:
                    trades = [t for t in trades if t.ticker.upper() == ticker.upper()]

                return trades

            return []

        except Exception as e:
            self.logger.warning("Failed to fetch Senate trades", error=str(e))
            return []

    def _parse_trading_data(
        self, data: pd.DataFrame, source: str, start_date: datetime
    ) -> List[CongressionalTrade]:
        """Parse trading data from DataFrame to CongressionalTrade objects."""
        trades = []

        for _, row in data.iterrows():
            try:
                # Parse transaction date
                date_value = row.get("Date") or row.get("TransactionDate")
                if date_value is None:
                    continue

                transaction_date = pd.to_datetime(date_value, errors="coerce")
                if transaction_date is None or pd.isna(transaction_date):
                    continue

                # Skip trades before start_date
                if transaction_date < start_date:
                    continue

                # Extract trade information
                representative = row.get(
                    "Representative", row.get("Senator", "Unknown")
                )
                ticker = row.get("Ticker", row.get("Symbol", ""))
                transaction_type = row.get("Transaction", row.get("Type", "Unknown"))
                amount = row.get("Amount", row.get("Range", "Unknown"))

                # Handle report date if available
                report_date = None
                report_date_value = row.get("ReportDate")
                if report_date_value is not None:
                    report_date = pd.to_datetime(report_date_value, errors="coerce")

                asset_description = row.get("AssetDescription", row.get("Description"))

                trade = CongressionalTrade(
                    representative=representative,
                    transaction_date=transaction_date.to_pydatetime(),
                    ticker=ticker,
                    transaction_type=transaction_type,
                    amount=amount,
                    source=source,
                    report_date=(
                        report_date.to_pydatetime()
                        if report_date is not None and not pd.isna(report_date)
                        else None
                    ),
                    asset_description=asset_description,
                )

                trades.append(trade)

            except Exception as e:
                self.logger.warning(
                    "Failed to parse trade row",
                    error=str(e),
                    row_data=row.to_dict() if hasattr(row, "to_dict") else str(row),
                )

        return trades

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

        # Analyze trading patterns
        buy_count = len([t for t in trades if "buy" in t.transaction_type.lower()])
        sale_count = len([t for t in trades if "sale" in t.transaction_type.lower()])

        active_tickers = list(set([t.ticker for t in trades if t.ticker]))

        last_activity_date = None
        if trades:
            last_activity_date = max(t.transaction_date for t in trades)

        activity = CongressionalActivity(
            representative=representative,
            recent_trades=trades,
            total_transactions=len(trades),
            buy_count=buy_count,
            sale_count=sale_count,
            active_tickers=active_tickers,
            analysis_period=f"{days_back} days",
            last_activity_date=last_activity_date,
        )

        self.logger.info(
            "Congressional activity analyzed",
            representative=representative,
            total_trades=len(trades),
            buy_count=buy_count,
            sale_count=sale_count,
            unique_tickers=len(active_tickers),
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
        return (
            f"{trade.representative} ({trade.source}) "
            f"{trade.transaction_type} {trade.ticker} "
            f"({trade.amount}) on {trade.transaction_date.strftime('%Y-%m-%d')}"
        )

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
        # This is a simple implementation - could be enhanced with proper amount parsing
        notable_trades = []

        for trade in trades:
            amount_str = trade.amount.upper()
            # Look for large amounts (this is a simplified check)
            if any(
                threshold in amount_str
                for threshold in ["$50,000", "$100,000", "$250,000", "$1,000,000"]
            ):
                notable_trades.append(trade)
            elif "OVER $" in amount_str:  # Catch "Over $1,000,000" type entries
                notable_trades.append(trade)

        return notable_trades

    async def _save_trades_to_db(self, trades: List[CongressionalTrade]) -> None:
        """Save trades to database."""
        try:
            with PoliticianActivityRepository() as activity_repo:
                politicians_updated = set()
                for trade in trades:
                    # Determine chamber based on source
                    chamber = "House" if trade.source == "House" else "Senate"

                    # Add the activity/trade using the correct method signature
                    activity_repo.add_activity(
                        politician_name=trade.representative,
                        ticker=trade.ticker,
                        transaction_date=trade.transaction_date,
                        transaction_type=trade.transaction_type,
                        amount_range=trade.amount,
                        source=trade.source,
                        chamber=chamber,
                        report_date=trade.report_date,
                        asset_description=trade.asset_description,
                    )
                    politicians_updated.add(trade.representative)

            # Update last_trade_check timestamp for all politicians whose data was fetched
            with PoliticianProfileRepository() as profile_repo:
                for politician_name in politicians_updated:
                    profile_repo.update_last_trade_check(politician_name)

            self.logger.info(
                "Saved congressional trades to database",
                trade_count=len(trades),
                politicians_updated=len(politicians_updated),
            )

        except Exception as e:
            self.logger.error(
                "Failed to save trades to database",
                trade_count=len(trades),
                error=str(e),
                exc_info=True,
            )

    async def add_tracked_member(
        self,
        member_name: str,
        chamber: str,
        alert_preferences: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a congressional member to the tracking list."""
        try:
            with TrackedPoliticianRepository() as tracked_repo:
                tracked_repo.add_tracked_politician(
                    member_name, chamber, alert_preferences
                )

            self.logger.info(
                "Added congressional member to tracking",
                member_name=member_name,
                chamber=chamber,
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to add tracked member",
                member_name=member_name,
                error=str(e),
                exc_info=True,
            )
            return False

    async def remove_tracked_member(self, member_name: str) -> bool:
        """Remove a congressional member from tracking."""
        try:
            with TrackedPoliticianRepository() as tracked_repo:
                success = tracked_repo.remove_tracked_politician(member_name)

            if success:
                self.logger.info(
                    "Removed congressional member from tracking",
                    member_name=member_name,
                )
            else:
                self.logger.warning(
                    "Member not found in tracking list",
                    member_name=member_name,
                )

            return success

        except Exception as e:
            self.logger.error(
                "Failed to remove tracked member",
                member_name=member_name,
                error=str(e),
                exc_info=True,
            )
            return False

    async def get_tracked_members(self) -> List[str]:
        """Get list of all tracked congressional members."""
        try:
            with TrackedPoliticianRepository() as tracked_repo:
                tracked_politicians = tracked_repo.get_all_tracked_politicians()

            member_names = []
            for tracked in tracked_politicians:
                if hasattr(tracked, "politician") and tracked.politician:
                    member_names.append(tracked.politician.name)

            return member_names

        except Exception as e:
            self.logger.error(
                "Failed to get tracked members",
                error=str(e),
                exc_info=True,
            )
            return []

    async def get_member_recent_trades_from_db(
        self, member_name: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get recent trades for a member from the database."""
        try:
            with PoliticianActivityRepository() as activity_repo:
                activities = activity_repo.get_recent_activities_by_politician(
                    member_name, days
                )

            recent_trades = [
                {
                    "ticker": activity.ticker,
                    "transaction_date": activity.activity_date,
                    "transaction_type": activity.activity_type,
                    "amount_range": activity.amount_range,
                    "source": activity.source,
                    "is_analyzed": activity.is_analyzed,
                    "alert_sent": activity.alert_sent,
                }
                for activity in activities
            ]

            return recent_trades

        except Exception as e:
            self.logger.error(
                "Failed to get member trades from database",
                member_name=member_name,
                error=str(e),
                exc_info=True,
            )
            return []

    async def get_ticker_congressional_activity_from_db(
        self, ticker: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get congressional activity for a ticker from database."""
        try:
            with PoliticianActivityRepository() as activity_repo:
                trades = activity_repo.get_activities_by_ticker(ticker)

            with PoliticianProfileRepository() as member_repo:
                # Filter by date range and add member info
                cutoff_date = datetime.now() - timedelta(days=days)
                activity_data = []

                for trade in trades:
                    if trade.transaction_date >= cutoff_date:
                        member = member_repo.get_politician_by_id(trade.member_id)
                        if member:
                            activity_data.append(
                                {
                                    "representative": member.name,
                                    "chamber": member.chamber,
                                    "transaction_date": trade.transaction_date,
                                    "transaction_type": trade.transaction_type,
                                    "amount_range": trade.amount_range,
                                    "source": trade.source,
                                    "is_analyzed": trade.is_analyzed,
                                }
                            )

                return activity_data

        except Exception as e:
            self.logger.error(
                "Failed to get ticker activity from database",
                ticker=ticker,
                error=str(e),
                exc_info=True,
            )
            return []

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
