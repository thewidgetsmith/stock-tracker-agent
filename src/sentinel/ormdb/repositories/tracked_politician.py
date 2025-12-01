"""Repository for tracked politician operations."""

from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from ..models import PoliticianProfile, TrackedPolitician
from .base import BaseRepository


class TrackedPoliticianRepository(BaseRepository):
    """Repository for tracked politician operations."""

    def add_tracked_politician(
        self,
        politician_name: str,
        chamber: Optional[str] = "House",
        alert_preferences: Optional[Dict[str, Any]] = None,
    ) -> TrackedPolitician:
        """Add a politician to the tracking list."""
        # Import here to avoid circular dependency
        from .politician_profile import PoliticianProfileRepository

        # Get or create the politician
        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.add_politician(politician_name, chamber)
            politician_repo.update_politician_tracking(politician_name, True)

        # Check if already being tracked
        existing_tracked = (
            self.session.query(TrackedPolitician)
            .filter(TrackedPolitician.politician_id == politician.id)
            .first()
        )

        if existing_tracked:
            if not existing_tracked.is_active:
                existing_tracked.is_active = True
                self.session.commit()
            return existing_tracked

        tracked_politician = TrackedPolitician(
            politician_id=politician.id, alert_preferences=alert_preferences
        )
        self.session.add(tracked_politician)
        self.session.commit()
        self.session.refresh(tracked_politician)

        return tracked_politician

    def remove_tracked_politician(self, politician_name: str) -> bool:
        """Remove a politician from tracking (soft delete)."""
        # Import here to avoid circular dependency
        from .politician_profile import PoliticianProfileRepository

        # Get the politician
        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.get_politician_by_name(politician_name)

        if not politician:
            return False

        tracked_politician = (
            self.session.query(TrackedPolitician)
            .filter(TrackedPolitician.politician_id == politician.id)
            .first()
        )

        if tracked_politician and tracked_politician.is_active:
            tracked_politician.is_active = False
            # Also update the politician tracking status
            with PoliticianProfileRepository(self.session) as politician_repo:
                politician_repo.update_politician_tracking(politician_name, False)
            self.session.commit()
            return True

        return False

    def get_all_tracked_politicians(self) -> List[TrackedPolitician]:
        """Get all actively tracked politicians with eager loading."""
        return (
            self.session.query(TrackedPolitician)
            .options(joinedload(TrackedPolitician.politician))
            .filter(TrackedPolitician.is_active == True)
            .join(PoliticianProfile)
            .order_by(PoliticianProfile.name)
            .all()
        )

    def is_politician_tracked(self, politician_name: str) -> bool:
        """Check if a politician is being tracked."""
        # Import here to avoid circular dependency
        from .politician_profile import PoliticianProfileRepository

        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.get_politician_by_name(politician_name)

        if not politician:
            return False

        tracked_politician = (
            self.session.query(TrackedPolitician)
            .filter(
                and_(
                    TrackedPolitician.politician_id == politician.id,
                    TrackedPolitician.is_active == True,
                )
            )
            .first()
        )

        return tracked_politician is not None

    def update_alert_preferences(
        self, politician_name: str, alert_preferences: Dict[str, Any]
    ) -> bool:
        """Update alert preferences for a tracked politician."""
        # Import here to avoid circular dependency
        from .politician_profile import PoliticianProfileRepository

        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.get_politician_by_name(politician_name)

        if not politician:
            return False

        tracked_politician = (
            self.session.query(TrackedPolitician)
            .filter(TrackedPolitician.politician_id == politician.id)
            .first()
        )

        if tracked_politician:
            tracked_politician.alert_preferences = alert_preferences
            self.session.commit()
            return True
        return False
