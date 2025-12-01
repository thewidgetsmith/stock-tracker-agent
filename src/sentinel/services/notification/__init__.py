"""Unified notification and alert service module."""

from .alert_manager import AlertManager
from .channels import (
    EmailNotificationChannel,
    NotificationChannelProtocol,
    TelegramNotificationChannel,
    WebhookNotificationChannel,
)
from .models import (
    Alert,
    AlertHistory,
    AlertSeverity,
    AlertType,
    NotificationChannel,
    NotificationResult,
)
from .service import NotificationService

__all__ = [
    "Alert",
    "AlertHistory",
    "AlertManager",
    "AlertSeverity",
    "AlertType",
    "EmailNotificationChannel",
    "NotificationChannel",
    "NotificationChannelProtocol",
    "NotificationResult",
    "NotificationService",
    "TelegramNotificationChannel",
    "WebhookNotificationChannel",
]
