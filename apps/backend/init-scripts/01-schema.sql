-- Infrastructure Management MCP Server - Database Schema
-- This script creates the initial database schema with PostgreSQL and core tables

-- =============================================================================
-- ENABLE POSTGRESQL EXTENSIONS
-- =============================================================================

-- Enable essential PostgreSQL extensions
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
    ip_address INET,
    ssh_port INTEGER DEFAULT 22,
    ssh_username VARCHAR(100) DEFAULT 'root',
    device_type VARCHAR(50) DEFAULT 'server', -- server, container_host, storage, network
    description TEXT,
    location VARCHAR(255),
    tags JSONB DEFAULT '{}',
    docker_compose_path VARCHAR(512), -- Primary docker-compose project path
    docker_appdata_path VARCHAR(512), -- Primary appdata directory path
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
-- TIME-SERIES DATA TABLES (REGULAR POSTGRESQL TABLES)
-- =============================================================================

-- System metrics time-series data
CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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

-- Create indexes for system_metrics
CREATE INDEX IF NOT EXISTS idx_system_metrics_device_time ON system_metrics(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_time ON system_metrics(time DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_additional ON system_metrics USING GIN(additional_metrics);

-- Drive health monitoring data
CREATE TABLE IF NOT EXISTS drive_health (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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

-- Create indexes for drive_health
CREATE INDEX IF NOT EXISTS idx_drive_health_device_time ON drive_health(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_drive_health_time ON drive_health(time DESC);
CREATE INDEX IF NOT EXISTS idx_drive_health_drive_name ON drive_health(drive_name);
CREATE INDEX IF NOT EXISTS idx_drive_health_smart_status ON drive_health(smart_status);
CREATE INDEX IF NOT EXISTS idx_drive_health_health_status ON drive_health(health_status);
CREATE INDEX IF NOT EXISTS idx_drive_health_smart_attrs ON drive_health USING GIN(smart_attributes);

-- Container snapshots and metrics
CREATE TABLE IF NOT EXISTS container_snapshots (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    container_id VARCHAR(64) NOT NULL,
    container_name VARCHAR(255) NOT NULL,
    image VARCHAR(500),
    status VARCHAR(50), -- running, paused, restarting, removing, dead, created, exited
    state JSONB DEFAULT '{}',
    running BOOLEAN,
    paused BOOLEAN,
    restarting BOOLEAN,
    oom_killed BOOLEAN,
    dead BOOLEAN,
    pid INTEGER,
    exit_code INTEGER,
    cpu_usage_percent NUMERIC(5,2),
    memory_usage_bytes BIGINT,
    memory_limit_bytes BIGINT,
    memory_cache_bytes BIGINT,
    network_bytes_sent BIGINT,
    network_bytes_recv BIGINT,
    block_read_bytes BIGINT,
    block_write_bytes BIGINT,
    ports JSONB DEFAULT '[]',
    environment JSONB DEFAULT '{}',
    labels JSONB DEFAULT '{}',
    volumes JSONB DEFAULT '[]',
    networks JSONB DEFAULT '[]',
    resource_limits JSONB DEFAULT '{}',
    metadata_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for container_snapshots
CREATE INDEX IF NOT EXISTS idx_container_snapshots_device_time ON container_snapshots(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_time ON container_snapshots(time DESC);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_container_id ON container_snapshots(container_id);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_container_name ON container_snapshots(container_name);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_status ON container_snapshots(status);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_labels ON container_snapshots USING GIN(labels);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_environment ON container_snapshots USING GIN(environment);

-- =============================================================================
-- ZFS MONITORING TABLES
-- =============================================================================

-- ZFS pool and dataset status
CREATE TABLE IF NOT EXISTS zfs_status (
    id BIGSERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    pool_name VARCHAR(255) NOT NULL,
    dataset_name VARCHAR(255),
    pool_state VARCHAR(50), -- ONLINE, DEGRADED, FAULTED, OFFLINE, UNAVAIL, REMOVED
    pool_health VARCHAR(50), -- ONLINE, DEGRADED, FAULTED, OFFLINE, UNAVAIL, REMOVED
    pool_capacity_bytes BIGINT,
    pool_allocated_bytes BIGINT,
    pool_free_bytes BIGINT,
    fragmentation_percent NUMERIC(5,2),
    dedup_ratio NUMERIC(8,2),
    compression_ratio NUMERIC(8,2),
    dataset_used_bytes BIGINT,
    dataset_available_bytes BIGINT,
    dataset_referenced_bytes BIGINT,
    dataset_compression VARCHAR(50),
    dataset_mountpoint VARCHAR(500),
    properties JSONB DEFAULT '{}',
    errors JSONB DEFAULT '[]'
);

-- Create indexes for zfs_status
CREATE INDEX IF NOT EXISTS idx_zfs_status_device_time ON zfs_status(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_zfs_status_time ON zfs_status(time DESC);
CREATE INDEX IF NOT EXISTS idx_zfs_status_pool_name ON zfs_status(pool_name);
CREATE INDEX IF NOT EXISTS idx_zfs_status_dataset_name ON zfs_status(dataset_name);
CREATE INDEX IF NOT EXISTS idx_zfs_status_pool_state ON zfs_status(pool_state);
CREATE INDEX IF NOT EXISTS idx_zfs_status_pool_health ON zfs_status(pool_health);
CREATE INDEX IF NOT EXISTS idx_zfs_status_properties ON zfs_status USING GIN(properties);

-- =============================================================================
-- PROXY CONFIGURATION MANAGEMENT
-- =============================================================================

-- SWAG reverse proxy configurations
CREATE TABLE IF NOT EXISTS proxy_configurations (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    service_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    content_hash VARCHAR(64),
    ssl_enabled BOOLEAN DEFAULT false,
    domains JSONB DEFAULT '[]',
    upstream_port INTEGER,
    upstream_protocol VARCHAR(10) DEFAULT 'http',
    auth_enabled BOOLEAN DEFAULT false,
    custom_config TEXT,
    status VARCHAR(20) DEFAULT 'active', -- active, inactive, error
    last_validated_at TIMESTAMPTZ,
    sync_status VARCHAR(20) DEFAULT 'synced', -- synced, pending, error
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for proxy_configurations
CREATE INDEX IF NOT EXISTS idx_proxy_configurations_device_id ON proxy_configurations(device_id);
CREATE INDEX IF NOT EXISTS idx_proxy_configurations_service_name ON proxy_configurations(service_name);
CREATE INDEX IF NOT EXISTS idx_proxy_configurations_file_path ON proxy_configurations(file_path);
CREATE INDEX IF NOT EXISTS idx_proxy_configurations_status ON proxy_configurations(status);
CREATE INDEX IF NOT EXISTS idx_proxy_configurations_ssl_enabled ON proxy_configurations(ssl_enabled);
CREATE INDEX IF NOT EXISTS idx_proxy_configurations_domains ON proxy_configurations USING GIN(domains);

-- =============================================================================
-- AUDIT AND METADATA TABLES
-- =============================================================================

-- Data collection audit trail
CREATE TABLE IF NOT EXISTS data_collection_audit (
    id BIGSERIAL PRIMARY KEY,
    data_type VARCHAR(50) NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    correlation_id VARCHAR(100),
    collected_at TIMESTAMPTZ NOT NULL,
    collection_duration_seconds NUMERIC(8,3),
    data_size INTEGER,
    cache_hit BOOLEAN DEFAULT false,
    force_refresh BOOLEAN DEFAULT false,
    metadata_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for data_collection_audit
CREATE INDEX IF NOT EXISTS idx_data_collection_audit_device_id ON data_collection_audit(device_id);
CREATE INDEX IF NOT EXISTS idx_data_collection_audit_data_type ON data_collection_audit(data_type);
CREATE INDEX IF NOT EXISTS idx_data_collection_audit_collected_at ON data_collection_audit(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_collection_audit_correlation_id ON data_collection_audit(correlation_id);

-- Configuration snapshots for change tracking
CREATE TABLE IF NOT EXISTS configuration_snapshots (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    config_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    raw_content TEXT NOT NULL,
    parsed_data JSONB DEFAULT '{}',
    change_type VARCHAR(20), -- CREATE, MODIFY, DELETE, MOVE
    previous_hash VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for configuration_snapshots
CREATE INDEX IF NOT EXISTS idx_configuration_snapshots_device_time ON configuration_snapshots(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_configuration_snapshots_config_type ON configuration_snapshots(config_type);
CREATE INDEX IF NOT EXISTS idx_configuration_snapshots_file_path ON configuration_snapshots(file_path);
CREATE INDEX IF NOT EXISTS idx_configuration_snapshots_content_hash ON configuration_snapshots(content_hash);

-- Service dependencies mapping
CREATE TABLE IF NOT EXISTS service_dependencies (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    service_name VARCHAR(255) NOT NULL,
    dependency_type VARCHAR(50) NOT NULL, -- container, volume, network, config
    dependency_name VARCHAR(255) NOT NULL,
    relationship VARCHAR(20) NOT NULL, -- depends_on, volume_mount, network_connect
    metadata_info JSONB DEFAULT '{}',
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active' -- active, inactive, missing
);

-- Create indexes for service_dependencies
CREATE INDEX IF NOT EXISTS idx_service_dependencies_device_id ON service_dependencies(device_id);
CREATE INDEX IF NOT EXISTS idx_service_dependencies_service_name ON service_dependencies(service_name);
CREATE INDEX IF NOT EXISTS idx_service_dependencies_dependency_type ON service_dependencies(dependency_type);
CREATE INDEX IF NOT EXISTS idx_service_dependencies_relationship ON service_dependencies(relationship);

-- =============================================================================
-- PERFORMANCE OPTIMIZATION RULES
-- =============================================================================

-- Data retention policy (manual cleanup for regular PostgreSQL)
-- System metrics: Keep last 90 days, aggregate older data
-- Container snapshots: Keep last 30 days  
-- Drive health: Keep last 180 days
-- Configuration snapshots: Keep permanently (small data size)
-- Audit logs: Keep last 365 days

COMMENT ON DATABASE infrastructor IS 'Infrastructure Management System Database - PostgreSQL';
COMMENT ON TABLE devices IS 'Infrastructure device registry and connectivity information';
COMMENT ON TABLE system_metrics IS 'System performance metrics time-series data';
COMMENT ON TABLE drive_health IS 'Storage drive health and SMART monitoring data';
COMMENT ON TABLE container_snapshots IS 'Docker container status and resource usage snapshots';
COMMENT ON TABLE zfs_status IS 'ZFS filesystem and pool status monitoring';
COMMENT ON TABLE proxy_configurations IS 'Reverse proxy configuration management';
COMMENT ON TABLE data_collection_audit IS 'Audit trail for all data collection operations';
COMMENT ON TABLE configuration_snapshots IS 'Configuration file change tracking';
COMMENT ON TABLE service_dependencies IS 'Service dependency mapping and relationship tracking';