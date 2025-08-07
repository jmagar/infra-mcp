"""
Docker Compose Deployment MCP Tools

MCP tools for modifying and deploying docker-compose files to target devices,
including path updates, port management, network configuration, and SWAG proxy setup.
"""

import logging
from typing import Dict, List, Optional, Any
import json

from apps.backend.src.services.compose_deployment import ComposeDeploymentService
from apps.backend.src.schemas.compose_deployment import (
    ComposeModificationRequest,
    ComposeDeploymentRequest,
    PortScanRequest,
    NetworkScanRequest,
)
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    ValidationError,
    SSHConnectionError,
)

logger = logging.getLogger(__name__)


async def modify_compose_for_device(
    compose_content: str,
    target_device: str,
    service_name: Optional[str] = None,
    update_appdata_paths: bool = True,
    auto_assign_ports: bool = True,
    port_range_start: int = 8000,
    port_range_end: int = 9000,
    custom_port_mappings: Optional[Dict[str, int]] = None,
    update_networks: bool = True,
    default_network: Optional[str] = None,
    generate_proxy_configs: bool = True,
    base_domain: Optional[str] = None,
    custom_appdata_path: Optional[str] = None,
    deployment_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Modify docker-compose content for deployment on target device.
    
    This tool takes a docker-compose.yml file and modifies it according to
    the target device configuration including:
    - Updating volume paths to use device appdata directories
    - Assigning available ports to avoid conflicts
    - Configuring appropriate Docker networks
    - Generating SWAG reverse proxy configurations
    
    Args:
        compose_content: Original docker-compose.yml content
        target_device: Target device hostname
        service_name: Specific service to modify (all services if None)
        update_appdata_paths: Update volume paths to device appdata path
        auto_assign_ports: Automatically assign available ports
        port_range_start: Start of port range for auto-assignment
        port_range_end: End of port range for auto-assignment
        custom_port_mappings: Custom port mappings by service name
        update_networks: Configure Docker networks for device
        default_network: Default network to use
        generate_proxy_configs: Generate SWAG proxy configurations
        base_domain: Base domain for proxy configurations
        custom_appdata_path: Override device default appdata path
        deployment_path: Where to store the compose file on device
        
    Returns:
        Dict containing modified compose and change details
    """
    try:
        service = ComposeDeploymentService()
        
        request = ComposeModificationRequest(
            compose_content=compose_content,
            target_device=target_device,
            service_name=service_name,
            update_appdata_paths=update_appdata_paths,
            custom_appdata_path=custom_appdata_path,
            auto_assign_ports=auto_assign_ports,
            port_range_start=port_range_start,
            port_range_end=port_range_end,
            custom_port_mappings=custom_port_mappings or {},
            update_networks=update_networks,
            default_network=default_network,
            generate_proxy_configs=generate_proxy_configs,
            base_domain=base_domain,
            deployment_path=deployment_path,
        )
        
        result = await service.modify_compose_for_device(request)
        
        return {
            "success": result.success,
            "device": result.device,
            "service_name": result.service_name,
            "modified_compose": result.modified_compose,
            "original_hash": result.original_compose_hash,
            "modified_hash": result.modified_compose_hash,
            "changes_applied": result.changes_applied,
            "port_assignments": {
                service: [
                    {
                        "host_port": port.host_port,
                        "container_port": port.container_port,
                        "protocol": port.protocol,
                    }
                    for port in ports
                ]
                for service, ports in result.port_assignments.items()
            },
            "volume_updates": {
                service: [
                    {
                        "host_path": vol.host_path,
                        "container_path": vol.container_path,
                        "mode": vol.mode,
                    }
                    for vol in volumes
                ]
                for service, volumes in result.volume_updates.items()
            },
            "network_configs": {
                service: {"name": net.name, "aliases": net.aliases}
                for service, net in result.network_configs.items()
            },
            "proxy_configs": result.proxy_configs,
            "deployment_path": result.deployment_path,
            "warnings": result.warnings,
            "errors": result.errors,
            "execution_time_ms": result.execution_time_ms,
            "device_info": result.device_info,
        }
        
    except DeviceNotFoundError as e:
        logger.error(f"Device not found: {e}")
        return {"success": False, "error": f"Device not found: {str(e)}"}
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return {"success": False, "error": f"Validation error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error modifying compose: {e}")
        return {"success": False, "error": f"Failed to modify compose: {str(e)}"}


async def deploy_compose_to_device(
    device: str,
    compose_content: str,
    deployment_path: str,
    start_services: bool = True,
    pull_images: bool = True,
    recreate_containers: bool = False,
    create_directories: bool = True,
    backup_existing: bool = True,
    services_to_start: Optional[List[str]] = None,
    services_to_stop: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Deploy docker-compose content to target device.
    
    This tool deploys the provided docker-compose content to the target device:
    - Creates necessary directories
    - Backs up existing compose files
    - Writes the new compose file
    - Optionally pulls images and starts services
    - Reports deployment status and service health
    
    Args:
        device: Target device hostname
        compose_content: Docker compose content to deploy
        deployment_path: Path where to store compose file on device
        start_services: Start services after deployment
        pull_images: Pull latest images before starting
        recreate_containers: Recreate containers even if config unchanged
        create_directories: Create necessary directories
        backup_existing: Backup existing compose file
        services_to_start: Specific services to start
        services_to_stop: Services to stop before deployment
        
    Returns:
        Dict containing deployment status and service information
    """
    try:
        service = ComposeDeploymentService()
        
        request = ComposeDeploymentRequest(
            device=device,
            compose_content=compose_content,
            deployment_path=deployment_path,
            start_services=start_services,
            pull_images=pull_images,
            recreate_containers=recreate_containers,
            create_directories=create_directories,
            backup_existing=backup_existing,
            services_to_start=services_to_start,
            services_to_stop=services_to_stop,
        )
        
        result = await service.deploy_compose_to_device(request)
        
        return {
            "success": result.success,
            "device": result.device,
            "deployment_path": result.deployment_path,
            "compose_file_created": result.compose_file_created,
            "backup_file_path": result.backup_file_path,
            "directories_created": result.directories_created,
            "images_pulled": result.images_pulled,
            "containers_created": result.containers_created,
            "containers_started": result.containers_started,
            "containers_stopped": result.containers_stopped,
            "service_status": result.service_status,
            "docker_compose_output": result.docker_compose_output,
            "warnings": result.warnings,
            "errors": result.errors,
            "execution_time_ms": result.execution_time_ms,
        }
        
    except SSHConnectionError as e:
        logger.error(f"SSH connection error: {e}")
        return {"success": False, "error": f"Cannot connect to device: {str(e)}"}
    except Exception as e:
        logger.error(f"Error deploying compose: {e}")
        return {"success": False, "error": f"Failed to deploy compose: {str(e)}"}


async def modify_and_deploy_compose(
    compose_content: str,
    target_device: str,
    service_name: Optional[str] = None,
    update_appdata_paths: bool = True,
    auto_assign_ports: bool = True,
    generate_proxy_configs: bool = True,
    start_services: bool = True,
    pull_images: bool = True,
    custom_appdata_path: Optional[str] = None,
    deployment_path: Optional[str] = None,
    port_range_start: int = 8000,
    port_range_end: int = 9000,
    base_domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Modify and deploy docker-compose in a single operation.
    
    This is a convenience tool that combines modification and deployment
    into a single atomic operation with sensible defaults.
    
    Args:
        compose_content: Docker compose YAML content
        target_device: Target device hostname
        service_name: Optional specific service to modify
        update_appdata_paths: Whether to update volume paths
        auto_assign_ports: Whether to auto-assign ports
        generate_proxy_configs: Whether to generate proxy configs
        start_services: Whether to start services after deployment
        pull_images: Whether to pull latest images
        custom_appdata_path: Custom appdata path override
        deployment_path: Custom deployment path
        port_range_start: Start of port range for auto-assignment  
        port_range_end: End of port range for auto-assignment
        base_domain: Base domain for proxy configurations
        
    Returns:
        Dict containing combined modification and deployment results
    """
    try:
        service = ComposeDeploymentService()
        
        # Step 1: Modify compose for target device
        modify_request = ComposeModificationRequest(
            compose_content=compose_content,
            target_device=target_device,
            service_name=service_name,
            update_appdata_paths=update_appdata_paths,
            auto_assign_ports=auto_assign_ports,
            generate_proxy_configs=generate_proxy_configs,
            custom_appdata_path=custom_appdata_path,
            deployment_path=deployment_path,
            port_range_start=port_range_start,
            port_range_end=port_range_end,
            base_domain=base_domain,
        )
        
        modify_result = await service.modify_compose_for_device(modify_request)
        
        if not modify_result.success:
            return {
                "success": False,
                "error": f"Failed to modify compose: {'; '.join(modify_result.errors)}",
                "modification_result": {
                    "success": modify_result.success,
                    "errors": modify_result.errors,
                    "warnings": modify_result.warnings,
                }
            }
        
        # Step 2: Deploy modified compose
        deploy_request = ComposeDeploymentRequest(
            device=target_device,
            compose_content=modify_result.modified_compose,
            deployment_path=modify_result.deployment_path or "/opt/docker-compose/docker-compose.yml",
            start_services=start_services,
            pull_images=pull_images,
        )
        
        deploy_result = await service.deploy_compose_to_device(deploy_request)
        
        # Combine results
        return {
            "success": modify_result.success and deploy_result.success,
            "modification": {
                "success": modify_result.success,
                "changes_applied": modify_result.changes_applied,
                "port_assignments": modify_result.port_assignments,
                "volume_updates": modify_result.volume_updates,
                "proxy_configs": modify_result.proxy_configs,
                "warnings": modify_result.warnings,
                "errors": modify_result.errors,
            },
            "deployment": {
                "success": deploy_result.success,
                "compose_file_created": deploy_result.compose_file_created,
                "backup_file_path": deploy_result.backup_file_path,
                "containers_started": deploy_result.containers_started,
                "service_status": deploy_result.service_status,
                "warnings": deploy_result.warnings,
                "errors": deploy_result.errors,
            },
            "overall_success": modify_result.success and deploy_result.success,
            "proxy_configs_generated": len(modify_result.proxy_configs),
            "services_started": len(deploy_result.containers_started),
            "total_execution_time_ms": modify_result.execution_time_ms + deploy_result.execution_time_ms,
        }
        
    except Exception as e:
        logger.error(f"Error in modify-and-deploy operation: {e}")
        return {"success": False, "error": f"Failed to modify and deploy: {str(e)}"}


async def scan_device_ports(
    device: str,
    port_range_start: int = 8000,
    port_range_end: int = 9000,
    protocol: str = "tcp",
    timeout: int = 5,
) -> Dict[str, Any]:
    """
    Scan for available ports on target device.
    
    This tool scans the specified port range on the target device to identify
    which ports are available for use in docker-compose port mappings.
    
    Args:
        device: Device hostname to scan
        port_range_start: Start of port range to scan
        port_range_end: End of port range to scan
        protocol: Protocol to scan (tcp/udp)
        timeout: Timeout for port checks in seconds
        
    Returns:
        Dict containing port availability information
    """
    try:
        service = ComposeDeploymentService()
        
        request = PortScanRequest(
            device=device,
            port_range_start=port_range_start,
            port_range_end=port_range_end,
            protocol=protocol,
            timeout=timeout,
        )
        
        result = await service.scan_available_ports(request)
        
        return {
            "device": result.device,
            "used_ports": result.used_ports,
            "docker_port_usage": result.docker_port_usage,
            "system_port_usage": result.system_port_usage,
            "total_ports_in_use": len(result.used_ports),
            "docker_containers": len(result.docker_port_usage),
            "system_services": len(result.system_port_usage),
            "execution_time_ms": result.execution_time_ms,
        }
        
    except SSHConnectionError as e:
        logger.error(f"SSH connection error: {e}")
        return {"success": False, "error": f"Cannot connect to device: {str(e)}"}
    except Exception as e:
        logger.error(f"Error scanning ports: {e}")
        return {"success": False, "error": f"Failed to scan ports: {str(e)}"}


async def scan_docker_networks(
    device: str,
    include_system_networks: bool = False,
) -> Dict[str, Any]:
    """
    Scan Docker networks on target device.
    
    This tool scans the target device for existing Docker networks and provides
    recommendations for network configuration in docker-compose deployments.
    
    Args:
        device: Device hostname to scan
        include_system_networks: Include Docker system networks
        
    Returns:
        Dict containing network information and recommendations
    """
    try:
        service = ComposeDeploymentService()
        
        request = NetworkScanRequest(
            device=device,
            include_system_networks=include_system_networks,
        )
        
        result = await service.scan_docker_networks(request)
        
        return {
            "device": result.device,
            "networks": result.networks,
            "available_subnets": result.available_subnets,
            "recommended_network": result.recommended_network,
            "containers_by_network": result.containers_by_network,
            "execution_time_ms": result.execution_time_ms,
        }
        
    except SSHConnectionError as e:
        logger.error(f"SSH connection error: {e}")
        return {"success": False, "error": f"Cannot connect to device: {str(e)}"}
    except Exception as e:
        logger.error(f"Error scanning networks: {e}")
        return {"success": False, "error": f"Failed to scan networks: {str(e)}"}


async def generate_proxy_config(
    service_name: str,
    upstream_port: int,
    device_hostname: str,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate SWAG proxy configuration for a specific service.
    
    This tool generates a SWAG reverse proxy configuration for a single service
    without requiring a full docker-compose modification.
    
    Args:
        service_name: Service name for the proxy configuration
        upstream_port: Port where the service is running
        device_hostname: Target device hostname
        domain: Domain name for the service (optional)
        
    Returns:
        Dict containing generated SWAG proxy configuration
    """
    try:
        service = ComposeDeploymentService()
        
        # Use the service's private method to generate proxy config
        base_domain = domain or f"{service_name}.example.com"
        proxy_config = service._generate_swag_config(
            service_name=service_name,
            upstream_port=upstream_port,
            domain=base_domain,
            device_hostname=device_hostname
        )
        
        return {
            "success": True,
            "service_name": service_name,
            "device": device_hostname,
            "upstream_port": upstream_port,
            "domain": base_domain,
            "config_content": proxy_config,
            "filename": f"{service_name}.subdomain.conf"
        }
        
    except Exception as e:
        logger.error(f"Error generating proxy config: {e}")
        return {"success": False, "error": f"Failed to generate proxy config: {str(e)}"}