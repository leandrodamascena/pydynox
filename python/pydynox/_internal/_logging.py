"""Internal logging helpers."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, Protocol

from pydynox import pydynox_core

# Default logger
_logger: logging.Logger | Any = logging.getLogger("pydynox")

# Correlation ID for request tracing
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class LoggerProtocol(Protocol):
    """Protocol for custom loggers (Powertools, structlog, etc)."""

    def debug(self, msg: str, **kwargs: Any) -> None: ...
    def info(self, msg: str, **kwargs: Any) -> None: ...
    def warning(self, msg: str, **kwargs: Any) -> None: ...
    def error(self, msg: str, **kwargs: Any) -> None: ...


def set_logger(
    logger: LoggerProtocol | logging.Logger,
    sdk_debug: bool = False,
) -> None:
    """Set a custom logger for pydynox.

    Works with stdlib logging, AWS Lambda Powertools Logger, structlog, etc.

    Args:
        logger: Any logger with debug/info/warning/error methods.
        sdk_debug: If True, enable AWS SDK debug logs via RUST_LOG.

    Example:
        >>> import logging
        >>> logging.getLogger("pydynox").setLevel(logging.DEBUG)

        >>> # Or with Powertools
        >>> from aws_lambda_powertools import Logger
        >>> from pydynox import set_logger
        >>> set_logger(Logger())

        >>> # Enable SDK debug logs
        >>> set_logger(Logger(), sdk_debug=True)
    """
    global _logger
    _logger = logger

    if sdk_debug:
        pydynox_core.enable_sdk_debug()


def get_logger() -> logging.Logger | Any:
    """Get the current logger."""
    return _logger


def set_correlation_id(correlation_id: str | None) -> None:
    """Set correlation ID for request tracing.

    Useful in Lambda to track requests across logs.

    Args:
        correlation_id: The correlation ID (e.g., context.aws_request_id).

    Example:
        >>> from pydynox import set_correlation_id
        >>> def handler(event, context):
        ...     set_correlation_id(context.aws_request_id)
        ...     # All pydynox logs will include this ID
    """
    _correlation_id.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get the current correlation ID."""
    return _correlation_id.get()


def _log_operation(
    operation: str,
    table: str,
    duration_ms: float,
    consumed_rcu: float | None = None,
    consumed_wcu: float | None = None,
    items_count: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log an operation at INFO level.

    Internal function called after each DynamoDB operation.
    """
    parts = [f"{operation} table={table} duration_ms={duration_ms:.1f}"]

    if consumed_rcu is not None:
        parts.append(f"rcu={consumed_rcu:.1f}")
    if consumed_wcu is not None:
        parts.append(f"wcu={consumed_wcu:.1f}")
    if items_count is not None:
        parts.append(f"items={items_count}")

    msg = " ".join(parts)

    # Add correlation ID if set
    correlation_id = get_correlation_id()
    kwargs: dict[str, Any] = {}
    if correlation_id:
        kwargs["correlation_id"] = correlation_id
    if extra:
        kwargs.update(extra)

    # Handle both stdlib and custom loggers
    if kwargs and hasattr(_logger, "info"):
        try:
            _logger.info(msg, extra=kwargs)
        except TypeError:
            # Some loggers (like Powertools) use **kwargs directly
            _logger.info(msg, **kwargs)
    else:
        _logger.info(msg)


def _log_debug(operation: str, msg: str, **kwargs: Any) -> None:
    """Log at DEBUG level."""
    correlation_id = get_correlation_id()
    if correlation_id:
        kwargs["correlation_id"] = correlation_id

    full_msg = f"{operation} {msg}"

    if kwargs and hasattr(_logger, "debug"):
        try:
            _logger.debug(full_msg, extra=kwargs)
        except TypeError:
            _logger.debug(full_msg, **kwargs)
    else:
        _logger.debug(full_msg)


def _log_warning(operation: str, msg: str, **kwargs: Any) -> None:
    """Log at WARNING level (throttling, retries, slow queries)."""
    correlation_id = get_correlation_id()
    if correlation_id:
        kwargs["correlation_id"] = correlation_id

    full_msg = f"{operation} {msg}"

    if kwargs and hasattr(_logger, "warning"):
        try:
            _logger.warning(full_msg, extra=kwargs)
        except TypeError:
            _logger.warning(full_msg, **kwargs)
    else:
        _logger.warning(full_msg)


def _log_error(operation: str, msg: str, **kwargs: Any) -> None:
    """Log at ERROR level."""
    correlation_id = get_correlation_id()
    if correlation_id:
        kwargs["correlation_id"] = correlation_id

    full_msg = f"{operation} {msg}"

    if kwargs and hasattr(_logger, "error"):
        try:
            _logger.error(full_msg, extra=kwargs)
        except TypeError:
            _logger.error(full_msg, **kwargs)
    else:
        _logger.error(full_msg)
