# **Phase 4: Advanced FastMCP Integration Patterns (Weeks 7-8)**

This phase focuses on evolving the architecture from two separate services (FastAPI and MCP) communicating over HTTP into a deeply integrated, unified application. By leveraging advanced patterns from FastMCP, we will share resources, middleware, and context, leading to a more efficient, maintainable, and powerful system.

## **Sophisticated FastAPI+MCP Shared Architecture**

This section details the core architectural changes required to create a single, cohesive application fabric.

### **71. Create `InfrastructorMCPIntegration` class for advanced integration patterns**

**Objective:** To create a central class that manages the lifecycle and shared context of both the FastAPI and MCP servers.

**Architecture:** The `InfrastructorMCPIntegration` class will be the heart of the unified application. It will be responsible for initializing shared resources (like database and SSH pools), setting up middleware, and managing the startup and shutdown sequences for both servers. This encapsulates the integration logic, keeping the main application file clean.

```python
# apps/backend/src/core/integration_manager.py

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
import structlog

from ..services.ssh_client_manager import SSHClientManager
from ..core.database import create_database_pool, create_redis_client

logger = structlog.get_logger(__name__)

class InfrastructorMCPIntegration:
    """
    Manages the integrated lifecycle of the FastAPI and MCP servers,
    including shared resources and context.
    """
    def __init__(self, fastapi_app, mcp_server):
        self.fastapi_app = fastapi_app
        self.mcp_server = mcp_server
        self.shared_context: Dict[str, Any] = {}

    @asynccontextmanager
    async def lifespan(self, app):
        """
        A unified application lifespan manager for both servers.
        Initializes all shared resources and ensures graceful shutdown.
        """
        async with self._initialize_database_context() as db_context, \
                     self._initialize_ssh_pool_context() as ssh_context, \
                     self._initialize_cache_context() as cache_context:

            self.shared_context.update(db_context)
            self.shared_context.update(ssh_context)
            self.shared_context.update(cache_context)
            
            app.state.shared_context = self.shared_context
            self.mcp_server.app_context = self.shared_context
            
            logger.info("Unified application startup complete. Resources shared.")
            
            yield
            
            logger.info("Unified application shutdown initiated.")
```

### **72. Implement nested lifecycle management with `asynccontextmanager`**

**Objective:** To ensure resources are initialized and shut down in the correct order, preventing race conditions and resource leaks.

**Architecture:** The `lifespan` method in the integration class will use nested `asynccontextmanager`s. This Python feature is ideal for managing resources that have setup and teardown phases. The nesting ensures a strict "first-in, last-out" (FILO) order for cleanup.

```python
# apps/backend/src/core/integration_manager.py (continued)

    @asynccontextmanager
    async def _initialize_database_context(self):
        """Manages the database connection pool lifecycle."""
        db_pool = None
        try:
            db_pool = await create_database_pool()
            logger.info("Database pool initialized.")
            yield {"db_pool": db_pool}
        finally:
            if db_pool:
                await db_pool.close()
                logger.info("Database pool closed.")

    @asynccontextmanager
    async def _initialize_ssh_pool_context(self):
        """Manages the SSH connection pool lifecycle."""
        ssh_manager = None
        try:
            ssh_manager = SSHClientManager()
            await ssh_manager.initialize_pools_from_db()
            logger.info("SSH connection pools initialized.")
            yield {"ssh_manager": ssh_manager}
        finally:
            if ssh_manager:
                await ssh_manager.close_all_pools()
                logger.info("SSH connection pools closed.")
    
    @asynccontextmanager
    async def _initialize_cache_context(self):
        """Manages the cache (e.g., Redis) connection lifecycle."""
        cache_client = None
        try:
            cache_client = await create_redis_client()
            logger.info("Cache client initialized.")
            yield {"cache_client": cache_client}
        finally:
            if cache_client:
                await cache_client.close()
                logger.info("Cache client closed.")
```

### **73. Create shared database context management across FastAPI and MCP**

**Objective:** To allow both FastAPI endpoints and MCP tools to use the same database connection pool, reducing resource consumption and ensuring transactional consistency.

**Architecture:** The database pool, created during the shared lifespan, will be stored in the `shared_context`. A dependency injection system will provide sessions from this shared pool to any function (in either FastAPI or MCP) that needs them.

### **74. Implement shared SSH pool context with health monitoring**

**Objective:** To unify all SSH operations through a single, monitored connection manager accessible to the entire application.

**Architecture:** The `SSHClientManager` instance will be a singleton living in the `shared_context`. A background task, also started during the lifespan, will periodically run health checks on the SSH connections, pruning stale or dead connections.

### **75. Create shared cache context with performance tracking**

**Objective:** To enable a unified caching layer where an operation in one part of the system can create a cache entry that is immediately available to another part.

**Architecture:** A `CacheManager` instance (using Redis) will be initialized in the shared lifespan. It will track performance metrics like hit/miss ratios, which can be exposed via a shared health endpoint.

### **76. Implement `SharedInfrastructureMiddleware` for cross-cutting concerns**

**Objective:** To apply common logic like logging, authentication, and error handling to both FastAPI requests and MCP tool calls without duplicating code.

**Architecture:** We will create a `SharedInfrastructureMiddleware` that contains the core logic. This middleware will be applied to the FastAPI app. The MCP server will then be configured to forward its calls *through* the FastAPI app's middleware stack, ensuring every operation passes through the same pipeline.

```python
# apps/backend/src/core/middleware.py
import time
import uuid
import structlog
from fastapi import Request, Response

logger = structlog.get_logger(__name__)

class SharedInfrastructureMiddleware:
    async def __call__(self, request: Request, call_next):
        correlation_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        
        start_time = time.time()
        logger.info("Operation started", path=request.url.path, method=request.method)
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info("Operation finished", duration=round(duration, 4), status_code=response.status_code)
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Operation failed", duration=round(duration, 4), error=str(e))
            response = Response(content="Internal Server Error", status_code=500)

        return response
```

### **77. Create unified authentication and authorization for both FastAPI and MCP**

**Objective:** To secure the entire platform with a single, consistent authentication and authorization model.

**Architecture:** The authentication logic will be implemented once in the `SharedInfrastructureMiddleware`. It will inspect the `Authorization` header. For MCP calls, the token will be passed in the call's `context`. The middleware will validate the token and attach a `user` object to the request state.

### **78. Implement correlation ID management across both interfaces**

**Objective:** To enable comprehensive tracing of operations as they flow through the system.

**Architecture:** The `SharedInfrastructureMiddleware` is responsible for generating a correlation ID for every incoming operation. This ID will be bound to the `structlog` context and passed along in any subsequent calls. All log messages will automatically include this ID, allowing for easy tracing.

### **79. Create shared dependency injection patterns with `MCPDepends`**

**Objective:** To make accessing shared resources simple and consistent for developers, whether they are writing an API endpoint or an MCP tool.

**Architecture:** We will create a set of shared dependency provider functions. FastAPI endpoints will use `fastapi.Depends`, while MCP tools will use `fastmcp.dependencies.MCPDepends`.

```python
# apps/backend/src/core/dependencies.py
from fastapi import Request, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from fastmcp import Tool
from fastmcp.dependencies import MCPDepends

from ..models.device import Device

router = APIRouter()

# Provider function
async def get_db_session(request: Request) -> AsyncSession:
    async with request.app.state.shared_context["db_pool"].begin() as session:
        yield session

# FastAPI usage
@router.get("/devices")
async def list_devices(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Device))
    devices = result.scalars().all()
    return [{"id": dev.id, "hostname": dev.hostname} for dev in devices]

# MCP usage
@Tool(name="get_device_health", description="Get health of a specific device")
async def get_device_health(device_name: str, db: AsyncSession = MCPDepends(get_db_session)):
    query = select(Device).where(Device.hostname == device_name)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    if device:
        return {"status": "ok", "device_id": device.id}
    return {"status": "error", "message": "Device not found"}
```

### **80. Implement unified error handling with automatic recovery attempts**

**Objective:** To centralize error handling, ensuring that exceptions are caught, logged, and responded to consistently, with a chance for automatic recovery.

**Architecture:** A custom exception handler in the `SharedInfrastructureMiddleware` will catch exceptions. It will log the error, then pass it to a `RecoveryManager` service. If the error is recoverable (e.g., a temporary database deadlock), it will attempt a recovery procedure (e.g., retry the transaction). Otherwise, it formats a standardized JSON error response.

### **81. Create performance monitoring integration across both systems**

**Objective:** To collect and expose performance metrics from a single, unified source.

**Architecture:** The `SharedInfrastructureMiddleware` will record the duration of every operation. This data will be sent to the `ServicePerformanceMetric` TimescaleDB table. A single API endpoint (`/api/performance/summary`) can then provide a holistic view of the application's performance.

### **82. Implement shared rate limiting and throttling mechanisms**

**Objective:** To protect the application from abuse or overload with a single, globally-aware rate-limiting system.

**Architecture:** A rate-limiting library (like `slowapi`) will be configured in the `SharedInfrastructureMiddleware`. It will use the shared Redis cache to track request counts. Because all operations flow through this middleware, the rate limit will apply globally.

---

## **Purpose-Built MCP Tools (Not Direct API Conversion)**

This section focuses on creating a suite of high-level, intelligent MCP tools that encapsulate complex workflows, providing a more intuitive and powerful interface than raw API endpoints.

### **83. Create infrastructure health monitoring tool with comprehensive diagnostics**

**Objective:** A single tool to get a complete health overview of the entire infrastructure.

**Architecture:** The `diagnose_infrastructure` tool will act as an orchestrator, making parallel calls to various internal services using `asyncio.gather` for efficiency.
1.  **Device Discovery:** Fetches all registered devices from the `DeviceService`.
2.  **Parallel Diagnostics:** For each device, it concurrently calls the `UnifiedDataCollectionService` to get metrics, container summaries, and configuration status.
3.  **System-Wide Checks:** It also calls the `PerformanceService` for API health and the `DatabaseService` for DB health (connection pool, replication lag).
4.  **Aggregation & Scoring:** The results are compiled into a single report. A health score is calculated based on errors, warnings, and performance deviations.

```python
# apps/backend/src/mcp/tools/infrastructure_diagnostics.py
@Tool(name="diagnose_infrastructure", description="Get a comprehensive health overview of the entire infrastructure.")
async def diagnose_infrastructure(
    device_service: DeviceService = MCPDepends(get_device_service),
    data_service: UnifiedDataCollectionService = MCPDepends(get_unified_data_service)
):
    devices = await device_service.get_all_active_devices()
    tasks = [data_service.get_device_health_summary(d.id) for d in devices]
    device_health_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # ... aggregate results and calculate a final health score ...
    return {"overall_status": "HEALTHY", "devices_checked": len(devices), "issues_found": 0}
```

### **84. Implement device diagnostics tool with capability detection**

**Objective:** A tool to perform a deep-dive diagnostic on a single device, tailoring its checks to the services running on that device.

**Architecture:** The `diagnose_device(device_name: str)` tool will be context-aware.
1.  **Capability Detection:** It executes a series of lightweight SSH commands (`command -v docker`, `command -v zpool`) to determine device capabilities.
2.  **Targeted Health Checks:** Based on capabilities, it runs specific diagnostics via the `UnifiedDataCollectionService` (e.g., `docker ps -a`, `zpool status -x`, `systemctl --failed`).
3.  **Log Analysis:** It fetches the last 100 lines of key system logs (`/var/log/syslog`, `journalctl`) and scans for error patterns.
4.  **Report Generation:** Returns a structured report with a summary, a list of passed/failed checks, and recommended actions.

```python
# apps/backend/src/mcp/tools/device_diagnostics.py
@Tool(name="diagnose_device", description="Run in-depth diagnostics on a specific device.")
async def diagnose_device(
    device_name: str,
    device_service: DeviceService = MCPDepends(get_device_service),
    ssh_manager: SSHCommandManager = MCPDepends(get_ssh_manager)
):
    device = await device_service.get_device_by_name(device_name)
    capabilities = await ssh_manager.detect_capabilities(device.id)
    
    report = {"summary": {}, "checks": []}
    if capabilities.get("docker"):
        docker_status = await ssh_manager.execute_command(device.id, "docker ps -a")
        report["checks"].append({"name": "Docker Status", "output": docker_status.stdout})
    # ... more checks based on capabilities ...
    return report
```

### **85. Create performance analysis tool with trend analysis**

**Objective:** A tool to analyze historical performance data from TimescaleDB to identify trends and potential future bottlenecks.

**Architecture:** The `analyze_performance_trends(resource: str, device: str, time_window: str)` tool leverages TimescaleDB's advanced time-series functions. It constructs a SQL query using `time_bucket()` to group data and `lag()` to compare current values to previous ones. For trend analysis, it can use PostgreSQL's `regr_slope()` function to perform a simple linear regression on the data, indicating if a metric is trending up or down.

```python
# apps/backend/src/mcp/tools/performance_analysis.py
@Tool(name="analyze_performance_trends", description="Analyze historical performance metrics for trends.")
async def analyze_performance_trends(
    resource: str, device_name: str, time_window: str = '7d',
    db: AsyncSession = MCPDepends(get_db_session)
):
    # Example for CPU usage
    query = f"""
        SELECT
            time_bucket('1 day', time) AS bucket,
            avg((metrics_data->'cpu'->>'usage_percent')::float) as avg_cpu,
            regr_slope( (metrics_data->'cpu'->>'usage_percent')::float, extract(epoch from time) ) OVER (ORDER BY time_bucket('1 day', time)) as slope
        FROM system_metrics
        WHERE device_id = (SELECT id FROM devices WHERE hostname = :device_name)
        AND time > now() - interval '{time_window}'
        GROUP BY bucket
        ORDER BY bucket DESC;
    """
    result = await db.execute(text(query), {"device_name": device_name})
    return [row._asdict() for row in result.all()]
```

### **86. Implement configuration orchestration tool with change management**

**Objective:** A high-level tool for managing complex configuration deployments using the two-phase commit pattern developed in Phase 2.

**Architecture:** The `deploy_configuration_change` tool will manage the workflow.
1.  **Input:** Takes a "change set" (a list of file paths and their new content).
2.  **Prepare Phase:** For each change, it calls the `ConfigurationService` to validate the content and upload it to a temporary location on the target device.
3.  **Commit Phase:** After all preparations succeed, it triggers a remote script via SSH that moves all temporary files to their final destinations and restarts any necessary services. If any step fails, it triggers a rollback.

```python
# apps/backend/src/mcp/tools/configuration_orchestration.py
@Tool(name="deploy_configuration_change", description="Deploy a set of configuration changes transactionally.")
async def deploy_configuration_change(
    device_name: str, changes: List[Dict[str, str]],
    config_service: ConfigurationService = MCPDepends(get_config_service)
):
    # ... implementation of the two-phase commit logic ...
    plan = await config_service.prepare_batch_update(device_name, changes)
    if not plan["prepare_success"]:
        return {"status": "error", "message": "Preparation failed", "details": plan["errors"]}
    
    result = await config_service.commit_batch_update(device_name, plan["transaction_id"])
    return result
```

### **87. Create container orchestration tool with dependency management**

**Objective:** A tool to safely start, stop, or restart complex, multi-container applications by respecting their dependencies.

**Architecture:** The `manage_application(app_name: str, action: str)` tool will use the `DependencyService`. It will fetch the full dependency graph for the given application, perform a topological sort to determine the correct operational order, and then execute the `docker` commands sequentially. For a `restart`, it sorts dependencies, stops containers in reverse order, and then starts them in the correct dependency order.

```python
# apps/backend/src/mcp/tools/container_orchestration.py
@Tool(name="manage_application", description="Safely manage a multi-container application and its dependencies.")
async def manage_application(
    app_name: str, action: str,
    dependency_service: DependencyService = MCPDepends(get_dependency_service),
    container_service: ContainerService = MCPDepends(get_container_service)
):
    graph = await dependency_service.get_dependency_graph(app_name)
    
    if action in ["stop", "restart"]:
        stop_order = dependency_service.get_topological_sort(graph, reverse=True)
        await container_service.stop_containers_in_order(stop_order)

    if action in ["start", "restart"]:
        start_order = dependency_service.get_topological_sort(graph)
        await container_service.start_containers_in_order(start_order)
        
    return {"status": "success", "action": action, "app": app_name}
```

### **88. Implement backup orchestration tool with validation**

**Objective:** A tool to manage and validate system backups, ensuring they are restorable.

**Architecture:** The `manage_backups(action: str, target: str)` tool will interface with a new `BackupService`.
*   **Trigger:** The tool can initiate a backup for a given `target` (e.g., a database or a device's config).
*   **Validate:** This is the key feature. The service will spin up a temporary, isolated environment (e.g., a new Docker container), restore the latest backup into it, run a series of predefined checks (e.g., can connect to DB, tables exist), and then tear down the environment. The result is a validated, trustworthy backup.

### **89. Create disaster recovery tool with automated procedures**

**Objective:** A tool to automate the execution of a predefined disaster recovery (DR) plan.

**Architecture:** The `execute_dr_plan(plan_name: str)` tool will read a DR plan from a secure location (e.g., a version-controlled YAML file). The plan will define a sequence of steps, where each step is a call to another MCP tool (e.g., `restore_config_from_backup`, `promote_db_replica`, `start_application`). The tool executes these steps in order, logging the outcome of each and halting if a critical step fails.

### **90. Implement predictive analysis tool with capacity planning**

**Objective:** To help administrators plan for future capacity needs by forecasting resource usage.

**Architecture:** The `predict_capacity(resource: str, device: str)` tool will use time-series forecasting models.
1.  **Data Fetching:** It queries the last 90 days of the specified `resource` metric from the `system_metrics` table in TimescaleDB.
2.  **Forecasting:** It applies a simple linear regression model to the data points to project the trend forward.
3.  **Reporting:** It calculates and returns the date at which usage is predicted to cross a predefined threshold (e.g., 90%), allowing administrators to act proactively.

### **91. Create cost optimization tool with resource analysis**

**Objective:** To identify underutilized resources that could be downsized to save costs, particularly in cloud environments.

**Architecture:** The `analyze_cost_optimization` tool will query the `system_metrics` table over a long period (e.g., 30-60 days). It will specifically look for "cold resources" by identifying devices or VMs where average CPU usage is below a low threshold (e.g., 5%) and network traffic is minimal. It will also identify large, uncompressed TimescaleDB hypertables that could be compressed to save on storage costs.

### **92. Implement maintenance automation tool with workflow management**

**Objective:** A tool to safely and automatically place a device into and out of maintenance mode.

**Architecture:** The `set_maintenance_mode(device: str, enable: bool)` tool will orchestrate a multi-step workflow.
*   **To Enable:**
    1.  Call the `NotificationService` to disable alerting for the device.
    2.  Use the `manage_application` tool to gracefully stop non-essential services.
    3.  Set a `maintenance_mode` flag on the `Device` model in the database.
*   **To Disable:**
    1.  Unset the `maintenance_mode` flag.
    2.  Use the `manage_application` tool to restart services.
    3.  Run the `diagnose_device` tool to ensure the device is healthy.
    4.  Re-enable alerting in the `NotificationService`.