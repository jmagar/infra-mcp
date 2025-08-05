"""Add notification system tables for Gotify integration

Revision ID: fccb9002fd60
Revises: 4e7e588d185a
Create Date: 2025-08-04 20:13:15.250929

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fccb9002fd60"
down_revision: Union[str, Sequence[str], None] = "4e7e588d185a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create gotify_notification_config table
    op.create_table(
        "gotify_notification_config",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("app_token", sa.String(length=255), nullable=False),
        sa.Column("gotify_url", sa.String(length=500), nullable=True),
        sa.Column("priority_mapping", sa.JSON(), nullable=False),
        sa.Column("rate_limit_per_hour", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_success", sa.Boolean(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create configuration_alerts table
    op.create_table(
        "configuration_alerts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("device_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_path", sa.String(length=1000), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("alert_data", sa.JSON(), nullable=False),
        sa.Column("gotify_message_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("delivery_attempts", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("delivery_time_ms", sa.Integer(), nullable=True),
        sa.Column("config_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_id"],
            ["gotify_notification_config.id"],
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create alert_suppressions table
    op.create_table(
        "alert_suppressions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("device_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("configuration_path_pattern", sa.String(length=1000), nullable=True),
        sa.Column("change_type", sa.String(length=50), nullable=True),
        sa.Column("min_risk_level", sa.String(length=20), nullable=True),
        sa.Column("suppression_window_minutes", sa.JSON(), nullable=False),
        sa.Column("max_alerts_in_window", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create indexes for better performance
    op.create_index("ix_configuration_alerts_device_id", "configuration_alerts", ["device_id"])
    op.create_index("ix_configuration_alerts_status", "configuration_alerts", ["status"])
    op.create_index("ix_configuration_alerts_risk_level", "configuration_alerts", ["risk_level"])
    op.create_index("ix_configuration_alerts_created_at", "configuration_alerts", ["created_at"])
    op.create_index("ix_alert_suppressions_active", "alert_suppressions", ["active"])
    op.create_index("ix_alert_suppressions_device_id", "alert_suppressions", ["device_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_alert_suppressions_device_id", table_name="alert_suppressions")
    op.drop_index("ix_alert_suppressions_active", table_name="alert_suppressions")
    op.drop_index("ix_configuration_alerts_created_at", table_name="configuration_alerts")
    op.drop_index("ix_configuration_alerts_risk_level", table_name="configuration_alerts")
    op.drop_index("ix_configuration_alerts_status", table_name="configuration_alerts")
    op.drop_index("ix_configuration_alerts_device_id", table_name="configuration_alerts")

    # Drop tables
    op.drop_table("alert_suppressions")
    op.drop_table("configuration_alerts")
    op.drop_table("gotify_notification_config")
