"""Domain events for the stock tracking system."""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Union, List
from uuid import uuid4


@dataclass
class DomainEvent(ABC):
    """Base class for all domain events."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        result = {
            "event_type": self.__class__.__name__,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_version": self.event_version,
            "metadata": self.metadata,
        }

        # Add event-specific fields
        for field_name, field_value in self.__dict__.items():
            if field_name not in ["event_id", "timestamp", "event_version", "metadata"]:
                if isinstance(field_value, datetime):
                    result[field_name] = field_value.isoformat()
                else:
                    result[field_name] = field_value

        return result


@dataclass
class StockPriceChangedEvent(DomainEvent):
    """Event triggered when a stock price changes significantly."""

    symbol: str = ""
    previous_price: float = 0.0
    current_price: float = 0.0
    price_change: float = 0.0
    price_change_percent: float = 0.0
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    is_significant_movement: bool = False
    movement_threshold: Optional[str] = None


@dataclass
class StockAddedToTrackingEvent(DomainEvent):
    """Event triggered when a stock is added to tracking."""

    symbol: str = ""
    added_by: Optional[str] = None
    validation_passed: bool = True
    initial_price: Optional[float] = None


@dataclass
class StockRemovedFromTrackingEvent(DomainEvent):
    """Event triggered when a stock is removed from tracking."""

    symbol: str = ""
    removed_by: Optional[str] = None
    was_active: bool = True
    final_price: Optional[float] = None


@dataclass
class AlertTriggeredEvent(DomainEvent):
    """Event triggered when an alert condition is met."""

    alert_id: str = ""
    symbol: str = ""
    alert_type: str = ""
    threshold_value: float = 0.0
    current_price: float = 0.0
    message: str = ""
    severity: str = "normal"
    title: str = ""
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    should_notify: bool = True


@dataclass
class AlertSentEvent(DomainEvent):
    """Event triggered when an alert is successfully sent."""

    symbol: str = ""
    alert_type: str = ""
    notification_channels: List[str] = field(default_factory=list)
    recipients: Dict[str, str] = field(default_factory=dict)
    delivery_results: List[Dict[str, Any]] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0


@dataclass
class NotificationSentEvent(DomainEvent):
    """Event triggered when a notification is sent."""
    
    channel: str = ""
    message: str = ""
    recipient: str = ""
    delivery_status: str = "pending"
    response_time_ms: float = 0.0


@dataclass
class PortfolioAnalyzedEvent(DomainEvent):
    """Event triggered when portfolio analysis is completed."""

    total_stocks: int = 0
    analyzed_stocks: int = 0
    significant_movements: int = 0
    average_change_percent: float = 0.0
    analysis_duration_ms: float = 0.0
    top_movers: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SystemHealthCheckEvent(DomainEvent):
    """Event triggered during system health checks."""

    overall_health: str = "unknown"
    database_health: str = "unknown"
    external_services_health: str = "unknown"
    uptime_seconds: float = 0.0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserInteractionEvent(DomainEvent):
    """Event triggered by user interactions."""

    user_id: str = ""
    action: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    response_time_ms: float = 0.0


@dataclass
class ResearchPipelineEvent(DomainEvent):
    """Event triggered by research pipeline operations."""

    symbol: str = ""
    trigger_reason: str = ""
    research_type: str = ""
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


@dataclass
class ErrorEvent(DomainEvent):
    """Event triggered when errors occur in the system."""

    error_type: str = ""
    error_message: str = ""
    component: str = ""
    operation: str = ""
    severity: str = "error"
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
