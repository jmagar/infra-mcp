"""
Device Information MCP Tool

Comprehensive device information tool that combines analysis capabilities with
system performance monitoring to provide a complete view of device status,
capabilities, and current performance metrics.
"""

import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.device import Device
from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo, execute_ssh_command_simple
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError, SSHConnectionError, SystemMonitoringError
)
from apps.backend.src.core.config import get_settings

logger = logging.getLogger(__name__)


async def _collect_smart_data(
    ssh_client, 
    connection_info: SSHConnectionInfo, 
    drive_path: str,
    drive_name: str
) -> Dict[str, Any]:
    """
    Collect SMART data for a drive with configurable sudo behavior.
    
    Returns:
        Dict containing SMART data or empty dict if collection is disabled/failed
    """
    settings = get_settings()
    
    # Check if SMART monitoring is enabled
    if not settings.monitoring.smart_monitoring_enabled:
        logger.debug(f"SMART monitoring disabled, skipping {drive_name}")
        return {}
    
    smart_data = {}
    timeout = settings.monitoring.smart_command_timeout
    
    try:
        # Build smartctl command with graceful fallback
        if settings.monitoring.smart_require_sudo:
            # Only try sudo if explicitly required
            smart_cmd = f"sudo smartctl -a {drive_path}"
        else:
            # Try sudo first, fallback to non-sudo, then graceful failure
            smart_cmd = f"sudo smartctl -a {drive_path} 2>/dev/null || smartctl -a {drive_path} 2>/dev/null || echo 'SMART_ACCESS_DENIED'"
        
        logger.debug(f"Executing SMART command for {drive_name}: {smart_cmd}")
        
        smart_result = await ssh_client.execute_command(
            connection_info,
            smart_cmd,
            timeout=timeout
        )
        
        # Handle different response scenarios
        if smart_result.return_code != 0:
            if settings.monitoring.smart_graceful_fallback:
                logger.warning(f"SMART command failed for {drive_name} (exit code {smart_result.return_code}), continuing without SMART data")
                return {}
            else:
                raise SystemMonitoringError(f"SMART command failed for {drive_name}: {smart_result.stderr}")
        
        smart_output = smart_result.stdout
        
        # Check for access denied scenarios
        if "SMART_ACCESS_DENIED" in smart_output:
            if settings.monitoring.smart_graceful_fallback:
                logger.warning(f"SMART access denied for {drive_name}, continuing without SMART data")
                return {}
            else:
                raise SystemMonitoringError(f"SMART access denied for {drive_name}. Check sudo configuration.")
        
        # Check for permission denied in stderr
        if "Permission denied" in smart_result.stderr or "Operation not permitted" in smart_result.stderr:
            if settings.monitoring.smart_graceful_fallback:
                logger.warning(f"SMART permission denied for {drive_name}, continuing without SMART data")
                return {}
            else:
                raise SystemMonitoringError(f"SMART permission denied for {drive_name}. Check sudo configuration.")
        
        # Parse SMART attributes if we got valid output
        if smart_output and "SMART" in smart_output:
            smart_data = _parse_smart_output(smart_output, drive_path)
            logger.debug(f"Successfully collected SMART data for {drive_name}: {list(smart_data.keys())}")
        else:
            logger.debug(f"No SMART data found in output for {drive_name}")
    
    except Exception as e:
        if settings.monitoring.smart_graceful_fallback:
            logger.warning(f"SMART data collection failed for {drive_name}: {e}, continuing without SMART data")
            return {}
        else:
            logger.error(f"SMART data collection failed for {drive_name}: {e}")
            raise SystemMonitoringError(f"SMART data collection failed for {drive_name}: {str(e)}") from e
    
    return smart_data


def _parse_smart_output(smart_output: str, drive_path: str) -> Dict[str, Any]:
    """
    Parse SMART output and extract key attributes.
    
    Args:
        smart_output: Raw smartctl output
        drive_path: Drive path for logging context
        
    Returns:
        Dict with parsed SMART attributes
    """
    smart_data = {}
    
    try:
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
            
            # Temperature - more specific parsing for SMART output
            elif 'Temperature_Celsius' in line or ('Temperature' in line and 'Celsius' in line):
                parts = line.split()
                
                # For traditional SMART output: "Temperature_Celsius 0x0022 xxx xxx xxx"
                if 'Temperature_Celsius' in line and len(parts) >= 10:
                    # Raw value is typically at index 9 (last column)
                    try:
                        temp_value = int(parts[9])
                        if 0 <= temp_value <= 100:  # Reasonable temperature range
                            smart_data["temperature_celsius"] = temp_value
                    except (ValueError, IndexError):
                        pass
                
                # For NVMe or other formats: "Temperature: 45 Celsius"
                elif 'Temperature:' in line and 'Celsius' in line:
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            temp_value = int(part)
                            # Verify it's followed by "Celsius" or similar
                            if (i + 1 < len(parts) and 
                                parts[i + 1].lower() in ['celsius', '°c', 'c'] and
                                0 <= temp_value <= 100):
                                smart_data["temperature_celsius"] = temp_value
                                break
            
            # Overall health status
            elif 'SMART overall-health self-assessment test result:' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    health_status = parts[1].strip()
                    smart_data["health_status"] = health_status
            
            # Reallocated sectors
            elif 'Reallocated_Sector_Ct' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i > 5:  # Raw value is usually last
                        smart_data["reallocated_sectors"] = int(part)
                        break
    
    except Exception as e:
        logger.warning(f"Error parsing SMART output for {drive_path}: {e}")
    
    return smart_data


async def get_device_info(
    device: str,
    include_processes: bool = False,
    store_results: bool = True,
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Get comprehensive device information including capabilities analysis and system metrics.
    
    This tool performs comprehensive device analysis by combining:
    - Network and SSH connectivity testing
    - Docker configuration and container analysis
    - ZFS pools and snapshot detection  
    - Hardware detection (CPU, memory, GPU)
    - Operating system information
    - Virtualization capabilities (virsh/libvirt)
    - Service detection (SWAG reverse proxy)
    - Real-time system performance metrics
    - Drive health and I/O statistics
    - Process information (optional)
    
    Args:
        device: Device hostname or IP address
        include_processes: Include top processes information (default: False)
        store_results: Whether to store analysis results in device registry (default: True)
        timeout: Overall timeout for analysis in seconds (default: 120)
        
    Returns:
        Dict containing:
        - connectivity: Network and SSH connectivity results
        - docker_info: Docker presence, compose paths, appdata paths
        - storage_info: ZFS, filesystem, and storage details with I/O stats
        - hardware_info: CPU, memory, GPU, and hardware details
        - os_info: Operating system and kernel information
        - virtualization: VM detection and hypervisor info
        - services: SWAG and other service detection
        - system_metrics: Real-time performance metrics (CPU, memory, disk, network)
        - drive_health: S.M.A.R.T. drive health information
        - processes: Top processes (if requested)
        - analysis_summary: Overall analysis and capabilities summary
        - timestamp: Analysis timestamp
        
    Raises:
        DeviceNotFoundError: If device cannot be reached
        SystemMonitoringError: If analysis fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Starting comprehensive device info collection for: {device}")
    
    analysis_start = datetime.now(timezone.utc)
    results = {
        "device": device,
        "analysis_timestamp": analysis_start.isoformat(),
        "connectivity": {},
        "docker_info": {},
        "storage_info": {},
        "hardware_info": {},
        "os_info": {},
        "virtualization": {},
        "services": {},
        "system_metrics": {},
        "drive_health": {},
        "processes": [],
        "analysis_summary": {},
        "errors": []
    }
    
    try:
        # Create SSH connection info
        connection_info = SSHConnectionInfo(
            host=device,
            command_timeout=timeout
        )
        
        # Get SSH client
        ssh_client = get_ssh_client()
        
        # 1. Network Connectivity Test
        logger.info(f"Testing network connectivity to {device}")
        try:
            ping_result = await execute_ssh_command_simple(
                "localhost",  # Run ping from local machine
                f"ping -c 4 -W 5 {device}",
                timeout=30
            )
            
            if ping_result.return_code == 0:
                # Parse ping statistics
                ping_output = ping_result.stdout
                packet_loss = None
                avg_time = None
                
                for line in ping_output.split('\n'):
                    if '% packet loss' in line:
                        match = re.search(r'(\d+)% packet loss', line)
                        if match:
                            packet_loss = int(match.group(1))
                    elif 'avg' in line and 'ms' in line:
                        # Extract average ping time
                        match = re.search(r'avg[^=]*=\s*([0-9.]+)', line)
                        if match:
                            avg_time = float(match.group(1))
                
                results["connectivity"]["ping"] = {
                    "status": "success",
                    "packet_loss_percent": packet_loss,
                    "average_response_time_ms": avg_time,
                    "details": "Ping test successful"
                }
            else:
                results["connectivity"]["ping"] = {
                    "status": "failed",
                    "error": "Ping test failed",
                    "details": ping_result.stderr
                }
                
        except Exception as e:
            results["connectivity"]["ping"] = {
                "status": "error",
                "error": str(e)
            }
            logger.warning(f"Ping test failed for {device}: {e}")
        
        # 2. SSH Connectivity Test
        logger.info(f"Testing SSH connectivity to {device}")
        try:
            ssh_test_result = await execute_ssh_command_simple(
                device,
                "echo 'SSH_CONNECTION_TEST' && whoami && hostname",
                timeout=15
            )
            
            if ssh_test_result.return_code == 0 and "SSH_CONNECTION_TEST" in ssh_test_result.stdout:
                lines = ssh_test_result.stdout.strip().split('\n')
                username = lines[1] if len(lines) > 1 else "unknown"
                hostname = lines[2] if len(lines) > 2 else device
                
                results["connectivity"]["ssh"] = {
                    "status": "success",
                    "username": username,
                    "hostname": hostname,
                    "details": "SSH connection successful"
                }
            else:
                results["connectivity"]["ssh"] = {
                    "status": "failed",
                    "error": "SSH test command failed",
                    "return_code": ssh_test_result.return_code
                }
                
        except Exception as e:
            results["connectivity"]["ssh"] = {
                "status": "error",
                "error": str(e)
            }
            logger.warning(f"SSH test failed for {device}: {e}")
            # If SSH fails, we can't continue with other tests
            results["analysis_summary"]["status"] = "failed"
            results["analysis_summary"]["reason"] = "SSH connectivity failed"
            return results
        
        # 3. System Performance Metrics (from get_system_info)
        logger.info(f"Collecting system performance metrics from {device}")
        try:
            cpu_metrics = {}
            memory_metrics = {}
            disk_metrics = {}
            network_metrics = {}
            system_info = {}
            
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
            
            results["system_metrics"] = {
                "cpu_metrics": cpu_metrics,
                "memory_metrics": memory_metrics,
                "disk_metrics": disk_metrics,
                "network_metrics": network_metrics,
                "system_info": system_info
            }
            
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
            results["system_metrics"]["error"] = str(e)
        
        # 4. Docker Detection and Configuration (from analyze_device)
        logger.info(f"Analyzing Docker configuration on {device}")
        try:
            # Check if Docker is installed and running
            docker_version_result = await execute_ssh_command_simple(
                device,
                "docker --version && docker info --format json 2>/dev/null || echo 'DOCKER_NOT_AVAILABLE'",
                timeout=30
            )
            
            if docker_version_result.return_code == 0 and "DOCKER_NOT_AVAILABLE" not in docker_version_result.stdout:
                docker_output = docker_version_result.stdout
                
                # Extract Docker version
                version_match = re.search(r'Docker version ([0-9.]+)', docker_output)
                docker_version = version_match.group(1) if version_match else "unknown"
                
                # Try to parse Docker info JSON
                docker_info = {}
                try:
                    json_start = docker_output.find('{')
                    if json_start != -1:
                        json_data = docker_output[json_start:]
                        docker_info = json.loads(json_data)
                except json.JSONDecodeError:
                    pass
                
                results["docker_info"]["installed"] = True
                results["docker_info"]["version"] = docker_version
                results["docker_info"]["docker_info"] = docker_info
                
                # Detect Docker Compose projects and common paths
                compose_result = await execute_ssh_command_simple(
                    device,
                    "find /home /opt /srv -name 'docker-compose.yml' -o -name 'docker-compose.yaml' 2>/dev/null | head -10",
                    timeout=20
                )
                
                if compose_result.return_code == 0:
                    compose_files = [f.strip() for f in compose_result.stdout.strip().split('\n') if f.strip()]
                    compose_base_paths = list({'/'.join(f.split('/')[:-1]) for f in compose_files})
                    
                    results["docker_info"]["compose_projects"] = compose_files
                    results["docker_info"]["compose_base_paths"] = compose_base_paths
                
                # Detect common appdata directories
                appdata_result = await execute_ssh_command_simple(
                    device,
                    "ls -la /mnt/appdata /opt/appdata /home/*/appdata 2>/dev/null || echo 'NO_APPDATA_FOUND'",
                    timeout=15
                )
                
                appdata_paths = []
                if appdata_result.return_code == 0 and "NO_APPDATA_FOUND" not in appdata_result.stdout:
                    for line in appdata_result.stdout.split('\n'):
                        if line.startswith('total') or not line.strip():
                            continue
                        if '/appdata' in line:
                            # Extract the directory path from ls -la output
                            match = re.search(r'(/[^\s]+appdata)', line)
                            if match:
                                appdata_paths.append(match.group(1))
                
                results["docker_info"]["appdata_paths"] = list(set(appdata_paths))
                
                # Check for SWAG container and reverse proxy setup
                swag_result = await execute_ssh_command_simple(
                    device,
                    "docker ps --format '{{.Names}}' | grep -i swag; ls -la /mnt/appdata/swag/nginx/proxy-confs 2>/dev/null | wc -l || echo 'NO_SWAG_FOUND'",
                    timeout=15
                )
                
                swag_running = False
                swag_containers = []
                swag_config_count = 0
                
                if swag_result.return_code == 0 and "NO_SWAG_FOUND" not in swag_result.stdout:
                    lines = swag_result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip() and not line.isdigit() and "NO_SWAG_FOUND" not in line:
                            swag_containers.append(line.strip())
                            swag_running = True
                        elif line.strip().isdigit():
                            swag_config_count = int(line.strip())
                
                results["services"]["swag_running"] = swag_running
                results["services"]["swag_containers"] = swag_containers
                results["services"]["swag_config_count"] = swag_config_count
                results["services"]["reverse_proxy_detected"] = swag_running or swag_config_count > 0
                
            else:
                results["docker_info"]["installed"] = False
                results["docker_info"]["reason"] = "Docker not available or not running"
                
        except Exception as e:
            results["docker_info"]["error"] = str(e)
            logger.warning(f"Docker analysis failed for {device}: {e}")
        
        # 5. ZFS Detection and Analysis
        logger.info(f"Analyzing ZFS configuration on {device}")
        try:
            zfs_result = await execute_ssh_command_simple(
                device,
                "zpool list -H -o name,size,alloc,free,health 2>/dev/null && echo '---SNAPSHOTS---' && zfs list -t snapshot -H -o name,used,creation 2>/dev/null | head -20 || echo 'ZFS_NOT_AVAILABLE'",
                timeout=30
            )
            
            if zfs_result.return_code == 0 and "ZFS_NOT_AVAILABLE" not in zfs_result.stdout:
                output_lines = zfs_result.stdout.strip().split('\n')
                pools = []
                snapshots = []
                
                # Parse pools (before ---SNAPSHOTS--- marker)
                snapshot_marker_found = False
                for line in output_lines:
                    if line.strip() == '---SNAPSHOTS---':
                        snapshot_marker_found = True
                        continue
                    
                    if not snapshot_marker_found and line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 5:
                            pools.append({
                                "name": parts[0],
                                "size": parts[1],
                                "allocated": parts[2],
                                "free": parts[3],
                                "health": parts[4]
                            })
                    elif snapshot_marker_found and line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            snapshots.append({
                                "name": parts[0],
                                "used": parts[1],
                                "creation": parts[2]
                            })
                
                results["storage_info"]["zfs_available"] = True
                results["storage_info"]["zfs_pools"] = pools
                results["storage_info"]["zfs_snapshots"] = snapshots[:10]  # Limit to 10 most recent
                
            else:
                results["storage_info"]["zfs_available"] = False
                
        except Exception as e:
            results["storage_info"]["zfs_error"] = str(e)
            logger.warning(f"ZFS analysis failed for {device}: {e}")
        
        # 6. Hardware and System Information
        logger.info(f"Analyzing hardware information on {device}")
        try:
            # Get CPU, memory, and hardware info
            hw_result = await execute_ssh_command_simple(
                device,
                "lscpu | grep -E 'Model name|CPU\\(s\\)|Architecture'; free -h | grep 'Mem:'; lspci | grep -i vga; lspci | grep -i nvidia; df -h / | tail -1",
                timeout=30
            )
            
            if hw_result.return_code == 0:
                hw_lines = hw_result.stdout.strip().split('\n')
                
                cpu_info = {}
                memory_info = {}
                gpu_info = []
                
                for line in hw_lines:
                    line = line.strip()
                    if 'Model name:' in line:
                        cpu_info["model"] = line.split(':', 1)[1].strip()
                    elif 'CPU(s):' in line and 'NUMA' not in line:
                        cpu_info["cores"] = line.split(':', 1)[1].strip()
                    elif 'Architecture:' in line:
                        cpu_info["architecture"] = line.split(':', 1)[1].strip()
                    elif line.startswith('Mem:'):
                        mem_parts = line.split()
                        if len(mem_parts) >= 3:
                            memory_info["total"] = mem_parts[1]
                            memory_info["used"] = mem_parts[2]
                            memory_info["available"] = mem_parts[6] if len(mem_parts) > 6 else mem_parts[3]
                    elif 'VGA' in line or 'nvidia' in line.lower():
                        gpu_info.append(line)
                
                results["hardware_info"]["cpu"] = cpu_info
                results["hardware_info"]["memory"] = memory_info
                results["hardware_info"]["gpu_detected"] = len(gpu_info) > 0
                results["hardware_info"]["gpu_info"] = gpu_info
                
        except Exception as e:
            results["hardware_info"]["error"] = str(e)
            logger.warning(f"Hardware analysis failed for {device}: {e}")
        
        # 7. Operating System Information
        logger.info(f"Analyzing OS information on {device}")
        try:
            os_result = await execute_ssh_command_simple(
                device,
                "cat /etc/os-release; uname -r; uptime",
                timeout=15
            )
            
            if os_result.return_code == 0:
                os_lines = os_result.stdout.strip().split('\n')
                
                os_info = {}
                for line in os_lines:
                    if '=' in line and not line.startswith('Linux'):
                        key, value = line.split('=', 1)
                        os_info[key.lower()] = value.strip('"')
                    elif line.startswith('Linux'):
                        os_info["kernel"] = line.strip()
                    elif 'up' in line and ('load average' in line or 'user' in line):
                        os_info["uptime"] = line.strip()
                
                results["os_info"] = os_info
                
        except Exception as e:
            results["os_info"]["error"] = str(e)
            logger.warning(f"OS analysis failed for {device}: {e}")
        
        # 8. Virtualization Detection
        logger.info(f"Analyzing virtualization on {device}")
        try:
            virt_result = await execute_ssh_command_simple(
                device,
                "which virsh && virsh list --all 2>/dev/null | grep -v '^$' | head -10 || echo 'VIRSH_NOT_AVAILABLE'",
                timeout=20
            )
            
            if virt_result.return_code == 0 and "VIRSH_NOT_AVAILABLE" not in virt_result.stdout:
                virt_lines = [line.strip() for line in virt_result.stdout.strip().split('\n') if line.strip()]
                
                results["virtualization"]["virsh_available"] = True
                results["virtualization"]["vm_list"] = virt_lines[1:]  # Skip header
            else:
                results["virtualization"]["virsh_available"] = False
                
        except Exception as e:
            results["virtualization"]["error"] = str(e)
            logger.warning(f"Virtualization analysis failed for {device}: {e}")
        
        # 9. Drive Health Analysis (S.M.A.R.T. data)
        logger.info(f"Analyzing drive health on {device}")
        try:
            # Check if smartctl is available
            smart_available = False
            smartctl_result = await ssh_client.execute_command(
                connection_info,
                "which smartctl",
                timeout=10
            )
            smart_available = smartctl_result.return_code == 0
            
            drives_info = []
            
            # Find all available drives
            lsblk_result = await ssh_client.execute_command(
                connection_info,
                "lsblk -d -n -o NAME,TYPE | grep disk",
                timeout=15
            )
            drives_to_check = []
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
                    "reallocated_sectors": None,
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
                            smart_data = await _collect_smart_data(ssh_client, connection_info, drive_path, drive_path)
                            if smart_data:
                                drive_info.update(smart_data)
                                drive_info["smart_attributes"] = smart_data
                                
                        except Exception as e:
                            drive_info["errors"].append(f"S.M.A.R.T. query failed: {str(e)}")
                            logger.warning(f"S.M.A.R.T. query failed for {drive_path}: {e}")
                    
                except Exception as e:
                    drive_info["errors"].append(f"Drive check failed: {str(e)}")
                    logger.warning(f"Drive check failed for {drive_path}: {e}")
                
                drives_info.append(drive_info)
            
            # Generate drive health summary
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
                "smart_capable_drives": sum(1 for d in drives_info if d["smart_available"])
            }
            
            # Calculate average temperature
            temps = [d["temperature"] for d in drives_info if d["temperature"] is not None]
            if temps:
                summary["average_temperature"] = round(sum(temps) / len(temps), 1)
            
            results["drive_health"] = {
                "drives": drives_info,
                "smart_available": smart_available,
                "summary": summary
            }
            
        except Exception as e:
            results["drive_health"]["error"] = str(e)
            logger.warning(f"Drive health analysis failed for {device}: {e}")
        
        # 10. Collect top processes if requested
        if include_processes:
            logger.info(f"Collecting process information from {device}")
            try:
                top_result = await ssh_client.execute_command(
                    connection_info,
                    "ps aux --sort=-%cpu | head -11",  # Top 10 processes + header
                    timeout=15
                )
                if top_result.return_code == 0:
                    lines = top_result.stdout.strip().split('\n')[1:]  # Skip header
                    processes = []
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
                    results["processes"] = processes
                        
            except Exception as e:
                logger.warning(f"Failed to collect process info: {e}")
                results["processes"] = [{"error": str(e)}]
        
        # 11. Generate Analysis Summary
        analysis_end = datetime.now(timezone.utc)
        analysis_duration = (analysis_end - analysis_start).total_seconds()
        
        # Determine device capabilities and tags
        capabilities = []
        capability_tags = []
        
        if results["docker_info"].get("installed"):
            capabilities.append("docker")
            capability_tags.append("docker")
        if results["storage_info"].get("zfs_available"):
            capabilities.append("zfs")
            capability_tags.append("zfs")
        if results["services"].get("reverse_proxy_detected"):
            capabilities.append("reverse-proxy")
            capability_tags.append("swag")
        if results["virtualization"].get("virsh_available"):
            capabilities.append("virtualization")
            capability_tags.append("vms")
        if results["hardware_info"].get("gpu_detected"):
            capabilities.append("gpu")
            capability_tags.append("gpu")
        
        results["analysis_summary"] = {
            "status": "completed",
            "duration_seconds": round(analysis_duration, 2),
            "capabilities_detected": capabilities,
            "capability_tags": capability_tags,
            "total_capabilities": len(capabilities),
            "connectivity_status": results["connectivity"].get("ssh", {}).get("status", "unknown"),
            "system_metrics_collected": "system_metrics" in results and "error" not in results["system_metrics"],
            "drive_health_checked": "drive_health" in results and "error" not in results["drive_health"],
            "processes_included": include_processes,
            "analysis_timestamp": analysis_end.isoformat()
        }
        
        # 12. Store results in database if requested
        if store_results:
            try:
                await _store_analysis_results(device, results)
                results["analysis_summary"]["stored_in_database"] = True
            except Exception as e:
                results["analysis_summary"]["database_storage_error"] = str(e)
                logger.error(f"Failed to store analysis results for {device}: {e}")
        
        logger.info(f"Comprehensive device info collection completed for {device} in {analysis_duration:.2f}s")
        return results
        
    except Exception as e:
        logger.error(f"Device info collection failed for {device}: {e}")
        results["analysis_summary"] = {
            "status": "failed",
            "error": str(e),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        return results


async def _store_analysis_results(device: str, analysis_results: dict[str, any]) -> None:
    """Store analysis results in the device registry and update device fields."""
    
    # Input validation
    if not analysis_results:
        logger.warning(f"Empty analysis_results provided for device {device}, cannot store")
        return
    
    if "analysis_summary" not in analysis_results:
        logger.warning(f"Missing 'analysis_summary' key in analysis_results for device {device}, cannot store")
        return
    
    analysis_summary = analysis_results["analysis_summary"]
    if not isinstance(analysis_summary, dict):
        logger.warning(f"Invalid 'analysis_summary' format for device {device}, expected dict got {type(analysis_summary)}")
        return
    
    # Validate required top-level keys exist and are dictionaries
    required_keys = ["docker_info", "storage_info", "services", "virtualization", "hardware_info", "os_info", "connectivity"]
    for key in required_keys:
        if key not in analysis_results:
            logger.warning(f"Missing '{key}' key in analysis_results for device {device}, initializing as empty dict")
            analysis_results[key] = {}
        elif not isinstance(analysis_results[key], dict):
            logger.warning(f"Invalid '{key}' format for device {device}, expected dict got {type(analysis_results[key])}, initializing as empty dict")
            analysis_results[key] = {}
    
    async with get_async_session() as session:
        # Find the device
        query = select(Device).where(Device.hostname == device)
        result = await session.execute(query)
        device_record = result.scalar_one_or_none()
        
        if not device_record:
            logger.warning(f"Device {device} not found in registry, cannot store analysis results")
            return
        
        # Initialize tags if not present
        if not device_record.tags:
            device_record.tags = {}
        
        # Store analysis summary and timestamp
        device_record.tags["last_analysis"] = analysis_results["analysis_summary"]
        device_record.tags["analysis_timestamp"] = analysis_results["analysis_summary"]["analysis_timestamp"]
        
        # Update capability tags (docker, zfs, swag, vms, gpu)
        capability_tags = analysis_results["analysis_summary"].get("capability_tags", [])
        existing_tags = set(device_record.tags.keys())
        
        # Remove old capability tags that are no longer detected
        old_capability_tags = {"docker", "zfs", "swag", "vms", "gpu"}
        for old_tag in old_capability_tags:
            if old_tag in existing_tags and old_tag not in capability_tags:
                del device_record.tags[old_tag]
        
        # Add new capability tags
        for tag in capability_tags:
            device_record.tags[tag] = True
        
        # Update Docker-specific fields and paths
        if analysis_results["docker_info"].get("installed"):
            device_record.tags["docker_version"] = analysis_results["docker_info"].get("version")
            
            # Set primary docker_compose_path (first detected path)
            compose_paths = analysis_results["docker_info"].get("compose_base_paths", [])
            if compose_paths:
                device_record.docker_compose_path = compose_paths[0]
                device_record.tags["all_docker_compose_paths"] = compose_paths
            
            # Set primary docker_appdata_path (first detected path)
            appdata_paths = analysis_results["docker_info"].get("appdata_paths", [])
            if appdata_paths:
                device_record.docker_appdata_path = appdata_paths[0]
                device_record.tags["all_appdata_paths"] = appdata_paths
        
        # Update ZFS information
        if analysis_results["storage_info"].get("zfs_available"):
            zfs_pools = analysis_results["storage_info"].get("zfs_pools", [])
            device_record.tags["zfs_pools"] = [pool["name"] for pool in zfs_pools]
            device_record.tags["zfs_pool_count"] = len(zfs_pools)
        
        # Update SWAG/reverse proxy information
        if analysis_results["services"].get("reverse_proxy_detected"):
            device_record.tags["swag_containers"] = analysis_results["services"].get("swag_containers", [])
            device_record.tags["swag_config_count"] = analysis_results["services"].get("swag_config_count", 0)
            device_record.tags["swag_running"] = analysis_results["services"].get("swag_running", False)
        
        # Update virtualization information
        if analysis_results["virtualization"].get("virsh_available"):
            vm_list = analysis_results["virtualization"].get("vm_list", [])
            device_record.tags["vm_count"] = len(vm_list)
            device_record.tags["hypervisor"] = "libvirt"
        
        # Update GPU information
        if analysis_results["hardware_info"].get("gpu_detected"):
            device_record.tags["gpu_info"] = analysis_results["hardware_info"].get("gpu_info", [])
            device_record.tags["gpu_count"] = len(analysis_results["hardware_info"].get("gpu_info", []))
        
        # Update OS information
        if analysis_results["os_info"]:
            device_record.tags["os_name"] = analysis_results["os_info"].get("name", "unknown")
            device_record.tags["os_version"] = analysis_results["os_info"].get("version", "unknown")
            device_record.tags["kernel"] = analysis_results["os_info"].get("kernel", "unknown")
        
        # Update hardware information
        if analysis_results["hardware_info"]:
            cpu_info = analysis_results["hardware_info"].get("cpu", {})
            memory_info = analysis_results["hardware_info"].get("memory", {})
            
            if cpu_info:
                device_record.tags["cpu_model"] = cpu_info.get("model", "unknown")
                device_record.tags["cpu_cores"] = cpu_info.get("cores", "unknown")
                device_record.tags["cpu_architecture"] = cpu_info.get("architecture", "unknown")
            
            if memory_info:
                device_record.tags["memory_total"] = memory_info.get("total", "unknown")
        
        # Update device status and last seen
        if analysis_results["connectivity"].get("ssh", {}).get("status") == "success":
            device_record.status = "online"
            device_record.last_seen = datetime.now(timezone.utc)
        
        await session.commit()
        logger.info(f"Analysis results stored for device {device} with tags: {capability_tags}")


# Tool registration metadata for MCP server
DEVICE_INFO_TOOLS = {
    "get_device_info": {
        "name": "get_device_info",
        "description": "Get comprehensive device information including capabilities analysis and system metrics",
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
                "store_results": {
                    "type": "boolean",
                    "description": "Whether to store analysis results in device registry",
                    "default": True
                },
                "timeout": {
                    "type": "integer",
                    "description": "Overall timeout for analysis in seconds",
                    "default": 120,
                    "minimum": 30,
                    "maximum": 600
                }
            },
            "required": ["device"]
        },
        "function": get_device_info
    }
}