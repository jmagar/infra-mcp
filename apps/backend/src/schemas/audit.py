"""
Data collection audit Pydantic schemas for request/response validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from apps.backend.src.schemas.common import APIResponse, OperationResult, PaginatedResponse


class DataCollectionAuditBase(BaseModel):
    """Base schema for data collection audit entries"""

    data_type: str = Field(
        ..., min_length=1, max_length=50, description="Type of data being collected"
    )
    collection_method: str = Field(
        ..., min_length=1, max_length=50, description="Method used for collection"
    )
    collection_source: str | None = Field(
        None, max_length=100, description="Source of the collection"
    )
    force_refresh: bool = Field(default=False, description="Whether cache was bypassed")
    cache_hit: bool = Field(default=False, description="Whether data was served from cache")
    duration_ms: int | None = Field(None, ge=0, description="Collection duration in milliseconds")
    ssh_command_count: int = Field(default=0, ge=0, description="Number of SSH commands executed")
    data_size_bytes: int | None = Field(None, ge=0, description="Size of collected data in bytes")
    status: str = Field(..., description="Collection status")
    error_message: str | None = Field(None, description="Error message if collection failed")
    warnings: list[str] = Field(
        default_factory=list, description="List of warnings during collection"
    )
    records_created: int = Field(default=0, ge=0, description="Number of database records created")
    records_updated: int = Field(default=0, ge=0, description="Number of database records updated")
    freshness_threshold: int | None = Field(
        None, ge=0, description="Freshness threshold in seconds"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["success", "failed", "partial", "timeout"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()

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
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Data type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("collection_method")
    @classmethod
    def validate_collection_method(cls, v):
        valid_methods = ["ssh", "api", "cache", "polling", "webhook", "manual"]
        if v.lower() not in valid_methods:
            raise ValueError(f"Collection method must be one of: {', '.join(valid_methods)}")
        return v.lower()

    @field_validator("duration_ms")
    @classmethod
    def validate_duration_ms(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError("Duration cannot be negative")
            if v > 300000:  # 5 minutes max
                raise ValueError("Duration cannot exceed 300 seconds (300,000ms)")
        return v

    @field_validator("ssh_command_count")
    @classmethod
    def validate_ssh_command_count(cls, v):
        if v < 0:
            raise ValueError("SSH command count cannot be negative")
        if v > 1000:  # Reasonable upper limit
            raise ValueError("SSH command count cannot exceed 1000")
        return v

    @field_validator("data_size_bytes")
    @classmethod
    def validate_data_size_bytes(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError("Data size cannot be negative")
            if v > 1073741824:  # 1GB max
                raise ValueError("Data size cannot exceed 1GB (1,073,741,824 bytes)")
        return v

    @field_validator("records_created", "records_updated")
    @classmethod
    def validate_record_counts(cls, v):
        if v < 0:
            raise ValueError("Record count cannot be negative")
        if v > 1000000:  # 1M records max
            raise ValueError("Record count cannot exceed 1,000,000")
        return v

    @field_validator("freshness_threshold")
    @classmethod
    def validate_freshness_threshold(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError("Freshness threshold cannot be negative")
            if v > 86400:  # 24 hours max
                raise ValueError("Freshness threshold cannot exceed 86400 seconds (24 hours)")
        return v

    @field_validator("warnings")
    @classmethod
    def validate_warnings(cls, v):
        if v and len(v) > 100:
            raise ValueError("Cannot have more than 100 warnings per operation")
        return v

    @field_validator("error_message")
    @classmethod
    def validate_error_message(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                return None  # Convert empty strings to None
            if len(v) > 2000:
                raise ValueError("Error message cannot exceed 2000 characters")
        return v

    @model_validator(mode="after")
    def validate_audit_consistency(self):
        """Cross-field validation for audit entry consistency"""
        # Validate cache_hit logic
        if self.cache_hit and self.collection_method != "cache" and self.force_refresh:
            # If force_refresh is true, cache_hit should be false
            if self.cache_hit:
                raise ValueError("Cannot have cache_hit=True when force_refresh=True")

        # Validate SSH command count consistency
        if self.collection_method != "ssh" and self.ssh_command_count > 0:
            raise ValueError("SSH command count should be 0 for non-SSH collection methods")

        # Validate status and error message consistency
        if self.status == "failed" and not self.error_message:
            raise ValueError("Failed operations must have an error message")
        if self.status == "success" and self.error_message:
            raise ValueError("Successful operations should not have error messages")

        # Validate duration and status consistency
        if self.status == "timeout" and (not self.duration_ms or self.duration_ms < 10000):
            raise ValueError("Timeout operations should have duration >= 10 seconds")

        # Validate record counts consistency
        if self.status == "failed" and (self.records_created > 0 or self.records_updated > 0):
            raise ValueError("Failed operations should not create or update records")

        # Validate data size consistency
        if self.data_size_bytes and self.data_size_bytes > 0 and self.status == "failed":
            raise ValueError("Failed operations should not have data_size_bytes > 0")

        return self


class DataCollectionAuditCreate(DataCollectionAuditBase):
    """Schema for creating a new data collection audit entry"""

    device_id: UUID = Field(..., description="UUID of the device being collected from")
    operation_id: UUID | None = Field(
        None, description="Operation ID (auto-generated if not provided)"
    )


class DataCollectionAuditResponse(DataCollectionAuditBase):
    """Schema for data collection audit response data"""

    time: datetime = Field(description="Timestamp when collection occurred")
    device_id: UUID = Field(description="UUID of the device")
    operation_id: UUID = Field(description="Unique operation identifier")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class DataCollectionAuditSummary(BaseModel):
    """Summary information for data collection audit entries"""

    time: datetime = Field(description="Timestamp when collection occurred")
    device_id: UUID = Field(description="UUID of the device")
    operation_id: UUID = Field(description="Unique operation identifier")
    data_type: str = Field(description="Type of data collected")
    collection_method: str = Field(description="Method used for collection")
    status: str = Field(description="Collection status")
    duration_ms: int | None = Field(description="Collection duration in milliseconds")
    cache_hit: bool = Field(description="Whether data was served from cache")
    records_created: int = Field(description="Number of records created")
    records_updated: int = Field(description="Number of records updated")

    class Config:
        from_attributes = True


class DataCollectionAuditList(PaginatedResponse[DataCollectionAuditSummary]):
    """Paginated list of data collection audit entries"""

    pass


class DataCollectionMetrics(BaseModel):
    """Aggregated metrics for data collection operations"""

    total_operations: int = Field(description="Total number of operations")
    successful_operations: int = Field(description="Number of successful operations")
    failed_operations: int = Field(description="Number of failed operations")
    partial_operations: int = Field(description="Number of partial operations")
    timeout_operations: int = Field(description="Number of timeout operations")

    success_rate: float = Field(description="Success rate as percentage")
    failure_rate: float = Field(description="Failure rate as percentage")

    avg_duration_ms: float | None = Field(description="Average operation duration in milliseconds")
    total_duration_ms: int = Field(description="Total duration of all operations in milliseconds")

    cache_hit_count: int = Field(description="Number of cache hits")
    cache_hit_rate: float = Field(description="Cache hit rate as percentage")

    total_ssh_commands: int = Field(description="Total SSH commands executed")
    total_data_bytes: int = Field(description="Total data collected in bytes")
    total_records_created: int = Field(description="Total database records created")
    total_records_updated: int = Field(description="Total database records updated")

    top_data_types: list[dict] = Field(description="Most collected data types with counts")
    top_errors: list[dict] = Field(description="Most common errors with counts")

    period_start: datetime = Field(description="Start of the metrics period")
    period_end: datetime = Field(description="End of the metrics period")


class DataCollectionFilter(BaseModel):
    """Filter parameters for data collection audit queries"""

    device_ids: list[UUID] | None = Field(None, description="Filter by device IDs")
    data_types: list[str] | None = Field(None, description="Filter by data types")
    collection_methods: list[str] | None = Field(None, description="Filter by collection methods")
    statuses: list[str] | None = Field(None, description="Filter by operation statuses")

    start_time: datetime | None = Field(None, description="Filter operations after this time")
    end_time: datetime | None = Field(None, description="Filter operations before this time")

    min_duration_ms: int | None = Field(None, ge=0, description="Minimum operation duration")
    max_duration_ms: int | None = Field(None, ge=0, description="Maximum operation duration")

    cache_hit_only: bool | None = Field(None, description="Filter only cache hits")
    errors_only: bool | None = Field(None, description="Filter only operations with errors")

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v, info):
        if v and info.data.get("start_time") and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator("max_duration_ms")
    @classmethod
    def validate_duration_range(cls, v, info):
        min_duration = info.data.get("min_duration_ms")
        if v and min_duration and v <= min_duration:
            raise ValueError("max_duration_ms must be greater than min_duration_ms")
        return v


class DataCollectionPerformanceReport(BaseModel):
    """Performance report for data collection operations"""

    device_id: UUID | None = Field(None, description="Device ID (if specific to one device)")
    device_hostname: str | None = Field(None, description="Device hostname")

    report_period: str = Field(description="Report period (e.g., 'last_24h', 'last_week')")
    generated_at: datetime = Field(description="When the report was generated")

    overall_metrics: DataCollectionMetrics = Field(description="Overall performance metrics")

    by_data_type: list[dict] = Field(description="Performance breakdown by data type")
    by_collection_method: list[dict] = Field(
        description="Performance breakdown by collection method"
    )
    by_hour: list[dict] = Field(description="Hourly performance breakdown")

    performance_trends: dict = Field(description="Performance trend analysis")
    recommendations: list[str] = Field(description="Performance improvement recommendations")


class BulkAuditCreate(BaseModel):
    """Schema for creating multiple audit entries in bulk"""

    entries: list[DataCollectionAuditCreate] = Field(
        ..., min_length=1, max_length=1000, description="List of audit entries to create"
    )

    @field_validator("entries")
    @classmethod
    def validate_entries_unique(cls, v):
        # Check for duplicate operation_ids if provided
        operation_ids = [entry.operation_id for entry in v if entry.operation_id]
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("Duplicate operation_ids found in entries")
        return v


class BulkAuditResponse(BaseModel):
    """Response for bulk audit creation"""

    total_entries: int = Field(description="Total number of entries processed")
    successful_entries: int = Field(description="Number of successfully created entries")
    failed_entries: int = Field(description="Number of failed entries")

    errors: list[dict] = Field(description="List of errors for failed entries")
    created_operation_ids: list[UUID] = Field(description="List of created operation IDs")

    processing_duration_ms: int = Field(description="Time taken to process the bulk operation")


# Specific Response Models following established patterns


class DataCollectionAuditListResponse(APIResponse[DataCollectionAuditList]):
    """Standardized paginated list response for audit entries"""

    pass


class DataCollectionAuditDetailResponse(APIResponse[DataCollectionAuditResponse]):
    """Standardized detail response for a single audit entry"""

    pass


class DataCollectionMetricsResponse(APIResponse[DataCollectionMetrics]):
    """Response for data collection metrics queries"""

    pass


class DataCollectionPerformanceReportResponse(APIResponse[DataCollectionPerformanceReport]):
    """Response for data collection performance reports"""

    pass


class BulkAuditOperationResponse(OperationResult[BulkAuditResponse]):
    """Response for bulk audit operations"""

    def __init__(self, bulk_result: BulkAuditResponse, **kwargs):
        super().__init__(
            success=bulk_result.failed_entries == 0,
            operation_type="bulk_audit_create",
            result=bulk_result,
            error_message=f"{bulk_result.failed_entries} entries failed to create"
            if bulk_result.failed_entries > 0
            else None,
            **kwargs,
        )
