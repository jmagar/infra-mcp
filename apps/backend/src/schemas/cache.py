"""
Cache metadata Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from apps.backend.src.schemas.common import PaginatedResponse


class CacheMetadataBase(BaseModel):
    """Base schema for cache metadata"""

    cache_key: str = Field(..., min_length=1, max_length=255, description="Unique cache key")
    data_type: str = Field(..., min_length=1, max_length=50, description="Type of cached data")
    ttl_seconds: int = Field(..., gt=0, description="Time-to-live in seconds")
    data_size_bytes: int | None = Field(None, ge=0, description="Size of cached data in bytes")
    collection_method: str | None = Field(
        None, max_length=50, description="Method used to collect data"
    )
    command_hash: str | None = Field(
        None, max_length=64, description="Hash of command that generated data"
    )

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v):
        valid_types = [
            "system_metrics",
            "containers",
            "drive_health",
            "configuration",
            "zfs_status",
            "network_interfaces",
            "vm_status",
            "system_logs",
            "docker_networks",
            "backup_status",
            "system_updates",
            "device_info",
            "proxy_config",
            "service_status",
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Data type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("collection_method")
    @classmethod
    def validate_collection_method(cls, v):
        if v is None:
            return v
        valid_methods = ["ssh", "api", "polling", "webhook", "manual", "docker", "file"]
        if v.lower() not in valid_methods:
            raise ValueError(f"Collection method must be one of: {', '.join(valid_methods)}")
        return v.lower()

    @field_validator("command_hash")
    @classmethod
    def validate_command_hash(cls, v):
        if v is None:
            return v
        import re

        if not re.match(r"^[a-fA-F0-9]{32,64}$", v):
            raise ValueError("Command hash must be a valid hexadecimal hash (32-64 characters)")
        return v.lower()

    @field_validator("cache_key")
    @classmethod
    def validate_cache_key(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Cache key cannot be empty")
        # Validate cache key format (alphanumeric, underscores, hyphens, colons)
        import re

        if not re.match(r"^[a-zA-Z0-9_:-]+$", v):
            raise ValueError(
                "Cache key must contain only letters, numbers, underscores, hyphens, and colons"
            )
        return v.strip()

    @field_validator("ttl_seconds")
    @classmethod
    def validate_ttl_seconds(cls, v):
        if v <= 0:
            raise ValueError("TTL must be greater than 0 seconds")
        if v > 2592000:  # 30 days max
            raise ValueError("TTL cannot exceed 30 days (2,592,000 seconds)")
        return v

    @field_validator("data_size_bytes")
    @classmethod
    def validate_data_size_bytes(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError("Data size cannot be negative")
            if v > 536870912:  # 512MB max per cache entry
                raise ValueError("Data size cannot exceed 512MB (536,870,912 bytes)")
        return v

    @model_validator(mode="after")
    def validate_cache_metadata_consistency(self):
        """Cross-field validation for cache metadata consistency"""
        # Validate collection method vs command hash
        if self.collection_method == "ssh" and not self.command_hash:
            # SSH operations should typically have command hashes
            pass  # Allow but may warn in logs

        # Validate data type vs collection method compatibility
        if self.data_type in ["docker_networks", "containers"] and self.collection_method not in [
            "docker",
            "api",
            "ssh",
        ]:
            raise ValueError(
                f'Data type "{self.data_type}" should use docker, api, or ssh collection method'
            )

        # Validate TTL vs data type
        if self.data_type in ["system_metrics", "drive_health"] and self.ttl_seconds > 3600:
            # Metrics data should have shorter TTL
            pass  # Allow but may warn in logs

        return self


class CacheMetadataCreate(CacheMetadataBase):
    """Schema for creating new cache metadata"""

    device_id: UUID = Field(..., description="UUID of the device this cache entry relates to")
    created_at: Optional[datetime] = Field(None, description="When cache entry was created")
    last_accessed: Optional[datetime] = Field(None, description="When cache entry was last accessed")
    access_count: int = Field(default=0, ge=0, description="Number of times accessed")
    hit_count: int = Field(default=0, ge=0, description="Number of cache hits")
    miss_count: int = Field(default=0, ge=0, description="Number of cache misses")
    expires_at: Optional[datetime] = Field(None, description="When cache entry expires")
    source_operation: Optional[str] = Field(None, max_length=100, description="Source operation that created this cache")
    freshness_threshold: Optional[int] = Field(None, ge=0, description="Freshness threshold in seconds")
    compression_ratio: Optional[float] = Field(None, ge=0.1, le=100.0, description="Compression ratio achieved")
    cache_tier: str = Field(default="memory", description="Cache storage tier")
    eviction_policy: str = Field(default="lru", description="Eviction policy used")
    tags: Optional[List[str]] = Field(None, description="Tags for cache entry classification")


class CacheMetadataUpdate(BaseModel):
    """Schema for updating cache metadata"""

    ttl_seconds: int | None = Field(None, gt=0, description="New TTL in seconds")
    data_size_bytes: int | None = Field(None, ge=0, description="Updated data size")
    invalidated: bool | None = Field(None, description="Mark as invalidated")
    invalidation_reason: str | None = Field(
        None, max_length=100, description="Reason for invalidation"
    )


class CacheMetadataResponse(CacheMetadataBase):
    """Schema for cache metadata response data"""

    time: datetime = Field(description="Timestamp when metadata was recorded")
    device_id: UUID = Field(description="UUID of the device")
    created_at: datetime = Field(description="When cache entry was created")
    last_accessed: datetime = Field(description="When cache entry was last accessed")
    expires_at: datetime = Field(description="When cache entry expires")
    access_count: int = Field(description="Number of times accessed")
    hit_count: int = Field(description="Number of cache hits")
    miss_count: int = Field(description="Number of cache misses")
    source_operation: Optional[str] = Field(description="Source operation that created this cache")
    freshness_threshold: Optional[int] = Field(description="Freshness threshold in seconds")
    compression_ratio: Optional[float] = Field(description="Compression ratio achieved")
    cache_tier: str = Field(description="Cache storage tier")
    eviction_policy: str = Field(description="Eviction policy used")
    tags: Optional[List[str]] = Field(description="Tags for cache entry classification")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class CacheMetadataSummary(BaseModel):
    """Summary information for cache metadata"""

    time: datetime = Field(description="Timestamp when metadata was recorded")
    device_id: UUID = Field(description="UUID of the device")
    cache_key: str = Field(description="Unique cache key")
    data_type: str = Field(description="Type of cached data")
    data_size_bytes: Optional[int] = Field(description="Size of cached data")
    last_accessed: datetime = Field(description="When cache entry was last accessed")
    access_count: int = Field(description="Number of times accessed")
    hit_ratio: float = Field(description="Cache hit ratio as percentage")
    cache_tier: str = Field(description="Cache storage tier")
    is_expired: bool = Field(description="Whether cache entry has expired")

    class Config:
        from_attributes = True


class CacheMetadataList(PaginatedResponse[CacheMetadataSummary]):
    """Paginated list of cache metadata entries"""

    pass


class CacheAccessRecord(BaseModel):
    """Record of cache access operation"""

    cache_key: str = Field(description="Cache key accessed")
    device_id: UUID = Field(description="Device ID")
    accessed_at: datetime = Field(description="When access occurred")
    hit: bool = Field(description="Whether it was a cache hit")
    data_size_bytes: int | None = Field(description="Size of data returned")
    access_duration_ms: int | None = Field(description="Time taken to access data")


class CacheFilter(BaseModel):
    """Filter parameters for cache metadata queries"""

    device_ids: Optional[List[UUID]] = Field(None, description="Filter by device IDs")
    data_types: Optional[List[str]] = Field(None, description="Filter by data types")
    cache_tiers: Optional[List[str]] = Field(None, description="Filter by cache tiers")
    
    expired_only: Optional[bool] = Field(None, description="Show only expired entries")
    recently_accessed_only: Optional[bool] = Field(None, description="Show only recently accessed entries")
    low_hit_ratio_only: Optional[bool] = Field(None, description="Show only entries with low hit ratios")
    
    start_time: Optional[datetime] = Field(None, description="Filter entries from this time")
    end_time: Optional[datetime] = Field(None, description="Filter entries until this time")


class CacheMetrics(BaseModel):
    """Aggregated cache metrics"""
    
    total_entries: int = Field(description="Total number of cache entries")
    total_size_bytes: int = Field(description="Total size of cached data")
    total_accesses: int = Field(description="Total number of cache accesses")
    total_hits: int = Field(description="Total number of cache hits")
    total_misses: int = Field(description="Total number of cache misses")
    cache_hit_rate: float = Field(description="Cache hit rate as percentage")
    cache_miss_rate: float = Field(description="Cache miss rate as percentage")
    expired_entries: int = Field(description="Number of expired entries")
    avg_compression_ratio: Optional[float] = Field(description="Average compression ratio")
    entries_by_tier: dict[str, int] = Field(description="Entry counts by cache tier")
    entries_by_data_type: dict[str, int] = Field(description="Entry counts by data type")
    top_accessed_keys: List[dict[str, Any]] = Field(description="Most accessed cache keys")
    period_start: datetime = Field(description="Start of metrics period")
    period_end: datetime = Field(description="End of metrics period")


class CachePerformanceAnalysis(BaseModel):
    """Cache performance analysis"""
    
    data_type: Optional[str] = Field(description="Data type analyzed")
    analysis_period_hours: int = Field(description="Analysis period in hours")
    efficiency_score: float = Field(ge=0, le=100, description="Overall efficiency score")
    performance_by_tier: List[dict[str, Any]] = Field(description="Performance metrics by tier")
    hottest_keys: List[dict[str, Any]] = Field(description="Most accessed cache keys")
    coldest_keys: List[dict[str, Any]] = Field(description="Least accessed cache keys")
    inefficient_keys: List[dict[str, Any]] = Field(description="Keys with low hit rates")
    recommendations: List[str] = Field(description="Performance recommendations")


class CacheEfficiencyReport(BaseModel):
    """Cache efficiency report"""
    
    device_id: Optional[UUID] = Field(description="Device ID for device-specific report")
    report_period: str = Field(description="Report period")
    generated_at: datetime = Field(description="When report was generated")
    executive_summary: str = Field(description="Executive summary of cache performance")
    cache_health_score: float = Field(ge=0, le=100, description="Overall cache health score")
    overall_metrics: CacheMetrics = Field(description="Overall cache metrics")
    performance_analysis: CachePerformanceAnalysis = Field(description="Performance analysis")
    improvement_suggestions: List[str] = Field(description="Suggestions for improvement")



class CacheStatistics(BaseModel):
    """Cache performance statistics"""

    total_entries: int = Field(description="Total number of cache entries")
    valid_entries: int = Field(description="Number of valid cache entries")
    expired_entries: int = Field(description="Number of expired entries")
    invalidated_entries: int = Field(description="Number of invalidated entries")

    total_size_bytes: int = Field(description="Total size of all cached data")
    average_size_bytes: float = Field(description="Average size per entry")

    total_accesses: int = Field(description="Total number of cache accesses")
    cache_hit_rate: float = Field(description="Cache hit rate as percentage")

    most_accessed_entries: list[dict[str, Any]] = Field(
        description="Most frequently accessed entries"
    )
    largest_entries: list[dict[str, Any]] = Field(description="Largest cache entries by size")

    entries_by_data_type: dict[str, int] = Field(description="Entry counts by data type")
    entries_by_device: dict[str, int] = Field(description="Entry counts by device")

    average_ttl_seconds: float = Field(description="Average TTL across all entries")
    entries_expiring_soon: int = Field(description="Entries expiring within next hour")

    memory_efficiency_score: float = Field(
        ge=0, le=100, description="Memory efficiency score (0-100)"
    )
    recommendations: list[str] = Field(description="Cache optimization recommendations")


class CachePerformanceMetrics(BaseModel):
    """Cache performance metrics over time"""

    period_start: datetime = Field(description="Start of metrics period")
    period_end: datetime = Field(description="End of metrics period")

    total_requests: int = Field(description="Total cache requests")
    cache_hits: int = Field(description="Number of cache hits")
    cache_misses: int = Field(description="Number of cache misses")
    cache_hit_rate: float = Field(description="Hit rate as percentage")

    avg_access_time_ms: float = Field(description="Average cache access time")
    total_data_served_bytes: int = Field(description="Total data served from cache")

    evictions: int = Field(description="Number of cache evictions")
    invalidations: int = Field(description="Number of manual invalidations")
    expirations: int = Field(description="Number of natural expirations")

    memory_usage_bytes: int = Field(description="Current memory usage")
    memory_peak_bytes: int = Field(description="Peak memory usage in period")

    hot_keys: list[str] = Field(description="Most frequently accessed keys")
    cold_keys: list[str] = Field(description="Least frequently accessed keys")

    performance_trend: str = Field(description="Performance trend (improving, degrading, stable)")


class CacheMaintenanceReport(BaseModel):
    """Cache maintenance and cleanup report"""

    scan_started_at: datetime = Field(description="When maintenance scan started")
    scan_completed_at: datetime = Field(description="When maintenance scan completed")
    scan_duration_ms: int = Field(description="Duration of maintenance scan")

    entries_scanned: int = Field(description="Total entries scanned")
    expired_entries_found: int = Field(description="Expired entries found")
    invalid_entries_found: int = Field(description="Invalid entries found")
    orphaned_entries_found: int = Field(description="Orphaned entries found")

    entries_cleaned_up: int = Field(description="Entries actually cleaned up")
    cleanup_errors: int = Field(description="Number of cleanup errors")

    space_freed_bytes: int = Field(description="Space freed by cleanup")
    space_remaining_bytes: int = Field(description="Space still occupied")

    recommendations: list[str] = Field(description="Maintenance recommendations")
    next_maintenance_suggested: datetime = Field(description="When next maintenance is suggested")


class CacheInvalidationRequest(BaseModel):
    """Request to invalidate cache entries"""

    cache_keys: list[str] | None = Field(None, description="Specific cache keys to invalidate")
    device_ids: list[UUID] | None = Field(
        None, description="Invalidate all entries for these devices"
    )
    data_types: list[str] | None = Field(
        None, description="Invalidate all entries of these data types"
    )

    invalidation_reason: str = Field(..., min_length=1, description="Reason for invalidation")
    force: bool = Field(default=False, description="Force invalidation even if entries are fresh")

    # Advanced filters
    older_than_hours: int | None = Field(
        None, gt=0, description="Invalidate entries older than X hours"
    )
    larger_than_bytes: int | None = Field(
        None, gt=0, description="Invalidate entries larger than X bytes"
    )
    access_count_less_than: int | None = Field(
        None, ge=0, description="Invalidate entries with fewer accesses"
    )

    @field_validator("cache_keys")
    @classmethod
    def validate_cache_keys(cls, v):
        if v and len(v) > 1000:
            raise ValueError("Cannot invalidate more than 1000 cache keys at once")
        return v

    @field_validator("invalidation_reason")
    @classmethod
    def validate_invalidation_reason(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Invalidation reason cannot be empty")
        if len(v) > 500:
            raise ValueError("Invalidation reason cannot exceed 500 characters")
        return v.strip()

    @field_validator("older_than_hours")
    @classmethod
    def validate_older_than_hours(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError("older_than_hours must be greater than 0")
            if v > 8760:  # 1 year max
                raise ValueError("older_than_hours cannot exceed 8760 hours (1 year)")
        return v

    @field_validator("larger_than_bytes")
    @classmethod
    def validate_larger_than_bytes(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError("larger_than_bytes must be greater than 0")
            if v > 1073741824:  # 1GB max
                raise ValueError("larger_than_bytes cannot exceed 1GB")
        return v

    @model_validator(mode="after")
    def validate_invalidation_request_consistency(self):
        """Cross-field validation for cache invalidation request consistency"""
        # Must specify at least one invalidation criteria
        criteria_count = sum(
            [
                bool(self.cache_keys),
                bool(self.device_ids),
                bool(self.data_types),
                bool(self.older_than_hours),
                bool(self.larger_than_bytes),
                bool(self.access_count_less_than is not None),
            ]
        )

        if criteria_count == 0:
            raise ValueError("Must specify at least one invalidation criteria")

        # Validate force flag usage
        if self.force and not any([self.cache_keys, self.device_ids, self.data_types]):
            raise ValueError(
                "Force invalidation should specify specific cache keys, devices, or data types"
            )

        return self


class CacheInvalidationResponse(BaseModel):
    """Response for cache invalidation operation"""

    invalidation_id: UUID = Field(description="Unique invalidation operation ID")
    requested_at: datetime = Field(description="When invalidation was requested")
    completed_at: datetime = Field(description="When invalidation completed")

    total_entries_found: int = Field(description="Total entries matching criteria")
    entries_invalidated: int = Field(description="Entries successfully invalidated")
    entries_failed: int = Field(description="Entries that failed to invalidate")

    space_freed_bytes: int = Field(description="Space freed by invalidation")

    errors: list[str] = Field(description="Any errors during invalidation")
    performance_impact: dict[str, Any] = Field(description="Performance impact assessment")


class CacheWarmupRequest(BaseModel):
    """Request to warm up cache with fresh data"""

    device_ids: list[UUID] | None = Field(None, description="Devices to warm up cache for")
    data_types: list[str] = Field(..., min_length=1, description="Data types to cache")

    priority: str = Field(default="normal", description="Warmup priority")
    force_refresh: bool = Field(default=False, description="Force refresh even if cache exists")
    parallel_workers: int = Field(default=5, ge=1, le=20, description="Number of parallel workers")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        valid_priorities = ["low", "normal", "high", "critical"]
        if v.lower() not in valid_priorities:
            raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
        return v.lower()

    @field_validator("data_types")
    @classmethod
    def validate_data_types(cls, v):
        if not v:
            raise ValueError("At least one data type must be specified for warmup")
        if len(v) > 20:
            raise ValueError("Cannot warm up more than 20 data types at once")
        return v

    @field_validator("device_ids")
    @classmethod
    def validate_device_ids(cls, v):
        if v and len(v) > 100:
            raise ValueError("Cannot warm up cache for more than 100 devices at once")
        return v

    @field_validator("parallel_workers")
    @classmethod
    def validate_parallel_workers(cls, v):
        if v < 1 or v > 20:
            raise ValueError("Parallel workers must be between 1 and 20")
        return v

    @model_validator(mode="after")
    def validate_warmup_request_consistency(self):
        """Cross-field validation for cache warmup request consistency"""
        # Validate priority vs parallel workers
        if self.priority == "critical" and self.parallel_workers < 3:
            raise ValueError("Critical priority warmup should use at least 3 parallel workers")
        if self.priority == "low" and self.parallel_workers > 10:
            raise ValueError("Low priority warmup should not use more than 10 parallel workers")

        # Validate data types vs device constraints
        if len(self.data_types) > 10 and self.device_ids and len(self.device_ids) > 20:
            raise ValueError(
                "Cannot warm up more than 10 data types for more than 20 devices simultaneously"
            )

        return self


class CacheWarmupResponse(BaseModel):
    """Response for cache warmup operation"""

    warmup_id: UUID = Field(description="Unique warmup operation ID")
    started_at: datetime = Field(description="When warmup started")
    completed_at: datetime | None = Field(description="When warmup completed")

    status: str = Field(description="Warmup status (running, completed, failed)")
    progress_percentage: float = Field(ge=0, le=100, description="Progress percentage")

    devices_processed: int = Field(description="Number of devices processed")
    cache_entries_created: int = Field(description="Cache entries created")
    cache_entries_updated: int = Field(description="Cache entries updated")

    total_data_cached_bytes: int = Field(description="Total data cached")
    average_collection_time_ms: float = Field(description="Average time to collect data")

    errors: list[str] = Field(description="Any errors during warmup")
    estimated_completion: datetime | None = Field(description="Estimated completion time")
