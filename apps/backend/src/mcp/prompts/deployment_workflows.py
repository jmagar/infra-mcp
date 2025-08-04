"""
Deployment automation workflow prompts for infrastructure management.

These prompts create comprehensive workflows for automated deployment,
CI/CD integration, and production rollout procedures.
"""


def full_stack_deployment(
    hostname: str,
    application_name: str,
    environment: str = "production",
    deployment_strategy: str = "blue_green"
) -> str:
    """
    Deploy a complete application stack with full automation and validation.
    
    Args:
        hostname: Target device for deployment
        application_name: Name of application stack to deploy
        environment: Target environment (development, staging, production)
        deployment_strategy: Deployment approach (rolling, blue_green, canary)
    """
    return f"""You are a DevOps automation specialist executing {deployment_strategy} deployment of '{application_name}' to {environment} environment on device: {hostname}

**Application**: {application_name}
**Target Device**: {hostname}
**Environment**: {environment}
**Deployment Strategy**: {deployment_strategy}

Please execute comprehensive full-stack deployment workflow:

## Phase 1: Pre-Deployment Validation
1. **Infrastructure Readiness Assessment**:
   - Use get_device_info to verify system resources and capacity
   - Use scan_device_ports to identify available ports and potential conflicts
   - Use scan_docker_networks to validate network configuration

2. **Environment Preparation**:
   - Verify {environment} environment configuration and secrets
   - Validate external dependencies (databases, APIs, storage)
   - Check backup systems and rollback preparation

## Phase 2: Deployment Planning and Staging
3. **Deployment Configuration**:
   - Use modify_compose_for_device to prepare application configuration for {hostname}
   - Generate proxy configurations using generate_proxy_config for web services
   - Plan service startup sequence and dependency management

4. **Resource Allocation and Scaling**:
   - Analyze current container load using list_containers
   - Plan resource allocation for new application components
   - Configure auto-scaling and load balancing parameters

## Phase 3: {deployment_strategy.title()} Deployment Execution
5. **Deployment Orchestration**:
   - Execute {deployment_strategy} deployment using modify_and_deploy_compose
   - Monitor deployment progress and service health during rollout
   - Implement gradual traffic shifting and validation checkpoints

6. **Service Validation and Health Checks**:
   - Verify all services start successfully using get_container_info
   - Monitor resource utilization with get_container_stats
   - Validate inter-service connectivity and API functionality

## Phase 4: Production Traffic Integration
7. **Traffic Management**:
   - Configure load balancer and proxy routing for new deployment
   - Implement gradual traffic shifting from old to new version
   - Monitor performance metrics and error rates during transition

8. **SSL and Security Configuration**:
   - Update SSL certificates and security configurations
   - Validate security headers and HTTPS enforcement
   - Test authentication and authorization systems

## Phase 5: Monitoring and Validation
9. **Application Performance Monitoring**:
   - Set up application-specific monitoring dashboards
   - Configure alerts for critical application metrics
   - Implement synthetic monitoring and health checks

10. **Data Integrity and Consistency**:
    - Validate data migration and consistency if applicable
    - Verify backup systems are capturing new application data
    - Test disaster recovery procedures for new deployment

## Phase 6: Post-Deployment Optimization
11. **Performance Optimization**:
    - Analyze application performance under production load
    - Optimize container resource allocation and limits
    - Tune caching and database connection settings

12. **Security Hardening**:
    - Implement production security controls and monitoring
    - Configure intrusion detection and log analysis
    - Validate compliance with security policies

## Phase 7: Rollback Preparation and Documentation
13. **Rollback Procedures**:
    - Document rollback procedures and validation steps
    - Test rollback process with non-critical components
    - Prepare emergency rollback triggers and automation

14. **Operations Documentation**:
    - Document deployment procedures and configurations
    - Create operational runbooks for application management
    - Train operations staff on new application components

## Deployment Strategy Specifics for {deployment_strategy}:

### Blue-Green Deployment:
- Deploy new version alongside existing version
- Validate new version thoroughly before traffic switch
- Implement instant rollback capability via traffic routing

### Rolling Deployment:
- Gradually replace instances with zero-downtime approach
- Monitor health during each replacement cycle
- Implement automatic rollback on health check failures

### Canary Deployment:
- Deploy to subset of infrastructure for testing
- Gradually increase traffic percentage to new version
- Monitor metrics and user feedback before full rollout

## Success Criteria for {environment} Deployment:
- All services running with healthy status
- Response times within acceptable thresholds
- Error rates below defined limits
- Security controls properly configured and validated

Provide specific deployment commands, validation procedures, and rollback plans optimized for {deployment_strategy} deployment strategy in {environment} environment."""


def cicd_pipeline_integration(
    hostname: str,
    pipeline_stage: str = "deploy",
    artifact_source: str = "registry",
    integration_type: str = "webhook"
) -> str:
    """
    Integrate infrastructure management with CI/CD pipeline automation.
    
    Args:
        hostname: Target device for pipeline integration
        pipeline_stage: Pipeline stage (build, test, deploy, promote)
        artifact_source: Source of deployment artifacts (registry, git, s3)
        integration_type: Integration method (webhook, api, ssh, agent)
    """
    return f"""You are a CI/CD automation engineer integrating {pipeline_stage} stage pipeline with infrastructure on device: {hostname}

**Target Device**: {hostname}
**Pipeline Stage**: {pipeline_stage}
**Artifact Source**: {artifact_source}
**Integration Type**: {integration_type}

Please execute comprehensive CI/CD pipeline integration workflow:

## Phase 1: Pipeline Integration Setup
1. **Infrastructure API Integration**:
   - Configure authentication and API access for pipeline systems
   - Set up secure credential management for automated deployments
   - Validate network connectivity and firewall rules for pipeline access

2. **Artifact Management Integration**:
   - Configure access to {artifact_source} for deployment artifacts
   - Set up artifact validation and security scanning integration
   - Implement artifact caching and optimization strategies

## Phase 2: Deployment Automation Framework
3. **Automated Deployment Scripts**:
   - Create deployment automation using modify_and_deploy_compose
   - Implement configuration templating and environment-specific variables
   - Set up deployment validation and health checking automation

4. **Infrastructure State Management**:
   - Implement infrastructure-as-code principles for deployment consistency
   - Use list_containers and get_container_info for state validation
   - Create idempotent deployment procedures for reliable automation

## Phase 3: Quality Gates and Validation
5. **Automated Testing Integration**:
   - Implement automated testing during deployment process
   - Configure smoke tests and integration test automation
   - Set up performance testing and validation benchmarks

6. **Security and Compliance Validation**:
   - Integrate security scanning and vulnerability assessment
   - Implement compliance checking and policy validation
   - Configure security monitoring and audit trail generation

## Phase 4: Deployment Orchestration
7. **Multi-Environment Promotion**:
   - Configure environment-specific deployment procedures
   - Implement promotion gates and approval workflows
   - Set up environment parity validation and consistency checks

8. **Service Dependency Management**:
   - Automate service dependency resolution and startup ordering
   - Implement dependency health checking and validation
   - Configure retry logic and failure handling for dependency issues

## Phase 5: Monitoring and Observability
9. **Deployment Monitoring Integration**:
   - Configure deployment progress monitoring and reporting
   - Implement real-time deployment status updates to pipeline
   - Set up deployment failure detection and alerting

10. **Application Performance Integration**:
    - Connect application performance monitoring to pipeline
    - Implement automated rollback triggers based on performance metrics
    - Configure capacity planning and resource optimization feedback

## Phase 6: Failure Handling and Recovery
11. **Automated Rollback Procedures**:
    - Implement automated rollback triggers and procedures
    - Configure rollback validation and success verification
    - Set up emergency rollback capabilities and escalation

12. **Failure Analysis and Learning**:
    - Implement deployment failure analysis and root cause tracking
    - Configure continuous improvement feedback loops
    - Create deployment success metrics and reporting

## Integration Specifics for {integration_type}:

### Webhook Integration:
- Configure secure webhook endpoints for pipeline triggers
- Implement payload validation and authentication
- Set up asynchronous processing and status reporting

### API Integration:
- Create RESTful API endpoints for pipeline operations
- Implement proper authentication and rate limiting
- Configure API versioning and backward compatibility

### SSH Integration:
- Set up secure key-based authentication for pipeline access
- Implement command execution sandboxing and security
- Configure audit logging and access monitoring

### Agent Integration:
- Deploy lightweight agents for pipeline communication
- Implement secure agent registration and management
- Configure agent health monitoring and automatic recovery

## Pipeline Stage Automation for {pipeline_stage}:

### Deploy Stage:
- Automated artifact deployment and configuration
- Service health validation and readiness checking
- Environment-specific configuration application

### Test Stage:
- Automated test environment provisioning and cleanup
- Test execution and result reporting
- Test data management and environment isolation

### Promote Stage:
- Automated promotion between environments
- Configuration drift detection and correction
- Promotion validation and approval workflow integration

Provide specific integration configurations, automation scripts, and monitoring procedures optimized for {integration_type} integration with {pipeline_stage} pipeline stage using {artifact_source} artifacts."""


def infrastructure_as_code_deployment(
    hostname: str,
    iac_tool: str = "compose",
    configuration_source: str = "git",
    drift_detection: bool = True
) -> str:
    """
    Implement Infrastructure as Code (IaC) deployment and management practices.
    
    Args:
        hostname: Target device for IaC deployment
        iac_tool: Infrastructure tool (compose, terraform, ansible, helm)
        configuration_source: Configuration repository (git, s3, registry)
        drift_detection: Enable configuration drift detection
    """
    return f"""You are an Infrastructure as Code specialist implementing {iac_tool}-based infrastructure management on device: {hostname}

**Target Device**: {hostname}
**IaC Tool**: {iac_tool}
**Configuration Source**: {configuration_source}
**Drift Detection**: {drift_detection}

Please execute comprehensive Infrastructure as Code deployment workflow:

## Phase 1: IaC Framework Setup
1. **Configuration Repository Structure**:
   - Establish standardized directory structure for {iac_tool} configurations
   - Implement version control best practices for infrastructure definitions
   - Set up environment-specific configuration management and templating

2. **Validation and Testing Framework**:
   - Configure syntax validation and linting for {iac_tool} configurations
   - Implement configuration testing and validation procedures
   - Set up dry-run capabilities for safe configuration changes

## Phase 2: Infrastructure State Management
3. **Current State Discovery**:
   - Use list_containers and get_container_info to inventory current infrastructure
   - Use list_proxy_configs to document current proxy configurations
   - Use get_device_info to establish infrastructure baseline

4. **Configuration Generation and Import**:
   - Generate {iac_tool} configurations from current infrastructure state
   - Import existing configurations into version control system
   - Establish configuration ownership and change management procedures

## Phase 3: Declarative Infrastructure Management
5. **Configuration Deployment**:
   - Implement declarative deployment using modify_and_deploy_compose
   - Configure idempotent operations for consistent infrastructure state
   - Set up configuration validation and pre-deployment checks

6. **State Reconciliation**:
   - Implement configuration drift detection and correction
   - Set up automated state reconciliation and healing
   - Configure change tracking and audit trail generation

## Phase 4: Environment Management
7. **Multi-Environment Configuration**:
   - Implement environment-specific configuration overlays
   - Configure promotion workflows between environments
   - Set up environment parity validation and consistency checking

8. **Configuration Templating and Parameterization**:
   - Implement dynamic configuration generation with parameters
   - Set up environment-specific variable management
   - Configure secret management and secure parameter handling

## Phase 5: Change Management and Validation
9. **Configuration Change Workflow**:
   - Implement pull request workflows for infrastructure changes
   - Set up peer review and approval processes for configuration updates
   - Configure automated testing and validation for proposed changes

10. **Deployment Validation and Testing**:
    - Implement automated deployment testing and validation
    - Configure rollback procedures for failed deployments
    - Set up integration testing for infrastructure changes

## Phase 6: Drift Detection and Compliance
11. **Configuration Drift Monitoring**:
    - {"Implement automated drift detection using infrastructure scanning" if drift_detection else "Configure manual drift detection procedures"}
    - Set up drift reporting and notification systems
    - Configure automatic drift correction and remediation

12. **Compliance and Policy Enforcement**:
    - Implement policy as code for infrastructure compliance
    - Configure security and governance policy validation
    - Set up compliance reporting and audit trail maintenance

## Phase 7: Operations and Maintenance
13. **Operational Procedures**:
    - Create operational runbooks for IaC management
    - Implement backup and disaster recovery for configuration repositories
    - Set up monitoring and alerting for infrastructure configuration health

14. **Continuous Improvement**:
    - Implement feedback loops for configuration optimization
    - Set up metrics collection for infrastructure management efficiency
    - Configure continuous learning and best practice evolution

## IaC Tool Specifics for {iac_tool}:

### Docker Compose:
- Standardized compose file structure and naming conventions
- Environment variable management and secret handling
- Service dependency management and health checking

### Terraform:
- State file management and remote backend configuration
- Module development and reusability patterns
- Provider configuration and version management

### Ansible:
- Playbook organization and role development
- Inventory management and dynamic inventory integration
- Variable management and encryption handling

### Helm:
- Chart development and template management
- Values file organization and environment-specific overrides
- Release management and upgrade procedures

## Configuration Source Integration for {configuration_source}:

### Git Integration:
- Branch-based environment management and promotion workflows
- Tag-based release management and rollback procedures
- Webhook integration for automated deployment triggers

### Registry Integration:
- Configuration artifact packaging and versioning
- Secure credential management for registry access
- Configuration distribution and caching strategies

## Success Metrics and Validation:
- Configuration drift detection and correction rates
- Deployment success rates and rollback frequency
- Infrastructure provisioning time and consistency
- Compliance adherence and policy violation rates

Provide specific IaC configurations, deployment procedures, and validation frameworks optimized for {iac_tool} with {configuration_source} integration and {"automated" if drift_detection else "manual"} drift detection."""


def zero_downtime_deployment(
    hostname: str,
    service_type: str = "web_application",
    load_balancer: str = "nginx",
    health_check_strategy: str = "comprehensive"
) -> str:
    """
    Execute zero-downtime deployment with comprehensive validation and rollback capabilities.
    
    Args:
        hostname: Target device for zero-downtime deployment
        service_type: Type of service (web_application, api_service, database, microservice)
        load_balancer: Load balancing solution (nginx, haproxy, traefik, cloud_lb)
        health_check_strategy: Health validation approach (basic, comprehensive, custom)
    """
    return f"""You are a high-availability deployment specialist executing zero-downtime deployment of {service_type} on device: {hostname}

**Target Device**: {hostname}
**Service Type**: {service_type}
**Load Balancer**: {load_balancer}
**Health Check Strategy**: {health_check_strategy}

Please execute comprehensive zero-downtime deployment workflow:

## Phase 1: Pre-Deployment Health Baseline
1. **Current Service Health Assessment**:
   - Use get_container_info and get_container_stats to establish service health baseline
   - Document current performance metrics and response characteristics
   - Validate current load balancer configuration and health checks

2. **Capacity and Resource Planning**:
   - Use get_device_info to assess available resources for parallel deployment
   - Plan resource allocation for running both old and new versions
   - Configure monitoring for resource contention during deployment

## Phase 2: Deployment Infrastructure Preparation
3. **Load Balancer Configuration**:
   - Configure {load_balancer} for gradual traffic shifting
   - Set up health check endpoints with {health_check_strategy} validation
   - Implement session persistence and connection draining procedures

4. **Service Discovery and Registration**:
   - Configure dynamic service registration for new service instances
   - Set up health check integration with service discovery
   - Plan service deregistration procedures for old instances

## Phase 3: Parallel Service Deployment
5. **New Version Deployment**:
   - Deploy new service version using modify_and_deploy_compose
   - Configure new instances with separate resource allocation
   - Validate new service startup and readiness independently

6. **Health Validation and Warm-up**:
   - Execute comprehensive health checks on new service instances
   - Perform service warm-up procedures and cache preloading
   - Validate all service dependencies and external integrations

## Phase 4: Traffic Management and Gradual Cutover
7. **Gradual Traffic Shifting**:
   - Begin with 5% traffic to new version with comprehensive monitoring
   - Gradually increase traffic percentage (5% → 25% → 50% → 75% → 100%)
   - Monitor error rates, response times, and resource utilization at each stage

8. **Real-time Health Monitoring**:
   - Implement real-time monitoring of both service versions
   - Configure automatic rollback triggers for performance degradation
   - Monitor business metrics and user experience indicators

## Phase 5: Service Validation and Testing
9. **Comprehensive Service Testing**:
   - Execute automated integration tests against new service version
   - Perform load testing to validate performance under production traffic
   - Test all critical user journeys and business processes

10. **Data Consistency and State Management**:
    - Validate data consistency between service versions if applicable
    - Verify session management and state preservation during cutover
    - Test transaction integrity and rollback procedures

## Phase 6: Old Version Decommissioning
11. **Connection Draining and Graceful Shutdown**:
    - Implement connection draining for old service instances
    - Allow existing requests to complete before instance shutdown
    - Monitor for any lingering connections or incomplete transactions

12. **Resource Cleanup and Optimization**:
    - Remove old service instances and configurations
    - Reclaim resources allocated to old version
    - Optimize resource allocation for new service version

## Phase 7: Post-Deployment Validation
13. **Complete System Validation**:
    - Perform end-to-end system testing and validation
    - Verify all integrations and dependencies are functioning correctly
    - Validate monitoring and alerting systems for new deployment

14. **Performance and Capacity Analysis**:
    - Analyze performance improvements or changes in new version
    - Document capacity utilization and resource efficiency
    - Plan future scaling and optimization opportunities

## Health Check Strategy Specifics for {health_check_strategy}:

### Basic Health Checks:
- HTTP endpoint availability and response code validation
- Service process and port availability checking
- Basic dependency connectivity validation

### Comprehensive Health Checks:
- Deep application health and dependency validation
- Database connectivity and query execution testing
- Cache availability and performance validation
- External service integration testing

### Custom Health Checks:
- Business logic validation and critical path testing
- Data consistency and integrity validation
- Performance benchmark and SLA compliance checking

## Service Type Specifics for {service_type}:

### Web Application:
- Static asset availability and CDN integration
- Session management and user authentication flow
- Database connectivity and transaction handling

### API Service:
- Endpoint availability and response validation
- Authentication and authorization system testing
- Rate limiting and throttling configuration validation

### Database Service:
- Data consistency and replication lag monitoring
- Connection pool management and query performance
- Backup and recovery system validation

## Rollback and Emergency Procedures:
- Automated rollback triggers and thresholds
- Emergency traffic redirection procedures
- Communication and escalation protocols

Provide specific deployment commands, health check configurations, and rollback procedures optimized for zero-downtime deployment of {service_type} using {load_balancer} with {health_check_strategy} health validation."""