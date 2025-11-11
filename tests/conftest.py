"""Shared test configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest
import yaml


@pytest.fixture(scope="session")
def test_env_vars():
    """Set up test environment variables."""
    test_vars = {
        "TELEGRAM_BOT_TOKEN": "test_bot_token",
        "TELEGRAM_CHAT_ID": "test_chat_id",
        "OPENAI_API_KEY": "test_openai_key",
        "TELEGRAM_AUTH_TOKEN": "test_auth_token",
        "HOST": "localhost",
        "PORT": "8000",
    }

    # Store original values
    original_values = {}
    for key, value in test_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield test_vars

    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_telegram_bot():
    """Mock telegram bot for testing."""
    mock_bot = Mock()
    mock_bot.send_message = AsyncMock(return_value=True)
    mock_bot.extract_message_info = Mock(
        return_value=("test message", "test_chat", "test_user")
    )
    mock_bot.get_webhook_info = AsyncMock(return_value={"ok": True, "url": ""})
    mock_bot.set_webhook = AsyncMock(return_value=True)
    mock_bot.delete_webhook = AsyncMock(return_value=True)
    return mock_bot


@pytest.fixture
def mock_stock_data():
    """Mock stock price data for testing."""
    return {
        "AAPL": {"regularMarketPrice": 150.0, "previousClose": 148.0, "symbol": "AAPL"},
        "GOOGL": {
            "regularMarketPrice": 2800.0,
            "previousClose": 2750.0,
            "symbol": "GOOGL",
        },
    }


@pytest.fixture
def temp_resources_dir(tmp_path):
    """Create temporary resources directory for testing."""
    resources_dir = tmp_path / "resources"
    resources_dir.mkdir()

    # Create test tracker list
    tracker_list = []
    with open(resources_dir / "tracker_list.json", "w") as f:
        import json

        json.dump(tracker_list, f)

    # Create test alert history
    alert_history = {}
    with open(resources_dir / "alert_history.json", "w") as f:
        import json

        json.dump(alert_history, f)

    return resources_dir


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for testing."""
    return {
        "name": "Test Agent",
        "instructions": "Test instructions for the agent",
        "model": "gpt-4o-mini",
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.final_output = "Test response from agent"
    return mock_response


@pytest.fixture
def test_yaml_prompts(tmp_path):
    """Create test YAML prompts file."""
    prompts_data = {
        "agents": {
            "test_agent": {
                "name": "Test Agent",
                "instructions": "Test instructions",
                "model": "gpt-4o-mini",
            }
        },
        "templates": {
            "test_template": "Test template: {variable}",
            "error_messages": {"test_error": "Test error message"},
        },
    }

    yaml_file = tmp_path / "prompts.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(prompts_data, f)

    return yaml_file


@pytest.fixture(autouse=True)
def clean_lru_cache():
    """Clear LRU cache between tests to avoid state pollution."""
    from src.stock_tracker.agents.prompts import load_agent_prompts

    yield

    # Clear the cache after each test
    load_agent_prompts.cache_clear()
