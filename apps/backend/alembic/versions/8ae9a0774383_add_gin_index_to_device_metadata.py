"""add_gin_index_to_device_metadata

Revision ID: 8ae9a0774383
Revises: da451fed707b
Create Date: 2025-08-04 09:10:14.686365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8ae9a0774383'
down_revision: Union[str, Sequence[str], None] = 'da451fed707b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "idx_devices_device_metadata",
        "devices",
        ["device_metadata"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_devices_device_metadata", table_name="devices")
