"""
Device-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from ipaddress import IPv4Address, IPv6Address
from apps.backend.src.schemas.common import DeviceStatus, PaginatedResponse


class DeviceBase(BaseModel):
    """Base device schema with common fields"""

    hostname: str = Field(..., min_length=1, max_length=255, description="Device hostname")
    ip_address: Optional[str] = Field(
        None, description="Device IP address (optional - SSH config can handle this)"
    )
    ssh_port: Optional[int] = Field(
        None, ge=1, le=65535, description="SSH port number (optional - SSH config can handle this)"
    )
    ssh_username: Optional[str] = Field(
        None, max_length=100, description="SSH username (optional - SSH config can handle this)"
    )
    device_type: str = Field(default="server", max_length=50, description="Device type")
    description: Optional[str] = Field(None, description="Device description")
    location: Optional[str] = Field(None, max_length=255, description="Physical location")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Device tags")
    monitoring_enabled: bool = Field(default=True, description="Whether monitoring is enabled")

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v):
        if v is None:
            return v
        try:
            # Handle both string and IPv4Address/IPv6Address objects
            from ipaddress import ip_address, IPv4Address, IPv6Address

            if isinstance(v, (IPv4Address, IPv6Address)):
                return str(v)  # Convert to string
            # Try to parse as IPv4 or IPv6
            ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v):
        # Basic hostname validation
        if not v.replace("-", "").replace(".", "").replace("_", "").isalnum():
            raise ValueError("Hostname contains invalid characters")
        return v.lower()

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v):
        valid_types = [
            "server",
            "container_host",
            "storage",
            "network",
            "router",
            "switch",
            "firewall",
            "workstation",
            "development",
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Device type must be one of: {', '.join(valid_types)}")
        return v.lower()


class DeviceCreate(DeviceBase):
    """Schema for creating a new device"""

    pass


class DeviceUpdate(BaseModel):
    """Schema for updating an existing device"""

    hostname: Optional[str] = Field(None, min_length=1, max_length=255)
    ip_address: Optional[str] = Field(None)
    ssh_port: Optional[int] = Field(None, ge=1, le=65535)
    ssh_username: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None)
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[Dict[str, Any]] = Field(None)
    monitoring_enabled: Optional[bool] = Field(None)
    status: Optional[DeviceStatus] = Field(None)

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v):
        if v is not None:
            try:
                from ipaddress import ip_address

                ip_address(v)
                return v
            except ValueError:
                raise ValueError("Invalid IP address format")
        return v

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v):
        if v is not None:
            if not v.replace("-", "").replace(".", "").replace("_", "").isalnum():
                raise ValueError("Hostname contains invalid characters")
            return v.lower()
        return v


class DeviceResponse(DeviceBase):
    """Schema for device response data"""

    id: UUID = Field(description="Device unique identifier")
    status: DeviceStatus = Field(description="Device status")
    last_seen: Optional[datetime] = Field(description="Last time device was seen")
    created_at: datetime = Field(description="Device creation timestamp")
    updated_at: datetime = Field(description="Device last update timestamp")

    @field_validator("ip_address", mode="before")
    @classmethod
    def convert_ip_address(cls, v):
        """Convert IPv4Address/IPv6Address objects to string"""
        if v is None:
            return v
        from ipaddress import IPv4Address, IPv6Address

        if isinstance(v, (IPv4Address, IPv6Address)):
            return str(v)
        return v

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class DeviceList(PaginatedResponse[DeviceResponse]):
    """Paginated list of devices"""

    pass


class DeviceSummary(BaseModel):
    """Device summary for dashboard and overview"""

    id: UUID
    hostname: str
    ip_address: Optional[str]
    device_type: str
    status: DeviceStatus
    monitoring_enabled: bool
    last_seen: Optional[datetime]

    class Config:
        from_attributes = True


class DeviceHealth(BaseModel):
    """Device health status summary"""

    device_id: UUID
    hostname: str
    status: DeviceStatus
    last_seen: Optional[datetime]
    connectivity_status: str = Field(description="SSH connectivity status")
    system_health: Optional[str] = Field(description="Overall system health")
    cpu_usage: Optional[float] = Field(description="Current CPU usage percentage")
    memory_usage: Optional[float] = Field(description="Current memory usage percentage")
    disk_usage: Optional[float] = Field(description="Current disk usage percentage")
    uptime_hours: Optional[int] = Field(description="System uptime in hours")
    active_containers: Optional[int] = Field(description="Number of active containers")
    alerts_count: Optional[int] = Field(description="Number of active alerts")

    class Config:
        from_attributes = True


class DeviceHealthList(BaseModel):
    """List of device health summaries"""

    devices: List[DeviceHealth] = Field(description="List of device health statuses")
    summary: Dict[str, int] = Field(description="Health summary statistics")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC), description="Report timestamp")


class DeviceConnectionTest(BaseModel):
    """Device connectivity test result"""

    device_id: UUID
    hostname: str
    ip_address: Optional[str]
    ssh_port: Optional[int]
    connection_status: str = Field(description="Connection test result")
    response_time_ms: Optional[float] = Field(description="Connection response time")
    error_message: Optional[str] = Field(description="Error message if connection failed")
    test_timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))

    @field_validator("ip_address", mode="before")
    @classmethod
    def convert_ip_address(cls, v):
        """Convert IPv4Address/IPv6Address objects to string"""
        if v is None:
            return v
        if isinstance(v, (IPv4Address, IPv6Address)):
            return str(v)
        return v

    class Config:
        from_attributes = True


class DeviceCredentials(BaseModel):
    """Device SSH credentials (for updates only)"""

    ssh_username: Optional[str] = Field(None, max_length=100)
    ssh_port: Optional[int] = Field(None, ge=1, le=65535)
    ssh_key_path: Optional[str] = Field(None, description="Path to SSH private key")


class DeviceMetricsOverview(BaseModel):
    """Device metrics overview for dashboard"""

    device_id: UUID
    hostname: str
    current_metrics: Dict[str, Any] = Field(description="Latest metric values")
    trend_data: Dict[str, List[float]] = Field(description="24-hour trend data")
    alerts: List[str] = Field(description="Active alerts for this device")
    last_updated: datetime = Field(description="Last metrics update timestamp")

    class Config:
        from_attributes = True


class DeviceImportRequest(BaseModel):
    """Request schema for importing devices from SSH config"""

    ssh_config_path: str = Field(description="Path to SSH configuration file (e.g., ~/.ssh/config)")
    dry_run: bool = Field(
        default=False, description="If true, return what would be imported without saving"
    )
    update_existing: bool = Field(
        default=True, description="Whether to update existing devices with new information"
    )
    default_device_type: str = Field(
        default="server", description="Default device type for imported devices"
    )
    default_monitoring: bool = Field(
        default=True, description="Default monitoring state for imported devices"
    )
    tag_prefix: Optional[str] = Field(None, description="Prefix to add to imported device tags")

    @field_validator("ssh_config_path")
    @classmethod
    def validate_ssh_config_path(cls, v):
        # Expand tilde if present
        if v.startswith("~"):
            from pathlib import Path

            v = str(Path(v).expanduser())
        return v

    @field_validator("default_device_type")
    @classmethod
    def validate_default_device_type(cls, v):
        valid_types = [
            "server",
            "container_host",
            "storage",
            "network",
            "router",
            "switch",
            "firewall",
            "workstation",
            "development",
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Device type must be one of: {', '.join(valid_types)}")
        return v.lower()


class DeviceImportResult(BaseModel):
    """Result of device import operation"""

    hostname: str = Field(description="Device hostname")
    action: str = Field(description="Action taken: 'created', 'updated', 'skipped', or 'error'")
    device_id: Optional[UUID] = Field(None, description="Device ID if successfully created/updated")
    error_message: Optional[str] = Field(None, description="Error message if action failed")
    changes: Dict[str, Any] = Field(default_factory=dict, description="What changed during update")


class DeviceImportResponse(BaseModel):
    """Response schema for device import operation"""

    total_hosts_found: int = Field(description="Total hosts found in SSH config")
    results: List[DeviceImportResult] = Field(description="Results for each device")
    summary: Dict[str, int] = Field(description="Summary of actions taken")
    dry_run: bool = Field(description="Whether this was a dry run")
    import_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(datetime.UTC), description="When the import was performed"
    )

    @classmethod
    def create_summary(cls, results: List[DeviceImportResult]) -> Dict[str, int]:
        """Create summary statistics from results"""
        summary = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
        for result in results:
            if result.action in summary:
                summary[result.action] += 1
            elif result.action == "error":
                summary["errors"] += 1
        return summary
