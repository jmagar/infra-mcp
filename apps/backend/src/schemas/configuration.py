"""
Configuration management Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from apps.backend.src.schemas.common import PaginatedResponse


class ConfigurationSnapshotBase(BaseModel):
    """Base schema for configuration snapshots"""

    config_type: str = Field(..., min_length=1, max_length=50, description="Type of configuration")
    file_path: str = Field(
        ..., min_length=1, max_length=1024, description="Path to configuration file"
    )
    content_hash: str = Field(..., min_length=1, max_length=64, description="Hash of file content")
    file_size_bytes: int | None = Field(None, ge=0, description="Size of file in bytes")
    raw_content: str = Field(..., min_length=1, description="Raw file content")
    parsed_data: dict[str, Any] = Field(
        default_factory=dict, description="Parsed configuration data"
    )
    change_type: str = Field(..., description="Type of change")
    previous_hash: str | None = Field(None, max_length=64, description="Hash of previous version")
    file_modified_time: datetime | None = Field(None, description="When file was last modified")
    collection_source: str = Field(
        ..., min_length=1, max_length=50, description="Source of snapshot collection"
    )
    detection_latency_ms: int | None = Field(
        None, ge=0, description="Time to detect change in milliseconds"
    )
    affected_services: list[str] = Field(
        default_factory=list, description="Services affected by this configuration"
    )
    requires_restart: bool = Field(default=False, description="Whether services need restart")
    risk_level: str = Field(default="MEDIUM", description="Risk level of configuration change")

    @field_validator("config_type")
    @classmethod
    def validate_config_type(cls, v):
        valid_types = [
            "docker-compose",
            "nginx",
            "apache",
            "systemd",
            "crontab",
            "ssh",
            "firewall",
            "network",
            "dns",
            "proxy",
            "ssl",
            "database",
            "application",
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Config type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("change_type")
    @classmethod
    def validate_change_type(cls, v):
        valid_types = ["created", "modified", "deleted", "moved", "renamed"]
        if v.lower() not in valid_types:
            raise ValueError(f"Change type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v):
        valid_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Risk level must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator("content_hash", "previous_hash")
    @classmethod
    def validate_content_hash(cls, v):
        if v is not None:
            import re

            if not re.match(r"^[a-fA-F0-9]{32,64}$", v):
                raise ValueError("Content hash must be a valid hexadecimal hash (32-64 characters)")
            return v.lower()
        return v

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size_bytes(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError("File size cannot be negative")
            if v > 104857600:  # 100MB max
                raise ValueError("File size cannot exceed 100MB (104,857,600 bytes)")
        return v

    @field_validator("detection_latency_ms")
    @classmethod
    def validate_detection_latency_ms(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError("Detection latency cannot be negative")
            if v > 3600000:  # 1 hour max
                raise ValueError("Detection latency cannot exceed 3600 seconds (3,600,000ms)")
        return v

    @field_validator("collection_source")
    @classmethod
    def validate_collection_source(cls, v):
        valid_sources = ["polling", "webhook", "manual", "api", "ssh", "file_watch"]
        if v.lower() not in valid_sources:
            raise ValueError(f"Collection source must be one of: {', '.join(valid_sources)}")
        return v.lower()

    @field_validator("affected_services")
    @classmethod
    def validate_affected_services(cls, v):
        if v and len(v) > 100:
            raise ValueError("Cannot have more than 100 affected services per configuration")
        return v

    @field_validator("raw_content")
    @classmethod
    def validate_raw_content(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Raw content cannot be empty")
        if len(v) > 10485760:  # 10MB max
            raise ValueError("Raw content cannot exceed 10MB")
        return v

    @model_validator(mode="after")
    def validate_configuration_consistency(self):
        """Cross-field validation for configuration snapshot consistency"""
        # Validate change type logic
        if self.change_type == "deleted" and self.raw_content:
            if len(self.raw_content.strip()) > 0:
                raise ValueError("Deleted configurations should not have raw content")

        # Validate hash consistency
        if self.change_type == "modified" and not self.previous_hash:
            raise ValueError("Modified configurations must have a previous_hash")
        if self.change_type == "created" and self.previous_hash:
            raise ValueError("Created configurations should not have a previous_hash")

        # Validate restart requirements
        if self.requires_restart and not self.affected_services:
            raise ValueError("Configurations requiring restart must specify affected services")

        # Validate risk level logic
        if self.risk_level == "CRITICAL" and not self.requires_restart:
            raise ValueError("CRITICAL risk configurations typically require service restart")
        if self.risk_level == "LOW" and self.requires_restart:
            # This is allowed but warn in logs
            pass

        # Validate file path patterns
        if self.config_type == "docker-compose" and not any(
            x in self.file_path.lower() for x in ["docker-compose", "compose"]
        ):
            raise ValueError(
                'Docker compose configurations should have "docker-compose" or "compose" in file path'
            )
        if self.config_type == "nginx" and not any(
            x in self.file_path.lower() for x in ["nginx", "conf"]
        ):
            raise ValueError('Nginx configurations should have "nginx" or "conf" in file path')

        return self


class ConfigurationSnapshotCreate(ConfigurationSnapshotBase):
    """Schema for creating a new configuration snapshot"""

    device_id: UUID = Field(..., description="UUID of the device")


class ConfigurationSnapshotResponse(ConfigurationSnapshotBase):
    """Schema for configuration snapshot response data"""

    id: UUID = Field(description="Unique snapshot identifier")
    device_id: UUID = Field(description="UUID of the device")
    time: datetime = Field(description="When snapshot was created")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class ConfigurationSnapshotSummary(BaseModel):
    """Summary information for configuration snapshots"""

    id: UUID = Field(description="Unique snapshot identifier")
    device_id: UUID = Field(description="UUID of the device")
    time: datetime = Field(description="When snapshot was created")
    config_type: str = Field(description="Type of configuration")
    file_path: str = Field(description="Path to configuration file")
    change_type: str = Field(description="Type of change")
    risk_level: str = Field(description="Risk level")
    requires_restart: bool = Field(description="Whether services need restart")
    affected_services_count: int = Field(description="Number of affected services")

    class Config:
        from_attributes = True


class ConfigurationSnapshotList(PaginatedResponse[ConfigurationSnapshotSummary]):
    """Paginated list of configuration snapshots"""

    pass


class ConfigurationChangeEventBase(BaseModel):
    """Base schema for configuration change events"""

    config_type: str = Field(..., min_length=1, max_length=50, description="Type of configuration")
    file_path: str = Field(
        ..., min_length=1, max_length=1024, description="Path to configuration file"
    )
    change_type: str = Field(..., description="Type of change")
    affected_services: list[str] = Field(
        default_factory=list, description="Services affected by change"
    )
    service_dependencies: list[str] = Field(
        default_factory=list, description="Service dependencies"
    )
    requires_restart: bool = Field(default=False, description="Whether services need restart")
    restart_services: list[str] = Field(
        default_factory=list, description="Services that need restart"
    )
    changes_summary: dict[str, Any] = Field(
        default_factory=dict, description="Summary of changes made"
    )
    risk_level: str = Field(default="MEDIUM", description="Risk level of change")
    confidence_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Confidence in change analysis"
    )
    processed: bool = Field(default=False, description="Whether event has been processed")
    notifications_sent: list[dict[str, Any]] = Field(
        default_factory=list, description="Notifications sent for this event"
    )

    @field_validator("config_type")
    @classmethod
    def validate_config_type(cls, v):
        valid_types = [
            "docker-compose",
            "nginx",
            "apache",
            "systemd",
            "crontab",
            "ssh",
            "firewall",
            "network",
            "dns",
            "proxy",
            "ssl",
            "database",
            "application",
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Config type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("change_type")
    @classmethod
    def validate_change_type(cls, v):
        valid_types = ["created", "modified", "deleted", "moved", "renamed"]
        if v.lower() not in valid_types:
            raise ValueError(f"Change type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v):
        valid_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Risk level must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v

    @field_validator("affected_services", "service_dependencies", "restart_services")
    @classmethod
    def validate_service_lists(cls, v):
        if v and len(v) > 100:
            raise ValueError("Service lists cannot exceed 100 items")
        return v

    @field_validator("notifications_sent")
    @classmethod
    def validate_notifications_sent(cls, v):
        if v and len(v) > 50:
            raise ValueError("Cannot have more than 50 notifications per event")
        return v

    @model_validator(mode="after")
    def validate_change_event_consistency(self):
        """Cross-field validation for configuration change event consistency"""
        # Validate restart service logic
        if self.requires_restart and not self.restart_services:
            if not self.affected_services:
                raise ValueError(
                    "Events requiring restart must specify either restart_services or affected_services"
                )

        # Validate restart services are subset of affected services
        if self.restart_services and self.affected_services:
            for service in self.restart_services:
                if service not in self.affected_services:
                    raise ValueError(
                        f'Restart service "{service}" must be in affected_services list'
                    )

        # Validate confidence score consistency
        if self.confidence_score is not None:
            if self.confidence_score < 0.5 and self.processed:
                raise ValueError(
                    "Events with low confidence (<0.5) should not be automatically processed"
                )

        # Validate risk level vs notifications
        if (
            self.risk_level in ["HIGH", "CRITICAL"]
            and not self.notifications_sent
            and self.processed
        ):
            # High risk processed events should have notifications
            pass  # Allow but may warn in logs

        # Validate change summary consistency
        if self.changes_summary and self.change_type:
            if self.change_type == "deleted" and self.changes_summary:
                # Deleted files shouldn't have detailed changes
                if (
                    len(self.changes_summary) > 1
                    or "deleted" not in str(self.changes_summary).lower()
                ):
                    raise ValueError("Deleted configurations should only have deletion summary")

        return self


class ConfigurationChangeEventCreate(ConfigurationChangeEventBase):
    """Schema for creating a new configuration change event"""

    device_id: UUID = Field(..., description="UUID of the device")
    snapshot_id: UUID = Field(..., description="UUID of related configuration snapshot")


class ConfigurationChangeEventResponse(ConfigurationChangeEventBase):
    """Schema for configuration change event response data"""

    id: UUID = Field(description="Unique event identifier")
    device_id: UUID = Field(description="UUID of the device")
    snapshot_id: UUID = Field(description="UUID of related configuration snapshot")
    time: datetime = Field(description="When event was created")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class ConfigurationChangeEventSummary(BaseModel):
    """Summary information for configuration change events"""

    id: UUID = Field(description="Unique event identifier")
    device_id: UUID = Field(description="UUID of the device")
    snapshot_id: UUID = Field(description="UUID of related configuration snapshot")
    time: datetime = Field(description="When event was created")
    config_type: str = Field(description="Type of configuration")
    file_path: str = Field(description="Path to configuration file")
    change_type: str = Field(description="Type of change")
    risk_level: str = Field(description="Risk level")
    requires_restart: bool = Field(description="Whether services need restart")
    processed: bool = Field(description="Whether event has been processed")
    confidence_score: float | None = Field(description="Confidence in change analysis")

    class Config:
        from_attributes = True


class ConfigurationChangeEventList(PaginatedResponse[ConfigurationChangeEventSummary]):
    """Paginated list of configuration change events"""

    pass


class ConfigurationFilter(BaseModel):
    """Filter parameters for configuration queries"""

    device_ids: list[UUID] | None = Field(None, description="Filter by device IDs")
    config_types: list[str] | None = Field(None, description="Filter by configuration types")
    change_types: list[str] | None = Field(None, description="Filter by change types")
    risk_levels: list[str] | None = Field(None, description="Filter by risk levels")

    start_time: datetime | None = Field(None, description="Filter changes after this time")
    end_time: datetime | None = Field(None, description="Filter changes before this time")

    requires_restart_only: bool | None = Field(
        None, description="Filter only changes requiring restart"
    )
    unprocessed_only: bool | None = Field(None, description="Filter only unprocessed events")
    high_risk_only: bool | None = Field(None, description="Filter only HIGH/CRITICAL risk changes")

    file_path_pattern: str | None = Field(None, description="Filter by file path pattern")
    affected_service: str | None = Field(None, description="Filter by affected service")

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, v, info):
        if v and info.data.get("start_time") and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class ConfigurationMetrics(BaseModel):
    """Aggregated metrics for configuration management"""

    total_snapshots: int = Field(description="Total number of snapshots")
    total_change_events: int = Field(description="Total number of change events")

    snapshots_by_type: dict[str, int] = Field(description="Snapshot counts by configuration type")
    changes_by_type: dict[str, int] = Field(description="Change counts by type")
    changes_by_risk: dict[str, int] = Field(description="Change counts by risk level")

    unprocessed_events: int = Field(description="Number of unprocessed events")
    high_risk_changes: int = Field(description="Number of high/critical risk changes")
    changes_requiring_restart: int = Field(description="Number of changes requiring restart")

    avg_detection_latency_ms: float | None = Field(description="Average change detection latency")
    most_changed_files: list[dict[str, Any]] = Field(description="Files with most changes")
    most_affected_services: list[dict[str, Any]] = Field(
        description="Services most affected by changes"
    )

    period_start: datetime = Field(description="Start of metrics period")
    period_end: datetime = Field(description="End of metrics period")


class ConfigurationAlert(BaseModel):
    """Configuration change alert information"""

    event_id: UUID = Field(description="Configuration change event ID")
    device_id: UUID = Field(description="Device ID")
    device_hostname: str | None = Field(None, description="Device hostname")

    alert_type: str = Field(description="Type of alert")
    severity: str = Field(description="Alert severity")

    config_type: str = Field(description="Configuration type")
    file_path: str = Field(description="Configuration file path")
    change_type: str = Field(description="Type of change")

    risk_level: str = Field(description="Risk level")
    requires_restart: bool = Field(description="Whether restart is required")
    affected_services: list[str] = Field(description="Affected services")

    detected_at: datetime = Field(description="When change was detected")
    alert_generated_at: datetime = Field(description="When alert was generated")

    recommended_actions: list[str] = Field(description="Recommended actions")
    notification_channels: list[str] = Field(description="Channels to notify")


class ConfigurationRollbackRequest(BaseModel):
    """Request to rollback a configuration change"""

    snapshot_id: UUID = Field(..., description="Snapshot ID to rollback to")
    target_snapshot_id: UUID | None = Field(
        None, description="Target snapshot to rollback to (if different)"
    )

    reason: str = Field(..., min_length=1, description="Reason for rollback")
    notify_services: bool = Field(default=True, description="Whether to notify affected services")
    restart_services: bool = Field(
        default=False, description="Whether to restart affected services"
    )

    confirm: bool = Field(default=False, description="Confirmation that rollback should proceed")

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Rollback reason cannot be empty")
        if len(v) > 1000:
            raise ValueError("Rollback reason cannot exceed 1000 characters")
        return v.strip()

    @model_validator(mode="after")
    def validate_rollback_request_consistency(self):
        """Cross-field validation for rollback request consistency"""
        # Validate snapshot IDs are different
        if self.target_snapshot_id and self.snapshot_id == self.target_snapshot_id:
            raise ValueError("Source and target snapshot IDs cannot be the same")

        # Validate confirmation for critical operations
        if self.restart_services and not self.confirm:
            raise ValueError(
                "Rollback operations that restart services require explicit confirmation"
            )

        return self


class ConfigurationRollbackResponse(BaseModel):
    """Response for configuration rollback operation"""

    rollback_id: UUID = Field(description="Unique rollback operation ID")
    original_snapshot_id: UUID = Field(description="Original snapshot ID")
    target_snapshot_id: UUID = Field(description="Target snapshot ID")

    success: bool = Field(description="Whether rollback was successful")
    error_message: str | None = Field(description="Error message if rollback failed")

    services_notified: list[str] = Field(description="Services that were notified")
    services_restarted: list[str] = Field(description="Services that were restarted")

    rollback_duration_ms: int = Field(description="Time taken for rollback")
    completed_at: datetime = Field(description="When rollback completed")


class ConfigurationDiff(BaseModel):
    """Difference between two configuration snapshots"""

    from_snapshot_id: UUID = Field(description="Source snapshot ID")
    to_snapshot_id: UUID = Field(description="Target snapshot ID")

    file_path: str = Field(description="Configuration file path")
    config_type: str = Field(description="Configuration type")

    changes: list[dict[str, Any]] = Field(description="List of changes between snapshots")
    summary: dict[str, Any] = Field(description="Summary of changes")

    lines_added: int = Field(description="Number of lines added")
    lines_removed: int = Field(description="Number of lines removed")
    lines_modified: int = Field(description="Number of lines modified")

    risk_assessment: dict[str, Any] = Field(description="Risk assessment of changes")
    affected_services: list[str] = Field(description="Services affected by changes")
