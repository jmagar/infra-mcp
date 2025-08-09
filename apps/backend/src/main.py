"""
Infrastructure Management MCP Server - Main Application

FastAPI + FastMCP unified application serving both REST API endpoints
and MCP tools from a single codebase with streamable HTTP transport.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import logging
from uuid import uuid4
from pathlib import Path
import time
from typing import Any, AsyncGenerator, cast
from collections.abc import Awaitable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import Boolean, and_, select
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.websockets import WebSocket
import uvicorn

from apps.backend.src.api import api_router
from apps.backend.src.api.monitoring import router as monitoring_router
from apps.backend.src.core.config import get_settings
from apps.backend.src.core.database import (
    check_database_health,
    close_database,
    get_async_session_factory,
    init_database,
)
from apps.backend.src.core.events import initialize_event_bus, shutdown_event_bus
from apps.backend.src.core.exceptions import (
    InfrastructureException,
    ServiceUnavailableError,
)
from apps.backend.src.models.device import Device
from apps.backend.src.utils.database_utils import get_database_helper
from apps.backend.src.schemas.common import HealthCheckResponse
from apps.backend.src.services.configuration_monitoring import get_configuration_monitoring_service
from apps.backend.src.services.polling_service import PollingService
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.utils.ssh_client import cleanup_ssh_client, get_ssh_client
from apps.backend.src.websocket import websocket_router
from apps.backend.src.core.logging import setup_logging, set_request_id, get_request_id

# Configure structured logging
setup_logging(level=logging.INFO)

# Reduce SSH logging spam - set asyncssh to WARNING level only
logging.getLogger("asyncssh").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global settings
settings = get_settings()

# Global service instances
polling_service = None
config_monitoring_service = None

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
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown tasks"""
    global polling_service, config_monitoring_service
    logger.info("Starting Infrastructure Management API Server...")

    # Startup tasks
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")

        # Initialize event bus for real-time communication
        await initialize_event_bus()
        logger.info("Event bus initialized successfully")

        # Initialize and start polling service if enabled
        if settings.polling.polling_enabled:
            polling_service = PollingService()
            app.state.polling_service = polling_service
            await polling_service.start_polling()
            logger.info("Polling service started successfully")
        else:
            app.state.polling_service = None
            logger.info("Polling service disabled via configuration")

        # Initialize configuration monitoring in background (non-blocking)
        logger.info("Starting configuration monitoring setup in background...")
        app.state.config_monitoring_service = None  # Initialize to None

        # Start background task for configuration monitoring setup
        async def setup_configuration_monitoring() -> None:
            """Background task to set up SWAG/Docker monitoring without blocking startup"""
            try:
                logger.info("Background: Starting configuration monitoring setup...")
                db_session_factory = get_async_session_factory()
                ssh_client = get_ssh_client()
                unified_data_service = await get_unified_data_collection_service(
                    db_session_factory=db_session_factory,
                    ssh_client=ssh_client
                )

                # Set up SWAG monitoring
                logger.info("Background: Setting up SWAG monitoring...")
                swag_monitoring_service = await _setup_swag_monitoring(
                    db_session_factory, ssh_client, unified_data_service
                )

                # Set up Docker monitoring
                logger.info("Background: Setting up Docker monitoring...")
                docker_monitoring_service = await _setup_docker_monitoring(
                    db_session_factory, ssh_client, unified_data_service
                )

                # Use whichever service was successfully created (or merge them later)
                config_monitoring_service = swag_monitoring_service or docker_monitoring_service
                app.state.config_monitoring_service = config_monitoring_service

                if swag_monitoring_service:
                    logger.info("Background: SWAG configuration monitoring set up successfully")
                if docker_monitoring_service:
                    logger.info("Background: Docker configuration monitoring set up successfully")
                if not config_monitoring_service:
                    logger.info("Background: No SWAG or Docker devices found - configuration monitoring not needed")

                logger.info("Background: Configuration monitoring setup completed")

            except Exception as e:
                logger.error(f"Background: Failed to set up configuration monitoring: {e}")
                app.state.config_monitoring_service = None

        # Start the background task without waiting for it
        asyncio.create_task(setup_configuration_monitoring())

        # Log configuration
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(
            f"Database: {settings.database.postgres_host}:{settings.database.postgres_port}"
        )
        logger.info(f"API Server: {settings.api.api_host}:{settings.api.api_port}")

        logger.info("✅ API Server startup completed - Ready to accept HTTP requests")

        yield

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    finally:
        # Shutdown tasks
        logger.info("Shutting down Infrastructure Management API Server...")

        # Stop polling service
        polling_service = getattr(app.state, 'polling_service', None)
        if polling_service is not None:
            await polling_service.stop_polling()
            app.state.polling_service = None
            logger.info("Polling service stopped")
        else:
            logger.info("Polling service was not running")

        # Stop configuration monitoring service
        config_monitoring_service = getattr(app.state, 'config_monitoring_service', None)
        if config_monitoring_service is not None:
            await config_monitoring_service.stop_all_monitoring()
            app.state.config_monitoring_service = None
            logger.info("Configuration monitoring service stopped")
        else:
            logger.info("Configuration monitoring service was not running")

        # Shutdown event bus
        await shutdown_event_bus()
        logger.info("Event bus shutdown complete")

        # Cleanup SSH connections
        await cleanup_ssh_client()
        logger.info("SSH connections cleaned up")

        # Close database connections
        await close_database()
        logger.info("Database connections closed")

        logger.info("Shutdown complete")


async def _setup_monitoring_service(
    service_type: str,
    db_session_factory: Any, 
    ssh_client: Any, 
    unified_data_service: Any
) -> Any:
    """
    Generic monitoring setup for different service types (SWAG, Docker, etc).
    
    Args:
        service_type: Type of service to monitor ('swag', 'docker')
        db_session_factory: Database session factory
        ssh_client: SSH client instance
        unified_data_service: Unified data collection service
    
    Returns:
        ConfigurationMonitoringService if devices found, None otherwise
    """
    monitoring_configs = {
        'swag': {
            'query_conditions': [
                Device.monitoring_enabled == True,
                Device.tags.op("?")("swag_running"),
                Device.tags["swag_running"].astext.cast(Boolean) == True
            ],
            'default_paths_key': 'swag_config_path',
            'default_paths': ["/mnt/appdata/swag/nginx/proxy-confs"],
            'device_key': 'proxy_conf_dir',
            'custom_path_logic': lambda device: device.tags.get("swag_config_path") or "/mnt/appdata/swag/nginx/proxy-confs"
        },
        'docker': {
            'query_conditions': [
                Device.monitoring_enabled == True,
                Device.tags.op("?")("docker")
            ],
            'default_paths': ["/opt", "/srv", "/home/docker", "/docker"],
            'device_key': 'compose_dirs',
            'custom_path_logic': lambda device: _get_docker_compose_paths(device)
        }
    }
    
    if service_type not in monitoring_configs:
        raise ValueError(f"Unknown service type: {service_type}")
    
    config = monitoring_configs[service_type]
    
    try:
        db_helper = get_database_helper(db_session_factory)
        
        # Build query operation based on service type
        async def query_devices(session) -> list[Device]:
            from sqlalchemy import and_
            result = await session.execute(
                select(Device).where(and_(*config['query_conditions']))
            )
            return result.scalars().all()
        
        devices = await db_helper.execute_query(query_devices)
        
        devices_found = []
        for device in devices:
            if service_type == 'swag':
                paths = config['custom_path_logic'](device)
                devices_found.append({
                    'device': device,
                    config['device_key']: paths
                })
            elif service_type == 'docker':
                paths = config['custom_path_logic'](device)
                devices_found.append({
                    'device': device,
                    config['device_key']: paths
                })
            
            logger.info(f"Found {service_type.upper()} device: {device.hostname}")
        
        if devices_found:
            config_monitoring_service = get_configuration_monitoring_service(
                db_session_factory=db_session_factory,
                ssh_client=ssh_client,
                unified_data_service=unified_data_service
            )
            
            successful_setups = 0
            for device_config in devices_found:
                device = device_config['device']
                paths = device_config[config['device_key']]
                
                # Ensure paths is a list
                if not isinstance(paths, list):
                    paths = [paths]
                
                success = await config_monitoring_service.setup_device_monitoring(
                    device_id=device.id,
                    custom_watch_paths=paths
                )
                
                if success:
                    successful_setups += 1
                    logger.info(f"Started file watching for {service_type.upper()} device {device.hostname} at {paths}")
                else:
                    logger.warning(f"Failed to start file watching for {service_type.upper()} device {device.hostname}")
            
            if successful_setups > 0:
                logger.info(f"Successfully set up {service_type.upper()} monitoring for {successful_setups}/{len(devices_found)} device(s)")
                return config_monitoring_service
            else:
                logger.error(f"Failed to set up monitoring for any {service_type.upper()} devices")
                return None
        else:
            logger.info(f"No {service_type.upper()} devices found - {service_type} monitoring not needed")
            return None
                
    except Exception as e:
        logger.error(f"Failed to set up {service_type.upper()} monitoring: {e}")
        return None


def _get_docker_compose_paths(device: Device) -> list[str]:
    """Extract and validate Docker compose paths for a device."""
    compose_dirs = ["/opt", "/srv", "/home/docker", "/docker"]
    
    # Also check if device has custom compose paths stored (but validate them)
    stored_paths = device.tags.get("all_docker_compose_paths", [])
    if stored_paths:
        # Filter out obviously wrong paths like Go modules
        valid_paths = []
        for path in stored_paths:
            # Skip paths in Go modules, node_modules, etc.
            if not any(exclude in path for exclude in [
                "/go/pkg/mod/",
                "/node_modules/",
                "/.git/",
                "/.cache/",
                "/vendor/"
            ]):
                valid_paths.append(str(Path(path).parent))
        
        if valid_paths:
            compose_dirs.extend(valid_paths)
    
    # Remove duplicates
    return list(set(compose_dirs))


async def _setup_swag_monitoring(db_session_factory: Any, ssh_client: Any, unified_data_service: Any) -> Any:
    """
    Detect SWAG devices and set up monitoring only if found.
    
    Returns:
        ConfigurationMonitoringService if SWAG devices found, None otherwise
    """
    return await _setup_monitoring_service('swag', db_session_factory, ssh_client, unified_data_service)


async def _setup_docker_monitoring(db_session_factory: Any, ssh_client: Any, unified_data_service: Any) -> Any:
    """
    Detect Docker devices and set up monitoring for docker-compose files.
    
    Returns:
        ConfigurationMonitoringService if Docker devices found, None otherwise
    """
    return await _setup_monitoring_service('docker', db_session_factory, ssh_client, unified_data_service)


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

# Wrapper for rate limit exception handler to fix type compatibility
def rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Wrapper for slowapi rate limit handler with proper typing"""
    if isinstance(exc, RateLimitExceeded):
        return _rate_limit_exceeded_handler(request, exc)
    return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Correlation ID middleware (request-scoped request_id)
@app.middleware("http")
async def correlation_middleware(request: Request, call_next: Any) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    set_request_id(request_id)
    try:
        response = cast(Response, await call_next(request))
    finally:
        # Ensure context var cleared for next request in same worker
        set_request_id(None)
    # Echo back the request ID
    response.headers["X-Request-ID"] = request_id
    return response


# Custom middleware for request timing and logging
@app.middleware("http")
async def timing_middleware(request: Request, call_next: Any) -> Response:
    """Add request timing and basic logging"""
    start_time = time.time()

    # Log request
    logger.info(
        "request.start",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "client": request.client.host if request.client else None,
        },
    )

    try:
        response = cast(Response, await call_next(request))

        # Calculate processing time
        process_time = time.time() - start_time

        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)

        # Log response
        logger.info(
            "request.end",
            extra={
                "method": request.method,
                "path": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": int(process_time * 1000),
            },
        )

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "request.error",
            exc_info=True,
            extra={
                "method": request.method,
                "path": str(request.url.path),
                "duration_ms": int(process_time * 1000),
                "exception_type": type(e).__name__,
            },
        )
        raise


@app.middleware("http")
async def security_middleware(request: Request, call_next: Any) -> Response:
    """Security and validation middleware"""

    # Security headers
    response = cast(Response, await call_next(request))

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
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, Any] | None:
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
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
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
                "timestamp": datetime.now(UTC).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
            }
        },
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
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
                "timestamp": datetime.now(UTC).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {"error_count": exc.error_count(), "errors": errors},
            }
        },
    )


@app.exception_handler(InfrastructureException)
async def infrastructure_exception_handler(request: Request, exc: InfrastructureException) -> JSONResponse:
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
                "timestamp": datetime.now(UTC).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": exc.details,
                "device_id": getattr(exc, "device_id", None),
                "operation": exc.operation,
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
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
                "timestamp": datetime.now(UTC).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {
                    "database_error": str(exc) if settings.debug else "Database error occurred"
                },
            }
        },
    )


@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError) -> JSONResponse:
    """Handle asyncio timeout errors"""
    logger.error(f"Timeout error on {request.method} {request.url.path}: Operation timed out")

    return JSONResponse(
        status_code=504,
        content={
            "error": {
                "code": "OPERATION_TIMEOUT",
                "message": "Operation timed out",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {"timeout_type": "asyncio_timeout"},
            }
        },
    )


@app.exception_handler(ConnectionError)
async def connection_exception_handler(request: Request, exc: ConnectionError) -> JSONResponse:
    """Handle connection errors (network, SSH, etc.)"""
    logger.error(f"Connection error on {request.method} {request.url.path}: {str(exc)}")

    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "CONNECTION_ERROR",
                "message": "Connection failed",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {
                    "connection_error": str(exc) if settings.debug else "Connection error occurred"
                },
            }
        },
    )


@app.exception_handler(PermissionError)
async def permission_exception_handler(request: Request, exc: PermissionError) -> JSONResponse:
    """Handle permission errors"""
    logger.warning(f"Permission error on {request.method} {request.url.path}: {str(exc)}")

    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "Permission denied",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {
                    "permission_error": str(exc) if settings.debug else "Permission denied"
                },
            }
        },
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_exception_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Handle file not found errors"""
    logger.warning(f"File not found error on {request.method} {request.url.path}: {str(exc)}")

    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "FILE_NOT_FOUND",
                "message": "Requested file not found",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": str(request.url.path),
                "method": request.method,
                "details": {"file_error": str(exc) if settings.debug else "File not found"},
            }
        },
    )


@app.exception_handler(OSError)
async def os_exception_handler(request: Request, exc: OSError) -> JSONResponse:
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
                "timestamp": datetime.now(UTC).isoformat(),
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
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
                "timestamp": datetime.now(UTC).isoformat(),
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
async def health_check(request: Request) -> HealthCheckResponse:
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
            timestamp=datetime.now(UTC),
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
async def root(request: Request) -> dict[str, Any]:
    """Root endpoint with API information"""
    return {
        "name": "Infrastructure Management API",
        "version": "1.0.0",
        "description": "Centralized monitoring and management system for self-hosted infrastructure",
        "endpoints": {"rest_api": "/api", "health": "/health", "documentation": "/docs"},
        "external_services": {"mcp_server": "Independent MCP server via mcp_server.py"},
        "timestamp": datetime.now(UTC).isoformat(),
    }


# Include API routers with /api prefix
app.include_router(api_router, prefix="/api")
app.include_router(monitoring_router)  # Enhanced monitoring endpoints
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
        host=settings.api.api_host,
        port=settings.api.api_port,
        reload=settings.debug,
        log_level=settings.api.api_log_level.lower(),
        access_log=True,
    )
