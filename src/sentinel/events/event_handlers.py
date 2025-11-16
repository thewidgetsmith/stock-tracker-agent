"""Event handlers for processing domain events."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from ..config.logging import get_logger
from ..services import AlertService, NotificationService, StockService, TrackingService
from .events import (
    AlertSentEvent,
    AlertTriggeredEvent,
    DomainEvent,
    ErrorEvent,
    StockAddedToTrackingEvent,
    StockPriceChangedEvent,
    StockRemovedFromTrackingEvent,
)

logger = get_logger(__name__)


class EventHandler(ABC):
    """Base class for event handlers."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logger.bind(handler=name)

    @abstractmethod
    async def handle(self, event: DomainEvent):
        """Handle the domain event."""
        pass


class StockPriceEventHandler(EventHandler):
    """Handler for stock price-related events."""

    def __init__(self):
        super().__init__("stock_price_handler")
        self.alert_service = AlertService()
        self.notification_service = NotificationService()

    async def handle_price_changed(self, event: StockPriceChangedEvent):
        """Handle stock price changed events."""
        self.logger.info(
            "Processing stock price change",
            symbol=event.symbol,
            price_change_percent=event.price_change_percent,
            is_significant=event.is_significant_movement,
        )

        # If movement is significant, create an alert
        if event.is_significant_movement:
            try:
                # Create stock analysis object for alert creation
                from datetime import datetime

                from ..services.stock_service import StockAnalysis

                analysis = StockAnalysis(
                    symbol=event.symbol,
                    current_price=event.current_price,
                    previous_close=event.previous_price,
                    price_change=event.price_change,
                    price_change_percent=event.price_change_percent,
                    volume=event.volume,
                    market_cap=event.market_cap,
                    analysis_timestamp=event.timestamp,
                    is_significant_movement=event.is_significant_movement,
                )

                # Create price movement alert
                alert = await self.alert_service.create_price_movement_alert(analysis)

                # Trigger alert event
                from .event_bus import get_event_bus

                alert_event = AlertTriggeredEvent(
                    symbol=event.symbol,
                    alert_type=alert.alert_type.value,
                    severity=alert.severity.value,
                    title=alert.title,
                    message=alert.message,
                    trigger_conditions={
                        "price_change_percent": event.price_change_percent,
                        "movement_threshold": event.movement_threshold,
                        "current_price": event.current_price,
                    },
                )

                await get_event_bus().publish(alert_event)

            except Exception as e:
                self.logger.error(
                    "Failed to process price change event",
                    symbol=event.symbol,
                    error=str(e),
                    exc_info=True,
                )

    async def handle(self, event: DomainEvent):
        """Route events to appropriate handlers."""
        if isinstance(event, StockPriceChangedEvent):
            await self.handle_price_changed(event)


class TrackingEventHandler(EventHandler):
    """Handler for stock tracking events."""

    def __init__(self):
        super().__init__("tracking_handler")

    async def handle_stock_added(self, event: StockAddedToTrackingEvent):
        """Handle stock added to tracking events."""
        self.logger.info(
            "Stock added to tracking",
            symbol=event.symbol,
            added_by=event.added_by,
            validation_passed=event.validation_passed,
        )

        # Could trigger additional actions like:
        # - Send confirmation notification
        # - Update portfolio metrics
        # - Log tracking change

    async def handle_stock_removed(self, event: StockRemovedFromTrackingEvent):
        """Handle stock removed from tracking events."""
        self.logger.info(
            "Stock removed from tracking",
            symbol=event.symbol,
            removed_by=event.removed_by,
            was_active=event.was_active,
        )

        # Could trigger additional actions like:
        # - Send confirmation notification
        # - Archive historical data
        # - Update portfolio metrics

    async def handle(self, event: DomainEvent):
        """Route events to appropriate handlers."""
        if isinstance(event, StockAddedToTrackingEvent):
            await self.handle_stock_added(event)
        elif isinstance(event, StockRemovedFromTrackingEvent):
            await self.handle_stock_removed(event)


class AlertEventHandler(EventHandler):
    """Handler for alert events."""

    def __init__(self):
        super().__init__("alert_handler")
        self.alert_service = AlertService()
        self.notification_service = NotificationService()

    async def handle_alert_triggered(self, event: AlertTriggeredEvent):
        """Handle alert triggered events."""
        self.logger.info(
            "Processing triggered alert",
            symbol=event.symbol,
            alert_type=event.alert_type,
            severity=event.severity,
            should_notify=event.should_notify,
        )

        if not event.should_notify:
            self.logger.debug(
                "Alert notification skipped",
                symbol=event.symbol,
                reason="should_notify=False",
            )
            return

        try:
            # Check if we should send alert today
            from ..services.alert_service import AlertType

            alert_type_enum = AlertType(event.alert_type)

            should_send = await self.alert_service.should_send_alert_today(
                event.symbol, alert_type_enum
            )

            if not should_send:
                self.logger.info(
                    "Alert not sent - already sent today",
                    symbol=event.symbol,
                    alert_type=event.alert_type,
                )
                return

            # Create alert object for notification
            from ..services.alert_service import Alert, AlertSeverity

            alert = Alert(
                symbol=event.symbol,
                alert_type=alert_type_enum,
                severity=AlertSeverity(event.severity),
                title=event.title,
                message=event.message,
                timestamp=event.timestamp,
                metadata=event.trigger_conditions,
            )

            # Send notification via Telegram (hardcoded for now)
            from ..config.settings import get_settings

            settings = get_settings()

            result = await self.notification_service.send_telegram_alert(
                alert, str(settings.telegram_chat_id)
            )

            # Record alert as sent
            await self.alert_service.record_alert_sent(alert)

            # Trigger alert sent event
            from .event_bus import get_event_bus

            sent_event = AlertSentEvent(
                symbol=event.symbol,
                alert_type=event.alert_type,
                notification_channels=["telegram"],
                recipients={"telegram": str(settings.telegram_chat_id)},
                delivery_results=[
                    result.to_dict() if hasattr(result, "to_dict") else str(result)
                ],
                success_count=1 if result.success else 0,
                failure_count=0 if result.success else 1,
            )

            await get_event_bus().publish(sent_event)

        except Exception as e:
            self.logger.error(
                "Failed to handle alert triggered event",
                symbol=event.symbol,
                alert_type=event.alert_type,
                error=str(e),
                exc_info=True,
            )

    async def handle_alert_sent(self, event: AlertSentEvent):
        """Handle alert sent events."""
        self.logger.info(
            "Alert delivery completed",
            symbol=event.symbol,
            alert_type=event.alert_type,
            success_count=event.success_count,
            failure_count=event.failure_count,
            channels=event.notification_channels,
        )

        # Could trigger additional actions like:
        # - Update delivery metrics
        # - Retry failed deliveries
        # - Update alert status

    async def handle(self, event: DomainEvent):
        """Route events to appropriate handlers."""
        if isinstance(event, AlertTriggeredEvent):
            await self.handle_alert_triggered(event)
        elif isinstance(event, AlertSentEvent):
            await self.handle_alert_sent(event)


class NotificationEventHandler(EventHandler):
    """Handler for notification events."""

    def __init__(self):
        super().__init__("notification_handler")

    async def handle(self, event: DomainEvent):
        """Handle notification-related events."""
        # This handler could process notification delivery status,
        # retry failed notifications, or update notification metrics
        pass


class ErrorEventHandler(EventHandler):
    """Handler for error events."""

    def __init__(self):
        super().__init__("error_handler")

    async def handle_error(self, event: ErrorEvent):
        """Handle error events."""
        self.logger.error(
            "System error event received",
            error_type=event.error_type,
            component=event.component,
            operation=event.operation,
            severity=event.severity,
            message=event.error_message,
        )

        # Could trigger additional actions like:
        # - Send error notifications to administrators
        # - Update system health metrics
        # - Trigger recovery procedures
        # - Log to external monitoring systems

    async def handle(self, event: DomainEvent):
        """Route events to appropriate handlers."""
        if isinstance(event, ErrorEvent):
            await self.handle_error(event)


class SystemEventHandler(EventHandler):
    """Handler for system-level events."""

    def __init__(self):
        super().__init__("system_handler")

    async def handle(self, event: DomainEvent):
        """Handle system events like health checks, performance metrics, etc."""
        # This handler could process system health events,
        # performance monitoring events, or system state changes

        self.logger.debug(
            "System event processed",
            event_type=type(event).__name__,
            event_id=event.event_id,
        )


def setup_default_event_handlers():
    """Set up default event handlers on the global event bus."""
    from .event_bus import get_event_bus

    event_bus = get_event_bus()

    # Create handlers
    stock_handler = StockPriceEventHandler()
    tracking_handler = TrackingEventHandler()
    alert_handler = AlertEventHandler()
    notification_handler = NotificationEventHandler()
    error_handler = ErrorEventHandler()
    system_handler = SystemEventHandler()

    # Subscribe handlers to events
    event_bus.subscribe(StockPriceChangedEvent, stock_handler.handle)
    event_bus.subscribe(StockAddedToTrackingEvent, tracking_handler.handle)
    event_bus.subscribe(StockRemovedFromTrackingEvent, tracking_handler.handle)
    event_bus.subscribe(AlertTriggeredEvent, alert_handler.handle)
    event_bus.subscribe(AlertSentEvent, alert_handler.handle)
    event_bus.subscribe(ErrorEvent, error_handler.handle)

    logger.info("Default event handlers configured")
