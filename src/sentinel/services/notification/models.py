"""Data models for notification and alert services."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


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


class NotificationChannel(Enum):
    """Available notification channels."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


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


@dataclass
class NotificationResult:
    """Result of notification delivery attempt."""

    channel: NotificationChannel
    success: bool
    message_id: Optional[str]
    error: Optional[str]
    delivery_time_ms: float
