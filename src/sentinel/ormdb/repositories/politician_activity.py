"""Repository for politician activity operations."""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..models import PoliticianActivity, PoliticianProfile
from .base import BaseRepository


class PoliticianActivityRepository(BaseRepository):
    """Repository for politician activity operations."""

    def add_activity(
        self,
        politician_name: str,
        ticker: str,
        transaction_date: datetime,
        transaction_type: str,
        amount_range: str,
        source: str,
        chamber: str,
        report_date: Optional[datetime] = None,
        asset_description: Optional[str] = None,
    ) -> PoliticianActivity:
        """Add a politician activity to the database."""
        # Import here to avoid circular dependency
        from .politician_profile import PoliticianProfileRepository

        # Get or create the politician
        with PoliticianProfileRepository(self.session) as politician_repo:
            politician = politician_repo.add_politician(politician_name, chamber)

        # Check if this activity already exists
        existing_activity = (
            self.session.query(PoliticianActivity)
            .filter(
                and_(
                    PoliticianActivity.politician_id == politician.id,
                    PoliticianActivity.ticker == ticker.upper(),
                    PoliticianActivity.activity_date == transaction_date,
                    PoliticianActivity.activity_type == transaction_type,
                    PoliticianActivity.amount_range == amount_range,
                )
            )
            .first()
        )

        if existing_activity:
            return existing_activity

        activity = PoliticianActivity(
            politician_id=politician.id,
            ticker=ticker.upper(),
            activity_date=transaction_date,
            activity_type=transaction_type,
            amount_range=amount_range,
            source=source,
            report_date=report_date,
            asset_description=asset_description,
        )

        self.session.add(activity)
        self.session.commit()
        self.session.refresh(activity)

        return activity

    def get_activities_by_politician(
        self, politician_name: str
    ) -> List[PoliticianActivity]:
        """Get all activities for a specific politician."""
        return (
            self.session.query(PoliticianActivity)
            .join(PoliticianProfile)
            .filter(PoliticianProfile.name == politician_name)
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def get_activities_by_ticker(self, ticker: str) -> List[PoliticianActivity]:
        """Get all activities for a specific ticker."""
        return (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.ticker == ticker.upper())
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def get_recent_activities_by_politician(
        self, politician_name: str, days: int = 30
    ) -> List[PoliticianActivity]:
        """Get recent activities for a specific politician within specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        return (
            self.session.query(PoliticianActivity)
            .join(PoliticianProfile)
            .filter(
                and_(
                    PoliticianProfile.name == politician_name,
                    PoliticianActivity.activity_date >= cutoff_date,
                )
            )
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def get_recent_activities(self, days: int = 7) -> List[PoliticianActivity]:
        """Get recent activities within specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        return (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.activity_date >= cutoff_date)
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def get_unanalyzed_activities(self) -> List[PoliticianActivity]:
        """Get activities that haven't been analyzed yet."""
        return (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.is_analyzed == False)
            .order_by(desc(PoliticianActivity.activity_date))
            .all()
        )

    def mark_activity_analyzed(
        self, activity_id: int, analysis_notes: Optional[str] = None
    ) -> bool:
        """Mark an activity as analyzed."""
        activity = (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.id == activity_id)
            .first()
        )

        if activity:
            activity.is_analyzed = True
            if analysis_notes:
                activity.analysis_notes = analysis_notes
            self.session.commit()
            return True
        return False

    def mark_alert_sent(self, activity_id: int) -> bool:
        """Mark that an alert has been sent for this activity."""
        activity = (
            self.session.query(PoliticianActivity)
            .filter(PoliticianActivity.id == activity_id)
            .first()
        )

        if activity:
            activity.alert_sent = True
            self.session.commit()
            return True
        return False
