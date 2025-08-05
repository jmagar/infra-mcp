"""
Configuration Compliance Schemas

Pydantic schemas for configuration compliance checking and reporting.
Provides validation and serialization for compliance rules, checks, reports, and exceptions.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ComplianceRuleBase(BaseModel):
    """Base schema for compliance rule data."""

    name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    description: str | None = Field(None, description="Rule description")
    category: str = Field(..., description="Rule category (security, performance, best-practices)")
    severity: str = Field(..., description="Rule severity (critical, high, medium, low)")
    rule_type: str = Field(
        ..., description="Rule type (regex, json-path, custom, template, function)"
    )

    rule_definition: dict[str, Any] = Field(..., description="Rule logic and parameters")
    expected_value: dict[str, Any] | None = Field(None, description="Expected configuration value")
    violation_message: str = Field(..., description="Message when rule fails")
    remediation_guidance: str | None = Field(None, description="How to fix violations")

    target_file_patterns: list[str] = Field(..., description="File path patterns to check")
    device_tags: list[str] | None = Field(
        None, description="Device tags to target (null = all devices)"
    )
    exclusions: dict[str, Any] | None = Field(None, description="Devices/files to exclude")

    enabled: bool = Field(default=True, description="Whether rule is enabled")
    enforce_mode: str = Field(default="monitor", description="Rule enforcement mode")
    auto_remediate: bool = Field(default=False, description="Whether to auto-remediate violations")

    check_frequency: str = Field(default="daily", description="Check frequency")
    grace_period_hours: int = Field(default=0, ge=0, description="Grace period before violation")

    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    @validator("category")
    def validate_category(cls, v):
        allowed = ["security", "performance", "best-practices", "compliance", "operational"]
        if v not in allowed:
            raise ValueError(f"Category must be one of: {allowed}")
        return v

    @validator("severity")
    def validate_severity(cls, v):
        allowed = ["critical", "high", "medium", "low"]
        if v not in allowed:
            raise ValueError(f"Severity must be one of: {allowed}")
        return v

    @validator("rule_type")
    def validate_rule_type(cls, v):
        allowed = ["regex", "json-path", "custom", "template", "function"]
        if v not in allowed:
            raise ValueError(f"Rule type must be one of: {allowed}")
        return v

    @validator("enforce_mode")
    def validate_enforce_mode(cls, v):
        allowed = ["monitor", "enforce", "disabled"]
        if v not in allowed:
            raise ValueError(f"Enforce mode must be one of: {allowed}")
        return v

    @validator("check_frequency")
    def validate_check_frequency(cls, v):
        allowed = ["continuous", "hourly", "daily", "weekly", "monthly"]
        if v not in allowed:
            raise ValueError(f"Check frequency must be one of: {allowed}")
        return v


class ComplianceRuleCreate(ComplianceRuleBase):
    """Schema for creating a new compliance rule."""

    created_by: str = Field(..., description="User who created the rule")


class ComplianceRuleUpdate(BaseModel):
    """Schema for updating an existing compliance rule."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    severity: str | None = None
    rule_type: str | None = None

    rule_definition: dict[str, Any] | None = None
    expected_value: dict[str, Any] | None = None
    violation_message: str | None = None
    remediation_guidance: str | None = None

    target_file_patterns: list[str] | None = None
    device_tags: list[str] | None = None
    exclusions: dict[str, Any] | None = None

    enabled: bool | None = None
    enforce_mode: str | None = None
    auto_remediate: bool | None = None

    check_frequency: str | None = None
    grace_period_hours: int | None = None

    metadata: dict[str, Any] | None = None


class ComplianceRuleResponse(ComplianceRuleBase):
    """Schema for compliance rule API responses."""

    id: UUID
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_checked_at: datetime | None

    total_checks: int
    violation_count: int
    last_violation_at: datetime | None
    change_log: dict[str, Any] | None

    class Config:
        from_attributes = True


class ComplianceCheckBase(BaseModel):
    """Base schema for compliance check data."""

    file_path: str = Field(..., description="Configuration file path")
    status: str = Field(..., description="Check status (pass, fail, error, skipped)")
    compliance_score: int | None = Field(None, ge=0, le=100, description="Compliance score (0-100)")

    violation_details: dict[str, Any] | None = Field(
        None, description="Detailed failure information"
    )
    violation_severity: str | None = Field(None, description="Actual severity based on context")
    violation_count: int = Field(default=0, ge=0, description="Number of violations found")

    execution_time_ms: int = Field(default=0, ge=0, description="Check execution time")
    error_message: str | None = Field(None, description="Error details when status = error")

    remediation_suggested: bool = Field(
        default=False, description="Whether remediation was suggested"
    )
    remediation_applied: bool = Field(default=False, description="Whether remediation was applied")
    remediation_details: dict[str, Any] | None = Field(None, description="Remediation details")

    device_metadata: dict[str, Any] | None = Field(None, description="Device context at check time")
    file_metadata: dict[str, Any] | None = Field(None, description="File metadata")
    check_metadata: dict[str, Any] | None = Field(None, description="Additional check context")

    @validator("status")
    def validate_status(cls, v):
        allowed = ["pass", "fail", "error", "skipped"]
        if v not in allowed:
            raise ValueError(f"Status must be one of: {allowed}")
        return v


class ComplianceCheckResponse(ComplianceCheckBase):
    """Schema for compliance check API responses."""

    id: UUID
    rule_id: UUID
    device_id: UUID
    snapshot_id: UUID | None
    checked_at: datetime

    # Include related data
    rule_name: str | None = None
    device_name: str | None = None

    class Config:
        from_attributes = True


class ComplianceReportBase(BaseModel):
    """Base schema for compliance report data."""

    report_type: str = Field(..., description="Report type (device, rule, global, category)")
    scope_id: str | None = Field(None, description="Scope identifier")
    scope_name: str = Field(..., description="Human-readable scope description")

    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")

    total_checks: int = Field(default=0, ge=0)
    passed_checks: int = Field(default=0, ge=0)
    failed_checks: int = Field(default=0, ge=0)
    error_checks: int = Field(default=0, ge=0)
    skipped_checks: int = Field(default=0, ge=0)

    overall_compliance_score: int = Field(
        default=0, ge=0, le=100, description="Overall compliance score"
    )
    compliance_grade: str = Field(..., description="Compliance grade (A, B, C, D, F)")
    compliance_trend: str = Field(default="stable", description="Compliance trend")

    critical_violations: int = Field(default=0, ge=0)
    high_violations: int = Field(default=0, ge=0)
    medium_violations: int = Field(default=0, ge=0)
    low_violations: int = Field(default=0, ge=0)

    violations_remediated: int = Field(default=0, ge=0)
    auto_remediations: int = Field(default=0, ge=0)
    manual_remediations: int = Field(default=0, ge=0)
    pending_remediations: int = Field(default=0, ge=0)

    top_violations: list[dict[str, Any]] | None = Field(None, description="Most common violations")
    improvement_recommendations: list[dict[str, Any]] | None = Field(
        None, description="Improvement suggestions"
    )
    compliance_trends: dict[str, Any] | None = Field(None, description="Historical trend data")

    generated_by: str = Field(..., description="Who generated the report")
    report_version: str = Field(default="1.0", description="Report version")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    @validator("report_type")
    def validate_report_type(cls, v):
        allowed = ["device", "rule", "global", "category", "team"]
        if v not in allowed:
            raise ValueError(f"Report type must be one of: {allowed}")
        return v

    @validator("compliance_grade")
    def validate_compliance_grade(cls, v):
        allowed = ["A", "B", "C", "D", "F"]
        if v not in allowed:
            raise ValueError(f"Compliance grade must be one of: {allowed}")
        return v

    @validator("compliance_trend")
    def validate_compliance_trend(cls, v):
        allowed = ["improving", "declining", "stable"]
        if v not in allowed:
            raise ValueError(f"Compliance trend must be one of: {allowed}")
        return v


class ComplianceReportResponse(ComplianceReportBase):
    """Schema for compliance report API responses."""

    id: UUID
    generated_at: datetime

    class Config:
        from_attributes = True


class ComplianceExceptionBase(BaseModel):
    """Base schema for compliance exception data."""

    reason: str = Field(..., description="Business justification for exception")
    approved_by: str = Field(..., description="Who approved the exception")

    valid_from: datetime = Field(..., description="Exception validity start")
    valid_until: datetime | None = Field(
        None, description="Exception validity end (null = permanent)"
    )
    active: bool = Field(default=True, description="Whether exception is active")

    review_required: bool = Field(default=True, description="Whether periodic review is required")
    review_frequency_days: int = Field(default=90, ge=1, description="Review frequency in days")

    risk_assessment: str | None = Field(None, description="Risk analysis for the exception")
    mitigation_controls: dict[str, Any] | None = Field(None, description="Compensating controls")

    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ComplianceExceptionCreate(ComplianceExceptionBase):
    """Schema for creating a new compliance exception."""

    rule_id: UUID = Field(..., description="Rule to create exception for")
    device_id: UUID | None = Field(None, description="Specific device (null = all devices)")
    file_pattern: str | None = Field(None, description="Specific file pattern")
    created_by: str = Field(..., description="User who created the exception")


class ComplianceExceptionUpdate(BaseModel):
    """Schema for updating an existing compliance exception."""

    reason: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    active: bool | None = None

    review_required: bool | None = None
    review_frequency_days: int | None = None

    risk_assessment: str | None = None
    mitigation_controls: dict[str, Any] | None = None

    metadata: dict[str, Any] | None = None


class ComplianceExceptionResponse(ComplianceExceptionBase):
    """Schema for compliance exception API responses."""

    id: UUID
    rule_id: UUID
    device_id: UUID | None
    file_pattern: str | None

    approved_at: datetime
    created_by: str
    created_at: datetime
    updated_at: datetime

    last_reviewed_at: datetime | None
    next_review_due: datetime | None

    # Include related data
    rule_name: str | None = None
    device_name: str | None = None

    class Config:
        from_attributes = True


class ComplianceCheckRequest(BaseModel):
    """Schema for requesting compliance checks."""

    rule_ids: list[UUID] | None = Field(
        None, description="Specific rules to check (null = all enabled)"
    )
    device_ids: list[UUID] | None = Field(
        None, description="Specific devices to check (null = all)"
    )
    file_patterns: list[str] | None = Field(None, description="Specific file patterns to check")

    force_refresh: bool = Field(default=False, description="Force fresh configuration snapshots")
    async_execution: bool = Field(default=True, description="Execute checks asynchronously")

    metadata: dict[str, Any] | None = Field(None, description="Additional request metadata")


class ComplianceCheckBulkResponse(BaseModel):
    """Schema for bulk compliance check responses."""

    request_id: str = Field(..., description="Unique request identifier")
    status: str = Field(..., description="Request status (pending, running, completed, failed)")

    total_rules: int = Field(default=0, ge=0, description="Total rules to check")
    total_devices: int = Field(default=0, ge=0, description="Total devices to check")
    total_files: int = Field(default=0, ge=0, description="Total files to check")

    checks_completed: int = Field(default=0, ge=0, description="Checks completed")
    checks_passed: int = Field(default=0, ge=0, description="Checks passed")
    checks_failed: int = Field(default=0, ge=0, description="Checks failed")
    checks_error: int = Field(default=0, ge=0, description="Checks with errors")

    started_at: datetime | None = Field(None, description="When checks started")
    completed_at: datetime | None = Field(None, description="When checks completed")
    estimated_completion: datetime | None = Field(None, description="Estimated completion time")

    error_message: str | None = Field(None, description="Error message if failed")
    results_url: str | None = Field(None, description="URL to retrieve detailed results")

    metadata: dict[str, Any] | None = Field(None, description="Additional response metadata")


class ComplianceDashboardResponse(BaseModel):
    """Schema for compliance dashboard summary."""

    overall_compliance_score: int = Field(..., ge=0, le=100, description="Overall compliance score")
    compliance_grade: str = Field(..., description="Overall compliance grade")
    compliance_trend: str = Field(..., description="Compliance trend")

    total_devices: int = Field(default=0, ge=0, description="Total devices monitored")
    compliant_devices: int = Field(default=0, ge=0, description="Fully compliant devices")
    non_compliant_devices: int = Field(default=0, ge=0, description="Non-compliant devices")

    total_rules: int = Field(default=0, ge=0, description="Total active rules")
    critical_violations: int = Field(default=0, ge=0, description="Critical violations")
    high_violations: int = Field(default=0, ge=0, description="High severity violations")
    medium_violations: int = Field(default=0, ge=0, description="Medium severity violations")
    low_violations: int = Field(default=0, ge=0, description="Low severity violations")

    recent_checks: list[ComplianceCheckResponse] = Field(
        default=[], description="Recent compliance checks"
    )
    top_violations: list[dict[str, Any]] = Field(default=[], description="Most common violations")
    compliance_by_category: dict[str, int] = Field(
        default={}, description="Compliance scores by category"
    )

    last_updated: datetime = Field(..., description="When dashboard was last updated")

    class Config:
        schema_extra = {
            "example": {
                "overall_compliance_score": 85,
                "compliance_grade": "B",
                "compliance_trend": "improving",
                "total_devices": 25,
                "compliant_devices": 20,
                "non_compliant_devices": 5,
                "total_rules": 50,
                "critical_violations": 2,
                "high_violations": 8,
                "medium_violations": 15,
                "low_violations": 25,
                "recent_checks": [],
                "top_violations": [
                    {
                        "rule_name": "SSL Certificate Expiry Check",
                        "violation_count": 5,
                        "severity": "high",
                    }
                ],
                "compliance_by_category": {"security": 78, "performance": 92, "best-practices": 88},
                "last_updated": "2025-01-08T10:30:00Z",
            }
        }
