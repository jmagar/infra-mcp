"""Initial migration with all tables

Revision ID: af4ba97c1822
Revises: 
Create Date: 2025-07-30 11:24:27.721549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'af4ba97c1822'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    
    # Create devices table (main registry)
    op.create_table('devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.func.gen_random_uuid()),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('ip_address', postgresql.INET(), nullable=False),
        sa.Column('mac_address', postgresql.MACADDR(), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=False, default='server'),
        sa.Column('operating_system', sa.String(length=100), nullable=True),
        sa.Column('architecture', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='unknown'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ssh_port', sa.Integer(), nullable=False, default=22),
        sa.Column('ssh_user', sa.String(length=100), nullable=True),
        sa.Column('ssh_key_path', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('environment', sa.String(length=50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, default=sa.func.array([])),
        sa.Column('metadata_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname')
    )
    op.create_index(op.f('ix_devices_hostname'), 'devices', ['hostname'], unique=False)
    op.create_index(op.f('ix_devices_ip_address'), 'devices', ['ip_address'], unique=False)
    
    # Create system_metrics table (hypertable)
    op.create_table('system_metrics',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cpu_usage_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('cpu_load_1min', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('cpu_load_5min', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('cpu_load_15min', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('cpu_temperature', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('memory_total_bytes', sa.BigInteger(), nullable=True),
        sa.Column('memory_used_bytes', sa.BigInteger(), nullable=True),
        sa.Column('memory_available_bytes', sa.BigInteger(), nullable=True),
        sa.Column('memory_cached_bytes', sa.BigInteger(), nullable=True),
        sa.Column('memory_buffers_bytes', sa.BigInteger(), nullable=True),
        sa.Column('swap_total_bytes', sa.BigInteger(), nullable=True),
        sa.Column('swap_used_bytes', sa.BigInteger(), nullable=True),
        sa.Column('disk_read_bytes_total', sa.BigInteger(), nullable=True),
        sa.Column('disk_write_bytes_total', sa.BigInteger(), nullable=True),
        sa.Column('disk_read_ops_total', sa.BigInteger(), nullable=True),
        sa.Column('disk_write_ops_total', sa.BigInteger(), nullable=True),
        sa.Column('disk_usage_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('disk_available_bytes', sa.BigInteger(), nullable=True),
        sa.Column('network_bytes_sent_total', sa.BigInteger(), nullable=True),
        sa.Column('network_bytes_recv_total', sa.BigInteger(), nullable=True),
        sa.Column('network_packets_sent_total', sa.BigInteger(), nullable=True),
        sa.Column('network_packets_recv_total', sa.BigInteger(), nullable=True),
        sa.Column('network_errors_total', sa.BigInteger(), nullable=True),
        sa.Column('uptime_seconds', sa.BigInteger(), nullable=True),
        sa.Column('processes_total', sa.Integer(), nullable=True),
        sa.Column('processes_running', sa.Integer(), nullable=True),
        sa.Column('processes_sleeping', sa.Integer(), nullable=True),
        sa.Column('processes_zombie', sa.Integer(), nullable=True),
        sa.Column('boot_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('users_logged_in', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id')
    )
    
    # Create drive_health table (hypertable)
    op.create_table('drive_health',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('drive_name', sa.String(length=255), nullable=False),
        sa.Column('drive_model', sa.String(length=255), nullable=True),
        sa.Column('drive_serial', sa.String(length=255), nullable=True),
        sa.Column('drive_type', sa.String(length=50), nullable=True),
        sa.Column('drive_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('drive_firmware', sa.String(length=100), nullable=True),
        sa.Column('smart_status', sa.String(length=20), nullable=True),
        sa.Column('smart_overall_health', sa.String(length=50), nullable=True),
        sa.Column('temperature_celsius', sa.Integer(), nullable=True),
        sa.Column('power_on_hours', sa.BigInteger(), nullable=True),
        sa.Column('power_cycle_count', sa.BigInteger(), nullable=True),
        sa.Column('reallocated_sectors', sa.Integer(), nullable=True),
        sa.Column('reallocated_events', sa.Integer(), nullable=True),
        sa.Column('current_pending_sectors', sa.Integer(), nullable=True),
        sa.Column('offline_uncorrectable', sa.Integer(), nullable=True),
        sa.Column('wear_leveling_count', sa.Integer(), nullable=True),
        sa.Column('used_reserved_blocks', sa.Integer(), nullable=True),
        sa.Column('program_fail_count', sa.Integer(), nullable=True),
        sa.Column('erase_fail_count', sa.Integer(), nullable=True),
        sa.Column('read_error_rate', sa.BigInteger(), nullable=True),
        sa.Column('seek_error_rate', sa.BigInteger(), nullable=True),
        sa.Column('spin_retry_count', sa.Integer(), nullable=True),
        sa.Column('airflow_temperature', sa.Integer(), nullable=True),
        sa.Column('g_sense_error_rate', sa.Integer(), nullable=True),
        sa.Column('head_flying_hours', sa.BigInteger(), nullable=True),
        sa.Column('smart_attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'drive_name')
    )
    
    # Create container_snapshots table (hypertable)
    op.create_table('container_snapshots',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('container_id', sa.String(length=64), nullable=False),
        sa.Column('container_name', sa.String(length=255), nullable=False),
        sa.Column('image', sa.String(length=255), nullable=True),
        sa.Column('image_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('running', sa.Boolean(), nullable=True),
        sa.Column('paused', sa.Boolean(), nullable=True),
        sa.Column('restarting', sa.Boolean(), nullable=True),
        sa.Column('oom_killed', sa.Boolean(), nullable=True),
        sa.Column('dead', sa.Boolean(), nullable=True),
        sa.Column('pid', sa.Integer(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('cpu_usage_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('memory_usage_bytes', sa.BigInteger(), nullable=True),
        sa.Column('memory_limit_bytes', sa.BigInteger(), nullable=True),
        sa.Column('memory_cache_bytes', sa.BigInteger(), nullable=True),
        sa.Column('network_bytes_sent', sa.BigInteger(), nullable=True),
        sa.Column('network_bytes_recv', sa.BigInteger(), nullable=True),
        sa.Column('block_read_bytes', sa.BigInteger(), nullable=True),
        sa.Column('block_write_bytes', sa.BigInteger(), nullable=True),
        sa.Column('ports', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('environment', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('volumes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('networks', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'container_id')
    )
    
    # Create zfs_status table (hypertable)
    op.create_table('zfs_status',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pool_name', sa.String(length=255), nullable=False),
        sa.Column('pool_state', sa.String(length=50), nullable=True),
        sa.Column('pool_health', sa.String(length=50), nullable=True),
        sa.Column('pool_guid', sa.String(length=100), nullable=True),
        sa.Column('pool_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('pool_allocated_bytes', sa.BigInteger(), nullable=True),
        sa.Column('pool_free_bytes', sa.BigInteger(), nullable=True),
        sa.Column('pool_fragmentation_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('pool_capacity_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('read_ops_total', sa.BigInteger(), nullable=True),
        sa.Column('write_ops_total', sa.BigInteger(), nullable=True),
        sa.Column('read_bytes_total', sa.BigInteger(), nullable=True),
        sa.Column('write_bytes_total', sa.BigInteger(), nullable=True),
        sa.Column('scrub_state', sa.String(length=50), nullable=True),
        sa.Column('scrub_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scrub_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scrub_examined_bytes', sa.BigInteger(), nullable=True),
        sa.Column('scrub_processed_bytes', sa.BigInteger(), nullable=True),
        sa.Column('scrub_errors', sa.Integer(), nullable=True),
        sa.Column('scrub_repaired_bytes', sa.BigInteger(), nullable=True),
        sa.Column('read_errors', sa.Integer(), nullable=True),
        sa.Column('write_errors', sa.Integer(), nullable=True),
        sa.Column('checksum_errors', sa.Integer(), nullable=True),
        sa.Column('pool_version', sa.Integer(), nullable=True),
        sa.Column('feature_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('pool_properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('dataset_name', sa.String(length=255), nullable=True),
        sa.Column('dataset_type', sa.String(length=50), nullable=True),
        sa.Column('dataset_used_bytes', sa.BigInteger(), nullable=True),
        sa.Column('dataset_available_bytes', sa.BigInteger(), nullable=True),
        sa.Column('dataset_referenced_bytes', sa.BigInteger(), nullable=True),
        sa.Column('dataset_compression_ratio', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('dataset_properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'pool_name')
    )
    
    # Create zfs_snapshots table (hypertable)
    op.create_table('zfs_snapshots',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('snapshot_name', sa.String(length=255), nullable=False),
        sa.Column('pool_name', sa.String(length=255), nullable=False),
        sa.Column('dataset_name', sa.String(length=255), nullable=False),
        sa.Column('snapshot_guid', sa.String(length=100), nullable=True),
        sa.Column('creation_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_bytes', sa.BigInteger(), nullable=True),
        sa.Column('referenced_bytes', sa.BigInteger(), nullable=True),
        sa.Column('compressed_bytes', sa.BigInteger(), nullable=True),
        sa.Column('uncompressed_bytes', sa.BigInteger(), nullable=True),
        sa.Column('snapshot_type', sa.String(length=50), nullable=True),
        sa.Column('retention_policy', sa.String(length=100), nullable=True),
        sa.Column('snapshot_properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('backup_status', sa.String(length=50), nullable=True),
        sa.Column('replication_status', sa.String(length=50), nullable=True),
        sa.Column('last_backup_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('backup_destination', sa.String(length=255), nullable=True),
        sa.Column('is_cloned', sa.Boolean(), nullable=True, default=False),
        sa.Column('clone_count', sa.Integer(), nullable=True, default=0),
        sa.Column('is_held', sa.Boolean(), nullable=True, default=False),
        sa.Column('hold_tag', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'snapshot_name')
    )
    
    # Create network_interfaces table (hypertable)
    op.create_table('network_interfaces',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interface_name', sa.String(length=255), nullable=False),
        sa.Column('interface_type', sa.String(length=50), nullable=True),
        sa.Column('mtu', sa.Integer(), nullable=True),
        sa.Column('speed_mbps', sa.Integer(), nullable=True),
        sa.Column('duplex', sa.String(length=20), nullable=True),
        sa.Column('is_up', sa.Boolean(), nullable=True),
        sa.Column('is_running', sa.Boolean(), nullable=True),
        sa.Column('carrier_state', sa.String(length=20), nullable=True),
        sa.Column('ip_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('mac_address', postgresql.MACADDR(), nullable=True),
        sa.Column('bytes_sent', sa.BigInteger(), nullable=True),
        sa.Column('bytes_recv', sa.BigInteger(), nullable=True),
        sa.Column('packets_sent', sa.BigInteger(), nullable=True),
        sa.Column('packets_recv', sa.BigInteger(), nullable=True),
        sa.Column('errors_sent', sa.BigInteger(), nullable=True),
        sa.Column('errors_recv', sa.BigInteger(), nullable=True),
        sa.Column('drops_sent', sa.BigInteger(), nullable=True),
        sa.Column('drops_recv', sa.BigInteger(), nullable=True),
        sa.Column('collisions', sa.BigInteger(), nullable=True),
        sa.Column('wireless_ssid', sa.String(length=255), nullable=True),
        sa.Column('wireless_signal_strength', sa.Integer(), nullable=True),
        sa.Column('wireless_frequency', sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column('vlan_id', sa.Integer(), nullable=True),
        sa.Column('vlan_priority', sa.Integer(), nullable=True),
        sa.Column('bridge_id', sa.String(length=100), nullable=True),
        sa.Column('bridge_stp_state', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'interface_name')
    )
    
    # Create docker_networks table (hypertable)
    op.create_table('docker_networks',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('network_id', sa.String(length=64), nullable=False),
        sa.Column('network_name', sa.String(length=255), nullable=False),
        sa.Column('driver', sa.String(length=100), nullable=True),
        sa.Column('scope', sa.String(length=50), nullable=True),
        sa.Column('subnet', postgresql.CIDR(), nullable=True),
        sa.Column('gateway', postgresql.INET(), nullable=True),
        sa.Column('ip_range', postgresql.CIDR(), nullable=True),
        sa.Column('is_internal', sa.Boolean(), nullable=True),
        sa.Column('enable_ipv6', sa.Boolean(), nullable=True),
        sa.Column('attachable', sa.Boolean(), nullable=True),
        sa.Column('ingress', sa.Boolean(), nullable=True),
        sa.Column('connected_containers', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('container_count', sa.Integer(), nullable=True, default=0),
        sa.Column('driver_options', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'network_id')
    )
    
    # Create vm_status table (hypertable)
    op.create_table('vm_status',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vm_id', sa.String(length=255), nullable=False),
        sa.Column('vm_name', sa.String(length=255), nullable=False),
        sa.Column('vm_type', sa.String(length=50), nullable=True),
        sa.Column('hypervisor', sa.String(length=100), nullable=True),
        sa.Column('vm_state', sa.String(length=50), nullable=True),
        sa.Column('vm_power_state', sa.String(length=50), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('memory_allocated_mb', sa.BigInteger(), nullable=True),
        sa.Column('disk_allocated_gb', sa.BigInteger(), nullable=True),
        sa.Column('cpu_usage_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('memory_usage_mb', sa.BigInteger(), nullable=True),
        sa.Column('disk_usage_gb', sa.BigInteger(), nullable=True),
        sa.Column('network_interfaces', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('ip_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('os_type', sa.String(length=100), nullable=True),
        sa.Column('os_version', sa.String(length=100), nullable=True),
        sa.Column('tools_version', sa.String(length=100), nullable=True),
        sa.Column('tools_running', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('boot_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uptime_seconds', sa.BigInteger(), nullable=True),
        sa.Column('snapshot_count', sa.Integer(), nullable=True, default=0),
        sa.Column('last_snapshot_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('vm_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, default=sa.func.array([])),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'vm_id')
    )
    
    # Create system_logs table (hypertable)
    op.create_table('system_logs',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('log_id', sa.String(length=64), nullable=False),
        sa.Column('log_source', sa.String(length=255), nullable=True),
        sa.Column('service_name', sa.String(length=255), nullable=True),
        sa.Column('facility', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('log_level', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('raw_message', sa.Text(), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('parsed_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('event_type', sa.String(length=100), nullable=True),
        sa.Column('event_category', sa.String(length=100), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=True, default=1),
        sa.Column('first_occurrence', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_occurrence', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('thread_id', sa.String(length=64), nullable=True),
        sa.Column('process_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('is_security_event', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_error', sa.Boolean(), nullable=True, default=False),
        sa.Column('alert_triggered', sa.Boolean(), nullable=True, default=False),
        sa.Column('alert_rule', sa.String(length=255), nullable=True),
        sa.Column('log_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, default=sa.func.array([])),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'log_id')
    )
    
    # Create backup_status table (hypertable)
    op.create_table('backup_status',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('backup_id', sa.String(length=255), nullable=False),
        sa.Column('backup_name', sa.String(length=255), nullable=False),
        sa.Column('backup_type', sa.String(length=50), nullable=True),
        sa.Column('backup_method', sa.String(length=100), nullable=True),
        sa.Column('source_path', sa.Text(), nullable=True),
        sa.Column('destination_path', sa.Text(), nullable=True),
        sa.Column('backup_location', sa.String(length=255), nullable=True),
        sa.Column('backup_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('backup_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('backup_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('backup_status', sa.String(length=50), nullable=True),
        sa.Column('data_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('backup_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('compression_ratio', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('deduplication_ratio', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('transfer_rate_mbps', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=True),
        sa.Column('verification_method', sa.String(length=100), nullable=True),
        sa.Column('checksum', sa.String(length=255), nullable=True),
        sa.Column('checksum_algorithm', sa.String(length=50), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True, default=0),
        sa.Column('warning_count', sa.Integer(), nullable=True, default=0),
        sa.Column('error_messages', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('retention_days', sa.Integer(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True, default=False),
        sa.Column('archive_location', sa.String(length=255), nullable=True),
        sa.Column('backup_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('backup_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, default=sa.func.array([])),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'backup_id')
    )
    
    # Create system_updates table (hypertable)
    op.create_table('system_updates',
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('update_id', sa.String(length=255), nullable=False),
        sa.Column('package_name', sa.String(length=255), nullable=False),
        sa.Column('package_type', sa.String(length=50), nullable=True),
        sa.Column('current_version', sa.String(length=255), nullable=True),
        sa.Column('available_version', sa.String(length=255), nullable=True),
        sa.Column('update_type', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('update_status', sa.String(length=50), nullable=True),
        sa.Column('is_security_update', sa.Boolean(), nullable=True, default=False),
        sa.Column('requires_reboot', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_auto_update', sa.Boolean(), nullable=True, default=False),
        sa.Column('release_date', sa.Date(), nullable=True),
        sa.Column('install_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('install_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('download_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('install_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('dependencies', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('[]')),
        sa.Column('repository', sa.String(length=255), nullable=True),
        sa.Column('repository_url', sa.String(length=255), nullable=True),
        sa.Column('maintainer', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('cve_numbers', postgresql.ARRAY(sa.String()), nullable=True, default=sa.func.array([])),
        sa.Column('signature_valid', sa.Boolean(), nullable=True),
        sa.Column('checksum', sa.String(length=255), nullable=True),
        sa.Column('checksum_algorithm', sa.String(length=50), nullable=True),
        sa.Column('error_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.Column('update_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=sa.func.jsonb('{}')),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, default=sa.func.array([])),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('time', 'device_id', 'update_id')
    )
    
    # Create hypertables (TimescaleDB-specific)
    # This will be done when the database is available
    op.execute("""
        -- Create hypertables for time-series data
        -- These will be created by the initialization scripts or when the database is first connected
        
        -- Hypertables will be created with:
        -- SELECT create_hypertable('system_metrics', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('drive_health', 'time', chunk_time_interval => INTERVAL '1 day');  
        -- SELECT create_hypertable('container_snapshots', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('zfs_status', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('zfs_snapshots', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('network_interfaces', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('docker_networks', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('vm_status', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('system_logs', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('backup_status', 'time', chunk_time_interval => INTERVAL '1 day');
        -- SELECT create_hypertable('system_updates', 'time', chunk_time_interval => INTERVAL '1 day');
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop hypertables first
    op.drop_table('system_updates')
    op.drop_table('backup_status')
    op.drop_table('system_logs')
    op.drop_table('vm_status')
    op.drop_table('docker_networks')
    op.drop_table('network_interfaces')
    op.drop_table('zfs_snapshots')
    op.drop_table('zfs_status')
    op.drop_table('container_snapshots')
    op.drop_table('drive_health')
    op.drop_table('system_metrics')
    
    # Drop devices table last (has foreign key references)
    op.drop_table('devices')
    
    # Drop TimescaleDB extension
    op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE;")
