"""Create unified infrastructure schema with TimescaleDB compatibility

Revision ID: f4a2b1c8d37e
Revises:
Create Date: 2025-08-04 01:10:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f4a2b1c8d37e'
down_revision: str | list[str] | None = None
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Create unified infrastructure schema with Phase 1 enhancements."""
    # Enable TimescaleDB and other extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gin"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gist"')
    
    # Create devices table (non-time-series, regular table)
    op.create_table('devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('device_type', sa.String(length=50), server_default='server', nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('docker_compose_path', sa.String(length=512), nullable=True),
        sa.Column('docker_appdata_path', sa.String(length=512), nullable=True),
        sa.Column('device_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('monitoring_enabled', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='unknown', nullable=True),
        sa.Column('last_successful_collection', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_collection_status', sa.String(length=20), server_default='never', nullable=True),
        sa.Column('collection_error_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname')
    )
    
    # Create system_metrics table (hypertable)
    op.create_table('system_metrics',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cpu_usage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('memory_usage_bytes', sa.BigInteger(), nullable=True),
        sa.Column('memory_total_bytes', sa.BigInteger(), nullable=True),
        sa.Column('disk_usage_bytes', sa.BigInteger(), nullable=True),
        sa.Column('disk_total_bytes', sa.BigInteger(), nullable=True),
        sa.Column('network_bytes_sent', sa.BigInteger(), nullable=True),
        sa.Column('network_bytes_recv', sa.BigInteger(), nullable=True),
        sa.Column('load_average_1m', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('load_average_5m', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('load_average_15m', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('uptime_seconds', sa.BigInteger(), nullable=True),
        sa.Column('boot_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('additional_metrics', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id')
    )
    
    # Create container_snapshots table (hypertable)
    op.create_table('container_snapshots',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('container_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('image', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('cpu_usage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('memory_usage_bytes', sa.BigInteger(), nullable=True),
        sa.Column('memory_limit_bytes', sa.BigInteger(), nullable=True),
        sa.Column('network_bytes_sent', sa.BigInteger(), nullable=True),
        sa.Column('network_bytes_recv', sa.BigInteger(), nullable=True),
        sa.Column('block_read_bytes', sa.BigInteger(), nullable=True),
        sa.Column('block_write_bytes', sa.BigInteger(), nullable=True),
        sa.Column('ports', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('environment', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('volumes', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('networks', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'container_id')
    )
    
    # Create drive_health table (hypertable)
    op.create_table('drive_health',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('drive_path', sa.String(length=255), nullable=False),
        sa.Column('drive_model', sa.String(length=255), nullable=True),
        sa.Column('drive_serial', sa.String(length=255), nullable=True),
        sa.Column('drive_type', sa.String(length=50), nullable=True),
        sa.Column('health_status', sa.String(length=50), nullable=True),
        sa.Column('temperature_celsius', sa.Integer(), nullable=True),
        sa.Column('power_on_hours', sa.BigInteger(), nullable=True),
        sa.Column('power_cycle_count', sa.Integer(), nullable=True),
        sa.Column('reallocated_sector_count', sa.Integer(), nullable=True),
        sa.Column('pending_sector_count', sa.Integer(), nullable=True),
        sa.Column('offline_uncorrectable', sa.Integer(), nullable=True),
        sa.Column('smart_status', sa.String(length=20), nullable=True),
        sa.Column('smart_attributes', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'drive_path')
    )
    
    # PHASE 1 TABLES
    
    # Create data_collection_audit table (hypertable)
    op.create_table('data_collection_audit',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('collection_method', sa.String(length=50), nullable=False),
        sa.Column('collection_source', sa.String(length=100), nullable=True),
        sa.Column('force_refresh', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('cache_hit', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('ssh_command_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('data_size_bytes', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('records_created', sa.Integer(), server_default='0', nullable=False),
        sa.Column('records_updated', sa.Integer(), server_default='0', nullable=False),
        sa.Column('freshness_threshold', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'operation_id')
    )
    
    # Create configuration_snapshots table (hypertable)
    op.create_table('configuration_snapshots',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=False),
        sa.Column('parsed_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=True),
        sa.Column('file_modified_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collection_source', sa.String(length=50), nullable=False),
        sa.Column('detection_latency_ms', sa.Integer(), nullable=True),
        sa.Column('affected_services', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('requires_restart', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('risk_level', sa.String(length=20), server_default='MEDIUM', nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'id')  # Include time in primary key for TimescaleDB
    )
    
    # Create configuration_change_events table (hypertable)
    op.create_table('configuration_change_events',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_type', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('change_type', sa.String(length=20), nullable=False),
        sa.Column('affected_services', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('service_dependencies', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('requires_restart', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('restart_services', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('changes_summary', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('risk_level', sa.String(length=20), server_default='MEDIUM', nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('processed', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('notifications_sent', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        # Note: Cannot add FK to configuration_snapshots.id due to TimescaleDB partitioning constraints
        sa.PrimaryKeyConstraint('time', 'id')  # Include time in primary key for TimescaleDB
    )
    
    # Create service_performance_metrics table (hypertable)
    op.create_table('service_performance_metrics',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_name', sa.String(length=50), nullable=False),
        sa.Column('operations_total', sa.Integer(), server_default='0', nullable=False),
        sa.Column('operations_successful', sa.Integer(), server_default='0', nullable=False),
        sa.Column('operations_failed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('avg_duration_ms', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('min_duration_ms', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('max_duration_ms', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('p95_duration_ms', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('p99_duration_ms', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('cache_hit_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cache_miss_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('timeout_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('throughput_ops_per_sec', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('concurrent_operations', sa.Integer(), nullable=True),
        sa.Column('memory_usage_bytes', sa.BigInteger(), nullable=True),
        sa.Column('cpu_usage_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('network_io_bytes', sa.BigInteger(), nullable=True),
        sa.Column('disk_io_bytes', sa.BigInteger(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.PrimaryKeyConstraint('time', 'service_name')
    )
    
    # Create cache_metadata table (regular table, not time-series)
    op.create_table('cache_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cache_key', sa.String(length=255), nullable=False),
        sa.Column('data_type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('access_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('hit_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('miss_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('data_size_bytes', sa.Integer(), nullable=True),
        sa.Column('ttl_seconds', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('invalidated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invalidation_reason', sa.String(length=100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id', 'cache_key', 'data_type')
    )
    
    # First create all indexes, then convert to hypertables
    # (Moving hypertable creation after table and index creation)
    
    # Create indexes for performance
    op.create_index('idx_devices_hostname', 'devices', ['hostname'])
    op.create_index('idx_devices_device_type', 'devices', ['device_type'])
    op.create_index('idx_devices_status', 'devices', ['status'])
    op.create_index('idx_devices_monitoring_enabled', 'devices', ['monitoring_enabled'])
    op.create_index('idx_devices_last_seen', 'devices', ['last_seen'])
    op.create_index('idx_devices_last_collection', 'devices', ['last_successful_collection'])
    
    op.create_index('idx_system_metrics_device_time', 'system_metrics', ['device_id', sa.text('time DESC')])
    op.create_index('idx_container_snapshots_device_time', 'container_snapshots', ['device_id', sa.text('time DESC')])
    op.create_index('idx_container_snapshots_container_id', 'container_snapshots', ['container_id'])
    op.create_index('idx_drive_health_device_time', 'drive_health', ['device_id', sa.text('time DESC')])
    op.create_index('idx_drive_health_drive_path', 'drive_health', ['drive_path'])
    
    # Phase 1 indexes
    op.create_index('idx_data_collection_audit_device_time', 'data_collection_audit', ['device_id', sa.text('time DESC')])
    op.create_index('idx_data_collection_audit_operation_id', 'data_collection_audit', ['operation_id'])
    op.create_index('idx_data_collection_audit_data_type', 'data_collection_audit', ['data_type'])
    op.create_index('idx_data_collection_audit_status', 'data_collection_audit', ['status'])
    
    op.create_index('idx_configuration_snapshots_device_time', 'configuration_snapshots', ['device_id', sa.text('time DESC')])
    op.create_index('idx_configuration_snapshots_config_type', 'configuration_snapshots', ['config_type'])
    op.create_index('idx_configuration_snapshots_file_path', 'configuration_snapshots', ['file_path'])
    op.create_index('idx_configuration_snapshots_content_hash', 'configuration_snapshots', ['content_hash'])
    
    op.create_index('idx_configuration_change_events_device_time', 'configuration_change_events', ['device_id', sa.text('time DESC')])
    op.create_index('idx_configuration_change_events_snapshot_id', 'configuration_change_events', ['snapshot_id'])
    op.create_index('idx_configuration_change_events_processed', 'configuration_change_events', ['processed'])
    
    op.create_index('idx_service_performance_metrics_service_time', 'service_performance_metrics', ['service_name', sa.text('time DESC')])
    op.create_index('idx_service_performance_metrics_time', 'service_performance_metrics', [sa.text('time DESC')])
    
    op.create_index('idx_cache_metadata_device_id', 'cache_metadata', ['device_id'])
    op.create_index('idx_cache_metadata_data_type', 'cache_metadata', ['data_type'])
    op.create_index('idx_cache_metadata_cache_key', 'cache_metadata', ['cache_key'])
    op.create_index('idx_cache_metadata_expires_at', 'cache_metadata', ['expires_at'])
    op.create_index('idx_cache_metadata_last_accessed', 'cache_metadata', ['last_accessed'])
    
    # Convert time-series tables to hypertables AFTER all tables and indexes are created
    op.execute("SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('container_snapshots', 'time', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('drive_health', 'time', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('data_collection_audit', 'time', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('configuration_snapshots', 'time', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('configuration_change_events', 'time', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('service_performance_metrics', 'time', if_not_exists => TRUE)")


def downgrade() -> None:
    """Drop all tables and extensions."""
    # Drop indexes first
    op.drop_index('idx_cache_metadata_last_accessed', table_name='cache_metadata')
    op.drop_index('idx_cache_metadata_expires_at', table_name='cache_metadata')
    op.drop_index('idx_cache_metadata_cache_key', table_name='cache_metadata')
    op.drop_index('idx_cache_metadata_data_type', table_name='cache_metadata')
    op.drop_index('idx_cache_metadata_device_id', table_name='cache_metadata')
    
    # Drop Phase 1 table indexes
    op.drop_index('idx_service_performance_metrics_time', table_name='service_performance_metrics')
    op.drop_index('idx_service_performance_metrics_service_time', table_name='service_performance_metrics')
    op.drop_index('idx_configuration_change_events_processed', table_name='configuration_change_events')
    op.drop_index('idx_configuration_change_events_snapshot_id', table_name='configuration_change_events')
    op.drop_index('idx_configuration_change_events_device_time', table_name='configuration_change_events')
    op.drop_index('idx_configuration_snapshots_content_hash', table_name='configuration_snapshots')
    op.drop_index('idx_configuration_snapshots_file_path', table_name='configuration_snapshots')
    op.drop_index('idx_configuration_snapshots_config_type', table_name='configuration_snapshots')
    op.drop_index('idx_configuration_snapshots_device_time', table_name='configuration_snapshots')
    op.drop_index('idx_data_collection_audit_status', table_name='data_collection_audit')
    op.drop_index('idx_data_collection_audit_data_type', table_name='data_collection_audit')
    op.drop_index('idx_data_collection_audit_operation_id', table_name='data_collection_audit')
    op.drop_index('idx_data_collection_audit_device_time', table_name='data_collection_audit')
    
    # Drop existing table indexes
    op.drop_index('idx_drive_health_drive_path', table_name='drive_health')
    op.drop_index('idx_drive_health_device_time', table_name='drive_health')
    op.drop_index('idx_container_snapshots_container_id', table_name='container_snapshots')
    op.drop_index('idx_container_snapshots_device_time', table_name='container_snapshots')
    op.drop_index('idx_system_metrics_device_time', table_name='system_metrics')
    op.drop_index('idx_devices_last_collection', table_name='devices')
    op.drop_index('idx_devices_last_seen', table_name='devices')
    op.drop_index('idx_devices_monitoring_enabled', table_name='devices')
    op.drop_index('idx_devices_status', table_name='devices')
    op.drop_index('idx_devices_device_type', table_name='devices')
    op.drop_index('idx_devices_hostname', table_name='devices')
    
    # Drop tables
    op.drop_table('cache_metadata')
    op.drop_table('service_performance_metrics')
    op.drop_table('configuration_change_events')
    op.drop_table('configuration_snapshots')
    op.drop_table('data_collection_audit')
    op.drop_table('drive_health')
    op.drop_table('container_snapshots')
    op.drop_table('system_metrics')
    op.drop_table('devices')