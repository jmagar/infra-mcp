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
from typing import Dict, List, Optional, Any
from fastmcp import FastMCP

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    status: Optional[str] = None,
    all_containers: bool = True,
    timeout: int = 60,
    limit: Optional[int] = None,
    offset: int = 0
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
    since: Optional[str] = None,
    tail: Optional[int] = None,
    timeout: int = 60
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
    drive: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
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


async def get_system_logs(
    device: str,
    service: Optional[str] = None,
    since: Optional[str] = None,
    lines: int = 100,
    timeout: int = 60
) -> Dict[str, Any]:
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
async def list_devices() -> Dict[str, Any]:
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
        name="get_system_logs",
        description="Get system logs from journald or traditional syslog"
    )(get_system_logs)
    
    # Register device management tools
    server.tool(
        name="list_devices",
        description="List all registered infrastructure devices with optional filtering"
    )(list_devices)
    
    logger.info(f"MCP server created with 7 HTTP client tools")
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