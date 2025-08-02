"""
Container Management MCP Tools

This module provides MCP tools for managing Docker containers across infrastructure
devices by making HTTP calls to the FastAPI REST endpoints. This eliminates
code duplication and ensures consistency between MCP and REST interfaces.
"""

import logging
import re
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from apps.backend.src.core.config import get_settings
from apps.backend.src.core.exceptions import ContainerError, DeviceNotFoundError, SSHConnectionError
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple, SSHConnectionInfo
from apps.backend.src.utils.docker_client import get_docker_client

logger = logging.getLogger(__name__)
settings = get_settings()


# Removed database-dependent hostname->UUID lookup - using direct SSH instead


# Removed API request helper - using direct SSH instead


async def list_containers(
    device: str,
    status: Optional[str] = None,
    all_containers: bool = True,
    timeout: int = 60,
    limit: Optional[int] = None,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List Docker containers on a specific device using direct SSH.

    This tool connects to the device via SSH using ~/.ssh/config and runs
    'docker ps' to get container information directly.

    Args:
        device: Device hostname (must be configured in ~/.ssh/config)
        status: Optional status filter (running, stopped, etc.)
        all_containers: Include stopped containers (default: True)
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing:
        - containers: List of container information dictionaries
        - device_info: Device connection information
        - summary: Container count summary
        - query_info: Query metadata

    Raises:
        ContainerError: If SSH connection fails or Docker command fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Listing containers on device: {device}")

    try:
        # First get container IDs, then inspect them for full details including complete mount paths
        list_cmd = "docker ps -q"
        if all_containers:
            list_cmd += " -a"

        # Execute command to get container IDs
        id_result = await execute_ssh_command_simple(device, list_cmd, timeout)

        if not id_result.success:
            raise ContainerError(
                message=f"Docker ps command failed on {device}: {id_result.stderr}",
                container_id="",
                hostname=device,
                operation="list_containers",
            )

        container_ids = [cid.strip() for cid in id_result.stdout.strip().split("\n") if cid.strip()]

        if not container_ids:
            logger.info(f"No containers found on {device}")
            return {
                "containers": [],
                "device_info": {
                    "hostname": device,
                    "connection_successful": True,
                    "docker_available": True,
                },
                "summary": {
                    "total_count": 0,
                    "returned_count": 0,
                    "running_count": 0,
                    "stopped_count": 0,
                },
                "pagination": {"offset": offset, "limit": limit, "has_more": False},
                "query_info": {
                    "status_filter": status,
                    "include_stopped": all_containers,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "execution_time_ms": 0,
                },
            }

        # Now inspect all containers for full details
        inspect_cmd = f"docker inspect {' '.join(container_ids)}"
        result = await execute_ssh_command_simple(device, inspect_cmd, timeout)

        if not result.success:
            raise ContainerError(
                message=f"Docker inspect command failed on {device}: {result.stderr}",
                container_id="",
                hostname=device,
                operation="list_containers",
            )

        # Parse docker inspect JSON output (single JSON array of container objects)
        containers = []

        try:
            # docker inspect returns a JSON array of container objects
            container_data_list = json.loads(result.stdout.strip())
            logger.info(f"Parsed {len(container_data_list)} containers from docker inspect")

            for container_data in container_data_list:
                # Extract basic container information
                config = container_data.get("Config", {})
                state = container_data.get("State", {})
                network_settings = container_data.get("NetworkSettings", {})

                # Extract Docker Compose information from labels
                labels = config.get("Labels") or {}
                compose_project = labels.get("com.docker.compose.project", "")
                compose_service = labels.get("com.docker.compose.service", "")
                compose_config_files = labels.get("com.docker.compose.project.config_files", "")

                # Extract volume mounts from Mounts array
                mounts = container_data.get("Mounts", [])
                volume_mounts = []
                if mounts:
                    for mount in mounts:
                        if isinstance(mount, dict):
                            # Use Source (host path) for bind mounts, Name for volumes
                            mount_path = mount.get("Source") or mount.get("Name", "")
                            if mount_path:
                                volume_mounts.append(mount_path)

                # Extract port information
                ports = []
                if network_settings.get("Ports"):
                    for container_port, host_bindings in network_settings["Ports"].items():
                        if host_bindings:
                            for binding in host_bindings:
                                host_ip = binding.get("HostIp", "0.0.0.0")
                                host_port = binding.get("HostPort")
                                if host_port:
                                    ports.append(f"{host_ip}:{host_port}->{container_port}")
                        else:
                            ports.append(container_port)

                # Build status string
                status_str = state.get("Status", "unknown")
                if state.get("Running"):
                    health = state.get("Health", {}).get("Status", "")
                    if health:
                        status_str = f"Up ({health})"
                    else:
                        status_str = "Up"

                # Extract creation and start times for uptime calculation
                created = container_data.get("Created", "")
                started = state.get("StartedAt", "")

                container = {
                    "name": container_data.get("Name", "").lstrip("/"),  # Remove leading slash
                    "image": config.get("Image", "").split("@")[0],  # Remove digest if present
                    "ports": ", ".join(ports) if ports else None,
                    "volumes": volume_mounts if volume_mounts else None,
                    "status": status_str,
                    "running": state.get("Running", False),
                    "compose_path": compose_config_files if compose_config_files else None,
                }

                # Apply status filter if specified
                if status and status.lower() not in container["status"].lower():
                    continue

                containers.append(container)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse docker inspect JSON output: {e}")
            logger.error(f"Raw output: {result.stdout[:500]}...")
            raise ContainerError(
                message=f"Failed to parse container data from {device}",
                container_id="",
                hostname=device,
                operation="list_containers",
            )

        # Calculate summary statistics
        running_count = sum(1 for c in containers if c.get("running", False))
        total_count = len(containers)

        # Apply pagination
        paginated_containers = (
            containers[offset : offset + limit] if limit is not None else containers[offset:]
        )
        returned_count = len(paginated_containers)

        return {
            "containers": paginated_containers,
            "device_info": {
                "hostname": device,
                "connection_successful": True,
                "docker_available": True,
            },
            "summary": {
                "total_count": total_count,
                "returned_count": returned_count,
                "running_count": running_count,  # This is for all containers, not just returned ones
                "stopped_count": total_count - running_count,
            },
            "pagination": {
                "offset": offset,
                "limit": limit,
                "has_more": offset + returned_count < total_count if limit is not None else False,
            },
            "query_info": {
                "status_filter": status,
                "include_stopped": all_containers,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_time_ms": int(result.execution_time * 1000),
            },
        }

    except ContainerError:
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing containers on {device}: {e}")
        raise ContainerError(
            message=f"Failed to list containers: {str(e)}",
            container_id="",
            hostname=device,
            operation="list_containers",
        )


async def get_container_info(device: str, container_name: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Get detailed information about a specific Docker container.

    This tool connects to a device via SSH and retrieves comprehensive
    information about a Docker container using the `docker inspect` command.
    It returns detailed configuration, network settings, mounts, and runtime data.

    Args:
        device: Device hostname or IP address to query
        container_name: Container name or ID to inspect
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing:
        - container: Detailed container information
        - device_info: Device connection information
        - inspection_data: Raw Docker inspect data
        - parsed_config: Parsed configuration details
        - timestamp: Query timestamp

    Raises:
        DeviceNotFoundError: If device cannot be reached
        ContainerError: If container not found or Docker command fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Getting container details for '{container_name}' on device: {device}")

    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(host=device, command_timeout=timeout)

        # Get Docker client
        docker_client = get_docker_client()

        # Execute Docker inspect command
        result = await docker_client.inspect_container(
            connection_info=connection_info, container_id=container_name, timeout=timeout
        )

        # Handle Docker command errors
        if not result.success:
            if result.error_category == "ssh_connection_error":
                raise DeviceNotFoundError(device, "hostname")
            elif result.error_category == "container_not_found":
                raise ContainerError(
                    message=f"Container '{container_name}' not found",
                    container_id=container_name,
                    operation="get_container_info",
                    hostname=device,
                )
            elif result.error_category == "docker_daemon_error":
                raise ContainerError(
                    message="Docker daemon is not running or not accessible",
                    container_id=container_name,
                    operation="get_container_info",
                    hostname=device,
                )
            else:
                docker_client.raise_docker_exception(result, "inspect container")

        # Parse container inspection data
        inspection_data = result.parsed_data
        if (
            not inspection_data
            or not isinstance(inspection_data, list)
            or len(inspection_data) == 0
        ):
            raise ContainerError(
                message=f"No inspection data returned for container '{container_name}'",
                container_id=container_name,
                operation="get_container_info",
                hostname=device,
            )

        # Docker inspect returns an array, get the first (and only) item
        container_data = inspection_data[0]

        # Extract key information from Docker inspect output
        config = container_data.get("Config", {})
        state = container_data.get("State", {})
        network_settings = container_data.get("NetworkSettings", {})
        host_config = container_data.get("HostConfig", {})
        mounts = container_data.get("Mounts", [])

        # Parse timestamps
        def parse_docker_timestamp(timestamp_str):
            """Parse Docker timestamp format"""
            if not timestamp_str or timestamp_str == "0001-01-01T00:00:00Z":
                return None
            try:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except Exception:
                return timestamp_str

        # Build standardized container details
        container_details = {
            "container_id": container_data.get("Id", "")[:12],  # Short ID
            "container_name": container_data.get("Name", "").lstrip("/"),
            "image": config.get("Image", ""),
            "image_id": container_data.get("Image", "")[:12],
            # Status information
            "status": state.get("Status", ""),
            "running": state.get("Running", False),
            "paused": state.get("Paused", False),
            "restarting": state.get("Restarting", False),
            "oom_killed": state.get("OOMKilled", False),
            "dead": state.get("Dead", False),
            "pid": state.get("Pid"),
            "exit_code": state.get("ExitCode"),
            "error": state.get("Error", ""),
            # Timestamps
            "created_at": parse_docker_timestamp(container_data.get("Created")),
            "started_at": parse_docker_timestamp(state.get("StartedAt")),
            "finished_at": parse_docker_timestamp(state.get("FinishedAt")),
            # Configuration
            "command": config.get("Cmd", []),
            "entrypoint": config.get("Entrypoint", []),
            "working_dir": config.get("WorkingDir", ""),
            "user": config.get("User", ""),
            "hostname": config.get("Hostname", ""),
            "domain_name": config.get("Domainname", ""),
            # Environment and labels
            "environment": {},
            "labels": config.get("Labels") or {},
            # Network configuration
            "network_mode": host_config.get("NetworkMode", ""),
            "networks": {},
            "ports": {},
            "exposed_ports": list(config.get("ExposedPorts", {}).keys())
            if config.get("ExposedPorts")
            else [],
            # Volume configuration
            "mounts": [],
            "volumes": config.get("Volumes") or {},
            # Resource limits
            "memory_limit": host_config.get("Memory"),
            "cpu_shares": host_config.get("CpuShares"),
            "cpu_quota": host_config.get("CpuQuota"),
            "cpu_period": host_config.get("CpuPeriod"),
            # Health check
            "health_status": state.get("Health", {}).get("Status") if state.get("Health") else None,
            "health_check": config.get("Healthcheck"),
            # Restart policy
            "restart_policy": host_config.get("RestartPolicy", {}),
            "restart_count": container_data.get("RestartCount", 0),
            # Additional metadata
            "platform": container_data.get("Platform", ""),
            "arch": config.get("Architecture", ""),
            "os": config.get("Os", ""),
        }

        # Parse environment variables
        if config.get("Env"):
            for env_var in config["Env"]:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    container_details["environment"][key] = value

        # Parse network settings
        if network_settings.get("Networks"):
            for network_name, network_info in network_settings["Networks"].items():
                container_details["networks"][network_name] = {
                    "ip_address": network_info.get("IPAddress", ""),
                    "gateway": network_info.get("Gateway", ""),
                    "mac_address": network_info.get("MacAddress", ""),
                    "network_id": network_info.get("NetworkID", "")[:12],
                }

        # Parse port mappings
        if network_settings.get("Ports"):
            for container_port, host_bindings in network_settings["Ports"].items():
                if host_bindings:
                    container_details["ports"][container_port] = [
                        {
                            "host_ip": binding.get("HostIp", ""),
                            "host_port": binding.get("HostPort", ""),
                        }
                        for binding in host_bindings
                    ]
                else:
                    container_details["ports"][container_port] = []

        # Parse mounts
        for mount in mounts:
            container_details["mounts"].append(
                {
                    "type": mount.get("Type", ""),
                    "source": mount.get("Source", ""),
                    "destination": mount.get("Destination", ""),
                    "mode": mount.get("Mode", ""),
                    "rw": mount.get("RW", True),
                    "propagation": mount.get("Propagation", ""),
                }
            )

        # Prepare response
        response = {
            "container": container_details,
            "device_info": {
                "hostname": device,
                "connection_successful": True,
                "docker_available": True,
            },
            "inspection_data": {
                "full_container_id": container_data.get("Id", ""),
                "docker_version": container_data.get("DockerVersion", ""),
                "driver": container_data.get("Driver", ""),
                "size_rw": container_data.get("SizeRw"),
                "size_root_fs": container_data.get("SizeRootFs"),
            },
            "query_info": {
                "container_identifier": container_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_time_ms": int(result.raw_result.execution_time * 1000),
            },
        }

        logger.info(
            f"Retrieved details for container '{container_name}' on {device} "
            f"(Status: {container_details['status']}, Running: {container_details['running']})"
        )

        return response

    except (DeviceNotFoundError, ContainerError, SSHConnectionError):
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error getting container details for '{container_name}' on {device}: {e}"
        )
        raise ContainerError(
            message=f"Failed to get container details: {str(e)}",
            container_id=container_name,
            operation="get_container_info",
            hostname=device,
        )


async def get_container_logs(
    device: str,
    container_name: str,
    since: Optional[str] = None,
    tail: int = 100,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Get logs from a specific Docker container.

    This tool connects to a device via SSH and retrieves log output from
    a Docker container using the `docker logs` command. It supports various
    filtering options including time-based filtering and line limits.

    Args:
        device: Device hostname or IP address to query
        container_name: Container name or ID to get logs from
        since: Get logs since timestamp/duration (e.g., "2023-01-01T10:00:00Z", "24h", "1h30m")
        tail: Number of lines to retrieve from the end of logs (default: 100)
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing:
        - logs: List of log entries with timestamps and content
        - container_info: Container identification information
        - log_metadata: Log retrieval metadata and statistics
        - query_info: Query parameters and execution information
        - timestamp: Query timestamp

    Raises:
        DeviceNotFoundError: If device cannot be reached
        ContainerError: If container not found or Docker command fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Getting logs for container '{container_name}' on device: {device}")

    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(host=device, command_timeout=timeout)

        # Get Docker client
        docker_client = get_docker_client()

        # Execute Docker logs command
        result = await docker_client.get_container_logs(
            connection_info=connection_info,
            container_id=container_name,
            lines=tail,
            since=since,
            timeout=timeout,
        )

        # Handle Docker command errors
        if not result.success:
            if result.error_category == "ssh_connection_error":
                raise DeviceNotFoundError(device, "hostname")
            elif result.error_category == "container_not_found":
                raise ContainerError(
                    message=f"Container '{container_name}' not found",
                    container_id=container_name,
                    operation="get_container_logs",
                    hostname=device,
                )
            elif result.error_category == "docker_daemon_error":
                raise ContainerError(
                    message="Docker daemon is not running or not accessible",
                    container_id=container_name,
                    operation="get_container_logs",
                    hostname=device,
                )
            else:
                docker_client.raise_docker_exception(result, "get container logs")

        # Parse log output
        raw_logs = result.raw_result.stdout or ""

        # Process log lines
        log_entries = []
        log_lines = raw_logs.strip().split("\n") if raw_logs.strip() else []

        for line_number, line_content in enumerate(log_lines, 1):
            if not line_content.strip():
                continue

            # Parse Docker log format (may include timestamps)
            log_entry = {
                "line_number": line_number,
                "content": line_content,
                "timestamp": None,
                "log_level": None,
                "raw_line": line_content,
            }

            # Try to extract timestamp from Docker log format
            # Docker logs can have format: "2023-01-01T10:00:00.000000000Z message"
            timestamp_match = re.match(
                r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+(.*)$", line_content
            )

            if timestamp_match:
                try:
                    timestamp_str, message_content = timestamp_match.groups()
                    # Parse timestamp
                    parsed_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    log_entry["timestamp"] = parsed_timestamp.isoformat()
                    log_entry["content"] = message_content.strip()
                except Exception as e:
                    logger.debug(f"Failed to parse timestamp from log line: {e}")
                    # Keep original content if timestamp parsing fails
                    pass

            # Try to detect log level from content
            content_lower = log_entry["content"].lower()
            if any(level in content_lower for level in ["error", "err", "fatal"]):
                log_entry["log_level"] = "error"
            elif any(level in content_lower for level in ["warn", "warning"]):
                log_entry["log_level"] = "warning"
            elif any(level in content_lower for level in ["info", "information"]):
                log_entry["log_level"] = "info"
            elif any(level in content_lower for level in ["debug", "trace"]):
                log_entry["log_level"] = "debug"
            else:
                log_entry["log_level"] = "unknown"

            log_entries.append(log_entry)

        # Calculate log statistics
        total_lines = len(log_entries)
        log_levels = {}
        for entry in log_entries:
            level = entry.get("log_level", "unknown")
            log_levels[level] = log_levels.get(level, 0) + 1

        # Determine time range of logs
        timestamped_entries = [e for e in log_entries if e.get("timestamp")]
        first_timestamp = None
        last_timestamp = None

        if timestamped_entries:
            try:
                timestamps = [datetime.fromisoformat(e["timestamp"]) for e in timestamped_entries]
                first_timestamp = min(timestamps).isoformat()
                last_timestamp = max(timestamps).isoformat()
            except Exception as e:
                logger.debug(f"Failed to calculate log time range: {e}")

        # Prepare response
        response = {
            "logs": log_entries,
            "container_info": {
                "container_name": container_name,
                "device": device,
                "logs_available": total_lines > 0,
            },
            "log_metadata": {
                "total_lines": total_lines,
                "log_levels": log_levels,
                "has_timestamps": len(timestamped_entries) > 0,
                "timestamped_lines": len(timestamped_entries),
                "first_timestamp": first_timestamp,
                "last_timestamp": last_timestamp,
                "time_range_seconds": None,
            },
            "device_info": {
                "hostname": device,
                "connection_successful": True,
                "docker_available": True,
            },
            "query_info": {
                "container_identifier": container_name,
                "since_filter": since,
                "tail_lines": tail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_time_ms": int(result.raw_result.execution_time * 1000),
            },
        }

        # Calculate time range if we have timestamps
        if first_timestamp and last_timestamp:
            try:
                first_dt = datetime.fromisoformat(first_timestamp)
                last_dt = datetime.fromisoformat(last_timestamp)
                time_range_seconds = (last_dt - first_dt).total_seconds()
                response["log_metadata"]["time_range_seconds"] = time_range_seconds
            except Exception as e:
                logger.debug(f"Failed to calculate time range: {e}")

        logger.info(
            f"Retrieved {total_lines} log lines for container '{container_name}' on {device} "
            f"(levels: {log_levels})"
        )

        return response

    except (DeviceNotFoundError, ContainerError, SSHConnectionError):
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error getting logs for container '{container_name}' on {device}: {e}"
        )
        raise ContainerError(
            message=f"Failed to get container logs: {str(e)}",
            container_id=container_name,
            operation="get_container_logs",
            hostname=device,
        )


async def get_service_dependencies(
    device: str, container_name: str, timeout: int = 60
) -> Dict[str, Any]:
    """
    Analyze and map dependencies between Docker Compose services.

    This tool connects to a device via SSH and analyzes Docker containers
    to identify service dependencies based on shared networks, volumes,
    and Docker Compose labels. It creates a dependency graph showing
    how services are interconnected.

    Args:
        device: Device hostname or IP address to query
        container_name: Container name or ID to analyze dependencies from
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing:
        - service_info: Information about the target service
        - dependencies: Services that this service depends on
        - dependents: Services that depend on this service
        - dependency_graph: Complete service dependency map
        - network_analysis: Network-based dependency details
        - volume_analysis: Volume-based dependency details
        - device_info: Device connection information
        - timestamp: Query timestamp

    Raises:
        DeviceNotFoundError: If device cannot be reached
        ContainerError: If container not found or Docker command fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(
        f"Analyzing service dependencies for container '{container_name}' on device: {device}"
    )

    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(host=device, command_timeout=timeout)

        # Get Docker client
        docker_client = get_docker_client()

        # First, get all containers to build complete dependency map
        containers_result = await docker_client.list_containers(
            connection_info=connection_info, all_containers=True, timeout=timeout
        )

        if not containers_result.success:
            if containers_result.error_category == "ssh_connection_error":
                raise DeviceNotFoundError(device, "hostname")
            elif containers_result.error_category == "docker_daemon_error":
                raise ContainerError(
                    message="Docker daemon is not running or not accessible",
                    container_id=container_name,
                    operation="get_service_dependencies",
                    hostname=device,
                )
            else:
                docker_client.raise_docker_exception(
                    containers_result, "list containers for dependency analysis"
                )

        # Get detailed information for the target container
        target_details_result = await docker_client.inspect_container(
            connection_info=connection_info, container_id=container_name, timeout=timeout
        )

        if not target_details_result.success:
            if target_details_result.error_category == "container_not_found":
                raise ContainerError(
                    message=f"Container '{container_name}' not found",
                    container_id=container_name,
                    operation="get_service_dependencies",
                    hostname=device,
                )
            else:
                docker_client.raise_docker_exception(
                    target_details_result, "inspect target container"
                )

        # Parse target container details
        target_container_data = target_details_result.parsed_data[0]
        target_config = target_container_data.get("Config", {})
        target_labels = target_config.get("Labels") or {}
        target_network_settings = target_container_data.get("NetworkSettings", {})
        target_host_config = target_container_data.get("HostConfig", {})
        target_mounts = target_container_data.get("Mounts", [])

        # Extract service information from target container
        target_service_name = target_labels.get("com.docker.compose.service")
        target_project_name = target_labels.get("com.docker.compose.project")
        target_container_id = target_container_data.get("Id", "")[:12]
        target_container_name_clean = target_container_data.get("Name", "").lstrip("/")

        # Collect all containers and their details for dependency analysis
        containers_data = containers_result.parsed_data or []
        service_containers = {}
        network_mappings = {}
        volume_mappings = {}

        # Analyze all containers to build service mapping
        for container_info in containers_data:
            container_id = container_info.get("ID", "")[:12]
            if not container_id:
                continue

            # Get detailed info for each container (this is expensive but necessary for dependency analysis)
            try:
                detail_result = await docker_client.inspect_container(
                    connection_info=connection_info,
                    container_id=container_id,
                    timeout=30,  # Shorter timeout for bulk operations
                )

                if not detail_result.success:
                    logger.warning(
                        f"Failed to inspect container {container_id}: {detail_result.error_message}"
                    )
                    continue

                container_data = detail_result.parsed_data[0]
                config = container_data.get("Config", {})
                labels = config.get("Labels") or {}
                network_settings = container_data.get("NetworkSettings", {})
                mounts = container_data.get("Mounts", [])

                # Extract service information
                service_name = labels.get("com.docker.compose.service")
                project_name = labels.get("com.docker.compose.project")

                if service_name and project_name:
                    service_key = f"{project_name}_{service_name}"

                    service_containers[service_key] = {
                        "service_name": service_name,
                        "project_name": project_name,
                        "container_id": container_id,
                        "container_name": container_data.get("Name", "").lstrip("/"),
                        "networks": list(network_settings.get("Networks", {}).keys()),
                        "volumes": [
                            mount.get("Source", "")
                            for mount in mounts
                            if mount.get("Type") == "bind" or mount.get("Type") == "volume"
                        ],
                        "volume_mounts": [mount.get("Destination", "") for mount in mounts],
                        "labels": labels,
                        "running": container_data.get("State", {}).get("Running", False),
                    }

                    # Map networks to services
                    for network_name in network_settings.get("Networks", {}).keys():
                        if network_name not in network_mappings:
                            network_mappings[network_name] = []
                        network_mappings[network_name].append(service_key)

                    # Map volumes to services
                    for mount in mounts:
                        if mount.get("Type") in ["bind", "volume"]:
                            volume_source = mount.get("Source", "")
                            if volume_source:
                                if volume_source not in volume_mappings:
                                    volume_mappings[volume_source] = []
                                volume_mappings[volume_source].append(service_key)

            except Exception as e:
                logger.warning(f"Error analyzing container {container_id}: {e}")
                continue

        # Find the target service
        target_service_key = None
        if target_service_name and target_project_name:
            target_service_key = f"{target_project_name}_{target_service_name}"

        if not target_service_key or target_service_key not in service_containers:
            # Handle standalone container (not part of Docker Compose)
            target_service_info = {
                "service_name": None,
                "project_name": None,
                "container_id": target_container_id,
                "container_name": target_container_name_clean,
                "is_compose_service": False,
                "networks": list(target_network_settings.get("Networks", {}).keys()),
                "volumes": [
                    mount.get("Source", "")
                    for mount in target_mounts
                    if mount.get("Type") in ["bind", "volume"]
                ],
                "running": target_container_data.get("State", {}).get("Running", False),
            }

            # For standalone containers, dependencies are based on shared networks/volumes
            dependencies = []
            dependents = []

            # Check network-based dependencies
            target_networks = set(target_network_settings.get("Networks", {}).keys())
            network_deps = []

            for network_name in target_networks:
                if network_name in network_mappings:
                    for service_key in network_mappings[network_name]:
                        if service_key in service_containers:
                            service = service_containers[service_key]
                            network_deps.append(
                                {
                                    "service_name": service["service_name"],
                                    "project_name": service["project_name"],
                                    "container_name": service["container_name"],
                                    "shared_network": network_name,
                                    "relationship": "network_peer",
                                }
                            )

            # Check volume-based dependencies
            target_volumes = set(
                mount.get("Source", "")
                for mount in target_mounts
                if mount.get("Type") in ["bind", "volume"]
            )
            volume_deps = []

            for volume_source in target_volumes:
                if volume_source and volume_source in volume_mappings:
                    for service_key in volume_mappings[volume_source]:
                        if service_key in service_containers:
                            service = service_containers[service_key]
                            volume_deps.append(
                                {
                                    "service_name": service["service_name"],
                                    "project_name": service["project_name"],
                                    "container_name": service["container_name"],
                                    "shared_volume": volume_source,
                                    "relationship": "volume_peer",
                                }
                            )

            response = {
                "service_info": target_service_info,
                "dependencies": [],
                "dependents": [],
                "dependency_graph": {"services": [], "relationships": []},
                "network_analysis": {
                    "target_networks": list(target_networks),
                    "network_dependencies": network_deps,
                    "shared_networks": len(network_deps) > 0,
                },
                "volume_analysis": {
                    "target_volumes": list(target_volumes),
                    "volume_dependencies": volume_deps,
                    "shared_volumes": len(volume_deps) > 0,
                },
                "compose_analysis": {
                    "is_compose_service": False,
                    "total_services_found": len(service_containers),
                    "total_networks": len(network_mappings),
                    "total_volumes": len(volume_mappings),
                },
                "device_info": {
                    "hostname": device,
                    "connection_successful": True,
                    "docker_available": True,
                },
                "query_info": {
                    "container_identifier": container_name,
                    "analysis_type": "standalone_container",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "execution_time_ms": int(
                        (
                            containers_result.raw_result.execution_time
                            + target_details_result.raw_result.execution_time
                        )
                        * 1000
                    ),
                },
            }

            logger.info(
                f"Analyzed standalone container '{container_name}' on {device} (found {len(network_deps)} network peers, {len(volume_deps)} volume peers)"
            )
            return response

        # Analyze Compose service dependencies
        target_service = service_containers[target_service_key]
        target_networks = set(target_service["networks"])
        target_volumes = set(target_service["volumes"])

        # Find dependencies (services this service depends on)
        dependencies = []
        dependents = []

        # Network-based dependencies
        network_dependencies = []
        for network_name in target_networks:
            if network_name in network_mappings:
                for service_key in network_mappings[network_name]:
                    if service_key != target_service_key and service_key in service_containers:
                        service = service_containers[service_key]
                        network_dependencies.append(
                            {
                                "service_name": service["service_name"],
                                "project_name": service["project_name"],
                                "container_name": service["container_name"],
                                "shared_network": network_name,
                                "relationship": "network_dependency",
                            }
                        )

        # Volume-based dependencies
        volume_dependencies = []
        for volume_source in target_volumes:
            if volume_source and volume_source in volume_mappings:
                for service_key in volume_mappings[volume_source]:
                    if service_key != target_service_key and service_key in service_containers:
                        service = service_containers[service_key]
                        volume_dependencies.append(
                            {
                                "service_name": service["service_name"],
                                "project_name": service["project_name"],
                                "container_name": service["container_name"],
                                "shared_volume": volume_source,
                                "relationship": "volume_dependency",
                            }
                        )

        # Build complete dependency graph for the project
        project_services = [
            s for s in service_containers.values() if s["project_name"] == target_project_name
        ]

        dependency_graph = {
            "services": [
                {
                    "service_name": service["service_name"],
                    "container_name": service["container_name"],
                    "container_id": service["container_id"],
                    "running": service["running"],
                    "networks": service["networks"],
                    "volume_count": len(service["volumes"]),
                }
                for service in project_services
            ],
            "relationships": [],
        }

        # Build relationships for the entire project
        for service_key, service in service_containers.items():
            if service["project_name"] != target_project_name:
                continue

            service_networks = set(service["networks"])
            service_volumes = set(service["volumes"])

            # Find network relationships
            for network_name in service_networks:
                if network_name in network_mappings:
                    for related_service_key in network_mappings[network_name]:
                        if (
                            related_service_key != service_key
                            and related_service_key in service_containers
                            and service_containers[related_service_key]["project_name"]
                            == target_project_name
                        ):
                            dependency_graph["relationships"].append(
                                {
                                    "from_service": service["service_name"],
                                    "to_service": service_containers[related_service_key][
                                        "service_name"
                                    ],
                                    "type": "network",
                                    "resource": network_name,
                                }
                            )

            # Find volume relationships
            for volume_source in service_volumes:
                if volume_source and volume_source in volume_mappings:
                    for related_service_key in volume_mappings[volume_source]:
                        if (
                            related_service_key != service_key
                            and related_service_key in service_containers
                            and service_containers[related_service_key]["project_name"]
                            == target_project_name
                        ):
                            dependency_graph["relationships"].append(
                                {
                                    "from_service": service["service_name"],
                                    "to_service": service_containers[related_service_key][
                                        "service_name"
                                    ],
                                    "type": "volume",
                                    "resource": volume_source,
                                }
                            )

        # Prepare response
        response = {
            "service_info": {
                "service_name": target_service["service_name"],
                "project_name": target_service["project_name"],
                "container_id": target_service["container_id"],
                "container_name": target_service["container_name"],
                "is_compose_service": True,
                "networks": target_service["networks"],
                "volumes": target_service["volumes"],
                "running": target_service["running"],
            },
            "dependencies": network_dependencies + volume_dependencies,
            "dependents": [],  # This would require reverse analysis - implemented in dependency_graph
            "dependency_graph": dependency_graph,
            "network_analysis": {
                "target_networks": list(target_networks),
                "network_dependencies": network_dependencies,
                "shared_networks": len(network_dependencies) > 0,
            },
            "volume_analysis": {
                "target_volumes": list(target_volumes),
                "volume_dependencies": volume_dependencies,
                "shared_volumes": len(volume_dependencies) > 0,
            },
            "compose_analysis": {
                "is_compose_service": True,
                "project_name": target_project_name,
                "project_services_count": len(project_services),
                "total_services_found": len(service_containers),
                "total_networks": len(network_mappings),
                "total_volumes": len(volume_mappings),
            },
            "device_info": {
                "hostname": device,
                "connection_successful": True,
                "docker_available": True,
            },
            "query_info": {
                "container_identifier": container_name,
                "analysis_type": "compose_service",
                "containers_analyzed": len(containers_data),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_time_ms": int(
                    (
                        containers_result.raw_result.execution_time
                        + target_details_result.raw_result.execution_time
                    )
                    * 1000
                ),
            },
        }

        logger.info(
            f"Analyzed service dependencies for '{target_service['service_name']}' in project '{target_project_name}' "
            f"on {device} (found {len(network_dependencies)} network deps, {len(volume_dependencies)} volume deps)"
        )

        return response

    except (DeviceNotFoundError, ContainerError, SSHConnectionError):
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error analyzing service dependencies for '{container_name}' on {device}: {e}"
        )
        raise ContainerError(
            message=f"Failed to analyze service dependencies: {str(e)}",
            container_id=container_name,
            operation="get_service_dependencies",
            hostname=device,
        )


async def start_container(device: str, container_name: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Start a Docker container on a specific device.

    Args:
        device: Device hostname (must be configured in ~/.ssh/config)
        container_name: Container name or ID to start
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing operation result and metadata

    Raises:
        ContainerError: If container not found or Docker command fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Starting container {container_name} on device: {device}")

    try:
        result = await execute_ssh_command_simple(device, f"docker start {container_name}", timeout)

        if not result.success:
            raise ContainerError(
                message=f"Failed to start container {container_name} on {device}: {result.stderr}",
                container_id=container_name,
                hostname=device,
                operation="start_container",
            )

        return {
            "action": "start",
            "container_name": container_name,
            "device": device,
            "success": True,
            "output": result.stdout,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_time_ms": int(result.execution_time * 1000),
        }

    except ContainerError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error starting container {container_name} on {device}: {e}")
        raise ContainerError(
            message=f"Failed to start container: {str(e)}",
            container_id=container_name,
            hostname=device,
            operation="start_container",
        )


async def stop_container(
    device: str, container_name: str, timeout: int = 10, force: bool = False, ssh_timeout: int = 60
) -> Dict[str, Any]:
    """
    Stop a Docker container on a specific device.

    Args:
        device: Device hostname (must be configured in ~/.ssh/config)
        container_name: Container name or ID to stop
        timeout: Timeout for graceful stop in seconds (default: 10)
        force: Force stop the container using docker kill (default: False)
        ssh_timeout: SSH command timeout in seconds (default: 60)

    Returns:
        Dict containing operation result and metadata

    Raises:
        ContainerError: If container not found or Docker command fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Stopping container {container_name} on device: {device} (force: {force})")

    try:
        if force:
            cmd = f"docker kill {container_name}"
            action = "kill"
        else:
            cmd = f"docker stop --time {timeout} {container_name}"
            action = "stop"

        result = await execute_ssh_command_simple(device, cmd, ssh_timeout)

        if not result.success:
            raise ContainerError(
                message=f"Failed to {action} container {container_name} on {device}: {result.stderr}",
                container_id=container_name,
                hostname=device,
                operation="stop_container",
            )

        return {
            "action": action,
            "container_name": container_name,
            "device": device,
            "success": True,
            "force": force,
            "timeout": timeout,
            "output": result.stdout,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_time_ms": int(result.execution_time * 1000),
        }

    except ContainerError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error stopping container {container_name} on {device}: {e}")
        raise ContainerError(
            message=f"Failed to stop container: {str(e)}",
            container_id=container_name,
            hostname=device,
            operation="stop_container",
        )


async def restart_container(
    device: str, container_name: str, timeout: int = 10, ssh_timeout: int = 60
) -> Dict[str, Any]:
    """
    Restart a Docker container on a specific device.

    Args:
        device: Device hostname (must be configured in ~/.ssh/config)
        container_name: Container name or ID to restart
        timeout: Timeout for restart in seconds (default: 10)
        ssh_timeout: SSH command timeout in seconds (default: 60)

    Returns:
        Dict containing operation result and metadata

    Raises:
        ContainerError: If container not found or Docker command fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Restarting container {container_name} on device: {device}")

    try:
        cmd = f"docker restart --time {timeout} {container_name}"
        result = await execute_ssh_command_simple(device, cmd, ssh_timeout)

        if not result.success:
            raise ContainerError(
                message=f"Failed to restart container {container_name} on {device}: {result.stderr}",
                container_id=container_name,
                hostname=device,
                operation="restart_container",
            )

        return {
            "action": "restart",
            "container_name": container_name,
            "device": device,
            "success": True,
            "timeout": timeout,
            "output": result.stdout,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_time_ms": int(result.execution_time * 1000),
        }

    except ContainerError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error restarting container {container_name} on {device}: {e}")
        raise ContainerError(
            message=f"Failed to restart container: {str(e)}",
            container_id=container_name,
            hostname=device,
            operation="restart_container",
        )


async def remove_container(
    device: str,
    container_name: str,
    force: bool = False,
    remove_volumes: bool = False,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Remove a Docker container on a specific device.

    Args:
        device: Device hostname (must be configured in ~/.ssh/config)
        container_name: Container name or ID to remove
        force: Force remove the container (default: False)
        remove_volumes: Remove associated volumes (default: False)
        timeout: SSH command timeout in seconds (default: 60)

    Returns:
        Dict containing operation result and metadata

    Raises:
        ContainerError: If container not found or Docker command fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Removing container {container_name} on device: {device} (force: {force}, volumes: {remove_volumes})")

    try:
        cmd = "docker rm"
        if force:
            cmd += " --force"
        if remove_volumes:
            cmd += " --volumes"
        cmd += f" {container_name}"

        result = await execute_ssh_command_simple(device, cmd, timeout)

        if not result.success:
            raise ContainerError(
                message=f"Failed to remove container {container_name} on {device}: {result.stderr}",
                container_id=container_name,
                hostname=device,
                operation="remove_container",
            )

        return {
            "action": "remove",
            "container_name": container_name,
            "device": device,
            "success": True,
            "force": force,
            "remove_volumes": remove_volumes,
            "output": result.stdout,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_time_ms": int(result.execution_time * 1000),
        }

    except ContainerError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error removing container {container_name} on {device}: {e}")
        raise ContainerError(
            message=f"Failed to remove container: {str(e)}",
            container_id=container_name,
            hostname=device,
            operation="remove_container",
        )


# Tool registration metadata for MCP server
CONTAINER_TOOLS = {
    "list_containers": {
        "name": "list_containers",
        "description": "List Docker containers on a specific device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "status": {
                    "type": "string",
                    "description": "Optional status filter (running, stopped, etc.)",
                    "enum": [
                        "running",
                        "exited",
                        "paused",
                        "restarting",
                        "removing",
                        "dead",
                        "created",
                    ],
                },
                "all_containers": {
                    "type": "boolean",
                    "description": "Include stopped containers",
                    "default": True,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device"],
        },
        "function": list_containers,
    },
    "get_container_info": {
        "name": "get_container_info",
        "description": "Get detailed information about a specific Docker container",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "container_name": {
                    "type": "string",
                    "description": "Container name or ID to inspect",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device", "container_name"],
        },
        "function": get_container_info,
    },
    "get_container_logs": {
        "name": "get_container_logs",
        "description": "Get logs from a specific Docker container",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "container_name": {
                    "type": "string",
                    "description": "Container name or ID to get logs from",
                },
                "since": {
                    "type": "string",
                    "description": "Get logs since timestamp/duration (e.g., '2023-01-01T10:00:00Z', '24h', '1h30m')",
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of lines to retrieve from the end of logs",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 10000,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device", "container_name"],
        },
        "function": get_container_logs,
    },
    "get_service_dependencies": {
        "name": "get_service_dependencies",
        "description": "Analyze and map dependencies between Docker Compose services",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "container_name": {
                    "type": "string",
                    "description": "Container name or ID to analyze dependencies from",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device", "container_name"],
        },
        "function": get_service_dependencies,
    },
    "start_container": {
        "name": "start_container",
        "description": "Start a Docker container on a specific device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "container_name": {"type": "string", "description": "Container name or ID to start"},
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device", "container_name"],
        },
        "function": start_container,
    },
    "stop_container": {
        "name": "stop_container",
        "description": "Stop a Docker container on a specific device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "container_name": {"type": "string", "description": "Container name or ID to stop"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout for graceful stop in seconds",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 300,
                },
                "force": {
                    "type": "boolean",
                    "description": "Force stop the container using docker kill",
                    "default": False,
                },
                "ssh_timeout": {
                    "type": "integer",
                    "description": "SSH command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device", "container_name"],
        },
        "function": stop_container,
    },
    "restart_container": {
        "name": "restart_container",
        "description": "Restart a Docker container on a specific device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "container_name": {"type": "string", "description": "Container name or ID to restart"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout for restart in seconds",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 300,
                },
                "ssh_timeout": {
                    "type": "integer",
                    "description": "SSH command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device", "container_name"],
        },
        "function": restart_container,
    },
    "remove_container": {
        "name": "remove_container",
        "description": "Remove a Docker container on a specific device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "container_name": {"type": "string", "description": "Container name or ID to remove"},
                "force": {
                    "type": "boolean",
                    "description": "Force remove the container",
                    "default": False,
                },
                "remove_volumes": {
                    "type": "boolean",
                    "description": "Remove associated volumes",
                    "default": False,
                },
                "timeout": {
                    "type": "integer",
                    "description": "SSH command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device", "container_name"],
        },
        "function": remove_container,
    },
}
