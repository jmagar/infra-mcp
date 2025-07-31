-- Infrastructure Management MCP Server - Hypertables Configuration
-- This script converts standard tables to TimescaleDB hypertables for time-series data

-- =============================================================================
-- CONVERT TIME-SERIES TABLES TO HYPERTABLES
-- =============================================================================

-- Convert system_metrics to hypertable with 1-day time partitioning
SELECT create_hypertable(
    'system_metrics',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Convert drive_health to hypertable with 1-day time partitioning
SELECT create_hypertable(
    'drive_health',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Convert container_snapshots to hypertable with 1-day time partitioning
SELECT create_hypertable(
    'container_snapshots',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Convert zfs_status to hypertable with 1-day time partitioning
SELECT create_hypertable(
    'zfs_status',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Convert zfs_snapshots to hypertable with 1-day time partitioning
SELECT create_hypertable(
    'zfs_snapshots',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Convert network_interfaces to hypertable with 1-day time partitioning
SELECT create_hypertable(
    'network_interfaces',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Convert docker_networks to hypertable with 1-day time partitioning
SELECT create_hypertable(
    'docker_networks',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Convert vm_status to hypertable with 1-day time partitioning
SELECT create_hypertable(
    'vm_status',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Convert system_logs to hypertable with 6-hour time partitioning (higher frequency data)
SELECT create_hypertable(
    'system_logs',
    'time',
    chunk_time_interval => INTERVAL '6 hours',
    if_not_exists => TRUE
);

-- =============================================================================
-- OPTIMIZE HYPERTABLE CONFIGURATION
-- =============================================================================

-- Set adaptive chunking for better performance on varying data loads
-- This allows TimescaleDB to automatically adjust chunk sizes based on data patterns
SELECT set_adaptive_chunking('system_metrics', '50MB');
SELECT set_adaptive_chunking('drive_health', '25MB');
SELECT set_adaptive_chunking('container_snapshots', '100MB');
SELECT set_adaptive_chunking('zfs_status', '10MB');
SELECT set_adaptive_chunking('zfs_snapshots', '25MB');
SELECT set_adaptive_chunking('network_interfaces', '50MB');
SELECT set_adaptive_chunking('docker_networks', '10MB');
SELECT set_adaptive_chunking('vm_status', '25MB');
SELECT set_adaptive_chunking('system_logs', '200MB');

-- =============================================================================
-- ADD SPACE PARTITIONING FOR HIGH-CARDINALITY DATA
-- =============================================================================

-- For system_metrics, add space partitioning by device_id to distribute data
-- across multiple nodes in a distributed setup (useful for scaling)
-- Note: This is optional and mainly beneficial in multi-node TimescaleDB setups
-- SELECT add_dimension('system_metrics', 'device_id', number_partitions => 4);

-- For container_snapshots, we could partition by device_id as well
-- SELECT add_dimension('container_snapshots', 'device_id', number_partitions => 4);

-- =============================================================================
-- VERIFY HYPERTABLE CREATION
-- =============================================================================

-- Create a verification function to check hypertable status
CREATE OR REPLACE FUNCTION verify_hypertables()
RETURNS TABLE(
    hypertable_name TEXT,
    time_column TEXT,
    chunk_time_interval INTERVAL,
    number_chunks BIGINT,
    compression_enabled BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ht.hypertable_name::TEXT,
        ht.time_column_name::TEXT,
        ht.chunk_time_interval,
        (SELECT COUNT(*) FROM timescaledb_information.chunks WHERE hypertable_name = ht.hypertable_name) as number_chunks,
        COALESCE(cs.compression_enabled, false) as compression_enabled
    FROM timescaledb_information.hypertables ht
    LEFT JOIN timescaledb_information.compression_settings cs 
        ON ht.hypertable_name = cs.hypertable_name
    WHERE ht.hypertable_schema = 'public'
    ORDER BY ht.hypertable_name;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- CREATE CHUNK MANAGEMENT FUNCTIONS
-- =============================================================================

-- Function to get chunk information for a specific hypertable
CREATE OR REPLACE FUNCTION get_chunk_info(table_name TEXT)
RETURNS TABLE(
    chunk_name TEXT,
    range_start TIMESTAMPTZ,
    range_end TIMESTAMPTZ,
    chunk_size TEXT,
    compression_status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.chunk_name::TEXT,
        c.range_start,
        c.range_end,
        pg_size_pretty(pg_total_relation_size(format('%I.%I', c.chunk_schema, c.chunk_name))) as chunk_size,
        CASE 
            WHEN cc.chunk_name IS NOT NULL THEN 'compressed'
            ELSE 'uncompressed'
        END as compression_status
    FROM timescaledb_information.chunks c
    LEFT JOIN timescaledb_information.compressed_chunks cc 
        ON c.chunk_name = cc.chunk_name
    WHERE c.hypertable_name = table_name
    ORDER BY c.range_start DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get hypertable statistics
CREATE OR REPLACE FUNCTION get_hypertable_stats()
RETURNS TABLE(
    hypertable_name TEXT,
    total_size TEXT,
    table_size TEXT,
    index_size TEXT,
    total_chunks BIGINT,
    compressed_chunks BIGINT,
    compression_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.table_name::TEXT as hypertable_name,
        pg_size_pretty(h.total_bytes) as total_size,
        pg_size_pretty(h.table_bytes) as table_size,
        pg_size_pretty(h.index_bytes) as index_size,
        h.num_chunks as total_chunks,
        COALESCE(comp.compressed_chunks, 0) as compressed_chunks,
        CASE 
            WHEN h.total_bytes > 0 THEN 
                ROUND((h.total_bytes::NUMERIC - COALESCE(comp.compressed_bytes, h.total_bytes)) / h.total_bytes::NUMERIC * 100, 2)
            ELSE 0
        END as compression_ratio
    FROM hypertable_detailed_size h
    LEFT JOIN (
        SELECT 
            cc.hypertable_name,
            COUNT(*) as compressed_chunks,
            SUM(cc.compressed_total_bytes) as compressed_bytes
        FROM timescaledb_information.compressed_chunks cc 
        GROUP BY cc.hypertable_name
    ) comp ON h.table_name = comp.hypertable_name
    WHERE h.table_schema = 'public'
    ORDER BY h.total_bytes DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- LOG HYPERTABLE CREATION RESULTS
-- =============================================================================

-- Log the results of hypertable creation
DO $$
DECLARE
    hypertable_record RECORD;
    total_hypertables INTEGER;
BEGIN
    -- Count total hypertables created
    SELECT COUNT(*) INTO total_hypertables 
    FROM timescaledb_information.hypertables 
    WHERE hypertable_schema = 'public';
    
    RAISE NOTICE 'TimescaleDB Hypertables Configuration Complete';
    RAISE NOTICE 'Total hypertables created: %', total_hypertables;
    RAISE NOTICE '';
    RAISE NOTICE 'Hypertable Summary:';
    RAISE NOTICE '==================';
    
    -- List all created hypertables
    FOR hypertable_record IN 
        SELECT hypertable_name, time_column_name, chunk_time_interval
        FROM timescaledb_information.hypertables 
        WHERE hypertable_schema = 'public'
        ORDER BY hypertable_name
    LOOP
        RAISE NOTICE '- %: time_column=%, chunk_interval=%', 
            hypertable_record.hypertable_name,
            hypertable_record.time_column_name,
            hypertable_record.chunk_time_interval;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Available utility functions:';
    RAISE NOTICE '- verify_hypertables(): Check hypertable status';
    RAISE NOTICE '- get_chunk_info(table_name): Get chunk details for a table';
    RAISE NOTICE '- get_hypertable_stats(): Get size and compression statistics';
END $$;