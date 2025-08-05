# **Phase 2: Real-time Configuration Monitoring (Weeks 3-4)**

This phase builds upon the unified service layer created in Phase 1 to introduce a sophisticated, real-time configuration monitoring system. The primary goal is to move from periodic polling to an event-driven architecture for configuration changes, providing immediate insights, impact analysis, and robust management capabilities.

## **File Watching and Event-driven Monitoring**

This section focuses on establishing the core components for real-time file monitoring, change detection, and impact analysis.

### **27. Implement `RemoteFileWatcher` class with SSH-based inotify streaming**

**Objective:** Create a resilient mechanism to monitor file system events on remote devices in real-time without constant polling.

**Architecture:** The `RemoteFileWatcher` will establish a persistent SSH connection to a target device and execute `inotifywait`. It will stream the output, parse events, and trigger callbacks for file changes. This approach is significantly more efficient than polling, as it only consumes resources when a change occurs.

```python
# apps/backend/src/services/configuration_monitoring.py

import asyncio
from typing import List, Callable, Dict, Optional
from uuid import UUID
from datetime import datetime, timezone
import structlog

from ...models.device import Device
from ...schemas.configuration import FileChangeEvent

logger = structlog.get_logger(__name__)

class RemoteFileWatcher:
    """
    Monitors file system events on a remote device using SSH and inotifywait.
    This class establishes a long-lived SSH process to stream file change events,
    providing a low-latency alternative to polling.
    """
    def __init__(self, device: Device, ssh_connection_manager):
        self.device = device
        self.ssh_connection_manager = ssh_connection_manager
        self.watch_process: Optional[asyncio.subprocess.Process] = None
        self.callbacks: Dict[str, Callable] = {} # Maps path patterns to callbacks
        self._is_running = False

    async def start(self, watch_definitions: Dict[str, Callable]):
        """
        Start the file watching process for a set of path definitions.

        Args:
            watch_definitions: A dictionary where keys are path patterns
                               (e.g., "/etc/nginx/conf.d/*.conf") and values
                               are the async callbacks to execute on change.
        """
        if self._is_running:
            logger.warning("File watcher already running for device", device_id=self.device.id)
            return

        self.callbacks = watch_definitions
        paths_to_watch = " ".join(self.callbacks.keys())
        
        # -m: monitor indefinitely
        # -r: recursive
        # -e: events to watch
        # --format: custom output format for easy parsing
        # --timefmt: timestamp format
        event_flags = "modify,create,delete,move"
        watch_cmd = (
            f"inotifywait -m -r -e {event_flags} "
            f"--format '%w%f|%e|%T' --timefmt '%s' "
            f"{paths_to_watch} 2>/dev/null"
        )
        
        logger.info("Starting remote file watcher", device_id=self.device.id, command=watch_cmd)
        
        try:
            self.watch_process = await self.ssh_connection_manager.stream_command(
                device_id=self.device.id,
                command=watch_cmd,
                stdout_callback=self._process_file_event_line,
                stderr_callback=self._process_stderr
            )
            self._is_running = True
            logger.info("Remote file watcher started successfully", device_id=self.device.id)
        except Exception as e:
            logger.error("Failed to start remote file watcher", device_id=self.device.id, error=e)
            self._is_running = False

    async def _process_file_event_line(self, line: str):
        """Parse a single line of output from inotifywait and trigger callbacks."""
        try:
            line = line.strip()
            if not line:
                return

            # Expected format: path|event_type|timestamp
            path, event_types, timestamp_str = line.split('|')
            
            file_event = FileChangeEvent(
                path=path,
                event_types=event_types.split(','),
                timestamp=datetime.fromtimestamp(int(timestamp_str), timezone.utc),
                device_id=self.device.id
            )
            
            # Find matching callback and execute
            for pattern, callback in self.callbacks.items():
                # Simple glob matching for now, can be enhanced
                if path.startswith(pattern.replace('*', '')):
                    await callback(file_event)
                    break
        except Exception as e:
            logger.warning("Failed to process file event line", line=line, error=e)

    async def _process_stderr(self, line: str):
        """Log stderr output from the watcher process."""
        logger.warning("Remote file watcher stderr", device_id=self.device.id, output=line.strip())

    async def stop(self):
        """Stop the file watching process."""
        if self.watch_process and self.watch_process.returncode is None:
            try:
                self.watch_process.terminate()
                await self.watch_process.wait()
                logger.info("Remote file watcher stopped", device_id=self.device.id)
            except ProcessLookupError:
                logger.warning("Watcher process already terminated", device_id=self.device.id)
        self._is_running = False
```

### **28. Create `ConfigurationMonitoringService` with hybrid file watching + polling fallback**

**Objective:** Orchestrate the configuration monitoring process, intelligently choosing between real-time file watching and periodic polling based on device capabilities and health.

**Architecture:** This service will manage `RemoteFileWatcher` instances for each device. If a device doesn't support `inotifywait` or if the SSH streaming connection fails, the service will automatically fall back to a periodic polling mechanism using the `UnifiedDataCollectionService`. This ensures reliability across a heterogeneous environment.

```python
# apps/backend/src/services/configuration_monitoring.py

class ConfigurationMonitoringService:
    """
    Orchestrates configuration monitoring using a hybrid approach.
    Prioritizes real-time file watching and falls back to periodic polling.
    """
    def __init__(self, unified_service: UnifiedDataCollectionService, device_service: DeviceService):
        self.unified_service = unified_service
        self.device_service = device_service
        self.file_watchers: Dict[UUID, RemoteFileWatcher] = {}
        self.polling_tasks: Dict[UUID, asyncio.Task] = {}
        
        # Define configurations to monitor
        self.monitored_configs = {
            "proxy_configs": {
                "paths": ["/config/nginx/proxy-confs/*.conf", "/config/nginx/site-confs/*.conf"],
                "parser": "nginx",
                "fallback_interval_sec": 300,
            },
            "docker_compose": {
                "paths": ["/docker-compose.yml", "/compose/*/docker-compose.yml"],
                "parser": "docker_compose",
                "fallback_interval_sec": 600,
            },
            "systemd_services": {
                "paths": ["/etc/systemd/system/*.service"],
                "parser": "systemd",
                "fallback_interval_sec": 900,
            }
        }

    async def setup_monitoring_for_all_devices(self):
        """Initialize monitoring for all active devices."""
        devices = await self.device_service.get_all_devices()
        for device in devices:
            await self.setup_device_monitoring(device)

    async def setup_device_monitoring(self, device: Device):
        """
        Set up configuration monitoring for a single device, attempting
        to use file watching first.
        """
        logger.info("Setting up configuration monitoring", device_id=device.id)
        
        # Check for inotify-tools capability
        has_inotify = await self.unified_service.check_command_availability(device.id, "inotifywait")
        
        if has_inotify:
            try:
                watcher = RemoteFileWatcher(device, self.unified_service.ssh_connection_manager)
                watch_definitions = {}
                for config_type, config_def in self.monitored_configs.items():
                    for path in config_def["paths"]:
                         watch_definitions[path] = lambda event, ct=config_type: self._handle_config_change_event(event, ct)
                
                await watcher.start(watch_definitions)
                self.file_watchers[device.id] = watcher
                logger.info("Using real-time file watching for device", device_id=device.id)
            except Exception as e:
                logger.warning("File watching setup failed, falling back to polling", device_id=device.id, error=e)
                await self._setup_polling_fallback(device)
        else:
            logger.info("inotifywait not available, using polling fallback", device_id=device.id)
            await self._setup_polling_fallback(device)

    async def _setup_polling_fallback(self, device: Device):
        """Set up periodic polling for a device as a fallback."""
        if device.id in self.polling_tasks:
            self.polling_tasks[device.id].cancel()

        task = asyncio.create_task(self._polling_loop(device))
        self.polling_tasks[device.id] = task

    async def _polling_loop(self, device: Device):
        """The main loop for periodic configuration checks."""
        # Use the minimum interval for the first check
        await asyncio.sleep(min(c["fallback_interval_sec"] for c in self.monitored_configs.values()))
        
        while True:
            logger.debug("Executing polling check for configs", device_id=device.id)
            for config_type, config_def in self.monitored_configs.items():
                try:
                    await self.unified_service.collect_and_store_data(
                        device_id=device.id,
                        data_type=config_type,
                        force_refresh=True # Always check fresh
                    )
                except Exception as e:
                    logger.error("Polling failed for config type", device_id=device.id, config_type=config_type, error=e)
            
            # This can be made more sophisticated to poll each config type on its own interval
            await asyncio.sleep(300) # Generic 5-minute interval for subsequent polls

    async def _handle_config_change_event(self, event: FileChangeEvent, config_type: str):
        """Callback triggered by RemoteFileWatcher."""
        logger.info("File change event detected", device_id=event.device_id, path=event.path, type=event.event_types)
        
        # Trigger immediate collection and processing
        await self.unified_service.collect_and_store_data(
            device_id=event.device_id,
            data_type=config_type,
            force_refresh=True,
            context={"source": "file_watch", "event": event.dict()}
        )
```

### **29. Implement persistent SSH connections for streaming file change events**

**Objective:** Minimize the overhead of establishing new SSH connections for file watching by maintaining a long-lived, stable connection.

**Architecture:** This task involves enhancing the `SSHCommandManager` (from Phase 1) to support streaming commands. Instead of waiting for a command to finish and return an exit code, it will open a process and yield stdout/stderr lines as they arrive. This requires careful management of the process lifecycle, connection health, and automatic reconnection logic.

```python
# apps/backend/src/utils/ssh_command_manager.py (Enhancements)

class SSHCommandManager:
    # ... (existing methods) ...

    async def stream_command(
        self,
        device_id: UUID,
        command: str,
        stdout_callback: Callable[[str], Awaitable[None]],
        stderr_callback: Callable[[str], Awaitable[None]],
        timeout: int = 3600 * 24 # Long timeout for persistent streams
    ) -> asyncio.subprocess.Process:
        """
        Executes a command over SSH and streams its output.

        This method is designed for long-running commands like `inotifywait` or `tail -f`.
        It returns the process object so the caller can manage its lifecycle.

        Args:
            device_id: The ID of the device to connect to.
            command: The command to execute.
            stdout_callback: An async callable to process each line of stdout.
            stderr_callback: An async callable to process each line of stderr.
            timeout: Command timeout in seconds. Defaults to 24 hours.

        Returns:
            An asyncio.subprocess.Process instance.
        """
        ssh_client = await self.ssh_client_manager.get_client(device_id)
        
        # The command needs to be properly escaped for the shell
        full_ssh_command = ssh_client.get_ssh_command(f"exec {command}")

        process = await asyncio.create_subprocess_shell(
            " ".join(full_ssh_command),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Create tasks to process stdout and stderr streams
        asyncio.create_task(self._stream_processor(process.stdout, stdout_callback))
        asyncio.create_task(self._stream_processor(process.stderr, stderr_callback))
        
        # Task to monitor connection health and handle reconnects
        asyncio.create_task(self._monitor_stream_process(process, device_id, command, stdout_callback, stderr_callback))

        return process

    async def _stream_processor(self, stream: asyncio.StreamReader, callback: Callable):
        """Helper to read from a stream and invoke a callback for each line."""
        async for line in stream:
            await callback(line.decode('utf-8', errors='ignore'))

    async def _monitor_stream_process(self, process, device_id, command, stdout_cb, stderr_cb):
        """Monitors the streaming process and attempts to reconnect on failure."""
        return_code = await process.wait()
        logger.warning(
            "Streaming command process exited",
            device_id=device_id,
            return_code=return_code,
            command=command
        )
        
        # Implement reconnection logic
        if return_code != 0:
            logger.info("Attempting to reconnect streaming command in 15 seconds...", device_id=device_id)
            await asyncio.sleep(15)
            # This is a simplified reconnect; a robust implementation would use exponential backoff
            # and would need to be handled by the calling service (e.g., ConfigurationMonitoringService)
            # to replace the dead process with a new one.
            # For now, we just log the event.
```

### **30. Create file change event parsing and correlation system**

**Objective:** To make sense of the raw stream of file events, correlate related changes, and reduce noise.

**Architecture:** A system that receives `FileChangeEvent` objects and applies logic to group them. For example, a `git pull` might generate hundreds of `MODIFY` events. This system should correlate these into a single, high-level "Repository Updated" event. It will use time windows and path analysis to group related events.

```python
# apps/backend/src/services/event_correlation.py

from collections import defaultdict

class FileEventCorrelator:
    """
    Correlates raw file change events into meaningful, high-level infrastructure events.
    """
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.pending_events: Dict[UUID, List[FileChangeEvent]] = defaultdict(list)
        self.correlation_window_sec = 5.0 # 5-second window to group events

    async def process_event(self, event: FileChangeEvent):
        """Process a single file change event."""
        device_id = event.device_id
        self.pending_events[device_id].append(event)
        
        # Schedule correlation if not already scheduled for this device
        if len(self.pending_events[device_id]) == 1:
            asyncio.create_task(self._schedule_correlation(device_id))

    async def _schedule_correlation(self, device_id: UUID):
        """Wait for the correlation window to pass, then process events."""
        await asyncio.sleep(self.correlation_window_sec)
        
        events_to_process = self.pending_events.pop(device_id, [])
        if not events_to_process:
            return

        await self._correlate_and_dispatch(device_id, events_to_process)

    async def _correlate_and_dispatch(self, device_id: UUID, events: List[FileChangeEvent]):
        """Analyze a batch of events and dispatch a correlated event."""
        
        # Example 1: Correlate multiple .conf changes into one ProxyConfigUpdated event
        proxy_conf_paths = ["/config/nginx/proxy-confs/", "/config/nginx/site-confs/"]
        proxy_events = [e for e in events if any(e.path.startswith(p) for p in proxy_conf_paths)]
        
        if len(proxy_events) > 1:
            # Create a single correlated event
            correlated_event = {
                "event_type": "ProxyConfigBulkUpdate",
                "device_id": device_id,
                "change_count": len(proxy_events),
                "files_changed": list(set(e.path for e in proxy_events)),
                "start_time": min(e.timestamp for e in proxy_events),
                "end_time": max(e.timestamp for e in proxy_events),
            }
            await self.event_bus.emit("configuration.proxy.bulk_update", correlated_event)
            
            # Remove correlated events from the list
            events = [e for e in events if e not in proxy_events]

        # Process remaining individual events
        for event in events:
            # Simple dispatch for now
            await self.event_bus.emit(f"configuration.file.changed", event.dict())
```

### **31. Implement configuration change detection with hash comparison**

**Objective:** To reliably determine if a configuration file's content has actually changed, avoiding false positives from timestamp-only checks.

**Architecture:** This will be a core function within the `UnifiedDataCollectionService`. When a file change event is received (or during a polling cycle), the service will:
1.  Read the file content from the remote device.
2.  Calculate a SHA256 hash of the content.
3.  Compare this hash against the most recent hash stored in the `ConfigurationSnapshot` table for that file path.
4.  If the hashes differ, a change is confirmed.

```python
# apps/backend/src/services/unified_data_collection.py (Enhancements)
import hashlib

class UnifiedDataCollectionService:
    # ...

    async def _detect_and_store_config_change(
        self,
        device_id: UUID,
        config_type: str,
        file_path: str,
        content: str,
        change_type: str = "MODIFY",
        source: str = "polling"
    ) -> Optional[ConfigurationSnapshot]:
        """
        Detects if content has changed using hash comparison and stores a new snapshot.
        """
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        async with self.db_session_factory() as session:
            # Get the last known snapshot for this file
            last_snapshot = await configuration_service.get_latest_snapshot(
                session, device_id, file_path
            )
            
            if last_snapshot and last_snapshot.content_hash == content_hash:
                logger.debug("No content change detected, hash is identical.", path=file_path, hash=content_hash)
                # Optionally update the 'last_checked' timestamp
                return None
        
        logger.info("Content change detected.", path=file_path, old_hash=getattr(last_snapshot, 'content_hash', None), new_hash=content_hash)
        
        # ... (Proceed with parsing, impact analysis, and storage) ...
        # This logic will be fully implemented in tasks 32-35
        
        # For now, just create the snapshot
        new_snapshot = await configuration_service.create_snapshot(
            session=session,
            device_id=device_id,
            config_type=config_type,
            file_path=file_path,
            raw_content=content,
            content_hash=content_hash,
            change_type=change_type,
            collection_source=source,
            previous_hash=last_snapshot.content_hash if last_snapshot else None
        )
        
        return new_snapshot
```

### **32. Create configuration content parsers (proxy configs, docker-compose, systemd)**

**Objective:** To transform raw configuration text into structured, queryable data.

**Architecture:** A new `parsers` module will be created within the `services` directory. It will contain a base parser class and specific implementations for different configuration types. These parsers will be invoked by the `UnifiedDataCollectionService` after a change is detected but before the `ConfigurationSnapshot` is saved. The parsed JSON will be stored in the `parsed_data` column of the snapshot.

```python
# apps/backend/src/services/parsers/base_parser.py
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseConfigParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> Dict[str, Any]:
        """Parse raw config content into a structured dictionary."""
        pass

# apps/backend/src/services/parsers/docker_compose_parser.py
import yaml
from .base_parser import BaseConfigParser

class DockerComposeParser(BaseConfigParser):
    def parse(self, content: str) -> Dict[str, Any]:
        try:
            data = yaml.safe_load(content)
            
            # Extract key information
            services = list(data.get("services", {}).keys())
            volumes = list(data.get("volumes", {}).keys())
            networks = list(data.get("networks", {}).keys())
            
            return {
                "version": data.get("version", "unknown"),
                "service_count": len(services),
                "services": services,
                "volumes": volumes,
                "networks": networks,
            }
        except yaml.YAMLError as e:
            return {"parsing_error": str(e)}

# apps/backend/src/services/parsers/nginx_parser.py
# Nginx parsing is complex. A library like `crossplane-python` could be used,
# or a regex-based approach for specific directives.
import re
from .base_parser import BaseConfigParser

class NginxParser(BaseConfigParser):
    def parse(self, content: str) -> Dict[str, Any]:
        upstreams = re.findall(r"upstream\s+(\w+)\s*\{", content)
        servers = re.findall(r"server_name\s+([^;]+);", content)
        locations = re.findall(r"location\s+([^\s\{]+)\s*\{", content)
        
        return {
            "upstreams": upstreams,
            "server_names": [s.strip() for s in servers],
            "locations": [l.strip() for l in locations],
        }
```

### **33. Implement impact analysis engine for configuration changes**

**Objective:** To automatically determine the potential consequences of a configuration change.

**Architecture:** An `ImpactAnalysisEngine` that takes a `ConfigurationSnapshot` (with its `parsed_data`) and compares it to the previous snapshot. It will use a rules-based system to determine the affected services, whether a restart is required, and a risk level.

```python
# apps/backend/src/services/impact_analysis.py

class ImpactAnalysisEngine:
    async def analyze(self, new_snapshot: ConfigurationSnapshot, old_snapshot: Optional[ConfigurationSnapshot]) -> Dict[str, Any]:
        """Analyze the impact of a configuration change."""
        
        if new_snapshot.config_type == "docker_compose":
            return self._analyze_compose_impact(new_snapshot, old_snapshot)
        elif new_snapshot.config_type == "proxy_configs":
            return self._analyze_proxy_impact(new_snapshot, old_snapshot)
        
        return {"risk_level": "LOW", "affected_services": [], "requires_restart": False}

    def _analyze_compose_impact(self, new, old) -> Dict[str, Any]:
        new_data = new.parsed_data or {}
        old_data = old.parsed_data or {} if old else {}
        
        new_services = set(new_data.get("services", []))
        old_services = set(old_data.get("services", []))
        
        if new_services != old_services:
            return {
                "risk_level": "HIGH",
                "summary": f"Services changed: added {list(new_services - old_services)}, removed {list(old_services - new_services)}",
                "affected_services": list(new_services.union(old_services)),
                "requires_restart": True,
            }
            
        # A more advanced check would look at image versions, ports, etc.
        return {"risk_level": "MEDIUM", "affected_services": list(new_services), "requires_restart": True}
        
    def _analyze_proxy_impact(self, new, old) -> Dict[str, Any]:
        # ... logic to compare upstreams, server names, etc. ...
        return {"risk_level": "HIGH", "affected_services": ["nginx"], "requires_restart": True}
```

### **34. Create service dependency mapping and analysis**

**Objective:** To understand the relationships between different services and configurations, enabling more accurate impact analysis.

**Architecture:** This requires a new database model, `ServiceDependency`, and a service to manage it. The dependency graph can be populated automatically (e.g., by parsing `docker-compose.yml` `depends_on` fields) and manually. The `ImpactAnalysisEngine` will query this graph.

```sql
-- New Table: service_dependencies
CREATE TABLE service_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    service_name VARCHAR(255) NOT NULL,
    depends_on VARCHAR(255) NOT NULL,
    dependency_type VARCHAR(50) NOT NULL, -- 'docker', 'network', 'config_file'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(device_id, service_name, depends_on)
);
```

```python
# apps/backend/src/services/dependency_service.py

class DependencyService:
    async def get_downstream_dependencies(self, session, device_id: UUID, service_name: str) -> List[str]:
        """Find all services that depend on the given service."""
        # ... recursive query on service_dependencies table ...
        pass

    async def build_dependencies_from_compose(self, device_id: UUID, parsed_compose: Dict):
        """Parse a docker-compose file and create dependency records."""
        # ... logic to iterate through services and find 'depends_on' keys ...
        pass
```

### **35. Implement configuration validation and syntax checking**

**Objective:** To prevent broken configurations from being deployed or recorded.

**Architecture:** Before saving a `ConfigurationSnapshot`, the `UnifiedDataCollectionService` will invoke a validation step. This will use external tools (`nginx -t`, `docker-compose config`) via SSH to check syntax. The validation result (success/failure + output) will be stored with the snapshot.

```python
# apps/backend/src/services/configuration_service.py (Enhancements)

class ConfigurationService:
    # ...
    
    async def validate_configuration(self, ssh_manager: SSHCommandManager, device_id: UUID, config_type: str, content: str) -> Dict[str, Any]:
        """Validate configuration content using remote tools."""
        
        # Write content to a temporary file on the remote device
        temp_path = f"/tmp/infrastructor_validation_{uuid.uuid4()}"
        await ssh_manager.write_file(device_id, temp_path, content)
        
        validation_command = ""
        if config_type == "proxy_configs":
            validation_command = f"nginx -t -c {temp_path}"
        elif config_type == "docker_compose":
            validation_command = f"docker-compose -f {temp_path} config"
            
        if not validation_command:
            return {"valid": True, "output": "No validator for this config type."}
            
        result = await ssh_manager.execute_command(device_id, validation_command)
        
        # Cleanup temporary file
        await ssh_manager.execute_command(device_id, f"rm {temp_path}")
        
        return {
            "valid": result.success,
            "output": result.stdout if result.success else result.stderr
        }
```

### **36. Create configuration backup and restoration capabilities**

**Objective:** To ensure that any configuration change can be reverted by providing automated backups and a simple restoration mechanism.

**Architecture:** Since every version of a configuration is stored in the `ConfigurationSnapshot` table (as per the "self-hosted optimized" principle), this is primarily an API task.
1.  **Backup:** Is implicit. Every change creates a new, versioned snapshot.
2.  **Restoration:** Requires an API endpoint that takes a `snapshot_id` and writes the `raw_content` from that snapshot back to the original `file_path` on the remote device.

```python
# apps/backend/src/api/configuration.py (New Endpoint)

@router.post("/{snapshot_id}/restore", status_code=200)
async def restore_configuration_snapshot(
    snapshot_id: UUID,
    device_id: UUID = Query(...), # For authorization/validation
    config_service: ConfigurationService = Depends(get_config_service),
    ssh_manager: SSHCommandManager = Depends(get_ssh_manager)
):
    """
    Restores a configuration on a device from a specific snapshot.
    """
    snapshot = await config_service.get_snapshot_by_id(snapshot_id)
    if not snapshot or snapshot.device_id != device_id:
        raise HTTPException(status_code=404, detail="Snapshot not found or does not belong to this device.")

    try:
        await ssh_manager.write_file(
            device_id=snapshot.device_id,
            path=snapshot.file_path,
            content=snapshot.raw_content
        )
        
        # Optional: Trigger an immediate re-validation after restore
        validation_result = await config_service.validate_configuration(...)
        
        return {
            "message": "Configuration restored successfully.",
            "file_path": snapshot.file_path,
            "restored_hash": snapshot.content_hash,
            "validation_after_restore": validation_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore configuration: {e}")

```

### **37. Implement configuration drift detection and reconciliation**

**Objective:** To detect and correct discrepancies between the intended state (in the database) and the actual state on the device.

**Architecture:** This is a periodic task managed by the `ConfigurationMonitoringService`. It will:
1.  For each tracked file, run a `stat` command via SSH to get the current modification time and hash.
2.  Compare this with the latest `ConfigurationSnapshot` in the database.
3.  If they don't match, a "drift" is detected.
4.  A drift event is emitted, and reconciliation can be triggered manually or automatically (e.g., by restoring the last known good configuration).

```python
# apps/backend/src/services/configuration_monitoring.py (Enhancement)

class ConfigurationMonitoringService:
    # ...
    
    async def _periodic_verification(self, device: Device):
        """Periodically verify configuration for drift."""
        while True:
            # Run every 30 minutes
            await asyncio.sleep(1800) 
            logger.info("Running periodic drift detection", device_id=device.id)
            
            async with self.db_session_factory() as session:
                tracked_files = await configuration_service.get_all_tracked_files_for_device(session, device.id)
                
                for file_path, latest_hash in tracked_files.items():
                    try:
                        # Get live hash from device
                        live_content = await self.unified_service.ssh_connection_manager.read_file(device.id, file_path)
                        live_hash = hashlib.sha256(live_content.encode('utf-8')).hexdigest()
                        
                        if live_hash != latest_hash:
                            logger.warning("Configuration drift detected!", device_id=device.id, file_path=file_path)
                            await self.event_bus.emit("configuration.drift.detected", {
                                "device_id": device.id,
                                "file_path": file_path,
                                "expected_hash": latest_hash,
                                "actual_hash": live_hash
                            })
                            # Trigger reconciliation logic here
                            
                    except Exception as e:
                        logger.error("Drift check failed for file", file_path=file_path, error=e)
```

### **38. Create configuration sync status tracking and error handling**

**Objective:** To provide clear, auditable status information for every configuration file.

**Architecture:** The `ConfigurationSnapshot` model needs to be extended with status fields (`sync_status`, `validation_status`, `last_error`). The `UnifiedDataCollectionService` will be responsible for updating these fields throughout the collection, validation, and storage process.

```python
# apps/backend/src/models/configuration.py (Enhancements)

class ConfigurationSnapshot(Base):
    # ... (existing columns) ...
    
    # Sync and Validation Status
    sync_status = Column(String(50), default="synced", nullable=False) # e.g., synced, out-of-sync, unknown
    validation_status = Column(String(50), default="pending", nullable=False) # e.g., pending, valid, invalid
    last_validation_output = Column(Text)
    last_sync_error = Column(Text)
```

### **39. Implement configuration rollback planning and execution**

**Objective:** To allow safe, multi-file rollbacks for complex changes.

**Architecture:** This is more than just restoring a single file. A rollback plan involves:
1.  Identifying a "change set" of related configuration snapshots (e.g., all changes that occurred within a 5-minute window).
2.  Creating a `RollbackPlan` object that lists the snapshots to be reverted.
3.  An API endpoint to execute the plan, which restores each file in the set. The system must handle failures gracefully (e.g., if one file fails to restore, should it continue or stop?).

```python
# apps/backend/src/services/rollback_service.py

class RollbackService:
    async def create_rollback_plan(self, session, device_id: UUID, target_time: datetime) -> Dict:
        """Create a plan to roll back all changes after a certain time."""
        
        # Find all snapshots created after the target time
        snapshots_to_revert = await configuration_service.get_snapshots_after(session, device_id, target_time)
        
        plan = {"steps": []}
        for snapshot in snapshots_to_revert:
            # Find the version to restore TO (the one right before this change)
            previous_snapshot = await configuration_service.get_snapshot_by_hash(session, device_id, snapshot.file_path, snapshot.previous_hash)
            if previous_snapshot:
                plan["steps"].append({
                    "file_path": snapshot.file_path,
                    "from_snapshot_id": snapshot.id,
                    "to_snapshot_id": previous_snapshot.id,
                })
        return plan

    async def execute_rollback_plan(self, plan: Dict):
        """Execute the steps in a rollback plan."""
        # ... logic to iterate through steps and call restore_configuration_snapshot ...
        pass
```

### **40. Create configuration change approval workflow system**

**Objective:** To introduce a manual approval gate for high-risk configuration changes.

**Architecture:** This requires significant new models (`ChangeRequest`, `Approval`) and API endpoints.
1.  A user proposes a change via an API endpoint. This creates a `ChangeRequest` in a `pending` state.
2.  The `ImpactAnalysisEngine` runs on the proposed change.
3.  Designated approvers are notified.
4.  Approvers use an API endpoint to approve or reject the `ChangeRequest`.
5.  If approved, the system automatically applies the configuration change.

This is a large feature and would likely be a major component of a subsequent phase, but the foundation is laid here.

### **41. Implement configuration template management and validation**

**Objective:** To allow users to create and manage reusable, parameterized configuration templates (e.g., for new Nginx sites).

**Architecture:**
1.  New `ConfigurationTemplate` model to store templates (using a templating engine like Jinja2).
2.  API endpoints for CRUD operations on templates.
3.  An endpoint to "render" a template with user-provided variables, which then gets applied as a new configuration.
4.  Validation can be performed on the template itself to ensure it produces valid syntax.

```python
# apps/backend/src/models/configuration.py (New Model)

class ConfigurationTemplate(Base):
    __tablename__ = "configuration_templates"
    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String, nullable=False, unique=True)
    config_type = Column(String, nullable=False) # e.g., 'nginx_site', 'docker_service'
    template_content = Column(Text, nullable=False) # Jinja2 template
    variables = Column(JSON, nullable=False) # List of required variable names
```

## **Advanced Configuration Features**

This section details features that build upon the core monitoring system to provide enhanced security, management, and operational capabilities.

### **42. Create configuration change alerting with risk assessment**

**Objective:** To notify administrators of configuration changes, with alert priority determined by the assessed risk.

**Architecture:** The `NotificationService` will subscribe to events from the `ImpactAnalysisEngine`. When a change event with a risk assessment is received, it will:
1.  Check the `risk_level` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
2.  Consult an alerting policy to determine the notification channel (e.g., email for `LOW`, webhook/Slack for `MEDIUM`, PagerDuty for `CRITICAL`).
3.  Format and send the alert.

```python
# apps/backend/src/services/notification_service.py (Enhancement)

class NotificationService:
    # ...
    
    async def handle_config_change_alert(self, change_event: Dict):
        """Handle a configuration change event and send alerts based on risk."""
        risk_level = change_event.get("risk_level", "LOW")
        
        alert_policy = {
            "LOW": [],
            "MEDIUM": ["email", "webhook"],
            "HIGH": ["email", "webhook", "slack"],
            "CRITICAL": ["email", "webhook", "slack", "pagerduty"]
        }
        
        channels_to_notify = alert_policy.get(risk_level, [])
        
        for channel in channels_to_notify:
            await self.send(channel, "Configuration Change Detected", change_event)
```

### **43. Implement configuration change batching and transaction management**

**Objective:** To apply a set of related configuration changes as a single atomic operation.

**Architecture:** This is a complex feature that requires a "two-phase commit" like pattern.
1.  **Phase 1: Prepare.** A user submits a "batch" of changes. The system validates each change and writes them to temporary files on the target device(s). It confirms all temporary files are in place.
2.  **Phase 2: Commit.** The user triggers the commit. The system executes a script on the remote device to move all temporary files to their final destinations in a single, quick operation.
3.  **Rollback:** If any step in the commit phase fails, the system reverts all changes.

### **44. Create configuration history and timeline visualization data**

**Objective:** To provide a user-friendly way to view the history of a configuration file.

**Architecture:** This is primarily a frontend task powered by a new API endpoint. The endpoint will query the `ConfigurationSnapshot` table for a specific `file_path` on a `device_id`, ordered by time. It will return a list of snapshots, including timestamps, change types, and who/what triggered the change. A "diff" view can be generated by comparing the `raw_content` of two consecutive snapshots.

### **45. Implement configuration compliance checking and reporting**

**Objective:** To automatically check configurations against a set of predefined rules or security policies.

**Architecture:**
1.  A new `ComplianceRule` model to store rules (e.g., "All SSH servers must disable password authentication"). Rules could be implemented using a simple engine or a dedicated policy language like Rego (from Open Policy Agent).
2.  A `ComplianceService` that runs periodically. It fetches all relevant configurations, evaluates them against the rule set, and stores the results in a `ComplianceReport` table.

### **46. Create configuration export and import capabilities**

**Objective:** To allow users to easily back up and migrate their infrastructure's configuration.

**Architecture:**
*   **Export:** An API endpoint that bundles all the latest `ConfigurationSnapshot` records for a given device (or all devices) into a single archive (e.g., a TAR file or a ZIP).
*   **Import:** A more complex API endpoint that accepts an exported archive. It would unpack the archive and systematically apply each configuration, creating new snapshots as it goes. This would need to be a carefully managed, potentially destructive operation.

### **47. Implement configuration encryption and secure storage**

**Objective:** To protect sensitive information (e.g., passwords, API keys) within stored configurations.

**Architecture:** This involves application-level encryption.
1.  The `UnifiedDataCollectionService` will use a library like `cryptography` to encrypt the `raw_content` and `parsed_data` fields before they are stored in the `ConfigurationSnapshot` table.
2.  The encryption key must be managed securely (e.g., via a key management service like HashiCorp Vault, or a key stored in the environment for simpler setups).
3.  Data will be decrypted on-the-fly when read via the API, based on user permissions. The raw encrypted data is never exposed.

### **48. Create configuration access control and permission management**

**Objective:** To control who can view, change, or restore configurations.

**Architecture:** This extends the application's existing user authentication/authorization system.
1.  Introduce new permission scopes (e.g., `config:view`, `config:edit`, `config:restore`, `config:approve`).
2.  Associate these permissions with user roles.
3.  Protect all configuration-related API endpoints with these permission checks. For example, viewing a config's content requires `config:view`, while restoring it requires `config:restore`.