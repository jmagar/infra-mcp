"""
Configuration Monitoring Service

Real-time configuration monitoring service that watches for changes in configuration
files on remote devices. Uses inotify over SSH for real-time monitoring with
polling fallback for reliability.

Task Master Task #5: Implement Real-Time Configuration Monitoring Service
"""

import asyncio
from datetime import UTC, datetime
import hashlib
import logging
from pathlib import Path

from typing import Any
from collections.abc import Awaitable, Callable, AsyncGenerator
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.backend.src.core.exceptions import (
    DatabaseOperationError,
)
from apps.backend.src.models.configuration import ConfigurationSnapshot
from apps.backend.src.models.device import Device
from apps.backend.src.services.unified_data_collection import UnifiedDataCollectionService
from apps.backend.src.utils.ssh_client import SSHClient, SSHConnectionInfo

logger = logging.getLogger(__name__)


class RemoteFileWatcher:
    """
    Manages file watching on a remote device via SSH.
    
    Uses inotify over SSH for real-time monitoring with polling fallback.
    """

    def __init__(
        self,
        device_id: UUID,
        ssh_client: SSHClient,
        db_session_factory: async_sessionmaker[AsyncSession],
        watch_paths: list[str],
        callback: Callable[[str, str, str], Awaitable[None]],
        poll_interval: int = 30
    ) -> None:
        self.device_id = device_id
        self.ssh_client = ssh_client
        self.db_session_factory = db_session_factory
        self.watch_paths = watch_paths
        self.callback = callback
        self.poll_interval = poll_interval
        self.is_monitoring = False
        self.monitor_task: asyncio.Task | None = None
        self.file_hashes: dict[str, str] = {}
        self.logger = logging.getLogger(f"{__name__}.RemoteFileWatcher")

    async def start_monitoring(self) -> bool:
        """Start file monitoring (real-time or polling fallback)"""
        if self.is_monitoring:
            return True

        # Perform initial bulk scan of existing configurations
        await self._perform_initial_bulk_scan()

        # Try real-time monitoring first
        if await self._setup_inotify_monitoring():
            self.logger.info(f"Started real-time monitoring for device {self.device_id}")
            return True

        # Fall back to polling
        self.logger.warning(f"Real-time monitoring failed for device {self.device_id}, using polling fallback")
        if await self._setup_polling_monitoring():
            self.logger.info(f"Started polling monitoring for device {self.device_id}")
            return True

        self.logger.error(f"Failed to start any monitoring for device {self.device_id}")
        return False

    async def stop_monitoring(self) -> None:
        """Stop file monitoring"""
        self.is_monitoring = False
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info(f"Stopped monitoring for device {self.device_id}")

    async def _setup_inotify_monitoring(self) -> bool:
        """Attempt to set up real-time inotify monitoring"""
        try:
            # Check if inotify tools are available
            async with self.db_session_factory() as session:
                device = await session.get(Device, self.device_id)
            if device is None or device.hostname is None:
                return False
            connection_info = SSHConnectionInfo(
                host=str(device.hostname),
                port=int(device.ssh_port or 22),
                username=str(device.ssh_username or "root"),
                password=getattr(device, 'ssh_password', None),
                private_key_path=getattr(device, 'ssh_private_key_path', None)
            )
            result = await self.ssh_client.execute_command(connection_info, "which inotifywait")
            if result.return_code != 0:
                return False

            # Initialize file hashes for change detection (bulk scan already done)
            await self._update_file_hashes()

            # Build inotifywait command for all watch paths
            watch_paths_str = " ".join(f'"{path}"' for path in self.watch_paths)
            inotify_cmd = f"inotifywait -m -r -e modify,create,delete,move --format '%w%f:%e' {watch_paths_str}"

            self.monitor_task = asyncio.create_task(self._run_inotify_monitoring(inotify_cmd))
            self.is_monitoring = True
            return True

        except Exception as e:
            self.logger.error(f"Failed to setup inotify monitoring: {e}")
            return False

    async def _setup_polling_monitoring(self) -> bool:
        """Set up polling fallback monitoring"""
        try:
            # Initialize file hashes (bulk scan already done in start_monitoring)
            await self._update_file_hashes()

            self.monitor_task = asyncio.create_task(self._run_polling_monitoring())
            self.is_monitoring = True
            return True

        except Exception as e:
            self.logger.error(f"Failed to setup polling monitoring: {e}")
            return False

    async def _run_inotify_monitoring(self, inotify_cmd: str) -> None:
        """Run real-time inotify monitoring loop"""
        try:
            # Stream command output using local helper to avoid relying on
            # a non-existent execute_streaming_command API on SSHClient
            async for line in self._stream_remote_command(inotify_cmd):
                if not self.is_monitoring:
                    break

                # Parse inotify output: filepath:event_type
                if ':' in line:
                    filepath, event_type = line.rsplit(':', 1)
                    await self._handle_file_event(filepath, event_type)

        except Exception as e:
            self.logger.error(f"inotify monitoring failed: {e}")

    async def _stream_remote_command(self, command: str) -> AsyncGenerator[str, None]:
        """Execute a remote command and yield its stdout lines.

        This provides a minimal streaming interface compatible with the
        monitoring loop while keeping type safety with mypy.
        """
        async with self.db_session_factory() as session:
            device = await session.get(Device, self.device_id)

        if device is None or device.hostname is None:
            return

        connection_info = SSHConnectionInfo(
            host=str(device.hostname),
            port=int(device.ssh_port or 22),
            username=str(device.ssh_username or "root"),
            password=getattr(device, "ssh_password", None),
            private_key_path=getattr(device, "ssh_private_key_path", None),
        )

        result = await self.ssh_client.execute_command(connection_info, command, check=False)
        for line in result.stdout.splitlines():
            yield line

    async def _run_polling_monitoring(self) -> None:
        """Run polling monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                if not self.is_monitoring:
                    break

                await self._check_for_changes()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Polling monitoring error: {e}")
                await asyncio.sleep(5)  # Short delay before retry

    async def _update_file_hashes(self) -> None:
        """Update stored file hashes for all watched files"""
        for watch_path in self.watch_paths:
            try:
                # Determine file pattern based on watch path type
                if "/proxy-confs" in watch_path.lower():
                    # For SWAG proxy configs, only watch .conf files
                    find_cmd = f"find '{watch_path}' -type f -name '*.conf' 2>/dev/null || true"
                elif "docker-compose" in watch_path.lower() or any(name in watch_path.lower() for name in ["compose", "stack"]):
                    # For Docker compose directories, watch YAML files
                    find_cmd = f"find '{watch_path}' -type f \\( -name '*.yml' -o -name '*.yaml' -o -name 'docker-compose*' -o -name 'compose*' \\) 2>/dev/null || true"
                else:
                    # General config directories - watch common config file types
                    find_cmd = f"find '{watch_path}' -type f \\( -name '*.yml' -o -name '*.yaml' -o -name '*.conf' -o -name '*.json' \\) 2>/dev/null || true"
                async with self.db_session_factory() as session:
                    device = await session.get(Device, self.device_id)
                if device is None or device.hostname is None:
                    continue
                connection_info = SSHConnectionInfo(
                    host=str(device.hostname),
                    port=int(device.ssh_port or 22),
                    username=str(device.ssh_username or "root"),
                    password=getattr(device, 'ssh_password', None),
                    private_key_path=getattr(device, 'ssh_private_key_path', None)
                )
                result = await self.ssh_client.execute_command(connection_info, find_cmd)

                if result.return_code == 0:
                    files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

                    for filepath in files:
                        try:
                            async with self.db_session_factory() as session:
                                device = await session.get(Device, self.device_id)
                            if device is None or device.hostname is None:
                                continue
                            connection_info = SSHConnectionInfo(
                                host=str(device.hostname),
                                port=int(device.ssh_port or 22),
                                username=str(device.ssh_username or "root"),
                                password=getattr(device, 'ssh_password', None),
                                private_key_path=getattr(device, 'ssh_private_key_path', None)
                            )
                            # Get file hash for change detection
                            result = await self.ssh_client.execute_command(
                                connection_info, f"sha256sum '{filepath}' | awk '{{print $1}}'"
                            )
                            if result.return_code == 0 and 'ERROR' not in result.stdout:
                                file_hash = result.stdout.split()[0]
                                self.file_hashes[filepath] = file_hash
                        except Exception as e:
                            self.logger.debug(f"Failed to hash file {filepath}: {e}")

            except Exception as e:
                self.logger.error(f"Failed to scan watch path {watch_path}: {e}")

    async def _perform_initial_bulk_scan(self) -> None:
        """Perform initial bulk scan of all existing configuration files"""
        self.logger.info(f"Starting initial bulk scan for device {self.device_id}")
        scanned_files = 0
        processed_configs = 0

        for watch_path in self.watch_paths:
            try:
                # Determine file pattern based on watch path type
                if "/proxy-confs" in watch_path.lower():
                    # For SWAG proxy configs, only scan .conf files
                    find_cmd = f"find '{watch_path}' -type f -name '*.conf' 2>/dev/null || true"
                elif "docker-compose" in watch_path.lower() or any(name in watch_path.lower() for name in ["compose", "stack"]):
                    # For Docker compose directories, scan YAML files
                    find_cmd = rf"find '{watch_path}' -type f \( -name '*.yml' -o -name '*.yaml' -o -name 'docker-compose*' -o -name 'compose*' \) 2>/dev/null || true"
                else:
                    # General config directories - scan common config file types
                    find_cmd = rf"find '{watch_path}' -type f \( -name '*.yml' -o -name '*.yaml' -o -name '*.conf' -o -name '*.json' \) 2>/dev/null || true"

                async with self.db_session_factory() as session:
                    device = await session.get(Device, self.device_id)
                if device is None or device.hostname is None:
                    continue
                connection_info = SSHConnectionInfo(
                    host=str(device.hostname),
                    port=int(device.ssh_port or 22),
                    username=str(device.ssh_username or "root"),
                    password=getattr(device, 'ssh_password', None),
                    private_key_path=getattr(device, 'ssh_private_key_path', None)
                )
                result = await self.ssh_client.execute_command(connection_info, find_cmd)

                if result.return_code == 0:
                    files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                    scanned_files += len(files)

                    for filepath in files:
                        try:
                            # Get file hash for tracking
                            async with self.db_session_factory() as session:
                                device = await session.get(Device, self.device_id)
                            if device is None or device.hostname is None:
                                continue
                            connection_info = SSHConnectionInfo(
                                host=str(device.hostname),
                                port=int(device.ssh_port or 22),
                                username=str(device.ssh_username or "root"),
                                password=getattr(device, 'ssh_password', None),
                                private_key_path=getattr(device, 'ssh_private_key_path', None)
                            )
                            hash_result = await self.ssh_client.execute_command(connection_info, f"sha256sum '{filepath}' 2>/dev/null || echo 'ERROR'")
                            if hash_result.return_code == 0 and 'ERROR' not in hash_result.stdout:
                                file_hash = hash_result.stdout.split()[0]
                                self.file_hashes[filepath] = file_hash

                                # Process this configuration file
                                await self._handle_file_event(filepath, "initial_scan")
                                processed_configs += 1

                        except Exception as e:
                            self.logger.warning(f"Failed to process file during bulk scan {filepath}: {e}")

                else:
                    self.logger.warning(f"Failed to scan watch path {watch_path}: {result.stderr}")

            except Exception as e:
                self.logger.error(f"Failed to perform bulk scan on watch path {watch_path}: {e}")

        self.logger.info(
            f"Initial bulk scan completed for device {self.device_id}: "
            f"scanned {scanned_files} files, processed {processed_configs} configurations"
        )

    async def _check_for_changes(self) -> None:
        """Check for file changes using hash comparison"""
        old_hashes = self.file_hashes.copy()
        await self._update_file_hashes()

        # Check for modifications
        for filepath, new_hash in self.file_hashes.items():
            old_hash = old_hashes.get(filepath)
            if old_hash is None:
                # New file
                await self._handle_file_event(filepath, "CREATE")
            elif old_hash != new_hash:
                # Modified file
                await self._handle_file_event(filepath, "MODIFY")

        # Check for deletions
        for filepath in old_hashes:
            if filepath not in self.file_hashes:
                await self._handle_file_event(filepath, "DELETE")

    async def _handle_file_event(self, filepath: str, event_type: str) -> None:
        """Handle a file change event"""
        try:
            await self.callback(filepath, event_type, str(self.device_id))
        except Exception as e:
            self.logger.error(f"Error handling file event {filepath}:{event_type}: {e}")


class ConfigurationMonitoringService:
    """
    Service for monitoring configuration file changes on remote devices.
    
    Manages RemoteFileWatcher instances for each device and coordinates
    configuration change detection and storage.
    """

    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        ssh_client: SSHClient,
        unified_data_service: UnifiedDataCollectionService
    ) -> None:
        self.db_session_factory = db_session_factory
        self.ssh_client = ssh_client
        self.unified_data_service = unified_data_service
        self.device_watchers: dict[UUID, RemoteFileWatcher] = {}
        self.logger = logging.getLogger(f"{__name__}.ConfigurationMonitoringService")

        # Default watch paths for different configuration types
        # NOTE: These are fallback paths. Actual paths should be discovered during device analysis
        self.fallback_watch_paths = [
            "/etc/nginx",                            # System Nginx configs
            "/etc/apache2",                          # System Apache configs
            "/etc/traefik",                          # System Traefik configs
        ]

    async def setup_device_monitoring(
        self,
        device_id: UUID,
        custom_watch_paths: list[str] | None = None
    ) -> bool:
        """
        Set up configuration monitoring for a specific device.
        
        Args:
            device_id: UUID of the device to monitor
            custom_watch_paths: Optional custom paths to watch instead of defaults
            
        Returns:
            bool: True if monitoring was successfully set up
        """
        if device_id in self.device_watchers:
            self.logger.warning(f"Device {device_id} is already being monitored")
            return True

        try:
            # Get device information
            async with self.db_session_factory() as session:
                result = await session.execute(
                    select(Device).where(Device.id == device_id)
                )
                device = result.scalar_one_or_none()

                if not device:
                    self.logger.error(f"Device {device_id} not found in database")
                    return False

            # Use custom paths from device analysis, or fallback paths, or empty if no discovery yet
            watch_paths = custom_watch_paths or self.fallback_watch_paths

            # If no paths provided, try to get discovered paths from device tags
            if not custom_watch_paths:
                discovered_paths = await self._get_discovered_config_paths(device)
                if discovered_paths:
                    watch_paths = discovered_paths

            # Create file watcher
            watcher = RemoteFileWatcher(
                device_id=device_id,
                ssh_client=self.ssh_client,
                watch_paths=watch_paths,
                db_session_factory=self.db_session_factory,
                callback=self._handle_config_change,
                poll_interval=30
            )

            # Start monitoring
            if await watcher.start_monitoring():
                self.device_watchers[device_id] = watcher
                self.logger.info(f"Started configuration monitoring for device {device_id}")
                return True
            else:
                self.logger.error(f"Failed to start monitoring for device {device_id}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to setup monitoring for device {device_id}: {e}")
            return False

    async def stop_device_monitoring(self, device_id: UUID) -> None:
        """Stop configuration monitoring for a specific device"""
        watcher = self.device_watchers.get(device_id)
        if watcher:
            await watcher.stop_monitoring()
            del self.device_watchers[device_id]
            self.logger.info(f"Stopped configuration monitoring for device {device_id}")

    async def _get_discovered_config_paths(self, device: Device) -> list[str]:
        """
        Extract configuration paths from device analysis results stored in device tags.
        
        Args:
            device: Device model with analysis results in tags
            
        Returns:
            List of discovered configuration paths to monitor
        """
        discovered_paths: list[str] = []

        if not device.tags:
            return discovered_paths

        try:
            # Get SWAG proxy config paths
            if device.tags.get("swag") and device.tags.get("swag_running"):
                # Look for SWAG config paths in analysis results
                analysis = device.tags.get("last_analysis", {})
                services = analysis.get("services", {}) if isinstance(analysis, dict) else {}

                # Add discovered SWAG config directories
                swag_containers = device.tags.get("swag_containers", [])
                if swag_containers:
                    # Common SWAG config paths to check
                    potential_swag_paths = [
                        "/mnt/appdata/swag/nginx/proxy-confs",
                        "/opt/appdata/swag/nginx/proxy-confs",
                        "/srv/swag/nginx/proxy-confs",
                        "/home/*/swag/nginx/proxy-confs"
                    ]
                    discovered_paths.extend(potential_swag_paths)

            # Get Docker Compose paths from analysis
            docker_compose_paths = device.tags.get("all_docker_compose_paths", [])
            if docker_compose_paths:
                # Add parent directories for Docker Compose file monitoring
                for compose_path in docker_compose_paths:
                    # Get directory containing docker-compose.yml
                    compose_dir = str(Path(compose_path).parent)
                    discovered_paths.append(compose_dir)

                    # Also watch subdirectories that might contain additional compose files
                    discovered_paths.append(f"{compose_dir}/*")

            # Get appdata paths that might contain configs
            appdata_paths = device.tags.get("all_appdata_paths", [])
            if appdata_paths:
                for appdata_path in appdata_paths:
                    # Monitor config-heavy subdirectories
                    config_subdirs = [
                        f"{appdata_path}/*/config",
                        f"{appdata_path}/nginx",
                        f"{appdata_path}/traefik"
                    ]
                    discovered_paths.extend(config_subdirs)

            # Remove duplicates and return
            unique_paths = list(set(discovered_paths))

            if unique_paths:
                self.logger.info(
                    f"Discovered {len(unique_paths)} config paths for device {device.hostname}: {unique_paths}"
                )

            return unique_paths

        except Exception as e:
            self.logger.error(f"Error extracting discovered config paths for device {device.hostname}: {e}")
            return []

    async def stop_all_monitoring(self) -> None:
        """Stop all configuration monitoring"""
        tasks = [
            watcher.stop_monitoring()
            for watcher in self.device_watchers.values()
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self.device_watchers.clear()
        self.logger.info("Stopped all configuration monitoring")

    async def get_monitored_devices(self) -> list[UUID]:
        """Get list of currently monitored device IDs"""
        return list(self.device_watchers.keys())

    async def _handle_config_change(self, filepath: str, event_type: str, device_id_str: str) -> None:
        """
        Handle a configuration file change event.
        
        This is the callback triggered by RemoteFileWatcher when a file changes.
        """
        try:
            device_id = UUID(device_id_str)

            # Determine configuration type from file path
            config_type = self._determine_config_type(filepath)

            # Get file content (if file still exists)
            raw_content = ""
            content_hash = ""

            if event_type != "DELETE":
                try:
                    async with self.db_session_factory() as session:
                        device = await session.get(Device, device_id)
                    if device is None or device.hostname is None:
                        raise ValueError("Device not found or missing hostname")
                    connection_info = SSHConnectionInfo(
                        host=str(device.hostname),
                        port=int(device.ssh_port or 22),
                        username=str(device.ssh_username or "root"),
                        password=getattr(device, 'ssh_password', None),
                        private_key_path=getattr(device, 'ssh_private_key_path', None)
                    )
                    result = await self.ssh_client.execute_command(connection_info, f"cat '{filepath}'")
                    if result.return_code == 0:
                        raw_content = result.stdout
                        content_hash = hashlib.sha256(raw_content.encode()).hexdigest()
                except Exception as e:
                    self.logger.error(f"Failed to read file {filepath}: {e}")
                    raw_content = f"ERROR_READING_FILE: {str(e)}"
                    content_hash = hashlib.sha256(raw_content.encode()).hexdigest()

            # Parse configuration data (basic parsing)
            parsed_data = None
            try:
                parsed_data = await self._parse_config_file(filepath, raw_content)
            except Exception as e:
                self.logger.warning(f"Failed to parse config file {filepath}: {e}")

            # Store configuration snapshot
            await self._store_configuration_snapshot(
                device_id=device_id,
                config_type=config_type,
                file_path=filepath,
                content_hash=content_hash,
                raw_content=raw_content,
                parsed_data=parsed_data,
                change_type=event_type
            )

            self.logger.info(
                f"Processed configuration change: {device_id}:{filepath}:{event_type}"
            )

        except Exception as e:
            self.logger.error(f"Error handling config change {filepath}:{event_type}: {e}")

    def _determine_config_type(self, filepath: str) -> str:
        """Determine configuration type from file path"""
        path_lower = filepath.lower()

        # SWAG proxy configurations - only .conf files in proxy-confs directories
        if "/proxy-confs/" in path_lower and filepath.endswith('.conf'):
            return "nginx_proxy"
        # Docker compose files
        elif ("docker-compose" in path_lower or
              (any(name in path_lower for name in ["compose", "stack"]) and
               filepath.endswith(('.yml', '.yaml')))):
            return "docker_compose"
        # Other specific service configurations
        elif "/traefik/" in path_lower:
            return "traefik"
        elif "/apache" in path_lower:
            return "apache"
        # Generic file type classifications
        elif filepath.endswith(('.yml', '.yaml')):
            return "yaml_config"
        elif filepath.endswith('.json'):
            return "json_config"
        elif filepath.endswith('.conf'):
            return "generic_config"
        else:
            return "unknown"

    async def _parse_config_file(self, filepath: str, content: str) -> dict[str, Any] | None:
        """Basic parsing of configuration files"""
        if not content or content.startswith("ERROR_READING_FILE"):
            return None

        try:
            # Basic YAML/JSON parsing would go here
            # For now, just return basic metadata
            return {
                "file_size": len(content),
                "line_count": len(content.split('\n')),
                "file_type": Path(filepath).suffix,
                "parse_timestamp": datetime.now(UTC).isoformat()
            }
        except Exception:
            return None

    async def _store_configuration_snapshot(
        self,
        device_id: UUID,
        config_type: str,
        file_path: str,
        content_hash: str,
        raw_content: str,
        parsed_data: dict[str, Any] | None,
        change_type: str
    ) -> None:
        """Store configuration snapshot in database"""
        try:
            async with self.db_session_factory() as session:
                snapshot = ConfigurationSnapshot(
                    device_id=device_id,
                    time=datetime.now(UTC),
                    config_type=config_type,
                    file_path=file_path,
                    content_hash=content_hash,
                    raw_content=raw_content,
                    parsed_data=parsed_data,
                    change_type=change_type
                )

                session.add(snapshot)
                await session.commit()

                self.logger.debug(f"Stored configuration snapshot: {device_id}:{file_path}")

        except Exception as e:
            self.logger.error(f"Failed to store configuration snapshot: {e}")
            raise DatabaseOperationError(
                message="Failed to store configuration snapshot",
                operation="store_configuration_snapshot",
                details={"exception": str(e), "file_path": file_path, "config_type": config_type},
            )


# Global service instance
_config_monitoring_service: ConfigurationMonitoringService | None = None


def get_configuration_monitoring_service(
    db_session_factory: async_sessionmaker[AsyncSession] | None = None,
    ssh_client: SSHClient | None = None,
    unified_data_service: UnifiedDataCollectionService | None = None
) -> ConfigurationMonitoringService:
    """Get or create the global configuration monitoring service instance"""
    global _config_monitoring_service

    if _config_monitoring_service is None:
        if not all([db_session_factory, ssh_client, unified_data_service]):
            raise ValueError("All parameters required for first initialization")

        # Help mypy understand these are non-None here
        assert db_session_factory is not None
        assert ssh_client is not None
        assert unified_data_service is not None

        _config_monitoring_service = ConfigurationMonitoringService(
            db_session_factory=db_session_factory,
            ssh_client=ssh_client,
            unified_data_service=unified_data_service
        )

    return _config_monitoring_service
