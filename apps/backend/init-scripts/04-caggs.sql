-- Infrastructure Management MCP Server - Continuous Aggregates Configuration
-- This script creates continuous aggregates for pre-calculated hourly and daily summaries

-- =============================================================================
-- SYSTEM METRICS CONTINUOUS AGGREGATES
-- =============================================================================

-- Hourly system metrics aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS system_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS time_bucket,
    device_id,
    -- CPU metrics
    avg(cpu_usage_percent) as avg_cpu_usage,
    max(cpu_usage_percent) as max_cpu_usage,
    min(cpu_usage_percent) as min_cpu_usage,
    -- Memory metrics
    avg(memory_usage_percent) as avg_memory_usage,
    max(memory_usage_percent) as max_memory_usage,
    min(memory_usage_percent) as min_memory_usage,
    avg(memory_total_bytes) as avg_memory_total,
    avg(memory_available_bytes) as avg_memory_available,
    -- Load average metrics
    avg(load_average_1m) as avg_load_1m,
    max(load_average_1m) as max_load_1m,
    avg(load_average_5m) as avg_load_5m,
    avg(load_average_15m) as avg_load_15m,
    -- Disk metrics
    avg(disk_usage_percent) as avg_disk_usage,
    max(disk_usage_percent) as max_disk_usage,
    avg(disk_total_bytes) as avg_disk_total,
    avg(disk_available_bytes) as avg_disk_available,
    -- Network metrics
    sum(network_bytes_sent) as total_network_sent,
    sum(network_bytes_recv) as total_network_recv,
    avg(network_bytes_sent) as avg_network_sent,
    avg(network_bytes_recv) as avg_network_recv,
    -- Process and uptime metrics
    avg(process_count) as avg_process_count,
    max(process_count) as max_process_count,
    avg(uptime_seconds) as avg_uptime,
    -- Aggregation metadata
    count(*) as sample_count,
    min(time) as period_start,
    max(time) as period_end
FROM system_metrics
GROUP BY time_bucket, device_id;

-- Daily system metrics aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS system_metrics_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS time_bucket,
    device_id,
    -- CPU metrics
    avg(cpu_usage_percent) as avg_cpu_usage,
    max(cpu_usage_percent) as max_cpu_usage,
    min(cpu_usage_percent) as min_cpu_usage,
    percentile_agg(cpu_usage_percent) as cpu_usage_percentiles,
    -- Memory metrics
    avg(memory_usage_percent) as avg_memory_usage,
    max(memory_usage_percent) as max_memory_usage,
    min(memory_usage_percent) as min_memory_usage,
    percentile_agg(memory_usage_percent) as memory_usage_percentiles,
    avg(memory_total_bytes) as avg_memory_total,
    avg(memory_available_bytes) as avg_memory_available,
    -- Load average metrics
    avg(load_average_1m) as avg_load_1m,
    max(load_average_1m) as max_load_1m,
    min(load_average_1m) as min_load_1m,
    avg(load_average_5m) as avg_load_5m,
    avg(load_average_15m) as avg_load_15m,
    -- Disk metrics
    avg(disk_usage_percent) as avg_disk_usage,
    max(disk_usage_percent) as max_disk_usage,
    min(disk_usage_percent) as min_disk_usage,
    avg(disk_total_bytes) as avg_disk_total,
    avg(disk_available_bytes) as avg_disk_available,
    -- Network metrics (daily totals and averages)
    sum(network_bytes_sent) as total_network_sent,
    sum(network_bytes_recv) as total_network_recv,
    avg(network_bytes_sent) as avg_network_sent,
    avg(network_bytes_recv) as avg_network_recv,
    -- Process metrics
    avg(process_count) as avg_process_count,
    max(process_count) as max_process_count,
    min(process_count) as min_process_count,
    -- Uptime metrics
    avg(uptime_seconds) as avg_uptime,
    max(uptime_seconds) as max_uptime,
    -- Aggregation metadata
    count(*) as sample_count,
    min(time) as period_start,
    max(time) as period_end
FROM system_metrics
GROUP BY time_bucket, device_id;

-- =============================================================================
-- DRIVE HEALTH CONTINUOUS AGGREGATES
-- =============================================================================

-- Daily drive health aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS drive_health_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS time_bucket,
    device_id,
    drive_name,
    drive_type,
    model,
    -- Temperature metrics
    avg(temperature_celsius) as avg_temperature,
    max(temperature_celsius) as max_temperature,
    min(temperature_celsius) as min_temperature,
    -- Usage metrics
    max(power_on_hours) as latest_power_on_hours,
    max(total_lbas_written) as latest_lbas_written,
    max(total_lbas_read) as latest_lbas_read,
    -- Health indicators
    max(reallocated_sectors) as latest_reallocated_sectors,
    max(pending_sectors) as latest_pending_sectors,
    max(uncorrectable_errors) as latest_uncorrectable_errors,
    -- Status aggregation
    mode() WITHIN GROUP (ORDER BY smart_status) as most_common_smart_status,
    mode() WITHIN GROUP (ORDER BY health_status) as most_common_health_status,
    -- Capacity tracking
    avg(capacity_bytes) as avg_capacity,
    -- Sample metadata
    count(*) as sample_count,
    min(time) as period_start,
    max(time) as period_end
FROM drive_health
GROUP BY time_bucket, device_id, drive_name, drive_type, model;

-- Weekly drive health trends
CREATE MATERIALIZED VIEW IF NOT EXISTS drive_health_weekly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 week', time) AS time_bucket,
    device_id,
    drive_name,
    -- Temperature trends
    avg(temperature_celsius) as avg_temperature,
    max(temperature_celsius) as max_temperature,
    min(temperature_celsius) as min_temperature,
    stddev(temperature_celsius) as temperature_stddev,
    -- Power-on hours progression
    first(power_on_hours, time) as start_power_on_hours,
    last(power_on_hours, time) as end_power_on_hours,
    last(power_on_hours, time) - first(power_on_hours, time) as power_on_hours_delta,
    -- LBA progression (wear indicators)
    first(total_lbas_written, time) as start_lbas_written,
    last(total_lbas_written, time) as end_lbas_written,
    last(total_lbas_written, time) - first(total_lbas_written, time) as lbas_written_delta,
    first(total_lbas_read, time) as start_lbas_read,
    last(total_lbas_read, time) as end_lbas_read,
    last(total_lbas_read, time) - first(total_lbas_read, time) as lbas_read_delta,
    -- Error progression
    first(reallocated_sectors, time) as start_reallocated_sectors,
    last(reallocated_sectors, time) as end_reallocated_sectors,
    last(reallocated_sectors, time) - first(reallocated_sectors, time) as reallocated_sectors_delta,
    -- Health status consistency
    mode() WITHIN GROUP (ORDER BY smart_status) as dominant_smart_status,
    mode() WITHIN GROUP (ORDER BY health_status) as dominant_health_status,
    count(DISTINCT smart_status) as smart_status_changes,
    count(DISTINCT health_status) as health_status_changes,
    -- Sample metadata
    count(*) as sample_count,
    min(time) as period_start,
    max(time) as period_end
FROM drive_health
GROUP BY time_bucket, device_id, drive_name;

-- =============================================================================
-- CONTAINER METRICS CONTINUOUS AGGREGATES
-- =============================================================================

-- Hourly container metrics aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS container_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS time_bucket,
    device_id,
    container_name,
    image,
    -- Resource usage metrics
    avg(cpu_usage_percent) as avg_cpu_usage,
    max(cpu_usage_percent) as max_cpu_usage,
    min(cpu_usage_percent) as min_cpu_usage,
    avg(memory_usage_bytes) as avg_memory_usage,
    max(memory_usage_bytes) as max_memory_usage,
    avg(memory_limit_bytes) as avg_memory_limit,
    -- Network metrics
    sum(network_bytes_sent) as total_network_sent,
    sum(network_bytes_recv) as total_network_recv,
    avg(network_bytes_sent) as avg_network_sent,
    avg(network_bytes_recv) as avg_network_recv,
    -- Block I/O metrics
    sum(block_read_bytes) as total_block_read,
    sum(block_write_bytes) as total_block_write,
    avg(block_read_bytes) as avg_block_read,
    avg(block_write_bytes) as avg_block_write,
    -- Status tracking
    mode() WITHIN GROUP (ORDER BY status) as most_common_status,
    mode() WITHIN GROUP (ORDER BY state) as most_common_state,
    count(DISTINCT status) as status_changes,
    count(DISTINCT state) as state_changes,
    -- Sample metadata
    count(*) as sample_count,
    min(time) as period_start,
    max(time) as period_end
FROM container_snapshots
GROUP BY time_bucket, device_id, container_name, image;

-- Daily container summary
CREATE MATERIALIZED VIEW IF NOT EXISTS container_summary_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS time_bucket,
    device_id,
    -- Container count metrics
    count(DISTINCT container_name) as unique_containers,
    count(DISTINCT image) as unique_images,
    -- Status distribution
    count(*) FILTER (WHERE status = 'running') as running_containers,
    count(*) FILTER (WHERE status = 'exited') as exited_containers,
    count(*) FILTER (WHERE status = 'paused') as paused_containers,
    count(*) FILTER (WHERE status NOT IN ('running', 'exited', 'paused')) as other_status_containers,
    -- Resource usage aggregations
    avg(cpu_usage_percent) as avg_cpu_usage_all,
    max(cpu_usage_percent) as max_cpu_usage_all,
    sum(memory_usage_bytes) as total_memory_usage,
    avg(memory_usage_bytes) as avg_memory_usage,
    sum(memory_limit_bytes) as total_memory_limit,
    -- Network aggregations
    sum(network_bytes_sent) as total_network_sent_all,
    sum(network_bytes_recv) as total_network_recv_all,
    -- Block I/O aggregations
    sum(block_read_bytes) as total_block_read_all,
    sum(block_write_bytes) as total_block_write_all,
    -- Sample metadata
    count(*) as total_samples,
    min(time) as period_start,
    max(time) as period_end
FROM container_snapshots
GROUP BY time_bucket, device_id;

-- =============================================================================
-- NETWORK INTERFACE CONTINUOUS AGGREGATES
-- =============================================================================

-- Daily network interface metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS network_interfaces_daily
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS time_bucket,
    device_id,
    interface_name,
    interface_type,
    -- Bandwidth utilization
    avg(rx_bytes) as avg_rx_bytes,
    max(rx_bytes) as max_rx_bytes,
    avg(tx_bytes) as avg_tx_bytes,
    max(tx_bytes) as max_tx_bytes,
    -- Packet statistics
    avg(rx_packets) as avg_rx_packets,
    max(rx_packets) as max_rx_packets,
    avg(tx_packets) as avg_tx_packets,
    max(tx_packets) as max_tx_packets,
    -- Error rates
    avg(rx_errors) as avg_rx_errors,
    sum(rx_errors) as total_rx_errors,
    avg(tx_errors) as avg_tx_errors,
    sum(tx_errors) as total_tx_errors,
    avg(rx_dropped) as avg_rx_dropped,
    sum(rx_dropped) as total_rx_dropped,
    avg(tx_dropped) as avg_tx_dropped,
    sum(tx_dropped) as total_tx_dropped,
    -- Interface state consistency
    mode() WITHIN GROUP (ORDER BY state) as most_common_state,
    count(DISTINCT state) as state_changes,
    -- Configuration tracking
    mode() WITHIN GROUP (ORDER BY mtu) as most_common_mtu,
    mode() WITHIN GROUP (ORDER BY speed_mbps) as most_common_speed,
    mode() WITHIN GROUP (ORDER BY duplex) as most_common_duplex,
    -- Sample metadata
    count(*) as sample_count,
    min(time) as period_start,
    max(time) as period_end
FROM network_interfaces
GROUP BY time_bucket, device_id, interface_name, interface_type;

-- =============================================================================
-- SYSTEM LOGS CONTINUOUS AGGREGATES
-- =============================================================================

-- Hourly log summary by service and level
CREATE MATERIALIZED VIEW IF NOT EXISTS system_logs_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS time_bucket,
    device_id,
    service_name,
    log_level,
    source,
    facility,
    -- Log count metrics
    count(*) as log_count,
    count(DISTINCT process_id) as unique_processes,
    count(DISTINCT user_name) as unique_users,
    -- Sample metadata
    min(time) as period_start,
    max(time) as period_end
FROM system_logs
GROUP BY time_bucket, device_id, service_name, log_level, source, facility;

-- Daily log summary with error focus
CREATE MATERIALIZED VIEW IF NOT EXISTS system_logs_daily_errors
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS time_bucket,
    device_id,
    service_name,
    -- Error level breakdown
    count(*) FILTER (WHERE log_level = 'emergency') as emergency_count,
    count(*) FILTER (WHERE log_level = 'alert') as alert_count,
    count(*) FILTER (WHERE log_level = 'critical') as critical_count,
    count(*) FILTER (WHERE log_level = 'error') as error_count,
    count(*) FILTER (WHERE log_level = 'warning') as warning_count,
    count(*) FILTER (WHERE log_level = 'notice') as notice_count,
    count(*) FILTER (WHERE log_level = 'info') as info_count,
    count(*) FILTER (WHERE log_level = 'debug') as debug_count,
    -- Total counts
    count(*) as total_logs,
    count(*) FILTER (WHERE log_level IN ('emergency', 'alert', 'critical', 'error')) as total_errors,
    count(*) FILTER (WHERE log_level = 'warning') as total_warnings,
    -- Service activity
    count(DISTINCT source) as unique_sources,
    count(DISTINCT facility) as unique_facilities,
    -- Sample metadata
    min(time) as period_start,
    max(time) as period_end
FROM system_logs
GROUP BY time_bucket, device_id, service_name;

-- =============================================================================
-- CONTINUOUS AGGREGATE REFRESH POLICIES
-- =============================================================================

-- Add refresh policies for all continuous aggregates
-- These policies automatically refresh the materialized views with new data

-- System metrics refresh policies
SELECT add_continuous_aggregate_policy('system_metrics_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('system_metrics_daily',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- Drive health refresh policies
SELECT add_continuous_aggregate_policy('drive_health_daily',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

SELECT add_continuous_aggregate_policy('drive_health_weekly',
    start_offset => INTERVAL '2 weeks',
    end_offset => INTERVAL '1 week',
    schedule_interval => INTERVAL '1 day');

-- Container metrics refresh policies
SELECT add_continuous_aggregate_policy('container_metrics_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('container_summary_daily',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- Network interface refresh policies
SELECT add_continuous_aggregate_policy('network_interfaces_daily',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- System logs refresh policies
SELECT add_continuous_aggregate_policy('system_logs_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('system_logs_daily_errors',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- =============================================================================
-- CONTINUOUS AGGREGATE MANAGEMENT FUNCTIONS
-- =============================================================================

-- Function to get all continuous aggregates
CREATE OR REPLACE FUNCTION get_continuous_aggregates()
RETURNS TABLE(
    view_name TEXT,
    view_definition TEXT,
    materialized BOOLEAN,
    compression_enabled BOOLEAN,
    refresh_lag INTERVAL,
    refresh_interval INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ca.view_name::TEXT,
        ca.view_definition::TEXT,
        ca.materialized,
        COALESCE(cs.compression_enabled, false) as compression_enabled,
        cap.refresh_lag,
        cap.refresh_interval
    FROM timescaledb_information.continuous_aggregates ca
    LEFT JOIN timescaledb_information.compression_settings cs 
        ON ca.view_name = cs.hypertable_name
    LEFT JOIN timescaledb_information.continuous_aggregate_policies cap 
        ON ca.view_name = cap.hypertable_name
    WHERE ca.view_schema = 'public'
    ORDER BY ca.view_name;
END;
$$ LANGUAGE plpgsql;

-- Function to manually refresh continuous aggregates
CREATE OR REPLACE FUNCTION refresh_continuous_aggregate(view_name TEXT, start_time TIMESTAMPTZ DEFAULT NULL, end_time TIMESTAMPTZ DEFAULT NULL)
RETURNS TEXT AS $$
BEGIN
    IF start_time IS NULL THEN
        start_time := NOW() - INTERVAL '7 days';
    END IF;
    
    IF end_time IS NULL THEN
        end_time := NOW();
    END IF;
    
    EXECUTE format('CALL refresh_continuous_aggregate(%L, %L, %L)', view_name, start_time, end_time);
    
    RETURN format('Refreshed continuous aggregate %s from %s to %s', view_name, start_time, end_time);
EXCEPTION
    WHEN OTHERS THEN
        RETURN format('Error refreshing continuous aggregate %s: %s', view_name, SQLERRM);
END;
$$ LANGUAGE plpgsql;

-- Function to get continuous aggregate statistics
CREATE OR REPLACE FUNCTION get_cagg_stats()
RETURNS TABLE(
    view_name TEXT,
    total_size TEXT,
    row_count BIGINT,
    oldest_data TIMESTAMPTZ,
    newest_data TIMESTAMPTZ,
    last_refresh TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ca.view_name::TEXT,
        pg_size_pretty(pg_total_relation_size(ca.view_name::regclass)) as total_size,
        (SELECT COUNT(*) FROM (SELECT 1 FROM (SELECT * FROM (VALUES ('dummy')) AS t LIMIT 0) AS sub) AS count_query),
        NULL::TIMESTAMPTZ as oldest_data, -- Would need specific query per view
        NULL::TIMESTAMPTZ as newest_data, -- Would need specific query per view
        js.last_successful_finish as last_refresh
    FROM timescaledb_information.continuous_aggregates ca
    LEFT JOIN timescaledb_information.continuous_aggregate_policies cap 
        ON ca.view_name = cap.hypertable_name
    LEFT JOIN timescaledb_information.job_stats js 
        ON cap.job_id = js.job_id
    WHERE ca.view_schema = 'public'
    ORDER BY ca.view_name;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- LOG CONTINUOUS AGGREGATE CONFIGURATION RESULTS
-- =============================================================================

-- Log the results of continuous aggregate configuration
DO $$
DECLARE
    cagg_count INTEGER;
    policy_count INTEGER;
    cagg_record RECORD;
BEGIN
    -- Count continuous aggregates created
    SELECT COUNT(*) INTO cagg_count 
    FROM timescaledb_information.continuous_aggregates 
    WHERE view_schema = 'public';
    
    SELECT COUNT(*) INTO policy_count 
    FROM timescaledb_information.continuous_aggregate_policies;
    
    RAISE NOTICE 'TimescaleDB Continuous Aggregates Configuration Complete';
    RAISE NOTICE 'Continuous aggregates created: %', cagg_count;
    RAISE NOTICE 'Refresh policies created: %', policy_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Continuous Aggregates Summary:';
    RAISE NOTICE '==============================';
    
    -- List all continuous aggregates
    FOR cagg_record IN 
        SELECT view_name, materialized
        FROM timescaledb_information.continuous_aggregates 
        WHERE view_schema = 'public'
        ORDER BY view_name
    LOOP
        RAISE NOTICE '- %: materialized=%', 
            cagg_record.view_name,
            cagg_record.materialized;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Available management functions:';
    RAISE NOTICE '- get_continuous_aggregates(): View all continuous aggregates';
    RAISE NOTICE '- refresh_continuous_aggregate(view_name, start_time, end_time): Manually refresh';
    RAISE NOTICE '- get_cagg_stats(): View continuous aggregate statistics';
    RAISE NOTICE '';
    RAISE NOTICE 'Query examples:';
    RAISE NOTICE '- SELECT * FROM system_metrics_hourly WHERE time_bucket >= NOW() - INTERVAL ''1 day'';';
    RAISE NOTICE '- SELECT * FROM drive_health_daily WHERE device_id = (SELECT id FROM devices WHERE hostname = ''localhost'');';
    RAISE NOTICE '- SELECT * FROM container_summary_daily ORDER BY time_bucket DESC LIMIT 7;';
END $$;