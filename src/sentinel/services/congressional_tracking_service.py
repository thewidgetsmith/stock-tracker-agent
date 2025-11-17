"""Congressional tracking service for monitoring congressional member trading activity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from ..config.logging import get_logger
from ..ormdb.database import get_session
from ..ormdb.repositories import (
    CongressionalMemberRepository,
    CongressionalTradeRepository,
    TrackedCongressionalMemberRepository,
)
from .congressional_service import CongressionalService
from .stock_service import StockService

logger = get_logger(__name__)


@dataclass
class CongressionalTrackingPortfolio:
    """Portfolio of tracked congressional members with metadata."""

    tracked_members: List[str]
    total_count: int
    active_count: int
    last_updated: datetime


@dataclass
class CongressionalTrackingResult:
    """Result of congressional member tracking operation."""

    member_name: str
    new_trades_count: int
    notable_trades_count: int
    alert_triggered: bool
    error: Optional[str]
    processing_time_ms: float


class CongressionalTrackingService:
    """Service for congressional trading tracking and monitoring operations."""

    def __init__(
        self,
        api_token: str,
        congressional_service: Optional[CongressionalService] = None,
        stock_service: Optional[StockService] = None,
    ):
        """
        Initialize congressional tracking service.

        Args:
            api_token: Quiver API token
            congressional_service: Congressional service instance (optional)
            stock_service: Stock service for additional analysis (optional)
        """
        self.api_token = api_token
        self.congressional_service = congressional_service or CongressionalService(
            api_token
        )
        self.stock_service = stock_service or StockService()
        self.logger = logger.bind(service="congressional_tracking_service")

    async def add_member_to_tracking(
        self, member_name: str, chamber: str, alert_preferences: Optional[Dict] = None
    ) -> dict:
        """
        Add a congressional member to the tracking portfolio.

        Args:
            member_name: Name of the congressional member
            chamber: "House" or "Senate"
            alert_preferences: Alert configuration (optional)

        Returns:
            Result dictionary with operation status
        """
        if not member_name or not isinstance(member_name, str):
            raise ValueError("Member name must be a non-empty string")

        member_name = member_name.strip()

        self.logger.info(
            "Adding congressional member to tracking",
            member_name=member_name,
            chamber=chamber,
        )

        session_gen = get_session()
        session = next(session_gen)

        try:
            with TrackedCongressionalMemberRepository(session) as repo:
                # Check if already tracked
                is_tracked = repo.is_member_tracked(member_name)

                if is_tracked:
                    self.logger.info(
                        "Member already being tracked", member_name=member_name
                    )
                    return {
                        "success": True,
                        "member_name": member_name,
                        "message": f"{member_name} is already being tracked",
                        "reason": "already_tracked",
                    }

                # Add to tracking
                tracked_member = repo.add_tracked_member(
                    member_name=member_name,
                    chamber=chamber,
                    alert_preferences=alert_preferences or {},
                )

                self.logger.info(
                    "Congressional member added to tracking", member_name=member_name
                )

                return {
                    "success": True,
                    "member_name": member_name,
                    "message": f"Successfully added {member_name} to tracking",
                    "action": "added",
                }

        except Exception as e:
            self.logger.error(
                "Failed to add congressional member to tracking",
                member_name=member_name,
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "member_name": member_name,
                "message": f"Failed to add {member_name} to tracking: {str(e)}",
                "reason": "database_error",
            }
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    async def remove_member_from_tracking(self, member_name: str) -> dict:
        """
        Remove a congressional member from tracking portfolio.

        Args:
            member_name: Name of the member to remove

        Returns:
            Result dictionary with operation status
        """
        if not member_name or not isinstance(member_name, str):
            raise ValueError("Member name must be a non-empty string")

        member_name = member_name.strip()

        self.logger.info(
            "Removing congressional member from tracking", member_name=member_name
        )

        session_gen = get_session()
        session = next(session_gen)

        try:
            with TrackedCongressionalMemberRepository(session) as repo:
                success = repo.remove_tracked_member(member_name)

                if success:
                    self.logger.info(
                        "Congressional member removed from tracking",
                        member_name=member_name,
                    )
                    return {
                        "success": True,
                        "member_name": member_name,
                        "message": f"Successfully removed {member_name} from tracking",
                    }
                else:
                    self.logger.warning(
                        "Congressional member not found in tracking",
                        member_name=member_name,
                    )
                    return {
                        "success": False,
                        "member_name": member_name,
                        "message": f"{member_name} is not currently being tracked",
                        "reason": "not_tracked",
                    }

        except Exception as e:
            self.logger.error(
                "Failed to remove congressional member from tracking",
                member_name=member_name,
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "member_name": member_name,
                "message": f"Failed to remove {member_name} from tracking: {str(e)}",
                "reason": "database_error",
            }
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    async def get_tracking_portfolio(self) -> CongressionalTrackingPortfolio:
        """
        Get the current congressional tracking portfolio.

        Returns:
            CongressionalTrackingPortfolio with all tracked members
        """
        self.logger.info("Retrieving congressional tracking portfolio")

        session_gen = get_session()
        session = next(session_gen)

        try:
            with TrackedCongressionalMemberRepository(session) as tracked_repo:
                tracked_members = tracked_repo.get_all_tracked_members()

            with CongressionalMemberRepository(session) as member_repo:
                member_names = []
                for tracked in tracked_members:
                    member = member_repo.get_member_by_id(tracked.member_id)
                    if member:
                        member_names.append(member.name)

            portfolio = CongressionalTrackingPortfolio(
                tracked_members=member_names,
                total_count=len(member_names),
                active_count=len(member_names),
                last_updated=datetime.utcnow(),
            )

            self.logger.info(
                "Congressional tracking portfolio retrieved",
                member_count=len(member_names),
                members=member_names,
            )

            return portfolio

        except Exception as e:
            self.logger.error(
                "Failed to retrieve congressional tracking portfolio",
                error=str(e),
                exc_info=True,
            )
            # Return empty portfolio on error
            return CongressionalTrackingPortfolio(
                tracked_members=[],
                total_count=0,
                active_count=0,
                last_updated=datetime.utcnow(),
            )
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    async def track_all_members(
        self, days_back: int = 7
    ) -> List[CongressionalTrackingResult]:
        """
        Track all congressional members in portfolio for new trades.

        Args:
            days_back: Number of days to look back for new trades

        Returns:
            List of tracking results for each member
        """
        self.logger.info(
            "Starting portfolio-wide congressional tracking", days_back=days_back
        )
        start_time = datetime.utcnow()

        portfolio = await self.get_tracking_portfolio()

        if not portfolio.tracked_members:
            self.logger.info("No congressional members in tracking portfolio")
            return []

        results = []

        for member_name in portfolio.tracked_members:
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
            total_members=len(portfolio.tracked_members),
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

    async def get_portfolio_summary(self) -> dict:
        """
        Get comprehensive congressional tracking portfolio summary.

        Returns:
            Dictionary with portfolio metrics and status
        """
        portfolio = await self.get_tracking_portfolio()

        # Get recent activity for all tracked members
        member_activities = []
        session_gen = get_session()
        session = next(session_gen)

        try:
            with CongressionalTradeRepository(session) as trade_repo:
                for member_name in portfolio.tracked_members[
                    :10
                ]:  # Limit to prevent overload
                    try:
                        trades = trade_repo.get_trades_by_member(member_name)
                        recent_trades = [
                            t
                            for t in trades
                            if (datetime.now() - t.transaction_date).days <= 30
                        ]

                        activity = {
                            "member_name": member_name,
                            "total_trades": len(trades),
                            "recent_trades": len(recent_trades),
                            "unique_tickers": len(set(t.ticker for t in trades)),
                            "last_activity": (
                                max(t.transaction_date for t in trades)
                                if trades
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

        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    def _calculate_portfolio_metrics(self, activities: List[dict]) -> dict:
        """
        Calculate aggregate portfolio metrics.

        Args:
            activities: List of member activity dictionaries

        Returns:
            Portfolio metrics dictionary
        """
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

        # Get all unique tickers across all members
        all_tickers = set()
        for activity in activities:
            if "unique_tickers" in activity:
                # This would need to be enhanced to get actual ticker list
                pass

        return {
            "total_trades": total_trades,
            "recent_trades": recent_trades,
            "active_members": active_members,
            "average_trades_per_member": round(avg_trades, 2),
            "total_analyzed": len(activities),
        }

    async def sync_all_tracked_members(self, days_back: int = 30) -> Dict[str, int]:
        """
        Sync all tracked members' trades from API to database.

        Args:
            days_back: Number of days to sync

        Returns:
            Dictionary with sync statistics
        """
        self.logger.info(
            "Starting sync for all tracked congressional members", days_back=days_back
        )

        portfolio = await self.get_tracking_portfolio()

        total_synced = 0
        total_errors = 0

        for member_name in portfolio.tracked_members:
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
            "members_processed": len(portfolio.tracked_members),
            "trades_synced": total_synced,
            "errors": total_errors,
        }

        self.logger.info("Congressional member sync completed", **stats)
        return stats
