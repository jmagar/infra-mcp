"""
Container Management API Endpoints

REST API endpoints for managing Docker containers across infrastructure devices
including listing, inspection, log retrieval, and metrics collection.
"""

import logging
from typing import List, Optional
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.mcp.tools.container_management import list_containers as mcp_list_containers

from fastapi import APIRouter, Depends, HTTPException, Query, Path
import json

from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("")
async def list_all_containers(
    current_user=Depends(get_current_user)
):
    """
    This endpoint is deprecated. Use /{hostname} to list containers on a specific device.
    Container management now requires specifying a hostname instead of database lookups.
    """
    raise HTTPException(
        status_code=400, 
        detail="This endpoint is deprecated. Use /{hostname} to list containers on a specific device."
    )

@router.get("/{hostname}")
async def list_device_containers(
    hostname: str = Path(..., description="Device hostname"),
    status: Optional[str] = Query(None, description="Filter by container status"),
    all_containers: bool = Query(True, description="Include stopped containers"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    limit: Optional[int] = Query(None, description="Maximum number of containers to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of containers to skip", ge=0),
    current_user=Depends(get_current_user)
):
    try:
        return await mcp_list_containers(hostname, status, all_containers, timeout, limit, offset)
    except Exception as e:
        logger.error(f"Error listing containers on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list containers on {hostname}: {str(e)}")

@router.get("/{hostname}/{container_name}")
async def get_container_info(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user)
):
    try:
        result = await execute_ssh_command_simple(hostname, f"docker inspect {container_name}", timeout)
        if not result.success:
            raise HTTPException(status_code=404, detail=f"Container {container_name} not found on {hostname}")
        
        import json
        container_data = json.loads(result.stdout)
        return {
            "container": container_data[0] if container_data else {},
            "hostname": hostname,
            "container_name": container_name,
            "timestamp": result.execution_time
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Failed to parse container data from {hostname}")
    except Exception as e:
        logger.error(f"Error getting container info for {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get container info: {str(e)}")

@router.get("/{hostname}/{container_name}/logs")
async def get_container_logs(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    since: Optional[str] = Query(None, description="Show logs since timestamp or duration (e.g., '1h', '30m')"),
    tail: Optional[int] = Query(100, description="Number of lines to show from the end", ge=1, le=10000),
    timestamps: bool = Query(True, description="Include timestamps in log output"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user)
):
    try:
        # Build docker logs command
        cmd = f"docker logs {container_name}"
        if since:
            cmd += f" --since {since}"
        if tail:
            cmd += f" --tail {tail}"
        if timestamps:
            cmd += " --timestamps"
            
        result = await execute_ssh_command_simple(hostname, cmd, timeout)
        if not result.success:
            raise HTTPException(status_code=404, detail=f"Container {container_name} not found on {hostname}")
        
        return {
            "logs": result.stdout,
            "hostname": hostname,
            "container_name": container_name,
            "since": since,
            "tail": tail,
            "timestamps": timestamps,
            "execution_time": result.execution_time
        }
    except Exception as e:
        logger.error(f"Error getting container logs for {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get container logs: {str(e)}")