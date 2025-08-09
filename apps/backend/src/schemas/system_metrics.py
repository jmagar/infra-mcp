"""
System metrics Pydantic schemas for request/response validation.
"""

from datetime import UTC, datetime

from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from apps.backend.src.schemas.common import AggregationParams, PaginatedResponse, TimeRangeParams


class SystemMetricBase(BaseModel):
    """Base system metric schema"""

    device_id: UUID = Field(description="Device identifier")

    # CPU metrics
    cpu_usage_percent: float | None = Field(
        None, ge=0, le=100, description="CPU usage percentage"
    )

    # Memory metrics
    memory_usage_percent: float | None = Field(
        None, ge=0, le=100, description="Memory usage percentage"
    )
    memory_total_bytes: int | None = Field(None, ge=0, description="Total memory in bytes")
    memory_available_bytes: int | None = Field(
        None, ge=0, description="Available memory in bytes"
    )

    # Load average metrics
    load_average_1m: float | None = Field(None, ge=0, description="1-minute load average")
    load_average_5m: float | None = Field(None, ge=0, description="5-minute load average")
    load_average_15m: float | None = Field(None, ge=0, description="15-minute load average")

    # Disk metrics
    disk_usage_percent: float | None = Field(
        None, ge=0, le=100, description="Disk usage percentage"
    )
    disk_total_bytes: int | None = Field(None, ge=0, description="Total disk space in bytes")
    disk_available_bytes: int | None = Field(
        None, ge=0, description="Available disk space in bytes"
    )

    # Network metrics
    network_bytes_sent: int | None = Field(None, ge=0, description="Network bytes sent")
    network_bytes_recv: int | None = Field(None, ge=0, description="Network bytes received")

    # Process and uptime metrics
    uptime_seconds: int | None = Field(None, ge=0, description="System uptime in seconds")
    process_count: int | None = Field(None, ge=0, description="Number of running processes")

    # Additional metrics
    additional_metrics: dict[str, Any] = Field(
        default_factory=dict, description="Additional metric data"
    )

    @field_validator("memory_available_bytes")
    @classmethod
    def validate_memory_available(cls, v: int | None, info: Any) -> int | None:
        if v is not None and "memory_total_bytes" in info.data and info.data["memory_total_bytes"]:
            if v > info.data["memory_total_bytes"]:
                raise ValueError("Available memory cannot exceed total memory")
        return v

    @field_validator("disk_available_bytes")
    @classmethod
    def validate_disk_available(cls, v: int | None, info: Any) -> int | None:
        if v is not None and "disk_total_bytes" in info.data and info.data["disk_total_bytes"]:
            if v > info.data["disk_total_bytes"]:
                raise ValueError("Available disk space cannot exceed total disk space")
        return v


class SystemMetricCreate(SystemMetricBase):
    """Schema for creating system metrics"""

    time: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Metric timestamp")


class SystemMetricResponse(SystemMetricBase):
    """Schema for system metric response"""

    time: datetime = Field(description="Metric timestamp")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class SystemMetricsList(PaginatedResponse[SystemMetricResponse]):
    """Paginated list of system metrics"""

    pass


class SystemMetricsQuery(TimeRangeParams):
    """Query parameters for system metrics"""

    device_ids: list[UUID] | None = Field(None, description="Filter by device IDs")
    metrics: list[str] | None = Field(
        None,
        description="Specific metrics to include (cpu_usage_percent, memory_usage_percent, etc.)",
    )
    aggregation: AggregationParams | None = Field(None, description="Aggregation parameters")

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, v: list[dict]) -> list[dict]:
        if v:
            valid_metrics = [
                "cpu_usage_percent",
                "memory_usage_percent",
                "memory_total_bytes",
                "memory_available_bytes",
                "load_average_1m",
                "load_average_5m",
                "load_average_15m",
                "disk_usage_percent",
                "disk_total_bytes",
                "disk_available_bytes",
                "network_bytes_sent",
                "network_bytes_recv",
                "uptime_seconds",
                "process_count",
            ]
            for metric in v:
                if metric not in valid_metrics:
                    raise ValueError(
                        f"Invalid metric: {metric}. Valid metrics: {', '.join(valid_metrics)}"
                    )
        return v


class SystemMetricsAggregated(BaseModel):
    """Aggregated system metrics response"""

    time_bucket: datetime = Field(description="Aggregation time bucket")
    device_id: UUID = Field(description="Device identifier")

    # Aggregated CPU metrics
    avg_cpu_usage: float | None = Field(description="Average CPU usage")
    max_cpu_usage: float | None = Field(description="Maximum CPU usage")
    min_cpu_usage: float | None = Field(description="Minimum CPU usage")

    # Aggregated memory metrics
    avg_memory_usage: float | None = Field(description="Average memory usage")
    max_memory_usage: float | None = Field(description="Maximum memory usage")
    min_memory_usage: float | None = Field(description="Minimum memory usage")
    avg_memory_total: float | None = Field(description="Average total memory")
    avg_memory_available: float | None = Field(description="Average available memory")

    # Aggregated load metrics
    avg_load_1m: float | None = Field(description="Average 1-minute load")
    max_load_1m: float | None = Field(description="Maximum 1-minute load")
    avg_load_5m: float | None = Field(description="Average 5-minute load")
    avg_load_15m: float | None = Field(description="Average 15-minute load")

    # Aggregated disk metrics
    avg_disk_usage: float | None = Field(description="Average disk usage")
    max_disk_usage: float | None = Field(description="Maximum disk usage")
    avg_disk_total: float | None = Field(description="Average total disk space")
    avg_disk_available: float | None = Field(description="Average available disk space")

    # Aggregated network metrics
    total_network_sent: int | None = Field(description="Total network bytes sent")
    total_network_recv: int | None = Field(description="Total network bytes received")
    avg_network_sent: float | None = Field(description="Average network bytes sent")
    avg_network_recv: float | None = Field(description="Average network bytes received")

    # Aggregated process metrics
    avg_process_count: float | None = Field(description="Average process count")
    max_process_count: int | None = Field(description="Maximum process count")

    # Aggregated uptime
    avg_uptime: float | None = Field(description="Average uptime in seconds")

    # Metadata
    sample_count: int = Field(description="Number of samples in aggregation")
    period_start: datetime = Field(description="Aggregation period start")
    period_end: datetime = Field(description="Aggregation period end")

    class Config:
        from_attributes = True


class SystemMetricsAggregatedList(BaseModel):
    """List of aggregated system metrics"""

    metrics: list[SystemMetricsAggregated] = Field(description="Aggregated metrics data")
    total_count: int = Field(description="Total number of aggregated records")
    query_params: SystemMetricsQuery = Field(description="Query parameters used")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Response generation timestamp"
    )


class SystemMetricsSummary(BaseModel):
    """System metrics summary for dashboard"""

    device_id: UUID = Field(description="Device identifier")
    hostname: str | None = Field(description="Device hostname")

    # Current values (latest)
    current_cpu_usage: float | None = Field(description="Current CPU usage percentage")
    current_memory_usage: float | None = Field(description="Current memory usage percentage")
    current_disk_usage: float | None = Field(description="Current disk usage percentage")
    current_load_1m: float | None = Field(description="Current 1-minute load average")
    current_uptime_hours: float | None = Field(description="Current uptime in hours")
    current_process_count: int | None = Field(description="Current process count")

    # 24-hour trends (min, max, avg)
    cpu_trend: dict[str, float] = Field(description="24-hour CPU usage trend")
    memory_trend: dict[str, float] = Field(description="24-hour memory usage trend")
    disk_trend: dict[str, float] = Field(description="24-hour disk usage trend")
    load_trend: dict[str, float] = Field(description="24-hour load average trend")

    # Status indicators
    cpu_status: str = Field(description="CPU status (normal/warning/critical)")
    memory_status: str = Field(description="Memory status (normal/warning/critical)")
    disk_status: str = Field(description="Disk status (normal/warning/critical)")
    load_status: str = Field(description="Load status (normal/warning/critical)")

    # Metadata
    last_updated: datetime = Field(description="Last metrics update timestamp")
    data_points_24h: int = Field(description="Number of data points in last 24 hours")

    class Config:
        from_attributes = True


class SystemMetricsThresholds(BaseModel):
    """System metrics thresholds for alerting"""

    cpu_warning: float = Field(default=80.0, ge=0, le=100, description="CPU warning threshold")
    cpu_critical: float = Field(default=95.0, ge=0, le=100, description="CPU critical threshold")
    memory_warning: float = Field(
        default=85.0, ge=0, le=100, description="Memory warning threshold"
    )
    memory_critical: float = Field(
        default=95.0, ge=0, le=100, description="Memory critical threshold"
    )
    disk_warning: float = Field(default=80.0, ge=0, le=100, description="Disk warning threshold")
    disk_critical: float = Field(default=90.0, ge=0, le=100, description="Disk critical threshold")
    load_warning: float = Field(default=2.0, ge=0, description="Load average warning threshold")
    load_critical: float = Field(default=4.0, ge=0, description="Load average critical threshold")

    @field_validator("cpu_critical")
    @classmethod
    def validate_cpu_critical(cls, v: bool, info: Any) -> bool:
        if "cpu_warning" in info.data and v <= info.data["cpu_warning"]:
            raise ValueError("CPU critical threshold must be higher than warning threshold")
        return v

    @field_validator("memory_critical")
    @classmethod
    def validate_memory_critical(cls, v: bool, info: Any) -> bool:
        if "memory_warning" in info.data and v <= info.data["memory_warning"]:
            raise ValueError("Memory critical threshold must be higher than warning threshold")
        return v

    @field_validator("disk_critical")
    @classmethod
    def validate_disk_critical(cls, v: bool, info: Any) -> bool:
        if "disk_warning" in info.data and v <= info.data["disk_warning"]:
            raise ValueError("Disk critical threshold must be higher than warning threshold")
        return v

    @field_validator("load_critical")
    @classmethod
    def validate_load_critical(cls, v: bool, info: Any) -> bool:
        if "load_warning" in info.data and v <= info.data["load_warning"]:
            raise ValueError("Load critical threshold must be higher than warning threshold")
        return v


class SystemMetricsAlert(BaseModel):
    """System metrics alert"""

    device_id: UUID = Field(description="Device identifier")
    hostname: str = Field(description="Device hostname")
    metric_name: str = Field(description="Metric that triggered the alert")
    current_value: float = Field(description="Current metric value")
    threshold_value: float = Field(description="Threshold that was exceeded")
    severity: str = Field(description="Alert severity (warning/critical)")
    message: str = Field(description="Alert message")
    triggered_at: datetime = Field(description="Alert trigger timestamp")

    class Config:
        from_attributes = True
