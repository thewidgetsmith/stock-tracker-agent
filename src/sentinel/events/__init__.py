"""Event-driven architecture components."""

from .event_bus import EventBus, get_event_bus
from .event_handlers import (
    AlertEventHandler,
    EventHandler,
    NotificationEventHandler,
    StockPriceEventHandler,
)
from .events import (
    AlertSentEvent,
    AlertTriggeredEvent,
    DomainEvent,
    ErrorEvent,
    NotificationSentEvent,
    PortfolioAnalyzedEvent,
    ResearchPipelineEvent,
    StockAddedToTrackingEvent,
    StockPriceChangedEvent,
    StockRemovedFromTrackingEvent,
    SystemHealthCheckEvent,
    UserInteractionEvent,
)

__all__ = [
    # Events
    "DomainEvent",
    "StockPriceChangedEvent",
    "StockAddedToTrackingEvent",
    "StockRemovedFromTrackingEvent",
    "AlertTriggeredEvent",
    "AlertSentEvent",
    "NotificationSentEvent",
    "PortfolioAnalyzedEvent",
    "SystemHealthCheckEvent",
    "UserInteractionEvent",
    "ResearchPipelineEvent",
    "ErrorEvent",
    # Event Bus
    "EventBus",
    "get_event_bus",
    # Event Handlers
    "EventHandler",
    "StockPriceEventHandler",
    "AlertEventHandler",
    "NotificationEventHandler",
]
