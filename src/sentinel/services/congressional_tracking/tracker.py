"""Tracking operations for congressional members."""

from datetime import datetime
from typing import Dict, List

from ...config.logging import get_logger
from ...ormdb.database import get_session
from ...ormdb.repositories import PoliticianActivityRepository
from ..congressional import CongressionalService
from .models import CongressionalTrackingResult

logger = get_logger(__name__)


class CongressionalTracker:
    """Handles congressional member trade tracking operations."""

    def __init__(self, congressional_service: CongressionalService):
        self.congressional_service = congressional_service
        self.logger = logger.bind(component="congressional_tracker")

    async def track_all_members(
        self, member_names: List[str], days_back: int = 7
    ) -> List[CongressionalTrackingResult]:
        """
        Track all congressional members in portfolio for new trades.

        Args:
            member_names: List of member names to track
            days_back: Number of days to look back for new trades

        Returns:
            List of tracking results for each member
        """
        self.logger.info(
            "Starting portfolio-wide congressional tracking",
            member_count=len(member_names),
            days_back=days_back,
        )
        start_time = datetime.utcnow()

        if not member_names:
            self.logger.info("No congressional members in tracking portfolio")
            return []

        results = []

        for member_name in member_names:
            member_start = datetime.utcnow()
            result = await self._track_single_member(member_name, days_back)
            result.processing_time_ms = (
                datetime.utcnow() - member_start
            ).total_seconds() * 1000
            results.append(result)

        total_time = (datetime.utcnow() - start_time).total_seconds()
        new_trades = sum(r.new_trades_count for r in results)
        alerts_triggered = sum(1 for r in results if r.alert_triggered)

        self.logger.info(
            "Congressional portfolio tracking completed",
            total_members=len(member_names),
            new_trades=new_trades,
            alerts_triggered=alerts_triggered,
            processing_time_seconds=total_time,
        )

        return results

    async def _track_single_member(
        self, member_name: str, days_back: int
    ) -> CongressionalTrackingResult:
        """
        Track a single congressional member for new trades.

        Args:
            member_name: Name of the congressional member
            days_back: Number of days to look back

        Returns:
            CongressionalTrackingResult for the member
        """
        try:
            # Fetch recent trades from API
            recent_trades = await self.congressional_service.get_congressional_trades(
                representative=member_name, days_back=days_back, save_to_db=True
            )

            # Identify notable trades
            notable_trades = self.congressional_service.get_notable_trades(
                recent_trades
            )

            # Determine if alert should be triggered
            alert_triggered = len(notable_trades) > 0 or len(recent_trades) > 3

            self.logger.info(
                "Congressional member tracking completed",
                member_name=member_name,
                new_trades=len(recent_trades),
                notable_trades=len(notable_trades),
                alert_triggered=alert_triggered,
            )

            return CongressionalTrackingResult(
                member_name=member_name,
                new_trades_count=len(recent_trades),
                notable_trades_count=len(notable_trades),
                alert_triggered=alert_triggered,
                error=None,
                processing_time_ms=0,  # Will be set by caller
            )

        except Exception as e:
            self.logger.error(
                "Failed to track congressional member",
                member_name=member_name,
                error=str(e),
                exc_info=True,
            )

            return CongressionalTrackingResult(
                member_name=member_name,
                new_trades_count=0,
                notable_trades_count=0,
                alert_triggered=False,
                error=str(e),
                processing_time_ms=0,  # Will be set by caller
            )

    async def sync_all_tracked_members(
        self, member_names: List[str], days_back: int = 30
    ) -> Dict[str, int]:
        """
        Sync all tracked members' trades from API to database.

        Args:
            member_names: List of member names to sync
            days_back: Number of days to sync

        Returns:
            Dictionary with sync statistics
        """
        self.logger.info(
            "Starting sync for all tracked congressional members",
            member_count=len(member_names),
            days_back=days_back,
        )

        total_synced = 0
        total_errors = 0

        for member_name in member_names:
            try:
                # Sync trades for this member
                trades = await self.congressional_service.get_congressional_trades(
                    representative=member_name, days_back=days_back, save_to_db=True
                )
                total_synced += len(trades)

                self.logger.info(
                    "Synced congressional member trades",
                    member_name=member_name,
                    trade_count=len(trades),
                )

            except Exception as e:
                total_errors += 1
                self.logger.error(
                    "Failed to sync congressional member",
                    member_name=member_name,
                    error=str(e),
                )

        stats = {
            "members_processed": len(member_names),
            "trades_synced": total_synced,
            "errors": total_errors,
        }

        self.logger.info("Congressional member sync completed", **stats)
        return stats

    def get_member_activity(self, member_names: List[str]) -> List[Dict]:
        """
        Get recent activity for all tracked members.

        Args:
            member_names: List of member names

        Returns:
            List of activity dictionaries
        """
        member_activities = []
        session_gen = get_session()
        session = next(session_gen)

        try:
            with PoliticianActivityRepository(session) as activity_repo:
                for member_name in member_names[:10]:  # Limit to prevent overload
                    try:
                        activities = activity_repo.get_activities_by_politician(
                            member_name
                        )
                        recent_activities = [
                            a
                            for a in activities
                            if (datetime.now() - a.activity_date).days <= 30
                        ]

                        activity = {
                            "member_name": member_name,
                            "total_trades": len(activities),
                            "recent_trades": len(recent_activities),
                            "unique_tickers": len(set(a.ticker for a in activities)),
                            "last_activity": (
                                max(a.activity_date for a in activities)
                                if activities
                                else None
                            ),
                        }
                        member_activities.append(activity)
                    except Exception as e:
                        self.logger.warning(
                            "Failed to get activity for member",
                            member_name=member_name,
                            error=str(e),
                        )
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

        return member_activities
