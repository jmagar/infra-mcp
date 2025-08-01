#!/usr/bin/env python3
"""
Standalone Infrastructure Management MCP Server

This server provides MCP tools that make HTTP calls to the FastAPI REST endpoints
instead of doing direct SSH operations. This eliminates code duplication and ensures
consistency between MCP and REST interfaces.
"""

import os
import sys
import asyncio
import logging
import httpx
from typing import List, Any
from fastmcp import FastMCP

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import device management functions
from apps.backend.src.mcp.tools.device_management import add_device as device_add_device

# Import proxy configuration management functions
from apps.backend.src.mcp.tools.proxy_management import (
    list_proxy_configs, get_proxy_config, scan_proxy_configs,
    sync_proxy_config, get_proxy_config_summary
)

# Import proxy configuration resources
from apps.backend.src.mcp.resources.proxy_configs import (
    get_proxy_config_resource, list_proxy_config_resources
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI server configuration
API_BASE_URL = "http://localhost:9101/api"
API_TIMEOUT = 120.0
API_KEY = os.getenv("API_KEY", "your-api-key-for-authentication")


class APIClient:
    """HTTP client for FastAPI endpoints"""
    
    def __init__(self):
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
            
        self.client = httpx.AsyncClient(
            base_url=API_BASE_URL,
            timeout=httpx.Timeout(API_TIMEOUT),
            headers=headers
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global API client instance
api_client = APIClient()


# Container Management Tools
async def list_containers(
    device: str,
    status: str | None = None,
    all_containers: bool = True,
    timeout: int = 60,
    limit: int | None = None,
    offset: int = 0
) -> dict[str, Any]:
    """List Docker containers on a specific device"""
    try:
        params = {
            "all_containers": all_containers,
            "timeout": timeout,
            "offset": offset
        }
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
            
        response = await api_client.client.get(f"/containers/{device}", params=params)
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error listing containers on {device}: {e}")
        raise Exception(f"Failed to list containers: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing containers on {device}: {e}")
        raise Exception(f"Failed to list containers: {str(e)}")


async def get_container_info(
    device: str,
    container_name: str,
    timeout: int = 60
) -> dict[str, Any]:
    """Get detailed information about a specific Docker container"""
    try:
        params = {"timeout": timeout}
        response = await api_client.client.get(f"/containers/{device}/{container_name}", params=params)
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting container info for {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container info: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting container info for {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container info: {str(e)}")


async def get_container_logs(
    device: str,
    container_name: str,
    since: str | None = None,
    tail: int | None = None,
    timeout: int = 60
) -> dict[str, Any]:
    """Get logs from a specific Docker container"""
    try:
        params = {"timeout": timeout}
        if since:
            params["since"] = since
        if tail:
            params["tail"] = tail
            
        response = await api_client.client.get(f"/containers/{device}/{container_name}/logs", params=params)
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting logs for {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container logs: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting logs for {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container logs: {str(e)}")


# System Monitoring Tools
async def get_system_info(
    device: str,
    include_processes: bool = False,
    timeout: int = 60
) -> dict[str, Any]:
    """Get comprehensive system performance metrics from a device"""
    try:
        params = {
            "include_processes": include_processes,
            "timeout": timeout
        }
        response = await api_client.client.get(f"/devices/{device}/metrics", params=params)
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting system info for {device}: {e}")
        raise Exception(f"Failed to get system info: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting system info for {device}: {e}")
        raise Exception(f"Failed to get system info: {str(e)}")


async def get_drive_health(
    device: str,
    drive: str | None = None,
    timeout: int = 60
) -> dict[str, Any]:
    """Get S.M.A.R.T. drive health information and disk status"""
    try:
        params = {"timeout": timeout}
        if drive:
            params["drive"] = drive
            
        response = await api_client.client.get(f"/devices/{device}/drives", params=params)
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting drive health for {device}: {e}")
        raise Exception(f"Failed to get drive health: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting drive health for {device}: {e}")
        raise Exception(f"Failed to get drive health: {str(e)}")


async def get_drives_stats(
    device: str,
    drive: str | None = None,
    timeout: int = 60
) -> dict[str, Any]:
    """Get drive usage statistics, I/O performance, and utilization metrics"""
    try:
        params = {"timeout": timeout}
        if drive:
            params["drive"] = drive
            
        response = await api_client.client.get(f"/devices/{device}/drives/stats", params=params)
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting drives stats for {device}: {e}")
        raise Exception(f"Failed to get drives stats: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting drives stats for {device}: {e}")
        raise Exception(f"Failed to get drives stats: {str(e)}")


async def get_system_logs(
    device: str,
    service: str | None = None,
    since: str | None = None,
    lines: int = 100,
    timeout: int = 60
) -> dict[str, Any]:
    """Get system logs from journald or traditional syslog"""
    try:
        params = {
            "lines": lines,
            "timeout": timeout
        }
        if service:
            params["service"] = service
        if since:
            params["since"] = since
            
        response = await api_client.client.get(f"/devices/{device}/logs", params=params)
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting system logs for {device}: {e}")
        raise Exception(f"Failed to get system logs: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting system logs for {device}: {e}")
        raise Exception(f"Failed to get system logs: {str(e)}")


# Device Management Tools
async def list_devices() -> dict[str, Any]:
    """List all registered infrastructure devices"""
    try:
        response = await api_client.client.get("/devices")
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error listing devices: {e}")
        raise Exception(f"Failed to list devices: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise Exception(f"Failed to list devices: {str(e)}")


async def add_device(
    hostname: str,
    device_type: str = "server",
    description: str | None = None,
    location: str | None = None,
    monitoring_enabled: bool = True,
    ip_address: str | None = None,
    ssh_port: int | None = None,
    ssh_username: str | None = None,
    tags: dict[str, str] | None = None
) -> dict[str, Any]:
    """Add a new device to the infrastructure registry"""
    return await device_add_device(
        hostname=hostname,
        device_type=device_type,
        description=description,
        location=location,
        monitoring_enabled=monitoring_enabled,
        ip_address=ip_address,
        ssh_port=ssh_port,
        ssh_username=ssh_username,
        tags=tags
    )


async def remove_device(hostname: str) -> dict[str, Any]:
    """Remove a device from the infrastructure registry"""
    try:
        response = await api_client.client.delete(f"/devices/{hostname}")
        response.raise_for_status()
        
        result = response.json()
        return {
            "hostname": hostname,
            "status": "deleted",
            "message": f"Device '{hostname}' removed successfully from infrastructure registry",
            "operation_result": result
        }
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error removing device {hostname}: {e}")
        if e.response.status_code == 404:
            raise Exception(f"Device with hostname '{hostname}' not found") from e
        raise Exception(f"Failed to remove device: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error removing device {hostname}: {e}")
        raise Exception(f"Failed to remove device: {str(e)}") from e


async def edit_device(
    hostname: str,
    device_type: str | None = None,
    description: str | None = None,
    location: str | None = None,
    monitoring_enabled: bool | None = None,
    ip_address: str | None = None,
    ssh_port: int | None = None,
    ssh_username: str | None = None,
    tags: dict[str, str] | None = None
) -> dict[str, Any]:
    """Edit/update details of an existing device in the infrastructure registry"""
    try:
        # Prepare update data (only include fields that are provided)
        update_data = {}
        
        if device_type is not None:
            update_data["device_type"] = device_type
        if description is not None:
            update_data["description"] = description
        if location is not None:
            update_data["location"] = location
        if monitoring_enabled is not None:
            update_data["monitoring_enabled"] = monitoring_enabled
        if ip_address is not None:
            update_data["ip_address"] = ip_address
        if ssh_port is not None:
            update_data["ssh_port"] = ssh_port
        if ssh_username is not None:
            update_data["ssh_username"] = ssh_username
        if tags is not None:
            update_data["tags"] = tags
        
        if not update_data:
            raise Exception("No fields provided to update")
        
        response = await api_client.client.put(f"/devices/{hostname}", json=update_data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "hostname": hostname,
            "status": "updated",
            "message": f"Device '{hostname}' updated successfully in infrastructure registry",
            "updated_fields": list(update_data.keys()),
            "device_info": result
        }
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error updating device {hostname}: {e}")
        if e.response.status_code == 404:
            raise Exception(f"Device with hostname '{hostname}' not found") from e
        raise Exception(f"Failed to update device: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error updating device {hostname}: {e}")
        raise Exception(f"Failed to update device: {str(e)}") from e


def create_mcp_server():
    """Create and configure the MCP server"""
    server = FastMCP(
        name="Infrastructure Management MCP Server",
        version="1.0.0", 
        instructions="Comprehensive infrastructure monitoring and management tools for heterogeneous Linux environments"
    )
    
    # Register container management tools
    server.tool(
        name="list_containers",
        description="List Docker containers on a specific device"
    )(list_containers)
    
    server.tool(
        name="get_container_info",
        description="Get detailed information about a specific Docker container"
    )(get_container_info)
    
    server.tool(
        name="get_container_logs",
        description="Get logs from a specific Docker container"
    )(get_container_logs)
    
    # DISABLED: Service dependencies endpoint does not exist in current API
    # server.tool(
    #     name="get_service_dependencies",
    #     description="Analyze and map dependencies between Docker Compose services"
    # )(get_service_dependencies)
    
    # Register system monitoring tools
    server.tool(
        name="get_system_info",
        description="Get comprehensive system performance metrics from a device"
    )(get_system_info)
    
    server.tool(
        name="get_drive_health",
        description="Get S.M.A.R.T. drive health information and disk status"
    )(get_drive_health)
    
    server.tool(
        name="get_drives_stats",
        description="Get drive usage statistics, I/O performance, and utilization metrics"
    )(get_drives_stats)
    
    server.tool(
        name="get_system_logs",
        description="Get system logs from journald or traditional syslog"
    )(get_system_logs)
    
    # Register device management tools
    server.tool(
        name="list_devices",
        description="List all registered infrastructure devices with optional filtering"
    )(list_devices)
    
    server.tool(
        name="add_device", 
        description="Add a new device to the infrastructure registry"
    )(add_device)
    
    server.tool(
        name="remove_device",
        description="Remove a device from the infrastructure registry"
    )(remove_device)
    
    server.tool(
        name="edit_device",
        description="Edit/update details of an existing device in the infrastructure registry"
    )(edit_device)
    
    # Register proxy configuration management tools
    server.tool(
        name="list_proxy_configs",
        description="List SWAG reverse proxy configurations with real-time sync check"
    )(list_proxy_configs)
    
    server.tool(
        name="get_proxy_config",
        description="Get specific proxy configuration with real-time file content"
    )(get_proxy_config)
    
    server.tool(
        name="scan_proxy_configs",
        description="Scan proxy configuration directory for fresh configs and sync to database"
    )(scan_proxy_configs)
    
    server.tool(
        name="sync_proxy_config",
        description="Sync specific proxy configuration with file system"
    )(sync_proxy_config)
    
    server.tool(
        name="get_proxy_config_summary",
        description="Get summary statistics for proxy configurations"
    )(get_proxy_config_summary)
    
    # Register SWAG proxy configuration resources
    @server.resource("swag://{service_name}")
    async def swag_service_resource(service_name: str) -> str:
        """Get SWAG service configuration resource content"""
        uri = f"swag://{service_name}"
        resource_data = await get_proxy_config_resource(uri)
        
        # Return appropriate content based on resource type
        if 'content' in resource_data:
            return resource_data['content']
        elif 'raw_content' in resource_data:
            return resource_data['raw_content']
        else:
            # Return JSON representation for structured data
            import json
            return json.dumps(resource_data, indent=2, default=str)
    
    @server.resource("swag://{device}/{path}")
    async def swag_device_resource(device: str, path: str) -> str:
        """Get SWAG device-specific resource content (directory/summary)"""
        uri = f"swag://{device}/{path}"
        resource_data = await get_proxy_config_resource(uri)
        
        # Return JSON representation for structured data
        import json
        return json.dumps(resource_data, indent=2, default=str)
    
    @server.list_resources()
    async def list_resources() -> List[dict]:
        """List all available proxy configuration resources"""
        resources = await list_proxy_config_resources()
        return resources
    
    logger.info("MCP server created with 16 tools (11 HTTP client + 5 proxy config) and proxy resources")
    return server


def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Infrastructure Management MCP Server...")
    
    # Create the MCP server
    server = create_mcp_server()
    
    try:
        # Run the server on HTTP transport
        logger.info("Starting MCP server on HTTP transport at port 9102...")
        server.run(transport="http", host="localhost", port=9102)
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server error: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Cleaning up MCP server...")
        asyncio.run(api_client.close())
        logger.info("MCP server shutdown complete")


if __name__ == "__main__":
    main()