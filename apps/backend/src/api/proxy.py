"""
Proxy Configuration API Endpoints

REST API endpoints for managing SWAG reverse proxy configurations
with real-time file access and database synchronization.
"""

import logging
import time
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.device import Device

from apps.backend.src.schemas.proxy_config import (
    ProxyConfigResponse,
    ProxyConfigList,
    ProxyConfigSummary,
    ProxyConfigSync,
)
# TODO: Use unified data collection service instead of MCP tools
from apps.backend.src.mcp.resources.proxy_configs import get_proxy_config_resource
from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_proxy_service_dep():
    """Dependency to get proxy service with database session"""
    async with get_async_session() as session:
        yield get_proxy_service(session)

# Cache SWAG device detection to prevent repeated expensive scans
_swag_device_cache: str | None = None
_swag_device_cache_timestamp: float = 0
SWAG_CACHE_TTL = 300  # 5 minutes

async def _detect_swag_device() -> str:
    """
    Detect the SWAG device by looking for running SWAG containers and */swag/nginx/* directories.
    
    Returns:
        str: SWAG device hostname
        
    Raises:
        HTTPException: If SWAG device cannot be determined
    """
    global _swag_device_cache, _swag_device_cache_timestamp
    
    # Check cache first
    current_time = time.time()
    if (_swag_device_cache is not None and 
        (current_time - _swag_device_cache_timestamp) < SWAG_CACHE_TTL):
        logger.debug(f"Using cached SWAG device: {_swag_device_cache}")
        return _swag_device_cache
    
    # Search for devices with running SWAG containers
    try:
        async with get_async_session() as session:
            # Get all monitoring-enabled devices
            result = await session.execute(
                select(Device).where(
                    Device.monitoring_enabled == True
                )
            )
            devices = result.scalars().all()
            
            ssh_client = get_ssh_client()
            
            for device in devices:
                try:
                    # Check for running SWAG container AND */swag/nginx/* directory
                    swag_check_cmd = (
                        "docker ps --format '{{.Names}}' | grep -i swag && "
                        "find /*/swag/nginx/ -type d 2>/dev/null | head -1 || "
                        "find /mnt/*/swag/nginx/ -type d 2>/dev/null | head -1"
                    )
                    
                    connection_info = SSHConnectionInfo(
                        host=device.hostname,
                        port=device.ssh_port,
                        username=device.ssh_username,
                        password=device.ssh_password,
                        private_key_path=device.ssh_private_key_path,
                        connect_timeout=10,
                    )
                    
                    result = await ssh_client.execute_command(
                        connection_info, swag_check_cmd, timeout=15
                    )
                    
                    if result.return_code == 0 and result.stdout.strip():
                        lines = result.stdout.strip().split('\n')
                        has_running_container = any('swag' in line.lower() for line in lines if not line.startswith('/'))
                        has_nginx_dir = any(line.startswith('/') and 'swag/nginx' in line for line in lines)
                        
                        if has_running_container and has_nginx_dir:
                            # Cache the result
                            _swag_device_cache = device.hostname
                            _swag_device_cache_timestamp = current_time
                            logger.info(f"Found SWAG device: {device.hostname} (running container + nginx directory)")
                            return device.hostname
                            
                except Exception as e:
                    logger.debug(f"Could not check SWAG on device {device.hostname}: {e}")
                    continue
                    
        # No SWAG device found
        raise HTTPException(
            status_code=404, 
            detail="No SWAG device found with running container and nginx directory"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting SWAG device: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"SWAG device detection failed: {str(e)}"
        )


@router.get("/configs", response_model=ProxyConfigList)
async def list_configs(
    device: str | None = Query(None, description="Device hostname (auto-detected if not provided)"),
    service_name: str | None = Query(None, description="Filter by service name"),
    status: str | None = Query(None, description="Filter by status"),
    ssl_enabled: bool | None = Query(None, description="Filter by SSL status"),
    limit: int = Query(100, description="Maximum number of results", ge=1, le=1000),
    offset: int = Query(0, description="Results offset for pagination", ge=0),
    proxy_service = Depends(get_proxy_service_dep),
):
    """List all proxy configurations"""
    try:
        result = await proxy_service.list_proxy_configs(
            device_hostname=device,
            service_name=service_name,
            limit=limit,
            offset=offset,
        )

        # Transform the result to match ProxyConfigList schema
        pagination = result.get("pagination", {})
        return ProxyConfigList(
            items=result.get("configs", []),
            total=pagination.get("total", 0),
            page=pagination.get("page", 1),
            page_size=pagination.get("limit", limit),
            total_pages=pagination.get("total_pages", 0),
        )
    except Exception as e:
        logger.error(f"Error listing proxy configs: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/configs/{service_name}", response_model=ProxyConfigResponse)
async def get_config(
    service_name: str = Path(..., description="Service name"),
    device: str | None = Query(None, description="Device hostname (optional for disambiguation)"),
    include_content: bool = Query(True, description="Include raw configuration content"),
    proxy_service = Depends(get_proxy_service_dep),
):
    """Get specific proxy configuration"""
    try:
        result = await proxy_service.get_proxy_config(
            service_name=service_name, 
            device_hostname=device, 
            include_content=include_content
        )
        return result
    except Exception as e:
        logger.error(f"Error getting proxy config for {service_name}: {e}")
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 500, detail=str(e)
        ) from e


@router.get("/configs/{service_name}/content", response_class=PlainTextResponse)
async def get_config_content(
    service_name: str = Path(..., description="Service name"),
    device: str | None = Query(None, description="Device hostname (auto-detected if not provided)"),
):
    """Get raw configuration file content"""
    try:
        # Use resource handler to get content
        uri = f"swag://{service_name}"
        resource_data = await get_proxy_config_resource(uri)

        if "error" in resource_data:
            raise HTTPException(status_code=404, detail=resource_data["error"])

        return resource_data.get("content", "")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config content for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/scan", response_model=ProxyConfigSync)
async def scan_configs(
    device: str | None = Query(None, description="Device hostname (auto-detected if not provided)"),
    config_directory: str = Query(
        "/mnt/appdata/swag/nginx/proxy-confs", description="Configuration directory path"
    ),
    sync_to_database: bool = Query(True, description="Whether to sync findings to database"),
):
    """Scan and synchronize proxy configurations"""
    try:
        # Auto-detect SWAG device if not provided
        device = device or await _detect_swag_device()
        
        result = await scan_proxy_configs(device, config_directory, sync_to_database)
        return result
    except Exception as e:
        logger.error(f"Error scanning proxy configs: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/configs/{service_name}/sync", response_model=ProxyConfigResponse)
async def sync_config(
    service_name: str = Path(..., description="Service name"),
    device: str | None = Query(None, description="Device hostname (optional)"),
):
    """Synchronize specific proxy configuration"""
    try:
        # First get the config to find the config_id
        config_result = await get_proxy_config(
            service_name=service_name, device=device, include_content=False
        )
        config_id = config_result.get("id")

        if not config_id:
            raise HTTPException(
                status_code=404, detail=f"Configuration not found for service '{service_name}'"
            )

        # Now sync using the config_id
        result = await sync_proxy_config(config_id=config_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing proxy config for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/summary", response_model=ProxyConfigSummary)
async def get_summary(device: str | None = Query(None, description="Device hostname (auto-detected if not provided)")):
    """Get proxy configuration summary statistics"""
    try:
        # Auto-detect SWAG device if not provided
        device = device or await _detect_swag_device()
        
        result = await get_proxy_config_summary(device)
        return result
    except Exception as e:
        logger.error(f"Error getting proxy config summary: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/templates/{template_type}", response_class=PlainTextResponse)
async def get_template(
    template_type: str = Path(..., description="Template type: subdomain or subfolder"),
):
    """Get SWAG configuration template"""
    try:
        if template_type not in ["subdomain", "subfolder"]:
            raise HTTPException(
                status_code=400, detail="Template type must be 'subdomain' or 'subfolder'"
            )

        uri = f"swag://{template_type}-template"
        resource_data = await get_proxy_config_resource(uri)

        if "error" in resource_data:
            raise HTTPException(status_code=404, detail=resource_data["error"])

        return resource_data.get("content", "")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/samples", response_model=dict)
async def list_samples():
    """List all available SWAG sample configurations"""
    try:
        uri = "swag://samples/"
        resource_data = await get_proxy_config_resource(uri)

        if "error" in resource_data:
            raise HTTPException(status_code=500, detail=resource_data["error"])

        return resource_data
    except Exception as e:
        logger.error(f"Error listing samples: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/samples/{sample_name}", response_class=PlainTextResponse)
async def get_sample(
    sample_name: str = Path(
        ..., description="Sample name (e.g., 'nextcloud' or 'nextcloud.subdomain.sample')"
    ),
):
    """Get SWAG sample configuration content"""
    try:
        uri = f"swag://samples/{sample_name}"
        resource_data = await get_proxy_config_resource(uri)

        if "error" in resource_data:
            raise HTTPException(status_code=404, detail=resource_data["error"])

        return resource_data.get("content", "")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sample {sample_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

