"""Main notification service orchestration."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from ...config.logging import get_logger
from .alert_manager import AlertManager
from .channels import (
    EmailNotificationChannel,
    NotificationChannelProtocol,
    TelegramNotificationChannel,
    WebhookNotificationChannel,
)
from .models import Alert, NotificationChannel, NotificationResult

logger = get_logger(__name__)


class NotificationService:
    """Service for managing alerts and sending notifications through multiple channels."""

    def __init__(self):
        self.logger = logger.bind(service="notification_service")
        self.alert_manager = AlertManager()

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

    # Delegate alert management methods to AlertManager
    async def create_price_movement_alert(self, *args, **kwargs):
        """Create a price movement alert."""
        return await self.alert_manager.create_price_movement_alert(*args, **kwargs)

    async def create_daily_summary_alert(self, *args, **kwargs):
        """Create a daily summary alert."""
        return await self.alert_manager.create_daily_summary_alert(*args, **kwargs)

    async def create_custom_alert(self, *args, **kwargs):
        """Create a custom alert."""
        return await self.alert_manager.create_custom_alert(*args, **kwargs)

    async def should_send_alert_today(self, *args, **kwargs):
        """Check if alert should be sent today."""
        return await self.alert_manager.should_send_alert_today(*args, **kwargs)

    async def record_alert_sent(self, *args, **kwargs):
        """Record that an alert was sent."""
        return await self.alert_manager.record_alert_sent(*args, **kwargs)

    async def get_alert_history(self, *args, **kwargs):
        """Get alert history."""
        return await self.alert_manager.get_alert_history(*args, **kwargs)

    async def get_alert_statistics(self):
        """Get alert statistics."""
        return await self.alert_manager.get_alert_statistics()
