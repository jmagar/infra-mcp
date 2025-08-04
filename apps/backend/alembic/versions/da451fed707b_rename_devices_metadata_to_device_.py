"""Rename devices.metadata to device_metadata

Revision ID: da451fed707b
Revises: f4a2b1c8d37e
Create Date: 2025-08-04 01:19:14.299567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da451fed707b'
down_revision: Union[str, Sequence[str], None] = 'f4a2b1c8d37e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename devices.metadata column to device_metadata to avoid SQLAlchemy reserved attribute conflict."""
    op.alter_column('devices', 'metadata', new_column_name='device_metadata')


def downgrade() -> None:
    """Rename devices.device_metadata back to metadata."""
    op.alter_column('devices', 'device_metadata', new_column_name='metadata')
