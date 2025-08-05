"""
Container Management API Endpoints

REST API endpoints for managing Docker containers across infrastructure devices
including listing, inspection, log retrieval, and metrics collection.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.core.logging_config import (
    set_correlation_id,
    set_operation_context,
    set_device_context,
)

from fastapi import APIRouter, Depends, HTTPException, Query, Path
import json

from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_unified_service():
    """Dependency to get UnifiedDataCollectionService instance"""
    return await get_unified_data_collection_service()


@router.get("/{hostname}")
async def list_device_containers(
    hostname: str = Path(..., description="Device hostname"),
    status: Optional[str] = Query(None, description="Filter by container status"),
    all_containers: bool = Query(True, description="Include stopped containers"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    limit: Optional[int] = Query(
        None, description="Maximum number of containers to return", ge=1, le=1000
    ),
    offset: int = Query(0, description="Number of containers to skip", ge=0),
    current_user=Depends(get_current_user),
):
    try:
        return await mcp_list_containers(hostname, status, all_containers, timeout, limit, offset)
    except Exception as e:
        logger.error(f"Error listing containers on {hostname}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list containers on {hostname}: {str(e)}"
        ) from e


@router.get("/{hostname}/{container_name}")
async def get_container_info(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    try:
        result = await execute_ssh_command_simple(
            hostname, f"docker inspect {container_name}", timeout
        )
        if not result.success:
            raise HTTPException(
                status_code=404, detail=f"Container {container_name} not found on {hostname}"
            )

        container_data = json.loads(result.stdout)
        return {
            "container": container_data[0] if container_data else {},
            "hostname": hostname,
            "container_name": container_name,
            "timestamp": result.execution_time,
        }
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse container data from {hostname}"
        ) from e
    except Exception as e:
        logger.error(f"Error getting container info for {container_name} on {hostname}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get container info: {str(e)}"
        ) from e


@router.get("/{hostname}/{container_name}/logs")
async def get_container_logs(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    since: Optional[str] = Query(
        None, description="Show logs since timestamp or duration (e.g., '1h', '30m')"
    ),
    tail: Optional[int] = Query(
        100, description="Number of lines to show from the end", ge=1, le=10000
    ),
    timestamps: bool = Query(True, description="Include timestamps in log output"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
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
            raise HTTPException(
                status_code=404, detail=f"Container {container_name} not found on {hostname}"
            )

        return {
            "logs": result.stdout,
            "hostname": hostname,
            "container_name": container_name,
            "since": since,
            "tail": tail,
            "timestamps": timestamps,
            "execution_time": result.execution_time,
        }
    except Exception as e:
        logger.error(f"Error getting container logs for {container_name} on {hostname}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get container logs: {str(e)}"
        ) from e


@router.post("/{hostname}/{container_name}/start")
async def start_container(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Start a Docker container"""
    try:
        result = await execute_ssh_command_simple(
            hostname, f"docker start {container_name}", timeout
        )
        if not result.success:
            raise HTTPException(
                status_code=404, detail=f"Container {container_name} not found on {hostname}"
            )

        return {
            "action": "start",
            "container_name": container_name,
            "hostname": hostname,
            "success": True,
            "output": result.stdout,
            "execution_time": result.execution_time,
        }
    except Exception as e:
        logger.error(f"Error starting container {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}") from e


@router.post("/{hostname}/{container_name}/stop")
async def stop_container(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    timeout: int = Query(10, description="Timeout for graceful stop in seconds"),
    force: bool = Query(False, description="Force stop the container"),
    ssh_timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Stop a Docker container"""
    try:
        cmd = "docker stop"
        if timeout != 10:
            cmd += f" --time {timeout}"
        if force:
            cmd = "docker kill"
        cmd += f" {container_name}"

        result = await execute_ssh_command_simple(hostname, cmd, ssh_timeout)
        if not result.success:
            raise HTTPException(
                status_code=404, detail=f"Container {container_name} not found on {hostname}"
            )

        return {
            "action": "stop" if not force else "kill",
            "container_name": container_name,
            "hostname": hostname,
            "success": True,
            "output": result.stdout,
            "execution_time": result.execution_time,
        }
    except Exception as e:
        logger.error(f"Error stopping container {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop container: {str(e)}") from e


@router.post("/{hostname}/{container_name}/restart")
async def restart_container(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    timeout: int = Query(10, description="Timeout for restart in seconds"),
    ssh_timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Restart a Docker container"""
    try:
        cmd = "docker restart"
        if timeout != 10:
            cmd += f" --time {timeout}"
        cmd += f" {container_name}"

        result = await execute_ssh_command_simple(hostname, cmd, ssh_timeout)
        if not result.success:
            raise HTTPException(
                status_code=404, detail=f"Container {container_name} not found on {hostname}"
            )

        return {
            "action": "restart",
            "container_name": container_name,
            "hostname": hostname,
            "success": True,
            "output": result.stdout,
            "execution_time": result.execution_time,
        }
    except Exception as e:
        logger.error(f"Error restarting container {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restart container: {str(e)}") from e


@router.delete("/{hostname}/{container_name}")
async def remove_container(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    force: bool = Query(False, description="Force remove the container"),
    remove_volumes: bool = Query(False, description="Remove associated volumes"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Remove a Docker container"""
    try:
        cmd = "docker rm"
        if force:
            cmd += " --force"
        if remove_volumes:
            cmd += " --volumes"
        cmd += f" {container_name}"

        result = await execute_ssh_command_simple(hostname, cmd, timeout)
        if not result.success:
            raise HTTPException(
                status_code=404, detail=f"Container {container_name} not found on {hostname}"
            )

        return {
            "action": "remove",
            "container_name": container_name,
            "hostname": hostname,
            "success": True,
            "force": force,
            "remove_volumes": remove_volumes,
            "output": result.stdout,
            "execution_time": result.execution_time,
        }
    except Exception as e:
        logger.error(f"Error removing container {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove container: {str(e)}") from e


@router.get("/{hostname}/{container_name}/stats")
async def get_container_stats(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Get real-time container resource usage statistics"""
    try:
        cmd = f"docker stats {container_name} --no-stream --format '{{{{.Container}}}}|{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}|{{{{.MemPerc}}}}|{{{{.NetIO}}}}|{{{{.BlockIO}}}}|{{{{.PIDs}}}}'"

        result = await execute_ssh_command_simple(hostname, cmd, timeout)
        if not result.success:
            raise HTTPException(
                status_code=404, detail=f"Container {container_name} not found on {hostname}"
            )

        # Parse the pipe-delimited stats output
        output = result.stdout.strip()
        if not output:
            raise HTTPException(status_code=500, detail="Empty container stats output")
        # Split on pipe delimiter
        parts = output.split("|")
        if len(parts) >= 7:
            return {
                "container_name": container_name,
                "hostname": hostname,
                "stats": {
                    "cpu_percent": parts[1].strip(),
                    "memory_usage": parts[2].strip(),
                    "memory_percent": parts[3].strip(),
                    "network_io": parts[4].strip(),
                    "block_io": parts[5].strip(),
                    "pids": parts[6].strip(),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_time": result.execution_time,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to parse container stats format - got {len(parts)} parts: {parts}",
            )

    except Exception as e:
        logger.error(f"Error getting container stats for {container_name} on {hostname}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get container stats: {str(e)}"
        ) from e


@router.post("/{hostname}/{container_name}/exec")
async def execute_in_container(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    command: str = Query(..., description="Command to execute"),
    interactive: bool = Query(False, description="Allocate a pseudo-TTY"),
    user: Optional[str] = Query(None, description="Username to execute as"),
    workdir: Optional[str] = Query(None, description="Working directory"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Execute a command inside a Docker container"""
    try:
        cmd = "docker exec"
        if interactive:
            cmd += " -it"
        if user:
            cmd += f" --user {user}"
        if workdir:
            cmd += f" --workdir {workdir}"
        cmd += f" {container_name} {command}"

        result = await execute_ssh_command_simple(hostname, cmd, timeout)

        # Check if the SSH connection or Docker exec command failed
        if not result.success:
            # Log the error for debugging
            logger.error(f"Docker exec command failed on {hostname}: {result.stderr}")

            # Determine appropriate HTTP status based on error type
            if result.return_code == 125:  # Docker container not found or not running
                raise HTTPException(
                    status_code=404,
                    detail=f"Container '{container_name}' not found or not running on {hostname}",
                )
            elif result.return_code == 126:  # Command not executable
                raise HTTPException(
                    status_code=400,
                    detail=f"Command not executable in container '{container_name}': {command}",
                )
            elif result.return_code == 127:  # Command not found
                raise HTTPException(
                    status_code=400,
                    detail=f"Command not found in container '{container_name}': {command}",
                )
            else:
                # Generic failure - include stderr for debugging
                error_detail = f"Command execution failed in container '{container_name}'"
                if result.stderr:
                    error_detail += f": {result.stderr}"
                raise HTTPException(status_code=500, detail=error_detail)

        return {
            "action": "exec",
            "container_name": container_name,
            "hostname": hostname,
            "command": command,
            "success": True,
            "exit_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": result.execution_time,
        }
    except Exception as e:
        logger.error(f"Error executing command in container {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute command: {str(e)}") from e
