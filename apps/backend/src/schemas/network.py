"""
Network-related Pydantic schemas for request/response validation.
"""

from datetime import UTC, datetime

from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from apps.backend.src.schemas.common import PaginatedResponse


class NetworkInterfaceBase(BaseModel):
    """Base network interface schema with common fields"""

    interface_name: str = Field(
        ..., min_length=1, max_length=100, description="Network interface name"
    )
    interface_type: str = Field(..., max_length=50, description="Interface type")
    mac_address: str | None = Field(None, description="MAC address")
    ip_addresses: list[str] = Field(default_factory=list, description="List of IP addresses")
    mtu: int | None = Field(None, ge=68, le=65536, description="Maximum Transmission Unit")
    speed_mbps: int | None = Field(None, ge=0, description="Interface speed in Mbps")
    duplex: str | None = Field(None, description="Duplex mode (full/half/unknown)")
    state: str = Field(..., description="Interface state (up/down/unknown)")
    rx_bytes: int | None = Field(None, ge=0, description="Bytes received")
    tx_bytes: int | None = Field(None, ge=0, description="Bytes transmitted")
    rx_packets: int | None = Field(None, ge=0, description="Packets received")
    tx_packets: int | None = Field(None, ge=0, description="Packets transmitted")
    rx_errors: int | None = Field(None, ge=0, description="Receive errors")
    tx_errors: int | None = Field(None, ge=0, description="Transmit errors")
    rx_dropped: int | None = Field(None, ge=0, description="Dropped receive packets")
    tx_dropped: int | None = Field(None, ge=0, description="Dropped transmit packets")

    @field_validator("interface_type")
    @classmethod
    def validate_interface_type(cls, v: str) -> str:
        valid_types = [
            "ethernet",
            "wifi",
            "loopback",
            "bridge",
            "vlan",
            "bond",
            "tun",
            "tap",
            "ppp",
            "can",
            "infiniband",
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Interface type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("duplex")
    @classmethod
    def validate_duplex(cls, v: str | None) -> str | None:
        if v is not None:
            valid_duplex = ["full", "half", "unknown"]
            if v.lower() not in valid_duplex:
                raise ValueError(f"Duplex must be one of: {', '.join(valid_duplex)}")
            return v.lower()
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        valid_states = ["up", "down", "unknown"]
        if v.lower() not in valid_states:
            raise ValueError(f"State must be one of: {', '.join(valid_states)}")
        return v.lower()

    @field_validator("mac_address")
    @classmethod
    def validate_mac_address(cls, v: str) -> str:
        if v is not None:
            # Basic MAC address validation
            import re

            mac_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
            if not mac_pattern.match(v):
                raise ValueError("Invalid MAC address format")
            return v.lower()
        return v

    @field_validator("ip_addresses")
    @classmethod
    def validate_ip_addresses(cls, v: list[str]) -> list[str]:
        if v:
            from ipaddress import ip_address

            for ip in v:
                try:
                    ip_address(ip)
                except ValueError:
                    raise ValueError(f"Invalid IP address: {ip}")
        return v


class NetworkInterfaceCreate(NetworkInterfaceBase):
    """Schema for creating a new network interface record"""

    device_id: UUID = Field(..., description="Device UUID")


class NetworkInterfaceResponse(NetworkInterfaceBase):
    """Schema for network interface response data"""

    time: datetime = Field(description="Timestamp of the interface record")
    device_id: UUID = Field(description="Device UUID")

    # Computed fields
    utilization_percent: float | None = Field(
        None, description="Interface utilization percentage"
    )
    error_rate: float | None = Field(None, description="Error rate percentage")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class NetworkInterfaceList(PaginatedResponse[NetworkInterfaceResponse]):
    """Paginated list of network interfaces"""

    pass


class DockerNetworkBase(BaseModel):
    """Base Docker network schema with common fields"""

    network_id: str = Field(..., min_length=1, max_length=64, description="Docker network ID")
    network_name: str = Field(..., min_length=1, max_length=255, description="Docker network name")
    driver: str = Field(..., max_length=100, description="Network driver")
    scope: str = Field(..., max_length=50, description="Network scope")
    subnet: str | None = Field(None, description="Network subnet (CIDR)")
    gateway: str | None = Field(None, description="Network gateway IP")
    containers_count: int = Field(default=0, ge=0, description="Number of connected containers")
    labels: dict[str, str] = Field(default_factory=dict, description="Network labels")
    options: dict[str, Any] = Field(default_factory=dict, description="Network options")
    config: dict[str, Any] = Field(default_factory=dict, description="Network configuration")

    @field_validator("driver")
    @classmethod
    def validate_driver(cls, v: str | None) -> str | None:
        valid_drivers = ["bridge", "host", "none", "overlay", "macvlan", "ipvlan"]
        if v.lower() not in valid_drivers:
            raise ValueError(f"Driver must be one of: {', '.join(valid_drivers)}")
        return v.lower()

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        valid_scopes = ["local", "global", "swarm"]
        if v.lower() not in valid_scopes:
            raise ValueError(f"Scope must be one of: {', '.join(valid_scopes)}")
        return v.lower()

    @field_validator("subnet")
    @classmethod
    def validate_subnet(cls, v: str) -> str:
        if v is not None:
            from ipaddress import ip_network

            try:
                ip_network(v)
                return v
            except ValueError:
                raise ValueError("Invalid subnet format")
        return v

    @field_validator("gateway")
    @classmethod
    def validate_gateway(cls, v: str | None) -> str | None:
        if v is not None:
            from ipaddress import ip_address

            try:
                ip_address(v)
                return v
            except ValueError:
                raise ValueError("Invalid gateway IP address")
        return v


class DockerNetworkCreate(DockerNetworkBase):
    """Schema for creating a new Docker network record"""

    device_id: UUID = Field(..., description="Device UUID")


class DockerNetworkResponse(DockerNetworkBase):
    """Schema for Docker network response data"""

    time: datetime = Field(description="Timestamp of the network record")
    device_id: UUID = Field(description="Device UUID")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class DockerNetworkList(PaginatedResponse[DockerNetworkResponse]):
    """Paginated list of Docker networks"""

    pass


class NetworkTopologyNode(BaseModel):
    """Network topology node representation"""

    device_id: UUID = Field(description="Device UUID")
    hostname: str = Field(description="Device hostname")
    ip_address: str = Field(description="Primary IP address")
    device_type: str = Field(description="Device type")
    interfaces: list[dict[str, Any]] = Field(description="Network interfaces")
    docker_networks: list[dict[str, Any]] = Field(description="Docker networks")
    connections: list[str] = Field(description="Connected device hostnames")
    last_seen: datetime | None = Field(description="Last seen timestamp")


class NetworkTopology(BaseModel):
    """Complete network topology"""

    nodes: list[NetworkTopologyNode] = Field(description="Network nodes")
    connections: list[dict[str, str]] = Field(description="Network connections")
    subnets: list[dict[str, Any]] = Field(description="Discovered subnets")
    docker_networks: list[dict[str, Any]] = Field(description="Docker networks across devices")
    statistics: dict[str, int] = Field(description="Topology statistics")
    discovery_time: datetime = Field(description="Topology discovery timestamp")

    class Config:
        from_attributes = True


class NetworkInterfaceMetrics(BaseModel):
    """Network interface metrics summary"""

    device_id: UUID
    interface_name: str
    current_metrics: dict[str, Any] = Field(description="Current interface metrics")
    throughput_mbps: float | None = Field(description="Current throughput in Mbps")
    utilization_percent: float | None = Field(description="Interface utilization")
    error_rate: float | None = Field(description="Error rate")
    packet_loss_percent: float | None = Field(description="Packet loss percentage")
    latency_ms: float | None = Field(description="Network latency in milliseconds")
    trend_data: dict[str, list[float]] = Field(description="24-hour trend data")
    alerts: list[str] = Field(description="Active network alerts")
    last_updated: datetime = Field(description="Last metrics update")

    class Config:
        from_attributes = True


class NetworkHealthOverview(BaseModel):
    """Network health overview across all devices"""

    total_interfaces: int = Field(description="Total network interfaces")
    active_interfaces: int = Field(description="Active interfaces")
    error_interfaces: int = Field(description="Interfaces with errors")
    total_docker_networks: int = Field(description="Total Docker networks")
    average_utilization: float = Field(description="Average network utilization")
    total_throughput_gbps: float = Field(description="Total network throughput in Gbps")
    interfaces_by_type: dict[str, int] = Field(description="Interface count by type")
    health_by_device: dict[str, str] = Field(description="Network health by device")
    high_utilization_interfaces: list[str] = Field(description="High utilization interfaces")
    error_prone_interfaces: list[str] = Field(description="Interfaces with frequent errors")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Report timestamp")


class NetworkFilter(BaseModel):
    """Network filtering parameters"""

    device_ids: list[UUID] | None = Field(description="Filter by device IDs")
    interface_types: list[str] | None = Field(description="Filter by interface types")
    interface_states: list[str] | None = Field(description="Filter by interface states")
    network_drivers: list[str] | None = Field(description="Filter by Docker network drivers")
    has_errors: bool | None = Field(description="Filter interfaces with errors")
    min_speed_mbps: int | None = Field(description="Minimum interface speed")
    subnet_filter: str | None = Field(description="Filter by subnet (CIDR)")


class NetworkPortScan(BaseModel):
    """Network port scan result"""

    target_ip: str = Field(description="Target IP address")
    port: int = Field(ge=1, le=65535, description="Port number")
    protocol: str = Field(description="Protocol (TCP/UDP)")
    status: str = Field(description="Port status (open/closed/filtered)")
    service: str | None = Field(description="Detected service")
    version: str | None = Field(description="Service version")
    banner: str | None = Field(description="Service banner")
    response_time_ms: float | None = Field(description="Response time in milliseconds")
    scan_time: datetime = Field(description="Scan timestamp")


class NetworkConnectivityTest(BaseModel):
    """Network connectivity test result"""

    source_device_id: UUID = Field(description="Source device ID")
    target_ip: str = Field(description="Target IP address")
    target_hostname: str | None = Field(description="Target hostname")
    test_type: str = Field(description="Test type (ping/traceroute/tcp)")
    status: str = Field(description="Test status (success/failed/timeout)")
    response_time_ms: float | None = Field(description="Response time")
    packet_loss_percent: float | None = Field(description="Packet loss percentage")
    hop_count: int | None = Field(description="Number of network hops")
    route_details: list[str] = Field(default_factory=list, description="Route hop details")
    error_message: str | None = Field(description="Error message if test failed")
    test_time: datetime = Field(description="Test timestamp")

    class Config:
        from_attributes = True
