"""Telegram bot functionality for communications handling."""

import asyncio
import os
from typing import Any, Dict, Optional

import aiohttp
from dotenv import load_dotenv

from .chat_history import chat_history_manager

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class TelegramBot:
    """Telegram Bot client for sending messages and handling webhooks."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        if not self.bot_token:
            raise ValueError("Telegram bot token is required")

    async def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        """
        Send a message to a Telegram chat.

        Args:
            text: Message text to send
            chat_id: Target chat ID (uses default if not provided)

        Returns:
            True if message sent successfully, False otherwise
        """
        target_chat_id = chat_id or self.chat_id

        if not target_chat_id:
            print("Error: No chat ID provided")
            return False

        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": "HTML",  # Allow HTML formatting
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        print(f"Message sent successfully to chat {target_chat_id}")
                        # Store the outgoing message in chat history
                        self.store_outgoing_message(text, target_chat_id)
                        return True
                    else:
                        error_text = await response.text()
                        print(
                            f"Failed to send message: {response.status} - {error_text}"
                        )
                        return False
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False

    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information."""
        url = f"{self.base_url}/getWebhookInfo"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    async def set_webhook(
        self, webhook_url: str, secret_token: Optional[str] = None
    ) -> bool:
        """
        Set webhook URL for receiving updates.

        Args:
            webhook_url: URL where Telegram will send updates
            secret_token: Optional secret token for webhook security

        Returns:
            True if webhook set successfully, False otherwise
        """
        url = f"{self.base_url}/setWebhook"
        data = {"url": webhook_url}

        # Add secret token if provided
        if secret_token:
            data["secret_token"] = secret_token

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("ok"):
                        print(f"Webhook set successfully to: {webhook_url}")
                        if secret_token:
                            print("Secret token configured for webhook security")
                        return True
                    else:
                        print(f"Failed to set webhook: {result}")
                        return False
        except Exception as e:
            print(f"Error setting webhook: {e}")
            return False

    async def delete_webhook(self) -> bool:
        """Delete the current webhook."""
        url = f"{self.base_url}/deleteWebhook"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    result = await response.json()
                    return result.get("ok", False)
        except Exception as e:
            print(f"Error deleting webhook: {e}")
            return False

    def store_outgoing_message(self, text: str, chat_id: Optional[str] = None) -> None:
        """
        Store an outgoing bot message in chat history.

        Args:
            text: Message text sent by bot
            chat_id: Target chat ID
        """
        target_chat_id = chat_id or self.chat_id
        if target_chat_id:
            chat_history_manager.store_bot_response(target_chat_id, text)

    def get_chat_history(
        self, chat_id: Optional[str] = None, limit: int = 10
    ) -> list[Dict[str, Any]]:
        """
        Get recent chat history from local storage.

        Args:
            chat_id: Target chat ID (uses default if not provided)
            limit: Maximum number of messages to retrieve

        Returns:
            List of message objects in chronological order (oldest first)
        """
        target_chat_id = chat_id or self.chat_id

        if not target_chat_id:
            print("Error: No chat ID provided for history retrieval")
            return []

        try:
            return chat_history_manager.get_chat_history(target_chat_id, limit)
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []

    def extract_message_info(
        self, update: Dict[str, Any]
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract message information from Telegram update.

        Args:
            update: Telegram update object

        Returns:
            Tuple of (message_text, chat_id, user_id)
        """
        message = update.get("message")
        if not message:
            return None, None, None

        text = message.get("text")
        chat_id = str(message.get("chat", {}).get("id", ""))
        user_id = str(message.get("from", {}).get("id", ""))

        return text, chat_id, user_id


# Global bot instance
telegram_bot = TelegramBot()


async def send_telegram_message(text: str) -> None:
    """
    Send a message via Telegram (convenience function).

    Args:
        text: Message text to send
    """
    await telegram_bot.send_message(text)


def send_telegram_message_sync(text: str) -> None:
    """
    Synchronous wrapper for sending Telegram messages.

    Args:
        text: Message text to send
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we have a running loop, create a task
        task = loop.create_task(send_telegram_message(text))
        # Since this is meant to be sync, we'll just start the task
        # Note: This won't wait for completion in sync context
        print(f"Telegram message queued: {text[:50]}...")
    except RuntimeError:
        # No running event loop, safe to use asyncio.run
        asyncio.run(send_telegram_message(text))
