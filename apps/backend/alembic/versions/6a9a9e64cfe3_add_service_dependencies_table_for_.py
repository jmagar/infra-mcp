"""Add service_dependencies table for dependency mapping

Revision ID: 6a9a9e64cfe3
Revises: 8ae9a0774383
Create Date: 2025-08-04 17:08:42.109175

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6a9a9e64cfe3"
down_revision: Union[str, Sequence[str], None] = "8ae9a0774383"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create service_dependencies table
    op.create_table(
        "service_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(length=255), nullable=False),
        sa.Column("depends_on", sa.String(length=255), nullable=False),
        sa.Column("dependency_type", sa.String(length=50), nullable=False),
        sa.Column("dependency_metadata", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(
        "idx_service_deps_unique",
        "service_dependencies",
        ["device_id", "service_name", "depends_on"],
        unique=True,
    )
    op.create_index(
        "idx_service_deps_service", "service_dependencies", ["device_id", "service_name"]
    )
    op.create_index(
        "idx_service_deps_depends_on", "service_dependencies", ["device_id", "depends_on"]
    )
    op.create_index("idx_service_deps_type", "service_dependencies", ["dependency_type"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index("idx_service_deps_type", table_name="service_dependencies")
    op.drop_index("idx_service_deps_depends_on", table_name="service_dependencies")
    op.drop_index("idx_service_deps_service", table_name="service_dependencies")
    op.drop_index("idx_service_deps_unique", table_name="service_dependencies")

    # Drop table
    op.drop_table("service_dependencies")
