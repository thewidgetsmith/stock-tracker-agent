"""Tests for communication modules."""

import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.append("src")
from sentinel.comm.telegram import (
    TelegramBot,
    send_telegram_message,
    send_telegram_message_sync,
)


@pytest.fixture(autouse=True)
def mock_aiohttp():
    """Mock the entire aiohttp module to prevent any real HTTP requests."""

    # Create proper async context manager classes
    class MockResponseContext:
        def __init__(self, response):
            self.response = response

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    class MockSessionContext:
        def __init__(self, session):
            self.session = session

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    with patch("sentinel.comm.telegram.aiohttp.ClientSession") as mock_client_session:
        # Create mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True, "result": {}})
        mock_response.text = AsyncMock(return_value="Success")

        # Create mock session
        mock_session = Mock()
        mock_session.post = Mock(return_value=MockResponseContext(mock_response))
        mock_session.get = Mock(return_value=MockResponseContext(mock_response))

        # Configure ClientSession to return the session context manager
        mock_client_session.return_value = MockSessionContext(mock_session)

        yield {
            "session": mock_session,
            "response": mock_response,
            "client_session": mock_client_session,
        }


class TestTelegramBot:
    """Test the TelegramBot class."""

    def test_telegram_bot_initialization(self):
        """Test that TelegramBot initializes correctly."""
        bot = TelegramBot()
        assert bot.base_url.startswith("https://api.telegram.org/bot")
        # Check that required attributes exist
        assert hasattr(bot, "bot_token")
        assert hasattr(bot, "chat_id")

    def test_telegram_bot_initialization_with_custom_values(self):
        """Test TelegramBot initialization with custom values."""
        custom_token = "custom_token"
        custom_chat_id = "custom_chat"
        bot = TelegramBot(bot_token=custom_token, chat_id=custom_chat_id)

        assert bot.bot_token == custom_token
        assert bot.chat_id == custom_chat_id
        assert f"bot{custom_token}" in bot.base_url

    def test_telegram_bot_initialization_without_token(self):
        """Test that TelegramBot raises error without token."""
        # Clear the TELEGRAM_BOT_TOKEN and override the mock
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": ""}, clear=False):
            with patch("sentinel.comm.telegram.TELEGRAM_BOT_TOKEN", None):
                with pytest.raises(ValueError, match="Telegram bot token is required"):
                    TelegramBot()

    @pytest.mark.asyncio
    async def test_send_message_with_storage(self, mock_aiohttp):
        """Test that send_message stores outgoing messages locally."""
        bot = TelegramBot()

        with patch(
            "sentinel.comm.telegram.chat_history_manager"
        ) as mock_history_manager:
            result = await bot.send_message("Test message", chat_id="test_chat")

            # Verify that message was sent successfully
            assert result is True

            # Verify that bot response was stored
            mock_history_manager.store_bot_response.assert_called_once_with(
                "test_chat", "Test message"
            )

    @pytest.mark.asyncio
    async def test_send_message_without_chat_id(self):
        """Test send_message fails without chat_id."""
        # Create bot with explicitly no chat_id and override environment
        with patch.dict("os.environ", {"TELEGRAM_CHAT_ID": ""}, clear=False):
            with patch("sentinel.comm.telegram.TELEGRAM_CHAT_ID", None):
                bot = TelegramBot(chat_id=None)

                result = await bot.send_message("Test message")
                assert result is False

    @pytest.mark.asyncio
    async def test_send_message_with_http_error(self, mock_aiohttp):
        """Test send_message handles HTTP errors gracefully."""
        bot = TelegramBot()

        # Configure mock for HTTP error response
        mock_aiohttp["response"].status = 400
        mock_aiohttp["response"].text = AsyncMock(return_value="Bad Request")

        with patch("sentinel.comm.telegram.chat_history_manager"):
            result = await bot.send_message("Test message", chat_id="test_chat")

            # Verify that message sending failed
            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_with_exception(self, mock_aiohttp):
        """Test send_message handles exceptions gracefully."""
        bot = TelegramBot()

        # Configure ClientSession to raise exception
        mock_aiohttp["client_session"].side_effect = Exception("Network error")

        with patch("sentinel.comm.telegram.chat_history_manager"):
            result = await bot.send_message("Test message", chat_id="test_chat")

            # Verify that message sending failed
            assert result is False

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

    @pytest.mark.asyncio
    async def test_get_webhook_info(self, mock_aiohttp):
        """Test getting webhook information."""
        bot = TelegramBot()

        # Configure mock response for webhook info
        mock_aiohttp["response"].json = AsyncMock(
            return_value={
                "ok": True,
                "result": {
                    "url": "https://example.com/webhook",
                    "has_custom_certificate": False,
                    "pending_update_count": 0,
                },
            }
        )

        result = await bot.get_webhook_info()

        assert result["ok"] is True
        assert "result" in result
        assert result["result"]["url"] == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_set_webhook_success(self, mock_aiohttp):
        """Test setting webhook successfully."""
        bot = TelegramBot()

        # Configure mock response for successful webhook setting
        mock_aiohttp["response"].json = AsyncMock(return_value={"ok": True})

        result = await bot.set_webhook("https://example.com/webhook")

        assert result is True

    @pytest.mark.asyncio
    async def test_set_webhook_with_secret_token(self, mock_aiohttp):
        """Test setting webhook with secret token."""
        bot = TelegramBot()

        # Configure mock response for successful webhook setting
        mock_aiohttp["response"].json = AsyncMock(return_value={"ok": True})

        result = await bot.set_webhook("https://example.com/webhook", "secret123")

        assert result is True

    @pytest.mark.asyncio
    async def test_set_webhook_failure(self, mock_aiohttp):
        """Test webhook setting failure."""
        bot = TelegramBot()

        # Configure mock response for failed webhook setting
        mock_aiohttp["response"].json = AsyncMock(
            return_value={"ok": False, "description": "Bad webhook URL"}
        )

        result = await bot.set_webhook("invalid-url")

        assert result is False

    @pytest.mark.asyncio
    async def test_set_webhook_exception(self, mock_aiohttp):
        """Test webhook setting with exception."""
        bot = TelegramBot()

        # Configure mock to raise exception
        mock_aiohttp["client_session"].side_effect = Exception("Network error")

        result = await bot.set_webhook("https://example.com/webhook")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_webhook_success(self, mock_aiohttp):
        """Test deleting webhook successfully."""
        bot = TelegramBot()

        # Configure mock response for successful webhook deletion
        mock_aiohttp["response"].json = AsyncMock(return_value={"ok": True})

        result = await bot.delete_webhook()

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_webhook_failure(self, mock_aiohttp):
        """Test webhook deletion failure."""
        bot = TelegramBot()

        # Configure mock response for failed webhook deletion
        mock_aiohttp["response"].json = AsyncMock(return_value={"ok": False})

        result = await bot.delete_webhook()

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_webhook_exception(self, mock_aiohttp):
        """Test webhook deletion with exception."""
        bot = TelegramBot()

        # Configure mock to raise exception
        mock_aiohttp["client_session"].side_effect = Exception("Network error")

        result = await bot.delete_webhook()

        assert result is False

    def test_extract_message_info_valid_message(self):
        """Test extracting message information from valid update."""
        bot = TelegramBot()

        update = {
            "message": {
                "text": "Hello world",
                "chat": {"id": 12345},
                "from": {"id": 67890},
            }
        }

        text, chat_id, user_id = bot.extract_message_info(update)

        assert text == "Hello world"
        assert chat_id == "12345"
        assert user_id == "67890"

    def test_extract_message_info_no_message(self):
        """Test extracting message information from update without message."""
        bot = TelegramBot()

        update = {"update_id": 123}  # No message field

        text, chat_id, user_id = bot.extract_message_info(update)

        assert text is None
        assert chat_id is None
        assert user_id is None

    def test_extract_message_info_incomplete_message(self):
        """Test extracting message information from incomplete message."""
        bot = TelegramBot()

        update = {
            "message": {
                "text": "Hello",
                # Missing chat and from fields
            }
        }

        text, chat_id, user_id = bot.extract_message_info(update)

        assert text == "Hello"
        assert chat_id == ""  # Empty string due to str() conversion of empty dict
        assert user_id == ""

    def test_send_telegram_message_sync_no_loop(self):
        """Test synchronous telegram message sending without event loop."""
        with patch("sentinel.comm.telegram.asyncio.get_running_loop") as mock_get_loop:
            with patch("sentinel.comm.telegram.asyncio.run") as mock_run:
                # Simulate no running event loop
                mock_get_loop.side_effect = RuntimeError("No running event loop")

                send_telegram_message_sync("Test message")

                # Should use asyncio.run
                mock_run.assert_called_once()

    def test_send_telegram_message_sync_with_loop(self):
        """Test synchronous telegram message sending with existing event loop."""
        with patch("sentinel.comm.telegram.asyncio.get_running_loop") as mock_get_loop:
            # Simulate running event loop
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop

            send_telegram_message_sync("Test message")

            # Should create task on existing loop
            mock_loop.create_task.assert_called_once()

    def test_get_chat_history_error_handling(self):
        """Test get_chat_history method error handling."""
        from sentinel.comm.telegram import telegram_bot

        with patch("sentinel.comm.telegram.chat_history_manager") as mock_manager:
            # Configure manager to raise exception
            mock_manager.get_chat_history.side_effect = Exception("Database error")

            result = telegram_bot.get_chat_history("test_chat")

            assert result == []

    def test_get_chat_history_no_chat_id(self):
        """Test get_chat_history with no chat_id provided."""
        # Test with bot that has no default chat_id
        with patch("sentinel.comm.telegram.TELEGRAM_CHAT_ID", None):
            bot = TelegramBot(chat_id=None)

            result = bot.get_chat_history()  # No chat_id parameter

            assert result == []
