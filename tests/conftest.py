"""Shared test configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest
import yaml


@pytest.fixture
def isolated_db():
    """Create an isolated database for testing."""
    # Create a temporary database file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    db_url = f'sqlite:///{temp_path}'
    
    try:
        # Create engine and session for this test
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables
        from sentinel.db.models import Base
        Base.metadata.create_all(bind=engine)
        
        yield {
            'engine': engine,
            'session_factory': SessionLocal,
            'db_url': db_url,
            'db_path': temp_path
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
    with patch('sentinel.db.database.SessionLocal', isolated_db['session_factory']):
        with patch('sentinel.db.database.engine', isolated_db['engine']):
            with patch('sentinel.db.database.get_session_sync', lambda: isolated_db['session_factory']()):
                yield isolated_db['session_factory']()


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
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "test_bot_token_123456",
        "TELEGRAM_CHAT_ID": "test_chat_id_123456"
    }):
        yield


@pytest.fixture(autouse=True)
def clean_lru_cache():
    """Clear LRU cache between tests to avoid state pollution."""
    from src.sentinel.agents.prompts import load_agent_prompts

    yield

    # Clear the cache after each test
    load_agent_prompts.cache_clear()
