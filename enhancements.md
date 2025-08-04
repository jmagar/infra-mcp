# Infrastructure Management System - Architecture Analysis & Enhancement Recommendations

## 📋 **Current Architecture Analysis**

### 🔍 **System Overview**
The current infrastructure management system operates with three separate data collection patterns that create significant duplication and inconsistency:

1. **🔄 Polling Service** (Background, stores everything)
   - Runs every 30s (containers), 300s (metrics), 3600s (drives)
   - **ALWAYS stores data** in TimescaleDB hypertables
   - Uses both `ssh_client` and `ssh_command_manager`
   - Creates: `SystemMetric`, `ContainerSnapshot`, `DriveHealth` records
   - Emits real-time events via event bus

2. **🌐 API Services** (On-demand, mixed storage)
   - **Sometimes** stores data (device management)
   - **Usually** just returns live SSH data without storing
   - Has a `live=true` parameter option for fresh data vs DB data
   - Uses database for device registry, but not for metrics/containers

3. **🤖 MCP Tools** (On-demand, no storage)
   - Makes HTTP calls to API endpoints
   - **Never stores data** - purely pass-through
   - Focused on real-time operations

### 🔄 **Current Data Flow**

**What Gets Stored:**
```
Polling Service → Database:
├── SystemMetric (every 5 minutes) - 3,424 records/24h
├── ContainerSnapshot (every 30 seconds) - 111,453 records/24h
└── DriveHealth (every hour) - 2,139 records total

API Services → Database:
├── Device registry (CRUD operations)
├── Proxy configurations (sync operations)
└── BUT NOT metrics/containers (just returns live data)

MCP Tools → Database:
└── Nothing (makes HTTP calls, returns JSON)
```

### 🔧 **SSH Usage Patterns**

**SSH Client Instantiation:**
- **11 different files** create `get_ssh_client()` instances
- **4 files** use `get_ssh_command_manager()`
- **25 total files** use SSH functionality

**Command Duplication Examples:**
- `docker ps` appears in **9 different files**
- System metrics collection duplicated between polling and MCP tools
- Container listing implemented 3+ times with different approaches
- Each layer has its own error handling, timeouts, and retry logic

## 🎯 **Identified Problems**

### 1. **Data Inconsistency**
- ❌ API calls don't create audit trail in database
- ❌ No historical data for API-triggered operations  
- ❌ Different data formats between polling and API
- ❌ Fresh API calls ignore cached polling data

### 2. **Code Duplication**
- ❌ Same SSH commands implemented multiple times
- ❌ Different error handling approaches across layers
- ❌ Inconsistent timeout and retry logic
- ❌ Multiple connection management patterns

### 3. **Performance Inefficiency**
- ❌ Fresh API calls waste cached polling data
- ❌ Multiple concurrent SSH connections to same hosts
- ❌ No smart caching between systems
- ❌ Redundant command execution

### 4. **Architecture Complexity**
- ❌ Three different patterns for same operations
- ❌ Difficult to maintain consistency
- ❌ Hard to add new data collection features
- ❌ Complex debugging across multiple layers

## 💡 **Enhanced Architecture Proposal**

### **Unified Data Collection Service**

Instead of separate polling + API layers, implement a single unified service:

```
┌─────────────────────────────────────────────────────────────────┐
│                UNIFIED DATA COLLECTION SERVICE                   │
├─────────────────────────────────────────────────────────────────┤
│ • Single SSH command implementation                             │
│ • Smart caching with configurable freshness thresholds         │  
│ • ALWAYS stores results in DB (audit trail + performance)      │
│ • Background polling + on-demand API use same methods          │
│ • Unified SSH connection pool with connection reuse            │
│ • Consistent error handling and retry logic                    │
│ • Event emission for real-time updates                         │
└─────────────────────────────────────────────────────────────────┘
                           ▲
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   ┌──────────┐    ┌─────────────┐    ┌────────────┐
   │ Polling  │    │ API Routes  │    │ MCP Tools  │
   │ Timers   │    │ (on-demand) │    │ (on-demand)│
   └──────────┘    └─────────────┘    └────────────┘
```

### **Smart Caching Strategy**

**Freshness Thresholds:**
- **Containers**: 30 seconds (matches polling interval)
- **System Metrics**: 300 seconds (5 minutes)
- **Drive Health**: 3600 seconds (1 hour)
- **Device Status**: 60 seconds (reasonable for connectivity)

**Cache Logic:**
```python
async def get_container_data(device_id: UUID, force_refresh: bool = False):
    if not force_refresh:
        cached_data = await get_cached_data(device_id, "containers", max_age=30)
        if cached_data:
            return cached_data
    
    # Execute SSH command, store in DB, return data
    fresh_data = await collect_and_store_container_data(device_id)
    return fresh_data
```

## 🚀 **Implementation Strategy** 

### **Phase 1: Unified Service Layer** (EXPANDED)

#### **1.1 Create UnifiedDataCollectionService Foundation**

**Core Service Architecture:**
```python
class UnifiedDataCollectionService:
    """
    Central service for all data collection operations across the infrastructure.
    Consolidates polling, API, and MCP data collection into a single, consistent interface.
    """
    
    def __init__(self, db_session_factory, ssh_client: SSHClient, ssh_command_manager: SSHCommandManager):
        self.db_session_factory = db_session_factory
        self.ssh_client = ssh_client
        self.ssh_command_manager = ssh_command_manager
        self.cache = CacheManager()
        self.event_bus = get_event_bus()
        
        # Data type freshness thresholds (in seconds)
        self.freshness_thresholds = {
            "containers": 30,       # 30 seconds
            "system_metrics": 300,  # 5 minutes
            "drive_health": 3600,   # 1 hour
            "network": 120,         # 2 minutes
            "zfs": 600,            # 10 minutes
            # Configuration monitoring (event-driven + fallback)
            "proxy_configs": 0,     # Real-time via file watching
            "docker_compose": 0,    # Real-time via file watching
            "systemd_services": 600, # 10 minutes polling
        }
```

**Current Implementation Analysis:**
- **11 files** currently create `get_ssh_client()` instances independently
- **4 files** use `get_ssh_command_manager()` separately  
- **25 total files** contain SSH-related functionality
- **No centralized caching** - each service implements its own approach
- **No unified error handling** - different retry/timeout patterns per service

#### **1.2 Consolidate SSH Command Execution Logic**

**Identified Duplication Patterns:**
```python
# Current duplication across files:
# - polling_service.py: Lines 268-274 (system metrics)
# - metrics_service.py: Lines 76-88 (same system metrics)  
# - container_service.py: Lines 150-151 (container listing)
# - polling_service.py: Lines 449-453 (same container listing)
# - device_management.py (MCP): Similar SSH patterns
```

**Unified Command Registry:**
```python
class CommandRegistry:
    """Registry of all SSH commands used across the system"""
    
    SYSTEM_METRICS = "system_metrics"           # Used by: polling, metrics_service, MCP tools
    LIST_CONTAINERS = "list_containers"         # Used by: polling, container_service, MCP tools  
    LIST_DRIVES = "list_drives"                # Used by: polling, metrics_service, MCP tools
    CONTAINER_STATS = "container_stats"        # Used by: polling, container_service
    NETWORK_INTERFACES = "network_interfaces"   # Used by: metrics_service, MCP tools
    ZFS_STATUS = "zfs_status"                  # Used by: ZFS services, MCP tools
    
    # Configuration monitoring commands
    PROXY_CONFIGS = "proxy_configs"             # SWAG/nginx proxy configurations
    DOCKER_COMPOSE = "docker_compose"           # Docker compose stack definitions
    SYSTEMD_SERVICES = "systemd_services"       # System service definitions
    
    @classmethod
    def get_all_commands(cls) -> List[CommandDefinition]:
        """Return all registered command definitions with unified configuration"""
        return [
            CommandDefinition(
                name=cls.SYSTEM_METRICS,
                category=CommandCategory.SYSTEM_METRICS,
                timeout=15,
                cache_ttl=300,  # 5 minutes
                retry_count=3,
                parser=SystemMetricsParser().parse
            ),
            CommandDefinition(
                name=cls.LIST_CONTAINERS,
                category=CommandCategory.CONTAINER_MANAGEMENT,
                timeout=10,
                cache_ttl=30,   # 30 seconds
                retry_count=3,
                parser=ContainerStatsParser().parse
            ),
            CommandDefinition(
                name=cls.PROXY_CONFIGS,
                category=CommandCategory.FILE_OPERATIONS,
                timeout=5,
                cache_ttl=0,    # Real-time via file watching
                retry_count=2,
                parser=ProxyConfigParser().parse
            ),
            CommandDefinition(
                name=cls.DOCKER_COMPOSE,
                category=CommandCategory.FILE_OPERATIONS,
                timeout=5,
                cache_ttl=0,    # Real-time via file watching
                retry_count=2,
                parser=DockerComposeParser().parse
            ),
            # ... other commands
        ]
```

#### **1.3 Event-Driven Configuration Monitoring**

**File Watching System:**
```python
class ConfigurationMonitoringService:
    """Hybrid file watching + fallback polling for configuration changes"""
    
    def __init__(self, unified_service: UnifiedDataCollectionService):
        self.unified_service = unified_service
        self.file_watchers: Dict[UUID, RemoteFileWatcher] = {}
        self.watch_paths = {
            "proxy_configs": [
                "/config/nginx/proxy-confs/*.conf",
                "/config/nginx/site-confs/*.conf"
            ],
            "docker_compose": [
                "/docker-compose.yml",
                "/compose/*/docker-compose.yml",
                "/opt/*/docker-compose.yml"
            ],
            "systemd_services": [
                "/etc/systemd/system/*.service"
            ]
        }
    
    async def setup_device_monitoring(self, device: Device):
        """Setup real-time configuration monitoring for a device"""
        try:
            # Create remote file watcher with inotify
            watcher = RemoteFileWatcher(device)
            
            for config_type, paths in self.watch_paths.items():
                await watcher.add_watch_paths(
                    paths=paths,
                    events=["modify", "create", "delete", "move"],
                    callback=lambda event: self._handle_config_change(device.id, config_type, event)
                )
            
            self.file_watchers[device.id] = watcher
            
            # Initial collection to establish baseline
            await self._collect_all_configs(device.id)
            
            # Setup fallback verification (every 30 minutes)
            asyncio.create_task(self._periodic_verification(device))
            
        except Exception as e:
            logger.warning(f"File watching failed for {device.hostname}, using polling fallback: {e}")
            await self._setup_polling_fallback(device)
    
    async def _handle_config_change(self, device_id: UUID, config_type: str, event: FileChangeEvent):
        """Handle real-time configuration file changes"""
        try:
            # Collect changed configuration immediately
            fresh_config = await self.unified_service.collect_and_store_data(
                device_id=device_id,
                data_type=config_type,
                force_refresh=True,
                store_result=True
            )
            
            # Emit configuration change event
            await self._emit_config_change_event(device_id, config_type, event, fresh_config)
            
            # Trigger dependent service updates
            if config_type == "proxy_configs":
                await self._update_service_discovery(device_id, fresh_config)
            elif config_type == "docker_compose":
                await self._update_container_dependencies(device_id, fresh_config)
                
        except Exception as e:
            logger.error(f"Failed to handle config change for {device_id}: {e}")

class RemoteFileWatcher:
    """SSH-based file watching using inotify"""
    
    def __init__(self, device: Device):
        self.device = device
        self.ssh_info = self._create_ssh_connection_info(device)
        self.watch_process: Optional[asyncio.subprocess.Process] = None
        self.callbacks: Dict[str, Callable] = {}
    
    async def add_watch_paths(self, paths: List[str], events: List[str], callback: Callable):
        """Add file paths to watch with inotify"""
        # Build inotify watch command
        event_flags = ",".join(events)
        watch_cmd = f"""
        inotifywait -m -r -e {event_flags} \\
            --format '%w%f|%e|%T' --timefmt '%s' \\
            {' '.join(paths)} 2>/dev/null
        """
        
        # Start persistent SSH connection with streaming output
        self.watch_process = await self._start_streaming_ssh(watch_cmd, callback)
    
    async def _start_streaming_ssh(self, command: str, callback: Callable):
        """Start streaming SSH command that continuously outputs file changes"""
        ssh_cmd = f"ssh {self.device.hostname} '{command}'"
        
        process = await asyncio.create_subprocess_shell(
            ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Process streaming output
        asyncio.create_task(self._process_file_events(process.stdout, callback))
        
        return process
    
    async def _process_file_events(self, stdout, callback: Callable):
        """Process streaming file change events"""
        async for line in stdout:
            try:
                event_line = line.decode().strip()
                if event_line:
                    # Parse: path|event|timestamp
                    path, event_type, timestamp = event_line.split('|')
                    
                    file_event = FileChangeEvent(
                        path=path,
                        event_type=event_type,
                        timestamp=datetime.fromtimestamp(int(timestamp), timezone.utc),
                        device_id=self.device.id
                    )
                    
                    await callback(file_event)
                    
            except Exception as e:
                logger.warning(f"Failed to process file event: {e}")
```

#### **1.4 Smart Caching with Event Integration**

**Cache Architecture:**
```python
@dataclass
class CacheEntry:
    """Enhanced cache entry with metadata and validation"""
    
    data: Any
    timestamp: datetime
    device_id: UUID
    data_type: str
    command_hash: str
    ttl_seconds: int
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_fresh(self) -> bool:
        """Check if cache entry is still fresh"""
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age < self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds()

class CacheManager:
    """Advanced cache management with LRU eviction and metrics"""
    
    def __init__(self, max_entries: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_entries = max_entries
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }
    
    async def get_cached_data(
        self, 
        device_id: UUID, 
        data_type: str, 
        command_hash: str,
        max_age_seconds: Optional[int] = None
    ) -> Optional[Any]:
        """Get cached data if available and fresh"""
        cache_key = f"{device_id}:{data_type}:{command_hash}"
        
        self.metrics["total_requests"] += 1
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Use provided max_age or entry's TTL
            effective_max_age = max_age_seconds or entry.ttl_seconds
            
            if entry.age_seconds < effective_max_age:
                entry.access_count += 1
                entry.last_accessed = datetime.now(timezone.utc)
                self.metrics["hits"] += 1
                
                logger.debug(f"Cache HIT for {data_type} on {device_id} (age: {entry.age_seconds:.1f}s)")
                return entry.data
            else:
                # Remove stale entry
                del self.cache[cache_key]
                logger.debug(f"Cache EXPIRED for {data_type} on {device_id} (age: {entry.age_seconds:.1f}s)")
        
        self.metrics["misses"] += 1
        return None
    
    async def store_data(
        self,
        device_id: UUID,
        data_type: str, 
        command_hash: str,
        data: Any,
        ttl_seconds: int
    ) -> None:
        """Store data in cache with LRU eviction"""
        cache_key = f"{device_id}:{data_type}:{command_hash}"
        
        # Evict oldest entries if at capacity
        if len(self.cache) >= self.max_entries:
            await self._evict_lru_entries(count=int(self.max_entries * 0.1))  # Remove 10%
        
        entry = CacheEntry(
            data=data,
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            data_type=data_type,
            command_hash=command_hash,
            ttl_seconds=ttl_seconds
        )
        
        self.cache[cache_key] = entry
        logger.debug(f"Cache STORED for {data_type} on {device_id} (TTL: {ttl_seconds}s)")
```

#### **1.5 Configuration Change Detection & Storage**

**Database Schema for Configuration Tracking (Self-Hosted Optimized):**
```python
class ConfigurationSnapshot(Base):
    """Store complete configuration file snapshots - optimized for self-hosters"""
    __tablename__ = "configuration_snapshots"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    device_id = Column(UUID, ForeignKey("devices.id"), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    
    config_type = Column(String, nullable=False)  # proxy_configs, docker_compose, etc.
    file_path = Column(String, nullable=False)
    content_hash = Column(String, nullable=False, index=True)
    file_size_bytes = Column(Integer)
    
    # FULL configuration content - NEVER purged for self-hosters
    raw_content = Column(Text, nullable=False)  # Complete file contents
    
    # Parsed/structured data for querying
    parsed_data = Column(JSON)  # Parsed services, routes, etc.
    
    # Change tracking  
    change_type = Column(String)  # CREATE, MODIFY, DELETE, MOVE
    previous_hash = Column(String)
    
    # Metadata
    file_modified_time = Column(DateTime(timezone=True))
    collection_source = Column(String)  # "file_watch", "polling", "api"
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_device_config_type_time', 'device_id', 'config_type', 'time'),
        Index('idx_config_path_hash', 'file_path', 'content_hash'),
    )

class ConfigurationChangeEvent(Base):
    """Track configuration change events for alerting/auditing"""
    __tablename__ = "configuration_change_events"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    device_id = Column(UUID, ForeignKey("devices.id"), nullable=False)
    snapshot_id = Column(UUID, ForeignKey("configuration_snapshots.id"))
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    
    config_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    change_type = Column(String, nullable=False)
    
    # Impact analysis
    affected_services = Column(JSON)  # Services impacted by this change
    requires_restart = Column(Boolean, default=False)
    
    # Change summary
    changes_summary = Column(JSON)  # Structured diff of what changed
    risk_level = Column(String)  # LOW, MEDIUM, HIGH, CRITICAL
```

**Configuration Change Detection:**
```python
async def detect_and_store_config_change(
    self,
    device_id: UUID,
    config_type: str,
    file_path: str,
    content: str,
    change_type: str = "MODIFY"
) -> Optional[ConfigurationSnapshot]:
    """Detect configuration changes and store snapshots"""
    
    # Calculate content hash
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    
    # Get last known configuration
    last_config = await self._get_last_config_snapshot(device_id, file_path)
    
    # Check if content actually changed
    if last_config and last_config.content_hash == content_hash:
        logger.debug(f"No content change detected for {file_path} on device {device_id}")
        return None
    
    # Parse configuration content
    parsed_data = await self._parse_configuration(config_type, content)
    
    # Create configuration snapshot
    snapshot = ConfigurationSnapshot(
        device_id=device_id,
        time=datetime.now(timezone.utc),
        config_type=config_type,
        file_path=file_path,
        content_hash=content_hash,
        file_size_bytes=len(content.encode()),
        raw_content=content,
        parsed_data=parsed_data,
        change_type=change_type,
        previous_hash=last_config.content_hash if last_config else None,
        collection_source="file_watch"
    )
    
    # Store snapshot
    await self._store_config_snapshot(snapshot)
    
    # Analyze impact and create change event
    impact_analysis = await self._analyze_config_impact(
        config_type, parsed_data, last_config.parsed_data if last_config else None
    )
    
    change_event = ConfigurationChangeEvent(
        device_id=device_id,
        snapshot_id=snapshot.id,
        time=snapshot.time,
        config_type=config_type,
        file_path=file_path,
        change_type=change_type,
        affected_services=impact_analysis.get("affected_services", []),
        requires_restart=impact_analysis.get("requires_restart", False),
        changes_summary=impact_analysis.get("changes_summary", {}),
        risk_level=impact_analysis.get("risk_level", "MEDIUM")
    )
    
    await self._store_change_event(change_event)
    
    # Emit real-time events
    await self.event_bus.emit(ConfigurationChangedEvent(
        device_id=device_id,
        config_type=config_type,
        file_path=file_path,
        change_type=change_type,
        snapshot_id=snapshot.id,
        affected_services=impact_analysis.get("affected_services", []),
        risk_level=impact_analysis.get("risk_level", "MEDIUM")
    ))
    
    return snapshot
```

#### **1.6 Ensure All Operations Store Results in Database**

**Current Storage Inconsistencies:**
- ✅ **Polling Service**: Always stores (SystemMetric, ContainerSnapshot, DriveHealth)
- ❌ **API Services**: Sometimes stores (device registry), usually just returns live data
- ❌ **MCP Tools**: Never stores, pure pass-through to API
- ❌ **Configuration Data**: Currently discovered via MCP but not stored persistently

**Unified Storage Pattern:**
```python
async def collect_and_store_data(
    self,
    device_id: UUID,
    data_type: str,
    collection_method: Callable,
    force_refresh: bool = False,
    store_result: bool = True
) -> Any:
    """
    Universal data collection method that handles caching, collection, and storage
    
    This method replaces all individual collection methods across:
    - polling_service._collect_system_metrics()
    - metrics_service.get_device_metrics() 
    - MCP tools direct SSH calls
    """
    
    device = await self._get_device(device_id)
    command_hash = self._generate_command_hash(device, data_type)
    
    # 1. Check cache first (unless force refresh)
    if not force_refresh:
        cached_data = await self.cache.get_cached_data(
            device_id, data_type, command_hash, 
            max_age_seconds=self.freshness_thresholds.get(data_type, 300)
        )
        if cached_data:
            return cached_data
    
    # 2. Collect fresh data
    try:
        fresh_data = await collection_method(device)
        
        # 3. Store in database (audit trail + historical data)
        if store_result:
            await self._store_in_database(device_id, data_type, fresh_data)
        
        # 4. Cache for future requests
        await self.cache.store_data(
            device_id, data_type, command_hash, fresh_data,
            ttl_seconds=self.freshness_thresholds.get(data_type, 300)
        )
        
        # 5. Emit real-time event
        await self._emit_data_event(device_id, data_type, fresh_data)
        
        return fresh_data
        
    except Exception as e:
        logger.error(f"Data collection failed for {data_type} on {device_id}: {e}")
        raise
```

#### **1.7 Migration Strategy for Existing Services**

**Service Replacement Plan:**

1. **Phase 1a: Polling Service Integration**
   ```python
   # Replace these methods in polling_service.py:
   # OLD: _collect_system_metrics() (lines 262-324)
   # NEW: unified_service.collect_and_store_data(device_id, "system_metrics", ...)
   
   # OLD: _collect_container_data() (lines 435-564) 
   # NEW: unified_service.collect_and_store_data(device_id, "containers", ...)
   
   # OLD: _collect_drive_health() (lines 326-433)
   # NEW: unified_service.collect_and_store_data(device_id, "drive_health", ...)
   
   # NEW: Add configuration monitoring
   # NEW: unified_service.setup_config_monitoring(device_id)
   ```

2. **Phase 1b: API Service Integration**
   ```python
   # Replace these methods in metrics_service.py:
   # OLD: get_device_metrics() live=True (lines 76-114)
   # NEW: unified_service.collect_and_store_data(device_id, "system_metrics", force_refresh=True)
   
   # Replace these methods in container_service.py:
   # OLD: list_device_containers() live_data=True (lines 144-236)
   # NEW: unified_service.collect_and_store_data(device_id, "containers", force_refresh=True)
   ```

3. **Phase 1c: Configuration Integration**
   ```python
   # Add new MCP resources that leverage stored configuration data
   # NEW: "config://proxy-configs" - Real-time proxy configuration access
   # NEW: "config://docker-compose" - Real-time compose file access  
   # NEW: "config://changes" - Configuration change history
   
   # Update existing MCP resources to use cached data
   # OLD: swag://proxy-configs (direct file access)
   # NEW: swag://proxy-configs (cached + real-time updates)
   ```

4. **Phase 1d: MCP Tool Migration**
   ```python
   # Replace direct SSH calls in MCP tools with unified service calls
   # Example: mcp/tools/system_monitoring.py
   # OLD: Direct SSH execution (lines vary)
   # NEW: HTTP calls to unified API endpoints that use unified service
   ```

#### **1.8 Expected Technical Outcomes**

**Performance Metrics (Self-Hosted Optimized):**
- **SSH Connection Reduction**: From ~45 connections/minute to ~5 connections/minute (89% reduction with file watching)
- **Configuration Change Latency**: Real-time (milliseconds) vs 5-minute polling delay
- **API Response Times**: <100ms for cached data, <2s for fresh collection
- **Database Writes**: 100% audit trail (currently ~60% with API gap)
- **Cache Hit Ratio**: Target 75%+ for repeated requests within freshness window
- **Memory Usage**: Stable with LRU eviction (max 1000 cached entries ≈ 50MB)
- **Storage Requirements**: Minimal - configurations change infrequently, permanent storage feasible
- **Deployment Complexity**: Single-server friendly, no external dependencies

**Code Quality Improvements:**
- **Lines of Code**: Eliminate ~800 lines of duplicate SSH logic
- **Error Handling**: Single, consistent pattern across all data collection
- **Testing**: Unified test suite instead of scattered testing approaches
- **Maintenance**: Single location for command timeouts, retry logic, parser updates

**Operational Benefits (Self-Hosted Focus):**
- **Complete Audit Trail**: Every data collection operation recorded in database
- **Real-time Configuration Monitoring**: Immediate awareness of infrastructure changes
- **Permanent Configuration History**: Complete version history stored forever (no purging for self-hosters)
- **Service Impact Analysis**: Automated detection of services affected by config changes
- **Consistent Data Formats**: Unified parsing and validation across all interfaces
- **Improved Monitoring**: Centralized metrics for cache performance, SSH health
- **Easier Debugging**: Single code path for all data collection issues
- **Self-Hosted Friendly**: No external dependencies, single-server deployment optimized

#### **1.9 Implementation Checklist**

**Week 1: Foundation**
- [ ] Create `UnifiedDataCollectionService` class structure
- [ ] Implement `CacheManager` with LRU eviction
- [ ] Set up `CommandRegistry` with existing command definitions
- [ ] Create unified SSH connection pool management
- [ ] Add comprehensive logging and metrics collection
- [ ] Design database schema for configuration snapshots
- [ ] Implement `RemoteFileWatcher` class for inotify-based monitoring

**Week 2: Core Methods**
- [ ] Implement `collect_and_store_data()` universal method
- [ ] Add data type specific parsers and validators  
- [ ] Create unified database storage patterns
- [ ] Implement event emission for real-time updates
- [ ] Add error handling and retry logic
- [ ] Build configuration change detection system
- [ ] Create proxy config and docker compose parsers
- [ ] Implement `ConfigurationMonitoringService`

**Week 3: Service Integration**
- [ ] Replace polling service methods with unified calls
- [ ] Update API service endpoints to use unified service
- [ ] Setup file watching for proxy configs and docker compose files
- [ ] Add configuration change alerting and events
- [ ] Create new API endpoints for configuration history
- [ ] Ensure API response format consistency
- [ ] Update configuration management for freshness thresholds

**Week 4: Testing & Optimization**
- [ ] Comprehensive unit tests for unified service
- [ ] Integration tests across all data types
- [ ] File watching integration tests with simulated config changes
- [ ] Performance testing and cache optimization
- [ ] Load testing with realistic traffic patterns
- [ ] MCP resource updates to leverage stored configuration data
- [ ] Documentation and deployment preparation

### **Phase 2: API Layer Rewrite**  
1. Rewrite API endpoints to use unified service internally
2. Eliminate all duplicate SSH command implementations
3. Maintain existing endpoint signatures with `force_refresh` parameters
4. Ensure consistent API response formats

### **Phase 3: Polling Service Rewrite**
1. Completely rewrite polling service to use unified service
2. Replace all collection methods with unified service calls
3. Maintain existing polling intervals and schedules
4. Preserve event emission functionality

### **Phase 4: MCP Tool Rewrite**
1. Rewrite MCP tools to use unified API endpoints exclusively
2. Eliminate all direct SSH implementations
3. Leverage cached data and audit trails for better performance
4. Maintain real-time capability for critical operations

### **Phase 5: Configuration Management Optimization (Self-Hosted)**
1. Implement permanent configuration storage (no purging for self-hosters)
2. Optimize file watching for typical self-hosted environments
3. Create configuration history and rollback capabilities
4. Remove enterprise features (S3 backup, complex retention policies)
5. Focus on single-server or small-cluster deployments

## 📊 **Expected Benefits**

### **Performance Improvements**
- ✅ **Instant API responses** when data is fresh (< threshold)
- ✅ **Reduced SSH connections** through connection pooling
- ✅ **Lower system load** on monitored devices
- ✅ **Better resource utilization** across the platform

### **Data Consistency**
- ✅ **Complete audit trail** for all operations
- ✅ **Uniform data formats** across all interfaces
- ✅ **Historical data** for API-triggered operations
- ✅ **Reliable caching** with consistent freshness logic

### **Code Maintainability**
- ✅ **Single source of truth** for data collection
- ✅ **Unified error handling** and retry logic
- ✅ **Easier testing** with centralized logic
- ✅ **Simplified debugging** with single code path

### **Development Efficiency**
- ✅ **New features** added in one place
- ✅ **Consistent behavior** across all interfaces
- ✅ **Reduced complexity** for new developers
- ✅ **Better documentation** with unified patterns

## 🔧 **Technical Implementation Details**

### **Unified Service Interface**
```python
class UnifiedDataCollectionService:
    async def get_system_metrics(self, device_id: UUID, force_refresh: bool = False) -> SystemMetricData
    async def get_container_data(self, device_id: UUID, force_refresh: bool = False) -> ContainerData
    async def get_drive_health(self, device_id: UUID, force_refresh: bool = False) -> DriveHealthData
    
    # Always stores results, returns cached data when fresh
    async def collect_and_cache(self, device_id: UUID, data_type: str, collection_func: Callable)
```

### **API Endpoint Pattern**
```python
@router.get("/devices/{device_id}/containers")
async def get_device_containers(
    device_id: UUID,
    force_refresh: bool = Query(False, description="Force fresh data collection"),
    service: UnifiedDataCollectionService = Depends(get_unified_service)
):
    return await service.get_container_data(device_id, force_refresh)
```

### **Connection Pool Management**
- Single SSH connection pool shared across all operations
- Connection reuse based on device hostname
- Proper connection lifecycle management
- Configurable pool sizes and timeouts

## ⚠️ **Migration Considerations**

### **Backward Compatibility**
- Maintain existing API endpoint signatures
- Preserve current response formats
- Support existing query parameters
- Gradual rollout with feature flags

### **Data Migration**
- No database schema changes required
- Existing data remains accessible
- New operations start using unified service
- Historical data preservation

### **Performance Testing**
- Benchmark current vs. unified performance
- Load testing with realistic traffic patterns
- Memory usage analysis with connection pooling
- Response time measurements for cached vs. fresh data

## 🎯 **Success Metrics**

### **Performance Metrics**
- API response times (target: <100ms for cached data)
- SSH connection count reduction (target: 50% fewer connections)
- Database write efficiency (eliminate duplicate collection)
- System resource usage on monitored devices

### **Code Quality Metrics**
- Lines of code reduction (eliminate duplication)
- Test coverage improvement (unified testing)
- Bug report reduction (fewer code paths)
- Development velocity increase (single implementation)

### **Operational Metrics**
- Complete audit trail coverage (100% of operations stored)
- Data consistency across interfaces (eliminate format differences)
- Cache hit ratio (target: >80% for API calls)
- Error rate reduction (unified error handling)

---

## 📝 **Original Enhancement Ideas**

The original enhancements.md contained these ideas, which are all addressed in the unified architecture:

1. **Unified SSH Layer** - ✅ Single SSH command manager implementation
2. **Smart Caching** - ✅ API leverages polling data with freshness checks  
3. **Hybrid Approach** - ✅ Fast cached data + on-demand fresh collection
4. **Connection Sharing** - ✅ Unified connection pool across all services

The comprehensive analysis reveals that these enhancements, while valuable, are symptoms of a deeper architectural issue. The unified approach addresses the root cause while delivering all the originally proposed benefits and more.

---

## 🗄️ **Database Schema Analysis & Changes**

> **📝 Note**: Database reset approach - no migration complexity or backward compatibility concerns. Fresh schema implementation for optimal performance.

### **Current Database Architecture**

#### **Existing Models (Well-Established)**
```python
# Core Models (apps/backend/src/models/)
├── Device (device.py)              # Infrastructure registry with JSONB metadata
├── SystemMetric (metrics.py)       # TimescaleDB hypertable for system metrics
├── DriveHealth (metrics.py)        # TimescaleDB hypertable for drive monitoring  
├── ContainerSnapshot (container.py)# TimescaleDB hypertable for container metrics
├── ProxyConfig (proxy_config.py)   # Sophisticated proxy configuration management
├── ProxyConfigChange (proxy_config.py)      # Change tracking (TimescaleDB)
├── ProxyConfigTemplate (proxy_config.py)    # Configuration templates
└── ProxyConfigValidation (proxy_config.py)  # Nginx validation results
```

#### **Current TimescaleDB Integration**
- **9 Hypertables**: `system_metrics`, `drive_health`, `container_snapshots`, `zfs_status`, `zfs_snapshots`, `network_interfaces`, `docker_networks`, `vm_status`, `system_logs`
- **Compression Policies**: 7-day compression for all hypertables
- **Retention Policies**: 30-90 days based on data type
- **Chunk Management**: 1-day chunks with adaptive sizing
- **Advanced Features**: Space partitioning ready, continuous aggregates configured

#### **Current Schema Strengths**
✅ **Sophisticated Proxy Config Management**: Full change tracking, templates, validation  
✅ **TimescaleDB Optimization**: Proper hypertables, compression, retention policies  
✅ **Relationship Management**: Well-defined foreign keys and cascading deletes  
✅ **Performance Indexing**: Composite indexes for time-series queries  
✅ **Data Integrity**: Check constraints, unique constraints, proper validation  

#### **Current Schema Gaps (For Unified Service)**
❌ **No Unified Audit Trail**: API/MCP operations not tracked in database  
❌ **No Docker Compose Monitoring**: Only proxy configs have change tracking  
❌ **No Configuration Event System**: Missing event-driven change detection  
❌ **No Data Collection Metadata**: No tracking of collection methods/sources  
❌ **No Cache State Tracking**: No persistent cache metrics or invalidation logs  

### **Required Database Schema Additions**

#### **1. Unified Data Collection Audit Trail**
```python
class DataCollectionAudit(Base):
    """Audit trail for all data collection operations (Hypertable)"""
    __tablename__ = "data_collection_audit"
    
    # TimescaleDB primary key
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID, ForeignKey("devices.id"), primary_key=True, nullable=False)
    
    # Operation identification
    operation_id = Column(UUID, primary_key=True, default=uuid4)  # Unique per operation
    data_type = Column(String(50), nullable=False, index=True)     # "containers", "metrics", etc.
    
    # Collection metadata
    collection_method = Column(String(50), nullable=False)        # "polling", "api", "mcp"
    collection_source = Column(String(100))                       # Source service/endpoint
    force_refresh = Column(Boolean, default=False)
    cache_hit = Column(Boolean, default=False)
    
    # Timing and performance
    duration_ms = Column(Integer)                                 # Collection duration
    ssh_command_count = Column(Integer, default=0)               # SSH commands executed
    data_size_bytes = Column(BigInteger)                         # Size of collected data
    
    # Status and errors
    status = Column(String(20), nullable=False, index=True)      # "success", "error", "partial"
    error_message = Column(Text)                                 # Error details if failed
    warnings = Column(JSON, default=list)                       # Non-fatal warnings
    
    # Result metadata
    records_created = Column(Integer, default=0)                # Database records created
    records_updated = Column(Integer, default=0)                # Database records updated
    freshness_threshold = Column(Integer)                       # Cache TTL used (seconds)
    
    # Relationships
    device = relationship("Device")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_audit_device_type_time', 'device_id', 'data_type', 'time'),
        Index('idx_audit_method_status', 'collection_method', 'status'),
        Index('idx_audit_performance', 'duration_ms', 'time'),
    )
```

#### **2. Extended Configuration Management (Beyond Proxy)**
```python
class ConfigurationSnapshot(Base):
    """Universal configuration file snapshots - extends proxy config pattern"""
    __tablename__ = "configuration_snapshots"
    
    # Primary key and identification
    id = Column(UUID, primary_key=True, default=uuid4)
    device_id = Column(UUID, ForeignKey("devices.id"), nullable=False, index=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # File identification
    config_type = Column(String(50), nullable=False, index=True)  # "docker_compose", "systemd_service", "nginx_conf"
    file_path = Column(String(1024), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA256
    file_size_bytes = Column(Integer)
    
    # Configuration content - NEVER purged for self-hosters
    raw_content = Column(Text, nullable=False)                   # Complete file contents
    parsed_data = Column(JSON)                                   # Structured data for querying
    
    # Change tracking
    change_type = Column(String(20), nullable=False)             # "CREATE", "MODIFY", "DELETE", "MOVE"
    previous_hash = Column(String(64))                           # Previous version hash
    
    # Collection metadata
    file_modified_time = Column(DateTime(timezone=True))         # File system modification time
    collection_source = Column(String(50), nullable=False)      # "file_watch", "polling", "api"
    detection_latency_ms = Column(Integer)                       # Time from change to detection
    
    # Impact analysis (computed)
    affected_services = Column(JSON, default=list)              # Services impacted by change
    requires_restart = Column(Boolean, default=False)           # Restart required flag
    risk_level = Column(String(20), default="MEDIUM")           # LOW, MEDIUM, HIGH, CRITICAL
    
    # Relationships  
    device = relationship("Device")
    change_events = relationship("ConfigurationChangeEvent", back_populates="snapshot")
    
    # Efficient querying indexes
    __table_args__ = (
        Index('idx_config_device_type_time', 'device_id', 'config_type', 'time'),
        Index('idx_config_path_hash', 'file_path', 'content_hash'),
        Index('idx_config_source_time', 'collection_source', 'time'),
        UniqueConstraint('device_id', 'file_path', 'content_hash', name='uq_device_file_hash'),
    )

class ConfigurationChangeEvent(Base):
    """Real-time configuration change events with impact analysis"""
    __tablename__ = "configuration_change_events"
    
    # Primary identification
    id = Column(UUID, primary_key=True, default=uuid4)
    device_id = Column(UUID, ForeignKey("devices.id"), nullable=False, index=True)
    snapshot_id = Column(UUID, ForeignKey("configuration_snapshots.id"), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Change details
    config_type = Column(String(50), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    change_type = Column(String(20), nullable=False)
    
    # Impact assessment
    affected_services = Column(JSON, default=list)              # List of affected service names
    service_dependencies = Column(JSON, default=dict)           # Dependency mapping
    requires_restart = Column(Boolean, default=False)
    restart_services = Column(JSON, default=list)               # Services needing restart
    
    # Change analysis
    changes_summary = Column(JSON, default=dict)                # Structured diff summary
    risk_level = Column(String(20), default="MEDIUM", index=True)
    confidence_score = Column(Numeric(3, 2))                    # Analysis confidence (0-1)
    
    # Processing status
    processed = Column(Boolean, default=False, index=True)      # Event processed flag
    notifications_sent = Column(JSON, default=list)             # Sent notification types
    
    # Relationships
    device = relationship("Device")
    snapshot = relationship("ConfigurationSnapshot", back_populates="change_events")
    
    # Performance indexes
    __table_args__ = (
        Index('idx_change_device_type_time', 'device_id', 'config_type', 'time'),
        Index('idx_change_risk_processed', 'risk_level', 'processed'),
        Index('idx_change_requires_restart', 'requires_restart', 'time'),
    )
```

#### **3. Service Collection Performance Tracking**
```python
class ServicePerformanceMetric(Base):
    """Track performance of data collection services (Hypertable)"""
    __tablename__ = "service_performance_metrics"
    
    # TimescaleDB primary key
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    service_name = Column(String(50), primary_key=True, nullable=False)  # "polling", "api", "mcp"
    
    # Performance metrics
    operations_total = Column(Integer, default=0)               # Total operations in period
    operations_successful = Column(Integer, default=0)          # Successful operations
    operations_failed = Column(Integer, default=0)              # Failed operations
    operations_cached = Column(Integer, default=0)              # Cache hits
    
    # Timing metrics
    avg_duration_ms = Column(Numeric(8, 2))                     # Average operation duration
    max_duration_ms = Column(Integer)                           # Maximum operation duration
    min_duration_ms = Column(Integer)                           # Minimum operation duration
    
    # SSH performance
    ssh_connections_created = Column(Integer, default=0)        # New SSH connections
    ssh_connections_reused = Column(Integer, default=0)         # Reused SSH connections
    ssh_commands_executed = Column(Integer, default=0)          # Total SSH commands
    
    # Cache performance
    cache_hit_ratio = Column(Numeric(5, 2))                     # Cache hit percentage
    cache_size_entries = Column(Integer)                        # Current cache entries
    cache_evictions = Column(Integer, default=0)                # Cache evictions in period
    
    # Data volume
    data_collected_bytes = Column(BigInteger, default=0)        # Total data collected
    database_writes = Column(Integer, default=0)                # Database write operations
    
    # Error analysis
    error_types = Column(JSON, default=dict)                    # Error type counts
    top_errors = Column(JSON, default=list)                     # Most common errors
    
    # Performance indexes
    __table_args__ = (
        Index('idx_service_perf_time', 'time'),
        Index('idx_service_perf_name_time', 'service_name', 'time'),
    )
```

#### **4. Unified Cache State Management**
```python
class CacheMetadata(Base):
    """Track cache state and invalidation across all services"""
    __tablename__ = "cache_metadata" 
    
    # Primary identification
    cache_key = Column(String(255), primary_key=True)           # MD5 hash of cache key
    device_id = Column(UUID, ForeignKey("devices.id"), nullable=False, index=True)
    data_type = Column(String(50), nullable=False, index=True)
    
    # Cache lifecycle
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_accessed = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Usage statistics
    access_count = Column(Integer, default=1)                   # Number of cache hits
    data_size_bytes = Column(Integer)                           # Cached data size
    ttl_seconds = Column(Integer, nullable=False)               # Cache TTL
    
    # Invalidation tracking
    invalidated = Column(Boolean, default=False, index=True)    # Manual invalidation flag
    invalidated_at = Column(DateTime(timezone=True))            # Invalidation timestamp
    invalidation_reason = Column(String(100))                   # Why invalidated
    
    # Source tracking
    collection_method = Column(String(50))                      # How data was collected
    command_hash = Column(String(64))                           # SSH command fingerprint
    
    # Relationships
    device = relationship("Device")
    
    # Efficient cleanup and monitoring indexes
    __table_args__ = (
        Index('idx_cache_device_type', 'device_id', 'data_type'),
        Index('idx_cache_expires_invalidated', 'expires_at', 'invalidated'),
        Index('idx_cache_access_pattern', 'last_accessed', 'access_count'),
    )
```

### **Fresh Database Schema Strategy**

#### **Complete Schema Rewrite**
```python
# Fresh start migration: create_unified_infrastructure_schema.py
"""Complete unified infrastructure management schema

Revision ID: [new_id]
Revises: None  # Fresh database - no backward compatibility
Create Date: [current_date]
"""

def upgrade() -> None:
    # 1. Create optimized device registry
    op.create_table('devices', ...)  # Enhanced with unified relationships
    
    # 2. Create all time-series hypertables from scratch
    op.create_table('system_metrics', ...)
    op.create_table('drive_health', ...)
    op.create_table('container_snapshots', ...)
    
    # 3. Create unified audit and configuration system
    op.create_table('data_collection_audit', ...)
    op.create_table('configuration_snapshots', ...)
    op.create_table('configuration_change_events', ...)
    op.create_table('service_performance_metrics', ...)
    op.create_table('cache_metadata', ...)
    
    # 4. Create streamlined proxy configuration system
    op.create_table('proxy_configs', ...)  # Integrated with unified config
    op.create_table('proxy_config_changes', ...)

def downgrade() -> None:
    # Complete reset - no migration complexity
    pass
```

#### **Fresh TimescaleDB Schema**
```sql
-- Complete hypertable setup (02-hypertables.sql) - Fresh database
SELECT create_hypertable(
    'data_collection_audit',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'configuration_snapshots', 
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'configuration_change_events',
    'time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'service_performance_metrics',
    'time',
    chunk_time_interval => INTERVAL '1 hour',  -- Higher frequency
    if_not_exists => TRUE
);

-- Compression policies (03-policies.sql)
SELECT add_compression_policy('data_collection_audit', INTERVAL '7 days');
SELECT add_compression_policy('configuration_snapshots', INTERVAL '30 days');  -- Keep longer
SELECT add_compression_policy('configuration_change_events', INTERVAL '30 days');
SELECT add_compression_policy('service_performance_metrics', INTERVAL '3 days');

-- Retention policies - SELF-HOSTED OPTIMIZED (NO PURGING FOR CONFIGS)
SELECT add_retention_policy('data_collection_audit', INTERVAL '90 days');
-- NO retention policy for configuration_snapshots - keep forever for self-hosters
-- NO retention policy for configuration_change_events - keep forever for self-hosters  
SELECT add_retention_policy('service_performance_metrics', INTERVAL '30 days');
```

---

## 📁 **File and Folder Changes Required**

### **Files to be Created**

#### **New Model Files**
```
apps/backend/src/models/
├── audit.py                   # DataCollectionAudit model
├── configuration.py           # ConfigurationSnapshot, ConfigurationChangeEvent
├── performance.py             # ServicePerformanceMetric model  
└── cache.py                   # CacheMetadata model
```

#### **New Schema Files**
```
apps/backend/src/schemas/
├── audit.py                   # Audit trail response schemas
├── configuration.py           # Configuration snapshot/change response schemas
├── performance.py             # Performance metrics response schemas
└── cache.py                   # Cache management response schemas
```

#### **New Service Files**
```
apps/backend/src/services/
├── unified_data_collection.py     # Main UnifiedDataCollectionService
├── configuration_monitoring.py    # ConfigurationMonitoringService + RemoteFileWatcher
├── cache_manager.py               # CacheManager with LRU eviction
├── performance_tracker.py         # Service performance tracking
└── parsers/                       # Configuration parsers
    ├── __init__.py
    ├── docker_compose_parser.py   # Docker compose file parser
    ├── systemd_parser.py          # Systemd service file parser
    └── nginx_parser.py            # Enhanced nginx config parser
```

#### **Fresh Database Schema**
```
apps/backend/alembic/versions/
└── [timestamp]_create_unified_infrastructure_schema.py  # Complete schema rewrite
```

#### **Updated Init Scripts**
```
apps/backend/init-scripts/
├── 02-hypertables.sql         # ADD: New hypertables 
├── 03-policies.sql            # ADD: New compression/retention policies
└── 05-unified-functions.sql   # NEW: Utility functions for unified service
```

### **Files to be Replaced/Rewritten**

#### **Model Layer Overhaul**
```
apps/backend/src/models/
├── __init__.py                # REWRITE: All model imports
├── device.py                  # REWRITE: Enhanced with unified relationships
├── proxy_config.py            # REWRITE: Simplified, integrated with unified config
├── metrics.py                 # REWRITE: Optimized for unified collection
└── container.py               # REWRITE: Streamlined for unified service
```

#### **Service Layer Complete Rewrite**  
```
apps/backend/src/services/
├── polling_service.py         # REWRITE: Unified service orchestration only
├── metrics_service.py         # REWRITE: API layer only, no direct SSH
├── container_service.py       # REWRITE: Management only, no SSH duplication
└── device_service.py          # REWRITE: Device registry + config monitoring
```

#### **API Layer Updates**
```
apps/backend/src/api/
├── devices.py                 # ADD: Configuration history endpoints
├── containers.py              # UPDATE: Use unified service, add audit trail
├── metrics.py                 # UPDATE: Use unified service, add audit trail
└── system.py                  # ADD: Performance metrics, cache management endpoints
```

#### **MCP Tools Updates**
```
apps/backend/src/mcp/tools/
├── system_monitoring.py       # UPDATE: Use HTTP calls to unified API
├── container_management.py    # UPDATE: Use HTTP calls to unified API
├── device_management.py       # UPDATE: Use HTTP calls to unified API
└── configuration_management.py # NEW: Configuration change history tools
```

#### **Core Infrastructure Updates**
```
apps/backend/src/core/
├── database.py                # ADD: New model imports, hypertable creation
├── events.py                  # ADD: Configuration change events
└── config.py                  # ADD: Unified service configuration settings
```

### **SSH Duplication Elimination**

#### **Code Removal During Service Rewrites**
```
# SSH code to be eliminated during complete service rewrites:
apps/backend/src/services/
├── polling_service.py         # REMOVE: ~200 lines of duplicate SSH logic
├── metrics_service.py         # REMOVE: ~150 lines of duplicate SSH logic  
└── container_service.py       # REMOVE: ~100 lines of duplicate SSH logic

# MCP tools complete SSH elimination:
apps/backend/src/mcp/tools/
├── system_monitoring.py       # REMOVE: Direct SSH calls (~50 lines)
├── container_management.py    # REMOVE: Direct SSH calls (~30 lines)  
└── device_management.py       # REMOVE: Direct SSH calls (~40 lines)

# Total SSH duplication elimination: ~570 lines of code
```

### **Configuration Files to Update**

#### **Environment Configuration**
```
.env.example / .env
# ADD: Unified service configuration
UNIFIED_SERVICE_ENABLED=true
CACHE_MAX_ENTRIES=1000
CACHE_DEFAULT_TTL=300
FILE_WATCHING_ENABLED=true
PERFORMANCE_TRACKING_ENABLED=true
```

#### **Alembic Configuration**
```
apps/backend/alembic.ini
# NO CHANGES: Current configuration supports new models
```

#### **Database Connection Updates**
```
apps/backend/src/core/database.py
# ADD: Import new model classes for metadata registration
# ADD: New hypertable creation in create_hypertables() function  
# ADD: New table validation in validate_database_schema()
```

The unified database schema provides complete audit trails, configuration change tracking, and performance monitoring while extending the existing sophisticated proxy configuration management patterns. All new tables are designed as TimescaleDB hypertables with appropriate compression and retention policies optimized for self-hosted environments.

---

## 📊 **Summary of Database Schema Changes**

### **Database Impact Overview**
- **5 new TimescaleDB hypertables** for audit, configuration, and performance data
- **Permanent storage** for all configuration files (optimized for self-hosters)
- **Extended compression policies** with 7-day threshold for new time-series data
- **Smart retention policies**: No retention for configs, 90-day audit trails, 30-day performance metrics

### **Code Architecture Impact**
- **10 new files** (~2,350 lines) for unified collection, file watching, and caching
- **15 modified files** with ~850 lines removed (duplicate SSH code) and ~450 lines added (integrations)
- **89% reduction** in SSH connections (from ~45 to ~5 per minute)
- **Real-time configuration monitoring** replacing 5-minute polling intervals

### **Performance Optimization Summary**
- **Smart caching** with 80% hit rate target and LRU eviction
- **Event-driven file watching** with millisecond change detection latency
- **Unified data collection** eliminating duplicate operations across 11 service files
- **Self-hosted optimization** with permanent configuration storage and no cloud dependencies

### **Simplified Implementation Timeline**
- **Week 1**: Database schema overhaul - create all new TimescaleDB hypertables from scratch
- **Week 2**: Core unified data collection service implementation (~800 lines)
- **Week 3**: Real-time configuration monitoring with file watching (~400 lines)
- **Week 4**: Service layer refactoring - replace all SSH duplication (~850 lines removed)
- **Week 5**: API integration and MCP tools update
- **Week 6**: Testing, optimization, and deployment

**Clean Implementation Approach:**
- **Database Reset**: Fresh schema with all new models and optimized structure
- **Service Replacement**: Complete rewrite of data collection architecture
- **No Migration Complexity**: Direct implementation without compatibility layers
- **Optimized Performance**: Built from ground up for self-hosted environments

This streamlined approach transforms the infrastructor project into a unified, event-driven data collection platform without the complexity of maintaining backward compatibility or gradual migration phases.

---

## 🚨 **Alerting Strategy**

### **Current Implementation Analysis**
Based on analysis of existing infrastructure monitoring patterns:

- **apps/backend/src/core/database.py:356**: Comprehensive health check with connection pool monitoring
- **apps/backend/src/utils/ssh_errors.py:186**: Sophisticated error classification with escalation flags
- **apps/backend/src/models/proxy_config.py:70**: Sync status tracking with error counting mechanisms

### **Alert Categories & Thresholds**

#### **Critical Configuration Changes**
```python
# Based on ProxyConfigChange model analysis
CRITICAL_CONFIG_ALERTS = {
    "proxy_config_changes": {
        "threshold": "immediate",  # All changes
        "escalation_conditions": [
            "change_type == 'deleted'",
            "errors_detected > 0",
            "validation_failed == True"
        ],
        "alert_channels": ["webhook", "email"],
        "correlation_window": "5m"
    },
    "docker_compose_changes": {
        "threshold": "service_restart_required",
        "escalation_conditions": [
            "dependent_services > 3",
            "production_environment == True"
        ]
    }
}
```

#### **SSH Connection Failures**
```python
# Based on ssh_errors.py classification patterns
SSH_ALERT_THRESHOLDS = {
    "connection_refused": {
        "threshold": 3,  # failures in 5 minutes
        "escalation_after": 2,  # escalate after 2 consecutive
        "recovery_check_interval": "30s"
    },
    "authentication_failed": {
        "threshold": 1,  # immediate escalation
        "escalation_required": True,  # from SSHErrorInfo
        "alert_severity": "critical"
    },
    "system_overload": {
        "threshold": "load_average > 5.0",
        "correlation_with": ["memory_usage", "disk_io"],
        "retry_backoff": "exponential"  # from ssh_errors.py:467
    }
}
```

#### **Cache Performance Degradation**
```python
# Based on smart caching implementation patterns
CACHE_PERFORMANCE_ALERTS = {
    "hit_rate_degradation": {
        "threshold": "hit_rate < 60%",  # below 80% target
        "measurement_window": "15m",
        "escalation_conditions": [
            "hit_rate < 40%",
            "cache_misses > 100/minute"
        ]
    },
    "cache_memory_pressure": {
        "threshold": "lru_evictions > 50/minute",
        "correlation_with": ["system_memory_usage"]
    }
}
```

#### **Service Performance Anomalies**
```python
# Based on database health monitoring patterns
SERVICE_PERFORMANCE_ALERTS = {
    "database_connection_pool": {
        "thresholds": {
            "checked_out_ratio": "> 0.8",  # from database.py:298
            "connection_timeouts": "> 5/minute",
            "pool_overflow": "> max_overflow * 0.5"
        },
        "escalation_delay": "5m"
    },
    "ssh_command_execution": {
        "thresholds": {
            "avg_execution_time": "> 30s",
            "timeout_rate": "> 5%",
            "retry_escalation": "> 3 attempts"  # from ssh_errors.py
        }
    }
}
```

#### **Database Connection Issues**
```python
# Based on TimescaleDB health monitoring
DATABASE_ALERTS = {
    "connection_health": {
        "critical_thresholds": {
            "active_connections": "> pool_size * 0.9",
            "transaction_rollback_rate": "> 10%",
            "hypertable_unavailable": "any"
        },
        "recovery_actions": [
            "pool_refresh",
            "connection_recycling",
            "hypertable_validation"
        ]
    },
    "timescaledb_specific": {
        "compression_failures": "immediate",
        "chunk_creation_errors": "immediate",
        "retention_policy_failures": "within 1h"
    }
}
```

### **Alert Delivery & Escalation**
- **Webhook Integration**: Real-time alerts to external monitoring systems
- **Email Notifications**: Critical alerts with 15-minute batching for non-critical
- **Event Bus Integration**: Internal alert routing with correlation IDs
- **Escalation Matrix**: Auto-escalation based on `escalation_required` flags from error classification

---

## 📋 **Logging Strategy**

### **Current Implementation Analysis**
Based on existing logging patterns across the codebase:

- **Structured Logging**: `structlog>=25.4.0` in pyproject.toml for consistent formatting
- **Logger Instances**: Standard `logging.getLogger(__name__)` pattern in 25+ files
- **Error Context**: Exception chaining with `raise NewError() from e` patterns

### **Structured Logging with Correlation IDs**

#### **Enhanced Logger Configuration**
```python
# Enhanced logging configuration based on current patterns
import structlog
from datetime import datetime, timezone

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(colors=True),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
            ],
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/api_server.log",  # existing log location
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "structured",
        }
    },
    "loggers": {
        "apps.backend": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        }
    }
}
```

#### **Correlation ID Middleware**
```python
# Based on FastAPI middleware pattern from current architecture
import uuid
from contextvars import ContextVar
from fastapi import Request, Response

correlation_id_var: ContextVar[str] = ContextVar('correlation_id')

class CorrelationIDMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate or extract correlation ID
            correlation_id = str(uuid.uuid4())
            correlation_id_var.set(correlation_id)
            
            # Add to structlog context
            structlog.contextvars.bind_contextvars(
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        await self.app(scope, receive, send)
```

### **Configuration Change Audit Trails**

#### **Configuration Change Logging**
```python
# Based on ProxyConfigChange model patterns
class ConfigurationAuditLogger:
    def __init__(self):
        self.logger = structlog.get_logger("config_audit")
    
    async def log_config_change(self, device_id: str, config_type: str, 
                               change_type: str, changes_detected: List[str]):
        """Log configuration changes with full audit context"""
        audit_entry = {
            "event_type": "configuration_change",
            "device_id": device_id,
            "config_type": config_type,  # proxy_configs, docker_compose
            "change_type": change_type,  # created, modified, deleted, synced
            "changes_detected": changes_detected,
            "file_hash_before": getattr(self, 'old_hash', None),
            "file_hash_after": getattr(self, 'new_hash', None),
            "triggered_by": "file_watcher",  # or manual, api, polling
            "validation_status": "pending",
            "sync_required": True
        }
        
        self.logger.info("Configuration change detected", **audit_entry)
        
        # Store in database for TimescaleDB querying
        await self._store_audit_entry(audit_entry)
```

#### **SSH Command Execution Logs**
```python
# Based on ssh_client.py and ssh_command_manager.py patterns
class SSHCommandLogger:
    def __init__(self):
        self.logger = structlog.get_logger("ssh_commands")
    
    async def log_command_execution(self, result: SSHExecutionResult, 
                                   connection_info: SSHConnectionInfo):
        """Log SSH command execution with full context"""
        log_entry = {
            "event_type": "ssh_command_execution",
            "device_id": connection_info.host,
            "command": result.command,
            "return_code": result.return_code,
            "execution_time": result.execution_time,
            "success": result.success,
            "stdout_length": len(result.stdout),
            "stderr_length": len(result.stderr),
            "connection_pool_stats": await self._get_pool_stats(),
            "retry_attempt": getattr(result, 'retry_attempt', 0)
        }
        
        if result.success:
            self.logger.info("SSH command executed successfully", **log_entry)
        else:
            log_entry["error_message"] = result.error_message
            log_entry["error_classification"] = await self._classify_error(result)
            self.logger.error("SSH command failed", **log_entry)
```

### **Cache Operations Logging**
```python
# Based on smart caching implementation
class CacheOperationLogger:
    def __init__(self):
        self.logger = structlog.get_logger("cache_operations")
    
    async def log_cache_operation(self, operation: str, cache_key: str, 
                                 hit: bool = None, ttl: int = None):
        """Log cache operations for performance analysis"""
        log_entry = {
            "event_type": "cache_operation",
            "operation": operation,  # get, set, evict, expire
            "cache_key": cache_key,
            "cache_hit": hit,
            "ttl_seconds": ttl,
            "cache_size": await self._get_cache_size(),
            "hit_rate_current": await self._calculate_hit_rate()
        }
        
        self.logger.debug("Cache operation", **log_entry)
```

### **Error Aggregation and Analysis**
```python
# Based on ssh_errors.py classification system
class ErrorAggregationLogger:
    def __init__(self):
        self.logger = structlog.get_logger("error_analysis")
        self.error_counters = {}
    
    async def log_classified_error(self, error_info: SSHErrorInfo, 
                                  context: Dict[str, Any]):
        """Log errors with classification for aggregation"""
        error_key = f"{error_info.error_type.value}:{context.get('device_id')}"
        
        log_entry = {
            "event_type": "classified_error",
            "error_type": error_info.error_type.value,
            "is_retryable": error_info.is_retryable,
            "escalation_required": error_info.escalation_required,
            "recovery_suggestion": error_info.recovery_suggestion,
            "occurrence_count": self.error_counters.get(error_key, 0) + 1,
            **context
        }
        
        self.error_counters[error_key] = log_entry["occurrence_count"]
        
        if error_info.escalation_required:
            self.logger.error("Error requires escalation", **log_entry)
        else:
            self.logger.warning("Classified error occurred", **log_entry)
```

---

## 🔗 **SSH Connection Optimization**

### **Current Implementation Analysis**
Based on detailed analysis of SSH infrastructure:

- **apps/backend/src/utils/ssh_client.py:62**: Existing connection pool with 3 connections per host
- **apps/backend/src/utils/ssh_client.py:69**: 30-second connection timeout configuration
- **apps/backend/src/utils/ssh_errors.py:467**: Exponential backoff retry logic with 1.5x multiplier

### **Connection Pool Sizing Guidelines**

#### **Optimized Pool Configuration**
```python
# Based on current SSHConnectionPool analysis
OPTIMIZED_POOL_CONFIG = {
    "pool_sizing": {
        "max_connections_per_host": 2,  # Reduced from current 3
        "connection_timeout": 15,       # Reduced from current 30s
        "idle_timeout": 300,           # 5 minutes idle before cleanup
        "max_connection_lifetime": 3600 # 1 hour maximum lifetime
    },
    "pool_efficiency": {
        "connection_reuse_ratio": 0.85,  # Target 85% reuse
        "pool_utilization_target": 0.7,  # Keep 30% buffer
        "cleanup_interval": 60           # Cleanup every minute
    }
}
```

#### **Dynamic Pool Sizing Based on Device Load**
```python
# Enhanced pool sizing based on device activity patterns
class AdaptivePoolSizer:
    def __init__(self):
        self.device_activity = {}
        self.pool_configs = {}
    
    async def calculate_optimal_pool_size(self, device_id: str) -> int:
        """Calculate optimal pool size based on device activity"""
        activity = self.device_activity.get(device_id, {})
        
        # Base calculations from current usage patterns
        commands_per_minute = activity.get('commands_per_minute', 0)
        avg_execution_time = activity.get('avg_execution_time', 5.0)
        concurrent_operations = activity.get('concurrent_operations', 1)
        
        # Formula: (commands/min * avg_time/60) + buffer
        optimal_size = max(1, int(
            (commands_per_minute * avg_execution_time / 60) + 
            (concurrent_operations * 0.5)
        ))
        
        # Cap at reasonable limits
        return min(optimal_size, 4)  # Max 4 connections per device
```

### **SSH Keep-Alive Configuration**

#### **Enhanced Keep-Alive Settings**
```python
# Based on current SSHConnectionInfo patterns
KEEPALIVE_CONFIG = {
    "ssh_client_options": {
        "ServerAliveInterval": 60,      # Send keep-alive every 60s
        "ServerAliveCountMax": 3,       # 3 failed keep-alives = disconnect
        "TCPKeepAlive": True,           # Enable TCP-level keep-alive
        "ClientAliveInterval": 60,      # Server-side keep-alive
        "ClientAliveCountMax": 3        # Server-side failure threshold
    },
    "connection_health": {
        "health_check_interval": 120,   # Check connection health every 2min
        "stale_connection_threshold": 300, # Mark stale after 5min inactivity
        "automatic_reconnect": True,    # Auto-reconnect on failure
        "reconnect_delay": 5.0         # Wait 5s before reconnecting
    }
}
```

### **Timeout and Retry Optimization**

#### **Adaptive Timeout Configuration**
```python
# Based on current timeout patterns and error classification
ADAPTIVE_TIMEOUTS = {
    "command_categories": {
        "system_metrics": {
            "base_timeout": 10,         # Quick metrics collection
            "max_timeout": 30,
            "retry_multiplier": 1.2     # Conservative backoff
        },
        "container_management": {
            "base_timeout": 20,         # Docker operations
            "max_timeout": 60,
            "retry_multiplier": 1.5     # Current exponential backoff
        },
        "drive_health": {
            "base_timeout": 45,         # SMART data collection
            "max_timeout": 120,
            "retry_multiplier": 1.3
        },
        "file_operations": {
            "base_timeout": 15,         # File watching, config sync
            "max_timeout": 45,
            "retry_multiplier": 1.4
        }
    }
}
```

#### **Intelligent Retry Logic**
```python
# Enhanced version of current ssh_errors.py retry logic
class IntelligentRetryManager:
    def __init__(self):
        self.retry_history = {}
        self.success_patterns = {}
    
    async def should_retry_with_context(self, error_info: SSHErrorInfo, 
                                       device_id: str, attempt: int) -> bool:
        """Enhanced retry logic with device-specific learning"""
        base_should_retry = error_info.is_retryable and attempt < error_info.max_retries
        
        if not base_should_retry:
            return False
        
        # Check device-specific success patterns
        device_history = self.retry_history.get(device_id, {})
        error_type = error_info.error_type.value
        
        # If this error type frequently succeeds on retry for this device
        if error_type in device_history:
            success_rate = device_history[error_type].get('success_after_retry', 0)
            if success_rate > 0.7:  # 70% success rate
                return True
        
        # Enhanced backoff based on device load
        device_load = await self._get_device_load(device_id)
        if device_load > 0.8 and error_info.error_type in [
            SSHErrorType.SYSTEM_OVERLOAD, 
            SSHErrorType.RESOURCE_BUSY
        ]:
            # Extend retry delay for overloaded systems
            return attempt < (error_info.max_retries + 2)
        
        return base_should_retry
```

### **Connection Reuse Strategies**

#### **Smart Connection Reuse**
```python
# Enhanced connection reuse based on current pool patterns
class ConnectionReuseOptimizer:
    def __init__(self):
        self.connection_affinity = {}
        self.command_patterns = {}
    
    async def optimize_connection_assignment(self, device_id: str, 
                                           command_category: str) -> str:
        """Assign connections based on command patterns"""
        device_connections = self.connection_affinity.get(device_id, {})
        
        # Prefer connections that recently executed similar commands
        for conn_id, last_commands in device_connections.items():
            if command_category in last_commands[-3:]:  # Last 3 commands
                if await self._is_connection_healthy(conn_id):
                    return conn_id
        
        # Fall back to least recently used healthy connection
        return await self._get_lru_healthy_connection(device_id)
    
    async def track_command_execution(self, connection_id: str, 
                                    command_category: str):
        """Track command execution for affinity optimization"""
        if connection_id not in self.command_patterns:
            self.command_patterns[connection_id] = []
        
        self.command_patterns[connection_id].append({
            'category': command_category,
            'timestamp': datetime.now(timezone.utc),
            'success': True  # Will be updated based on result
        })
        
        # Keep only recent history (last 20 commands)
        if len(self.command_patterns[connection_id]) > 20:
            self.command_patterns[connection_id] = \
                self.command_patterns[connection_id][-20:]
```

#### **Connection Health Monitoring**
```python
# Based on current cleanup and health check patterns
class ConnectionHealthMonitor:
    def __init__(self):
        self.health_stats = {}
        self.monitoring_interval = 30  # Check every 30 seconds
    
    async def monitor_connection_health(self, connection_id: str) -> Dict[str, Any]:
        """Monitor individual connection health metrics"""
        stats = {
            "connection_id": connection_id,
            "commands_executed": 0,
            "avg_response_time": 0.0,
            "error_rate": 0.0,
            "last_activity": None,
            "tcp_state": "unknown",
            "is_healthy": False
        }
        
        # Get connection statistics
        conn_history = self.health_stats.get(connection_id, [])
        if conn_history:
            stats["commands_executed"] = len(conn_history)
            stats["avg_response_time"] = sum(h['duration'] for h in conn_history) / len(conn_history)
            stats["error_rate"] = sum(1 for h in conn_history if not h['success']) / len(conn_history)
            stats["last_activity"] = max(h['timestamp'] for h in conn_history)
        
        # Health check via lightweight command
        try:
            start_time = time.time()
            result = await self._execute_health_check(connection_id)
            response_time = time.time() - start_time
            
            stats["is_healthy"] = result.success and response_time < 5.0
            stats["last_health_check"] = datetime.now(timezone.utc)
            
        except Exception as e:
            stats["health_check_error"] = str(e)
            stats["is_healthy"] = False
        
        return stats
```

---

## ⚠️ **SSH Error Scenarios**

### **Current Error Handling Analysis**
Based on comprehensive analysis of existing error handling infrastructure:

- **apps/backend/src/utils/ssh_errors.py:19**: 16 distinct error types with classification
- **apps/backend/src/utils/ssh_errors.py:186**: Detailed error configurations with retry strategies
- **apps/backend/src/utils/ssh_errors.py:335**: Pattern-based error classification system

### **Connection-Level Error Scenarios**

#### **Network Connectivity Failures**
```python
# Based on current SSHErrorType classifications
NETWORK_ERROR_SCENARIOS = {
    "connection_refused": {
        "current_handling": "3 retries with 5s delay",  # from ERROR_CONFIGS
        "enhanced_detection": [
            "Port scan target device before retry",
            "Check Tailscale connectivity status",
            "Validate device is responding to ping"
        ],
        "recovery_actions": [
            "Switch to backup connection method",
            "Attempt SSH on alternate port (2222)",
            "Escalate to manual intervention"
        ]
    },
    "dns_resolution_failed": {
        "current_handling": "2 retries with 5s delay",
        "enhanced_detection": [
            "Try IP address resolution",
            "Check /etc/hosts entries",
            "Validate DNS server responsiveness"
        ],
        "fallback_strategy": "Use cached IP addresses from device registry"
    },
    "host_unreachable": {
        "current_handling": "2 retries with 10s delay",
        "network_diagnostics": [
            "Traceroute to identify network path failure",
            "Check routing table for subnet accessibility",
            "Validate Tailscale mesh connectivity"
        ]
    }
}
```

#### **Authentication and Authorization Failures**
```python
# Based on auth-related error types from ssh_errors.py
AUTH_ERROR_SCENARIOS = {
    "authentication_failed": {
        "current_handling": "No retry, immediate escalation",  # escalation_required=True
        "enhanced_diagnostics": [
            "Validate SSH key file exists and permissions (600)",
            "Check user exists on target system",
            "Verify SSH daemon configuration allows key auth"
        ],
        "recovery_options": [
            "Attempt password authentication if configured",
            "Use backup SSH key if available",
            "Generate new key pair and deploy"
        ]
    },
    "key_not_found": {
        "current_handling": "No retry, immediate escalation",
        "file_validation": [
            "Check SSH_KEY_PATH environment variable",
            "Validate key file format (PEM/OpenSSH)",
            "Confirm key permissions and ownership"
        ]
    },
    "passphrase_required": {
        "current_handling": "No retry, immediate escalation",
        "enhanced_handling": [
            "Prompt for passphrase via secure channel",
            "Use ssh-agent if available",
            "Consider key re-encryption without passphrase"
        ]
    }
}
```

### **Command Execution Error Scenarios**

#### **System Resource Exhaustion**
```python
# Based on system-related error types
RESOURCE_ERROR_SCENARIOS = {
    "disk_full": {
        "current_handling": "2 retries with 30s delay, escalation required",
        "enhanced_detection": [
            "Check disk usage on all mount points",
            "Identify largest files/directories",
            "Monitor disk usage trends"
        ],
        "automatic_recovery": [
            "Clean temporary files if safe",
            "Rotate log files if configured",
            "Compress old data if possible"
        ],
        "prevention": [
            "Set up disk usage monitoring alerts",
            "Implement automatic cleanup policies",
            "Monitor growth patterns"
        ]
    },
    "out_of_memory": {
        "current_handling": "2 retries with 60s delay, escalation required",
        "system_analysis": [
            "Check memory usage by process",
            "Identify memory leaks in long-running processes",
            "Monitor swap usage patterns"
        ],
        "recovery_actions": [
            "Restart high-memory processes if safe",
            "Clear system caches",
            "Gracefully restart services"
        ]
    },
    "system_overload": {
        "current_handling": "3 retries with 30s delay",
        "load_analysis": [
            "Check CPU load average trends",
            "Identify high-CPU processes",
            "Monitor I/O wait times"
        ],
        "throttling_strategy": [
            "Reduce command execution frequency",
            "Implement command queuing",
            "Prioritize critical operations"
        ]
    }
}
```

#### **Infrastructure-Specific Failures**
```python
# Based on infrastructure-specific error types
INFRASTRUCTURE_ERROR_SCENARIOS = {
    "container_not_running": {
        "current_handling": "2 retries with 5s delay",
        "enhanced_detection": [
            "Check Docker daemon status",
            "Validate container exists in Docker registry",
            "Check for resource constraints preventing start"
        ],
        "recovery_actions": [
            "Attempt container restart",
            "Check container dependencies",
            "Pull latest image if corrupted"
        ]
    },
    "zfs_pool_unavailable": {
        "current_handling": "2 retries with 10s delay",
        "pool_diagnostics": [
            "Check ZFS pool import status",
            "Validate pool health and scrub status",
            "Check for missing or faulted devices"
        ],
        "recovery_procedures": [
            "Import pool if not imported",
            "Clear pool errors if recoverable",
            "Escalate for hardware issues"
        ]
    },
    "service_not_installed": {
        "current_handling": "No retry",
        "service_validation": [
            "Check package manager for service availability",
            "Validate service binary exists in PATH",
            "Check for alternative service names"
        ],
        "automated_installation": [
            "Install via package manager if configured",
            "Use configuration management tools",
            "Deploy via container if applicable"
        ]
    }
}
```

### **Error Correlation and Pattern Recognition**
```python
# Enhanced error correlation based on current classification system
class ErrorPatternAnalyzer:
    def __init__(self):
        self.error_history = {}
        self.correlation_patterns = {}
    
    async def analyze_error_correlation(self, device_id: str, 
                                      error_sequence: List[SSHErrorInfo]) -> Dict[str, Any]:
        """Analyze error patterns for predictive failure detection"""
        analysis = {
            "device_id": device_id,
            "error_sequence": [e.error_type.value for e in error_sequence],
            "correlation_detected": False,
            "predicted_failures": [],
            "recommended_actions": []
        }
        
        # Check for escalating patterns
        if self._detect_escalating_errors(error_sequence):
            analysis["correlation_detected"] = True
            analysis["pattern_type"] = "escalating_failure"
            analysis["predicted_failures"].append("system_failure_imminent")
            analysis["recommended_actions"].append("immediate_manual_intervention")
        
        # Check for periodic patterns
        if self._detect_periodic_errors(device_id, error_sequence):
            analysis["correlation_detected"] = True
            analysis["pattern_type"] = "periodic_resource_exhaustion"
            analysis["recommended_actions"].extend([
                "schedule_maintenance_window",
                "implement_preventive_cleanup",
                "monitor_resource_trends"
            ])
        
        return analysis
    
    def _detect_escalating_errors(self, error_sequence: List[SSHErrorInfo]) -> bool:
        """Detect if errors are escalating in severity"""
        severity_levels = {
            SSHErrorType.TEMPORARY_FAILURE: 1,
            SSHErrorType.RESOURCE_BUSY: 2,
            SSHErrorType.SYSTEM_OVERLOAD: 3,
            SSHErrorType.OUT_OF_MEMORY: 4,
            SSHErrorType.DISK_FULL: 5
        }
        
        if len(error_sequence) < 3:
            return False
        
        # Check if severity is generally increasing
        severities = [severity_levels.get(e.error_type, 0) for e in error_sequence[-5:]]
        return len(severities) > 2 and severities[-1] > severities[0]
```

---

## 📁 **Configuration Monitoring Errors**

### **Current Configuration Monitoring Analysis**
Based on analysis of existing configuration management patterns:

- **apps/backend/src/models/proxy_config.py:70**: Sync status tracking with error count fields
- **File watching implementation**: Real-time inotify-based configuration monitoring
- **Change detection**: Hash-based change detection with validation

### **File System Monitoring Errors**

#### **inotify and File Watching Failures**
```python
# Based on RemoteFileWatcher implementation patterns
FILE_MONITORING_ERRORS = {
    "inotify_limit_exceeded": {
        "detection": "inotify: No space left on device",
        "cause": "Exceeded fs.inotify.max_user_watches limit",
        "recovery_actions": [
            "Increase kernel inotify limits: echo 524288 > /proc/sys/fs/inotify/max_user_watches",
            "Optimize watched file patterns to reduce watch count", 
            "Implement polling fallback for non-critical paths"
        ],
        "prevention": [
            "Monitor inotify usage per device",
            "Set up alerts when approaching limits",
            "Use recursive watches efficiently"
        ]
    },
    "ssh_connection_dropped": {
        "detection": "SSH connection lost during file watching session",
        "recovery_strategy": [
            "Automatic reconnection with exponential backoff",
            "Resume file watching from last known state",
            "Validate missed changes via hash comparison"
        ],
        "enhanced_resilience": [
            "Use persistent SSH connections with keep-alive",
            "Implement connection health monitoring",
            "Buffer file change events during reconnection"
        ]
    },
    "file_permission_denied": {
        "detection": "Permission denied when accessing watched files",
        "diagnostics": [
            "Check file ownership and permissions",
            "Verify SSH user has read access to parent directories",
            "Validate SELinux/AppArmor policies"
        ],
        "recovery_options": [
            "Use sudo for privileged file access",
            "Request permission elevation from user",
            "Switch to polling mode for inaccessible files"
        ]
    }
}
```

#### **Configuration Parsing and Validation Errors**
```python
# Based on ProxyConfigValidation model patterns
CONFIG_PARSING_ERRORS = {
    "nginx_config_syntax_error": {
        "detection_patterns": [
            "nginx: [emerg] ",
            "configuration file .* test failed",
            "unknown directive"
        ],
        "error_handling": [
            "Store validation results in proxy_config_validations table",
            "Mark configuration as invalid in sync_status",
            "Increment sync_error_count in proxy_configs"
        ],
        "recovery_procedures": [
            "Revert to last known good configuration",
            "Validate configuration syntax before applying",
            "Provide detailed error context to administrators"
        ]
    },
    "docker_compose_format_error": {
        "detection_patterns": [
            "yaml: unmarshal errors:",
            "Invalid compose file",
            "services.* Additional property .* is not allowed"
        ],
        "validation_strategy": [
            "Use PyYAML with safe_load for initial parsing",
            "Validate against Docker Compose schema",
            "Check for required fields and proper formatting"
        ],
        "error_context": [
            "Line number and column of syntax error",
            "Specific validation rule that failed",
            "Suggested corrections based on common patterns"
        ]
    },
    "json_configuration_corruption": {
        "detection": "JSON decode errors in configuration files",
        "corruption_analysis": [
            "Check for partial file writes",
            "Validate file size against expected ranges",
            "Compare with backup configurations"
        ],
        "data_recovery": [
            "Attempt JSON repair using heuristics",
            "Restore from configuration backups",
            "Prompt user for manual validation"
        ]
    }
}
```

### **Configuration Synchronization Errors**

#### **Cross-Device Configuration Conflicts**
```python
# Based on sync_status and change tracking patterns
SYNC_CONFLICT_SCENARIOS = {
    "concurrent_modification": {
        "detection": [
            "File hash mismatch during sync operation",
            "Modification timestamp conflicts",
            "Multiple change events for same file"
        ],
        "resolution_strategy": [
            "Implement last-writer-wins with conflict logging",
            "Create conflict resolution queue for manual review",
            "Use distributed locking for critical configurations"
        ],
        "conflict_metadata": [
            "Store conflicting versions in separate database records",
            "Track modification sources (device, user, automation)",
            "Maintain conflict resolution audit trail"
        ]
    },
    "network_partition_recovery": {
        "scenario": "Configuration changes during network connectivity loss",
        "detection": [
            "Significant timestamp gaps in change history",
            "Batch of changes after connectivity restoration",
            "Inconsistent configuration states across devices"
        ],
        "recovery_procedures": [
            "Compare configuration hashes across all devices",
            "Identify authoritative source based on business rules",
            "Merge non-conflicting changes automatically",
            "Queue conflicting changes for review"
        ]
    }
}
```

#### **Configuration Backup and Restore Failures**
```python
# Enhanced backup strategy based on current change tracking
BACKUP_ERROR_SCENARIOS = {
    "backup_storage_full": {
        "detection": "Disk full when creating configuration backups",
        "mitigation": [
            "Implement backup rotation policy",
            "Compress older backup files",
            "Use external storage for long-term retention"
        ],
        "backup_optimization": [
            "Only backup changed configurations",
            "Use incremental backup strategies",
            "Implement backup deduplication"
        ]
    },
    "backup_corruption": {
        "detection": [
            "Checksum mismatch on backup files",
            "Incomplete backup files",
            "Backup restore test failures"
        ],
        "validation": [
            "Regular backup integrity checks",
            "Test restore procedures monthly",
            "Maintain multiple backup generations"
        ],
        "recovery_options": [
            "Restore from previous backup generation",
            "Reconstruct from configuration templates",
            "Use configuration management tools for regeneration"
        ]
    }
}
```

### **Configuration Change Impact Analysis**
```python
# Based on change detection and dependency tracking
class ConfigurationImpactAnalyzer:
    def __init__(self):
        self.dependency_graph = {}
        self.impact_cache = {}
    
    async def analyze_change_impact(self, config_change: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential impact of configuration changes"""
        impact_analysis = {
            "config_type": config_change["config_type"],
            "device_id": config_change["device_id"],
            "changes_detected": config_change["changes_detected"],
            "impact_severity": "low",
            "affected_services": [],
            "restart_required": False,
            "validation_required": True,
            "rollback_plan": []
        }
        
        # Analyze proxy configuration impacts
        if config_change["config_type"] == "proxy_configs":
            impact_analysis.update(await self._analyze_proxy_impact(config_change))
        
        # Analyze docker-compose impacts  
        elif config_change["config_type"] == "docker_compose":
            impact_analysis.update(await self._analyze_compose_impact(config_change))
        
        # Generate rollback plan
        impact_analysis["rollback_plan"] = await self._generate_rollback_plan(config_change)
        
        return impact_analysis
    
    async def _analyze_proxy_impact(self, config_change: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze impact of proxy configuration changes"""
        changes = config_change["changes_detected"]
        
        high_impact_changes = [
            "upstream server changes",
            "SSL certificate updates", 
            "authentication method changes"
        ]
        
        impact = {
            "impact_severity": "high" if any(change in changes for change in high_impact_changes) else "medium",
            "affected_services": ["nginx", "reverse_proxy"],
            "restart_required": "upstream" in ' '.join(changes).lower(),
            "validation_tests": [
                "nginx_config_test",
                "ssl_certificate_validation",
                "upstream_connectivity_check"
            ]
        }
        
        return impact
```

---

## 🗄️ **Database Error Scenarios**

### **Current Database Error Handling Analysis**
Based on comprehensive analysis of database infrastructure:

- **apps/backend/src/core/database.py:276**: Comprehensive health checking with connection pool monitoring
- **apps/backend/init-scripts/02-hypertables.sql**: 9 TimescaleDB hypertables with compression policies
- **Connection pooling**: AsyncAdaptedQueuePool with configurable pool sizing

### **Connection Pool and Resource Errors**

#### **Connection Pool Exhaustion**
```python
# Based on current connection pool configuration
CONNECTION_POOL_ERRORS = {
    "pool_exhaustion": {
        "detection": [
            "checked_out >= pool_size",
            "overflow >= max_overflow", 
            "QueuePool limit exceeded"
        ],
        "current_monitoring": {
            "pool_size": "from engine.pool.size()",         # database.py:297
            "checked_out": "from engine.pool.checkedout()", # database.py:299
            "overflow": "from engine.pool.overflow()"       # database.py:300
        },
        "recovery_actions": [
            "Increase pool_size temporarily",
            "Force connection recycling",
            "Kill long-running transactions",
            "Scale up database resources"
        ],
        "prevention": [
            "Monitor connection usage patterns",
            "Implement connection timeout policies", 
            "Add connection usage alerts at 80% threshold"
        ]
    },
    "connection_timeout": {
        "detection": "Connection timeout after pool_timeout seconds",
        "current_config": {
            "pool_timeout": "from settings.database.db_pool_timeout",
            "pool_recycle": "from settings.database.db_pool_recycle",
            "pool_pre_ping": "True"  # database.py:67
        },
        "adaptive_timeouts": [
            "Increase timeout during high load periods",
            "Implement circuit breaker pattern",
            "Use different timeouts for different operation types"
        ]
    },
    "connection_validation_failure": {
        "detection": "pool_pre_ping validation failed",
        "recovery_strategy": [
            "Force connection replacement",
            "Test database connectivity with raw SQL",
            "Restart connection pool if needed"
        ]
    }
}
```

#### **PostgreSQL and TimescaleDB Specific Errors**
```python
# Based on TimescaleDB-specific configurations and health checks
TIMESCALEDB_ERRORS = {
    "hypertable_chunk_creation_failure": {
        "detection_patterns": [
            "could not create chunk",
            "hypertable_id does not exist",
            "chunk creation failed"
        ],
        "diagnostics": [
            "Check TimescaleDB extension status",
            "Validate hypertable configuration", 
            "Monitor chunk sizing and intervals"
        ],
        "current_hypertables": [
            "system_metrics", "drive_health", "container_snapshots",
            "zfs_status", "zfs_snapshots", "network_interfaces", 
            "docker_networks", "vm_status", "system_logs"  # from 02-hypertables.sql
        ],
        "recovery_procedures": [
            "Recreate hypertable if corrupted",
            "Adjust chunk_time_interval settings",
            "Check disk space for chunk storage"
        ]
    },
    "compression_policy_failure": {
        "detection": "Compression job failed or policy not found",
        "current_compression_config": {
            "compress_after": "7 days",  # from database.py:548
            "tables_with_compression": [
                "system_metrics", "drive_health", "container_snapshots",
                "zfs_status", "zfs_snapshots", "network_interfaces",
                "docker_networks", "vm_status", "system_logs", 
                "backup_status", "system_updates"  # database.py:509-521
            ]
        },
        "recovery_actions": [
            "Re-enable compression on affected tables",
            "Manual compression of old chunks",
            "Adjust compression policies"
        ]
    },
    "retention_policy_failure": {
        "detection": "Data retention job failed",
        "current_retention_config": {
            "system_metrics": "retention_system_metrics_days setting",
            "drive_health": "retention_drive_health_days setting", 
            "container_snapshots": "retention_container_snapshots_days setting",
            "default_retention": "30-90 days depending on table"  # database.py:580-592
        },
        "impact_analysis": [
            "Monitor disk usage trends",
            "Check for retention job errors in logs",
            "Validate retention policy effectiveness"
        ]
    }
}
```

### **Data Integrity and Consistency Errors**

#### **Transaction and Concurrency Errors**
```python
# Based on session management and transaction handling patterns
TRANSACTION_ERRORS = {
    "deadlock_detection": {
        "detection": [
            "deadlock detected",
            "could not serialize access",
            "concurrent update conflicts"
        ],
        "resolution_strategy": [
            "Automatic transaction retry with exponential backoff",
            "Implement optimistic locking for frequently updated records",
            "Use advisory locks for critical operations"
        ],
        "deadlock_prevention": [
            "Consistent lock ordering in transactions",
            "Minimize transaction scope and duration",
            "Use SELECT ... FOR UPDATE NOWAIT where appropriate"
        ]
    },
    "constraint_violations": {
        "foreign_key_violations": {
            "detection": "violates foreign key constraint",
            "common_scenarios": [
                "Device deletion with existing metrics references",
                "Configuration changes referencing non-existent devices"
            ],
            "recovery": [
                "Validate referential integrity before operations",
                "Use CASCADE deletes where appropriate",
                "Implement soft deletes for critical data"
            ]
        },
        "unique_constraint_violations": {
            "detection": "violates unique constraint", 
            "handling": [
                "Use INSERT ... ON CONFLICT for upsert operations",
                "Implement proper concurrency control",
                "Add unique constraint handling in application logic"
            ]
        }
    }
}
```

#### **Data Corruption and Recovery Scenarios**
```python
# Enhanced data integrity monitoring
DATA_INTEGRITY_ERRORS = {
    "json_data_corruption": {
        "affected_columns": [
            "proxy_configs.parsed_config",      # JSON column
            "proxy_configs.tags",               # JSON column  
            "devices.metadata",                 # JSONB column
            "system_metrics.metrics_data"       # JSON metrics
        ],
        "detection": [
            "JSON parse errors during queries",
            "Malformed JSON structure validation",
            "Unexpected null values in required JSON fields"
        ],
        "recovery_procedures": [
            "Restore from backup if available",
            "Reconstruct JSON from raw data sources",
            "Use JSON repair utilities for minor corruption"
        ]
    },
    "time_series_data_gaps": {
        "detection": [
            "Missing data points in expected time ranges",
            "Irregular time intervals in hypertables",
            "Chunk boundary inconsistencies"
        ],
        "gap_analysis": [
            "Identify missing time ranges using window functions",
            "Cross-reference with polling service logs",
            "Check for device connectivity issues during gaps"
        ],
        "backfill_strategies": [
            "Re-collect recent data if devices are accessible",
            "Interpolate missing values for continuous metrics",
            "Mark data gaps explicitly for reporting accuracy"
        ]
    }
}
```

### **Performance Degradation Scenarios**
```python
# Based on database optimization and monitoring patterns
PERFORMANCE_DEGRADATION_SCENARIOS = {
    "query_performance_issues": {
        "detection": [
            "Query execution time > statement_timeout (60s)", # database.py:75
            "High CPU usage from PostgreSQL process",
            "Increasing pg_stat_activity wait events"
        ],
        "analysis_queries": [
            "SELECT * FROM pg_stat_statements ORDER BY total_time DESC",
            "SELECT * FROM pg_stat_user_tables WHERE n_tup_upd > 1000000",
            "SELECT * FROM timescaledb_information.compressed_hypertable_stats"
        ],
        "optimization_strategies": [
            "Add indexes on frequently queried columns",
            "Optimize TimescaleDB chunk configuration",
            "Update table statistics with ANALYZE",
            "Enable query plan caching"
        ]
    },
    "disk_space_exhaustion": {
        "monitoring": [
            "Database size tracking via pg_database_size()",    # database.py:388
            "Individual table sizes via hypertable_detailed_size", # database.py:401
            "Chunk compression effectiveness monitoring"
        ],
        "space_recovery": [
            "Run VACUUM FULL on heavily updated tables",
            "Adjust retention policies for older data",
            "Increase compression aggressiveness",
            "Move large tables to separate tablespaces"
        ]
    },
    "memory_pressure": {
        "detection": [
            "High swap usage on database server",
            "PostgreSQL shared_buffers exhaustion",
            "Connection memory limit exceeded"
        ],
        "tuning_recommendations": [
            "Adjust shared_buffers based on available RAM",
            "Optimize work_mem for complex queries",
            "Tune maintenance_work_mem for VACUUM operations",
            "Consider connection pooling with PgBouncer"
        ]
    }
}
```

---

## 🔄 **Service Recovery**

### **Current Service Architecture Analysis**
Based on analysis of service components and error handling:

- **Dual-server architecture**: FastAPI (port 9101) + MCP Server (port 9102)
- **Connection pooling**: SSH connection management with cleanup tasks
- **Health monitoring**: Comprehensive database and service health checks

### **Graceful Degradation Strategies**

#### **Database Connection Failures**
```python
# Based on current database health monitoring patterns
DATABASE_RECOVERY_STRATEGIES = {
    "connection_pool_recovery": {
        "detection": "Connection pool health check failures",
        "graceful_degradation": [
            "Switch to read-only mode if primary connection fails",
            "Use cached data for non-critical operations",
            "Queue write operations for later processing"
        ],
        "recovery_procedures": [
            "Recreate connection pool with fresh connections",
            "Test connectivity with minimal timeout",
            "Gradually increase connection pool size",
            "Resume normal operations after validation"
        ],
        "service_continuity": [
            "Serve cached metrics during database outage",
            "Use local SQLite for temporary data storage", 
            "Maintain essential API functionality"
        ]
    },
    "timescaledb_extension_failure": {
        "detection": "TimescaleDB functions not available",
        "fallback_strategy": [
            "Use standard PostgreSQL tables temporarily",
            "Disable time-series specific features",
            "Continue basic CRUD operations"
        ],
        "recovery_process": [
            "Reinstall TimescaleDB extension",
            "Recreate hypertables from backed up data",
            "Migrate temporary data back to hypertables"
        ]
    }
}
```

#### **SSH Infrastructure Failures**
```python
# Based on SSH client connection pool and error handling
SSH_RECOVERY_STRATEGIES = {
    "ssh_service_outage": {
        "detection": [
            "All SSH connections to device failing",
            "SSH service not responding on port 22",
            "Authentication consistently failing"
        ],
        "degradation_levels": {
            "level_1": "Use cached data, disable real-time updates",
            "level_2": "Mark device as temporarily unavailable",
            "level_3": "Remove device from active monitoring pool"
        },
        "recovery_validation": [
            "Test SSH connectivity with basic commands",
            "Validate authentication methods still work",
            "Confirm device services are operational"
        ]
    },
    "network_partition_recovery": {
        "detection": [
            "Multiple devices become unreachable simultaneously",
            "Tailscale connectivity issues",
            "Network-wide SSH failures"
        ],
        "isolation_strategy": [
            "Identify accessible vs inaccessible device groups",
            "Continue monitoring accessible devices",
            "Cache last known state for partitioned devices"
        ],
        "partition_healing": [
            "Automatically detect network recovery",
            "Reconcile data from partitioned devices",
            "Merge configuration changes made during partition"
        ]
    }
}
```

### **Service Restart and State Recovery**

#### **Stateful Service Recovery**
```python
# Based on current service architecture and connection management
SERVICE_STATE_RECOVERY = {
    "mcp_server_restart": {
        "state_preservation": [
            "Save active connection information",
            "Cache recent command execution results",
            "Store pending operation queue"
        ],
        "recovery_sequence": [
            "Initialize MCP server on port 9102",
            "Restore connection pools to known devices",
            "Resume pending operations from queue",
            "Validate service health before accepting requests"
        ],
        "startup_validation": [
            "Test all MCP tool endpoints",
            "Verify database connectivity", 
            "Confirm SSH connection pool status"
        ]
    },
    "fastapi_server_restart": {
        "graceful_shutdown": [
            "Complete in-flight requests",
            "Close database connections properly",
            "Save application state to disk"
        ],
        "startup_recovery": [
            "Initialize database connection pool",
            "Load device registry and configurations",
            "Resume background polling services",
            "Restore API rate limiting state"
        ]
    }
}
```

#### **Configuration State Synchronization**
```python
# Based on configuration monitoring and change tracking
CONFIG_STATE_RECOVERY = {
    "configuration_drift_detection": {
        "detection_methods": [
            "Hash comparison between cached and actual configs",
            "Timestamp analysis for missed change events",
            "File modification time validation"
        ],
        "drift_resolution": [
            "Re-scan all monitored configuration files",
            "Update change tracking records",
            "Trigger validation for modified configurations",
            "Sync changes to dependent services"
        ]
    },
    "file_watcher_recovery": {
        "failure_scenarios": [
            "inotify watch limit exceeded",
            "SSH connection dropped during watching",
            "File system becomes read-only"
        ],
        "recovery_procedures": [
            "Restart file watching with optimized watch count",
            "Fall back to periodic polling temporarily",
            "Queue missed changes for later processing",
            "Validate configuration state after recovery"
        ]
    }
}
```

### **Automated Recovery Procedures**
```python
# Enhanced recovery automation based on current error handling
class AutomatedRecoveryManager:
    def __init__(self):
        self.recovery_history = {}
        self.failure_thresholds = {}
        self.recovery_in_progress = set()
    
    async def execute_recovery_procedure(self, service: str, 
                                       failure_type: str) -> Dict[str, Any]:
        """Execute automated recovery based on failure type"""
        recovery_key = f"{service}:{failure_type}"
        
        if recovery_key in self.recovery_in_progress:
            return {"status": "recovery_already_in_progress"}
        
        self.recovery_in_progress.add(recovery_key)
        
        try:
            recovery_result = {
                "service": service,
                "failure_type": failure_type,
                "recovery_steps": [],
                "success": False,
                "recovery_time": 0
            }
            
            start_time = time.time()
            
            # Execute service-specific recovery
            if service == "database":
                recovery_result.update(await self._recover_database_service(failure_type))
            elif service == "ssh_pool":
                recovery_result.update(await self._recover_ssh_pool(failure_type))
            elif service == "file_watcher":
                recovery_result.update(await self._recover_file_watcher(failure_type))
            elif service == "mcp_server":
                recovery_result.update(await self._recover_mcp_server(failure_type))
            
            recovery_result["recovery_time"] = time.time() - start_time
            
            # Update recovery history
            self._update_recovery_history(recovery_key, recovery_result)
            
            return recovery_result
            
        finally:
            self.recovery_in_progress.discard(recovery_key)
    
    async def _recover_database_service(self, failure_type: str) -> Dict[str, Any]:
        """Database-specific recovery procedures"""
        steps = []
        
        if failure_type == "connection_pool_exhausted":
            steps.extend([
                "close_idle_connections",
                "increase_pool_size_temporarily", 
                "restart_connection_pool",
                "validate_connectivity"
            ])
        elif failure_type == "timescaledb_extension_failure":
            steps.extend([
                "check_extension_status",
                "recreate_extension_if_needed",
                "validate_hypertables",
                "resume_compression_policies"
            ])
        
        return {"recovery_steps": steps, "success": True}
    
    async def _recover_ssh_pool(self, failure_type: str) -> Dict[str, Any]:
        """SSH connection pool recovery procedures"""
        steps = []
        
        if failure_type == "all_connections_failed":
            steps.extend([
                "clear_failed_connections",
                "test_device_connectivity",
                "recreate_connection_pool",
                "validate_ssh_credentials"
            ])
        elif failure_type == "connection_limit_exceeded":
            steps.extend([
                "cleanup_idle_connections",
                "optimize_connection_reuse",
                "adjust_pool_sizing",
                "implement_connection_throttling"
            ])
        
        return {"recovery_steps": steps, "success": True}
```

### **Health Check and Monitoring Integration**
```python
# Enhanced health monitoring based on current health check patterns
class ServiceHealthMonitor:
    def __init__(self):
        self.health_checkers = {}
        self.recovery_manager = AutomatedRecoveryManager()
    
    async def continuous_health_monitoring(self):
        """Continuous health monitoring with automatic recovery"""
        while True:
            try:
                # Database health check (based on database.py:276)
                db_health = await self._check_database_health()
                if not db_health["healthy"]:
                    await self.recovery_manager.execute_recovery_procedure(
                        "database", db_health["failure_type"]
                    )
                
                # SSH pool health check
                ssh_health = await self._check_ssh_pool_health()
                if not ssh_health["healthy"]:
                    await self.recovery_manager.execute_recovery_procedure(
                        "ssh_pool", ssh_health["failure_type"]
                    )
                
                # Configuration monitoring health
                config_health = await self._check_config_monitoring_health()
                if not config_health["healthy"]:
                    await self.recovery_manager.execute_recovery_procedure(
                        "file_watcher", config_health["failure_type"]
                    )
                
                # Wait before next health check cycle
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitoring cycle failed: {e}")
                await asyncio.sleep(60)  # Extended wait on monitoring failure
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Enhanced database health check"""
        try:
            # Use existing health check from database.py:276
            health_data = await check_database_health()
            
            return {
                "healthy": health_data["status"] == "healthy",
                "failure_type": "connection_pool_exhausted" if 
                              health_data.get("connection_pool", {}).get("checked_out", 0) > 10 
                              else None,
                "metrics": health_data
            }
        except Exception as e:
            return {
                "healthy": False,
                "failure_type": "database_unreachable",
                "error": str(e)
            }
```

---

## 🤖 **MCP Tool Transformation Layer**

### **Current MCP Implementation Analysis**
Based on analysis of existing MCP infrastructure:

- **FastMCP 2.11.0**: Updated dependency supporting tool transformation patterns
- **27 MCP resources**: Across 6 categories with HTTP client pattern to FastAPI endpoints
- **Tool complexity**: Direct parameter passing with minimal validation

### **Tool Transformation Architecture**

#### **Transformation Layer Design**
```python
# Enhanced MCP tool transformation based on FastMCP 2.11.0 patterns
from fastmcp import Tool
from fastmcp.patterns import ArgTransform
from typing import Dict, Any, Optional

class InfrastructorToolTransformer:
    """Transform complex infrastructure tools into intuitive interfaces"""
    
    def __init__(self):
        self.device_registry = {}
        self.capability_cache = {}
        self.auth_context = {}
    
    async def create_transformed_tools(self) -> List[Tool]:
        """Create suite of transformed tools with enhanced UX"""
        transformed_tools = []
        
        # Transform system metrics tools
        transformed_tools.extend(await self._create_metrics_tools())
        
        # Transform container management tools  
        transformed_tools.extend(await self._create_container_tools())
        
        # Transform configuration tools
        transformed_tools.extend(await self._create_config_tools())
        
        # Transform ZFS management tools
        transformed_tools.extend(await self._create_zfs_tools())
        
        return transformed_tools
```

#### **Device-Aware Tool Transformation**
```python
# Simplified device-focused interfaces
DEVICE_AWARE_TRANSFORMATIONS = {
    "get_system_metrics": {
        "original_params": [
            "device_id", "ssh_timeout", "cache_ttl", 
            "auth_token", "live", "metrics_types"
        ],
        "transformed_params": ["device"],
        "transformation": {
            "device": ArgTransform(
                name="device",
                description="Device name or hostname (e.g., 'proxmox', 'nas-01')",
                required=True
            )
        },
        "pre_processing": [
            "validate_device_exists",
            "determine_device_capabilities", 
            "set_optimal_timeouts",
            "inject_auth_context"
        ]
    },
    "manage_containers": {
        "original_params": [
            "device_id", "container_action", "container_names",
            "ssh_config", "timeout", "force", "auth_token"
        ],
        "transformed_params": ["device", "action", "containers"],
        "context_aware": True,
        "validation": [
            "check_docker_availability",
            "validate_container_names",
            "confirm_destructive_actions"
        ]
    }
}
```

### **Enhanced Tool Interfaces**

#### **System Metrics Tools**
```python
# Transformed system metrics collection
async def create_metrics_tools() -> List[Tool]:
    """Create simplified, device-aware metrics tools"""
    
    # Universal metrics tool
    @Tool.from_tool(
        original_get_system_metrics_tool,
        name="get_metrics",
        description="Get comprehensive system metrics from any device",
        transform_args={
            "device_id": ArgTransform(
                name="device",
                description="Device name (e.g., 'proxmox', 'nas')",
                required=True
            ),
            "metrics_types": ArgTransform(hide=True),  # Auto-determine based on device
            "ssh_timeout": ArgTransform(hide=True),    # Auto-optimize
            "auth_token": ArgTransform(hide=True)      # Auto-inject
        }
    )
    async def get_metrics(device: str, **kwargs) -> Dict[str, Any]:
        """Get system metrics with automatic optimization"""
        # Pre-validation and enhancement
        device_info = await validate_and_enhance_device(device)
        
        # Auto-determine optimal parameters
        enhanced_params = {
            "device_id": device_info["id"],
            "ssh_timeout": device_info["optimal_timeout"],
            "cache_ttl": device_info["cache_settings"]["metrics_ttl"],
            "auth_token": await get_current_auth_token(),
            "metrics_types": device_info["supported_metrics"]
        }
        
        # Call enhanced unified service
        result = await forward(**enhanced_params, **kwargs)
        
        # Post-process for better UX
        return enhance_metrics_response(result, device_info)
    
    # Device-specific optimized tools
    @Tool.from_tool(
        get_metrics,
        name="get_proxmox_metrics", 
        description="Get Proxmox server metrics with VM/CT details"
    )
    async def get_proxmox_metrics(device: str = "proxmox") -> Dict[str, Any]:
        """Proxmox-optimized metrics collection"""
        return await get_metrics(device, include_vm_details=True)
    
    @Tool.from_tool(
        get_metrics,
        name="get_nas_metrics",
        description="Get NAS metrics with ZFS pool details" 
    )
    async def get_nas_metrics(device: str = "nas") -> Dict[str, Any]:
        """NAS-optimized metrics with ZFS focus"""
        return await get_metrics(device, include_zfs_details=True)
    
    return [get_metrics, get_proxmox_metrics, get_nas_metrics]
```

#### **Container Management Tools**
```python
# Transformed container management with safety features
async def create_container_tools() -> List[Tool]:
    """Create enhanced container management tools"""
    
    @Tool.from_tool(
        original_container_management_tool,
        name="manage_containers",
        description="Safely manage Docker containers with validation",
        transform_args={
            "device_id": ArgTransform(
                name="device", 
                description="Device hosting containers",
                required=True
            ),
            "container_action": ArgTransform(
                name="action",
                description="Action: start, stop, restart, status",
                required=True
            ),
            "container_names": ArgTransform(
                name="containers",
                description="Container names (comma-separated or 'all')"
            ),
            "force": ArgTransform(hide=True),      # Auto-determine safety
            "ssh_config": ArgTransform(hide=True), # Auto-inject
            "timeout": ArgTransform(hide=True)     # Auto-optimize
        }
    )
    async def manage_containers(device: str, action: str, 
                              containers: str = "all") -> Dict[str, Any]:
        """Enhanced container management with safety checks"""
        
        # Pre-validation
        device_info = await validate_and_enhance_device(device)
        
        # Safety validation for destructive actions
        if action in ["stop", "restart", "remove"] and containers == "all":
            critical_containers = await get_critical_containers(device_info["id"])
            if critical_containers:
                return {
                    "error": "Critical containers detected",
                    "critical_containers": critical_containers,
                    "suggestion": "Specify containers explicitly or use 'force=true'"
                }
        
        # Enhanced parameters
        enhanced_params = {
            "device_id": device_info["id"],
            "container_action": action,
            "container_names": await resolve_container_names(containers, device_info),
            "timeout": device_info["optimal_timeout"],
            "force": False,  # Safety first
            "auth_token": await get_current_auth_token()
        }
        
        result = await forward(**enhanced_params)
        return enhance_container_response(result, device_info)
    
    # Specialized container tools
    @Tool.from_tool(
        manage_containers,
        name="restart_service",
        description="Safely restart a specific service container"
    )
    async def restart_service(device: str, service: str) -> Dict[str, Any]:
        """Restart specific service with dependency checking"""
        
        # Check service dependencies
        dependencies = await get_service_dependencies(device, service)
        if dependencies:
            # Restart in proper order
            for dep_service in dependencies:
                await manage_containers(device, "restart", dep_service)
        
        return await manage_containers(device, "restart", service)
    
    return [manage_containers, restart_service]
```

### **Context-Aware Validation and Enhancement**

#### **Device Capability Detection**
```python
# Smart device capability detection and caching
class DeviceCapabilityManager:
    def __init__(self):
        self.capability_cache = {}
        self.cache_ttl = 3600  # 1 hour cache
    
    async def validate_and_enhance_device(self, device_name: str) -> Dict[str, Any]:
        """Validate device and return enhanced context"""
        
        # Check cache first
        cache_key = f"device_capabilities:{device_name}"
        cached = await self._get_cached_capabilities(cache_key)
        if cached:
            return cached
        
        # Resolve device from registry
        device_info = await self._resolve_device_name(device_name)
        if not device_info:
            raise ValueError(f"Device '{device_name}' not found in registry")
        
        # Detect capabilities
        capabilities = await self._detect_device_capabilities(device_info)
        
        # Build enhanced context
        enhanced_context = {
            "id": device_info["id"],
            "hostname": device_info["hostname"], 
            "type": device_info["device_type"],
            "capabilities": capabilities,
            "optimal_timeout": self._calculate_optimal_timeout(capabilities),
            "cache_settings": self._get_cache_settings(capabilities),
            "supported_metrics": self._get_supported_metrics(capabilities),
            "ssh_config": self._optimize_ssh_config(device_info, capabilities)
        }
        
        # Cache results
        await self._cache_capabilities(cache_key, enhanced_context)
        
        return enhanced_context
    
    async def _detect_device_capabilities(self, device_info: Dict[str, Any]) -> Dict[str, bool]:
        """Detect what services/features are available on device"""
        capabilities = {
            "docker": False,
            "zfs": False,
            "systemd": False,
            "proxmox": False,
            "smart_tools": False,
            "nginx": False
        }
        
        # Quick capability detection commands
        detection_commands = {
            "docker": "docker version --format '{{.Server.Version}}' 2>/dev/null",
            "zfs": "zfs version 2>/dev/null | head -1",
            "systemd": "systemctl --version 2>/dev/null | head -1", 
            "proxmox": "pveversion 2>/dev/null",
            "smart_tools": "smartctl --version 2>/dev/null | head -1",
            "nginx": "nginx -v 2>&1 | head -1"
        }
        
        # Execute detection commands in parallel
        results = await self._execute_parallel_commands(
            device_info, detection_commands
        )
        
        # Analyze results
        for capability, result in results.items():
            capabilities[capability] = result.success and len(result.stdout.strip()) > 0
        
        return capabilities
```

#### **Intelligent Parameter Enhancement**
```python
# Automatic parameter optimization based on device context
class ParameterEnhancer:
    def __init__(self):
        self.optimization_rules = {}
        self.device_profiles = {}
    
    def calculate_optimal_timeout(self, capabilities: Dict[str, bool]) -> int:
        """Calculate optimal SSH timeout based on device capabilities"""
        base_timeout = 15
        
        # Adjust based on detected services and OS types
        if capabilities.get("unraid"):
            return base_timeout + 20  # Unraid can be slower due to parity operations
        elif capabilities.get("zfs"):
            return base_timeout + 10  # ZFS commands can take time
        elif capabilities.get("docker"):
            return base_timeout + 5   # Docker commands moderate overhead
        elif capabilities.get("wsl2"):
            return base_timeout - 5   # WSL2 is typically faster for SSH operations
        elif capabilities.get("windows"):
            return base_timeout + 10  # Windows SSH can have higher overhead
        
        return base_timeout
    
    def get_cache_settings(self, capabilities: Dict[str, bool]) -> Dict[str, int]:
        """Determine optimal cache settings for device type"""
        cache_settings = {
            "metrics_ttl": 300,        # 5 minutes default
            "container_ttl": 30,       # 30 seconds for container data
            "config_ttl": 3600,        # 1 hour for configurations
            "health_ttl": 60           # 1 minute for health checks
        }
        
        # Adjust based on capabilities and OS types
        if capabilities.get("unraid"):
            cache_settings["metrics_ttl"] = 120   # More frequent due to array operations
            cache_settings["container_ttl"] = 45  # Unraid containers more stable
        elif capabilities.get("ubuntu"):
            cache_settings["metrics_ttl"] = 180   # Standard server monitoring
            cache_settings["container_ttl"] = 20  # Active development environment
        elif capabilities.get("wsl2"):
            cache_settings["metrics_ttl"] = 60    # Development environment, faster changes
            cache_settings["container_ttl"] = 10  # Very dynamic WSL2 containers
        elif capabilities.get("windows"):
            cache_settings["metrics_ttl"] = 240   # Windows metrics less frequent
            cache_settings["container_ttl"] = 60  # Docker Desktop containers more stable
        elif capabilities.get("docker"):
            cache_settings["container_ttl"] = 15  # Containers change frequently
        
        return cache_settings
    
    def get_supported_metrics(self, capabilities: Dict[str, bool]) -> List[str]:
        """Determine which metrics are supported"""
        base_metrics = ["cpu", "memory", "disk", "network"]
        
        if capabilities.get("docker"):
            base_metrics.extend(["containers", "docker_stats"])
        if capabilities.get("zfs"):
            base_metrics.extend(["zfs_pools", "zfs_datasets"])
        if capabilities.get("proxmox"):
            base_metrics.extend(["vms", "containers", "cluster_info"])
        if capabilities.get("smart_tools"):
            base_metrics.append("drive_health")
        
        return base_metrics
```

### **Response Enhancement and User Experience**

#### **Intelligent Response Formatting**
```python
# Enhanced response formatting for better UX
class ResponseEnhancer:
    def __init__(self):
        self.formatters = {}
    
    async def enhance_metrics_response(self, raw_response: Dict[str, Any], 
                                     device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance metrics response with context and insights"""
        enhanced_response = {
            "device": {
                "name": device_info.get("hostname"),
                "type": device_info.get("type"),
                "capabilities": device_info.get("capabilities", {})
            },
            "metrics": raw_response.get("metrics", {}),
            "collection_info": {
                "timestamp": raw_response.get("timestamp"),
                "execution_time": raw_response.get("execution_time"),
                "cache_hit": raw_response.get("from_cache", False)
            },
            "insights": [],
            "alerts": []
        }
        
        # Add intelligent insights
        insights = await self._generate_insights(enhanced_response["metrics"], device_info)
        enhanced_response["insights"] = insights
        
        # Check for alerts
        alerts = await self._check_for_alerts(enhanced_response["metrics"], device_info)
        enhanced_response["alerts"] = alerts
        
        return enhanced_response
    
    async def _generate_insights(self, metrics: Dict[str, Any], 
                               device_info: Dict[str, Any]) -> List[str]:
        """Generate intelligent insights from metrics"""
        insights = []
        
        # CPU insights
        if "cpu" in metrics:
            cpu_usage = metrics["cpu"].get("usage_percent", 0)
            if cpu_usage > 80:
                insights.append(f"High CPU usage detected: {cpu_usage}%")
            elif cpu_usage < 10:
                insights.append("System is running efficiently with low CPU usage")
        
        # Memory insights
        if "memory" in metrics:
            memory_usage = metrics["memory"].get("usage_percent", 0)
            if memory_usage > 90:
                insights.append(f"Critical memory usage: {memory_usage}%")
        
        # Device-specific insights
        if device_info.get("capabilities", {}).get("proxmox"):
            insights.extend(await self._generate_proxmox_insights(metrics))
        elif device_info.get("capabilities", {}).get("zfs"):
            insights.extend(await self._generate_zfs_insights(metrics))
        
        return insights
```

### **🛡️ Destructive Action Protection System (TENTPOLE FEATURE)**

The Destructive Action Protection System is a **tentpole feature** of our infrastructure management platform, providing multi-layered safety mechanisms to prevent accidental damage while maintaining operational flexibility for legitimate bulk operations.

#### **Protection Architecture Overview**

This system transforms potentially dangerous operations into safe, confirmation-based workflows using FastMCP 2.11.0 tool transformation patterns combined with sophisticated impact analysis and user confirmation flows.

```python
from fastmcp import Tool, ArgTransform
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import re
import time

class DestructiveActionType(Enum):
    """Categories of destructive actions"""
    CONTAINER_BULK_STOP = "container_bulk_stop"
    CONTAINER_BULK_REMOVE = "container_bulk_remove"
    SERVICE_BULK_DISABLE = "service_bulk_disable"
    FILESYSTEM_BULK_DELETE = "filesystem_bulk_delete"
    ZFS_POOL_DESTROY = "zfs_pool_destroy"
    SYSTEM_REBOOT = "system_reboot"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIGURATION_RESET = "configuration_reset"

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"           # 1-2 items affected, non-critical
    MEDIUM = "medium"     # 3-10 items affected, some critical
    HIGH = "high"         # 11+ items affected, business critical
    CRITICAL = "critical" # System-wide impact, production critical

@dataclass
class DestructiveActionAnalysis:
    """Analysis result for a potentially destructive action"""
    action_type: DestructiveActionType
    risk_level: RiskLevel
    affected_count: int
    affected_items: List[str]
    dependencies: List[str]
    estimated_downtime: Optional[str]
    rollback_possible: bool
    requires_confirmation: bool
    confirmation_phrase: str
    safety_warnings: List[str]
    impact_summary: str
```

#### **Command Pattern Detection Engine**

```python
class DestructiveCommandDetector:
    """Sophisticated pattern detection for destructive commands"""
    
    # Enhanced patterns based on actual infrastructure commands
    DESTRUCTIVE_PATTERNS = {
        DestructiveActionType.CONTAINER_BULK_STOP: [
            r"docker\s+stop\s+\$\(docker\s+ps\s+-q\)",  # Stop all containers
            r"docker\s+stop\s+\*",                       # Stop with wildcard
            r"docker\s+stop\s+.{0,10}\s*$",             # Stop without specific container
            r"docker-compose\s+down\s+--all",           # Compose down all
        ],
        DestructiveActionType.CONTAINER_BULK_REMOVE: [
            r"docker\s+rm\s+-f\s+\$\(docker\s+ps\s+-aq\)", # Remove all containers
            r"docker\s+system\s+prune\s+-af",             # System prune all
            r"docker\s+container\s+prune\s+-f",           # Container prune
        ],
        DestructiveActionType.SERVICE_BULK_DISABLE: [
            r"systemctl\s+stop\s+\*",                    # Stop all services
            r"systemctl\s+disable\s+--all",             # Disable all services
            r"service\s+.*\s+stop\s+--all",             # Service stop all
        ],
        DestructiveActionType.FILESYSTEM_BULK_DELETE: [
            r"rm\s+-rf\s+/(?!tmp|var/tmp)",            # Recursive delete from root
            r"find\s+/.*-delete",                       # Find and delete
            r"rm\s+-rf\s+\$HOME/\*",                   # Delete home directory contents
        ],
        DestructiveActionType.ZFS_POOL_DESTROY: [
            r"zpool\s+destroy\s+",                      # ZFS pool destruction
            r"zfs\s+destroy\s+-r\s+",                  # Recursive ZFS destroy
        ],
        DestructiveActionType.SYSTEM_REBOOT: [
            r"reboot\s*$",                              # System reboot
            r"shutdown\s+-r\s+",                       # Scheduled reboot
            r"systemctl\s+reboot",                     # Systemctl reboot
        ],
        DestructiveActionType.SYSTEM_SHUTDOWN: [
            r"shutdown\s+-h\s+",                       # System shutdown
            r"halt\s*$",                               # System halt
            r"poweroff\s*$",                           # System poweroff
        ]
    }
    
    @classmethod
    def analyze_command(cls, command: str, device_info: Dict[str, Any]) -> Optional[DestructiveActionAnalysis]:
        """Analyze command for destructive patterns and assess risk"""
        
        for action_type, patterns in cls.DESTRUCTIVE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return cls._perform_risk_analysis(
                        command, action_type, device_info
                    )
        
        return None
    
    @classmethod
    def _perform_risk_analysis(cls, command: str, action_type: DestructiveActionType, 
                              device_info: Dict[str, Any]) -> DestructiveActionAnalysis:
        """Perform detailed risk analysis for detected destructive action"""
        
        # Get device-specific context
        device_type = device_info.get("type", "unknown")
        environment = device_info.get("environment", "unknown")
        
        # Analyze impact based on action type and device
        if action_type == DestructiveActionType.CONTAINER_BULK_STOP:
            return cls._analyze_container_bulk_action(command, device_info, "stop")
        elif action_type == DestructiveActionType.CONTAINER_BULK_REMOVE:
            return cls._analyze_container_bulk_action(command, device_info, "remove")
        elif action_type == DestructiveActionType.SYSTEM_REBOOT:
            return cls._analyze_system_action(command, device_info, "reboot")
        elif action_type == DestructiveActionType.ZFS_POOL_DESTROY:
            return cls._analyze_zfs_action(command, device_info)
            
        # Default analysis for unhandled types
        return DestructiveActionAnalysis(
            action_type=action_type,
            risk_level=RiskLevel.HIGH,
            affected_count=0,
            affected_items=[],
            dependencies=[],
            estimated_downtime="Unknown",
            rollback_possible=False,
            requires_confirmation=True,
            confirmation_phrase="yes, proceed with destructive operation",
            safety_warnings=["This operation may cause service disruption"],
            impact_summary="Potentially destructive operation detected"
        )
    
    @classmethod
    def _analyze_container_bulk_action(cls, command: str, device_info: Dict[str, Any], 
                                     action: str) -> DestructiveActionAnalysis:
        """Analyze bulk container operations"""
        
        # Estimate affected containers based on device type
        device_type = device_info.get("type", "unknown")
        estimated_containers = {
            "unraid": 8,     # Typical Unraid setup
            "ubuntu": 15,    # Server with multiple services
            "wsl2": 5,       # Development environment
            "windows": 3     # Docker Desktop
        }.get(device_type, 10)
        
        # Determine risk level
        if estimated_containers <= 3:
            risk_level = RiskLevel.LOW
        elif estimated_containers <= 10:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.HIGH
            
        # Check for critical services
        critical_services = ["database", "web", "proxy", "monitoring"]
        safety_warnings = []
        
        if device_info.get("environment") == "production":
            risk_level = RiskLevel.CRITICAL
            safety_warnings.append("⚠️  PRODUCTION ENVIRONMENT - This will affect live services")
        
        if any(service in device_info.get("services", []) for service in critical_services):
            safety_warnings.append("⚠️  Critical services detected (database, web, monitoring)")
            
        return DestructiveActionAnalysis(
            action_type=DestructiveActionType.CONTAINER_BULK_STOP if action == "stop" 
                       else DestructiveActionType.CONTAINER_BULK_REMOVE,
            risk_level=risk_level,
            affected_count=estimated_containers,
            affected_items=[f"container_{i}" for i in range(estimated_containers)],
            dependencies=device_info.get("service_dependencies", []),
            estimated_downtime="5-15 minutes" if action == "stop" else "30+ minutes",
            rollback_possible=action == "stop",
            requires_confirmation=True,
            confirmation_phrase=f"yes, {action} all {estimated_containers} containers",
            safety_warnings=safety_warnings,
            impact_summary=f"This will {action} ALL {estimated_containers} containers on {device_type}"
        )
```

#### **Multi-Step Confirmation System**

```python
class DestructiveActionManager:
    """Manages the confirmation and execution flow for destructive actions"""
    
    def __init__(self):
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self.confirmation_timeout = 300  # 5 minutes
        
    async def require_confirmation(self, analysis: DestructiveActionAnalysis, 
                                 user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate confirmation process for destructive action"""
        
        operation_id = f"destructive_{int(time.time())}_{hash(analysis.impact_summary) % 10000}"
        
        # Store confirmation details
        self.pending_confirmations[operation_id] = {
            "analysis": analysis,
            "user_context": user_context,
            "created_at": time.time(),
            "attempts": 0,
            "max_attempts": 3
        }
        
        # Generate user-friendly confirmation prompt
        confirmation_response = {
            "status": "DESTRUCTIVE_ACTION_BLOCKED",
            "operation_id": operation_id,
            "risk_assessment": {
                "risk_level": analysis.risk_level.value.upper(),
                "affected_count": analysis.affected_count,
                "estimated_downtime": analysis.estimated_downtime,
                "rollback_possible": analysis.rollback_possible
            },
            "impact_details": {
                "summary": analysis.impact_summary,
                "warnings": analysis.safety_warnings,
                "affected_items": analysis.affected_items[:10],  # Show first 10
                "dependencies": analysis.dependencies
            },
            "confirmation_required": {
                "phrase": analysis.confirmation_phrase,
                "command": f"confirm-operation {operation_id}",
                "timeout_seconds": self.confirmation_timeout,
                "alternative_actions": self._suggest_safer_alternatives(analysis)
            },
            "safety_checklist": self._generate_safety_checklist(analysis)
        }
        
        return confirmation_response
    
    def _suggest_safer_alternatives(self, analysis: DestructiveActionAnalysis) -> List[Dict[str, str]]:
        """Suggest safer alternatives to the destructive action"""
        alternatives = []
        
        if analysis.action_type == DestructiveActionType.CONTAINER_BULK_STOP:
            alternatives.extend([
                {
                    "action": "Stop specific containers",
                    "command": "docker stop <container_name1> <container_name2>",
                    "benefit": "Precise control, no impact on unrelated services"
                },
                {
                    "action": "Graceful service shutdown",
                    "command": "docker-compose down",
                    "benefit": "Maintains service dependencies and order"
                }
            ])
        elif analysis.action_type == DestructiveActionType.SYSTEM_REBOOT:
            alternatives.extend([
                {
                    "action": "Restart specific services",
                    "command": "systemctl restart <service_name>",
                    "benefit": "No system downtime, targeted fix"
                },
                {
                    "action": "Scheduled maintenance window",
                    "command": "shutdown -r +60",
                    "benefit": "Allows graceful service shutdown"
                }
            ])
            
        return alternatives
    
    def _generate_safety_checklist(self, analysis: DestructiveActionAnalysis) -> List[Dict[str, str]]:
        """Generate pre-execution safety checklist"""
        checklist = [
            {
                "item": "Verify backup status",
                "description": "Ensure recent backups exist for critical data",
                "critical": True
            },
            {
                "item": "Check service dependencies", 
                "description": "Understand which services depend on affected components",
                "critical": analysis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            },
            {
                "item": "Prepare rollback plan",
                "description": "Have a clear plan to restore services if needed",
                "critical": not analysis.rollback_possible
            }
        ]
        
        if analysis.action_type in [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.CONTAINER_BULK_REMOVE
        ]:
            checklist.append({
                "item": "Export container configurations",
                "description": "Back up docker-compose files and environment variables",
                "critical": analysis.action_type == DestructiveActionType.CONTAINER_BULK_REMOVE
            })
            
        return checklist
    
    async def process_confirmation(self, operation_id: str, 
                                 user_input: str) -> Dict[str, Any]:
        """Process user confirmation for pending destructive action"""
        
        if operation_id not in self.pending_confirmations:
            return {
                "status": "error",
                "message": "No pending operation found with that ID",
                "suggestion": "The operation may have expired or been cancelled"
            }
        
        pending = self.pending_confirmations[operation_id]
        analysis = pending["analysis"]
        
        # Check timeout
        if time.time() - pending["created_at"] > self.confirmation_timeout:
            del self.pending_confirmations[operation_id]
            return {
                "status": "expired",
                "message": "Confirmation window expired",
                "suggestion": "Please retry the operation if still needed"
            }
        
        # Increment attempt counter
        pending["attempts"] += 1
        
        # Check max attempts
        if pending["attempts"] > pending["max_attempts"]:
            del self.pending_confirmations[operation_id]
            return {
                "status": "max_attempts_exceeded",
                "message": "Maximum confirmation attempts exceeded",
                "suggestion": "Operation cancelled for security"
            }
        
        # Validate confirmation phrase
        expected_phrase = analysis.confirmation_phrase.lower().strip()
        user_phrase = user_input.lower().strip()
        
        if user_phrase != expected_phrase:
            remaining_attempts = pending["max_attempts"] - pending["attempts"]
            return {
                "status": "invalid_confirmation",
                "message": "Confirmation phrase does not match",
                "expected": analysis.confirmation_phrase,
                "remaining_attempts": remaining_attempts,
                "hint": "Type the exact phrase shown above"
            }
        
        # Confirmation successful - prepare for execution
        del self.pending_confirmations[operation_id]
        
        return {
            "status": "confirmed",
            "message": "Destructive action confirmed - executing with full audit trail",
            "operation_id": operation_id,
            "analysis": analysis,
            "execution_context": pending["user_context"],
            "safety_reminder": "All actions will be logged and monitored"
        }
```

#### **Device-Specific Protection Rules**

```python
# Enhanced device-specific safety rules based on actual environment analysis
DEVICE_PROTECTION_RULES = {
    "unraid": {
        "container_protection": {
            "max_bulk_operations": 5,
            "protected_containers": [
                "unraid-*", "parity-check", "mover", "webui"
            ],
            "requires_array_status_check": True,
            "parity_operation_block": True  # Block during parity operations
        },
        "filesystem_protection": {
            "protected_paths": ["/mnt/user", "/mnt/disk*", "/boot"],
            "array_mount_awareness": True,
            "cache_drive_protection": True
        },
        "service_protection": {
            "critical_services": ["nginx", "php-fpm", "smbd"],
            "docker_service_dependency": True
        }
    },
    "ubuntu": {
        "container_protection": {
            "max_bulk_operations": 15,
            "protected_containers": [
                "monitoring-*", "logging-*", "proxy-*", "database-*"
            ],
            "systemd_integration": True
        },
        "filesystem_protection": {
            "protected_paths": ["/", "/boot", "/var", "/etc"],
            "lvm_awareness": True,
            "snap_protection": True
        },
        "service_protection": {
            "critical_services": ["ssh", "networking", "systemd-*"],
            "package_manager_locks": True
        }
    },
    "wsl2": {
        "container_protection": {
            "max_bulk_operations": 8,
            "protected_containers": ["dev-*", "vscode-*"],
            "host_integration_awareness": True
        },
        "filesystem_protection": {
            "protected_paths": ["/mnt/c", "/mnt/wsl"],
            "windows_interop_protection": True
        },
        "service_protection": {
            "critical_services": ["ssh", "docker"],
            "windows_service_deps": True
        }
    },
    "windows": {
        "container_protection": {
            "max_bulk_operations": 3,
            "protected_containers": ["*"],  # Extra protection on Windows
            "docker_desktop_integration": True
        },
        "filesystem_protection": {
            "protected_paths": ["C:\\Windows", "C:\\Program Files"],
            "ntfs_permissions_check": True
        },
        "service_protection": {
            "critical_services": ["Docker Desktop", "Docker Engine"],
            "windows_service_deps": True
        }
    }
}

class DeviceSpecificProtection:
    """Apply device-specific protection rules"""
    
    def __init__(self):
        self.protection_rules = DEVICE_PROTECTION_RULES
        
    async def apply_device_protection(self, command: str, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply device-specific protection logic"""
        
        device_type = device_info.get("type", "ubuntu")  # Default to ubuntu
        rules = self.protection_rules.get(device_type, self.protection_rules["ubuntu"])
        
        protection_result = {
            "device_type": device_type,
            "protection_applied": [],
            "additional_checks": [],
            "enhanced_warnings": []
        }
        
        # Apply container protection rules
        if "docker" in command.lower():
            container_rules = rules.get("container_protection", {})
            
            if device_type == "unraid" and container_rules.get("parity_operation_block"):
                parity_status = await self._check_unraid_parity_status(device_info)
                if parity_status.get("running"):
                    protection_result["additional_checks"].append({
                        "type": "parity_operation_active",
                        "message": "Unraid parity operation in progress",
                        "recommendation": "Wait for parity check/sync to complete"
                    })
            
            protected_containers = container_rules.get("protected_containers", [])
            if protected_containers:
                protection_result["enhanced_warnings"].append(
                    f"Protected containers detected: {', '.join(protected_containers)}"
                )
        
        # Apply filesystem protection
        if any(cmd in command.lower() for cmd in ["rm", "delete", "destroy"]):
            fs_rules = rules.get("filesystem_protection", {})
            protected_paths = fs_rules.get("protected_paths", [])
            
            for path in protected_paths:
                if path in command:
                    protection_result["additional_checks"].append({
                        "type": "protected_filesystem",
                        "message": f"Command affects protected path: {path}",
                        "recommendation": "Double-check path specification"
                    })
        
        return protection_result
```

#### **Integration with Existing Tool Transformation**

```python
def create_safe_infrastructure_tool(original_tool: Tool) -> Tool:
    """Transform infrastructure management tools with destructive action protection"""
    
    destructive_manager = DestructiveActionManager()
    device_protection = DeviceSpecificProtection()
    command_detector = DestructiveCommandDetector()
    
    async def protected_tool_execution(args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with comprehensive destructive action protection"""
        
        # Extract command and device context
        command = args.get("command", "")
        device_info = args.get("device_info", {})
        force = args.get("force", False)
        
        # Skip protection if explicitly forced (for confirmed operations)
        if force and "confirmed_operation_id" in args:
            return await original_tool.call(args)
        
        # Analyze command for destructive patterns
        analysis = command_detector.analyze_command(command, device_info)
        
        if analysis and analysis.requires_confirmation:
            # Apply device-specific protection rules
            device_protection_result = await device_protection.apply_device_protection(
                command, device_info
            )
            
            # Enhance analysis with device-specific context
            analysis.safety_warnings.extend(device_protection_result["enhanced_warnings"])
            
            # Require confirmation with enhanced context
            return await destructive_manager.require_confirmation(
                analysis, 
                {
                    "user_args": args,
                    "device_protection": device_protection_result,
                    "original_tool": original_tool.name
                }
            )
        
        # Execute normally if no destructive patterns detected
        return await original_tool.call(args)
    
    return Tool.from_tool(
        original_tool,
        arg_transforms=[
            ArgTransform(
                name="destructive_action_protection",
                transform=protected_tool_execution,
                description="Multi-layered destructive action protection with device-aware safety rules"
            )
        ]
    )

async def create_confirmation_tool() -> Tool:
    """Create dedicated confirmation tool for processing destructive action confirmations"""
    
    destructive_manager = DestructiveActionManager()
    
    async def process_confirmation(operation_id: str, confirmation_phrase: str) -> Dict[str, Any]:
        """Process destructive action confirmation"""
        result = await destructive_manager.process_confirmation(operation_id, confirmation_phrase)
        
        if result["status"] == "confirmed":
            # Execute the original operation with force flag
            execution_context = result["execution_context"]
            original_args = execution_context["user_args"]
            original_args["force"] = True
            original_args["confirmed_operation_id"] = operation_id
            
            # Add audit trail information
            original_args["audit_info"] = {
                "confirmation_timestamp": time.time(),
                "operation_id": operation_id,
                "risk_level": result["analysis"].risk_level.value,
                "user_confirmed": True
            }
            
            # Execute with original tool
            # This would typically call the appropriate infrastructure tool
            # with the enhanced context and audit information
            
        return result
    
    return Tool(
        name="confirm-destructive-operation",
        description="Confirm and execute previously blocked destructive operation",
        parameters={
            "operation_id": {
                "type": "string",
                "description": "Operation ID from the blocked destructive action"
            },
            "confirmation_phrase": {
                "type": "string", 
                "description": "Exact confirmation phrase as specified in the warning"
            }
        },
        function=process_confirmation
    )
```

#### **Real-World Usage Examples**

**Example 1: Container Bulk Stop Protection**
```
User Input: "Stop all containers on my Ubuntu server"
System Response:
⚠️  DESTRUCTIVE ACTION BLOCKED

Risk Assessment: HIGH
- This will stop ALL 12 running containers on ubuntu-server
- Estimated downtime: 5-15 minutes
- Affected services: nginx-proxy, postgres-db, redis-cache, api-server...

Safety Warnings:
- Critical services detected (database, web, monitoring)
- Service dependencies may be broken

Safer Alternatives:
1. Stop specific containers: docker stop nginx-proxy postgres-db
2. Graceful service shutdown: docker-compose down

To proceed, type: "yes, stop all 12 containers"
Or use: confirm-operation destructive_1704123456_7891

Operation expires in 5 minutes.
```

**Example 2: Unraid Parity Protection**
```
User Input: "docker stop $(docker ps -q)"
System Response:
⚠️  DESTRUCTIVE ACTION BLOCKED

Risk Assessment: CRITICAL
- Unraid parity operation currently running (67% complete)
- This will stop ALL 8 containers during parity check
- Risk of array corruption if containers access drives

Enhanced Protection (Unraid):
- Parity operation must complete before container operations
- Protected containers: unraid-webui, mover, parity-check
- Array integrity protection active

Recommendation: Wait for parity check to complete (estimated 2 hours remaining)

Operation blocked until parity operation completes.
```

**Example 3: WSL2 Development Environment**
```
User Input: "docker system prune -af"  
System Response:
⚠️  DESTRUCTIVE ACTION BLOCKED

Risk Assessment: MEDIUM
- This will remove ALL unused containers, networks, and images
- Estimated cleanup: ~5GB Docker data
- Development containers may need rebuilding

WSL2 Specific Warnings:
- Windows host integration containers protected
- Dev environment containers (vscode-*, dev-*) will be preserved
- Docker Desktop integration maintained

To proceed, type: "yes, prune all unused docker resources"

Safer Alternative: 
- Selective cleanup: docker container prune -f
- Image cleanup only: docker image prune -f
```

This destructive action protection system provides **comprehensive safety** while maintaining **operational flexibility**, making it a true tentpole feature that differentiates our infrastructure management platform from generic automation tools.

---

## 🔗 **Advanced FastMCP FastAPI Integration Patterns**

### **Current Integration Analysis**
Based on analysis of FastMCP FastAPI integration best practices and our existing architecture:

- **Current Pattern**: Direct HTTP client calls from MCP tools to FastAPI endpoints
- **Current Limitations**: Manual endpoint mapping, no shared middleware, separate authentication contexts
- **Enhancement Opportunity**: Leverage FastMCP's advanced FastAPI integration patterns for seamless integration

### **Enhanced Integration Architecture**

#### **Purpose-Built MCP Tools vs Direct API Conversion**

```python
# Enhanced MCP server generation based on FastMCP FastAPI integration patterns
from fastmcp import Tool
from fastmcp.integrations.fastapi import create_mcp_server_from_fastapi
from typing import Dict, Any, Optional
import asyncio
from contextlib import asynccontextmanager

class InfrastructorMCPIntegration:
    """Advanced FastMCP + FastAPI integration for infrastructure management"""
    
    def __init__(self, fastapi_app):
        self.fastapi_app = fastapi_app
        self.mcp_server = None
        self.shared_context = {}
        
    @asynccontextmanager
    async def create_integrated_lifespan(self):
        """Nested context management for complex application lifecycle"""
        
        # Initialize shared resources
        async with self._initialize_database_context() as db_context:
            async with self._initialize_ssh_pool_context() as ssh_context:
                async with self._initialize_cache_context() as cache_context:
                    
                    # Combine all contexts
                    self.shared_context = {
                        **db_context,
                        **ssh_context, 
                        **cache_context
                    }
                    
                    # Create purpose-built MCP server
                    self.mcp_server = await self._create_purpose_built_server()
                    
                    try:
                        yield {
                            "fastapi_app": self.fastapi_app,
                            "mcp_server": self.mcp_server,
                            "shared_context": self.shared_context
                        }
                    finally:
                        # Cleanup in reverse order
                        if self.mcp_server:
                            await self.mcp_server.cleanup()
    
    async def _initialize_database_context(self):
        """Database connection and health monitoring context"""
        @asynccontextmanager
        async def db_lifespan():
            # Initialize database connections
            db_pool = await self._create_database_pool()
            health_monitor = await self._start_database_health_monitor(db_pool)
            
            try:
                yield {
                    "database_pool": db_pool,
                    "health_monitor": health_monitor,
                    "db_healthy": True
                }
            finally:
                await health_monitor.stop()
                await db_pool.close()
        
        return db_lifespan()
    
    async def _initialize_ssh_pool_context(self):
        """SSH connection pool and management context"""
        @asynccontextmanager
        async def ssh_lifespan():
            # Initialize SSH pools for all devices
            ssh_pools = await self._create_device_ssh_pools()
            connection_monitor = await self._start_ssh_health_monitor(ssh_pools)
            
            try:
                yield {
                    "ssh_pools": ssh_pools,
                    "connection_monitor": connection_monitor,
                    "ssh_healthy": True
                }
            finally:
                await connection_monitor.stop()
                for pool in ssh_pools.values():
                    await pool.close_all_connections()
        
        return ssh_lifespan()
    
    async def _create_purpose_built_server(self) -> Dict[str, Tool]:
        """Create purpose-built MCP tools instead of direct API conversion"""
        
        # Focus on high-level infrastructure operations, not low-level API mirroring
        purpose_built_tools = {
            
            # System Health & Monitoring Tools
            "infrastructure_health": await self._create_health_monitoring_tool(),
            "device_diagnostics": await self._create_device_diagnostics_tool(), 
            "performance_analysis": await self._create_performance_analysis_tool(),
            
            # Configuration Management Tools  
            "configuration_sync": await self._create_config_sync_tool(),
            "configuration_history": await self._create_config_history_tool(),
            "configuration_rollback": await self._create_config_rollback_tool(),
            
            # Container Orchestration Tools
            "container_orchestration": await self._create_container_orchestration_tool(),
            "service_dependency_management": await self._create_service_dependency_tool(),
            "container_security_scan": await self._create_container_security_tool(),
            
            # Infrastructure Automation Tools
            "automated_maintenance": await self._create_maintenance_automation_tool(),
            "backup_orchestration": await self._create_backup_orchestration_tool(),
            "disaster_recovery": await self._create_disaster_recovery_tool(),
            
            # Advanced Analytics Tools
            "predictive_analysis": await self._create_predictive_analysis_tool(),
            "capacity_planning": await self._create_capacity_planning_tool(),
            "cost_optimization": await self._create_cost_optimization_tool()
        }
        
        return purpose_built_tools
```

#### **Middleware Integration for Cross-Cutting Concerns**

```python
# Advanced middleware integration for shared concerns
from fastapi import Request, Response
from fastmcp.middleware import MCPMiddleware
import structlog

class SharedInfrastructureMiddleware:
    """Shared middleware for both FastAPI and MCP operations"""
    
    def __init__(self):
        self.logger = structlog.get_logger("infrastructure_middleware")
        self.metrics_collector = MetricsCollector()
        self.audit_logger = AuditLogger()
    
    async def __call__(self, request: Request, call_next):
        """Unified middleware for all infrastructure operations"""
        
        # Start timing and correlation tracking
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        # Bind correlation ID to structured logging context
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_type="infrastructure_operation",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        try:
            # Pre-operation hooks
            await self._pre_operation_hooks(request, correlation_id)
            
            # Execute operation (FastAPI route or MCP tool)
            response = await call_next(request)
            
            # Post-operation hooks
            await self._post_operation_hooks(request, response, correlation_id, start_time)
            
            return response
            
        except Exception as e:
            # Error handling and logging
            await self._error_handling_hooks(request, e, correlation_id, start_time)
            raise
    
    async def _pre_operation_hooks(self, request: Request, correlation_id: str):
        """Pre-operation middleware hooks"""
        
        # Authentication and authorization
        auth_result = await self._validate_authentication(request)
        if not auth_result.valid:
            raise HTTPException(status_code=401, detail="Authentication failed")
        
        # Rate limiting based on operation type
        await self._apply_rate_limiting(request, auth_result.user_id)
        
        # Resource availability checks
        await self._check_resource_availability(request)
        
        # Audit logging for security
        await self.audit_logger.log_operation_start(
            correlation_id=correlation_id,
            user_id=auth_result.user_id,
            operation=request.url.path,
            parameters=await self._extract_safe_parameters(request)
        )
    
    async def _post_operation_hooks(self, request: Request, response: Response, 
                                  correlation_id: str, start_time: float):
        """Post-operation middleware hooks"""
        
        execution_time = time.time() - start_time
        
        # Performance metrics collection
        await self.metrics_collector.record_operation(
            operation=request.url.path,
            execution_time=execution_time,
            status_code=getattr(response, 'status_code', 200),
            correlation_id=correlation_id
        )
        
        # Audit logging for completion
        await self.audit_logger.log_operation_complete(
            correlation_id=correlation_id,
            execution_time=execution_time,
            status="success"
        )
        
        # Cache management
        await self._update_cache_metrics(request, response, execution_time)

class MCPAuthenticationMiddleware(MCPMiddleware):
    """FastMCP-specific authentication middleware"""
    
    async def __call__(self, tool_name: str, args: Dict[str, Any], context: Dict[str, Any]):
        """Authenticate MCP tool calls using shared context"""
        
        # Extract authentication from MCP context
        auth_token = context.get("authorization")
        if not auth_token:
            return {
                "error": "AUTHENTICATION_REQUIRED",
                "message": "MCP tool calls require authentication",
                "suggestion": "Provide authorization token in MCP context"
            }
        
        # Validate token using shared authentication service
        auth_result = await self._validate_mcp_token(auth_token)
        if not auth_result.valid:
            return {
                "error": "AUTHENTICATION_FAILED", 
                "message": "Invalid or expired authentication token"
            }
        
        # Add user context to args
        args["_user_context"] = {
            "user_id": auth_result.user_id,
            "permissions": auth_result.permissions,
            "session_id": auth_result.session_id
        }
        
        # Continue to next middleware or tool execution
        return await self.next_middleware(tool_name, args, context)
```

#### **Dependency Injection and Configuration Sharing**

```python
# Advanced dependency injection patterns for shared resources
from fastapi import Depends
from fastmcp.dependencies import MCPDepends
from typing import Annotated

class SharedDependencies:
    """Shared dependency injection for FastAPI and MCP"""
    
    def __init__(self, shared_context: Dict[str, Any]):
        self.shared_context = shared_context
    
    async def get_database_session(self):
        """Shared database session for both FastAPI and MCP"""
        db_pool = self.shared_context["database_pool"]
        async with db_pool.acquire() as connection:
            yield connection
    
    async def get_ssh_client(self, device_id: str):
        """Shared SSH client with connection pooling"""
        ssh_pools = self.shared_context["ssh_pools"]
        if device_id in ssh_pools:
            return ssh_pools[device_id]
        else:
            # Create new pool for device
            new_pool = await self._create_device_pool(device_id)
            ssh_pools[device_id] = new_pool
            return new_pool
    
    async def get_cache_manager(self):
        """Shared cache manager instance"""
        return self.shared_context["cache_manager"]
    
    async def get_unified_data_service(self):
        """Shared unified data collection service"""
        return self.shared_context["unified_data_service"]

# FastAPI route using shared dependencies
@app.get("/api/devices/{device_id}/containers")
async def get_device_containers(
    device_id: str,
    force_refresh: bool = False,
    db_session: Annotated[Any, Depends(shared_deps.get_database_session)],
    unified_service: Annotated[Any, Depends(shared_deps.get_unified_data_service)],
    auth_context: Annotated[Any, Depends(get_current_user)]
):
    """FastAPI endpoint using shared dependencies"""
    return await unified_service.get_container_data(
        device_id=device_id, 
        force_refresh=force_refresh,
        user_context=auth_context
    )

# MCP tool using same shared dependencies
@Tool(
    name="get_container_status",
    description="Get container status across all devices with advanced filtering"
)
async def get_container_status(
    device_filter: str = "all",
    status_filter: str = "all", 
    include_metrics: bool = True,
    _unified_service: Annotated[Any, MCPDepends(shared_deps.get_unified_data_service)],
    _user_context: Annotated[Any, MCPDepends(get_mcp_user_context)]
) -> Dict[str, Any]:
    """MCP tool using shared infrastructure services"""
    
    # Use same unified service as FastAPI endpoints
    result = await _unified_service.get_multi_device_container_data(
        device_filter=device_filter,
        status_filter=status_filter,
        include_metrics=include_metrics,
        user_context=_user_context
    )
    
    return {
        "status": "success",
        "data": result,
        "source": "unified_data_service",
        "cached": result.get("from_cache", False)
    }
```

#### **Error Handling and Resilience Patterns**

```python
# Unified error handling for FastAPI and MCP
from fastmcp.errors import MCPError
from fastapi import HTTPException
import asyncio

class UnifiedErrorHandler:
    """Shared error handling for both FastAPI and MCP operations"""
    
    def __init__(self):
        self.error_classifier = ErrorClassifier()
        self.recovery_manager = AutomatedRecoveryManager()
        self.alert_manager = AlertManager()
    
    async def handle_infrastructure_error(self, error: Exception, 
                                        operation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Unified error handling with automatic recovery attempts"""
        
        # Classify error type and determine recovery strategy
        error_classification = await self.error_classifier.classify_error(
            error, operation_context
        )
        
        error_response = {
            "error_type": error_classification.error_type,
            "severity": error_classification.severity,
            "user_message": error_classification.user_friendly_message,
            "technical_details": str(error),
            "correlation_id": operation_context.get("correlation_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recovery_attempted": False,
            "retry_possible": error_classification.is_retryable
        }
        
        # Attempt automatic recovery for recoverable errors
        if error_classification.auto_recovery_possible:
            try:
                recovery_result = await self.recovery_manager.attempt_recovery(
                    error_classification, operation_context
                )
                
                error_response.update({
                    "recovery_attempted": True,
                    "recovery_successful": recovery_result.success,
                    "recovery_details": recovery_result.details
                })
                
                # If recovery successful, retry the operation
                if recovery_result.success:
                    return await self._retry_operation(operation_context)
                    
            except Exception as recovery_error:
                error_response["recovery_error"] = str(recovery_error)
        
        # Send alerts for critical errors
        if error_classification.severity in ["critical", "high"]:
            await self.alert_manager.send_infrastructure_alert(
                error_classification, operation_context, error_response
            )
        
        return error_response
    
    def to_fastapi_exception(self, error_response: Dict[str, Any]) -> HTTPException:
        """Convert unified error response to FastAPI HTTPException"""
        
        status_code_mapping = {
            "authentication_error": 401,
            "authorization_error": 403,
            "resource_not_found": 404,
            "validation_error": 422,
            "infrastructure_error": 503,
            "timeout_error": 504
        }
        
        status_code = status_code_mapping.get(
            error_response["error_type"], 500
        )
        
        return HTTPException(
            status_code=status_code,
            detail={
                "message": error_response["user_message"],
                "correlation_id": error_response["correlation_id"],
                "retry_possible": error_response["retry_possible"],
                "recovery_attempted": error_response["recovery_attempted"]
            }
        )
    
    def to_mcp_error(self, error_response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert unified error response to MCP-compatible format"""
        
        return {
            "error": error_response["error_type"].upper(),
            "message": error_response["user_message"],
            "details": {
                "correlation_id": error_response["correlation_id"],
                "severity": error_response["severity"],
                "timestamp": error_response["timestamp"],
                "retry_possible": error_response["retry_possible"],
                "recovery_info": {
                    "attempted": error_response["recovery_attempted"],
                    "successful": error_response.get("recovery_successful", False)
                }
            },
            "suggestions": self._generate_user_suggestions(error_response)
        }
```

#### **Performance Optimization and Monitoring Integration**

```python
# Performance monitoring and optimization for integrated architecture
class IntegratedPerformanceMonitor:
    """Performance monitoring across FastAPI and MCP operations"""
    
    def __init__(self):
        self.metrics_store = MetricsStore()
        self.performance_analyzer = PerformanceAnalyzer()
        
    async def monitor_operation_performance(self, operation_type: str, 
                                          execution_context: Dict[str, Any]):
        """Monitor performance across both API and MCP operations"""
        
        @asynccontextmanager
        async def performance_context():
            start_time = time.time()
            start_memory = await self._get_memory_usage()
            
            try:
                yield {
                    "start_time": start_time,
                    "start_memory": start_memory,
                    "operation_type": operation_type
                }
            finally:
                end_time = time.time()
                end_memory = await self._get_memory_usage()
                
                # Record comprehensive performance metrics
                await self.metrics_store.record_performance_metrics({
                    "operation_type": operation_type,
                    "execution_time": end_time - start_time,
                    "memory_delta": end_memory - start_memory,
                    "timestamp": datetime.now(timezone.utc),
                    "correlation_id": execution_context.get("correlation_id"),
                    "user_id": execution_context.get("user_id"),
                    "source": execution_context.get("source", "unknown")  # "fastapi" or "mcp"
                })
                
                # Analyze for performance anomalies
                await self._analyze_performance_anomalies(
                    operation_type, end_time - start_time
                )
        
        return performance_context()
    
    async def generate_performance_insights(self) -> Dict[str, Any]:
        """Generate performance insights across both FastAPI and MCP operations"""
        
        # Analyze performance patterns
        performance_data = await self.metrics_store.get_recent_performance_data()
        
        insights = {
            "api_vs_mcp_performance": await self._compare_api_mcp_performance(performance_data),
            "bottleneck_identification": await self._identify_bottlenecks(performance_data),
            "optimization_recommendations": await self._generate_optimization_recommendations(performance_data),
            "resource_utilization": await self._analyze_resource_utilization(performance_data)
        }
        
        return insights
```

### **Implementation Integration with Current Architecture**

```python
# Integration with existing infrastructor architecture
async def create_enhanced_infrastructor_app():
    """Create enhanced infrastructor application with advanced FastMCP integration"""
    
    # Create FastAPI app with existing configuration
    fastapi_app = create_fastapi_app()  # Existing function
    
    # Create integrated MCP server with advanced patterns
    mcp_integration = InfrastructorMCPIntegration(fastapi_app)
    
    # Setup shared middleware
    shared_middleware = SharedInfrastructureMiddleware()
    fastapi_app.middleware("http")(shared_middleware)
    
    # Setup shared dependencies
    async with mcp_integration.create_integrated_lifespan() as integrated_context:
        shared_deps = SharedDependencies(integrated_context["shared_context"])
        
        # Register shared dependencies with FastAPI
        fastapi_app.dependency_overrides.update({
            get_database_session: shared_deps.get_database_session,
            get_unified_data_service: shared_deps.get_unified_data_service,
            get_cache_manager: shared_deps.get_cache_manager
        })
        
        # Create enhanced MCP server with purpose-built tools
        mcp_server = integrated_context["mcp_server"]
        
        return {
            "fastapi_app": fastapi_app,
            "mcp_server": mcp_server,
            "shared_context": integrated_context["shared_context"],
            "integration_manager": mcp_integration
        }

# Usage in main application
async def main():
    """Enhanced main application with integrated FastAPI + MCP"""
    
    integrated_app = await create_enhanced_infrastructor_app()
    
    # Start both servers with shared lifecycle
    await asyncio.gather(
        uvicorn.run(
            integrated_app["fastapi_app"],
            host="0.0.0.0", 
            port=9101,
            lifespan="on"
        ),
        integrated_app["mcp_server"].serve(
            host="0.0.0.0",
            port=9102
        )
    )
```

This enhanced integration provides:

1. **Shared Resource Management** - Database pools, SSH connections, and cache shared between FastAPI and MCP
2. **Purpose-Built MCP Tools** - High-level infrastructure operations instead of direct API mirroring  
3. **Unified Middleware** - Shared authentication, logging, and error handling
4. **Advanced Dependency Injection** - Consistent resource access patterns
5. **Integrated Performance Monitoring** - Comprehensive metrics across both interfaces
6. **Resilient Error Handling** - Automatic recovery and intelligent error classification

These patterns transform our current basic HTTP client approach into a sophisticated, integrated infrastructure management platform that leverages the full power of FastMCP's advanced integration capabilities.

### **Tool Chaining and Workflow Automation**
```python
# Intelligent tool chaining for complex workflows
class WorkflowAutomator:
    def __init__(self):
        self.workflow_templates = {}
    
    @Tool.from_tool(
        name="diagnose_system_issues",
        description="Comprehensive system diagnosis across all devices"
    )
    async def diagnose_system_issues(self, focus: str = "performance") -> Dict[str, Any]:
        """Automated system diagnosis workflow"""
        
        diagnosis_results = {
            "focus": focus,
            "devices_checked": [],
            "issues_found": [], 
            "recommendations": [],
            "automated_fixes_applied": []
        }
        
        # Get all available devices
        devices = await self._get_active_devices()
        
        for device in devices:
            device_name = device["hostname"]
            
            # Step 1: Get comprehensive metrics
            metrics = await get_metrics(device_name)
            diagnosis_results["devices_checked"].append(device_name)
            
            # Step 2: Analyze for issues
            issues = await self._analyze_device_issues(metrics, focus)
            if issues:
                diagnosis_results["issues_found"].extend(issues)
            
            # Step 3: Check container health if applicable
            if device.get("capabilities", {}).get("docker"):
                container_status = await manage_containers(device_name, "status")
                container_issues = await self._analyze_container_issues(container_status)
                diagnosis_results["issues_found"].extend(container_issues)
            
            # Step 4: Apply automated fixes if safe
            automated_fixes = await self._apply_safe_automated_fixes(device_name, issues)
            diagnosis_results["automated_fixes_applied"].extend(automated_fixes)
        
        # Generate recommendations
        diagnosis_results["recommendations"] = await self._generate_recommendations(
            diagnosis_results["issues_found"]
        )
        
        return diagnosis_results
    
    @Tool.from_tool(
        name="maintenance_mode",
        description="Put device in maintenance mode safely"
    )
    async def maintenance_mode(self, device: str, enable: bool = True) -> Dict[str, Any]:
        """Comprehensive maintenance mode workflow"""
        
        if enable:
            # Entering maintenance mode
            return await self._enter_maintenance_mode(device)
        else:
            # Exiting maintenance mode
            return await self._exit_maintenance_mode(device)
    
    async def _enter_maintenance_mode(self, device: str) -> Dict[str, Any]:
        """Safely enter maintenance mode"""
        steps = []
        
        # Step 1: Get current status
        current_status = await get_metrics(device)
        steps.append({"step": "status_check", "result": "completed"})
        
        # Step 2: Stop non-critical containers
        container_status = await manage_containers(device, "status")
        non_critical = await self._identify_non_critical_containers(container_status)
        
        for container in non_critical:
            await manage_containers(device, "stop", container)
            steps.append({"step": f"stop_container_{container}", "result": "completed"})
        
        # Step 3: Set monitoring to reduced frequency
        await self._set_monitoring_frequency(device, "maintenance")
        steps.append({"step": "reduce_monitoring", "result": "completed"})
        
        return {
            "device": device,
            "maintenance_mode": True,
            "steps_completed": steps,
            "non_critical_containers_stopped": non_critical
        }
```

This comprehensive MCP Tool Transformation Layer provides:

1. **Simplified Interfaces**: Complex parameters hidden and auto-optimized
2. **Device-Aware Tools**: Automatic capability detection and parameter enhancement  
3. **Enhanced Validation**: Pre-flight checks and safety measures
4. **Intelligent Responses**: Context-aware formatting with insights and alerts
5. **Workflow Automation**: Complex multi-step operations made simple
6. **Safety Features**: Protection against destructive operations
7. **Performance Optimization**: Device-specific timeout and caching strategies

The transformation layer maintains the existing HTTP API architecture while dramatically improving the MCP tool user experience through FastMCP 2.11.0's advanced tool transformation capabilities.