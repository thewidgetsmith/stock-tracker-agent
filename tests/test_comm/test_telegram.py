"""Tests for communication modules."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.append("src")
from sentinel.comm.telegram import TelegramBot, send_telegram_message


class TestTelegramBot:
    """Test the TelegramBot class."""

    def test_telegram_bot_initialization(self):
        """Test that TelegramBot initializes correctly."""
        bot = TelegramBot()
        assert bot.base_url.startswith("https://api.telegram.org/bot")
        # Check that required attributes exist
        assert hasattr(bot, "bot_token")
        assert hasattr(bot, "chat_id")

    @pytest.mark.asyncio
    async def test_send_message_with_storage(self):
        """Test that send_message stores outgoing messages locally."""
        bot = TelegramBot()

        with patch(
            "sentinel.comm.telegram.chat_history_manager"
        ) as mock_history_manager:
            with patch("aiohttp.ClientSession") as mock_session_class:
                # Create mock session
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session

                # Create mock response
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {"ok": True, "result": {}}

                # Mock the post call to return the mock response
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__.return_value = mock_response
                mock_session.post.return_value = mock_context_manager

                result = await bot.send_message("Test message", chat_id="test_chat")

                # Verify that message was sent successfully
                assert result is True

                # Verify that bot response was stored
                mock_history_manager.store_bot_response.assert_called_once_with(
                    "test_chat", "Test message"
                )

    @pytest.mark.asyncio
    async def test_send_message_functionality(self):
        """Test that send_message works correctly."""
        # This tests the global send_telegram_message function
        with patch("sentinel.comm.telegram.telegram_bot") as mock_bot:
            mock_bot.send_message = AsyncMock()

            await send_telegram_message("Test message")

            # Verify bot.send_message was called
            mock_bot.send_message.assert_called_once_with("Test message")


class TestTelegramBotIntegration:
    """Integration tests for Telegram bot functionality."""

    def test_global_telegram_bot_instance_exists(self):
        """Test that the global telegram_bot instance is created."""
        from sentinel.comm.telegram import telegram_bot

        assert telegram_bot is not None
        assert isinstance(telegram_bot, TelegramBot)

    def test_get_chat_history_method_still_exists(self):
        """Test that the get_chat_history method still exists (now uses local storage)."""
        from sentinel.comm.telegram import telegram_bot

        # Verify the method exists (now uses ChatHistoryManager internally)
        assert hasattr(telegram_bot, "get_chat_history")
        assert callable(telegram_bot.get_chat_history)

    def test_send_message_method_exists(self):
        """Test that the send_message method exists and is callable."""
        from sentinel.comm.telegram import telegram_bot

        # Verify the method exists
        assert hasattr(telegram_bot, "send_message")
        assert callable(telegram_bot.send_message)
