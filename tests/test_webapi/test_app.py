"""Tests for FastAPI application endpoints."""

import json
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

sys.path.append("src")


class TestFastAPIApp:
    """Test the FastAPI application endpoints."""

    @pytest.fixture(scope="function")
    def env_vars(self):
        """Setup environment variables for testing."""
        test_env = {
            "ENDPOINT_AUTH_TOKEN": "test_endpoint_token",
            "TELEGRAM_AUTH_TOKEN": "test_telegram_token",
            "TELEGRAM_CHAT_ID": "123456789",
        }

        with patch.dict(os.environ, test_env, clear=False):
            yield test_env

    @pytest.fixture
    def app(self, env_vars):
        """Create test FastAPI app with mocked dependencies."""
        from sentinel.webapi.app import create_app

        return create_app()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def async_client(self, app):
        """Create async test client."""
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.fixture
    def mock_telegram_bot(self):
        """Mock telegram bot."""
        mock_bot = Mock()
        mock_bot.extract_message_info.return_value = (
            "test message",
            "123456789",
            "user123",
        )
        mock_bot.send_message = AsyncMock()
        mock_bot.set_webhook = AsyncMock(return_value=True)
        mock_bot.get_webhook_info = AsyncMock(return_value={"ok": True, "url": ""})
        mock_bot.delete_webhook = AsyncMock(return_value=True)
        return mock_bot

    # Root and Health Endpoints Tests

    def test_root_endpoint_requires_auth(self, client):
        """Test that root endpoint requires authentication."""
        response = client.get("/")
        assert response.status_code == 403

    def test_root_endpoint_with_valid_auth(self, client):
        """Test root endpoint with valid authentication."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        response = client.get("/", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "Sentinel is running"}

    def test_root_endpoint_with_invalid_auth(self, client):
        """Test root endpoint with invalid authentication."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/", headers=headers)
        assert response.status_code == 401
        assert "Invalid authentication token" in response.json()["detail"]

    def test_health_endpoint_requires_auth(self, client):
        """Test that health endpoint requires authentication."""
        response = client.get("/health")
        assert response.status_code == 403

    def test_health_endpoint_with_valid_auth(self, client):
        """Test health endpoint with valid authentication."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_endpoint_with_invalid_auth(self, client):
        """Test health endpoint with invalid authentication."""
        headers = {"Authorization": "Bearer wrong_token"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 401

    # Authentication Function Tests

    def test_verify_auth_token_no_env_var(self):
        """Test auth verification when ENDPOINT_AUTH_TOKEN is not set."""
        from fastapi.security import HTTPAuthorizationCredentials

        from sentinel.webapi.app import verify_auth_token

        with patch.dict(os.environ, {}, clear=True):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="test"
            )
            with pytest.raises(Exception) as exc_info:
                verify_auth_token(credentials)
            assert "ENDPOINT_AUTH_TOKEN environment variable not set" in str(
                exc_info.value
            )

    def test_verify_auth_token_valid(self):
        """Test auth verification with valid token."""
        from fastapi.security import HTTPAuthorizationCredentials

        from sentinel.webapi.app import verify_auth_token

        with patch.dict(os.environ, {"ENDPOINT_AUTH_TOKEN": "test_token"}):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="test_token"
            )
            result = verify_auth_token(credentials)
            assert result == "test_token"

    def test_verify_auth_token_invalid(self):
        """Test auth verification with invalid token."""
        from fastapi.security import HTTPAuthorizationCredentials

        from sentinel.webapi.app import verify_auth_token

        with patch.dict(os.environ, {"ENDPOINT_AUTH_TOKEN": "correct_token"}):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="wrong_token"
            )
            with pytest.raises(Exception) as exc_info:
                verify_auth_token(credentials)
            assert "Invalid authentication token" in str(exc_info.value)

    # Telegram Webhook Authentication Tests

    def test_verify_telegram_webhook_auth_no_env_var(self):
        """Test telegram webhook auth when TELEGRAM_AUTH_TOKEN is not set."""
        from sentinel.webapi.app import verify_telegram_webhook_auth

        with patch.dict(os.environ, {}, clear=True):
            mock_request = Mock()
            mock_request.headers.get.return_value = "some_token"
            result = verify_telegram_webhook_auth(mock_request)
            assert result is False

    def test_verify_telegram_webhook_auth_valid(self):
        """Test telegram webhook auth with valid token."""
        from sentinel.webapi.app import verify_telegram_webhook_auth

        with patch.dict(os.environ, {"TELEGRAM_AUTH_TOKEN": "test_telegram_token"}):
            mock_request = Mock()
            mock_request.headers.get.return_value = "test_telegram_token"
            result = verify_telegram_webhook_auth(mock_request)
            assert result is True

    def test_verify_telegram_webhook_auth_invalid(self):
        """Test telegram webhook auth with invalid token."""
        from sentinel.webapi.app import verify_telegram_webhook_auth

        with patch.dict(os.environ, {"TELEGRAM_AUTH_TOKEN": "correct_token"}):
            mock_request = Mock()
            mock_request.headers.get.return_value = "wrong_token"
            result = verify_telegram_webhook_auth(mock_request)
            assert result is False

    def test_verify_telegram_webhook_auth_missing_header(self):
        """Test telegram webhook auth with missing header."""
        from sentinel.webapi.app import verify_telegram_webhook_auth

        with patch.dict(os.environ, {"TELEGRAM_AUTH_TOKEN": "test_token"}):
            mock_request = Mock()
            mock_request.headers.get.return_value = None
            result = verify_telegram_webhook_auth(mock_request)
            assert result is False

    # Webhook Management Tests

    def test_set_webhook_requires_auth(self, client):
        """Test that set webhook endpoint requires authentication."""
        response = client.post("/webhook/set?webhook_url=https://test.com")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_set_webhook_with_valid_auth(self, async_client, mock_telegram_bot):
        """Test setting webhook with valid authentication."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        webhook_url = "https://test.example.com/webhook"

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.post(
                f"/webhook/set?webhook_url={webhook_url}", headers=headers
            )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "webhook set successfully"
        assert response_data["url"] == webhook_url
        assert response_data["secret_token_configured"] is True
        mock_telegram_bot.set_webhook.assert_called_once_with(
            webhook_url, secret_token="test_telegram_token"
        )

    @pytest.mark.asyncio
    async def test_set_webhook_failure(self, async_client, mock_telegram_bot):
        """Test setting webhook when telegram bot fails."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        webhook_url = "https://test.example.com/webhook"

        # Configure the AsyncMock to return False
        mock_telegram_bot.set_webhook.return_value = False

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.post(
                f"/webhook/set?webhook_url={webhook_url}", headers=headers
            )

        # The 400 HTTPException gets caught by the outer exception handler and becomes a 500
        assert response.status_code == 500
        assert "Failed to set webhook" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_webhook_exception(self, async_client, mock_telegram_bot):
        """Test setting webhook when exception occurs."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        webhook_url = "https://test.example.com/webhook"

        mock_telegram_bot.set_webhook.side_effect = Exception("Network error")

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.post(
                f"/webhook/set?webhook_url={webhook_url}", headers=headers
            )

        assert response.status_code == 500
        assert "Error setting webhook: Network error" in response.json()["detail"]

    def test_webhook_info_requires_auth(self, client):
        """Test that webhook info endpoint requires authentication."""
        response = client.get("/webhook/info")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_webhook_info_with_valid_auth(self, async_client, mock_telegram_bot):
        """Test webhook info endpoint with valid authentication."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        mock_info = {
            "ok": True,
            "url": "https://test.com",
            "has_custom_certificate": False,
        }
        mock_telegram_bot.get_webhook_info.return_value = mock_info

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.get("/webhook/info", headers=headers)

        assert response.status_code == 200
        assert response.json() == mock_info
        mock_telegram_bot.get_webhook_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_info_exception(self, async_client, mock_telegram_bot):
        """Test webhook info endpoint when exception occurs."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        mock_telegram_bot.get_webhook_info.side_effect = Exception("API error")

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.get("/webhook/info", headers=headers)

        assert response.status_code == 500
        assert "Error getting webhook info: API error" in response.json()["detail"]

    def test_delete_webhook_requires_auth(self, client):
        """Test that delete webhook endpoint requires authentication."""
        response = client.delete("/webhook")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_webhook_with_valid_auth(
        self, async_client, mock_telegram_bot
    ):
        """Test deleting webhook with valid authentication."""
        headers = {"Authorization": "Bearer test_endpoint_token"}

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.delete("/webhook", headers=headers)

        assert response.status_code == 200
        assert response.json()["status"] == "webhook deleted successfully"
        mock_telegram_bot.delete_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_webhook_failure(self, async_client, mock_telegram_bot):
        """Test deleting webhook when telegram bot fails."""
        headers = {"Authorization": "Bearer test_endpoint_token"}

        # Configure the AsyncMock to return False
        mock_telegram_bot.delete_webhook.return_value = False

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.delete("/webhook", headers=headers)

        # The 400 HTTPException gets caught by the outer exception handler and becomes a 500
        assert response.status_code == 500
        assert "Failed to delete webhook" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_webhook_exception(self, async_client, mock_telegram_bot):
        """Test deleting webhook when exception occurs."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        mock_telegram_bot.delete_webhook.side_effect = Exception("Connection error")

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.delete("/webhook", headers=headers)

        assert response.status_code == 500
        assert "Error deleting webhook: Connection error" in response.json()["detail"]

    # Telegram Webhook Tests

    def test_telegram_webhook_requires_secret_header(self, client):
        """Test that telegram webhook requires X-Telegram-Bot-Api-Secret-Token header."""
        webhook_data = {
            "message": {
                "text": "test message",
                "chat": {"id": "123456789"},
                "from": {"id": "test_user"},
            }
        }

        response = client.post("/webhook/tg-nqlftdvdqi", json=webhook_data)
        assert response.status_code == 404  # Returns 404 when auth fails
        assert "Not Found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_telegram_webhook_with_valid_header(
        self, async_client, mock_telegram_bot
    ):
        """Test telegram webhook with valid secret token header."""
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test_telegram_token"}
        webhook_data = {
            "message": {
                "text": "test message",
                "chat": {"id": "123456789"},
                "from": {"id": "user123"},
                "message_id": 1234,
            }
        }

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            with patch(
                "sentinel.webapi.app.handle_incoming_message", new_callable=AsyncMock
            ) as mock_handler:
                with patch(
                    "sentinel.webapi.app.chat_history_manager"
                ) as mock_chat_manager:
                    mock_handler.return_value = "Test response"

                    response = await async_client.post(
                        "/webhook/tg-nqlftdvdqi", json=webhook_data, headers=headers
                    )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify interactions
        mock_telegram_bot.extract_message_info.assert_called_once_with(webhook_data)
        mock_chat_manager.store_user_message.assert_called_once()
        mock_handler.assert_called_once_with("test message", chat_id="123456789")
        mock_telegram_bot.send_message.assert_called_once_with(
            "Test response", chat_id="123456789"
        )

    @pytest.mark.asyncio
    async def test_telegram_webhook_unauthorized_chat(
        self, async_client, mock_telegram_bot
    ):
        """Test telegram webhook with unauthorized chat ID."""
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test_telegram_token"}
        webhook_data = {
            "message": {
                "text": "test message",
                "chat": {"id": "unauthorized_chat"},
                "from": {"id": "user123"},
            }
        }

        mock_telegram_bot.extract_message_info.return_value = (
            "test message",
            "unauthorized_chat",
            "user123",
        )

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.post(
                "/webhook/tg-nqlftdvdqi", json=webhook_data, headers=headers
            )

        assert response.status_code == 200
        assert response.json()["status"] == "unauthorized"
        mock_telegram_bot.send_message.assert_called_once_with(
            "Sorry, you are not authorized to use this bot.",
            chat_id="unauthorized_chat",
        )

    @pytest.mark.asyncio
    async def test_telegram_webhook_empty_message(
        self, async_client, mock_telegram_bot
    ):
        """Test telegram webhook with empty message."""
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test_telegram_token"}
        webhook_data = {"message": {}}

        mock_telegram_bot.extract_message_info.return_value = ("", None, None)

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            response = await async_client.post(
                "/webhook/tg-nqlftdvdqi", json=webhook_data, headers=headers
            )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_telegram_webhook_processing_exception(
        self, async_client, mock_telegram_bot
    ):
        """Test telegram webhook when message processing throws exception."""
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test_telegram_token"}
        webhook_data = {
            "message": {
                "text": "test message",
                "chat": {"id": "123456789"},
                "from": {"id": "user123"},
            }
        }

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            with patch(
                "sentinel.webapi.app.handle_incoming_message",
                side_effect=Exception("Processing error"),
            ):
                response = await async_client.post(
                    "/webhook/tg-nqlftdvdqi", json=webhook_data, headers=headers
                )

        assert response.status_code == 500
        assert response.json()["error"] == "Internal server error"

    @pytest.mark.asyncio
    async def test_telegram_webhook_no_username(self, async_client, mock_telegram_bot):
        """Test telegram webhook with message from user without first_name."""
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test_telegram_token"}
        webhook_data = {
            "message": {
                "text": "test message",
                "chat": {"id": "123456789"},
                "from": {"id": "user123"},
                # No first_name in from object
            }
        }

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            with patch(
                "sentinel.webapi.app.handle_incoming_message", new_callable=AsyncMock
            ) as mock_handler:
                with patch(
                    "sentinel.webapi.app.chat_history_manager"
                ) as mock_chat_manager:
                    mock_handler.return_value = "Test response"

                    response = await async_client.post(
                        "/webhook/tg-nqlftdvdqi", json=webhook_data, headers=headers
                    )

        assert response.status_code == 200

        # Verify default username is used
        call_args = mock_chat_manager.store_user_message.call_args
        assert call_args[1]["username"] == "User"

    @pytest.mark.asyncio
    async def test_telegram_webhook_no_message_id(
        self, async_client, mock_telegram_bot
    ):
        """Test telegram webhook with message without message_id."""
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test_telegram_token"}
        webhook_data = {
            "message": {
                "text": "test message",
                "chat": {"id": "123456789"},
                "from": {"id": "user123", "first_name": "TestUser"},
                # No message_id
            }
        }

        with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
            with patch(
                "sentinel.webapi.app.handle_incoming_message", new_callable=AsyncMock
            ) as mock_handler:
                with patch(
                    "sentinel.webapi.app.chat_history_manager"
                ) as mock_chat_manager:
                    mock_handler.return_value = "Test response"

                    response = await async_client.post(
                        "/webhook/tg-nqlftdvdqi", json=webhook_data, headers=headers
                    )

        assert response.status_code == 200

        # Verify None is passed for message_id
        call_args = mock_chat_manager.store_user_message.call_args
        assert call_args[1]["message_id"] is None

    # Environment Variable Tests

    @pytest.mark.asyncio
    async def test_set_webhook_no_telegram_auth_token(
        self, async_client, mock_telegram_bot
    ):
        """Test setting webhook when TELEGRAM_AUTH_TOKEN is not set."""
        headers = {"Authorization": "Bearer test_endpoint_token"}
        webhook_url = "https://test.example.com/webhook"

        with patch.dict(os.environ, {"TELEGRAM_AUTH_TOKEN": ""}, clear=False):
            with patch("sentinel.webapi.app.telegram_bot", mock_telegram_bot):
                response = await async_client.post(
                    f"/webhook/set?webhook_url={webhook_url}", headers=headers
                )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["secret_token_configured"] is False
        mock_telegram_bot.set_webhook.assert_called_once_with(
            webhook_url, secret_token=""
        )


class TestCreateApp:
    """Test the create_app function itself."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        from fastapi import FastAPI

        from sentinel.webapi.app import create_app

        app = create_app()
        assert isinstance(app, FastAPI)
        assert app.title == "Sentinel"
        assert (
            app.description == "AI-powered stock monitoring with Telegram notifications"
        )
        assert app.version == "1.0.0"
