# Claude Code Memory - Infrastructor Project

This file contains comprehensive instructions for Claude to follow when working on the `infrastructor` project - a comprehensive infrastructure management and monitoring platform.

## 🏛️ Project Architecture

**Updated: August 7, 2025** - Critical Architectural Decision Change

### Core Architecture
- **Dual-Server Design**: FastAPI REST API + WebSocket Server (port 9101) + Independent FastMCP Server (port 9102)
- **Database**: PostgreSQL for relational data storage (port 9100)
- **Caching**: Redis for session storage and caching (port 9104)
- **Communication**: Both API endpoints and MCP tools call unified data collection service directly (NOT via HTTP)
- **Package Management**: UV package manager for modern Python dependency management
- **Python Version**: 3.11+ with async/await throughout

### Key Architectural Decision
**IMPORTANT**: MCP tools and API endpoints both call the unified data collection service directly via Python function calls, NOT via HTTP requests. This provides:
- Better performance (no HTTP serialization overhead)
- Consistent caching and data handling
- Shared audit trails and error handling
- Simplified debugging and maintenance

### Technology Stack

#### Backend
- **Web Framework**: FastAPI with comprehensive middleware (CORS, security, rate limiting, timing)
- **MCP Integration**: FastMCP with 27 resources across 6 categories
- **Database**: SQLAlchemy + AsyncPG + Alembic migrations + PostgreSQL
- **SSH Communication**: AsyncSSH for secure device communication over Tailscale
- **Authentication**: Bearer token auth with JWT support
- **Code Quality**: Ruff (linting/formatting) + MyPy (type checking) + Pre-commit hooks
- **Testing**: Pytest with async support, coverage reporting (80% minimum)

#### Frontend
- **Framework**: React 19.1.1 with TypeScript 5.9.2
- **Build Tool**: Vite 7.1.0 with hot module replacement
- **Styling**: Tailwind CSS v4.1.11 (CSS-first configuration, @tailwindcss/vite plugin)
- **UI Components**: shadcn/ui with Radix UI primitives
- **State Management**: Zustand for global state
- **Routing**: React Router v7 for navigation
- **API Client**: Axios with interceptors and TypeScript types
- **WebSocket**: Custom hooks for real-time data streaming
- **Type Safety**: Shared types package with backend schema parity

### Project Structure
```
infraestructor/
├── apps/backend/src/          # Main application code
│   ├── main.py               # FastAPI app with lifespan management
│   ├── api/                  # REST API routers (devices, containers, proxy, zfs)
│   ├── core/                 # Configuration, database, exceptions
│   ├── mcp/                  # MCP tools, resources, prompts
│   ├── models/               # SQLAlchemy database models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/             # Business logic layer
│   └── utils/                # Utilities (SSH, logging, etc.)
├── apps/backend/
│   ├── alembic/              # Database migrations
│   ├── alembic.ini           # Alembic configuration
│   ├── init-scripts/         # Database initialization SQL
├── dev.sh                    # Development script (start/stop/logs)
├── docker-compose.yaml       # PostgreSQL container
└── logs/                     # Application logs with rotation
```

## 💻 Development Workflow

### Essential Commands
```bash
# Start development environment (both servers)
./dev.sh start                # Starts API + MCP servers in background
./dev.sh logs                 # View real-time logs with color coding
./dev.sh stop                 # Stop both servers
./dev.sh restart              # Restart both servers

# Development commands
uv sync                       # Install/update dependencies
uv run uvicorn apps.backend.src.main:app --host 0.0.0.0 --port 9101 --reload
python apps/backend/src/mcp/server.py  # MCP server

# Code quality
uv run ruff check src/        # Linting
uv run ruff format src/       # Formatting
uv run mypy src/              # Type checking
uv run pytest                # Run tests with coverage

# Database operations
docker compose up postgres -d # Start PostgreSQL
cd apps/backend && uv run alembic upgrade head   # Apply migrations
cd apps/backend && uv run alembic revision --autogenerate -m "description"  # Create migration
```

### Development URLs
- **API Server + WebSocket**: http://localhost:9101
- **API Documentation**: http://localhost:9101/docs
- **API Health Check**: http://localhost:9101/health
- **WebSocket Endpoint**: ws://localhost:9101/ws/stream
- **MCP Server**: http://localhost:9102/mcp (independent server)
- **Database**: postgresql://postgres:change_me_in_production@localhost:9100/infrastructor
- **Redis**: redis://localhost:9104/0

## 🗄️ Database Architecture

### Core Tables
- **devices**: Device registry with JSONB metadata, tags, SSH config
- **system_metrics**: Time-series data for CPU, memory, disk metrics with PostgreSQL indexes
- **container_snapshots**: Container status and resource usage over time
- **drive_health**: S.M.A.R.T. drive monitoring data
- **proxy_configurations**: SWAG reverse proxy configuration management
- **data_collection_audit**: Complete audit trail for all data collection operations
- **configuration_snapshots**: Configuration file change tracking

### PostgreSQL Features
- **Efficient Indexing**: BTREE indexes for time-based queries, GIN indexes for JSONB data
- **Data Retention**: Manual cleanup policies for time-series data (90-365 days)
- **JSONB Support**: Native JSON storage and querying capabilities
- **Foreign Keys**: Proper referential integrity with CASCADE deletions

### Migration Management
```bash
# Check current schema version
cd apps/backend && uv run alembic current

# Create new migration
cd apps/backend && uv run alembic revision --autogenerate -m "add_new_feature"

# Apply migrations
cd apps/backend && uv run alembic upgrade head

# Database console access
docker compose exec postgres psql -U postgres -d infrastructor
```

## 🔧 API Structure & Patterns

### REST API Endpoints
- **`/api/devices`**: Device management (CRUD, analysis, health)
- **`/api/containers`**: Docker container management
- **`/api/proxies`**: SWAG reverse proxy configuration
- **`/api/zfs`**: ZFS filesystem management (16 endpoints)
- **`/health`**: Application health check
- **`/docs`**: Auto-generated OpenAPI documentation

### Error Handling Pattern
- **Custom Exceptions**: Comprehensive exception hierarchy in `core/exceptions.py`
- **HTTP Status Mapping**: Automatic mapping from error codes to HTTP status
- **Structured Responses**: Consistent error format with timestamps, details
- **Logging Integration**: All errors logged with context and correlation IDs

### Authentication & Security
- **Bearer Token**: HTTP Bearer authentication with JWT support
- **Rate Limiting**: Configurable per-endpoint rate limits
- **Security Headers**: CORS, XSS protection, content type sniffing prevention
- **SSH Security**: Ed25519 keys, connection timeouts, retry limits

## 🤖 MCP Integration

### 27 MCP Resources (6 Categories)
1. **SWAG Proxy** (`swag://`): Reverse proxy configuration management
2. **Docker Compose** (`docker://`): Container stack discovery and management
3. **ZFS Management** (`zfs://`): Pool, dataset, snapshot management
4. **System Logs** (`logs://`): Multi-source log access (journald, Docker, VMs)
5. **Network Ports** (`ports://`): Port analysis and process mapping
6. **Device Configuration**: Device registry and analysis tools

### MCP Tools Organization
- **Container Management**: List, inspect, logs, service dependencies
- **System Monitoring**: Metrics, drive health, system logs
- **Device Management**: Registration, analysis, SSH operations
- **Proxy Management**: SWAG configuration parsing and templating
- **Metrics Collection**: Background polling with configurable intervals

### MCP Server Architecture
- **Independent Process**: Runs separately from FastAPI (apps/backend/src/mcp/server.py)
- **Direct Service Integration**: All operations call unified data collection service directly
- **Resource Integration**: Real-time access to configurations and logs
- **Shared Authentication**: Uses same authentication and database connections as API

## 🛡️ Code Quality & Standards

### Code Style Conventions
- **Line Length**: 100 characters (configured in pyproject.toml)
- **Import Organization**: isort with known-first-party=["src"] - ALL imports at top of file
- **Type Hints**: Required for all functions (enforced by MyPy)
- **Modern Type Annotations**: Use Python 3.11+ built-in generics (`list[str]`, `dict[str, int]`, `str | None`)
- **Async/Await**: Use throughout for I/O operations
- **Error Handling**: Always use custom exception classes with proper chaining (`raise NewError() from e`)
- **Logging**: Structured logging with correlation IDs
- **Timezone Handling**: Always use UTC (`datetime.now(timezone.utc)`)
- **String Formatting**: Only use f-strings when actually interpolating variables

### Critical Anti-Patterns to Avoid
- ❌ **Wrong timezone handling**: `datetime.now()` without timezone
- ❌ **Deprecated type annotations**: `from typing import Union, List, Dict` (use built-in `|`, `list`, `dict`)
- ❌ **Imports not at top**: Imports scattered throughout functions
- ❌ **Unnecessary f-strings**: `f"static string"` instead of `"static string"`
- ❌ **Missing exception chaining**: `raise NewError()` instead of `raise NewError() from e`

### File Naming Patterns
- **API Routes**: `apps/backend/src/api/{resource}.py` (e.g., devices.py)
- **Services**: `apps/backend/src/services/{resource}_service.py`
- **Models**: `apps/backend/src/models/{resource}.py`
- **Schemas**: `apps/backend/src/schemas/{resource}.py`
- **MCP Tools**: `apps/backend/src/mcp/tools/{category}.py`

### Testing Conventions
- **Test Location**: `apps/backend/tests/` mirrors `src/` structure
- **Async Tests**: Use `pytest-asyncio` for async test functions
- **Coverage**: Minimum 80% coverage required
- **Fixtures**: Shared fixtures in `conftest.py`
- **Mocking**: Use `pytest-mock` for external dependencies

## 🚀 Common Development Tasks

### Adding a New API Endpoint
1. **Create route** in appropriate `apps/backend/src/api/{resource}.py`
2. **Add Pydantic schemas** in `apps/backend/src/schemas/{resource}.py`
3. **Use unified data collection service** with collection methods pattern
4. **Add database models** if needed in `apps/backend/src/models/{resource}.py`
5. **Create tests** in `apps/backend/tests/test_api/test_{resource}.py`
6. **Update OpenAPI docs** (automatic via FastAPI)

### Adding a New MCP Tool
1. **Create tool function** in `apps/backend/src/mcp/tools/{category}.py`
2. **Use unified data collection service directly** (NOT HTTP calls to API)
3. **Implement collection methods** for data gathering
4. **Register tool** in MCP server configuration
5. **Create tests** for tool functionality
6. **Update MCP documentation**

### Data Collection Pattern (Both API and MCP)
```python
# Correct pattern for both API endpoints and MCP tools
async def collect_data_example():
    # Get unified data collection service
    unified_service = await get_unified_data_collection_service(
        db_session_factory=db_session_factory,
        ssh_client=ssh_client
    )
    
    # Create collection method
    async def collect_method() -> dict[str, Any]:
        # Your data collection logic here
        return {"data": "collected_data"}
    
    # Use unified service
    result = await unified_service.collect_and_store_data(
        collection_method=collect_method,
        device_id=device_id,
        data_type="data_type_name"
    )
    return result
```

### Database Schema Changes
1. **Modify models** in `apps/backend/src/models/`
2. **Generate migration**: `cd apps/backend && uv run alembic revision --autogenerate -m "description"`
3. **Review migration** for correctness
4. **Apply migration**: `cd apps/backend && uv run alembic upgrade head`
5. **Update schemas** if response format changes

### Adding Background Polling
1. **Implement collection logic** in service layer
2. **Add to polling service** in `apps/backend/src/services/polling_service.py`
3. **Configure intervals** in `.env` file
4. **Test with polling enabled**: `POLLING_ENABLED=true`

## 🐛 Debugging & Troubleshooting

### Log Locations
- **API Server**: `logs/api_server.log`
- **MCP Server**: `logs/mcp_server.log`
- **PostgreSQL**: `logs/postgres/`
- **Live Logs**: `./dev.sh logs` (colored, real-time)

### Common Issues
- **Port Conflicts**: Check `lsof -ti:9101` and `lsof -ti:9102`
- **Database Connection**: Verify PostgreSQL container is running
- **SSH Timeouts**: Check Tailscale connectivity and SSH key permissions
- **MCP Authentication**: Verify Bearer token is passed correctly
- **Migration Errors**: Check database state with `cd apps/backend && uv run alembic current`

### Health Check Endpoints
- **API Health**: `GET /health` - Comprehensive system status
- **Database Health**: Included in `/health` response
- **MCP Health**: Independent server status

## 🔄 Environment Configuration

### Key Environment Variables
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=9100
POSTGRES_DB=infrastructor

# Redis
REDIS_HOST=localhost
REDIS_PORT=9104
REDIS_DB=0

# Server Configuration  
MCP_HOST=0.0.0.0
MCP_PORT=9101          # Corrected: Main API/WebSocket server port
WEBSOCKET_PORT=9102    # Corrected: Independent MCP server port

# Authentication
API_KEY=your-api-key-for-authentication
JWT_SECRET_KEY=your-super-secret-jwt-key

# SSH Configuration
SSH_CONNECTION_TIMEOUT=10
SSH_COMMAND_TIMEOUT=30
SSH_KEY_PATH=~/.ssh/id_ed25519

# Polling & Performance
POLLING_ENABLED=false
POLLING_CONTAINER_INTERVAL=30
POLLING_SYSTEM_METRICS_INTERVAL=300
RATE_LIMIT_REQUESTS_PER_MINUTE=100
```

### Configuration Files
- **Main Config**: `.env` (copy from `.env.example`)
- **Docker Compose**: `docker-compose.yaml` (PostgreSQL + Redis)
- **Alembic**: `alembic.ini` (database migration settings)
- **Python Project**: `pyproject.toml` (dependencies, tools, scripts)

## 📚 Additional Resources

### Documentation Files
- **MCP Resources**: `MCP_RESOURCES_SUMMARY.md` - Complete resource listing
- **API Documentation**: Auto-generated at `/docs` endpoint
- **README**: `README.md` - User-facing documentation
- **Database Schema**: `init-scripts/` - SQL initialization scripts

### Development Scripts
- **`dev.sh`**: Main development script (start/stop/logs/restart)
- **Log Management**: Automatic rotation, colored output, health checks
- **Process Management**: Automatic PID tracking and cleanup

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md

---

## 🎯 Development Best Practices

### Before Making Changes
1. **Run health check**: `curl http://localhost:9101/health`
2. **Check current branch**: `git status`
3. **Update dependencies**: `uv sync`
4. **Run tests**: `uv run pytest`

### After Making Changes
1. **Run code quality checks**: `uv run ruff check src/ && uv run mypy src/`
2. **Run tests with coverage**: `uv run pytest --cov=apps/backend/src`
3. **Test API manually**: Visit `/docs` endpoint
4. **Check logs for errors**: `./dev.sh logs`

### Git Workflow
- **Feature branches**: `git checkout -b feature/description`
- **Commit style**: Conventional commits preferred
- **Pre-push**: Always run tests and linting
- **API changes**: Update OpenAPI documentation automatically generated

*This CLAUDE.md provides comprehensive guidance for working effectively with the infrastructor project. Refer to specific sections as needed and keep this file updated as the project evolves.*

## 📝 System Configuration Memories

### Docker and Containers
- postgres is running in a container