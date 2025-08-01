"""
System Monitoring MCP Tools

This module implements MCP tools for system performance monitoring,
resource usage analysis, and health checking across infrastructure devices.
"""

import logging
import re
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError, SSHConnectionError, SystemMonitoringError
)

logger = logging.getLogger(__name__)


async def get_system_info(
    device: str,
    include_processes: bool = False,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Get comprehensive system performance metrics from a device.
    
    This tool connects to a device via SSH and collects detailed system
    performance metrics including CPU usage, memory utilization, disk I/O,
    network statistics, and optionally top processes.
    
    Args:
        device: Device hostname or IP address
        include_processes: Include top processes information (default: False)
        timeout: Command timeout in seconds (default: 60)
        
    Returns:
        Dict containing:
        - cpu_metrics: CPU usage, load averages, core count
        - memory_metrics: RAM and swap usage statistics
        - disk_metrics: Disk usage and I/O statistics
        - network_metrics: Network interface statistics
        - system_info: Kernel, uptime, and system information
        - processes: Top processes (if requested)
        - timestamp: Collection timestamp
        
    Raises:
        DeviceNotFoundError: If device cannot be reached
        SystemMonitoringError: If metric collection fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Collecting system metrics from device: {device}")
    
    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(
            host=device,
            command_timeout=timeout
        )
        
        # Get SSH client
        ssh_client = get_ssh_client()
        
        # Initialize metric containers
        cpu_metrics = {}
        memory_metrics = {}
        disk_metrics = {}
        network_metrics = {}
        system_info = {}
        processes = []
        
        # Collect CPU metrics
        try:
            # CPU usage from /proc/stat
            cpu_result = await ssh_client.execute_command(
                connection_info,
                "cat /proc/stat | head -1",
                timeout=10
            )
            if cpu_result.return_code == 0:
                cpu_line = cpu_result.stdout.strip()
                cpu_values = cpu_line.split()[1:]  # Skip 'cpu' label
                if len(cpu_values) >= 7:
                    user, nice, system, idle, iowait, irq, softirq = map(int, cpu_values[:7])
                    total = sum([user, nice, system, idle, iowait, irq, softirq])
                    
                    cpu_metrics.update({
                        "user_percent": round((user / total) * 100, 2),
                        "system_percent": round((system / total) * 100, 2),
                        "idle_percent": round((idle / total) * 100, 2),
                        "iowait_percent": round((iowait / total) * 100, 2),
                        "usage_percent": round(((total - idle) / total) * 100, 2)
                    })
            
            # Load averages
            load_result = await ssh_client.execute_command(
                connection_info,
                "cat /proc/loadavg",
                timeout=10
            )
            if load_result.return_code == 0:
                load_values = load_result.stdout.strip().split()
                if len(load_values) >= 3:
                    cpu_metrics.update({
                        "load_1min": float(load_values[0]),
                        "load_5min": float(load_values[1]),
                        "load_15min": float(load_values[2])
                    })
            
            # CPU count
            cpu_count_result = await ssh_client.execute_command(
                connection_info,
                "nproc",
                timeout=10
            )
            if cpu_count_result.return_code == 0:
                cpu_metrics["core_count"] = int(cpu_count_result.stdout.strip())
            
        except Exception as e:
            logger.warning(f"Failed to collect CPU metrics: {e}")
            cpu_metrics["error"] = str(e)
        
        # Collect memory metrics
        try:
            mem_result = await ssh_client.execute_command(
                connection_info,
                "cat /proc/meminfo",
                timeout=10
            )
            if mem_result.return_code == 0:
                mem_info = {}
                for line in mem_result.stdout.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        # Extract numeric value (remove 'kB' unit)
                        value_match = re.search(r'(\d+)', value.strip())
                        if value_match:
                            mem_info[key.strip()] = int(value_match.group(1))
                
                if 'MemTotal' in mem_info and 'MemAvailable' in mem_info:
                    total_kb = mem_info['MemTotal']
                    available_kb = mem_info['MemAvailable']
                    used_kb = total_kb - available_kb
                    
                    memory_metrics.update({
                        "total_mb": round(total_kb / 1024, 2),
                        "used_mb": round(used_kb / 1024, 2),
                        "available_mb": round(available_kb / 1024, 2),
                        "usage_percent": round((used_kb / total_kb) * 100, 2),
                        "cached_mb": round(mem_info.get('Cached', 0) / 1024, 2),
                        "buffers_mb": round(mem_info.get('Buffers', 0) / 1024, 2)
                    })
                
                # Swap information
                if 'SwapTotal' in mem_info:
                    swap_total_kb = mem_info['SwapTotal']
                    swap_free_kb = mem_info.get('SwapFree', 0)
                    swap_used_kb = swap_total_kb - swap_free_kb
                    
                    memory_metrics.update({
                        "swap_total_mb": round(swap_total_kb / 1024, 2),
                        "swap_used_mb": round(swap_used_kb / 1024, 2),
                        "swap_usage_percent": round((swap_used_kb / swap_total_kb) * 100, 2) if swap_total_kb > 0 else 0
                    })
                    
        except Exception as e:
            logger.warning(f"Failed to collect memory metrics: {e}")
            memory_metrics["error"] = str(e)
        
        # Collect disk metrics
        try:
            # Disk usage for all mounted filesystems
            df_result = await ssh_client.execute_command(
                connection_info,
                "df -h --output=source,size,used,avail,pcent,target | grep -E '^/dev/'",
                timeout=15
            )
            if df_result.return_code == 0:
                filesystems = []
                for line in df_result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 6:
                            filesystem = {
                                "device": parts[0],
                                "size": parts[1],
                                "used": parts[2],
                                "available": parts[3],
                                "usage_percent": int(parts[4].rstrip('%')),
                                "mount_point": parts[5]
                            }
                            filesystems.append(filesystem)
                disk_metrics["filesystems"] = filesystems
            
            # Disk I/O statistics
            iostat_result = await ssh_client.execute_command(
                connection_info,
                "cat /proc/diskstats",
                timeout=10
            )
            if iostat_result.return_code == 0:
                disk_io = []
                for line in iostat_result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 14 and not parts[2].startswith('loop'):
                        device_name = parts[2]
                        reads_completed = int(parts[3])
                        reads_merged = int(parts[4])
                        sectors_read = int(parts[5])
                        writes_completed = int(parts[7])
                        writes_merged = int(parts[8])
                        sectors_written = int(parts[9])
                        
                        disk_io.append({
                            "device": device_name,
                            "reads_completed": reads_completed,
                            "reads_merged": reads_merged,
                            "sectors_read": sectors_read,
                            "writes_completed": writes_completed,
                            "writes_merged": writes_merged,
                            "sectors_written": sectors_written
                        })
                disk_metrics["io_stats"] = disk_io
                
        except Exception as e:
            logger.warning(f"Failed to collect disk metrics: {e}")
            disk_metrics["error"] = str(e)
        
        # Collect network metrics
        try:
            net_result = await ssh_client.execute_command(
                connection_info,
                "cat /proc/net/dev",
                timeout=10
            )
            if net_result.return_code == 0:
                interfaces = []
                lines = net_result.stdout.strip().split('\n')[2:]  # Skip header lines
                for line in lines:
                    if ':' in line:
                        interface_name, stats = line.split(':', 1)
                        interface_name = interface_name.strip()
                        stats = stats.split()
                        
                        if len(stats) >= 16:
                            interface_stats = {
                                "interface": interface_name,
                                "rx_bytes": int(stats[0]),
                                "rx_packets": int(stats[1]),
                                "rx_errors": int(stats[2]),
                                "rx_dropped": int(stats[3]),
                                "tx_bytes": int(stats[8]),
                                "tx_packets": int(stats[9]),
                                "tx_errors": int(stats[10]),
                                "tx_dropped": int(stats[11])
                            }
                            interfaces.append(interface_stats)
                network_metrics["interfaces"] = interfaces
                
        except Exception as e:
            logger.warning(f"Failed to collect network metrics: {e}")
            network_metrics["error"] = str(e)
        
        # Collect system information
        try:
            # Kernel and system info
            uname_result = await ssh_client.execute_command(
                connection_info,
                "uname -a",
                timeout=10
            )
            if uname_result.return_code == 0:
                system_info["kernel"] = uname_result.stdout.strip()
            
            # Uptime
            uptime_result = await ssh_client.execute_command(
                connection_info,
                "cat /proc/uptime",
                timeout=10
            )
            if uptime_result.return_code == 0:
                uptime_seconds = float(uptime_result.stdout.split()[0])
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                system_info["uptime"] = {
                    "seconds_total": uptime_seconds,
                    "days": days,
                    "hours": hours,
                    "minutes": minutes,
                    "formatted": f"{days}d {hours}h {minutes}m"
                }
            
            # Boot time
            boot_time_result = await ssh_client.execute_command(
                connection_info,
                "stat -c %Y /proc/1",
                timeout=10
            )
            if boot_time_result.return_code == 0:
                boot_timestamp = int(boot_time_result.stdout.strip())
                boot_time = datetime.fromtimestamp(boot_timestamp, tz=timezone.utc)
                system_info["boot_time"] = boot_time.isoformat()
                
        except Exception as e:
            logger.warning(f"Failed to collect system info: {e}")
            system_info["error"] = str(e)
        
        # Collect top processes if requested
        if include_processes:
            try:
                top_result = await ssh_client.execute_command(
                    connection_info,
                    "ps aux --sort=-%cpu | head -11",  # Top 10 processes + header
                    timeout=15
                )
                if top_result.return_code == 0:
                    lines = top_result.stdout.strip().split('\n')[1:]  # Skip header
                    for line in lines:
                        parts = line.split(None, 10)  # Split into max 11 parts
                        if len(parts) >= 11:
                            process = {
                                "user": parts[0],
                                "pid": int(parts[1]),
                                "cpu_percent": float(parts[2]),
                                "memory_percent": float(parts[3]),
                                "vsz_kb": int(parts[4]),
                                "rss_kb": int(parts[5]),
                                "tty": parts[6],
                                "stat": parts[7],
                                "start": parts[8],
                                "time": parts[9],
                                "command": parts[10]
                            }
                            processes.append(process)
                            
            except Exception as e:
                logger.warning(f"Failed to collect process info: {e}")
                processes = [{"error": str(e)}]
        
        # Prepare response
        response = {
            "cpu_metrics": cpu_metrics,
            "memory_metrics": memory_metrics,
            "disk_metrics": disk_metrics,
            "network_metrics": network_metrics,
            "system_info": system_info,
            "processes": processes if include_processes else None,
            "device_info": {
                "hostname": device,
                "connection_successful": True
            },
            "collection_info": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "include_processes": include_processes,
                "timeout_seconds": timeout
            }
        }
        
        logger.info(f"Collected system metrics from {device}")
        return response
        
    except Exception as e:
        logger.error(f"Error collecting system metrics from {device}: {e}")
        raise SystemMonitoringError(
            message=f"Failed to collect system metrics: {str(e)}",
            device=device,
            operation="get_system_info",
            details={"error": str(e)}
        )


async def get_drive_health(
    device: str,
    drive: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Get S.M.A.R.T. drive health information and disk status.
    
    This tool connects to a device via SSH and retrieves S.M.A.R.T. health
    data for storage drives, including temperature, error counts, and
    overall health status. Supports both specific drive queries and all drives.
    
    Args:
        device: Device hostname or IP address
        drive: Specific drive to check (e.g., '/dev/sda') or None for all
        timeout: Command timeout in seconds (default: 60)
        
    Returns:
        Dict containing:
        - drives: List of drive health information
        - smart_available: Whether S.M.A.R.T. tools are available
        - summary: Overall drive health summary
        - device_info: Device connection information
        - timestamp: Check timestamp
        
    Raises:
        DeviceNotFoundError: If device cannot be reached
        SystemMonitoringError: If drive health check fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Checking drive health on device: {device}")
    
    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(
            host=device,
            command_timeout=timeout
        )
        
        # Get SSH client
        ssh_client = get_ssh_client()
        
        # Check if smartctl is available
        smart_available = False
        smartctl_result = await ssh_client.execute_command(
            connection_info,
            "which smartctl",
            timeout=10
        )
        smart_available = smartctl_result.return_code == 0
        
        drives_info = []
        
        if drive:
            # Check specific drive
            drives_to_check = [drive]
        else:
            # Find all available drives
            drives_to_check = []
            
            # List block devices
            lsblk_result = await ssh_client.execute_command(
                connection_info,
                "lsblk -d -n -o NAME,TYPE | grep disk",
                timeout=15
            )
            if lsblk_result.return_code == 0:
                for line in lsblk_result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] == 'disk':
                            drive_name = f"/dev/{parts[0]}"
                            drives_to_check.append(drive_name)
        
        # Check each drive
        for drive_path in drives_to_check:
            drive_info = {
                "device": drive_path,
                "health_status": "unknown",
                "smart_available": smart_available,
                "temperature": None,
                "power_on_hours": None,
                "power_cycle_count": None,
                "reallocated_sectors": None,
                "pending_sectors": None,
                "uncorrectable_errors": None,
                "smart_attributes": {},
                "errors": []
            }
            
            try:
                # Get basic drive info
                drive_info_result = await ssh_client.execute_command(
                    connection_info,
                    f"lsblk {drive_path} -o NAME,SIZE,MODEL,SERIAL -n",
                    timeout=10
                )
                if drive_info_result.return_code == 0:
                    info_parts = drive_info_result.stdout.strip().split(None, 3)
                    if len(info_parts) >= 2:
                        drive_info["size"] = info_parts[1]
                        if len(info_parts) >= 3:
                            drive_info["model"] = info_parts[2]
                        if len(info_parts) >= 4:
                            drive_info["serial"] = info_parts[3]
                
                # Get S.M.A.R.T. information if available
                if smart_available:
                    try:
                        # Get overall health status
                        health_result = await ssh_client.execute_command(
                            connection_info,
                            f"smartctl -H {drive_path}",
                            timeout=15
                        )
                        if health_result.return_code == 0:
                            health_output = health_result.stdout.lower()
                            if "passed" in health_output:
                                drive_info["health_status"] = "healthy"
                            elif "failed" in health_output:
                                drive_info["health_status"] = "failed"
                            else:
                                drive_info["health_status"] = "unknown"
                        
                        # Get detailed S.M.A.R.T. attributes
                        smart_result = await ssh_client.execute_command(
                            connection_info,
                            f"smartctl -A {drive_path}",
                            timeout=20
                        )
                        if smart_result.return_code == 0:
                            smart_attributes = {}
                            
                            # Parse S.M.A.R.T. attributes table
                            lines = smart_result.stdout.split('\n')
                            in_attributes = False
                            
                            for line in lines:
                                if 'ID#' in line and 'ATTRIBUTE_NAME' in line:
                                    in_attributes = True
                                    continue
                                
                                if in_attributes and line.strip():
                                    parts = line.split()
                                    if len(parts) >= 10:
                                        attr_id = parts[0]
                                        attr_name = parts[1]
                                        raw_value = parts[9]
                                        
                                        smart_attributes[attr_name] = {
                                            "id": attr_id,
                                            "raw_value": raw_value,
                                            "normalized_value": parts[3] if len(parts) > 3 else None
                                        }
                                        
                                        # Extract key metrics
                                        if attr_name == "Temperature_Celsius":
                                            try:
                                                temp_match = re.search(r'(\d+)', raw_value)
                                                if temp_match:
                                                    drive_info["temperature"] = int(temp_match.group(1))
                                            except:
                                                pass
                                        elif attr_name == "Power_On_Hours":
                                            try:
                                                drive_info["power_on_hours"] = int(raw_value)
                                            except:
                                                pass
                                        elif attr_name == "Power_Cycle_Count":
                                            try:
                                                drive_info["power_cycle_count"] = int(raw_value)
                                            except:
                                                pass
                                        elif attr_name == "Reallocated_Sector_Ct":
                                            try:
                                                drive_info["reallocated_sectors"] = int(raw_value)
                                            except:
                                                pass
                                        elif attr_name == "Current_Pending_Sector":
                                            try:
                                                drive_info["pending_sectors"] = int(raw_value)
                                            except:
                                                pass
                                        elif attr_name == "Offline_Uncorrectable":
                                            try:
                                                drive_info["uncorrectable_errors"] = int(raw_value)
                                            except:
                                                pass
                            
                            drive_info["smart_attributes"] = smart_attributes
                            
                    except Exception as e:
                        drive_info["errors"].append(f"S.M.A.R.T. query failed: {str(e)}")
                        logger.warning(f"S.M.A.R.T. query failed for {drive_path}: {e}")
                
                
            except Exception as e:
                drive_info["errors"].append(f"Drive check failed: {str(e)}")
                logger.warning(f"Drive check failed for {drive_path}: {e}")
            
            drives_info.append(drive_info)
        
        # Generate summary
        total_drives = len(drives_info)
        healthy_drives = sum(1 for d in drives_info if d["health_status"] == "healthy")
        failed_drives = sum(1 for d in drives_info if d["health_status"] == "failed")
        unknown_drives = sum(1 for d in drives_info if d["health_status"] == "unknown")
        
        summary = {
            "total_drives": total_drives,
            "healthy_drives": healthy_drives,
            "failed_drives": failed_drives,
            "unknown_drives": unknown_drives,
            "overall_status": "healthy" if failed_drives == 0 and healthy_drives > 0 else ("failed" if failed_drives > 0 else "unknown"),
            "smart_capable_drives": sum(1 for d in drives_info if d["smart_available"]),
            "average_temperature": None
        }
        
        # Calculate average temperature
        temps = [d["temperature"] for d in drives_info if d["temperature"] is not None]
        if temps:
            summary["average_temperature"] = round(sum(temps) / len(temps), 1)
        
        # Prepare response
        response = {
            "drives": drives_info,
            "smart_available": smart_available,
            "summary": summary,
            "device_info": {
                "hostname": device,
                "connection_successful": True,
                "smartctl_installed": smart_available
            },
            "query_info": {
                "specific_drive": drive,
                "drives_checked": len(drives_to_check),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        logger.info(
            f"Checked {total_drives} drives on {device} "
            f"(Healthy: {healthy_drives}, Failed: {failed_drives}, Unknown: {unknown_drives})"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error checking drive health on {device}: {e}")
        raise SystemMonitoringError(
            message=f"Failed to check drive health: {str(e)}",
            device=device,
            operation="get_drive_health",
            details={"error": str(e), "drive": drive}
        )


async def get_system_logs(
    device: str,
    service: Optional[str] = None,
    since: Optional[str] = None,
    lines: int = 100,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Get system logs from journald or traditional syslog.
    
    This tool connects to a device via SSH and retrieves system logs
    using journalctl (systemd) or traditional log files. Supports filtering
    by service, time range, and line limits.
    
    Args:
        device: Device hostname or IP address
        service: Specific service to get logs for (e.g., 'docker', 'nginx')
        since: Get logs since timestamp/duration (e.g., '2h', '1d', '2023-01-01 10:00:00')
        lines: Number of log lines to retrieve (default: 100)
        timeout: Command timeout in seconds (default: 60)
        
    Returns:
        Dict containing:
        - logs: List of log entries with timestamps and content
        - log_source: Source of logs (journald or syslog)
        - service_info: Service-specific information
        - log_metadata: Log retrieval metadata and statistics
        - device_info: Device connection information
        - timestamp: Query timestamp
        
    Raises:
        DeviceNotFoundError: If device cannot be reached
        SystemMonitoringError: If log retrieval fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Retrieving system logs from device: {device}")
    
    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(
            host=device,
            command_timeout=timeout
        )
        
        # Get SSH client
        ssh_client = get_ssh_client()
        
        # Skip journalctl and use syslog directly to avoid timestamp parsing issues
        journald_available = False  # Force use of traditional syslog
        
        log_entries = []
        log_source = "unknown"
        service_info = {}
        
        if journald_available:
            log_source = "journald"
            
            # Build journalctl command
            cmd_parts = ["journalctl", "--no-pager", "--output=json"]
            
            if service:
                cmd_parts.extend(["-u", service])
                
            if since:
                cmd_parts.extend(["--since", f'"{since}"'])
                
            if lines:
                cmd_parts.extend(["-n", str(lines)])
            
            journalctl_cmd = " ".join(cmd_parts)
            
            try:
                logs_result = await ssh_client.execute_command(
                    connection_info,
                    journalctl_cmd,
                    timeout=timeout
                )
                
                if logs_result.return_code == 0:
                    # Parse JSON output from journalctl
                    for line in logs_result.stdout.strip().split('\n'):
                        if line.strip():
                            try:
                                log_entry = json.loads(line)
                                
                                # Extract relevant fields
                                entry = {
                                    "timestamp": log_entry.get("__REALTIME_TIMESTAMP"),
                                    "hostname": log_entry.get("_HOSTNAME", device),
                                    "service": log_entry.get("_SYSTEMD_UNIT", log_entry.get("SYSLOG_IDENTIFIER", "unknown")),
                                    "pid": log_entry.get("_PID"),
                                    "priority": log_entry.get("PRIORITY"),
                                    "message": log_entry.get("MESSAGE", ""),
                                    "boot_id": log_entry.get("_BOOT_ID")
                                }
                                
                                # Convert timestamp to ISO format
                                if entry["timestamp"]:
                                    try:
                                        # Systemd timestamp is in microseconds
                                        timestamp_seconds = int(entry["timestamp"]) / 1000000
                                        dt = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
                                        entry["timestamp"] = dt.isoformat()
                                    except:
                                        pass
                                
                                # Determine log level from priority
                                priority = entry.get("priority")
                                if priority is not None:
                                    try:
                                        priority_int = int(priority)
                                        if priority_int <= 3:
                                            entry["level"] = "error"
                                        elif priority_int <= 4:
                                            entry["level"] = "warning"
                                        elif priority_int <= 6:
                                            entry["level"] = "info"
                                        else:
                                            entry["level"] = "debug"
                                    except:
                                        entry["level"] = "unknown"
                                else:
                                    entry["level"] = "unknown"
                                
                                log_entries.append(entry)
                                
                            except json.JSONDecodeError:
                                # Handle non-JSON lines
                                log_entries.append({
                                    "timestamp": None,
                                    "hostname": device,
                                    "service": "unknown",
                                    "message": line.strip(),
                                    "level": "unknown",
                                    "raw_line": True
                                })
                
                # Get service information if specific service requested
                if service and logs_result.return_code == 0:
                    try:
                        service_status_result = await ssh_client.execute_command(
                            connection_info,
                            f"systemctl status {service} --no-pager",
                            timeout=15
                        )
                        if service_status_result.return_code == 0:
                            status_lines = service_status_result.stdout.strip().split('\n')
                            for line in status_lines:
                                if 'Active:' in line:
                                    service_info["status"] = line.split('Active:', 1)[1].strip()
                                elif 'Main PID:' in line:
                                    service_info["main_pid"] = line.split('Main PID:', 1)[1].strip()
                                elif 'Memory:' in line:
                                    service_info["memory_usage"] = line.split('Memory:', 1)[1].strip()
                    except Exception as e:
                        service_info["error"] = f"Failed to get service status: {str(e)}"
                        
            except Exception as e:
                logger.warning(f"Journalctl failed: {e}")
                # Fall back to traditional syslog
                journald_available = False
        
        # Fall back to traditional syslog if journald not available or failed
        if not journald_available or not log_entries:
            log_source = "syslog"
            
            # Try common syslog locations
            syslog_paths = ["/var/log/syslog", "/var/log/messages"]
            
            for syslog_path in syslog_paths:
                try:
                    # Check if log file exists
                    test_result = await ssh_client.execute_command(
                        connection_info,
                        f"test -f {syslog_path}",
                        timeout=5
                    )
                    
                    if test_result.return_code == 0:
                        # Build tail command
                        cmd_parts = ["tail", "-n", str(lines), syslog_path]
                        
                        if service:
                            # Filter by service using grep
                            cmd_parts = ["tail", "-n", str(lines * 5), syslog_path, "|", "grep", service, "|", "tail", "-n", str(lines)]
                        
                        tail_cmd = " ".join(cmd_parts)
                        
                        logs_result = await ssh_client.execute_command(
                            connection_info,
                            tail_cmd,
                            timeout=timeout
                        )
                        
                        if logs_result.return_code == 0:
                            # Parse traditional syslog format
                            for line in logs_result.stdout.strip().split('\n'):
                                if line.strip():
                                    # Try to parse syslog format: timestamp hostname service[pid]: message
                                    log_match = re.match(
                                        r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:\[\]]+)(?:\[(\d+)\])?\s*:\s*(.*)$',
                                        line
                                    )
                                    
                                    if log_match:
                                        timestamp_str, hostname, service_name, pid, message = log_match.groups()
                                        
                                        # Parse timestamp (add current year as syslog doesn't include it)
                                        try:
                                            current_year = datetime.now().year
                                            full_timestamp = f"{current_year} {timestamp_str}"
                                            dt = datetime.strptime(full_timestamp, "%Y %b %d %H:%M:%S")
                                            dt = dt.replace(tzinfo=timezone.utc)
                                            iso_timestamp = dt.isoformat()
                                        except:
                                            iso_timestamp = timestamp_str
                                        
                                        # Determine log level from message content
                                        message_lower = message.lower()
                                        if any(word in message_lower for word in ['error', 'err', 'fail', 'fatal']):
                                            level = "error"
                                        elif any(word in message_lower for word in ['warn', 'warning']):
                                            level = "warning"
                                        elif any(word in message_lower for word in ['info', 'notice']):
                                            level = "info"
                                        else:
                                            level = "debug"
                                        
                                        entry = {
                                            "timestamp": iso_timestamp,
                                            "hostname": hostname,
                                            "service": service_name,
                                            "pid": int(pid) if pid else None,
                                            "message": message.strip(),
                                            "level": level,
                                            "source_file": syslog_path
                                        }
                                        log_entries.append(entry)
                                    else:
                                        # Handle unparseable lines
                                        log_entries.append({
                                            "timestamp": None,
                                            "hostname": device,
                                            "service": "unknown",
                                            "message": line.strip(),
                                            "level": "unknown",
                                            "raw_line": True,
                                            "source_file": syslog_path
                                        })
                            break  # Exit loop if we successfully got logs
                            
                except Exception as e:
                    logger.debug(f"Failed to read {syslog_path}: {e}")
                    continue
        
        # Calculate log statistics
        total_entries = len(log_entries)
        level_counts = {}
        service_counts = {}
        
        for entry in log_entries:
            level = entry.get("level", "unknown")
            level_counts[level] = level_counts.get(level, 0) + 1
            
            service = entry.get("service", "unknown")
            service_counts[service] = service_counts.get(service, 0) + 1
        
        # Find time range
        timestamped_entries = [e for e in log_entries if e.get("timestamp") and not e.get("raw_line")]
        first_timestamp = None
        last_timestamp = None
        
        if timestamped_entries:
            try:
                timestamps = [
                    datetime.fromisoformat(e["timestamp"]) 
                    for e in timestamped_entries
                    if e["timestamp"]
                ]
                if timestamps:
                    first_timestamp = min(timestamps).isoformat()
                    last_timestamp = max(timestamps).isoformat()
            except Exception as e:
                logger.debug(f"Failed to calculate time range: {e}")
        
        # Prepare response
        response = {
            "logs": log_entries,
            "log_source": log_source,
            "service_info": service_info,
            "log_metadata": {
                "total_entries": total_entries,
                "level_counts": level_counts,
                "service_counts": service_counts,
                "first_timestamp": first_timestamp,
                "last_timestamp": last_timestamp,
                "has_timestamps": len(timestamped_entries) > 0
            },
            "device_info": {
                "hostname": device,
                "connection_successful": True,
                "journald_available": journald_available
            },
            "query_info": {
                "service_filter": service,
                "since_filter": since,
                "lines_requested": lines,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        logger.info(
            f"Retrieved {total_entries} log entries from {device} "
            f"(Source: {log_source}, Levels: {level_counts})"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving system logs from {device}: {e}")
        raise SystemMonitoringError(
            message=f"Failed to retrieve system logs: {str(e)}",
            device=device,
            operation="get_system_logs",
            details={
                "error": str(e),
                "service": service,
                "since": since,
                "lines": lines
            }
        )


async def get_drive_stats(
    device: str,
    drive: str | None = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Get drive usage statistics, I/O performance, and utilization metrics.
    
    This tool focuses on drive performance and usage data including I/O statistics,
    throughput, utilization percentages, queue depths, and filesystem usage.
    This is separate from drive health monitoring (S.M.A.R.T. data).
    
    Args:
        device: Device hostname or IP address
        drive: Specific drive to check (e.g., 'sda') or None for all drives
        timeout: Command timeout in seconds (default: 60)
        
    Returns:
        Dict containing:
        - drives: List of drive usage and performance statistics
        - filesystem_usage: Filesystem usage statistics for mounted drives
        - io_performance: I/O performance metrics
        - summary: Overall drive usage summary
        - device_info: Device connection information
        - timestamp: Collection timestamp
        
    Raises:
        DeviceNotFoundError: If device cannot be reached
        SystemMonitoringError: If drive stats collection fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Collecting drive usage statistics from device: {device}")
    
    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(
            host=device,
            command_timeout=timeout
        )
        
        # Get SSH client
        ssh_client = get_ssh_client()
        
        drives_stats = []
        filesystem_usage = []
        
        if drive:
            # Check specific drive
            drives_to_check = [drive]
        else:
            # Find all available drives
            drives_to_check = []
            
            # List block devices (exclude loop devices)
            lsblk_result = await ssh_client.execute_command(
                connection_info,
                "lsblk -d -n -o NAME,TYPE | grep disk",
                timeout=15
            )
            if lsblk_result.return_code == 0:
                for line in lsblk_result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] == 'disk':
                            drives_to_check.append(parts[0])
        
        # Collect I/O statistics from /proc/diskstats
        try:
            diskstats_result = await ssh_client.execute_command(
                connection_info,
                "cat /proc/diskstats",
                timeout=10
            )
            diskstats_data = {}
            if diskstats_result.return_code == 0:
                for line in diskstats_result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 14:
                        device_name = parts[2]
                        # Skip loop and partition devices for main stats
                        if not device_name.startswith('loop') and not any(device_name.endswith(str(i)) for i in range(10)):
                            diskstats_data[device_name] = {
                                "reads_completed": int(parts[3]),
                                "reads_merged": int(parts[4]),
                                "sectors_read": int(parts[5]),
                                "time_reading_ms": int(parts[6]),
                                "writes_completed": int(parts[7]),
                                "writes_merged": int(parts[8]),
                                "sectors_written": int(parts[9]),
                                "time_writing_ms": int(parts[10]),
                                "io_in_progress": int(parts[11]),
                                "time_io_ms": int(parts[12]),
                                "weighted_time_io_ms": int(parts[13])
                            }
        except Exception as e:
            logger.warning(f"Failed to collect diskstats: {e}")
            diskstats_data = {}
        
        # Collect filesystem information first
        try:
            # Get filesystem types and mount information
            mount_result = await ssh_client.execute_command(
                connection_info,
                "findmnt -D -o SOURCE,TARGET,FSTYPE,SIZE,USED,AVAIL,USE% -t ext4,xfs,btrfs,zfs,ntfs,vfat,exfat",
                timeout=15
            )
            filesystem_info = {}
            if mount_result.return_code == 0:
                lines = mount_result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 7:
                            source = parts[0]
                            target = parts[1]
                            fstype = parts[2]
                            filesystem_info[source] = {
                                "mount_point": target,
                                "filesystem_type": fstype,
                                "size": parts[3] if parts[3] != '-' else None,
                                "used": parts[4] if parts[4] != '-' else None,
                                "available": parts[5] if parts[5] != '-' else None,
                                "usage_percent": parts[6] if parts[6] != '-' else None
                            }
        except Exception as e:
            logger.warning(f"Failed to collect filesystem info: {e}")
            filesystem_info = {}

        # Check each drive for usage statistics
        for drive_name in drives_to_check:
            drive_path = f"/dev/{drive_name}"
            drive_stats = {
                "device": drive_name,
                "device_path": drive_path,
                "io_stats": {},
                "utilization": {},
                "errors": []
            }
            
            try:
                # Get basic drive information
                drive_info_result = await ssh_client.execute_command(
                    connection_info,
                    f"lsblk {drive_path} -o NAME,SIZE,TYPE,MOUNTPOINT -n",
                    timeout=10
                )
                if drive_info_result.return_code == 0:
                    lines = drive_info_result.stdout.strip().split('\n')
                    if lines:
                        info_parts = lines[0].split(None, 3)
                        if len(info_parts) >= 2:
                            drive_stats["size"] = info_parts[1]
                            drive_stats["type"] = info_parts[2] if len(info_parts) >= 3 else "disk"
                
                # Add I/O statistics from diskstats
                if drive_name in diskstats_data:
                    io_data = diskstats_data[drive_name]
                    drive_stats["io_stats"] = {
                        "reads_completed": io_data["reads_completed"],
                        "reads_merged": io_data["reads_merged"],
                        "sectors_read": io_data["sectors_read"],
                        "kb_read": io_data["sectors_read"] * 512 // 1024,  # Convert sectors to KB
                        "time_reading_ms": io_data["time_reading_ms"],
                        "writes_completed": io_data["writes_completed"],
                        "writes_merged": io_data["writes_merged"],
                        "sectors_written": io_data["sectors_written"],
                        "kb_written": io_data["sectors_written"] * 512 // 1024,  # Convert sectors to KB
                        "time_writing_ms": io_data["time_writing_ms"],
                        "io_in_progress": io_data["io_in_progress"],
                        "time_io_ms": io_data["time_io_ms"],
                        "weighted_time_io_ms": io_data["weighted_time_io_ms"]
                    }
                    
                    # Calculate utilization percentages (simplified)
                    total_io_time = io_data["time_io_ms"]
                    if total_io_time > 0:
                        read_percentage = (io_data["time_reading_ms"] / total_io_time) * 100
                        write_percentage = (io_data["time_writing_ms"] / total_io_time) * 100
                        drive_stats["utilization"] = {
                            "read_percentage": round(read_percentage, 2),
                            "write_percentage": round(write_percentage, 2),
                            "total_io_time_ms": total_io_time,
                            "average_queue_size": round(io_data["weighted_time_io_ms"] / max(total_io_time, 1), 2)
                        }
                
                # Get iostat-style current performance if available
                try:
                    iostat_result = await ssh_client.execute_command(
                        connection_info,
                        f"iostat -x {drive_name} 1 2 | tail -1",
                        timeout=15
                    )
                    if iostat_result.return_code == 0 and iostat_result.stdout.strip():
                        iostat_line = iostat_result.stdout.strip()
                        iostat_parts = iostat_line.split()
                        if len(iostat_parts) >= 10:
                            drive_stats["current_performance"] = {
                                "utilization_percent": float(iostat_parts[-1]) if iostat_parts[-1] != '-' else 0.0,
                                "avg_queue_size": float(iostat_parts[-2]) if iostat_parts[-2] != '-' else 0.0,
                                "await_ms": float(iostat_parts[-3]) if iostat_parts[-3] != '-' else 0.0,
                                "r_await_ms": float(iostat_parts[-5]) if iostat_parts[-5] != '-' else 0.0,
                                "w_await_ms": float(iostat_parts[-4]) if iostat_parts[-4] != '-' else 0.0
                            }
                except Exception as e:
                    # iostat might not be available, that's okay
                    logger.debug(f"iostat not available for {drive_name}: {e}")
                
                # Collect SMART data if available
                try:
                    # Try smartctl for detailed drive information (try sudo first, then without)
                    smart_result = await ssh_client.execute_command(
                        connection_info,
                        f"sudo smartctl -a {drive_path} 2>/dev/null || smartctl -a {drive_path} 2>/dev/null || echo 'SMART_NOT_AVAILABLE'",
                        timeout=15
                    )
                    if smart_result.return_code == 0 and "SMART_NOT_AVAILABLE" not in smart_result.stdout:
                        smart_output = smart_result.stdout
                        smart_data = {}
                        
                        # Parse key SMART attributes
                        for line in smart_output.split('\n'):
                            line = line.strip()
                            
                            # Power on hours (traditional SMART and NVMe)
                            if 'Power_On_Hours' in line or 'Power On Hours' in line or 'Power on Hours:' in line:
                                parts = line.split()
                                for i, part in enumerate(parts):
                                    if part.replace(',', '').isdigit() and i > 0:
                                        smart_data["power_on_hours"] = int(part.replace(',', ''))
                                        break
                            
                            # Temperature
                            elif 'Temperature_Celsius' in line or 'Temperature' in line and 'Celsius' in line:
                                parts = line.split()
                                for part in parts:
                                    if part.isdigit() and int(part) < 100:  # Reasonable temp range
                                        smart_data["temperature_celsius"] = int(part)
                                        break
                            
                            # Wear leveling (SSD)
                            elif 'Wear_Leveling_Count' in line:
                                parts = line.split()
                                for i, part in enumerate(parts):
                                    if part.isdigit() and i > 5:  # Raw value is usually last
                                        smart_data["wear_leveling_count"] = int(part)
                                        break
                            
                            # Data units written (NVMe)
                            elif 'Data Units Written:' in line:
                                parts = line.split()
                                if len(parts) >= 4:
                                    try:
                                        value = float(parts[3].replace(',', ''))
                                        smart_data["data_units_written"] = value
                                    except ValueError:
                                        pass
                            
                            # Data units read (NVMe)
                            elif 'Data Units Read:' in line:
                                parts = line.split()
                                if len(parts) >= 4:
                                    try:
                                        value = float(parts[3].replace(',', ''))
                                        smart_data["data_units_read"] = value
                                    except ValueError:
                                        pass
                            
                            # Overall health
                            elif 'SMART overall-health self-assessment test result:' in line:
                                if 'PASSED' in line:
                                    smart_data["health_status"] = "PASSED"
                                elif 'FAILED' in line:
                                    smart_data["health_status"] = "FAILED"
                            
                            # Model and serial
                            elif line.startswith('Model Family:') or line.startswith('Device Model:'):
                                model = line.split(':', 1)[1].strip()
                                smart_data["model"] = model
                            elif line.startswith('Serial Number:'):
                                serial = line.split(':', 1)[1].strip()
                                smart_data["serial_number"] = serial
                            
                            # Capacity
                            elif 'User Capacity:' in line:
                                parts = line.split('[')
                                if len(parts) >= 2:
                                    capacity = parts[1].split(']')[0]
                                    smart_data["capacity"] = capacity
                        
                        if smart_data:
                            drive_stats["smart_data"] = smart_data
                    
                    # Also add filesystem type if available
                    for fs_source, fs_info in filesystem_info.items():
                        if drive_path in fs_source or drive_name in fs_source:
                            drive_stats["filesystem_type"] = fs_info["filesystem_type"]
                            drive_stats["mount_point"] = fs_info["mount_point"]
                            break
                    
                except Exception as e:
                    logger.debug(f"SMART data collection failed for {drive_name}: {e}")
                
            except Exception as e:
                drive_stats["errors"].append(f"Stats collection failed: {str(e)}")
                logger.warning(f"Drive stats collection failed for {drive_path}: {e}")
            
            drives_stats.append(drive_stats)
        
        # Get filesystem usage for mounted drives
        try:
            df_result = await ssh_client.execute_command(
                connection_info,
                "df -h --output=source,size,used,avail,pcent,target | grep -E '^/dev/'",
                timeout=15
            )
            if df_result.return_code == 0:
                for line in df_result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 6:
                            fs_stats = {
                                "device": parts[0],
                                "size": parts[1],
                                "used": parts[2],
                                "available": parts[3],
                                "usage_percent": int(parts[4].rstrip('%')),
                                "mount_point": parts[5]
                            }
                            
                            # Get inode usage
                            try:
                                inode_result = await ssh_client.execute_command(
                                    connection_info,
                                    f"df -i {parts[5]} | tail -1",
                                    timeout=5
                                )
                                if inode_result.return_code == 0:
                                    inode_parts = inode_result.stdout.strip().split()
                                    if len(inode_parts) >= 5:
                                        fs_stats["inodes_total"] = int(inode_parts[1]) if inode_parts[1] != '-' else 0
                                        fs_stats["inodes_used"] = int(inode_parts[2]) if inode_parts[2] != '-' else 0
                                        fs_stats["inodes_available"] = int(inode_parts[3]) if inode_parts[3] != '-' else 0
                                        fs_stats["inodes_usage_percent"] = int(inode_parts[4].rstrip('%')) if inode_parts[4] != '-' else 0
                            except Exception as e:
                                logger.debug(f"Failed to get inode stats for {parts[5]}: {e}")
                            
                            filesystem_usage.append(fs_stats)
        except Exception as e:
            logger.warning(f"Failed to collect filesystem usage: {e}")
        
        # Generate summary statistics
        total_drives = len(drives_stats)
        total_reads = sum(d.get("io_stats", {}).get("reads_completed", 0) for d in drives_stats)
        total_writes = sum(d.get("io_stats", {}).get("writes_completed", 0) for d in drives_stats)
        total_kb_read = sum(d.get("io_stats", {}).get("kb_read", 0) for d in drives_stats)
        total_kb_written = sum(d.get("io_stats", {}).get("kb_written", 0) for d in drives_stats)
        
        # Calculate average utilization
        utilizations = [d.get("current_performance", {}).get("utilization_percent", 0) for d in drives_stats]
        avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
        
        summary = {
            "total_drives": total_drives,
            "total_filesystems": len(filesystem_usage),
            "total_reads_completed": total_reads,
            "total_writes_completed": total_writes,
            "total_kb_read": total_kb_read,
            "total_kb_written": total_kb_written,
            "average_utilization_percent": round(avg_utilization, 2),
            "high_utilization_drives": len([u for u in utilizations if u > 80])
        }
        
        # Prepare response
        response = {
            "drives": drives_stats,
            "filesystem_usage": filesystem_usage,
            "summary": summary,
            "device_info": {
                "hostname": device,
                "connection_successful": True
            },
            "query_info": {
                "specific_drive": drive,
                "drives_checked": len(drives_to_check),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        logger.info(
            f"Collected drive stats from {device}: {total_drives} drives, "
            f"{total_reads + total_writes} total I/O operations"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error collecting drive stats from {device}: {e}")
        raise SystemMonitoringError(
            message=f"Failed to collect drive stats: {str(e)}",
            device=device,
            operation="get_drive_stats",
            details={"error": str(e), "drive": drive}
        )


# Tool registration metadata for MCP server
SYSTEM_MONITORING_TOOLS = {
    "get_system_info": {
        "name": "get_system_info",
        "description": "Get comprehensive system performance metrics from a device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device hostname or IP address"
                },
                "include_processes": {
                    "type": "boolean",
                    "description": "Include top processes information",
                    "default": False
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300
                }
            },
            "required": ["device"]
        },
        "function": get_system_info
    },
    "get_drive_health": {
        "name": "get_drive_health",
        "description": "Get S.M.A.R.T. drive health information and disk status",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device hostname or IP address"
                },
                "drive": {
                    "type": "string",
                    "description": "Specific drive to check (e.g., '/dev/sda') or omit for all drives"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300
                }
            },
            "required": ["device"]
        },
        "function": get_drive_health
    },
    "get_system_logs": {
        "name": "get_system_logs",
        "description": "Get system logs from journald or traditional syslog",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device hostname or IP address"
                },
                "service": {
                    "type": "string",
                    "description": "Specific service to get logs for (e.g., 'docker', 'nginx')"
                },
                "since": {
                    "type": "string",
                    "description": "Get logs since timestamp/duration (e.g., '2h', '1d', '2023-01-01 10:00:00')"
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of log lines to retrieve",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 10000
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300
                }
            },
            "required": ["device"]
        },
        "function": get_system_logs
    },
    "get_drive_stats": {
        "name": "get_drive_stats",
        "description": "Get drive usage statistics, I/O performance, and utilization metrics",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device hostname or IP address"
                },
                "drive": {
                    "type": "string",
                    "description": "Specific drive to check (e.g., 'sda') or omit for all drives"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300
                }
            },
            "required": ["device"]
        },
        "function": get_drive_stats
    }
}