"""
Pydantic schemas for Docker Compose deployment operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ComposeServicePort(BaseModel):
    """Docker Compose service port mapping."""
    host_port: int
    container_port: int
    protocol: str = "tcp"
    host_ip: str = "0.0.0.0"


class ComposeServiceVolume(BaseModel):
    """Docker Compose service volume mapping."""
    host_path: str
    container_path: str
    mode: str = "rw"
    type: str = "bind"


class ComposeServiceNetwork(BaseModel):
    """Docker Compose service network configuration."""
    name: str
    aliases: Optional[List[str]] = None
    ipv4_address: Optional[str] = None


class ComposeModificationRequest(BaseModel):
    """Request for modifying a docker-compose file for target device deployment."""
    
    # Source and target information
    compose_content: str = Field(..., description="Original docker-compose.yml content")
    target_device: str = Field(..., description="Target device hostname")
    
    # Service configuration
    service_name: Optional[str] = Field(None, description="Specific service to modify (all if None)")
    
    # Path modifications
    update_appdata_paths: bool = Field(True, description="Update volume paths to device appdata path")
    custom_appdata_path: Optional[str] = Field(None, description="Override device default appdata path")
    
    # Port management
    auto_assign_ports: bool = Field(True, description="Automatically assign available ports")
    port_range_start: int = Field(8000, description="Start of port range for auto-assignment")
    port_range_end: int = Field(9000, description="End of port range for auto-assignment")
    custom_port_mappings: Optional[Dict[str, int]] = Field(None, description="Custom port mappings by service")
    
    # Network configuration
    update_networks: bool = Field(True, description="Configure Docker networks for device")
    default_network: Optional[str] = Field(None, description="Default network to use")
    
    # Proxy configuration
    generate_proxy_configs: bool = Field(True, description="Generate SWAG proxy configurations")
    base_domain: Optional[str] = Field(None, description="Base domain for proxy configurations")
    
    # Deployment settings
    deployment_path: Optional[str] = Field(None, description="Where to store the compose file on device")
    create_directories: bool = Field(True, description="Create necessary directories on device")


class ComposeModificationResult(BaseModel):
    """Result of docker-compose modification operation."""
    
    # Operation metadata
    device: str
    service_name: Optional[str]
    timestamp: datetime
    success: bool
    execution_time_ms: int
    
    # Modified compose content
    modified_compose: str
    original_compose_hash: str
    modified_compose_hash: str
    
    # Changes applied
    changes_applied: List[str] = []
    
    # Port assignments
    port_assignments: Dict[str, List[ComposeServicePort]] = {}
    
    # Volume path updates
    volume_updates: Dict[str, List[ComposeServiceVolume]] = {}
    
    # Network configurations
    network_configs: Dict[str, ComposeServiceNetwork] = {}
    
    # Proxy configurations generated
    proxy_configs: List[Dict[str, Any]] = []
    
    # Deployment information
    deployment_path: Optional[str] = None
    directories_created: List[str] = []
    
    # Warnings and errors
    warnings: List[str] = []
    errors: List[str] = []
    
    # Device information
    device_info: Dict[str, Any] = {}


class ComposeDeploymentRequest(BaseModel):
    """Request for deploying modified compose to target device."""
    
    device: str = Field(..., description="Target device hostname")
    compose_content: str = Field(..., description="Docker compose content to deploy")
    deployment_path: str = Field(..., description="Path where to store compose file on device")
    
    # Deployment options
    start_services: bool = Field(True, description="Start services after deployment")
    pull_images: bool = Field(True, description="Pull latest images before starting")
    recreate_containers: bool = Field(False, description="Recreate containers even if config unchanged")
    
    # Directory management
    create_directories: bool = Field(True, description="Create necessary directories")
    backup_existing: bool = Field(True, description="Backup existing compose file")
    
    # Service management
    services_to_start: Optional[List[str]] = Field(None, description="Specific services to start")
    services_to_stop: Optional[List[str]] = Field(None, description="Services to stop before deployment")


class ComposeDeploymentResult(BaseModel):
    """Result of compose deployment operation."""
    
    device: str
    deployment_path: str
    timestamp: datetime
    success: bool
    execution_time_ms: int
    
    # Files managed
    compose_file_created: bool
    backup_file_path: Optional[str] = None
    directories_created: List[str] = []
    
    # Docker operations
    images_pulled: List[str] = []
    containers_created: List[str] = []
    containers_started: List[str] = []
    containers_stopped: List[str] = []
    
    # Service status
    service_status: Dict[str, str] = {}  # service_name -> status
    
    # Output and errors
    docker_compose_output: str = ""
    warnings: List[str] = []
    errors: List[str] = []


class PortScanRequest(BaseModel):
    """Request for scanning available ports on a device."""
    
    device: str = Field(..., description="Device hostname to scan")
    port_range_start: int = Field(8000, description="Start of port range to scan")
    port_range_end: int = Field(9000, description="End of port range to scan")
    protocol: str = Field("tcp", description="Protocol to scan (tcp/udp)")
    timeout: int = Field(5, description="Timeout for port checks in seconds")


class PortScanResult(BaseModel):
    """Result of port scanning operation."""
    
    device: str
    port_range_start: int
    port_range_end: int
    timestamp: datetime
    execution_time_ms: int
    
    # Port availability
    available_ports: List[int] = []
    used_ports: List[int] = []
    total_scanned: int
    
    # Docker port usage
    docker_port_usage: Dict[int, str] = {}  # port -> container_name
    
    # System port usage
    system_port_usage: Dict[int, str] = {}  # port -> process_info


class NetworkScanRequest(BaseModel):
    """Request for scanning Docker networks on a device."""
    
    device: str = Field(..., description="Device hostname to scan")
    include_system_networks: bool = Field(False, description="Include Docker system networks")


class NetworkScanResult(BaseModel):
    """Result of Docker network scanning."""
    
    device: str
    timestamp: datetime
    execution_time_ms: int
    
    # Network information
    networks: List[Dict[str, Any]] = []
    available_subnets: List[str] = []
    recommended_network: Optional[str] = None
    
    # Network usage
    containers_by_network: Dict[str, List[str]] = {}