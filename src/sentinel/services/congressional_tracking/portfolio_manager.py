"""Portfolio management for congressional tracking."""

from datetime import datetime
from typing import Dict, Optional

from ...config.logging import get_logger
from ...ormdb.database import get_session
from ...ormdb.repositories import (
    PoliticianProfileRepository,
    TrackedPoliticianRepository,
)
from .models import CongressionalTrackingPortfolio

logger = get_logger(__name__)


class CongressionalPortfolioManager:
    """Manages tracked congressional members portfolio."""

    def __init__(self):
        self.logger = logger.bind(component="congressional_portfolio_manager")

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
            with TrackedPoliticianRepository(session) as repo:
                # Check if already tracked
                is_tracked = repo.is_politician_tracked(member_name)

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
                tracked_member = repo.add_tracked_politician(
                    politician_name=member_name,
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
            with TrackedPoliticianRepository(session) as repo:
                success = repo.remove_tracked_politician(member_name)

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
            with TrackedPoliticianRepository(session) as tracked_repo:
                tracked_politicians = tracked_repo.get_all_tracked_politicians()

            member_names = []
            for tracked in tracked_politicians:
                if hasattr(tracked, "politician") and tracked.politician:
                    member_names.append(tracked.politician.name)

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
