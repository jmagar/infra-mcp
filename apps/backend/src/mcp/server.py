"""
Infrastructure Management MCP Server

This module sets up the FastMCP server for infrastructure monitoring and management.
It registers all MCP tools and provides the server interface for LLM integration.
"""

import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastmcp import FastMCP, Context

# Import tool modules
from apps.backend.src.mcp.tools.container_management import CONTAINER_TOOLS
from apps.backend.src.mcp.tools.device_management import DEVICE_TOOLS
from apps.backend.src.mcp.tools.system_monitoring import SYSTEM_MONITORING_TOOLS

# Import database initialization
from apps.backend.src.core.database import init_database, close_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def mcp_lifespan(app):
    """MCP server lifespan manager for startup and shutdown tasks"""
    logger.info("Starting Infrastructure Management MCP Server")
    
    try:
        # Initialize database connection
        await init_database()
        logger.info("Database initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Infrastructure Management MCP Server")
        try:
            await close_database()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error during MCP server shutdown: {e}")


# Create FastMCP server instance
# For development, we'll disable authentication completely
mcp_server = FastMCP(
    name="Infrastructure Management MCP Server",
    version="1.0.0",
    instructions="Comprehensive infrastructure monitoring and management tools for heterogeneous Linux environments",
    lifespan=mcp_lifespan,
    # No authentication for development
)


def register_container_tools():
    """Register container management tools"""
    logger.info("Registering container management tools")
    
    for tool_name, tool_config in CONTAINER_TOOLS.items():
        try:
            # Register the function directly with FastMCP
            mcp_server.tool(
                name=tool_config["name"],
                description=tool_config["description"]
            )(tool_config["function"])
            
            logger.debug(f"Registered container tool: {tool_name}")
            
        except Exception as e:
            logger.error(f"Failed to register container tool {tool_name}: {e}")


def register_device_tools():
    """Register device management tools"""
    logger.info("Registering device management tools")
    
    for tool_name, tool_config in DEVICE_TOOLS.items():
        try:
            # Register the function directly with FastMCP
            mcp_server.tool(
                name=tool_config["name"],
                description=tool_config["description"]
            )(tool_config["function"])
            
            logger.debug(f"Registered device tool: {tool_name}")
            
        except Exception as e:
            logger.error(f"Failed to register device tool {tool_name}: {e}")


def register_system_monitoring_tools():
    """Register system monitoring tools"""
    logger.info("Registering system monitoring tools")
    
    for tool_name, tool_config in SYSTEM_MONITORING_TOOLS.items():
        try:
            # Register the function directly with FastMCP
            mcp_server.tool(
                name=tool_config["name"],
                description=tool_config["description"]
            )(tool_config["function"])
            
            logger.debug(f"Registered system monitoring tool: {tool_name}")
            
        except Exception as e:
            logger.error(f"Failed to register system monitoring tool {tool_name}: {e}")


# Additional utility tools for infrastructure management
@mcp_server.tool(
    name="get_infrastructure_health",
    description="Get overall infrastructure health summary across all monitored devices"
)
async def get_infrastructure_health(
    include_details: bool = False,
    timeout: int = 30,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Get comprehensive infrastructure health overview.
    
    This tool provides a high-level summary of infrastructure health
    across all registered devices, including connectivity status,
    resource utilization, and potential issues.
    """
    from apps.backend.src.mcp.tools.device_management import list_devices, get_device_summary
    
    if ctx:
        await ctx.info("Starting infrastructure health assessment")
    
    try:
        # Get all devices
        devices_response = await list_devices()
        all_devices = devices_response.get("devices", [])
        
        if not all_devices:
            return {
                "overall_status": "no_devices",
                "message": "No devices registered in the infrastructure",
                "summary": {
                    "total_devices": 0,
                    "online_devices": 0,
                    "offline_devices": 0,
                    "unknown_devices": 0
                },
                "timestamp": devices_response.get("query_info", {}).get("timestamp")
            }
        
        if ctx:
            await ctx.report_progress(progress=10, total=100)
            await ctx.info(f"Found {len(all_devices)} registered devices")
        
        # Analyze each device if details requested
        device_health_data = []
        healthy_count = 0
        unhealthy_count = 0
        offline_count = 0
        
        if include_details:
            for i, device in enumerate(all_devices):
                if ctx:
                    progress = 10 + (i / len(all_devices)) * 80
                    await ctx.report_progress(progress=int(progress), total=100)
                    await ctx.debug(f"Checking health for device: {device['hostname']}")
                
                try:
                    # Get detailed device summary
                    device_summary = await get_device_summary(
                        device=device["hostname"], 
                        timeout=timeout
                    )
                    
                    health_status = device_summary.get("health_status", {})
                    overall_health = health_status.get("overall_health", "unknown")
                    
                    device_health = {
                        "hostname": device["hostname"],
                        "status": device["status"],
                        "health": overall_health,
                        "health_score": health_status.get("health_score", 0),
                        "issues": health_status.get("issues", []),
                        "warnings": health_status.get("warnings", [])
                    }
                    
                    if overall_health in ["excellent", "good"]:
                        healthy_count += 1
                    elif overall_health == "offline":
                        offline_count += 1
                    else:
                        unhealthy_count += 1
                    
                    device_health_data.append(device_health)
                    
                except Exception as e:
                    logger.warning(f"Failed to get health data for {device['hostname']}: {e}")
                    device_health_data.append({
                        "hostname": device["hostname"],
                        "status": "error",
                        "health": "error",
                        "health_score": 0,
                        "issues": [f"Health check failed: {str(e)}"],
                        "warnings": []
                    })
                    unhealthy_count += 1
        else:
            # Just count based on device status
            status_summary = devices_response.get("summary", {})
            healthy_count = status_summary.get("online", 0)
            offline_count = status_summary.get("offline", 0)
            unhealthy_count = status_summary.get("unknown", 0)
        
        # Determine overall infrastructure health
        total_devices = len(all_devices)
        
        if total_devices == 0:
            overall_status = "no_devices"
        elif offline_count == total_devices:
            overall_status = "critical"
        elif unhealthy_count >= total_devices * 0.5:
            overall_status = "degraded"
        elif offline_count > 0 or unhealthy_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        if ctx:
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"Infrastructure health assessment completed: {overall_status}")
        
        # Prepare response
        response = {
            "overall_status": overall_status,
            "summary": {
                "total_devices": total_devices,
                "healthy_devices": healthy_count,
                "unhealthy_devices": unhealthy_count,
                "offline_devices": offline_count,
                "health_percentage": round((healthy_count / total_devices) * 100, 1) if total_devices > 0 else 0
            },
            "devices": device_health_data if include_details else None,
            "recommendations": [],
            "query_info": {
                "include_details": include_details,
                "timeout_used": timeout,
                "timestamp": devices_response.get("query_info", {}).get("timestamp")
            }
        }
        
        # Add recommendations based on status
        if offline_count > 0:
            response["recommendations"].append(f"Check connectivity for {offline_count} offline device(s)")
        if unhealthy_count > 0:
            response["recommendations"].append(f"Investigate health issues on {unhealthy_count} device(s)")
        if overall_status == "healthy" and total_devices > 0:
            response["recommendations"].append("Infrastructure is healthy - maintain current monitoring")
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get infrastructure health: {e}")
        if ctx:
            await ctx.error(f"Infrastructure health check failed: {str(e)}")
        
        return {
            "overall_status": "error",
            "message": f"Failed to assess infrastructure health: {str(e)}",
            "summary": {
                "total_devices": 0,
                "healthy_devices": 0,
                "unhealthy_devices": 0,
                "offline_devices": 0,
                "health_percentage": 0
            },
            "error": str(e)
        }


@mcp_server.tool(
    name="troubleshoot_device",
    description="Run automated troubleshooting checks on a specific device"
)
async def troubleshoot_device(
    device: str,
    check_type: str = "all",
    timeout: int = 60,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Run comprehensive troubleshooting checks on a device.
    
    This tool performs automated diagnostic checks to identify
    common infrastructure issues and provide remediation suggestions.
    """
    from apps.backend.src.mcp.tools.device_management import get_device_info
    from apps.backend.src.mcp.tools.system_monitoring import get_system_info
    from apps.backend.src.mcp.tools.container_management import list_containers
    
    if ctx:
        await ctx.info(f"Starting troubleshooting for device: {device}")
    
    troubleshooting_results = {
        "device": device,
        "check_type": check_type,
        "overall_status": "unknown",
        "checks_performed": [],
        "issues_found": [],
        "recommendations": [],
        "detailed_results": {}
    }
    
    try:
        # Connectivity check
        if check_type in ["connectivity", "all"]:
            if ctx:
                await ctx.debug("Performing connectivity check")
                await ctx.report_progress(progress=10, total=100)
            
            try:
                device_info = await get_device_info(
                    device=device,
                    test_connectivity=True,
                    timeout=min(timeout, 30)
                )
                
                connectivity = device_info.get("connectivity", {})
                troubleshooting_results["checks_performed"].append("connectivity")
                troubleshooting_results["detailed_results"]["connectivity"] = connectivity
                
                if not connectivity.get("ssh_accessible", False):
                    troubleshooting_results["issues_found"].append("SSH connectivity failed")
                    troubleshooting_results["recommendations"].append("Check SSH service and network connectivity")
                    
            except Exception as e:
                troubleshooting_results["issues_found"].append(f"Connectivity check failed: {str(e)}")
        
        # Performance check
        if check_type in ["performance", "all"]:
            if ctx:
                await ctx.debug("Performing performance check")
                await ctx.report_progress(progress=40, total=100)
            
            try:
                system_metrics = await get_system_info(
                    device=device,
                    include_processes=True,
                    timeout=timeout
                )
                
                cpu_metrics = system_metrics.get("cpu_metrics", {})
                memory_metrics = system_metrics.get("memory_metrics", {})
                disk_metrics = system_metrics.get("disk_metrics", {})
                
                troubleshooting_results["checks_performed"].append("performance")
                troubleshooting_results["detailed_results"]["performance"] = {
                    "cpu_usage": cpu_metrics.get("usage_percent"),
                    "memory_usage": memory_metrics.get("usage_percent"),
                    "load_average": cpu_metrics.get("load_1min")
                }
                
                # Check for performance issues
                if cpu_metrics.get("usage_percent", 0) > 90:
                    troubleshooting_results["issues_found"].append("High CPU usage detected")
                    troubleshooting_results["recommendations"].append("Investigate high CPU usage processes")
                
                if memory_metrics.get("usage_percent", 0) > 90:
                    troubleshooting_results["issues_found"].append("High memory usage detected")
                    troubleshooting_results["recommendations"].append("Check for memory leaks or resize memory")
                
                # Check disk usage
                filesystems = disk_metrics.get("filesystems", [])
                for fs in filesystems:
                    if fs.get("usage_percent", 0) > 90:
                        troubleshooting_results["issues_found"].append(f"High disk usage on {fs.get('mount_point', 'unknown')}")
                        troubleshooting_results["recommendations"].append(f"Clean up disk space on {fs.get('mount_point', 'unknown')}")
                        
            except Exception as e:
                troubleshooting_results["issues_found"].append(f"Performance check failed: {str(e)}")
        
        # Services check (Docker containers)
        if check_type in ["services", "all"]:
            if ctx:
                await ctx.debug("Performing services check")
                await ctx.report_progress(progress=70, total=100)
            
            try:
                containers_result = await list_containers(
                    device=device,
                    timeout=timeout
                )
                
                containers = containers_result.get("containers", [])
                troubleshooting_results["checks_performed"].append("services")
                
                stopped_containers = [c for c in containers if not c.get("running", False)]
                if stopped_containers:
                    troubleshooting_results["detailed_results"]["services"] = {
                        "total_containers": len(containers),
                        "stopped_containers": len(stopped_containers),
                        "stopped_container_names": [c.get("container_name") for c in stopped_containers]
                    }
                    
                    if len(stopped_containers) > 0:
                        troubleshooting_results["issues_found"].append(f"{len(stopped_containers)} containers are not running")
                        troubleshooting_results["recommendations"].append("Check container logs and restart failed services")
                        
            except Exception as e:
                troubleshooting_results["issues_found"].append(f"Services check failed: {str(e)}")
        
        # Determine overall status
        if not troubleshooting_results["issues_found"]:
            troubleshooting_results["overall_status"] = "healthy"
            troubleshooting_results["recommendations"].append("No issues detected - system appears healthy")
        elif len(troubleshooting_results["issues_found"]) <= 2:
            troubleshooting_results["overall_status"] = "warning"
        else:
            troubleshooting_results["overall_status"] = "critical"
        
        if ctx:
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"Troubleshooting completed: {troubleshooting_results['overall_status']}")
        
        return troubleshooting_results
        
    except Exception as e:
        logger.error(f"Troubleshooting failed for {device}: {e}")
        if ctx:
            await ctx.error(f"Troubleshooting failed: {str(e)}")
        
        troubleshooting_results["overall_status"] = "error"
        troubleshooting_results["issues_found"].append(f"Troubleshooting process failed: {str(e)}")
        return troubleshooting_results


def initialize_mcp_server():
    """Initialize and configure the MCP server with all tools"""
    logger.info("Initializing Infrastructure Management MCP Server")
    
    try:
        # Register all tool categories
        register_container_tools()
        register_device_tools()
        register_system_monitoring_tools()
        
        logger.info("MCP Server initialized successfully with all tools registered")
        
        # Log registered tools summary
        logger.info(f"Registered {len(CONTAINER_TOOLS)} container management tools")
        logger.info(f"Registered {len(DEVICE_TOOLS)} device management tools")
        logger.info(f"Registered {len(SYSTEM_MONITORING_TOOLS)} system monitoring tools")
        logger.info("Registered 2 additional utility tools")
        
        return mcp_server
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        raise


# Initialize the server
def get_mcp_server() -> FastMCP:
    """Get the configured MCP server instance"""
    return initialize_mcp_server()


# Export the server instance
__all__ = ["get_mcp_server", "mcp_server"]