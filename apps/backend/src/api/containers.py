"""
Container Management API Endpoints

REST API endpoints for managing Docker containers across infrastructure devices
including listing, inspection, log retrieval, and metrics collection.
"""

from datetime import UTC, datetime
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from apps.backend.src.api.common import get_current_user
from apps.backend.src.core.database import get_async_session_factory
from apps.backend.src.core.exceptions import DataCollectionError
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.utils.database_utils import get_database_helper
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple, get_ssh_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_all_containers(
    status: str | None = Query(None, description="Filter by container status"),
    device_hostname: str | None = Query(None, description="Filter by device hostname"),  
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    current_user: Any = Depends(get_current_user)
):
    """
    List all containers from all devices.
    
    Returns aggregated container data from the database, updated by background polling.
    This provides fast responses while ensuring relatively fresh data.
    """
    try:
        from sqlalchemy import text
        
        session_factory = get_async_session_factory()
        
        # Build query dynamically to avoid NULL parameter issues
        base_query = """
        WITH latest_snapshots AS (
            SELECT DISTINCT ON (cs.device_id, cs.container_name) 
                d.hostname as device_hostname,
                cs.container_name,
                cs.container_id,
                cs.image,
                cs.status,
                cs.running,
                cs.cpu_usage_percent,
                cs.memory_usage_bytes,
                cs.memory_limit_bytes,
                cs.ports,
                cs.labels,
                cs.created_at,
                cs.time
            FROM container_snapshots cs
            JOIN devices d ON cs.device_id = d.id
            WHERE cs.time > NOW() - INTERVAL '2 hours'  -- Recent data
            ORDER BY cs.device_id, cs.container_name, cs.time DESC
        )
        SELECT 
            device_hostname,
            container_name,
            container_id,
            image,
            status,
            running,
            cpu_usage_percent,
            memory_usage_bytes,
            memory_limit_bytes,
            ports,
            labels,
            created_at,
            time
        FROM latest_snapshots
        WHERE 1=1"""
        
        params = {}
        
        if status:
            base_query += " AND LOWER(status) = LOWER(:status_param)"
            params['status_param'] = status
            
        if device_hostname:
            base_query += " AND device_hostname = :device_param"
            params['device_param'] = device_hostname
            
        base_query += " ORDER BY device_hostname, container_name LIMIT :limit_param OFFSET :offset_param"
        params['limit_param'] = page_size
        params['offset_param'] = (page - 1) * page_size
        
        query = text(base_query)
        
        # Build count query
        count_base = """
        WITH latest_snapshots AS (
            SELECT DISTINCT ON (cs.device_id, cs.container_name) 
                d.hostname as device_hostname,
                cs.container_name,
                cs.status
            FROM container_snapshots cs
            JOIN devices d ON cs.device_id = d.id
            WHERE cs.time > NOW() - INTERVAL '2 hours'  -- Recent data
            ORDER BY cs.device_id, cs.container_name, cs.time DESC
        )
        SELECT COUNT(*) as count
        FROM latest_snapshots
        WHERE 1=1"""
        
        count_params = {}
        
        if status:
            count_base += " AND LOWER(status) = LOWER(:status_param)"
            count_params['status_param'] = status
            
        if device_hostname:
            count_base += " AND device_hostname = :device_param"
            count_params['device_param'] = device_hostname
            
        count_query = text(count_base)
        
        async with session_factory() as session:
            # Execute data query
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            # Execute count query
            count_result = await session.execute(count_query, count_params)
            total_count = count_result.scalar()
        
        # Transform the data into the expected format
        containers = []
        for row in rows:
            # Transform actual table columns to expected format
            # Use _mapping to access by column name
            row_dict = row._mapping
            container = {
                "device_hostname": row_dict["device_hostname"],
                "name": row_dict["container_name"],
                "id": row_dict["container_id"],
                "image": row_dict["image"],
                "command": "",  # Not available in snapshots
                "created_at": row_dict["created_at"].isoformat() if row_dict["created_at"] else "",
                "status": row_dict["status"].lower() if row_dict["status"] else "unknown",
                "state": "running" if (row_dict["status"] and "up " in row_dict["status"].lower()) else "stopped",
                "ports": row_dict["ports"] if row_dict["ports"] else [],
                "labels": row_dict["labels"] if row_dict["labels"] else {},
                "cpu_usage_percent": row_dict["cpu_usage_percent"],
                "memory_usage_bytes": row_dict["memory_usage_bytes"], 
                "memory_limit_bytes": row_dict["memory_limit_bytes"],
                "last_updated": row_dict["time"].isoformat() if row_dict["time"] else "",
            }
            containers.append(container)
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "items": containers,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }
        
    except Exception as e:
        logger.error(f"Failed to list all containers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve containers: {str(e)}")


def _parse_container_ports(ports_str: str) -> list[dict]:
    """Parse Docker container ports string into structured format."""
    if not ports_str or ports_str == "":
        return []
    
    ports = []
    # Example ports_str: "0.0.0.0:8080->80/tcp, 0.0.0.0:8443->443/tcp"
    for port_mapping in ports_str.split(", "):
        if "->" in port_mapping:
            try:
                host_part, container_part = port_mapping.split("->")
                if ":" in host_part:
                    host_ip, host_port = host_part.rsplit(":", 1)
                    host_port = int(host_port)
                else:
                    host_ip = "0.0.0.0"
                    host_port = int(host_part)
                
                if "/" in container_part:
                    container_port, protocol = container_part.split("/")
                    container_port = int(container_port)
                else:
                    container_port = int(container_part)
                    protocol = "tcp"
                
                ports.append({
                    "host_ip": host_ip,
                    "host_port": host_port,
                    "container_port": container_port,
                    "protocol": protocol
                })
            except (ValueError, IndexError):
                logger.warning(f"Failed to parse port mapping: {port_mapping}")
    
    return ports


class ContainerOperations:
    """Utility class for container operations to eliminate duplicate collection methods."""
    
    @staticmethod
    async def collect_container_list(
        hostname: str, 
        timeout: int,
        status: str | None = None,
        all_containers: bool = True
    ) -> dict[str, Any]:
        """Collect container list with filters."""
        cmd_parts = ["docker", "ps"]
        if all_containers:
            cmd_parts.append("-a")
        cmd_parts.extend(["--format", "'{{json .}}'"])
        if status:
            cmd_parts.extend(["--filter", f"status={status}"])
        cmd = " ".join(cmd_parts)

        result = await execute_ssh_command_simple(hostname, cmd, timeout)
        if not result.success:
            raise DataCollectionError(
                message=f"Failed to list containers: {result.stderr}",
                operation="container_listing"
            )

        containers = []
        if result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        container_data = json.loads(line)
                        containers.append(container_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse container JSON: {line}")

        return {
            "containers": containers,
            "hostname": hostname,
            "filters": {"status": status, "all_containers": all_containers},
            "collection_time": datetime.now(UTC).isoformat(),
            "status": "success"
        }

    @staticmethod
    async def collect_container_info(hostname: str, container_name: str, timeout: int) -> dict[str, Any]:
        """Collect detailed container information."""
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
        }

    @staticmethod
    async def collect_container_logs(
        hostname: str, 
        container_name: str, 
        timeout: int,
        since: str | None = None,
        tail: int | None = None,
        timestamps: bool = False
    ) -> dict[str, Any]:
        """Collect container logs with options."""
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
            "options": {"since": since, "tail": tail, "timestamps": timestamps},
            "collection_time": datetime.now(UTC).isoformat()
        }

    @staticmethod
    async def collect_container_stats(hostname: str, container_name: str, timeout: int) -> dict[str, Any]:
        """Collect container resource usage statistics."""
        cmd = f"docker stats {container_name} --no-stream --format '{{{{.Container}}}}|{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}|{{{{.MemPerc}}}}|{{{{.NetIO}}}}|{{{{.BlockIO}}}}|{{{{.PIDs}}}}'"
        result = await execute_ssh_command_simple(hostname, cmd, timeout)
        if not result.success:
            raise HTTPException(
                status_code=404, detail=f"Container {container_name} not found on {hostname}"
            )
            
        output = result.stdout.strip()
        if not output:
            raise HTTPException(status_code=500, detail="Empty container stats output")
            
        parts = output.split('|')
        if len(parts) >= 7:
            return {
                "container_id": parts[0],
                "cpu_percent": parts[1],
                "memory_usage": parts[2],
                "memory_percent": parts[3],
                "network_io": parts[4],
                "block_io": parts[5],
                "pids": parts[6],
                "hostname": hostname,
                "container_name": container_name,
                "collection_time": datetime.now(UTC).isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Invalid container stats format")


@router.get("/{hostname}")
async def list_device_containers(
    hostname: str = Path(..., description="Device hostname"),
    status: str | None = Query(None, description="Filter by container status"),
    all_containers: bool = Query(True, description="Include stopped containers"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    limit: int | None = Query(
        None, description="Maximum number of containers to return", ge=1, le=1000
    ),
    offset: int = Query(0, description="Number of containers to skip", ge=0),
    live: bool = Query(False, description="Force fresh data collection"),
    current_user: Any = Depends(get_current_user),
) -> dict:
    try:
        # Get unified service and database helper
        session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=session_factory,
            ssh_client=ssh_client
        )
        db_helper = get_database_helper(session_factory)
        device_id = await db_helper.get_device_id_by_hostname(hostname)

        # Define collection method using utility class
        async def collect_container_list() -> dict[str, Any]:
            result = await ContainerOperations.collect_container_list(
                hostname=hostname,
                timeout=timeout,
                status=status,
                all_containers=all_containers
            )
            # Add pagination info
            result["pagination"] = {"limit": limit, "offset": offset}
            return result

        # Use unified service to collect data
        result = await unified_service.collect_and_store_data(
            data_type="containers",
            device_id=device_id,
            collection_method=collect_container_list,
            force_refresh=live,
            correlation_id=f"containers_{hostname}"
        )

        return result

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
    live: bool = Query(False, description="Force fresh data collection"),
    current_user: Any = Depends(get_current_user),
) -> dict:
    try:
        # Get unified service and database helper
        session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=session_factory,
            ssh_client=ssh_client
        )
        db_helper = get_database_helper(session_factory)
        device_id = await db_helper.get_device_id_by_hostname(hostname)

        # Define collection method using utility class
        async def collect_container_info() -> dict[str, Any]:
            return await ContainerOperations.collect_container_info(
                hostname=hostname,
                container_name=container_name,
                timeout=timeout
            )

        # Use unified service to collect data
        result = await unified_service.collect_and_store_data(
            data_type="container_info",
            device_id=device_id,
            collection_method=collect_container_info,
            force_refresh=live,
            correlation_id=f"container_info_{hostname}_{container_name}"
        )

        return result

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse container data from {hostname}"
        ) from e
    except Exception as e:
        logger.error(f"Error getting container info for {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get container info: {str(e)}") from e


@router.get("/{hostname}/{container_name}/logs")
async def get_container_logs(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    since: str | None = Query(
        None, description="Show logs since timestamp or duration (e.g., '1h', '30m')"
    ),
    tail: int | None = Query(
        100, description="Number of lines to show from the end", ge=1, le=10000
    ),
    timestamps: bool = Query(True, description="Include timestamps in log output"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    live: bool = Query(False, description="Force fresh data collection"),
    current_user: Any = Depends(get_current_user),
) -> dict:
    try:
        # Get unified service and database helper
        session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=session_factory,
            ssh_client=ssh_client
        )
        db_helper = get_database_helper(session_factory)
        device_id = await db_helper.get_device_id_by_hostname(hostname)

        # Define collection method using utility class
        async def collect_container_logs() -> dict[str, Any]:
            return await ContainerOperations.collect_container_logs(
                hostname=hostname,
                container_name=container_name,
                timeout=timeout,
                since=since,
                tail=tail,
                timestamps=timestamps
            )

        # Use unified service to collect data
        # Container logs change frequently so should have shorter cache TTL
        result = await unified_service.collect_and_store_data(
            data_type="container_logs",
            device_id=device_id,
            collection_method=collect_container_logs,
            force_refresh=live,
            correlation_id=f"container_logs_{hostname}_{container_name}"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting container logs for {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get container logs: {str(e)}") from e


@router.post("/{hostname}/{container_name}/start")
async def start_container(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Start a Docker container"""
    try:
        result = await execute_ssh_command_simple(hostname, f"docker start {container_name}", timeout)
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
    current_user: Any = Depends(get_current_user),
) -> dict:
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
    current_user: Any = Depends(get_current_user),
) -> dict:
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
    current_user: Any = Depends(get_current_user),
) -> dict:
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
    live: bool = Query(True, description="Force fresh data collection (stats are real-time by default)"),
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Get real-time container resource usage statistics"""
    try:
        # Get unified service and database helper
        session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=session_factory,
            ssh_client=ssh_client
        )
        db_helper = get_database_helper(session_factory)
        device_id = await db_helper.get_device_id_by_hostname(hostname)

        # Define collection method using utility class
        async def collect_container_stats() -> dict[str, Any]:
            result = await ContainerOperations.collect_container_stats(
                hostname=hostname,
                container_name=container_name,
                timeout=timeout
            )
            # Restructure for API consistency
            return {
                "container_name": container_name,
                "hostname": hostname,
                "stats": {
                    "cpu_percent": result["cpu_percent"],
                    "memory_usage": result["memory_usage"],
                    "memory_percent": result["memory_percent"],
                    "network_io": result["network_io"],
                    "block_io": result["block_io"],
                    "pids": result["pids"],
                },
                "timestamp": result["collection_time"],
            }

        # Use unified service to collect data
        # Container stats are real-time and should always be fresh
        result = await unified_service.collect_and_store_data(
            data_type="container_stats",
            device_id=device_id,
            collection_method=collect_container_stats,
            force_refresh=live,
            correlation_id=f"container_stats_{hostname}_{container_name}"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting container stats for {container_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get container stats: {str(e)}") from e


@router.post("/{hostname}/{container_name}/exec")
async def execute_in_container(
    hostname: str = Path(..., description="Device hostname"),
    container_name: str = Path(..., description="Container name"),
    command: str = Query(..., description="Command to execute"),
    interactive: bool = Query(False, description="Allocate a pseudo-TTY"),
    user: str | None = Query(None, description="Username to execute as"),
    workdir: str | None = Query(None, description="Working directory"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user: Any = Depends(get_current_user),
) -> dict:
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
                    detail=f"Container '{container_name}' not found or not running on {hostname}"
                )
            elif result.return_code == 126:  # Command not executable
                raise HTTPException(
                    status_code=400,
                    detail=f"Command not executable in container '{container_name}': {command}"
                )
            elif result.return_code == 127:  # Command not found
                raise HTTPException(
                    status_code=400,
                    detail=f"Command not found in container '{container_name}': {command}"
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
