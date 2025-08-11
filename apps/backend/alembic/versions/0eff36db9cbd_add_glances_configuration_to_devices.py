"""Add Glances configuration to devices

Revision ID: 0eff36db9cbd
Revises: 66cc68f4e112
Create Date: 2025-08-09 00:10:58.855197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0eff36db9cbd'
down_revision: Union[str, Sequence[str], None] = '66cc68f4e112'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Glances configuration fields to devices table."""
    # Add Glances configuration columns
    op.add_column('devices', sa.Column('glances_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('devices', sa.Column('glances_port', sa.Integer(), nullable=False, server_default='61208'))
    op.add_column('devices', sa.Column('glances_url', sa.String(length=512), nullable=True))


def downgrade() -> None:
    """Remove Glances configuration fields from devices table."""
    # Remove Glances configuration columns
    op.drop_column('devices', 'glances_url')
    op.drop_column('devices', 'glances_port')
    op.drop_column('devices', 'glances_enabled')
