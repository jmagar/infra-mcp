"""
Proxy Configuration Management MCP Tools

MCP tools for managing SWAG reverse proxy configurations via HTTP client calls
to the REST API endpoints. Follows the HTTP client architecture pattern.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx
import os

logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:9101/api")
API_KEY = os.getenv("API_KEY")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "120.0"))

# HTTP client setup
class APIClient:
    """HTTP client for FastAPI endpoints"""
    def __init__(self):
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        
        self.client = httpx.AsyncClient(
            base_url=API_BASE_URL,
            timeout=httpx.Timeout(API_TIMEOUT),
            headers=headers
        )
    
    async def close(self):
        await self.client.aclose()

# Global API client instance
_api_client: Optional[APIClient] = None

async def get_api_client() -> APIClient:
    """Get or create global API client"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client


async def list_proxy_configs(
    device: Optional[str] = None,
    service_name: Optional[str] = None,
    status: Optional[str] = None,
    ssl_enabled: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List proxy configurations with real-time sync check via API call

    Args:
        device: Filter by device hostname 
        service_name: Filter by service name
        status: Filter by status (active, inactive, error)
        ssl_enabled: Filter by SSL status
        limit: Maximum number of results
        offset: Results offset for pagination

    Returns:
        Dict containing proxy configurations list from REST API
    """
    try:
        api_client = await get_api_client()
        
        # Build query parameters
        params = {
            "limit": limit,
            "offset": offset,
        }
        if device:
            params["device"] = device
        if service_name:
            params["service_name"] = service_name
        if status:
            params["status"] = status
        if ssl_enabled is not None:
            params["ssl_enabled"] = ssl_enabled
        
        # Make API call to proxy configs endpoint
        response = await api_client.client.get("/proxies/configs", params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully retrieved {len(result.get('items', []))} proxy configurations")
        
        # Convert ProxyConfigList response to legacy format
        return {
            "configs": result.get("items", []),
            "pagination": {
                "total": result.get("total", 0),
                "limit": result.get("page_size", limit),
                "offset": offset,
                "page": result.get("page", 1),
                "total_pages": result.get("total_pages", 0),
            },
            "query_timestamp": datetime.now(timezone.utc).isoformat(),
            "real_time_check": True,
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error listing proxy configs: {e}")
        raise Exception(f"Failed to list proxy configurations: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error listing proxy configs: {e}")
        raise Exception(f"Failed to list proxy configurations: {str(e)}") from e


async def get_proxy_config(
    config_id: Optional[int] = None,
    device: Optional[str] = None,
    service_name: Optional[str] = None,
    include_content: bool = True,
) -> Dict[str, Any]:
    """
    Get specific proxy configuration via API call

    Args:
        config_id: Configuration ID (not used - service_name required)
        device: Device hostname
        service_name: Service name (required for API call)
        include_content: Include raw configuration content

    Returns:
        Dict containing proxy configuration details from REST API
    """
    try:
        if not service_name:
            raise Exception("service_name is required for proxy config lookup")
        
        api_client = await get_api_client()
        
        # Build query parameters
        params = {
            "include_content": include_content,
        }
        if device:
            params["device"] = device
        
        # Make API call to specific proxy config endpoint
        response = await api_client.client.get(f"/proxies/configs/{service_name}", params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully retrieved proxy configuration for service '{service_name}'")
        
        return result

    except httpx.TimeoutException as e:
        logger.error(f"Timeout getting proxy config for {service_name}: {e}")
        raise Exception(f"Timeout getting proxy configuration for '{service_name}' - operation took longer than {API_TIMEOUT}s") from e
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting proxy config for {service_name}: {e}")
        if hasattr(e, 'response') and e.response.status_code == 404:
            raise Exception(f"Proxy configuration not found for service '{service_name}'") from e
        raise Exception(f"Failed to get proxy configuration: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error getting proxy config: {e}")
        raise Exception(f"Failed to get proxy configuration: {str(e)}") from e


async def scan_proxy_configs(
    device: Optional[str] = None,
    config_directory: Optional[str] = None,
    sync_to_database: bool = True,
) -> Dict[str, Any]:
    """
    Scan proxy configuration directory for fresh configs via API call

    Args:
        device: Device hostname
        config_directory: Directory containing proxy configs
        sync_to_database: Whether to sync findings to database

    Returns:
        Dict containing scan results from REST API
    """
    try:
        api_client = await get_api_client()
        
        # Build query parameters
        params = {
            "sync_to_database": sync_to_database,
        }
        if device:
            params["device"] = device
        if config_directory:
            params["config_directory"] = config_directory
        
        # Make API call to scan endpoint
        response = await api_client.client.post("/proxies/scan", params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully scanned proxy configs on device {device or 'default'}")
        
        return result

    except httpx.HTTPError as e:
        logger.error(f"HTTP error scanning proxy configs: {e}")
        raise Exception(f"Failed to scan proxy configurations: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error scanning proxy configs: {e}")
        raise Exception(f"Failed to scan proxy configurations: {str(e)}") from e


async def sync_proxy_config(
    config_id: Optional[int] = None, 
    service_name: Optional[str] = None,
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Sync specific proxy configuration with file system via API call

    Args:
        config_id: Configuration ID (not used - service_name required)
        service_name: Service name (required for API call)
        force_update: Force update even if hashes match

    Returns:
        Dict containing sync results from REST API
    """
    try:
        if not service_name:
            raise Exception("service_name is required for proxy config sync")
        
        api_client = await get_api_client()
        
        # Build query parameters
        params = {}
        if force_update:
            params["force_update"] = force_update
        
        # Make API call to sync endpoint
        response = await api_client.client.post(f"/proxies/configs/{service_name}/sync", params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully synced proxy configuration for service '{service_name}'")
        
        return result

    except httpx.TimeoutException as e:
        logger.error(f"Timeout syncing proxy config for {service_name}: {e}")
        raise Exception(f"Timeout syncing proxy configuration for '{service_name}' - operation took longer than {API_TIMEOUT}s") from e
    except httpx.HTTPError as e:
        logger.error(f"HTTP error syncing proxy config for {service_name}: {e}")
        if hasattr(e, 'response') and e.response.status_code == 404:
            raise Exception(f"Proxy configuration not found for service '{service_name}'") from e
        raise Exception(f"Failed to sync proxy configuration: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error syncing proxy config: {e}")
        raise Exception(f"Failed to sync proxy configuration: {str(e)}") from e


async def get_proxy_config_summary(device: Optional[str] = None) -> Dict[str, Any]:
    """
    Get summary statistics for proxy configurations via API call

    Args:
        device: Optional device filter

    Returns:
        Dict containing summary statistics from REST API
    """
    try:
        api_client = await get_api_client()
        
        # Build query parameters
        params = {}
        if device:
            params["device"] = device
        
        # Make API call to summary endpoint
        response = await api_client.client.get("/proxies/summary", params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully retrieved proxy configuration summary")
        
        return result

    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting proxy config summary: {e}")
        raise Exception(f"Failed to get proxy configuration summary: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error getting proxy config summary: {e}")
        raise Exception(f"Failed to get proxy configuration summary: {str(e)}") from e