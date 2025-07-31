"""
Infrastructure Management API - Device Monitoring Endpoints

This module provides comprehensive monitoring endpoints for real-time infrastructure data
including system metrics, drive health, network statistics, ZFS status, and more.

NOTE: These endpoints are now DEPRECATED in favor of direct MCP tools.
Use the MCP tools directly for hostname-based monitoring without database dependencies.
These endpoints remain for backwards compatibility but will bypass database lookups.
"""

import logging
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path

from apps.backend.src.core.exceptions import SSHCommandError, SSHConnectionError
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/{hostname}/metrics",
    summary="Get system metrics via hostname (DEPRECATED - use MCP tools directly)",
    deprecated=True
)
async def get_device_metrics_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    current_user=Depends(get_current_user)
):
    """
    DEPRECATED: Use MCP get_system_info tool directly.
    This endpoint wraps the MCP tool for backwards compatibility.
    """
    try:
        from apps.backend.src.mcp.tools.system_monitoring import get_system_info
        return await get_system_info(hostname)
    except SSHCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting device metrics for {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device metrics.")

@router.get(
    "/{hostname}/drives",
    summary="Get drive health via hostname (DEPRECATED - use MCP tools directly)",
    deprecated=True
)
async def get_device_drives_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    drive: Optional[str] = Query(None, description="Filter by specific drive name"),
    current_user=Depends(get_current_user)
):
    """
    DEPRECATED: Use MCP get_drive_health tool directly.
    This endpoint wraps the MCP tool for backwards compatibility.
    """
    try:
        from apps.backend.src.mcp.tools.system_monitoring import get_drive_health
        return await get_drive_health(hostname, drive)
    except SSHCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting drive health for {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get drive health.")

@router.get(
    "/{hostname}/logs",
    summary="Get system logs via hostname (DEPRECATED - use MCP tools directly)",
    deprecated=True
)
async def get_device_logs_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    since: Optional[str] = Query("1h", description="Time range (1h, 6h, 24h, 7d)"),
    lines: int = Query(100, ge=1, le=1000, description="Number of log lines to return"),
    current_user=Depends(get_current_user)
):
    """
    DEPRECATED: Use MCP get_system_logs tool directly.
    This endpoint wraps the MCP tool for backwards compatibility.
    """
    try:
        from apps.backend.src.mcp.tools.system_monitoring import get_system_logs
        return await get_system_logs(hostname, service, since, lines)
    except SSHCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting system logs for {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system logs.")

# Add a note for users about the MCP tools
@router.get("/", include_in_schema=False)
async def monitoring_deprecated_notice():
    """
    Monitoring endpoints have been simplified to use hostname-based SSH access.
    
    For optimal performance, use the MCP tools directly:
    - get_system_info(hostname)
    - get_drive_health(hostname, drive)  
    - get_system_logs(hostname, service, since, lines)
    - list_containers(hostname, status, all_containers)
    
    These REST endpoints are kept for backwards compatibility but are deprecated.
    """
    return {
        "message": "Monitoring endpoints deprecated - use MCP tools directly",
        "mcp_tools": [
            "get_system_info",
            "get_drive_health", 
            "get_system_logs",
            "list_containers",
            "get_zfs_status",
            "get_backup_status"
        ],
        "migration_guide": "Replace UUID-based REST calls with hostname-based MCP tool calls"
    }