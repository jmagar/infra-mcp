"""
Container-related Pydantic schemas for request/response validation.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from apps.backend.src.schemas.common import (
    PaginatedResponse,
    TimeRangeParams,
    APIResponse,
    OperationResult,
)


class ContainerSnapshotBase(BaseModel):
    """Base container snapshot schema - aligned with container_snapshots table"""

    device_id: UUID = Field(description="Device identifier")
    container_id: str = Field(..., max_length=255, description="Container ID")
    name: str = Field(..., max_length=255, description="Container name")
    image: Optional[str] = Field(None, max_length=255, description="Container image")

    # Container status
    status: Optional[str] = Field(None, description="Container status")
    state: Optional[str] = Field(None, description="Container state")

    # Resource usage metrics
    cpu_usage: Optional[float] = Field(
        None, ge=0, description="CPU usage (matches database field)"
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
    """Query parameters for container data - database-aligned"""

    device_ids: Optional[List[UUID]] = Field(None, description="Filter by device IDs")
    container_ids: Optional[List[str]] = Field(None, description="Filter by container IDs")
    names: Optional[List[str]] = Field(None, description="Filter by container names")
    images: Optional[List[str]] = Field(None, description="Filter by container images")
    statuses: Optional[List[str]] = Field(None, description="Filter by container statuses")
    labels: Optional[Dict[str, str]] = Field(None, description="Filter by labels")


class ContainerSummary(BaseModel):
    """Container summary for dashboard - database-first approach"""

    device_id: UUID = Field(description="Device identifier")
    hostname: Optional[str] = Field(description="Device hostname")
    container_id: str = Field(description="Container ID")
    name: str = Field(description="Container name")
    image: Optional[str] = Field(description="Container image")

    # Current status from database
    status: Optional[str] = Field(description="Container status from latest snapshot")

    # Resource usage from database
    cpu_usage: Optional[float] = Field(description="CPU usage from latest snapshot")
    memory_usage_bytes: Optional[int] = Field(description="Memory usage in bytes")
    memory_limit_bytes: Optional[int] = Field(description="Memory limit in bytes")
    memory_usage_percent: Optional[float] = Field(description="Calculated memory usage percentage")

    # Network I/O from database
    network_bytes_sent: Optional[int] = Field(description="Network bytes sent")
    network_bytes_recv: Optional[int] = Field(description="Network bytes received")

    # Block I/O from database
    block_read_bytes: Optional[int] = Field(description="Block read bytes")
    block_write_bytes: Optional[int] = Field(description="Block write bytes")

    # Configuration from database
    ports: List[Dict[str, Any]] = Field(default_factory=list, description="Port mappings")
    labels: Dict[str, str] = Field(default_factory=dict, description="Container labels")

    # Metadata
    last_snapshot_time: datetime = Field(description="Timestamp of latest snapshot")

    class Config:
        from_attributes = True


class ContainerMetrics(BaseModel):
    """Container resource metrics from database snapshots"""

    container_id: str = Field(description="Container ID")
    name: str = Field(description="Container name")

    # CPU metrics from database
    cpu_usage: Optional[float] = Field(description="CPU usage from snapshot")

    # Memory metrics from database  
    memory_usage_bytes: Optional[int] = Field(description="Memory usage in bytes")
    memory_limit_bytes: Optional[int] = Field(description="Memory limit in bytes")

    # Network metrics from database
    network_bytes_recv: Optional[int] = Field(description="Network bytes received")
    network_bytes_sent: Optional[int] = Field(description="Network bytes sent")

    # Block I/O metrics from database
    block_read_bytes: Optional[int] = Field(description="Block bytes read")
    block_write_bytes: Optional[int] = Field(description="Block bytes written")

    # Snapshot metadata
    snapshot_time: datetime = Field(description="Snapshot timestamp")

    class Config:
        from_attributes = True


class ContainerDetails(BaseModel):
    """Detailed container information from database snapshots"""

    device_id: UUID = Field(description="Device identifier")
    hostname: Optional[str] = Field(description="Device hostname")
    container_id: str = Field(description="Container ID")
    name: str = Field(description="Container name")
    image: Optional[str] = Field(description="Container image")

    # Status from latest snapshot
    status: Optional[str] = Field(description="Container status from database")

    # Resource usage from latest snapshot
    cpu_usage: Optional[float] = Field(description="CPU usage")
    memory_usage_bytes: Optional[int] = Field(description="Memory usage in bytes")
    memory_limit_bytes: Optional[int] = Field(description="Memory limit in bytes")

    # Network I/O from database
    network_bytes_sent: Optional[int] = Field(description="Network bytes sent")
    network_bytes_recv: Optional[int] = Field(description="Network bytes received")

    # Block I/O from database
    block_read_bytes: Optional[int] = Field(description="Block read bytes")
    block_write_bytes: Optional[int] = Field(description="Block write bytes")

    # Configuration from database
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    labels: Dict[str, str] = Field(default_factory=dict, description="Container labels")
    ports: List[Dict[str, Any]] = Field(default_factory=list, description="Port configurations")
    volumes: List[Dict[str, Any]] = Field(default_factory=list, description="Volume mounts")
    networks: List[Dict[str, Any]] = Field(default_factory=list, description="Network configurations")

    # Snapshot metadata
    snapshot_time: datetime = Field(description="Timestamp of data snapshot")

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
    """Container event from database snapshots"""

    device_id: UUID = Field(description="Device identifier")
    container_id: str = Field(description="Container ID")
    name: str = Field(description="Container name")
    status: Optional[str] = Field(description="Container status change")
    snapshot_time: datetime = Field(description="Event timestamp from snapshot")

    class Config:
        from_attributes = True


class ServiceDependency(BaseModel):
    """Service dependency information from database snapshots"""

    container_id: str = Field(description="Container ID")
    name: str = Field(description="Container name")
    service_name: Optional[str] = Field(description="Service name")
    dependencies: List[str] = Field(description="List of dependent services")
    dependents: List[str] = Field(description="List of services that depend on this")
    networks: List[Dict[str, Any]] = Field(default_factory=list, description="Network dependencies")
    volumes: List[Dict[str, Any]] = Field(default_factory=list, description="Volume dependencies")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment dependencies")

    class Config:
        from_attributes = True


# Specific Response Models following established patterns

class ContainerListResponse(APIResponse[PaginatedResponse[ContainerSummary]]):
    """Standardized paginated list response for containers"""
    pass


class ContainerDetailResponse(APIResponse[ContainerDetails]):
    """Standardized detail response for a single container"""
    pass


class ContainerMetricsResponse(APIResponse[ContainerMetrics]):
    """Response for container metrics queries"""
    pass


class ContainerStatsResponse(APIResponse[ContainerStats]):
    """Response for container statistics over time"""
    pass


class ContainerLogsResponse(APIResponse[ContainerLogs]):
    """Response for container logs queries"""
    pass


class ContainerEventsResponse(APIResponse[List[ContainerEvent]]):
    """Response for container events queries"""
    pass


class ServiceDependencyResponse(APIResponse[List[ServiceDependency]]):
    """Response for service dependency analysis"""
    pass


class ContainerOperationResponse(OperationResult[Dict[str, Any]]):
    """Response for container operations (start, stop, restart, etc.)"""
    
    def __init__(self, container_id: str, operation: str, success: bool, **kwargs):
        super().__init__(
            success=success,
            operation_type=f"container_{operation}",
            result={"container_id": container_id, "operation": operation},
            **kwargs
        )
