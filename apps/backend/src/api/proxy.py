"""
Proxy Configuration API Endpoints

REST API endpoints for managing SWAG reverse proxy configurations
with real-time file access and database synchronization.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import PlainTextResponse

from apps.backend.src.schemas.proxy_config import (
    ProxyConfigResponse, ProxyConfigList, ProxyConfigSummary,
    ProxyConfigFileInfo, ProxyConfigSync
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
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    ssl_enabled: Optional[bool] = Query(None, description="Filter by SSL status"),
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
    device: str = Query("squirts", description="Device hostname"),
    force_refresh: bool = Query(False, description="Force refresh from file system"),
    include_parsed: bool = Query(True, description="Include parsed nginx configuration")
):
    """Get specific proxy configuration"""
    try:
        result = await get_proxy_config(device, service_name, force_refresh, include_parsed)
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
    force_update: bool = Query(False, description="Force update existing records")
):
    """Scan and synchronize proxy configurations"""
    try:
        result = await scan_proxy_configs(device, config_directory, force_update)
        return result
    except Exception as e:
        logger.error(f"Error scanning proxy configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configs/{service_name}/sync", response_model=ProxyConfigResponse)
async def sync_config(
    service_name: str = Path(..., description="Service name"),
    device: str = Query("squirts", description="Device hostname")
):
    """Synchronize specific proxy configuration"""
    try:
        result = await sync_proxy_config(device, service_name)
        return result
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