"""
ZFS Management MCP Tools

MCP tools for comprehensive ZFS pool, dataset, and snapshot management
utilizing the ZFS REST API endpoints for operation execution.
"""

import logging
from typing import Any, cast

import httpx

logger = logging.getLogger(__name__)


# Pool Management Tools
async def list_zfs_pools(device: str, timeout: int = 30) -> dict[str, Any]:
    """List all ZFS pools on a device."""
    logger.info(f"Listing ZFS pools on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/pools", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error listing ZFS pools on {device}: {e}")
        raise Exception(f"Failed to list ZFS pools on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error listing ZFS pools on {device}: {e}")
        raise Exception(f"Failed to list ZFS pools on {device}: {str(e)}") from e


async def get_zfs_pool_status(device: str, pool_name: str, timeout: int = 30) -> dict[str, Any]:
    """Get detailed status for a specific ZFS pool."""
    logger.info(f"Getting ZFS pool status for {pool_name} on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/pools/{pool_name}/status", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting pool status for {pool_name} on {device}: {e}")
        raise Exception(f"Failed to get pool status for {pool_name} on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting pool status for {pool_name} on {device}: {e}")
        raise Exception(f"Failed to get pool status for {pool_name} on {device}: {str(e)}") from e


# Dataset Management Tools
async def list_zfs_datasets(device: str, pool_name: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """List ZFS datasets, optionally filtered by pool."""
    logger.info(f"Listing ZFS datasets on device: {device} (pool: {pool_name or 'all'})")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        if pool_name:
            params["pool_name"] = pool_name

        response = await api_client.client.get(f"/zfs/{device}/datasets", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error listing ZFS datasets on {device}: {e}")
        raise Exception(f"Failed to list ZFS datasets on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error listing ZFS datasets on {device}: {e}")
        raise Exception(f"Failed to list ZFS datasets on {device}: {str(e)}") from e


async def get_zfs_dataset_properties(device: str, dataset_name: str, timeout: int = 30) -> dict[str, Any]:
    """Get all properties for a specific ZFS dataset."""
    logger.info(f"Getting properties for dataset {dataset_name} on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/datasets/{dataset_name}/properties", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting dataset properties for {dataset_name} on {device}: {e}")
        raise Exception(f"Failed to get dataset properties for {dataset_name} on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting dataset properties for {dataset_name} on {device}: {e}")
        raise Exception(f"Failed to get dataset properties for {dataset_name} on {device}: {str(e)}") from e


# Snapshot Management Tools
async def list_zfs_snapshots(device: str, dataset_name: str | None = None, timeout: int = 30) -> dict[str, Any]:
    """List ZFS snapshots, optionally filtered by dataset."""
    logger.info(f"Listing ZFS snapshots on device: {device} (dataset: {dataset_name or 'all'})")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        if dataset_name:
            params["dataset_name"] = dataset_name

        response = await api_client.client.get(f"/zfs/{device}/snapshots", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error listing ZFS snapshots on {device}: {e}")
        raise Exception(f"Failed to list ZFS snapshots on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error listing ZFS snapshots on {device}: {e}")
        raise Exception(f"Failed to list ZFS snapshots on {device}: {str(e)}") from e


async def create_zfs_snapshot(
    device: str,
    dataset_name: str,
    snapshot_name: str,
    recursive: bool = False,
    timeout: int = 60
) -> dict[str, Any]:
    """Create a new ZFS snapshot."""
    logger.info(f"Creating ZFS snapshot {snapshot_name} for dataset {dataset_name} on device: {device} (recursive: {recursive})")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        payload = {
            "dataset_name": dataset_name,
            "snapshot_name": snapshot_name,
            "recursive": recursive
        }
        response = await api_client.client.post(f"/zfs/{device}/snapshots", json=payload, params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error creating snapshot {snapshot_name} on {device}: {e}")
        raise Exception(f"Failed to create snapshot {snapshot_name} on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error creating snapshot {snapshot_name} on {device}: {e}")
        raise Exception(f"Failed to create snapshot {snapshot_name} on {device}: {str(e)}") from e


async def clone_zfs_snapshot(
    device: str,
    snapshot_name: str,
    clone_name: str,
    timeout: int = 60
) -> dict[str, Any]:
    """Clone a ZFS snapshot."""
    logger.info(f"Cloning ZFS snapshot {snapshot_name} to {clone_name} on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        payload = {"clone_name": clone_name}
        response = await api_client.client.post(f"/zfs/{device}/snapshots/{snapshot_name}/clone", json=payload, params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error cloning snapshot {snapshot_name} on {device}: {e}")
        raise Exception(f"Failed to clone snapshot {snapshot_name} on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error cloning snapshot {snapshot_name} on {device}: {e}")
        raise Exception(f"Failed to clone snapshot {snapshot_name} on {device}: {str(e)}") from e


async def send_zfs_snapshot(
    device: str,
    snapshot_name: str,
    destination: str | None = None,
    incremental: bool = False,
    timeout: int = 300
) -> dict[str, Any]:
    """Send a ZFS snapshot for replication/backup."""
    logger.info(f"Sending ZFS snapshot {snapshot_name} from device: {device} (destination: {destination}, incremental: {incremental})")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        payload = {
            "destination": destination,
            "incremental": incremental
        }
        response = await api_client.client.post(f"/zfs/{device}/snapshots/{snapshot_name}/send", json=payload, params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error sending snapshot {snapshot_name} from {device}: {e}")
        raise Exception(f"Failed to send snapshot {snapshot_name} from {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error sending snapshot {snapshot_name} from {device}: {e}")
        raise Exception(f"Failed to send snapshot {snapshot_name} from {device}: {str(e)}") from e


async def receive_zfs_snapshot(
    device: str,
    dataset_name: str,
    timeout: int = 300
) -> dict[str, Any]:
    """Receive a ZFS snapshot stream."""
    logger.info(f"Receiving ZFS snapshot stream for dataset {dataset_name} on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        payload = {"dataset_name": dataset_name}
        response = await api_client.client.post(f"/zfs/{device}/receive", json=payload, params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error receiving snapshot for {dataset_name} on {device}: {e}")
        raise Exception(f"Failed to receive snapshot for {dataset_name} on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error receiving snapshot for {dataset_name} on {device}: {e}")
        raise Exception(f"Failed to receive snapshot for {dataset_name} on {device}: {str(e)}") from e


async def diff_zfs_snapshots(
    device: str,
    snapshot1: str,
    snapshot2: str,
    timeout: int = 60
) -> dict[str, Any]:
    """Compare differences between two ZFS snapshots."""
    logger.info(f"Comparing ZFS snapshots {snapshot1} and {snapshot2} on device: {device}")
    try:
        from ..server import api_client
        params = {"snapshot2": snapshot2, "timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/snapshots/{snapshot1}/diff", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error diffing snapshots {snapshot1} and {snapshot2} on {device}: {e}")
        raise Exception(f"Failed to diff snapshots {snapshot1} and {snapshot2} on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error diffing snapshots {snapshot1} and {snapshot2} on {device}: {e}")
        raise Exception(f"Failed to diff snapshots {snapshot1} and {snapshot2} on {device}: {str(e)}") from e


# Health and Monitoring Tools
async def check_zfs_health(device: str, timeout: int = 60) -> dict[str, Any]:
    """Comprehensive ZFS health check."""
    logger.info(f"Checking ZFS health on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/health", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error checking ZFS health on {device}: {e}")
        raise Exception(f"Failed to check ZFS health on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error checking ZFS health on {device}: {e}")
        raise Exception(f"Failed to check ZFS health on {device}: {str(e)}") from e


async def get_zfs_arc_stats(device: str, timeout: int = 30) -> dict[str, Any]:
    """Get ZFS ARC (Adaptive Replacement Cache) statistics."""
    logger.info(f"Getting ZFS ARC stats on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/arc-stats", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting ARC stats on {device}: {e}")
        raise Exception(f"Failed to get ARC stats on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting ARC stats on {device}: {e}")
        raise Exception(f"Failed to get ARC stats on {device}: {str(e)}") from e


async def monitor_zfs_events(device: str, timeout: int = 30) -> dict[str, Any]:
    """Monitor ZFS events and error messages."""
    logger.info(f"Monitoring ZFS events on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/events", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error monitoring ZFS events on {device}: {e}")
        raise Exception(f"Failed to monitor ZFS events on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error monitoring ZFS events on {device}: {e}")
        raise Exception(f"Failed to monitor ZFS events on {device}: {str(e)}") from e


# Analysis and Reporting Tools
async def generate_zfs_report(device: str, timeout: int = 120) -> dict[str, Any]:
    """Generate comprehensive ZFS report."""
    logger.info(f"Generating ZFS report for device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/report", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error generating ZFS report on {device}: {e}")
        raise Exception(f"Failed to generate ZFS report on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error generating ZFS report on {device}: {e}")
        raise Exception(f"Failed to generate ZFS report on {device}: {str(e)}") from e


async def analyze_snapshot_usage(device: str, timeout: int = 60) -> dict[str, Any]:
    """Analyze snapshot space usage and provide cleanup recommendations."""
    logger.info(f"Analyzing snapshot usage on device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/snapshots/usage", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error analyzing snapshot usage on {device}: {e}")
        raise Exception(f"Failed to analyze snapshot usage on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error analyzing snapshot usage on {device}: {e}")
        raise Exception(f"Failed to analyze snapshot usage on {device}: {str(e)}") from e


async def optimize_zfs_settings(device: str, timeout: int = 60) -> dict[str, Any]:
    """Analyze ZFS configuration and suggest optimizations."""
    logger.info(f"Optimizing ZFS settings for device: {device}")
    try:
        from ..server import api_client
        params = {"timeout": str(timeout)}
        response = await api_client.client.get(f"/zfs/{device}/optimize", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except httpx.HTTPError as e:
        logger.error(f"HTTP error optimizing ZFS settings on {device}: {e}")
        raise Exception(f"Failed to optimize ZFS settings on {device}: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error optimizing ZFS settings on {device}: {e}")
        raise Exception(f"Failed to optimize ZFS settings on {device}: {str(e)}") from e


# ZFS Tool Registration
ZFS_TOOLS: dict[str, dict[str, Any]] = {
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