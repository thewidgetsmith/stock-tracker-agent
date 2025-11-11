"""Configuration and environment utilities."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

REQUIRED_VARS = [
    "TELEGRAM_AUTH_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "OPENAI_API_KEY",
]


def ensure_resources_directory() -> None:
    """Ensure the resources directory and required files exist."""
    resources_path = Path("resources")
    resources_path.mkdir(exist_ok=True)

    # Create alert_history.json if it doesn't exist
    alert_history_path = resources_path / "alert_history.json"
    if not alert_history_path.exists():
        with open(alert_history_path, "w") as f:
            json.dump({}, f)
        print("Created alert_history.json")

    # Create tracker_list.json if it doesn't exist
    tracker_list_path = resources_path / "tracker_list.json"
    if not tracker_list_path.exists():
        with open(tracker_list_path, "w") as f:
            json.dump([], f)
        print("Created tracker_list.json")


def load_config() -> Dict[str, Any]:
    """Load and validate configuration from environment variables."""
    config = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "webhook_url": os.getenv("WEBHOOK_URL"),
        "host": os.getenv("ENDPOINT_HOST", "0.0.0.0"),
        "port": int(os.getenv("ENDPOINT_PORT", "8000")),
    }

    # Validate required config
    required_keys = ["telegram_bot_token", "telegram_chat_id", "openai_api_key"]
    missing_keys = [key for key in required_keys if not config[key]]

    if missing_keys:
        raise ValueError(f"Missing required environment variables: {missing_keys}")

    return config


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.

    Returns:
        True if all required variables are set, False otherwise
    """

    missing_vars = []
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        return False

    return True
