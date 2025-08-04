# Claude Memory for the MCP Layer

This document provides a high-level overview of the Model-Context-Promise (MCP) layer in the Infrastructor project, designed to give Claude context for code generation, analysis, and modifications.

## 1. Architectural Role and Vision

The MCP layer provides a powerful, programmatic interface to the infrastructure, designed for use by autonomous agents and advanced scripts. It exposes the system's capabilities as a set of tools and resources that can be composed to perform complex tasks.

**Core Principles:**

-   **Tool-Based Interface**: All infrastructure operations are exposed as well-defined MCP tools with clear schemas.
-   **Resource-Oriented**: Key infrastructure components (devices, containers, configurations) are exposed as MCP resources.
-   **Seamless Integration**: The MCP layer is tightly integrated with the FastAPI backend, sharing the same core services and data models.
-   **Transformation and Abstraction**: The MCP layer uses FastMCP's tool transformation capabilities to abstract away the complexity of the underlying API, providing a simplified and more intuitive interface for agents.

## 2. Key MCP Components

The MCP layer is composed of three main components:

-   `server.py`: The main MCP server, responsible for defining and serving the available tools and resources.
-   `tools/`: A collection of Python modules that define the MCP tools. Each tool corresponds to a specific infrastructure operation.
-   `resources/`: A collection of modules that define the MCP resources, providing access to infrastructure data.

## 3. Data Flow and Service Interaction

The MCP layer follows the same data flow principles as the API layer, relying on the `UnifiedDataCollectionService` for all data collection.

**Standard Data Flow:**

1.  An MCP client makes a request to execute a tool.
2.  The MCP server receives the request and invokes the corresponding tool function.
3.  The tool function calls the appropriate method on the `UnifiedDataCollectionService` or another core service.
4.  The service handles the data collection, caching, and database interaction.
5.  The tool formats the result and returns it to the MCP client.

**Direct API interaction is discouraged.** All operations should go through the unified service layer to ensure consistency and auditing.

## 4. Authentication and Security

-   MCP tools are secured using header-based authentication, leveraging FastMCP's dependency injection system (`get_http_headers`).
-   A `get_current_user` dependency is used to validate tokens and provide user context to the tools.
-   This ensures that all MCP operations are authenticated and authorized, and that all actions are audited with the correct user information.

## 5. Tool Transformation

A key feature of the MCP layer is the use of tool transformation to create a more user-friendly and intelligent interface.

-   **Parameter Hiding**: Complex parameters like `ssh_timeout` and `auth_token` are hidden from the user and automatically injected by the transformation layer.
-   **Device-Aware Tools**: The MCP layer provides device-aware tools (e.g., `get_proxmox_metrics`) that automatically determine the correct parameters based on the device type.
-   **Safety Features**: Destructive operations are protected by a confirmation system that requires explicit user consent.

## 6. Key Files & Structure

```
apps/backend/src/mcp/
├── __init__.py
├── server.py              # Main MCP server
├── resources/             # MCP resources
│   ├── __init__.py
│   └── ...
└── tools/                 # MCP tools
    ├── __init__.py
    └── ...
```

By leveraging these patterns, the MCP layer provides a powerful, secure, and easy-to-use interface for programmatic access to the infrastructure, while maintaining the same level of consistency and auditability as the API layer.