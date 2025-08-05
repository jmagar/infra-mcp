"""
Configuration Compliance Models

Database models for configuration compliance rules, checks, and reporting.
Supports policy enforcement, compliance tracking, and audit reporting.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..core.database import Base


class ComplianceRule(Base):
    """
    Configuration compliance rule definition.

    Defines policies and checks that configurations must satisfy,
    with support for different rule types, severity levels, and automated checking.
    """

    __tablename__ = "compliance_rules"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Rule classification
    category = Column(
        String(100), nullable=False, index=True
    )  # security, performance, best-practices
    severity = Column(String(50), nullable=False, index=True)  # critical, high, medium, low
    rule_type = Column(String(100), nullable=False)  # regex, json-path, custom, template

    # Rule definition
    rule_definition = Column(JSONB, nullable=False)  # Rule logic and parameters
    expected_value = Column(JSONB, nullable=True)  # Expected configuration value
    violation_message = Column(Text, nullable=False)  # Message when rule fails
    remediation_guidance = Column(Text, nullable=True)  # How to fix violations

    # Scope and targeting
    target_file_patterns = Column(JSONB, nullable=False)  # File path patterns to check
    device_tags = Column(JSONB, nullable=True)  # Device tags to target (null = all devices)
    exclusions = Column(JSONB, nullable=True)  # Devices/files to exclude

    # Rule status and control
    enabled = Column(Boolean, nullable=False, default=True)
    enforce_mode = Column(
        String(50), nullable=False, default="monitor"
    )  # monitor, enforce, disabled
    auto_remediate = Column(Boolean, nullable=False, default=False)

    # Scheduling and frequency
    check_frequency = Column(
        String(100), nullable=False, default="daily"
    )  # continuous, hourly, daily, weekly
    grace_period_hours = Column(Integer, nullable=False, default=0)  # Allow time before violation

    # Metadata and tracking
    created_by = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_checked_at = Column(DateTime(timezone=True), nullable=True)

    # Rule versioning and change tracking
    version = Column(Integer, nullable=False, default=1)
    change_log = Column(JSONB, nullable=True)  # History of rule changes

    # Statistics
    total_checks = Column(Integer, nullable=False, default=0)
    violation_count = Column(Integer, nullable=False, default=0)
    last_violation_at = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    additional_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    compliance_checks = relationship(
        "ComplianceCheck", back_populates="rule", cascade="all, delete-orphan", lazy="dynamic"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_compliance_rules_category_severity", "category", "severity"),
        Index("idx_compliance_rules_enabled_frequency", "enabled", "check_frequency"),
        Index("idx_compliance_rules_created_at", "created_at"),
        Index("idx_compliance_rules_last_checked", "last_checked_at"),
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="check_compliance_rule_severity",
        ),
        CheckConstraint(
            "rule_type IN ('regex', 'json-path', 'custom', 'template', 'function')",
            name="check_compliance_rule_type",
        ),
        CheckConstraint(
            "enforce_mode IN ('monitor', 'enforce', 'disabled')",
            name="check_compliance_enforce_mode",
        ),
        CheckConstraint(
            "check_frequency IN ('continuous', 'hourly', 'daily', 'weekly', 'monthly')",
            name="check_compliance_frequency",
        ),
    )


class ComplianceCheck(Base):
    """
    Individual compliance check execution record.

    Records the result of applying a compliance rule to a specific
    configuration file on a device at a point in time.
    """

    __tablename__ = "compliance_checks"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key relationships
    rule_id = Column(
        UUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=False, index=True
    )
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("configuration_snapshots.id"), nullable=True, index=True
    )

    # Check execution details
    file_path = Column(String(1000), nullable=False, index=True)
    checked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Check results
    status = Column(String(50), nullable=False, index=True)  # pass, fail, error, skipped
    compliance_score = Column(Integer, nullable=True)  # 0-100 score for partial compliance

    # Violation details (when status = fail)
    violation_details = Column(JSONB, nullable=True)  # Detailed failure information
    violation_severity = Column(String(50), nullable=True)  # Actual severity based on context
    violation_count = Column(Integer, nullable=False, default=0)  # Number of violations found

    # Check execution metadata
    execution_time_ms = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)  # Error details when status = error

    # Remediation tracking
    remediation_suggested = Column(Boolean, nullable=False, default=False)
    remediation_applied = Column(Boolean, nullable=False, default=False)
    remediation_details = Column(JSONB, nullable=True)

    # Context and metadata
    device_metadata = Column(JSONB, nullable=True)  # Device context at check time
    file_metadata = Column(JSONB, nullable=True)  # File metadata (size, hash, etc.)
    check_metadata = Column(JSONB, nullable=True)  # Additional check context

    # Relationships
    rule = relationship("ComplianceRule", back_populates="compliance_checks")
    device = relationship("Device")
    snapshot = relationship("ConfigurationSnapshot")

    # Indexes for performance and querying
    __table_args__ = (
        Index("idx_compliance_checks_rule_device", "rule_id", "device_id"),
        Index("idx_compliance_checks_status_severity", "status", "violation_severity"),
        Index("idx_compliance_checks_checked_at", "checked_at"),
        Index("idx_compliance_checks_file_path", "file_path"),
        Index("idx_compliance_checks_device_status", "device_id", "status"),
        CheckConstraint(
            "status IN ('pass', 'fail', 'error', 'skipped')", name="check_compliance_check_status"
        ),
        CheckConstraint(
            "compliance_score IS NULL OR (compliance_score >= 0 AND compliance_score <= 100)",
            name="check_compliance_score_range",
        ),
    )


class ComplianceReport(Base):
    """
    Compliance report summary for devices, rules, or time periods.

    Pre-computed compliance statistics and summaries for efficient
    reporting and dashboard display.
    """

    __tablename__ = "compliance_reports"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Report scope and classification
    report_type = Column(String(100), nullable=False, index=True)  # device, rule, global, category
    scope_id = Column(String(255), nullable=True, index=True)  # device_id, rule_id, category, etc.
    scope_name = Column(String(255), nullable=False)  # Human-readable scope description

    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    generated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Compliance statistics
    total_checks = Column(Integer, nullable=False, default=0)
    passed_checks = Column(Integer, nullable=False, default=0)
    failed_checks = Column(Integer, nullable=False, default=0)
    error_checks = Column(Integer, nullable=False, default=0)
    skipped_checks = Column(Integer, nullable=False, default=0)

    # Compliance scores and ratings
    overall_compliance_score = Column(Integer, nullable=False, default=0)  # 0-100
    compliance_grade = Column(String(10), nullable=False)  # A, B, C, D, F
    compliance_trend = Column(
        String(50), nullable=False, default="stable"
    )  # improving, declining, stable

    # Violation breakdown
    critical_violations = Column(Integer, nullable=False, default=0)
    high_violations = Column(Integer, nullable=False, default=0)
    medium_violations = Column(Integer, nullable=False, default=0)
    low_violations = Column(Integer, nullable=False, default=0)

    # Remediation tracking
    violations_remediated = Column(Integer, nullable=False, default=0)
    auto_remediations = Column(Integer, nullable=False, default=0)
    manual_remediations = Column(Integer, nullable=False, default=0)
    pending_remediations = Column(Integer, nullable=False, default=0)

    # Report details and analysis
    top_violations = Column(JSONB, nullable=True)  # Most common violation types
    improvement_recommendations = Column(JSONB, nullable=True)  # Suggested improvements
    compliance_trends = Column(JSONB, nullable=True)  # Historical trend data

    # Report metadata
    generated_by = Column(String(255), nullable=False)
    report_version = Column(String(50), nullable=False, default="1.0")
    additional_metadata = Column("metadata", JSONB, nullable=True)

    # Indexes for efficient reporting queries
    __table_args__ = (
        Index("idx_compliance_reports_type_scope", "report_type", "scope_id"),
        Index("idx_compliance_reports_period", "period_start", "period_end"),
        Index("idx_compliance_reports_generated_at", "generated_at"),
        Index("idx_compliance_reports_compliance_score", "overall_compliance_score"),
        CheckConstraint(
            "report_type IN ('device', 'rule', 'global', 'category', 'team')",
            name="check_compliance_report_type",
        ),
        CheckConstraint(
            "overall_compliance_score >= 0 AND overall_compliance_score <= 100",
            name="check_compliance_report_score",
        ),
        CheckConstraint(
            "compliance_grade IN ('A', 'B', 'C', 'D', 'F')", name="check_compliance_grade"
        ),
        CheckConstraint(
            "compliance_trend IN ('improving', 'declining', 'stable')",
            name="check_compliance_trend",
        ),
    )


class ComplianceException(Base):
    """
    Approved exceptions to compliance rules.

    Allows specific devices, files, or time periods to be exempt
    from certain compliance rules with proper approval and tracking.
    """

    __tablename__ = "compliance_exceptions"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Exception scope
    rule_id = Column(
        UUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=False, index=True
    )
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True, index=True)
    file_pattern = Column(String(1000), nullable=True)  # Specific files or patterns

    # Exception details
    reason = Column(Text, nullable=False)  # Business justification
    approved_by = Column(String(255), nullable=False)  # Who approved the exception
    approved_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Exception validity
    valid_from = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    valid_until = Column(DateTime(timezone=True), nullable=True)  # null = permanent
    active = Column(Boolean, nullable=False, default=True, index=True)

    # Review and renewal
    review_required = Column(Boolean, nullable=False, default=True)
    review_frequency_days = Column(Integer, nullable=False, default=90)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    next_review_due = Column(DateTime(timezone=True), nullable=True, index=True)

    # Exception metadata
    risk_assessment = Column(Text, nullable=True)  # Risk analysis for the exception
    mitigation_controls = Column(JSONB, nullable=True)  # Compensating controls
    created_by = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Additional metadata
    additional_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    rule = relationship("ComplianceRule")
    device = relationship("Device")

    # Indexes for efficient exception checking
    __table_args__ = (
        Index("idx_compliance_exceptions_rule_device", "rule_id", "device_id"),
        Index("idx_compliance_exceptions_active_valid", "active", "valid_from", "valid_until"),
        Index("idx_compliance_exceptions_review_due", "next_review_due"),
        Index("idx_compliance_exceptions_approved_at", "approved_at"),
    )
