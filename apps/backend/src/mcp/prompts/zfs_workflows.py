"""
ZFS management workflow prompts for infrastructure operations.

These prompts create comprehensive workflows for managing ZFS filesystems,
including pool management, snapshot strategies, and data protection.
"""


def zfs_health_assessment(hostname: str, pool_name: str | None = None) -> str:
    """
    Comprehensive ZFS health assessment and optimization recommendations.
    
    Args:
        hostname: Device hostname with ZFS pools
        pool_name: Specific pool to assess (optional, defaults to all pools)
    """
    pool_context = f"pool '{pool_name}'" if pool_name else "all ZFS pools"
    
    return f"""You are a ZFS storage specialist conducting a comprehensive health assessment of {pool_context} on device: {hostname}

**Target Device**: {hostname}
{'**Specific Pool**: ' + pool_name if pool_name else '**Scope**: All ZFS pools'}

Please execute thorough ZFS health assessment workflow:

## Phase 1: Pool Status and Health
1. **Pool Inventory and Status**:
   - Use list_zfs_pools to get overview of all pools and their basic status
   - Use get_zfs_pool_status for detailed status of each pool
   - Use check_zfs_health for comprehensive health analysis across all pools

2. **Performance Metrics**:
   - Use get_zfs_arc_stats to analyze ARC cache performance and hit ratios
   - Evaluate read/write performance and IOPS capabilities
   - Assess compression ratios and deduplication effectiveness

## Phase 2: Storage Analysis
3. **Capacity and Usage Analysis**:
   - Use list_zfs_datasets to analyze dataset structure and usage patterns
   - Identify datasets with high growth rates or unusual usage patterns
   - Evaluate free space and capacity planning requirements

4. **Snapshot Analysis**:
   - Use list_zfs_snapshots to inventory all snapshots and their retention
   - Use analyze_snapshot_usage to identify cleanup opportunities
   - Assess snapshot space usage and impact on pool capacity

## Phase 3: Configuration Optimization
5. **Pool Configuration Review**:
   - Analyze VDEV layout and redundancy levels
   - Review pool properties and optimization settings
   - Assess record size, compression, and deduplication settings

6. **Performance Tuning Recommendations**:
   - Use optimize_zfs_settings to get specific optimization recommendations
   - Analyze workload patterns and suggest tuning parameters
   - Review ARC sizing and memory allocation

## Phase 4: Data Protection Assessment
7. **Backup and Replication Status**:
   - Review snapshot retention policies and backup strategies
   - Assess replication configurations and schedules
   - Verify disaster recovery capabilities and procedures

8. **Resilience and Redundancy**:
   - Evaluate RAID-Z configuration and hot spare availability
   - Assess device failure scenarios and recovery procedures
   - Review scrub schedules and historical results

## Phase 5: Maintenance and Monitoring
9. **Preventive Maintenance**:
   - Check scrub schedules and last execution dates
   - Review pool events and error history using monitor_zfs_events
   - Assess need for hardware maintenance or upgrades

10. **Monitoring and Alerting**:
    - Configure monitoring for pool health and performance metrics
    - Set up alerts for capacity thresholds and error conditions
    - Document baseline performance metrics for trend analysis

Provide specific recommendations for optimization, capacity planning, and maintenance scheduling based on current pool status and usage patterns."""


def zfs_snapshot_strategy(
    hostname: str,
    dataset_pattern: str = "*",
    retention_policy: str = "7d-4w-12m"
) -> str:
    """
    Implement comprehensive ZFS snapshot management strategy.
    
    Args:
        hostname: Device hostname with ZFS datasets
        dataset_pattern: Pattern for datasets to include (default: all)
        retention_policy: Retention policy format (daily-weekly-monthly)
    """
    return f"""You are a ZFS data protection specialist implementing snapshot management strategy for device: {hostname}

**Target Device**: {hostname}
**Dataset Pattern**: {dataset_pattern}
**Retention Policy**: {retention_policy}

Please execute comprehensive snapshot management workflow:

## Phase 1: Current State Assessment
1. **Snapshot Inventory**:
   - Use list_zfs_snapshots to catalog all existing snapshots
   - Use analyze_snapshot_usage to assess current space usage and patterns
   - Identify orphaned or excessive snapshots consuming space

2. **Dataset Analysis**:
   - Use list_zfs_datasets to identify datasets requiring snapshot protection
   - Analyze dataset change rates and backup requirements
   - Evaluate business criticality and recovery time objectives

## Phase 2: Strategy Design
3. **Retention Policy Implementation**:
   - Design snapshot naming convention with timestamps
   - Implement {retention_policy} retention schedule (daily-weekly-monthly)
   - Calculate storage impact and capacity requirements

4. **Automation Framework**:
   - Plan automated snapshot creation using create_zfs_snapshot
   - Design cleanup automation for expired snapshots
   - Implement verification and monitoring procedures

## Phase 3: Snapshot Creation and Management
5. **Strategic Snapshot Creation**:
   - Create initial baseline snapshots for all critical datasets
   - Implement recursive snapshots for dataset hierarchies
   - Coordinate snapshots with application quiescing if needed

6. **Space Management**:
   - Monitor snapshot space consumption impact
   - Implement cleanup procedures for retention policy compliance
   - Optimize snapshot scheduling to minimize storage overhead

## Phase 4: Replication and Backup
7. **Replication Setup**:
   - Use send_zfs_snapshot for off-site replication
   - Configure incremental replication for efficiency
   - Verify replication integrity and recovery procedures

8. **Backup Integration**:
   - Coordinate snapshots with backup systems
   - Implement point-in-time recovery capabilities
   - Test backup and restore procedures regularly

## Phase 5: Monitoring and Maintenance
9. **Snapshot Monitoring**:
   - Implement monitoring for snapshot creation success/failure
   - Track snapshot space usage and growth trends
   - Alert on retention policy violations or excessive usage

10. **Operational Procedures**:
    - Document snapshot recovery procedures
    - Create operational runbooks for snapshot management
    - Train staff on snapshot restoration and cloning procedures

## Phase 6: Testing and Validation
11. **Recovery Testing**:
    - Test snapshot rollback procedures using clone_zfs_snapshot
    - Validate point-in-time recovery capabilities
    - Perform regular disaster recovery drills

12. **Performance Impact Assessment**:
    - Monitor impact of snapshot operations on system performance
    - Optimize snapshot scheduling for minimal business impact
    - Tune snapshot creation parameters for efficiency

Provide specific commands, schedules, and monitoring configurations for implementing the {retention_policy} retention strategy across {dataset_pattern} datasets."""


def zfs_disaster_recovery(
    hostname: str,
    recovery_scenario: str = "pool_failure",
    rto_target: str = "4 hours"
) -> str:
    """
    Implement comprehensive ZFS disaster recovery procedures.
    
    Args:
        hostname: Device hostname for disaster recovery planning
        recovery_scenario: Type of disaster (pool_failure, device_failure, data_corruption)
        rto_target: Recovery Time Objective target
    """
    return f"""You are a disaster recovery specialist implementing ZFS recovery procedures for {recovery_scenario} scenario on device: {hostname}

**Target Device**: {hostname}
**Recovery Scenario**: {recovery_scenario}
**RTO Target**: {rto_target}

Please execute comprehensive disaster recovery workflow:

## Phase 1: Disaster Assessment and Triage
1. **Damage Assessment**:
   - Use check_zfs_health to assess current pool and dataset status
   - Use monitor_zfs_events to analyze error history and failure patterns
   - Determine scope of data loss and system availability impact

2. **Recovery Strategy Selection**:
   - Evaluate available recovery options (repair, restore, rebuild)
   - Assess data age and acceptable recovery point objectives
   - Calculate estimated recovery time for each option

## Phase 2: Immediate Stabilization
3. **System Stabilization**:
   - Prevent further data loss or corruption
   - Use get_zfs_pool_status to determine if pools can be safely imported
   - Isolate affected storage components if hardware failure detected

4. **Critical Data Identification**:
   - Identify most critical datasets requiring immediate recovery
   - Prioritize recovery operations based on business impact
   - Establish communication with stakeholders about recovery timeline

## Phase 3: Recovery Execution
5. **Pool Recovery Operations**:
   - Attempt pool import with various recovery options
   - Use available snapshots for point-in-time recovery
   - Implement incremental recovery strategies to minimize downtime

6. **Data Restoration**:
   - Use receive_zfs_snapshot to restore from replication targets
   - Use clone_zfs_snapshot to create working copies from snapshots
   - Verify data integrity after restoration operations

## Phase 4: System Reconstruction
7. **Pool Reconstruction** (if needed):
   - Design new pool layout with improved resilience
   - Use create_zfs_snapshot for baseline protection before migration
   - Migrate data from recovery sources to new pool structure

8. **Configuration Restoration**:
   - Restore ZFS properties and mount points
   - Reconfigure dataset permissions and sharing settings
   - Restore snapshot schedules and replication configurations

## Phase 5: Validation and Testing
9. **Data Integrity Verification**:
   - Perform comprehensive data validation and integrity checks
   - Compare restored data with known good checksums if available
   - Verify application functionality and data accessibility

10. **Performance Validation**:
    - Use get_zfs_arc_stats to ensure cache performance is optimal
    - Verify read/write performance meets baseline requirements
    - Test backup and replication functionality

## Phase 6: Recovery Completion
11. **Production Readiness**:
    - Restore monitoring and alerting systems
    - Update documentation with lessons learned
    - Implement additional resilience measures identified during recovery

12. **Post-Recovery Analysis**:
    - Document root cause analysis and recovery procedures used
    - Update disaster recovery plans based on experience
    - Schedule testing of improved procedures

## Recovery Time Checkpoints:
- **0-1 hours**: Assessment and triage completion
- **1-2 hours**: Stabilization and recovery strategy finalization  
- **2-{rto_target}**: Active recovery operations and validation
- **Post-{rto_target}**: Optimization and documentation

Provide specific recovery procedures, commands, and validation steps optimized for {recovery_scenario} with detailed rollback options if recovery attempts fail."""


def zfs_pool_optimization(
    hostname: str,
    performance_goal: str = "balanced",
    workload_type: str = "mixed"
) -> str:
    """
    Optimize ZFS pool configuration for specific workloads and performance goals.
    
    Args:
        hostname: Device hostname with ZFS pools
        performance_goal: Optimization target (performance, capacity, balanced)
        workload_type: Workload characteristics (sequential, random, mixed, vm)
    """
    return f"""You are a ZFS performance engineer optimizing pools on device: {hostname} for {workload_type} workloads with {performance_goal} optimization goal

**Target Device**: {hostname}
**Performance Goal**: {performance_goal}
**Workload Type**: {workload_type}

Please execute comprehensive ZFS optimization workflow:

## Phase 1: Performance Baseline
1. **Current Performance Analysis**:
   - Use get_zfs_arc_stats to establish ARC performance baseline
   - Use generate_zfs_report to get comprehensive performance overview
   - Document current IOPS, throughput, and latency characteristics

2. **Workload Pattern Analysis**:
   - Analyze I/O patterns and access frequencies
   - Identify hot datasets and performance bottlenecks
   - Assess read/write ratios and block size distributions

## Phase 2: Configuration Analysis
3. **Pool Layout Assessment**:
   - Use list_zfs_pools and get_zfs_pool_status to analyze current VDEV structure
   - Evaluate RAID-Z vs mirror configurations for workload requirements
   - Assess special device usage (cache, log, dedup)

4. **Dataset Configuration Review**:
   - Use list_zfs_datasets to analyze dataset properties
   - Review record sizes, compression algorithms, and deduplication settings
   - Assess dataset layout and mount point optimization

## Phase 3: Optimization Implementation
5. **Pool-Level Optimizations**:
   - Use optimize_zfs_settings to get specific tuning recommendations
   - Implement ARC sizing optimizations for available memory
   - Configure prefetch settings for {workload_type} access patterns

6. **Dataset-Level Tuning**:
   - Optimize record sizes for {workload_type} workloads
   - Configure compression algorithms for {performance_goal} balance
   - Tune deduplication settings based on data characteristics

## Phase 4: Advanced Performance Features
7. **Special Device Configuration**:
   - Plan L2ARC (cache) device implementation for read acceleration
   - Configure ZIL (log) devices for write optimization
   - Implement metadata special devices for small file performance

8. **Memory and Cache Optimization**:
   - Optimize ARC sizing for available system memory
   - Configure secondary cache policies and eviction strategies
   - Tune prefetch algorithms for access pattern optimization

## Phase 5: Validation and Monitoring
9. **Performance Testing**:
   - Conduct benchmark tests to validate optimization results
   - Compare performance metrics with baseline measurements
   - Verify that {performance_goal} objectives are achieved

10. **Monitoring Implementation**:
    - Configure performance monitoring dashboards
    - Set up alerts for performance degradation or threshold violations
    - Implement capacity planning and trend analysis

## Phase 6: Maintenance and Tuning
11. **Ongoing Optimization**:
    - Schedule regular performance reviews and adjustments
    - Monitor workload evolution and adapt configurations
    - Plan hardware upgrades based on performance trends

12. **Documentation and Knowledge Transfer**:
    - Document optimization procedures and rationale
    - Create performance tuning guides for operations staff
    - Establish performance management best practices

## Specific Optimizations for {workload_type} workloads:
- Configure appropriate record sizes and prefetch settings
- Optimize ARC allocation and eviction policies  
- Tune compression and deduplication for workload characteristics
- Implement appropriate VDEV layouts for access patterns

Provide specific tuning parameters, performance targets, and validation procedures optimized for {performance_goal} performance with {workload_type} workload characteristics."""