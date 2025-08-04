# Infrastructor - Unified Architecture Blueprint

## 1. 🎯 **Architectural Vision & Goals**

This document outlines the refactored architecture for the Infrastructor project, designed to create a unified, efficient, and maintainable system for infrastructure management. The primary goals of this new architecture are:

-   **Unified Data Collection**: Consolidate all data gathering (polling, API, MCP) into a single, authoritative service.
-   **Data Consistency**: Ensure all data collection operations are audited and stored in the database, providing a complete historical record.
-   **Code Centralization**: Eliminate duplicate SSH command implementations and error handling logic.
-   **Performance Optimization**: Implement smart caching, connection pooling, and event-driven updates to reduce system load and improve API response times.
-   **Scalability & Maintainability**: Create a modular, decoupled architecture that is easy to extend, test, and maintain.
-   **Enhanced User Experience**: Provide more reliable and performant tools and APIs.

## 2. 📁 **New Directory & File Structure**

The following tree represents the complete file structure of the `apps/backend/src/` directory after the refactoring.

```
apps/backend/src/
├── __init__.py
├── main.py
│
├── api/
│   ├── __init__.py
│   ├── common.py
│   ├── containers.py
│   ├── devices.py
│   ├── monitoring.py
│   ├── proxy.py
│   └── system.py
│
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── events.py
│   └── exceptions.py
│
├── mcp/
│   ├── __init__.py
│   ├── server.py
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── configuration_resources.py
│   │   └── ... (existing resources updated)
│   └── tools/
│       ├── __init__.py
│       ├── configuration_management.py
│       └── ... (existing tools refactored)
│
├── models/
│   ├── __init__.py
│   ├── audit.py                   # NEW
│   ├── cache.py                   # NEW
│   ├── configuration.py           # NEW
│   ├── container.py               # REWRITTEN
│   ├── device.py                  # REWRITTEN
│   ├── metrics.py                 # REWRITTEN
│   ├── performance.py             # NEW
│   └── proxy_config.py            # REWRITTEN
│
├── schemas/
│   ├── __init__.py
│   ├── audit.py                   # NEW
│   ├── cache.py                   # NEW
│   ├── configuration.py           # NEW
│   └── ... (existing schemas updated)
│
├── services/
│   ├── __init__.py
│   ├── cache_manager.py           # NEW
│   ├── command_registry.py        # NEW
│   ├── configuration_monitoring.py# NEW
│   ├── polling_service.py         # REWRITTEN
│   ├── performance_tracker.py     # NEW
│   ├── unified_data_collection.py # NEW
│   └── parsers/                   # NEW
│       ├── __init__.py
│       ├── base_parser.py
│       ├── docker_compose_parser.py
│       ├── nginx_parser.py
│       └── systemd_parser.py
│
└── utils/
    ├── __init__.py
    ├── ssh_client.py              # REWRITTEN (Simplified)
    └── ssh_errors.py              # REWRITTEN (Unified)
```

## 3. 🏛️ **Core Architectural Components**

### 3.1. **UnifiedDataCollectionService (`services/unified_data_collection.py`)**

This is the cornerstone of the new architecture. It centralizes all data collection logic, replacing the fragmented implementations in the old `PollingService`, `MetricsService`, and `ContainerService`.

**Key Responsibilities:**

-   Execute all SSH commands via the `CommandRegistry`.
-   Manage smart caching of command results using the `CacheManager`.
-   **Always** store collected data in the database, creating a complete audit trail.
-   Provide a single, consistent interface for all data collection requests (from polling, APIs, or MCP tools).
-   Emit events via the event bus after data collection.

**High-Level Implementation:**

```python
# services/unified_data_collection.py

class UnifiedDataCollectionService:
    def __init__(self, db_session_factory, command_registry, cache_manager, event_bus):
        # ... initialization ...

    async def collect_and_store_data(
        self,
        device_id: UUID,
        command_name: str,
        force_refresh: bool = False,
        store_result: bool = True,
        **kwargs
    ) -> Any:
        # 1. Check cache
        # 2. Execute command via CommandRegistry
        # 3. Parse result
        # 4. Store in database (audit + data models)
        # 5. Update cache
        # 6. Emit event
        # 7. Return result
```

### 3.2. **CommandRegistry (`services/command_registry.py`)**

This service acts as a central repository for all SSH command definitions, eliminating duplicate command strings and providing a single place to manage timeouts, retries, and parsing logic.

**Key Features:**

-   Defines all SSH commands used in the system as `CommandDefinition` objects.
-   Specifies the command template, category, timeout, cache TTL, and parser for each command.
-   Decouples the command logic from the services that use them.

**Example Command Definition:**

```python
# services/command_registry.py

@dataclass
class CommandDefinition:
    name: str
    command_template: str
    category: CommandCategory
    parser: Callable

# In CommandRegistry class:
def get_all_commands():
    return [
        CommandDefinition(
            name="system_metrics",
            command_template="...",
            category=CommandCategory.SYSTEM_METRICS,
            parser=SystemMetricsParser().parse
        ),
        # ... other commands
    ]
```

### 3.3. **ConfigurationMonitoringService (`services/configuration_monitoring.py`)**

This new service provides real-time monitoring of configuration files on remote devices, using a hybrid approach of file watching (inotify) and periodic polling as a fallback.

**Key Responsibilities:**

-   Watch critical configuration files (`docker-compose.yml`, `nginx.conf`, etc.) for changes.
-   When a change is detected, trigger the `UnifiedDataCollectionService` to collect the new configuration.
-   Store configuration snapshots in the database to maintain a complete version history.
-   Emit `ConfigurationChangedEvent` for real-time updates and alerting.

### 3.4. **CacheManager (`services/cache_manager.py`)**

A dedicated caching service with configurable TTLs and an LRU (Least Recently Used) eviction policy to prevent memory exhaustion.

**Key Features:**

-   Provides `get_cached_data` and `store_data` methods.
-   Uses freshness thresholds defined in the `UnifiedDataCollectionService`.
-   Tracks cache hit/miss metrics for performance monitoring.

## 4. 🗄️ **Database Schema Changes**

The new architecture introduces several new database models to support the unified data collection and auditing goals. A fresh database schema will be implemented, so no complex data migration is required.

### **New Models:**

-   **`DataCollectionAudit` (`models/audit.py`)**: A TimescaleDB hypertable that logs every single data collection operation, whether from polling, API, or MCP. This provides a complete audit trail.
-   **`ConfigurationSnapshot` (`models/configuration.py`)**: Stores a complete snapshot of any monitored configuration file whenever a change is detected.
-   **`ConfigurationChangeEvent` (`models/configuration.py`)**: Records details about each configuration change, including the type of change, affected services, and risk level.
-   **`ServicePerformanceMetric` (`models/performance.py`)**: A hypertable to track the performance of the data collection services.
-   **`CacheMetadata` (`models/cache.py`)**: Tracks the state of the cache, including hits, misses, and evictions.

### **Rewritten Models:**

Existing models like `Device`, `SystemMetric`, `ContainerSnapshot`, and `DriveHealth` will be updated to integrate with the new unified services and relationships.

## 5. 🔄 **Data Flow & Interaction Diagram**

The following diagram illustrates the new, unified data flow:

```
+------------------+      +------------------+      +------------------+
|   API Endpoints  |      |   Polling Service|      |     MCP Tools    |
+------------------+      +------------------+      +------------------+
         |                        |                         |
         +------------------------+-------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
|               services.unified_data_collection.py                  |
|                (UnifiedDataCollectionService)                      |
+--------------------------------------------------------------------+
| 1. Check Cache (CacheManager)                                      |
| 2. Get Command Definition (CommandRegistry)                        |
| 3. Execute SSH Command (ssh_client)                                |
| 4. Parse Result (parsers)                                          |
| 5. Store in Database (models -> audit, metrics, configs)           |
| 6. Update Cache (CacheManager)                                     |
| 7. Emit Event (core.events)                                        |
+--------------------------------------------------------------------+
         ^                        |                         |
         |                        v                         v
+------------------+      +------------------+      +------------------+
| services.cache_  |      | services.command_|      |   core.database  |
| manager.py       |      | registry.py      |      | (SQLAlchemy)     |
+------------------+      +------------------+      +------------------+
```

## 6. 🔐 **Security & Auditing**

The new architecture incorporates robust security and auditing features, leveraging FastMCP's dependency injection system for accessing HTTP request data.

### 6.1. **Header-Based Authentication**

All MCP tools that perform sensitive operations will be secured using header-based authentication. The `get_http_headers()` dependency from FastMCP will be used to extract and validate `Authorization` tokens.

```python
# mcp/tools/base.py (or a new middleware file)
from fastmcp.server.dependencies import get_http_headers

async def get_current_user(headers: dict = Depends(get_http_headers)):
    token = headers.get("authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate token and return user
    user = await validate_token(token.split(" ")[1])
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
```

### 6.2. **Detailed Audit Trails**

The `DataCollectionAudit` model will be populated with rich contextual information extracted from the HTTP request. This will provide a comprehensive audit trail for all operations.

-   **Client IP Address**: The `request.client.host` attribute will be used to log the IP address of the client that initiated the operation.
-   **Request Path**: The `request.url.path` will be logged to identify the specific MCP tool or API endpoint that was called.
-   **User Agent**: The `user-agent` header will be stored to track the type of client making the request.

This information will be invaluable for security analysis, debugging, and understanding how the system is being used.

## 7. 🛣️ **Migration & Refactoring Path**

The transition to the new architecture will be performed in phases:

1.  **Phase 1: Build the Foundation**:
    -   Create the new database schema with all new and updated models.
    -   Implement the `UnifiedDataCollectionService`, `CommandRegistry`, `CacheManager`, and `ConfigurationMonitoringService`.
    -   Implement the new parsers.

2.  **Phase 2: Refactor Services**:
    -   Rewrite the `PollingService` to be a lightweight orchestrator that calls the `UnifiedDataCollectionService`.
    -   Remove all data collection logic from the `MetricsService` and `ContainerService`, and update them to call the `UnifiedDataCollectionService`.

3.  **Phase 3: Update API and MCP Layers**:
    -   Refactor all API endpoints to use the updated services. The `live=true` parameter will be replaced by a `force_refresh=True` parameter passed to the unified service.
    -   Refactor all MCP tools to call the new, unified API endpoints instead of performing their own SSH operations.

4.  **Phase 4: Deprecate and Remove Old Code**:
    -   Remove the old, duplicated SSH logic from all services.
    -   Delete the old `ssh_command_manager.py` as its functionality is now part of the `CommandRegistry` and `UnifiedDataCollectionService`.
    -   Simplify `ssh_client.py` to focus purely on connection management and raw command execution.

## 8. 🧪 **Testing Strategy**

-   **Unit Tests**: Each new service and component will have comprehensive unit tests.
-   **Integration Tests**:
    -   Test the full data collection flow from API call to database storage.
    -   Test the interaction between the `PollingService` and the `UnifiedDataCollectionService`.
    -   Test the configuration monitoring service with simulated file changes.
-   **Performance Tests**:
    -   Benchmark API response times for cached vs. non-cached data.
    -   Measure the reduction in SSH connections under load.
    -   Monitor cache hit/miss ratios.

## 9. 📈 **Expected Outcomes**

This new architecture will deliver significant improvements across the board:

-   **80-90% Reduction in SSH Connections**: Due to connection pooling and smart caching.
-   **Sub-100ms API Response Times**: For cached data.
-   **100% Audit Trail**: Every data collection operation will be logged.
-   **Real-time Configuration Monitoring**: Changes detected in milliseconds instead of minutes.
-   **Drastic Code Reduction**: ~800-1000 lines of duplicate code will be eliminated.
-   **Simplified Maintenance**: A single, clear code path for all data collection makes debugging and adding new features much easier.

This blueprint provides a clear path to a more robust, efficient, and maintainable infrastructure management system.