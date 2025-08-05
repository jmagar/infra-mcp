"""
File Change Event Correlation Service

Correlates raw file change events into meaningful, high-level infrastructure events.
Reduces noise from bulk operations like git pull that generate hundreds of events.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from ..core.events import event_bus
from ..schemas.configuration import FileChangeEvent
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FileEventCorrelator:
    """
    Correlates raw file change events into meaningful, high-level infrastructure events.

    Features:
    - Groups related file changes within a time window
    - Identifies bulk operations like git pull or config deployments
    - Reduces event noise by correlating related changes
    - Emits high-level infrastructure events via event bus
    """

    def __init__(
        self,
        correlation_window_sec: float | None = None,
    ):
        self.event_bus = event_bus
        self.pending_events: dict[UUID, list[FileChangeEvent]] = defaultdict(list)
        self.correlation_window_sec = correlation_window_sec or getattr(
            settings, "FILE_EVENT_CORRELATION_WINDOW_SEC", 5.0
        )

        # Scheduling tasks for correlation by device
        self._correlation_tasks: dict[UUID, asyncio.Task] = {}

        # Service state
        self._running = False

        logger.info(
            f"FileEventCorrelator initialized - correlation_window: {self.correlation_window_sec}s"
        )

    async def start(self) -> None:
        """Start the file event correlator service"""
        if self._running:
            return

        self._running = True
        logger.info("FileEventCorrelator started successfully")

    async def stop(self) -> None:
        """Stop the file event correlator service"""
        self._running = False

        # Cancel all pending correlation tasks
        for task in list(self._correlation_tasks.values()):
            task.cancel()

        # Wait for tasks to complete
        if self._correlation_tasks:
            await asyncio.gather(*self._correlation_tasks.values(), return_exceptions=True)

        self._correlation_tasks.clear()
        self.pending_events.clear()

        logger.info("FileEventCorrelator stopped successfully")

    async def process_event(self, event: FileChangeEvent) -> None:
        """Process a single file change event."""
        if not self._running:
            return

        device_id = event.device_id
        self.pending_events[device_id].append(event)

        logger.debug(
            f"Added event to correlation queue: {device_id}:{event.path} "
            f"({len(self.pending_events[device_id])} pending)"
        )

        # Schedule correlation if not already scheduled for this device
        if device_id not in self._correlation_tasks:
            self._correlation_tasks[device_id] = asyncio.create_task(
                self._schedule_correlation(device_id)
            )

    async def _schedule_correlation(self, device_id: UUID) -> None:
        """Wait for the correlation window to pass, then process events."""
        try:
            await asyncio.sleep(self.correlation_window_sec)

            events_to_process = self.pending_events.pop(device_id, [])
            if not events_to_process:
                return

            logger.debug(
                f"Processing {len(events_to_process)} events for correlation on device {device_id}"
            )

            await self._correlate_and_dispatch(device_id, events_to_process)

        except asyncio.CancelledError:
            # Clean up pending events for this device
            self.pending_events.pop(device_id, [])
            raise
        finally:
            # Remove completed task
            self._correlation_tasks.pop(device_id, None)

    async def _correlate_and_dispatch(self, device_id: UUID, events: list[FileChangeEvent]) -> None:
        """Analyze a batch of events and dispatch correlated events."""
        try:
            remaining_events = list(events)

            # Correlation 1: Proxy configuration bulk updates
            proxy_events = await self._correlate_proxy_config_events(device_id, remaining_events)
            remaining_events = [e for e in remaining_events if e not in proxy_events]

            # Correlation 2: Docker Compose service updates
            compose_events = await self._correlate_docker_compose_events(
                device_id, remaining_events
            )
            remaining_events = [e for e in remaining_events if e not in compose_events]

            # Correlation 3: Systemd service configuration updates
            systemd_events = await self._correlate_systemd_events(device_id, remaining_events)
            remaining_events = [e for e in remaining_events if e not in systemd_events]

            # Correlation 4: Git repository updates
            git_events = await self._correlate_git_events(device_id, remaining_events)
            remaining_events = [e for e in remaining_events if e not in git_events]

            # Correlation 5: Application configuration directories
            app_config_events = await self._correlate_app_config_events(device_id, remaining_events)
            remaining_events = [e for e in remaining_events if e not in app_config_events]

            # Process remaining individual events
            for event in remaining_events:
                await self._dispatch_individual_event(event)

        except Exception as e:
            logger.error(f"Error correlating events for device {device_id}: {e}")

    async def _correlate_proxy_config_events(
        self, device_id: UUID, events: list[FileChangeEvent]
    ) -> list[FileChangeEvent]:
        """Correlate multiple proxy configuration changes into one bulk update event."""
        proxy_conf_paths = [
            "/config/nginx/proxy-confs/",
            "/config/nginx/site-confs/",
            "/etc/nginx/sites-enabled/",
            "/etc/nginx/sites-available/",
            "/etc/nginx/conf.d/",
        ]

        proxy_events = [e for e in events if any(e.path.startswith(p) for p in proxy_conf_paths)]

        if len(proxy_events) > 1:
            correlated_event = {
                "event_type": "ProxyConfigBulkUpdate",
                "device_id": str(device_id),
                "change_count": len(proxy_events),
                "files_changed": list(set(e.path for e in proxy_events)),
                "event_types": list(
                    set(event_type for e in proxy_events for event_type in e.event_types)
                ),
                "start_time": min(e.timestamp for e in proxy_events).isoformat(),
                "end_time": max(e.timestamp for e in proxy_events).isoformat(),
                "correlation_window_sec": self.correlation_window_sec,
            }

            await self.event_bus.emit("configuration.proxy.bulk_update", correlated_event)

            logger.info(
                f"Correlated {len(proxy_events)} proxy config events into bulk update "
                f"for device {device_id}"
            )

            return proxy_events

        return []

    async def _correlate_docker_compose_events(
        self, device_id: UUID, events: list[FileChangeEvent]
    ) -> list[FileChangeEvent]:
        """Correlate Docker Compose file changes."""
        compose_patterns = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
        ]

        compose_events = [
            e for e in events if any(pattern in e.path for pattern in compose_patterns)
        ]

        if len(compose_events) > 1:
            correlated_event = {
                "event_type": "DockerComposeBulkUpdate",
                "device_id": str(device_id),
                "change_count": len(compose_events),
                "files_changed": list(set(e.path for e in compose_events)),
                "event_types": list(
                    set(event_type for e in compose_events for event_type in e.event_types)
                ),
                "start_time": min(e.timestamp for e in compose_events).isoformat(),
                "end_time": max(e.timestamp for e in compose_events).isoformat(),
                "correlation_window_sec": self.correlation_window_sec,
            }

            await self.event_bus.emit("configuration.docker_compose.bulk_update", correlated_event)

            logger.info(
                f"Correlated {len(compose_events)} Docker Compose events into bulk update "
                f"for device {device_id}"
            )

            return compose_events

        return []

    async def _correlate_systemd_events(
        self, device_id: UUID, events: list[FileChangeEvent]
    ) -> list[FileChangeEvent]:
        """Correlate systemd service configuration changes."""
        systemd_paths = [
            "/etc/systemd/system/",
            "/lib/systemd/system/",
            "/usr/lib/systemd/system/",
        ]

        systemd_events = [
            e
            for e in events
            if any(e.path.startswith(p) for p in systemd_paths)
            and e.path.endswith((".service", ".timer", ".socket"))
        ]

        if len(systemd_events) > 1:
            correlated_event = {
                "event_type": "SystemdServiceBulkUpdate",
                "device_id": str(device_id),
                "change_count": len(systemd_events),
                "files_changed": list(set(e.path for e in systemd_events)),
                "event_types": list(
                    set(event_type for e in systemd_events for event_type in e.event_types)
                ),
                "start_time": min(e.timestamp for e in systemd_events).isoformat(),
                "end_time": max(e.timestamp for e in systemd_events).isoformat(),
                "correlation_window_sec": self.correlation_window_sec,
            }

            await self.event_bus.emit("configuration.systemd.bulk_update", correlated_event)

            logger.info(
                f"Correlated {len(systemd_events)} systemd service events into bulk update "
                f"for device {device_id}"
            )

            return systemd_events

        return []

    async def _correlate_git_events(
        self, device_id: UUID, events: list[FileChangeEvent]
    ) -> list[FileChangeEvent]:
        """Correlate git repository operations."""
        # Detect git operations by looking for .git directory changes or many file changes
        git_events = [e for e in events if "/.git/" in e.path or e.path.endswith("/.git")]

        # Also look for patterns that suggest git operations (many file changes in short time)
        if not git_events and len(events) >= 10:
            # Check if events are spread across multiple directories (suggests git pull/clone)
            directories = set()
            for event in events:
                directory = "/".join(event.path.split("/")[:-1])
                directories.add(directory)

            # If we have changes in 3+ directories with 10+ files, likely a git operation
            if len(directories) >= 3:
                git_events = events[: min(len(events), 50)]  # Limit to first 50 events

        if len(git_events) >= 3:  # Need at least 3 events to consider it a git operation
            correlated_event = {
                "event_type": "GitRepositoryUpdate",
                "device_id": str(device_id),
                "change_count": len(git_events),
                "files_changed": list(set(e.path for e in git_events))[:20],  # Limit paths shown
                "event_types": list(
                    set(
                        event_type
                        for e in git_events[:10]  # Sample first 10 events
                        for event_type in e.event_types
                    )
                ),
                "start_time": min(e.timestamp for e in git_events).isoformat(),
                "end_time": max(e.timestamp for e in git_events).isoformat(),
                "correlation_window_sec": self.correlation_window_sec,
            }

            await self.event_bus.emit("configuration.git.repository_update", correlated_event)

            logger.info(
                f"Correlated {len(git_events)} file events into git repository update "
                f"for device {device_id}"
            )

            return git_events

        return []

    async def _correlate_app_config_events(
        self, device_id: UUID, events: list[FileChangeEvent]
    ) -> list[FileChangeEvent]:
        """Correlate application configuration directory changes."""
        config_directories = [
            "/etc/",
            "/opt/",
            "/config/",
            "/app/config/",
            "/.env",
            "/settings/",
        ]

        # Group events by directory
        directory_events: dict[str, list[FileChangeEvent]] = defaultdict(list)

        for event in events:
            for config_dir in config_directories:
                if event.path.startswith(config_dir):
                    # Get the immediate subdirectory
                    path_parts = event.path[len(config_dir) :].split("/")
                    if path_parts:
                        subdir = f"{config_dir}{path_parts[0]}/"
                        directory_events[subdir].append(event)
                    break

        correlated_events = []

        # Correlate directories with 2+ changes
        for directory, dir_events in directory_events.items():
            if len(dir_events) >= 2:
                correlated_event = {
                    "event_type": "ApplicationConfigBulkUpdate",
                    "device_id": str(device_id),
                    "directory": directory,
                    "change_count": len(dir_events),
                    "files_changed": list(set(e.path for e in dir_events)),
                    "event_types": list(
                        set(event_type for e in dir_events for event_type in e.event_types)
                    ),
                    "start_time": min(e.timestamp for e in dir_events).isoformat(),
                    "end_time": max(e.timestamp for e in dir_events).isoformat(),
                    "correlation_window_sec": self.correlation_window_sec,
                }

                await self.event_bus.emit("configuration.application.bulk_update", correlated_event)

                logger.info(
                    f"Correlated {len(dir_events)} application config events in {directory} "
                    f"for device {device_id}"
                )

                correlated_events.extend(dir_events)

        return correlated_events

    async def _dispatch_individual_event(self, event: FileChangeEvent) -> None:
        """Dispatch an individual file change event."""
        event_data = {
            "device_id": str(event.device_id),
            "path": event.path,
            "event_types": event.event_types,
            "timestamp": event.timestamp.isoformat(),
        }

        await self.event_bus.emit("configuration.file.changed", event_data)

        logger.debug(f"Dispatched individual file event: {event.device_id}:{event.path}")

    def get_correlation_stats(self) -> dict[str, Any]:
        """Get current correlation statistics."""
        return {
            "running": self._running,
            "correlation_window_sec": self.correlation_window_sec,
            "devices_with_pending_events": len(self.pending_events),
            "total_pending_events": sum(len(events) for events in self.pending_events.values()),
            "active_correlation_tasks": len(self._correlation_tasks),
            "pending_events_by_device": {
                str(device_id): len(events) for device_id, events in self.pending_events.items()
            },
        }


# Global singleton instance
_file_event_correlator: FileEventCorrelator | None = None


async def get_file_event_correlator() -> FileEventCorrelator:
    """Get the global file event correlator instance."""
    global _file_event_correlator

    if _file_event_correlator is None:
        _file_event_correlator = FileEventCorrelator()
        await _file_event_correlator.start()

    return _file_event_correlator


async def shutdown_file_event_correlator() -> None:
    """Shutdown the global service instance."""
    global _file_event_correlator

    if _file_event_correlator is not None:
        await _file_event_correlator.stop()
        _file_event_correlator = None
