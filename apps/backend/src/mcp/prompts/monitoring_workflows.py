"""
Infrastructure monitoring and alerting workflow prompts.

These prompts create comprehensive workflows for monitoring infrastructure health,
setting up alerting systems, and implementing observability best practices.
"""


def infrastructure_health_monitoring(
    hostname: str,
    monitoring_scope: str = "comprehensive",
    alert_urgency: str = "production"
) -> str:
    """
    Set up comprehensive infrastructure health monitoring and alerting.
    
    Args:
        hostname: Device hostname for monitoring setup
        monitoring_scope: Scope of monitoring (basic, comprehensive, enterprise)
        alert_urgency: Alert level (development, staging, production, critical)
    """
    return f"""You are an infrastructure monitoring specialist implementing {monitoring_scope} monitoring for device: {hostname}

**Target Device**: {hostname}
**Monitoring Scope**: {monitoring_scope}
**Alert Urgency**: {alert_urgency}

Please execute comprehensive infrastructure monitoring setup workflow:

## Phase 1: Infrastructure Health Baseline
1. **System Health Assessment**:
   - Use get_device_info to establish comprehensive system baseline
   - Use get_drive_health to assess storage health and establish SMART baselines
   - Use get_drives_stats to understand I/O patterns and performance baselines

2. **Service Inventory and Health**:
   - Use list_containers to inventory all services and their current states
   - Use get_container_stats to establish resource utilization baselines
   - Document critical services and their performance characteristics

## Phase 2: Monitoring Infrastructure Setup
3. **Core Metrics Collection**:
   - Configure system-level monitoring (CPU, memory, disk, network)
   - Set up container-level monitoring with resource tracking
   - Implement storage monitoring with SMART data collection and trend analysis

4. **Log Aggregation and Analysis**:
   - Use get_device_logs to configure system log collection
   - Use get_container_logs to set up application log aggregation
   - Implement log parsing, filtering, and correlation for error detection

## Phase 3: Service-Specific Monitoring
5. **Container and Application Monitoring**:
   - Monitor container health, restart counts, and resource consumption
   - Set up application performance monitoring and response time tracking
   - Configure dependency monitoring and service connectivity validation

6. **ZFS and Storage Monitoring**:
   - Use check_zfs_health for comprehensive ZFS pool monitoring
   - Use get_zfs_arc_stats for cache performance and hit ratio monitoring
   - Monitor snapshot usage and space consumption trends

## Phase 4: Alert Configuration and Thresholds
7. **Critical Alert Setup**:
   - Configure {alert_urgency}-level alerts for system failures and outages
   - Set up immediate alerts for storage failures, pool degradation, and critical errors
   - Implement escalation procedures for unacknowledged critical alerts

8. **Performance and Capacity Alerts**:
   - Configure threshold-based alerts for resource utilization
   - Set up predictive alerts for capacity planning and growth trends
   - Implement performance degradation detection and alerting

## Phase 5: Advanced Monitoring Features
9. **Trend Analysis and Capacity Planning**:
   - Implement historical data collection and trend analysis
   - Set up capacity planning alerts and growth projections
   - Configure seasonal and pattern-based anomaly detection

10. **Service Dependency Monitoring**:
    - Monitor inter-service connectivity and dependency health
    - Set up cascade failure detection and root cause analysis
    - Implement service map visualization and impact analysis

## Phase 6: Incident Response Integration
11. **Alert Routing and Escalation**:
    - Configure alert routing based on severity and service impact
    - Set up escalation procedures for different alert types
    - Implement on-call rotation and notification management

12. **Automated Response and Remediation**:
    - Configure automated responses for common issues
    - Set up self-healing procedures for known failure patterns
    - Implement runbook automation for incident response

## Monitoring Scope Configuration for {monitoring_scope}:

### Basic Monitoring:
- System health, disk space, and service availability
- Basic alerting for critical failures and resource exhaustion
- Simple log collection and error detection

### Comprehensive Monitoring:
- Detailed performance monitoring and capacity planning
- Advanced alerting with trend analysis and predictive capabilities
- Complete log aggregation with correlation and analysis

### Enterprise Monitoring:
- Full observability with distributed tracing and APM
- Advanced analytics with machine learning anomaly detection
- Complete automation with self-healing and predictive maintenance

## Alert Urgency Configuration for {alert_urgency}:

### Production Alerts:
- Immediate notification for service outages and critical failures
- 5-minute SLA for alert acknowledgment and response
- Automated escalation and incident management integration

Provide specific monitoring configurations, alert thresholds, and incident response procedures optimized for {monitoring_scope} monitoring with {alert_urgency} alert urgency."""


def performance_monitoring_optimization(
    hostname: str,
    performance_focus: str = "latency",
    monitoring_depth: str = "application"
) -> str:
    """
    Implement performance monitoring and optimization workflows.
    
    Args:
        hostname: Device hostname for performance monitoring
        performance_focus: Focus area (latency, throughput, resource_efficiency, user_experience)
        monitoring_depth: Monitoring level (system, application, business)
    """
    return f"""You are a performance monitoring specialist optimizing {performance_focus} monitoring at {monitoring_depth} level on device: {hostname}

**Target Device**: {hostname}
**Performance Focus**: {performance_focus}
**Monitoring Depth**: {monitoring_depth}

Please execute comprehensive performance monitoring optimization workflow:

## Phase 1: Performance Baseline Establishment
1. **System Performance Baseline**:
   - Use get_device_info to establish comprehensive system performance baseline
   - Use get_container_stats to measure current application performance characteristics
   - Document performance patterns and identify optimization opportunities

2. **Workload Analysis and Profiling**:
   - Analyze current workload patterns and resource utilization
   - Identify performance bottlenecks and constraint points
   - Establish performance SLAs and target metrics

## Phase 2: Monitoring Infrastructure Design
3. **Performance Metrics Collection**:
   - Configure detailed {performance_focus} monitoring and measurement
   - Set up real-time performance dashboards and visualization
   - Implement performance trend analysis and historical comparison

4. **Deep Performance Instrumentation**:
   - Configure application-level performance monitoring and tracing
   - Set up database query performance monitoring and optimization
   - Implement network performance monitoring and analysis

## Phase 3: Advanced Performance Analytics
5. **Performance Correlation and Analysis**:
   - Correlate system metrics with application performance
   - Analyze resource contention and performance impact
   - Identify performance patterns and optimization opportunities

6. **Predictive Performance Monitoring**:
   - Implement performance forecasting and capacity planning
   - Set up performance regression detection and alerting
   - Configure automated performance optimization recommendations

## Phase 4: Performance Optimization Implementation
7. **Resource Optimization**:
   - Optimize container resource allocation based on monitoring data
   - Implement dynamic resource scaling and performance tuning
   - Configure caching and performance acceleration strategies

8. **Application Performance Tuning**:
   - Optimize application configurations based on performance monitoring
   - Implement performance-aware load balancing and traffic management
   - Configure application-specific performance optimizations

## Phase 5: Performance Monitoring Automation
9. **Automated Performance Testing**:
   - Set up continuous performance testing and benchmarking
   - Implement performance regression testing in deployment pipelines
   - Configure performance comparison and validation automation

10. **Self-Healing Performance Management**:
    - Implement automated performance issue detection and resolution
    - Configure dynamic resource allocation and performance optimization
    - Set up performance-based auto-scaling and load management

## Performance Focus Optimization for {performance_focus}:

### Latency Optimization:
- Response time monitoring and percentile analysis
- Request tracing and bottleneck identification
- Cache performance optimization and hit ratio improvement

### Throughput Optimization:
- Request rate monitoring and capacity analysis
- Resource utilization optimization and scaling strategies
- Queue depth monitoring and processing optimization

### Resource Efficiency:
- Resource utilization monitoring and waste identification
- Cost optimization and efficiency improvement strategies
- Capacity planning and right-sizing recommendations

### User Experience:
- End-user performance monitoring and real user monitoring (RUM)
- User journey analysis and experience optimization
- Performance impact on business metrics and conversion rates

Provide specific performance monitoring configurations, optimization procedures, and automation scripts optimized for {performance_focus} with {monitoring_depth} level monitoring."""


def alerting_and_incident_management(
    hostname: str,
    alert_strategy: str = "tiered",
    incident_severity: str = "production"
) -> str:
    """
    Implement comprehensive alerting and incident management procedures.
    
    Args:
        hostname: Device hostname for alerting setup
        alert_strategy: Alerting approach (basic, tiered, intelligent, predictive)
        incident_severity: Incident classification (development, staging, production, mission_critical)
    """
    return f"""You are an incident management specialist implementing {alert_strategy} alerting strategy for {incident_severity} environment on device: {hostname}

**Target Device**: {hostname}
**Alert Strategy**: {alert_strategy}
**Incident Severity**: {incident_severity}

Please execute comprehensive alerting and incident management workflow:

## Phase 1: Alert Classification and Prioritization
1. **Alert Taxonomy Development**:
   - Classify alerts by severity, impact, and urgency for {incident_severity} environment
   - Define alert categories: critical, warning, informational, and predictive
   - Establish service impact levels and business priority mapping

2. **Threshold Definition and Tuning**:
   - Use get_device_info and get_container_stats to establish baseline thresholds
   - Configure dynamic thresholds based on historical data and patterns
   - Implement alert suppression and correlation to reduce noise

## Phase 2: Multi-Level Alert Strategy Implementation
3. **System-Level Alerting**:
   - Configure critical system alerts using get_drive_health for storage failures
   - Set up resource exhaustion alerts for CPU, memory, and disk space
   - Implement network connectivity and infrastructure failure detection

4. **Application-Level Alerting**:
   - Configure service availability and health check alerting
   - Set up performance degradation and SLA violation alerts
   - Implement application error rate and failure pattern detection

## Phase 3: Intelligent Alert Management
5. **Alert Correlation and Suppression**:
   - Implement alert correlation to identify root causes and reduce noise
   - Configure alert suppression during maintenance windows and deployments
   - Set up dependent service alert correlation and cascade failure detection

6. **Predictive and Proactive Alerting**:
   - Configure trend-based alerts for capacity planning and growth
   - Implement anomaly detection for unusual patterns and behaviors
   - Set up predictive alerts for potential failures and performance issues

## Phase 4: Incident Response Automation
7. **Automated Incident Classification**:
   - Implement automated incident creation and classification
   - Configure severity assessment based on service impact and business priority
   - Set up automatic escalation procedures and timeline management

8. **Response Automation and Orchestration**:
   - Configure automated response procedures for common incidents
   - Implement self-healing automation for known failure patterns
   - Set up automated diagnostic data collection and analysis

## Phase 5: Communication and Escalation
9. **Notification and Communication**:
   - Configure multi-channel notification (email, SMS, Slack, PagerDuty)
   - Set up role-based notification routing and escalation procedures
   - Implement stakeholder communication and status page automation

10. **Escalation Management**:
    - Configure time-based escalation procedures for unacknowledged alerts
    - Set up management escalation for high-impact incidents
    - Implement follow-the-sun support and global escalation procedures

## Phase 6: Incident Lifecycle Management
11. **Incident Tracking and Management**:
    - Set up comprehensive incident tracking and lifecycle management
    - Configure incident documentation and knowledge base integration
    - Implement post-incident review and continuous improvement processes

12. **Metrics and Reporting**:
    - Configure MTTR, MTBF, and availability metrics tracking
    - Set up incident trend analysis and pattern identification
    - Implement SLA reporting and compliance monitoring

## Alert Strategy Implementation for {alert_strategy}:

### Basic Alerting:
- Simple threshold-based alerts for critical system and service failures
- Basic notification routing and escalation procedures
- Manual incident management and response procedures

### Tiered Alerting:
- Multi-level alert classification with severity-based routing
- Automated correlation and suppression to reduce alert noise
- Structured escalation procedures with timeline management

### Intelligent Alerting:
- Machine learning-based anomaly detection and pattern recognition
- Context-aware alert correlation and root cause analysis
- Predictive alerting with proactive issue identification

### Predictive Alerting:
- Advanced analytics and forecasting for proactive issue prevention
- Behavioral analysis and trend-based alerting
- Automated remediation and self-healing capabilities

## Incident Severity Configuration for {incident_severity}:

### Production Environment:
- 15-minute response time for critical incidents
- 24/7 on-call coverage with immediate escalation procedures
- Complete incident documentation and post-mortem requirements

### Mission Critical Environment:
- 5-minute response time for critical incidents
- Redundant on-call coverage with automatic failover
- Real-time incident communication and executive reporting

Provide specific alerting configurations, escalation procedures, and incident management workflows optimized for {alert_strategy} alerting with {incident_severity} incident severity requirements."""