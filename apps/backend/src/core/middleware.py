"""
FastAPI Middleware for Structured Logging

Integrates structured logging with HTTP requests, setting correlation IDs
and logging request/response information.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging_config import (
    set_correlation_id,
    set_user_context,
    set_operation_context,
    clear_context,
    get_correlation_id,
    log_operation_start,
    log_operation_end,
    log_security_event,
    get_logger,
)
from .exceptions import InfrastructureException

logger = get_logger(__name__)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add structured logging to HTTP requests."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()

        # Extract or generate correlation ID
        correlation_id = (
            request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or None
        )

        # Set correlation ID in context
        actual_correlation_id = set_correlation_id(correlation_id)

        # Extract user information from headers or auth
        user_id = self._extract_user_id(request)
        if user_id:
            set_user_context(user_id)

        # Set operation context based on request
        operation = f"{request.method} {request.url.path}"
        set_operation_context(operation)

        # Log request start
        logger.info(
            "HTTP request started",
            extra={
                "event_type": "http_request_start",
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_agent": request.headers.get("user-agent"),
                "client_ip": self._get_client_ip(request),
                "content_length": request.headers.get("content-length"),
            },
        )

        response = None
        error = None

        try:
            # Process request
            response = await call_next(request)

        except Exception as e:
            error = e
            logger.error(
                f"HTTP request failed with exception: {str(e)}",
                extra={
                    "event_type": "http_request_error",
                    "method": request.method,
                    "path": request.url.path,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                },
                exc_info=True,
            )

            # Create error response
            if isinstance(e, InfrastructureException):
                # Map error codes to HTTP status codes (similar to main.py)
                status_code_map = {
                    "DEVICE_NOT_FOUND": 404,
                    "AUTHENTICATION_ERROR": 401,
                    "AUTHORIZATION_ERROR": 403,
                    "RATE_LIMIT_ERROR": 429,
                    "VALIDATION_ERROR": 422,
                    "SERVICE_UNAVAILABLE": 503,
                    "DEVICE_OFFLINE": 503,
                    "SSH_CONNECTION_ERROR": 503,
                    "SSH_TIMEOUT_ERROR": 504,
                    "SSH_COMMAND_ERROR": 500,
                    "DATABASE_CONNECTION_ERROR": 503,
                    "DATABASE_OPERATION_ERROR": 500,
                    "CONFIGURATION_ERROR": 500,
                    "CONTAINER_ERROR": 500,
                    "ZFS_ERROR": 500,
                    "NETWORK_ERROR": 500,
                    "BACKUP_ERROR": 500,
                    "OPERATION_TIMEOUT": 504,
                    "PERMISSION_ERROR": 403,
                    "RESOURCE_NOT_FOUND": 404,
                    "RESOURCE_CONFLICT": 409,
                    "BUSINESS_LOGIC_ERROR": 422,
                    "EXTERNAL_SERVICE_ERROR": 502,
                }
                status_code = status_code_map.get(e.error_code, 500)

                response = JSONResponse(
                    status_code=status_code,
                    content={
                        "error": e.error_code,
                        "message": e.message,
                        "correlation_id": actual_correlation_id,
                        "timestamp": time.time(),
                    },
                )
            else:
                response = JSONResponse(
                    status_code=500,
                    content={
                        "error": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "correlation_id": actual_correlation_id,
                        "timestamp": time.time(),
                    },
                )

        # Calculate duration
        duration = time.time() - start_time

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = actual_correlation_id

        # Log request completion
        status_code = response.status_code

        log_level = self._get_log_level_for_status(status_code)

        logger.log(
            log_level,
            "HTTP request completed",
            extra={
                "event_type": "http_request_end",
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration": duration,
                "response_size": response.headers.get("content-length"),
                "success": error is None,
            },
        )

        # Log security events for suspicious activity
        self._check_security_events(request, response, duration)

        # Clean up context
        clear_context()

        return response

    def _extract_user_id(self, request: Request) -> str | None:
        """Extract user ID from request headers or authentication."""
        # Check for user ID in various places
        user_id = request.headers.get("X-User-ID") or request.headers.get("X-Authenticated-User")

        # Could also extract from JWT token if present
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Extract user from JWT token (simplified)
            # In production, you'd decode and validate the JWT
            pass

        return user_id

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to client address
        if hasattr(request.client, "host"):
            return request.client.host

        return "unknown"

    def _get_log_level_for_status(self, status_code: int) -> int:
        """Get appropriate log level based on HTTP status code."""
        if status_code < 400:
            return logging.INFO
        elif status_code < 500:
            return logging.WARNING
        else:
            return logging.ERROR

    def _check_security_events(self, request: Request, response: Response, duration: float) -> None:
        """Check for potential security events in the request/response."""

        # Check for brute force attempts (multiple failed auth attempts)
        if response.status_code == 401:
            log_security_event(
                event_type="authentication_failure",
                severity="medium",
                description=f"Authentication failed for {request.url.path}",
                client_ip=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                path=request.url.path,
            )

        # Check for potential DoS attacks (many requests from same IP)
        # This would require rate limiting state - simplified here

        # Check for suspicious user agents
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "masscan", "zap"]
        if any(agent in user_agent for agent in suspicious_agents):
            log_security_event(
                event_type="suspicious_user_agent",
                severity="high",
                description=f"Suspicious user agent detected: {user_agent}",
                client_ip=self._get_client_ip(request),
                path=request.url.path,
            )

        # Check for path traversal attempts
        path = request.url.path
        if "../" in path or "..%2F" in path or "..%5C" in path:
            log_security_event(
                event_type="path_traversal_attempt",
                severity="high",
                description=f"Path traversal attempt detected: {path}",
                client_ip=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )

        # Check for SQL injection patterns in query parameters
        query_string = str(request.query_params).lower()
        sql_patterns = ["union select", "drop table", "delete from", "insert into", "' or '1'='1"]
        if any(pattern in query_string for pattern in sql_patterns):
            log_security_event(
                event_type="sql_injection_attempt",
                severity="high",
                description="SQL injection attempt detected in query parameters",
                client_ip=self._get_client_ip(request),
                query_params=str(request.query_params),
                path=request.url.path,
            )

        # Check for extremely slow requests (potential DoS)
        if duration > 30.0:  # 30 seconds threshold
            log_security_event(
                event_type="slow_request",
                severity="medium",
                description=f"Extremely slow request detected: {duration:.2f}s",
                client_ip=self._get_client_ip(request),
                path=request.url.path,
                duration=duration,
            )


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log performance metrics for HTTP requests."""

    def __init__(self, app: ASGIApp, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Log performance metrics
        if duration > self.slow_request_threshold:
            logger.warning(
                "Slow HTTP request detected",
                extra={
                    "event_type": "slow_request",
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                    "threshold": self.slow_request_threshold,
                },
            )

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle and log unhandled exceptions."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            # Log unhandled exception
            correlation_id = get_correlation_id() or "unknown"

            logger.error(
                "Unhandled exception in request processing",
                extra={
                    "event_type": "unhandled_exception",
                    "method": request.method,
                    "path": request.url.path,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "correlation_id": correlation_id,
                },
                exc_info=True,
            )

            # Return generic error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "correlation_id": correlation_id,
                    "timestamp": time.time(),
                },
            )


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request size and log large requests."""

    def __init__(self, app: ASGIApp, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                size = int(content_length)

                # Log large requests
                if size > 1024 * 1024:  # 1MB threshold for logging
                    logger.info(
                        "Large request received",
                        extra={
                            "event_type": "large_request",
                            "method": request.method,
                            "path": request.url.path,
                            "content_length": size,
                        },
                    )

                # Reject requests that are too large
                if size > self.max_request_size:
                    logger.warning(
                        "Request too large, rejecting",
                        extra={
                            "event_type": "request_too_large",
                            "method": request.method,
                            "path": request.url.path,
                            "content_length": size,
                            "max_allowed": self.max_request_size,
                        },
                    )

                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "REQUEST_TOO_LARGE",
                            "message": f"Request size {size} exceeds maximum allowed {self.max_request_size}",
                            "correlation_id": get_correlation_id() or "unknown",
                        },
                    )
            except ValueError:
                # Invalid content-length header
                logger.warning(
                    "Invalid content-length header",
                    extra={
                        "event_type": "invalid_content_length",
                        "method": request.method,
                        "path": request.url.path,
                        "content_length_header": content_length,
                    },
                )

        return await call_next(request)


# Health check endpoint logging
class HealthCheckLoggingFilter(logging.Filter):
    """Filter to reduce noise from health check endpoints."""

    def __init__(self, health_check_paths: list[str] | None = None):
        super().__init__()
        self.health_check_paths = health_check_paths or ["/health", "/health/", "/ping", "/status"]

    def filter(self, record: logging.LogRecord) -> bool:
        # Check if this is a health check request
        if hasattr(record, "path"):
            if record.path in self.health_check_paths:
                # Only log health check requests at DEBUG level
                return record.levelno >= logging.DEBUG

        return True


def setup_middleware_logging() -> None:
    """Set up middleware-specific logging configuration."""
    # Add health check filter to reduce noise
    health_filter = HealthCheckLoggingFilter()

    # Get the main logger and add the filter
    main_logger = logging.getLogger("apps.backend.src")
    for handler in main_logger.handlers:
        handler.addFilter(health_filter)

    logger.info("Middleware logging filters configured")
