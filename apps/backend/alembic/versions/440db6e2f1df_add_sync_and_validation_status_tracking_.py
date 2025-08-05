"""Add sync and validation status tracking to configuration snapshots

Revision ID: 440db6e2f1df
Revises: 6a9a9e64cfe3
Create Date: 2025-08-04 17:45:04.200608

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "440db6e2f1df"
down_revision: Union[str, Sequence[str], None] = "6a9a9e64cfe3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add sync and validation status fields to configuration_snapshots
    op.add_column(
        "configuration_snapshots",
        sa.Column("sync_status", sa.String(50), nullable=False, server_default="synced"),
    )
    op.add_column(
        "configuration_snapshots",
        sa.Column("validation_status", sa.String(50), nullable=False, server_default="pending"),
    )
    op.add_column("configuration_snapshots", sa.Column("last_validation_output", sa.Text))
    op.add_column("configuration_snapshots", sa.Column("last_sync_error", sa.Text))

    # Add indexes for the new status columns
    op.create_index(
        "ix_configuration_snapshots_sync_status", "configuration_snapshots", ["sync_status"]
    )
    op.create_index(
        "ix_configuration_snapshots_validation_status",
        "configuration_snapshots",
        ["validation_status"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_configuration_snapshots_validation_status", "configuration_snapshots")
    op.drop_index("ix_configuration_snapshots_sync_status", "configuration_snapshots")

    # Drop columns
    op.drop_column("configuration_snapshots", "last_sync_error")
    op.drop_column("configuration_snapshots", "last_validation_output")
    op.drop_column("configuration_snapshots", "validation_status")
    op.drop_column("configuration_snapshots", "sync_status")
