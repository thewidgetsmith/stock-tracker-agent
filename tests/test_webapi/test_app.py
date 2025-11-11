"""Tests for FastAPI application endpoints."""

# Import your app
import sys
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

sys.path.append("src")
from stock_tracker.webapi.app import create_app


@pytest.fixture
def app():
    """Create test FastAPI app."""
    return create_app()


@pytest.mark.asyncio
async def test_root_endpoint(app):
    """Test the root health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Stock Tracker Agent is running"}


@pytest.mark.asyncio
async def test_health_endpoint(app):
    """Test the health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_webhook_info_requires_auth(app, test_env_vars):
    """Test that webhook info endpoint requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/webhook/info")

    assert response.status_code == 401
    assert "Invalid or missing authorization" in response.text.lower()


@pytest.mark.asyncio
async def test_webhook_info_with_valid_auth(app, test_env_vars, mock_telegram_bot):
    """Test webhook info endpoint with valid authentication."""
    headers = {"Authorization": f"Bearer {test_env_vars['TELEGRAM_AUTH_TOKEN']}"}

    with patch("stock_tracker.api.app.telegram_bot", mock_telegram_bot):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/webhook/info", headers=headers)

    assert response.status_code == 200
    mock_telegram_bot.get_webhook_info.assert_called_once()


@pytest.mark.asyncio
async def test_set_webhook_requires_auth(app):
    """Test that set webhook endpoint requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/webhook/set?webhook_url=https://test.com")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_set_webhook_with_auth(app, test_env_vars, mock_telegram_bot):
    """Test setting webhook with valid authentication."""
    headers = {"Authorization": f"Bearer {test_env_vars['TELEGRAM_AUTH_TOKEN']}"}
    webhook_url = "https://test.example.com/webhook"

    with patch("stock_tracker.api.app.telegram_bot", mock_telegram_bot):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post(
                f"/webhook/set?webhook_url={webhook_url}", headers=headers
            )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "webhook set successfully"
    assert response_data["url"] == webhook_url

    mock_telegram_bot.set_webhook.assert_called_once()


@pytest.mark.asyncio
async def test_delete_webhook_with_auth(app, test_env_vars, mock_telegram_bot):
    """Test deleting webhook with valid authentication."""
    headers = {"Authorization": f"Bearer {test_env_vars['TELEGRAM_AUTH_TOKEN']}"}

    with patch("stock_tracker.api.app.telegram_bot", mock_telegram_bot):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.delete("/webhook", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "webhook deleted successfully"
    mock_telegram_bot.delete_webhook.assert_called_once()


@pytest.mark.asyncio
async def test_telegram_webhook_requires_secret_header(app, test_env_vars):
    """Test that telegram webhook requires X-Telegram-Bot-Api-Secret-Token header."""
    webhook_data = {
        "message": {
            "text": "test message",
            "chat": {"id": test_env_vars["TELEGRAM_CHAT_ID"]},
            "from": {"id": "test_user"},
        }
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/webhook/tg-nqlftdvdqi", json=webhook_data)

    assert response.status_code == 401
    assert "Invalid or missing X-Telegram-Bot-Api-Secret-Token" in response.text


@pytest.mark.asyncio
async def test_telegram_webhook_with_valid_header(
    app, test_env_vars, mock_telegram_bot
):
    """Test telegram webhook with valid secret token header."""
    headers = {"X-Telegram-Bot-Api-Secret-Token": test_env_vars["TELEGRAM_AUTH_TOKEN"]}
    webhook_data = {
        "message": {
            "text": "test message",
            "chat": {"id": test_env_vars["TELEGRAM_CHAT_ID"]},
            "from": {"id": "test_user"},
        }
    }

    with patch("stock_tracker.api.app.telegram_bot", mock_telegram_bot):
        with patch(
            "stock_tracker.api.app.handle_incoming_message", new_callable=AsyncMock
        ) as mock_handler:
            mock_handler.return_value = "Test response"

            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post(
                    "/webhook/tg-nqlftdvdqi", json=webhook_data, headers=headers
                )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
