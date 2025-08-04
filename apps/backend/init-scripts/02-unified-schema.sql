-- Infrastructure Management MCP Server - Unified Database Schema
-- This script creates the complete, unified database schema with TimescaleDB extension
-- Includes both existing tables (rewritten) and new unified architecture tables

-- =============================================================================
-- ENABLE TIMESCALEDB EXTENSION AND CORE EXTENSIONS
-- =============================================================================

-- Enable TimescaleDB extension for time-series data
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable additional extensions for enhanced functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- =============================================================================
-- EXISTING TABLES (REWRITTEN FOR UNIFIED ARCHITECTURE)
-- =============================================================================

-- Device Registry (Enhanced for unified architecture)
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname VARCHAR(255) UNIQUE NOT NULL,
    device_type VARCHAR(50) DEFAULT 'server',
    description TEXT,
    location VARCHAR(255),
    
    -- Docker configuration paths
    docker_compose_path VARCHAR(512),
    docker_appdata_path VARCHAR(512),
    
    -- Enhanced metadata storage
    metadata JSONB DEFAULT '{}',
    tags JSONB DEFAULT '{}',
    
    -- Monitoring and status
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'unknown', -- online, offline, unknown, maintenance
    
    -- Data collection tracking (new fields)
    last_successful_collection TIMESTAMPTZ,
    last_collection_status VARCHAR(20) DEFAULT 'never', -- never, success, failed, partial
    collection_error_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for devices table
CREATE INDEX IF NOT EXISTS idx_devices_hostname ON devices(hostname);
CREATE INDEX IF NOT EXISTS idx_devices_device_type ON devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_monitoring_enabled ON devices(monitoring_enabled);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_devices_last_collection ON devices(last_successful_collection);
CREATE INDEX IF NOT EXISTS idx_devices_collection_status ON devices(last_collection_status);
CREATE INDEX IF NOT EXISTS idx_devices_metadata ON devices USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_devices_tags ON devices USING GIN(tags);

-- System Metrics Hypertable (Enhanced)
CREATE TABLE IF NOT EXISTS system_metrics (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    
    -- CPU metrics
    cpu_usage FLOAT,
    
    -- Memory metrics
    memory_usage FLOAT,
    memory_total_bytes BIGINT,
    memory_available_bytes BIGINT,
    
    -- Load average metrics
    load_average_1m NUMERIC(6,2),
    load_average_5m NUMERIC(6,2),
    load_average_15m NUMERIC(6,2),
    
    -- Disk I/O as JSONB for flexibility
    disk_io JSONB DEFAULT '{}',
    
    -- Network traffic as JSONB for flexibility
    network_traffic JSONB DEFAULT '{}',
    
    -- Process and uptime metrics
    uptime_seconds BIGINT,
    process_count INTEGER,
    
    -- Additional metrics storage
    additional_metrics JSONB DEFAULT '{}',
    
    PRIMARY KEY (time, device_id)
);

-- Container Snapshots Hypertable (Enhanced)
CREATE TABLE IF NOT EXISTS container_snapshots (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    container_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    image VARCHAR(255),
    status VARCHAR(50),
    
    -- Resource usage metrics
    cpu_usage FLOAT,
    memory_usage_bytes BIGINT,
    memory_limit_bytes BIGINT,
    
    -- Network and disk I/O
    network_bytes_sent BIGINT,
    network_bytes_recv BIGINT,
    block_read_bytes BIGINT,
    block_write_bytes BIGINT,
    
    -- Configuration data as JSONB
    ports JSONB DEFAULT '[]',
    environment JSONB DEFAULT '{}',
    labels JSONB DEFAULT '{}',
    volumes JSONB DEFAULT '[]',
    networks JSONB DEFAULT '[]',
    
    PRIMARY KEY (time, device_id, container_id)
);

-- Drive Health Hypertable (Enhanced)
CREATE TABLE IF NOT EXISTS drive_health (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    drive_name VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    serial_number VARCHAR(255),
    
    -- S.M.A.R.T. attributes as JSONB for flexibility
    smart_attributes JSONB DEFAULT '{}',
    
    -- Key health indicators
    temperature_celsius INTEGER,
    power_on_hours INTEGER,
    is_healthy BOOLEAN,
    
    -- Additional drive info
    capacity_bytes BIGINT,
    drive_type VARCHAR(20), -- ssd, hdd, nvme
    smart_status VARCHAR(20), -- PASSED, FAILED, UNKNOWN
    health_status VARCHAR(20) DEFAULT 'unknown', -- healthy, warning, critical, unknown
    
    PRIMARY KEY (time, device_id, drive_name)
);

-- =============================================================================
-- NEW TABLES FOR UNIFIED ARCHITECTURE
-- =============================================================================

-- 1. Data Collection Audit Table
CREATE TABLE IF NOT EXISTS data_collection_audit (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    operation_id UUID NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    collection_method VARCHAR(50) NOT NULL,
    collection_source VARCHAR(100),
    force_refresh BOOLEAN DEFAULT FALSE,
    cache_hit BOOLEAN DEFAULT FALSE,
    duration_ms INTEGER,
    ssh_command_count INTEGER DEFAULT 0,
    data_size_bytes BIGINT,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    warnings JSONB DEFAULT '[]',
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    freshness_threshold INTEGER,
    PRIMARY KEY (time, device_id, operation_id)
);

-- 2. Configuration Snapshots Table
CREATE TABLE IF NOT EXISTS configuration_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    time TIMESTAMPTZ NOT NULL,
    config_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    file_size_bytes INTEGER,
    raw_content TEXT NOT NULL,
    parsed_data JSONB DEFAULT '{}',
    change_type VARCHAR(20) NOT NULL,
    previous_hash VARCHAR(64),
    file_modified_time TIMESTAMPTZ,
    collection_source VARCHAR(50) NOT NULL,
    detection_latency_ms INTEGER,
    affected_services JSONB DEFAULT '[]',
    requires_restart BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20) DEFAULT 'MEDIUM'
);

-- 3. Configuration Change Events Table
CREATE TABLE IF NOT EXISTS configuration_change_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    snapshot_id UUID NOT NULL REFERENCES configuration_snapshots(id) ON DELETE CASCADE,
    time TIMESTAMPTZ NOT NULL,
    config_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    change_type VARCHAR(20) NOT NULL,
    affected_services JSONB DEFAULT '[]',
    service_dependencies JSONB DEFAULT '[]',
    requires_restart BOOLEAN DEFAULT FALSE,
    restart_services JSONB DEFAULT '[]',
    changes_summary JSONB DEFAULT '{}',
    risk_level VARCHAR(20) DEFAULT 'MEDIUM',
    confidence_score NUMERIC(3, 2),
    processed BOOLEAN DEFAULT FALSE,
    notifications_sent JSONB DEFAULT '[]'
);

-- 4. Service Performance Metrics Table
CREATE TABLE IF NOT EXISTS service_performance_metrics (
    time TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(50) NOT NULL,
    operations_total INTEGER DEFAULT 0,
    operations_successful INTEGER DEFAULT 0,
    operations_failed INTEGER DEFAULT 0,
    operations_cached INTEGER DEFAULT 0,
    avg_duration_ms NUMERIC(8, 2),
    max_duration_ms INTEGER,
    min_duration_ms INTEGER,
    ssh_connections_created INTEGER DEFAULT 0,
    ssh_connections_reused INTEGER DEFAULT 0,
    ssh_commands_executed INTEGER DEFAULT 0,
    cache_hit_ratio NUMERIC(5, 2),
    cache_size_entries INTEGER,
    cache_evictions INTEGER DEFAULT 0,
    data_collected_bytes BIGINT DEFAULT 0,
    database_writes INTEGER DEFAULT 0,
    error_types JSONB DEFAULT '{}',
    top_errors JSONB DEFAULT '[]',
    PRIMARY KEY (time, service_name)
);

-- 5. Cache Metadata Table
CREATE TABLE IF NOT EXISTS cache_metadata (
    cache_key VARCHAR(255) PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    data_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    access_count INTEGER DEFAULT 1,
    data_size_bytes INTEGER,
    ttl_seconds INTEGER NOT NULL,
    invalidated BOOLEAN DEFAULT FALSE,
    invalidated_at TIMESTAMPTZ,
    invalidation_reason VARCHAR(100),
    collection_method VARCHAR(50),
    command_hash VARCHAR(64)
);

-- =============================================================================
-- EXISTING TABLES FROM CURRENT SCHEMA (PRESERVED)
-- =============================================================================

-- ZFS Status Table (from existing schema)
CREATE TABLE IF NOT EXISTS zfs_status (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    pool_name VARCHAR(255) NOT NULL,
    dataset_name VARCHAR(255),
    pool_state VARCHAR(50),
    pool_health VARCHAR(50),
    capacity_bytes BIGINT,
    allocated_bytes BIGINT,
    free_bytes BIGINT,
    fragmentation_percent NUMERIC(5,2),
    dedup_ratio NUMERIC(6,2),
    compression_ratio NUMERIC(6,2),
    scrub_state VARCHAR(50),
    scrub_progress_percent NUMERIC(5,2),
    scrub_errors INTEGER DEFAULT 0,
    last_scrub TIMESTAMPTZ,
    properties JSONB DEFAULT '{}'
);

-- ZFS Snapshots Table (from existing schema)
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

-- Network Interfaces Table (from existing schema)
CREATE TABLE IF NOT EXISTS network_interfaces (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    interface_name VARCHAR(100) NOT NULL,
    interface_type VARCHAR(50),
    mac_address MACADDR,
    ip_addresses JSONB DEFAULT '[]',
    mtu INTEGER,
    speed_mbps INTEGER,
    duplex VARCHAR(20),
    state VARCHAR(20),
    rx_bytes BIGINT,
    tx_bytes BIGINT,
    rx_packets BIGINT,
    tx_packets BIGINT,
    rx_errors BIGINT,
    tx_errors BIGINT,
    rx_dropped BIGINT,
    tx_dropped BIGINT
);

-- Docker Networks Table (from existing schema)
CREATE TABLE IF NOT EXISTS docker_networks (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    network_id VARCHAR(64) NOT NULL,
    network_name VARCHAR(255) NOT NULL,
    driver VARCHAR(100),
    scope VARCHAR(50),
    subnet CIDR,
    gateway INET,
    containers_count INTEGER DEFAULT 0,
    labels JSONB DEFAULT '{}',
    options JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}'
);

-- Backup Status Table (from existing schema)
CREATE TABLE IF NOT EXISTS backup_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    backup_type VARCHAR(100) NOT NULL,
    backup_name VARCHAR(255) NOT NULL,
    source_path TEXT,
    destination_path TEXT,
    status VARCHAR(50) DEFAULT 'pending',
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

-- System Updates Table (from existing schema)
CREATE TABLE IF NOT EXISTS system_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    package_type VARCHAR(50) NOT NULL,
    package_name VARCHAR(255) NOT NULL,
    current_version VARCHAR(255),
    available_version VARCHAR(255),
    update_priority VARCHAR(20) DEFAULT 'normal',
    security_update BOOLEAN DEFAULT FALSE,
    release_date DATE,
    description TEXT,
    changelog TEXT,
    update_status VARCHAR(50) DEFAULT 'available',
    last_checked TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- VM Status Table (from existing schema)
CREATE TABLE IF NOT EXISTS vm_status (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    vm_id VARCHAR(255) NOT NULL,
    vm_name VARCHAR(255) NOT NULL,
    hypervisor VARCHAR(100),
    status VARCHAR(50),
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

-- System Logs Table (from existing schema)
CREATE TABLE IF NOT EXISTS system_logs (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    service_name VARCHAR(255),
    log_level VARCHAR(20),
    message TEXT NOT NULL,
    source VARCHAR(255),
    process_id INTEGER,
    user_name VARCHAR(100),
    facility VARCHAR(50),
    raw_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- =============================================================================
-- CONVERT TIME-SERIES TABLES TO TIMESCALEDB HYPERTABLES
-- =============================================================================

-- Convert existing and new time-series tables to hypertables
SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);
SELECT create_hypertable('container_snapshots', 'time', if_not_exists => TRUE);
SELECT create_hypertable('drive_health', 'time', if_not_exists => TRUE);
SELECT create_hypertable('data_collection_audit', 'time', if_not_exists => TRUE);
SELECT create_hypertable('configuration_snapshots', 'time', if_not_exists => TRUE);
SELECT create_hypertable('configuration_change_events', 'time', if_not_exists => TRUE);
SELECT create_hypertable('service_performance_metrics', 'time', if_not_exists => TRUE);
SELECT create_hypertable('zfs_status', 'time', if_not_exists => TRUE);
SELECT create_hypertable('zfs_snapshots', 'time', if_not_exists => TRUE);
SELECT create_hypertable('network_interfaces', 'time', if_not_exists => TRUE);
SELECT create_hypertable('docker_networks', 'time', if_not_exists => TRUE);
SELECT create_hypertable('vm_status', 'time', if_not_exists => TRUE);
SELECT create_hypertable('system_logs', 'time', if_not_exists => TRUE);

-- =============================================================================
-- CREATE COMPREHENSIVE INDEXES
-- =============================================================================

-- System metrics indexes
CREATE INDEX IF NOT EXISTS idx_system_metrics_device_time ON system_metrics(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_time ON system_metrics(time DESC);

-- Container snapshots indexes
CREATE INDEX IF NOT EXISTS idx_container_snapshots_device_time ON container_snapshots(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_container_id ON container_snapshots(container_id);
CREATE INDEX IF NOT EXISTS idx_container_snapshots_status ON container_snapshots(status);

-- Drive health indexes
CREATE INDEX IF NOT EXISTS idx_drive_health_device_time ON drive_health(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_drive_health_drive_name ON drive_health(drive_name);
CREATE INDEX IF NOT EXISTS idx_drive_health_is_healthy ON drive_health(is_healthy);

-- Data collection audit indexes
CREATE INDEX IF NOT EXISTS idx_data_collection_audit_device_time ON data_collection_audit(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_data_collection_audit_operation_id ON data_collection_audit(operation_id);
CREATE INDEX IF NOT EXISTS idx_data_collection_audit_data_type ON data_collection_audit(data_type);
CREATE INDEX IF NOT EXISTS idx_data_collection_audit_status ON data_collection_audit(status);

-- Configuration snapshots indexes
CREATE INDEX IF NOT EXISTS idx_configuration_snapshots_device_time ON configuration_snapshots(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_configuration_snapshots_config_type ON configuration_snapshots(config_type);
CREATE INDEX IF NOT EXISTS idx_configuration_snapshots_file_path ON configuration_snapshots(file_path);
CREATE INDEX IF NOT EXISTS idx_configuration_snapshots_content_hash ON configuration_snapshots(content_hash);

-- Configuration change events indexes
CREATE INDEX IF NOT EXISTS idx_configuration_change_events_device_time ON configuration_change_events(device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_configuration_change_events_snapshot_id ON configuration_change_events(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_configuration_change_events_processed ON configuration_change_events(processed);

-- Service performance metrics indexes
CREATE INDEX IF NOT EXISTS idx_service_performance_metrics_service_time ON service_performance_metrics(service_name, time DESC);
CREATE INDEX IF NOT EXISTS idx_service_performance_metrics_time ON service_performance_metrics(time DESC);

-- Cache metadata indexes
CREATE INDEX IF NOT EXISTS idx_cache_metadata_device_id ON cache_metadata(device_id);
CREATE INDEX IF NOT EXISTS idx_cache_metadata_data_type ON cache_metadata(data_type);
CREATE INDEX IF NOT EXISTS idx_cache_metadata_expires_at ON cache_metadata(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_metadata_invalidated ON cache_metadata(invalidated);

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
DROP TRIGGER IF EXISTS update_devices_updated_at ON devices;
CREATE TRIGGER update_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- INITIAL SAMPLE DATA (OPTIONAL FOR TESTING)
-- =============================================================================

-- Insert a sample device for testing purposes (updated for new schema)
INSERT INTO devices (hostname, device_type, description, location, metadata, tags)
VALUES (
    'localhost',
    'development',
    'Local development machine for testing unified architecture',
    'local',
    '{"environment": "development", "role": "test", "architecture": "unified"}',
    '{"environment": "development", "role": "test", "phase": "1"}'
) ON CONFLICT (hostname) DO UPDATE SET
    description = EXCLUDED.description,
    metadata = EXCLUDED.metadata,
    tags = EXCLUDED.tags,
    updated_at = NOW();

-- =============================================================================
-- SCHEMA INITIALIZATION LOGGING
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Infrastructure Management MCP Server - Unified Schema initialized successfully';
    RAISE NOTICE 'TimescaleDB extension enabled: %', (SELECT installed_version FROM pg_available_extensions WHERE name = 'timescaledb');
    RAISE NOTICE 'Total tables created: %', (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public');
    RAISE NOTICE 'Total hypertables created: %', (SELECT COUNT(*) FROM timescaledb_information.hypertables);
    RAISE NOTICE 'Total indexes created: %', (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public');
    RAISE NOTICE 'Unified architecture ready for Phase 1 implementation';
END $$;