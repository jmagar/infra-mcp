"""
Structured logging configuration with request-scoped correlation IDs.

- Provides setup_logging() to configure structlog + stdlib bridge
- Exposes request_id_var ContextVar and helpers
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import logging
from typing import Any, MutableMapping

import structlog

# Context variable to carry request correlation id across async tasks
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def _add_request_id_event_dict(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Structlog processor to inject request_id from contextvars."""
    rid = request_id_var.get()
    if rid is not None:
        event_dict["request_id"] = rid
    return event_dict


def _iso_time(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured logging with stdlib bridge.

    This sets up structlog to render JSON and configures the stdlib logging
    to route through structlog so existing logging.getLogger() usage works.
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_id_event_dict,
            _iso_time,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        wrapper_class=structlog.stdlib.BoundLogger,
    )

    # Configure standard logging to forward to structlog
    handler = logging.StreamHandler()
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            _add_request_id_event_dict,
            _iso_time,
            structlog.stdlib.add_log_level,
        ],
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Clear existing handlers to avoid duplicate logs
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Reduce noisy loggers
    logging.getLogger("asyncssh").setLevel(logging.WARNING)


def get_request_id() -> str | None:
    return request_id_var.get()


def set_request_id(value: str | None) -> None:
    request_id_var.set(value)
