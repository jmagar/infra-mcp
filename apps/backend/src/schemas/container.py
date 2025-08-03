"""
Container-related Pydantic schemas for request/response validation.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from apps.backend.src.schemas.common import PaginatedResponse, TimeRangeParams


class ContainerSnapshotBase(BaseModel):
    """Base container snapshot schema"""

    device_id: UUID = Field(description="Device identifier")
    container_id: str = Field(..., max_length=64, description="Container ID")
    container_name: str = Field(..., max_length=255, description="Container name")
    image: Optional[str] = Field(None, max_length=255, description="Container image")

    # Container status
    status: Optional[str] = Field(None, description="Container status")
    state: Optional[str] = Field(None, description="Container state")

    # Resource usage metrics
    cpu_usage_percent: Optional[float] = Field(
        None, ge=0, le=100, description="CPU usage percentage"
    )
    memory_usage_bytes: Optional[int] = Field(None, ge=0, description="Memory usage in bytes")
    memory_limit_bytes: Optional[int] = Field(None, ge=0, description="Memory limit in bytes")

    # Network metrics
    network_bytes_sent: Optional[int] = Field(None, ge=0, description="Network bytes sent")
    network_bytes_recv: Optional[int] = Field(None, ge=0, description="Network bytes received")

    # Block I/O metrics
    block_read_bytes: Optional[int] = Field(None, ge=0, description="Block read bytes")
    block_write_bytes: Optional[int] = Field(None, ge=0, description="Block write bytes")

    # Configuration data
    ports: List[Dict[str, Any]] = Field(default_factory=list, description="Port mappings")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    labels: Dict[str, str] = Field(default_factory=dict, description="Container labels")
    volumes: List[Dict[str, Any]] = Field(default_factory=list, description="Volume mounts")
    networks: List[Dict[str, Any]] = Field(default_factory=list, description="Network connections")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = [
                "running",
                "paused",
                "restarting",
                "removing",
                "dead",
                "created",
                "exited",
                "stopped",
            ]
            if v.lower() not in valid_statuses:
                raise ValueError(
                    f"Invalid container status. Valid statuses: {', '.join(valid_statuses)}"
                )
            return v.lower()
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v):
        if v is not None:
            valid_states = [
                "created",
                "restarting",
                "running",
                "removing",
                "paused",
                "exited",
                "dead",
            ]
            if v.lower() not in valid_states:
                raise ValueError(
                    f"Invalid container state. Valid states: {', '.join(valid_states)}"
                )
            return v.lower()
        return v

    @field_validator("memory_usage_bytes")
    @classmethod
    def validate_memory_usage(cls, v, info):
        if v is not None and info.data.get("memory_limit_bytes"):
            if v > info.data["memory_limit_bytes"]:
                # Allow slight overflow for reporting accuracy
                pass
        return v

    @field_validator("container_id")
    @classmethod
    def validate_container_id(cls, v):
        # Basic Docker container ID validation (hex string)
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("Container ID must be a hexadecimal string")
        return v.lower()


class ContainerSnapshotCreate(ContainerSnapshotBase):
    """Schema for creating container snapshot"""

    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Snapshot timestamp")


class ContainerSnapshotResponse(ContainerSnapshotBase):
    """Schema for container snapshot response"""

    time: datetime = Field(description="Snapshot timestamp")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class ContainerSnapshotList(PaginatedResponse[ContainerSnapshotResponse]):
    """Paginated list of container snapshots"""

    pass


class ContainerQuery(TimeRangeParams):
    """Query parameters for container data"""

    device_ids: Optional[List[UUID]] = Field(None, description="Filter by device IDs")
    container_ids: Optional[List[str]] = Field(None, description="Filter by container IDs")
    container_names: Optional[List[str]] = Field(None, description="Filter by container names")
    images: Optional[List[str]] = Field(None, description="Filter by container images")
    statuses: Optional[List[str]] = Field(None, description="Filter by container statuses")
    states: Optional[List[str]] = Field(None, description="Filter by container states")
    labels: Optional[Dict[str, str]] = Field(None, description="Filter by labels")


class ContainerSummary(BaseModel):
    """Container summary for dashboard"""

    device_id: UUID = Field(description="Device identifier")
    hostname: Optional[str] = Field(description="Device hostname")
    container_id: str = Field(description="Container ID")
    container_name: str = Field(description="Container name")
    image: Optional[str] = Field(description="Container image")

    # Current status
    status: Optional[str] = Field(description="Current container status")
    state: Optional[str] = Field(description="Current container state")
    uptime: Optional[str] = Field(description="Container uptime")

    # Resource usage
    cpu_usage_percent: Optional[float] = Field(description="Current CPU usage")
    memory_usage_mb: Optional[float] = Field(description="Current memory usage in MB")
    memory_limit_mb: Optional[float] = Field(description="Memory limit in MB")
    memory_usage_percent: Optional[float] = Field(description="Memory usage percentage")

    # Network I/O
    network_io_mb: Optional[Dict[str, float]] = Field(description="Network I/O in MB")

    # Block I/O
    block_io_mb: Optional[Dict[str, float]] = Field(description="Block I/O in MB")

    # Port mappings
    exposed_ports: List[str] = Field(description="Exposed ports")

    # Health status
    health_status: Optional[str] = Field(description="Container health status")
    restart_count: Optional[int] = Field(description="Number of restarts")

    # Metadata
    created_at: Optional[datetime] = Field(description="Container creation timestamp")
    last_updated: datetime = Field(description="Last snapshot timestamp")

    class Config:
        from_attributes = True


class ContainerMetrics(BaseModel):
    """Container resource metrics"""

    container_id: str = Field(description="Container ID")
    container_name: str = Field(description="Container name")

    # CPU metrics
    cpu_usage_percent: float = Field(description="CPU usage percentage")
    cpu_throttled_periods: Optional[int] = Field(description="CPU throttled periods")

    # Memory metrics
    memory_usage_bytes: int = Field(description="Memory usage in bytes")
    memory_limit_bytes: Optional[int] = Field(description="Memory limit in bytes")
    memory_cache_bytes: Optional[int] = Field(description="Memory cache in bytes")
    memory_rss_bytes: Optional[int] = Field(description="Memory RSS in bytes")

    # Network metrics
    network_rx_bytes: int = Field(description="Network bytes received")
    network_tx_bytes: int = Field(description="Network bytes transmitted")
    network_rx_packets: Optional[int] = Field(description="Network packets received")
    network_tx_packets: Optional[int] = Field(description="Network packets transmitted")

    # Block I/O metrics
    block_read_bytes: int = Field(description="Block bytes read")
    block_write_bytes: int = Field(description="Block bytes written")
    block_read_ops: Optional[int] = Field(description="Block read operations")
    block_write_ops: Optional[int] = Field(description="Block write operations")

    # PIDs
    pids_current: Optional[int] = Field(description="Current number of PIDs")
    pids_limit: Optional[int] = Field(description="PID limit")

    timestamp: datetime = Field(description="Metrics timestamp")

    class Config:
        from_attributes = True


class ContainerDetails(BaseModel):
    """Detailed container information"""

    device_id: UUID = Field(description="Device identifier")
    hostname: str = Field(description="Device hostname")
    container_id: str = Field(description="Container ID")
    container_name: str = Field(description="Container name")
    image: str = Field(description="Container image")
    image_id: Optional[str] = Field(description="Image ID")

    # Status information
    status: str = Field(description="Container status")
    state: str = Field(description="Container state")
    running: bool = Field(description="Whether container is running")
    paused: bool = Field(description="Whether container is paused")
    restarting: bool = Field(description="Whether container is restarting")
    oom_killed: bool = Field(description="Whether container was OOM killed")
    dead: bool = Field(description="Whether container is dead")
    pid: Optional[int] = Field(description="Container PID")
    exit_code: Optional[int] = Field(description="Exit code")
    error: Optional[str] = Field(description="Error message if any")

    # Timestamps
    created_at: datetime = Field(description="Container creation time")
    started_at: Optional[datetime] = Field(description="Container start time")
    finished_at: Optional[datetime] = Field(description="Container finish time")

    # Configuration
    command: Optional[List[str]] = Field(description="Container command")
    args: Optional[List[str]] = Field(description="Container arguments")
    working_dir: Optional[str] = Field(description="Working directory")
    entrypoint: Optional[List[str]] = Field(description="Container entrypoint")
    user: Optional[str] = Field(description="User")

    # Environment and labels
    environment: Dict[str, str] = Field(description="Environment variables")
    labels: Dict[str, str] = Field(description="Container labels")

    # Network configuration
    network_mode: Optional[str] = Field(description="Network mode")
    networks: Dict[str, Any] = Field(description="Network configurations")
    ports: Dict[str, Any] = Field(description="Port configurations")

    # Volume configuration
    mounts: List[Dict[str, Any]] = Field(description="Volume mounts")

    # Resource limits
    memory_limit: Optional[int] = Field(description="Memory limit in bytes")
    cpu_limit: Optional[float] = Field(description="CPU limit")

    # Health check
    health_status: Optional[str] = Field(description="Health check status")
    health_check: Optional[Dict[str, Any]] = Field(description="Health check configuration")

    # Restart policy
    restart_policy: Optional[Dict[str, Any]] = Field(description="Restart policy")
    restart_count: int = Field(description="Restart count")

    class Config:
        from_attributes = True


class ContainerLogs(BaseModel):
    """Container logs response"""

    container_id: str = Field(description="Container ID")
    container_name: str = Field(description="Container name")
    logs: List[Dict[str, Any]] = Field(description="Log entries")
    total_lines: int = Field(description="Total number of log lines")
    since: Optional[datetime] = Field(description="Logs since timestamp")
    until: Optional[datetime] = Field(description="Logs until timestamp")
    tail: Optional[int] = Field(description="Number of lines from tail")
    timestamps: bool = Field(description="Whether timestamps are included")

    class Config:
        from_attributes = True


class ContainerStats(BaseModel):
    """Container statistics over time"""

    container_id: str = Field(description="Container ID")
    container_name: str = Field(description="Container name")

    # Time-series data
    cpu_usage_history: List[Dict[str, Any]] = Field(description="CPU usage over time")
    memory_usage_history: List[Dict[str, Any]] = Field(description="Memory usage over time")
    network_io_history: List[Dict[str, Any]] = Field(description="Network I/O over time")
    block_io_history: List[Dict[str, Any]] = Field(description="Block I/O over time")

    # Summary statistics
    avg_cpu_usage: float = Field(description="Average CPU usage")
    max_cpu_usage: float = Field(description="Maximum CPU usage")
    avg_memory_usage: float = Field(description="Average memory usage")
    max_memory_usage: float = Field(description="Maximum memory usage")

    # Time range
    start_time: datetime = Field(description="Statistics start time")
    end_time: datetime = Field(description="Statistics end time")
    data_points: int = Field(description="Number of data points")

    class Config:
        from_attributes = True


class ContainerEvent(BaseModel):
    """Container event"""

    device_id: UUID = Field(description="Device identifier")
    container_id: str = Field(description="Container ID")
    container_name: str = Field(description="Container name")
    event_type: str = Field(description="Event type (start, stop, restart, etc.)")
    action: str = Field(description="Action performed")
    actor: Dict[str, Any] = Field(description="Actor information")
    scope: str = Field(description="Event scope")
    timestamp: datetime = Field(description="Event timestamp")

    class Config:
        from_attributes = True


class ServiceDependency(BaseModel):
    """Service dependency information"""

    container_id: str = Field(description="Container ID")
    container_name: str = Field(description="Container name")
    service_name: Optional[str] = Field(description="Service name")
    dependencies: List[str] = Field(description="List of dependent services")
    dependents: List[str] = Field(description="List of services that depend on this")
    network_dependencies: List[str] = Field(description="Network dependencies")
    volume_dependencies: List[str] = Field(description="Volume dependencies")
    environment_dependencies: List[str] = Field(description="Environment dependencies")

    class Config:
        from_attributes = True
