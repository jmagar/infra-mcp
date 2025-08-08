"""
System Monitoring MCP Tools

This module implements MCP tools for system performance monitoring,
resource usage analysis, and health checking across infrastructure devices.

Architectural Change (August 7, 2025): Uses unified data collection service directly
instead of HTTP API calls for better performance and consistency.
"""

from datetime import UTC, datetime
import logging

from typing import Any

from apps.backend.src.core.database import get_async_session_factory
from apps.backend.src.core.exceptions import DataCollectionError
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.utils.ssh_client import get_ssh_client

logger = logging.getLogger(__name__)


# Note: SMART data parsing functions removed as they are now handled by the unified data collection service
# All SMART data collection, parsing, and caching is managed by the polling service and cached in the database


async def get_drive_health(
    device: str, drive: str | None = None, timeout: int = 60
) -> dict[str, Any]:
    """
    Get S.M.A.R.T. drive health information and disk status.

    This tool uses the unified data collection service directly to retrieve cached or fresh
    S.M.A.R.T. health data for storage drives, including temperature, error counts,
    and overall health status. Supports both specific drive queries and all drives.

    Args:
        device: Device hostname or IP address
        drive: Specific drive to check (e.g., '/dev/sda') or None for all
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing drive health information from unified data collection service

    Raises:
        Exception: If data collection fails or device cannot be reached
    """
    logger.info(f"Getting drive health for device: {device}")

    try:
        # Get unified data collection service
        db_session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=db_session_factory,
            ssh_client=ssh_client
        )

        # Create collection method for drive health
        async def collect_drive_health() -> dict[str, Any]:
            from apps.backend.src.utils.ssh_client import execute_ssh_command_simple

            # S.M.A.R.T. data collection logic
            if drive:
                # Query specific drive
                cmd = f"sudo smartctl -a {drive} 2>/dev/null || echo 'SMART_ERROR'"
            else:
                # Query all drives
                cmd = 'lsblk -d -n -o NAME,TYPE | grep disk | while read name type; do echo "=== /dev/$name ==="; sudo smartctl -a /dev/$name 2>/dev/null || echo "SMART_ERROR"; done'

            result = await execute_ssh_command_simple(device, cmd, timeout)

            if not result.success:
                raise DataCollectionError(
                    message=f"Failed to collect drive health data: {result.stderr}",
                    operation="drive_health_collection"
                )

            # Parse S.M.A.R.T. output (simplified)
            return {
                "device": device,
                "drive_filter": drive,
                "raw_output": result.stdout,
                "collection_time": datetime.now(UTC).isoformat(),
                "status": "success"
            }

        # Use unified data collection
        result = await unified_service.collect_and_store_data(
            collection_method=collect_drive_health,
            device_id=None,  # type: ignore[arg-type]
            data_type="drive_health"
        )

        logger.info(f"Successfully retrieved drive health data for {device}")
        return result

    except DataCollectionError as e:
        logger.error(f"Data collection error getting drive health for {device}: {e}")
        raise Exception(f"Failed to get drive health data: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting drive health for {device}: {e}")
        raise Exception(f"Failed to get drive health data: {str(e)}") from e


async def get_system_logs(
    device: str,
    service: str | None = None,
    since: str | None = None,
    lines: int = 100,
    timeout: int = 60,
) -> dict[str, Any]:
    """
    Get system logs from journald or traditional syslog.

    This tool uses the unified data collection service directly to retrieve system logs
    using journalctl commands and traditional log file access. Supports filtering by service,
    time range, and line limits.

    Args:
        device: Device hostname or IP address
        service: Specific service to get logs for (e.g., 'docker', 'nginx')
        since: Get logs since timestamp/duration (e.g., '2h', '1d', '2023-01-01 10:00:00')
        lines: Number of log lines to retrieve (default: 100)
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing log data from unified data collection service

    Raises:
        Exception: If data collection fails or device cannot be reached
    """
    logger.info(f"Getting system logs for device: {device}")

    try:
        # Get unified data collection service
        db_session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=db_session_factory,
            ssh_client=ssh_client
        )

        # Create collection method for system logs
        async def collect_system_logs() -> dict[str, Any]:
            from apps.backend.src.utils.ssh_client import execute_ssh_command_simple

            # Build journalctl command
            cmd_parts = ["journalctl", "--no-pager"]

            if service:
                cmd_parts.extend(["-u", service])
            if since:
                cmd_parts.extend(["--since", f"'{since}'"])
            if lines:
                cmd_parts.extend(["-n", str(lines)])

            cmd = " ".join(cmd_parts)

            result = await execute_ssh_command_simple(device, cmd, timeout)

            if not result.success:
                raise DataCollectionError(
                    message=f"Failed to collect system logs: {result.stderr}",
                    operation="system_logs_collection"
                )

            return {
                "device": device,
                "service_filter": service,
                "since_filter": since,
                "lines_requested": lines,
                "log_content": result.stdout,
                "collection_time": datetime.now(UTC).isoformat(),
                "status": "success"
            }

        # Use unified data collection
        result = await unified_service.collect_and_store_data(
            collection_method=collect_system_logs,
            device_id=None,  # type: ignore[arg-type]
            data_type="system_logs"
        )

        logger.info(f"Successfully retrieved system logs for {device}")
        return result

    except DataCollectionError as e:
        logger.error(f"Data collection error getting system logs for {device}: {e}")
        raise Exception(f"Failed to get system logs: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting system logs for {device}: {e}")
        raise Exception(f"Failed to get system logs: {str(e)}") from e


async def get_drive_stats(
    device: str, drive: str | None = None, timeout: int = 60
) -> dict[str, Any]:
    """
    Get drive usage statistics, I/O performance, and utilization metrics.

    This tool uses the unified data collection service directly to retrieve cached or fresh
    drive performance and usage data including I/O statistics, throughput,
    utilization percentages, queue depths, and filesystem usage.

    Args:
        device: Device hostname or IP address
        drive: Specific drive to check (e.g., 'sda') or None for all drives
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing drive statistics from unified data collection service

    Raises:
        Exception: If data collection fails or device cannot be reached
    """
    logger.info(f"Getting drive stats for device: {device}")

    try:
        # Get unified data collection service
        db_session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=db_session_factory,
            ssh_client=ssh_client
        )

        # Create collection method for drive stats
        async def collect_drive_stats() -> dict[str, Any]:
            from apps.backend.src.utils.ssh_client import execute_ssh_command_simple

            # Collect I/O stats and filesystem usage
            if drive:
                # Specific drive stats
                iostat_cmd = f"iostat -x 1 2 {drive} | tail -n +4 | grep -E '^{drive}'"
                df_cmd = f"df -h | grep {drive}"
            else:
                # All drives stats
                iostat_cmd = "iostat -x 1 2 | tail -n +4 | grep -E '^[a-z]+[0-9]*'"
                df_cmd = "df -h | grep -E '^/dev/'"

            # Get I/O statistics
            iostat_result = await execute_ssh_command_simple(device, iostat_cmd, timeout)
            # Get filesystem usage
            df_result = await execute_ssh_command_simple(device, df_cmd, timeout)

            if not iostat_result.success:
                raise DataCollectionError(
                    message=f"Failed to collect iostat data: {iostat_result.stderr}",
                    operation="drive_stats_collection"
                )

            return {
                "device": device,
                "drive_filter": drive,
                "iostat_output": iostat_result.stdout,
                "filesystem_usage": df_result.stdout if df_result.success else "",
                "collection_time": datetime.now(UTC).isoformat(),
                "status": "success"
            }

        # Use unified data collection
        result = await unified_service.collect_and_store_data(
            collection_method=collect_drive_stats,
            device_id=None,  # type: ignore[arg-type]
            data_type="drive_stats"
        )

        logger.info(f"Successfully retrieved drive stats for {device}")
        return result

    except DataCollectionError as e:
        logger.error(f"Data collection error getting drive stats for {device}: {e}")
        raise Exception(f"Failed to get drive stats: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting drive stats for {device}: {e}")
        raise Exception(f"Failed to get drive stats: {str(e)}") from e


async def get_network_ports(device: str, timeout: int = 30) -> dict[str, Any]:
    """
    Get network port information and listening processes.

    This tool uses the unified data collection service directly to retrieve network port
    information using 'ss -tulpn' and 'netstat' commands, showing listening ports
    and the processes using them.

    Args:
        device: Device hostname or IP address
        timeout: Command timeout in seconds (default: 30)

    Returns:
        Dict containing port information from unified data collection service

    Raises:
        Exception: If data collection fails or device cannot be reached
    """
    logger.info(f"Getting network ports for device: {device}")

    try:
        # Get unified data collection service
        db_session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=db_session_factory,
            ssh_client=ssh_client
        )

        # Create collection method for network ports
        async def collect_network_ports() -> dict[str, Any]:
            from apps.backend.src.utils.ssh_client import execute_ssh_command_simple

            # Try ss command first (modern), fallback to netstat
            ss_cmd = "ss -tulpn"
            netstat_cmd = "netstat -tulpn 2>/dev/null || echo 'NETSTAT_NOT_AVAILABLE'"

            ss_result = await execute_ssh_command_simple(device, ss_cmd, timeout)

            if not ss_result.success:
                # Fallback to netstat
                netstat_result = await execute_ssh_command_simple(device, netstat_cmd, timeout)
                if not netstat_result.success:
                    raise DataCollectionError(
                        message=f"Failed to collect network port data: {netstat_result.stderr}",
                        operation="network_ports_collection"
                    )
                port_output = netstat_result.stdout
                method_used = "netstat"
            else:
                port_output = ss_result.stdout
                method_used = "ss"

            return {
                "device": device,
                "port_output": port_output,
                "method_used": method_used,
                "collection_time": datetime.now(UTC).isoformat(),
                "status": "success"
            }

        # Use unified data collection
        result = await unified_service.collect_and_store_data(
            collection_method=collect_network_ports,
            device_id=None,  # type: ignore[arg-type]
            data_type="network_ports"
        )

        logger.info(f"Successfully retrieved network ports for {device}")
        return result

    except DataCollectionError as e:
        logger.error(f"Data collection error getting network ports for {device}: {e}")
        raise Exception(f"Failed to get network ports: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting network ports for {device}: {e}")
        raise Exception(f"Failed to get network ports: {str(e)}") from e


# Tool registration metadata for MCP server
SYSTEM_MONITORING_TOOLS = {
    "get_drive_health": {
        "name": "get_drive_health",
        "description": "Get S.M.A.R.T. drive health information via unified data collection service",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "drive": {
                    "type": "string",
                    "description": "Specific drive to check (e.g., '/dev/sda') or omit for all drives",
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
        "function": get_drive_health,
    },
    "get_system_logs": {
        "name": "get_system_logs",
        "description": "Get system logs via unified data collection service",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "service": {
                    "type": "string",
                    "description": "Specific service to get logs for (e.g., 'docker', 'nginx')",
                },
                "since": {
                    "type": "string",
                    "description": "Get logs since timestamp/duration (e.g., '2h', '1d', '2023-01-01 10:00:00')",
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of log lines to retrieve",
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
            "required": ["device"],
        },
        "function": get_system_logs,
    },
    "get_drive_stats": {
        "name": "get_drive_stats",
        "description": "Get drive usage statistics and I/O performance via unified data collection service",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "drive": {
                    "type": "string",
                    "description": "Specific drive to check (e.g., 'sda') or omit for all drives",
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
        "function": get_drive_stats,
    },
    "get_network_ports": {
        "name": "get_network_ports",
        "description": "Get network port information via unified data collection service",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 30,
                    "minimum": 5,
                    "maximum": 120,
                },
            },
            "required": ["device"],
        },
        "function": get_network_ports,
    },
}
