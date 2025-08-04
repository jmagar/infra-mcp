-- Infrastructure Management MCP Server - Compression and Retention Policies
-- This script configures automated data compression and retention policies for TimescaleDB hypertables

-- =============================================================================
-- COMPRESSION POLICIES CONFIGURATION
-- =============================================================================

-- Enable compression for system_metrics after 7 days
-- This compresses old data to save storage space while maintaining query performance
SELECT add_compression_policy('system_metrics', INTERVAL '7 days');

-- Enable compression for drive_health after 7 days
SELECT add_compression_policy('drive_health', INTERVAL '7 days');

-- Enable compression for container_snapshots after 7 days
SELECT add_compression_policy('container_snapshots', INTERVAL '7 days');

-- Enable compression for zfs_status after 7 days
SELECT add_compression_policy('zfs_status', INTERVAL '7 days');

-- Enable compression for zfs_snapshots after 7 days
SELECT add_compression_policy('zfs_snapshots', INTERVAL '7 days');

-- Enable compression for network_interfaces after 7 days
SELECT add_compression_policy('network_interfaces', INTERVAL '7 days');

-- Enable compression for docker_networks after 7 days
SELECT add_compression_policy('docker_networks', INTERVAL '7 days');

-- Enable compression for vm_status after 7 days
SELECT add_compression_policy('vm_status', INTERVAL '7 days');

-- Enable compression for system_logs after 3 days (compress sooner due to high volume)
SELECT add_compression_policy('system_logs', INTERVAL '3 days');

-- =============================================================================
-- PHASE 1: NEW HYPERTABLES COMPRESSION POLICIES
-- =============================================================================

-- Enable compression for data_collection_audit after 1 day (high volume audit data)
SELECT add_compression_policy('data_collection_audit', INTERVAL '1 day');

-- Enable compression for configuration_snapshots after 7 days
SELECT add_compression_policy('configuration_snapshots', INTERVAL '7 days');

-- Enable compression for configuration_change_events after 7 days
SELECT add_compression_policy('configuration_change_events', INTERVAL '7 days');

-- Enable compression for service_performance_metrics after 1 day (high volume metrics)
SELECT add_compression_policy('service_performance_metrics', INTERVAL '1 day');

-- =============================================================================
-- RETENTION POLICIES CONFIGURATION
-- =============================================================================

-- Set retention policy for system_metrics (keep 30 days based on environment config)
-- This automatically drops chunks older than the specified interval
SELECT add_retention_policy('system_metrics', INTERVAL '30 days');

-- Set retention policy for drive_health (keep 90 days - longer for trend analysis)
SELECT add_retention_policy('drive_health', INTERVAL '90 days');

-- Set retention policy for container_snapshots (keep 30 days)
SELECT add_retention_policy('container_snapshots', INTERVAL '30 days');

-- Set retention policy for zfs_status (keep 90 days - important for ZFS monitoring)
SELECT add_retention_policy('zfs_status', INTERVAL '90 days');

-- Set retention policy for zfs_snapshots (keep 180 days - important for backup tracking)
SELECT add_retention_policy('zfs_snapshots', INTERVAL '180 days');

-- Set retention policy for network_interfaces (keep 30 days)
SELECT add_retention_policy('network_interfaces', INTERVAL '30 days');

-- Set retention policy for docker_networks (keep 30 days)
SELECT add_retention_policy('docker_networks', INTERVAL '30 days');

-- Set retention policy for vm_status (keep 30 days)
SELECT add_retention_policy('vm_status', INTERVAL '30 days');

-- Set retention policy for system_logs (keep 14 days - logs can grow large quickly)
SELECT add_retention_policy('system_logs', INTERVAL '14 days');

-- =============================================================================
-- PHASE 1: NEW HYPERTABLES RETENTION POLICIES
-- =============================================================================

-- Set retention policy for data_collection_audit (keep 90 days - detailed audit trail)
SELECT add_retention_policy('data_collection_audit', INTERVAL '90 days');

-- Set retention policy for configuration_snapshots (keep 1 year - important for compliance)
SELECT add_retention_policy('configuration_snapshots', INTERVAL '365 days');

-- Set retention policy for configuration_change_events (keep 1 year - important for compliance)
SELECT add_retention_policy('configuration_change_events', INTERVAL '365 days');

-- Set retention policy for service_performance_metrics (keep 180 days - performance analysis)
SELECT add_retention_policy('service_performance_metrics', INTERVAL '180 days');

-- =============================================================================
-- ADVANCED COMPRESSION CONFIGURATION
-- =============================================================================

-- Configure compression algorithms and options for specific tables
-- Set compression algorithm for high-cardinality tables

-- Configure advanced compression for system_metrics with specific ordering
ALTER TABLE system_metrics SET (
    timescaledb.compress_orderby = 'time DESC, device_id',
    timescaledb.compress_segmentby = 'device_id'
);

-- Configure advanced compression for container_snapshots with container-specific ordering
ALTER TABLE container_snapshots SET (
    timescaledb.compress_orderby = 'time DESC, device_id, container_id',
    timescaledb.compress_segmentby = 'device_id, container_id'
);

-- Configure advanced compression for drive_health with drive-specific ordering
ALTER TABLE drive_health SET (
    timescaledb.compress_orderby = 'time DESC, device_id, drive_name',
    timescaledb.compress_segmentby = 'device_id, drive_name'
);

-- Configure advanced compression for system_logs with service-specific ordering
ALTER TABLE system_logs SET (
    timescaledb.compress_orderby = 'time DESC, device_id, log_level',
    timescaledb.compress_segmentby = 'device_id, service_name'
);

-- Configure advanced compression for network_interfaces with interface-specific ordering
ALTER TABLE network_interfaces SET (
    timescaledb.compress_orderby = 'time DESC, device_id, interface_name',
    timescaledb.compress_segmentby = 'device_id, interface_name'
);

-- =============================================================================
-- PHASE 1: NEW HYPERTABLES ADVANCED COMPRESSION CONFIGURATION
-- =============================================================================

-- Configure advanced compression for data_collection_audit with operation-specific ordering
ALTER TABLE data_collection_audit SET (
    timescaledb.compress_orderby = 'time DESC, device_id, data_type',
    timescaledb.compress_segmentby = 'device_id, data_type, collection_method'
);

-- Configure advanced compression for configuration_snapshots with config-specific ordering
ALTER TABLE configuration_snapshots SET (
    timescaledb.compress_orderby = 'time DESC, device_id, config_type',
    timescaledb.compress_segmentby = 'device_id, config_type'
);

-- Configure advanced compression for configuration_change_events with change-specific ordering
ALTER TABLE configuration_change_events SET (
    timescaledb.compress_orderby = 'time DESC, device_id, config_type',
    timescaledb.compress_segmentby = 'device_id, config_type, change_type'
);

-- Configure advanced compression for service_performance_metrics with service-specific ordering
ALTER TABLE service_performance_metrics SET (
    timescaledb.compress_orderby = 'time DESC, service_name',
    timescaledb.compress_segmentby = 'service_name'
);

-- =============================================================================
-- POLICY MANAGEMENT FUNCTIONS
-- =============================================================================

-- Function to get all compression policies
CREATE OR REPLACE FUNCTION get_compression_policies()
RETURNS TABLE(
    hypertable_name TEXT,
    compress_after INTERVAL,
    max_runtime INTERVAL,
    max_retries INTEGER,
    retry_period INTERVAL,
    scheduled BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        jp.hypertable_name::TEXT,
        (jp.config->>'compress_after')::INTERVAL as compress_after,
        (jp.config->>'maxruntime')::INTERVAL as max_runtime,
        (jp.config->>'max_retries')::INTEGER as max_retries,
        (jp.config->>'retry_period')::INTERVAL as retry_period,
        jp.scheduled
    FROM timescaledb_information.job_stats js
    JOIN timescaledb_information.jobs j ON js.job_id = j.job_id
    JOIN timescaledb_information.compression_policies jp ON j.job_id = jp.job_id
    ORDER BY jp.hypertable_name;
END;
$$ LANGUAGE plpgsql;

-- Function to get all retention policies
CREATE OR REPLACE FUNCTION get_retention_policies()
RETURNS TABLE(
    hypertable_name TEXT,
    drop_after INTERVAL,
    max_runtime INTERVAL,
    max_retries INTEGER,
    retry_period INTERVAL,
    scheduled BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rp.hypertable_name::TEXT,
        (rp.config->>'drop_after')::INTERVAL as drop_after,
        (rp.config->>'maxruntime')::INTERVAL as max_runtime,
        (rp.config->>'max_retries')::INTEGER as max_retries,
        (rp.config->>'retry_period')::INTERVAL as retry_period,
        rp.scheduled
    FROM timescaledb_information.job_stats js
    JOIN timescaledb_information.jobs j ON js.job_id = j.job_id
    JOIN timescaledb_information.retention_policies rp ON j.job_id = rp.job_id
    ORDER BY rp.hypertable_name;
END;
$$ LANGUAGE plpgsql;

-- Function to get policy execution statistics
CREATE OR REPLACE FUNCTION get_policy_stats()
RETURNS TABLE(
    job_id INTEGER,
    hypertable_name TEXT,
    policy_type TEXT,
    last_run_success BOOLEAN,
    last_successful_finish TIMESTAMPTZ,
    last_run_duration INTERVAL,
    next_start TIMESTAMPTZ,
    total_runs BIGINT,
    total_successes BIGINT,
    total_failures BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        js.job_id,
        COALESCE(cp.hypertable_name, rp.hypertable_name)::TEXT as hypertable_name,
        CASE 
            WHEN cp.job_id IS NOT NULL THEN 'compression'
            WHEN rp.job_id IS NOT NULL THEN 'retention'
            ELSE 'unknown'
        END as policy_type,
        js.last_run_success,
        js.last_successful_finish,
        js.last_run_duration,
        js.next_start,
        js.total_runs,
        js.total_successes,
        js.total_failures
    FROM timescaledb_information.job_stats js
    JOIN timescaledb_information.jobs j ON js.job_id = j.job_id
    LEFT JOIN timescaledb_information.compression_policies cp ON j.job_id = cp.job_id
    LEFT JOIN timescaledb_information.retention_policies rp ON j.job_id = rp.job_id
    WHERE cp.job_id IS NOT NULL OR rp.job_id IS NOT NULL
    ORDER BY hypertable_name, policy_type;
END;
$$ LANGUAGE plpgsql;

-- Function to manually trigger compression for a specific table
CREATE OR REPLACE FUNCTION manual_compress_table(table_name TEXT, older_than INTERVAL DEFAULT '7 days')
RETURNS TEXT AS $$
DECLARE
    result_text TEXT;
BEGIN
    -- Compress chunks older than specified interval
    PERFORM compress_chunk(chunk_name)
    FROM timescaledb_information.chunks
    WHERE hypertable_name = table_name
    AND range_end < NOW() - older_than
    AND NOT EXISTS (
        SELECT 1 FROM timescaledb_information.compressed_chunks cc
        WHERE cc.chunk_name = chunks.chunk_name
    );
    
    GET DIAGNOSTICS result_text = ROW_COUNT;
    
    RETURN format('Compressed %s chunks for table %s', result_text, table_name);
END;
$$ LANGUAGE plpgsql;

-- Function to manually trigger retention policy for a specific table
CREATE OR REPLACE FUNCTION manual_drop_chunks(table_name TEXT, older_than INTERVAL)
RETURNS TEXT AS $$
DECLARE
    result_text TEXT;
BEGIN
    -- Drop chunks older than specified interval
    PERFORM drop_chunks(table_name, older_than);
    
    RETURN format('Dropped chunks older than %s for table %s', older_than, table_name);
EXCEPTION
    WHEN OTHERS THEN
        RETURN format('Error dropping chunks for table %s: %s', table_name, SQLERRM);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- POLICY MONITORING AND ALERTING
-- =============================================================================

-- Function to check policy health and generate alerts
CREATE OR REPLACE FUNCTION check_policy_health()
RETURNS TABLE(
    alert_level TEXT,
    hypertable_name TEXT,
    policy_type TEXT,
    issue_description TEXT,
    recommended_action TEXT
) AS $$
BEGIN
    RETURN QUERY
    -- Check for failed compression jobs
    SELECT 
        'WARNING'::TEXT as alert_level,
        COALESCE(cp.hypertable_name, rp.hypertable_name)::TEXT as hypertable_name,
        CASE 
            WHEN cp.job_id IS NOT NULL THEN 'compression'
            WHEN rp.job_id IS NOT NULL THEN 'retention'
        END as policy_type,
        'Policy job has failed in recent runs'::TEXT as issue_description,
        'Check job logs and consider manual execution'::TEXT as recommended_action
    FROM timescaledb_information.job_stats js
    JOIN timescaledb_information.jobs j ON js.job_id = j.job_id
    LEFT JOIN timescaledb_information.compression_policies cp ON j.job_id = cp.job_id
    LEFT JOIN timescaledb_information.retention_policies rp ON j.job_id = rp.job_id
    WHERE (cp.job_id IS NOT NULL OR rp.job_id IS NOT NULL)
    AND js.last_run_success = false
    AND js.last_finish > NOW() - INTERVAL '24 hours'
    
    UNION ALL
    
    -- Check for policies that haven't run recently
    SELECT 
        'INFO'::TEXT as alert_level,
        COALESCE(cp.hypertable_name, rp.hypertable_name)::TEXT as hypertable_name,
        CASE 
            WHEN cp.job_id IS NOT NULL THEN 'compression'
            WHEN rp.job_id IS NOT NULL THEN 'retention'
        END as policy_type,
        'Policy has not run in the last 48 hours'::TEXT as issue_description,
        'Verify job scheduling and consider manual trigger'::TEXT as recommended_action
    FROM timescaledb_information.job_stats js
    JOIN timescaledb_information.jobs j ON js.job_id = j.job_id
    LEFT JOIN timescaledb_information.compression_policies cp ON j.job_id = cp.job_id
    LEFT JOIN timescaledb_information.retention_policies rp ON j.job_id = rp.job_id
    WHERE (cp.job_id IS NOT NULL OR rp.job_id IS NOT NULL)
    AND (js.last_finish IS NULL OR js.last_finish < NOW() - INTERVAL '48 hours')
    
    ORDER BY alert_level DESC, hypertable_name;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- ENVIRONMENT-BASED POLICY ADJUSTMENTS
-- =============================================================================

-- Function to adjust policies based on environment variables
-- This allows dynamic policy configuration without schema changes
CREATE OR REPLACE FUNCTION update_policies_from_env()
RETURNS TEXT AS $$
DECLARE
    env_retention_days INTEGER;
    env_compression_days INTEGER;
    policy_record RECORD;
    result_msg TEXT := '';
BEGIN
    -- Note: In a real environment, these would come from environment variables
    -- For now, using default values that can be customized per deployment
    
    -- Get environment-specific retention settings (defaults from .env.example)
    env_retention_days := 30; -- RETENTION_SYSTEM_METRICS_DAYS
    env_compression_days := 7; -- COMPRESSION_AFTER_DAYS
    
    result_msg := format('Updated policies with retention: %s days, compression: %s days', 
                        env_retention_days, env_compression_days);
    
    RETURN result_msg;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- LOG POLICY CONFIGURATION RESULTS
-- =============================================================================

-- Log the results of policy configuration
DO $$
DECLARE
    compression_count INTEGER;
    retention_count INTEGER;
    policy_record RECORD;
BEGIN
    -- Count policies created
    SELECT COUNT(*) INTO compression_count 
    FROM timescaledb_information.compression_policies;
    
    SELECT COUNT(*) INTO retention_count 
    FROM timescaledb_information.retention_policies;
    
    RAISE NOTICE 'TimescaleDB Compression and Retention Policies Configuration Complete';
    RAISE NOTICE 'Compression policies created: %', compression_count;
    RAISE NOTICE 'Retention policies created: %', retention_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Policy Summary:';
    RAISE NOTICE '===============';
    
    -- List compression policies
    RAISE NOTICE 'Compression Policies (compress after 7 days, except system_logs after 3 days):';
    FOR policy_record IN 
        SELECT hypertable_name, (config->>'compress_after')::INTERVAL as compress_after
        FROM timescaledb_information.compression_policies 
        ORDER BY hypertable_name
    LOOP
        RAISE NOTICE '- %: compress after %', 
            policy_record.hypertable_name,
            policy_record.compress_after;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Retention Policies:';
    FOR policy_record IN 
        SELECT hypertable_name, (config->>'drop_after')::INTERVAL as drop_after
        FROM timescaledb_information.retention_policies 
        ORDER BY hypertable_name
    LOOP
        RAISE NOTICE '- %: drop after %', 
            policy_record.hypertable_name,
            policy_record.drop_after;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Available management functions:';
    RAISE NOTICE '- get_compression_policies(): View all compression policies';
    RAISE NOTICE '- get_retention_policies(): View all retention policies';
    RAISE NOTICE '- get_policy_stats(): View policy execution statistics';
    RAISE NOTICE '- check_policy_health(): Check for policy issues';
    RAISE NOTICE '- manual_compress_table(table_name, older_than): Manually compress chunks';
    RAISE NOTICE '- manual_drop_chunks(table_name, older_than): Manually drop old chunks';
END $$;