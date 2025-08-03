# Polling Service & WebSocket Implementation Plan

## Investigation Summary

This document provides a comprehensive implementation plan for making the polling service fully operational and implementing WebSocket real-time streaming capabilities in the infrastructor project.

### Current Status ✅
- **Polling Service**: Well-architected but **disabled by default** (`POLLING_ENABLED=false`)
- **Database**: TimescaleDB models ready for time-series data (`SystemMetric`, `DriveHealth`, `ContainerSnapshot`)
- **Infrastructure**: FastAPI server running on port 9101, MCP server on port 9102
- **Dependencies**: WebSocket library already included, notification service implemented
- **Integration**: Properly integrated with FastAPI lifecycle management

### Key Findings 🔍
1. **Polling service is production-ready** but needs configuration and testing
2. **No WebSocket server exists** - needs full implementation
3. **Event system exists** via notification service - can be leveraged for real-time updates
4. **SSH parsing needs refinement** for reliable metrics collection
5. **Integration points are well-defined** for connecting polling to WebSocket broadcasting

## Implementation Strategy

## Phase 1: Enable Polling Service

### Current Implementation Assessment

**✅ Strong Foundation:**
- **Comprehensive Configuration**: Full environment variable support with typed settings classes
- **Proper FastAPI Integration**: Graceful startup/shutdown with lifespan management  
- **TimescaleDB Ready**: Production-ready hypertables with compression and retention policies
- **Good Error Handling**: Consecutive failure tracking and device status management
- **Async Architecture**: Proper concurrent polling with per-device tasks

**❌ Identified Gaps:**
1. **Configuration Issues**: Hard-coded 300s poll interval instead of using configured intervals per metric type
2. **Incomplete Data Collection**: Network I/O metrics fields exist but not populated, SMART data parsing only extracts temperature
3. **Database Integration**: Several model fields not populated (memory_total_bytes, disk_total_bytes, etc.)

### Implementation Steps

#### Step 1: Environment Configuration
**Required Settings:**
```bash
POLLING_ENABLED=true                           # Enable the service
POLLING_CONTAINER_INTERVAL=30                  # Container polling (30 seconds)
POLLING_SYSTEM_METRICS_INTERVAL=300           # System metrics (5 minutes)  
POLLING_DRIVE_HEALTH_INTERVAL=3600            # Drive health (1 hour)
POLLING_MAX_CONCURRENT_DEVICES=10              # Concurrent device limit
```

#### Step 2: Database Preparation
```bash
# Start database and run migrations
docker compose up postgres -d
cd apps/backend && uv run alembic upgrade head
```

#### Step 3: Fix Critical Polling Service Issues
**Issue 1**: Polling service uses hard-coded 300-second interval instead of configured intervals
**Issue 2**: `POLLING_MAX_CONCURRENT_DEVICES` setting is not enforced

#### Step 4: Device Registration
At least one device must be registered with `monitoring_enabled=true` before polling can begin.

#### Step 5: Service Startup and Testing
```bash
./dev.sh start
./dev.sh logs | grep -i polling
```

#### Step 6: Verification
- Check service logs for successful startup
- Verify data collection in TimescaleDB
- Monitor device connection status

**Expected Performance:**
- System Metrics: Every 5 minutes per device
- Container Data: Every 30 seconds per device  
- Drive Health: Every 1 hour per device

---

## Phase 2: Implement WebSocket Server

### Current WebSocket Implementation State

**✅ What Already Exists:**
- **WebSocket Configuration**: Complete `WebSocketSettings` class configured for port 9102
- **Dependencies**: `websockets>=15.0.1` already included in pyproject.toml
- **Event System**: Comprehensive notification service with structured event patterns
- **Architecture Foundation**: Dual-server design (FastAPI REST + independent services)

**❌ What Needs to Be Built:**
- **WebSocket Server Implementation**: No actual WebSocket server code exists
- **Connection Management**: Client connection pool and subscription system
- **Message Protocol**: Standardized WebSocket message format
- **Event Bus**: Communication bridge between polling service and WebSocket server

### Implementation Steps

#### Step 1: Create WebSocket Server Architecture
**Files to Create:**
```
apps/backend/src/websocket/
├── __init__.py
├── server.py              # Main WebSocket server
├── connection_manager.py  # Connection pool & subscription management  
├── message_protocol.py    # Message schemas and validation
├── event_bus.py          # Event distribution system
└── auth.py               # WebSocket authentication
```

#### Step 2: Message Protocol Design
Based on existing notification service patterns, implement standardized message format:
```python
class MessageType(str, Enum):
    DATA = "data"           # Real-time metrics data
    EVENT = "event"         # Notification events  
    SUBSCRIPTION = "subscription"  # Client subscription changes
    HEARTBEAT = "heartbeat" # Connection keepalive
    ERROR = "error"         # Error messages
```

#### Step 3: Connection Management Architecture
**Client Connection Lifecycle:**
1. **Connect**: WebSocket handshake with Bearer token authentication
2. **Authenticate**: Validate token using existing auth system
3. **Subscribe**: Client specifies subscription topics
4. **Receive**: Stream real-time data and events
5. **Disconnect**: Cleanup subscriptions and connections

**Subscription Topics:**
- `devices.{device_id}` - Device-specific updates
- `categories.{category}` - Category-based filtering
- `global` - All events and data
- `metrics.{metric_type}` - Specific metric types

#### Step 4: Integration with Existing FastAPI Application
**Recommended**: Integrated approach using existing FastAPI app:
```python
# Add to apps/backend/src/main.py
from apps.backend.src.websocket.server import websocket_router
app.include_router(websocket_router, prefix="/ws")
```

#### Step 5: Authentication Integration
Leverage existing authentication system for WebSocket connections using Bearer tokens.

---

## Phase 3: Connect Polling to WebSockets

### Current Architecture Analysis

**Polling Service Structure:**
- **Asyncio-based**: Uses concurrent tasks for device polling
- **Session Factory Pattern**: Database operations through `get_async_session_factory()`
- **No Event System**: Currently only stores data, doesn't emit events
- **Service Lifecycle**: Managed by FastAPI lifespan with global instance

**Service Communication Gaps:**
- **No Inter-Service Communication**: Services operate independently
- **No Event Bus**: Missing pub/sub architecture
- **No Observer Pattern**: No event-driven architecture

### Implementation Steps

#### Step 1: Event Bus Architecture
Create core event infrastructure with `BaseEvent` class and `EventBus` for async event processing:
```python
# apps/backend/src/core/events.py
class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue = asyncio.Queue(maxsize=1000)  # Bounded queue
```

#### Step 2: Event Models
Define structured events for different monitoring scenarios:
```python
class MetricCollectedEvent(BaseEvent):
    event_type: str = "metric_collected"
    cpu_usage: float
    memory_usage: float
    hostname: str

class DeviceStatusChangedEvent(BaseEvent):
    event_type: str = "device_status_changed"
    old_status: str
    new_status: str
```

#### Step 3: Polling Service Modifications
Modify `PollingService` to emit events without blocking operations:
```python
# Non-blocking event emission
self.event_bus.emit_nowait(MetricCollectedEvent(...))
```

#### Step 4: WebSocket Service Integration
Create `WebSocketManager` that subscribes to events and broadcasts to connected clients:
```python
class WebSocketManager:
    def _setup_event_handlers(self):
        self.event_bus.subscribe("metric_collected", self._handle_metric_event)
        self.event_bus.subscribe("device_status_changed", self._handle_device_status_event)
```

#### Step 5: FastAPI Application Integration
Integrate event bus and WebSocket manager into FastAPI lifecycle:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize event bus
    event_bus = get_event_bus()
    await event_bus.start()
    
    # Initialize WebSocket manager
    websocket_manager = get_websocket_manager()
```

**Key Technical Benefits:**
- **Non-blocking Event System**: Polling service emits events without performance impact
- **Real-time WebSocket Streaming**: Clients receive live updates
- **Type-safe Event Architecture**: Pydantic models ensure data consistency
- **Error Isolation**: Event handler failures don't affect polling operations

---

## Phase 4: Enhance & Test

### Research Findings Summary

**Strengths Identified:**
- Comprehensive exception hierarchy with structured error handling
- Well-developed notification service with multi-channel support
- Robust health check infrastructure with detailed monitoring
- Strong configuration management and middleware stack

**Areas for Improvement:**
- SSH command parsing is fragile with hardcoded commands
- Missing retry logic and result caching
- Testing framework configured but not implemented
- Performance optimizations needed in polling service

### Implementation Steps

#### 1. SSH Command Parsing Improvements

**Current Issues:**
- Hardcoded command strings with fragile parsing
- No command-level timeout or retry logic
- No result caching or command optimization

**Solutions:**
- Create `SSHCommandManager` with command registry pattern
- Implement robust result parsing with validation
- Add exponential backoff retry logic
- Implement result caching with TTL

#### 2. Error Handling and Retry Logic Enhancements

**Implementation:**
- Enhanced SSH connection pool with circuit breaker pattern
- Smart retry logic with device-specific failure tracking
- Auto-recovery mechanisms for connection issues

#### 3. New Monitoring and Health Check Endpoints

**New Endpoints to Add:**
- `/health/detailed` - Comprehensive system health with component-level details
- `/health/polling` - Dedicated polling service health check
- `/metrics/performance` - API and system performance metrics
- `/monitoring/dashboard` - Comprehensive monitoring dashboard data

#### 4. Notification Service Integration for Alerting

**Smart Alerting Engine:**
- Process metric updates and trigger alerts based on configurable rules
- Integration with existing notification service
- Alert cooldown logic to prevent spam
- Configurable alert rules for different metrics

#### 5. Testing Strategies for Complete System

**Test Infrastructure:**
- Unit tests for SSH command parsing and retry logic
- Integration tests for polling service lifecycle
- API endpoint tests for all monitoring endpoints
- Load and performance tests for high-scale scenarios

**Test Coverage Requirements:**
- Minimum 80% coverage as configured in pyproject.toml
- Comprehensive mocking for SSH operations
- Database integration testing with in-memory SQLite

#### 6. Performance Optimization Recommendations

**Optimization Areas:**
- Intelligent polling intervals based on device state
- Connection pool optimization with per-device pools  
- Database query optimization with proper indexing
- Result caching strategy with TTL-based invalidation
- Structured logging and Prometheus-style metrics

#### 7. Code Quality Improvements

**Enhancements:**
- Structured logging with correlation IDs
- Enhanced configuration validation with Pydantic
- Prometheus-style metrics for observability
- Comprehensive error handling with context

### Implementation Timeline

1. **Week 1-2**: SSH Command Manager and Enhanced Parsing
2. **Week 3**: Error Handling and Retry Logic Improvements  
3. **Week 4**: New Monitoring Endpoints and Health Checks
4. **Week 5**: Notification Service Integration and Alerting
5. **Week 6-7**: Comprehensive Testing Implementation
6. **Week 8**: Performance Optimizations and Load Testing
7. **Week 9**: Code Quality Improvements and Documentation
8. **Week 10**: Final Integration Testing and Deployment

### Success Criteria

- **Reliability**: 99.5% uptime for polling service
- **Performance**: <100ms average API response time
- **Test Coverage**: 80% minimum coverage achieved
- **Error Handling**: <1% unhandled exceptions
- **Alerting**: <5 minute alert response time
- **Resource Usage**: <2GB memory usage for API server

## Todo List Reference

A comprehensive todo list with 26 tasks has been created covering:
- **poll-1**: Enable and test polling service functionality (4 subtasks)
- **poll-2**: Implement WebSocket server for real-time data streaming (4 subtasks)
- **poll-3**: Integrate polling service with WebSocket broadcasting (4 subtasks)
- **poll-4**: Address polling service operational improvements (4 subtasks)
- **poll-5**: Add monitoring and health check endpoints (3 subtasks)
- **poll-6**: Integrate with notification service for alerting (3 subtasks)
- **poll-7**: Test and validate complete polling + WebSocket system (4 subtasks)

---

*This plan provides a roadmap for implementing real-time infrastructure monitoring with WebSocket streaming capabilities.*