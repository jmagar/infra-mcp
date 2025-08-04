# Claude Memory for the Core Layer

This document provides a high-level overview of the `core` layer in the Infrastructor project. This layer contains the foundational components and shared infrastructure that the rest of the application is built upon.

## 1. Architectural Role and Vision

The `core` layer is the heart of the application, providing the essential services and configurations needed for the system to operate. It is responsible for:

-   **Configuration Management**: Loading and providing access to application settings.
-   **Database Connectivity**: Managing the database connection pool and session lifecycle.
-   **Event System**: Defining and dispatching events across the application.
-   **Centralized Exceptions**: Defining custom exception types for consistent error handling.

**Core Principles:**

-   **Application-Agnostic**: The components in this layer are designed to be generic and reusable across the application.
-   **Single Source of Truth**: This layer provides the single source of truth for configuration and database connections.
-   **High Cohesion**: The modules in this layer are tightly related and focused on providing the core application infrastructure.

## 2. Key Components

-   `config.py`: Defines the application's configuration settings using Pydantic. It loads settings from environment variables and `.env` files.
-   `database.py`: Manages the SQLAlchemy database engine and session creation. It is responsible for creating the database connection pool and providing session objects to the rest of the application.
-   `events.py`: Defines the application's event system using a simple pub/sub pattern. This allows for decoupled communication between different parts of the application.
-   `exceptions.py`: Defines a set of custom exception classes that are used throughout the application to represent specific error conditions.

## 3. Interaction with Other Layers

-   **Services Layer**: The `services` layer uses the `database.py` module to get database sessions and the `events.py` module to dispatch events.
-   **API and MCP Layers**: These layers use the `exceptions.py` module for error handling and the `database.py` module for database access (via dependency injection).
-   **All Layers**: All layers of the application use the `config.py` module to access configuration settings.

## 4. Key Files & Structure

```
apps/backend/src/core/
├── __init__.py
├── config.py          # Application configuration settings
├── database.py        # Database connection management
├── events.py          # Event bus and event definitions
└── exceptions.py      # Custom exception classes
```

Understanding the `core` layer is essential for understanding how the application is bootstrapped and how its various components are connected.