"""
Event Bus System for Real-time Infrastructure Monitoring

Provides an async event bus for communication between services,
particularly connecting polling service data collection to WebSocket broadcasting.
"""

import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BaseEvent(BaseModel):
    """Base class for all events in the system"""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "infrastructor"
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class MetricCollectedEvent(BaseEvent):
    """Event emitted when system metrics are collected from a device"""

    event_type: str = "metric_collected"
    device_id: UUID
    hostname: str
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float
    uptime_seconds: int
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0


class DeviceStatusChangedEvent(BaseEvent):
    """Event emitted when a device status changes"""

    event_type: str = "device_status_changed"
    device_id: UUID
    hostname: str
    old_status: str
    new_status: str
    status_reason: str | None = None


class ContainerStatusEvent(BaseEvent):
    """Event emitted when container data is collected"""

    event_type: str = "container_status"
    device_id: UUID
    hostname: str
    container_id: str
    container_name: str
    image: str
    status: str
    cpu_usage_percent: float = 0.0
    memory_usage_bytes: int = 0
    memory_limit_bytes: int = 0


class DriveHealthEvent(BaseEvent):
    """Event emitted when drive health data is collected"""

    event_type: str = "drive_health"
    device_id: UUID
    hostname: str
    drive_name: str
    health_status: str
    temperature_celsius: int | None = None
    model: str | None = None
    serial_number: str | None = None


class EventHandler:
    """Wrapper for event handler functions with metadata"""

    def __init__(
        self,
        handler: Callable[[BaseEvent], Awaitable[None]],
        event_types: list[str],
        priority: int = 0,
    ):
        self.handler = handler
        self.event_types = set(event_types)
        self.priority = priority
        self.handler_id = str(uuid4())

    async def handle(self, event: BaseEvent) -> None:
        """Execute the handler function"""
        try:
            await self.handler(event)
        except Exception as e:
            logger.error(f"Event handler {self.handler_id} failed: {e}", exc_info=True)

    def matches_event(self, event: BaseEvent) -> bool:
        """Check if this handler should process the given event"""
        return event.event_type in self.event_types


class EventBus:
    """
    Async event bus for inter-service communication

    Features:
    - Non-blocking event emission
    - Topic-based event routing
    - Priority-based handler execution
    - Bounded queue to prevent memory issues
    - Graceful error handling
    """

    def __init__(self, max_queue_size: int = 1000):
        self._handlers: dict[str, list[EventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._processor_task: asyncio.Task | None = None
        self._running = False
        self._handler_tasks: set[asyncio.Task] = set()
        self._stats = {
            "events_processed": 0,
            "events_failed": 0,
            "events_dropped": 0,
            "handlers_count": 0,
            "active_handler_tasks": 0,
        }

    async def start(self) -> None:
        """Start the event processing loop"""
        if self._running:
            logger.warning("Event bus is already running")
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop the event processing loop gracefully"""
        if not self._running:
            return

        self._running = False

        if self._processor_task:
            self._processor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._processor_task

        # Process remaining events
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                await self._process_single_event(event)
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Error processing remaining event: {e}")

        # Cancel and cleanup remaining handler tasks
        await self._cleanup_handler_tasks()

        logger.info("Event bus stopped")

    def subscribe(
        self,
        event_types: str | list[str],
        handler: Callable[[BaseEvent], Awaitable[None]],
        priority: int = 0,
    ) -> str:
        """
        Subscribe to events

        Args:
            event_types: Event type(s) to listen for
            handler: Async function to handle events
            priority: Handler priority (higher = executed first)

        Returns:
            Handler ID for unsubscribing
        """
        if isinstance(event_types, str):
            event_types = [event_types]

        event_handler = EventHandler(handler, event_types, priority)

        for event_type in event_types:
            if event_type not in self._handlers:
                self._handlers[event_type] = []

            self._handlers[event_type].append(event_handler)
            # Sort by priority (highest first)
            self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)

        self._stats["handlers_count"] = sum(len(handlers) for handlers in self._handlers.values())
        logger.debug(f"Handler {event_handler.handler_id} subscribed to {event_types}")

        return event_handler.handler_id

    def unsubscribe(self, handler_id: str) -> bool:
        """
        Unsubscribe a handler

        Args:
            handler_id: ID returned from subscribe()

        Returns:
            True if handler was found and removed
        """
        removed = False

        for event_type, handlers in self._handlers.items():
            self._handlers[event_type] = [h for h in handlers if h.handler_id != handler_id]
            if len(handlers) != len(self._handlers[event_type]):
                removed = True

        # Clean up empty event types
        self._handlers = {
            event_type: handlers for event_type, handlers in self._handlers.items() if handlers
        }

        self._stats["handlers_count"] = sum(len(handlers) for handlers in self._handlers.values())

        if removed:
            logger.debug(f"Handler {handler_id} unsubscribed")

        return removed

    def emit_nowait(self, event: BaseEvent) -> bool:
        """
        Emit an event without blocking

        Args:
            event: Event to emit

        Returns:
            True if event was queued, False if queue is full
        """
        try:
            self._event_queue.put_nowait(event)
            logger.debug(f"Event {event.event_type} queued: {event.event_id}")
            return True
        except asyncio.QueueFull:
            self._stats["events_dropped"] += 1
            logger.warning(f"Event queue full, dropping event: {event.event_type}")
            return False

    async def emit(self, event: BaseEvent, timeout: float | None = None) -> bool:
        """
        Emit an event with optional timeout

        Args:
            event: Event to emit
            timeout: Maximum time to wait for queue space

        Returns:
            True if event was queued
        """
        try:
            await asyncio.wait_for(self._event_queue.put(event), timeout=timeout)
            logger.debug(f"Event {event.event_type} queued: {event.event_id}")
            return True
        except asyncio.TimeoutError:
            self._stats["events_dropped"] += 1
            logger.warning(f"Event queue timeout, dropping event: {event.event_type}")
            return False

    async def _process_events(self) -> None:
        """Main event processing loop"""
        logger.info("Event processing loop started")

        try:
            while self._running:
                try:
                    # Wait for events with timeout to allow graceful shutdown
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                    await self._process_single_event(event)

                except asyncio.TimeoutError:
                    # Normal timeout for shutdown checking
                    continue
                except Exception as e:
                    logger.error(f"Error in event processing loop: {e}", exc_info=True)
                    await asyncio.sleep(0.1)  # Brief pause on error

        except asyncio.CancelledError:
            logger.info("Event processing loop cancelled")
            raise
        finally:
            logger.info("Event processing loop stopped")

    async def _process_single_event(self, event: BaseEvent) -> None:
        """Process a single event by calling all matching handlers"""
        handlers = self._handlers.get(event.event_type, [])

        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type}")
            return

        logger.debug(f"Processing event {event.event_type} with {len(handlers)} handlers")

        # Execute handlers concurrently but don't wait for completion
        handler_tasks = []
        for handler in handlers:
            task = asyncio.create_task(handler.handle(event))
            # Add cleanup callback to remove task from tracking when done
            task.add_done_callback(self._remove_handler_task)
            handler_tasks.append(task)

        # Track handler tasks for lifecycle management
        self._handler_tasks.update(handler_tasks)
        self._stats["active_handler_tasks"] = len(self._handler_tasks)

        # Fire and forget - don't wait for completion to avoid blocking
        # Log any immediate failures but don't propagate them
        try:
            # Give handlers a brief moment to start
            await asyncio.sleep(0)
            self._stats["events_processed"] += 1
        except Exception as e:
            self._stats["events_failed"] += 1
            logger.error(f"Error starting event handlers: {e}")

    def _remove_handler_task(self, task: asyncio.Task) -> None:
        """Remove completed handler task from tracking set"""
        self._handler_tasks.discard(task)
        self._stats["active_handler_tasks"] = len(self._handler_tasks)

    async def _cleanup_handler_tasks(self) -> None:
        """Cancel and cleanup all remaining handler tasks"""
        if not self._handler_tasks:
            return

        logger.info(f"Cancelling {len(self._handler_tasks)} remaining handler tasks")

        # Cancel all remaining tasks
        for task in self._handler_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete cancellation with timeout
        if self._handler_tasks:
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(
                    asyncio.gather(*self._handler_tasks, return_exceptions=True), timeout=5.0
                )

        # Clear the task set
        self._handler_tasks.clear()
        self._stats["active_handler_tasks"] = 0
        logger.info("Handler task cleanup completed")

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics"""
        return {
            **self._stats,
            "queue_size": self._event_queue.qsize(),
            "max_queue_size": self._event_queue.maxsize,
            "is_running": self._running,
            "event_types": list(self._handlers.keys()),
        }

    def is_running(self) -> bool:
        """Check if the event bus is currently running"""
        return self._running


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def initialize_event_bus() -> EventBus:
    """Initialize and start the global event bus"""
    event_bus = get_event_bus()
    if not event_bus.is_running():
        await event_bus.start()
    return event_bus


async def shutdown_event_bus() -> None:
    """Shutdown the global event bus"""
    global _event_bus
    if _event_bus and _event_bus.is_running():
        await _event_bus.stop()


# Export the global event bus instance for direct access
event_bus = get_event_bus()
