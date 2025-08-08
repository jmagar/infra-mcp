"""Fix configuration_snapshots ID column from bigint to UUID

Revision ID: 66cc68f4e112
Revises: af4ba97c1822
Create Date: 2025-08-07 02:28:20.575166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '66cc68f4e112'
down_revision: Union[str, Sequence[str], None] = 'af4ba97c1822'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - fix configuration_snapshots ID column to UUID."""
    # Drop the existing table since it's empty and we need to recreate with UUID
    op.drop_table('configuration_snapshots')
    
    # Recreate with correct UUID primary key
    op.create_table(
        'configuration_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', UUID(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('time', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('config_type', sa.String(100), nullable=False, index=True),
        sa.Column('file_path', sa.String(1024), nullable=False, index=True),
        sa.Column('content_hash', sa.String(128), nullable=False, index=True),
        sa.Column('raw_content', sa.Text, nullable=False),
        sa.Column('parsed_data', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('change_type', sa.String(20), nullable=False, server_default='MODIFY', index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Recreate indexes
    op.create_index('ix_config_snapshots_device_time', 'configuration_snapshots', ['device_id', 'time'])
    op.create_index('ix_config_snapshots_device_type_time', 'configuration_snapshots', ['device_id', 'config_type', 'time'])
    op.create_index('ix_config_snapshots_hash_lookup', 'configuration_snapshots', ['device_id', 'file_path', 'content_hash'])
    op.create_index('ix_config_snapshots_change_tracking', 'configuration_snapshots', ['device_id', 'change_type', 'time'])


def downgrade() -> None:
    """Downgrade schema - revert to bigint ID."""
    # Drop the UUID version
    op.drop_table('configuration_snapshots')
    
    # Recreate with bigint ID (original version)
    op.create_table(
        'configuration_snapshots',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('device_id', UUID(as_uuid=True), sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('time', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('config_type', sa.String(100), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('content_hash', sa.String(128), nullable=False),
        sa.Column('raw_content', sa.Text, nullable=False),
        sa.Column('parsed_data', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('change_type', sa.String(20), nullable=False, server_default='MODIFY'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
