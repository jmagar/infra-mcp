"""
Device analysis prompts for infrastructure management.
"""


def analyze_device_performance(hostname: str, metric_type: str = "all") -> str:
    """
    Generate analysis prompt for device performance based on system metrics.

    Args:
        hostname: The device hostname to analyze
        metric_type: Type of metrics to focus on (cpu, memory, disk, network, or all)
    """
    return f"""You are an expert system administrator analyzing infrastructure performance data for device: {hostname}

Please analyze the device performance data and provide:

1. **Performance Summary**: Overall health assessment of {hostname}
2. **Key Metrics Analysis**: Focus on {metric_type} metrics if specified, otherwise all metrics
3. **Resource Utilization**: CPU, memory, disk usage patterns
4. **Performance Bottlenecks**: Identify any resource constraints
5. **Optimization Recommendations**: Specific actions to improve performance
6. **Monitoring Alerts**: Suggest thresholds for monitoring critical metrics

Use the get_device_info tool to gather comprehensive system information for {hostname}.
Format your analysis in clear sections with actionable recommendations."""


def container_stack_analysis(hostname: str, focus_area: str = "performance") -> str:
    """
    Generate analysis prompt for Docker container stack on a device.

    Args:
        hostname: The device hostname running containers
        focus_area: Area to focus analysis on (performance, security, resources, or overview)
    """
    return f"""You are a Docker infrastructure specialist analyzing the container stack on device: {hostname}

Please analyze the containerized services and provide:

1. **Container Overview**: List all running and stopped containers
2. **Resource Analysis**: Memory, CPU usage per container
3. **Service Dependencies**: Identify service relationships and dependencies  
4. **{focus_area.title()} Assessment**: Deep dive into {focus_area} aspects
5. **Optimization Opportunities**: Container efficiency improvements
6. **Security Considerations**: Container security best practices
7. **Scaling Recommendations**: Horizontal and vertical scaling options

Use the list_containers and get_container_info tools to gather detailed container information for {hostname}.
Provide specific, actionable recommendations for container optimization."""


def infrastructure_health_check(hostname: str) -> str:
    """
    Generate comprehensive health check prompt for infrastructure device.

    Args:
        hostname: The device hostname to health check
    """
    return f"""You are a senior infrastructure engineer performing a comprehensive health check on device: {hostname}

Please conduct a thorough health assessment covering:

1. **System Health**: OS status, uptime, system load
2. **Storage Health**: Disk usage, SMART status, I/O performance  
3. **Network Connectivity**: Network interfaces, connectivity status
4. **Service Status**: Critical services and daemon status
5. **Security Posture**: Security updates, firewall status, open ports
6. **Backup Status**: Backup systems and data protection
7. **Monitoring Coverage**: Existing monitoring and alerting setup

Use multiple tools including get_device_info, get_drive_health, get_drives_stats, and list_containers to gather comprehensive data.
Provide a health score (1-10) and prioritized action items for any issues found."""


def troubleshoot_system_issue(
    hostname: str, issue_description: str, symptom_type: str = "performance"
) -> str:
    """
    Generate troubleshooting prompt for system issues.

    Args:
        hostname: The affected device hostname
        issue_description: Description of the problem
        symptom_type: Type of symptoms (performance, connectivity, service, or error)
    """
    return f"""You are an expert system troubleshooter diagnosing issues on device: {hostname}

**Issue Report**: {issue_description}
**Symptom Type**: {symptom_type}

Please provide systematic troubleshooting guidance:

1. **Issue Classification**: Categorize the problem type and severity
2. **Data Collection**: Specify what diagnostic data to gather
3. **Root Cause Analysis**: Step-by-step investigation approach
4. **Immediate Actions**: Quick fixes or temporary mitigation steps  
5. **Diagnostic Commands**: Specific commands to run for diagnosis
6. **Resolution Steps**: Detailed fix procedures
7. **Prevention Measures**: How to prevent recurrence

Use tools like get_system_logs, get_device_info, and get_container_logs to gather diagnostic information.
Prioritize solutions by impact and implementation complexity."""
