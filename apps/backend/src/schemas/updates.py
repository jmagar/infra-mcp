"""
System updates-related Pydantic schemas for request/response validation.
"""

from datetime import UTC, date, datetime

from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from apps.backend.src.schemas.common import PaginatedResponse


class SystemUpdateBase(BaseModel):
    """Base system update schema with common fields"""

    package_type: str = Field(..., max_length=50, description="Package type")
    package_name: str = Field(..., min_length=1, max_length=255, description="Package name")
    current_version: str | None = Field(
        None, max_length=255, description="Current package version"
    )
    available_version: str | None = Field(
        None, max_length=255, description="Available package version"
    )
    update_priority: str = Field(default="normal", description="Update priority level")
    security_update: bool = Field(default=False, description="Whether this is a security update")
    release_date: date | None = Field(None, description="Package release date")
    description: str | None = Field(None, description="Update description")
    changelog: str | None = Field(None, description="Package changelog")
    update_status: str = Field(default="available", description="Update status")
    last_checked: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last check timestamp"
    )
    extra_metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("package_type")
    @classmethod
    def validate_package_type(cls, v: str) -> str:
        valid_types = [
            "system",
            "container",
            "snap",
            "flatpak",
            "pip",
            "npm",
            "apt",
            "yum",
            "dnf",
            "zypper",
            "pacman",
            "homebrew",
            "custom",
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Package type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @field_validator("update_priority")
    @classmethod
    def validate_update_priority(cls, v: str) -> str:
        valid_priorities = ["critical", "high", "normal", "low"]
        if v.lower() not in valid_priorities:
            raise ValueError(f"Update priority must be one of: {', '.join(valid_priorities)}")
        return v.lower()

    @field_validator("update_status")
    @classmethod
    def validate_update_status(cls, v: str) -> str:
        valid_statuses = ["available", "pending", "installed", "failed", "skipped", "ignored"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Update status must be one of: {', '.join(valid_statuses)}")
        return v.lower()


class SystemUpdateCreate(SystemUpdateBase):
    """Schema for creating a new system update record"""

    device_id: UUID = Field(..., description="Device UUID")


class SystemUpdateUpdate(BaseModel):
    """Schema for updating system update record"""

    current_version: str | None = Field(None, description="Updated current version")
    available_version: str | None = Field(None, description="Updated available version")
    update_priority: str | None = Field(None, description="Updated priority")
    security_update: bool | None = Field(None, description="Updated security flag")
    description: str | None = Field(None, description="Updated description")
    changelog: str | None = Field(None, description="Updated changelog")
    update_status: str | None = Field(None, description="Updated status")
    extra_metadata: dict[str, Any] | None = Field(None, description="Updated metadata")


class SystemUpdateResponse(SystemUpdateBase):
    """Schema for system update response data"""

    id: UUID = Field(description="Update record UUID")
    device_id: UUID = Field(description="Device UUID")

    # Computed fields
    hostname: str | None = Field(None, description="Device hostname")
    days_since_release: int | None = Field(None, description="Days since package release")
    update_size_mb: float | None = Field(None, description="Update size in MB")
    requires_reboot: bool | None = Field(None, description="Whether update requires reboot")
    has_dependencies: bool | None = Field(None, description="Whether update has dependencies")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class SystemUpdateList(PaginatedResponse[SystemUpdateResponse]):
    """Paginated list of system updates"""

    pass


class UpdateSummary(BaseModel):
    """Update summary for a device"""

    device_id: UUID
    hostname: str
    total_updates: int = Field(description="Total available updates")
    security_updates: int = Field(description="Security updates available")
    critical_updates: int = Field(description="Critical updates available")
    high_priority_updates: int = Field(description="High priority updates available")
    updates_by_type: dict[str, int] = Field(description="Update count by package type")
    pending_reboot: bool = Field(description="Whether device needs reboot for updates")
    last_update_check: datetime = Field(description="Last update check timestamp")
    last_update_installed: datetime | None = Field(description="Last update installation")
    update_policy: str | None = Field(description="Device update policy")
    auto_updates_enabled: bool = Field(description="Whether auto-updates are enabled")

    class Config:
        from_attributes = True


class UpdateHealthOverview(BaseModel):
    """Update health overview across all devices"""

    total_devices: int = Field(description="Total number of devices")
    devices_with_updates: int = Field(description="Devices with available updates")
    devices_up_to_date: int = Field(description="Devices that are up to date")
    total_available_updates: int = Field(description="Total available updates")
    total_security_updates: int = Field(description="Total security updates")
    total_critical_updates: int = Field(description="Total critical updates")
    devices_needing_reboot: int = Field(description="Devices needing reboot")
    updates_by_package_type: dict[str, int] = Field(description="Updates by package type")
    outdated_devices: list[str] = Field(description="Most outdated devices")
    recent_installations: int = Field(description="Recent update installations")
    failed_installations: int = Field(description="Failed update installations")
    update_compliance_score: float = Field(description="Overall update compliance score")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Report timestamp")


class UpdateInstallation(BaseModel):
    """Update installation request"""

    installation_id: str = Field(description="Installation identifier")
    device_id: UUID = Field(description="Target device UUID")
    update_ids: list[UUID] = Field(description="List of update record UUIDs to install")
    install_type: str = Field(default="standard", description="Installation type")
    schedule_time: datetime | None = Field(None, description="Scheduled installation time")
    reboot_if_required: bool = Field(default=False, description="Reboot if required")
    backup_before_install: bool = Field(
        default=True, description="Create backup before installation"
    )
    test_mode: bool = Field(default=False, description="Run in test mode")
    initiated_by: str = Field(description="User who initiated installation")
    initiated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Installation request time"
    )

    @field_validator("install_type")
    @classmethod
    def validate_install_type(cls, v: str) -> str:
        valid_types = ["standard", "force", "simulate", "download_only"]
        if v.lower() not in valid_types:
            raise ValueError(f"Install type must be one of: {', '.join(valid_types)}")
        return v.lower()


class UpdateInstallationResult(BaseModel):
    """Update installation result"""

    installation_id: str = Field(description="Installation identifier")
    device_id: UUID = Field(description="Device UUID")
    status: str = Field(description="Installation status")
    start_time: datetime = Field(description="Installation start time")
    end_time: datetime | None = Field(description="Installation end time")
    duration_seconds: int | None = Field(description="Installation duration")
    updates_attempted: int = Field(description="Number of updates attempted")
    updates_successful: int = Field(description="Number of successful updates")
    updates_failed: int = Field(description="Number of failed updates")
    updates_skipped: int = Field(description="Number of skipped updates")
    reboot_required: bool = Field(description="Whether reboot is required")
    reboot_performed: bool = Field(description="Whether reboot was performed")
    backup_created: bool = Field(description="Whether backup was created")
    error_message: str | None = Field(description="Error message if installation failed")
    installation_log: list[str] = Field(
        default_factory=list, description="Detailed installation log"
    )

    class Config:
        from_attributes = True


class UpdatePolicy(BaseModel):
    """Update policy configuration"""

    policy_id: str = Field(description="Policy identifier")
    policy_name: str = Field(description="Policy name")
    description: str = Field(description="Policy description")
    auto_install_security: bool = Field(default=True, description="Auto-install security updates")
    auto_install_critical: bool = Field(default=False, description="Auto-install critical updates")
    auto_install_normal: bool = Field(default=False, description="Auto-install normal updates")
    allowed_update_windows: list[str] = Field(description="Allowed update time windows")
    excluded_packages: list[str] = Field(
        default_factory=list, description="Packages to exclude from updates"
    )
    required_packages: list[str] = Field(
        default_factory=list, description="Packages that must be updated"
    )
    max_concurrent_updates: int = Field(ge=1, description="Maximum concurrent updates")
    backup_before_update: bool = Field(default=True, description="Create backup before updates")
    reboot_window: str | None = Field(None, description="Allowed reboot window")
    auto_reboot: bool = Field(default=False, description="Automatically reboot if required")
    rollback_on_failure: bool = Field(default=True, description="Rollback on update failure")
    notification_settings: dict[str, bool] = Field(description="Notification preferences")
    testing_period_days: int = Field(default=0, description="Testing period before installation")
    compliance_reporting: bool = Field(default=True, description="Enable compliance reporting")
    is_active: bool = Field(default=True, description="Whether policy is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Policy creation time"
    )


class UpdateSchedule(BaseModel):
    """Update schedule configuration"""

    schedule_id: str = Field(description="Schedule identifier")
    schedule_name: str = Field(description="Schedule name")
    device_ids: list[UUID] = Field(description="Target device UUIDs")
    update_types: list[str] = Field(description="Types of updates to include")
    cron_expression: str = Field(description="Cron schedule expression")
    max_updates_per_run: int | None = Field(
        None, description="Maximum updates per scheduled run"
    )
    stagger_installations: bool = Field(
        default=True, description="Stagger installations across devices"
    )
    maintenance_window_hours: int = Field(ge=1, description="Maintenance window duration")
    pre_update_commands: list[str] = Field(
        default_factory=list, description="Commands to run before updates"
    )
    post_update_commands: list[str] = Field(
        default_factory=list, description="Commands to run after updates"
    )
    notification_emails: list[str] = Field(default_factory=list, description="Email notifications")
    rollback_on_failure: bool = Field(default=True, description="Rollback on failure")
    is_active: bool = Field(default=True, description="Whether schedule is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Schedule creation time"
    )
    last_run: datetime | None = Field(None, description="Last execution time")
    next_run: datetime | None = Field(None, description="Next scheduled execution")


class VulnerabilityInfo(BaseModel):
    """Security vulnerability information"""

    vulnerability_id: str = Field(description="Vulnerability identifier (CVE, etc.)")
    severity: str = Field(description="Vulnerability severity")
    score: float | None = Field(None, ge=0, le=10, description="CVSS score")
    description: str = Field(description="Vulnerability description")
    affected_packages: list[str] = Field(description="Affected package names")
    fixed_versions: list[str] = Field(description="Fixed package versions")
    published_date: date | None = Field(None, description="Vulnerability publication date")
    discovery_date: date | None = Field(None, description="Vulnerability discovery date")
    exploit_available: bool = Field(
        default=False, description="Whether exploit is publicly available"
    )
    references: list[str] = Field(default_factory=list, description="Reference URLs")
    mitigation_steps: list[str] = Field(
        default_factory=list, description="Mitigation recommendations"
    )

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid_severities = ["critical", "high", "medium", "low", "informational"]
        if v.lower() not in valid_severities:
            raise ValueError(f"Severity must be one of: {', '.join(valid_severities)}")
        return v.lower()


class ComplianceReport(BaseModel):
    """Update compliance report"""

    report_id: str = Field(description="Report identifier")
    report_name: str = Field(description="Report name")
    generated_at: datetime = Field(description="Report generation time")
    reporting_period: str = Field(description="Reporting time period")
    total_devices: int = Field(description="Total devices assessed")
    compliant_devices: int = Field(description="Compliant devices count")
    non_compliant_devices: int = Field(description="Non-compliant devices count")
    compliance_percentage: float = Field(description="Overall compliance percentage")
    security_updates_pending: int = Field(description="Security updates pending")
    critical_updates_pending: int = Field(description="Critical updates pending")
    devices_needing_reboot: int = Field(description="Devices needing reboot")
    policy_violations: list[dict[str, Any]] = Field(description="Policy violations")
    top_missing_updates: list[dict[str, Any]] = Field(description="Most common missing updates")
    compliance_trends: dict[str, list[float]] = Field(description="Compliance trends over time")
    recommendations: list[str] = Field(description="Compliance recommendations")


class UpdateFilter(BaseModel):
    """Update filtering parameters"""

    device_ids: list[UUID] | None = Field(description="Filter by device IDs")
    package_types: list[str] | None = Field(description="Filter by package types")
    update_priorities: list[str] | None = Field(description="Filter by update priorities")
    update_statuses: list[str] | None = Field(description="Filter by update statuses")
    security_updates_only: bool | None = Field(description="Show only security updates")
    available_since: date | None = Field(description="Updates available since date")
    package_name_pattern: str | None = Field(description="Package name pattern (regex)")
    requires_reboot: bool | None = Field(description="Filter updates requiring reboot")
    has_vulnerabilities: bool | None = Field(description="Filter updates fixing vulnerabilities")


class UpdateMetrics(BaseModel):
    """Update metrics for a device"""

    device_id: UUID
    hostname: str
    update_compliance_score: float = Field(description="Update compliance score")
    total_packages: int = Field(description="Total installed packages")
    outdated_packages: int = Field(description="Outdated packages count")
    security_updates_pending: int = Field(description="Pending security updates")
    days_since_last_update: int = Field(description="Days since last update")
    auto_update_enabled: bool = Field(description="Auto-update status")
    update_success_rate: float = Field(description="Update installation success rate")
    average_update_delay_days: float = Field(description="Average delay in applying updates")
    vulnerability_exposure: int = Field(description="Number of known vulnerabilities")
    patch_level: str = Field(description="Overall patch level status")
    last_updated: datetime = Field(description="Last metrics update")

    class Config:
        from_attributes = True
