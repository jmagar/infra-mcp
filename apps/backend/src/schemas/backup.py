"""
Backup-related Pydantic schemas for request/response validation.
"""

from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from apps.backend.src.schemas.common import PaginatedResponse


class BackupStatusBase(BaseModel):
    """Base backup status schema with common fields"""

    backup_type: str = Field(..., max_length=100, description="Backup type")
    backup_name: str = Field(..., min_length=1, max_length=255, description="Backup name")
    source_path: Optional[str] = Field(None, description="Source path for backup")
    destination_path: Optional[str] = Field(None, description="Destination path for backup")
    status: str = Field(..., description="Backup status")
    start_time: Optional[datetime] = Field(None, description="Backup start time")
    end_time: Optional[datetime] = Field(None, description="Backup end time")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Backup duration in seconds")
    size_bytes: Optional[int] = Field(None, ge=0, description="Backup size in bytes")
    compressed_size_bytes: Optional[int] = Field(None, ge=0, description="Compressed backup size")
    files_count: Optional[int] = Field(None, ge=0, description="Number of files backed up")
    success_count: Optional[int] = Field(None, ge=0, description="Number of successful operations")
    error_count: Optional[int] = Field(None, ge=0, description="Number of errors")
    warning_count: Optional[int] = Field(None, ge=0, description="Number of warnings")
    error_message: Optional[str] = Field(None, description="Error message if backup failed")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("backup_type")
    @classmethod
    def validate_backup_type(cls, v):
        valid_types = [
            "system",
            "database",
            "container",
            "zfs",
            "file",
            "config",
            "docker-volume",
            "vm",
            "snapshot",
            "incremental",
            "full",
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Backup type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled", "paused"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v, info):
        if v and info.data.get("start_time"):
            if v <= info.data["start_time"]:
                raise ValueError("end_time must be after start_time")
        return v


class BackupStatusCreate(BackupStatusBase):
    """Schema for creating a new backup status record"""

    device_id: UUID = Field(..., description="Device UUID")


class BackupStatusUpdate(BaseModel):
    """Schema for updating backup status"""

    status: Optional[str] = Field(None, description="Updated backup status")
    end_time: Optional[datetime] = Field(None, description="Backup end time")
    duration_seconds: Optional[int] = Field(None, ge=0, description="Backup duration")
    size_bytes: Optional[int] = Field(None, ge=0, description="Backup size")
    compressed_size_bytes: Optional[int] = Field(None, ge=0, description="Compressed size")
    files_count: Optional[int] = Field(None, ge=0, description="Files count")
    success_count: Optional[int] = Field(None, ge=0, description="Success count")
    error_count: Optional[int] = Field(None, ge=0, description="Error count")
    warning_count: Optional[int] = Field(None, ge=0, description="Warning count")
    error_message: Optional[str] = Field(None, description="Error message")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BackupStatusResponse(BackupStatusBase):
    """Schema for backup status response data"""

    id: UUID = Field(description="Backup record UUID")
    device_id: UUID = Field(description="Device UUID")
    created_at: datetime = Field(description="Record creation timestamp")

    # Computed fields
    hostname: Optional[str] = Field(None, description="Device hostname")
    compression_ratio: Optional[float] = Field(None, description="Compression ratio")
    success_rate: Optional[float] = Field(None, description="Success rate percentage")
    throughput_mbps: Optional[float] = Field(None, description="Backup throughput in Mbps")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class BackupStatusList(PaginatedResponse[BackupStatusResponse]):
    """Paginated list of backup status records"""

    pass


class BackupSchedule(BaseModel):
    """Backup schedule configuration"""

    schedule_id: str = Field(description="Schedule identifier")
    schedule_name: str = Field(description="Schedule name")
    device_id: UUID = Field(description="Target device UUID")
    backup_type: str = Field(description="Type of backup")
    source_paths: List[str] = Field(description="Source paths to backup")
    destination_path: str = Field(description="Destination path")
    cron_expression: str = Field(description="Cron schedule expression")
    retention_days: int = Field(ge=1, description="Retention period in days")
    compression_enabled: bool = Field(default=True, description="Enable compression")
    encryption_enabled: bool = Field(default=False, description="Enable encryption")
    exclude_patterns: List[str] = Field(
        default_factory=list, description="File patterns to exclude"
    )
    pre_backup_commands: List[str] = Field(
        default_factory=list, description="Commands to run before backup"
    )
    post_backup_commands: List[str] = Field(
        default_factory=list, description="Commands to run after backup"
    )
    notification_emails: List[str] = Field(default_factory=list, description="Email notifications")
    is_active: bool = Field(default=True, description="Whether schedule is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Schedule creation time"
    )
    last_run: Optional[datetime] = Field(None, description="Last execution time")
    next_run: Optional[datetime] = Field(None, description="Next scheduled execution")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v):
        # Basic cron validation - should have 5 or 6 parts
        parts = v.split()
        if len(parts) not in [5, 6]:
            raise ValueError("Cron expression must have 5 or 6 parts")
        return v


class BackupPolicy(BaseModel):
    """Backup policy configuration"""

    policy_id: str = Field(description="Policy identifier")
    policy_name: str = Field(description="Policy name")
    description: str = Field(description="Policy description")
    backup_types: List[str] = Field(description="Backup types covered by policy")
    default_retention_days: int = Field(ge=1, description="Default retention period")
    max_backup_size_gb: Optional[int] = Field(None, description="Maximum backup size in GB")
    compression_required: bool = Field(default=False, description="Require compression")
    encryption_required: bool = Field(default=False, description="Require encryption")
    verification_required: bool = Field(default=True, description="Require verification")
    offsite_copy_required: bool = Field(default=False, description="Require offsite copy")
    max_concurrent_backups: int = Field(ge=1, description="Maximum concurrent backups")
    bandwidth_limit_mbps: Optional[int] = Field(None, description="Bandwidth limit in Mbps")
    allowed_backup_windows: List[str] = Field(description="Allowed backup time windows")
    excluded_days: List[str] = Field(default_factory=list, description="Excluded days of week")
    notification_settings: Dict[str, bool] = Field(description="Notification preferences")
    is_active: bool = Field(default=True, description="Whether policy is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Policy creation time"
    )


class BackupHealthOverview(BaseModel):
    """Backup health overview across all devices"""

    total_backup_jobs: int = Field(description="Total number of backup jobs")
    successful_backups_24h: int = Field(description="Successful backups in last 24 hours")
    failed_backups_24h: int = Field(description="Failed backups in last 24 hours")
    running_backups: int = Field(description="Currently running backups")
    total_backup_data_tb: float = Field(description="Total backup data in TB")
    backup_success_rate: float = Field(description="Overall backup success rate")
    average_backup_duration_minutes: float = Field(description="Average backup duration")
    backups_by_type: Dict[str, int] = Field(description="Backup count by type")
    backups_by_device: Dict[str, int] = Field(description="Backup count by device")
    recent_failures: List[str] = Field(description="Recent backup failures")
    overdue_backups: List[str] = Field(description="Overdue backup schedules")
    storage_utilization: Dict[str, float] = Field(description="Backup storage utilization")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Report timestamp")


class BackupMetrics(BaseModel):
    """Backup metrics summary for a device"""

    device_id: UUID
    hostname: str
    total_backups: int = Field(description="Total number of backups")
    successful_backups: int = Field(description="Number of successful backups")
    failed_backups: int = Field(description="Number of failed backups")
    success_rate: float = Field(description="Backup success rate percentage")
    total_data_gb: float = Field(description="Total data backed up in GB")
    average_duration_minutes: float = Field(description="Average backup duration")
    last_successful_backup: Optional[datetime] = Field(description="Last successful backup")
    last_failed_backup: Optional[datetime] = Field(description="Last failed backup")
    backup_types_used: List[str] = Field(description="Types of backups performed")
    storage_efficiency: float = Field(description="Storage efficiency ratio")
    alerts: List[str] = Field(description="Active backup alerts")
    recommendations: List[str] = Field(description="Backup recommendations")
    last_updated: datetime = Field(description="Last metrics update")

    class Config:
        from_attributes = True


class BackupVerification(BaseModel):
    """Backup verification result"""

    verification_id: str = Field(description="Verification identifier")
    backup_id: UUID = Field(description="Backup record UUID")
    verification_type: str = Field(description="Type of verification")
    status: str = Field(description="Verification status")
    start_time: datetime = Field(description="Verification start time")
    end_time: Optional[datetime] = Field(description="Verification end time")
    files_verified: Optional[int] = Field(None, description="Number of files verified")
    files_corrupted: Optional[int] = Field(None, description="Number of corrupted files")
    checksum_matches: Optional[int] = Field(None, description="Number of checksum matches")
    checksum_mismatches: Optional[int] = Field(None, description="Number of checksum mismatches")
    verification_details: Dict[str, Any] = Field(description="Detailed verification results")
    error_message: Optional[str] = Field(None, description="Error message if verification failed")

    @field_validator("verification_type")
    @classmethod
    def validate_verification_type(cls, v):
        valid_types = ["checksum", "restore_test", "file_list", "integrity", "full"]
        if v.lower() not in valid_types:
            raise ValueError(f"Verification type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["pending", "running", "passed", "failed", "warning"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()


class BackupRestore(BaseModel):
    """Backup restore operation"""

    restore_id: str = Field(description="Restore operation identifier")
    backup_id: UUID = Field(description="Source backup UUID")
    restore_type: str = Field(description="Type of restore operation")
    source_path: str = Field(description="Source path in backup")
    destination_path: str = Field(description="Destination path for restore")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing files")
    preserve_permissions: bool = Field(default=True, description="Preserve file permissions")
    files_to_restore: Optional[List[str]] = Field(None, description="Specific files to restore")
    exclude_patterns: List[str] = Field(default_factory=list, description="Patterns to exclude")
    initiated_by: str = Field(description="User who initiated restore")
    initiated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Restore initiation time"
    )

    @field_validator("restore_type")
    @classmethod
    def validate_restore_type(cls, v):
        valid_types = ["full", "partial", "selective", "point_in_time"]
        if v.lower() not in valid_types:
            raise ValueError(f"Restore type must be one of: {', '.join(valid_types)}")
        return v.lower()


class BackupRestoreResult(BaseModel):
    """Backup restore operation result"""

    restore_id: str = Field(description="Restore operation identifier")
    status: str = Field(description="Restore status")
    start_time: datetime = Field(description="Restore start time")
    end_time: Optional[datetime] = Field(description="Restore end time")
    duration_seconds: Optional[int] = Field(description="Restore duration")
    files_restored: Optional[int] = Field(description="Number of files restored")
    bytes_restored: Optional[int] = Field(description="Number of bytes restored")
    files_skipped: Optional[int] = Field(description="Number of files skipped")
    files_failed: Optional[int] = Field(description="Number of files that failed to restore")
    success_rate: Optional[float] = Field(description="Restore success rate")
    error_message: Optional[str] = Field(description="Error message if restore failed")
    restore_log: List[str] = Field(default_factory=list, description="Detailed restore log")

    class Config:
        from_attributes = True


class BackupFilter(BaseModel):
    """Backup filtering parameters"""

    device_ids: Optional[List[UUID]] = Field(description="Filter by device IDs")
    backup_types: Optional[List[str]] = Field(description="Filter by backup types")
    statuses: Optional[List[str]] = Field(description="Filter by backup statuses")
    start_date: Optional[date] = Field(description="Filter backups after this date")
    end_date: Optional[date] = Field(description="Filter backups before this date")
    min_size_gb: Optional[float] = Field(description="Minimum backup size in GB")
    max_size_gb: Optional[float] = Field(description="Maximum backup size in GB")
    has_errors: Optional[bool] = Field(description="Filter backups with errors")
    backup_name_pattern: Optional[str] = Field(description="Backup name pattern (regex)")
    duration_min_minutes: Optional[int] = Field(description="Minimum duration in minutes")
    duration_max_minutes: Optional[int] = Field(description="Maximum duration in minutes")
