# API Layer Guidelines - Infrastructor Project

This file contains specific guidelines for working with the REST API layer of the infrastructor project.

## 🏗️ API Architecture Overview

The API layer provides REST endpoints for infrastructure management with the following structure:

### Core API Modules
- **`common.py`**: Shared authentication, rate limiting, and common endpoints
- **`devices.py`**: Device registry management and system monitoring endpoints  
- **`containers.py`**: Docker container lifecycle management
- **`compose_deployment.py`**: Docker Compose deployment and modification
- **`proxy.py`**: SWAG reverse proxy configuration management
- **`zfs.py`**: ZFS filesystem operations (pools, datasets, snapshots, health, analysis)
- **`vms.py`**: Virtual machine log access

### Router Mounting Map (as in `api/__init__.py`)
- `common` → `/api` (no additional prefix; endpoints like `/api/status`, `/api/system-info`)
- `devices` → `/api/devices`
- `containers` → `/api/containers`
- `proxy` → `/api/proxies`
- `zfs` → `/api/zfs`
- `compose_deployment` → `/api/compose`
- `vms` → `/api/vms`

## 🔧 API Patterns & Standards

### Router Organization
```python
# Standard router pattern
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# All endpoints require authentication
@router.get("/endpoint")
async def endpoint_function(
    param: str = Path(..., description="Parameter description"),
    query_param: int = Query(60, description="Query parameter"),
    current_user=Depends(get_current_user),
):
```

### Authentication Pattern
```python
# All endpoints MUST include authentication dependency
current_user=Depends(get_current_user)

# Authentication is implemented in common.py with Bearer token
# Simple validation: tokens must be >= 10 characters
# If settings.auth.api_key is not configured, endpoints accept unauthenticated requests (development mode)
# Production: Implement proper JWT validation or API key verification
```

### Error Handling Pattern
```python
# Always use try/except with proper exception chaining
try:
    result = await service_function()
    return result
except SpecificCustomError as e:
    # Map to appropriate HTTP status
    raise HTTPException(status_code=404, detail=str(e)) from e
except Exception as e:
    # Log unexpected errors
    logger.error(f"Error in operation: {e}")
    raise HTTPException(status_code=500, detail="Internal server error") from e
```

### Rate Limiting Pattern
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter configured in common.py
@router.get("/endpoint")
@limiter.limit("60/minute")  # Specific rate limit
async def endpoint(request: Request):
```

## 📊 API Endpoint Categories

### Device Management (`devices.py`)
- **CRUD Operations**: Create, read, update, delete device registry entries
- **Status Monitoring**: SSH connectivity testing and device status
- **System Metrics**: Drive health, system logs, network ports
- **Import Function**: Bulk import from SSH config files

**Key Pattern**: Device registry is OPTIONAL - SSH-based tools work directly with hostnames

### Container Management (`containers.py`)
- **Lifecycle Operations**: Start, stop, restart, remove containers
- **Information Gathering**: List, inspect, logs, stats
- **Command Execution**: Execute commands inside containers
- **Resource Monitoring**: Real-time container resource usage
- **Error Mapping**: Maps Docker exec return codes (e.g., 125/126/127) to appropriate HTTP status codes

**Key Pattern**: Direct SSH command execution with structured response formatting

### Docker Compose Deployment (`compose_deployment.py`)
- **Modification**: Adapt compose files for target devices (ports, paths, networks)
- **Deployment**: Deploy modified compose with backup and health checks
- **Combined Operations**: Modify-and-deploy in single atomic operation
- **Port/Network Scanning**: Pre-deployment infrastructure analysis

**Key Pattern**: Complex multi-step operations with comprehensive error handling

### Proxy Configuration (`proxy.py`)
- **SWAG Integration**: Real-time access to reverse proxy configurations
- **File Synchronization**: Database sync with actual configuration files
- **Template Management**: Access to configuration templates and samples
- **Content Delivery**: Raw configuration file content as plain text

**Key Pattern**: MCP resource integration with database synchronization

### ZFS Management (`zfs.py`)
- **ZFS filesystem operations**: Pools, datasets, snapshots, health, analysis
- **Service Layer Architecture**: Dedicated service classes for each ZFS area
- **Complex Operations**: Snapshot send/receive, cloning, diffing
- **Health Monitoring**: ARC stats, events, comprehensive health checks

**Key Pattern**: Service dependency injection with comprehensive timeout handling

## 🛡️ Critical API Coding Standards

### Import Organization
```python
# Standard library imports first
import logging
from datetime import datetime, timezone
from typing import Optional

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

# Local imports
from apps.backend.src.api.common import get_current_user
from apps.backend.src.services.example_service import ExampleService
from apps.backend.src.schemas.example import ExampleResponse
from apps.backend.src.core.exceptions import CustomError
```

### Modern Type Annotations
```python
# ✅ Correct - Python 3.11+ built-in generics
def process_items(items: list[str]) -> dict[str, int]:
    return {"count": len(items)}

# Query parameters with union types
optional_param: str | None = Query(None, description="Optional parameter")

# ❌ Avoid - Deprecated typing imports
from typing import Union, List, Dict  # Don't use these
```

### Timezone Handling
```python
# ✅ Always use UTC timezone
from datetime import datetime, timezone

timestamp = datetime.now(timezone.utc)

# ❌ Never use naive datetime
timestamp = datetime.now()  # Missing timezone
```

### Exception Chaining
```python
# ✅ Proper exception chaining with 'from e'
try:
    result = await external_service()
except ExternalError as e:
    logger.error(f"External service failed: {e}")
    raise HTTPException(status_code=503, detail="Service unavailable") from e

# ❌ Missing exception chaining
except ExternalError as e:
    raise HTTPException(status_code=503, detail="Error")  # Missing 'from e'
```

### String Formatting
```python
# ✅ Use f-strings only when interpolating
error_msg = f"Device {device_id} not found"  # Interpolating variable
static_msg = "Operation completed successfully"  # No f-string needed

# ❌ Unnecessary f-strings
static_msg = f"Operation completed successfully"  # Don't use f-string for static text
```

## 📋 Response Format Standards

### Success Response Pattern
```python
# Simple data return
return {"result": data, "timestamp": datetime.now(timezone.utc)}

# Complex operation result  
return OperationResult[dict](
    success=True,
    operation_type="device_create",
    result=device_data,
    execution_time_ms=execution_time,
    message="Device created successfully"
)
```

### Error Response Pattern
```python
# HTTP exceptions with proper status codes
# 400: Bad Request (validation errors)
# 404: Not Found (resource doesn't exist)
# 503: Service Unavailable (SSH connection failed)
# 500: Internal Server Error (unexpected errors)

raise HTTPException(
    status_code=404,
    detail=f"Device '{hostname}' not found"
)
```

### Pagination Pattern
```python
# Use PaginationParams dependency
async def list_items(
    pagination: PaginationParams = Depends(),
    current_user=Depends(get_current_user),
):
    return await service.list_items(pagination=pagination)
```

## 🔍 API Testing Patterns

### Parameter Validation
```python
# Path parameters with descriptions
hostname: str = Path(..., description="Device hostname")

# Query parameters with validation
timeout: int = Query(60, description="SSH timeout in seconds", ge=1, le=300)
limit: int = Query(100, description="Max results", ge=1, le=1000)
```

### Request/Response Models
```python
# Use Pydantic models for complex requests
class DeviceCreateRequest(BaseModel):
    hostname: str = Field(..., description="Device hostname")
    device_type: str = Field("server", description="Device type")
    
# Use response_model in decorators
@router.post("/devices", response_model=DeviceResponse)
async def create_device(request: DeviceCreateRequest):
```

## 🚀 Performance Considerations

### SSH Command Optimization
```python
# Use appropriate timeouts based on operation complexity
quick_ops = 30   # Status checks, simple queries
medium_ops = 60  # Container operations, file operations  
long_ops = 300   # ZFS operations, large transfers

# Command construction with proper escaping
cmd = f"docker logs {container_name}"
if since:
    cmd += f" --since {since}"  # Parameters validated by Pydantic
```

### Service Layer Integration
```python
# Dependency injection for services
def get_device_service(db: AsyncSession = Depends(get_db_session)) -> DeviceService:
    return DeviceService(db)

# Use in endpoints
async def create_device(
    device_data: DeviceCreate,
    service: DeviceService = Depends(get_device_service),
):
```

## 🔗 Cross-Module Integration

### Unified Data Collection Integration
```python
# Use unified data collection service for data retrieval + caching/persistence
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.core.database import get_async_session_factory
from apps.backend.src.utils.ssh_client import get_ssh_client, execute_ssh_command_simple

session_factory = get_async_session_factory()
ssh_client = get_ssh_client()
unified_service = await get_unified_data_collection_service(
    db_session_factory=session_factory,
    ssh_client=ssh_client,
)

# Define a collection method that performs the SSH work
async def collect_container_list():
    result = await execute_ssh_command_simple(hostname, "docker ps --format '{{json .}}'", timeout)
    # parse and return structured data...

# Collect and store with caching and correlation
result = await unified_service.collect_and_store_data(
    data_type="container_list",
    device_id=device_id,
    collection_method=collect_container_list,
    force_refresh=live,
    correlation_id=f"container_list_{hostname}",
)
```

### Resource Access Pattern
```python
# Access MCP resources for real-time SWAG template/sample data (proxy.py)
from apps.backend.src.mcp.resources.proxy_configs import get_proxy_config_resource

uri = f"swag://{service_name}"
resource_data = await get_proxy_config_resource(uri)
```

## 📝 Documentation Standards

### Endpoint Documentation
```python
@router.get("/endpoint")
async def endpoint_function():
    """
    Brief description of what this endpoint does.
    
    Detailed explanation of the operation including:
    - What data is retrieved/modified
    - Special behaviors or requirements
    - Performance considerations
    
    Args:
        param: Parameter description with expected format
        
    Returns:
        Description of response format and contents
    """
```

### OpenAPI Integration
- All endpoints automatically generate OpenAPI documentation
- Use Pydantic models for request/response schemas
- Include parameter descriptions in Query/Path declarations
- Response models ensure consistent API documentation

## ⚠️ Security Considerations

### Input Validation
```python
# Always validate hostnames and device names
# Use Pydantic Field validation for complex patterns
# Sanitize SSH command parameters to prevent injection
```

### Authentication
```python
# Current: Simple Bearer token validation (>= 10 chars)
# Production TODO: Implement proper JWT validation
# All endpoints require authentication via get_current_user dependency
```

### SSH Security
```python
# Use execute_ssh_command_simple for safety
# Commands are executed with configured timeouts
# Error messages don't expose sensitive system information
```

---

*This API layer follows infrastructor project standards with modern Python patterns, comprehensive error handling, and secure SSH-based infrastructure management.*