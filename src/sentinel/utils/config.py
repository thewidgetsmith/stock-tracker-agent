"""Configuration and environment utilities."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from ..config.logging import get_logger, setup_logging

# Import new configuration system
from ..config.settings import (
    get_required_env_vars,
    get_settings,
    validate_required_settings,
)

# For backward compatibility
REQUIRED_VARS = get_required_env_vars()


def ensure_resources_directory() -> None:
    """Ensure the resources directory and database are initialized."""
    logger = get_logger(__name__)

    # Get settings to use configured data directory
    settings = get_settings()
    resources_path = Path(settings.data_directory)
    resources_path.mkdir(exist_ok=True)

    logger.info("Ensured data directory exists", path=str(resources_path))

    # Initialize database tables
    from ..db.database import create_tables

    create_tables()
    logger.info("Ensured database tables exist")


def initialize_application() -> None:
    """Initialize application configuration and logging."""
    # Get settings (this will load from environment)
    settings = get_settings()

    # Setup logging with configured settings
    setup_logging(
        level=settings.log_level,
        format_type=settings.log_format,
        file_enabled=settings.log_file_enabled,
        file_path=settings.log_file_path,
        max_file_size=settings.log_max_file_size,
        backup_count=settings.log_backup_count,
    )

    # Initialize resources
    ensure_resources_directory()

    logger = get_logger(__name__)
    logger.info(
        "Application initialized successfully",
        environment=settings.environment,
        debug=settings.debug,
        data_dir=settings.data_directory,
    )


def load_config() -> Dict[str, Any]:
    """
    Load and validate configuration from environment variables.

    DEPRECATED: Use get_settings() instead.
    This function is kept for backward compatibility.
    """
    logger = get_logger(__name__)
    logger.warning("load_config() is deprecated, use get_settings() instead")

    settings = get_settings()

    return {
        "telegram_bot_token": settings.telegram_bot_token,
        "telegram_chat_id": settings.telegram_chat_id,
        "openai_api_key": settings.openai_api_key,
        "webhook_url": settings.telegram_webhook_url,
        "host": settings.endpoint_host,
        "port": settings.endpoint_port,
    }


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.

    Returns:
        True if all required variables are set, False otherwise
    """
    return validate_required_settings()
