"""
System logs-related Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from apps.backend.src.schemas.common import PaginatedResponse, LogLevel


class SystemLogBase(BaseModel):
    """Base system log schema with common fields"""

    service_name: Optional[str] = Field(None, max_length=255, description="Service name")
    log_level: LogLevel = Field(..., description="Log severity level")
    source: str = Field(..., max_length=255, description="Log source")
    process_id: Optional[int] = Field(None, description="Process ID")
    user_name: Optional[str] = Field(None, max_length=100, description="User name")
    facility: Optional[str] = Field(None, max_length=50, description="Syslog facility")
    message: str = Field(..., description="Log message content")
    raw_message: Optional[str] = Field(None, description="Raw log message")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("source")
    @classmethod
    def validate_source(cls, v):
        valid_sources = [
            "systemd",
            "syslog",
            "kernel",
            "application",
            "security",
            "cron",
            "auth",
            "mail",
            "daemon",
            "docker",
            "nginx",
            "ssh",
        ]
        if v.lower() not in valid_sources:
            # Allow custom sources, just log a warning
            pass
        return v.lower()

    @field_validator("facility")
    @classmethod
    def validate_facility(cls, v):
        if v is not None:
            valid_facilities = [
                "kern",
                "user",
                "mail",
                "daemon",
                "auth",
                "syslog",
                "lpr",
                "news",
                "uucp",
                "cron",
                "authpriv",
                "ftp",
                "local0",
                "local1",
                "local2",
                "local3",
                "local4",
                "local5",
                "local6",
                "local7",
            ]
            if v.lower() not in valid_facilities:
                raise ValueError(f"Facility must be one of: {', '.join(valid_facilities)}")
            return v.lower()
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Log message cannot be empty")
        return v.strip()


class SystemLogCreate(SystemLogBase):
    """Schema for creating a new system log record"""

    device_id: UUID = Field(..., description="Device UUID")


class SystemLogResponse(SystemLogBase):
    """Schema for system log response data"""

    time: datetime = Field(description="Log timestamp")
    device_id: UUID = Field(description="Device UUID")

    # Computed fields
    hostname: Optional[str] = Field(None, description="Device hostname")
    age_minutes: Optional[int] = Field(None, description="Age of log entry in minutes")
    severity_score: Optional[int] = Field(None, description="Severity score (0-10)")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class SystemLogList(PaginatedResponse[SystemLogResponse]):
    """Paginated list of system logs"""

    pass


class LogAnalytics(BaseModel):
    """Log analytics and statistics"""

    device_id: Optional[UUID] = Field(None, description="Device ID (None for all devices)")
    time_range: str = Field(description="Time range analyzed")
    total_logs: int = Field(description="Total number of log entries")
    logs_by_level: Dict[str, int] = Field(description="Log count by severity level")
    logs_by_source: Dict[str, int] = Field(description="Log count by source")
    logs_by_service: Dict[str, int] = Field(description="Log count by service")
    error_rate: float = Field(description="Error log rate per hour")
    warning_rate: float = Field(description="Warning log rate per hour")
    top_error_messages: List[Dict[str, Any]] = Field(description="Most common error messages")
    anomalies_detected: List[Dict[str, Any]] = Field(description="Detected log anomalies")
    trends: Dict[str, List[float]] = Field(description="Log volume trends")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis timestamp"
    )


class LogPattern(BaseModel):
    """Log pattern analysis result"""

    pattern_id: str = Field(description="Pattern identifier")
    pattern_regex: str = Field(description="Regular expression pattern")
    pattern_description: str = Field(description="Human-readable pattern description")
    occurrence_count: int = Field(description="Number of matches")
    first_seen: datetime = Field(description="First occurrence timestamp")
    last_seen: datetime = Field(description="Last occurrence timestamp")
    severity_distribution: Dict[str, int] = Field(description="Severity level distribution")
    affected_devices: List[str] = Field(description="List of affected device hostnames")
    sample_messages: List[str] = Field(description="Sample log messages matching pattern")
    confidence_score: float = Field(ge=0, le=1, description="Pattern confidence score")


class LogAlert(BaseModel):
    """Log-based alert configuration"""

    alert_id: str = Field(description="Alert identifier")
    alert_name: str = Field(description="Alert name")
    description: str = Field(description="Alert description")
    pattern: str = Field(description="Log pattern to match (regex)")
    log_level: Optional[LogLevel] = Field(None, description="Minimum log level to trigger")
    services: List[str] = Field(default_factory=list, description="Services to monitor")
    devices: List[UUID] = Field(default_factory=list, description="Devices to monitor")
    threshold_count: int = Field(ge=1, description="Minimum occurrence count")
    time_window_minutes: int = Field(ge=1, description="Time window in minutes")
    cooldown_minutes: int = Field(ge=1, description="Cooldown period between alerts")
    is_active: bool = Field(default=True, description="Whether alert is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Alert creation time")
    last_triggered: Optional[datetime] = Field(None, description="Last trigger timestamp")


class LogAlertTrigger(BaseModel):
    """Log alert trigger event"""

    alert_id: str = Field(description="Alert identifier")
    alert_name: str = Field(description="Alert name")
    trigger_time: datetime = Field(description="Trigger timestamp")
    matching_logs_count: int = Field(description="Number of matching log entries")
    affected_devices: List[str] = Field(description="Affected device hostnames")
    severity: str = Field(description="Alert severity level")
    sample_messages: List[str] = Field(description="Sample matching log messages")
    pattern_matched: str = Field(description="Regex pattern that matched")
    resolution_status: str = Field(default="open", description="Resolution status")
    acknowledged_by: Optional[str] = Field(None, description="User who acknowledged alert")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgment timestamp")

    class Config:
        from_attributes = True


class LogSearch(BaseModel):
    """Log search parameters"""

    query: Optional[str] = Field(None, description="Search query (supports regex)")
    device_ids: Optional[List[UUID]] = Field(None, description="Device IDs to search")
    log_levels: Optional[List[LogLevel]] = Field(None, description="Log levels to include")
    services: Optional[List[str]] = Field(None, description="Services to search")
    sources: Optional[List[str]] = Field(None, description="Log sources to search")
    start_time: Optional[datetime] = Field(None, description="Search start time")
    end_time: Optional[datetime] = Field(None, description="Search end time")
    include_raw: bool = Field(default=False, description="Include raw log messages")
    highlight_matches: bool = Field(default=True, description="Highlight search matches")

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v, info):
        if v and info.data.get("start_time"):
            if v <= info.data["start_time"]:
                raise ValueError("end_time must be after start_time")
        return v


class LogExport(BaseModel):
    """Log export configuration"""

    export_format: str = Field(description="Export format (json/csv/syslog)")
    compression: str = Field(default="gzip", description="Compression format")
    include_metadata: bool = Field(default=True, description="Include metadata fields")
    filter_params: LogSearch = Field(description="Filter parameters for export")
    max_entries: Optional[int] = Field(None, ge=1, description="Maximum entries to export")

    @field_validator("export_format")
    @classmethod
    def validate_export_format(cls, v):
        valid_formats = ["json", "csv", "syslog", "txt"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Export format must be one of: {', '.join(valid_formats)}")
        return v.lower()

    @field_validator("compression")
    @classmethod
    def validate_compression(cls, v):
        valid_compression = ["none", "gzip", "bzip2", "zip"]
        if v.lower() not in valid_compression:
            raise ValueError(f"Compression must be one of: {', '.join(valid_compression)}")
        return v.lower()


class LogRetentionPolicy(BaseModel):
    """Log retention policy configuration"""

    policy_id: str = Field(description="Policy identifier")
    policy_name: str = Field(description="Policy name")
    retention_days: int = Field(ge=1, description="Retention period in days")
    log_levels: List[LogLevel] = Field(description="Log levels affected by policy")
    services: List[str] = Field(default_factory=list, description="Services affected by policy")
    devices: List[UUID] = Field(default_factory=list, description="Devices affected by policy")
    archive_before_delete: bool = Field(default=False, description="Archive logs before deletion")
    archive_location: Optional[str] = Field(None, description="Archive storage location")
    compression_enabled: bool = Field(
        default=True, description="Enable compression for archived logs"
    )
    is_active: bool = Field(default=True, description="Whether policy is active")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Policy creation time"
    )
    last_applied: Optional[datetime] = Field(None, description="Last policy application time")


class LogAggregation(BaseModel):
    """Log aggregation result"""

    time_bucket: datetime = Field(description="Time bucket for aggregation")
    device_id: Optional[UUID] = Field(None, description="Device ID (None for all devices)")
    service_name: Optional[str] = Field(None, description="Service name (None for all services)")
    log_level: LogLevel = Field(description="Log level")
    count: int = Field(description="Number of log entries")
    error_rate: Optional[float] = Field(None, description="Error rate in this bucket")
    unique_messages: Optional[int] = Field(None, description="Number of unique messages")

    class Config:
        from_attributes = True


class LogHealthMetrics(BaseModel):
    """Log health metrics summary"""

    device_id: UUID
    hostname: str
    total_logs_24h: int = Field(description="Total logs in last 24 hours")
    error_logs_24h: int = Field(description="Error logs in last 24 hours")
    warning_logs_24h: int = Field(description="Warning logs in last 24 hours")
    error_rate_per_hour: float = Field(description="Average error rate per hour")
    log_sources_active: int = Field(description="Number of active log sources")
    services_logging: int = Field(description="Number of services producing logs")
    recent_patterns: List[str] = Field(description="Recently detected log patterns")
    anomalies_detected: int = Field(description="Number of anomalies detected")
    health_score: float = Field(ge=0, le=10, description="Overall log health score")
    last_updated: datetime = Field(description="Last metrics update")

    class Config:
        from_attributes = True
