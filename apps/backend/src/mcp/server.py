#!/usr/bin/env python3
"""
Standalone Infrastructure Management MCP Server

This server provides MCP tools that make HTTP calls to the FastAPI REST endpoints
instead of doing direct SSH operations. This eliminates code duplication and ensures
consistency between MCP and REST interfaces.
"""

# Standard library imports
import asyncio
import json
import logging
import os
import sys
from typing import Any

# Third-party imports
import httpx
from fastmcp import FastMCP

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

# Local imports
from apps.backend.src.core.database import init_database
from apps.backend.src.mcp.resources.compose_configs import (
    get_compose_config_resource, list_compose_config_resources
)
from apps.backend.src.mcp.resources.proxy_configs import get_proxy_config_resource
from apps.backend.src.mcp.tools.device_info import get_device_info
from apps.backend.src.mcp.tools.device_management import add_device as device_add_device
from apps.backend.src.mcp.tools.proxy_management import (
    get_proxy_config, get_proxy_config_summary, list_proxy_configs,
    scan_proxy_configs, sync_proxy_config
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
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.warning("API_KEY environment variable not set. Authentication may fail.")


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
        raise Exception(f"Failed to list containers: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error listing containers on {device}: {e}")
        raise Exception(f"Failed to list containers: {str(e)}") from e


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
        raise Exception(f"Failed to get container info: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting container info for {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container info: {str(e)}") from e


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
        raise Exception(f"Failed to get container logs: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting logs for {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container logs: {str(e)}") from e


# System Monitoring Tools


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
        raise Exception(f"Failed to get drive health: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting drive health for {device}: {e}")
        raise Exception(f"Failed to get drive health: {str(e)}") from e


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
        raise Exception(f"Failed to get drives stats: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting drives stats for {device}: {e}")
        raise Exception(f"Failed to get drives stats: {str(e)}") from e


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
        raise Exception(f"Failed to get system logs: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting system logs for {device}: {e}")
        raise Exception(f"Failed to get system logs: {str(e)}") from e


# Device Management Tools
async def list_devices() -> dict[str, Any]:
    """List all registered infrastructure devices"""
    try:
        response = await api_client.client.get("/devices")
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error listing devices: {e}")
        raise Exception(f"Failed to list devices: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise Exception(f"Failed to list devices: {str(e)}") from e


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
    
    # Register comprehensive device info tool
    server.tool(
        name="get_device_info",
        description="Get comprehensive device information including capabilities analysis and system metrics (replaces analyze_device and get_system_info)"
    )(get_device_info)
    
    # Register SWAG proxy configuration resources
    @server.resource(
        uri="swag://configs",
        name="SWAG Configurations",
        description="List all SWAG reverse proxy configurations",
        mime_type="application/json"
    )
    async def swag_configs_list() -> str:
        """Get list of all SWAG proxy configurations"""
        try:
            response = await api_client.client.get("/proxy/configs")
            response.raise_for_status()
            configs_data = response.json()
            return json.dumps(configs_data, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    
    @server.resource(
        uri="swag://{service_name}",
        name="SWAG Service Configuration",
        description="Get SWAG service configuration content",
        mime_type="text/plain"
    )
    async def swag_service_resource(service_name: str) -> str:
        """Get SWAG service configuration resource content"""
        uri = f"swag://{service_name}"
        try:
            # Use HTTP client to get proxy config
            response = await api_client.client.get(f"/proxy/configs/{service_name}")
            response.raise_for_status()
            resource_data = response.json()
            
            # Return appropriate content based on resource type
            if 'content' in resource_data:
                return resource_data['content']
            elif 'raw_content' in resource_data:
                return resource_data['raw_content']
            else:
                # Return JSON representation for structured data
                return json.dumps(resource_data, indent=2, default=str)
        except Exception as e:
            return f"Error accessing resource {uri}: {str(e)}"
    
    @server.resource(
        uri="swag://{device}/{path}",
        name="SWAG Device Resource",
        description="Get SWAG device-specific resource content",
        mime_type="application/json"
    )
    async def swag_device_resource(device: str, path: str) -> str:
        """Get SWAG device-specific resource content (directory/summary)"""
        uri = f"swag://{device}/{path}"
        try:
            # Use HTTP client - this endpoint may not exist yet, placeholder for now
            # Would need to implement device/path specific endpoints in FastAPI
            return json.dumps({
                "message": "Device/path specific resources not yet implemented",
                "uri": uri,
                "device": device,
                "path": path
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "uri": uri}, indent=2)
    
    # Register additional infrastructure resources
    @server.resource(
        uri="infra://devices",
        name="Infrastructure Devices",
        description="List all registered infrastructure devices",
        mime_type="application/json"
    )
    async def infra_devices_resource() -> str:
        """Get list of all infrastructure devices"""
        try:
            devices_data = await list_devices()
            return json.dumps(devices_data, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    
    @server.resource(
        uri="infra://{device}/status",
        name="Device Status",
        description="Get comprehensive device status and metrics",
        mime_type="application/json"
    )
    async def infra_device_status(device: str) -> str:
        """Get device status including system info and containers"""
        try:
            # Get system info and container list in parallel
            import asyncio
            system_task = asyncio.create_task(get_device_info(device, include_processes=False))
            containers_task = asyncio.create_task(list_containers(device, all_containers=True))
            
            system_info, containers_info = await asyncio.gather(
                system_task, containers_task, return_exceptions=True
            )
            
            status_data = {
                "device": device,
                "timestamp": None,
                "system_info": system_info if not isinstance(system_info, Exception) else {"error": str(system_info)},
                "containers": containers_info if not isinstance(containers_info, Exception) else {"error": str(containers_info)}
            }
            
            return json.dumps(status_data, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "device": device}, indent=2)
    
    # Register Docker Compose configuration resources
    @server.resource(
        uri="docker://configs",
        name="Docker Compose Global Configs",
        description="Global listing of all Docker Compose configurations across all devices",
        mime_type="application/json"
    )
    async def docker_configs_global() -> str:
        """Get global listing of all Docker Compose configurations"""
        try:
            configs_data = await get_compose_config_resource("docker://configs")
            return json.dumps(configs_data, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    
    @server.resource(
        uri="docker://{device}/stacks",
        name="Docker Compose Stacks",
        description="List all Docker Compose stacks on a specific device",
        mime_type="application/json"
    )
    async def docker_device_stacks(device: str) -> str:
        """Get list of Docker Compose stacks on device"""
        try:
            stacks_data = await get_compose_config_resource(f"docker://{device}/stacks")
            return json.dumps(stacks_data, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "device": device}, indent=2)
    
    @server.resource(
        uri="docker://{device}/{service}",
        name="Docker Compose Service Configuration",
        description="Get Docker Compose configuration for a specific service",
        mime_type="text/yaml"
    )
    async def docker_service_config(device: str, service: str) -> str:
        """Get Docker Compose service configuration"""
        try:
            service_data = await get_compose_config_resource(f"docker://{device}/{service}")
            
            # Return raw YAML content if available, otherwise JSON
            if 'content' in service_data:
                return service_data['content']
            else:
                return json.dumps(service_data, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "device": device, "service": service}, indent=2)
    
    logger.info("MCP server created with 17 tools (11 HTTP client + 5 proxy config + 1 device analysis) and infrastructure + compose resources")
    return server


async def initialize_mcp_server():
    """Initialize database and other required services for MCP server"""
    logger.info("Initializing MCP server database connection...")
    try:
        await init_database()
        logger.info("MCP server database initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database for MCP server: {e}")
        raise


def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Infrastructure Management MCP Server...")
    
    # Initialize database first
    try:
        asyncio.run(initialize_mcp_server())
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        return
    
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