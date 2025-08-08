# Infrastructor Backend API

A comprehensive guide to the API layer located in `apps/backend/src/api`.

This document describes the architecture, capabilities, data flows, cross-cutting concerns, and module-specific behaviors of the infrastructure management API. It is intended for contributors and integrators who need a deep understanding of how the API is structured and how it operates.


## Table of Contents
- Overview
- Architecture and Router Structure
- Cross-Cutting Concerns
  - Authentication and Authorization
  - Rate Limiting
  - Error Handling and Exceptions
  - Logging and Observability
- Data Flows and Persistence
  - SSH Command Execution
  - Unified Data Collection Service
  - Database Models and Snapshots
- Endpoint Categories and Responsibilities
  - Common
  - Devices
  - Containers
  - Docker Compose Deployment
  - Proxy (SWAG)
  - ZFS
  - VMs
- Business Logic Highlights
- Performance Considerations
- Security Considerations
- Usage Examples (curl)
- Extensibility Guidelines


## Overview
The API provides a unified interface to manage and monitor heterogeneous infrastructure via SSH and database-backed services. It exposes REST endpoints for devices, containers, proxy configuration, ZFS operations, VM logs, and Docker Compose deployment workflows. Routers are aggregated and mounted under a single base path, providing a consistent, typed, and documented interface.

Base path: `/api`


## Architecture and Router Structure
Routers are defined in modules within this directory and aggregated in `__init__.py`.

Router mounting map (from `apps/backend/src/api/__init__.py`):
- `common` → `/api` (no additional prefix; e.g., `/api/status`, `/api/system-info`)
- `devices` → `/api/devices`
- `containers` → `/api/containers`
- `proxy` → `/api/proxies`
- `zfs` → `/api/zfs`
- `compose_deployment` → `/api/compose`
- `vms` → `/api/vms`

Routers use `fastapi.APIRouter` with typed request/response models. The codebase emphasizes explicit parameter descriptions using `Path`/`Query` and pydantic models where appropriate.


## Cross-Cutting Concerns

### Authentication and Authorization
- Dependency: `current_user=Depends(get_current_user)` from `common.py` is included on all endpoints.
- Mechanism: `HTTPBearer` token-based. In development, if `settings.auth.api_key` is not configured, endpoints accept unauthenticated requests. In production, implement proper JWT/API key validation.
- Minimal validation: tokens must be ≥ 10 characters; otherwise 401 is returned with `WWW-Authenticate: Bearer`.

### Rate Limiting
- Implemented via `slowapi` (`Limiter` with `get_remote_address`).
- Global defaults read from configuration; endpoints may set method-specific limits (e.g., `@limiter.limit("60/minute")`).

### Error Handling and Exceptions
- Consistent try/except mapping to `fastapi.HTTPException` with appropriate status codes.
- Domain-specific exceptions (e.g., `DeviceNotFoundError`, `SSHConnectionError`, `ZFSError`, `ValidationError`) are translated to 4xx/5xx responses with clear messages.
- Unknown failures are logged and surfaced as 500 with non-sensitive detail. Exception chaining (`from e`) is used where appropriate.
- Containers exec error codes are mapped:
  - `125` → 404 Not Found (container not found or not running)
  - `126` → 400 Bad Request (command not executable)
  - `127` → 400 Bad Request (command not found)

### Logging and Observability
- `logging.getLogger(__name__)` per module.
- Rich diagnostics in error paths; sensitive data is not logged.
- Health endpoints expose aggregate status with performance hints (see Monitoring).


## Data Flows and Persistence

### SSH Command Execution
- SSH utilities live under `apps/backend/src/utils/ssh_client.py` and related helpers.
- Typical pattern: build a safe command string, call `execute_ssh_command_simple(hostname, cmd, timeout)`, then parse stdout/stderr.
- Timeouts are parameterized per endpoint to reflect operation complexity.

### Unified Data Collection Service
- Many endpoints use `get_unified_data_collection_service(db_session_factory, ssh_client)` to:
  - Execute a provided async `collection_method`
  - Persist results to the database (for historical analysis/cache)
  - Control freshness via `force_refresh` flags
  - Correlate operations with keys like `f"container_stats_{hostname}_{container_name}"`
- This pattern centralizes caching, persistence, and deduplication of concurrent requests.

### Database Models and Snapshots
- Device metadata and monitoring status are stored via `DeviceService` and related models (e.g., `Device`).
- Monitoring data (e.g., `SystemMetric`, `ContainerSnapshot`) is used by the monitoring endpoints to compute health and activity statistics.
- Proxy config files can be mirrored into `ConfigurationSnapshot` rows via file watchers or scan/sync operations, enabling fast queries without remote I/O.


## Endpoint Categories and Responsibilities

### Common (`common.py`)
- `GET /api/status` → lightweight operational status
- `GET /api/system-info` → host platform/runtime info for the API process
- `GET /api/test-error` → development-only error generator for testing exception handling

### Devices (`devices.py`)
- Registry management: create/list/get/update/delete devices
- Status and summaries: `/{hostname}/status`, `/{hostname}/summary`
- System monitoring via SSH: metrics, drive health, drive stats, logs, network ports
- Import workflow: parse SSH config to upsert devices; supports dry-run and update-existing semantics
- Notes: the SSH-based tools can operate on raw hostnames; the device registry is optional but recommended

### Containers (`containers.py`)
- Inventory: list containers on a device with filters/pagination
- Inspection: retrieve per-container details
- Logs: streaming recent logs with `since`/`tail` controls
- Lifecycle: start/stop/restart/remove
- Metrics: real-time resource stats via `docker stats` parsing
- Exec: run commands inside containers with robust error mapping
- Uses unified data collection for caching and DB persistence where appropriate

### Docker Compose Deployment (`compose_deployment.py`)
- Modify: rewrite docker-compose content for a target device (paths, networks, ports, proxy)
- Deploy: backup, write, and optionally pull/up services on the device
- Combined: modify-and-deploy atomic workflow
- Scanning: pre-deployment port availability and Docker network scans
- Proxy generation: produce SWAG subdomain conf for a given service
- Errors are translated to 400/404/503 with detailed causes; success returns structured results

### Proxy (SWAG) (`proxy.py`)
- Auto-detect SWAG device by probing running containers and filesystem layout via SSH; with TTL-cached result
- List and fetch proxy configurations from DB snapshots; optional live collection fallback
- Scan/sync: reconcile filesystem configs to database records
- Templates and samples: retrieve via MCP resource `get_proxy_config_resource` (e.g., `swag://samples/...`)
- Summary stats for config inventory by device

### ZFS (`zfs.py`)
- Pools: list, detailed status
- Datasets: list by pool, properties by dataset
- Snapshots: list/create/clone/send/receive/diff
- Health: scrub status, ARC stats, events
- Analysis: full report, snapshot usage, optimization suggestions
- Service-layer orchestration with precise SSH timeouts and domain-specific error handling

### VMs (`vms.py`)
- Logs: `/{hostname}/logs` (libvirtd or journalctl fallback)
- VM-specific logs: `/{hostname}/logs/{vm_name}`
- Uses unified data collection for persistence and caching.


## Business Logic Highlights
- Device registry is optional for SSH operations; many endpoints can work solely with hostnames. However, registry entries enable richer monitoring and polling features.
- Compose deployment service applies deterministic transforms to docker-compose content to align with device-specific appdata paths, available ports, and networks, and can generate SWAG proxy configs.
- Proxy management favors cached snapshots for performance, with live SSH collection available when requested or required.
- Monitoring endpoints aggregate DB state, polling service status, and SSH cache metrics to provide actionable health indicators and dashboards.


## Performance Considerations
- Timeouts are calibrated per operation: short for status/logs, medium for container ops, long for ZFS operations.
- Unified data collection reduces redundant SSH calls and provides shared caches across requests.
- Batch queries to the database are favored over per-item queries; aggregate counts and time-window-limited statistics are used in monitoring endpoints.
- Avoid parsing large outputs on the hot path; prefer JSON-ready formats where tools support it (e.g., `docker ps --format '{{json .}}'`).


## Security Considerations
- Authentication is required in production. In dev mode (no `settings.auth.api_key`), endpoints may accept unauthenticated requests.
- All user inputs are validated via Pydantic/Query/Path constraints; command strings are constructed from validated parameters.
- Error messages avoid exposing sensitive details (e.g., credentials, internal paths). SSH errors are summarized.
- For JWT/API key validation, rotate secrets and enforce TLS at the ingress layer.


## Usage Examples (curl)

Common:
```bash
curl -sS http://localhost:8000/api/status
curl -sS http://localhost:8000/api/system-info
```

Containers:
```bash
curl -sS -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/containers/my-host?all_containers=true&status=running"

curl -sS -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/containers/my-host/my-container/logs?tail=200"
```

Compose Deployment:
```bash
curl -sS -X POST -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" \
  -d '{"compose_content":"version: \"3\"\nservices:\n  app:\n    image: nginx","device":"my-host"}' \
  http://localhost:8000/api/compose/modify
```

Proxy:
```bash
curl -sS -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/proxies/configs?limit=50"
```

ZFS:
```bash
curl -sS -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/zfs/my-host/pools"
```

VMs:
```bash
curl -sS -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/vms/my-host/logs/my-vm"
```


## Extensibility Guidelines
- New resources should be implemented as separate modules with an `APIRouter()` instance and imported into `api/__init__.py` for inclusion.
- Follow the patterns in `CLAUDE.md` for:
  - Router creation and dependency injection
  - Authentication (`get_current_user`) and rate limiting (`Limiter`)
  - Error handling with precise exception-to-HTTP mapping
  - Parameter validation using `Path`/`Query` and typed request/response models
- Prefer the unified data collection service when retrieving data over SSH to gain caching and persistence benefits.
- Document every endpoint with clear docstrings (triple-quoted) describing intent, arguments, returns, and caveats; FastAPI will include these in OpenAPI.

---

For deeper standards and patterns, see `apps/backend/src/api/CLAUDE.md`. This README is kept in sync with the codebase; please update it whenever new routers or significant behaviors are introduced.
