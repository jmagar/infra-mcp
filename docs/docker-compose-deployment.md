# Docker Compose Deployment 🐳

This document provides comprehensive documentation for the Docker Compose deployment functionality in Infrastructor, which allows you to automatically modify and deploy docker-compose files to target devices with intelligent path updates, port conflict resolution, network configuration, and SWAG reverse proxy setup.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [REST API Endpoints](#rest-api-endpoints)
- [MCP Tools](#mcp-tools)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## 🎯 Overview

The Docker Compose deployment system addresses the challenge of deploying docker-compose configurations across heterogeneous infrastructure environments. Each target device may have different:

- **Appdata paths** - Different devices store application data in different locations
- **Port availability** - Ports that are free on one device may be occupied on another
- **Network configurations** - Docker networks vary between devices
- **Proxy requirements** - SWAG reverse proxy configurations need device-specific settings

This system automatically adapts docker-compose files for each target environment, ensuring successful deployments without manual configuration changes.

## 🏗️ Architecture

The Docker Compose deployment system follows Infrastructor's dual-server architecture:

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   MCP Tools     │───▶│   REST API      │───▶│   Service Layer │
│                 │    │   Endpoints     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │                 │    │                 │
                       │   PostgreSQL    │    │   SSH Client    │
                       │   Database      │    │   (via Tailscale)│
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
```

### Components

1. **REST API Layer** (`/api/compose/*`) - HTTP endpoints for web/API access
2. **MCP Tools Layer** - Command-line interface tools for Claude and other MCP clients
3. **Service Layer** (`ComposeDeploymentService`) - Core business logic and orchestration
4. **Database Layer** - Device configuration and deployment metadata storage
5. **SSH Communication** - Secure remote operations via Tailscale network

## ✨ Features

### 🗂️ Path Management
- **Automatic Path Updates**: Transforms volume paths to use device-specific appdata directories
- **Pattern Recognition**: Identifies appdata paths using configurable patterns
- **Fallback Handling**: Graceful handling of unknown path structures

### 🔌 Port Conflict Resolution  
- **Port Scanning**: Real-time scanning of system and Docker port usage
- **Smart Assignment**: Automatic assignment of available ports from configurable ranges
- **Conflict Prevention**: Avoids port conflicts with existing services

### 🌐 Network Configuration
- **Network Discovery**: Scans existing Docker networks on target devices
- **Smart Recommendations**: Suggests optimal networks based on usage patterns
- **Auto-Configuration**: Automatically configures services for appropriate networks

### 🔄 SWAG Proxy Integration
- **Auto-Generation**: Creates SWAG reverse proxy configurations for services
- **Template-Based**: Uses proven nginx configuration templates
- **Domain Management**: Handles subdomain and domain configuration

### 📦 Deployment Management
- **Backup & Safety**: Automatic backup of existing configurations
- **Directory Creation**: Ensures required directories exist on target devices
- **Service Lifecycle**: Optional image pulling, service stopping/starting
- **Status Monitoring**: Real-time monitoring of deployment progress

## 🌐 REST API Endpoints

Base URL: `http://localhost:9101/api/compose`

### POST `/modify`

Modify docker-compose content for deployment on target device.

**Request Body:**
```json
{
  "compose_content": "version: '3.8'\nservices:\n  web:\n    image: nginx:latest\n    ports:\n      - \"8080:80\"\n    volumes:\n      - \"./appdata/nginx:/usr/share/nginx/html:ro\"",
  "target_device": "homelab-server",
  "service_name": "web",
  "update_appdata_paths": true,
  "auto_assign_ports": true,
  "port_range_start": 8000,
  "port_range_end": 9000,
  "generate_proxy_configs": true,
  "base_domain": "homelab.local"
}
```

**Response:**
```json
{
  "success": true,
  "device": "homelab-server",
  "modified_compose": "# Modified docker-compose content...",
  "changes_applied": [
    "Updated web volume: ./appdata/nginx -> /mnt/appdata/nginx",
    "Assigned port 8080 to web (container port 80)",
    "Generated proxy config for web"
  ],
  "port_assignments": {
    "web": [{"host_port": 8080, "container_port": 80, "protocol": "tcp"}]
  },
  "proxy_configs": [
    {
      "service_name": "web",
      "domain": "web.homelab.local",
      "config_content": "# SWAG configuration..."
    }
  ],
  "execution_time_ms": 1250
}
```

### POST `/deploy`

Deploy docker-compose content to target device.

**Request Body:**
```json
{
  "device": "homelab-server",
  "compose_content": "# Modified docker-compose content...",
  "deployment_path": "/opt/stacks/web/docker-compose.yml",
  "start_services": true,
  "pull_images": true,
  "create_directories": true,
  "backup_existing": true
}
```

**Response:**
```json
{
  "success": true,
  "device": "homelab-server",
  "deployment_path": "/opt/stacks/web/docker-compose.yml",
  "compose_file_created": true,
  "backup_file_path": "/opt/stacks/web/docker-compose.yml.backup_20241202_143022",
  "containers_started": ["web_container"],
  "service_status": {"web": "running"},
  "execution_time_ms": 3400
}
```

### POST `/modify-and-deploy`

Convenience endpoint that combines modification and deployment in a single operation.

**Request Body:**
```json
{
  "compose_content": "# Original docker-compose content...",
  "target_device": "homelab-server",
  "update_appdata_paths": true,
  "auto_assign_ports": true,
  "generate_proxy_configs": true,
  "start_services": true,
  "pull_images": true
}
```

### POST `/scan-ports`

Scan for available ports on target device.

**Request Body:**
```json
{
  "device": "homelab-server",
  "port_range_start": 8000,
  "port_range_end": 9000
}
```

**Response:**
```json
{
  "device": "homelab-server",
  "available_ports": [8001, 8002, 8005, 8007, 8009],
  "used_ports": [8000, 8003, 8004, 8006, 8008],
  "docker_port_usage": {
    "8000": "nginx_container",
    "8003": "app_container"
  },
  "system_port_usage": {
    "8004": "python3 (PID: 1234)",
    "8006": "node (PID: 5678)"
  }
}
```

### POST `/scan-networks`

Scan Docker networks on target device.

**Request Body:**
```json
{
  "device": "homelab-server",
  "include_system_networks": false
}
```

**Response:**
```json
{
  "device": "homelab-server",
  "networks": [
    {
      "id": "abc123def456",
      "name": "traefik_default",
      "driver": "bridge",
      "scope": "local"
    }
  ],
  "recommended_network": "traefik_default",
  "containers_by_network": {
    "traefik_default": ["traefik", "whoami"]
  }
}
```

### GET `/download-modified/{device}`

Download modified docker-compose content as plain text without deploying.

**Query Parameters:**
- `compose_content`: Original docker-compose YAML content
- `service_name`: Optional specific service to modify
- `update_appdata_paths`: Whether to update volume paths
- `auto_assign_ports`: Whether to auto-assign ports

**Response:** Plain text docker-compose YAML content

### GET `/proxy-configs/{device}/{service_name}`

Generate SWAG proxy configuration for a specific service.

**Query Parameters:**
- `upstream_port`: Port where the service is running
- `domain`: Domain name for the service (optional)

**Response:**
```json
{
  "service_name": "web",
  "device": "homelab-server",
  "upstream_port": 8080,
  "domain": "web.homelab.local",
  "config_content": "# Generated SWAG configuration...",
  "filename": "web.subdomain.conf"
}
```

## 🛠️ MCP Tools

The Docker Compose deployment system provides 6 MCP tools for command-line and programmatic access:

### `modify_compose_for_device`

Modify docker-compose content for deployment on target device.

**Parameters:**
- `compose_content` (str): Original docker-compose.yml content
- `target_device` (str): Target device hostname  
- `service_name` (str, optional): Specific service to modify
- `update_appdata_paths` (bool, optional): Update volume paths to device appdata path
- `auto_assign_ports` (bool, optional): Automatically assign available ports
- `port_range_start` (int, optional): Start of port range for auto-assignment (default: 8000)
- `port_range_end` (int, optional): End of port range for auto-assignment (default: 9000)
- `custom_port_mappings` (dict, optional): Custom port mappings by service name
- `update_networks` (bool, optional): Configure Docker networks for device
- `default_network` (str, optional): Default network to use
- `generate_proxy_configs` (bool, optional): Generate SWAG proxy configurations
- `base_domain` (str, optional): Base domain for proxy configurations
- `custom_appdata_path` (str, optional): Override device default appdata path
- `deployment_path` (str, optional): Where to store the compose file on device

**Example:**
```python
result = await modify_compose_for_device(
    compose_content=compose_yaml,
    target_device="homelab-server",
    service_name="web",
    update_appdata_paths=True,
    auto_assign_ports=True,
    generate_proxy_configs=True,
    base_domain="homelab.local"
)
```

### `deploy_compose_to_device`

Deploy docker-compose content to target device.

**Parameters:**
- `device` (str): Target device hostname
- `compose_content` (str): Docker compose content to deploy
- `deployment_path` (str): Path where to store compose file on device
- `start_services` (bool, optional): Start services after deployment (default: True)
- `pull_images` (bool, optional): Pull latest images before starting (default: True)
- `recreate_containers` (bool, optional): Recreate containers even if config unchanged (default: False)
- `create_directories` (bool, optional): Create necessary directories (default: True)
- `backup_existing` (bool, optional): Backup existing compose file (default: True)
- `services_to_start` (list, optional): Specific services to start
- `services_to_stop` (list, optional): Services to stop before deployment

### `modify_and_deploy_compose`

Convenience tool that combines modification and deployment into a single operation.

**Parameters:**
- `compose_content` (str): Docker compose YAML content
- `target_device` (str): Target device hostname
- `service_name` (str, optional): Optional specific service to modify
- `update_appdata_paths` (bool, optional): Whether to update volume paths
- `auto_assign_ports` (bool, optional): Whether to auto-assign ports
- `generate_proxy_configs` (bool, optional): Whether to generate proxy configs
- `start_services` (bool, optional): Whether to start services after deployment
- `pull_images` (bool, optional): Whether to pull latest images

### `scan_device_ports`

Scan for available ports on target device.

**Parameters:**
- `device` (str): Device hostname to scan
- `port_range_start` (int, optional): Start of port range to scan (default: 8000)
- `port_range_end` (int, optional): End of port range to scan (default: 9000)
- `protocol` (str, optional): Protocol to scan (default: "tcp")
- `timeout` (int, optional): Timeout for port checks in seconds (default: 5)

### `scan_docker_networks`

Scan Docker networks on target device and provide configuration recommendations.

**Parameters:**
- `device` (str): Device hostname to scan
- `include_system_networks` (bool, optional): Include Docker system networks (default: False)

### `generate_proxy_config`

Generate SWAG reverse proxy configuration for a specific service.

**Parameters:**
- `service_name` (str): Service name for the proxy configuration
- `upstream_port` (int): Port where the service is running
- `device_hostname` (str): Target device hostname
- `domain` (str, optional): Domain name for the service

## 📝 Usage Examples

### Basic Docker Compose Modification

```python
# Original docker-compose.yml content
compose_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./appdata/nginx:/usr/share/nginx/html:ro
    networks:
      - web-network

networks:
  web-network:
    driver: bridge
"""

# Modify for target device
result = await modify_compose_for_device(
    compose_content=compose_content,
    target_device="homelab-server",
    update_appdata_paths=True,
    auto_assign_ports=True,
    generate_proxy_configs=True,
    base_domain="homelab.local"
)

print(f"Modified compose:\n{result['modified_compose']}")
```

### Complete Deployment Workflow

```python
# Step 1: Scan available ports
ports = await scan_device_ports(
    device="homelab-server",
    port_range_start=8000,
    port_range_end=9000
)
print(f"Available ports: {ports['available_ports']}")

# Step 2: Scan Docker networks
networks = await scan_docker_networks(
    device="homelab-server",
    include_system_networks=False
)
print(f"Recommended network: {networks['recommended_network']}")

# Step 3: Deploy with one command
deployment = await modify_and_deploy_compose(
    compose_content=compose_content,
    target_device="homelab-server",
    update_appdata_paths=True,
    auto_assign_ports=True,
    generate_proxy_configs=True,
    start_services=True,
    pull_images=True
)

print(f"Deployment successful: {deployment['overall_success']}")
print(f"Services started: {deployment['services_started']}")
```

### Custom Port Mappings

```python
# Deploy with specific port assignments
result = await modify_compose_for_device(
    compose_content=compose_content,
    target_device="homelab-server",
    auto_assign_ports=True,
    custom_port_mappings={
        "web": 8080,
        "api": 8081,
        "db": 5432
    },
    port_range_start=8000,
    port_range_end=9000
)
```

### Service-Specific Modifications

```python
# Modify only a specific service
result = await modify_compose_for_device(
    compose_content=compose_content,
    target_device="homelab-server",
    service_name="web",  # Only modify the 'web' service
    update_appdata_paths=True,
    auto_assign_ports=True
)
```

## ⚙️ Configuration

### Device Configuration

Each device in the PostgreSQL database can be configured with deployment-specific settings:

```sql
-- Example device configuration
INSERT INTO devices (
    hostname, 
    docker_appdata_path, 
    docker_compose_path,
    device_type,
    tags
) VALUES (
    'homelab-server',
    '/mnt/appdata',
    '/opt/stacks',
    'server',
    '{"environment": "production", "role": "docker-host"}'::jsonb
);
```

### Environment Variables

Configure the deployment system using environment variables:

```bash
# SSH Configuration
SSH_CONNECTION_TIMEOUT=10
SSH_COMMAND_TIMEOUT=30
SSH_KEY_PATH=~/.ssh/id_ed25519

# Port Scanning
DEFAULT_PORT_RANGE_START=8000
DEFAULT_PORT_RANGE_END=9000

# Deployment Paths
DEFAULT_APPDATA_PATH=/mnt/appdata
DEFAULT_COMPOSE_PATH=/opt/stacks
```

### Appdata Path Patterns

The system recognizes these patterns as appdata paths for automatic updating:

- `/appdata/`
- `/mnt/appdata/`
- `./appdata/`
- `../appdata/`

Custom patterns can be added by modifying the `_is_appdata_path()` method in the service class.

## 🚨 Error Handling

The Docker Compose deployment system provides comprehensive error handling:

### Common Error Types

1. **DeviceNotFoundError**: Target device not found in database
2. **ValidationError**: Invalid docker-compose YAML content
3. **SSHConnectionError**: Cannot connect to target device
4. **SSHCommandError**: Command execution failed on target device
5. **PortConflictError**: No available ports in specified range

### Error Response Format

```json
{
  "success": false,
  "error": "Device not found: unknown-device",
  "errors": [
    "Target device 'unknown-device' not found in device registry"
  ],
  "warnings": [],
  "execution_time_ms": 45
}
```

### Retry and Recovery

- **SSH Failures**: Automatic retry with exponential backoff
- **Port Conflicts**: Automatic fallback to next available port
- **Network Issues**: Graceful degradation to default networks
- **Deployment Failures**: Automatic rollback to backup configurations

## 📋 Best Practices

### 1. Device Preparation

Before deploying to a device, ensure:

```bash
# Register device in database
curl -X POST http://localhost:9101/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "homelab-server",
    "docker_appdata_path": "/mnt/appdata",
    "docker_compose_path": "/opt/stacks",
    "device_type": "server"
  }'

# Verify SSH connectivity
ssh homelab-server "docker version"
```

### 2. Port Range Planning

Configure non-overlapping port ranges for different device types:

```python
# Production servers: 8000-8999
# Development servers: 9000-9999  
# IoT devices: 10000-10999

port_ranges = {
    "production": {"start": 8000, "end": 8999},
    "development": {"start": 9000, "end": 9999},
    "iot": {"start": 10000, "end": 10999}
}
```

### 3. Network Organization

Use consistent network naming across devices:

```yaml
# Standard network names
networks:
  traefik_default:    # For web services
    external: true
  database_internal:  # For database connections
    external: true
  monitoring_net:     # For monitoring stack
    external: true
```

### 4. Backup Strategy

Always enable backups for production deployments:

```python
# Production deployment with safety measures
result = await deploy_compose_to_device(
    device="prod-server",
    compose_content=modified_compose,
    deployment_path="/opt/stacks/app/docker-compose.yml",
    backup_existing=True,  # Always backup in production
    start_services=False,  # Manual service start for verification
    pull_images=True,      # Ensure latest images
    create_directories=True
)
```

### 5. Service Dependencies

Handle service dependencies properly:

```python
# Stop dependent services first
result = await deploy_compose_to_device(
    device="homelab-server",
    compose_content=compose_content,
    services_to_stop=["web", "api"],  # Stop in dependency order
    services_to_start=["db", "api", "web"],  # Start in dependency order
)
```

### 6. Monitoring and Alerting

Monitor deployment operations:

```python
# Check deployment success
if not result['success']:
    # Send alert to monitoring system
    send_alert(f"Deployment failed on {device}: {result['errors']}")

# Monitor service health after deployment
await asyncio.sleep(30)  # Wait for services to start
health_check = await get_container_info(device, "web_container")
```

---

## 🔗 Related Documentation

- [API Reference](../README.md#-api-endpoints)
- [MCP Tools Reference](../README.md#-mcp-tools)
- [Database Schema](../README.md#-database-schema)
- [Development Guide](../CLAUDE.md)

For more information or support, please refer to the main [README.md](../README.md) or open an issue on the project repository.