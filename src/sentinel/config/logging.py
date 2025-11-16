"""Structured logging configuration using structlog."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.types import Processor


def setup_logging(
    level: str = "INFO",
    format_type: str = "structured",
    file_enabled: bool = True,
    file_path: str = "data/sentinel.log",
    max_file_size: str = "10MB",
    backup_count: int = 5,
) -> None:
    """
    Set up application logging with structlog.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format ('structured' or 'plain')
        file_enabled: Whether to enable file logging
        file_path: Path to log file
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
    """
    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Configure processors based on format type
    processors: list[Processor] = [
        # Add timestamp
        structlog.processors.TimeStamper(fmt="ISO"),
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add positional args
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Process stack info
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
        # Add unicode handling
        structlog.processors.UnicodeDecoder(),
    ]

    if format_type == "structured":
        # JSON output for structured logging
        processors.extend(
            [
                # Remove color codes for file output
                (
                    structlog.dev.ConsoleRenderer()
                    if not file_enabled
                    else structlog.processors.JSONRenderer()
                ),
            ]
        )
    else:
        # Plain text output
        processors.extend(
            [
                # Human-readable console output
                structlog.dev.ConsoleRenderer(colors=True),
            ]
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Set up file logging if enabled
    if file_enabled:
        _setup_file_logging(file_path, max_file_size, backup_count, log_level)


def _setup_file_logging(
    file_path: str,
    max_file_size: str,
    backup_count: int,
    log_level: int,
) -> None:
    """Set up rotating file handler for logging."""
    # Create log directory if it doesn't exist
    log_file = Path(file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Parse max file size
    size_bytes = _parse_file_size(max_file_size)

    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=size_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(log_level)

    # Use JSON format for file output
    file_formatter = logging.Formatter("%(message)s")
    file_handler.setFormatter(file_formatter)

    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)


def _parse_file_size(size_str: str) -> int:
    """Parse file size string into bytes."""
    size_str = size_str.strip().upper()

    if size_str.endswith("KB"):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith("MB"):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith("GB"):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        # Assume bytes
        return int(size_str)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (defaults to calling module)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def add_log_context(**kwargs: Any) -> None:
    """
    Add context to all subsequent log messages in the current context.

    Args:
        **kwargs: Key-value pairs to add to log context
    """
    logger = get_logger()
    return logger.bind(**kwargs)


class LoggerMixin:
    """Mixin class to add structured logging to any class."""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get a logger bound to this class."""
        return get_logger(self.__class__.__name__)

    def log_with_context(self, **context: Any) -> structlog.stdlib.BoundLogger:
        """Get a logger with additional context."""
        return self.logger.bind(**context)


def log_function_call(func_name: str, **kwargs: Any) -> structlog.stdlib.BoundLogger:
    """
    Create a logger with function call context.

    Args:
        func_name: Name of the function being called
        **kwargs: Additional context to log

    Returns:
        Logger with function context
    """
    logger = get_logger()
    return logger.bind(function=func_name, **kwargs)


def log_performance(operation: str, duration_ms: float, **context: Any) -> None:
    """
    Log performance metrics.

    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        **context: Additional context
    """
    logger = get_logger("performance")
    logger.info(
        "Performance metric",
        operation=operation,
        duration_ms=duration_ms,
        **context,
    )


def log_error(error: Exception, **context: Any) -> None:
    """
    Log an error with structured context.

    Args:
        error: The exception that occurred
        **context: Additional context
    """
    logger = get_logger("error")
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        exc_info=True,
        **context,
    )


def log_audit_event(event: str, user_id: str = None, **context: Any) -> None:
    """
    Log an audit event.

    Args:
        event: Description of the event
        user_id: ID of the user who triggered the event
        **context: Additional context
    """
    logger = get_logger("audit")
    logger.info(
        "Audit event",
        event=event,
        user_id=user_id,
        **context,
    )
