"""Tests for agent prompt management."""

# Import modules to test
import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

sys.path.append("src")
from stock_tracker.agents.prompts import (
    get_agent_config,
    get_error_message,
    get_message_handler_config,
    get_research_pipeline_template,
    get_stock_research_config,
    get_summarizer_config,
    get_template,
    load_agent_prompts,
)


def test_load_agent_prompts_success(test_yaml_prompts):
    """Test successfully loading agent prompts from YAML file."""
    with patch("stock_tracker.agents.prompts.Path") as mock_path:
        mock_path(__file__).parent = test_yaml_prompts.parent

        # Clear cache first
        load_agent_prompts.cache_clear()

        prompts = load_agent_prompts()

        assert "agents" in prompts
        assert "templates" in prompts
        assert "test_agent" in prompts["agents"]


def test_load_agent_prompts_file_not_found():
    """Test FileNotFoundError when prompts file doesn't exist."""
    with patch("stock_tracker.agents.prompts.Path") as mock_path:
        mock_path(__file__).parent = Path("/nonexistent")

        # Clear cache first
        load_agent_prompts.cache_clear()

        with pytest.raises(FileNotFoundError) as exc_info:
            load_agent_prompts()

        assert "Agent prompts file not found" in str(exc_info.value)


def test_load_agent_prompts_invalid_yaml():
    """Test YAMLError when prompts file has invalid YAML."""
    invalid_yaml = "invalid: yaml: content: ["

    with patch("stock_tracker.agents.prompts.open", mock_open(read_data=invalid_yaml)):
        with patch("stock_tracker.agents.prompts.Path"):
            # Clear cache first
            load_agent_prompts.cache_clear()

            with pytest.raises(yaml.YAMLError):
                load_agent_prompts()


def test_get_agent_config_success(test_yaml_prompts):
    """Test successfully getting agent configuration."""
    with patch("stock_tracker.agents.prompts.Path") as mock_path:
        mock_path(__file__).parent = test_yaml_prompts.parent

        # Clear cache first
        load_agent_prompts.cache_clear()

        config = get_agent_config("test_agent")

        assert config["name"] == "Test Agent"
        assert config["instructions"] == "Test instructions"
        assert config["model"] == "gpt-4o-mini"


def test_get_agent_config_not_found(test_yaml_prompts):
    """Test KeyError when agent key doesn't exist."""
    with patch("stock_tracker.agents.prompts.Path") as mock_path:
        mock_path(__file__).parent = test_yaml_prompts.parent

        # Clear cache first
        load_agent_prompts.cache_clear()

        with pytest.raises(KeyError) as exc_info:
            get_agent_config("nonexistent_agent")

        assert "Agent 'nonexistent_agent' not found" in str(exc_info.value)
        assert "Available agents: ['test_agent']" in str(exc_info.value)


def test_get_template_success(test_yaml_prompts):
    """Test successfully getting template."""
    with patch("stock_tracker.agents.prompts.Path") as mock_path:
        mock_path(__file__).parent = test_yaml_prompts.parent

        # Clear cache first
        load_agent_prompts.cache_clear()

        template = get_template("test_template")
        assert template == "Test template: {variable}"


def test_get_template_nested_key(test_yaml_prompts):
    """Test getting template with nested key."""
    with patch("stock_tracker.agents.prompts.Path") as mock_path:
        mock_path(__file__).parent = test_yaml_prompts.parent

        # Clear cache first
        load_agent_prompts.cache_clear()

        template = get_template("error_messages.test_error")
        assert template == "Test error message"


def test_get_template_not_found(test_yaml_prompts):
    """Test KeyError when template key doesn't exist."""
    with patch("stock_tracker.agents.prompts.Path") as mock_path:
        mock_path(__file__).parent = test_yaml_prompts.parent

        # Clear cache first
        load_agent_prompts.cache_clear()

        with pytest.raises(KeyError) as exc_info:
            get_template("nonexistent_template")

        assert "Template 'nonexistent_template' not found" in str(exc_info.value)


@pytest.mark.parametrize(
    "config_func,expected_agent",
    [
        (get_message_handler_config, "message_handler"),
        (get_stock_research_config, "stock_research"),
        (get_summarizer_config, "summarizer"),
    ],
)
def test_convenience_config_functions(config_func, expected_agent):
    """Test convenience functions for getting agent configs."""
    with patch("stock_tracker.agents.prompts.get_agent_config") as mock_get_config:
        mock_get_config.return_value = {"name": "Test Agent"}

        result = config_func()

        mock_get_config.assert_called_once_with(expected_agent)
        assert result == {"name": "Test Agent"}


@pytest.mark.parametrize(
    "error_type,expected_template",
    [
        ("general_error", "error_messages.general_error"),
        ("research_failed", "error_messages.research_failed"),
    ],
)
def test_get_error_message(error_type, expected_template):
    """Test getting error message templates."""
    with patch("stock_tracker.agents.prompts.get_template") as mock_get_template:
        mock_get_template.return_value = "Error message"

        result = get_error_message(error_type)

        mock_get_template.assert_called_once_with(expected_template)
        assert result == "Error message"


def test_get_research_pipeline_template():
    """Test getting research pipeline template."""
    with patch("stock_tracker.agents.prompts.get_template") as mock_get_template:
        mock_get_template.return_value = "Pipeline template"

        result = get_research_pipeline_template()

        mock_get_template.assert_called_once_with("research_pipeline_message")
        assert result == "Pipeline template"


def test_cache_functionality():
    """Test that LRU cache works correctly."""
    with patch("stock_tracker.agents.prompts.open", mock_open(read_data="agents: {}")):
        with patch("stock_tracker.agents.prompts.Path"):
            # Clear cache first
            load_agent_prompts.cache_clear()

            # First call
            result1 = load_agent_prompts()

            # Second call should use cache
            result2 = load_agent_prompts()

            assert result1 is result2  # Should be the same object (cached)

            # Check cache info
            cache_info = load_agent_prompts.cache_info()
            assert cache_info.hits >= 1
            assert cache_info.misses >= 1
