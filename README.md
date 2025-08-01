# Infrastructor

> **Infrastructure Management MCP Server with FastAPI Integration**  
> A comprehensive system for monitoring and managing Linux devices via SSH with LLM-friendly APIs

## 🚀 Features

### Core Infrastructure Management
- **Comprehensive Device Analysis**: Automated capability detection (Docker, ZFS, hardware, OS, virtualization)
- **SWAG Reverse Proxy Management**: Real-time configuration sync, template management, and service discovery
- **Enhanced Drive Monitoring**: SMART data collection, filesystem detection, I/O statistics, temperature monitoring
- **Container Management**: Docker discovery, log streaming, service dependency mapping
- **System Monitoring**: CPU, memory, disk usage, network statistics with time-series storage
- **ZFS Integration**: Pool health, snapshot management, scrub monitoring

### Architecture
- **Separated API Design**: Independent FastAPI REST API + MCP server for optimal performance
- **Real-time Synchronization**: Database storage with live file system access for fresh data
- **SSH-based Communication**: Secure device management over SSH with proper key authentication
- **TimescaleDB Integration**: Efficient time-series metrics storage with automatic retention
- **MCP Resources**: Direct file access via `swag://`, `infra://` URI schemes for LLM integration

## 📋 Requirements

- **Python**: 3.11+
- **Database**: PostgreSQL 15+ with TimescaleDB extension
- **Access**: SSH key access to monitored devices
- **Package Manager**: UV (recommended) or pip
- **Optional**: Docker for containerized database

## 🏗️ Architecture

### System Overview

```mermaid
graph TB
    subgraph "API Layer"
        A[FastAPI REST API<br/>Port 9101] --> B[/api/devices]
        A --> C[/api/containers] 
        A --> D[/api/proxy]
        A --> E[/health]
    end
    
    subgraph "MCP Layer"
        F[MCP Server<br/>HTTP 9102] --> G[17 Infrastructure Tools]
        F --> H[SWAG Resources swag://]
        F --> I[Device Resources infra://]
    end
    
    subgraph "Data Layer"
        J[PostgreSQL + TimescaleDB<br/>Port 9100] --> K[Device Registry]
        J --> L[Proxy Configurations]
        J --> M[System Metrics]
        J --> N[Change History]
    end
    
    subgraph "Infrastructure"
        O[Device 1: SSH] --> P[Docker Containers]
        O --> Q[System Metrics]
        O --> R[SWAG Configs]
        S[Device 2: SSH] --> T[ZFS Pools]
        S --> U[Hardware Info]
        S --> V[Log Files]
    end
    
    A --> J
    F --> A
    A --> O
    A --> S
```

### Port Allocation
- **PostgreSQL**: 9100 (Docker container)
- **FastAPI REST API**: 9101 (HTTP endpoints)
- **MCP Server**: 9102 (HTTP transport for Claude Code)
- **Development Scripts**: `./dev.sh` manages all services

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/jmagar/infra-mcp.git
cd infrastructor

# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your settings (database, API keys, etc.)
```

### 2. Database Setup

```bash
# Start PostgreSQL with TimescaleDB
docker compose up postgres -d

# Run database migrations
uv run alembic upgrade head

# Verify database health
curl http://localhost:9101/health
```

### 3. Development Server

```bash
# Start both API and MCP servers
./dev.sh start

# View logs from both servers
./dev.sh logs

# Stop all servers
./dev.sh stop
```

The development script manages:
- **FastAPI server** on port 9101 with auto-reload
- **MCP server** on port 9102 for Claude Code integration
- **Log rotation** with size management
- **Health monitoring** with startup verification

## 📁 Project Structure

```
infrastructor/
├── apps/backend/src/           # FastAPI application
│   ├── main.py                 # FastAPI app entry point
│   ├── api/                    # REST API endpoints
│   │   ├── devices.py          # Device management endpoints
│   │   ├── containers.py       # Container operations
│   │   ├── proxy.py            # SWAG proxy configuration
│   │   └── common.py           # Health checks, utilities
│   ├── mcp/                    # MCP server implementation
│   │   ├── server.py           # Main MCP server
│   │   ├── tools/              # 17 MCP tools
│   │   │   ├── device_analysis.py      # Comprehensive device analysis
│   │   │   ├── device_management.py    # Device registry operations
│   │   │   ├── container_management.py # Docker operations
│   │   │   ├── system_monitoring.py    # System metrics & drive stats
│   │   │   ├── proxy_management.py     # SWAG configuration tools
│   │   │   └── metrics_collection.py   # Historical data collection
│   │   └── resources/          # MCP resources (swag://, infra://)
│   │       └── proxy_configs.py        # Direct file access resources
│   ├── models/                 # Database models (SQLAlchemy)
│   ├── schemas/                # API schemas (Pydantic)
│   ├── services/               # Business logic
│   ├── core/                   # Configuration, database setup
│   └── utils/                  # SSH client, nginx parser
├── alembic/                    # Database migrations
├── init-scripts/               # TimescaleDB setup scripts
├── logs/                       # Application logs (auto-managed)
├── dev.sh                      # Development server management
├── docker-compose.yaml         # PostgreSQL setup
└── docs/                       # Documentation
    ├── PRD.md                  # Product requirements
    └── MONOREPO.md             # Development guidelines
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=9100
POSTGRES_DB=infrastructor
POSTGRES_USER=infrastructor
POSTGRES_PASSWORD=your_secure_password

# API Authentication
API_KEY=your-api-key-for-authentication

# Server Configuration
MCP_HOST=localhost
MCP_PORT=9102
DEBUG=true
ENVIRONMENT=development

# SSH Configuration (uses ~/.ssh/config by default)
SSH_CONNECTION_TIMEOUT=30
SSH_COMMAND_TIMEOUT=60
```

### Device Registration

**Automatic Discovery** (Recommended):
```bash
# Auto-register devices from your infrastructure
curl -X POST http://localhost:9101/api/devices \
  -H "Authorization: Bearer your-api-key-for-authentication" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "server1",
    "device_type": "server",
    "monitoring_enabled": true
  }'
```

**Device Analysis** (New Feature):
```bash
# Run comprehensive capability analysis
curl -X POST http://localhost:9101/api/devices/server1/analyze \
  -H "Authorization: Bearer your-api-key-for-authentication"
```

## 🛠️ API Interfaces

### 1. REST API (Port 9101)

**Core Endpoints:**
```bash
# Device Management
GET  /api/devices                    # List all devices
POST /api/devices                    # Register new device  
GET  /api/devices/{hostname}         # Get device details
POST /api/devices/{hostname}/analyze # Run device analysis

# Container Operations
GET  /api/containers/{device}               # List containers
GET  /api/containers/{device}/{name}       # Container details
GET  /api/containers/{device}/{name}/logs  # Container logs

# System Monitoring  
GET  /api/devices/{device}/metrics     # System metrics
GET  /api/devices/{device}/drives      # Drive health (SMART data)
GET  /api/devices/{device}/drives/stats # Enhanced drive statistics

# SWAG Proxy Management (New)
GET  /api/proxy/configs                     # List proxy configurations
GET  /api/proxy/configs/{service}          # Get specific config
GET  /api/proxy/templates/{type}           # Get templates (subdomain/subfolder)
GET  /api/proxy/samples                     # List sample configurations
POST /api/proxy/scan                       # Scan and sync configurations

# Health & Status
GET  /health                          # Application health check
```

**Enhanced Features:**
- **SMART Drive Data**: Power-on hours, temperature, wear leveling
- **Filesystem Detection**: ext4, xfs, btrfs, zfs, ntfs, vfat, exfat
- **Real-time Sync**: Live file system access with database caching
- **Comprehensive Analysis**: Hardware, OS, virtualization, service detection

### 2. MCP Interface (Port 9102)

**Claude Code Integration:**
```json
{
  "mcpServers": {
    "infra": {
      "command": "python",
      "args": ["apps/backend/src/mcp/server.py"],
      "cwd": "/path/to/infrastructor"
    }
  }
}
```

**Available Tools (17 total):**

**Device Management (4 tools):**
- `list_devices` - Device registry with filtering
- `add_device` - Register new devices  
- `edit_device` - Update device configuration
- `analyze_device` - **NEW**: Comprehensive capability analysis

**Container Management (3 tools):**
- `list_containers` - Docker container discovery
- `get_container_info` - Detailed container inspection
- `get_container_logs` - Log streaming with filtering

**System Monitoring (3 tools):**
- `get_system_info` - CPU, memory, disk, network metrics
- `get_drive_health` - SMART data and drive health
- `get_drives_stats` - **Enhanced**: I/O statistics, filesystem types
- `get_system_logs` - System log access and filtering

**SWAG Proxy Management (5 tools):**
- `list_proxy_configs` - Configuration discovery with sync status
- `get_proxy_config` - Real-time configuration content  
- `scan_proxy_configs` - Directory scanning and database sync
- `sync_proxy_config` - Individual configuration synchronization
- `get_proxy_config_summary` - Statistics and health overview

**MCP Resources:**
- `swag://configs` - List all SWAG configurations
- `swag://{service}` - Direct access to service configurations  
- `swag://templates/{type}` - Configuration templates
- `swag://samples/{name}` - Sample configurations
- `infra://devices` - Device registry overview
- `infra://{device}/status` - Real-time device status

## 📊 Development

### Development Workflow

```bash
# Start development environment
./dev.sh start

# Monitor logs in real-time  
./dev.sh logs

# Restart after code changes
./dev.sh restart

# Stop all services
./dev.sh stop
```

### Code Quality

```bash
# Type checking
uv run mypy apps/backend/src/

# Linting and formatting
uv run ruff check apps/backend/src/
uv run ruff format apps/backend/src/
```

### Database Operations

```bash
# Create migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
uv run alembic upgrade head

# Check migration status
uv run alembic current
```

### Testing

```bash
# Run comprehensive device analysis
curl -X POST "http://localhost:9101/api/devices/your-device/analyze" \
  -H "Authorization: Bearer your-api-key-for-authentication"

# Test SWAG configuration sync
curl -X POST "http://localhost:9101/api/proxy/scan?device=squirts" \
  -H "Authorization: Bearer your-api-key-for-authentication"
```

## 🔐 Security

- **SSH Key Authentication**: Uses existing SSH configuration and keys
- **API Key Authentication**: Bearer token authentication for REST endpoints
- **Secure Communication**: All device communication over SSH
- **No Credential Storage**: Credentials managed via SSH agent and environment variables
- **Permission Handling**: Graceful fallback when elevated permissions unavailable

## 🗺️ Roadmap

### ✅ Completed Features (Phase 1-2)
- [x] **Core MCP Server**: 17 tools with HTTP transport
- [x] **Device Registry**: CRUD operations with automatic discovery
- [x] **Container Management**: Docker integration with log streaming
- [x] **Enhanced Drive Monitoring**: SMART data, filesystem detection, I/O stats
- [x] **SWAG Proxy Management**: Real-time sync, templates, sample configurations
- [x] **Device Analysis Tool**: Comprehensive capability detection
- [x] **Database Integration**: TimescaleDB with efficient time-series storage
- [x] **Development Tools**: Automated server management with `./dev.sh`

### 🚧 Current Development (Phase 3)
- [ ] **System Log Integration**: Centralized log access and searching
- [ ] **Historical Metrics**: Long-term trend analysis and alerting
- [ ] **Performance Optimization**: Connection pooling and caching strategies
- [ ] **Enhanced Error Handling**: Retry logic and graceful degradation

### 📅 Planned Features (Phase 4-5)
- [ ] **Web Dashboard**: React-based monitoring interface
- [ ] **WebSocket Streaming**: Real-time data feeds for dashboards
- [ ] **Advanced Analytics**: Service dependency mapping and health scoring
- [ ] **Backup Integration**: Automated backup verification and management
- [ ] **Mobile Support**: Progressive web app with responsive design

## 📚 Documentation

- **[docs/PRD.md](docs/PRD.md)** - Product Requirements Document with technical architecture
- **[docs/MONOREPO.md](docs/MONOREPO.md)** - Project structure and development patterns  
- **[CLAUDE.md](CLAUDE.md)** - Development guide and Claude Code integration
- **API Documentation** - OpenAPI docs available at `/docs` when server is running

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feat/amazing-feature`)
3. **Develop** following the existing patterns in `MONOREPO.md`
4. **Test** using the development tools (`./dev.sh`)
5. **Commit** with descriptive messages
6. **Push** and create a Pull Request

### Development Guidelines
- Follow the monorepo structure with clear separation of concerns
- Write comprehensive tests for new MCP tools
- Use proper type hints and error handling
- Document new features with examples
- Test against real infrastructure devices

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework for APIs
- **[FastMCP](https://github.com/jlowin/fastmcp)** - Model Context Protocol server integration  
- **[TimescaleDB](https://www.timescale.com/)** - Time-series database for metrics
- **[UV](https://github.com/astral-sh/uv)** - Fast Python package manager
- **[Claude Code](https://claude.ai/code)** - AI-powered development assistance

---

**Status**: 🚀 **Production Ready** | **Version**: 2.0.0 | **Python**: 3.11+ | **MCP Tools**: 17

**Quick Start**: `./dev.sh start` → **API**: http://localhost:9101/docs → **Health**: http://localhost:9101/health