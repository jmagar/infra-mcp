# MCP (Model Context Protocol) Module - Infrastructor Project

This directory contains the comprehensive MCP server implementation for the infrastructor project, providing extensive infrastructure management capabilities through 27 tools, 6 resource categories, and 4 analysis prompts.

## 🏛️ Architecture Overview

### MCP Server Design
- **Independent HTTP Server**: Runs on port 9102, separate from FastAPI (port 9101)
- **HTTP Client Pattern**: All MCP operations make authenticated HTTP calls to REST API
- **No Code Duplication**: Eliminates SSH/database logic duplication between MCP and REST
- **Bearer Token Authentication**: Consistent auth flow using API_KEY environment variable
- **Real-time Data**: Direct file system access combined with database synchronization

### Core Components
```
src/mcp/
├── server.py              # Main MCP server with FastMCP framework
├── tools/                 # 12 tool modules across infrastructure domains
├── resources/             # 6 resource categories with URI-based access
├── prompts/               # 4 analysis prompts for infrastructure expertise
├── agents/                # (Reserved for future agent implementations)
└── commands/              # (Reserved for future command extensions)
```

## 🛠️ Tool Categories (27 Tools)

### 1. Container Management Tools (9 tools)
**File**: `tools/container_management.py` (logic embedded in server.py)
- `list_containers` - List Docker containers with filtering
- `get_container_info` - Detailed container inspection
- `get_container_logs` - Container log retrieval with filtering
- `start_container` / `stop_container` / `restart_container` - Container lifecycle
- `remove_container` - Container removal with volume options
- `get_container_stats` - Real-time resource usage statistics
- `execute_in_container` - Command execution inside containers

### 2. System Monitoring Tools (3 tools)
**Files**: `tools/system_monitoring.py`, `tools/monitoring.py`
- `get_drive_health` - S.M.A.R.T. drive health monitoring
- `get_drives_stats` - Drive usage and I/O performance metrics
- `get_device_logs` - System logs from journald/syslog

### 3. Device Management Tools (4 tools)
**Files**: `tools/device_management.py`, `tools/device_info.py`, `tools/device_import.py`
- `list_devices` - Infrastructure device registry listing
- `add_device` / `edit_device` / `remove_device` - Device CRUD operations
- `get_device_info` - Comprehensive device analysis (replaces analyze_device)
- `import_devices_from_ssh_config` - Bulk device import from SSH config

### 4. Proxy Management Tools (5 tools)
**File**: `tools/proxy_management.py`
- `list_proxy_configs` - SWAG reverse proxy configuration listing
- `get_proxy_config` - Individual proxy configuration retrieval
- `scan_proxy_configs` - Directory scanning and database sync
- `sync_proxy_config` - Real-time file-database synchronization
- `get_proxy_config_summary` - Statistics and overview

### 5. Docker Compose Deployment Tools (6 tools)
**File**: `tools/compose_deployment.py`
- `modify_compose_for_device` - Adapt compose files for target devices
- `deploy_compose_to_device` - Full deployment with directory creation
- `modify_and_deploy_compose` - Combined operation with sensible defaults
- `scan_device_ports` - Port conflict detection and recommendations
- `scan_docker_networks` - Network topology analysis
- `generate_proxy_config` - Automatic SWAG configuration generation

### 6. ZFS Management Tools (16 tools)
**File**: `tools/zfs_management.py`

#### Pool Management (2 tools)
- `list_zfs_pools` - ZFS pool enumeration
- `get_zfs_pool_status` - Detailed pool status and health

#### Dataset Management (2 tools)
- `list_zfs_datasets` - Dataset listing with pool filtering
- `get_zfs_dataset_properties` - Comprehensive dataset property inspection

#### Snapshot Management (6 tools)
- `list_zfs_snapshots` - Snapshot enumeration with dataset filtering
- `create_zfs_snapshot` - Snapshot creation with recursive options
- `clone_zfs_snapshot` - Snapshot cloning operations
- `send_zfs_snapshot` / `receive_zfs_snapshot` - Replication operations
- `diff_zfs_snapshots` - Snapshot comparison and diff analysis

#### Health and Monitoring (3 tools)
- `check_zfs_health` - Comprehensive ZFS health assessment
- `get_zfs_arc_stats` - ARC cache performance metrics
- `monitor_zfs_events` - ZFS event monitoring and error tracking

#### Analysis and Reporting (3 tools)
- `generate_zfs_report` - Comprehensive ZFS system report
- `analyze_snapshot_usage` - Snapshot space analysis with cleanup recommendations
- `optimize_zfs_settings` - Configuration optimization suggestions

## 📁 Resource Categories (6 Categories, 27+ URIs)

### 1. SWAG Proxy Resources (`swag://`)
**File**: `resources/proxy_configs.py`
- `swag://service_name` - Direct service configuration access
- `swag://configs` - Active configuration directory listing
- `swag://summary` - Proxy configuration statistics
- `swag://samples/` - Sample configuration directory
- `swag://samples/filename` - Individual sample files
- `swag://subdomain-template` / `swag://subfolder-template` - Configuration templates

**Features**:
- Real-time file content with database synchronization
- Nginx configuration parsing with structured output
- Multiple format support (raw, JSON, YAML)
- Template and sample file discovery
- Service auto-discovery with fallback patterns

### 2. Docker Compose Resources (`docker://`)
**File**: `resources/compose_configs.py`
- `docker://configs` - Global compose configuration listing
- `docker://{device}/stacks` - Device-specific stack enumeration
- `docker://{device}/{service}` - Individual service configurations

### 3. ZFS Resources (`zfs://`)
**File**: `resources/zfs_resources.py`
- `zfs://pools/{hostname}` - ZFS pool information
- `zfs://pools/{hostname}/{pool_name}` - Specific pool status
- `zfs://datasets/{hostname}` - Dataset enumeration
- `zfs://snapshots/{hostname}` - Snapshot listing
- `zfs://health/{hostname}` - ZFS health status

### 4. System Logs Resources (`logs://`)
**Embedded in**: `server.py`
- `logs://{hostname}` - System logs (journald/syslog)
- `logs://{hostname}/{container_name}` - Container-specific logs
- `logs://{hostname}/vms` - Libvirt daemon logs
- `logs://{hostname}/vms/{vm_name}` - Specific VM logs

### 5. Network Ports Resources (`ports://`)
**File**: `resources/ports_resources.py`
- `ports://{hostname}` - Network port analysis and process mapping

### 6. Infrastructure Resources (`infra://`)
**Embedded in**: `server.py`
- `infra://devices` - Device registry listing
- `infra://{device}/status` - Comprehensive device status with parallel data collection

## 🧠 Analysis Prompts (4 Prompts)

### Infrastructure Analysis Prompts
**File**: `prompts/device_analysis.py`

1. **`analyze_device_performance`**
   - Comprehensive performance analysis with metric focus
   - Resource utilization patterns and bottleneck identification
   - Optimization recommendations and monitoring thresholds

2. **`container_stack_analysis`**
   - Docker container ecosystem analysis
   - Service dependency mapping and resource optimization
   - Security assessment and scaling recommendations

3. **`infrastructure_health_check`**
   - Comprehensive device health assessment
   - Multi-domain evaluation (system, storage, network, security)
   - Health scoring (1-10) with prioritized action items

4. **`troubleshoot_system_issue`**
   - Systematic troubleshooting methodology
   - Root cause analysis with diagnostic command recommendations
   - Resolution procedures with prevention measures

### Troubleshooting Prompts
**File**: `prompts/troubleshooting.py`
- Additional specialized troubleshooting scenarios and methodologies

## 🔧 Development Patterns

### HTTP Client Architecture
```python
class APIClient:
    """Centralized HTTP client for FastAPI endpoints"""
    def __init__(self):
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        
        self.client = httpx.AsyncClient(
            base_url=API_BASE_URL, 
            timeout=httpx.Timeout(API_TIMEOUT), 
            headers=headers
        )
```

### Error Handling Pattern
```python
try:
    response = await api_client.client.get(f"/endpoint/{device}")
    response.raise_for_status()
    return response.json()
except httpx.HTTPError as e:
    logger.error(f"HTTP error: {e}")
    raise Exception(f"Failed to execute operation: {str(e)}") from e
```

### Resource URI Patterns
```python
# Service-specific access
swag://service_name

# Device-specific resources  
swag://{device}/directory
docker://{device}/stacks
zfs://pools/{hostname}

# Global resources
swag://configs
docker://configs
infra://devices
```

### Tool Registration Pattern
```python
# Individual tool registration
server.tool(
    name="tool_name",
    description="Tool description"
)(tool_function)

# Bulk registration (ZFS tools)
for tool_name, tool_config in ZFS_TOOLS.items():
    server.tool(
        name=tool_name, 
        description=tool_config["description"]
    )(tool_config["function"])
```

## 🔒 Security Patterns

### Input Validation
```python
def _validate_service_name(service_name: str) -> bool:
    """Validate service name for shell safety"""
    return bool(re.match(r"^[a-zA-Z0-9._-]+$", service_name))

def _validate_file_path(file_path: str) -> bool:
    """Validate file path for shell safety"""
    return bool(re.match(r"^[a-zA-Z0-9._/-]+$", file_path))
```

### SSH Command Safety
- All SSH commands use validation functions
- No direct user input in shell commands
- Parameterized command construction
- Timeout controls for all operations

### Authentication Flow
- Bearer token passed through all HTTP requests
- API key validation at MCP server startup
- Consistent authentication between MCP and REST API

## 📊 Real-time Data Integration

### File System Synchronization
```python
async def _get_real_time_file_info(device: str, file_path: str) -> dict:
    """Get real-time file metadata via SSH"""
    
async def _get_real_time_file_content(device: str, file_path: str) -> str:
    """Get real-time file content via SSH"""
```

### Database Integration
- Real-time file-database comparison
- Automatic sync status tracking
- Content hash verification
- Last modified timestamp comparison

## 🚀 MCP Server Lifecycle

### Initialization Sequence
1. **Environment Setup**: Load .env and configure paths
2. **Database Connection**: Initialize async database connection
3. **API Client Setup**: Configure HTTP client with authentication
4. **Tool Registration**: Register all 27 tools with FastMCP
5. **Resource Registration**: Register all 6 resource categories
6. **Prompt Registration**: Register 4 analysis prompts
7. **HTTP Server Start**: Listen on port 9102

### Runtime Operation
- **Stateless Operations**: Each tool call is independent
- **Connection Pooling**: Reuse HTTP client connections
- **Error Propagation**: Consistent error handling across all tools
- **Logging Integration**: Structured logging with correlation

### Shutdown Sequence
- **Graceful Shutdown**: Handle KeyboardInterrupt
- **Resource Cleanup**: Close HTTP client connections
- **Database Cleanup**: Close async database connections

## 🔧 Configuration Management

### Environment Variables
```bash
# API Configuration
API_KEY=your-api-key-for-authentication
API_BASE_URL=http://localhost:9101/api  # FastAPI base URL
API_TIMEOUT=120.0

# SWAG Configuration (via settings)
SWAG_DEVICE=your-swag-device
SWAG_CONFIG_DIR=/mnt/appdata/swag/nginx/proxy-confs

# SSH Configuration
SSH_CONNECTION_TIMEOUT=10
SSH_COMMAND_TIMEOUT=30
```

### Settings Integration
- Uses centralized settings from `core.config`
- SWAG device and directory configuration
- SSH timeout and connection settings
- Database connection parameters

## 🧪 Testing Patterns

### Tool Testing
```python
# Test individual tools via HTTP
curl -X POST http://localhost:9102/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "list_containers", "arguments": {"device": "hostname"}}}'
```

### Resource Testing
```python
# Test resource access
curl -X POST http://localhost:9102/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "resources/read", "params": {"uri": "swag://service_name"}}'
```

### Integration Testing
- All tools tested against live FastAPI endpoints
- Resource URIs validated with real file system data
- Error handling tested with invalid inputs
- Authentication tested with missing/invalid tokens

## 📈 Performance Considerations

### HTTP Client Optimization
- Connection reuse across tool calls
- Configurable timeout settings
- Async/await throughout for non-blocking operations
- Error retry logic where appropriate

### Resource Caching
- Real-time file access balanced with performance
- Database caching for frequently accessed configurations
- Parallel data collection for device status resources

### Memory Management
- Streaming large log outputs
- Efficient JSON serialization
- Connection pool limits
- Timeout controls prevent hanging operations

## 🔄 Future Extensions

### Agent Integration (`agents/`)
- Reserved directory for future MCP agent implementations
- Multi-step workflow automation
- Cross-device coordination agents

### Command Extensions (`commands/`)
- Reserved for complex command sequences
- Workflow automation commands
- Batch operation commands

### Additional Resources
- VM management resources (`vm://`)
- Network topology resources (`network://`)
- Security audit resources (`security://`)

---

## 🎯 Development Guidelines

### Adding New Tools
1. **Create tool function** with proper type hints and error handling
2. **Register in server.py** with descriptive name and documentation
3. **Follow HTTP client pattern** for API communication
4. **Add input validation** for security
5. **Include comprehensive logging** for debugging

### Adding New Resources
1. **Create resource module** in `resources/` directory
2. **Implement URI parsing** with proper validation
3. **Add real-time data access** where applicable
4. **Register resource handlers** in server.py
5. **Document URI patterns** and usage examples

### Adding New Prompts
1. **Create prompt function** in `prompts/` directory
2. **Include comprehensive instruction set** for analysis
3. **Specify required tools** for data collection
4. **Register prompt** in server.py
5. **Test with real infrastructure data**

This MCP module provides comprehensive infrastructure management capabilities through a well-architected, secure, and performant interface that eliminates code duplication while maintaining real-time data access and robust error handling.