"""Database operations for congressional trading data."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ...config.logging import get_logger
from ...ormdb.repositories import (
    PoliticianActivityRepository,
    PoliticianProfileRepository,
    TrackedPoliticianRepository,
)
from .models import CongressionalTrade

logger = get_logger(__name__)


class CongressionalDatabase:
    """Database operations for congressional trading data."""

    def __init__(self):
        self.logger = logger.bind(component="congressional_database")

    async def save_trades(self, trades: List[CongressionalTrade]) -> None:
        """
        Save trades to database.

        Args:
            trades: List of CongressionalTrade objects to save
        """
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
        """
        Add a congressional member to the tracking list.

        Args:
            member_name: Name of the congressional member
            chamber: Congressional chamber (House or Senate)
            alert_preferences: Optional alert preferences

        Returns:
            True if successful, False otherwise
        """
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
        """
        Remove a congressional member from tracking.

        Args:
            member_name: Name of the congressional member

        Returns:
            True if successful, False otherwise
        """
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
        """
        Get list of all tracked congressional members.

        Returns:
            List of tracked member names
        """
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

    async def get_member_recent_trades(
        self, member_name: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent trades for a member from the database.

        Args:
            member_name: Name of the congressional member
            days: Number of days to look back

        Returns:
            List of trade dictionaries
        """
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

    async def get_ticker_activity(
        self, ticker: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get congressional activity for a ticker from database.

        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back

        Returns:
            List of activity dictionaries
        """
        try:
            with PoliticianActivityRepository() as activity_repo:
                trades = activity_repo.get_activities_by_ticker(ticker)

            with PoliticianProfileRepository() as member_repo:
                # Filter by date range and add member info
                cutoff_date = datetime.now() - timedelta(days=days)
                activity_data = []

                for trade in trades:
                    # Type checkers see Column types but runtime works correctly
                    if trade.activity_date >= cutoff_date:  # type: ignore
                        member = member_repo.get_politician_by_id(trade.politician_id)  # type: ignore
                        if member:
                            activity_data.append(
                                {
                                    "representative": member.name,
                                    "chamber": member.chamber,
                                    "transaction_date": trade.activity_date,
                                    "transaction_type": trade.activity_type,
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

    async def update_last_trade_check(self, representative: str) -> None:
        """
        Update last_trade_check timestamp for a politician.

        Args:
            representative: Name of the congressional member
        """
        with PoliticianProfileRepository() as profile_repo:
            profile_repo.update_last_trade_check(representative)
