"""Repository for alert history operations."""

from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from ..models import AlertHistory, TrackedStock
from .base import BaseRepository


class AlertHistoryRepository(BaseRepository):
    """Repository for alert history operations."""

    def add_alert(
        self,
        stock_symbol: str,
        alert_date: str,
        alert_type: str = "daily",
        message_content: Optional[str] = None,
    ) -> AlertHistory:
        """Add an alert to history."""
        # Import here to avoid circular dependency
        from .tracked_stock import TrackedStockRepository

        # Get or create the tracked stock
        with TrackedStockRepository(self.session) as stock_repo:
            stock = stock_repo.add_stock(stock_symbol)

        alert = AlertHistory(
            stock_id=stock.id,
            alert_date=alert_date,
            alert_type=alert_type,
            message_content=message_content,
        )

        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)

        return alert

    def get_alerts_for_stock(self, stock_symbol: str) -> List[AlertHistory]:
        """Get all alerts for a specific stock."""
        return (
            self.session.query(AlertHistory)
            .join(TrackedStock)
            .filter(TrackedStock.symbol == stock_symbol.upper())
            .order_by(desc(AlertHistory.alert_date))
            .all()
        )

    def get_alerts_for_date(self, alert_date: str) -> List[AlertHistory]:
        """Get all alerts for a specific date."""
        return (
            self.session.query(AlertHistory)
            .filter(AlertHistory.alert_date == alert_date)
            .all()
        )

    def has_alert_been_sent(self, stock_symbol: str, alert_date: str) -> bool:
        """Check if an alert has already been sent for a stock on a specific date."""
        count = (
            self.session.query(AlertHistory)
            .join(TrackedStock)
            .filter(
                and_(
                    TrackedStock.symbol == stock_symbol.upper(),
                    AlertHistory.alert_date == alert_date,
                )
            )
            .count()
        )

        return count > 0

    def get_alert_dates_for_stock(self, stock_symbol: str) -> List[str]:
        """Get all alert dates for a specific stock."""
        alerts = self.get_alerts_for_stock(stock_symbol)
        return [alert.alert_date for alert in alerts]
