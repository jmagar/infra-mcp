"""
Proxy configuration workflow prompts for SWAG reverse proxy management.

These prompts create comprehensive workflows for managing SWAG reverse proxy
configurations, SSL certificates, and service routing.
"""


def deploy_reverse_proxy_service(
    hostname: str,
    service_name: str,
    upstream_port: int,
    domain: str | None = None,
    ssl_enabled: bool = True
) -> str:
    """
    Deploy and configure reverse proxy for a new service with SSL termination.
    
    Args:
        hostname: Device hostname running SWAG proxy
        service_name: Name of service to proxy
        upstream_port: Backend service port
        domain: Custom domain (optional)
        ssl_enabled: Enable SSL/TLS termination
    """
    return f"""You are a reverse proxy specialist deploying proxy configuration for service '{service_name}' on device: {hostname}

**Service**: {service_name}
**Target Device**: {hostname}
**Upstream Port**: {upstream_port}
{'**Domain**: ' + domain if domain else '**Domain**: Auto-generated'}
**SSL Enabled**: {ssl_enabled}

Please execute comprehensive reverse proxy deployment workflow:

## Phase 1: Infrastructure Assessment
1. **Proxy Infrastructure Analysis**:
   - Use get_proxy_config_summary to assess current proxy configuration state
   - Use list_proxy_configs to identify existing configurations and potential conflicts
   - Verify SWAG container status and configuration using get_container_info

2. **Service Discovery and Validation**:
   - Verify upstream service is running and accessible on port {upstream_port}
   - Use scan_device_ports to confirm port availability and service binding
   - Test backend service health and response characteristics

## Phase 2: Configuration Generation
3. **Proxy Configuration Creation**:
   - Use generate_proxy_config to create optimized proxy configuration for {service_name}
   - Configure upstream backend pointing to localhost:{upstream_port}
   - Implement health checks and failure handling for backend service

4. **SSL and Security Configuration**:
   - Configure SSL certificate management {"(Let's Encrypt)" if ssl_enabled else "(disabled)"}
   - Implement security headers and HTTPS redirection
   - Configure rate limiting and DDoS protection measures

## Phase 3: Advanced Routing and Load Balancing
5. **Traffic Management**:
   - Configure load balancing if multiple backend instances exist
   - Implement sticky sessions if required by application
   - Configure request/response buffering and timeouts

6. **Path-Based Routing**:
   - Configure location blocks for different application paths
   - Implement API vs static content routing optimization
   - Set up custom error pages and maintenance modes

## Phase 4: Deployment and Activation
7. **Configuration Deployment**:
   - Deploy proxy configuration to SWAG configuration directory
   - Use sync_proxy_config to synchronize configuration with database
   - Validate configuration syntax and structure

8. **Service Activation**:
   - Reload SWAG configuration without service interruption
   - Verify configuration parsing and activation
   - Monitor SWAG logs for configuration errors or warnings

## Phase 5: Testing and Validation
9. **Connectivity Testing**:
   - Test HTTP and HTTPS access to proxied service
   - Verify SSL certificate installation and validity
   - Test various request types and response handling

10. **Performance and Security Validation**:
    - Validate proxy performance and response times
    - Test security headers and HTTPS enforcement
    - Verify rate limiting and protection mechanisms

## Phase 6: Monitoring and Maintenance
11. **Monitoring Configuration**:
    - Set up monitoring for proxy service health and performance
    - Configure alerts for SSL certificate expiration
    - Monitor backend service connectivity and response times

12. **Documentation and Operations**:
    - Document proxy configuration and routing rules
    - Create operational procedures for service maintenance
    - Plan SSL certificate renewal and configuration updates

## Specific Configuration Elements:
- **Backend Configuration**: upstream {service_name}_backend {{ server 127.0.0.1:{upstream_port}; }}
- **SSL Settings**: {"SSL certificate automation with Let's Encrypt" if ssl_enabled else "HTTP-only configuration"}
- **Security Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **Performance**: Gzip compression, static file caching, connection pooling

Provide specific NGINX configuration blocks, SSL setup procedures, and validation steps for production-ready reverse proxy deployment."""


def ssl_certificate_management(
    hostname: str,
    domain_pattern: str = "*",
    certificate_provider: str = "letsencrypt",
    renewal_strategy: str = "automatic"
) -> str:
    """
    Manage SSL certificates across all proxy configurations.
    
    Args:
        hostname: Device hostname running SWAG proxy
        domain_pattern: Domain pattern to manage (*, specific domain, or wildcard)
        certificate_provider: Certificate provider (letsencrypt, custom, cloudflare)
        renewal_strategy: Renewal approach (automatic, manual, staged)
    """
    return f"""You are an SSL/TLS certificate management specialist managing certificates for {domain_pattern} domains on device: {hostname}

**Target Device**: {hostname}
**Domain Pattern**: {domain_pattern}
**Certificate Provider**: {certificate_provider}
**Renewal Strategy**: {renewal_strategy}

Please execute comprehensive SSL certificate management workflow:

## Phase 1: Certificate Inventory and Assessment
1. **Current Certificate Analysis**:
   - Use list_proxy_configs to inventory all proxy configurations with SSL
   - Identify certificates nearing expiration (within 30 days)
   - Assess certificate coverage and domain validation status

2. **Domain Validation and DNS Setup**:
   - Verify DNS records point to proxy server correctly
   - Validate domain ownership for {certificate_provider} validation
   - Check for wildcard certificate opportunities and consolidation

## Phase 2: Certificate Acquisition Strategy
3. **Acquisition Planning**:
   - Plan certificate requests based on {domain_pattern} requirements
   - Determine optimal certificate structure (individual vs wildcard vs SAN)
   - Coordinate with DNS and domain management systems

4. **Automation Configuration**:
   - Configure {certificate_provider} automation for {renewal_strategy} renewal
   - Set up DNS challenge validation if required
   - Implement certificate deployment automation

## Phase 3: Certificate Deployment
5. **Certificate Installation**:
   - Install new certificates with proper file permissions
   - Update SWAG configuration to reference new certificates
   - Verify certificate chain completeness and validity

6. **Configuration Updates**:
   - Update proxy configurations to use new certificates
   - Use sync_proxy_config to synchronize certificate references
   - Implement proper certificate rotation procedures

## Phase 4: Validation and Testing
7. **SSL Configuration Testing**:
   - Test SSL connectivity and certificate validation
   - Verify certificate chain and root CA validation
   - Test SSL Labs rating and security configuration

8. **Cross-Service Validation**:
   - Test all proxied services for SSL functionality
   - Verify mixed content issues are resolved
   - Test certificate validation across different clients

## Phase 5: Renewal and Maintenance
9. **Renewal Automation**:
   - Configure automatic renewal 30 days before expiration
   - Implement renewal success/failure notifications
   - Set up rollback procedures for failed renewals

10. **Monitoring and Alerting**:
    - Monitor certificate expiration dates and validity
    - Set up alerts for renewal failures or validation issues
    - Track certificate usage and performance impact

## Phase 6: Security and Compliance
11. **Security Hardening**:
    - Implement HSTS with appropriate max-age settings
    - Configure certificate transparency monitoring
    - Enable OCSP stapling for performance optimization

12. **Compliance and Documentation**:
    - Document certificate management procedures
    - Maintain certificate inventory and renewal schedules
    - Create incident response procedures for certificate issues

## Certificate Management Tasks:
- **Acquisition**: Domain validation, certificate requests, and installation
- **Renewal**: Automated renewal processes and deployment procedures
- **Monitoring**: Expiration tracking, validation monitoring, and alerting
- **Security**: Certificate pinning, transparency logs, and security headers

## Specific Provider Configuration for {certificate_provider}:
- Configure appropriate validation methods and automation
- Set up provider-specific API credentials and permissions
- Implement provider-specific renewal and deployment procedures

Provide specific configuration files, automation scripts, and monitoring procedures for {renewal_strategy} certificate management with {certificate_provider} provider."""


def proxy_performance_optimization(
    hostname: str,
    optimization_focus: str = "latency",
    traffic_pattern: str = "mixed"
) -> str:
    """
    Optimize reverse proxy performance for specific traffic patterns and goals.
    
    Args:
        hostname: Device hostname running SWAG proxy
        optimization_focus: Optimization target (latency, throughput, concurrent_connections)
        traffic_pattern: Traffic characteristics (static, dynamic, api, mixed)
    """
    return f"""You are a reverse proxy performance engineer optimizing SWAG proxy on device: {hostname} for {optimization_focus} with {traffic_pattern} traffic patterns

**Target Device**: {hostname}
**Optimization Focus**: {optimization_focus}
**Traffic Pattern**: {traffic_pattern}

Please execute comprehensive proxy performance optimization workflow:

## Phase 1: Performance Baseline and Analysis
1. **Current Performance Assessment**:
   - Use get_proxy_config_summary to analyze current proxy configuration
   - Use get_container_stats for SWAG container resource utilization
   - Establish baseline metrics for response times, throughput, and error rates

2. **Traffic Pattern Analysis**:
   - Analyze access logs for request patterns and resource utilization
   - Identify hot paths and resource-intensive endpoints
   - Assess cache hit ratios and static vs dynamic content distribution

## Phase 2: Configuration Optimization
3. **Core NGINX Tuning**:
   - Optimize worker processes and connections for available CPU cores
   - Configure appropriate buffer sizes for {traffic_pattern} workloads
   - Tune keepalive settings and connection pooling

4. **Caching Strategy Implementation**:
   - Configure proxy caching for static content and API responses
   - Implement intelligent cache keys and invalidation strategies
   - Set up browser caching headers and CDN integration

## Phase 3: Connection and Resource Management
5. **Connection Optimization**:
   - Configure upstream connection pooling and keepalive
   - Optimize proxy buffer sizes and timeouts for {optimization_focus}
   - Implement connection rate limiting and queuing strategies

6. **Resource Allocation**:
   - Optimize SWAG container resource limits and requests
   - Configure memory allocation for proxy buffers and caches
   - Tune worker process priority and CPU affinity

## Phase 4: Advanced Performance Features
7. **Compression and Content Optimization**:
   - Configure gzip compression with appropriate levels and types
   - Implement Brotli compression for modern browsers
   - Set up content minification and optimization

8. **Load Balancing and Failover**:
   - Configure optimal load balancing algorithms for backend services
   - Implement health checks and automatic failover
   - Set up circuit breaker patterns for backend protection

## Phase 5: Security Performance Balance
9. **SSL/TLS Optimization**:
   - Configure SSL session caching and resumption
   - Optimize cipher suites for performance and security balance
   - Implement OCSP stapling and SSL optimization

10. **Security Feature Tuning**:
    - Balance rate limiting with legitimate traffic patterns
    - Optimize security header processing overhead
    - Configure efficient DDoS protection without impacting performance

## Phase 6: Monitoring and Continuous Optimization
11. **Performance Monitoring**:
    - Set up detailed performance metrics and dashboards
    - Configure alerting for performance degradation
    - Implement automated performance testing and validation

12. **Continuous Improvement**:
    - Schedule regular performance reviews and optimization cycles
    - Monitor traffic pattern evolution and adapt configurations
    - Plan capacity scaling and infrastructure improvements

## Specific Optimizations for {optimization_focus}:

### Latency Optimization:
- Minimize proxy buffering and enable streaming
- Optimize DNS resolution and upstream connections
- Configure aggressive caching for cacheable content

### Throughput Optimization:  
- Maximize worker processes and connections
- Optimize buffer sizes for high-volume transfers
- Configure efficient load balancing algorithms

### Concurrent Connections:
- Tune connection limits and queuing strategies
- Optimize memory usage per connection
- Configure efficient event handling and I/O multiplexing

## Performance Targets for {traffic_pattern} Traffic:
- Define specific latency, throughput, and concurrency targets
- Establish performance benchmarks and testing procedures
- Create performance regression detection and alerting

Provide specific NGINX configuration optimizations, resource allocation recommendations, and performance validation procedures optimized for {optimization_focus} with {traffic_pattern} traffic characteristics."""


def proxy_security_hardening(
    hostname: str,
    security_level: str = "production",
    compliance_requirements: str = "general"
) -> str:
    """
    Implement comprehensive security hardening for reverse proxy infrastructure.
    
    Args:
        hostname: Device hostname running SWAG proxy
        security_level: Security profile (development, staging, production, high_security)
        compliance_requirements: Compliance needs (general, pci_dss, hipaa, sox)
    """
    return f"""You are a security specialist implementing {security_level} level security hardening for SWAG reverse proxy on device: {hostname}

**Target Device**: {hostname}
**Security Level**: {security_level}
**Compliance Requirements**: {compliance_requirements}

Please execute comprehensive proxy security hardening workflow:

## Phase 1: Security Assessment and Planning
1. **Current Security Posture Analysis**:
   - Use list_proxy_configs to inventory all proxy configurations and security settings
   - Assess current SSL/TLS configuration and certificate security
   - Evaluate existing security headers and protection mechanisms

2. **Threat Model and Risk Assessment**:
   - Identify potential attack vectors for reverse proxy infrastructure
   - Assess risks specific to proxied applications and data sensitivity
   - Plan security controls based on {compliance_requirements} requirements

## Phase 2: SSL/TLS Hardening
3. **Certificate and Encryption Hardening**:
   - Configure strong cipher suites and eliminate weak encryption
   - Implement perfect forward secrecy and modern TLS protocols
   - Set up certificate transparency monitoring and validation

4. **SSL Configuration Security**:
   - Configure HSTS with appropriate max-age and includeSubDomains settings
   - Implement HPKP (HTTP Public Key Pinning) where appropriate
   - Set up SSL session security and anti-replay protection

## Phase 3: Request Processing Security
5. **Input Validation and Sanitization**:
   - Configure request size limits and upload restrictions
   - Implement header validation and sanitization rules
   - Set up protection against malformed requests and protocol attacks

6. **Rate Limiting and DDoS Protection**:
   - Configure intelligent rate limiting based on IP, endpoint, and user patterns
   - Implement progressive penalties and temporary blocking
   - Set up geolocation-based access controls where appropriate

## Phase 4: Security Headers and Policies
7. **Security Header Implementation**:
   - Configure comprehensive Content Security Policy (CSP) headers
   - Implement X-Frame-Options, X-Content-Type-Options, and referrer policies
   - Set up feature policy and permissions policy headers

8. **Cross-Origin and CORS Security**:
   - Configure strict CORS policies for API endpoints
   - Implement proper cross-origin isolation for sensitive applications
   - Set up SameSite cookie attributes and secure cookie handling

## Phase 5: Access Control and Authentication
9. **Access Control Implementation**:
   - Configure IP whitelisting/blacklisting for sensitive endpoints
   - Implement geographic access controls and restrictions
   - Set up client certificate authentication where required

10. **Authentication Integration**:
    - Configure OAuth2/OIDC integration for centralized authentication
    - Implement proper session management and timeout policies
    - Set up multi-factor authentication support for administrative access

## Phase 6: Monitoring and Incident Response
11. **Security Monitoring**:
    - Configure comprehensive security logging and audit trails
    - Set up intrusion detection and suspicious activity monitoring
    - Implement automated threat detection and response procedures

12. **Incident Response Preparation**:
    - Create security incident response procedures
    - Set up automated blocking and mitigation capabilities
    - Document escalation procedures and communication plans

## Phase 7: Compliance and Validation
13. **Compliance Configuration**:
    - Implement {compliance_requirements} specific security requirements
    - Configure audit logging and retention policies
    - Set up compliance monitoring and reporting procedures

14. **Security Testing and Validation**:
    - Perform security scanning and penetration testing
    - Validate SSL configuration with security testing tools
    - Test security controls and incident response procedures

## Security Controls by Level:

### {security_level} Level Controls:
- Configure appropriate security headers and policies
- Implement rate limiting and access controls suitable for environment
- Set up monitoring and logging appropriate for security requirements

### Compliance-Specific Controls for {compliance_requirements}:
- Implement regulatory-specific security requirements
- Configure audit logging and data protection measures
- Set up compliance monitoring and reporting procedures

## Security Validation and Testing:
- SSL Labs A+ rating achievement and maintenance
- OWASP ZAP security testing and vulnerability assessment
- Regular security configuration reviews and updates

Provide specific security configurations, validation procedures, and compliance checklists optimized for {security_level} security level with {compliance_requirements} compliance requirements."""