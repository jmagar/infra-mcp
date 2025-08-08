# Infrastructor Core Layer

A deep dive into the core modules under `apps/backend/src/core`. This layer provides configuration management, database access, eventing primitives, and shared exception types used across the API and services.

Modules:
- `config.py` — Structured application configuration via Pydantic Settings
- `database.py` — Async SQLAlchemy + TimescaleDB setup, session management, health/ops utilities
- `events.py` — Async event bus with typed events for monitoring and real-time communication
- `exceptions.py` — Structured exception hierarchy with rich context
- `__init__.py` — Public exports for convenient imports


## Table of Contents
- Architecture Overview
- Module Details
  - config.py
  - database.py
  - events.py
  - exceptions.py
- Data Flows and Interactions
- Usage Patterns and Examples
- Operational Considerations
- Extension Guidelines


## Architecture Overview
The core layer centralizes cross-cutting concerns:
- Configuration: composed settings tree, environment-driven, cached via `lru_cache()`
- Database: async engine and sessions with a TimescaleDB-optimized pool; health checks, stats, retention and compression helpers
- Events: lightweight async event bus for non-blocking, topic-oriented communication
- Exceptions: unified domain exceptions with serializable metadata and timestamps

These modules are imported by API routers, services, and background workers.


## Module Details

### `config.py`
Provides strongly-typed settings using Pydantic v2 `BaseSettings`. The configuration is grouped by concern and aggregated into `ApplicationSettings`.

Key classes and responsibilities:
- `DatabaseSettings` — Postgres/Timescale connection details and pool tunables; exposes `database_url` and `sync_database_url` properties
- `RedisSettings` — Redis host, port, db, and pool/timeout settings; exposes `redis_url`
- `MCPServerSettings` — MCP (Model Context Protocol) server host/port/path/log level
- `WebSocketSettings` — Capacity limits for real-time connections
- `SSHSettings` — Connect/command timeouts, max retries, global SSH key path defaults
- `PollingSettings` — Enable/intervals for periodic data collection tasks
- `MonitoringSettings` — Feature flags and timeout validation for monitoring subsystems
- `RetentionSettings` — Data TTLs and compression cutover windows
- `AuthSettings` — JWT parameters and optional API key (`api_key`) for dev/prod modes
- `LoggingSettings` — Log level/format/path and rotation/sampling (see full file)
- `APISettings` — API host/port/log levels; CORS origins; cache and rate limit toggles; SSH concurrency caps
- `SWAGSettings` — SWAG reverse proxy device and configuration directory
- `ExternalIntegrationSettings` — Gotify notification endpoint and token
- `ApplicationSettings` — Aggregates all above sections and provides `is_development`/`is_production`

Helpers:
- `get_settings()` — Cached singleton `ApplicationSettings` using `@lru_cache()`
- Environment variable precedence with `.env` support; `APISettings` custom handling of `CORS_ORIGINS` comma-separated lists

Usage:
```python
from apps.backend.src.core import get_settings
settings = get_settings()
if settings.is_production:
    ...
```


### `database.py`
Async SQLAlchemy integration tuned for TimescaleDB and high-concurrency workloads.

Core pieces:
- Engine/session lifecycle
  - `create_async_database_engine()` — builds `AsyncEngine` with pool sizing, statement timeouts, UTC timezone, JIT off (TimescaleDB compat), and debug echos in dev
  - `create_async_session_factory(engine)` — `async_sessionmaker` with `expire_on_commit=False`
  - `init_database()`/`close_database()` — application startup/shutdown wiring to initialize `_async_engine` and `_async_session_factory`
  - `get_async_engine()`/`get_async_session_factory()` — accessors that error if not initialized
  - `get_async_session()`/`get_db_session()` — contextmanager and FastAPI dependency yielding `AsyncSession`
- Health and observability
  - `test_database_connection()` — connectivity and Timescale extension checks
  - `check_database_health()` — multi-metric health diagnostic suite
  - `get_database_stats()` — sizes, performance metrics, and activity
  - `get_connection_info()` — connection/pool/server metadata
- TimescaleDB utilities
  - `create_hypertables()` — convert time-series tables post-migration
  - `setup_compression_policies()` — configure native compression
  - `setup_retention_policies()` — enforce TTL on historical data
  - `get_timescaledb_info()` — extension-level info and stats
- Maintenance
  - `execute_raw_sql()` — parameterized raw SQL execution
  - `optimize_database()` — autovacuum/analyze helpers
  - `get_chunk_statistics()` — per-chunk storage metrics
  - `validate_database_schema()` — integrity and extension validation

Usage:
```python
from apps.backend.src.core.database import get_db_session

async def handler(dep_session = Depends(get_db_session)):
    async with dep_session as session:
        await session.execute(...)
        await session.commit()
```


### `events.py`
An async event bus to decouple producers and consumers of infrastructure telemetry and status changes.

Components:
- Event models (Pydantic):
  - `BaseEvent` — id, type, timestamp (UTC), source, metadata
  - `MetricCollectedEvent`, `DeviceStatusChangedEvent`, `ContainerStatusEvent`, `DriveHealthEvent`
- `EventHandler` — wraps async handlers, tracks supported event types and priority
- `EventBus` — bounded queue, non-blocking `emit_nowait` and timed `emit`, concurrent handler execution, lifecycle mgmt, stats, graceful shutdown
- Global helpers: `get_event_bus()`, `initialize_event_bus()`, `shutdown_event_bus()`

Usage:
```python
from apps.backend.src.core.events import get_event_bus, MetricCollectedEvent

bus = get_event_bus()
await bus.start()
await bus.emit(MetricCollectedEvent(device_id=..., hostname="host", cpu_usage_percent=42.0, ...))
```


### `exceptions.py`
Unified exception hierarchy with context for consistent API error mapping.

Highlights:
- Base: `InfrastructureException(message, error_code, details, hostname, operation)` with UTC timestamp and `to_dict()`
- Database: `DatabaseConnectionError`, `DatabaseOperationError`
- SSH: `SSHConnectionError`, `SSHCommandError(command, exit_code, stderr)`, `SSHTimeoutError(timeout_seconds)`
- Devices: `DeviceNotFoundError`, `DeviceOfflineError(last_seen)`
- Validation/Business: `ValidationError`, `BusinessLogicError(rule_name, context)`
- Resources/External: `ResourceNotFoundError(resource_type, identifier)`, `ResourceConflictError(...)`, `ExternalServiceError(service_name, status_code, response_body)`
- Monitoring/Data: `SystemMonitoringError`, `DataCollectionError(data_type)`, `CacheOperationError(cache_key)`

These exceptions are raised in services and translated to `HTTPException` statuses by API layers.


## Data Flows and Interactions
- API routers/services call SSH helpers and DB via `get_db_session()`; exceptions raised are typed from `exceptions.py`.
- Background polling pushes device/container metrics, which emit events via `EventBus`. WebSocket services can subscribe to those topics to broadcast to clients.
- Database operations adhere to TimescaleDB patterns (hypertables + compression + retention) configured via `config.py`.


## Usage Patterns and Examples

Get cached settings:
```python
from apps.backend.src.core import settings  # singleton
print(settings.database.database_url)
```

Create a custom operation with DB session:
```python
from apps.backend.src.core.database import get_async_session
from sqlalchemy import text

async with get_async_session() as session:
    await session.execute(text("SELECT 1"))
```

Emit and subscribe to events:
```python
from apps.backend.src.core.events import get_event_bus, EventBus, BaseEvent

bus = get_event_bus()

async def on_any(e: BaseEvent):
    print("Event:", e.event_type)

handler_id = await bus.subscribe(["metric_collected", "device_status_changed"], on_any)
await bus.emit_nowait(BaseEvent(event_type="device_status_changed"))
await bus.unsubscribe(handler_id)
```

Raise and serialize exceptions:
```python
from apps.backend.src.core.exceptions import SSHCommandError

try:
    raise SSHCommandError("Failed", command="docker ps", exit_code=127, stderr="not found")
except SSHCommandError as e:
    payload = e.to_dict()
```


## Operational Considerations
- Initialize DB on app startup: call `init_database()`; close on shutdown.
- After migrations, run Timescale helpers: `create_hypertables()`, then `setup_compression_policies()`, then `setup_retention_policies()`.
- Tune pool sizes and timeouts through environment variables (see `DatabaseSettings`).
- In dev, `settings.auth.api_key` may be unset; production should configure proper auth.
- Event bus must be started (`initialize_event_bus()`) before emitting; stop on shutdown.


## Extension Guidelines
- Add new settings: create a `BaseSettings` subclass, include it in `ApplicationSettings`, and document env vars.
- Add new DB utilities: prefer async, parameterized SQL; gate long-running operations with statement timeouts.
- Add events: subclass `BaseEvent` and document fields; emit from producers; subscribe in consumers with clear priorities.
- Add exceptions: subclass `InfrastructureException` with a distinct `error_code` and minimal, non-sensitive `details`.
- Maintain UTC usage for all timestamps and avoid naive datetimes.

---

For API-layer usage and patterns, see `apps/backend/src/api/README.md` and `apps/backend/src/api/CLAUDE.md`. Keep this document updated when core capabilities evolve.
