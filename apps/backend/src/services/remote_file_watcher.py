"""
Remote File Watcher Service

Implements SSH-based inotify streaming for real-time configuration file monitoring
with persistent connections and robust error handling.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import UUID

from apps.backend.src.core.exceptions import (
    SSHConnectionError,
    SSHCommandError,
    ValidationError,
)
from apps.backend.src.models.device import Device
from apps.backend.src.schemas.configuration import FileChangeEvent
from apps.backend.src.utils.ssh_client import SSHClient, SSHConnectionInfo, get_ssh_client
from apps.backend.src.core.events import event_bus
from apps.backend.src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class WatchTarget:
    """Configuration for a file or directory to watch"""

    path: str
    device_id: UUID
    recursive: bool = False
    events: list[str] = field(default_factory=lambda: ["modify", "create", "delete", "move"])
    exclude_patterns: list[str] = field(default_factory=list)


@dataclass
class RemoteWatchSession:
    """Active remote watching session"""

    device_id: UUID
    connection_info: SSHConnectionInfo
    targets: list[WatchTarget]
    ssh_task: asyncio.Task | None = None
    stream_reader: asyncio.StreamReader | None = None
    stream_writer: asyncio.StreamWriter | None = None
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_count: int = 0


class RemoteFileWatcher:
    """
    SSH-based remote file watching with inotify streaming.

    Features:
    - Persistent SSH connections for low-latency event streaming
    - Real-time inotify event parsing and correlation
    - Automatic reconnection with exponential backoff
    - Event filtering and deduplication
    - Multi-device concurrent watching
    """

    def __init__(
        self,
        max_connections: int | None = None,
        heartbeat_interval: int | None = None,
        max_reconnect_attempts: int | None = None,
        reconnect_delay: int | None = None,
    ):
        self.max_connections = max_connections or getattr(
            settings, "FILE_WATCHER_MAX_CONNECTIONS", 50
        )
        self.heartbeat_interval = heartbeat_interval or getattr(
            settings, "FILE_WATCHER_HEARTBEAT_INTERVAL", 30
        )
        self.max_reconnect_attempts = max_reconnect_attempts or getattr(
            settings, "FILE_WATCHER_MAX_RECONNECT_ATTEMPTS", 5
        )
        self.reconnect_delay = reconnect_delay or getattr(
            settings, "FILE_WATCHER_RECONNECT_DELAY", 5
        )

        # Active watch sessions by device_id
        self._sessions: dict[UUID, RemoteWatchSession] = {}

        # SSH client for connections
        self._ssh_client = get_ssh_client()

        # Service state
        self._running = False
        self._heartbeat_task: asyncio.Task | None = None

        logger.info(
            f"RemoteFileWatcher initialized - max_connections: {self.max_connections}, "
            f"heartbeat_interval: {self.heartbeat_interval}s"
        )

    async def start(self) -> None:
        """Start the remote file watcher service"""
        if self._running:
            return

        self._running = True

        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("RemoteFileWatcher started successfully")

    async def stop(self) -> None:
        """Stop the remote file watcher service"""
        self._running = False

        # Stop heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close all active sessions
        for session in list(self._sessions.values()):
            await self._close_session(session.device_id)

        logger.info("RemoteFileWatcher stopped successfully")

    async def add_watch(
        self,
        device: Device,
        targets: list[WatchTarget],
    ) -> None:
        """Add file watches for a device"""
        if len(self._sessions) >= self.max_connections:
            raise ValidationError(
                field="device_id", message=f"Maximum connections ({self.max_connections}) reached"
            )

        device_id = device.id

        # Close existing session if any
        if device_id in self._sessions:
            await self._close_session(device_id)

        # Create SSH connection info
        connection_info = SSHConnectionInfo(
            host=device.hostname,
            port=device.ssh_port or getattr(settings, "SSH_DEFAULT_PORT", 22),
            username=device.username,
            private_key_path=device.ssh_key_path,
            connect_timeout=getattr(settings, "SSH_CONNECTION_TIMEOUT", 10),
            command_timeout=getattr(
                settings, "SSH_STREAM_COMMAND_TIMEOUT", None
            ),  # No timeout for streaming
        )

        # Create new session
        session = RemoteWatchSession(
            device_id=device_id,
            connection_info=connection_info,
            targets=targets,
        )

        self._sessions[device_id] = session

        # Start watching task
        session.ssh_task = asyncio.create_task(self._watch_device_task(session))

        logger.info(f"Added watch for device {device.hostname} with {len(targets)} targets")

    async def remove_watch(self, device_id: UUID) -> bool:
        """Remove file watches for a device"""
        if device_id not in self._sessions:
            return False

        await self._close_session(device_id)
        logger.info(f"Removed watch for device {device_id}")
        return True

    async def get_active_watches(self) -> dict[UUID, list[WatchTarget]]:
        """Get all active watch targets by device"""
        return {device_id: session.targets for device_id, session in self._sessions.items()}

    async def _watch_device_task(self, session: RemoteWatchSession) -> None:
        """Main watching task for a device"""
        device_id = session.device_id
        attempts = 0

        while self._running and attempts < self.max_reconnect_attempts:
            try:
                logger.info(
                    f"Starting watch session for device {device_id} (attempt {attempts + 1})"
                )

                # Setup inotify watches
                await self._setup_inotify_watches(session)

                # Stream events
                async for event in self._stream_file_events(session):
                    if not self._running:
                        break

                    # Process event
                    await self._process_file_event(event)

                    # Update heartbeat
                    session.last_heartbeat = datetime.now(timezone.utc)
                    session.error_count = 0

                # If we reach here, connection was closed gracefully
                break

            except asyncio.CancelledError:
                logger.info(f"Watch task cancelled for device {device_id}")
                break
            except Exception as e:
                attempts += 1
                session.error_count += 1

                logger.error(
                    f"Error in watch task for device {device_id} "
                    f"(attempt {attempts}/{self.max_reconnect_attempts}): {e}"
                )

                if attempts < self.max_reconnect_attempts:
                    # Exponential backoff
                    delay = self.reconnect_delay * (2 ** (attempts - 1))
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Max reconnection attempts reached for device {device_id}")
                    break

        # Clean up session
        if device_id in self._sessions:
            del self._sessions[device_id]

    async def _setup_inotify_watches(self, session: RemoteWatchSession) -> None:
        """Setup inotify watches on the remote device"""
        device_id = session.device_id

        # Check if inotify is available
        try:
            result = await self._ssh_client.execute_command(
                session.connection_info, "which inotifywait"
            )
            if result.exit_code != 0:
                raise SSHCommandError(
                    "inotifywait not available on remote device",
                    command="which inotifywait",
                    hostname=session.connection_info.host,
                )
        except Exception as e:
            raise SSHConnectionError(
                f"Failed to check inotify availability: {e}", hostname=session.connection_info.host
            ) from e

        logger.debug(f"Setting up inotify for device {device_id}")

    async def _stream_file_events(
        self, session: RemoteWatchSession
    ) -> AsyncGenerator[FileChangeEvent, None]:
        """Stream file change events from inotify"""
        device_id = session.device_id

        # Build inotify command
        events = set()
        paths = []

        for target in session.targets:
            paths.append(target.path)
            events.update(target.events)

        inotify_events = []
        event_map = {
            "modify": "modify",
            "create": "create",
            "delete": "delete",
            "move": "move",
            "attrib": "attrib",
            "access": "access",
        }

        for event in events:
            if event in event_map:
                inotify_events.append(event_map[event])

        command_parts = [
            "inotifywait",
            "-m",  # Monitor continuously
            "-r",  # Recursive
            "-e",
            ",".join(inotify_events),
            "--format",
            "'%w%f|%e|%T'",
            "--timefmt",
            "'%Y-%m-%d %H:%M:%S'",
        ]

        command_parts.extend(f"'{path}'" for path in paths)
        command = " ".join(command_parts)

        ssh_timeout = getattr(settings, "SSH_STREAM_TIMEOUT", self.heartbeat_interval + 10)
        ssh_key_path = session.connection_info.private_key_path or getattr(
            settings, "SSH_DEFAULT_KEY_PATH", "~/.ssh/id_rsa"
        )

        try:
            # Execute streaming command
            proc = await asyncio.create_subprocess_exec(
                "ssh",
                f"{session.connection_info.username}@{session.connection_info.host}",
                "-p",
                str(session.connection_info.port),
                "-i",
                ssh_key_path,
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if not proc.stdout:
                raise SSHConnectionError(
                    "Failed to create SSH subprocess for streaming",
                    hostname=session.connection_info.host,
                )

            # Process lines from stdout
            while self._running:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=ssh_timeout)

                    if not line:
                        # Process ended
                        break

                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue

                    # Parse inotify output
                    event = self._parse_inotify_line(line_str, device_id)
                    if event:
                        yield event

                except asyncio.TimeoutError:
                    # Send heartbeat or check if process is still alive
                    if proc.returncode is not None:
                        logger.warning(f"SSH process terminated for device {device_id}")
                        break
                    continue

        except Exception as e:
            logger.error(f"Error streaming events for device {device_id}: {e}")
            raise
        finally:
            # Clean up process
            if proc.returncode is None:
                proc.terminate()
                try:
                    cleanup_timeout = getattr(settings, "SSH_CLEANUP_TIMEOUT", 5)
                    await asyncio.wait_for(proc.wait(), timeout=cleanup_timeout)
                except asyncio.TimeoutError:
                    proc.kill()

    def _parse_inotify_line(self, line: str, device_id: UUID) -> FileChangeEvent | None:
        """Parse a single inotify output line"""
        try:
            # Expected format: /path/to/file|CREATE,ISDIR|2024-01-15 10:30:45
            parts = line.split("|")
            if len(parts) != 3:
                logger.debug(f"Invalid inotify line format: {line}")
                return None

            file_path, events_str, timestamp_str = parts

            # Parse events
            event_types = [e.strip().lower() for e in events_str.split(",")]

            # Filter out internal events we don't care about
            filtered_events = []
            for event in event_types:
                if event in ["modify", "create", "delete", "move", "attrib", "access"]:
                    filtered_events.append(event)

            if not filtered_events:
                return None

            # Parse timestamp
            try:
                timestamp = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S")
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            except ValueError:
                timestamp = datetime.now(timezone.utc)

            return FileChangeEvent(
                path=file_path.strip(),
                event_types=filtered_events,
                timestamp=timestamp,
                device_id=device_id,
            )

        except Exception as e:
            logger.error(f"Error parsing inotify line '{line}': {e}")
            return None

    async def _process_file_event(self, event: FileChangeEvent) -> None:
        """Process a file change event"""
        try:
            # Apply exclusion filters
            if self._should_exclude_event(event):
                return

            # Emit event to event bus
            await event_bus.emit(
                "file_changed",
                {
                    "device_id": str(event.device_id),
                    "path": event.path,
                    "event_types": event.event_types,
                    "timestamp": event.timestamp.isoformat(),
                },
            )

            logger.debug(
                f"Processed file event: {event.device_id}:{event.path} "
                f"({', '.join(event.event_types)})"
            )

        except Exception as e:
            logger.error(f"Error processing file event: {e}")

    def _should_exclude_event(self, event: FileChangeEvent) -> bool:
        """Check if event should be excluded based on patterns"""
        device_id = event.device_id

        if device_id not in self._sessions:
            return True

        session = self._sessions[device_id]

        # Check exclusion patterns for relevant targets
        for target in session.targets:
            if event.path.startswith(target.path):
                for pattern in target.exclude_patterns:
                    if re.search(pattern, event.path):
                        logger.debug(f"Excluding event {event.path} (pattern: {pattern})")
                        return True

        return False

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop to monitor session health"""
        while self._running:
            try:
                current_time = datetime.now(timezone.utc)

                # Check each session
                for device_id, session in list(self._sessions.items()):
                    time_since_heartbeat = (current_time - session.last_heartbeat).total_seconds()
                    heartbeat_threshold = self.heartbeat_interval * 2

                    if time_since_heartbeat > heartbeat_threshold:
                        logger.warning(
                            f"No heartbeat from device {device_id} for {time_since_heartbeat:.1f}s"
                        )

                        # Check if task is still running
                        if session.ssh_task and session.ssh_task.done():
                            logger.error(f"SSH task died for device {device_id}")
                            await self._close_session(device_id)

                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _close_session(self, device_id: UUID) -> None:
        """Close a watch session for a device"""
        if device_id not in self._sessions:
            return

        session = self._sessions[device_id]

        # Cancel SSH task
        if session.ssh_task:
            session.ssh_task.cancel()
            try:
                await session.ssh_task
            except asyncio.CancelledError:
                pass

        # Close streams
        if session.stream_writer:
            session.stream_writer.close()
            try:
                await session.stream_writer.wait_closed()
            except Exception:
                pass

        # Remove from sessions
        del self._sessions[device_id]

        logger.info(f"Closed watch session for device {device_id}")

    def get_session_stats(self) -> dict[str, Any]:
        """Get statistics about active watch sessions"""
        return {
            "total_sessions": len(self._sessions),
            "max_connections": self.max_connections,
            "sessions": [
                {
                    "device_id": str(session.device_id),
                    "targets_count": len(session.targets),
                    "last_heartbeat": session.last_heartbeat.isoformat(),
                    "error_count": session.error_count,
                    "task_running": session.ssh_task is not None and not session.ssh_task.done(),
                }
                for session in self._sessions.values()
            ],
        }


# Global singleton instance
_remote_file_watcher: RemoteFileWatcher | None = None


async def get_remote_file_watcher() -> RemoteFileWatcher:
    """Get the global remote file watcher instance"""
    global _remote_file_watcher

    if _remote_file_watcher is None:
        _remote_file_watcher = RemoteFileWatcher()
        await _remote_file_watcher.start()

    return _remote_file_watcher


async def shutdown_remote_file_watcher() -> None:
    """Shutdown the global service instance"""
    global _remote_file_watcher

    if _remote_file_watcher is not None:
        await _remote_file_watcher.stop()
        _remote_file_watcher = None
