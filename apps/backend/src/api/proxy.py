"""
Proxy Configuration API Endpoints

REST API endpoints for managing SWAG reverse proxy configurations
with real-time file access and database synchronization.
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import PlainTextResponse

from apps.backend.src.schemas.proxy_config import (
    ProxyConfigResponse, ProxyConfigList, ProxyConfigSummary,
    ProxyConfigSync
)
from apps.backend.src.mcp.tools.proxy_management import (
    list_proxy_configs, get_proxy_config, scan_proxy_configs,
    sync_proxy_config, get_proxy_config_summary
)
from apps.backend.src.mcp.resources.proxy_configs import get_proxy_config_resource

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/configs", response_model=ProxyConfigList)
async def list_configs(
    device: str = Query("squirts", description="Device hostname"),
    service_name: str | None = Query(None, description="Filter by service name"),
    status: str | None = Query(None, description="Filter by status"),
    ssl_enabled: bool | None = Query(None, description="Filter by SSL status"),
    limit: int = Query(100, description="Maximum number of results", ge=1, le=1000),
    offset: int = Query(0, description="Results offset for pagination", ge=0)
):
    """List all proxy configurations"""
    try:
        result = await list_proxy_configs(
            device=device,
            service_name=service_name,
            status=status,
            ssl_enabled=ssl_enabled,
            limit=limit,
            offset=offset
        )
        
        # Transform the result to match ProxyConfigList schema
        pagination = result.get('pagination', {})
        return ProxyConfigList(
            items=result.get('configs', []),
            total=pagination.get('total', 0),
            page=pagination.get('page', 1),
            page_size=pagination.get('limit', limit),
            total_pages=pagination.get('total_pages', 0)
        )
    except Exception as e:
        logger.error(f"Error listing proxy configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{service_name}", response_model=ProxyConfigResponse)
async def get_config(
    service_name: str = Path(..., description="Service name"),
    device: str | None = Query(None, description="Device hostname (optional for disambiguation)"),
    include_content: bool = Query(True, description="Include raw configuration content")
):
    """Get specific proxy configuration"""
    try:
        result = await get_proxy_config(
            service_name=service_name,
            device=device,
            include_content=include_content
        )
        return result
    except Exception as e:
        logger.error(f"Error getting proxy config for {service_name}: {e}")
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 500, detail=str(e))


@router.get("/configs/{service_name}/content", response_class=PlainTextResponse)
async def get_config_content(
    service_name: str = Path(..., description="Service name"),
    device: str = Query("squirts", description="Device hostname")
):
    """Get raw configuration file content"""
    try:
        # Use resource handler to get content
        uri = f"swag://{service_name}"
        resource_data = await get_proxy_config_resource(uri)
        
        if 'error' in resource_data:
            raise HTTPException(status_code=404, detail=resource_data['error'])
        
        return resource_data.get('content', '')
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config content for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan", response_model=ProxyConfigSync)
async def scan_configs(
    device: str = Query("squirts", description="Device hostname"),
    config_directory: str = Query("/mnt/appdata/swag/nginx/proxy-confs", description="Configuration directory path"),
    sync_to_database: bool = Query(True, description="Whether to sync findings to database")
):
    """Scan and synchronize proxy configurations"""
    try:
        result = await scan_proxy_configs(device, config_directory, sync_to_database)
        return result
    except Exception as e:
        logger.error(f"Error scanning proxy configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{service_name}/sync", response_model=ProxyConfigResponse)
async def sync_config(
    service_name: str = Path(..., description="Service name"),
    device: str | None = Query(None, description="Device hostname (optional)")
):
    """Synchronize specific proxy configuration"""
    try:
        # First get the config to find the config_id
        config_result = await get_proxy_config(
            service_name=service_name,
            device=device,
            include_content=False
        )
        config_id = config_result.get('id')
        
        if not config_id:
            raise HTTPException(status_code=404, detail=f"Configuration not found for service '{service_name}'")
        
        # Now sync using the config_id
        result = await sync_proxy_config(config_id=config_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing proxy config for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=ProxyConfigSummary)
async def get_summary(
    device: str = Query("squirts", description="Device hostname")
):
    """Get proxy configuration summary statistics"""
    try:
        result = await get_proxy_config_summary(device)
        return result
    except Exception as e:
        logger.error(f"Error getting proxy config summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_type}", response_class=PlainTextResponse)
async def get_template(
    template_type: str = Path(..., description="Template type: subdomain or subfolder")
):
    """Get SWAG configuration template"""
    try:
        if template_type not in ['subdomain', 'subfolder']:
            raise HTTPException(status_code=400, detail="Template type must be 'subdomain' or 'subfolder'")
        
        uri = f"swag://{template_type}-template"
        resource_data = await get_proxy_config_resource(uri)
        
        if 'error' in resource_data:
            raise HTTPException(status_code=404, detail=resource_data['error'])
        
        return resource_data.get('content', '')
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/samples", response_model=dict)
async def list_samples():
    """List all available SWAG sample configurations"""
    try:
        uri = "swag://samples/"
        resource_data = await get_proxy_config_resource(uri)
        
        if 'error' in resource_data:
            raise HTTPException(status_code=500, detail=resource_data['error'])
        
        return resource_data
    except Exception as e:
        logger.error(f"Error listing samples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/samples/{sample_name}", response_class=PlainTextResponse)
async def get_sample(
    sample_name: str = Path(..., description="Sample name (e.g., 'nextcloud' or 'nextcloud.subdomain.sample')")
):
    """Get SWAG sample configuration content"""
    try:
        uri = f"swag://samples/{sample_name}"
        resource_data = await get_proxy_config_resource(uri)
        
        if 'error' in resource_data:
            raise HTTPException(status_code=404, detail=resource_data['error'])
        
        return resource_data.get('content', '')
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sample {sample_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))