"""
ZFS-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from apps.backend.src.schemas.common import PaginatedResponse, TimeRangeParams


class ZFSStatusBase(BaseModel):
    """Base ZFS status schema with common fields"""

    pool_name: str = Field(..., min_length=1, max_length=255, description="ZFS pool name")
    dataset_name: Optional[str] = Field(None, max_length=255, description="ZFS dataset name")
    pool_state: str = Field(..., description="Pool state (ONLINE, DEGRADED, FAULTED, etc.)")
    pool_health: str = Field(..., description="Pool health status")
    capacity_bytes: Optional[int] = Field(None, ge=0, description="Total pool capacity in bytes")
    allocated_bytes: Optional[int] = Field(None, ge=0, description="Allocated space in bytes")
    free_bytes: Optional[int] = Field(None, ge=0, description="Free space in bytes")
    fragmentation_percent: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Fragmentation percentage"
    )
    dedup_ratio: Optional[Decimal] = Field(None, ge=1, description="Deduplication ratio")
    compression_ratio: Optional[Decimal] = Field(None, ge=1, description="Compression ratio")
    scrub_state: Optional[str] = Field(
        None, description="Scrub state (none, scanning, finished, etc.)"
    )
    scrub_progress_percent: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Scrub progress percentage"
    )
    scrub_errors: int = Field(default=0, ge=0, description="Number of scrub errors")
    last_scrub: Optional[datetime] = Field(None, description="Last scrub timestamp")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional ZFS properties"
    )

    @field_validator("pool_state")
    @classmethod
    def validate_pool_state(cls, v):
        valid_states = ["ONLINE", "DEGRADED", "FAULTED", "OFFLINE", "UNAVAIL", "REMOVED"]
        if v.upper() not in valid_states:
            raise ValueError(f"Pool state must be one of: {', '.join(valid_states)}")
        return v.upper()

    @field_validator("scrub_state")
    @classmethod
    def validate_scrub_state(cls, v):
        if v is not None:
            valid_states = ["none", "scanning", "finished", "canceled", "suspended"]
            if v.lower() not in valid_states:
                raise ValueError(f"Scrub state must be one of: {', '.join(valid_states)}")
            return v.lower()
        return v


class ZFSStatusCreate(ZFSStatusBase):
    """Schema for creating a new ZFS status record"""

    device_id: UUID = Field(..., description="Device UUID")


class ZFSStatusResponse(ZFSStatusBase):
    """Schema for ZFS status response data"""

    time: datetime = Field(description="Timestamp of the status record")
    device_id: UUID = Field(description="Device UUID")

    # Computed fields
    usage_percent: Optional[float] = Field(None, description="Storage usage percentage")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
            Decimal: lambda v: float(v),
        }


class ZFSStatusList(PaginatedResponse[ZFSStatusResponse]):
    """Paginated list of ZFS status records"""

    pass


class ZFSSnapshotBase(BaseModel):
    """Base ZFS snapshot schema with common fields"""

    dataset_name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    snapshot_name: str = Field(..., min_length=1, max_length=255, description="Snapshot name")
    creation_time: datetime = Field(..., description="Snapshot creation time")
    used_bytes: Optional[int] = Field(None, ge=0, description="Space used by snapshot in bytes")
    referenced_bytes: Optional[int] = Field(
        None, ge=0, description="Space referenced by snapshot in bytes"
    )
    properties: Dict[str, Any] = Field(default_factory=dict, description="Snapshot properties")

    @field_validator("snapshot_name")
    @classmethod
    def validate_snapshot_name(cls, v):
        # Basic validation - snapshots typically have @ symbol
        if "@" not in v:
            raise ValueError("Snapshot name should contain '@' symbol")
        return v


class ZFSSnapshotCreate(ZFSSnapshotBase):
    """Schema for creating a new ZFS snapshot record"""

    device_id: UUID = Field(..., description="Device UUID")


class ZFSSnapshotResponse(ZFSSnapshotBase):
    """Schema for ZFS snapshot response data"""

    time: datetime = Field(description="Timestamp when snapshot was recorded")
    device_id: UUID = Field(description="Device UUID")

    # Computed fields
    age_days: Optional[int] = Field(None, description="Age of snapshot in days")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class ZFSSnapshotList(PaginatedResponse[ZFSSnapshotResponse]):
    """Paginated list of ZFS snapshots"""

    pass


class ZFSPoolSummary(BaseModel):
    """ZFS pool summary for dashboard"""

    device_id: UUID
    pool_name: str
    pool_state: str
    pool_health: str
    total_capacity_gb: Optional[float] = Field(description="Total capacity in GB")
    used_capacity_gb: Optional[float] = Field(description="Used capacity in GB")
    usage_percent: Optional[float] = Field(description="Usage percentage")
    fragmentation_percent: Optional[float] = Field(description="Fragmentation percentage")
    dedup_ratio: Optional[float] = Field(description="Deduplication ratio")
    compression_ratio: Optional[float] = Field(description="Compression ratio")
    last_scrub: Optional[datetime] = Field(description="Last scrub timestamp")
    scrub_errors: int = Field(description="Number of scrub errors")
    dataset_count: Optional[int] = Field(description="Number of datasets in pool")
    snapshot_count: Optional[int] = Field(description="Number of snapshots in pool")
    last_updated: datetime = Field(description="Last update timestamp")

    class Config:
        from_attributes = True


class ZFSHealthOverview(BaseModel):
    """ZFS health overview across all devices"""

    total_pools: int = Field(description="Total number of ZFS pools")
    healthy_pools: int = Field(description="Number of healthy pools")
    degraded_pools: int = Field(description="Number of degraded pools")
    faulted_pools: int = Field(description="Number of faulted pools")
    total_capacity_tb: float = Field(description="Total ZFS capacity in TB")
    used_capacity_tb: float = Field(description="Used ZFS capacity in TB")
    overall_usage_percent: float = Field(description="Overall usage percentage")
    pools_by_device: Dict[str, int] = Field(description="Pool count by device")
    health_by_device: Dict[str, str] = Field(description="Health status by device")
    recent_scrub_errors: int = Field(description="Recent scrub errors count")
    overdue_scrubs: int = Field(description="Number of pools with overdue scrubs")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC), description="Report timestamp")


class ZFSDatasetInfo(BaseModel):
    """ZFS dataset information"""

    name: str = Field(description="Dataset name")
    pool_name: str = Field(description="Parent pool name")
    type: str = Field(description="Dataset type (filesystem, volume, snapshot)")
    used_bytes: Optional[int] = Field(description="Space used by dataset")
    available_bytes: Optional[int] = Field(description="Available space")
    referenced_bytes: Optional[int] = Field(description="Space referenced by dataset")
    compression: Optional[str] = Field(description="Compression algorithm")
    dedup: Optional[str] = Field(description="Deduplication setting")
    encryption: Optional[str] = Field(description="Encryption status")
    mountpoint: Optional[str] = Field(description="Mount point for filesystems")
    quota: Optional[int] = Field(description="Dataset quota in bytes")
    reservation: Optional[int] = Field(description="Dataset reservation in bytes")
    properties: Dict[str, str] = Field(default_factory=dict, description="Dataset properties")


class ZFSIntegrityCheck(BaseModel):
    """ZFS integrity check result"""

    device_id: UUID
    pool_name: str
    check_type: str = Field(description="Type of integrity check (scrub, verify)")
    status: str = Field(description="Check status (running, completed, failed)")
    start_time: datetime = Field(description="Check start time")
    end_time: Optional[datetime] = Field(description="Check end time")
    duration_seconds: Optional[int] = Field(description="Check duration")
    bytes_processed: Optional[int] = Field(description="Bytes processed during check")
    errors_found: int = Field(default=0, description="Number of errors found")
    errors_repaired: int = Field(default=0, description="Number of errors repaired")
    error_details: List[str] = Field(default_factory=list, description="Detailed error information")

    class Config:
        from_attributes = True


class ZFSFilter(BaseModel):
    """ZFS filtering parameters"""

    device_ids: Optional[List[UUID]] = Field(description="Filter by device IDs")
    pool_names: Optional[List[str]] = Field(description="Filter by pool names")
    pool_states: Optional[List[str]] = Field(description="Filter by pool states")
    health_status: Optional[List[str]] = Field(description="Filter by health status")
    min_capacity_gb: Optional[float] = Field(description="Minimum capacity in GB")
    max_usage_percent: Optional[float] = Field(description="Maximum usage percentage")
    has_scrub_errors: Optional[bool] = Field(description="Filter pools with scrub errors")
    overdue_scrub_days: Optional[int] = Field(description="Filter pools with overdue scrubs")


class ZFSAggregatedMetrics(BaseModel):
    """Aggregated ZFS metrics for time-series analysis"""

    time_bucket: datetime = Field(description="Time bucket for aggregation")
    device_id: UUID = Field(description="Device ID")
    pool_name: str = Field(description="Pool name")
    avg_usage_percent: Optional[float] = Field(description="Average usage percentage")
    max_usage_percent: Optional[float] = Field(description="Maximum usage percentage")
    avg_fragmentation_percent: Optional[float] = Field(description="Average fragmentation")
    dedup_ratio: Optional[float] = Field(description="Deduplication ratio")
    compression_ratio: Optional[float] = Field(description="Compression ratio")
    scrub_error_count: int = Field(description="Total scrub errors in period")

    class Config:
        from_attributes = True
