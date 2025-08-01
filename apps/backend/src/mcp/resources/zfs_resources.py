"""
ZFS MCP Resources

MCP resources for exposing ZFS pools, datasets, and snapshots 
with real-time data access via the REST API.
"""

import logging
import json
from typing import Any, Dict, List
from urllib.parse import urlparse, parse_qs

import httpx

from apps.backend.src.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_api_config():
    """Get API configuration settings"""
    settings = get_settings()
    return {
        'base_url': f"http://localhost:{settings.api.port}",
        'api_key': settings.auth.api_key,
        'timeout': 30
    }


async def _make_api_request(endpoint: str) -> Dict[str, Any]:
    """Make authenticated request to the REST API"""
    config = _get_api_config()
    
    headers = {}
    if config['api_key']:
        headers['Authorization'] = f"Bearer {config['api_key']}"
    
    full_url = f"{config['base_url']}{endpoint}"
    logger.info(f"Making API request to: {full_url}")
    
    async with httpx.AsyncClient(timeout=config['timeout']) as client:
        try:
            response = await client.get(full_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API request failed to {full_url}: {e}")
            logger.error(f"Response status: {e.response.status_code if hasattr(e, 'response') else 'unknown'}")
            logger.error(f"Response text: {e.response.text if hasattr(e, 'response') else 'unknown'}")
            raise RuntimeError(f"Failed to fetch ZFS data: {str(e)}")


async def get_zfs_pools_resource(uri: str) -> str:
    """
    Get ZFS pools resource content.
    
    URI format: zfs://pools/{hostname} or zfs://pools/{hostname}/{pool_name}
    """
    try:
        # Parse URI: zfs://pools/hostname or zfs://pools/hostname/pool_name
        parsed = urlparse(uri)
        if not parsed.scheme == 'zfs' or not parsed.path.startswith('/pools/'):
            raise ValueError(f"Invalid ZFS pools URI: {uri}")
        
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            raise ValueError(f"Invalid ZFS pools URI - missing hostname: {uri}")
        
        hostname = path_parts[1]
        pool_name = path_parts[2] if len(path_parts) > 2 else None
        
        if pool_name:
            # Get specific pool status
            endpoint = f"/api/zfs/{hostname}/pools/{pool_name}/status"
            data = await _make_api_request(endpoint)
            
            return json.dumps({
                "resource_type": "zfs_pool_status",
                "hostname": hostname,
                "pool_name": pool_name,
                "status": data,
                "uri": uri
            }, indent=2)
        else:
            # Get all pools
            endpoint = f"/api/zfs/{hostname}/pools"  
            data = await _make_api_request(endpoint)
            
            return json.dumps({
                "resource_type": "zfs_pools",
                "hostname": hostname,
                "pools": data,
                "uri": uri
            }, indent=2)
            
    except Exception as e:
        logger.error(f"Error fetching ZFS pools resource {uri}: {e}")
        return json.dumps({
            "error": str(e),
            "uri": uri,
            "resource_type": "zfs_pools"
        }, indent=2)


async def get_zfs_datasets_resource(uri: str) -> str:
    """
    Get ZFS datasets resource content.
    
    URI format: zfs://datasets/{hostname} or zfs://datasets/{hostname}?pool={pool_name}
    """
    try:
        # Parse URI: zfs://datasets/hostname?pool=pool_name
        parsed = urlparse(uri)
        if not parsed.scheme == 'zfs' or not parsed.path.startswith('/datasets/'):
            raise ValueError(f"Invalid ZFS datasets URI: {uri}")
        
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            raise ValueError(f"Invalid ZFS datasets URI - missing hostname: {uri}")
        
        hostname = path_parts[1]
        query_params = parse_qs(parsed.query)
        pool_name = query_params.get('pool', [None])[0]
        
        # Build endpoint with optional pool filter
        endpoint = f"/api/zfs/{hostname}/datasets"
        if pool_name:
            endpoint += f"?pool_name={pool_name}"
            
        data = await _make_api_request(endpoint)
        
        return json.dumps({
            "resource_type": "zfs_datasets",
            "hostname": hostname,
            "pool_name": pool_name,
            "datasets": data,
            "uri": uri
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error fetching ZFS datasets resource {uri}: {e}")
        return json.dumps({
            "error": str(e),
            "uri": uri,
            "resource_type": "zfs_datasets"
        }, indent=2)


async def get_zfs_snapshots_resource(uri: str) -> str:
    """
    Get ZFS snapshots resource content.
    
    URI format: zfs://snapshots/{hostname} or zfs://snapshots/{hostname}?dataset={dataset_name}&limit={limit}
    """
    try:
        # Parse URI: zfs://snapshots/hostname?dataset=dataset_name&limit=100
        parsed = urlparse(uri)
        if not parsed.scheme == 'zfs' or not parsed.path.startswith('/snapshots/'):
            raise ValueError(f"Invalid ZFS snapshots URI: {uri}")
        
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            raise ValueError(f"Invalid ZFS snapshots URI - missing hostname: {uri}")
        
        hostname = path_parts[1]
        query_params = parse_qs(parsed.query)
        dataset_name = query_params.get('dataset', [None])[0]
        limit = query_params.get('limit', [None])[0]
        
        # Build endpoint with optional filters
        endpoint = f"/api/zfs/{hostname}/snapshots"
        query_parts = []
        if dataset_name:
            query_parts.append(f"dataset_name={dataset_name}")
        if limit:
            query_parts.append(f"limit={limit}")
        if query_parts:
            endpoint += "?" + "&".join(query_parts)
            
        data = await _make_api_request(endpoint)
        
        return json.dumps({
            "resource_type": "zfs_snapshots",
            "hostname": hostname,
            "dataset_name": dataset_name,
            "limit": limit,
            "snapshots": data,
            "uri": uri
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error fetching ZFS snapshots resource {uri}: {e}")
        return json.dumps({
            "error": str(e),
            "uri": uri,
            "resource_type": "zfs_snapshots"
        }, indent=2)


async def get_zfs_health_resource(uri: str) -> str:
    """
    Get ZFS health resource content.
    
    URI format: zfs://health/{hostname}
    """
    try:
        # Parse URI: zfs://health/hostname
        parsed = urlparse(uri)
        if not parsed.scheme == 'zfs' or not parsed.path.startswith('/health/'):
            raise ValueError(f"Invalid ZFS health URI: {uri}")
        
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            raise ValueError(f"Invalid ZFS health URI - missing hostname: {uri}")
        
        hostname = path_parts[1]
        
        endpoint = f"/api/zfs/{hostname}/health"
        data = await _make_api_request(endpoint)
        
        return json.dumps({
            "resource_type": "zfs_health",
            "hostname": hostname,
            "health": data,
            "uri": uri
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error fetching ZFS health resource {uri}: {e}")
        return json.dumps({
            "error": str(e),
            "uri": uri,
            "resource_type": "zfs_health"
        }, indent=2)


async def list_zfs_resources() -> List[Dict[str, Any]]:
    """List all available ZFS MCP resources"""
    try:
        # Get list of devices from API
        config = _get_api_config()
        headers = {}
        if config['api_key']:
            headers['Authorization'] = f"Bearer {config['api_key']}"
        
        async with httpx.AsyncClient(timeout=config['timeout']) as client:
            response = await client.get(
                f"{config['base_url']}/api/devices",
                headers=headers
            )
            response.raise_for_status()
            devices = response.json()
        
        resources = []
        
        # Generate ZFS resources for each device
        for device in devices:
            hostname = device.get('hostname', 'unknown')
            
            # ZFS pools resources
            resources.extend([
                {
                    "uri": f"zfs://pools/{hostname}",
                    "name": f"ZFS Pools - {hostname}",
                    "description": f"All ZFS pools on {hostname}",
                    "mimeType": "application/json"
                },
                {
                    "uri": f"zfs://datasets/{hostname}",
                    "name": f"ZFS Datasets - {hostname}",
                    "description": f"All ZFS datasets on {hostname}",
                    "mimeType": "application/json"
                },
                {
                    "uri": f"zfs://snapshots/{hostname}",
                    "name": f"ZFS Snapshots - {hostname}",
                    "description": f"ZFS snapshots on {hostname}",
                    "mimeType": "application/json"
                },
                {
                    "uri": f"zfs://health/{hostname}",
                    "name": f"ZFS Health - {hostname}",
                    "description": f"ZFS health status for {hostname}",
                    "mimeType": "application/json"
                }
            ])
        
        return resources
        
    except Exception as e:
        logger.error(f"Error listing ZFS resources: {e}")
        return [
            {
                "uri": "zfs://error",
                "name": "ZFS Resources Error",
                "description": f"Failed to list ZFS resources: {str(e)}",
                "mimeType": "text/plain"
            }
        ]


async def get_zfs_resource(uri: str) -> str:
    """Route ZFS resource requests to appropriate handlers"""
    try:
        parsed = urlparse(uri)
        logger.info(f"Routing ZFS resource request - URI: {uri}, Path: {parsed.path}")
        
        if parsed.path.startswith('/pools/'):
            logger.info(f"Routing to pools handler for {uri}")
            return await get_zfs_pools_resource(uri)
        elif parsed.path.startswith('/datasets/'):
            logger.info(f"Routing to datasets handler for {uri}")
            return await get_zfs_datasets_resource(uri)
        elif parsed.path.startswith('/snapshots/'):
            logger.info(f"Routing to snapshots handler for {uri}")
            return await get_zfs_snapshots_resource(uri)
        elif parsed.path.startswith('/health/'):
            logger.info(f"Routing to health handler for {uri}")
            return await get_zfs_health_resource(uri)
        else:
            raise ValueError(f"Unknown ZFS resource type: {parsed.path}")
            
    except Exception as e:
        logger.error(f"Error routing ZFS resource request {uri}: {e}")
        return json.dumps({
            "error": str(e),
            "uri": uri,
            "resource_type": "zfs_unknown"
        }, indent=2)