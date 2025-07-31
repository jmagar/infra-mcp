"""
Device Management MCP Tools

This module implements MCP tools for device registry management,
monitoring status checks, and device information retrieval.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
# UUID import removed - now using hostname-only approach

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.device import Device
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError, DatabaseOperationError, SSHConnectionError
)
from apps.backend.src.schemas.device import DeviceResponse, DeviceSummary, DeviceConnectionTest
from apps.backend.src.schemas.common import DeviceStatus, PaginationParams
from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo, test_ssh_connectivity

logger = logging.getLogger(__name__)


async def list_devices(
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    monitoring_enabled: Optional[bool] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List all registered infrastructure devices with optional filtering.
    
    This tool retrieves devices from the device registry with support for
    various filtering options including type, status, location, and search.
    It provides essential device information for infrastructure monitoring.
    
    Args:
        device_type: Optional device type filter (server, workstation, etc.)
        status: Optional status filter (online, offline, unknown)
        monitoring_enabled: Filter by monitoring status
        location: Optional location filter
        search: Search in hostname and description
        limit: Maximum number of devices to return (default: 50)
        offset: Pagination offset (default: 0)
        
    Returns:
        Dict containing:
        - devices: List of device information dictionaries
        - pagination: Pagination information
        - filters_applied: Applied filter information
        - summary: Device count summary
        - timestamp: Query timestamp
        
    Raises:
        DatabaseOperationError: If database query fails
    """
    logger.info("Listing devices from registry")
    
    try:
        # Get database session
        async with get_async_session() as db:
            # Build query with filters
            query = select(Device)
            
            # Apply filters
            filters = []
            if device_type:
                filters.append(Device.device_type == device_type)
            if status:
                filters.append(Device.status == DeviceStatus(status))
            if monitoring_enabled is not None:
                filters.append(Device.monitoring_enabled == monitoring_enabled)
            if location:
                filters.append(Device.location.ilike(f"%{location}%"))
            if search:
                search_filter = f"%{search}%"
                filters.append(
                    Device.hostname.ilike(search_filter) |
                    Device.description.ilike(search_filter)
                )
            
            if filters:
                query = query.where(*filters)
            
            # Get total count
            count_query = select(func.count(Device.id)).where(*filters) if filters else select(func.count(Device.id))
            total_count_result = await db.execute(count_query)
            total_count = total_count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(Device.hostname).offset(offset).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            devices = result.scalars().all()
            
            # Transform devices to response format
            device_list = []
            status_counts = {"online": 0, "offline": 0, "unknown": 0}
            
            for device in devices:
                device_info = {
                    "id": str(device.id),
                    "hostname": device.hostname,
                    "ip_address": device.ip_address,
                    "device_type": device.device_type,
                    "status": device.status.value,
                    "location": device.location,
                    "description": device.description,
                    "monitoring_enabled": device.monitoring_enabled,
                    "created_at": device.created_at.isoformat(),
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    "ssh_config": {
                        "port": device.ssh_port,
                        "username": device.ssh_username,
                        "key_based_auth": bool(device.ssh_private_key_path)
                    }
                }
                device_list.append(device_info)
                
                # Count statuses
                status_counts[device.status.value] += 1
            
            # Prepare response
            response = {
                "devices": device_list,
                "pagination": {
                    "total_count": total_count,
                    "returned_count": len(device_list),
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(device_list) < total_count
                },
                "filters_applied": {
                    "device_type": device_type,
                    "status": status,
                    "monitoring_enabled": monitoring_enabled,
                    "location": location,
                    "search": search
                },
                "summary": {
                    "total_devices": total_count,
                    "online": status_counts["online"],
                    "offline": status_counts["offline"],
                    "unknown": status_counts["unknown"],
                    "monitoring_enabled": sum(1 for d in device_list if d["monitoring_enabled"])
                },
                "query_info": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "execution_time_ms": 0  # Database queries are typically fast
                }
            }
            
            logger.info(f"Listed {len(device_list)} devices (total: {total_count})")
            return response
            
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise DatabaseOperationError(
            operation="list_devices",
            details={
                "error": str(e),
                "filters": {
                    "device_type": device_type,
                    "status": status,
                    "monitoring_enabled": monitoring_enabled,
                    "location": location,
                    "search": search
                }
            }
        )


async def get_device_info(
    device: str,
    test_connectivity: bool = True,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Get comprehensive information about a specific device.
    
    This tool retrieves detailed device information from the registry
    and optionally tests SSH connectivity. It provides both static
    configuration data and dynamic connectivity status.
    
    NOTE: This tool is OPTIONAL - the core MCP monitoring tools work 
    directly with hostnames from SSH config without requiring device registration.
    
    Args:
        device: Device hostname (must match SSH config)
        test_connectivity: Whether to test SSH connectivity (default: True)
        timeout: SSH connection timeout in seconds (default: 30)
        
    Returns:
        Dict containing:
        - device_info: Complete device configuration
        - connectivity: SSH connectivity test results
        - system_info: Basic system information if connected
        - network_info: Network configuration details
        - monitoring_status: Monitoring configuration
        - timestamp: Query timestamp
        
    Raises:
        DeviceNotFoundError: If device not found in registry
        DatabaseOperationError: If database query fails
    """
    logger.info(f"Getting device info for: {device}")
    
    try:
        # Get database session
        async with get_async_session() as db:
            # Find device by hostname only (simplified approach)
            query = select(Device).where(Device.hostname == device)
            
            result = await db.execute(query)
            device_record = result.scalar_one_or_none()
            
            if not device_record:
                raise DeviceNotFoundError(device, "hostname")
            
            # Build device info
            device_info = {
                "id": str(device_record.id),
                "hostname": device_record.hostname,
                "ip_address": device_record.ip_address,
                "device_type": device_record.device_type,
                "status": device_record.status.value,
                "location": device_record.location,
                "description": device_record.description,
                "monitoring_enabled": device_record.monitoring_enabled,
                "created_at": device_record.created_at.isoformat(),
                "updated_at": device_record.updated_at.isoformat(),
                "last_seen": device_record.last_seen.isoformat() if device_record.last_seen else None,
                "metadata": device_record.metadata or {}
            }
            
            # SSH configuration
            ssh_config = {
                "port": device_record.ssh_port,
                "username": device_record.ssh_username,
                "password_auth": bool(device_record.ssh_password),
                "key_based_auth": bool(device_record.ssh_private_key_path),
                "private_key_path": device_record.ssh_private_key_path,
                "connect_timeout": 30,
                "command_timeout": 120
            }
            
            # Initialize connectivity info
            connectivity_info = {
                "test_performed": test_connectivity,
                "is_reachable": False,
                "ssh_accessible": False,
                "response_time_ms": None,
                "error_message": None,
                "last_test": datetime.now(timezone.utc).isoformat()
            }
            
            # System info (only available if connected)
            system_info = None
            
            # Test connectivity if requested
            if test_connectivity:
                try:
                    start_time = time.time()
                    
                    connection_info = SSHConnectionInfo(
                        host=device_record.ip_address,
                        port=device_record.ssh_port,
                        username=device_record.ssh_username,
                        password=device_record.ssh_password,
                        private_key_path=device_record.ssh_private_key_path,
                        connect_timeout=timeout
                    )
                    
                    # Test basic connectivity
                    is_connected = await test_ssh_connectivity(
                        host=device_record.ip_address,
                        port=device_record.ssh_port,
                        username=device_record.ssh_username,
                        password=device_record.ssh_password,
                        private_key_path=device_record.ssh_private_key_path,
                        timeout=timeout
                    )
                    
                    connectivity_info["is_reachable"] = is_connected
                    connectivity_info["ssh_accessible"] = is_connected
                    connectivity_info["response_time_ms"] = int((time.time() - start_time) * 1000)
                    
                    # If connected, get basic system info
                    if is_connected:
                        ssh_client = get_ssh_client()
                        
                        # Get system information
                        uname_result = await ssh_client.execute_command(
                            connection_info, "uname -a", timeout=10
                        )
                        
                        uptime_result = await ssh_client.execute_command(
                            connection_info, "uptime", timeout=10
                        )
                        
                        df_result = await ssh_client.execute_command(
                            connection_info, "df -h / | tail -1", timeout=10
                        )
                        
                        free_result = await ssh_client.execute_command(
                            connection_info, "free -h | head -n 2 | tail -1", timeout=10
                        )
                        
                        system_info = {
                            "kernel": uname_result.stdout.strip() if uname_result.return_code == 0 else None,
                            "uptime": uptime_result.stdout.strip() if uptime_result.return_code == 0 else None,
                            "disk_usage": df_result.stdout.strip() if df_result.return_code == 0 else None,
                            "memory_usage": free_result.stdout.strip() if free_result.return_code == 0 else None,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Update device last_seen in database
                        device_record.last_seen = datetime.now(timezone.utc)
                        device_record.status = DeviceStatus.online
                        await db.commit()
                        
                except Exception as e:
                    logger.warning(f"Connectivity test failed for {device}: {e}")
                    connectivity_info["error_message"] = str(e)
                    connectivity_info["is_reachable"] = False
                    connectivity_info["ssh_accessible"] = False
            
            # Network information
            network_info = {
                "primary_ip": device_record.ip_address,
                "ssh_port": device_record.ssh_port,
                "hostname": device_record.hostname,
                "fqdn": f"{device_record.hostname}.local" if device_record.hostname else None
            }
            
            # Monitoring status
            monitoring_status = {
                "enabled": device_record.monitoring_enabled,
                "last_check": device_record.last_seen.isoformat() if device_record.last_seen else None,
                "status": device_record.status.value,
                "health_checks": []  # Could be expanded with specific health checks
            }
            
            # Prepare response
            response = {
                "device_info": device_info,
                "ssh_config": ssh_config,
                "connectivity": connectivity_info,
                "system_info": system_info,
                "network_info": network_info,
                "monitoring_status": monitoring_status,
                "query_info": {
                    "queried_identifier": device,
                    "found_by": "uuid" if (device.count('-') == 4 and len(device) == 36) else "hostname_or_ip",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            logger.info(f"Retrieved device info for {device_record.hostname} (Status: {device_record.status.value})")
            return response
            
    except DeviceNotFoundError:
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting device info for {device}: {e}")
        raise DatabaseOperationError(
            operation="get_device_info",
            details={
                "device": device,
                "error": str(e)
            }
        )


async def get_device_summary(
    device: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Get a comprehensive summary of device status and health.
    
    This tool provides a high-level overview of device health including
    connectivity status, basic system metrics, Docker status, and
    recent activity summary. Optimized for dashboard display.
    
    Args:
        device: Device hostname, IP address, or UUID
        timeout: SSH connection timeout in seconds (default: 30)
        
    Returns:
        Dict containing:
        - device_summary: Basic device identification
        - health_status: Overall device health assessment
        - connectivity_status: Network and SSH accessibility
        - system_summary: CPU, memory, disk overview
        - docker_summary: Container count and status
        - recent_activity: Recent events and changes
        - timestamp: Query timestamp
        
    Raises:
        DeviceNotFoundError: If device not found in registry
        DatabaseOperationError: If database query fails
    """
    logger.info(f"Getting device summary for: {device}")
    
    try:
        # Get database session
        async with get_async_session() as db:
            # Find device by hostname, IP, or UUID
            query = select(Device)
            try:
                # Try UUID first
                device_uuid = UUID(device)
                query = query.where(Device.id == device_uuid)
            except ValueError:
                # Not a UUID, try hostname or IP
                query = query.where(
                    (Device.hostname == device) | (Device.ip_address == device)
                )
            
            result = await db.execute(query)
            device_record = result.scalar_one_or_none()
            
            if not device_record:
                raise DeviceNotFoundError(device, "hostname/ip/uuid")
            
            # Build device summary
            device_summary = {
                "id": str(device_record.id),
                "hostname": device_record.hostname,
                "ip_address": device_record.ip_address,
                "device_type": device_record.device_type,
                "location": device_record.location,
                "status": device_record.status.value
            }
            
            # Initialize health status
            health_status = {
                "overall_health": "unknown",
                "health_score": 0,
                "issues": [],
                "warnings": [],
                "last_assessment": datetime.now(timezone.utc).isoformat()
            }
            
            # Initialize connectivity status
            connectivity_status = {
                "is_online": False,
                "ssh_accessible": False,
                "last_seen": device_record.last_seen.isoformat() if device_record.last_seen else None,
                "uptime": None,
                "ping_response_ms": None
            }
            
            # Initialize system summary
            system_summary = {
                "cpu_usage_percent": None,
                "memory_usage_percent": None,
                "disk_usage_percent": None,
                "load_average": None,
                "processes_count": None
            }
            
            # Initialize Docker summary
            docker_summary = {
                "docker_available": False,
                "containers_total": 0,
                "containers_running": 0,
                "containers_stopped": 0,
                "images_count": 0
            }
            
            # Initialize recent activity
            recent_activity = {
                "last_update": device_record.updated_at.isoformat(),
                "monitoring_events": [],
                "status_changes": [],
                "error_count_24h": 0
            }
            
            # Test connectivity and gather system info if device is online
            if device_record.monitoring_enabled:
                try:
                    start_time = time.time()
                    
                    connection_info = SSHConnectionInfo(
                        host=device_record.ip_address,
                        port=device_record.ssh_port,
                        username=device_record.ssh_username,
                        password=device_record.ssh_password,
                        private_key_path=device_record.ssh_private_key_path,
                        connect_timeout=timeout
                    )
                    
                    # Test SSH connectivity
                    is_connected = await test_ssh_connectivity(
                        host=device_record.ip_address,
                        port=device_record.ssh_port,
                        username=device_record.ssh_username,
                        password=device_record.ssh_password,
                        private_key_path=device_record.ssh_private_key_path,
                        timeout=timeout
                    )
                    
                    connectivity_status["is_online"] = is_connected
                    connectivity_status["ssh_accessible"] = is_connected
                    connectivity_status["ping_response_ms"] = int((time.time() - start_time) * 1000)
                    
                    if is_connected:
                        ssh_client = get_ssh_client()
                        
                        # Get system metrics
                        try:
                            # CPU usage (1-minute average)
                            cpu_result = await ssh_client.execute_command(
                                connection_info, 
                                "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | sed 's/%us,//'",
                                timeout=10
                            )
                            if cpu_result.return_code == 0 and cpu_result.stdout.strip():
                                system_summary["cpu_usage_percent"] = float(cpu_result.stdout.strip())
                        except:
                            pass
                        
                        # Memory usage
                        try:
                            mem_result = await ssh_client.execute_command(
                                connection_info,
                                "free | grep Mem | awk '{printf \"%.1f\", $3/$2 * 100.0}'",
                                timeout=10
                            )
                            if mem_result.return_code == 0 and mem_result.stdout.strip():
                                system_summary["memory_usage_percent"] = float(mem_result.stdout.strip())
                        except:
                            pass
                        
                        # Disk usage for root filesystem
                        try:
                            disk_result = await ssh_client.execute_command(
                                connection_info,
                                "df / | tail -1 | awk '{print $5}' | sed 's/%//'",
                                timeout=10
                            )
                            if disk_result.return_code == 0 and disk_result.stdout.strip():
                                system_summary["disk_usage_percent"] = int(disk_result.stdout.strip())
                        except:
                            pass
                        
                        # Load average
                        try:
                            load_result = await ssh_client.execute_command(
                                connection_info,
                                "uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//'",
                                timeout=10
                            )
                            if load_result.return_code == 0 and load_result.stdout.strip():
                                system_summary["load_average"] = float(load_result.stdout.strip())
                        except:
                            pass
                        
                        # Uptime
                        try:
                            uptime_result = await ssh_client.execute_command(
                                connection_info, "uptime -p", timeout=10
                            )
                            if uptime_result.return_code == 0:
                                connectivity_status["uptime"] = uptime_result.stdout.strip()
                        except:
                            pass
                        
                        # Process count
                        try:
                            proc_result = await ssh_client.execute_command(
                                connection_info, "ps aux | wc -l", timeout=10
                            )
                            if proc_result.return_code == 0 and proc_result.stdout.strip():
                                system_summary["processes_count"] = int(proc_result.stdout.strip()) - 1  # Subtract header
                        except:
                            pass
                        
                        # Docker status
                        try:
                            docker_version_result = await ssh_client.execute_command(
                                connection_info, "docker --version", timeout=10
                            )
                            if docker_version_result.return_code == 0:
                                docker_summary["docker_available"] = True
                                
                                # Get container counts
                                container_stats_result = await ssh_client.execute_command(
                                    connection_info, 
                                    "docker ps -a --format '{{.Status}}' | sort | uniq -c",
                                    timeout=15
                                )
                                if container_stats_result.return_code == 0:
                                    lines = container_stats_result.stdout.strip().split('\n')
                                    for line in lines:
                                        if line.strip():
                                            parts = line.strip().split(None, 1)
                                            if len(parts) == 2:
                                                count, status = parts
                                                count = int(count)
                                                docker_summary["containers_total"] += count
                                                if status.startswith("Up"):
                                                    docker_summary["containers_running"] += count
                                                else:
                                                    docker_summary["containers_stopped"] += count
                                
                                # Get image count
                                images_result = await ssh_client.execute_command(
                                    connection_info, "docker images -q | wc -l", timeout=10
                                )
                                if images_result.return_code == 0 and images_result.stdout.strip():
                                    docker_summary["images_count"] = int(images_result.stdout.strip())
                        except:
                            pass
                        
                        # Update device status
                        device_record.last_seen = datetime.now(timezone.utc)
                        device_record.status = DeviceStatus.online
                        await db.commit()
                        
                        # Calculate health score
                        health_score = 100
                        issues = []
                        warnings = []
                        
                        # Check system metrics for issues
                        if system_summary["cpu_usage_percent"] and system_summary["cpu_usage_percent"] > 90:
                            issues.append("High CPU usage")
                            health_score -= 20
                        elif system_summary["cpu_usage_percent"] and system_summary["cpu_usage_percent"] > 70:
                            warnings.append("Elevated CPU usage")
                            health_score -= 10
                            
                        if system_summary["memory_usage_percent"] and system_summary["memory_usage_percent"] > 90:
                            issues.append("High memory usage")
                            health_score -= 20
                        elif system_summary["memory_usage_percent"] and system_summary["memory_usage_percent"] > 75:
                            warnings.append("Elevated memory usage")
                            health_score -= 10
                            
                        if system_summary["disk_usage_percent"] and system_summary["disk_usage_percent"] > 90:
                            issues.append("High disk usage")
                            health_score -= 25
                        elif system_summary["disk_usage_percent"] and system_summary["disk_usage_percent"] > 80:
                            warnings.append("Elevated disk usage")
                            health_score -= 10
                        
                        # Determine overall health
                        if health_score >= 90:
                            overall_health = "excellent"
                        elif health_score >= 75:
                            overall_health = "good"
                        elif health_score >= 50:
                            overall_health = "fair"
                        elif health_score >= 25:
                            overall_health = "poor"
                        else:
                            overall_health = "critical"
                        
                        health_status.update({
                            "overall_health": overall_health,
                            "health_score": health_score,
                            "issues": issues,
                            "warnings": warnings
                        })
                        
                    else:
                        # Device is offline
                        health_status.update({
                            "overall_health": "offline",
                            "health_score": 0,
                            "issues": ["Device is not accessible via SSH"],
                            "warnings": []
                        })
                        
                except Exception as e:
                    logger.warning(f"Error gathering system info for {device}: {e}")
                    health_status.update({
                        "overall_health": "error",
                        "health_score": 0,
                        "issues": [f"Failed to gather system information: {str(e)}"],
                        "warnings": []
                    })
            
            # Prepare response
            response = {
                "device_summary": device_summary,
                "health_status": health_status,
                "connectivity_status": connectivity_status,
                "system_summary": system_summary,
                "docker_summary": docker_summary,
                "recent_activity": recent_activity,
                "query_info": {
                    "queried_identifier": device,
                    "monitoring_enabled": device_record.monitoring_enabled,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            logger.info(
                f"Generated summary for {device_record.hostname} "
                f"(Health: {health_status['overall_health']}, Score: {health_status['health_score']})"
            )
            
            return response
            
    except DeviceNotFoundError:
        # Re-raise known exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting device summary for {device}: {e}")
        raise DatabaseOperationError(
            operation="get_device_summary",
            details={
                "device": device,
                "error": str(e)
            }
        )


# Tool registration metadata for MCP server
DEVICE_TOOLS = {
    "list_devices": {
        "name": "list_devices",
        "description": "List all registered infrastructure devices with optional filtering",
        "parameters": {
            "type": "object",
            "properties": {
                "device_type": {
                    "type": "string",
                    "description": "Filter by device type",
                    "enum": ["server", "workstation", "router", "switch", "nas", "iot", "other"]
                },
                "status": {
                    "type": "string",
                    "description": "Filter by device status",
                    "enum": ["online", "offline", "unknown"]
                },
                "monitoring_enabled": {
                    "type": "boolean",
                    "description": "Filter by monitoring status"
                },
                "location": {
                    "type": "string",
                    "description": "Filter by location (partial match)"
                },
                "search": {
                    "type": "string",
                    "description": "Search in hostname and description"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of devices to return",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset",
                    "default": 0,
                    "minimum": 0
                }
            },
            "required": []
        },
        "function": list_devices
    },
    "get_device_info": {
        "name": "get_device_info",
        "description": "Get comprehensive information about a specific device",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device hostname, IP address, or UUID"
                },
                "test_connectivity": {
                    "type": "boolean",
                    "description": "Whether to test SSH connectivity",
                    "default": True
                },
                "timeout": {
                    "type": "integer",
                    "description": "SSH connection timeout in seconds",
                    "default": 30,
                    "minimum": 5,
                    "maximum": 120
                }
            },
            "required": ["device"]
        },
        "function": get_device_info
    },
    "get_device_summary": {
        "name": "get_device_summary",
        "description": "Get a comprehensive summary of device status and health",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device hostname, IP address, or UUID"
                },
                "timeout": {
                    "type": "integer",
                    "description": "SSH connection timeout in seconds",
                    "default": 30,
                    "minimum": 5,
                    "maximum": 120
                }
            },
            "required": ["device"]
        },
        "function": get_device_summary
    }
}