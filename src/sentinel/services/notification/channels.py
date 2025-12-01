"""Notification channel implementations."""

import asyncio
from datetime import datetime
from typing import Protocol

from ...comm.telegram import telegram_bot
from ...config.logging import get_logger
from .models import Alert, AlertSeverity, NotificationChannel, NotificationResult

logger = get_logger(__name__)


class NotificationChannelProtocol(Protocol):
    """Protocol for notification channel implementations."""

    async def send_notification(
        self, alert: Alert, recipient: str, **kwargs
    ) -> NotificationResult:
        """Send notification through this channel."""
        ...


class TelegramNotificationChannel:
    """Telegram notification channel implementation."""

    def __init__(self):
        self.logger = logger.bind(channel="telegram")

    async def send_notification(
        self, alert: Alert, recipient: str, **kwargs
    ) -> NotificationResult:
        """
        Send alert notification via Telegram.

        Args:
            alert: Alert to send
            recipient: Telegram chat ID
            **kwargs: Additional parameters

        Returns:
            NotificationResult with delivery status
        """
        start_time = datetime.utcnow()

        try:
            # Format message for Telegram
            message = self._format_telegram_message(alert)

            # Send via Telegram bot
            await telegram_bot.send_message(message, chat_id=recipient)

            delivery_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            self.logger.info(
                "Telegram notification sent successfully",
                symbol=alert.symbol,
                chat_id=recipient,
                alert_type=alert.alert_type.value,
                delivery_time_ms=delivery_time,
            )

            return NotificationResult(
                channel=NotificationChannel.TELEGRAM,
                success=True,
                message_id=None,  # Telegram bot doesn't return message ID in this implementation
                error=None,
                delivery_time_ms=delivery_time,
            )

        except Exception as e:
            delivery_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            self.logger.error(
                "Failed to send Telegram notification",
                symbol=alert.symbol,
                chat_id=recipient,
                error=str(e),
                exc_info=True,
            )

            return NotificationResult(
                channel=NotificationChannel.TELEGRAM,
                success=False,
                message_id=None,
                error=str(e),
                delivery_time_ms=delivery_time,
            )

    def _format_telegram_message(self, alert: Alert) -> str:
        """
        Format alert as Telegram message.

        Args:
            alert: Alert to format

        Returns:
            Formatted message string
        """
        # Use emoji based on severity
        severity_emojis = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }

        emoji = severity_emojis.get(alert.severity, "📈")

        # Format timestamp
        time_str = alert.timestamp.strftime("%H:%M:%S")

        message = f"{emoji} **{alert.title}**\n\n"
        message += f"{alert.message}\n\n"
        message += f"🕐 {time_str}"

        # Add metadata if available
        if alert.metadata:
            if "current_price" in alert.metadata:
                message += f"\n💰 Current: ${alert.metadata['current_price']:.2f}"
            if "price_change_percent" in alert.metadata:
                change = alert.metadata["price_change_percent"]
                direction = "📈" if change > 0 else "📉"
                message += f"\n{direction} Change: {change:+.2%}"

        return message


class EmailNotificationChannel:
    """Email notification channel implementation (placeholder)."""

    def __init__(self):
        self.logger = logger.bind(channel="email")

    async def send_notification(
        self, alert: Alert, recipient: str, **kwargs
    ) -> NotificationResult:
        """
        Send alert notification via Email.

        Note: This is a placeholder implementation.
        """
        start_time = datetime.utcnow()

        self.logger.info(
            "Email notification requested (placeholder)",
            symbol=alert.symbol,
            recipient=recipient,
        )

        # Simulate email sending delay
        await asyncio.sleep(0.1)

        delivery_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return NotificationResult(
            channel=NotificationChannel.EMAIL,
            success=False,  # Not implemented yet
            message_id=None,
            error="Email notifications not implemented",
            delivery_time_ms=delivery_time,
        )


class WebhookNotificationChannel:
    """Webhook notification channel implementation (placeholder)."""

    def __init__(self):
        self.logger = logger.bind(channel="webhook")

    async def send_notification(
        self, alert: Alert, recipient: str, **kwargs
    ) -> NotificationResult:
        """
        Send alert notification via Webhook.

        Note: This is a placeholder implementation.
        """
        start_time = datetime.utcnow()

        self.logger.info(
            "Webhook notification requested (placeholder)",
            symbol=alert.symbol,
            recipient=recipient,
        )

        delivery_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return NotificationResult(
            channel=NotificationChannel.WEBHOOK,
            success=False,  # Not implemented yet
            message_id=None,
            error="Webhook notifications not implemented",
            delivery_time_ms=delivery_time,
        )
