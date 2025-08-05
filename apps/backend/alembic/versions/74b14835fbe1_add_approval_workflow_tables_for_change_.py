"""Add approval workflow tables for change request management

Revision ID: 74b14835fbe1
Revises: 440db6e2f1df
Create Date: 2025-08-04 18:19:36.970464

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "74b14835fbe1"
down_revision: Union[str, Sequence[str], None] = "440db6e2f1df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create approval_policies table
    op.create_table(
        "approval_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("approvals_required", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approver_roles", sa.JSON(), nullable=True),
        sa.Column("approver_users", sa.JSON(), nullable=True),
        sa.Column("auto_approve_emergency", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("approval_timeout_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create change_requests table
    op.create_table(
        "change_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_type", sa.String(50), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("proposed_content", sa.Text(), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("emergency_change", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("approvals_required", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("impact_analysis", sa.JSON(), nullable=True),
        sa.Column("affected_services", sa.JSON(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.String(255), nullable=True),
        sa.Column("execution_results", sa.JSON(), nullable=True),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create change_request_approvals table
    op.create_table(
        "change_request_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_id", sa.String(255), nullable=False),
        sa.Column("approver_name", sa.String(255), nullable=False),
        sa.Column("approver_role", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["change_request_id"],
            ["change_requests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create workflow_executions table
    op.create_table(
        "workflow_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_name", sa.String(100), nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("execution_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("performer", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["change_request_id"],
            ["change_requests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for better query performance
    op.create_index("ix_change_requests_device_id", "change_requests", ["device_id"])
    op.create_index("ix_change_requests_status", "change_requests", ["status"])
    op.create_index("ix_change_requests_created_at", "change_requests", ["created_at"])
    op.create_index("ix_change_requests_requested_by", "change_requests", ["requested_by"])
    op.create_index("ix_change_requests_risk_level", "change_requests", ["risk_level"])
    op.create_index(
        "ix_change_request_approvals_change_request_id",
        "change_request_approvals",
        ["change_request_id"],
    )
    op.create_index(
        "ix_change_request_approvals_approver_id", "change_request_approvals", ["approver_id"]
    )
    op.create_index(
        "ix_workflow_executions_change_request_id", "workflow_executions", ["change_request_id"]
    )
    op.create_index("ix_workflow_executions_started_at", "workflow_executions", ["started_at"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_workflow_executions_started_at", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_change_request_id", table_name="workflow_executions")
    op.drop_index("ix_change_request_approvals_approver_id", table_name="change_request_approvals")
    op.drop_index(
        "ix_change_request_approvals_change_request_id", table_name="change_request_approvals"
    )
    op.drop_index("ix_change_requests_risk_level", table_name="change_requests")
    op.drop_index("ix_change_requests_requested_by", table_name="change_requests")
    op.drop_index("ix_change_requests_created_at", table_name="change_requests")
    op.drop_index("ix_change_requests_status", table_name="change_requests")
    op.drop_index("ix_change_requests_device_id", table_name="change_requests")

    # Drop tables (in reverse order of creation due to foreign key constraints)
    op.drop_table("workflow_executions")
    op.drop_table("change_request_approvals")
    op.drop_table("change_requests")
    op.drop_table("approval_policies")
