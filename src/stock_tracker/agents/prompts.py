"""Agent prompt management utilities."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


@lru_cache(maxsize=1)
def load_agent_prompts() -> Dict[str, Any]:
    """
    Load agent prompts from YAML configuration file.

    Returns:
        Dictionary containing agent configurations

    Raises:
        FileNotFoundError: If the prompts file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    prompts_file = Path(__file__).parent / "prompts.yaml"

    try:
        with open(prompts_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Agent prompts file not found: {prompts_file}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing prompts YAML file: {e}")


def get_agent_config(agent_key: str) -> Dict[str, Any]:
    """
    Get configuration for a specific agent.

    Args:
        agent_key: Key identifying the agent (e.g., 'message_handler', 'stock_research')

    Returns:
        Dictionary containing agent configuration

    Raises:
        KeyError: If the agent key doesn't exist
    """
    prompts = load_agent_prompts()

    if agent_key not in prompts.get("agents", {}):
        available_agents = list(prompts.get("agents", {}).keys())
        raise KeyError(
            f"Agent '{agent_key}' not found. Available agents: {available_agents}"
        )

    return prompts["agents"][agent_key]


def get_template(template_key: str) -> str:
    """
    Get a template string from the prompts configuration.

    Args:
        template_key: Key identifying the template

    Returns:
        Template string

    Raises:
        KeyError: If the template key doesn't exist
    """
    prompts = load_agent_prompts()

    # Support nested keys like 'error_messages.general_error'
    keys = template_key.split(".")
    current = prompts.get("templates", {})

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            available_templates = _get_available_template_keys(
                prompts.get("templates", {})
            )
            raise KeyError(
                f"Template '{template_key}' not found. Available templates: {available_templates}"
            )
        current = current[key]

    return current


def _get_available_template_keys(templates: Dict[str, Any], prefix: str = "") -> list:
    """
    Recursively get all available template keys.

    Args:
        templates: Templates dictionary
        prefix: Current key prefix for nested keys

    Returns:
        List of available template keys
    """
    keys = []
    for key, value in templates.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.extend(_get_available_template_keys(value, full_key))
        else:
            keys.append(full_key)
    return keys


# Convenience functions for commonly used prompts
def get_message_handler_config() -> Dict[str, Any]:
    """Get message handler agent configuration."""
    return get_agent_config("message_handler")


def get_stock_research_config() -> Dict[str, Any]:
    """Get stock research agent configuration."""
    return get_agent_config("stock_research")


def get_summarizer_config() -> Dict[str, Any]:
    """Get summarizer agent configuration."""
    return get_agent_config("summarizer")


def get_error_message(error_type: str) -> str:
    """
    Get an error message template.

    Args:
        error_type: Type of error ('general_error', 'research_failed')

    Returns:
        Error message template
    """
    return get_template(f"error_messages.{error_type}")


def get_research_pipeline_template() -> str:
    """Get the research pipeline message template."""
    return get_template("research_pipeline_message")
