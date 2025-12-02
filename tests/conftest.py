"""Shared test configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def isolated_db():
    """Create an isolated database for testing."""
    # Create a temporary database file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".db")
    db_url = f"sqlite:///{temp_path}"

    try:
        # Create engine and session for this test
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create tables
        from sentinel.ormdb.models import Base

        Base.metadata.create_all(bind=engine)

        yield {
            "engine": engine,
            "session_factory": SessionLocal,
            "db_url": db_url,
            "db_path": temp_path,
        }

    finally:
        # Cleanup
        try:
            os.close(temp_fd)
            os.unlink(temp_path)
        except:
            pass


@pytest.fixture
def mock_db_session(isolated_db):
    """Mock database session to use isolated test database."""
    with patch(
        "sentinel.ormdb.database.get_session_factory",
        lambda: isolated_db["session_factory"],
    ):
        with patch("sentinel.ormdb.database.get_engine", lambda: isolated_db["engine"]):
            with patch(
                "sentinel.ormdb.database.get_session_sync",
                lambda: isolated_db["session_factory"](),
            ):
                yield isolated_db["session_factory"]()


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
def mock_telegram_env():
    """Mock Telegram environment variables for all tests to prevent real API calls."""
    from unittest.mock import patch

    with patch.dict(
        "os.environ",
        {
            "TELEGRAM_BOT_TOKEN": "test_bot_token_123456",
            "TELEGRAM_CHAT_ID": "test_chat_id_123456",
        },
    ):
        yield


@pytest.fixture(autouse=True)
def clean_lru_cache():
    """Clear LRU cache between tests to avoid state pollution."""
    from sentinel.agents.prompts import load_agent_prompts

    yield

    # Clear the cache after each test
    load_agent_prompts.cache_clear()


@pytest.fixture(autouse=True)
def mock_agents_api_calls():
    """Mock all external API calls in agents module to prevent real calls during tests."""
    with patch("sentinel.agents.handlers.Runner") as mock_runner:
        # Default mock response for all Runner.run calls
        mock_response = AsyncMock()
        mock_response.final_output = "Mocked AI response"
        mock_runner.run = AsyncMock(return_value=mock_response)

        # Mock core agent_tools to prevent real stock API calls
        with patch("sentinel.core.agent_tools.get_stock_price_info") as mock_stock_info:
            with patch(
                "sentinel.core.agent_tools.get_tracked_stocks_list"
            ) as mock_get_stocks:
                with patch(
                    "sentinel.core.agent_tools.add_stock_to_tracker"
                ) as mock_add_stock:
                    with patch(
                        "sentinel.core.agent_tools.remove_stock_from_tracker"
                    ) as mock_remove_stock:
                        with patch(
                            "sentinel.comm.telegram.send_telegram_message"
                        ) as mock_telegram:

                            # Configure default mock returns
                            mock_stock_info.return_value = {
                                "symbol": "AAPL",
                                "price": 150.0,
                                "change": 2.0,
                            }
                            mock_get_stocks.return_value = ["AAPL", "GOOGL", "MSFT"]
                            mock_add_stock.return_value = "Stock added successfully"
                            mock_remove_stock.return_value = (
                                "Stock removed successfully"
                            )
                            mock_telegram.return_value = None

                            yield {
                                "runner": mock_runner,
                                "stock_info": mock_stock_info,
                                "get_stocks": mock_get_stocks,
                                "add_stock": mock_add_stock,
                                "remove_stock": mock_remove_stock,
                                "telegram": mock_telegram,
                            }
