"""Alert service for managing stock alerts and notifications."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..config.logging import get_logger
from ..ormdb.database import get_session
from ..ormdb.repositories import AlertHistoryRepository
from .stock_service import StockAnalysis

logger = get_logger(__name__)


class AlertType(Enum):
    """Types of stock alerts."""

    PRICE_MOVEMENT = "price_movement"
    DAILY_SUMMARY = "daily_summary"
    THRESHOLD_BREACH = "threshold_breach"
    VOLUME_SPIKE = "volume_spike"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data container."""

    symbol: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AlertHistory:
    """Alert history record."""

    symbol: str
    alert_date: str
    alert_type: str
    message_content: Optional[str]
    created_at: datetime


class AlertService:
    """Service for alert management and history tracking."""

    def __init__(self):
        self.logger = logger.bind(service="alert_service")

    async def create_price_movement_alert(
        self, analysis: StockAnalysis, custom_message: Optional[str] = None
    ) -> Alert:
        """
        Create an alert for significant price movement.

        Args:
            analysis: Stock analysis with movement data
            custom_message: Optional custom alert message

        Returns:
            Alert object for the price movement
        """
        # Determine severity based on movement magnitude
        abs_change = abs(analysis.price_change_percent)

        if abs_change >= 0.10:  # 10%+
            severity = AlertSeverity.CRITICAL
        elif abs_change >= 0.05:  # 5%+
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        # Generate title and message
        direction = "increased" if analysis.price_change > 0 else "decreased"
        title = f"{analysis.symbol} price {direction} significantly"

        if custom_message:
            message = custom_message
        else:
            message = (
                f"{analysis.symbol} price {direction} by "
                f"{analysis.price_change_percent:.2%} "
                f"(${analysis.price_change:+.2f}) to ${analysis.current_price:.2f}"
            )

        alert = Alert(
            symbol=analysis.symbol,
            alert_type=AlertType.PRICE_MOVEMENT,
            severity=severity,
            title=title,
            message=message,
            timestamp=analysis.analysis_timestamp,
            metadata={
                "current_price": analysis.current_price,
                "previous_close": analysis.previous_close,
                "price_change": analysis.price_change,
                "price_change_percent": analysis.price_change_percent,
                "volume": analysis.volume,
                "movement_threshold": abs_change,
            },
        )

        self.logger.info(
            "Price movement alert created",
            symbol=analysis.symbol,
            severity=severity.value,
            change_percent=analysis.price_change_percent,
        )

        return alert

    async def should_send_alert_today(self, symbol: str, alert_type: AlertType) -> bool:
        """
        Check if an alert of this type should be sent today for the given symbol.

        Args:
            symbol: Stock symbol
            alert_type: Type of alert to check

        Returns:
            True if alert should be sent, False if already sent today
        """
        today_str = str(date.today())

        session_gen = get_session()
        session = next(session_gen)

        try:
            with AlertHistoryRepository(session) as repo:
                # Check if we already have this type of alert for today
                has_alert = repo.has_alert_been_sent(symbol, today_str)

                # For now, we use a simple daily limit
                # In the future, we could check by alert_type
                return not has_alert

        except Exception as e:
            self.logger.error(
                "Failed to check alert history",
                symbol=symbol,
                alert_type=alert_type.value,
                error=str(e),
                exc_info=True,
            )
            # On error, allow alert to be safe
            return True
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    async def record_alert_sent(
        self, alert: Alert, delivery_status: str = "sent"
    ) -> bool:
        """
        Record that an alert was sent.

        Args:
            alert: Alert that was sent
            delivery_status: Status of alert delivery

        Returns:
            True if recorded successfully
        """
        today_str = str(date.today())

        session_gen = get_session()
        session = next(session_gen)

        try:
            with AlertHistoryRepository(session) as repo:
                repo.add_alert(
                    stock_symbol=alert.symbol,
                    alert_date=today_str,
                    alert_type=alert.alert_type.value,
                    message_content=alert.message,
                )

                self.logger.info(
                    "Alert delivery recorded",
                    symbol=alert.symbol,
                    alert_type=alert.alert_type.value,
                    severity=alert.severity.value,
                    delivery_status=delivery_status,
                )

                return True

        except Exception as e:
            self.logger.error(
                "Failed to record alert delivery",
                symbol=alert.symbol,
                alert_type=alert.alert_type.value,
                error=str(e),
                exc_info=True,
            )
            return False
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    async def get_alert_history(
        self, symbol: Optional[str] = None, days_back: int = 30
    ) -> List[AlertHistory]:
        """
        Get alert history for a symbol or all symbols.

        Args:
            symbol: Optional stock symbol to filter by
            days_back: Number of days to look back

        Returns:
            List of AlertHistory records
        """
        session_gen = get_session()
        session = next(session_gen)

        try:
            with AlertHistoryRepository(session) as repo:
                if symbol:
                    # Get alerts for specific symbol
                    alert_dates = repo.get_alert_dates_for_stock(symbol)
                    history = [
                        AlertHistory(
                            symbol=symbol,
                            alert_date=alert_date,
                            alert_type="price_movement",  # Default type for now
                            message_content=None,
                            created_at=datetime.strptime(alert_date, "%Y-%m-%d"),
                        )
                        for alert_date in alert_dates
                    ]
                else:
                    # Get all alerts - would need repository method enhancement
                    history = []

                self.logger.info(
                    "Alert history retrieved",
                    symbol=symbol,
                    record_count=len(history),
                    days_back=days_back,
                )

                return history

        except Exception as e:
            self.logger.error(
                "Failed to retrieve alert history",
                symbol=symbol,
                error=str(e),
                exc_info=True,
            )
            return []
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass

    async def create_daily_summary_alert(
        self, portfolio_summary: Dict[str, Any]
    ) -> Alert:
        """
        Create a daily portfolio summary alert.

        Args:
            portfolio_summary: Portfolio performance summary

        Returns:
            Alert object for daily summary
        """
        performance = portfolio_summary.get("performance", {})
        portfolio = portfolio_summary.get("portfolio", {})

        total_stocks = portfolio.get("total_stocks", 0)
        avg_change = performance.get("average_change_percent", 0)
        significant_movements = performance.get("significant_movements", 0)

        # Determine severity based on portfolio performance
        if significant_movements >= 3 or abs(avg_change) >= 0.05:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO

        title = f"Daily Portfolio Summary - {total_stocks} stocks"

        message = (
            f"Portfolio Performance:\n"
            f"• Total stocks: {total_stocks}\n"
            f"• Average change: {avg_change:+.2%}\n"
            f"• Significant movements: {significant_movements}\n"
            f"• Positive movers: {performance.get('positive_movers', 0)}\n"
            f"• Negative movers: {performance.get('negative_movers', 0)}"
        )

        alert = Alert(
            symbol="PORTFOLIO",
            alert_type=AlertType.DAILY_SUMMARY,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=portfolio_summary,
        )

        self.logger.info(
            "Daily summary alert created",
            total_stocks=total_stocks,
            avg_change=avg_change,
            significant_movements=significant_movements,
        )

        return alert

    async def create_custom_alert(
        self,
        symbol: str,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """
        Create a custom alert.

        Args:
            symbol: Stock symbol
            title: Alert title
            message: Alert message
            severity: Alert severity level
            metadata: Optional metadata

        Returns:
            Custom Alert object
        """
        alert = Alert(
            symbol=symbol,
            alert_type=AlertType.CUSTOM,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )

        self.logger.info(
            "Custom alert created", symbol=symbol, severity=severity.value, title=title
        )

        return alert

    async def get_alert_statistics(self) -> Dict[str, Any]:
        """
        Get alert statistics and metrics.

        Returns:
            Dictionary with alert statistics
        """
        # This would require enhanced repository methods
        # For now, return basic stats

        self.logger.info("Retrieving alert statistics")

        return {
            "total_alerts_sent": 0,  # Would need database query
            "alerts_by_type": {},  # Would need aggregation
            "alerts_by_severity": {},  # Would need aggregation
            "most_active_symbols": [],  # Would need grouping
            "last_updated": datetime.utcnow().isoformat(),
        }
