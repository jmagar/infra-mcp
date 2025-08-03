"""
Infrastructure Management MCP Server - Main Application

FastAPI + FastMCP unified application serving both REST API endpoints
and MCP tools from a single codebase with streamable HTTP transport.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from apps.backend.src.core.config import get_settings
from apps.backend.src.core.database import (
    init_database,
    close_database,
    check_database_health,
)
from apps.backend.src.utils.ssh_client import cleanup_ssh_client
from apps.backend.src.schemas.common import HealthCheckResponse
from apps.backend.src.services.polling_service import PollingService
from apps.backend.src.core.exceptions import (
    InfrastructureException,
    DatabaseConnectionError,
    DatabaseOperationError,
    SSHConnectionError,
    SSHCommandError,
    SSHTimeoutError,
    DeviceNotFoundError,
    DeviceOfflineError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ValidationError as CustomValidationError,
    ServiceUnavailableError,
    ContainerError,
    ZFSError,
    NetworkError,
    BackupError,
    ConfigurationError,
    TimeoutError as CustomTimeoutError,
    PermissionError as CustomPermissionError,
    ResourceNotFoundError,
    ResourceConflictError,
    BusinessLogicError,
    ExternalServiceError,
)
from apps.backend.src.api import api_router
from apps.backend.src.websocket import websocket_router

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Reduce SSH logging spam - set asyncssh to WARNING level only
logging.getLogger("asyncssh").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global settings
settings = get_settings()

# Global polling service instance
polling_service = None

# Rate limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.api.rate_limit_requests_per_minute}/minute"]
    if settings.api.rate_limit_enabled
    else [],
)

# Security
security = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks"""
    global polling_service
    logger.info("Starting Infrastructure Management API Server...")

    # Startup tasks
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")

        # Initialize and start polling service if enabled
        if settings.polling.polling_enabled:
            polling_service = PollingService()
            app.state.polling_service = polling_service
            await polling_service.start_polling()
            logger.info("Polling service started successfully")
        else:
            polling_service = None
            app.state.polling_service = None
            logger.info("Polling service disabled via configuration")

        # Log configuration
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(
            f"Database: {settings.database.postgres_host}:{settings.database.postgres_port}"
        )
        logger.info(f"API Server: {settings.mcp_server.mcp_host}:{settings.mcp_server.mcp_port}")

        yield

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        # Shutdown tasks
        logger.info("Shutting down Infrastructure Management API Server...")

        # Stop polling service
        if polling_service is not None:
            await polling_service.stop_polling()
            logger.info("Polling service stopped")
        else:
            logger.info("Polling service was not running")

        # Cleanup SSH connections
        await cleanup_ssh_client()
        logger.info("SSH connections cleaned up")

        # Close database connections
        await close_database()
        logger.info("Database connections closed")

        logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Infrastructure Management API",
    description="Centralized monitoring and management system for self-hosted infrastructure",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.debug,
)

# Add rate limiter state to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.mcp_server.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Custom middleware for request timing and logging
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Add request timing and basic logging"""
    start_time = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path} - Start")

    try:
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)

        # Log response
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"{request.method} {request.url.path} - Error: {str(e)} - Time: {process_time:.3f}s"
        )
        raise


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Security and validation middleware"""

    # Security headers
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Add API version header
    response.headers["X-API-Version"] = "1.0.0"

    # Add rate limiting headers if enabled
    if settings.api.rate_limit_enabled:
        response.headers["X-RateLimit-Limit"] = str(settings.api.rate_limit_requests_per_minute)
        # Note: actual remaining count would require accessing limiter state
        # For now, just use the configured limit
        response.headers["X-RateLimit-Remaining"] = str(
            settings.api.rate_limit_requests_per_minute - 1
        )
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

    return response


# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Authentication dependency for protected endpoints"""
    if not credentials:
        if settings.auth.api_key:  # API key required
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None  # No auth required

    # For now, accept any valid-looking token/API key
    # In production, implement proper JWT validation or API key verification
    token = credentials.credentials
    if len(token) < 10:  # Basic validation
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"token": token}


# Global exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent error format"""
    logger.warning(
        f"HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
            }
        },
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {exc.error_count()} errors"
    )

    # Format validation errors for better readability
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {"error_count": exc.error_count(), "errors": errors},
            }
        },
    )


@app.exception_handler(InfrastructureException)
async def infrastructure_exception_handler(request: Request, exc: InfrastructureException):
    """Handle custom infrastructure exceptions"""
    logger.error(
        f"Infrastructure error on {request.method} {request.url.path}: "
        f"{exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "device_id": getattr(exc, "device_id", None),
            "operation": exc.operation,
            "details": exc.details,
        },
    )

    # Map error codes to HTTP status codes
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

    status_code = status_code_map.get(exc.error_code, 500)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": exc.details,
                "device_id": getattr(exc, "device_id", None),
                "operation": exc.operation,
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy database errors"""
    logger.error(
        f"Database error on {request.method} {request.url.path}: {str(exc)}", exc_info=True
    )

    # Check if it's a connection error
    error_msg = str(exc).lower()
    if any(keyword in error_msg for keyword in ["connection", "timeout", "connect"]):
        status_code = 503
        error_code = "DATABASE_CONNECTION_ERROR"
        message = "Database connection failed"
    else:
        status_code = 500
        error_code = "DATABASE_OPERATION_ERROR"
        message = "Database operation failed"

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {
                    "database_error": str(exc) if settings.debug else "Database error occurred"
                },
            }
        },
    )


@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError):
    """Handle asyncio timeout errors"""
    logger.error(f"Timeout error on {request.method} {request.url.path}: Operation timed out")

    return JSONResponse(
        status_code=504,
        content={
            "error": {
                "code": "OPERATION_TIMEOUT",
                "message": "Operation timed out",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {"timeout_type": "asyncio_timeout"},
            }
        },
    )


@app.exception_handler(ConnectionError)
async def connection_exception_handler(request: Request, exc: ConnectionError):
    """Handle connection errors (network, SSH, etc.)"""
    logger.error(f"Connection error on {request.method} {request.url.path}: {str(exc)}")

    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "CONNECTION_ERROR",
                "message": "Connection failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {
                    "connection_error": str(exc) if settings.debug else "Connection error occurred"
                },
            }
        },
    )


@app.exception_handler(PermissionError)
async def permission_exception_handler(request: Request, exc: PermissionError):
    """Handle permission errors"""
    logger.warning(f"Permission error on {request.method} {request.url.path}: {str(exc)}")

    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "Permission denied",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {
                    "permission_error": str(exc) if settings.debug else "Permission denied"
                },
            }
        },
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_exception_handler(request: Request, exc: FileNotFoundError):
    """Handle file not found errors"""
    logger.warning(f"File not found error on {request.method} {request.url.path}: {str(exc)}")

    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "FILE_NOT_FOUND",
                "message": "Requested file not found",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {"file_error": str(exc) if settings.debug else "File not found"},
            }
        },
    )


@app.exception_handler(OSError)
async def os_exception_handler(request: Request, exc: OSError):
    """Handle OS-level errors"""
    logger.error(f"OS error on {request.method} {request.url.path}: {str(exc)}")

    # Map common OS errors to appropriate HTTP status codes
    status_code = 500
    if exc.errno == 13:  # Permission denied
        status_code = 403
    elif exc.errno == 2:  # No such file or directory
        status_code = 404
    elif exc.errno == 28:  # No space left on device
        status_code = 507
    elif exc.errno in [110, 111]:  # Connection timed out / Connection refused
        status_code = 503

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": "SYSTEM_ERROR",
                "message": "System operation failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {
                    "os_error": str(exc) if settings.debug else "System error occurred",
                    "errno": exc.errno if hasattr(exc, "errno") and settings.debug else None,
                },
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
        extra={
            "exception_type": type(exc).__name__,
            "request_path": str(request.url.path),
            "request_method": request.method,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc) if settings.debug else "Internal server error",
                },
            }
        },
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
@limiter.limit("10/minute")  # More generous limit for health checks
async def health_check(request: Request):
    """Application health check endpoint with comprehensive system status"""
    try:
        # Test database connection and get detailed health info
        database_health = await check_database_health()

        # Construct health check response
        response = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            environment=settings.environment,
            database=database_health,
            services={
                "database": "healthy"
                if database_health.get("status") == "healthy"
                else "unhealthy",
                "ssh_client": "healthy",
                "api_server": "healthy",
            },
            timestamp=datetime.now(timezone.utc),
        )

        return response

    except Exception as e:
        logger.error(f"Health check failed: {e}")

        # Return unhealthy status using consistent error format
        raise ServiceUnavailableError(
            service_name="infrastructure_management",
            message="Health check failed",
            details={"health_check_error": str(e)},
        )


# Root endpoint
@app.get("/")
@limiter.limit("30/minute")  # Standard limit for root endpoint
async def root(request: Request):
    """Root endpoint with API information"""
    return {
        "name": "Infrastructure Management API",
        "version": "1.0.0",
        "description": "Centralized monitoring and management system for self-hosted infrastructure",
        "endpoints": {"rest_api": "/api", "health": "/health", "documentation": "/docs"},
        "external_services": {"mcp_server": "Independent MCP server via mcp_server.py"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Include API routers with /api prefix
app.include_router(api_router, prefix="/api")
app.include_router(websocket_router)


# The application now serves only the REST API
# MCP server runs independently via mcp_server.py


# Development server startup
if __name__ == "__main__":
    # Configure logging for development
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run development server
    uvicorn.run(
        "apps.backend.src.main:app",
        host=settings.mcp_server.mcp_host,
        port=settings.mcp_server.mcp_port,
        reload=settings.debug,
        log_level=settings.mcp_server.mcp_log_level.lower(),
        access_log=True,
    )
