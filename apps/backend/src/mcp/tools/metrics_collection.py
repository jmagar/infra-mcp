"""
Metrics Collection MCP Tools

This module implements MCP tools for drive health monitoring and Glances-based system metrics
across infrastructure devices.
"""

from datetime import UTC, datetime
import json
import logging
import re

from typing import Any, Dict, List, Optional

from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
)
from apps.backend.src.utils.ssh_client import SSHConnectionInfo, get_ssh_client
from apps.backend.src.services.glances_service import GlancesService
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.models.device import Device
from apps.backend.src.core.database import get_db_session, get_async_session_factory
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def get_system_info_glances(device: str, timeout: int = 60) -> dict[str, Any]:
    """
    Collect comprehensive system metrics from a device using Glances API via unified data collection.
    
    This tool uses the unified data collection service to gather system metrics
    through Glances API, providing structured JSON responses with intelligent caching.

    Args:
        device: Device hostname or IP address to query
        timeout: Request timeout in seconds (default: 60)

    Returns:
        Dict containing comprehensive system data including:
        - CPU usage statistics
        - Memory usage information  
        - Network interface statistics
        - Process list with resource usage
        - File system usage
        - Disk I/O statistics
        - GPU stats (if available)
        - Sensor data (temperature, fans, power)
        - System load averages and uptime

    Raises:
        DeviceNotFoundError: If device cannot be reached
        GlancesConnectionError: If Glances API is unavailable
        DataCollectionError: If data collection fails
    """
    logger.info(f"Collecting system metrics via Glances from device: {device}")

    try:
        # Get database session factory
        session_factory = get_async_session_factory()
        
        # Get SSH client for potential fallback operations
        ssh_client = get_ssh_client()
        
        # Get unified data collection service
        unified_service = await get_unified_data_collection_service(
            db_session_factory=session_factory,
            ssh_client=ssh_client
        )

        # Get device from database to access Glances configuration
        async with session_factory() as db_session:
            result = await db_session.execute(
                select(Device).where(Device.hostname == device)
            )
            device_obj = result.scalar_one_or_none()
            
            if not device_obj:
                raise DeviceNotFoundError(device, "hostname")

            # Collect all system data via unified service
            system_data = await unified_service._collect_all_system_data_glances(
                device_obj, timeout=timeout
            )
            
            return system_data

    except Exception as e:
        logger.error(f"Failed to collect system metrics from {device}: {e}")
        
        # Check if it's a connection error
        if "connection" in str(e).lower() or "unreachable" in str(e).lower():
            raise DeviceNotFoundError(device, "hostname")
        
        # Return error response with basic structure
        return {
            "device": device,
            "timestamp": datetime.now(UTC).isoformat(),
            "error": f"Failed to collect system metrics: {str(e)}",
            "system_metrics": {},
            "network_stats": [],
            "process_list": [],
            "filesystem_usage": [],
            "disk_io_stats": [],
            "gpu_stats": [],
            "sensor_data": []
        }


async def get_drive_health(
    device: str, drive: str | None = None, timeout: int = 120
) -> dict[str, Any]:
    """
    Collect drive health and SMART data from a specific device.

    This tool connects to a device via SSH and collects comprehensive
    drive health information using smartctl and lsblk commands.
    Supports SATA, NVMe, and SAS drives with different SMART attribute formats.

    Args:
        device: Device hostname or IP address to query
        drive: Specific drive to check (e.g., 'sda', 'nvme0n1'). If None, checks all drives
        timeout: Command timeout in seconds (default: 120)

    Returns:
        Dict containing:
        - device: Device hostname
        - timestamp: Query timestamp (ISO 8601)
        - drives: List of drive health information
        - summary: Total, healthy, and warning drive counts

    Raises:
        DeviceNotFoundError: If device cannot be reached
        SSHConnectionError: If SSH connection fails
        SSHCommandError: If SMART commands fail
    """
    logger.info(f"Collecting drive health from device: {device}")

    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(host=device, command_timeout=timeout)

        # Get SSH client
        ssh_client = get_ssh_client()

        # First, discover available drives
        drives_to_check = []

        if drive:
            # Check specific drive
            drives_to_check = [drive]
        else:
            # Discover all drives
            try:
                discover_result = await ssh_client.execute_command(
                    connection_info=connection_info,
                    command="lsblk -d -o NAME,TYPE,SIZE,MODEL --noheadings | grep -E '^(sd|nvme|hd)'",
                    timeout=30,
                    check=False,
                )

                if discover_result.success and discover_result.stdout:
                    for line in discover_result.stdout.strip().split("\n"):
                        if line.strip():
                            parts = line.strip().split()
                            if parts and parts[0]:
                                drive_name = parts[0]
                                drives_to_check.append(drive_name)

                    logger.debug(f"Discovered drives on {device}: {drives_to_check}")
                else:
                    logger.warning(
                        f"Could not discover drives on {device}: {discover_result.stderr}"
                    )

            except Exception as e:
                logger.warning(f"Error discovering drives on {device}: {e}")

        # If no drives found, try common drive names
        if not drives_to_check:
            drives_to_check = ["sda", "sdb", "sdc", "nvme0n1", "nvme1n1"]
            logger.info(f"No drives discovered, trying common names: {drives_to_check}")

        # Collect health data for each drive
        drive_health_data = []

        for drive_name in drives_to_check:
            logger.debug(f"Checking health for drive {drive_name} on {device}")

            drive_info = await _collect_single_drive_health(
                ssh_client, connection_info, device, drive_name
            )

            if drive_info:
                drive_health_data.append(drive_info)

        # Calculate summary statistics
        total_drives = len(drive_health_data)
        healthy_drives = sum(
            1
            for d in drive_health_data
            if not d.get("error") and d.get("health_percentage", 0) >= 80
        )
        warning_drives = total_drives - healthy_drives

        # Prepare response
        response = {
            "device": device,
            "timestamp": datetime.now(UTC).isoformat(),
            "drives": drive_health_data,
            "summary": {
                "total_drives": total_drives,
                "healthy_drives": healthy_drives,
                "warning_drives": warning_drives,
            },
        }

        logger.info(
            f"Successfully collected drive health from {device} "
            f"({total_drives} drives checked, {healthy_drives} healthy, {warning_drives} warnings)"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to collect drive health from {device}: {e}")

        # Check if it's a connection error
        if "connection" in str(e).lower() or "unreachable" in str(e).lower():
            raise DeviceNotFoundError(device, "hostname")

        # Return error response
        return {
            "device": device,
            "timestamp": datetime.now(UTC).isoformat(),
            "drives": [],
            "summary": {"total_drives": 0, "healthy_drives": 0, "warning_drives": 0},
            "error": f"Failed to collect drive health: {str(e)}",
        }


async def _collect_single_drive_health(
    ssh_client, connection_info: SSHConnectionInfo, device: str, drive_name: str
) -> dict[str, Any] | None:
    """
    Collect health data for a single drive.

    Args:
        ssh_client: SSH client instance
        connection_info: SSH connection configuration
        device: Device hostname
        drive_name: Drive name (e.g., 'sda', 'nvme0n1')

    Returns:
        Dict with drive health information or None if drive unavailable
    """
    try:
        # Determine drive path
        if drive_name.startswith("nvme"):
            drive_path = f"/dev/{drive_name}"
        else:
            drive_path = f"/dev/{drive_name}"

        # Check if smartctl is available and drive supports SMART
        smart_result = await ssh_client.execute_command(
            connection_info=connection_info,
            command=f"smartctl -i {drive_path}",
            timeout=30,
            check=False,
        )

        if not smart_result.success:
            logger.debug(
                f"SMART not available for drive {drive_name} on {device}: {smart_result.stderr}"
            )
            return {
                "device": device,
                "drive": drive_name,
                "model": "unknown",
                "serial": "unknown",
                "capacity": 0,
                "smart_status": False,
                "error": f"SMART not available: {smart_result.stderr.strip()}",
            }

        # Parse basic drive information
        drive_info = _parse_smart_info(smart_result.stdout)
        drive_info.update({"device": device, "drive": drive_name, "smart_status": True})

        # Get detailed SMART attributes
        attributes_result = await ssh_client.execute_command(
            connection_info=connection_info,
            command=f"smartctl -A {drive_path}",
            timeout=30,
            check=False,
        )

        if attributes_result.success:
            smart_attributes = _parse_smart_attributes(
                attributes_result.stdout, drive_name.startswith("nvme")
            )
            drive_info.update(smart_attributes)
        else:
            logger.debug(
                f"Could not get SMART attributes for {drive_name} on {device}: {attributes_result.stderr}"
            )

        # Get overall SMART health status
        health_result = await ssh_client.execute_command(
            connection_info=connection_info,
            command=f"smartctl -H {drive_path}",
            timeout=30,
            check=False,
        )

        if health_result.success:
            health_info = _parse_smart_health(health_result.stdout)
            drive_info.update(health_info)
        else:
            logger.debug(
                f"Could not get SMART health for {drive_name} on {device}: {health_result.stderr}"
            )

        logger.debug(f"Successfully collected health data for drive {drive_name} on {device}")
        return drive_info

    except Exception as e:
        logger.error(f"Error collecting health data for drive {drive_name} on {device}: {e}")
        return {
            "device": device,
            "drive": drive_name,
            "model": "unknown",
            "serial": "unknown",
            "capacity": 0,
            "smart_status": False,
            "error": f"Error collecting data: {str(e)}",
        }


def _parse_smart_info(smart_output: str) -> dict[str, Any]:
    """
    Parse basic drive information from smartctl -i output.

    Args:
        smart_output: Output from smartctl -i command

    Returns:
        Dict with basic drive information
    """
    if not smart_output:
        return {"model": "unknown", "serial": "unknown", "capacity": 0}

    try:
        info = {"model": "unknown", "serial": "unknown", "capacity": 0}

        lines = smart_output.strip().split("\n")
        for line in lines:
            line = line.strip()

            # Device Model
            if line.startswith("Device Model:") or line.startswith("Model Name:"):
                model = line.split(":", 1)[1].strip()
                info["model"] = model

            # Serial Number
            elif line.startswith("Serial Number:") or line.startswith("Serial number:"):
                serial = line.split(":", 1)[1].strip()
                info["serial"] = serial

            # User Capacity (for traditional drives)
            elif line.startswith("User Capacity:"):
                # Example: "User Capacity:    500,107,862,016 bytes [500 GB]"
                capacity_match = re.search(r"([\d,]+)\s*bytes", line)
                if capacity_match:
                    capacity_str = capacity_match.group(1).replace(",", "")
                    info["capacity"] = int(capacity_str)

            # Total NVM Capacity (for NVMe drives)
            elif line.startswith("Total NVM Capacity:"):
                # Example: "Total NVM Capacity:                  500,107,862,016 [500 GB]"
                capacity_match = re.search(r"([\d,]+)", line)
                if capacity_match:
                    capacity_str = capacity_match.group(1).replace(",", "")
                    info["capacity"] = int(capacity_str)

        return info

    except Exception as e:
        logger.error(f"Error parsing SMART info: {e}")
        return {"model": "unknown", "serial": "unknown", "capacity": 0}


def _parse_smart_attributes(smart_output: str, is_nvme: bool = False) -> dict[str, Any]:
    """
    Parse SMART attributes from smartctl -A output.

    Args:
        smart_output: Output from smartctl -A command
        is_nvme: Whether this is an NVMe drive

    Returns:
        Dict with parsed SMART attributes
    """
    if not smart_output:
        return {"attributes": {}, "health_percentage": 0}

    try:
        if is_nvme:
            return _parse_nvme_attributes(smart_output)
        else:
            return _parse_traditional_smart_attributes(smart_output)

    except Exception as e:
        logger.error(f"Error parsing SMART attributes: {e}")
        return {"attributes": {}, "health_percentage": 0}


def _parse_nvme_attributes(smart_output: str) -> dict[str, Any]:
    """
    Parse NVMe SMART attributes.

    NVMe drives have different attribute formats than traditional SATA drives.
    """
    attributes = {}
    health_percentage = 100

    try:
        lines = smart_output.strip().split("\n")
        for line in lines:
            line = line.strip()

            # Critical Warning
            if "Critical Warning:" in line:
                warning = line.split(":", 1)[1].strip()
                attributes["critical_warning"] = warning

            # Temperature
            elif "Temperature:" in line:
                temp_match = re.search(r"(\d+)", line)
                if temp_match:
                    attributes["temperature"] = int(temp_match.group(1))

            # Available Spare
            elif "Available Spare:" in line:
                spare_match = re.search(r"(\d+)%", line)
                if spare_match:
                    attributes["available_spare"] = int(spare_match.group(1))

            # Available Spare Threshold
            elif "Available Spare Threshold:" in line:
                threshold_match = re.search(r"(\d+)%", line)
                if threshold_match:
                    attributes["available_spare_threshold"] = int(threshold_match.group(1))

            # Percentage Used
            elif "Percentage Used:" in line:
                used_match = re.search(r"(\d+)%", line)
                if used_match:
                    percentage_used = int(used_match.group(1))
                    attributes["percentage_used"] = percentage_used
                    health_percentage = max(0, 100 - percentage_used)

        return {"attributes": attributes, "health_percentage": health_percentage}

    except Exception as e:
        logger.error(f"Error parsing NVMe attributes: {e}")
        return {"attributes": {}, "health_percentage": 0}


def _parse_traditional_smart_attributes(smart_output: str) -> dict[str, Any]:
    """
    Parse traditional SATA/SAS SMART attributes.

    Traditional drives use the standard SMART attribute table format.
    """
    attributes = {}
    health_percentage = 100

    try:
        lines = smart_output.strip().split("\n")
        in_attribute_section = False

        for line in lines:
            line = line.strip()

            # Look for the start of the SMART attribute table
            if "ID#" in line and "ATTRIBUTE_NAME" in line:
                in_attribute_section = True
                continue

            if in_attribute_section and line:
                # Parse attribute line
                # Format: ID# ATTRIBUTE_NAME          FLAGS    VALUE WORST THRESH FAIL RAW_VALUE
                parts = line.split()
                if len(parts) >= 10 and parts[0].isdigit():
                    attr_id = int(parts[0])
                    attr_name = parts[1]
                    value = int(parts[3]) if parts[3].isdigit() else 0
                    worst = int(parts[4]) if parts[4].isdigit() else 0
                    thresh = int(parts[5]) if parts[5].isdigit() else 0
                    raw_value = parts[9] if len(parts) > 9 else "0"

                    attributes[attr_name.lower()] = {
                        "id": attr_id,
                        "value": value,
                        "worst": worst,
                        "threshold": thresh,
                        "raw_value": raw_value,
                    }

                    # Calculate health based on critical attributes
                    if attr_name.lower() in [
                        "reallocated_sector_ct",
                        "current_pending_sector",
                        "offline_uncorrectable",
                    ]:
                        raw_int = 0
                        try:
                            raw_int = int(raw_value.split()[0])
                        except (ValueError, IndexError):
                            pass

                        if raw_int > 0:
                            health_percentage = min(health_percentage, 70)  # Warning level

        return {"attributes": attributes, "health_percentage": health_percentage}

    except Exception as e:
        logger.error(f"Error parsing traditional SMART attributes: {e}")
        return {"attributes": {}, "health_percentage": 0}


def _parse_smart_health(smart_output: str) -> dict[str, Any]:
    """
    Parse overall SMART health status from smartctl -H output.

    Args:
        smart_output: Output from smartctl -H command

    Returns:
        Dict with overall health status
    """
    if not smart_output:
        return {"overall_health": "unknown"}

    try:
        health_info = {"overall_health": "unknown"}

        lines = smart_output.strip().split("\n")
        for line in lines:
            line = line.strip().lower()

            if "overall-health self-assessment test result:" in line:
                # Traditional SMART health
                if "passed" in line:
                    health_info["overall_health"] = "passed"
                elif "failed" in line:
                    health_info["overall_health"] = "failed"

            elif "smart overall-health self-assessment test result:" in line:
                # Alternative format
                if "passed" in line:
                    health_info["overall_health"] = "passed"
                elif "failed" in line:
                    health_info["overall_health"] = "failed"

            elif "smart health status:" in line:
                # NVMe format
                if "ok" in line:
                    health_info["overall_health"] = "passed"
                else:
                    health_info["overall_health"] = "failed"

        return health_info

    except Exception as e:
        logger.error(f"Error parsing SMART health: {e}")
        return {"overall_health": "unknown"}


# Tool registry for MCP server
METRICS_COLLECTION_TOOLS = {
    "get_system_info_glances": {
        "name": "get_system_info_glances",
        "description": "Collect comprehensive system metrics from a device using Glances API",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
            },
            "required": ["device"],
        },
        "function": get_system_info_glances,
    },
    "get_drive_health": {
        "name": "get_drive_health",
        "description": "Collect drive health and SMART data from a specific device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "drive": {
                    "type": "string",
                    "description": "Specific drive to check (e.g., 'sda', 'nvme0n1'). If not provided, checks all drives",
                    "optional": True,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 120,
                    "minimum": 30,
                    "maximum": 300,
                },
            },
            "required": ["device"],
        },
        "function": get_drive_health,
    },
}