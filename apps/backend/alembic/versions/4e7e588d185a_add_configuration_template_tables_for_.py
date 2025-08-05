"""Add configuration template tables for Jinja2 templating support

Revision ID: 4e7e588d185a
Revises: 74b14835fbe1
Create Date: 2025-08-04 18:50:31.716234

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "4e7e588d185a"
down_revision: Union[str, Sequence[str], None] = "74b14835fbe1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create configuration_templates table
    op.create_table(
        "configuration_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0.0"),
        sa.Column("template_content", sa.Text(), nullable=False),
        sa.Column("default_variables", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("required_variables", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("variable_schema", sa.JSON(), nullable=True),
        sa.Column("validation_mode", sa.String(20), nullable=False, server_default="strict"),
        sa.Column("auto_reload", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("source_path", sa.String(500), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("environments", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("supported_devices", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("validated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_count", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_template_name_version"),
    )

    # Create template_instances table
    op.create_table(
        "template_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("environment", sa.String(100), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("rendered_content", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("target_path", sa.String(500), nullable=False),
        sa.Column("file_mode", sa.String(10), nullable=True),
        sa.Column("file_owner", sa.String(100), nullable=True),
        sa.Column("file_group", sa.String(100), nullable=True),
        sa.Column("deployed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deployed_by", sa.String(255), nullable=True),
        sa.Column("validation_status", sa.String(20), nullable=True),
        sa.Column("validation_errors", sa.JSON(), nullable=True),
        sa.Column("drift_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_drift_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("drift_details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "template_id", "device_id", "target_path", name="uq_instance_template_device_path"
        ),
    )

    # Create template_variables table
    op.create_table(
        "template_variables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("variable_type", sa.String(50), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validation_regex", sa.String(500), nullable=True),
        sa.Column("allowed_values", sa.JSON(), nullable=True),
        sa.Column("min_length", sa.JSON(), nullable=True),
        sa.Column("max_length", sa.JSON(), nullable=True),
        sa.Column("default_value", sa.JSON(), nullable=True),
        sa.Column("environment_defaults", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("documentation", sa.Text(), nullable=True),
        sa.Column("examples", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "name", name="uq_template_variable_name"),
    )

    # Create indexes for better query performance
    op.create_index("ix_configuration_templates_name", "configuration_templates", ["name"])
    op.create_index("ix_configuration_templates_type", "configuration_templates", ["template_type"])
    op.create_index("ix_configuration_templates_category", "configuration_templates", ["category"])
    op.create_index("ix_configuration_templates_active", "configuration_templates", ["active"])
    op.create_index(
        "ix_configuration_templates_created_at", "configuration_templates", ["created_at"]
    )
    # Note: JSON arrays cannot be indexed directly in PostgreSQL
    # Filtering will be done using JSON operators without indexes

    op.create_index("ix_template_instances_template_id", "template_instances", ["template_id"])
    op.create_index("ix_template_instances_device_id", "template_instances", ["device_id"])
    op.create_index("ix_template_instances_environment", "template_instances", ["environment"])
    op.create_index("ix_template_instances_deployed", "template_instances", ["deployed"])
    op.create_index("ix_template_instances_created_at", "template_instances", ["created_at"])
    op.create_index("ix_template_instances_target_path", "template_instances", ["target_path"])

    op.create_index("ix_template_variables_template_id", "template_variables", ["template_id"])
    op.create_index("ix_template_variables_name", "template_variables", ["name"])
    op.create_index("ix_template_variables_required", "template_variables", ["required"])
    op.create_index("ix_template_variables_sensitive", "template_variables", ["sensitive"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_template_variables_sensitive", table_name="template_variables")
    op.drop_index("ix_template_variables_required", table_name="template_variables")
    op.drop_index("ix_template_variables_name", table_name="template_variables")
    op.drop_index("ix_template_variables_template_id", table_name="template_variables")

    op.drop_index("ix_template_instances_target_path", table_name="template_instances")
    op.drop_index("ix_template_instances_created_at", table_name="template_instances")
    op.drop_index("ix_template_instances_deployed", table_name="template_instances")
    op.drop_index("ix_template_instances_environment", table_name="template_instances")
    op.drop_index("ix_template_instances_device_id", table_name="template_instances")
    op.drop_index("ix_template_instances_template_id", table_name="template_instances")

    # Note: No JSON array indexes were created
    op.drop_index("ix_configuration_templates_created_at", table_name="configuration_templates")
    op.drop_index("ix_configuration_templates_active", table_name="configuration_templates")
    op.drop_index("ix_configuration_templates_category", table_name="configuration_templates")
    op.drop_index("ix_configuration_templates_type", table_name="configuration_templates")
    op.drop_index("ix_configuration_templates_name", table_name="configuration_templates")

    # Drop tables (in reverse order due to foreign key constraints)
    op.drop_table("template_variables")
    op.drop_table("template_instances")
    op.drop_table("configuration_templates")
