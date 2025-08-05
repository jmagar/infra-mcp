"""
Configuration Monitoring Service

Provides real-time monitoring of configuration files on remote devices
using a hybrid approach of file watching (inotify) and intelligent polling.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.backend.src.core.database import get_async_session
from apps.backend.src.core.exceptions import (
    SSHConnectionError,
    SSHCommandError,
    ValidationError,
    ConfigurationError,
    ServiceUnavailableError,
)
from apps.backend.src.models.device import Device
from apps.backend.src.models.configuration import ConfigurationSnapshot, ConfigurationChangeEvent
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.services.remote_file_watcher import (
    get_remote_file_watcher,
    WatchTarget,
    RemoteFileWatcher,
)
from apps.backend.src.services.event_correlation import get_file_event_correlator
from apps.backend.src.utils.ssh_client import get_ssh_client
from apps.backend.src.core.events import event_bus

logger = logging.getLogger(__name__)


class ConfigurationType(str, Enum):
    """Types of configuration files supported."""

    DOCKER_COMPOSE = "docker_compose"
    NGINX_CONFIG = "nginx_config"
    SYSTEMD_SERVICE = "systemd_service"
    ENV_FILE = "env_file"
    YAML_CONFIG = "yaml_config"
    JSON_CONFIG = "json_config"
    INI_CONFIG = "ini_config"
    GENERIC_TEXT = "generic_text"


class ChangeType(str, Enum):
    """Types of configuration changes."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    PERMISSIONS_CHANGED = "permissions_changed"
    MOVED = "moved"


@dataclass
class ConfigurationWatchTarget:
    """Configuration file or directory to monitor."""

    device_id: str
    path: str
    config_type: ConfigurationType
    description: str
    watch_subdirectories: bool = False
    file_patterns: list[str] = field(default_factory=list)
    ignore_patterns: list[str] = field(default_factory=list)
    check_interval_seconds: int = 300  # 5 minutes default
    change_threshold_bytes: int = 1024  # Minimum change size to trigger event
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigurationChange:
    """Details of a configuration change."""

    device_id: str
    file_path: str
    change_type: ChangeType
    config_type: ConfigurationType
    timestamp: datetime
    old_content_hash: str | None = None
    new_content_hash: str | None = None
    old_size_bytes: int | None = None
    new_size_bytes: int | None = None
    old_permissions: str | None = None
    new_permissions: str | None = None
    diff_summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ConfigurationMonitoringService:
    """
    Real-time configuration file monitoring service.

    Features:
    - inotify-based file watching on supported devices
    - Intelligent polling fallback for non-inotify systems
    - Content hash-based change detection
    - Configurable monitoring targets per device
    - Integration with UnifiedDataCollectionService
    - Real-time event emission for configuration changes
    """

    def __init__(
        self,
        default_check_interval: int = 300,  # 5 minutes
        max_file_size_bytes: int = 10 * 1024 * 1024,  # 10MB
        enable_inotify: bool = True,
        enable_polling: bool = True,
    ):
        self.default_check_interval = default_check_interval
        self.max_file_size_bytes = max_file_size_bytes
        self.enable_inotify = enable_inotify
        self.enable_polling = enable_polling

        # Watch targets by device
        self._watch_targets: dict[str, list[ConfigurationWatchTarget]] = {}

        # File state tracking (path -> (hash, size, mtime, permissions))
        self._file_states: dict[str, dict[str, tuple[str, int, float, str]]] = {}

        # Active monitoring tasks
        self._monitoring_tasks: dict[str, asyncio.Task] = {}
        self._inotify_tasks: dict[str, asyncio.Task] = {}

        # Service state
        self._running = False
        self._unified_service = None
        self._remote_file_watcher: RemoteFileWatcher | None = None
        self._file_event_correlator = None

        logger.info(
            f"ConfigurationMonitoringService initialized - "
            f"inotify: {enable_inotify}, polling: {enable_polling}, "
            f"check_interval: {default_check_interval}s"
        )

    async def start(self) -> None:
        """Start the configuration monitoring service."""
        if self._running:
            return

        try:
            self._running = True
            self._unified_service = await get_unified_data_collection_service()

            # Initialize file event correlator
            self._file_event_correlator = await get_file_event_correlator()

            # Initialize remote file watcher if inotify is enabled
            if self.enable_inotify:
                self._remote_file_watcher = await get_remote_file_watcher()

                # Subscribe to file change events
                event_bus.subscribe("file_changed", self._handle_file_change_event)

            # Subscribe to correlated events from the file event correlator
            event_bus.subscribe(
                "configuration.proxy.bulk_update", self._handle_correlated_proxy_event
            )
            event_bus.subscribe(
                "configuration.docker_compose.bulk_update", self._handle_correlated_compose_event
            )
            event_bus.subscribe(
                "configuration.systemd.bulk_update", self._handle_correlated_systemd_event
            )
            event_bus.subscribe(
                "configuration.git.repository_update", self._handle_correlated_git_event
            )
            event_bus.subscribe(
                "configuration.application.bulk_update", self._handle_correlated_app_config_event
            )
            event_bus.subscribe("configuration.file.changed", self._handle_individual_file_event)

            # Load existing watch targets from database
            await self._load_watch_targets()

            # Start monitoring for all devices
            await self._start_all_monitoring()

            logger.info("ConfigurationMonitoringService started successfully")

        except Exception as e:
            logger.error(f"Failed to start ConfigurationMonitoringService: {e}")
            raise ServiceUnavailableError(
                service_name="configuration_monitoring",
                message="Failed to start service",
                details={"startup_error": str(e)},
            ) from e

    async def stop(self) -> None:
        """Stop the configuration monitoring service."""
        self._running = False

        # Cancel all monitoring tasks
        for task in list(self._monitoring_tasks.values()):
            task.cancel()
        for task in list(self._inotify_tasks.values()):
            task.cancel()

        # Wait for tasks to complete
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks.values(), return_exceptions=True)
        if self._inotify_tasks:
            await asyncio.gather(*self._inotify_tasks.values(), return_exceptions=True)

        self._monitoring_tasks.clear()
        self._inotify_tasks.clear()

        logger.info("ConfigurationMonitoringService stopped successfully")

    async def add_watch_target(self, target: ConfigurationWatchTarget) -> None:
        """Add a new configuration file or directory to monitor."""
        device_id = target.device_id

        # Initialize device watch list if needed
        if device_id not in self._watch_targets:
            self._watch_targets[device_id] = []
            self._file_states[device_id] = {}

        # Check if target already exists
        existing = next((t for t in self._watch_targets[device_id] if t.path == target.path), None)
        if existing:
            logger.warning(f"Watch target already exists: {device_id}:{target.path}")
            return

        # Add target
        self._watch_targets[device_id].append(target)

        # Perform initial scan
        await self._initial_scan(target)

        # Add to remote file watcher if enabled
        if self._running and self.enable_inotify and self._remote_file_watcher:
            try:
                # Get device from database
                async with get_async_session() as session:
                    device_result = await session.execute(
                        select(Device).where(Device.id == device_id)
                    )
                    device = device_result.scalar_one_or_none()

                    if device:
                        # Create WatchTarget for remote file watcher
                        watch_target = WatchTarget(
                            path=target.path,
                            device_id=device.id,
                            recursive=target.watch_subdirectories,
                            events=["modify", "create", "delete", "move"],
                            exclude_patterns=target.ignore_patterns,
                        )

                        await self._remote_file_watcher.add_watch(device, [watch_target])
            except Exception:
                pass  # Fall back to polling if remote watcher fails

        # Start monitoring if service is running
        if self._running:
            await self._start_device_monitoring(device_id)

    async def remove_watch_target(self, device_id: str, path: str) -> bool:
        """Remove a watch target."""
        if device_id not in self._watch_targets:
            return False

        # Find and remove target
        targets = self._watch_targets[device_id]
        target_to_remove = next((t for t in targets if t.path == path), None)

        if not target_to_remove:
            return False

        targets.remove(target_to_remove)

        # Remove file states for this path
        if device_id in self._file_states:
            self._file_states[device_id] = {
                file_path: state
                for file_path, state in self._file_states[device_id].items()
                if not file_path.startswith(path)
            }

        # Remove from remote file watcher if enabled
        if self._running and self.enable_inotify and self._remote_file_watcher:
            try:
                await self._remote_file_watcher.remove_watch(device_id)
            except Exception:
                pass  # Continue with local removal

        # Restart monitoring for this device
        if self._running:
            await self._restart_device_monitoring(device_id)

        return True

    async def get_watch_targets(
        self, device_id: str | None = None
    ) -> dict[str, list[ConfigurationWatchTarget]]:
        """Get current watch targets."""
        if device_id:
            return {device_id: self._watch_targets.get(device_id, [])}
        return dict(self._watch_targets)

    async def trigger_immediate_check(
        self, device_id: str, path: str | None = None
    ) -> list[ConfigurationChange]:
        """Trigger immediate configuration check for device or specific path."""
        if device_id not in self._watch_targets:
            raise ValidationError(
                field="device_id",
                message=f"No watch targets configured for device: {device_id}",
            )

        changes = []
        targets = self._watch_targets[device_id]

        if path:
            # Check specific path
            target = next((t for t in targets if t.path == path), None)
            if not target:
                raise ValidationError(
                    field="path",
                    message=f"Path not monitored: {path}",
                )
            changes.extend(await self._check_target(target))
        else:
            # Check all targets for device
            for target in targets:
                changes.extend(await self._check_target(target))

        return changes

    async def get_configuration_history(
        self,
        device_id: str,
        path: str | None = None,
        hours: int = 24,
    ) -> list[ConfigurationChangeEvent]:
        """Get configuration change history."""
        try:
            async with get_async_session() as session:
                query = select(ConfigurationChangeEvent).where(
                    ConfigurationChangeEvent.device_id == device_id
                )

                if path:
                    query = query.where(ConfigurationChangeEvent.file_path == path)

                # Time filter
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
                query = query.where(ConfigurationChangeEvent.timestamp >= cutoff)

                query = query.order_by(ConfigurationChangeEvent.timestamp.desc())

                result = await session.execute(query)
                return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error getting configuration history: {e}")
            raise

    async def _load_watch_targets(self) -> None:
        """Load watch targets from database or configuration."""
        # For now, we'll set up some default targets
        # In production, this would load from database or config file

        try:
            async with get_async_session() as session:
                # Get all devices to set up default monitoring
                result = await session.execute(select(Device))
                devices = result.scalars().all()

                for device in devices:
                    device_id = str(device.id)

                    # Default configuration targets for each device
                    default_targets = [
                        ConfigurationWatchTarget(
                            device_id=device_id,
                            path="/etc/nginx/nginx.conf",
                            config_type=ConfigurationType.NGINX_CONFIG,
                            description="Main nginx configuration",
                        ),
                        ConfigurationWatchTarget(
                            device_id=device_id,
                            path="/etc/nginx/sites-enabled/",
                            config_type=ConfigurationType.NGINX_CONFIG,
                            description="Nginx site configurations",
                            watch_subdirectories=True,
                            file_patterns=["*.conf"],
                        ),
                        ConfigurationWatchTarget(
                            device_id=device_id,
                            path="/docker-compose.yml",
                            config_type=ConfigurationType.DOCKER_COMPOSE,
                            description="Docker Compose configuration",
                        ),
                        ConfigurationWatchTarget(
                            device_id=device_id,
                            path="/etc/systemd/system/",
                            config_type=ConfigurationType.SYSTEMD_SERVICE,
                            description="Systemd service configurations",
                            watch_subdirectories=True,
                            file_patterns=["*.service"],
                        ),
                    ]

                    self._watch_targets[device_id] = default_targets
                    self._file_states[device_id] = {}

        except Exception as e:
            logger.error(f"Error loading watch targets: {e}")

    async def _start_all_monitoring(self) -> None:
        """Start monitoring for all configured devices."""
        for device_id in self._watch_targets:
            await self._start_device_monitoring(device_id)

    async def _start_device_monitoring(self, device_id: str) -> None:
        """Start monitoring for a specific device."""
        # Cancel existing monitoring task
        if device_id in self._monitoring_tasks:
            self._monitoring_tasks[device_id].cancel()

        # Start new monitoring task
        self._monitoring_tasks[device_id] = asyncio.create_task(
            self._device_monitoring_loop(device_id)
        )

        # Start inotify monitoring if enabled
        if self.enable_inotify:
            if device_id in self._inotify_tasks:
                self._inotify_tasks[device_id].cancel()

            self._inotify_tasks[device_id] = asyncio.create_task(
                self._device_inotify_loop(device_id)
            )

    async def _restart_device_monitoring(self, device_id: str) -> None:
        """Restart monitoring for a device."""
        # Cancel existing tasks
        if device_id in self._monitoring_tasks:
            self._monitoring_tasks[device_id].cancel()
            del self._monitoring_tasks[device_id]

        if device_id in self._inotify_tasks:
            self._inotify_tasks[device_id].cancel()
            del self._inotify_tasks[device_id]

        # Restart if we have targets
        if device_id in self._watch_targets and self._watch_targets[device_id]:
            await self._start_device_monitoring(device_id)

    async def _device_monitoring_loop(self, device_id: str) -> None:
        """Main monitoring loop for a device (polling-based)."""
        if not self.enable_polling:
            return

        logger.info(f"Starting polling monitoring for device: {device_id}")

        while self._running:
            try:
                targets = self._watch_targets.get(device_id, [])

                for target in targets:
                    if not self._running:
                        break

                    try:
                        changes = await self._check_target(target)
                        for change in changes:
                            await self._handle_configuration_change(change)
                    except Exception as e:
                        logger.error(f"Error checking target {target.path}: {e}")

                # Wait for next check interval
                if self._running:
                    interval = (
                        min(target.check_interval_seconds for target in targets)
                        if targets
                        else self.default_check_interval
                    )

                    await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop for {device_id}: {e}")
                await asyncio.sleep(60)  # Wait before retrying

        logger.info(f"Stopped polling monitoring for device: {device_id}")

    async def _device_inotify_loop(self, device_id: str) -> None:
        """inotify-based monitoring loop for a device."""
        if not self.enable_inotify:
            return

        logger.info(f"Starting inotify monitoring for device: {device_id}")

        try:
            # This would implement actual inotify monitoring
            # For now, we'll use a simplified approach
            while self._running:
                # Check if device supports inotify
                supports_inotify = await self._check_inotify_support(device_id)

                if supports_inotify:
                    # Set up inotify watches
                    await self._setup_inotify_watches(device_id)

                    # Process inotify events
                    await self._process_inotify_events(device_id)
                else:
                    # Fall back to polling
                    logger.info(f"Device {device_id} doesn't support inotify, using polling only")
                    break

                await asyncio.sleep(1)  # Brief pause between event processing

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in inotify loop for {device_id}: {e}")

        logger.info(f"Stopped inotify monitoring for device: {device_id}")

    async def _check_inotify_support(self, device_id: str) -> bool:
        """Check if device supports inotify."""
        try:
            # Use unified service to check for inotify support
            result = await self._unified_service.collect_data(
                operation_name="read_file",
                device_id=device_id,
                parameters={"file_path": "/proc/sys/fs/inotify/max_user_watches"},
                timeout_override=5,
            )

            return result.success and result.data is not None

        except Exception as e:
            logger.debug(f"inotify support check failed for {device_id}: {e}")
            return False

    async def _setup_inotify_watches(self, device_id: str) -> None:
        """Set up inotify watches for device targets."""
        targets = self._watch_targets.get(device_id, [])

        for target in targets:
            try:
                # Create inotify watch command
                watch_command = f"inotifywait -m -e modify,create,delete,move {target.path}"

                # This would set up the actual inotify watch
                # For now, we'll log the intent
                logger.debug(f"Would set up inotify watch: {device_id}:{target.path}")

            except Exception as e:
                logger.error(f"Error setting up inotify watch for {target.path}: {e}")

    async def _process_inotify_events(self, device_id: str) -> None:
        """Process inotify events for a device."""
        # This would process actual inotify events
        # For now, this is a placeholder
        await asyncio.sleep(10)

    async def _initial_scan(self, target: ConfigurationWatchTarget) -> None:
        """Perform initial scan of a watch target."""
        try:
            if target.watch_subdirectories:
                # Scan directory
                result = await self._unified_service.collect_data(
                    operation_name="list_directory",
                    device_id=target.device_id,
                    parameters={"directory_path": target.path},
                )

                if result.success and result.data:
                    # Parse directory listing and update file states
                    await self._update_directory_states(target, result.data)
            else:
                # Scan single file
                result = await self._unified_service.collect_data(
                    operation_name="read_file",
                    device_id=target.device_id,
                    parameters={"file_path": target.path},
                )

                if result.success and result.data:
                    await self._update_file_state(target, target.path, result.data)

        except Exception as e:
            logger.error(f"Error in initial scan for {target.path}: {e}")

    async def _check_target(self, target: ConfigurationWatchTarget) -> list[ConfigurationChange]:
        """Check a specific target for changes."""
        changes = []

        try:
            if target.watch_subdirectories:
                changes.extend(await self._check_directory_target(target))
            else:
                changes.extend(await self._check_file_target(target))

        except Exception as e:
            logger.error(f"Error checking target {target.path}: {e}")

        return changes

    async def _check_file_target(
        self, target: ConfigurationWatchTarget
    ) -> list[ConfigurationChange]:
        """Check a single file target for changes."""
        changes = []

        try:
            # Get current file content
            result = await self._unified_service.collect_data(
                operation_name="read_file",
                device_id=target.device_id,
                parameters={"file_path": target.path},
                force_refresh=True,  # Always get fresh data for change detection
            )

            if result.success and result.data:
                change = await self._detect_file_change(target, target.path, result.data)
                if change:
                    changes.append(change)
            elif not result.success:
                # File might have been deleted
                change = await self._detect_file_deletion(target, target.path)
                if change:
                    changes.append(change)

        except Exception as e:
            logger.error(f"Error checking file {target.path}: {e}")

        return changes

    async def _check_directory_target(
        self, target: ConfigurationWatchTarget
    ) -> list[ConfigurationChange]:
        """Check a directory target for changes."""
        changes = []

        try:
            # List directory contents
            result = await self._unified_service.collect_data(
                operation_name="list_directory",
                device_id=target.device_id,
                parameters={"directory_path": target.path},
                force_refresh=True,
            )

            if result.success and result.data:
                changes.extend(await self._detect_directory_changes(target, result.data))

        except Exception as e:
            logger.error(f"Error checking directory {target.path}: {e}")

        return changes

    async def _detect_file_change(
        self, target: ConfigurationWatchTarget, file_path: str, content: str
    ) -> ConfigurationChange | None:
        """Detect if a file has changed."""
        device_id = target.device_id
        current_hash = hashlib.sha256(content.encode()).hexdigest()
        current_size = len(content.encode())
        current_time = datetime.now(timezone.utc)

        # Get previous state
        file_states = self._file_states.get(device_id, {})
        old_state = file_states.get(file_path)

        if old_state:
            old_hash, old_size, old_mtime, old_permissions = old_state

            # Check if content changed
            if old_hash != current_hash:
                # Update state
                self._file_states[device_id][file_path] = (
                    current_hash,
                    current_size,
                    current_time.timestamp(),
                    old_permissions,
                )

                return ConfigurationChange(
                    device_id=device_id,
                    file_path=file_path,
                    change_type=ChangeType.MODIFIED,
                    config_type=target.config_type,
                    timestamp=current_time,
                    old_content_hash=old_hash,
                    new_content_hash=current_hash,
                    old_size_bytes=old_size,
                    new_size_bytes=current_size,
                    diff_summary=f"Content changed ({current_size - old_size:+} bytes)",
                    metadata={"target_description": target.description},
                )
        else:
            # New file
            if device_id not in self._file_states:
                self._file_states[device_id] = {}

            self._file_states[device_id][file_path] = (
                current_hash,
                current_size,
                current_time.timestamp(),
                "unknown",
            )

            return ConfigurationChange(
                device_id=device_id,
                file_path=file_path,
                change_type=ChangeType.CREATED,
                config_type=target.config_type,
                timestamp=current_time,
                new_content_hash=current_hash,
                new_size_bytes=current_size,
                diff_summary=f"File created ({current_size} bytes)",
                metadata={"target_description": target.description},
            )

        return None

    async def _detect_file_deletion(
        self, target: ConfigurationWatchTarget, file_path: str
    ) -> ConfigurationChange | None:
        """Detect if a file has been deleted."""
        device_id = target.device_id
        file_states = self._file_states.get(device_id, {})

        if file_path in file_states:
            old_hash, old_size, old_mtime, old_permissions = file_states[file_path]

            # Remove from tracking
            del self._file_states[device_id][file_path]

            return ConfigurationChange(
                device_id=device_id,
                file_path=file_path,
                change_type=ChangeType.DELETED,
                config_type=target.config_type,
                timestamp=datetime.now(timezone.utc),
                old_content_hash=old_hash,
                old_size_bytes=old_size,
                diff_summary=f"File deleted (was {old_size} bytes)",
                metadata={"target_description": target.description},
            )

        return None

    async def _detect_directory_changes(
        self, target: ConfigurationWatchTarget, directory_listing: str
    ) -> list[ConfigurationChange]:
        """Detect changes in a directory."""
        changes = []

        # This would parse the directory listing and compare with previous state
        # For now, this is a placeholder
        logger.debug(f"Would detect directory changes for {target.path}")

        return changes

    async def _update_file_state(
        self, target: ConfigurationWatchTarget, file_path: str, content: str
    ) -> None:
        """Update the stored state for a file."""
        device_id = target.device_id
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        size_bytes = len(content.encode())
        current_time = datetime.now(timezone.utc).timestamp()

        if device_id not in self._file_states:
            self._file_states[device_id] = {}

        self._file_states[device_id][file_path] = (
            content_hash,
            size_bytes,
            current_time,
            "unknown",
        )

    async def _update_directory_states(
        self, target: ConfigurationWatchTarget, listing: str
    ) -> None:
        """Update states for all files in a directory."""
        # This would parse directory listing and update file states
        # For now, this is a placeholder
        pass

    async def _handle_configuration_change(self, change: ConfigurationChange) -> None:
        """Handle a detected configuration change."""
        try:
            # Store change event in database
            async with get_async_session() as session:
                change_event = ConfigurationChangeEvent(
                    device_id=change.device_id,
                    file_path=change.file_path,
                    change_type=change.change_type.value,
                    config_type=change.config_type.value,
                    timestamp=change.timestamp,
                    old_content_hash=change.old_content_hash,
                    new_content_hash=change.new_content_hash,
                    old_size_bytes=change.old_size_bytes,
                    new_size_bytes=change.new_size_bytes,
                    diff_summary=change.diff_summary,
                    change_metadata=change.metadata,
                )

                session.add(change_event)
                await session.commit()

            # Create configuration snapshot if this is a significant change
            if change.change_type in [ChangeType.CREATED, ChangeType.MODIFIED]:
                await self._create_configuration_snapshot(change)

            # Emit real-time event
            await event_bus.emit(
                "configuration_changed",
                {
                    "device_id": change.device_id,
                    "file_path": change.file_path,
                    "change_type": change.change_type.value,
                    "config_type": change.config_type.value,
                    "timestamp": change.timestamp.isoformat(),
                    "diff_summary": change.diff_summary,
                },
            )

            logger.info(
                f"Configuration change detected: {change.device_id}:{change.file_path} "
                f"({change.change_type.value})"
            )

        except Exception as e:
            logger.error(f"Error handling configuration change: {e}")

    async def _create_configuration_snapshot(self, change: ConfigurationChange) -> None:
        """Create a configuration snapshot for significant changes."""
        try:
            # Get current file content
            result = await self._unified_service.collect_data(
                operation_name="read_file",
                device_id=change.device_id,
                parameters={"file_path": change.file_path},
                force_refresh=True,
            )

            if result.success and result.data:
                async with get_async_session() as session:
                    snapshot = ConfigurationSnapshot(
                        device_id=change.device_id,
                        config_type=change.config_type.value,
                        file_path=change.file_path,
                        content_hash=change.new_content_hash,
                        content_size_bytes=change.new_size_bytes or 0,
                        snapshot_timestamp=change.timestamp,
                        configuration_content=result.data,
                        parser_version="1.0",
                        snapshot_metadata={
                            "change_type": change.change_type.value,
                            "diff_summary": change.diff_summary,
                        },
                    )

                    session.add(snapshot)
                    await session.commit()

        except Exception as e:
            logger.error(f"Error creating configuration snapshot: {e}")

    async def _handle_file_change_event(self, event_data: dict[str, Any]) -> None:
        """Handle file change events from the remote file watcher"""
        try:
            device_id_str = event_data.get("device_id")
            file_path = event_data.get("path")
            event_types = event_data.get("event_types", [])
            timestamp_str = event_data.get("timestamp")

            if not all([device_id_str, file_path, event_types]):
                return

            # Parse timestamp
            try:
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.now(timezone.utc)
            except ValueError:
                timestamp = datetime.now(timezone.utc)

            # Convert to UUID
            from uuid import UUID

            try:
                device_id = UUID(device_id_str)
            except (ValueError, TypeError):
                return

            # Create FileChangeEvent and send to correlator
            from apps.backend.src.schemas.configuration import FileChangeEvent

            file_event = FileChangeEvent(
                path=file_path,
                event_types=event_types,
                timestamp=timestamp,
                device_id=device_id,
            )

            # Send to correlator for processing
            if self._file_event_correlator:
                await self._file_event_correlator.process_event(file_event)

        except Exception:
            pass  # Error handling without logger

    def _map_inotify_to_change_type(self, event_types: list[str]) -> ChangeType | None:
        """Map inotify event types to configuration change types"""
        if "delete" in event_types:
            return ChangeType.DELETED
        elif "create" in event_types:
            return ChangeType.CREATED
        elif "modify" in event_types:
            return ChangeType.MODIFIED
        elif "move" in event_types:
            return ChangeType.MOVED
        elif "attrib" in event_types:
            return ChangeType.PERMISSIONS_CHANGED
        return None

    def _find_watch_target_for_path(
        self, device_id: str, file_path: str
    ) -> ConfigurationWatchTarget | None:
        """Find the watch target that matches the given file path"""
        targets = self._watch_targets.get(device_id, [])

        for target in targets:
            if target.watch_subdirectories:
                # Check if file is under this directory
                if file_path.startswith(target.path):
                    # Check file patterns if specified
                    if not target.file_patterns:
                        return target

                    for pattern in target.file_patterns:
                        import fnmatch

                        if fnmatch.fnmatch(file_path, pattern):
                            return target
            else:
                # Exact path match
                if file_path == target.path:
                    return target

        return None

    async def _handle_correlated_proxy_event(self, event_data: dict[str, Any]) -> None:
        """Handle correlated proxy configuration bulk update events"""
        try:
            device_id = event_data.get("device_id")
            files_changed = event_data.get("files_changed", [])

            if not device_id or not files_changed:
                return

            # Create a single configuration change event for the bulk update
            change = ConfigurationChange(
                device_id=device_id,
                file_path=f"bulk_update:{len(files_changed)}_proxy_configs",
                change_type=ChangeType.MODIFIED,
                config_type=ConfigurationType.NGINX_CONFIG,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "source": "correlator",
                    "event_type": "ProxyConfigBulkUpdate",
                    "files_changed": files_changed,
                    "change_count": event_data.get("change_count", len(files_changed)),
                },
            )

            await self._handle_configuration_change(change)

        except Exception:
            pass

    async def _handle_correlated_compose_event(self, event_data: dict[str, Any]) -> None:
        """Handle correlated Docker Compose bulk update events"""
        try:
            device_id = event_data.get("device_id")
            files_changed = event_data.get("files_changed", [])

            if not device_id or not files_changed:
                return

            change = ConfigurationChange(
                device_id=device_id,
                file_path=f"bulk_update:{len(files_changed)}_compose_files",
                change_type=ChangeType.MODIFIED,
                config_type=ConfigurationType.DOCKER_COMPOSE,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "source": "correlator",
                    "event_type": "DockerComposeBulkUpdate",
                    "files_changed": files_changed,
                    "change_count": event_data.get("change_count", len(files_changed)),
                },
            )

            await self._handle_configuration_change(change)

        except Exception:
            pass

    async def _handle_correlated_systemd_event(self, event_data: dict[str, Any]) -> None:
        """Handle correlated systemd service bulk update events"""
        try:
            device_id = event_data.get("device_id")
            files_changed = event_data.get("files_changed", [])

            if not device_id or not files_changed:
                return

            change = ConfigurationChange(
                device_id=device_id,
                file_path=f"bulk_update:{len(files_changed)}_systemd_services",
                change_type=ChangeType.MODIFIED,
                config_type=ConfigurationType.SYSTEMD_SERVICE,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "source": "correlator",
                    "event_type": "SystemdServiceBulkUpdate",
                    "files_changed": files_changed,
                    "change_count": event_data.get("change_count", len(files_changed)),
                },
            )

            await self._handle_configuration_change(change)

        except Exception:
            pass

    async def _handle_correlated_git_event(self, event_data: dict[str, Any]) -> None:
        """Handle correlated git repository update events"""
        try:
            device_id = event_data.get("device_id")
            files_changed = event_data.get("files_changed", [])

            if not device_id or not files_changed:
                return

            change = ConfigurationChange(
                device_id=device_id,
                file_path=f"git_update:{len(files_changed)}_files",
                change_type=ChangeType.MODIFIED,
                config_type=ConfigurationType.GENERIC_TEXT,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "source": "correlator",
                    "event_type": "GitRepositoryUpdate",
                    "files_changed": files_changed[:10],  # Limit shown files
                    "change_count": event_data.get("change_count", len(files_changed)),
                },
            )

            await self._handle_configuration_change(change)

        except Exception:
            pass

    async def _handle_correlated_app_config_event(self, event_data: dict[str, Any]) -> None:
        """Handle correlated application configuration bulk update events"""
        try:
            device_id = event_data.get("device_id")
            directory = event_data.get("directory", "")
            files_changed = event_data.get("files_changed", [])

            if not device_id or not files_changed:
                return

            change = ConfigurationChange(
                device_id=device_id,
                file_path=f"app_config_update:{directory}:{len(files_changed)}_files",
                change_type=ChangeType.MODIFIED,
                config_type=ConfigurationType.GENERIC_TEXT,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "source": "correlator",
                    "event_type": "ApplicationConfigBulkUpdate",
                    "directory": directory,
                    "files_changed": files_changed,
                    "change_count": event_data.get("change_count", len(files_changed)),
                },
            )

            await self._handle_configuration_change(change)

        except Exception:
            pass

    async def _handle_individual_file_event(self, event_data: dict[str, Any]) -> None:
        """Handle individual file change events from the correlator"""
        try:
            device_id_str = event_data.get("device_id")
            file_path = event_data.get("path")
            event_types = event_data.get("event_types", [])

            if not all([device_id_str, file_path, event_types]):
                return

            # Convert to configuration change type
            change_type = self._map_inotify_to_change_type(event_types)
            if not change_type:
                return

            # Find matching watch target
            watch_target = self._find_watch_target_for_path(device_id_str, file_path)
            if not watch_target:
                return

            change = ConfigurationChange(
                device_id=device_id_str,
                file_path=file_path,
                change_type=change_type,
                config_type=watch_target.config_type,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "source": "correlator_individual",
                    "event_types": event_types,
                },
            )

            await self._handle_configuration_change(change)

        except Exception:
            pass

    def get_monitoring_statistics(self) -> dict[str, Any]:
        """Get current monitoring statistics."""
        remote_watcher_stats = {}
        if self._remote_file_watcher:
            remote_watcher_stats = self._remote_file_watcher.get_session_stats()

        correlator_stats = {}
        if self._file_event_correlator:
            correlator_stats = self._file_event_correlator.get_correlation_stats()

        return {
            "running": self._running,
            "total_devices": len(self._watch_targets),
            "total_targets": sum(len(targets) for targets in self._watch_targets.values()),
            "active_monitoring_tasks": len(self._monitoring_tasks),
            "active_inotify_tasks": len(self._inotify_tasks),
            "total_files_tracked": sum(len(states) for states in self._file_states.values()),
            "enable_inotify": self.enable_inotify,
            "enable_polling": self.enable_polling,
            "default_check_interval": self.default_check_interval,
            "remote_file_watcher": remote_watcher_stats,
            "file_event_correlator": correlator_stats,
        }


# Global singleton instance
_config_monitoring_service: ConfigurationMonitoringService | None = None


async def get_configuration_monitoring_service() -> ConfigurationMonitoringService:
    """Get the global configuration monitoring service instance."""
    global _config_monitoring_service

    if _config_monitoring_service is None:
        _config_monitoring_service = ConfigurationMonitoringService()
        await _config_monitoring_service.start()

    return _config_monitoring_service


async def shutdown_configuration_monitoring_service() -> None:
    """Shutdown the global service instance."""
    global _config_monitoring_service

    if _config_monitoring_service is not None:
        await _config_monitoring_service.stop()
        _config_monitoring_service = None
