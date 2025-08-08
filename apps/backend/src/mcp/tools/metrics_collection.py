"""
Metrics Collection MCP Tools

This module implements MCP tools for system resource and health monitoring
across infrastructure devices using SSH communication.
"""

from datetime import UTC, datetime
import json
import logging
import re

from typing import Any, Dict, List, Optional
# UUID import removed - now using hostname-only approach

from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
)
from apps.backend.src.utils.ssh_client import SSHConnectionInfo, get_ssh_client

logger = logging.getLogger(__name__)


async def get_system_info(device: str, timeout: int = 60) -> dict[str, Any]:
    """
    Collect system resource metrics from a specific device.

    This tool connects to a device via SSH and collects comprehensive
    system metrics including CPU usage, memory usage, disk usage,
    load averages, process count, and uptime using standard Linux commands.

    Args:
        device: Device hostname or IP address to query
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing:
        - device: Device hostname
        - timestamp: Query timestamp (ISO 8601)
        - cpu_usage_percent: CPU usage percentage
        - memory: Memory usage information (total, used, free, percent)
        - disk_usage: List of disk usage for all mount points
        - load_average: Load averages (1min, 5min, 15min)
        - process_count: Total number of running processes
        - uptime: System uptime string

    Raises:
        DeviceNotFoundError: If device cannot be reached
        SSHConnectionError: If SSH connection fails
        SSHCommandError: If system commands fail
    """
    logger.info(f"Collecting system metrics from device: {device}")

    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(host=device, command_timeout=timeout)

        # Get SSH client
        ssh_client = get_ssh_client()

        # Define system metric collection commands
        commands = {
            # CPU usage from top (1 iteration, batch mode)
            "cpu": "top -bn1 | grep 'Cpu(s)' | head -1",
            # Memory usage from free command
            "memory": "free -b",
            # Disk usage from df command
            "disk": "df -h",
            # Load averages and uptime
            "uptime": "uptime",
            # Process count
            "processes": "ps -e --no-headers | wc -l",
        }

        # Execute all commands
        results = {}
        for metric_name, command in commands.items():
            try:
                result = await ssh_client.execute_command(
                    connection_info=connection_info,
                    command=command,
                    timeout=30,  # Shorter timeout for individual commands
                    check=False,  # Don't raise on non-zero exit codes
                )

                if result.success:
                    results[metric_name] = result.stdout.strip()
                    logger.debug(f"Successfully collected {metric_name} metrics from {device}")
                else:
                    logger.warning(
                        f"Failed to collect {metric_name} metrics from {device}: {result.stderr}"
                    )
                    results[metric_name] = None

            except Exception as e:
                logger.warning(f"Error collecting {metric_name} metrics from {device}: {e}")
                results[metric_name] = None

        # Parse collected metrics
        parsed_metrics = {}

        # Parse CPU usage
        cpu_usage = _parse_cpu_usage(results.get("cpu"))
        parsed_metrics["cpu_usage_percent"] = cpu_usage

        # Parse memory usage
        memory_info = _parse_memory_usage(results.get("memory"))
        parsed_metrics["memory"] = memory_info

        # Parse disk usage
        disk_info = _parse_disk_usage(results.get("disk"))
        parsed_metrics["disk_usage"] = disk_info

        # Parse load averages and uptime
        uptime_info = _parse_uptime(results.get("uptime"))
        parsed_metrics["load_average"] = uptime_info.get(
            "load_average", {"1min": 0.0, "5min": 0.0, "15min": 0.0}
        )
        parsed_metrics["uptime"] = uptime_info.get("uptime", "unknown")

        # Parse process count
        process_count = _parse_process_count(results.get("processes"))
        parsed_metrics["process_count"] = process_count

        # Prepare response
        response = {
            "device": device,
            "timestamp": datetime.now(UTC).isoformat(),
            **parsed_metrics,
        }

        logger.info(
            f"Successfully collected system metrics from {device} "
            f"(CPU: {cpu_usage}%, Memory: {memory_info.get('percent', 0)}%, "
            f"Load: {parsed_metrics['load_average']['1min']})"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to collect system metrics from {device}: {e}")

        # Check if it's a connection error
        if "connection" in str(e).lower() or "unreachable" in str(e).lower():
            raise DeviceNotFoundError(device, "hostname")

        # Return error response
        return {
            "device": device,
            "timestamp": datetime.now(UTC).isoformat(),
            "error": f"Failed to collect system metrics: {str(e)}",
            "cpu_usage_percent": 0,
            "memory": {"total": 0, "used": 0, "free": 0, "percent": 0},
            "disk_usage": [],
            "load_average": {"1min": 0.0, "5min": 0.0, "15min": 0.0},
            "process_count": 0,
            "uptime": "unknown",
        }


def _parse_cpu_usage(cpu_output: str | None) -> float:
    """
    Parse CPU usage from top command output.

    Expected formats:
    - Ubuntu: "Cpu(s):  5.3%us,  1.2%sy,  0.0%ni, 93.2%id,  0.3%wa,  0.0%hi,  0.0%si,  0.0%st"
    - CentOS: "%Cpu(s):  2.7 us,  1.3 sy,  0.0 ni, 95.3 id,  0.7 wa,  0.0 hi,  0.0 si,  0.0 st"
    """
    if not cpu_output:
        return 0.0

    try:
        # Look for idle percentage and calculate usage
        idle_match = re.search(r"(\d+\.?\d*)\s*%?\s*id", cpu_output, re.IGNORECASE)
        if idle_match:
            idle_percent = float(idle_match.group(1))
            usage_percent = 100.0 - idle_percent
            return round(usage_percent, 1)

        # Alternative: look for direct usage percentages
        usage_patterns = [
            r"(\d+\.?\d*)\s*%\s*us",  # user space
            r"(\d+\.?\d*)\s*%?\s*cpu",  # generic cpu usage
        ]

        for pattern in usage_patterns:
            match = re.search(pattern, cpu_output, re.IGNORECASE)
            if match:
                return round(float(match.group(1)), 1)

        logger.warning(f"Could not parse CPU usage from: {cpu_output}")
        return 0.0

    except Exception as e:
        logger.error(f"Error parsing CPU usage: {e}")
        return 0.0


def _parse_memory_usage(memory_output: str | None) -> dict[str, Any]:
    """
    Parse memory usage from free command output.

    Expected format:
    ```
                 total        used        free      shared  buff/cache   available
    Mem:    8201916416  2157568000  1892745216   123904000  4151603200  5720576000
    Swap:   2147479552           0  2147479552
    ```
    """
    if not memory_output:
        return {"total": 0, "used": 0, "free": 0, "percent": 0}

    try:
        lines = memory_output.strip().split("\n")

        # Find the memory line (starts with "Mem:")
        mem_line = None
        for line in lines:
            if line.strip().startswith("Mem:"):
                mem_line = line
                break

        if not mem_line:
            logger.warning("Could not find memory line in free output")
            return {"total": 0, "used": 0, "free": 0, "percent": 0}

        # Parse memory values (in bytes when using free -b)
        parts = mem_line.split()
        if len(parts) >= 4:
            total = int(parts[1])
            used = int(parts[2])
            free = int(parts[3])

            # Calculate percentage
            percent = round((used / total) * 100, 1) if total > 0 else 0

            return {"total": total, "used": used, "free": free, "percent": percent}

        logger.warning(f"Unexpected free command format: {mem_line}")
        return {"total": 0, "used": 0, "free": 0, "percent": 0}

    except Exception as e:
        logger.error(f"Error parsing memory usage: {e}")
        return {"total": 0, "used": 0, "free": 0, "percent": 0}


def _parse_disk_usage(disk_output: str | None) -> list[dict[str, Any]]:
    """
    Parse disk usage from df command output.

    Expected format:
    ```
    Filesystem      Size  Used Avail Use% Mounted on
    /dev/sda1        20G  5.5G   14G  30% /
    /dev/sda2       100G   45G   50G  48% /home
    tmpfs           4.0G     0  4.0G   0% /dev/shm
    ```
    """
    if not disk_output:
        return []

    try:
        lines = disk_output.strip().split("\n")

        # Skip header line
        if len(lines) < 2:
            return []

        disk_info = []

        for line in lines[1:]:  # Skip header
            parts = line.split()

            # Handle cases where filesystem name wraps to next line
            if len(parts) >= 6:
                filesystem = parts[0]
                size = parts[1]
                used = parts[2]
                available = parts[3]
                percent = parts[4].rstrip("%")
                mount = parts[5]

                # Skip special filesystems we don't want to monitor
                if mount.startswith(("/proc", "/sys", "/dev", "/run")) and mount != "/":
                    continue

                disk_info.append(
                    {
                        "device": filesystem,
                        "size": size,
                        "used": used,
                        "available": available,
                        "percent": percent,
                        "mount": mount,
                    }
                )

        return disk_info

    except Exception as e:
        logger.error(f"Error parsing disk usage: {e}")
        return []


def _parse_uptime(uptime_output: str | None) -> dict[str, Any]:
    """
    Parse uptime and load averages from uptime command output.

    Expected format:
    " 10:30:15 up 5 days, 14:25,  2 users,  load average: 0.52, 0.58, 0.59"
    """
    if not uptime_output:
        return {"uptime": "unknown", "load_average": {"1min": 0.0, "5min": 0.0, "15min": 0.0}}

    try:
        # Extract uptime string (everything before "load average")
        uptime_parts = uptime_output.split("load average:")
        uptime_str = uptime_parts[0].strip() if uptime_parts else uptime_output.strip()

        # Clean up uptime string (remove time and user count)
        uptime_match = re.search(r"up\s+(.+?)(?:,\s*\d+\s*users?)?$", uptime_str, re.IGNORECASE)
        if uptime_match:
            uptime_clean = uptime_match.group(1).strip()
        else:
            uptime_clean = uptime_str

        # Parse load averages
        load_averages = {"1min": 0.0, "5min": 0.0, "15min": 0.0}

        if len(uptime_parts) > 1:
            load_str = uptime_parts[1].strip()
            load_values = [x.strip() for x in load_str.split(",")]

            if len(load_values) >= 3:
                try:
                    load_averages["1min"] = float(load_values[0])
                    load_averages["5min"] = float(load_values[1])
                    load_averages["15min"] = float(load_values[2])
                except ValueError as e:
                    logger.warning(f"Could not parse load averages: {load_values}, error: {e}")

        return {"uptime": uptime_clean, "load_average": load_averages}

    except Exception as e:
        logger.error(f"Error parsing uptime: {e}")
        return {"uptime": "unknown", "load_average": {"1min": 0.0, "5min": 0.0, "15min": 0.0}}


def _parse_process_count(process_output: str | None) -> int:
    """
    Parse process count from wc output.
    """
    if not process_output:
        return 0

    try:
        return int(process_output.strip())
    except (ValueError, AttributeError):
        logger.warning(f"Could not parse process count: {process_output}")
        return 0


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
            health_status = _parse_smart_health(health_result.stdout)
            drive_info.update(health_status)

        # Calculate health percentage based on various factors
        health_percentage = _calculate_health_percentage(drive_info)
        drive_info["health_percentage"] = health_percentage

        return drive_info

    except Exception as e:
        logger.error(f"Error collecting health for drive {drive_name} on {device}: {e}")
        return {
            "device": device,
            "drive": drive_name,
            "model": "unknown",
            "serial": "unknown",
            "capacity": 0,
            "smart_status": False,
            "error": f"Collection failed: {str(e)}",
        }


def _parse_smart_info(smart_output: str) -> dict[str, Any]:
    """
    Parse basic drive information from smartctl -i output.

    Args:
        smart_output: Output from smartctl -i command

    Returns:
        Dict with model, serial, and capacity information
    """
    info = {"model": "unknown", "serial": "unknown", "capacity": 0}

    try:
        for line in smart_output.split("\n"):
            line = line.strip()

            # Parse model name
            if line.startswith("Device Model:") or line.startswith("Model Number:"):
                info["model"] = line.split(":", 1)[1].strip()

            # Parse serial number
            elif line.startswith("Serial Number:") or line.startswith("Serial number:"):
                info["serial"] = line.split(":", 1)[1].strip()

            # Parse capacity
            elif "User Capacity:" in line:
                # Extract capacity in bytes
                capacity_match = re.search(r"\[([0-9,]+)\s*bytes\]", line)
                if capacity_match:
                    capacity_str = capacity_match.group(1).replace(",", "")
                    info["capacity"] = int(capacity_str)
                else:
                    # Try to extract from human readable format
                    capacity_match = re.search(r"([0-9,]+\.?[0-9]*)\s*([KMGT]B)", line)
                    if capacity_match:
                        size_val = float(capacity_match.group(1).replace(",", ""))
                        size_unit = capacity_match.group(2)

                        multipliers = {"KB": 1000, "MB": 1000**2, "GB": 1000**3, "TB": 1000**4}
                        if size_unit in multipliers:
                            info["capacity"] = int(size_val * multipliers[size_unit])

    except Exception as e:
        logger.warning(f"Error parsing SMART info: {e}")

    return info


def _parse_smart_attributes(smart_output: str, is_nvme: bool = False) -> dict[str, Any]:
    """
    Parse SMART attributes from smartctl -A output.

    Args:
        smart_output: Output from smartctl -A command
        is_nvme: True if this is an NVMe drive

    Returns:
        Dict with parsed SMART attributes
    """
    attributes = {}

    try:
        if is_nvme:
            # Parse NVMe SMART attributes
            attributes.update(_parse_nvme_attributes(smart_output))
        else:
            # Parse traditional SATA/SAS SMART attributes
            attributes.update(_parse_traditional_smart_attributes(smart_output))

    except Exception as e:
        logger.warning(f"Error parsing SMART attributes: {e}")

    return attributes


def _parse_nvme_attributes(smart_output: str) -> dict[str, Any]:
    """Parse NVMe SMART attributes."""
    attributes = {}

    try:
        for line in smart_output.split("\n"):
            line = line.strip()

            # Temperature
            if "Temperature:" in line:
                temp_match = re.search(r"(\d+)\s*Celsius", line)
                if temp_match:
                    attributes["temperature"] = int(temp_match.group(1))

            # Power on hours
            elif "Power On Hours:" in line:
                hours_match = re.search(r"([0-9,]+)", line)
                if hours_match:
                    attributes["power_on_hours"] = int(hours_match.group(1).replace(",", ""))

            # Power cycles
            elif "Power Cycles:" in line:
                cycles_match = re.search(r"([0-9,]+)", line)
                if cycles_match:
                    attributes["power_cycle_count"] = int(cycles_match.group(1).replace(",", ""))

            # Media and Data Integrity Errors (closest to reallocated sectors)
            elif "Media and Data Integrity Errors:" in line:
                errors_match = re.search(r"([0-9,]+)", line)
                if errors_match:
                    attributes["uncorrectable_errors"] = int(errors_match.group(1).replace(",", ""))

    except Exception as e:
        logger.warning(f"Error parsing NVMe attributes: {e}")

    return attributes


def _parse_traditional_smart_attributes(smart_output: str) -> dict[str, Any]:
    """Parse traditional SATA/SAS SMART attributes."""
    attributes = {}

    try:
        lines = smart_output.split("\n")

        # Look for the SMART attributes table
        in_attributes_section = False

        for line in lines:
            line = line.strip()

            # Start of attributes table
            if "ID#" in line and "RAW_VALUE" in line:
                in_attributes_section = True
                continue

            if not in_attributes_section:
                continue

            # End of attributes table
            if not line or line.startswith("=") or "SMART Error Log" in line:
                break

            # Parse attribute line
            parts = line.split()
            if len(parts) >= 7:  # At least: ID, NAME, FLAGS, VALUE, WORST, THRESH, FAIL, RAW_VALUE
                try:
                    attr_id = int(parts[0])
                    attr_name = parts[1]
                    # Raw value typically starts after the dash separator
                    # Find the dash and take everything after it
                    dash_index = -1
                    for i, part in enumerate(parts):
                        if part == "-":
                            dash_index = i
                            break

                    if dash_index >= 0 and dash_index + 1 < len(parts):
                        # Join all parts after the dash to handle complex raw values
                        raw_value = " ".join(parts[dash_index + 1 :])
                    else:
                        # Fallback to traditional position
                        raw_value = parts[7] if len(parts) > 7 else parts[-1]

                    # Map important attributes
                    if attr_id == 5:  # Reallocated_Sector_Ct
                        attributes["reallocated_sectors"] = int(raw_value)
                    elif attr_id == 197:  # Current_Pending_Sector
                        attributes["pending_sectors"] = int(raw_value)
                    elif attr_id == 198:  # Offline_Uncorrectable
                        attributes["uncorrectable_errors"] = int(raw_value)
                    elif attr_id == 194:  # Temperature_Celsius
                        # Raw value might be in format "32 (Min/Max 18/45)" or just "32"
                        temp_match = re.search(r"^(\d+)", raw_value)
                        if temp_match:
                            temp_val = int(temp_match.group(1))
                            # If temperature seems too low, try to get current temp from format like "32 (Min/Max 18/45)"
                            if temp_val < 15:  # Unrealistic low temp, try different parsing
                                current_temp_match = re.search(r"(\d+)\s*\(Min/Max", raw_value)
                                if current_temp_match:
                                    temp_val = int(current_temp_match.group(1))
                            attributes["temperature"] = temp_val
                    elif attr_id == 9:  # Power_On_Hours
                        attributes["power_on_hours"] = int(raw_value)
                    elif attr_id == 12:  # Power_Cycle_Count
                        attributes["power_cycle_count"] = int(raw_value)

                except (ValueError, IndexError) as e:
                    logger.debug(f"Could not parse SMART attribute line: {line}, error: {e}")
                    continue

    except Exception as e:
        logger.warning(f"Error parsing traditional SMART attributes: {e}")

    return attributes


def _parse_smart_health(smart_output: str) -> dict[str, Any]:
    """
    Parse overall SMART health status.

    Args:
        smart_output: Output from smartctl -H command

    Returns:
        Dict with health status information
    """
    health_info = {}

    try:
        for line in smart_output.split("\n"):
            line = line.strip()

            if "SMART overall-health self-assessment test result:" in line:
                if "PASSED" in line:
                    health_info["smart_health_passed"] = True
                else:
                    health_info["smart_health_passed"] = False

            elif "SMART Health Status:" in line:
                if "OK" in line:
                    health_info["smart_health_passed"] = True
                else:
                    health_info["smart_health_passed"] = False

    except Exception as e:
        logger.warning(f"Error parsing SMART health: {e}")

    return health_info


def _calculate_health_percentage(drive_info: dict[str, Any]) -> int:
    """
    Calculate overall drive health percentage based on SMART attributes.

    Args:
        drive_info: Dict containing drive SMART attributes

    Returns:
        Health percentage (0-100)
    """
    try:
        health_score = 100

        # Check overall SMART health
        if not drive_info.get("smart_health_passed", True):
            health_score -= 50

        # Check for reallocated sectors (critical)
        reallocated = drive_info.get("reallocated_sectors", 0)
        if reallocated > 0:
            health_score -= min(30, reallocated * 5)

        # Check for pending sectors (critical)
        pending = drive_info.get("pending_sectors", 0)
        if pending > 0:
            health_score -= min(25, pending * 10)

        # Check for uncorrectable errors (critical)
        uncorrectable = drive_info.get("uncorrectable_errors", 0)
        if uncorrectable > 0:
            health_score -= min(20, uncorrectable * 2)

        # Check temperature (warning level)
        temperature = drive_info.get("temperature")
        if temperature:
            if temperature > 60:  # Very hot
                health_score -= 10
            elif temperature > 50:  # Hot
                health_score -= 5

        # Check power on hours (age factor)
        power_hours = drive_info.get("power_on_hours")
        if power_hours:
            # After 5 years (43800 hours), start reducing health
            if power_hours > 87600:  # 10+ years
                health_score -= 15
            elif power_hours > 43800:  # 5+ years
                health_score -= 5

        # Ensure health percentage is within bounds
        return max(0, min(100, health_score))

    except Exception as e:
        logger.warning(f"Error calculating health percentage: {e}")
        return 50  # Default to 50% if calculation fails


async def get_system_logs(
    device: str,
    service: str | None = None,
    since: str | None = None,
    timeout: int = 60,
    limit: int = 100,
    priority: str | None = None,
) -> dict[str, Any]:
    """
    Retrieve system logs from a specific device using OS-appropriate commands.

    This tool connects to a device via SSH and retrieves system logs using
    the appropriate command based on the device's OS type:
    - Ubuntu/systemd: journalctl  
    - Unraid/syslog: tail /var/log/syslog or dmesg
    
    Supports service-specific filtering, time-based filtering, and
    priority level filtering where applicable.

    Args:
        device: Device hostname or IP address to query
        service: Service name to filter logs (e.g., 'sshd', 'docker', 'nginx')
        since: Time range start (e.g., '2023-01-01', '1 hour ago', 'yesterday')
        timeout: Command timeout in seconds (default: 60)
        limit: Maximum number of log entries to return (default: 100)
        priority: Log priority level filter (e.g., 'err', 'warning', 'info', 'debug')

    Returns:
        Dict containing:
        - device: Device hostname
        - timestamp: Query timestamp (ISO 8601)
        - os_type: Detected OS type
        - log_source: Source of logs (journalctl, syslog, etc.)
        - service_filter: Applied service filter (if any)
        - since_filter: Applied time filter (if any)
        - log_count: Number of log entries returned
        - logs: List of log entries with parsed log data

    Raises:
        DeviceNotFoundError: If device cannot be reached
        SSHConnectionError: If SSH connection fails
        SSHCommandError: If log command fails
    """
    logger.info(f"Collecting system logs from device: {device}")

    try:
        # First, get device OS type from database
        from sqlalchemy import select

        from apps.backend.src.core.database import get_async_session
        from apps.backend.src.models.device import Device

        async with get_async_session() as db:
            result = await db.execute(select(Device.tags).where(Device.hostname == device))
            device_record = result.scalar_one_or_none()

        os_name = "unknown"
        if device_record and device_record.get('os_name'):
            os_name = device_record['os_name'].lower()

        # Create SSH connection info
        connection_info = SSHConnectionInfo(host=device, command_timeout=timeout)

        # Get SSH client
        ssh_client = get_ssh_client()

        # Determine command based on OS type
        if 'unraid' in os_name:
            # Unraid uses syslog - use tail to get recent entries
            cmd_parts = ["tail", f"-{limit}", "/var/log/syslog"]
            log_source = "syslog"
        else:
            # Default to journalctl for Ubuntu and other systemd systems
            cmd_parts = ["journalctl", "--output=json", f"--lines={limit}", "--no-pager"]
            log_source = "journalctl"

        # Add service filter (only for journalctl)
        if service and log_source == "journalctl":
            cmd_parts.append(f"--unit={service}")

        # Add time range filter (only for journalctl)
        if since and log_source == "journalctl":
            cmd_parts.append(f"--since={since}")

        # Add priority filter (only for journalctl)
        if priority and log_source == "journalctl":
            cmd_parts.append(f"--priority={priority}")

        # For syslog, add service filtering via grep if specified
        if service and log_source == "syslog":
            # Pipe through grep to filter by service
            cmd_parts.extend(["|", "grep", "-i", service])

        # Join command parts
        log_cmd = " ".join(cmd_parts)

        logger.debug(f"Executing {log_source} command on {device}: {log_cmd}")

        # Execute log command
        result = await ssh_client.execute_command(
            connection_info=connection_info, command=log_cmd, timeout=timeout, check=False
        )

        if not result.success:
            logger.error(f"{log_source} command failed on {device}: {result.stderr}")

            # Check for common errors
            error_msg = result.stderr.lower() if result.stderr else ""

            if log_source == "journalctl":
                if "unit" in error_msg and "not found" in error_msg:
                    return {
                        "device": device,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "os_type": os_name,
                        "log_source": log_source,
                        "service_filter": service,
                        "since_filter": since,
                        "log_count": 0,
                        "logs": [],
                        "error": f"Service '{service}' not found or not active",
                    }
                elif "invalid" in error_msg and "time" in error_msg:
                    return {
                        "device": device,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "os_type": os_name,
                        "log_source": log_source,
                        "service_filter": service,
                        "since_filter": since,
                        "log_count": 0,
                        "logs": [],
                        "error": f"Invalid time format: '{since}'",
                    }
            elif log_source == "syslog":
                if "no such file" in error_msg or "cannot open" in error_msg:
                    return {
                        "device": device,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "os_type": os_name,
                        "log_source": log_source,
                        "service_filter": service,
                        "since_filter": since,
                        "log_count": 0,
                        "logs": [],
                        "error": "Syslog file not found or not accessible",
                    }

            return {
                    "device": device,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "service_filter": service,
                    "since_filter": since,
                    "log_count": 0,
                    "logs": [],
                    "error": f"{log_source} failed: {result.stderr}",
                }

        # Parse log entries based on source
        log_entries = []
        lines = result.stdout.strip().split("\n")

        if log_source == "journalctl":
            # Parse JSON log entries from journalctl
            for line in lines:
                if line.strip():
                    try:
                        log_data = json.loads(line)
                        parsed_entry = _parse_journalctl_json_entry(log_data)
                        if parsed_entry:
                            log_entries.append(parsed_entry)
                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse JSON log line: {line[:100]}..., error: {e}")
                        continue
                    except Exception as e:
                        logger.debug(f"Error processing log entry: {e}")
                        continue

        elif log_source == "syslog":
            # Parse plain text syslog entries
            for line in lines:
                if line.strip():
                    try:
                        parsed_entry = _parse_syslog_line(line.strip())
                        if parsed_entry:
                            log_entries.append(parsed_entry)
                    except Exception as e:
                        logger.debug(f"Error processing syslog entry: {e}")
                        continue

        # Sort by timestamp (most recent first)
        log_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Prepare response
        response = {
            "device": device,
            "timestamp": datetime.now(UTC).isoformat(),
            "os_type": os_name,
            "log_source": log_source,
            "service_filter": service,
            "since_filter": since,
            "log_count": len(log_entries),
            "logs": log_entries,
        }

        logger.info(
            f"Successfully collected {len(log_entries)} log entries from {device}"
            f"{f' (service: {service})' if service else ''}"
            f"{f' (since: {since})' if since else ''}"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to collect system logs from {device}: {e}")

        # Check if it's a connection error
        if "connection" in str(e).lower() or "unreachable" in str(e).lower():
            raise DeviceNotFoundError(device, "hostname")

        # Return error response
        return {
            "device": device,
            "timestamp": datetime.now(UTC).isoformat(),
            "service_filter": service,
            "since_filter": since,
            "log_count": 0,
            "logs": [],
            "error": f"Failed to collect system logs: {str(e)}",
        }


def _parse_journalctl_json_entry(log_data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Parse a single journalctl JSON log entry into SystemLogEntry format.

    Args:
        log_data: Raw JSON log entry from journalctl --output=json

    Returns:
        Parsed log entry dict or None if parsing fails
    """
    try:
        # Extract timestamp - journalctl provides microsecond timestamp
        timestamp_us = log_data.get("__REALTIME_TIMESTAMP")
        if timestamp_us:
            # Convert microseconds to seconds and create datetime
            timestamp_s = int(timestamp_us) / 1000000
            dt = datetime.fromtimestamp(timestamp_s, tz=UTC)
            timestamp = dt.isoformat()
        else:
            # Fallback to current time if no timestamp
            timestamp = datetime.now(UTC).isoformat()

        # Extract hostname
        hostname = log_data.get("_HOSTNAME", "unknown")

        # Extract service/unit name
        service = (
            log_data.get("_SYSTEMD_UNIT", "")
            or log_data.get("SYSLOG_IDENTIFIER", "")
            or log_data.get("_COMM", "")
            or "unknown"
        )

        # Map priority number to string
        priority_num = log_data.get("PRIORITY", "6")  # Default to info
        priority_map = {
            "0": "emerg",  # Emergency
            "1": "alert",  # Alert
            "2": "crit",  # Critical
            "3": "err",  # Error
            "4": "warning",  # Warning
            "5": "notice",  # Notice
            "6": "info",  # Info
            "7": "debug",  # Debug
        }
        priority = priority_map.get(str(priority_num), "info")

        # Extract message
        message = log_data.get("MESSAGE", "")

        # Extract PID
        pid = str(log_data.get("_PID", ""))

        return {
            "timestamp": timestamp,
            "hostname": hostname,
            "service": service,
            "priority": priority,
            "message": message,
            "pid": pid,
        }

    except Exception as e:
        logger.debug(f"Error parsing journalctl entry: {e}")
        return None


def _parse_syslog_line(line: str) -> dict[str, Any] | None:
    """
    Parse a single syslog line into SystemLogEntry format.
    
    Example syslog line:
    Dec  7 10:30:15 tootie kernel: [12345.123456] Some kernel message
    
    Args:
        line: Raw syslog line
        
    Returns:
        Parsed log entry dict or None if parsing fails
    """
    try:
        from datetime import datetime
        import re

        # Regex to parse standard syslog format
        # Month Day Time Hostname Service[PID]: Message
        syslog_pattern = r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:\[]+)(?:\[(\d+)\])?:\s*(.+)$'

        match = re.match(syslog_pattern, line.strip())
        if not match:
            # Fallback for lines that don't match standard format
            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "hostname": "unknown",
                "service": "unknown",
                "priority": "info",
                "message": line.strip(),
                "pid": None,
            }

        date_str, hostname, service, pid, message = match.groups()

        # Parse timestamp (add current year since syslog doesn't include it)
        try:
            current_year = datetime.now().year
            full_date_str = f"{current_year} {date_str}"
            dt = datetime.strptime(full_date_str, "%Y %b %d %H:%M:%S")
            dt = dt.replace(tzinfo=UTC)
            timestamp = dt.isoformat()
        except ValueError:
            timestamp = datetime.now(UTC).isoformat()

        # Extract PID if present
        pid_int = int(pid) if pid else None

        return {
            "timestamp": timestamp,
            "hostname": hostname.strip(),
            "service": service.strip(),
            "priority": "info",  # Syslog doesn't easily provide priority in this format
            "message": message.strip(),
            "pid": pid_int,
        }

    except Exception as e:
        logger.debug(f"Error parsing syslog entry: {e}")
        return None


# Tool registration metadata for MCP server
METRICS_COLLECTION_TOOLS = {
    "get_system_info": {
        "name": "get_system_info",
        "description": "Collect system resource metrics from a specific device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
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
        "function": get_system_info,
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
    "get_system_logs": {
        "name": "get_system_logs",
        "description": "Retrieve system logs from a specific device using journalctl",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "service": {
                    "type": "string",
                    "description": "Service name to filter logs (e.g., 'sshd', 'docker', 'nginx')",
                    "optional": True,
                },
                "since": {
                    "type": "string",
                    "description": "Time range start (e.g., '2023-01-01', '1 hour ago', 'yesterday')",
                    "optional": True,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of log entries to return",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000,
                },
                "priority": {
                    "type": "string",
                    "description": "Log priority level filter (e.g., 'err', 'warning', 'info', 'debug')",
                    "optional": True,
                },
            },
            "required": ["device"],
        },
        "function": get_system_logs,
    },
}
