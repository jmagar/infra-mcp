# Overview  
The Infrastructure Management MCP (Model Context Protocol) Server is a centralized monitoring and management system for self-hosted infrastructure environments. It solves the problem of fragmented visibility across multiple devices running containerized services by providing a unified interface to monitor containers, system resources, storage health, and service dependencies across heterogeneous Linux environments connected via Tailscale.

The primary user is a technical individual managing a complex self-hosted infrastructure consisting of multiple Unraid servers, Ubuntu VMs/physical machines, and various containerized services. The system provides real-time monitoring capabilities with historical data fallbacks, enabling both reactive troubleshooting and proactive infrastructure management.

# Core Features  

## Container Management
- **Container Discovery**: Automatically discover and list all running containers across all devices
- **Service Details**: Retrieve container IPs, exposed ports, volume mounts, and resource usage
- **Compose Integration**: Extract service configurations and dependencies via Docker API container inspection and labels
- **Status Monitoring**: Real-time container health and status tracking

## System Resource Monitoring
- **Resource Usage**: Track CPU, memory, and storage utilization across all devices
- **Drive Health**: Monitor SMART data and disk health metrics for early failure detection
- **ZFS Management**: Monitor ZFS pool health, scrub status, and dataset information
- **VM Oversight**: Track virtual machine status and resource allocation

## Data Persistence & Backup Monitoring
- **Volume Mapping**: Track all persistent data locations for containers and services
- **Snapshot Integrity**: Verify ZFS snapshot schedules and integrity checks
- **Backup Status**: Monitor backup job completion across different backup strategies (ZFS, rsync, restic)

## Logging & Diagnostics
- **System Logs**: Access and search system logs (syslog) across all devices
- **Container Logs**: Retrieve and stream Docker container logs
- **Log Aggregation**: Centralized log searching and filtering capabilities

## Network & Dependency Mapping
- **Service Dependencies**: Extract inter-service dependencies from Docker container labels and network configuration
- **Network Topology**: Discover container networking, port mappings, and service communication patterns via Docker API
- **Update Management**: Track available updates for containers, images, and system packages

## Real-time Data Streaming
- **WebSocket API**: Live streaming of metrics, logs, and status changes to external applications
- **MCP Tool Behavior**: Always fetch real-time data when devices are online, fall back to cached data when offline
- **Intelligent Polling**: Background data collection for historical storage and WebSocket streaming

# User Experience  

## User Personas
**Primary User**: Infrastructure Administrator
- Technical background with Linux/Docker expertise
- Manages 5-10 devices with 20+ containerized services
- Needs quick troubleshooting capabilities and overview dashboards
- Values automation and proactive monitoring

## Key User Flows
1. **Infrastructure Overview**: Single dashboard showing health of all devices and services
2. **Container Troubleshooting**: Drill down from service status to logs and resource usage
3. **Capacity Planning**: Review historical resource trends across devices
4. **Backup Verification**: Check backup status and snapshot integrity across all systems
5. **Update Management**: Identify outdated containers and plan maintenance windows

## FastAPI + MCP Integration Architecture
- **LLM-Friendly API Design**: Unified application serving both REST API (`/api/*`) and MCP server (`/mcp`) endpoints from a single codebase
- **Dual Interface Benefits**: Traditional programmatic access via REST API alongside natural language infrastructure management via MCP tools
- **Auto-Conversion + Custom Tools**: FastAPI endpoints automatically converted to MCP tools using `FastMCP.from_fastapi()`, enhanced with purpose-built LLM-optimized tools for complex infrastructure analysis
- **Streamable HTTP Transport**: Production-ready MCP server supporting multiple simultaneous client connections with session management and connection resumption
- **Real-time Data Access**: MCP tools fetch live data when devices are online, with intelligent fallback to cached data when offline
- **Advanced MCP Features**: Context management for progress reporting, user elicitation for interactive operations, JWT authentication, custom middleware for logging and rate limiting
- **Complete Implementation Guide**: Detailed setup instructions and examples available in @FASTAPI-FASTMCP-STREAMABLE-HTTP-SETUP.md
- **Production-Ready Tools**: 17 comprehensive MCP tools documented in @TOOLS.md covering container management, system monitoring, ZFS management, and network topology
- **Comprehensive Data Schemas**: Full type definitions in @SCHEMAS.md including API responses, database structure, WebSocket messages, and Pydantic models for FastAPI integration
- **Complete API Documentation**: Full reference for all three interfaces (REST, MCP, WebSocket) with examples and implementation patterns in @API.md

# Technical Architecture  

## System Components
**Unified FastAPI + MCP Server Architecture**:
- **LLM-Friendly API Pattern**: Single application serving both traditional REST endpoints and optimized MCP interface from the same codebase
- **FastAPI REST API**: Traditional HTTP endpoints for programmatic access (`/api/*`)
- **Auto-Generated MCP Tools**: FastAPI endpoints automatically converted to MCP tools using `FastMCP.from_fastapi()`
- **Purpose-Built MCP Tools**: Custom LLM-optimized tools for enhanced infrastructure analysis and troubleshooting
- **Streamable HTTP Transport**: MCP server accessible at `/mcp` endpoint with support for multiple simultaneous client connections
- **PostgreSQL + TimescaleDB**: Optimized time-series data storage for metrics and historical analysis
- **Background Polling Engine**: Configurable intervals for data collection with real-time WebSocket streaming
- **Device Registry & SSH Management**: Centralized device inventory with secure SSH-based command execution
- **JSON Schema Validation**: Consistent data formats across REST API and MCP tool responses

**Data Collection Layer**:
- SSH-based command execution across Tailscale network
- Docker CLI integration for container management via SSH
- System command wrappers (df, free, iostat, smartctl, zpool)
- Error handling and retry logic for unreliable network conditions

## Modular Architecture Principles
**Code Organization**:
- **Small, Focused Modules**: Keep all code files under 500 lines when possible
- **Single Responsibility**: Each module should handle one specific concern
- **Loose Coupling**: Minimize dependencies between modules to enable easy extension
- **Plugin-Based Tools**: Each MCP tool should be independently implementable and testable
- **Layered Design**: Clear separation between data collection, business logic, and presentation layers

**Extensibility Design**:
- **Tool Registration System**: New MCP tools can be added without modifying core server code
- **Device Type Adapters**: Abstract device-specific commands behind pluggable interfaces
- **Data Source Abstraction**: Enable easy addition of new data collection methods
- **Schema Evolution**: Database and API schemas designed for backward-compatible extension

## Data Models
```typescript
interface Device {
  id: string;
  hostname: string;
  ip_address: string;
  ssh_user: string;
  device_type: "unraid" | "ubuntu_vm" | "ubuntu_physical";
  last_seen: timestamp;
  status: "online" | "offline" | "unreachable";
}

interface Container {
  id: string;
  name: string;
  device_id: string;
  image: string;
  status: "running" | "stopped" | "paused";
  ports: Array<{host: number, container: number, protocol: string}>;
  volumes: Array<{host_path: string, container_path: string}>;
  labels: Record<string, string>;
  networks: string[];
  dependencies: string[];
}

interface SystemMetrics {
  device_id: string;
  timestamp: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: Array<{mount: string, used_percent: number}>;
  load_average: [number, number, number];
}

interface DriveHealth {
  device_id: string;
  drive_path: string;
  model: string;
  smart_status: "PASSED" | "FAILED" | "UNKNOWN";
  temperature: number;
  power_on_hours: number;
  reallocated_sectors: number;
}
```

## API Architecture Overview

The Infrastructure Management system provides **three complementary interfaces** serving different integration patterns:

### 1. REST API (`/api/*`)
- **Traditional HTTP endpoints** for direct programmatic integration
- **OpenAPI documentation** with automatic validation and type safety
- **API key authentication** for secure external access
- **Resource-based URLs** following REST conventions (`GET /api/devices`, `POST /api/containers/{id}/restart`)
- **JSON responses** with consistent error handling and status codes

### 2. MCP Interface (`/mcp`)
- **LLM-optimized tools** for natural language infrastructure management
- **Auto-generated from FastAPI** using `FastMCP.from_fastapi()` for consistency
- **Purpose-built tools** for complex infrastructure analysis and troubleshooting
- **JWT bearer token authentication** with advanced features (context, resources, prompts)
- **Streamable HTTP transport** supporting multiple simultaneous client connections

### 3. WebSocket API (`/ws`)
- **Real-time streaming** of metrics, alerts, and status changes
- **Event subscription model** with filtering and rate limiting
- **JWT token authentication** via query parameter or header
- **Message-based protocol** for live monitoring and dashboard updates

### Unified Implementation Benefits
- **Single codebase** serving all three interfaces with shared business logic
- **Consistent data models** and schemas across all access patterns
- **Intelligent data access**: Real-time when devices online, cached fallback when offline
- **Comprehensive documentation**: Complete API reference available in @API.md

### Integration Capabilities
- **Docker CLI Integration**: Container management via SSH commands
- **SSH Command Execution**: System metrics, drive health, ZFS operations across Tailscale network
- **Background Polling**: Continuous data collection for historical storage and live streaming
- **External Notifications**: Gotify integration for alerts and status updates

## Infrastructure Requirements
- Central server (can run on any existing device)
- PostgreSQL 15+ with TimescaleDB extension (deployed via Docker)
- SSH key access to all monitored devices
- Tailscale network connectivity
- Python 3.11+ runtime environment (local development until server is fully operational)

# Development Roadmap  

## Phase 1: MVP Foundation
**Core Infrastructure**:
- Basic MCP server framework with WebSocket support
- Device registry and SSH connection management
- PostgreSQL + TimescaleDB setup with hypertables for time-series data
- Basic container discovery via Docker CLI

**Essential Tools**:
- `list_devices()` - Show all registered devices and their status
- `list_containers(device?, status?)` - Show running containers
- `get_container_details(device, container_name)` - Basic container information
- `get_system_metrics(device)` - CPU, memory, disk usage

## Phase 2: Monitoring & Health
**System Health Monitoring**:
- Drive health monitoring with SMART data
- ZFS pool status and health checks
- System resource tracking with historical storage
- Background polling engine with configurable intervals

**Additional Tools**:
- `get_drive_health(device, drive?)` - SMART data and drive status
- `get_zfs_status(device)` - Pool health and scrub information
- `get_zfs_snapshots(device, dataset?)` - Snapshot listing and integrity
- Historical data queries for trending analysis

## Phase 3: Logging & Diagnostics
**Log Management**:
- System log access and searching
- Docker container log streaming
- Log aggregation and filtering capabilities

**Diagnostic Tools**:
- `get_system_logs(device, service?, since?)` - Syslog access
- `get_container_logs(device, container_name, since?, tail?)` - Docker log streaming
- Real-time log tailing via WebSocket

## Phase 4: Advanced Features
**Service Management**:
- Docker container label inspection for service configuration and dependency mapping
- VM status monitoring
- Backup job monitoring and verification
- Update management and tracking

**Enhanced Tools**:
- `get_service_dependencies(device, container_name)` - Extract dependency mapping from Docker labels
- `get_vm_status(device)` - Virtual machine monitoring
- `get_backup_status(device, backup_type?)` - Backup job verification including non-ZFS
- `verify_zfs_integrity(device, dataset?)` - ZFS snapshot integrity verification
- `get_network_topology(device?)` - Docker networks and container connectivity
- `list_docker_networks(device)` - Network discovery
- `check_updates(device, package_type?)` - Available updates
- `get_device_info(device)` - Device type, capabilities, last seen

## Phase 5: Optimization & Polish
**Performance Enhancements**:
- Intelligent caching strategies
- Connection pooling and retry logic
- Data retention policies and cleanup
- Performance monitoring and optimization

**User Experience**:
- Advanced querying capabilities
- Custom alerting thresholds
- Export capabilities for historical data
- Enhanced error handling and user feedback

## Phase 6: Frontend Dashboard (Future)
**Web UI Development**:
- **Frontend Stack**: Vite + React 19 + TypeScript + TailwindCSS v4 + ShadCN UI
- **Real-time Dashboard**: Live infrastructure overview with WebSocket integration
- **Interactive Monitoring**: Device and container drill-down interfaces
- **Historical Analysis**: Charts and trends for capacity planning
- **Alert Management**: Custom threshold configuration and notification center

**Design Considerations**:
- **API-First Development**: All backend functionality exposed via clean REST/WebSocket APIs
- **Mobile-First Design**: Primary development focus on mobile/tablet interfaces with desktop as enhancement
- **Progressive Web App**: Installable PWA for native-like mobile experience
- **Touch-Optimized**: Interfaces designed for touch interaction and mobile workflows
- **Dark Mode Support**: Professional appearance for 24/7 monitoring environments
- **Component Architecture**: Reusable UI components for consistent experience across screen sizes

# Logical Dependency Chain

## Foundation First (Phase 1)
- **MCP Server Framework**: Must be built first as everything depends on it
- **Device Registry**: Required before any device communication
- **SSH Connection Management**: Needed for all data collection
- **Basic WebSocket API**: Essential for MCP protocol compliance

## Quick Wins for Visibility (Phase 1-2)
- **Container Discovery**: Provides immediate value and validates the approach
- **System Metrics**: Shows the system is working and collecting data
- **Basic Historical Storage**: Demonstrates data persistence capabilities
- **Health Monitoring**: Critical infrastructure visibility

## Build Upon Success (Phase 2-3)
- **Drive Health**: Builds on existing SSH command framework
- **ZFS Integration**: Leverages existing device communication patterns
- **Logging System**: Reuses SSH and Docker API patterns established earlier

## Advanced Capabilities (Phase 4-5)
- **Dependency Mapping**: Requires stable container discovery and Docker API label inspection
- **VM Monitoring**: Builds on established device communication patterns
- **Update Management**: Leverages existing package querying capabilities
- **Performance Optimization**: Can only be done after core functionality is stable

## Future Frontend Integration (Phase 6)
- **API Stabilization**: All backend APIs must be stable and well-documented before frontend development
- **WebSocket Streaming**: Real-time data streaming infrastructure enables live dashboard updates
- **Modular Backend**: Plugin-based architecture allows frontend to dynamically discover available tools and capabilities

Each phase should result in a working, deployable system that provides immediate value while building the foundation for subsequent features.

# Risks and Mitigations  

## Technical Challenges
**Risk**: SSH connection reliability across Tailscale network
**Mitigation**: Implement connection pooling, retry logic, and graceful degradation to cached data

**Risk**: Heterogeneous command variations across different Linux distributions
**Mitigation**: Abstract commands behind device-type-specific adapters, extensive testing across target environments

**Risk**: PostgreSQL complexity vs simpler embedded solutions
**Mitigation**: Use Docker for PostgreSQL + TimescaleDB deployment during development, full containerization after server is operational, leverage TimescaleDB's automatic partitioning and compression

## MVP Definition and Scope Creep
**Risk**: Over-engineering the initial implementation
**Mitigation**: Strict adherence to Phase 1 scope, resist adding features until MVP is stable and deployed

**Risk**: Complex dependency mapping overwhelming initial development
**Mitigation**: Start with simple Docker label inspection, iterate based on real-world usage patterns

## Resource Constraints
**Risk**: Development complexity of WebSocket + MCP integration
**Mitigation**: Use existing MCP server libraries, start with basic HTTP endpoints before WebSocket streaming

**Risk**: Time investment in database schema design
**Mitigation**: Use flexible JSON columns in SQLite initially, normalize schema as usage patterns emerge

**Risk**: SSH key management across multiple devices
**Mitigation**: Leverage existing SSH key setup, document clear setup procedures, implement connection testing tools

## Architecture and Maintainability
**Risk**: Monolithic code files becoming difficult to maintain and extend
**Mitigation**: Enforce 500-line file limit, implement modular plugin architecture, use dependency injection for loose coupling

**Risk**: Frontend/backend coupling preventing independent development
**Mitigation**: API-first design with comprehensive OpenAPI documentation, WebSocket protocol specification, maintain backward compatibility

# Appendix  

## Technical Specifications
**Supported Platforms**: Ubuntu 20.04+, Unraid 6.9+, Docker 20.10+
**Programming Language**: Python 3.11+ with asyncio for concurrent operations
**Package Manager**: UV (modern Python package manager) for dependency management
**Database**: PostgreSQL 15+ with TimescaleDB extension for time-series optimization
**MCP Transport**: Streamable-HTTP for MCP tool communication (implementation guide: [@fastapi-fastmcp-streamable-http-setup.md](fastapi-fastmcp-streamable-http-setup.md))
**Real-time Streaming**: WebSocket for external application integration
**Network Protocol**: SSH over Tailscale for device communication

## Research Findings
**MCP Protocol**: Well-established JSON-RPC based protocol with existing Python libraries
**Docker CLI**: Stable command-line interface with JSON output support
- Container labels provide compose service information (com.docker.compose.service, com.docker.compose.depends_on)
- `docker inspect` reveals detailed container configuration and networking
- `docker ps --format json` provides structured container listings
**ZFS Commands**: Consistent across platforms, JSON output available for most commands
**SMART Data**: Accessible via smartctl with JSON output format

## Performance Considerations
**Polling Intervals**: 30s for containers, 5min for system metrics, 1hr for drive health
**Data Retention**: 30 days for high-frequency metrics, 1 year for health checks
**Concurrent Connections**: Support for 10+ simultaneous device polling
**WebSocket Clients**: Design for 5+ concurrent external application connections
**MCP Tool Response**: Real-time data when devices online, <1s cached fallback when offline
