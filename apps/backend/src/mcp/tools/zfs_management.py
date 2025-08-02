"""
ZFS Management MCP Tools

MCP tools for comprehensive ZFS pool, dataset, and snapshot management
utilizing the ZFS REST API endpoints for operation execution.
"""

import logging
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger(__name__)


def _get_api_config():
    """Get API configuration settings"""
    import os
    return {
        "base_url": "http://localhost:9101",
        "api_key": os.getenv("API_KEY", "your-api-key-for-authentication"),
        "timeout": 60,
    }


async def _make_api_request(method: str, endpoint: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make authenticated request to the ZFS API"""
    config = _get_api_config()
    
    headers = {}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"
    
    full_url = f"{config['base_url']}{endpoint}"
    logger.info(f"Making {method} API request to: {full_url}")
    
    async with httpx.AsyncClient(timeout=config["timeout"]) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(full_url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(full_url, headers=headers, json=json_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"ZFS API request failed to {full_url}: {e}")
            if hasattr(e, 'response'):
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            raise Exception(f"Failed to execute ZFS operation: {str(e)}")


# Pool Management Tools
async def list_zfs_pools(device: str, timeout: int = 30) -> Dict[str, Any]:
    """List all ZFS pools on a device."""
    logger.info(f"Listing ZFS pools on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/pools?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "pools": result.get("pools", []),
            "total_pools": result.get("total_pools", 0),
            "success": True
        }
    except Exception as e:
        logger.error(f"Error listing ZFS pools on {device}: {e}")
        raise Exception(f"Failed to list ZFS pools on {device}: {str(e)}")


async def get_zfs_pool_status(device: str, pool_name: str, timeout: int = 30) -> Dict[str, Any]:
    """Get detailed status for a specific ZFS pool."""
    logger.info(f"Getting ZFS pool status for {pool_name} on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/pools/{pool_name}/status?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "pool_name": pool_name,
            "status": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error getting pool status for {pool_name} on {device}: {e}")
        raise Exception(f"Failed to get pool status for {pool_name} on {device}: {str(e)}")


# Dataset Management Tools
async def list_zfs_datasets(device: str, pool_name: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
    """List ZFS datasets, optionally filtered by pool."""
    logger.info(f"Listing ZFS datasets on device: {device} (pool: {pool_name or 'all'})")
    try:
        endpoint = f"/api/zfs/{device}/datasets?timeout={timeout}"
        if pool_name:
            endpoint += f"&pool_name={pool_name}"
        
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "pool_name": pool_name,
            "datasets": result.get("datasets", []),
            "total_datasets": result.get("total_datasets", 0),
            "success": True
        }
    except Exception as e:
        logger.error(f"Error listing ZFS datasets on {device}: {e}")
        raise Exception(f"Failed to list ZFS datasets on {device}: {str(e)}")


async def get_zfs_dataset_properties(device: str, dataset_name: str, timeout: int = 30) -> Dict[str, Any]:
    """Get all properties for a specific ZFS dataset."""
    logger.info(f"Getting properties for dataset {dataset_name} on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/datasets/{dataset_name}/properties?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "dataset_name": dataset_name,
            "properties": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error getting dataset properties for {dataset_name} on {device}: {e}")
        raise Exception(f"Failed to get dataset properties for {dataset_name} on {device}: {str(e)}")


# Snapshot Management Tools
async def list_zfs_snapshots(device: str, dataset_name: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
    """List ZFS snapshots, optionally filtered by dataset."""
    logger.info(f"Listing ZFS snapshots on device: {device} (dataset: {dataset_name or 'all'})")
    try:
        endpoint = f"/api/zfs/{device}/snapshots?timeout={timeout}"
        if dataset_name:
            endpoint += f"&dataset_name={dataset_name}"
        
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "dataset_name": dataset_name,
            "snapshots": result.get("snapshots", []),
            "total_snapshots": result.get("total_snapshots", 0),
            "success": True
        }
    except Exception as e:
        logger.error(f"Error listing ZFS snapshots on {device}: {e}")
        raise Exception(f"Failed to list ZFS snapshots on {device}: {str(e)}")


async def create_zfs_snapshot(
    device: str, 
    dataset_name: str, 
    snapshot_name: str, 
    recursive: bool = False, 
    timeout: int = 60
) -> Dict[str, Any]:
    """Create a new ZFS snapshot."""
    logger.info(f"Creating ZFS snapshot {snapshot_name} for dataset {dataset_name} on device: {device} (recursive: {recursive})")
    try:
        endpoint = f"/api/zfs/{device}/snapshots?timeout={timeout}"
        payload = {
            "dataset_name": dataset_name,
            "snapshot_name": snapshot_name,
            "recursive": recursive
        }
        result = await _make_api_request("POST", endpoint, payload)
        return {
            "device": device,
            "dataset_name": dataset_name,
            "snapshot_name": snapshot_name,
            "recursive": recursive,
            "result": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error creating snapshot {snapshot_name} on {device}: {e}")
        raise Exception(f"Failed to create snapshot {snapshot_name} on {device}: {str(e)}")


async def clone_zfs_snapshot(
    device: str, 
    snapshot_name: str, 
    clone_name: str, 
    timeout: int = 60
) -> Dict[str, Any]:
    """Clone a ZFS snapshot."""
    logger.info(f"Cloning ZFS snapshot {snapshot_name} to {clone_name} on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/snapshots/{snapshot_name}/clone?timeout={timeout}"
        payload = {"clone_name": clone_name}
        result = await _make_api_request("POST", endpoint, payload)
        return {
            "device": device,
            "snapshot_name": snapshot_name,
            "clone_name": clone_name,
            "result": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error cloning snapshot {snapshot_name} on {device}: {e}")
        raise Exception(f"Failed to clone snapshot {snapshot_name} on {device}: {str(e)}")


async def send_zfs_snapshot(
    device: str, 
    snapshot_name: str, 
    destination: Optional[str] = None, 
    incremental: bool = False, 
    timeout: int = 300
) -> Dict[str, Any]:
    """Send a ZFS snapshot for replication/backup."""
    logger.info(f"Sending ZFS snapshot {snapshot_name} from device: {device} (destination: {destination}, incremental: {incremental})")
    try:
        endpoint = f"/api/zfs/{device}/snapshots/{snapshot_name}/send?timeout={timeout}"
        payload = {
            "destination": destination,
            "incremental": incremental
        }
        result = await _make_api_request("POST", endpoint, payload)
        return {
            "device": device,
            "snapshot_name": snapshot_name,
            "destination": destination,
            "incremental": incremental,
            "result": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error sending snapshot {snapshot_name} from {device}: {e}")
        raise Exception(f"Failed to send snapshot {snapshot_name} from {device}: {str(e)}")


async def receive_zfs_snapshot(
    device: str, 
    dataset_name: str, 
    timeout: int = 300
) -> Dict[str, Any]:
    """Receive a ZFS snapshot stream."""
    logger.info(f"Receiving ZFS snapshot stream for dataset {dataset_name} on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/receive?timeout={timeout}"
        payload = {"dataset_name": dataset_name}
        result = await _make_api_request("POST", endpoint, payload)
        return {
            "device": device,
            "dataset_name": dataset_name,
            "result": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error receiving snapshot for {dataset_name} on {device}: {e}")
        raise Exception(f"Failed to receive snapshot for {dataset_name} on {device}: {str(e)}")


async def diff_zfs_snapshots(
    device: str, 
    snapshot1: str, 
    snapshot2: str, 
    timeout: int = 60
) -> Dict[str, Any]:
    """Compare differences between two ZFS snapshots."""
    logger.info(f"Comparing ZFS snapshots {snapshot1} and {snapshot2} on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/snapshots/{snapshot1}/diff?snapshot2={snapshot2}&timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "snapshot1": snapshot1,
            "snapshot2": snapshot2,
            "diff": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error diffing snapshots {snapshot1} and {snapshot2} on {device}: {e}")
        raise Exception(f"Failed to diff snapshots {snapshot1} and {snapshot2} on {device}: {str(e)}")


# Health and Monitoring Tools
async def check_zfs_health(device: str, timeout: int = 60) -> Dict[str, Any]:
    """Comprehensive ZFS health check."""
    logger.info(f"Checking ZFS health on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/health?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "health": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error checking ZFS health on {device}: {e}")
        raise Exception(f"Failed to check ZFS health on {device}: {str(e)}")


async def get_zfs_arc_stats(device: str, timeout: int = 30) -> Dict[str, Any]:
    """Get ZFS ARC (Adaptive Replacement Cache) statistics."""
    logger.info(f"Getting ZFS ARC stats on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/arc-stats?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "arc_stats": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error getting ARC stats on {device}: {e}")
        raise Exception(f"Failed to get ARC stats on {device}: {str(e)}")


async def monitor_zfs_events(device: str, timeout: int = 30) -> Dict[str, Any]:
    """Monitor ZFS events and error messages."""
    logger.info(f"Monitoring ZFS events on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/events?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "events": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error monitoring ZFS events on {device}: {e}")
        raise Exception(f"Failed to monitor ZFS events on {device}: {str(e)}")


# Analysis and Reporting Tools
async def generate_zfs_report(device: str, timeout: int = 120) -> Dict[str, Any]:
    """Generate comprehensive ZFS report."""
    logger.info(f"Generating ZFS report for device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/report?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "report": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error generating ZFS report on {device}: {e}")
        raise Exception(f"Failed to generate ZFS report on {device}: {str(e)}")


async def analyze_snapshot_usage(device: str, timeout: int = 60) -> Dict[str, Any]:
    """Analyze snapshot space usage and provide cleanup recommendations."""
    logger.info(f"Analyzing snapshot usage on device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/snapshots/usage?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "analysis": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error analyzing snapshot usage on {device}: {e}")
        raise Exception(f"Failed to analyze snapshot usage on {device}: {str(e)}")


async def optimize_zfs_settings(device: str, timeout: int = 60) -> Dict[str, Any]:
    """Analyze ZFS configuration and suggest optimizations."""
    logger.info(f"Optimizing ZFS settings for device: {device}")
    try:
        endpoint = f"/api/zfs/{device}/optimize?timeout={timeout}"
        result = await _make_api_request("GET", endpoint)
        return {
            "device": device,
            "optimization": result,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error optimizing ZFS settings on {device}: {e}")
        raise Exception(f"Failed to optimize ZFS settings on {device}: {str(e)}")


# ZFS Tool Registration
ZFS_TOOLS = {
    # Pool Management
    "list_zfs_pools": {
        "function": list_zfs_pools,
        "description": "List all ZFS pools on a device",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 30}
        }
    },
    "get_zfs_pool_status": {
        "function": get_zfs_pool_status,
        "description": "Get detailed status for a specific ZFS pool",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "pool_name": {"type": "string", "description": "ZFS pool name"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 30}
        }
    },
    
    # Dataset Management
    "list_zfs_datasets": {
        "function": list_zfs_datasets,
        "description": "List ZFS datasets, optionally filtered by pool",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "pool_name": {"type": "string", "description": "Filter by pool name", "optional": True},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 30}
        }
    },
    "get_zfs_dataset_properties": {
        "function": get_zfs_dataset_properties,
        "description": "Get all properties for a specific ZFS dataset",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "dataset_name": {"type": "string", "description": "Dataset name"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 30}
        }
    },
    
    # Snapshot Management
    "list_zfs_snapshots": {
        "function": list_zfs_snapshots,
        "description": "List ZFS snapshots, optionally filtered by dataset",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "dataset_name": {"type": "string", "description": "Filter by dataset name", "optional": True},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 30}
        }
    },
    "create_zfs_snapshot": {
        "function": create_zfs_snapshot,
        "description": "Create a new ZFS snapshot",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "dataset_name": {"type": "string", "description": "Dataset name to snapshot"},
            "snapshot_name": {"type": "string", "description": "Snapshot name"},
            "recursive": {"type": "boolean", "description": "Create recursive snapshot", "default": False},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 60}
        }
    },
    "clone_zfs_snapshot": {
        "function": clone_zfs_snapshot,
        "description": "Clone a ZFS snapshot",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "snapshot_name": {"type": "string", "description": "Snapshot name to clone"},
            "clone_name": {"type": "string", "description": "Name for the cloned dataset"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 60}
        }
    },
    "send_zfs_snapshot": {
        "function": send_zfs_snapshot,
        "description": "Send a ZFS snapshot for replication/backup",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "snapshot_name": {"type": "string", "description": "Snapshot name to send"},
            "destination": {"type": "string", "description": "Destination for snapshot send", "optional": True},
            "incremental": {"type": "boolean", "description": "Use incremental send", "default": False},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 300}
        }
    },
    "receive_zfs_snapshot": {
        "function": receive_zfs_snapshot,
        "description": "Receive a ZFS snapshot stream",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "dataset_name": {"type": "string", "description": "Dataset name for receiving snapshot"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 300}
        }
    },
    "diff_zfs_snapshots": {
        "function": diff_zfs_snapshots,
        "description": "Compare differences between two ZFS snapshots",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "snapshot1": {"type": "string", "description": "First snapshot name"},
            "snapshot2": {"type": "string", "description": "Second snapshot name"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 60}
        }
    },
    
    # Health and Monitoring
    "check_zfs_health": {
        "function": check_zfs_health,
        "description": "Comprehensive ZFS health check",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 60}
        }
    },
    "get_zfs_arc_stats": {
        "function": get_zfs_arc_stats,
        "description": "Get ZFS ARC (Adaptive Replacement Cache) statistics",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 30}
        }
    },
    "monitor_zfs_events": {
        "function": monitor_zfs_events,
        "description": "Monitor ZFS events and error messages",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 30}
        }
    },
    
    # Analysis and Reporting
    "generate_zfs_report": {
        "function": generate_zfs_report,
        "description": "Generate comprehensive ZFS report",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 120}
        }
    },
    "analyze_snapshot_usage": {
        "function": analyze_snapshot_usage,
        "description": "Analyze snapshot space usage and provide cleanup recommendations",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 60}
        }
    },
    "optimize_zfs_settings": {
        "function": optimize_zfs_settings,
        "description": "Analyze ZFS configuration and suggest optimizations",
        "parameters": {
            "device": {"type": "string", "description": "Device hostname"},
            "timeout": {"type": "integer", "description": "SSH timeout in seconds", "default": 60}
        }
    }
}