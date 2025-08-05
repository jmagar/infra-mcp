# FastMCP Server Testing Guide: In-Memory & Integration Patterns

This guide provides a comprehensive overview of setting up a robust testing environment for the FastMCP server, focusing on in-memory testing for speed and isolation, as well as advanced integration patterns for end-to-end validation.

## 📋 **Testing Philosophy**

Our testing strategy is built on the following principles:

1.  **Isolation**: Unit tests should be completely isolated, using in-memory implementations and mocks to prevent external dependencies (network, disk).
2.  **Speed**: The test suite must run quickly to encourage frequent execution. In-memory testing is key to achieving this.
3.  **Realism**: Integration tests should closely mimic the production environment, using a shared application context to validate the interactions between FastAPI, MCP, and shared services.
4.  **Comprehensiveness**: The testing suite must cover tool logic, middleware, dependency injection, error handling, and advanced integration patterns.

---

## **Phase 1: In-Memory Test Server Setup**

The foundation of our testing strategy is the `InMemoryTestServer`, which allows us to run the MCP server without network sockets, providing significant performance gains.

### **1.1 Create the In-Memory Test Harness**

```python
# tests/mcp/conftest.py
import pytest
from fastmcp.testing import InMemoryTestServer
from typing import AsyncGenerator

from my_mcp_project.server import create_mcp_server # Your server factory

@pytest.fixture
async def mcp_test_server() -> AsyncGenerator[InMemoryTestServer, None]:
    """
    Provides a fully initialized, in-memory MCP server for testing.
    """
    server = await create_mcp_server()
    test_server = InMemoryTestServer(server)
    await test_server.start_server()
    try:
        yield test_server
    finally:
        await test_server.stop_server()
```

### **1.2 Create the Asynchronous Test Client**

The `TestClient` connects to the `InMemoryTestServer` and provides a simple interface for sending requests and receiving responses.

```python
# tests/mcp/conftest.py (continued)
from fastmcp.testing import TestClient

@pytest.fixture
async def mcp_test_client(mcp_test_server: InMemoryTestServer) -> AsyncGenerator[TestClient, None]:
    """
    Provides a client connected to the in-memory MCP test server.
    """
    async with mcp_test_server.get_client() as client:
        yield client
```

### **1.3 Writing a Basic In-Memory Test**

Now, you can write simple, fast, and isolated tests for your MCP tools.

```python
# tests/mcp/test_basic_tools.py
import pytest
from fastmcp.testing import TestClient

@pytest.mark.asyncio
async def test_get_system_health(mcp_test_client: TestClient):
    """
    Tests the 'get_system_health' tool using the in-memory server.
    """
    # Act: Call the tool
    response = await mcp_test_client.call_tool(
        "get_system_health",
        {"component": "database"}
    )

    # Assert: Validate the response
    assert response["status"] == "ok"
    assert response["data"]["component"] == "database"
    assert response["data"]["healthy"] is True
```

---

## **Phase 2: Mocking and Dependency Injection**

For true unit testing, we must replace external services (database, SSH clients, APIs) with mocks. We leverage `pytest` fixtures and dependency injection for this.

### **2.1 Mocking the Unified Data Service**

```python
# tests/mcp/mocks.py
from unittest.mock import MagicMock, AsyncMock

def create_mock_unified_service() -> MagicMock:
    """Creates a mock of the UnifiedDataCollectionService."""
    mock_service = MagicMock()
    mock_service.get_container_data = AsyncMock(
        return_value={"status": "success", "containers": []}
    )
    mock_service.get_system_metrics = AsyncMock(
        return_value={"status": "success", "cpu": {"usage": 10.5}}
    )
    return mock_service

# tests/mcp/conftest.py (updated)
from my_mcp_project.dependencies import get_unified_service # Your dependency getter

@pytest.fixture
def mock_unified_service() -> MagicMock:
    return create_mock_unified_service()

@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch, mock_unified_service):
    """Override dependencies for all tests in this module."""
    monkeypatch.setattr(
        "my_mcp_project.server.app.dependency_overrides",
        {get_unified_service: lambda: mock_unified_service}
    )
```

### **2.2 Testing with Mocked Dependencies**

Tests will now run against the mock service, ensuring they are fast and predictable.

```python
# tests/mcp/test_container_tools.py
import pytest
from fastmcp.testing import TestClient
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_manage_containers_with_mock(
    mcp_test_client: TestClient,
    mock_unified_service: MagicMock
):
    """Tests container management tool with a mocked backend service."""
    # Act
    await mcp_test_client.call_tool("manage_containers", {"action": "stop", "containers": "all"})

    # Assert
    mock_unified_service.stop_all_containers.assert_called_once()
```

---

## **Phase 3: Advanced Integration Testing**

While unit tests are essential, we also need to validate the full stack. For this, we use a shared application context that both the FastAPI test client and the MCP test client can use.

### **3.1 Shared Application Lifespan for Testing**

We'll use a fixture to manage the lifecycle of the entire application, including the database, SSH pools, and other shared resources.

```python
# tests/integration/conftest.py
import pytest
from httpx import AsyncClient
from fastmcp.testing import InMemoryTestServer, TestClient

from my_mcp_project.main import app # Your FastAPI app
from my_mcp_project.server import create_mcp_server

@pytest.fixture(scope="session")
async def full_app_test_harness():
    """
    Creates a full test harness with a shared context for both
    the FastAPI app and the MCP server.
    """
    # Use a test database
    # Override settings to use in-memory SQLite or a test Postgres DB
    # ...

    mcp_server = await create_mcp_server()
    mcp_test_server = InMemoryTestServer(mcp_server)
    await mcp_test_server.start_server()

    async with AsyncClient(app=app, base_url="http://test") as http_client, \
               mcp_test_server.get_client() as mcp_client:
        yield http_client, mcp_client

    await mcp_test_server.stop_server()
```

### **3.2 Writing End-to-End Integration Tests**

These tests validate complete user workflows that span both the API and MCP tools.

```python
# tests/integration/test_workflows.py
import pytest

@pytest.mark.asyncio
async def test_device_provisioning_workflow(full_app_test_harness):
    """
    Tests a complete workflow:
    1. Add a device via API.
    2. Verify its status via MCP tool.
    3. Trigger a configuration sync via another MCP tool.
    4. Check the sync status via API.
    """
    http_client, mcp_client = full_app_test_harness

    # Step 1: Add a new device via the API
    response = await http_client.post("/api/devices", json={"hostname": "new-test-device"})
    assert response.status_code == 201
    device_id = response.json()["id"]

    # Step 2: Verify device health via an MCP tool
    mcp_response = await mcp_client.call_tool("get_device_health", {"device_id": device_id})
    assert mcp_response["data"]["status"] == "healthy"

    # Step 3: Trigger a configuration sync via MCP
    mcp_response = await mcp_client.call_tool("sync_configuration", {"device_id": device_id})
    assert mcp_response["status"] == "ok"
    sync_job_id = mcp_response["data"]["job_id"]

    # Step 4: Check sync job status via API
    response = await http_client.get(f"/api/jobs/{sync_job_id}")
    assert response.json()["status"] == "completed"
```

## **Testing Destructive Action Protection**

Special care must be taken to test the tentpole destructive action protection system.

```python
# tests/mcp/test_destructive_actions.py
import pytest
from fastmcp.testing import TestClient

@pytest.mark.asyncio
async def test_bulk_stop_is_blocked(mcp_test_client: TestClient):
    """Ensures the destructive action protection blocks unsafe commands."""
    # Act
    response = await mcp_test_client.call_tool(
        "execute_shell_command",
        {"device": "ubuntu-server", "command": "docker stop $(docker ps -q)"}
    )

    # Assert
    assert response["status"] == "DESTRUCTIVE_ACTION_BLOCKED"
    assert response["risk_assessment"]["risk_level"] == "HIGH"
    assert "confirmation_required" in response
    assert "operation_id" in response

@pytest.mark.asyncio
async def test_confirmation_workflow(mcp_test_client: TestClient):
    """Tests the full confirmation and execution workflow."""
    # Step 1: Trigger the destructive action
    blocked_response = await mcp_test_client.call_tool(
        "execute_shell_command",
        {"device": "ubuntu-server", "command": "docker stop $(docker ps -q)"}
    )
    operation_id = blocked_response["operation_id"]
    confirmation_phrase = blocked_response["confirmation_required"]["phrase"]

    # Step 2: Confirm the action with the correct phrase
    confirmation_response = await mcp_test_client.call_tool(
        "confirm-destructive-operation",
        {"operation_id": operation_id, "confirmation_phrase": confirmation_phrase}
    )

    # Assert
    assert confirmation_response["status"] == "confirmed"
    # Further assertions can be made by mocking the execution backend
    # to verify the command was actually dispatched after confirmation.
```

By combining fast in-memory unit tests with comprehensive end-to-end integration tests, we can ensure the reliability, correctness, and performance of our entire infrastructure management platform.