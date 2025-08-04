"""
Service performance metrics Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from apps.backend.src.schemas.common import PaginatedResponse


class ServicePerformanceMetricBase(BaseModel):
    """Base schema for service performance metrics"""

    service_name: str = Field(..., min_length=1, max_length=50, description="Name of the service")
    operations_total: int = Field(default=0, ge=0, description="Total number of operations")
    operations_successful: int = Field(
        default=0, ge=0, description="Number of successful operations"
    )
    operations_failed: int = Field(default=0, ge=0, description="Number of failed operations")
    operations_cached: int = Field(default=0, ge=0, description="Number of cached operations")

    avg_duration_ms: float | None = Field(
        None, ge=0, description="Average operation duration in milliseconds"
    )
    max_duration_ms: int | None = Field(
        None, ge=0, description="Maximum operation duration in milliseconds"
    )
    min_duration_ms: int | None = Field(
        None, ge=0, description="Minimum operation duration in milliseconds"
    )

    ssh_connections_created: int = Field(
        default=0, ge=0, description="Number of SSH connections created"
    )
    ssh_connections_reused: int = Field(
        default=0, ge=0, description="Number of SSH connections reused"
    )
    ssh_commands_executed: int = Field(
        default=0, ge=0, description="Number of SSH commands executed"
    )

    cache_hit_ratio: float | None = Field(
        None, ge=0, le=100, description="Cache hit ratio as percentage"
    )
    cache_size_entries: int | None = Field(None, ge=0, description="Number of cache entries")
    cache_evictions: int = Field(default=0, ge=0, description="Number of cache evictions")

    data_collected_bytes: int = Field(default=0, ge=0, description="Total bytes of data collected")
    database_writes: int = Field(default=0, ge=0, description="Number of database writes")

    error_types: dict[str, int] = Field(
        default_factory=dict, description="Error types and their counts"
    )
    top_errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Top errors with details"
    )

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, v):
        # Allow any service name but validate format
        import re

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Service name must start with letter and contain only letters, numbers, underscores, and hyphens"
            )
        return v.lower()

    @field_validator("operations_successful")
    @classmethod
    def validate_successful_operations(cls, v, info):
        total = info.data.get("operations_total", 0)
        if v > total:
            raise ValueError("Successful operations cannot exceed total operations")
        return v

    @field_validator("operations_failed")
    @classmethod
    def validate_failed_operations(cls, v, info):
        total = info.data.get("operations_total", 0)
        successful = info.data.get("operations_successful", 0)
        if v > total - successful:
            raise ValueError("Failed operations cannot exceed remaining operations")
        return v

    @field_validator("max_duration_ms")
    @classmethod
    def validate_max_duration(cls, v, info):
        min_duration = info.data.get("min_duration_ms")
        if v is not None and min_duration is not None and v < min_duration:
            raise ValueError("Max duration cannot be less than min duration")
        return v

    @field_validator("avg_duration_ms", "max_duration_ms", "min_duration_ms")
    @classmethod
    def validate_duration_values(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError("Duration values cannot be negative")
            if v > 3600000:  # 1 hour max
                raise ValueError("Duration values cannot exceed 3600 seconds (3,600,000ms)")
        return v

    @field_validator("cache_hit_ratio")
    @classmethod
    def validate_cache_hit_ratio(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Cache hit ratio must be between 0 and 100 percent")
        return v

    @field_validator("operations_cached")
    @classmethod
    def validate_cached_operations(cls, v, info):
        total = info.data.get("operations_total", 0)
        if v > total:
            raise ValueError("Cached operations cannot exceed total operations")
        return v

    @field_validator("ssh_connections_reused")
    @classmethod
    def validate_ssh_reused(cls, v, info):
        created = info.data.get("ssh_connections_created", 0)
        if v > created * 10:  # Allow some reuse multiplier
            raise ValueError("SSH connections reused seems unreasonably high compared to created")
        return v

    @field_validator("error_types")
    @classmethod
    def validate_error_types(cls, v):
        if v and len(v) > 100:
            raise ValueError("Cannot track more than 100 different error types")
        return v

    @field_validator("top_errors")
    @classmethod
    def validate_top_errors(cls, v):
        if v and len(v) > 50:
            raise ValueError("Cannot have more than 50 top errors")
        return v

    @field_validator("data_collected_bytes")
    @classmethod
    def validate_data_collected_bytes(cls, v):
        if v < 0:
            raise ValueError("Data collected bytes cannot be negative")
        if v > 10737418240:  # 10GB max
            raise ValueError("Data collected bytes cannot exceed 10GB per metric period")
        return v

    @model_validator(mode="after")
    def validate_performance_metric_consistency(self):
        """Cross-field validation for performance metric consistency"""
        # Validate operations totals
        if self.operations_successful + self.operations_failed > self.operations_total:
            raise ValueError(
                "Sum of successful and failed operations cannot exceed total operations"
            )

        # Validate SSH connection logic
        if self.ssh_connections_reused > 0 and self.ssh_connections_created == 0:
            raise ValueError("Cannot reuse SSH connections if none were created")

        # Validate cache consistency
        if self.operations_cached > 0 and (
            self.cache_hit_ratio is None or self.cache_hit_ratio == 0
        ):
            raise ValueError("If operations were cached, cache hit ratio should be > 0")
        if self.cache_hit_ratio and self.cache_hit_ratio > 0 and self.operations_cached == 0:
            raise ValueError("If cache hit ratio > 0, some operations should be cached")

        # Validate duration consistency
        if (
            self.min_duration_ms is not None
            and self.max_duration_ms is not None
            and self.avg_duration_ms is not None
        ):
            if not (self.min_duration_ms <= self.avg_duration_ms <= self.max_duration_ms):
                raise ValueError("Duration values must satisfy: min <= avg <= max")

        # Validate error consistency
        if self.operations_failed > 0 and not self.error_types and not self.top_errors:
            raise ValueError("Failed operations should have error types or top errors recorded")

        return self


class ServicePerformanceMetricCreate(ServicePerformanceMetricBase):
    """Schema for creating a new service performance metric"""

    pass


class ServicePerformanceMetricResponse(ServicePerformanceMetricBase):
    """Schema for service performance metric response data"""

    time: datetime = Field(description="Timestamp when metric was recorded")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ServicePerformanceMetricSummary(BaseModel):
    """Summary information for service performance metrics"""

    time: datetime = Field(description="Timestamp when metric was recorded")
    service_name: str = Field(description="Name of the service")
    operations_total: int = Field(description="Total number of operations")
    success_rate: float = Field(description="Success rate as percentage")
    avg_duration_ms: float | None = Field(description="Average operation duration")
    cache_hit_ratio: float | None = Field(description="Cache hit ratio as percentage")
    performance_grade: str = Field(description="Performance grade (A-F)")

    class Config:
        from_attributes = True


class ServicePerformanceMetricList(PaginatedResponse[ServicePerformanceMetricSummary]):
    """Paginated list of service performance metrics"""

    pass


class ServicePerformanceAggregation(BaseModel):
    """Aggregated service performance metrics"""

    service_name: str = Field(description="Name of the service")
    period_start: datetime = Field(description="Start of aggregation period")
    period_end: datetime = Field(description="End of aggregation period")

    total_operations: int = Field(description="Total operations in period")
    total_successful: int = Field(description="Total successful operations")
    total_failed: int = Field(description="Total failed operations")
    total_cached: int = Field(description="Total cached operations")

    success_rate: float = Field(description="Overall success rate as percentage")
    failure_rate: float = Field(description="Overall failure rate as percentage")
    cache_hit_rate: float = Field(description="Overall cache hit rate as percentage")

    avg_duration_ms: float | None = Field(description="Average operation duration")
    median_duration_ms: float | None = Field(description="Median operation duration")
    p95_duration_ms: float | None = Field(description="95th percentile duration")
    p99_duration_ms: float | None = Field(description="99th percentile duration")

    total_ssh_connections: int = Field(description="Total SSH connections created")
    ssh_reuse_rate: float = Field(description="SSH connection reuse rate as percentage")

    total_data_bytes: int = Field(description="Total data collected in bytes")
    total_database_writes: int = Field(description="Total database writes")

    performance_grade: str = Field(description="Overall performance grade (A-F)")
    performance_trend: str = Field(description="Performance trend (improving, degrading, stable)")

    top_error_types: list[dict[str, Any]] = Field(description="Most common error types")
    hourly_breakdown: list[dict[str, Any]] = Field(description="Hourly performance breakdown")


class ServicePerformanceFilter(BaseModel):
    """Filter parameters for service performance metrics"""

    service_names: list[str] | None = Field(None, description="Filter by service names")
    start_time: datetime | None = Field(None, description="Filter metrics after this time")
    end_time: datetime | None = Field(None, description="Filter metrics before this time")

    min_operations: int | None = Field(None, ge=0, description="Minimum number of operations")
    max_operations: int | None = Field(None, ge=0, description="Maximum number of operations")

    min_success_rate: float | None = Field(
        None, ge=0, le=100, description="Minimum success rate percentage"
    )
    max_failure_rate: float | None = Field(
        None, ge=0, le=100, description="Maximum failure rate percentage"
    )

    min_duration_ms: float | None = Field(None, ge=0, description="Minimum average duration")
    max_duration_ms: float | None = Field(None, ge=0, description="Maximum average duration")

    performance_grades: list[str] | None = Field(None, description="Filter by performance grades")

    has_errors_only: bool | None = Field(None, description="Filter only services with errors")
    low_performance_only: bool | None = Field(
        None, description="Filter only low-performing services"
    )

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v, info):
        if v and info.data.get("start_time") and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator("max_operations")
    @classmethod
    def validate_operations_range(cls, v, info):
        min_ops = info.data.get("min_operations")
        if v is not None and min_ops is not None and v <= min_ops:
            raise ValueError("max_operations must be greater than min_operations")
        return v

    @field_validator("performance_grades")
    @classmethod
    def validate_performance_grades(cls, v):
        if v:
            valid_grades = ["A", "B", "C", "D", "F"]
            invalid_grades = [grade for grade in v if grade.upper() not in valid_grades]
            if invalid_grades:
                raise ValueError(
                    f"Invalid performance grades: {invalid_grades}. Must be A, B, C, D, or F"
                )
            return [grade.upper() for grade in v]
        return v


class ServicePerformanceComparison(BaseModel):
    """Comparison of service performance between two periods"""

    service_name: str = Field(description="Name of the service")

    period1_start: datetime = Field(description="Start of first period")
    period1_end: datetime = Field(description="End of first period")
    period2_start: datetime = Field(description="Start of second period")
    period2_end: datetime = Field(description="End of second period")

    period1_metrics: ServicePerformanceAggregation = Field(description="Metrics for first period")
    period2_metrics: ServicePerformanceAggregation = Field(description="Metrics for second period")

    improvements: list[str] = Field(description="Areas of improvement")
    regressions: list[str] = Field(description="Areas of regression")

    success_rate_change: float = Field(description="Change in success rate (percentage points)")
    avg_duration_change: float | None = Field(
        description="Change in average duration (milliseconds)"
    )
    cache_hit_rate_change: float = Field(description="Change in cache hit rate (percentage points)")

    overall_trend: str = Field(description="Overall performance trend (improved, degraded, stable)")
    recommendation: str = Field(description="Performance improvement recommendation")


class ServicePerformanceAlert(BaseModel):
    """Service performance alert information"""

    service_name: str = Field(description="Name of the service")
    alert_type: str = Field(description="Type of performance alert")
    severity: str = Field(description="Alert severity level")

    metric_name: str = Field(description="Name of the metric that triggered alert")
    current_value: float = Field(description="Current value of the metric")
    threshold_value: float = Field(description="Threshold value that was breached")

    description: str = Field(description="Description of the performance issue")
    detected_at: datetime = Field(description="When the issue was detected")

    duration_minutes: int | None = Field(description="How long the issue has persisted")
    affected_operations: int = Field(description="Number of operations affected")

    recommended_actions: list[str] = Field(description="Recommended actions to resolve issue")
    auto_resolution_attempted: bool = Field(description="Whether auto-resolution was attempted")

    related_services: list[str] = Field(description="Other services potentially affected")
    impact_assessment: str = Field(description="Assessment of impact on system")


class ServicePerformanceTrend(BaseModel):
    """Service performance trend analysis"""

    service_name: str = Field(description="Name of the service")
    analysis_period_days: int = Field(description="Number of days analyzed")

    trend_direction: str = Field(
        description="Overall trend direction (improving, degrading, stable)"
    )
    trend_strength: float = Field(description="Strength of trend (0.0 to 1.0)")

    success_rate_trend: dict[str, Any] = Field(description="Success rate trend analysis")
    duration_trend: dict[str, Any] = Field(description="Duration trend analysis")
    throughput_trend: dict[str, Any] = Field(description="Throughput trend analysis")

    seasonal_patterns: list[dict[str, Any]] = Field(description="Identified seasonal patterns")
    anomalies_detected: list[dict[str, Any]] = Field(description="Performance anomalies detected")

    forecast_7_days: dict[str, Any] = Field(description="7-day performance forecast")
    confidence_interval: float = Field(description="Confidence interval for forecast")

    recommendations: list[str] = Field(description="Trend-based recommendations")


class ServicePerformanceReport(BaseModel):
    """Comprehensive service performance report"""

    service_name: str | None = Field(None, description="Service name (if specific to one service)")
    report_period: str = Field(description="Report period description")
    generated_at: datetime = Field(description="When report was generated")

    executive_summary: str = Field(description="Executive summary of performance")
    overall_health_score: float = Field(ge=0, le=100, description="Overall health score (0-100)")

    key_metrics: dict[str, Any] = Field(description="Key performance metrics")
    performance_by_service: list[ServicePerformanceAggregation] = Field(
        description="Performance by service"
    )

    top_performing_services: list[str] = Field(description="Best performing services")
    underperforming_services: list[str] = Field(description="Services needing attention")

    trends_analysis: list[ServicePerformanceTrend] = Field(
        description="Trend analysis for services"
    )
    alerts_summary: list[ServicePerformanceAlert] = Field(description="Active performance alerts")

    recommendations: list[str] = Field(description="Performance improvement recommendations")
    action_items: list[dict[str, Any]] = Field(description="Specific action items with priorities")

    @field_validator("executive_summary")
    @classmethod
    def validate_executive_summary(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Executive summary cannot be empty")
        if len(v) > 5000:
            raise ValueError("Executive summary cannot exceed 5000 characters")
        return v.strip()

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations(cls, v):
        if v and len(v) > 50:
            raise ValueError("Cannot have more than 50 recommendations")
        return v

    @field_validator("action_items")
    @classmethod
    def validate_action_items(cls, v):
        if v and len(v) > 100:
            raise ValueError("Cannot have more than 100 action items")
        return v

    @field_validator("top_performing_services", "underperforming_services")
    @classmethod
    def validate_service_lists(cls, v):
        if v and len(v) > 50:
            raise ValueError("Service lists cannot exceed 50 items")
        return v

    @model_validator(mode="after")
    def validate_report_consistency(self):
        """Cross-field validation for performance report consistency"""
        # Validate service overlap
        if self.top_performing_services and self.underperforming_services:
            overlap = set(self.top_performing_services) & set(self.underperforming_services)
            if overlap:
                raise ValueError(
                    f"Services cannot be both top-performing and underperforming: {overlap}"
                )

        # Validate health score consistency
        if self.overall_health_score < 50 and not self.underperforming_services:
            raise ValueError("Low health score should identify underperforming services")
        if self.overall_health_score > 80 and not self.top_performing_services:
            raise ValueError("High health score should identify top-performing services")

        # Validate recommendations consistency
        if self.underperforming_services and not self.recommendations:
            raise ValueError("Reports with underperforming services should include recommendations")

        return self
