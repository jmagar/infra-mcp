"""
System Monitoring MCP Tools

This module implements MCP tools for system performance monitoring,
resource usage analysis, and health checking across infrastructure devices.

Uses HTTP API calls to the unified data collection service instead of direct SSH.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:9101/api")
API_KEY = os.getenv("API_KEY")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "120.0"))

# HTTP client setup
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
        await self.client.aclose()

# Global API client instance
_api_client: Optional[APIClient] = None

async def get_api_client() -> APIClient:
    """Get or create global API client"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client

logger = logging.getLogger(__name__)


# Note: SMART data parsing functions removed as they are now handled by the unified data collection service
# All SMART data collection, parsing, and caching is managed by the polling service and cached in the database


async def get_drive_health(
    device: str, drive: Optional[str] = None, timeout: int = 60
) -> Dict[str, Any]:
    """
    Get S.M.A.R.T. drive health information and disk status.

    This tool calls the unified data collection API to retrieve cached or fresh
    S.M.A.R.T. health data for storage drives, including temperature, error counts,
    and overall health status. Supports both specific drive queries and all drives.

    Args:
        device: Device hostname or IP address
        drive: Specific drive to check (e.g., '/dev/sda') or None for all
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing drive health information from unified data collection service

    Raises:
        Exception: If API call fails or device cannot be reached
    """
    logger.info(f"Getting drive health for device: {device}")

    try:
        api_client = await get_api_client()
        
        # Build API endpoint URL
        url = f"/devices/{device}/drives"
        params = {}
        if drive:
            params["drive"] = drive
        if timeout != 60:
            params["timeout"] = timeout
        
        # Make API call to get drive health data
        response = await api_client.client.get(url, params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully retrieved drive health data for {device}")
        return result

    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting drive health for {device}: {e}")
        raise Exception(f"Failed to get drive health data: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting drive health for {device}: {e}")
        raise Exception(f"Failed to get drive health data: {str(e)}") from e


async def get_system_logs(
    device: str,
    service: Optional[str] = None,
    since: Optional[str] = None,
    lines: int = 100,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Get system logs from journald or traditional syslog.

    This tool calls the unified data collection API to retrieve system logs
    using the polling service that handles journalctl and traditional log files.
    Supports filtering by service, time range, and line limits.

    Args:
        device: Device hostname or IP address
        service: Specific service to get logs for (e.g., 'docker', 'nginx')
        since: Get logs since timestamp/duration (e.g., '2h', '1d', '2023-01-01 10:00:00')
        lines: Number of log lines to retrieve (default: 100)
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing log data from unified data collection service

    Raises:
        Exception: If API call fails or device cannot be reached
    """
    logger.info(f"Getting system logs for device: {device}")

    try:
        api_client = await get_api_client()
        
        # Build API endpoint URL
        url = f"/devices/{device}/logs"
        params = {}
        if service:
            params["service"] = service
        if since:
            params["since"] = since
        if lines != 100:
            params["lines"] = lines
        if timeout != 60:
            params["timeout"] = timeout
        
        # Make API call to get system logs
        response = await api_client.client.get(url, params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully retrieved system logs for {device}")
        return result

    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting system logs for {device}: {e}")
        raise Exception(f"Failed to get system logs: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting system logs for {device}: {e}")
        raise Exception(f"Failed to get system logs: {str(e)}") from e


async def get_drive_stats(
    device: str, drive: Optional[str] = None, timeout: int = 60
) -> Dict[str, Any]:
    """
    Get drive usage statistics, I/O performance, and utilization metrics.

    This tool calls the unified data collection API to retrieve cached or fresh
    drive performance and usage data including I/O statistics, throughput,
    utilization percentages, queue depths, and filesystem usage.

    Args:
        device: Device hostname or IP address
        drive: Specific drive to check (e.g., 'sda') or None for all drives
        timeout: Command timeout in seconds (default: 60)

    Returns:
        Dict containing drive statistics from unified data collection service

    Raises:
        Exception: If API call fails or device cannot be reached
    """
    logger.info(f"Getting drive stats for device: {device}")

    try:
        api_client = await get_api_client()
        
        # Build API endpoint URL
        url = f"/devices/{device}/drives/stats"
        params = {}
        if drive:
            params["drive"] = drive
        if timeout != 60:
            params["timeout"] = timeout
        
        # Make API call to get drive stats
        response = await api_client.client.get(url, params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully retrieved drive stats for {device}")
        return result

    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting drive stats for {device}: {e}")
        raise Exception(f"Failed to get drive stats: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting drive stats for {device}: {e}")
        raise Exception(f"Failed to get drive stats: {str(e)}") from e


async def get_network_ports(device: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Get network port information and listening processes.

    This tool calls the unified data collection API to retrieve network port
    information using the polling service that handles 'ss -tulpn' command,
    showing listening ports and the processes using them.

    Args:
        device: Device hostname or IP address
        timeout: Command timeout in seconds (default: 30)

    Returns:
        Dict containing port information from unified data collection service

    Raises:
        Exception: If API call fails or device cannot be reached
    """
    logger.info(f"Getting network ports for device: {device}")

    try:
        api_client = await get_api_client()
        
        # Build API endpoint URL
        url = f"/devices/{device}/ports"
        params = {}
        if timeout != 30:
            params["timeout"] = timeout
        
        # Make API call to get network ports
        response = await api_client.client.get(url, params=params)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Successfully retrieved network ports for {device}")
        return result

    except httpx.HTTPError as e:
        logger.error(f"HTTP error getting network ports for {device}: {e}")
        raise Exception(f"Failed to get network ports: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting network ports for {device}: {e}")
        raise Exception(f"Failed to get network ports: {str(e)}") from e


# Tool registration metadata for MCP server
SYSTEM_MONITORING_TOOLS = {
    "get_drive_health": {
        "name": "get_drive_health",
        "description": "Get S.M.A.R.T. drive health information via unified data collection API",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "drive": {
                    "type": "string",
                    "description": "Specific drive to check (e.g., '/dev/sda') or omit for all drives",
                },
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
        "function": get_drive_health,
    },
    "get_system_logs": {
        "name": "get_system_logs",
        "description": "Get system logs via unified data collection API",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "service": {
                    "type": "string",
                    "description": "Specific service to get logs for (e.g., 'docker', 'nginx')",
                },
                "since": {
                    "type": "string",
                    "description": "Get logs since timestamp/duration (e.g., '2h', '1d', '2023-01-01 10:00:00')",
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of log lines to retrieve",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 10000,
                },
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
        "function": get_system_logs,
    },
    "get_drive_stats": {
        "name": "get_drive_stats",
        "description": "Get drive usage statistics and I/O performance via unified data collection API",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "drive": {
                    "type": "string",
                    "description": "Specific drive to check (e.g., 'sda') or omit for all drives",
                },
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
        "function": get_drive_stats,
    },
    "get_network_ports": {
        "name": "get_network_ports",
        "description": "Get network port information via unified data collection API",
        "parameters": {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device hostname or IP address"},
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 30,
                    "minimum": 5,
                    "maximum": 120,
                },
            },
            "required": ["device"],
        },
        "function": get_network_ports,
    },
}
