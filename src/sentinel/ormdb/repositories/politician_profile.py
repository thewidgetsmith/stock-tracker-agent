"""Repository for politician profile operations."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models import PoliticianProfile
from .base import BaseRepository


class PoliticianProfileRepository(BaseRepository):
    """Repository for politician profile operations."""

    def add_politician(
        self,
        name: str,
        chamber: str,
        state: Optional[str] = None,
        party: Optional[str] = None,
    ) -> PoliticianProfile:
        """Add a politician to the database."""
        # Check if politician already exists
        existing_politician = self.get_politician_by_name(name)
        if existing_politician:
            return existing_politician

        # Generate a slug from the name
        slug = name.lower().replace(" ", "-").replace(".", "")

        politician = PoliticianProfile(
            name=name, slug=slug, chamber=chamber, state=state, party=party
        )
        self.session.add(politician)
        self.session.commit()
        self.session.refresh(politician)

        return politician

    def get_politician_by_name(self, name: str) -> Optional[PoliticianProfile]:
        """Get a politician by name."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.name == name)
            .first()
        )

    def get_politician_by_slug(self, slug: str) -> Optional[PoliticianProfile]:
        """Get a politician by slugified name."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.slug == slug)
            .first()
        )

    def get_politician_by_id(self, politician_id: int) -> Optional[PoliticianProfile]:
        """Get a politician by ID."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.id == politician_id)
            .first()
        )

    def get_politicians_by_chamber(self, chamber: str) -> List[PoliticianProfile]:
        """Get all politicians from a specific chamber."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.chamber == chamber)
            .order_by(PoliticianProfile.name)
            .all()
        )

    def get_tracked_politicians(self) -> List[PoliticianProfile]:
        """Get all politicians that are being tracked."""
        return (
            self.session.query(PoliticianProfile)
            .filter(PoliticianProfile.is_tracked == True)
            .order_by(PoliticianProfile.name)
            .all()
        )

    def update_politician_tracking(self, name: str, is_tracked: bool) -> bool:
        """Update tracking status for a politician."""
        politician = self.get_politician_by_name(name)
        if politician:
            politician.is_tracked = is_tracked
            self.session.commit()
            return True
        return False

    def is_data_stale(self, name: str, hours: int = 12) -> bool:
        """
        Check if politician trading data is stale (older than specified hours).

        Args:
            name: Name of the politician
            hours: Number of hours to consider data stale (default: 12)

        Returns:
            True if data is stale or has never been checked, False if fresh
        """
        politician = self.get_politician_by_name(name)
        if not politician or not getattr(politician, "last_trade_check", None):
            return True  # No data or never checked

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Ensure both timestamps are timezone-aware for comparison
        last_check = politician.last_trade_check
        if last_check.tzinfo is None:
            last_check = last_check.replace(tzinfo=timezone.utc)

        return last_check < cutoff_time

    def update_last_trade_check(self, name: str) -> bool:
        """
        Update the last_trade_check timestamp for a politician.

        Args:
            name: Name of the politician

        Returns:
            True if updated successfully, False otherwise
        """
        politician = self.get_politician_by_name(name)
        if politician:
            politician.last_trade_check = datetime.now(timezone.utc)
            self.session.commit()
            return True
        return False
