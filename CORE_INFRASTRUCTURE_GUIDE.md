# Core Infrastructure Foundation - Implementation Guide

This document provides a detailed, step-by-step guide for implementing the core infrastructure foundation of the new unified architecture. It expands on the tasks outlined in the "Core Infrastructure Foundation" phase and is based on the principles and patterns defined in `enhancements.md`.

## 1. Task 23: Create `UnifiedDataCollectionService` Class Architecture

The `UnifiedDataCollectionService` is the central component of the new architecture. It will be located in `apps/backend/src/services/unified_data_collection.py`.

**1.1. Class Definition and Initialization:**

```python
# apps/backend/src/services/unified_data_collection.py

from typing import Any, Callable, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timezone
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.events import EventBus, get_event_bus
from .cache_manager import CacheManager
from .command_registry import CommandRegistry, CommandDefinition
from ..utils.ssh_client import SSHClient
from ..models.audit import DataCollectionAudit
from ..schemas.device import Device

class UnifiedDataCollectionService:
    """
    Central service for all data collection operations across the infrastructure.
    Consolidates polling, API, and MCP data collection into a single, consistent interface.
    """

    def __init__(
        self,
        db_session_factory: Callable[[], AsyncSession],
        command_registry: CommandRegistry,
        cache_manager: CacheManager,
        event_bus: EventBus,
    ):
        self.db_session_factory = db_session_factory
        self.command_registry = command_registry
        self.cache_manager = cache_manager
        self.event_bus = event_bus
        self.ssh_client = SSHClient()  # Simplified SSH client

        # Data type freshness thresholds (in seconds)
        self.freshness_thresholds = {
            "containers": 30,
            "system_metrics": 300,
            "drive_health": 3600,
            "network": 120,
            "zfs": 600,
            "proxy_configs": 0,
            "docker_compose": 0,
            "systemd_services": 600,
        }

    # ... methods will be added in subsequent tasks ...
```

**1.2. Core `collect_and_store_data` Method:**

This method will be the primary entry point for all data collection.

```python
# Add to UnifiedDataCollectionService class

async def collect_and_store_data(
    self,
    device: Device,
    command_name: str,
    force_refresh: bool = False,
    collection_source: str = "unknown",
    **kwargs,
) -> Any:
    """
    Universal data collection method that handles caching, collection, and storage.
    """
    command_def = self.command_registry.get_command(command_name)
    if not command_def:
        raise ValueError(f"Command '{command_name}' not found in registry.")

    command_hash = self._generate_command_hash(device, command_def, **kwargs)

    # 1. Check cache first
    if not force_refresh:
        cached_data = await self.cache_manager.get_cached_data(
            device.id, command_name, command_hash, max_age_seconds=command_def.cache_ttl
        )
        if cached_data:
            # Although cached, we still create an audit log for the request
            await self._create_audit_log(
                device_id=device.id,
                command_def=command_def,
                status="cached",
                collection_source=collection_source,
                cache_hit=True,
            )
            return cached_data

    # 2. Collect fresh data
    start_time = datetime.now(timezone.utc)
    try:
        # 2a. Get SSH connection
        async with self.ssh_client.get_connection(device.hostname) as conn:
            # 2b. Execute command
            command_str = command_def.command_template.format(**kwargs)
            result = await conn.run(command_str, timeout=command_def.timeout)

        # 2c. Parse result
        parsed_data = command_def.parser(result.stdout)

        # 3. Store in database
        await self._store_in_database(device.id, command_name, parsed_data)

        # 4. Cache for future requests
        await self.cache_manager.store_data(
            device.id, command_name, command_hash, parsed_data, command_def.cache_ttl
        )

        # 5. Emit real-time event
        await self.event_bus.emit(f"{command_name}.updated", device_id=device.id, data=parsed_data)

        # 6. Create audit log
        await self._create_audit_log(
            device_id=device.id,
            command_def=command_def,
            status="success",
            duration_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
            collection_source=collection_source,
        )

        return parsed_data

    except Exception as e:
        await self._create_audit_log(
            device_id=device.id,
            command_def=command_def,
            status="error",
            error_message=str(e),
            duration_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000,
            collection_source=collection_source,
        )
        raise

async def _create_audit_log(self, **kwargs):
    async with self.db_session_factory() as session:
        audit_log = DataCollectionAudit(**kwargs)
        session.add(audit_log)
        await session.commit()

def _generate_command_hash(self, device: Device, command_def: CommandDefinition, **kwargs) -> str:
    # ... implementation to create a unique hash for the command + args ...
    return hashlib.sha256(f"{device.id}{command_def.name}{kwargs}".encode()).hexdigest()

async def _store_in_database(self, device_id: UUID, command_name: str, data: Any):
    # ... implementation to store data in the appropriate model based on command_name ...
    pass
```

---

## 2. Task 24: Create `CacheManager` with LRU Eviction

This service will be located in `apps/backend/src/services/cache_manager.py`.

```python
# apps/backend/src/services/cache_manager.py

from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

@dataclass
class CacheEntry:
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
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age < self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds()

class CacheManager:
    """Advanced cache management with LRU eviction and metrics"""

    def __init__(self, max_entries: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_entries = max_entries
        self.metrics = {"hits": 0, "misses": 0, "evictions": 0, "total_requests": 0}

    async def get_cached_data(
        self,
        device_id: UUID,
        data_type: str,
        command_hash: str,
        max_age_seconds: Optional[int] = None,
    ) -> Optional[Any]:
        cache_key = f"{device_id}:{data_type}:{command_hash}"
        self.metrics["total_requests"] += 1

        if cache_key in self.cache:
            entry = self.cache[cache_key]
            effective_max_age = max_age_seconds if max_age_seconds is not None else entry.ttl_seconds

            if entry.age_seconds < effective_max_age:
                entry.access_count += 1
                entry.last_accessed = datetime.now(timezone.utc)
                self.metrics["hits"] += 1
                logger.debug("Cache HIT", key=cache_key)
                return entry.data
            else:
                del self.cache[cache_key]
                logger.debug("Cache EXPIRED", key=cache_key)
        
        self.metrics["misses"] += 1
        return None

    async def store_data(
        self,
        device_id: UUID,
        data_type: str,
        command_hash: str,
        data: Any,
        ttl_seconds: int,
    ) -> None:
        cache_key = f"{device_id}:{data_type}:{command_hash}"

        if len(self.cache) >= self.max_entries:
            await self._evict_lru_entries(count=int(self.max_entries * 0.1))

        entry = CacheEntry(
            data=data,
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            data_type=data_type,
            command_hash=command_hash,
            ttl_seconds=ttl_seconds,
        )
        self.cache[cache_key] = entry
        logger.debug("Cache STORED", key=cache_key)

    async def _evict_lru_entries(self, count: int):
        if not self.cache:
            return
        
        sorted_entries = sorted(self.cache.items(), key=lambda item: item[1].last_accessed)
        
        for i in range(min(count, len(sorted_entries))):
            key, _ = sorted_entries[i]
            del self.cache[key]
            self.metrics["evictions"] += 1
            logger.debug("Cache EVICTED", key=key)
```

---

## 3. Task 25: Create `CommandRegistry`

This service will be located in `apps/backend/src/services/command_registry.py`.

```python
# apps/backend/src/services/command_registry.py

from dataclasses import dataclass
from typing import Callable, List, Dict
from enum import Enum

# Import all parsers
from .parsers import *

class CommandCategory(Enum):
    SYSTEM_METRICS = "system_metrics"
    CONTAINER_MANAGEMENT = "container_management"
    FILE_OPERATIONS = "file_operations"
    # ... other categories

@dataclass
class CommandDefinition:
    name: str
    command_template: str
    category: CommandCategory
    parser: Callable
    timeout: int = 15
    cache_ttl: int = 300
    retry_count: int = 3

class CommandRegistry:
    """Registry of all SSH commands used across the system"""

    def __init__(self):
        self._commands = {cmd.name: cmd for cmd in self._get_all_commands()}

    def get_command(self, name: str) -> CommandDefinition:
        return self._commands.get(name)

    def _get_all_commands(self) -> List[CommandDefinition]:
        return [
            CommandDefinition(
                name="system_metrics",
                command_template="cat /proc/stat && cat /proc/meminfo",
                category=CommandCategory.SYSTEM_METRICS,
                parser=SystemMetricsParser().parse,
            ),
            CommandDefinition(
                name="list_containers",
                command_template="docker ps -a --format '{{json .}}'",
                category=CommandCategory.CONTAINER_MANAGEMENT,
                parser=ContainerListParser().parse,
                cache_ttl=30,
            ),
            # ... all other commands from enhancements.md
        ]
```

---

## 4. Task 26: Create SSH Connection Pool

This will be a rewrite of `apps/backend/src/utils/ssh_client.py`.

```python
# apps/backend/src/utils/ssh_client.py

import asyncio
from asyncssh import connect, SSHClientConnection
from typing import Dict

class SSHClient:
    """Manages a pool of SSH connections to multiple hosts."""

    def __init__(self, max_connections_per_host: int = 2):
        self._pools: Dict[str, asyncio.Queue[SSHClientConnection]] = {}
        self._max_connections = max_connections_per_host

    async def get_connection(self, hostname: str, **kwargs) -> SSHClientConnection:
        if hostname not in self._pools:
            self._pools[hostname] = asyncio.Queue(maxsize=self._max_connections)

        queue = self._pools[hostname]
        
        try:
            return queue.get_nowait()
        except asyncio.QueueEmpty:
            # If no connections are available and pool is not full, create a new one
            if queue.qsize() < self._max_connections:
                return await connect(hostname, **kwargs)
            # If pool is full, wait for a connection to be released
            return await queue.get()

    async def release_connection(self, hostname: str, conn: SSHClientConnection):
        if hostname in self._pools:
            await self._pools[hostname].put(conn)

    # ... Add health monitoring and cleanup tasks ...
```

---

## 5. Task 27: Implement Structured Logging

This involves configuring `structlog` in `apps/backend/src/main.py` and creating a correlation ID middleware.

```python
# apps/backend/src/main.py

import structlog
from fastapi import FastAPI, Request
from contextvars import ContextVar
import uuid

# ... other imports

correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default=None)

app = FastAPI()

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        # ... other context
    )
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

# ... rest of main.py, including structlog configuration ...
```

---

## 6. Task 28: Create Configuration Parser Framework

This involves creating a base parser and specific implementations in `apps/backend/src/services/parsers/`.

```python
# apps/backend/src/services/parsers/base_parser.py

from abc import ABC, abstractmethod
from typing import Any

class BaseParser(ABC):
    @abstractmethod
    def parse(self, data: str) -> Any:
        """Parses raw string data into a structured format."""
        pass

# apps/backend/src/services/parsers/docker_compose_parser.py

import yaml
from .base_parser import BaseParser

class DockerComposeParser(BaseParser):
    def parse(self, data: str) -> Dict[str, Any]:
        try:
            return yaml.safe_load(data)
        except yaml.YAMLError as e:
            # Handle parsing errors
            raise ValueError(f"Failed to parse Docker Compose file: {e}")

# ... other parsers for nginx, systemd, etc.
```

---

## 7. Task 29: Setup Event Bus Architecture

This will be implemented in `apps/backend/src/core/events.py`.

```python
# apps/backend/src/core/events.py

import asyncio
from typing import Callable, Dict, List, Any

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def emit(self, event_type: str, *args, **kwargs):
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                await callback(*args, **kwargs)

_event_bus_instance = EventBus()

def get_event_bus() -> EventBus:
    return _event_bus_instance
```

---

## 8. Task 30: Create Base Error Handling System

This will be implemented in `apps/backend/src/core/exceptions.py`.

```python
# apps/backend/src/core/exceptions.py

class InfrastructorException(Exception):
    """Base exception for the application."""
    pass

class SSHCommandError(InfrastructorException):
    """Raised when an SSH command fails."""
    def __init__(self, command: str, exit_code: int, stderr: str):
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(f"Command '{command}' failed with exit code {exit_code}: {stderr}")

class DataParsingError(InfrastructorException):
    """Raised when data parsing fails."""
    pass

# ... other custom exceptions ...