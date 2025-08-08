"""
Pydantic schemas for Docker Compose deployment operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
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
    aliases: list[str] | None = None
    ipv4_address: str | None = None


class ComposeModificationRequest(BaseModel):
    """Request for modifying a docker-compose file for target device deployment."""

    # Source and target information
    compose_content: str = Field(..., description="Original docker-compose.yml content")
    target_device: str = Field(..., description="Target device hostname")

    # Service configuration
    service_name: str | None = Field(None, description="Specific service to modify (all if None)")

    # Path modifications
    update_appdata_paths: bool = Field(True, description="Update volume paths to device appdata path")
    custom_appdata_path: str | None = Field(None, description="Override device default appdata path")

    # Port management
    auto_assign_ports: bool = Field(True, description="Automatically assign available ports")
    port_range_start: int = Field(8000, description="Start of port range for auto-assignment")
    port_range_end: int = Field(9000, description="End of port range for auto-assignment")
    custom_port_mappings: dict[str, int] | None = Field(None, description="Custom port mappings by service")

    # Network configuration
    update_networks: bool = Field(True, description="Configure Docker networks for device")
    default_network: str | None = Field(None, description="Default network to use")

    # Proxy configuration
    generate_proxy_configs: bool = Field(True, description="Generate SWAG proxy configurations")
    base_domain: str | None = Field(None, description="Base domain for proxy configurations")

    # Deployment settings
    deployment_path: str | None = Field(None, description="Where to store the compose file on device")
    create_directories: bool = Field(True, description="Create necessary directories on device")


class ComposeModificationResult(BaseModel):
    """Result of docker-compose modification operation."""

    # Operation metadata
    device: str
    service_name: str | None
    timestamp: datetime
    success: bool
    execution_time_ms: int

    # Modified compose content
    modified_compose: str
    original_compose_hash: str
    modified_compose_hash: str

    # Changes applied
    changes_applied: list[str] = []

    # Port assignments
    port_assignments: dict[str, list[ComposeServicePort]] = {}

    # Volume path updates
    volume_updates: dict[str, list[ComposeServiceVolume]] = {}

    # Network configurations
    network_configs: dict[str, ComposeServiceNetwork] = {}

    # Proxy configurations generated
    proxy_configs: list[dict[str, Any]] = []

    # Deployment information
    deployment_path: str | None = None
    directories_created: list[str] = []

    # Warnings and errors
    warnings: list[str] = []
    errors: list[str] = []

    # Device information
    device_info: dict[str, Any] = {}


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
    services_to_start: list[str] | None = Field(None, description="Specific services to start")
    services_to_stop: list[str] | None = Field(None, description="Services to stop before deployment")


class ComposeDeploymentResult(BaseModel):
    """Result of compose deployment operation."""

    device: str
    deployment_path: str
    timestamp: datetime
    success: bool
    execution_time_ms: int

    # Files managed
    compose_file_created: bool
    backup_file_path: str | None = None
    directories_created: list[str] = []

    # Docker operations
    images_pulled: list[str] = []
    containers_created: list[str] = []
    containers_started: list[str] = []
    containers_stopped: list[str] = []

    # Service status
    service_status: dict[str, str] = {}  # service_name -> status

    # Output and errors
    docker_compose_output: str = ""
    warnings: list[str] = []
    errors: list[str] = []


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
    available_ports: list[int] = []
    used_ports: list[int] = []
    total_scanned: int

    # Docker port usage
    docker_port_usage: dict[int, str] = {}  # port -> container_name

    # System port usage
    system_port_usage: dict[int, str] = {}  # port -> process_info


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
    networks: list[dict[str, Any]] = []
    available_subnets: list[str] = []
    recommended_network: str | None = None

    # Network usage
    containers_by_network: dict[str, list[str]] = {}
