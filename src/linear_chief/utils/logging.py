"""Structured logging configuration with JSON and console formatters.

This module provides centralized logging configuration for the Linear Chief of Staff
application. It supports both JSON-structured logs (for production) and human-readable
console logs (for development).

Features:
- JSON structured logs with python-json-logger
- Console logs with colors and readable formatting
- Configurable via environment variables
- Log file rotation support
- Context injection (request_id, session_id, etc.)
- Exception logging with stack traces
- Performance logging helpers
"""

import asyncio
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import contextvars
from pythonjsonlogger import jsonlogger

# Context variables for request tracking
request_id_ctx = contextvars.ContextVar("request_id", default=None)
session_id_ctx = contextvars.ContextVar("session_id", default=None)
user_id_ctx = contextvars.ContextVar("user_id", default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional context fields.

    Automatically injects request_id, session_id, user_id from context variables.
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """
        Add custom fields to the log record.

        Args:
            log_record: Dictionary that will be logged as JSON
            record: Standard Python LogRecord
            message_dict: Dictionary of message fields
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add log level
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add process and thread info
        log_record["process"] = record.process
        log_record["thread"] = record.thread

        # Add context variables if present
        request_id = request_id_ctx.get()
        if request_id:
            log_record["request_id"] = request_id

        session_id = session_id_ctx.get()
        if session_id:
            log_record["session_id"] = session_id

        user_id = user_id_ctx.get()
        if user_id:
            log_record["user_id"] = user_id

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Console formatter with colors for different log levels.

    Provides human-readable logs with color coding for easy scanning.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(self, use_colors: bool = True):
        """
        Initialize formatter.

        Args:
            use_colors: Whether to use ANSI colors (disable for non-TTY)
        """
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.use_colors = use_colors and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.

        Args:
            record: Log record to format

        Returns:
            Formatted log string with colors
        """
        if self.use_colors:
            # Color the log level
            levelname = record.levelname
            color = self.COLORS.get(levelname, "")
            record.levelname = f"{color}{self.BOLD}{levelname}{self.RESET}"

        # Format the base message
        formatted = super().format(record)

        # Add context variables if present
        context_parts = []
        request_id = request_id_ctx.get()
        if request_id:
            context_parts.append(f"request_id={request_id}")
        session_id = session_id_ctx.get()
        if session_id:
            context_parts.append(f"session_id={session_id}")
        user_id = user_id_ctx.get()
        if user_id:
            context_parts.append(f"user_id={user_id}")

        if context_parts:
            formatted = f"{formatted} [{', '.join(context_parts)}]"

        return formatted


def setup_logging(
    level: str = "INFO",
    format_type: str = "console",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Configure logging for the application.

    This should be called once at application startup, typically in __main__.py.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("json" or "console")
        log_file: Optional file path for log output
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup log files to keep (default: 5)

    Raises:
        ValueError: If invalid log level or format type provided
    """
    # Validate log level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    # Validate format type
    if format_type not in ("json", "console"):
        raise ValueError(
            f"Invalid format type: {format_type}. Must be 'json' or 'console'"
        )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)

    # Set formatter based on type
    if format_type == "json":
        formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
    else:
        formatter = ColoredConsoleFormatter(use_colors=True)

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if log file specified
    if log_file:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)

        # Always use JSON format for file logs
        json_formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    # Log initialization
    logger = get_logger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": level,
            "log_format": format_type,
            "log_file": str(log_file) if log_file else None,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    This is the recommended way to get a logger in any module.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance

    Example:
        >>> from linear_chief.utils.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Hello, world!")
    """
    return logging.getLogger(name)


def set_request_id(request_id: str) -> None:
    """
    Set request ID for current context.

    This will be automatically included in all log messages.

    Args:
        request_id: Unique request identifier
    """
    request_id_ctx.set(request_id)


def set_session_id(session_id: str) -> None:
    """
    Set session ID for current context.

    This will be automatically included in all log messages.

    Args:
        session_id: Session identifier
    """
    session_id_ctx.set(session_id)


def set_user_id(user_id: str) -> None:
    """
    Set user ID for current context.

    This will be automatically included in all log messages.

    Args:
        user_id: User identifier
    """
    user_id_ctx.set(user_id)


def clear_context() -> None:
    """
    Clear all context variables.

    Call this at the end of a request/session to avoid context leakage.
    """
    request_id_ctx.set(None)
    session_id_ctx.set(None)
    user_id_ctx.set(None)


class LogContext:
    """
    Context manager for setting log context variables.

    Automatically clears context on exit to prevent leakage.

    Example:
        >>> with LogContext(request_id="req-123", user_id="user-456"):
        ...     logger.info("Processing request")  # Will include request_id and user_id
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Initialize context.

        Args:
            request_id: Optional request identifier
            session_id: Optional session identifier
            user_id: Optional user identifier
        """
        self.request_id = request_id
        self.session_id = session_id
        self.user_id = user_id
        self._tokens = []

    def __enter__(self):
        """Enter context and set variables."""
        if self.request_id:
            self._tokens.append(request_id_ctx.set(self.request_id))
        if self.session_id:
            self._tokens.append(session_id_ctx.set(self.session_id))
        if self.user_id:
            self._tokens.append(user_id_ctx.set(self.user_id))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous values."""
        for token in reversed(self._tokens):
            try:
                token.var.reset(token)
            except ValueError:
                # Token already reset, ignore
                pass


def log_execution_time(logger: logging.Logger, operation: str):
    """
    Decorator to log execution time of a function.

    Args:
        logger: Logger instance to use
        operation: Name of the operation being timed

    Example:
        >>> logger = get_logger(__name__)
        >>> @log_execution_time(logger, "fetch_issues")
        ... async def fetch_issues():
        ...     # ... fetch issues
        ...     pass
    """

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                start_time = datetime.utcnow()
                try:
                    result = await func(*args, **kwargs)
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.info(
                        f"{operation} completed",
                        extra={
                            "operation": operation,
                            "duration_seconds": duration,
                            "success": True,
                        },
                    )
                    return result
                except Exception as e:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.error(
                        f"{operation} failed",
                        extra={
                            "operation": operation,
                            "duration_seconds": duration,
                            "success": False,
                            "error_type": type(e).__name__,
                        },
                        exc_info=True,
                    )
                    raise

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs):
                start_time = datetime.utcnow()
                try:
                    result = func(*args, **kwargs)
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.info(
                        f"{operation} completed",
                        extra={
                            "operation": operation,
                            "duration_seconds": duration,
                            "success": True,
                        },
                    )
                    return result
                except Exception as e:
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    logger.error(
                        f"{operation} failed",
                        extra={
                            "operation": operation,
                            "duration_seconds": duration,
                            "success": False,
                            "error_type": type(e).__name__,
                        },
                        exc_info=True,
                    )
                    raise

            return sync_wrapper

    return decorator
