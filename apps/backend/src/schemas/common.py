"""
Common Pydantic schemas used across the application.
"""

from datetime import UTC, datetime
from typing import Any, TypeVar, Generic
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class DeviceStatus(str, Enum):
    """Device status enumeration"""

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class LogLevel(str, Enum):
    """System log level enumeration"""

    EMERGENCY = "emergency"
    ALERT = "alert"
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"
    INFO = "info"
    DEBUG = "debug"


class HealthStatus(str, Enum):
    """Health status enumeration"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints"""

    page: int = Field(default=1, ge=1, description="Page number (starts from 1)")
    page_size: int = Field(default=50, ge=1, le=1000, description="Number of items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.page_size


class TimeRangeParams(BaseModel):
    """Time range parameters for time-series queries"""

    start_time: datetime | None = Field(
        default=None, description="Start time for time-series data (ISO 8601 format)"
    )
    end_time: datetime | None = Field(
        default=None, description="End time for time-series data (ISO 8601 format)"
    )

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v: datetime | None, info: Any) -> datetime | None:
        if v and info.data.get("start_time"):
            if v <= info.data["start_time"]:
                raise ValueError("end_time must be after start_time")
        return v


class APIResponse(BaseModel, Generic[T]):
    """Generic API response wrapper"""

    success: bool = Field(description="Whether the request was successful")
    data: T | None = Field(description="Response data")
    message: str | None = Field(description="Response message")
    errors: list[str] | None = Field(description="List of errors if any")

    class Config:
        arbitrary_types_allowed = True


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""

    items: list[T] = Field(description="List of items")
    total_count: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there are more pages")
    has_previous: bool = Field(description="Whether there are previous pages")

    class Config:
        arbitrary_types_allowed = True


class ErrorResponse(BaseModel):
    """Error response schema"""

    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: dict[str, Any] | None = Field(description="Additional error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Error timestamp")


class HealthCheckResponse(BaseModel):
    """Health check response schema"""

    status: str = Field(description="Overall health status")
    version: str = Field(description="Application version")
    environment: str = Field(description="Environment (development/production)")
    database: dict[str, Any] = Field(description="Database health information")
    services: dict[str, str] = Field(description="Service status map")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Health check timestamp"
    )


class DatabaseHealthInfo(BaseModel):
    """Database health information schema"""

    status: str = Field(description="Database status (healthy/unhealthy)")
    connection_pool: dict[str, int] = Field(description="Connection pool statistics")
    timescaledb_info: dict[str, int] = Field(description="TimescaleDB information")
    table_counts: dict[str, Any] = Field(description="Table row counts")
    performance_metrics: dict[str, Any] = Field(description="Database performance metrics")


class DeviceFilter(BaseModel):
    """Device filtering parameters"""

    hostname: str | None = Field(description="Filter by hostname (partial match)")
    device_type: str | None = Field(description="Filter by device type")
    status: DeviceStatus | None = Field(description="Filter by device status")
    monitoring_enabled: bool | None = Field(description="Filter by monitoring status")
    tags: dict[str, str] | None = Field(description="Filter by tags (key-value pairs)")


class TimeSeriesAggregation(str, Enum):
    """Time-series aggregation methods"""

    AVG = "avg"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"


class TimeSeriesInterval(str, Enum):
    """Time-series aggregation intervals"""

    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    HOUR = "1h"
    SIX_HOURS = "6h"
    DAY = "1d"
    WEEK = "1w"


class AggregationParams(BaseModel):
    """Time-series aggregation parameters"""

    interval: TimeSeriesInterval = Field(
        default=TimeSeriesInterval.HOUR, description="Aggregation time interval"
    )
    aggregation: TimeSeriesAggregation = Field(
        default=TimeSeriesAggregation.AVG, description="Aggregation method"
    )


class MetricFilter(BaseModel):
    """Metric filtering parameters"""

    device_ids: list[UUID] | None = Field(description="List of device IDs to include")
    metric_names: list[str] | None = Field(description="List of specific metrics to include")
    threshold_min: float | None = Field(description="Minimum threshold value")
    threshold_max: float | None = Field(description="Maximum threshold value")


class SortParams(BaseModel):
    """Sorting parameters"""

    sort_by: str = Field(default="time", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class BulkOperationResponse(BaseModel):
    """Bulk operation response"""

    total_processed: int = Field(description="Total number of items processed")
    successful: int = Field(description="Number of successful operations")
    failed: int = Field(description="Number of failed operations")
    errors: list[str] = Field(description="List of error messages")
    duration_ms: int = Field(description="Operation duration in milliseconds")


class StatusResponse(BaseModel):
    """Simple status response"""

    status: str = Field(description="Operation status")
    message: str | None = Field(description="Status message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Status timestamp")


class CreatedResponse(BaseModel, Generic[T]):
    """Response for resource creation"""

    id: str = Field(description="ID of created resource")
    resource_type: str = Field(description="Type of resource created")
    data: T | None = Field(description="Created resource data")
    message: str = Field(default="Resource created successfully", description="Success message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")

    class Config:
        arbitrary_types_allowed = True


class UpdatedResponse(BaseModel, Generic[T]):
    """Response for resource updates"""

    id: str = Field(description="ID of updated resource")
    resource_type: str = Field(description="Type of resource updated")
    data: T | None = Field(description="Updated resource data")
    changes: dict[str, Any] = Field(description="Fields that were changed")
    message: str = Field(default="Resource updated successfully", description="Success message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Update timestamp")

    class Config:
        arbitrary_types_allowed = True


class DeletedResponse(BaseModel):
    """Response for resource deletion"""

    id: str = Field(description="ID of deleted resource")
    resource_type: str = Field(description="Type of resource deleted")
    message: str = Field(default="Resource deleted successfully", description="Success message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Deletion timestamp")


class ValidationErrorResponse(BaseModel):
    """Detailed validation error response"""

    error_type: str = Field(default="validation_error", description="Type of validation error")
    message: str = Field(description="Error message")
    field_errors: list[dict[str, Any]] = Field(description="Field-specific validation errors")
    error_count: int = Field(description="Total number of validation errors")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Error timestamp")


class HealthMetrics(BaseModel):
    """Health metrics for services and components"""

    cpu_usage_percent: float | None = Field(description="CPU usage percentage")
    memory_usage_percent: float | None = Field(description="Memory usage percentage")
    disk_usage_percent: float | None = Field(description="Disk usage percentage")
    network_latency_ms: float | None = Field(description="Network latency in milliseconds")
    active_connections: int | None = Field(description="Number of active connections")
    error_rate_percent: float | None = Field(description="Error rate percentage")
    uptime_seconds: int | None = Field(description="Service uptime in seconds")
    last_health_check: datetime | None = Field(description="Last health check timestamp")


class OperationResult(BaseModel, Generic[T]):
    """Generic operation result wrapper"""

    success: bool = Field(description="Whether operation was successful")
    operation_id: str | None = Field(description="Unique operation identifier")
    operation_type: str = Field(description="Type of operation performed")
    result: T | None = Field(description="Operation result data")
    error_message: str | None = Field(description="Error message if operation failed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    execution_time_ms: int | None = Field(description="Operation execution time in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Operation timestamp")

    class Config:
        arbitrary_types_allowed = True


class SearchParams(BaseModel):
    """Search parameters for text search operations"""

    query: str = Field(min_length=1, max_length=1000, description="Search query string")
    field: str | None = Field(description="Specific field to search in")
    case_sensitive: bool = Field(default=False, description="Whether search is case sensitive")
    exact_match: bool = Field(default=False, description="Whether to match exact phrase")
    include_metadata: bool = Field(
        default=False, description="Whether to include metadata in results"
    )


class RateLimitInfo(BaseModel):
    """Rate limiting information"""

    limit: int = Field(description="Rate limit (requests per window)")
    remaining: int = Field(description="Remaining requests in current window")
    reset_time: datetime = Field(description="When the rate limit window resets")
    window_seconds: int = Field(description="Rate limit window duration in seconds")


class SystemInfo(BaseModel):
    """System information response"""

    hostname: str = Field(description="System hostname")
    platform: str = Field(description="Operating system platform")
    architecture: str = Field(description="System architecture")
    python_version: str = Field(description="Python version")
    app_version: str = Field(description="Application version")
    startup_time: datetime = Field(description="Application startup time")
    current_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Current system time"
    )
