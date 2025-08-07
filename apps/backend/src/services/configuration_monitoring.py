"""
Configuration Monitoring Service

Real-time configuration monitoring service that watches for changes in configuration
files on remote devices. Uses inotify over SSH for real-time monitoring with
polling fallback for reliability.

Task Master Task #5: Implement Real-Time Configuration Monitoring Service
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Callable, Awaitable, Any, Set
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, insert

from apps.backend.src.models.configuration import ConfigurationSnapshot
from apps.backend.src.models.device import Device
from apps.backend.src.utils.ssh_client import SSHClient, SSHConnectionInfo
from apps.backend.src.services.unified_data_collection import UnifiedDataCollectionService
from apps.backend.src.core.exceptions import (
    DatabaseOperationError,
    SSHConnectionError,
    DataCollectionError,
)

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
        watch_paths: List[str],
        callback: Callable[[str, str, str], Awaitable[None]],
        poll_interval: int = 30
    ):
        self.device_id = device_id
        self.ssh_client = ssh_client
        self.watch_paths = watch_paths
        self.callback = callback
        self.poll_interval = poll_interval
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.file_hashes: Dict[str, str] = {}
        self.logger = logging.getLogger(f"{__name__}.RemoteFileWatcher")
        
    async def start_monitoring(self) -> bool:
        """Start file monitoring (real-time or polling fallback)"""
        if self.is_monitoring:
            return True
            
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
            result = await self.ssh_client.execute_command("which inotifywait")
            if result.return_code != 0:
                return False
                
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
            # Initialize file hashes
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
            async for line in self.ssh_client.execute_streaming_command(inotify_cmd):
                if not self.is_monitoring:
                    break
                    
                # Parse inotify output: filepath:event_type
                if ':' in line:
                    filepath, event_type = line.rsplit(':', 1)
                    await self._handle_file_event(filepath, event_type)
                    
        except Exception as e:
            self.logger.error(f"inotify monitoring failed: {e}")
            # Fall back to polling
            if self.is_monitoring:
                await self._setup_polling_monitoring()
                
    async def _run_polling_monitoring(self) -> None:
        """Run polling monitoring loop"""
        while self.is_monitoring:
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
                # Find all files in watch path
                find_cmd = f"find '{watch_path}' -type f -name '*.yml' -o -name '*.yaml' -o -name '*.conf' -o -name '*.json' 2>/dev/null || true"
                result = await self.ssh_client.execute_command(find_cmd)
                
                if result.return_code == 0:
                    files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                    
                    for filepath in files:
                        try:
                            hash_result = await self.ssh_client.execute_command(f"sha256sum '{filepath}' 2>/dev/null || echo 'ERROR'")
                            if hash_result.return_code == 0 and 'ERROR' not in hash_result.stdout:
                                file_hash = hash_result.stdout.split()[0]
                                self.file_hashes[filepath] = file_hash
                        except Exception as e:
                            self.logger.debug(f"Failed to hash file {filepath}: {e}")
                            
            except Exception as e:
                self.logger.error(f"Failed to scan watch path {watch_path}: {e}")
                
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
    ):
        self.db_session_factory = db_session_factory
        self.ssh_client = ssh_client
        self.unified_data_service = unified_data_service
        self.device_watchers: Dict[UUID, RemoteFileWatcher] = {}
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
        custom_watch_paths: Optional[List[str]] = None
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
    
    async def _get_discovered_config_paths(self, device: Device) -> List[str]:
        """
        Extract configuration paths from device analysis results stored in device tags.
        
        Args:
            device: Device model with analysis results in tags
            
        Returns:
            List of discovered configuration paths to monitor
        """
        discovered_paths = []
        
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
        
    async def get_monitored_devices(self) -> List[UUID]:
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
                    result = await self.ssh_client.execute_command(f"cat '{filepath}'")
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
        
        if "/proxy-confs/" in path_lower or "/nginx/" in path_lower:
            return "nginx_proxy"
        elif "docker-compose" in path_lower:
            return "docker_compose"
        elif "/traefik/" in path_lower:
            return "traefik"
        elif "/apache" in path_lower:
            return "apache"
        elif filepath.endswith(('.yml', '.yaml')):
            return "yaml_config"
        elif filepath.endswith('.json'):
            return "json_config"
        elif filepath.endswith('.conf'):
            return "generic_config"
        else:
            return "unknown"
            
    async def _parse_config_file(self, filepath: str, content: str) -> Optional[Dict[str, Any]]:
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
                "parse_timestamp": datetime.now(timezone.utc).isoformat()
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
        parsed_data: Optional[Dict[str, Any]],
        change_type: str
    ) -> None:
        """Store configuration snapshot in database"""
        try:
            async with self.db_session_factory() as session:
                snapshot = ConfigurationSnapshot(
                    device_id=device_id,
                    time=datetime.now(timezone.utc),
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
            raise DatabaseOperationError(f"Failed to store configuration snapshot: {e}")


# Global service instance
_config_monitoring_service: Optional[ConfigurationMonitoringService] = None


def get_configuration_monitoring_service(
    db_session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    ssh_client: Optional[SSHClient] = None,
    unified_data_service: Optional[UnifiedDataCollectionService] = None
) -> ConfigurationMonitoringService:
    """Get or create the global configuration monitoring service instance"""
    global _config_monitoring_service
    
    if _config_monitoring_service is None:
        if not all([db_session_factory, ssh_client, unified_data_service]):
            raise ValueError("All parameters required for first initialization")
            
        _config_monitoring_service = ConfigurationMonitoringService(
            db_session_factory=db_session_factory,
            ssh_client=ssh_client,
            unified_data_service=unified_data_service
        )
        
    return _config_monitoring_service