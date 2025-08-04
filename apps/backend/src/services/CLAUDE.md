# Claude Memory for the Services Layer

This document provides a detailed overview of the `services` layer, which forms the core of the Infrastructor application's business logic. Understanding this layer is critical for any code generation or analysis task.

## 1. Architectural Role and Vision

The `services` layer implements the primary business logic of the application. It is responsible for orchestrating all data collection, processing, and storage. The central component of this layer is the **`UnifiedDataCollectionService`**, which acts as the single entry point for all infrastructure-related operations.

**Core Principles:**

-   **Centralization**: All data collection logic is centralized in the `UnifiedDataCollectionService`.
-   **Decoupling**: The services are decoupled from the API and MCP layers, which act as thin wrappers around them.
-   **Modularity**: The services are broken down into small, focused components with clear responsibilities (e.g., caching, command registration, configuration monitoring).
-   **Auditability**: Every operation performed by the services is audited, providing a complete historical record.

## 2. The UnifiedDataCollectionService

The `UnifiedDataCollectionService` (`services/unified_data_collection.py`) is the most important component in the new architecture. It replaces all previous data collection logic and provides a single, consistent interface for all data-related operations.

**Key Responsibilities:**

-   **Orchestration**: It orchestrates the entire data collection process, from checking the cache to executing commands and storing the results.
-   **Caching**: It interacts with the `CacheManager` to store and retrieve cached data, based on predefined freshness thresholds.
-   **Command Execution**: It uses the `CommandRegistry` to get command definitions and the `ssh_client` to execute them.
-   **Data Persistence**: It is responsible for storing all collected data in the appropriate database models, including creating audit trail entries.
-   **Event Emission**: It emits events after data collection to notify other parts of the system of changes.

**A call to any method in this service is the *only* correct way to collect data from infrastructure.**

## 3. Supporting Services

The `UnifiedDataCollectionService` is supported by several other new services:

-   **`CommandRegistry` (`services/command_registry.py`)**: A central repository for all SSH command definitions. It eliminates duplicate command strings and provides a single place to manage timeouts, retries, and parsing logic.
-   **`CacheManager` (`services/cache_manager.py`)**: A dedicated caching service with an LRU (Least Recently Used) eviction policy. It is responsible for all caching logic.
-   **`ConfigurationMonitoringService` (`services/configuration_monitoring.py`)**: A new service that provides real-time monitoring of configuration files on remote devices using a hybrid of file watching (inotify) and polling.
-   **`PerformanceTracker` (`services/performance_tracker.py`)**: A service for tracking the performance of the data collection services and storing the results in the `ServicePerformanceMetric` model.

## 4. Refactored Services

-   **`PollingService` (`services/polling_service.py`)**: This service is now a lightweight orchestrator. Its only job is to call the `UnifiedDataCollectionService` on a schedule. It contains no data collection logic itself.
-   **`MetricsService` & `ContainerService`**: These services have been stripped of all data collection logic. They now simply delegate all calls to the `UnifiedDataCollectionService`.

## 5. Key Files & Structure

```
apps/backend/src/services/
├── __init__.py
├── cache_manager.py           # (NEW) Caching service
├── command_registry.py        # (NEW) Central repository for SSH commands
├── configuration_monitoring.py# (NEW) Real-time config file monitoring
├── polling_service.py         # (REWRITTEN) Lightweight orchestrator
├── performance_tracker.py     # (NEW) Performance tracking service
├── unified_data_collection.py # (NEW) The core of the new architecture
└── parsers/                   # (NEW) Data parsers for SSH command output
    ├── __init__.py
    ├── base_parser.py
    └── ...
```

This services layer represents a fundamental shift from a fragmented, duplicated architecture to a centralized, unified, and highly efficient system. All future development should adhere to these new patterns.