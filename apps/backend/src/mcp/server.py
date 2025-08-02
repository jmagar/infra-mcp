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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to Python path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
sys.path.insert(0, project_root)

# Local imports
from apps.backend.src.core.database import init_database
from apps.backend.src.mcp.resources.compose_configs import get_compose_config_resource
from apps.backend.src.mcp.resources.ports_resources import get_ports_resource, list_ports_resources
from apps.backend.src.mcp.tools.device_info import get_device_info
from apps.backend.src.mcp.tools.device_import import import_devices
from apps.backend.src.mcp.tools.proxy_management import (
    get_proxy_config,
    get_proxy_config_summary,
    list_proxy_configs,
    scan_proxy_configs,
    sync_proxy_config,
)
from apps.backend.src.mcp.tools.compose_deployment import (
    modify_compose_for_device,
    deploy_compose_to_device,
    modify_and_deploy_compose,
    scan_device_ports,
    scan_docker_networks,
    generate_proxy_config,
)
from apps.backend.src.mcp.tools.zfs_management import ZFS_TOOLS
from apps.backend.src.mcp.prompts.device_analysis import (
    analyze_device_performance,
    container_stack_analysis,
    infrastructure_health_check,
    troubleshoot_system_issue,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
            base_url=API_BASE_URL, timeout=httpx.Timeout(API_TIMEOUT), headers=headers
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
    offset: int = 0,
) -> dict[str, Any]:
    """List Docker containers on a specific device"""
    try:
        params = {"all_containers": all_containers, "timeout": timeout, "offset": offset}
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


async def get_container_info(device: str, container_name: str, timeout: int = 60) -> dict[str, Any]:
    """Get detailed information about a specific Docker container"""
    try:
        params = {"timeout": timeout}
        response = await api_client.client.get(
            f"/containers/{device}/{container_name}", params=params
        )
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
    timeout: int = 60,
) -> dict[str, Any]:
    """Get logs from a specific Docker container"""
    try:
        params = {"timeout": timeout}
        if since:
            params["since"] = since
        if tail:
            params["tail"] = tail

        response = await api_client.client.get(
            f"/containers/{device}/{container_name}/logs", params=params
        )
        response.raise_for_status()
        return response.json()

    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting logs for {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container logs: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting logs for {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container logs: {str(e)}") from e


async def start_container(device: str, container_name: str, timeout: int = 60) -> dict[str, Any]:
    """Start a Docker container on a specific device"""
    try:
        params = {"timeout": timeout}
        response = await api_client.client.post(
            f"/containers/{device}/{container_name}/start", params=params
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error starting container {container_name} on {device}: {e}")
        raise Exception(f"Failed to start container: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error starting container {container_name} on {device}: {e}")
        raise Exception(f"Failed to start container: {str(e)}") from e


async def stop_container(
    device: str, container_name: str, timeout: int = 10, force: bool = False, ssh_timeout: int = 60
) -> dict[str, Any]:
    """Stop a Docker container on a specific device"""
    try:
        params = {"timeout": timeout, "force": force, "ssh_timeout": ssh_timeout}
        response = await api_client.client.post(
            f"/containers/{device}/{container_name}/stop", params=params
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error stopping container {container_name} on {device}: {e}")
        raise Exception(f"Failed to stop container: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error stopping container {container_name} on {device}: {e}")
        raise Exception(f"Failed to stop container: {str(e)}") from e


async def restart_container(
    device: str, container_name: str, timeout: int = 10, ssh_timeout: int = 60
) -> dict[str, Any]:
    """Restart a Docker container on a specific device"""
    try:
        params = {"timeout": timeout, "ssh_timeout": ssh_timeout}
        response = await api_client.client.post(
            f"/containers/{device}/{container_name}/restart", params=params
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error restarting container {container_name} on {device}: {e}")
        raise Exception(f"Failed to restart container: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error restarting container {container_name} on {device}: {e}")
        raise Exception(f"Failed to restart container: {str(e)}") from e


async def remove_container(
    device: str,
    container_name: str,
    force: bool = False,
    remove_volumes: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """Remove a Docker container on a specific device"""
    try:
        params = {"force": force, "remove_volumes": remove_volumes, "timeout": timeout}
        response = await api_client.client.delete(
            f"/containers/{device}/{container_name}", params=params
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error removing container {container_name} on {device}: {e}")
        raise Exception(f"Failed to remove container: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error removing container {container_name} on {device}: {e}")
        raise Exception(f"Failed to remove container: {str(e)}") from e


async def get_container_stats(device: str, container_name: str, timeout: int = 30) -> dict[str, Any]:
    """Get real-time resource usage statistics for a Docker container"""
    try:
        params = {"timeout": timeout}
        response = await api_client.client.get(
            f"/containers/{device}/{container_name}/stats", params=params
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting stats for container {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container stats: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting stats for container {container_name} on {device}: {e}")
        raise Exception(f"Failed to get container stats: {str(e)}") from e


async def execute_in_container(
    device: str,
    container_name: str,
    command: str,
    interactive: bool = False,
    user: str | None = None,
    workdir: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Execute a command inside a Docker container"""
    try:
        params = {
            "command": command,
            "interactive": interactive,
            "timeout": timeout,
        }
        if user:
            params["user"] = user
        if workdir:
            params["workdir"] = workdir

        response = await api_client.client.post(
            f"/containers/{device}/{container_name}/exec", params=params
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error executing command in container {container_name} on {device}: {e}")
        raise Exception(f"Failed to execute command in container: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error executing command in container {container_name} on {device}: {e}")
        raise Exception(f"Failed to execute command in container: {str(e)}") from e


# System Monitoring Tools


async def get_drive_health(
    device: str, drive: str | None = None, timeout: int = 60
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
    device: str, drive: str | None = None, timeout: int = 60
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


async def get_device_logs(
    device: str,
    service: str | None = None,
    since: str | None = None,
    lines: int = 100,
    timeout: int = 60,
) -> dict[str, Any]:
    """Get system logs from journald or traditional syslog"""
    try:
        params = {"lines": lines, "timeout": timeout}
        if service:
            params["service"] = service
        if since:
            params["since"] = since

        response = await api_client.client.get(f"/devices/{device}/logs", params=params)
        response.raise_for_status()
        return response.json()

    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting device logs for {device}: {e}")
        raise Exception(f"Failed to get device logs: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting device logs for {device}: {e}")
        raise Exception(f"Failed to get device logs: {str(e)}") from e


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
    tags: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Add a new device to the infrastructure registry"""
    try:
        device_data = {
            "hostname": hostname,
            "device_type": device_type,
            "monitoring_enabled": monitoring_enabled
        }
        
        if description is not None:
            device_data["description"] = description
        if location is not None:
            device_data["location"] = location
        if ip_address is not None:
            device_data["ip_address"] = ip_address
        if ssh_port is not None:
            device_data["ssh_port"] = ssh_port
        if ssh_username is not None:
            device_data["ssh_username"] = ssh_username
        if tags is not None:
            device_data["tags"] = tags
        
        response = await api_client.client.post("/devices", json=device_data)
        response.raise_for_status()
        return response.json()
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error adding device {hostname}: {e}")
        raise Exception(f"Failed to add device: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error adding device {hostname}: {e}")
        raise Exception(f"Failed to add device: {str(e)}") from e


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
            "operation_result": result,
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
    tags: dict[str, str] | None = None,
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
            "device_info": result,
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
        instructions="Comprehensive infrastructure monitoring and management tools for heterogeneous Linux environments",
    )

    # Register container management tools
    server.tool(name="list_containers", description="List Docker containers on a specific device")(
        list_containers
    )

    server.tool(
        name="get_container_info",
        description="Get detailed information about a specific Docker container",
    )(get_container_info)

    server.tool(name="get_container_logs", description="Get logs from a specific Docker container")(
        get_container_logs
    )

    server.tool(name="start_container", description="Start a Docker container on a specific device")(
        start_container
    )

    server.tool(name="stop_container", description="Stop a Docker container on a specific device")(
        stop_container
    )

    server.tool(name="restart_container", description="Restart a Docker container on a specific device")(
        restart_container
    )

    server.tool(name="remove_container", description="Remove a Docker container on a specific device")(
        remove_container
    )

    server.tool(name="get_container_stats", description="Get real-time resource usage statistics for a Docker container")(
        get_container_stats
    )

    server.tool(name="execute_in_container", description="Execute a command inside a Docker container")(
        execute_in_container
    )

    # DISABLED: Service dependencies endpoint does not exist in current API
    # server.tool(
    #     name="get_service_dependencies",
    #     description="Analyze and map dependencies between Docker Compose services"
    # )(get_service_dependencies)

    # Register system monitoring tools

    server.tool(
        name="get_drive_health",
        description="Get S.M.A.R.T. drive health information and disk status",
    )(get_drive_health)

    server.tool(
        name="get_drives_stats",
        description="Get drive usage statistics, I/O performance, and utilization metrics",
    )(get_drives_stats)

    server.tool(
        name="get_device_logs", description="Get system logs from journald or traditional syslog"
    )(get_device_logs)

    # Register device management tools
    server.tool(
        name="list_devices",
        description="List all registered infrastructure devices with optional filtering",
    )(list_devices)

    server.tool(name="add_device", description="Add a new device to the infrastructure registry")(
        add_device
    )

    server.tool(
        name="remove_device", description="Remove a device from the infrastructure registry"
    )(remove_device)

    server.tool(
        name="edit_device",
        description="Edit/update details of an existing device in the infrastructure registry",
    )(edit_device)

    # Register proxy configuration management tools
    server.tool(
        name="list_proxy_configs",
        description="List SWAG reverse proxy configurations with real-time sync check",
    )(list_proxy_configs)

    server.tool(
        name="get_proxy_config",
        description="Get specific proxy configuration with real-time file content",
    )(get_proxy_config)

    server.tool(
        name="scan_proxy_configs",
        description="Scan proxy configuration directory for fresh configs and sync to database",
    )(scan_proxy_configs)

    server.tool(
        name="sync_proxy_config", description="Sync specific proxy configuration with file system"
    )(sync_proxy_config)

    server.tool(
        name="get_proxy_config_summary",
        description="Get summary statistics for proxy configurations",
    )(get_proxy_config_summary)

    # Register Docker Compose deployment tools
    server.tool(
        name="modify_compose_for_device",
        description="Modify docker-compose content for deployment on target device - updates paths, ports, networks, and generates proxy configs",
    )(modify_compose_for_device)

    server.tool(
        name="deploy_compose_to_device",
        description="Deploy docker-compose content to target device - creates directories, backups files, and starts services",
    )(deploy_compose_to_device)

    server.tool(
        name="modify_and_deploy_compose",
        description="Modify and deploy docker-compose in a single operation with sensible defaults",
    )(modify_and_deploy_compose)

    server.tool(
        name="scan_device_ports",
        description="Scan for available ports on target device to avoid conflicts in port mappings",
    )(scan_device_ports)

    server.tool(
        name="scan_docker_networks",
        description="Scan Docker networks on target device and provide configuration recommendations",
    )(scan_docker_networks)

    server.tool(
        name="generate_proxy_config",
        description="Generate SWAG reverse proxy configuration for a specific service",
    )(generate_proxy_config)

    # Register ZFS management tools
    for tool_name, tool_config in ZFS_TOOLS.items():
        server.tool(name=tool_name, description=tool_config["description"])(tool_config["function"])

    # Register comprehensive device info tool
    server.tool(
        name="get_device_info",
        description="Get comprehensive device information including capabilities analysis and system metrics (replaces analyze_device and get_system_info)",
    )(get_device_info)

    # Register device import tool
    server.tool(
        name="import_devices_from_ssh_config",
        description="Import devices from SSH configuration file. Parses SSH config to extract host information and creates or updates devices in the registry.",
    )(import_devices)

    # Register infrastructure analysis prompts
    server.prompt(analyze_device_performance)
    server.prompt(container_stack_analysis)
    server.prompt(infrastructure_health_check)
    server.prompt(troubleshoot_system_issue)

    # Register SWAG proxy configuration resources
    @server.resource(
        uri="swag://configs",
        name="SWAG Configurations",
        description="List all SWAG reverse proxy configurations",
        mime_type="application/json",
    )
    async def swag_configs_list() -> str:
        """Get list of all SWAG proxy configurations"""
        try:
            response = await api_client.client.get("/proxy/configs")
            response.raise_for_status()
            configs_data = response.json()
            return json.dumps(configs_data, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)

    @server.resource(
        uri="swag://{service_name}",
        name="SWAG Service Configuration",
        description="Get SWAG service configuration content",
        mime_type="text/plain",
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
            if "content" in resource_data:
                return resource_data["content"]
            elif "raw_content" in resource_data:
                return resource_data["raw_content"]
            else:
                # Return JSON representation for structured data
                return json.dumps(resource_data, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return f"Error accessing resource {uri}: {str(e)}"

    @server.resource(
        uri="swag://{device}/{path}",
        name="SWAG Device Resource",
        description="Get SWAG device-specific resource content",
        mime_type="application/json",
    )
    async def swag_device_resource(device: str, path: str) -> str:
        """Get SWAG device-specific resource content (directory/summary)"""
        uri = f"swag://{device}/{path}"
        try:
            # TODO: Implement device/path specific endpoints in FastAPI
            # Use HTTP client - this endpoint may not exist yet, placeholder for now
            return json.dumps(
                {
                    "message": "Device/path specific resources not yet implemented",
                    "uri": uri,
                    "device": device,
                    "path": path,
                },
                indent=2,
                ensure_ascii=False,
            )
        except Exception as e:
            return json.dumps({"error": str(e), "uri": uri}, indent=2, ensure_ascii=False)

    # Register additional infrastructure resources
    @server.resource(
        uri="infra://devices",
        name="Infrastructure Devices",
        description="List all registered infrastructure devices",
        mime_type="application/json",
    )
    async def infra_devices_resource() -> str:
        """Get list of all infrastructure devices"""
        try:
            devices_data = await list_devices()
            return json.dumps(devices_data, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)

    @server.resource(
        uri="infra://{device}/status",
        name="Device Status",
        description="Get comprehensive device status and metrics",
        mime_type="application/json",
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
                "system_info": system_info
                if not isinstance(system_info, Exception)
                else {"error": str(system_info)},
                "containers": containers_info
                if not isinstance(containers_info, Exception)
                else {"error": str(containers_info)},
            }

            return json.dumps(status_data, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e), "device": device}, indent=2, ensure_ascii=False)

    # Register Docker Compose configuration resources
    @server.resource(
        uri="docker://configs",
        name="Docker Compose Global Configs",
        description="Global listing of all Docker Compose configurations across all devices",
        mime_type="application/json",
    )
    async def docker_configs_global() -> str:
        """Get global listing of all Docker Compose configurations"""
        try:
            configs_data = await get_compose_config_resource("docker://configs")
            return json.dumps(configs_data, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)

    @server.resource(
        uri="docker://{device}/stacks",
        name="Docker Compose Stacks",
        description="List all Docker Compose stacks on a specific device",
        mime_type="application/json",
    )
    async def docker_device_stacks(device: str) -> str:
        """Get list of Docker Compose stacks on device"""
        try:
            stacks_data = await get_compose_config_resource(f"docker://{device}/stacks")
            return json.dumps(stacks_data, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e), "device": device}, indent=2, ensure_ascii=False)

    @server.resource(
        uri="docker://{device}/{service}",
        name="Docker Compose Service Configuration",
        description="Get Docker Compose configuration for a specific service",
        mime_type="text/yaml",
    )
    async def docker_service_config(device: str, service: str) -> str:
        """Get Docker Compose service configuration"""
        try:
            service_data = await get_compose_config_resource(f"docker://{device}/{service}")

            # Return raw YAML content if available, otherwise JSON
            if "content" in service_data:
                return service_data["content"]
            else:
                return json.dumps(service_data, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps(
                {"error": str(e), "device": device, "service": service},
                indent=2,
                ensure_ascii=False,
            )

    # Register ZFS resources
    @server.resource(
        uri="zfs://pools/{hostname}",
        name="ZFS Pools",
        description="Get ZFS pools for a device",
        mime_type="application/json",
    )
    async def zfs_pools(hostname: str) -> str:
        """Get ZFS pools for a device"""
        try:
            response = await api_client.client.get(f"/zfs/{hostname}/pools")
            response.raise_for_status()
            data = response.json()

            return json.dumps(
                {
                    "resource_type": "zfs_pools",
                    "hostname": hostname,
                    "pools": data.get("pools", []),
                    "total_pools": data.get("total_pools", 0),
                    "uri": f"zfs://pools/{hostname}",
                },
                indent=2,
                default=str,
            )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting ZFS pools for {hostname}: {e}")
            return json.dumps(
                {
                    "error": f"Failed to get ZFS pools: {str(e)}",
                    "hostname": hostname,
                    "uri": f"zfs://pools/{hostname}",
                },
                indent=2,
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"Error getting ZFS pools for {hostname}: {e}")
            return json.dumps(
                {"error": str(e), "hostname": hostname, "uri": f"zfs://pools/{hostname}"},
                indent=2,
                ensure_ascii=False,
            )

    @server.resource(
        uri="zfs://pools/{hostname}/{pool_name}",
        name="ZFS Pool Status",
        description="Get ZFS pool status for a specific pool",
        mime_type="application/json",
    )
    async def zfs_pool_status(hostname: str, pool_name: str) -> str:
        """Get ZFS pool status for a specific pool"""
        try:
            response = await api_client.client.get(f"/zfs/{hostname}/pools/{pool_name}/status")
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps(
                {"error": str(e), "hostname": hostname, "pool_name": pool_name},
                indent=2,
                ensure_ascii=False,
            )

    @server.resource(
        uri="zfs://datasets/{hostname}",
        name="ZFS Datasets",
        description="Get ZFS datasets for a device",
        mime_type="application/json",
    )
    async def zfs_datasets(hostname: str) -> str:
        """Get ZFS datasets for a device"""
        try:
            response = await api_client.client.get(f"/zfs/{hostname}/datasets")
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e), "hostname": hostname}, indent=2, ensure_ascii=False)

    @server.resource(
        uri="zfs://snapshots/{hostname}",
        name="ZFS Snapshots",
        description="Get ZFS snapshots for a device",
        mime_type="application/json",
    )
    async def zfs_snapshots(hostname: str) -> str:
        """Get ZFS snapshots for a device"""
        try:
            response = await api_client.client.get(f"/zfs/{hostname}/snapshots")
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e), "hostname": hostname}, indent=2, ensure_ascii=False)

    @server.resource(
        uri="zfs://health/{hostname}",
        name="ZFS Health",
        description="Get ZFS health status for a device",
        mime_type="application/json",
    )
    async def zfs_health(hostname: str) -> str:
        """Get ZFS health status for a device"""
        try:
            response = await api_client.client.get(f"/zfs/{hostname}/health")
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e), "hostname": hostname}, indent=2, ensure_ascii=False)

    # Register Logs resources
    @server.resource(
        uri="logs://{hostname}",
        name="System Logs",
        description="Get system logs (syslog/journald) for a device",
        mime_type="application/json",
    )
    async def logs_system(hostname: str) -> str:
        """Get system logs for a device"""
        try:
            response = await api_client.client.get(f"/devices/{hostname}/logs")
            response.raise_for_status()
            data = response.json()

            return json.dumps(
                {
                    "resource_type": "system_logs",
                    "hostname": hostname,
                    "logs": data,
                    "uri": f"logs://{hostname}",
                },
                indent=2,
                default=str,
                ensure_ascii=False,
            )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting system logs for {hostname}: {e}")
            return json.dumps(
                {
                    "error": f"Failed to get system logs: {str(e)}",
                    "hostname": hostname,
                    "uri": f"logs://{hostname}",
                },
                indent=2,
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"Error getting system logs for {hostname}: {e}")
            return json.dumps(
                {"error": str(e), "hostname": hostname, "uri": f"logs://{hostname}"},
                indent=2,
                ensure_ascii=False,
            )

    @server.resource(
        uri="logs://{hostname}/{container_name}",
        name="Container Logs",
        description="Get Docker container logs for a specific container",
        mime_type="application/json",
    )
    async def logs_container(hostname: str, container_name: str) -> str:
        """Get container logs for a specific container"""
        try:
            response = await api_client.client.get(f"/containers/{hostname}/{container_name}/logs")
            response.raise_for_status()
            data = response.json()

            return json.dumps(
                {
                    "resource_type": "container_logs",
                    "hostname": hostname,
                    "container_name": container_name,
                    "logs": data,
                    "uri": f"logs://{hostname}/{container_name}",
                },
                indent=2,
                default=str,
                ensure_ascii=False,
            )
        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error getting container logs for {container_name} on {hostname}: {e}"
            )
            return json.dumps(
                {
                    "error": f"Failed to get container logs: {str(e)}",
                    "hostname": hostname,
                    "container_name": container_name,
                    "uri": f"logs://{hostname}/{container_name}",
                },
                indent=2,
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"Error getting container logs for {container_name} on {hostname}: {e}")
            return json.dumps(
                {
                    "error": str(e),
                    "hostname": hostname,
                    "container_name": container_name,
                    "uri": f"logs://{hostname}/{container_name}",
                },
                indent=2,
                ensure_ascii=False,
            )

    @server.resource(
        uri="logs://{hostname}/vms",
        name="VM Logs - All",
        description="Get libvirtd daemon logs for VM management",
        mime_type="application/json",
    )
    async def logs_vms_all(hostname: str) -> str:
        """Get libvirtd daemon logs"""
        try:
            # Use HTTP endpoint for VM logs
            response = await api_client.client.get(f"/vms/{hostname}/logs")
            response.raise_for_status()
            data = response.json()
            
            return json.dumps(
                {
                    "resource_type": "libvirt_logs",
                    "hostname": hostname,
                    "log_source": data.get("log_source", "libvirtd.log or journalctl"),
                    "logs": data.get("logs", ""),
                    "uri": f"logs://{hostname}/vms",
                },
                indent=2,
                default=str,
                ensure_ascii=False,
            )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting VM logs for {hostname}: {e}")
            return json.dumps(
                {
                    "error": f"Failed to get VM logs: {str(e)}",
                    "hostname": hostname,
                    "uri": f"logs://{hostname}/vms"
                },
                indent=2,
                ensure_ascii=False
            )
        except Exception as e:
            logger.error(f"Error getting VM logs for {hostname}: {e}")
            return json.dumps(
                {"error": str(e), "hostname": hostname, "uri": f"logs://{hostname}/vms"},
                indent=2,
                ensure_ascii=False,
            )

    @server.resource(
        uri="logs://{hostname}/vms/{vm_name}",
        name="VM Logs - Specific",
        description="Get logs for a specific virtual machine",
        mime_type="application/json",
    )
    async def logs_vm_specific(hostname: str, vm_name: str) -> str:
        """Get logs for a specific VM"""
        try:
            # Use HTTP endpoint for specific VM logs
            response = await api_client.client.get(f"/vms/{hostname}/logs/{vm_name}")
            response.raise_for_status()
            data = response.json()

            return json.dumps(
                {
                    "resource_type": "vm_logs",
                    "hostname": hostname,
                    "vm_name": vm_name,
                    "log_source": data.get("log_source", f"qemu/{vm_name}.log"),
                    "logs": data.get("logs", ""),
                    "uri": f"logs://{hostname}/vms/{vm_name}",
                },
                indent=2,
                default=str,
                ensure_ascii=False,
            )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting VM logs for {vm_name} on {hostname}: {e}")
            return json.dumps(
                {
                    "error": f"Failed to get VM logs: {str(e)}",
                    "hostname": hostname,
                    "vm_name": vm_name,
                    "uri": f"logs://{hostname}/vms/{vm_name}",
                },
                indent=2,
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"Error getting VM logs for {vm_name} on {hostname}: {e}")
            return json.dumps(
                {
                    "error": str(e),
                    "hostname": hostname,
                    "vm_name": vm_name,
                    "uri": f"logs://{hostname}/vms/{vm_name}",
                },
                indent=2,
                ensure_ascii=False,
            )

    # Ports Resources
    @server.resource(
        uri="ports://{hostname}",
        name="Network Ports",
        description="Get network port information and listening processes for a device",
        mime_type="application/json",
    )
    async def ports_device(hostname: str) -> str:
        """Get network ports and processes for a device"""
        try:
            return await get_ports_resource(f"ports://{hostname}")
        except Exception as e:
            logger.error(f"Error getting ports for {hostname}: {e}")
            return json.dumps({
                "error": str(e),
                "hostname": hostname,
                "uri": f"ports://{hostname}"
            }, indent=2, ensure_ascii=False)

    logger.info(
        "MCP server created with 24 tools, 4 prompts, and infrastructure + compose + ZFS + logs + ports resources"
    )
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
