"""
Approval Workflow Models

Database models for configuration change approval workflow system,
including change requests, approvals, and workflow state management.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class ChangeRequestStatus(str, Enum):
    """Status states for change requests."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    """Status states for individual approvals."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ChangeRequest(Base):
    """
    Change request for configuration modifications requiring approval.

    Tracks proposed configuration changes through the approval workflow,
    including impact analysis, approval status, and execution results.
    """

    __tablename__ = "change_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Basic request information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    requested_by = Column(String(255), nullable=False)  # User ID or name
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Request details
    device_id = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    config_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    proposed_content = Column(Text, nullable=False)

    # Change metadata
    change_type = Column(String(50), nullable=False)  # create, update, delete
    change_reason = Column(Text, nullable=True)
    emergency_change = Column(Boolean, default=False, nullable=False)

    # Workflow state
    status = Column(String(20), nullable=False, default=ChangeRequestStatus.PENDING.value)
    requires_approval = Column(Boolean, default=True, nullable=False)
    approvals_required = Column(Integer, default=1, nullable=False)

    # Impact analysis results
    risk_level = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH, CRITICAL
    impact_analysis = Column(JSON, nullable=True)
    affected_services = Column(JSON, nullable=True)  # List of service names

    # Execution tracking
    applied_at = Column(DateTime(timezone=True), nullable=True)
    applied_by = Column(String(255), nullable=True)
    execution_results = Column(JSON, nullable=True)
    snapshot_id = Column(PG_UUID(as_uuid=True), nullable=True)  # Created snapshot after application

    # Failure handling
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Relationships
    device = relationship("Device", back_populates="change_requests")
    approvals = relationship(
        "ChangeRequestApproval", back_populates="change_request", cascade="all, delete-orphan"
    )


class ChangeRequestApproval(Base):
    """
    Individual approval for a change request.

    Tracks approval decisions from designated approvers,
    including approval comments and timestamps.
    """

    __tablename__ = "change_request_approvals"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Approval relationship
    change_request_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("change_requests.id"), nullable=False
    )

    # Approver information
    approver_id = Column(String(255), nullable=False)  # User ID
    approver_name = Column(String(255), nullable=False)
    approver_role = Column(String(100), nullable=True)

    # Approval decision
    status = Column(String(20), nullable=False, default=ApprovalStatus.PENDING.value)
    decision_at = Column(DateTime(timezone=True), nullable=True)
    comments = Column(Text, nullable=True)

    # Approval metadata
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    notified_at = Column(DateTime(timezone=True), nullable=True)
    reminder_count = Column(Integer, default=0, nullable=False)

    # Relationships
    change_request = relationship("ChangeRequest", back_populates="approvals")


class ApprovalPolicy(Base):
    """
    Approval policy configuration for different types of changes.

    Defines approval requirements based on change characteristics,
    such as risk level, config type, or affected services.
    """

    __tablename__ = "approval_policies"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Policy identification
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)

    # Policy conditions (JSON format for flexibility)
    conditions = Column(JSON, nullable=False)  # e.g., {"risk_level": ["HIGH", "CRITICAL"]}

    # Approval requirements
    approvals_required = Column(Integer, default=1, nullable=False)
    approver_roles = Column(JSON, nullable=True)  # List of roles that can approve
    approver_users = Column(JSON, nullable=True)  # Specific users that can approve

    # Policy behavior
    auto_approve_emergency = Column(Boolean, default=False, nullable=False)
    approval_timeout_hours = Column(Integer, default=24, nullable=False)

    # Metadata
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(String(255), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class WorkflowExecution(Base):
    """
    Execution log for workflow steps and state transitions.

    Provides audit trail for workflow execution, including
    automated steps, approvals, and system actions.
    """

    __tablename__ = "workflow_executions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Workflow context
    change_request_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("change_requests.id"), nullable=False
    )
    step_name = Column(String(100), nullable=False)
    step_type = Column(String(50), nullable=False)  # approval, validation, execution, notification

    # Execution details
    started_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False)  # pending, completed, failed, skipped

    # Results and metadata
    execution_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    performer = Column(String(255), nullable=True)  # User or system component

    # Relationships
    change_request = relationship("ChangeRequest")
