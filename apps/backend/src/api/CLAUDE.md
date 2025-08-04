# Claude Memory for the API Layer

This document provides a high-level overview of the API layer in the Infrastructor project, designed to give Claude context for code generation, analysis, and modifications.

## 1. Architectural Role and Vision

The API layer serves as the primary synchronous interface for interacting with the infrastructure. It is responsible for handling on-demand requests from the UI, MCP tools, and external systems.

**Core Principles:**

-   **Thin & Stateless**: The API layer is designed to be a thin wrapper around the `UnifiedDataCollectionService`. It contains minimal business logic and is primarily responsible for request handling, authentication, and data formatting.
-   **Consistent Interface**: All API endpoints follow a consistent design pattern, providing a predictable and easy-to-use interface for all infrastructure operations.
-   **Real-time & On-Demand**: The API is optimized for real-time, on-demand data collection, with a `force_refresh` parameter to bypass the cache when necessary.

## 2. Key API Endpoints

The API is organized into several resource-based modules:

-   `devices.py`: Manages device registration, discovery, and status.
-   `containers.py`: Handles Docker container management (start, stop, status).
-   `monitoring.py`: Provides access to real-time system metrics.
-   `proxy.py`: Manages Nginx proxy configurations.
-   `system.py`: Provides system-level information, such as performance metrics and cache status.

**Example Endpoint Pattern:**

```python
# api/containers.py

@router.get("/devices/{device_id}/containers")
async def get_device_containers(
    device_id: UUID,
    force_refresh: bool = Query(False, description="Force fresh data collection"),
    service: UnifiedDataCollectionService = Depends(get_unified_service)
):
    return await service.get_container_data(device_id, force_refresh)
```

## 3. Data Flow and Service Interaction

The API layer **does not** contain any direct SSH or data collection logic. All data is retrieved through the `UnifiedDataCollectionService`.

**Standard Data Flow:**

1.  An HTTP request is received by a FastAPI endpoint.
2.  The endpoint uses dependency injection to get an instance of the `UnifiedDataCollectionService`.
3.  The endpoint calls the appropriate method on the unified service (e.g., `get_container_data`).
4.  The unified service handles all the complexity of caching, command execution, and database interaction.
5.  The API endpoint formats the result from the service and returns it as a JSON response.

## 4. Authentication and Authorization

-   API endpoints are secured using JWT-based authentication.
-   A `get_current_user` dependency is used to protect routes and provide user context.
-   The user context is passed to the `UnifiedDataCollectionService` to ensure that all operations are properly audited.

## 5. Error Handling

-   The API layer uses a centralized exception handling middleware.
-   Custom exceptions defined in `core/exceptions.py` are used to represent specific error conditions.
-   The middleware catches these exceptions and converts them into appropriate HTTP responses.

## 6. Key Files & Structure

```
apps/backend/src/api/
├── __init__.py
├── common.py          # Shared utilities and dependencies
├── containers.py      # Docker container endpoints
├── devices.py         # Device management endpoints
├── monitoring.py      # System metrics endpoints
├── proxy.py           # Nginx proxy endpoints
└── system.py          # System-level endpoints
```

By adhering to these patterns, the API layer remains clean, maintainable, and decoupled from the underlying data collection logic, ensuring that all interactions with the infrastructure are consistent and audited.