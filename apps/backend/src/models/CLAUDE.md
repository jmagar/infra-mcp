# Claude Memory for the Models Layer

This document provides a high-level overview of the data models in the Infrastructor project, designed to give Claude context on how data is structured and stored.

## 1. Architectural Role and Vision

The `models` layer defines the application's database schema using SQLAlchemy. It represents the single source of truth for how data is structured and persisted.

**Core Principles:**

-   **Declarative Mapping**: All models are defined using the SQLAlchemy declarative base, providing a clear and concise way to map Python classes to database tables.
-   **TimescaleDB Integration**: Time-series data is stored in TimescaleDB hypertables, with appropriate compression and retention policies.
-   **Data Integrity**: The models enforce data integrity through the use of foreign keys, constraints, and relationships.
-   **Unified Schema**: The new architecture introduces a unified schema for auditing and configuration management, providing a complete and consistent view of the system's state.

## 2. Key Data Models

The `models` layer is organized into several modules, each representing a different aspect of the system:

-   **`device.py`**: Defines the `Device` model, which is the central registry for all managed infrastructure.
-   **`metrics.py`**: Contains the models for time-series metrics, such as `SystemMetric` and `DriveHealth`. These are all TimescaleDB hypertables.
-   **`container.py`**: Defines the `ContainerSnapshot` model for storing historical container data.
-   **`proxy_config.py`**: Manages the sophisticated proxy configuration models.
-   **`audit.py`**: **(NEW)** Defines the `DataCollectionAudit` model, which provides a complete audit trail for all data collection operations.
-   **`configuration.py`**: **(NEW)** Contains the `ConfigurationSnapshot` and `ConfigurationChangeEvent` models for tracking changes to configuration files.
-   **`performance.py`**: **(NEW)** Defines the `ServicePerformanceMetric` model for tracking the performance of the data collection services.
-   **`cache.py`**: **(NEW)** Contains the `CacheMetadata` model for tracking the state of the cache.

## 3. Relationships and Data Integrity

-   All models are linked via foreign keys to ensure referential integrity.
-   The `Device` model is the central point of the schema, with most other models having a direct or indirect relationship to it.
-   Cascading deletes are used to ensure that when a device is deleted, all of its associated data is also removed.

## 4. TimescaleDB Hypertables

The following models are implemented as TimescaleDB hypertables for efficient time-series data storage:

-   `DataCollectionAudit`
-   `ConfigurationSnapshot`
-   `ConfigurationChangeEvent`
-   `ServicePerformanceMetric`
-   `SystemMetric`
-   `DriveHealth`
-   `ContainerSnapshot`

These tables are configured with appropriate `chunk_time_interval`, compression, and retention policies to optimize performance and storage.

## 5. Key Files & Structure

```plaintext
apps/backend/src/models/
├── __init__.py
├── audit.py                   # (NEW) DataCollectionAudit model
├── cache.py                   # (NEW) CacheMetadata model
├── configuration.py           # (NEW) ConfigurationSnapshot, ConfigurationChangeEvent
├── container.py               # (REWRITTEN) ContainerSnapshot model
├── device.py                  # (REWRITTEN) Device model
├── metrics.py                 # (REWRITTEN) SystemMetric, DriveHealth models
├── performance.py             # (NEW) ServicePerformanceMetric model
└── proxy_config.py            # (REWRITTEN) ProxyConfig models
```

Understanding the data models is crucial for understanding how the application's state is stored and managed. The new models introduced in this architecture provide a comprehensive and unified view of the system's operations.