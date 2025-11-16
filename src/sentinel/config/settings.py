"""Application settings and configuration management using Pydantic."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Main application settings combining all configuration sections."""

    # Environment and deployment
    environment: str = "development"
    debug: bool = False

    # Telegram settings
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_auth_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None

    # AI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_research_model: str = "gpt-4.1"
    openai_max_tokens: int = 4000
    openai_temperature: float = 0.7

    # Tracking settings
    tracking_interval_minutes: int = 60
    price_change_threshold: float = 0.01
    max_tracked_stocks: int = 50
    alert_cooldown_hours: int = 24

    # API settings
    endpoint_host: str = "0.0.0.0"
    endpoint_port: int = 8000
    endpoint_auth_token: Optional[str] = None
    api_reload: bool = False
    api_log_level: str = "INFO"

    # Database settings
    database_url: Optional[str] = None
    data_directory: str = "data"
    database_echo_sql: bool = False
    database_pool_pre_ping: bool = True
    database_pool_recycle: int = 3600

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "structured"  # 'structured' or 'plain'
    log_file_enabled: bool = True
    log_file_path: str = "data/sentinel.log"
    log_max_file_size: str = "10MB"
    log_backup_count: int = 5

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
    }

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_environments = ["development", "testing", "production"]
        if v.lower() not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v.lower()

    @field_validator("telegram_chat_id")
    @classmethod
    def validate_chat_id(cls, v):
        """Validate that chat_id is numeric (Telegram chat IDs are numeric)."""
        if not v.lstrip("-").isdigit():
            raise ValueError("chat_id must be numeric")
        return v

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v):
        """Validate OpenAI API key format."""
        if not v.startswith(("sk-", "sk-proj-")):
            raise ValueError("Invalid OpenAI API key format")
        return v

    @field_validator("tracking_interval_minutes")
    @classmethod
    def validate_interval(cls, v):
        """Validate tracking interval is reasonable."""
        if v < 1 or v > 1440:  # 1 minute to 24 hours
            raise ValueError("Tracking interval must be between 1 and 1440 minutes")
        return v

    @field_validator("price_change_threshold")
    @classmethod
    def validate_threshold(cls, v):
        """Validate price change threshold."""
        if v <= 0 or v > 1:
            raise ValueError("Price change threshold must be between 0 and 1 (0-100%)")
        return v

    @field_validator("endpoint_port")
    @classmethod
    def validate_port(cls, v):
        """Validate port number is in valid range."""
        if v < 1 or v > 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("log_level", "api_log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ["structured", "plain"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of: {valid_formats}")
        return v.lower()

    def get_database_url(self) -> str:
        """Get the complete database URL."""
        if self.database_url:
            return self.database_url

        # Default to SQLite in data directory
        from pathlib import Path

        db_dir = Path(self.data_directory)
        db_dir.mkdir(exist_ok=True)
        db_path = db_dir / "sentinel.db"
        return f"sqlite:///{db_path}"

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application configuration instance
    """
    return Settings()


def validate_required_settings() -> bool:
    """
    Validate that all required settings are properly configured.

    Returns:
        bool: True if all required settings are valid, False otherwise
    """
    try:
        settings = get_settings()

        # Check if we can access all required settings
        _ = settings.telegram_bot_token
        _ = settings.telegram_chat_id
        _ = settings.openai_api_key
        _ = settings.endpoint_auth_token

        return True

    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False


def get_required_env_vars() -> list[str]:
    """
    Get list of required environment variables.

    Returns:
        list: List of required environment variable names
    """
    return [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TELEGRAM_AUTH_TOKEN",
        "OPENAI_API_KEY",
        "ENDPOINT_AUTH_TOKEN",
    ]
