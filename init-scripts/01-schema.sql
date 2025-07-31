-- Infrastructure Management MCP Server - Database Schema
-- This script creates the initial database schema with TimescaleDB extension and core tables

-- =============================================================================
-- ENABLE TIMESCALEDB EXTENSION
-- =============================================================================

-- Enable TimescaleDB extension for time-series data
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable additional extensions for enhanced functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- =============================================================================
-- CORE DEVICE REGISTRY TABLES
-- =============================================================================

-- Devices table for infrastructure node registry
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hostname VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET NOT NULL,
    ssh_port INTEGER DEFAULT 22,
    ssh_username VARCHAR(100) DEFAULT 'root',
    device_type VARCHAR(50) DEFAULT 'server', -- server, container_host, storage, network
    description TEXT,
    location VARCHAR(255),
    tags JSONB DEFAULT '{}',
    monitoring_enabled BOOLEAN DEFAULT true,
    last_seen TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'unknown', -- online, offline, unknown, maintenance
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for devices table
CREATE INDEX IF NOT EXISTS idx_devices_hostname ON devices(hostname);
CREATE INDEX IF NOT EXISTS idx_devices_ip_address ON devices(ip_address);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_monitoring_enabled ON devices(monitoring_enabled);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_tags ON devices USING GIN(tags);

-- =============================================================================
-- TIME-SERIES DATA TABLES (TO BE CONVERTED TO HYPERTABLES)
-- =============================================================================

-- System metrics time-series data
CREATE TABLE IF NOT EXISTS system_metrics (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    cpu_usage_percent NUMERIC(5,2),
    memory_usage_percent NUMERIC(5,2),
    memory_total_bytes BIGINT,
    memory_available_bytes BIGINT,
    load_average_1m NUMERIC(6,2),
    load_average_5m NUMERIC(6,2),
    load_average_15m NUMERIC(6,2),
    disk_usage_percent NUMERIC(5,2),
    disk_total_bytes BIGINT,
    disk_available_bytes BIGINT,
    network_bytes_sent BIGINT,
    network_bytes_recv BIGINT,
    uptime_seconds BIGINT,
    process_count INTEGER,
    additional_metrics JSONB DEFAULT '{}'
);

-- Create indexes for system_metrics (before hypertable conversion)
CREATE INDEX IF NOT EXISTS idx_system_metrics_device_time ON system_metrics(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_time ON system_metrics(time DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_additional ON system_metrics USING GIN(additional_metrics);

-- Drive health monitoring data
CREATE TABLE IF NOT EXISTS drive_health (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    drive_name VARCHAR(100) NOT NULL, -- /dev/sda, /dev/nvme0n1, etc.
    drive_type VARCHAR(20), -- ssd, hdd, nvme
    model VARCHAR(255),
    serial_number VARCHAR(255),
    capacity_bytes BIGINT,
    temperature_celsius INTEGER,
    power_on_hours INTEGER,
    total_lbas_written BIGINT,
    total_lbas_read BIGINT,
    reallocated_sectors INTEGER,
    pending_sectors INTEGER,
    uncorrectable_errors INTEGER,
    smart_status VARCHAR(20), -- PASSED, FAILED, UNKNOWN
    smart_attributes JSONB DEFAULT '{}',
    health_status VARCHAR(20) DEFAULT 'unknown' -- healthy, warning, critical, unknown
);

-- Create indexes for drive_health (before hypertable conversion)
CREATE INDEX IF NOT EXISTS idx_drive_health_device_time ON drive_health(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_drive_health_time ON drive_health(time DESC);
CREATE INDEX IF NOT EXISTS idx_drive_health_drive_name ON drive_health(drive_name);
CREATE INDEX IF NOT EXISTS idx_drive_health_smart_status ON drive_health(smart_status);
CREATE INDEX IF NOT EXISTS idx_drive_health_health_status ON drive_health(health_status);
CREATE INDEX IF NOT EXISTS idx_drive_health_smart_attrs ON drive_health USING GIN(smart_attributes);

-- Container snapshots and metrics
CREATE TABLE IF NOT EXISTS container_snapshots (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    container_id VARCHAR(64) NOT NULL,
    container_name VARCHAR(255) NOT NULL,
    image VARCHAR(255),
    status VARCHAR(50), -- running, paused, restarting, removing, dead, created, exited
    state VARCHAR(50), -- created, restarting, running, removing, paused, exited, dead
    cpu_usage_percent NUMERIC(5,2),
    memory_usage_bytes BIGINT,
    memory_limit_bytes BIGINT,
    network_bytes_sent BIGINT,
    network_bytes_recv BIGINT,
    block_read_bytes BIGINT,
    block_write_bytes BIGINT,
    ports JSONB DEFAULT '[]',
    environment JSONB DEFAULT '{}',
    labels JSONB DEFAULT '{}',
    volumes JSONB DEFAULT '[]',
    networks JSONB DEFAULT '[]'
);

-- Create indexes for container_snapshots (before hypertable conversion)
CREATE INDEX IF NOT EXISTS idx_container_snapshots_device_time ON container_snapshots(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_time ON container_snapshots(time DESC);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_container_id ON container_snapshots(container_id);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_container_name ON container_snapshots(container_name);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_status ON container_snapshots(status);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_state ON container_snapshots(state);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_labels ON container_snapshots USING GIN(labels);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_environment ON container_snapshots USING GIN(environment);

-- =============================================================================
-- ZFS MONITORING TABLES
-- =============================================================================

-- ZFS pool and dataset status
CREATE TABLE IF NOT EXISTS zfs_status (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    pool_name VARCHAR(255) NOT NULL,
    dataset_name VARCHAR(255),
    pool_state VARCHAR(50), -- ONLINE, DEGRADED, FAULTED, OFFLINE, UNAVAIL, REMOVED
    pool_health VARCHAR(50), -- ONLINE, DEGRADED, FAULTED, OFFLINE, UNAVAIL, REMOVED
    capacity_bytes BIGINT,
    allocated_bytes BIGINT,
    free_bytes BIGINT,
    fragmentation_percent NUMERIC(5,2),
    dedup_ratio NUMERIC(6,2),
    compression_ratio NUMERIC(6,2),
    scrub_state VARCHAR(50), -- none, scanning, finished, canceled, suspended
    scrub_progress_percent NUMERIC(5,2),
    scrub_errors INTEGER DEFAULT 0,
    last_scrub TIMESTAMPTZ,
    properties JSONB DEFAULT '{}'
);

-- Create indexes for zfs_status
CREATE INDEX IF NOT EXISTS idx_zfs_status_device_time ON zfs_status(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_zfs_status_time ON zfs_status(time DESC);
CREATE INDEX IF NOT EXISTS idx_zfs_status_pool_name ON zfs_status(pool_name);
CREATE INDEX IF NOT EXISTS idx_zfs_status_pool_state ON zfs_status(pool_state);
CREATE INDEX IF NOT EXISTS idx_zfs_status_pool_health ON zfs_status(pool_health);
CREATE INDEX IF NOT EXISTS idx_zfs_status_scrub_state ON zfs_status(scrub_state);
CREATE INDEX IF NOT EXISTS idx_zfs_status_properties ON zfs_status USING GIN(properties);

-- ZFS snapshots tracking
CREATE TABLE IF NOT EXISTS zfs_snapshots (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    dataset_name VARCHAR(255) NOT NULL,
    snapshot_name VARCHAR(255) NOT NULL,
    creation_time TIMESTAMPTZ NOT NULL,
    used_bytes BIGINT,
    referenced_bytes BIGINT,
    properties JSONB DEFAULT '{}'
);

-- Create indexes for zfs_snapshots
CREATE INDEX IF NOT EXISTS idx_zfs_snapshots_device_time ON zfs_snapshots(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_zfs_snapshots_dataset ON zfs_snapshots(dataset_name);
CREATE INDEX IF NOT EXISTS idx_zfs_snapshots_creation_time ON zfs_snapshots(creation_time DESC);
CREATE INDEX IF NOT EXISTS idx_zfs_snapshots_properties ON zfs_snapshots USING GIN(properties);

-- =============================================================================
-- NETWORK TOPOLOGY AND DOCKER NETWORKS
-- =============================================================================

-- Network topology and interface information
CREATE TABLE IF NOT EXISTS network_interfaces (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    interface_name VARCHAR(100) NOT NULL,
    interface_type VARCHAR(50), -- ethernet, wifi, loopback, bridge, vlan, etc.
    mac_address MACADDR,
    ip_addresses JSONB DEFAULT '[]', -- Array of IP addresses
    mtu INTEGER,
    speed_mbps INTEGER,
    duplex VARCHAR(20), -- full, half, unknown
    state VARCHAR(20), -- up, down, unknown
    rx_bytes BIGINT,
    tx_bytes BIGINT,
    rx_packets BIGINT,
    tx_packets BIGINT,
    rx_errors BIGINT,
    tx_errors BIGINT,
    rx_dropped BIGINT,
    tx_dropped BIGINT
);

-- Create indexes for network_interfaces
CREATE INDEX IF NOT EXISTS idx_network_interfaces_device_time ON network_interfaces(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_network_interfaces_interface_name ON network_interfaces(interface_name);
CREATE INDEX IF NOT EXISTS idx_network_interfaces_interface_type ON network_interfaces(interface_type);
CREATE INDEX IF NOT EXISTS idx_network_interfaces_state ON network_interfaces(state);
CREATE INDEX IF NOT EXISTS idx_network_interfaces_ip_addresses ON network_interfaces USING GIN(ip_addresses);

-- Docker networks tracking
CREATE TABLE IF NOT EXISTS docker_networks (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    network_id VARCHAR(64) NOT NULL,
    network_name VARCHAR(255) NOT NULL,
    driver VARCHAR(100),
    scope VARCHAR(50), -- local, global, swarm
    subnet CIDR,
    gateway INET,
    containers_count INTEGER DEFAULT 0,
    labels JSONB DEFAULT '{}',
    options JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}'
);

-- Create indexes for docker_networks
CREATE INDEX IF NOT EXISTS idx_docker_networks_device_time ON docker_networks(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_docker_networks_network_id ON docker_networks(network_id);
CREATE INDEX IF NOT EXISTS idx_docker_networks_network_name ON docker_networks(network_name);
CREATE INDEX IF NOT EXISTS idx_docker_networks_driver ON docker_networks(driver);
CREATE INDEX IF NOT EXISTS idx_docker_networks_scope ON docker_networks(scope);
CREATE INDEX IF NOT EXISTS idx_docker_networks_labels ON docker_networks USING GIN(labels);

-- =============================================================================
-- BACKUP AND MAINTENANCE TRACKING
-- =============================================================================

-- Backup status and history
CREATE TABLE IF NOT EXISTS backup_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    backup_type VARCHAR(100) NOT NULL, -- system, database, container, zfs, custom
    backup_name VARCHAR(255) NOT NULL,
    source_path TEXT,
    destination_path TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    size_bytes BIGINT,
    compressed_size_bytes BIGINT,
    files_count BIGINT,
    success_count BIGINT,
    error_count BIGINT,
    warning_count BIGINT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for backup_status
CREATE INDEX IF NOT EXISTS idx_backup_status_device_id ON backup_status(device_id);
CREATE INDEX IF NOT EXISTS idx_backup_status_backup_type ON backup_status(backup_type);
CREATE INDEX IF NOT EXISTS idx_backup_status_status ON backup_status(status);
CREATE INDEX IF NOT EXISTS idx_backup_status_start_time ON backup_status(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_backup_status_end_time ON backup_status(end_time DESC);
CREATE INDEX IF NOT EXISTS idx_backup_status_created_at ON backup_status(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_status_metadata ON backup_status USING GIN(metadata);

-- System updates tracking
CREATE TABLE IF NOT EXISTS system_updates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    package_type VARCHAR(50) NOT NULL, -- system, container, snap, flatpak, custom
    package_name VARCHAR(255) NOT NULL,
    current_version VARCHAR(255),
    available_version VARCHAR(255),
    update_priority VARCHAR(20) DEFAULT 'normal', -- critical, high, normal, low
    security_update BOOLEAN DEFAULT false,
    release_date DATE,
    description TEXT,
    changelog TEXT,
    update_status VARCHAR(50) DEFAULT 'available', -- available, pending, installed, failed, skipped
    last_checked TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for system_updates
CREATE INDEX IF NOT EXISTS idx_system_updates_device_id ON system_updates(device_id);
CREATE INDEX IF NOT EXISTS idx_system_updates_package_type ON system_updates(package_type);
CREATE INDEX IF NOT EXISTS idx_system_updates_package_name ON system_updates(package_name);
CREATE INDEX IF NOT EXISTS idx_system_updates_update_priority ON system_updates(update_priority);
CREATE INDEX IF NOT EXISTS idx_system_updates_security_update ON system_updates(security_update);
CREATE INDEX IF NOT EXISTS idx_system_updates_update_status ON system_updates(update_status);
CREATE INDEX IF NOT EXISTS idx_system_updates_last_checked ON system_updates(last_checked DESC);
CREATE INDEX IF NOT EXISTS idx_system_updates_metadata ON system_updates USING GIN(metadata);

-- =============================================================================
-- VIRTUAL MACHINE MONITORING
-- =============================================================================

-- Virtual machine status and metrics
CREATE TABLE IF NOT EXISTS vm_status (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    vm_id VARCHAR(255) NOT NULL,
    vm_name VARCHAR(255) NOT NULL,
    hypervisor VARCHAR(100), -- kvm, xen, vmware, virtualbox, etc.
    status VARCHAR(50), -- running, paused, shutdown, crashed, dying, pmsuspended
    vcpus INTEGER,
    memory_mb INTEGER,
    memory_usage_mb INTEGER,
    cpu_usage_percent NUMERIC(5,2),
    disk_usage_bytes BIGINT,
    network_bytes_sent BIGINT,
    network_bytes_recv BIGINT,
    uptime_seconds BIGINT,
    boot_time TIMESTAMPTZ,
    config JSONB DEFAULT '{}'
);

-- Create indexes for vm_status
CREATE INDEX IF NOT EXISTS idx_vm_status_device_time ON vm_status(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_vm_status_time ON vm_status(time DESC);
CREATE INDEX IF NOT EXISTS idx_vm_status_vm_id ON vm_status(vm_id);
CREATE INDEX IF NOT EXISTS idx_vm_status_vm_name ON vm_status(vm_name);
CREATE INDEX IF NOT EXISTS idx_vm_status_hypervisor ON vm_status(hypervisor);
CREATE INDEX IF NOT EXISTS idx_vm_status_status ON vm_status(status);
CREATE INDEX IF NOT EXISTS idx_vm_status_config ON vm_status USING GIN(config);

-- =============================================================================
-- SYSTEM LOGS AND EVENTS
-- =============================================================================

-- System logs aggregation and analysis
CREATE TABLE IF NOT EXISTS system_logs (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    service_name VARCHAR(255),
    log_level VARCHAR(20), -- emergency, alert, critical, error, warning, notice, info, debug
    message TEXT NOT NULL,
    source VARCHAR(255), -- systemd, syslog, kernel, application, etc.
    process_id INTEGER,
    user_name VARCHAR(100),
    facility VARCHAR(50), -- kern, user, mail, daemon, auth, syslog, etc.
    raw_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for system_logs
CREATE INDEX IF NOT EXISTS idx_system_logs_device_time ON system_logs(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_time ON system_logs(time DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_service_name ON system_logs(service_name);
CREATE INDEX IF NOT EXISTS idx_system_logs_log_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_system_logs_source ON system_logs(source);
CREATE INDEX IF NOT EXISTS idx_system_logs_process_id ON system_logs(process_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_facility ON system_logs(facility);
CREATE INDEX IF NOT EXISTS idx_system_logs_message_text ON system_logs USING GIN(to_tsvector('english', message));
CREATE INDEX IF NOT EXISTS idx_system_logs_metadata ON system_logs USING GIN(metadata);

-- =============================================================================
-- UPDATE TRIGGERS FOR TIMESTAMP MANAGEMENT
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add update trigger to devices table
CREATE TRIGGER update_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- INITIAL SAMPLE DATA (OPTIONAL FOR TESTING)
-- =============================================================================

-- Insert a sample device for testing purposes
INSERT INTO devices (hostname, ip_address, device_type, description, location, tags)
VALUES (
    'localhost',
    '127.0.0.1',
    'development',
    'Local development machine for testing',
    'local',
    '{"environment": "development", "role": "test"}'
) ON CONFLICT (hostname) DO NOTHING;

-- Log schema initialization
DO $$
BEGIN
    RAISE NOTICE 'Infrastructure Management MCP Server schema initialized successfully';
    RAISE NOTICE 'TimescaleDB extension enabled: %', (SELECT installed_version FROM pg_available_extensions WHERE name = 'timescaledb');
    RAISE NOTICE 'Total tables created: %', (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public');
    RAISE NOTICE 'Total indexes created: %', (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public');
END $$;