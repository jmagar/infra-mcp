"""
Common API Endpoints

General-purpose API endpoints including status, system information,
and utility endpoints for the infrastructure management system.
"""

from datetime import UTC, datetime
import logging
import platform
import random
import sys
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

# Import authentication dependency directly to avoid circular imports
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address

from apps.backend.src.core.config import get_settings
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    SSHConnectionError,
)
from apps.backend.src.core.exceptions import (
    ValidationError as CustomValidationError,
)
from apps.backend.src.schemas.common import OperationResult, StatusResponse, SystemInfo

# Security
security = HTTPBearer(auto_error=False)

# Rate limiter for API endpoints
settings = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.api.rate_limit_requests_per_minute}/minute"]
    if settings.api.rate_limit_enabled
    else [],
)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, Any]:
    """Authentication dependency for protected endpoints"""
    settings = get_settings()

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


# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/status", response_model=StatusResponse)
@limiter.limit("60/minute")
async def api_status(request: Request) -> dict[str, Any]:
    """
    API status endpoint with structured response.

    Returns the current operational status of the API service
    including timestamp and status message.
    """
    return StatusResponse(
        status="operational",
        message="All systems operational",
        timestamp=datetime.now(UTC),
    )


@router.get("/system-info", response_model=SystemInfo)
@limiter.limit("30/minute")
async def get_system_info(request: Request) -> dict[str, Any]:
    """
    Get system information.

    Returns detailed information about the server hosting the API
    including platform details, versions, and runtime information.
    """
    return SystemInfo(
        hostname=platform.node(),
        platform=platform.system(),
        architecture=platform.machine(),
        python_version=sys.version.split()[0],
        app_version="1.0.0",
        startup_time=datetime.now(UTC),  # This would be tracked in real implementation
        current_time=datetime.now(UTC),
    )


@router.get("/test-error", response_model=OperationResult[dict[str, str]])
@limiter.limit("10/minute")  # Lower limit for test endpoint
async def test_error_handling(request: Request) -> dict[str, Any]:
    """
    Test endpoint for error handling (for development/testing).

    **Warning**: This endpoint is for development and testing purposes only.
    It randomly generates different types of errors to test the exception
    handling system. Should be removed or secured in production.
    """

    # This endpoint demonstrates different types of errors
    error_type = random.choice(["device_not_found", "ssh_error", "validation_error", "success"])

    if error_type == "device_not_found":
        raise DeviceNotFoundError("test-device", "hostname")
    elif error_type == "ssh_error":
        raise SSHConnectionError(
            "Failed to connect to test device",
            device_id="test-device-id",
            hostname="test-host",
            details={"error": "Connection timeout"},
        )
    elif error_type == "validation_error":
        raise CustomValidationError(
            "Invalid device configuration", field="hostname", value="invalid..hostname"
        )
    else:
        return OperationResult[dict[str, str]](
            success=True,
            operation_id="test-op-123",
            operation_type="test_operation",
            result={"message": "Test completed successfully"},
            error_message=None,
            execution_time_ms=150,
        )
