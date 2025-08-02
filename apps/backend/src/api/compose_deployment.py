"""
Docker Compose Deployment API Endpoints

REST API endpoints for modifying and deploying docker-compose files
to target infrastructure devices.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import PlainTextResponse

from apps.backend.src.api.common import get_current_user
from apps.backend.src.services.compose_deployment import ComposeDeploymentService
from apps.backend.src.schemas.compose_deployment import (
    ComposeModificationRequest,
    ComposeModificationResult,
    ComposeDeploymentRequest,
    ComposeDeploymentResult,
    PortScanRequest,
    PortScanResult,
    NetworkScanRequest,
    NetworkScanResult,
)
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    ValidationError,
    SSHConnectionError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/modify", response_model=ComposeModificationResult)
async def modify_compose_for_device(
    request: ComposeModificationRequest,
    current_user=Depends(get_current_user),
):
    """
    Modify docker-compose content for deployment on target device.
    
    This endpoint takes a docker-compose.yml file and modifies it according to
    the target device configuration including:
    - Updating volume paths to use device appdata directories
    - Assigning available ports to avoid conflicts
    - Configuring appropriate Docker networks
    - Generating SWAG reverse proxy configurations
    
    Args:
        request: Compose modification request with content and options
        
    Returns:
        ComposeModificationResult with modified compose and change details
    """
    try:
        service = ComposeDeploymentService()
        result = await service.modify_compose_for_device(request)
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to modify compose: {'; '.join(result.errors)}"
            )
            
        return result
        
    except DeviceNotFoundError as e:
        logger.error(f"Device not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error modifying compose: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/deploy", response_model=ComposeDeploymentResult)
async def deploy_compose_to_device(
    request: ComposeDeploymentRequest,
    current_user=Depends(get_current_user),
):
    """
    Deploy docker-compose content to target device.
    
    This endpoint deploys the provided docker-compose content to the target device:
    - Creates necessary directories
    - Backs up existing compose files
    - Writes the new compose file
    - Optionally pulls images and starts services
    - Reports deployment status and service health
    
    Args:
        request: Compose deployment request with content and deployment options
        
    Returns:
        ComposeDeploymentResult with deployment status and service information
    """
    try:
        service = ComposeDeploymentService()
        result = await service.deploy_compose_to_device(request)
        
        # Return result even if not fully successful, but include warnings in response
        return result
        
    except SSHConnectionError as e:
        logger.error(f"SSH connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to device: {str(e)}")
    except Exception as e:
        logger.error(f"Error deploying compose: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/modify-and-deploy", response_model=dict)
async def modify_and_deploy_compose(
    compose_content: str = Body(..., description="Docker compose YAML content"),
    target_device: str = Body(..., description="Target device hostname"),
    service_name: Optional[str] = Body(None, description="Specific service to modify"),
    update_appdata_paths: bool = Body(True, description="Update volume paths"),
    auto_assign_ports: bool = Body(True, description="Auto-assign available ports"),
    generate_proxy_configs: bool = Body(True, description="Generate SWAG proxy configs"),
    start_services: bool = Body(True, description="Start services after deployment"),
    pull_images: bool = Body(True, description="Pull latest images"),
    custom_appdata_path: Optional[str] = Body(None, description="Custom appdata path"),
    deployment_path: Optional[str] = Body(None, description="Custom deployment path"),
    current_user=Depends(get_current_user),
):
    """
    Modify and deploy docker-compose in a single operation.
    
    This is a convenience endpoint that combines modification and deployment
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
        
    Returns:
        Combined result with both modification and deployment details
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
        )
        
        modify_result = await service.modify_compose_for_device(modify_request)
        
        if not modify_result.success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to modify compose: {'; '.join(modify_result.errors)}"
            )
        
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
            "modification": modify_result,
            "deployment": deploy_result,
            "overall_success": modify_result.success and deploy_result.success,
            "proxy_configs_generated": len(modify_result.proxy_configs),
            "services_started": len(deploy_result.containers_started),
            "total_execution_time_ms": modify_result.execution_time_ms + deploy_result.execution_time_ms,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in modify-and-deploy operation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/download-modified/{device}", response_class=PlainTextResponse)
async def download_modified_compose(
    device: str,
    compose_content: str = Body(..., description="Original docker-compose YAML content"),
    service_name: Optional[str] = None,
    update_appdata_paths: bool = True,
    auto_assign_ports: bool = True,
    generate_proxy_configs: bool = False,  # Don't generate proxy configs for download
    custom_appdata_path: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """
    Download modified docker-compose content without deploying.
    
    This endpoint returns the modified docker-compose.yml content as plain text
    for review or manual deployment.
    
    Args:
        device: Target device hostname
        compose_content: Original compose content
        service_name: Optional specific service to modify
        update_appdata_paths: Whether to update volume paths
        auto_assign_ports: Whether to auto-assign ports
        generate_proxy_configs: Whether to generate proxy configs
        custom_appdata_path: Custom appdata path override
        
    Returns:
        Modified docker-compose.yml content as plain text
    """
    try:
        service = ComposeDeploymentService()
        
        modify_request = ComposeModificationRequest(
            compose_content=compose_content,
            target_device=device,
            service_name=service_name,
            update_appdata_paths=update_appdata_paths,
            auto_assign_ports=auto_assign_ports,
            generate_proxy_configs=generate_proxy_configs,
            custom_appdata_path=custom_appdata_path,
        )
        
        result = await service.modify_compose_for_device(modify_request)
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to modify compose: {'; '.join(result.errors)}"
            )
        
        return result.modified_compose
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating modified compose: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/scan-ports", response_model=PortScanResult)
async def scan_device_ports(
    request: PortScanRequest,
    current_user=Depends(get_current_user),
):
    """
    Scan for available ports on target device.
    
    This endpoint scans the specified port range on the target device to identify
    which ports are available for use in docker-compose port mappings.
    
    Args:
        request: Port scan request with device and port range
        
    Returns:
        PortScanResult with available and used ports information
    """
    try:
        service = ComposeDeploymentService()
        result = await service.scan_available_ports(request)
        return result
        
    except SSHConnectionError as e:
        logger.error(f"SSH connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to device: {str(e)}")
    except Exception as e:
        logger.error(f"Error scanning ports: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/scan-networks", response_model=NetworkScanResult)
async def scan_docker_networks(
    request: NetworkScanRequest,
    current_user=Depends(get_current_user),
):
    """
    Scan Docker networks on target device.
    
    This endpoint scans the target device for existing Docker networks and provides
    recommendations for network configuration in docker-compose deployments.
    
    Args:
        request: Network scan request with device and options
        
    Returns:
        NetworkScanResult with network information and recommendations
    """
    try:
        service = ComposeDeploymentService()
        result = await service.scan_docker_networks(request)
        return result
        
    except SSHConnectionError as e:
        logger.error(f"SSH connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to device: {str(e)}")
    except Exception as e:
        logger.error(f"Error scanning networks: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/proxy-configs/{device}/{service_name}")
async def get_generated_proxy_config(
    device: str,
    service_name: str,
    upstream_port: int,
    domain: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """
    Generate SWAG proxy configuration for a specific service.
    
    This endpoint generates a SWAG reverse proxy configuration for a single service
    without requiring a full docker-compose modification.
    
    Args:
        device: Target device hostname
        service_name: Service name for the proxy configuration
        upstream_port: Port where the service is running
        domain: Domain name for the service (optional)
        
    Returns:
        Generated SWAG proxy configuration content
    """
    try:
        service = ComposeDeploymentService()
        
        # Use the service's private method to generate proxy config
        base_domain = domain or f"{service_name}.example.com"
        proxy_config = service._generate_swag_config(
            service_name=service_name,
            upstream_port=upstream_port,
            domain=base_domain,
            device_hostname=device
        )
        
        return {
            "service_name": service_name,
            "device": device,
            "upstream_port": upstream_port,
            "domain": base_domain,
            "config_content": proxy_config,
            "filename": f"{service_name}.subdomain.conf"
        }
        
    except Exception as e:
        logger.error(f"Error generating proxy config: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")