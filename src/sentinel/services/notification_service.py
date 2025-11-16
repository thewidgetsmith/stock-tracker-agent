"""Notification service for sending alerts through various channels."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from ..comm.telegram import telegram_bot
from ..config.logging import get_logger
from .alert_service import Alert, AlertSeverity

logger = get_logger(__name__)


class NotificationChannel(Enum):
    """Available notification channels."""

    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


@dataclass
class NotificationResult:
    """Result of notification delivery attempt."""

    channel: NotificationChannel
    success: bool
    message_id: Optional[str]
    error: Optional[str]
    delivery_time_ms: float


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


class NotificationService:
    """Service for managing and sending notifications through multiple channels."""

    def __init__(self):
        self.logger = logger.bind(service="notification_service")

        # Initialize available notification channels
        self.channels = {
            NotificationChannel.TELEGRAM: TelegramNotificationChannel(),
            NotificationChannel.EMAIL: EmailNotificationChannel(),
            NotificationChannel.WEBHOOK: WebhookNotificationChannel(),
        }

    async def send_alert(
        self,
        alert: Alert,
        channels: List[NotificationChannel],
        recipients: Dict[NotificationChannel, str],
        **kwargs,
    ) -> List[NotificationResult]:
        """
        Send alert through specified channels.

        Args:
            alert: Alert to send
            channels: List of channels to use
            recipients: Mapping of channels to recipient identifiers
            **kwargs: Additional parameters for channels

        Returns:
            List of NotificationResult objects
        """
        self.logger.info(
            "Sending alert through channels",
            symbol=alert.symbol,
            alert_type=alert.alert_type.value,
            severity=alert.severity.value,
            channels=[ch.value for ch in channels],
        )

        results = []

        # Send through each channel concurrently
        tasks = []
        for channel in channels:
            if channel in recipients and channel in self.channels:
                recipient = recipients[channel]
                channel_impl = self.channels[channel]

                task = channel_impl.send_notification(alert, recipient, **kwargs)
                tasks.append(task)
            else:
                # Create failed result for missing channel/recipient
                results.append(
                    NotificationResult(
                        channel=channel,
                        success=False,
                        message_id=None,
                        error=f"No recipient configured for {channel.value} or channel not available",
                        delivery_time_ms=0,
                    )
                )

        if tasks:
            # Execute all channel deliveries concurrently
            channel_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in channel_results:
                if isinstance(result, Exception):
                    # Handle exceptions from channel delivery
                    self.logger.error(
                        "Channel delivery raised exception",
                        error=str(result),
                        exc_info=True,
                    )
                    results.append(
                        NotificationResult(
                            channel=NotificationChannel.TELEGRAM,  # Default for error
                            success=False,
                            message_id=None,
                            error=str(result),
                            delivery_time_ms=0,
                        )
                    )
                else:
                    results.append(result)

        # Log delivery summary
        successful = sum(1 for r in results if r.success)
        total = len(results)

        self.logger.info(
            "Alert delivery completed",
            symbol=alert.symbol,
            successful_deliveries=successful,
            total_attempts=total,
            success_rate=successful / total if total > 0 else 0,
        )

        return results

    async def send_telegram_alert(
        self, alert: Alert, chat_id: str
    ) -> NotificationResult:
        """
        Convenience method to send alert via Telegram only.

        Args:
            alert: Alert to send
            chat_id: Telegram chat ID

        Returns:
            NotificationResult for Telegram delivery
        """
        return await self.channels[NotificationChannel.TELEGRAM].send_notification(
            alert, chat_id
        )

    async def get_channel_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all notification channels.

        Returns:
            Dictionary with channel status information
        """
        status = {}

        for channel_type, channel_impl in self.channels.items():
            # Basic health check - could be enhanced with actual connectivity tests
            status[channel_type.value] = {
                "available": True,
                "implementation": type(channel_impl).__name__,
                "last_checked": datetime.utcnow().isoformat(),
            }

        return status

    def add_notification_channel(
        self,
        channel_type: NotificationChannel,
        implementation: NotificationChannelProtocol,
    ):
        """
        Add or replace a notification channel implementation.

        Args:
            channel_type: Type of notification channel
            implementation: Channel implementation
        """
        self.channels[channel_type] = implementation

        self.logger.info(
            "Notification channel added",
            channel_type=channel_type.value,
            implementation=type(implementation).__name__,
        )
