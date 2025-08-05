# Claude Memory for the Schemas Layer

This document provides a high-level overview of the `schemas` layer in the Infrastructor project. This layer is responsible for data validation, serialization, and defining the data contracts for the API and MCP layers.

## 1. Architectural Role and Vision

The `schemas` layer uses Pydantic to define the shape of the data that is exchanged between the client and the server. It serves as the single source of truth for the application's data contracts.

**Core Principles:**

-   **Data Validation**: All incoming data is validated against the Pydantic schemas to ensure that it is well-formed and meets the application's requirements.
-   **Serialization**: The schemas are used to serialize data from the database models into JSON for API and MCP responses.
-   **Clear Contracts**: The schemas provide a clear and explicit definition of the data that is expected and returned by the application's interfaces.
-   **Decoupling**: The schemas provide a layer of decoupling between the database models and the API/MCP layers, allowing the internal data representation to change without affecting the external API.

## 2. Key Schema Types

The `schemas` layer contains several types of schemas:

-   **Create Schemas**: Used for validating data when creating new resources (e.g., `DeviceCreate`).
-   **Update Schemas**: Used for validating data when updating existing resources (e.g., `DeviceUpdate`).
-   **Response Schemas**: Used for serializing data for API and MCP responses (e.g., `DeviceResponse`).
-   **Filter Schemas**: Used for defining the available filter parameters for list endpoints.

## 3. Interaction with Other Layers

-   **API Layer**: The API layer uses the schemas for request body validation and response serialization. FastAPI automatically uses the Pydantic schemas to validate incoming data and serialize outgoing data.
-   **MCP Layer**: The MCP layer uses the schemas to define the input and output schemas for its tools.
--   **Services Layer**: The services layer uses the schemas to ensure that the data it receives and returns is well-formed.

## 4. New Schemas in the Unified Architecture

The new architecture introduces several new schemas to support the new features:

-   **`audit.py`**: Schemas for the `DataCollectionAudit` model.
-   **`configuration.py`**: Schemas for the `ConfigurationSnapshot` and `ConfigurationChangeEvent` models.
-   **`performance.py`**: Schemas for the `ServicePerformanceMetric` model.
-   **`cache.py`**: Schemas for the `CacheMetadata` model.

## 5. Key Files & Structure

```text
apps/backend/src/schemas/
├── __init__.py
├── audit.py                   # (NEW) Schemas for audit trail
├── cache.py                   # (NEW) Schemas for cache management
├── common.py                  # Shared schema components
├── configuration.py           # (NEW) Schemas for configuration management
├── container.py               # Schemas for container data
├── device.py                  # Schemas for device management
├── ...                        # Other existing schemas
└── performance.py             # (NEW) Schemas for performance metrics
```

By using Pydantic schemas, the application ensures that all data is validated and consistently structured, which improves the reliability and maintainability of the codebase.