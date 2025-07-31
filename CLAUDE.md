# Infrastructor Development Guide

> **Infrastructure Management MCP Server with FastAPI Integration**  
> A comprehensive system for monitoring and managing Linux devices via SSH with LLM-friendly APIs

## Project Overview

**Infrastructor** is a production-ready infrastructure monitoring system that provides both traditional REST APIs and optimized MCP (Model Context Protocol) interfaces for LLM interactions. The system monitors Docker containers, system metrics, ZFS storage, network topology, and more across heterogeneous Linux environments.

### Core Architecture
- **FastAPI + FastMCP**: Unified REST API and MCP server using streamable HTTP transport
- **PostgreSQL + TimescaleDB**: Time-series optimized database for metrics storage
- **SSH Communication**: Secure device communication over Tailscale network
- **17 Production Tools**: Complete coverage of infrastructure monitoring needs

### Development Status
- **Phase 1**: In Progress - Core MCP tools and FastAPI integration
- **Current Deployment**: PostgreSQL via Docker (port 9100), app runs locally
- **Future**: Full containerized deployment with sequential ports (9100-9102)

## Quick Start Development

### 1. Environment Setup
```bash
# Install UV (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Start PostgreSQL + TimescaleDB
docker compose up postgres -d

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
```

### 2. Development Commands
```bash
# Development server with auto-reload
uv run uvicorn src.main:app --host 0.0.0.0 --port 9101 --reload

# Type checking
uv run mypy src/

# Linting and formatting
uv run ruff check src/
uv run ruff format src/

# Run tests
uv run pytest
```

## Key Technical Concepts

### Separated API Architecture
The system uses a clean separation between REST API and MCP server for optimal performance and maintainability:

```python
# REST API (apps/backend/src/main.py)
app = FastAPI(title="Infrastructure Management API")

@app.get("/api/devices")
async def list_devices(): pass

# Serves only REST endpoints at /api/*
app.include_router(api_router, prefix="/api")

# MCP Server (mcp_server.py) - Independent process
server = FastMCP(name="Infrastructure Management MCP Server")

@server.tool
async def analyze_infrastructure_health() -> dict:
    """Get comprehensive health overview optimized for LLM analysis"""
    return {"overall_status": "healthy", "summary": "All systems operational"}

# Runs via stdio transport for Claude Code integration
await server.run_stdio_async()
```

### Database Architecture
- **PostgreSQL 15+** for device registry and configuration
- **TimescaleDB** hypertables for time-series metrics with automatic partitioning
- **Continuous aggregates** for hourly/daily rollups and dashboard performance
- **Compression policies** (7 days) and retention policies (30-90 days)

### SSH Communication Pattern
All device communication uses SSH over Tailscale for security:
```python
import asyncssh

async def execute_command(device: str, command: str) -> str:
    """Execute command on remote device via SSH"""
    async with asyncssh.connect(
        host=device,
        username=ssh_user,
        client_keys=[ssh_key_path],
        known_hosts=None
    ) as conn:
        result = await conn.run(command)
        return result.stdout
```

## File Structure & Navigation

### Core Documentation
- API.md - Complete API reference for REST, MCP, and WebSocket interfaces
- SCHEMAS.md - Complete TypeScript/Pydantic schemas for all data structures
- TOOLS.md - All 17 MCP tools organized by category with descriptions
- FASTAPI-FASTMCP-STREAMABLE-HTTP-SETUP.md - Complete integration guide
- PRD.md - Product Requirements Document with technical architecture
- MONOREPO.md - Project structure and development patterns
- README.md - User-facing documentation and deployment guide

### Configuration Files
- pyproject.toml - Python project config with latest package versions
- docker-compose.yaml - Production-ready Docker setup
- Dockerfile - Container build (prepared for future use)
- .env.example - Environment variables template

### Application Structure
See MONOREPO.md for complete project structure. Key directories:

```
infrastructor/
├── apps/backend/src/           # FastAPI + MCP application code
│   ├── main.py                 # FastAPI app with MCP integration
│   ├── mcp/tools/              # 17 MCP tools implementation
│   ├── core/database.py        # PostgreSQL + TimescaleDB models
│   ├── utils/ssh_client.py     # SSH communication utilities
│   └── core/config.py          # Configuration management
├── init-scripts/               # Database initialization scripts
├── logs/                       # Application and PostgreSQL logs
└── packages/shared-types/      # Shared TypeScript schemas
```

## MCP Tools Overview

### Container Management (4 tools)
- `list_containers(device?: string, status?: string)` - List Docker containers across devices
- `get_container_details(device: string, container_name: string)` - Detailed container inspection
- `get_container_logs(device: string, container_name: string, since?: string, tail?: number)` - Container log retrieval
- `get_service_dependencies(device: string, container_name: string)` - Service dependency analysis

### System Monitoring (3 tools)
- `get_system_metrics(device: string)` - CPU, memory, disk, load averages
- `get_drive_health(device: string, drive?: string)` - S.M.A.R.T. drive health monitoring
- `get_system_logs(device: string, service?: string, since?: string)` - System log analysis

### ZFS Management (3 tools)
- `get_zfs_status(device: string)` - Pool health and scrub status
- `get_zfs_snapshots(device: string, dataset?: string)` - Snapshot management and analysis
- `verify_zfs_integrity(device: string, dataset?: string)` - Data integrity verification

### Network & Infrastructure (2 tools)
- `get_network_topology(device?: string)` - Cross-device network discovery
- `list_docker_networks(device: string)` - Docker network analysis

### Backup & Maintenance (2 tools)
- `get_backup_status(device: string, backup_type?: string)` - Multi-type backup verification
- `check_updates(device: string, package_type?: string)` - System and container update checking

### Utility (3 tools)
- `list_devices()` - Device registry management
- `get_device_info(device: string)` - Comprehensive device information
- `get_vm_status(device: string)` - Virtual machine monitoring

Complete tool signatures and response schemas: SCHEMAS.md

## Development Workflow

### Adding New MCP Tools
1. **Define schemas** in SCHEMAS.md with TypeScript interfaces
2. **Implement tool** in `apps/backend/src/mcp/tools/`
3. **Add Pydantic models** in `apps/backend/src/schemas/` for request validation
4. **Update TOOLS.md** with tool documentation
5. **Register tool** in MCP server configuration at `apps/backend/src/mcp/server.py`
6. **Test locally** against device registry
7. **Add database models** if tool requires data persistence

### Database Schema Changes
1. **Update schemas** in SCHEMAS.md with new SQL DDL
2. **Create Alembic migration**: `uv run alembic revision --autogenerate -m "description"`
3. **Review migration** and test against development database
4. **Apply migration**: `uv run alembic upgrade head`
5. **Update continuous aggregates** if needed for time-series data
6. **Update Pydantic models** in `apps/backend/src/schemas/` for request validation

### FastAPI Endpoint Development
1. **Add REST endpoint** to FastAPI app with OpenAPI documentation
2. **Create Pydantic models** for request/response validation
3. **Test endpoint** with automatic FastAPI docs at `/docs`
4. **Verify MCP conversion** using `FastMCP.from_fastapi()`
5. **Add purpose-built MCP tools** for LLM optimization if needed

## Testing Strategy

### Unit Testing
```bash
# Run all tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest apps/backend/tests/test_containers.py -v

# Run tests for specific tool
uv run pytest -k "test_list_containers" -v
```

### Integration Testing
- **SSH connectivity** testing against real devices
- **Database operations** with PostgreSQL + TimescaleDB
- **MCP protocol** testing with FastMCP client
- **WebSocket connections** for real-time streaming

### Performance Testing
- **Concurrent device polling** with asyncio throttling
- **Database query performance** with TimescaleDB continuous aggregates
- **Memory usage** monitoring for long-running processes

## Production Deployment

### Current Development Setup
```bash
# PostgreSQL via Docker
docker compose up postgres -d

# FastAPI REST API
uv run uvicorn apps.backend.src.main:app --host 0.0.0.0 --port 9101 --reload

# MCP Server (separate process for Claude Code)
python mcp_server.py
```

### Future Containerized Deployment
```bash
# Full production stack
docker compose up -d

# Sequential ports:
# 9100: PostgreSQL + TimescaleDB
# 9101: FastAPI REST API
# 9102: WebSocket real-time streaming (future)
# 9103: Frontend Dev Server (development only)
# MCP Server: Independent stdio process for Claude Code integration
```

### Environment Configuration
- **Database**: Connection details, pool configuration, retention policies
- **SSH**: Key paths, timeouts, retry configuration
- **Polling**: Device polling intervals, concurrent limits
- **Authentication**: JWT secrets, API keys, bearer tokens
- **Logging**: Structured logging with levels and rotation

## Monitoring & Observability

### Health Checks
- **Database connectivity** with connection pooling
- **SSH device accessibility** with timeout handling
- **API server status** with endpoint validation
- **TimescaleDB performance** with query metrics

### Logging Strategy
- **Structured logging** with JSON format for production
- **Device operation tracking** with correlation IDs
- **Performance metrics** for SSH operations and database queries
- **Error aggregation** with contextual information

### Metrics Collection
- **System metrics** stored in TimescaleDB hypertables
- **Application metrics** via FastAPI middleware
- **Database performance** monitoring with PostgreSQL stats
- **SSH operation latency** tracking across devices

## Security Considerations

### SSH Security
- **Ed25519 keys** for device authentication
- **Tailscale network** for encrypted communication
- **Connection timeouts** and retry limits
- **Command injection prevention** with parameterized execution

### API Security
- **JWT bearer tokens** for MCP server authentication
- **API key validation** for REST endpoints
- **CORS configuration** for web client access
- **Rate limiting** to prevent abuse

### Database Security
- **Connection encryption** with SSL/TLS
- **Credential management** via environment variables
- **Query parameterization** to prevent SQL injection
- **Access control** with database user permissions

## Performance Optimization

### Database Performance
- **TimescaleDB compression** for historical data
- **Continuous aggregates** for dashboard queries
- **Proper indexing** on time-series and device columns
- **Connection pooling** with SQLAlchemy async

### Concurrent Operations
- **Asyncio throttling** for device polling
- **Connection limits** to prevent SSH exhaustion
- **Batch operations** for multi-device queries
- **WebSocket streaming** for real-time updates

### Memory Management
- **Streaming responses** for large datasets
- **Connection cleanup** for SSH and database
- **Memory monitoring** with health check endpoints
- **Log rotation** to prevent disk space issues

## FastMCP Server Features

### Context Management
Provides advanced capabilities including logging, progress reporting, and user interaction:

```python
from fastmcp import FastMCP, Context

@mcp.tool
async def analyze_system_health(device: str, ctx: Context) -> dict:
    """Analyze system health with progress reporting and logging"""
    await ctx.info(f"Starting health analysis of {device}")
    
    # Report progress during long operations
    await ctx.report_progress(progress=0, total=100)
    
    await ctx.debug("Checking CPU metrics...")
    await ctx.report_progress(progress=25, total=100)
    
    await ctx.debug("Checking memory usage...")
    await ctx.report_progress(progress=50, total=100)
    
    await ctx.debug("Checking disk health...")
    await ctx.report_progress(progress=75, total=100)
    
    try:
        result = {"status": "healthy", "cpu": 45, "memory": 67}
        await ctx.info("Analysis completed successfully")
        await ctx.report_progress(progress=100, total=100)
        return result
    except Exception as e:
        await ctx.error(f"Analysis failed: {str(e)}")
        raise
```

### Resources and Prompts
Expose structured data and prompt templates to MCP clients:

```python
# Resource definitions for infrastructure data
@mcp.resource("config://infrastructure")
async def get_infrastructure_config() -> dict:
    """Expose infrastructure configuration"""
    return {
        "monitoring_interval": 30,
        "retention_days": 30,
        "alert_thresholds": {
            "cpu": 80,
            "memory": 85,
            "disk": 90
        }
    }

@mcp.resource("devices://{device_id}/status")
async def get_device_status(device_id: str) -> dict:
    """Get real-time device status"""
    return {
        "device_id": device_id,
        "status": "online",
        "last_seen": "2024-01-15T10:30:00Z",
        "uptime": "7 days, 3 hours"
    }

# Prompt templates for infrastructure queries
@mcp.prompt
def troubleshoot_device(device: str, issue: str) -> str:
    """Generate troubleshooting prompt for device issues"""
    return f"""
    Please help troubleshoot the following issue on device '{device}':
    
    Issue: {issue}
    
    Please provide:
    1. Immediate steps to diagnose the problem
    2. Common causes for this type of issue
    3. Recommended solutions
    4. Prevention strategies
    """
```

### User Elicitation for Interactive Tools
Enable tools to request additional information from users during execution:

```python
from fastmcp.elicitation import ask_user

@mcp.tool
async def deploy_container(image: str, ctx: Context) -> dict:
    """Deploy container with interactive configuration"""
    await ctx.info(f"Preparing to deploy {image}")
    
    # Ask user for deployment configuration
    config = await ask_user(
        ctx=ctx,
        prompt="Container deployment configuration needed:",
        response_type={
            "port": int,
            "replicas": int,
            "environment": str,
            "auto_restart": bool
        }
    )
    
    if config.action == "accept":
        await ctx.info(f"Deploying with config: {config.response}")
        return {
            "status": "deployed",
            "config": config.response,
            "container_id": "abc123"
        }
    else:
        await ctx.warning("Deployment cancelled by user")
        return {"status": "cancelled"}
```

### Authentication with Bearer Tokens
Secure MCP server with JWT bearer token authentication:

```python
from fastmcp.auth import BearerAuthProvider

# Configure JWT authentication
auth = BearerAuthProvider(
    jwks_uri="https://your-identity-provider.com/.well-known/jwks.json",
    issuer="https://your-identity-provider.com/",
    algorithm="RS256",
    audience="infrastructure-mcp-server"
)

# Create authenticated MCP server
mcp = FastMCP(
    name="Infrastructure Monitor",
    auth=auth
)

@mcp.tool
async def secure_operation(ctx: Context) -> dict:
    """Tool that requires authentication"""
    if hasattr(ctx, 'access_token'):
        client_id = ctx.access_token.client_id
        scopes = ctx.access_token.scopes
        await ctx.info(f"Authenticated client: {client_id} with scopes: {scopes}")
    
    return {"status": "authorized", "data": "sensitive information"}
```

### Middleware for Cross-Cutting Concerns
Add logging, rate limiting, and other cross-cutting functionality:

```python
from fastmcp.middleware import Middleware
import time
from datetime import datetime

class InfrastructureLoggingMiddleware(Middleware):
    """Custom middleware for infrastructure monitoring logging"""
    
    async def on_message(self, context, call_next):
        start_time = time.time()
        client_info = getattr(context, 'client_id', 'unknown')
        
        print(f"[{datetime.utcnow()}] Client {client_info} -> {context.method}")
        
        try:
            result = await call_next(context)
            execution_time = time.time() - start_time
            print(f"[{datetime.utcnow()}] {context.method} completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"[{datetime.utcnow()}] {context.method} failed after {execution_time:.3f}s: {str(e)}")
            raise

class RateLimitingMiddleware(Middleware):
    """Rate limiting for infrastructure operations"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.client_requests = {}
    
    async def on_call_tool(self, context, call_next):
        client_id = getattr(context, 'client_id', 'anonymous')
        current_time = time.time()
        
        # Clean old requests
        if client_id in self.client_requests:
            self.client_requests[client_id] = [
                req_time for req_time in self.client_requests[client_id]
                if current_time - req_time < 60
            ]
        else:
            self.client_requests[client_id] = []
        
        # Check rate limit
        if len(self.client_requests[client_id]) >= self.requests_per_minute:
            raise Exception(f"Rate limit exceeded: {self.requests_per_minute} requests per minute")
        
        self.client_requests[client_id].append(current_time)
        return await call_next(context)

# Apply middleware to MCP server
mcp.add_middleware(InfrastructureLoggingMiddleware())
mcp.add_middleware(RateLimitingMiddleware(requests_per_minute=100))
```

### HTTP Request Access
Access HTTP request information for web-based MCP servers:

```python
from fastmcp.http import get_http_request, get_http_headers
from datetime import datetime

@mcp.tool
async def audit_request(ctx: Context) -> dict:
    """Tool that logs HTTP request details for auditing"""
    try:
        request = get_http_request()
        headers = get_http_headers()
        
        audit_info = {
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": headers.get("user-agent", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "url": str(request.url)
        }
        
        await ctx.info(f"Request audit: {audit_info}")
        return audit_info
        
    except RuntimeError:
        # Not in HTTP context (e.g., stdio transport)
        return {"audit": "not_available", "transport": "non-http"}
```

### Tool Transformation Patterns
Transform and enhance existing tools for different use cases:

```python
from fastmcp.tools import Tool, ArgTransform

# Original complex tool
@mcp.tool
async def complex_system_analysis(
    device_id: str,
    metrics: list[str],
    time_range: str,
    aggregation: str = "avg",
    include_history: bool = False,
    ctx: Context = None
) -> dict:
    """Complex system analysis with many parameters"""
    # Complex implementation
    pass

# Create simplified version for common use cases
simple_health_check = Tool.from_tool(
    complex_system_analysis,
    name="simple_health_check",
    description="Quick health check for a device",
    transform_args={
        "device_id": ArgTransform(
            name="device",
            description="Device hostname or IP"
        ),
        "metrics": ArgTransform(
            default=["cpu", "memory", "disk"],
            hidden=True
        ),
        "time_range": ArgTransform(
            default="5m",
            hidden=True
        ),
        "aggregation": ArgTransform(
            hidden=True
        ),
        "include_history": ArgTransform(
            hidden=True
        )
    }
)

mcp.add_tool(simple_health_check)
```

### Class Method Integration
Properly integrate class-based infrastructure components:

```python
class InfrastructureManager:
    """Infrastructure management class with MCP integration"""
    
    def __init__(self, config: dict):
        self.config = config
        self.devices = {}
    
    def add_device(self, hostname: str, ip: str) -> dict:
        """Add device to monitoring"""
        self.devices[hostname] = {"ip": ip, "status": "unknown"}
        return {"hostname": hostname, "added": True}
    
    def get_device_status(self, hostname: str) -> dict:
        """Get status of specific device"""
        if hostname in self.devices:
            return self.devices[hostname]
        raise ValueError(f"Device {hostname} not found")
    
    @classmethod
    def create_from_config(cls, config_file: str):
        """Create manager from configuration file"""
        config = {"monitoring_interval": 30}
        return cls(config)

# Create instance and register methods as MCP tools
infra_manager = InfrastructureManager.create_from_config("config.yaml")

# Register instance methods properly
mcp.tool(infra_manager.add_device)
mcp.tool(infra_manager.get_device_status)

# Register class method
mcp.tool(InfrastructureManager.create_from_config)
```

## Database Operations

### Schema Management
```bash
# Check current database schema version
uv run alembic current

# Generate new migration after model changes
uv run alembic revision --autogenerate -m "description"

# Apply pending migrations
uv run alembic upgrade head

# View migration history
uv run alembic history
```

### TimescaleDB Operations
```bash
# Connect to database via Docker container
docker compose exec postgres psql -U postgres -d infrastructor

# Or run single queries
docker compose exec postgres psql -U postgres -d infrastructor -c "SELECT * FROM timescaledb_information.hypertables;"

# Check hypertable status
SELECT * FROM timescaledb_information.hypertables;

# Monitor compression status
SELECT * FROM timescaledb_information.chunks ORDER BY chunk_name;

# View continuous aggregate policies
SELECT * FROM timescaledb_information.continuous_aggregates;

# Check retention policies
SELECT * FROM timescaledb_information.data_retention_policies;
```

### Data Validation
```bash
# Test database connection from app
uv run python -c "from src.core.database import get_db; print('DB Connected')"

# Validate data integrity via Docker container
docker compose exec postgres psql -U postgres -d infrastructor -c "SELECT COUNT(*) FROM devices;"

# Check recent metrics data
docker compose exec postgres psql -U postgres -d infrastructor -c "SELECT device_id, time, cpu_usage_percent FROM system_metrics ORDER BY time DESC LIMIT 10;"

# Alternative: Use pgcli through host port (if preferred)
uv run pgcli postgresql://postgres:password@localhost:9100/infrastructor
```

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
