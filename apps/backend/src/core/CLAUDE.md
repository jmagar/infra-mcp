# Core Development Guidelines (apps/backend/src/core)

This document establishes authoritative guidelines for building and maintaining the core layer: `config.py`, `database.py`, `events.py`, and `exceptions.py`.

Audience: maintainers and contributors implementing cross-cutting infrastructure concerns. Keep this file in sync with the codebase.


## Principles
- Single source of truth for cross-cutting concerns (config, DB, events, errors)
- Strong typing and explicitness (Pydantic v2, SQLAlchemy types)
- Async-first, non-blocking I/O
- Security by default (no secrets in code, least privilege)
- Operationally observable (health checks, stats, structured logging)
- Backward-compatible changes where possible; document breaking changes


## Configuration (`config.py`)

### Patterns
- Use Pydantic `BaseSettings` per concern: `DatabaseSettings`, `RedisSettings`, `SSHSettings`, `PollingSettings`, `MonitoringSettings`, `RetentionSettings`, `AuthSettings`, `APISettings`, `SWAGSettings`, `ExternalIntegrationSettings`.
- Aggregate into `ApplicationSettings` and expose via `get_settings()` with `lru_cache()` for a process-wide singleton.
- Normalize env vars and support `.env` file. Parse list-like values (e.g., `CORS_ORIGINS`) safely.
- Provide derived properties (e.g., `database_url`, `redis_url`) so callers don’t build URLs.
- Validate numeric/time ranges (timeouts, intervals) with clear error messages.

### Anti-patterns
- Accessing environment variables directly outside `config.py`.
- Creating additional global state for settings or mutating `settings` after load.
- Storing secrets in VCS or defaulting to insecure values in production.

### Testing
- Use `monkeypatch` to set env vars per test; re-seed by clearing the `lru_cache` for `get_settings()`.
- Provide table-driven tests for edge values (timeouts, pool sizes, invalid URIs).


## Database (`database.py`)

### Patterns
- Initialize engine once at app startup via `init_database()`; close with `close_database()` on shutdown.
- Use `async_sessionmaker(expire_on_commit=False)`; obtain sessions through `get_async_session()` or FastAPI `Depends(get_db_session)`.
- Set server- and statement-level timeouts. Use UTC timezone. Optimize for TimescaleDB compatibility (disable JIT where needed).
- Manage TimescaleDB lifecycle post-migration in order: `create_hypertables()` → `setup_compression_policies()` → `setup_retention_policies()`.
- Expose health/diagnostics (`test_database_connection()`, `check_database_health()`, `get_database_stats()`, `get_connection_info()`).
- Prefer parameterized SQL (`text()` with bound params) when using raw SQL. Keep DDL/DML helpers idempotent.

### Anti-patterns
- Long-running transactions or holding sessions across await points unrelated to DB work.
- Creating ad-hoc engines or sessions instead of using the shared factory/dependency.
- Disabling timeouts globally or using `autocommit`-like patterns.
- Raw SQL with string interpolation; missing parameters; non-UTC timestamps.

### Testing
- Use a dedicated test database (schema or ephemeral DB). Apply migrations before tests if needed.
- Wrap each test in a transaction and roll back to isolate state where practical.
- Include tests for hypertable creation and compression/retention setup when schema evolves.

### Performance
- Tune pool size, max overflow, and statement timeouts via settings. Monitor with provided stats endpoints/utilities.
- Use appropriate indexes and Timescale chunks; audit with `get_chunk_statistics()`.


## Events (`events.py`)

### Patterns
- Define Pydantic event models: derive from `BaseEvent` (id, type, timestamp UTC, source, metadata).
- Keep event payloads minimal and serializable. Avoid embedding large blobs; prefer IDs and fetch on demand.
- Use `EventBus` for async, non-blocking publication. Start bus at app startup and stop gracefully on shutdown.
- Handlers should be small, idempotent, and resilient. Use priorities only when necessary and document them.
- Apply backpressure through queue sizing. Drop or buffer with explicit policy; never block critical paths indefinitely.

### Anti-patterns
- Blocking I/O or CPU-heavy work inside handlers. Offload to background tasks/job queues.
- Global mutable state in handlers. Hidden coupling between handlers.
- Emitting events before the bus has started or after shutdown.

### Testing
- Unit test handlers with synthetic events; assert side effects and idempotency.
- Integration test bus lifecycle (start, subscribe, emit, unsubscribe, shutdown) and backpressure behavior.


## Exceptions (`exceptions.py`)

### Patterns
- Inherit from `InfrastructureException` (message, `error_code`, `details`, `hostname`, `operation`, UTC timestamp). Provide `to_dict()` for logging and API mapping.
- Use specific exception types: Database*, SSH*, Device*, Validation/Business*, Resource*, ExternalService*, Monitoring/Data*, Cache*.
- Include minimal non-sensitive context in `details` (e.g., exit codes, identifiers, not raw secrets or full payloads).
- Map domain exceptions to HTTP errors at the API layer only. Core must remain framework-agnostic.

### Anti-patterns
- Catch-all `except Exception:` without re-raise/logging.
- Raising `HTTPException` from core modules.
- Attaching large binary payloads or secrets to exception details.

### Testing
- Verify exception `to_dict()` structure and redaction behavior.
- Ensure command/timeout exceptions include the right fields (exit_code, stderr, timeout_seconds).


## Security
- Never log secrets or raw tokens. Redact sensitive fields in logs and exception details.
- Use least-privilege DB roles and rotate credentials. Enforce SSL where applicable.
- Validate inputs at the boundary and use strict types. Reject invalid ranges for timeouts/intervals.


## Observability & Logging
- Prefer structured logs with event context and correlation IDs when available.
- Emit health and diagnostic metrics from DB and EventBus utilities.
- Keep logs actionable: include operation names, device/host identifiers, and error codes.


## Migration & Change Management
- Document new settings and default values. Provide upgrade notes for breaking changes.
- For DB schema changes, update Timescale helpers and regression tests accordingly.
- Version event payloads if structure changes; maintain consumers or add adapters.


## Contribution Checklist
- [ ] Types are explicit and Pydantic models validated
- [ ] New settings covered by tests and docstrings; defaults are safe
- [ ] DB code uses the shared engine/session and respects timeouts
- [ ] Timescale helpers updated and idempotent
- [ ] Event definitions small, serializable, and versioned if needed
- [ ] Handlers idempotent; no blocking I/O
- [ ] Exceptions specific, non-leaky, and mapped only at API boundary
- [ ] Security review (secrets redaction, least privilege)
- [ ] Observability hooks present (health/stats/logging)
- [ ] README and this CLAUDE.md updated


## Quick References
- Settings: `from apps.backend.src.core import get_settings`
- DB dependency: `from apps.backend.src.core.database import get_db_session`
- Event bus: `from apps.backend.src.core.events import get_event_bus`
- Exceptions: `from apps.backend.src.core.exceptions import InfrastructureException`
