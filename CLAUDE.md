# Infrastructor Development Guide

> **Infrastructure Management MCP Server with FastAPI Integration**  
> A comprehensive system for monitoring and managing Linux devices via SSH with LLM-friendly APIs

## Project Overview

**Infrastructor** is an infrastructure monitoring system that provides both traditional REST APIs and optimized MCP (Model Context Protocol) interfaces for LLM interactions. The system monitors Docker containers, system metrics, drive health, and system logs across Linux environments.

### Core Architecture
- **FastAPI + FastMCP**: Separated REST API and MCP server using HTTP transport
- **PostgreSQL + TimescaleDB**: Time-series optimized database for metrics storage
- **SSH Communication**: Direct SSH communication for device operations
- **7 Production Tools**: Core infrastructure monitoring functionality

### Development Status
- **Phase 1**: Completed - Core MCP tools and FastAPI integration
- **Current Deployment**: PostgreSQL via Docker (port 9100), FastAPI runs locally (port 9101), MCP server independent
- **Architecture**: MCP server makes HTTP calls to FastAPI endpoints for consistency

## Quick Start Development

### 1. Environment Setup
```bash
# Install UV (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Start PostgreSQL + TimescaleDB
docker compose up postgres -d

# Copy environment template and configure
cp .env.example .env
# Edit .env with your configuration (ensure API_KEY is set)
```

### 2. Development Commands
```bash
# Development server with auto-reload
uv run uvicorn apps.backend.src.main:app --host 0.0.0.0 --port 9101 --reload

# MCP Server (separate process for Claude Code)
python mcp_server.py

# Type checking
uv run mypy apps/backend/src/

# Linting and formatting
uv run ruff check apps/backend/src/
uv run ruff format apps/backend/src/
```

## Key Technical Concepts

### Separated API Architecture
The system uses a clean separation between REST API and independent MCP server:

```python
# REST API (apps/backend/src/main.py)
app = FastAPI(title="Infrastructure Management API")

# Serves REST endpoints at /api/*
app.include_router(devices_router, prefix="/api/devices")
app.include_router(containers_router, prefix="/api/containers")

# MCP Server (mcp_server.py) - Independent HTTP client
class APIClient:
    def __init__(self):
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        self.client = httpx.AsyncClient(base_url="http://localhost:9101/api")
```

### SSH Communication Pattern
All device communication uses direct SSH:
```python
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple

async def execute_command(device: str, command: str) -> SSHResult:
    """Execute command on remote device via SSH"""
    return await execute_ssh_command_simple(device, command, timeout)
```

## File Structure & Navigation

### Core Documentation
- **README.md** - User-facing documentation and deployment guide
- **PRD.md** - Product Requirements Document with technical architecture
- **MONOREPO.md** - Project structure and development patterns
- **MCP_TOOLS_REFERENCE.md** - MCP tools reference
- **endpoint_test_results.md** - API testing results

### Configuration Files
- **pyproject.toml** - Python project config with dependencies
- **docker-compose.yaml** - PostgreSQL + TimescaleDB setup
- **.env.example** - Environment variables template
- **.mcp.json** - MCP server configuration for Claude Code

### Application Structure
```
infrastructor/
├── apps/backend/src/           # FastAPI application code
│   ├── main.py                 # FastAPI app entry point
│   ├── api/                    # REST API endpoints
│   │   ├── containers.py       # Container management endpoints
│   │   ├── devices.py          # Device management endpoints  
│   │   └── __init__.py         # API router configuration
│   ├── mcp/tools/              # MCP tools implementation
│   │   ├── container_management.py
│   │   ├── system_monitoring.py
│   │   ├── device_management.py
│   │   └── metrics_collection.py
│   ├── core/                   # Core utilities
│   │   ├── database.py         # Database models and connections
│   │   ├── config.py           # Configuration management
│   │   └── exceptions.py       # Custom exception classes
│   ├── utils/                  # Utility modules
│   │   └── ssh_client.py       # SSH communication utilities
│   ├── schemas/                # Pydantic models
│   ├── models/                 # Database models
│   └── services/               # Business logic services
├── mcp_server.py               # Standalone MCP server
├── init-scripts/               # Database initialization
│   ├── 01-schema.sql
│   ├── 02-hypertables.sql
│   ├── 03-policies.sql
│   └── 04-caggs.sql
└── packages/                   # Shared packages
    ├── shared-types/
    └── shared-utils/
```

## MCP Tools Overview

### Container Management (3 tools)
- `list_containers(device: string, all_containers?: boolean)` - List Docker containers on devices
- `get_container_info(device: string, container_name: string)` - Detailed container inspection
- `get_container_logs(device: string, container_name: string, tail?: number)` - Container log retrieval

### System Monitoring (3 tools)
- `get_system_info(device: string, include_processes?: boolean)` - CPU, memory, disk, network metrics
- `get_drive_health(device: string, drive?: string)` - S.M.A.R.T. drive health monitoring
- `get_system_logs(device: string, service?: string, lines?: number)` - System log analysis

### Device Management (1 tool)
- `list_devices()` - Device registry management

All tools are tested and verified working. Complete signatures available in MCP_TOOLS_REFERENCE.md.

## Development Workflow

### Current Architecture Pattern
1. **MCP Server**: Independent HTTP client that calls FastAPI endpoints
2. **FastAPI**: Handles REST endpoints and makes direct SSH calls to devices
3. **Authentication**: API key-based authentication between MCP server and FastAPI
4. **Error Handling**: Structured exceptions with proper parameter mapping

### Adding New MCP Tools
1. **Implement tool** in `apps/backend/src/mcp/tools/`
2. **Add FastAPI endpoint** in `apps/backend/src/api/`
3. **Register MCP tool** in `mcp_server.py` with HTTP client call
4. **Test locally** against live devices
5. **Update documentation** in MCP_TOOLS_REFERENCE.md

### Development Commands
```bash
# Start services
docker compose up postgres -d
uv run uvicorn apps.backend.src.main:app --host 0.0.0.0 --port 9101 --reload

# In separate terminal, start MCP server
python mcp_server.py

# Test via Claude Code MCP connection
# Configuration in .mcp.json
```

## Production Deployment

### Current Setup
```bash
# Database
docker compose up postgres -d  # Port 9100

# FastAPI REST API
uv run uvicorn apps.backend.src.main:app --host 0.0.0.0 --port 9101

# MCP Server (stdio for Claude Code)
python mcp_server.py
```

### Environment Configuration
- **API_KEY**: Authentication between MCP server and FastAPI (required)
- **Database**: PostgreSQL connection details (default: localhost:9100)
- **SSH**: Uses ~/.ssh/config for device connectivity
- **Logging**: Structured logging with timestamps

## Security Considerations

### SSH Security
- **SSH config-based authentication** using existing SSH keys
- **Connection timeouts** and proper error handling
- **Command parameterization** to prevent injection

### API Security
- **Bearer token authentication** between MCP server and FastAPI
- **Structured error handling** with proper exception classes
- **Request validation** with Pydantic models

## Database Operations

### TimescaleDB Management
```bash
# Connect to database
docker compose exec postgres psql -U postgres -d infrastructor

# Check hypertables
SELECT * FROM timescaledb_information.hypertables;

# Check retention policies
SELECT * FROM timescaledb_information.data_retention_policies;
```

### Schema Management
- **Schema files**: Located in `init-scripts/`
- **Migrations**: Currently manual via SQL files
- **Time-series data**: Optimized with TimescaleDB hypertables

## Claude Code Integration

### MCP Configuration (.mcp.json)
```json
{
  "mcpServers": {
    "infra": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/home/jmagar/code/infrastructor",
      "env": {
        "API_KEY": "your-api-key-for-authentication"
      }
    }
  }
}
```

### Usage
- **Transport**: HTTP on port 9102 (independent process)
- **Authentication**: API key in environment variable
- **Tools**: 7 verified tools for container and system monitoring
- **Error Handling**: Structured error responses with context

## Task Master AI Integration
Task Master AI development workflow commands and guidelines are available.
**Reference**: `.taskmaster/CLAUDE.md` for complete Task Master integration details.

---

**Note**: This documentation reflects the current verified state of the project. All mentioned files, tools, and functionality have been tested and confirmed working.