"""
Virtual Machine-related Pydantic schemas for request/response validation.
"""

from datetime import UTC, datetime

from typing import Optional, List, Any
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from apps.backend.src.schemas.common import PaginatedResponse


class VMStatusBase(BaseModel):
    """Base VM status schema with common fields"""

    vm_id: str = Field(..., min_length=1, max_length=255, description="Virtual machine ID")
    vm_name: str = Field(..., min_length=1, max_length=255, description="Virtual machine name")
    hypervisor: str = Field(..., max_length=100, description="Hypervisor type")
    status: str = Field(..., description="VM status")
    vcpus: int | None = Field(None, ge=1, description="Number of virtual CPUs")
    memory_mb: int | None = Field(None, ge=1, description="Allocated memory in MB")
    memory_usage_mb: int | None = Field(None, ge=0, description="Current memory usage in MB")
    cpu_usage_percent: Decimal | None = Field(
        None, ge=0, le=100, description="CPU usage percentage"
    )
    disk_usage_bytes: int | None = Field(None, ge=0, description="Disk usage in bytes")
    network_bytes_sent: int | None = Field(None, ge=0, description="Network bytes sent")
    network_bytes_recv: int | None = Field(None, ge=0, description="Network bytes received")
    uptime_seconds: int | None = Field(None, ge=0, description="VM uptime in seconds")
    boot_time: datetime | None = Field(None, description="VM boot time")
    config: dict[str, Any] = Field(default_factory=dict, description="VM configuration")

    @field_validator("hypervisor")
    @classmethod
    def validate_hypervisor(cls, v: str) -> str:
        valid_hypervisors = [
            "kvm",
            "qemu",
            "xen",
            "vmware",
            "virtualbox",
            "hyper-v",
            "bhyve",
            "lxc",
            "docker",
            "openvz",
        ]
        if v.lower() not in valid_hypervisors:
            raise ValueError(f"Hypervisor must be one of: {', '.join(valid_hypervisors)}")
        return v.lower()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [
            "running",
            "paused",
            "shutdown",
            "shutoff",
            "crashed",
            "dying",
            "pmsuspended",
            "starting",
            "stopping",
        ]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()

    @field_validator("vm_name")
    @classmethod
    def validate_vm_name(cls, v: str) -> str:
        # Basic VM name validation
        if not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("VM name contains invalid characters")
        return v


class VMStatusCreate(VMStatusBase):
    """Schema for creating a new VM status record"""

    device_id: UUID = Field(..., description="Device UUID")


class VMStatusResponse(VMStatusBase):
    """Schema for VM status response data"""

    time: datetime = Field(description="Timestamp of the VM status record")
    device_id: UUID = Field(description="Device UUID")

    # Computed fields
    memory_usage_percent: float | None = Field(None, description="Memory usage percentage")
    uptime_hours: float | None = Field(None, description="Uptime in hours")
    cpu_cores_used: float | None = Field(None, description="CPU cores effectively used")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
            Decimal: lambda v: float(v),
        }


class VMStatusList(PaginatedResponse[VMStatusResponse]):
    """Paginated list of VM status records"""

    pass


class VMSummary(BaseModel):
    """VM summary for dashboard"""

    device_id: UUID
    vm_id: str
    vm_name: str
    hypervisor: str
    status: str
    vcpus: int | None
    memory_mb: int | None
    cpu_usage_percent: float | None
    memory_usage_percent: float | None
    uptime_hours: float | None
    network_active: bool = Field(description="Whether VM has active network traffic")
    health_status: str = Field(description="Overall VM health status")
    last_updated: datetime = Field(description="Last status update")

    class Config:
        from_attributes = True


class VMHealthOverview(BaseModel):
    """VM health overview across all devices"""

    total_vms: int = Field(description="Total number of VMs")
    running_vms: int = Field(description="Number of running VMs")
    paused_vms: int = Field(description="Number of paused VMs")
    shutdown_vms: int = Field(description="Number of shutdown VMs")
    crashed_vms: int = Field(description="Number of crashed VMs")
    total_vcpus: int = Field(description="Total allocated vCPUs")
    total_memory_gb: float = Field(description="Total allocated memory in GB")
    average_cpu_usage: float = Field(description="Average CPU usage across all VMs")
    average_memory_usage: float = Field(description="Average memory usage across all VMs")
    vms_by_hypervisor: dict[str, int] = Field(description="VM count by hypervisor")
    vms_by_device: dict[str, int] = Field(description="VM count by device")
    high_resource_vms: list[str] = Field(description="VMs with high resource usage")
    problematic_vms: list[str] = Field(description="VMs with issues")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Report timestamp")


class VMPerformanceMetrics(BaseModel):
    """VM performance metrics summary"""

    device_id: UUID
    vm_id: str
    vm_name: str
    current_metrics: dict[str, Any] = Field(description="Current VM metrics")
    cpu_usage_trend: list[float] = Field(description="CPU usage trend over time")
    memory_usage_trend: list[float] = Field(description="Memory usage trend over time")
    network_throughput_mbps: float | None = Field(description="Network throughput in Mbps")
    disk_iops: float | None = Field(description="Disk I/O operations per second")
    performance_score: float | None = Field(description="Overall performance score")
    resource_efficiency: float | None = Field(description="Resource efficiency ratio")
    alerts: list[str] = Field(description="Active VM alerts")
    recommendations: list[str] = Field(description="Performance recommendations")
    last_updated: datetime = Field(description="Last metrics update")

    class Config:
        from_attributes = True


class VMResourceAllocation(BaseModel):
    """VM resource allocation configuration"""

    vm_id: str
    vm_name: str
    vcpus: int = Field(ge=1, description="Number of virtual CPUs")
    memory_mb: int = Field(ge=1, description="Memory allocation in MB")
    disk_gb: int | None = Field(None, ge=1, description="Disk allocation in GB")
    network_interfaces: list[dict[str, str]] = Field(description="Network interface configurations")
    cpu_shares: int | None = Field(None, description="CPU shares/priority")
    memory_balloon: bool | None = Field(None, description="Memory ballooning enabled")
    cpu_limit_percent: int | None = Field(None, ge=1, le=100, description="CPU limit percentage")
    memory_limit_mb: int | None = Field(None, description="Memory limit in MB")

    @field_validator("vcpus")
    @classmethod
    def validate_vcpus(cls, v: int) -> int:
        if v > 128:  # Reasonable upper limit
            raise ValueError("vCPUs cannot exceed 128")
        return v

    @field_validator("memory_mb")
    @classmethod
    def validate_memory_mb(cls, v: int) -> int:
        if v < 64:  # Minimum viable memory
            raise ValueError("Memory cannot be less than 64MB")
        if v > 1048576:  # 1TB limit
            raise ValueError("Memory cannot exceed 1TB")
        return v


class VMOperation(BaseModel):
    """VM operation request/response"""

    vm_id: str = Field(description="VM ID")
    operation: str = Field(description="Operation type")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    initiated_by: str | None = Field(None, description="User who initiated operation")
    initiated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Operation start time"
    )

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        valid_operations = [
            "start",
            "stop",
            "restart",
            "pause",
            "resume",
            "suspend",
            "snapshot",
            "clone",
            "migrate",
            "backup",
            "restore",
        ]
        if v.lower() not in valid_operations:
            raise ValueError(f"Operation must be one of: {', '.join(valid_operations)}")
        return v.lower()


class VMOperationResult(BaseModel):
    """VM operation result"""

    vm_id: str
    operation: str
    status: str = Field(description="Operation status (success/failed/pending)")
    message: str | None = Field(description="Operation message")
    error_details: str | None = Field(description="Error details if failed")
    duration_seconds: float | None = Field(description="Operation duration")
    result_data: dict[str, Any] = Field(default_factory=dict, description="Operation result data")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Completion time")

    class Config:
        from_attributes = True


class VMSnapshot(BaseModel):
    """VM snapshot information"""

    snapshot_id: str = Field(description="Snapshot ID")
    vm_id: str = Field(description="VM ID")
    vm_name: str = Field(description="VM name")
    snapshot_name: str = Field(description="Snapshot name")
    description: str | None = Field(description="Snapshot description")
    created_at: datetime = Field(description="Snapshot creation time")
    size_bytes: int | None = Field(description="Snapshot size in bytes")
    memory_included: bool = Field(description="Whether memory state is included")
    disk_included: bool = Field(description="Whether disk state is included")
    parent_snapshot: str | None = Field(description="Parent snapshot ID")
    is_current: bool = Field(description="Whether this is the current snapshot")

    class Config:
        from_attributes = True


class VMFilter(BaseModel):
    """VM filtering parameters"""

    device_ids: list[UUID] | None = Field(description="Filter by device IDs")
    hypervisors: list[str] | None = Field(description="Filter by hypervisor types")
    statuses: list[str] | None = Field(description="Filter by VM statuses")
    min_vcpus: int | None = Field(description="Minimum vCPU count")
    max_vcpus: int | None = Field(description="Maximum vCPU count")
    min_memory_mb: int | None = Field(description="Minimum memory in MB")
    max_memory_mb: int | None = Field(description="Maximum memory in MB")
    high_cpu_usage: bool | None = Field(description="Filter VMs with high CPU usage")
    high_memory_usage: bool | None = Field(description="Filter VMs with high memory usage")
    vm_name_pattern: str | None = Field(description="VM name pattern (regex)")


class VMBackup(BaseModel):
    """VM backup information"""

    backup_id: str = Field(description="Backup ID")
    vm_id: str = Field(description="VM ID")
    vm_name: str = Field(description="VM name")
    backup_type: str = Field(description="Backup type (full/incremental/differential)")
    backup_location: str = Field(description="Backup storage location")
    created_at: datetime = Field(description="Backup creation time")
    size_bytes: int = Field(description="Backup size in bytes")
    compression_ratio: float | None = Field(description="Compression ratio")
    verification_status: str = Field(description="Backup verification status")
    retention_days: int | None = Field(description="Retention period in days")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Backup metadata")

    class Config:
        from_attributes = True
