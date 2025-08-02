"""
Logs MCP Resources

MCP resources for exposing system and container logs
with real-time access via the REST API.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

import httpx

from apps.backend.src.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_api_config():
    """Get API configuration settings"""
    settings = get_settings()
    return {
        "base_url": f"http://localhost:{settings.api.port}",
        "api_key": settings.auth.api_key,
        "timeout": 30,
    }


async def _make_api_request(
    endpoint: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Make authenticated request to the REST API"""
    config = _get_api_config()

    headers = {}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"

    full_url = f"{config['base_url']}{endpoint}"
    logger.info(f"Making API request to: {full_url}")

    async with httpx.AsyncClient(timeout=config["timeout"]) as client:
        try:
            response = await client.get(full_url, headers=headers, params=params or {})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API request failed to {full_url}: {e}")
            logger.error(
                f"Response status: {e.response.status_code if hasattr(e, 'response') else 'unknown'}"
            )
            logger.error(
                f"Response text: {e.response.text if hasattr(e, 'response') else 'unknown'}"
            )
            raise RuntimeError(f"Failed to fetch logs data: {str(e)}")


async def get_system_logs_resource(uri: str) -> str:
    """
    Get system logs resource content.

    URI format: logs://{hostname} or logs://{hostname}?service={service}&since={since}&lines={lines}
    """
    try:
        # Parse URI: logs://hostname?service=service&since=timestamp&lines=100
        parsed = urlparse(uri)
        if not parsed.scheme == "logs" or not parsed.netloc:
            raise ValueError(f"Invalid logs URI: {uri}")

        hostname = parsed.netloc
        query_params = parse_qs(parsed.query)

        # Extract query parameters
        service = query_params.get("service", [None])[0]
        since = query_params.get("since", [None])[0]
        lines = query_params.get("lines", ["100"])[0]

        # Build endpoint parameters
        endpoint = f"/api/devices/{hostname}/logs"
        params = {"lines": int(lines), "timeout": 60}

        if service:
            params["service"] = service
        if since:
            params["since"] = since

        data = await _make_api_request(endpoint, params)

        # Extract the actual log content to avoid double JSON encoding
        log_content = data.get("logs", "") if isinstance(data, dict) else str(data)

        return json.dumps(
            {
                "resource_type": "system_logs",
                "hostname": hostname,
                "service": service,
                "since": since,
                "lines": int(lines),
                "log_content": log_content,
                "metadata": {
                    "execution_time": data.get("execution_time")
                    if isinstance(data, dict)
                    else None,
                    "timestamp": data.get("timestamp") if isinstance(data, dict) else None,
                },
                "uri": uri,
            },
            indent=2,
            default=str,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Error fetching system logs resource {uri}: {e}")
        return json.dumps(
            {"error": str(e), "uri": uri, "resource_type": "system_logs"},
            indent=2,
            ensure_ascii=False,
        )


async def get_container_logs_resource(uri: str) -> str:
    """
    Get container logs resource content.

    URI format: logs://{hostname}/{container_name} or
               logs://{hostname}/{container_name}?since={since}&tail={tail}
    """
    try:
        # Parse URI: logs://hostname/container_name?since=timestamp&tail=100
        parsed = urlparse(uri)
        if not parsed.scheme == "logs" or not parsed.netloc or not parsed.path:
            raise ValueError(f"Invalid container logs URI: {uri}")

        hostname = parsed.netloc
        container_name = parsed.path.strip("/")
        query_params = parse_qs(parsed.query)

        # Extract query parameters
        since = query_params.get("since", [None])[0]
        tail = query_params.get("tail", ["100"])[0]

        # Build endpoint parameters
        endpoint = f"/api/containers/{hostname}/{container_name}/logs"
        params = {"timeout": 60}

        if since:
            params["since"] = since
        if tail:
            params["tail"] = int(tail)

        data = await _make_api_request(endpoint, params)

        # Extract the actual log content to avoid double JSON encoding
        log_content = data.get("logs", "") if isinstance(data, dict) else str(data)

        return json.dumps(
            {
                "resource_type": "container_logs",
                "hostname": hostname,
                "container_name": container_name,
                "since": since,
                "tail": int(tail) if tail else None,
                "log_content": log_content,
                "metadata": {
                    "execution_time": data.get("execution_time")
                    if isinstance(data, dict)
                    else None,
                    "timestamps": data.get("timestamps") if isinstance(data, dict) else None,
                    "container_info": {
                        "hostname": data.get("hostname") if isinstance(data, dict) else hostname,
                        "container_name": data.get("container_name")
                        if isinstance(data, dict)
                        else container_name,
                    },
                },
                "uri": uri,
            },
            indent=2,
            default=str,
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Error fetching container logs resource {uri}: {e}")
        return json.dumps(
            {"error": str(e), "uri": uri, "resource_type": "container_logs"},
            indent=2,
            ensure_ascii=False,
        )


async def get_vm_logs_resource(uri: str) -> str:
    """
    Get VM logs resource content.

    URI format: logs://{hostname}/vms or logs://{hostname}/vms/{vm_name}
    """
    try:
        # Parse URI: logs://hostname/vms or logs://hostname/vms/vm_name
        parsed = urlparse(uri)
        if not parsed.scheme == "logs" or not parsed.netloc:
            raise ValueError(f"Invalid VM logs URI: {uri}")

        hostname = parsed.netloc
        path_parts = parsed.path.strip("/").split("/")

        if len(path_parts) < 1 or path_parts[0] != "vms":
            raise ValueError(f"Invalid VM logs URI: {uri}")

        if len(path_parts) == 1:
            # logs://hostname/vms - get libvirtd.log
            vm_name = None
        else:
            # logs://hostname/vms/vm_name - get specific VM log
            vm_name = path_parts[1]

        # Use SSH to get VM logs since they're file-based
        import asyncio
        from apps.backend.src.utils.ssh_client import execute_ssh_command_simple

        if vm_name:
            # Get specific VM log file
            log_command = (
                f"cat /var/log/libvirt/qemu/{vm_name}.log 2>/dev/null || echo 'VM log not found'"
            )
            result = await execute_ssh_command_simple(hostname, log_command, timeout=30)

            if result.return_code == 0:
                log_content = result.stdout
            else:
                log_content = f"Error reading VM log: {result.stderr}"

            return json.dumps(
                {
                    "resource_type": "vm_logs",
                    "hostname": hostname,
                    "vm_name": vm_name,
                    "log_file": f"/var/log/libvirt/qemu/{vm_name}.log",
                    "log_content": log_content,
                    "uri": uri,
                },
                indent=2,
                default=str,
                ensure_ascii=False,
            )
        else:
            # Get libvirtd.log
            log_command = "cat /var/log/libvirt/libvirtd.log 2>/dev/null || journalctl -u libvirtd --no-pager -n 100"
            result = await execute_ssh_command_simple(hostname, log_command, timeout=30)

            if result.return_code == 0:
                log_content = result.stdout
            else:
                log_content = f"Error reading libvirt logs: {result.stderr}"

            return json.dumps(
                {
                    "resource_type": "libvirt_logs",
                    "hostname": hostname,
                    "log_source": "libvirtd.log or journalctl",
                    "log_content": log_content,
                    "uri": uri,
                },
                indent=2,
                default=str,
                ensure_ascii=False,
            )

    except Exception as e:
        logger.error(f"Error fetching VM logs resource {uri}: {e}")
        return json.dumps(
            {"error": str(e), "uri": uri, "resource_type": "vm_logs"}, indent=2, ensure_ascii=False
        )


async def list_logs_resources() -> List[Dict[str, Any]]:
    """List all available logs MCP resources"""
    try:
        # Get list of devices from API
        config = _get_api_config()
        headers = {}
        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"

        async with httpx.AsyncClient(timeout=config["timeout"]) as client:
            response = await client.get(f"{config['base_url']}/api/devices", headers=headers)
            response.raise_for_status()
            devices = response.json()

        resources = []

        # Generate logs resources for each device
        for device in devices:
            hostname = device.get("hostname", "unknown")

            # System logs resource
            resources.append(
                {
                    "uri": f"logs://{hostname}",
                    "name": f"System Logs - {hostname}",
                    "description": f"System logs (syslog/journald) for {hostname}",
                    "mimeType": "application/json",
                }
            )

            # Try to get containers for this device to create container log resources
            try:
                containers_response = await client.get(
                    f"{config['base_url']}/api/containers/{hostname}",
                    headers=headers,
                    params={"all_containers": True},
                )
                if containers_response.status_code == 200:
                    containers_data = containers_response.json()
                    containers = containers_data.get("containers", [])

                    for container in containers:
                        container_name = container.get("name", "").lstrip("/")
                        if container_name:
                            resources.append(
                                {
                                    "uri": f"logs://{hostname}/{container_name}",
                                    "name": f"Container Logs - {container_name} ({hostname})",
                                    "description": f"Docker logs for {container_name} container on {hostname}",
                                    "mimeType": "application/json",
                                }
                            )
            except Exception as e:
                logger.warning(f"Could not fetch containers for {hostname}: {e}")

        return resources

    except Exception as e:
        logger.error(f"Error listing logs resources: {e}")
        return [
            {
                "uri": "logs://error",
                "name": "Logs Resources Error",
                "description": f"Failed to list logs resources: {str(e)}",
                "mimeType": "text/plain",
            }
        ]


async def get_logs_resource(uri: str) -> str:
    """Route logs resource requests to appropriate handlers"""
    try:
        parsed = urlparse(uri)
        logger.info(f"Routing logs resource request - URI: {uri}, Path: {parsed.path}")

        if parsed.path and parsed.path != "/":
            path_parts = parsed.path.strip("/").split("/")

            if path_parts[0] == "vms":
                # VM logs: logs://hostname/vms or logs://hostname/vms/vm_name
                logger.info(f"Routing to VM logs handler for {uri}")
                return await get_vm_logs_resource(uri)
            else:
                # Container logs: logs://hostname/container_name
                logger.info(f"Routing to container logs handler for {uri}")
                return await get_container_logs_resource(uri)
        else:
            # System logs: logs://hostname
            logger.info(f"Routing to system logs handler for {uri}")
            return await get_system_logs_resource(uri)

    except Exception as e:
        logger.error(f"Error routing logs resource request {uri}: {e}")
        return json.dumps(
            {"error": str(e), "uri": uri, "resource_type": "logs_routing_error"},
            indent=2,
            ensure_ascii=False,
        )
