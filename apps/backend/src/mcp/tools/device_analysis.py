"""
Device Analysis MCP Tool

Comprehensive device analysis tool that runs a series of commands on target devices
to gather information about their capabilities and store the results in the device registry.
"""

import asyncio
import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.device import Device
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError, SSHConnectionError, SSHCommandError,
    SystemMonitoringError
)

logger = logging.getLogger(__name__)


async def analyze_device(
    device: str,
    timeout: int = 120,
    store_results: bool = True
) -> Dict[str, Any]:
    """
    Run comprehensive analysis on a target device to determine its capabilities.
    
    This tool performs a series of diagnostic commands to gather information about:
    - Network connectivity (ping test)
    - SSH connectivity test
    - Docker presence and configuration
    - ZFS pools and snapshots
    - Storage setup and hardware
    - Operating system information
    - Virtual machine detection (virsh)
    - SWAG reverse proxy detection
    
    Args:
        device: Device hostname or IP address to analyze
        timeout: Overall timeout for analysis in seconds (default: 120)
        store_results: Whether to store results in device registry (default: True)
        
    Returns:
        Dict containing:
        - connectivity: Network and SSH connectivity results
        - docker_info: Docker presence, compose paths, appdata paths
        - storage_info: ZFS, filesystem, and storage details
        - hardware_info: CPU, memory, GPU, and hardware details
        - os_info: Operating system and kernel information
        - virtualization: VM detection and hypervisor info
        - services: SWAG and other service detection
        - analysis_summary: Overall analysis summary
        - timestamp: Analysis timestamp
        
    Raises:
        DeviceNotFoundError: If device cannot be reached
        SystemMonitoringError: If analysis fails
        SSHConnectionError: If SSH connection fails
    """
    logger.info(f"Starting comprehensive analysis of device: {device}")
    
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
        "analysis_summary": {},
        "errors": []
    }
    
    try:
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
        
        # 3. Docker Detection and Configuration
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
                    compose_base_paths = list(set(['/'.join(f.split('/')[:-1]) for f in compose_files]))
                    
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
                
                # Check for SWAG container
                swag_result = await execute_ssh_command_simple(
                    device,
                    "docker ps --format '{{.Names}}' | grep -i swag || echo 'NO_SWAG_FOUND'",
                    timeout=15
                )
                
                if swag_result.return_code == 0 and "NO_SWAG_FOUND" not in swag_result.stdout:
                    swag_containers = [name.strip() for name in swag_result.stdout.strip().split('\n') if name.strip()]
                    results["services"]["swag_running"] = True
                    results["services"]["swag_containers"] = swag_containers
                else:
                    results["services"]["swag_running"] = False
                    results["services"]["swag_containers"] = []
                
            else:
                results["docker_info"]["installed"] = False
                results["docker_info"]["reason"] = "Docker not available or not running"
                
        except Exception as e:
            results["docker_info"]["error"] = str(e)
            logger.warning(f"Docker analysis failed for {device}: {e}")
        
        # 4. ZFS Detection and Analysis
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
        
        # 5. Hardware and System Information
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
        
        # 6. Operating System Information
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
        
        # 7. Virtualization Detection
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
        
        # 8. Generate Analysis Summary
        analysis_end = datetime.now(timezone.utc)
        analysis_duration = (analysis_end - analysis_start).total_seconds()
        
        # Determine device capabilities
        capabilities = []
        if results["docker_info"].get("installed"):
            capabilities.append("docker")
        if results["storage_info"].get("zfs_available"):
            capabilities.append("zfs")
        if results["services"].get("swag_running"):
            capabilities.append("reverse-proxy")
        if results["virtualization"].get("virsh_available"):
            capabilities.append("virtualization")
        if results["hardware_info"].get("gpu_detected"):
            capabilities.append("gpu")
        
        results["analysis_summary"] = {
            "status": "completed",
            "duration_seconds": round(analysis_duration, 2),
            "capabilities_detected": capabilities,
            "total_capabilities": len(capabilities),
            "connectivity_status": results["connectivity"].get("ssh", {}).get("status", "unknown"),
            "analysis_timestamp": analysis_end.isoformat()
        }
        
        # 9. Store results in database if requested
        if store_results:
            try:
                await _store_analysis_results(device, results)
                results["analysis_summary"]["stored_in_database"] = True
            except Exception as e:
                results["analysis_summary"]["database_storage_error"] = str(e)
                logger.error(f"Failed to store analysis results for {device}: {e}")
        
        logger.info(f"Device analysis completed for {device} in {analysis_duration:.2f}s")
        return results
        
    except Exception as e:
        logger.error(f"Device analysis failed for {device}: {e}")
        results["analysis_summary"] = {
            "status": "failed",
            "error": str(e),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        return results


async def _store_analysis_results(device: str, analysis_results: Dict[str, Any]) -> None:
    """Store analysis results in the device registry."""
    async with get_async_session() as session:
        from sqlalchemy import select
        
        # Find the device
        query = select(Device).where(Device.hostname == device)
        result = await session.execute(query)
        device_record = result.scalar_one_or_none()
        
        if not device_record:
            logger.warning(f"Device {device} not found in registry, cannot store analysis results")
            return
        
        # Update device with analysis results
        # Note: This assumes the Device model has been extended with analysis fields
        # The actual implementation would depend on the database schema
        
        # For now, store as JSON in tags or a dedicated analysis field
        if not device_record.tags:
            device_record.tags = {}
        
        device_record.tags["last_analysis"] = analysis_results["analysis_summary"]
        device_record.tags["capabilities"] = analysis_results["analysis_summary"].get("capabilities_detected", [])
        
        # Update other fields based on analysis
        if analysis_results["docker_info"].get("installed"):
            device_record.tags["docker_version"] = analysis_results["docker_info"].get("version")
            device_record.tags["docker_compose_paths"] = analysis_results["docker_info"].get("compose_base_paths", [])
            device_record.tags["appdata_paths"] = analysis_results["docker_info"].get("appdata_paths", [])
        
        if analysis_results["storage_info"].get("zfs_available"):
            device_record.tags["zfs_pools"] = [pool["name"] for pool in analysis_results["storage_info"].get("zfs_pools", [])]
        
        if analysis_results["hardware_info"].get("gpu_detected"):
            device_record.tags["has_gpu"] = True
            device_record.tags["gpu_info"] = analysis_results["hardware_info"].get("gpu_info", [])
        
        if analysis_results["os_info"]:
            device_record.tags["os_name"] = analysis_results["os_info"].get("name", "unknown")
            device_record.tags["os_version"] = analysis_results["os_info"].get("version", "unknown")
        
        await session.commit()
        logger.info(f"Analysis results stored for device {device}")