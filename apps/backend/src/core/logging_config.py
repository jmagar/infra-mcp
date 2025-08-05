"""
Structured Logging Configuration

Provides centralized logging configuration with correlation IDs,
structured formatting, and enhanced error classification.
"""

import logging
import logging.config
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any
from contextvars import ContextVar
from pathlib import Path

from .config import get_settings

# Context variables for request tracking
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
operation_var: ContextVar[str | None] = ContextVar("operation", default=None)
device_id_var: ContextVar[str | None] = ContextVar("device_id", default=None)


class CorrelationIDFilter(logging.Filter):
    """Add correlation ID and context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Add correlation ID
        record.correlation_id = correlation_id_var.get() or "unknown"

        # Add user context
        record.user_id = user_id_var.get() or "system"

        # Add operation context
        record.operation = operation_var.get() or "unknown"

        # Add device context
        record.device_id = device_id_var.get() or "none"

        # Add timestamp in EST format [YY-MM-DD][HH:MM:SS AM/PM]
        est_time = datetime.now(ZoneInfo("America/New_York"))
        record.timestamp_formatted = (
            f"[{est_time.strftime('%y-%m-%d')}][{est_time.strftime('%I:%M:%S %p')}]"
        )
        # Keep ISO timestamp for JSON logs
        record.timestamp_iso = datetime.now(timezone.utc).isoformat()

        return True


class StructuredJSONFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import socket

        self.hostname = socket.gethostname()

    def format(self, record: logging.LogRecord) -> str:
        # Create base log entry
        log_entry = {
            "timestamp": record.timestamp_iso,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "unknown"),
            "user_id": getattr(record, "user_id", "system"),
            "operation": getattr(record, "operation", "unknown"),
            "device_id": getattr(record, "device_id", "none"),
            "hostname": self.hostname,
            "process_id": record.process,
            "thread_id": record.thread,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from the record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
                "correlation_id",
                "user_id",
                "operation",
                "device_id",
                "timestamp_iso",
            }:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Format log records with colors for console output."""

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{level_color}{record.levelname}{self.RESET}"

        # Format correlation ID
        correlation_id = getattr(record, "correlation_id", "unknown")[:8]

        # Format operation
        operation = getattr(record, "operation", "unknown")

        # Format device ID
        device_id = getattr(record, "device_id", "none")
        if device_id != "none":
            device_id = device_id[:8]

        # Create formatted message
        formatted = (
            f"{record.timestamp_formatted} | "
            f"{record.levelname} | "
            f"{correlation_id} | "
            f"{operation} | "
            f"{device_id} | "
            f"{record.name} | "
            f"{record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class ErrorClassificationFilter(logging.Filter):
    """Classify errors based on type and content."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.ERROR:
            # Classify the error
            error_class = self._classify_error(record)
            record.error_class = error_class

            # Add severity based on classification
            record.error_severity = self._get_error_severity(error_class)

            # Extract error context
            record.error_context = self._extract_error_context(record)

        return True

    def _classify_error(self, record: logging.LogRecord) -> str:
        """Classify error based on exception type and message."""
        message = record.getMessage().lower()

        # Check exception type first
        if record.exc_info and record.exc_info[0]:
            exc_type = record.exc_info[0].__name__.lower()

            if "connection" in exc_type or "timeout" in exc_type:
                return "network_error"
            elif "permission" in exc_type or "access" in exc_type:
                return "permission_error"
            elif "validation" in exc_type:
                return "validation_error"
            elif "configuration" in exc_type:
                return "configuration_error"
            elif "ssh" in exc_type:
                return "ssh_error"
            elif "database" in exc_type or "sql" in exc_type:
                return "database_error"

        # Check message content
        if any(keyword in message for keyword in ["connection", "timeout", "network"]):
            return "network_error"
        elif any(keyword in message for keyword in ["permission", "access", "forbidden"]):
            return "permission_error"
        elif any(keyword in message for keyword in ["validation", "invalid", "malformed"]):
            return "validation_error"
        elif any(keyword in message for keyword in ["config", "setting", "parameter"]):
            return "configuration_error"
        elif any(keyword in message for keyword in ["ssh", "authentication", "key"]):
            return "ssh_error"
        elif any(keyword in message for keyword in ["database", "sql", "query"]):
            return "database_error"
        elif any(keyword in message for keyword in ["docker", "container"]):
            return "container_error"
        elif any(keyword in message for keyword in ["file", "directory", "path"]):
            return "filesystem_error"
        elif any(keyword in message for keyword in ["memory", "cpu", "resource"]):
            return "resource_error"
        else:
            return "application_error"

    def _get_error_severity(self, error_class: str) -> str:
        """Get severity level based on error classification."""
        severity_map = {
            "network_error": "high",
            "database_error": "critical",
            "ssh_error": "high",
            "permission_error": "medium",
            "validation_error": "low",
            "configuration_error": "medium",
            "container_error": "medium",
            "filesystem_error": "medium",
            "resource_error": "high",
            "application_error": "medium",
        }
        return severity_map.get(error_class, "medium")

    def _extract_error_context(self, record: logging.LogRecord) -> dict[str, Any]:
        """Extract contextual information from error."""
        context = {}

        # Add basic context
        context["module"] = record.module
        context["function"] = record.funcName
        context["line"] = record.lineno

        # Add exception details
        if record.exc_info and record.exc_info[1]:
            context["exception_message"] = str(record.exc_info[1])
            context["exception_type"] = record.exc_info[0].__name__

        # Extract device and operation context
        device_id = getattr(record, "device_id", None)
        if device_id and device_id != "none":
            context["device_id"] = device_id

        operation = getattr(record, "operation", None)
        if operation and operation != "unknown":
            context["operation"] = operation

        return context


class PerformanceLoggingFilter(logging.Filter):
    """Add performance metrics to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Add performance tracking for slow operations
        if hasattr(record, "duration"):
            if record.duration > 5.0:  # Slow operation threshold
                record.performance_issue = "slow_operation"
            elif record.duration > 1.0:
                record.performance_issue = "moderate_delay"

        return True


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID in context."""
    if correlation_id is None:
        correlation_id = generate_correlation_id()

    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str | None:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def set_user_context(user_id: str) -> None:
    """Set user ID in context."""
    user_id_var.set(user_id)


def set_operation_context(operation: str) -> None:
    """Set operation in context."""
    operation_var.set(operation)


def set_device_context(device_id: str) -> None:
    """Set device ID in context."""
    device_id_var.set(device_id)


def clear_context() -> None:
    """Clear all context variables."""
    correlation_id_var.set(None)
    user_id_var.set(None)
    operation_var.set(None)
    device_id_var.set(None)


def setup_logging() -> None:
    """Set up structured logging configuration."""
    # Ensure log directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Base logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": StructuredJSONFormatter,
            },
            "console": {
                "()": ColoredConsoleFormatter,
                "format": "%(message)s",
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "filters": {
            "correlation_id": {
                "()": CorrelationIDFilter,
            },
            "error_classification": {
                "()": ErrorClassificationFilter,
            },
            "performance": {
                "()": PerformanceLoggingFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "console",
                "filters": ["correlation_id", "error_classification", "performance"],
                "stream": sys.stdout,
            },
            "file_json": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filters": ["correlation_id", "error_classification", "performance"],
                "filename": "logs/app.json",
                "maxBytes": 50 * 1024 * 1024,  # 50MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filters": ["correlation_id", "error_classification", "performance"],
                "filename": "logs/errors.json",
                "maxBytes": 20 * 1024 * 1024,  # 20MB
                "backupCount": 10,
                "encoding": "utf-8",
            },
            "audit_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filters": ["correlation_id"],
                "filename": "logs/audit.json",
                "maxBytes": 100 * 1024 * 1024,  # 100MB
                "backupCount": 20,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            # Application loggers
            "apps.backend.src": {
                "level": "DEBUG",
                "handlers": ["console", "file_json", "error_file"],
                "propagate": False,
            },
            # Audit logger
            "audit": {
                "level": "INFO",
                "handlers": ["audit_file"],
                "propagate": False,
            },
            # SSH operations logger
            "ssh": {
                "level": "DEBUG",
                "handlers": ["console", "file_json"],
                "propagate": False,
            },
            # Performance logger
            "performance": {
                "level": "INFO",
                "handlers": ["file_json"],
                "propagate": False,
            },
            # Third-party library loggers
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["file_json"],
                "propagate": False,
            },
            "asyncssh": {
                "level": "WARNING",
                "handlers": ["file_json"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file_json"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file_json"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "file_json"],
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console", "file_json"],
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file_json"],
        },
    }

    # Apply configuration
    logging.config.dictConfig(logging_config)

    # Set up correlation ID for startup
    set_correlation_id()
    set_operation_context("startup")

    logger = logging.getLogger(__name__)
    logger.info("Structured logging initialized successfully")


# Convenience functions for structured logging
def get_logger(name: str) -> logging.Logger:
    """Get a logger with structured logging configured."""
    return logging.getLogger(name)


def log_operation_start(operation: str, **kwargs) -> str:
    """Log the start of an operation and return correlation ID."""
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)
    set_operation_context(operation)

    logger = get_logger("audit")
    logger.info(
        f"Operation started: {operation}",
        extra={"event_type": "operation_start", "operation": operation, **kwargs},
    )

    return correlation_id


def log_operation_end(
    operation: str, success: bool = True, duration: float | None = None, **kwargs
) -> None:
    """Log the end of an operation."""
    logger = get_logger("audit")

    extra_data = {
        "event_type": "operation_end",
        "operation": operation,
        "success": success,
        **kwargs,
    }

    if duration is not None:
        extra_data["duration"] = duration

    if success:
        logger.info(f"Operation completed: {operation}", extra=extra_data)
    else:
        logger.error(f"Operation failed: {operation}", extra=extra_data)


def log_ssh_command(device_id: str, command: str, success: bool, duration: float, **kwargs) -> None:
    """Log SSH command execution."""
    set_device_context(device_id)

    logger = get_logger("ssh")

    extra_data = {
        "event_type": "ssh_command",
        "device_id": device_id,
        "command": command,
        "success": success,
        "duration": duration,
        **kwargs,
    }

    if success:
        logger.info("SSH command executed successfully", extra=extra_data)
    else:
        logger.error("SSH command failed", extra=extra_data)


def log_performance_metric(operation: str, duration: float, **kwargs) -> None:
    """Log performance metrics."""
    logger = get_logger("performance")

    logger.info(
        f"Performance metric: {operation}",
        extra={
            "event_type": "performance_metric",
            "operation": operation,
            "duration": duration,
            **kwargs,
        },
    )


def log_security_event(event_type: str, severity: str, description: str, **kwargs) -> None:
    """Log security-related events."""
    logger = get_logger("audit")

    logger.warning(
        f"Security event: {event_type}",
        extra={
            "event_type": "security_event",
            "security_event_type": event_type,
            "severity": severity,
            "description": description,
            **kwargs,
        },
    )


def log_configuration_change(device_id: str, file_path: str, change_type: str, **kwargs) -> None:
    """Log configuration changes."""
    set_device_context(device_id)

    logger = get_logger("audit")

    logger.info(
        f"Configuration changed: {file_path}",
        extra={
            "event_type": "configuration_change",
            "device_id": device_id,
            "file_path": file_path,
            "change_type": change_type,
            **kwargs,
        },
    )


class LoggingContextManager:
    """Context manager for logging operations."""

    def __init__(self, operation: str, device_id: str | None = None, **kwargs):
        self.operation = operation
        self.device_id = device_id
        self.kwargs = kwargs
        self.correlation_id = None
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.correlation_id = log_operation_start(self.operation, **self.kwargs)

        if self.device_id:
            set_device_context(self.device_id)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else None
        success = exc_type is None

        log_operation_end(self.operation, success=success, duration=duration, **self.kwargs)

        return False  # Don't suppress exceptions


# Initialize logging on module import
if not logging.getLogger().handlers:
    setup_logging()
