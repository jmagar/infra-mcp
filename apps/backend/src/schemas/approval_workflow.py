"""
Approval Workflow Pydantic Schemas

Request/response schemas for configuration change approval workflow,
including change requests, approvals, and workflow management.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .common import PaginatedResponse


class ChangeRequestCreate(BaseModel):
    """Schema for creating a new change request."""

    title: str = Field(..., min_length=1, max_length=255, description="Change request title")
    description: str | None = Field(None, description="Detailed description of the change")
    device_id: UUID = Field(..., description="Target device UUID")
    config_type: str = Field(..., min_length=1, max_length=50, description="Configuration type")
    file_path: str = Field(..., min_length=1, max_length=500, description="Target file path")
    proposed_content: str = Field(..., min_length=1, description="Proposed configuration content")
    change_type: str = Field(..., description="Type of change: create, update, delete")
    change_reason: str | None = Field(None, description="Reason for the change")
    emergency_change: bool = Field(False, description="Mark as emergency change")


class ChangeRequestUpdate(BaseModel):
    """Schema for updating an existing change request."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None)
    proposed_content: str | None = Field(None, min_length=1)
    change_reason: str | None = Field(None)
    emergency_change: bool | None = Field(None)


class ChangeRequestApprovalCreate(BaseModel):
    """Schema for creating an approval decision."""

    status: str = Field(..., description="Approval status: approved, rejected")
    comments: str | None = Field(None, description="Approval comments")


class ChangeRequestApprovalResponse(BaseModel):
    """Schema for approval response."""

    id: UUID
    change_request_id: UUID
    approver_id: str
    approver_name: str
    approver_role: str | None
    status: str
    decision_at: datetime | None
    comments: str | None
    created_at: datetime
    notified_at: datetime | None
    reminder_count: int

    class Config:
        from_attributes = True


class ChangeRequestResponse(BaseModel):
    """Schema for change request response."""

    id: UUID
    title: str
    description: str | None
    requested_by: str
    created_at: datetime
    updated_at: datetime

    # Request details
    device_id: UUID
    config_type: str
    file_path: str
    proposed_content: str

    # Change metadata
    change_type: str
    change_reason: str | None
    emergency_change: bool

    # Workflow state
    status: str
    requires_approval: bool
    approvals_required: int

    # Impact analysis results
    risk_level: str | None
    impact_analysis: dict[str, Any] | None
    affected_services: list[str] | None

    # Execution tracking
    applied_at: datetime | None
    applied_by: str | None
    execution_results: dict[str, Any] | None
    snapshot_id: UUID | None

    # Failure handling
    failure_reason: str | None
    retry_count: int

    # Related data
    approvals: list[ChangeRequestApprovalResponse] = []

    class Config:
        from_attributes = True


class ChangeRequestList(PaginatedResponse):
    """Paginated list of change requests."""

    items: list[ChangeRequestResponse]


class ApprovalPolicyCreate(BaseModel):
    """Schema for creating an approval policy."""

    name: str = Field(..., min_length=1, max_length=255, description="Policy name")
    description: str | None = Field(None, description="Policy description")
    conditions: dict[str, Any] = Field(..., description="Policy matching conditions")
    approvals_required: int = Field(1, ge=1, le=10, description="Number of approvals required")
    approver_roles: list[str] | None = Field(None, description="List of approver roles")
    approver_users: list[str] | None = Field(None, description="List of specific approver users")
    auto_approve_emergency: bool = Field(False, description="Auto-approve emergency changes")
    approval_timeout_hours: int = Field(24, ge=1, le=168, description="Approval timeout in hours")


class ApprovalPolicyUpdate(BaseModel):
    """Schema for updating an approval policy."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None)
    active: bool | None = Field(None)
    conditions: dict[str, Any] | None = Field(None)
    approvals_required: int | None = Field(None, ge=1, le=10)
    approver_roles: list[str] | None = Field(None)
    approver_users: list[str] | None = Field(None)
    auto_approve_emergency: bool | None = Field(None)
    approval_timeout_hours: int | None = Field(None, ge=1, le=168)


class ApprovalPolicyResponse(BaseModel):
    """Schema for approval policy response."""

    id: UUID
    name: str
    description: str | None
    active: bool
    conditions: dict[str, Any]
    approvals_required: int
    approver_roles: list[str] | None
    approver_users: list[str] | None
    auto_approve_emergency: bool
    approval_timeout_hours: int
    created_at: datetime
    created_by: str
    updated_at: datetime

    class Config:
        from_attributes = True


class ApprovalPolicyList(PaginatedResponse):
    """Paginated list of approval policies."""

    items: list[ApprovalPolicyResponse]


class WorkflowExecutionResponse(BaseModel):
    """Schema for workflow execution response."""

    id: UUID
    change_request_id: UUID
    step_name: str
    step_type: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    execution_data: dict[str, Any] | None
    error_message: str | None
    performer: str | None

    class Config:
        from_attributes = True


class WorkflowExecutionList(PaginatedResponse):
    """Paginated list of workflow executions."""

    items: list[WorkflowExecutionResponse]


class ChangeRequestFilter(BaseModel):
    """Filter criteria for change requests."""

    device_ids: list[UUID] | None = Field(None, description="Filter by device IDs")
    statuses: list[str] | None = Field(None, description="Filter by status")
    risk_levels: list[str] | None = Field(None, description="Filter by risk level")
    config_types: list[str] | None = Field(None, description="Filter by config type")
    requested_by: str | None = Field(None, description="Filter by requester")
    emergency_only: bool | None = Field(None, description="Show only emergency changes")
    pending_approval: bool | None = Field(None, description="Show only changes pending approval")
    hours_back: int | None = Field(
        None, ge=1, le=8760, description="Show changes from last N hours"
    )


class ApprovalWorkflowMetrics(BaseModel):
    """Metrics for approval workflow performance."""

    total_requests: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    applied_requests: int
    failed_requests: int
    emergency_requests: int

    average_approval_time_hours: float | None
    approval_rate: float  # Percentage of approved vs total decided

    requests_by_status: dict[str, int]
    requests_by_risk_level: dict[str, int]
    requests_by_config_type: dict[str, int]

    top_requesters: list[dict[str, Any]]  # Top users by request count
    top_approvers: list[dict[str, Any]]  # Top approvers by approval count


class BulkApprovalRequest(BaseModel):
    """Schema for bulk approval operations."""

    change_request_ids: list[UUID] = Field(..., min_items=1, max_items=50)
    action: str = Field(..., description="Action: approve, reject, cancel")
    comments: str | None = Field(None, description="Comments for all approvals")


class BulkApprovalResponse(BaseModel):
    """Schema for bulk approval response."""

    total_requests: int
    successful_operations: int
    failed_operations: int
    results: list[dict[str, Any]]  # Individual operation results
