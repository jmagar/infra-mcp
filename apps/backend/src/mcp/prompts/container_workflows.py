"""
Container lifecycle management prompts for infrastructure workflows.

These prompts create comprehensive workflows for managing Docker containers
across the infrastructure, leveraging multiple MCP tools for complete lifecycle management.
"""


def deploy_application_stack(
    hostname: str, 
    stack_name: str, 
    compose_content: str | None = None,
    environment: str = "production"
) -> str:
    """
    Deploy a complete application stack with all dependencies and configurations.
    
    Args:
        hostname: Target device for deployment
        stack_name: Name of the application stack  
        compose_content: Docker Compose content (optional)
        environment: Target environment (development, staging, production)
    """
    return f"""You are a DevOps engineer deploying the '{stack_name}' application stack to device: {hostname}

**Deployment Environment**: {environment}
**Target Device**: {hostname}
**Stack Name**: {stack_name}

Please execute a complete application deployment workflow:

## Phase 1: Pre-Deployment Analysis
1. **Infrastructure Assessment**: 
   - Use get_device_info to verify system resources and capabilities
   - Use scan_device_ports to identify available ports for services
   - Use scan_docker_networks to analyze network configuration

2. **Resource Planning**:
   - Analyze current container load using list_containers
   - Check disk space and storage health with get_drives_stats
   - Verify network connectivity and port availability

## Phase 2: Stack Preparation
3. **Compose Configuration**:
   - Use modify_compose_for_device to adapt the compose file for {hostname}
   - Generate proxy configurations for web services using generate_proxy_config
   - Validate network configurations and port mappings

4. **Dependency Management**:
   - Identify service dependencies and startup order
   - Plan volume mounts and persistent storage requirements
   - Configure environment-specific variables for {environment}

## Phase 3: Deployment Execution  
5. **Stack Deployment**:
   - Use deploy_compose_to_device or modify_and_deploy_compose for deployment
   - Monitor deployment progress and container startup
   - Verify all services start successfully using get_container_info

6. **Post-Deployment Verification**:
   - Check container health and resource usage with get_container_stats
   - Verify log outputs using get_container_logs
   - Test service connectivity and proxy configurations

## Phase 4: Production Readiness
7. **Monitoring Setup**:
   - Configure health checks and monitoring alerts
   - Set up log aggregation and analysis
   - Document service endpoints and access methods

8. **Rollback Preparation**:
   - Create deployment snapshot for quick rollback
   - Document rollback procedures
   - Test rollback process in case of issues

Provide detailed execution steps, error handling procedures, and success validation criteria for each phase."""


def troubleshoot_container_issues(
    hostname: str, 
    container_name: str | None = None, 
    issue_type: str = "performance"
) -> str:
    """
    Comprehensive container troubleshooting workflow.
    
    Args:
        hostname: Device hostname with container issues
        container_name: Specific container to troubleshoot (optional)
        issue_type: Type of issue (performance, connectivity, startup, resource)
    """
    container_context = f"container '{container_name}'" if container_name else "containers"
    
    return f"""You are a senior container specialist troubleshooting {issue_type} issues with {container_context} on device: {hostname}

**Issue Type**: {issue_type}
**Target Device**: {hostname}
{'**Specific Container**: ' + container_name if container_name else '**Scope**: All containers'}

Please execute systematic container troubleshooting:

## Phase 1: Issue Assessment
1. **Container Status Analysis**:
   - Use list_containers to get overview of all container states
   - Use get_container_info for detailed information on affected containers
   - Identify patterns in container failures or performance issues

2. **Resource Impact Analysis**:
   - Use get_container_stats to analyze resource consumption
   - Check system-wide impact with get_device_info
   - Identify resource contention or limits

## Phase 2: Diagnostic Data Collection
3. **Log Analysis**:
   - Use get_container_logs to examine container output and errors
   - Use get_device_logs to check system-level events
   - Correlate timestamps between container and system logs

4. **System Health Check**:
   - Verify storage health with get_drive_health and get_drives_stats
   - Check network connectivity and port conflicts
   - Analyze Docker daemon status and configuration

## Phase 3: Root Cause Investigation
5. **Container-Specific Analysis**:
   - Examine container configuration and environment variables
   - Check volume mounts and file permissions
   - Analyze network connectivity between containers

6. **Infrastructure Dependencies**:
   - Verify proxy configurations if web services affected
   - Check database connections and external service dependencies
   - Analyze resource limits and Docker daemon settings

## Phase 4: Resolution and Recovery
7. **Immediate Mitigation**:
   - Apply quick fixes for critical service restoration
   - Use restart_container or stop_container/start_container as needed
   - Implement temporary workarounds if necessary

8. **Permanent Resolution**:
   - Address root cause with configuration changes
   - Update compose files or container configurations  
   - Implement monitoring to prevent recurrence

## Phase 5: Validation and Documentation
9. **Solution Verification**:
   - Verify container functionality and performance
   - Run integration tests and health checks
   - Monitor for 15-30 minutes to ensure stability

10. **Documentation and Prevention**:
    - Document issue, root cause, and resolution steps
    - Update monitoring alerts and thresholds
    - Create preventive measures and best practices

Focus on {issue_type} specific diagnostics and provide step-by-step resolution procedures with validation checkpoints."""


def container_stack_maintenance(
    hostname: str, 
    maintenance_type: str = "routine",
    downtime_window: str = "30 minutes"
) -> str:
    """
    Perform comprehensive container stack maintenance operations.
    
    Args:
        hostname: Device hostname for maintenance
        maintenance_type: Type of maintenance (routine, security, performance, cleanup)
        downtime_window: Available maintenance window
    """
    return f"""You are a container infrastructure specialist performing {maintenance_type} maintenance on device: {hostname}

**Maintenance Type**: {maintenance_type}
**Target Device**: {hostname}  
**Downtime Window**: {downtime_window}

Please execute comprehensive container maintenance workflow:

## Phase 1: Pre-Maintenance Assessment
1. **Current State Analysis**:
   - Use list_containers to inventory all containers and their states
   - Use get_container_stats to establish baseline performance metrics
   - Document current resource utilization and service health

2. **Maintenance Planning**:
   - Identify critical services that require special handling
   - Plan service shutdown and startup sequence to minimize dependencies
   - Prepare rollback procedures in case of issues

## Phase 2: Backup and Safety Measures  
3. **Data Protection**:
   - Create snapshots of critical data volumes
   - Backup container configurations and compose files
   - Document current network and proxy configurations

4. **Service Dependencies**:
   - Map service dependencies and communication patterns
   - Plan graceful shutdown sequence for dependent services
   - Prepare health check procedures for service validation

## Phase 3: Maintenance Execution
5. **System Updates** (if {maintenance_type} includes security):
   - Update base system packages and Docker daemon
   - Pull latest security patches for container images
   - Update container runtime and orchestration tools

6. **Container Optimization**:
   - Clean up unused containers, images, and volumes
   - Optimize container resource limits and requests
   - Update container configurations for better performance

7. **Storage Maintenance**:
   - Use get_drives_stats to analyze storage utilization
   - Clean up log files and temporary data
   - Optimize volume mounts and storage configurations

## Phase 4: Service Restoration
8. **Controlled Restart**:
   - Restart containers in dependency order using restart_container
   - Monitor startup sequence and service health
   - Verify inter-service connectivity and functionality

9. **Performance Validation**:
   - Use get_container_stats to verify post-maintenance performance
   - Compare metrics with pre-maintenance baseline
   - Run integration tests to ensure full functionality

## Phase 5: Post-Maintenance Verification
10. **System Health Check**:
    - Verify all services are running optimally
    - Check proxy configurations and external access
    - Monitor system resources and container performance

11. **Documentation and Reporting**:
    - Document maintenance activities and results
    - Update system configuration documentation
    - Schedule next maintenance window and create monitoring alerts

Ensure all activities stay within the {downtime_window} window and provide detailed rollback procedures if issues arise."""


def scale_container_services(
    hostname: str,
    service_name: str,
    target_scale: str = "auto",
    scaling_strategy: str = "horizontal"
) -> str:
    """
    Scale container services based on demand and resource availability.
    
    Args:
        hostname: Device hostname for scaling operations
        service_name: Name of service to scale
        target_scale: Target scaling (number or 'auto' for automatic)
        scaling_strategy: Scaling approach (horizontal, vertical, or hybrid)
    """
    return f"""You are a container orchestration specialist implementing {scaling_strategy} scaling for service '{service_name}' on device: {hostname}

**Service**: {service_name}
**Target Device**: {hostname}
**Target Scale**: {target_scale}
**Scaling Strategy**: {scaling_strategy}

Please execute comprehensive service scaling workflow:

## Phase 1: Current State Analysis
1. **Service Assessment**:
   - Use get_container_info to analyze current service configuration
   - Use get_container_stats to understand current resource utilization
   - Document current performance metrics and bottlenecks

2. **Capacity Planning**:
   - Use get_device_info to assess available system resources
   - Analyze network and storage capacity for scaling requirements
   - Evaluate proxy and load balancing configuration needs

## Phase 2: Scaling Strategy Implementation
3. **Resource Allocation**:
   - Calculate resource requirements for target scale
   - Use scan_device_ports to identify available ports for new instances
   - Plan network configuration for service discovery and load balancing

4. **Configuration Updates**:
   - Update compose configurations for scaling requirements
   - Configure load balancers and proxy settings using generate_proxy_config
   - Prepare environment variables and service discovery

## Phase 3: Scaling Execution
5. **Gradual Scaling**:
   - Implement scaling in stages to minimize service disruption
   - Monitor resource consumption during scaling process
   - Use get_container_stats to track performance impact

6. **Service Mesh Updates**:
   - Update service discovery and registration
   - Configure load balancing and traffic distribution
   - Verify inter-service communication and dependencies

## Phase 4: Validation and Optimization
7. **Performance Validation**:
   - Load test scaled service to verify performance improvements
   - Monitor resource utilization across all service instances
   - Validate failover and redundancy capabilities

8. **Cost and Resource Optimization**:
   - Analyze resource efficiency of scaled deployment
   - Optimize container resource limits and requests
   - Implement auto-scaling triggers and policies

## Phase 5: Monitoring and Maintenance
9. **Monitoring Setup**:
   - Configure monitoring for scaled service instances
   - Set up alerts for performance degradation or failures
   - Implement health checks and automatic recovery

10. **Documentation and Operations**:
    - Document scaling procedures and configurations
    - Create operational runbooks for scaled service management
    - Plan capacity monitoring and future scaling decisions

Provide specific commands and configurations for {scaling_strategy} scaling, with rollback procedures and performance validation criteria."""