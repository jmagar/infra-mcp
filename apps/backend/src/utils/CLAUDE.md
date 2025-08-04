# Claude Memory for the Utils Layer

This document provides a high-level overview of the `utils` layer in the Infrastructor project. This layer contains utility functions and classes that are shared across the application.

## 1. Architectural Role and Vision

The `utils` layer provides a collection of reusable components and helper functions that support the other layers of the application.

**Core Principles:**

-   **Reusability**: The components in this layer are designed to be reusable and application-agnostic.
-   **Simplicity**: The utilities in this layer are designed to be simple and easy to use.
-   **Focus**: Each utility has a single, well-defined purpose.

## 2. Key Components

-   **`ssh_client.py`**: This module has been significantly **rewritten and simplified**. It is now solely responsible for managing SSH connections and executing raw commands. It no longer contains any business logic or command-specific knowledge. All command definitions, timeouts, and retries are now handled by the `CommandRegistry` in the `services` layer.
-   **`ssh_errors.py`**: This module has been **rewritten** to provide a unified system for classifying and handling SSH errors. It defines a comprehensive set of error types and provides a consistent way to handle them across the application.

## 3. Interaction with Other Layers

-   **Services Layer**: The `UnifiedDataCollectionService` uses the `ssh_client.py` module to execute SSH commands and the `ssh_errors.py` module to handle any errors that occur.
-   **All Layers**: Various utility functions may be used throughout the application as needed.

## 4. Key Files & Structure

```
apps/backend/src/utils/
├── __init__.py
├── ssh_client.py      # (REWRITTEN) Simplified SSH connection management
└── ssh_errors.py      # (REWRITTEN) Unified SSH error handling
```

The `utils` layer provides the essential building blocks that the rest of the application relies on. The simplification of the `ssh_client` is a key part of the new architecture, as it enforces the centralization of all command logic in the `services` layer.