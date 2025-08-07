"""
Integration tests for ConfigurationMonitoringService.

Tests the real-time configuration monitoring functionality including
file watching, change detection, and database storage.
"""

import asyncio
import tempfile
import os
import pytest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from src.services.configuration_monitoring import (
    ConfigurationMonitoringService,
    RemoteFileWatcher,
    get_configuration_monitoring_service
)
from src.models.configuration import ConfigurationSnapshot
from src.models.device import Device
from src.utils.ssh_client import SSHClient, CommandResult
from src.services.unified_data_collection import UnifiedDataCollectionService


class TestRemoteFileWatcher:
    """Test the RemoteFileWatcher class"""

    @pytest.fixture
    def mock_ssh_client(self):
        """Mock SSH client for testing"""
        ssh_client = AsyncMock(spec=SSHClient)
        return ssh_client

    @pytest.fixture
    def mock_callback(self):
        """Mock callback function for file events"""
        return AsyncMock()

    @pytest.fixture
    def file_watcher(self, mock_ssh_client, mock_callback):
        """Create a RemoteFileWatcher instance for testing"""
        device_id = uuid4()
        watch_paths = ["/test/path1", "/test/path2"]
        
        return RemoteFileWatcher(
            device_id=device_id,
            ssh_client=mock_ssh_client,
            watch_paths=watch_paths,
            callback=mock_callback,
            poll_interval=5  # Short interval for testing
        )

    @pytest.mark.asyncio
    async def test_remote_file_watcher_initialization(self, file_watcher, mock_ssh_client, mock_callback):
        """Test RemoteFileWatcher initialization"""
        assert file_watcher.ssh_client == mock_ssh_client
        assert file_watcher.callback == mock_callback
        assert file_watcher.watch_paths == ["/test/path1", "/test/path2"]
        assert file_watcher.poll_interval == 5
        assert file_watcher.is_monitoring is False
        assert file_watcher.monitor_task is None
        assert file_watcher.file_hashes == {}

    @pytest.mark.asyncio
    async def test_start_monitoring_with_inotify_success(self, file_watcher, mock_ssh_client):
        """Test successful start of monitoring with inotify"""
        # Mock inotifywait availability
        mock_ssh_client.execute_command.return_value = CommandResult(
            return_code=0, stdout="", stderr=""
        )
        
        # Mock the streaming command
        async def mock_streaming():
            yield "/test/path1/file.conf:MODIFY"
            yield "/test/path2/docker-compose.yml:CREATE"
        
        mock_ssh_client.execute_streaming_command.return_value = mock_streaming()
        
        # Start monitoring
        result = await file_watcher.start_monitoring()
        assert result is True
        assert file_watcher.is_monitoring is True
        assert file_watcher.monitor_task is not None

    @pytest.mark.asyncio
    async def test_start_monitoring_fallback_to_polling(self, file_watcher, mock_ssh_client):
        """Test fallback to polling when inotify is unavailable"""
        # Mock inotifywait not available
        mock_ssh_client.execute_command.return_value = CommandResult(
            return_code=1, stdout="", stderr="command not found"
        )
        
        # Mock find command for polling setup
        find_results = [
            CommandResult(return_code=0, stdout="/test/path1/file1.conf\n/test/path1/file2.yml", stderr=""),
            CommandResult(return_code=0, stdout="/test/path2/docker-compose.yml", stderr="")
        ]
        
        # Mock sha256sum results
        hash_results = [
            CommandResult(return_code=0, stdout="abc123 /test/path1/file1.conf", stderr=""),
            CommandResult(return_code=0, stdout="def456 /test/path1/file2.yml", stderr=""),
            CommandResult(return_code=0, stdout="ghi789 /test/path2/docker-compose.yml", stderr="")
        ]
        
        mock_ssh_client.execute_command.side_effect = [
            CommandResult(return_code=1, stdout="", stderr=""),  # inotifywait check
            *find_results,
            *hash_results
        ]
        
        result = await file_watcher.start_monitoring()
        assert result is True
        assert file_watcher.is_monitoring is True
        assert len(file_watcher.file_hashes) == 3

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, file_watcher, mock_ssh_client):
        """Test stopping file monitoring"""
        # Set up a mock monitoring task
        file_watcher.is_monitoring = True
        file_watcher.monitor_task = AsyncMock()
        file_watcher.monitor_task.done.return_value = False
        
        await file_watcher.stop_monitoring()
        
        assert file_watcher.is_monitoring is False
        file_watcher.monitor_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_file_event(self, file_watcher, mock_callback):
        """Test file event handling"""
        filepath = "/test/path/config.conf"
        event_type = "MODIFY"
        device_id = str(file_watcher.device_id)
        
        await file_watcher._handle_file_event(filepath, event_type)
        
        mock_callback.assert_called_once_with(filepath, event_type, device_id)

    @pytest.mark.asyncio
    async def test_check_for_changes_detect_modifications(self, file_watcher, mock_ssh_client, mock_callback):
        """Test detecting file modifications during polling"""
        # Set initial file hashes
        file_watcher.file_hashes = {
            "/test/file1.conf": "old_hash_1",
            "/test/file2.yml": "old_hash_2"
        }
        
        # Mock find and hash commands for update
        mock_ssh_client.execute_command.side_effect = [
            # Find commands
            CommandResult(return_code=0, stdout="/test/file1.conf\n/test/file2.yml\n/test/file3.json", stderr=""),
            CommandResult(return_code=0, stdout="", stderr=""),  # Empty second path
            # Hash commands
            CommandResult(return_code=0, stdout="new_hash_1 /test/file1.conf", stderr=""),  # Modified
            CommandResult(return_code=0, stdout="old_hash_2 /test/file2.yml", stderr=""),  # Unchanged
            CommandResult(return_code=0, stdout="new_hash_3 /test/file3.json", stderr=""),  # New file
        ]
        
        await file_watcher._check_for_changes()
        
        # Should detect one modification and one new file
        assert mock_callback.call_count == 2
        mock_callback.assert_any_call("/test/file1.conf", "MODIFY", str(file_watcher.device_id))
        mock_callback.assert_any_call("/test/file3.json", "CREATE", str(file_watcher.device_id))


class TestConfigurationMonitoringService:
    """Test the ConfigurationMonitoringService class"""

    @pytest.fixture
    def mock_db_session_factory(self):
        """Mock database session factory"""
        return AsyncMock(spec=async_sessionmaker)

    @pytest.fixture
    def mock_ssh_client(self):
        """Mock SSH client"""
        return AsyncMock(spec=SSHClient)

    @pytest.fixture
    def mock_unified_data_service(self):
        """Mock unified data collection service"""
        return AsyncMock(spec=UnifiedDataCollectionService)

    @pytest.fixture
    def monitoring_service(self, mock_db_session_factory, mock_ssh_client, mock_unified_data_service):
        """Create ConfigurationMonitoringService instance"""
        return ConfigurationMonitoringService(
            db_session_factory=mock_db_session_factory,
            ssh_client=mock_ssh_client,
            unified_data_service=mock_unified_data_service
        )

    def test_service_initialization(self, monitoring_service, mock_db_session_factory, mock_ssh_client, mock_unified_data_service):
        """Test service initialization"""
        assert monitoring_service.db_session_factory == mock_db_session_factory
        assert monitoring_service.ssh_client == mock_ssh_client
        assert monitoring_service.unified_data_service == mock_unified_data_service
        assert monitoring_service.device_watchers == {}
        assert len(monitoring_service.default_watch_paths) == 6

    def test_default_watch_paths(self, monitoring_service):
        """Test default watch paths are correctly defined"""
        expected_paths = [
            "/mnt/appdata/swag/nginx/proxy-confs",
            "/opt/docker-compose",
            "/home/*/docker-compose.yml",
            "/etc/nginx",
            "/etc/apache2",
            "/etc/traefik",
        ]
        assert monitoring_service.default_watch_paths == expected_paths

    @pytest.mark.asyncio
    async def test_setup_device_monitoring_success(self, monitoring_service, mock_db_session_factory):
        """Test successful device monitoring setup"""
        device_id = uuid4()
        
        # Mock database session and device lookup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock device query result
        mock_device = Device(
            id=device_id,
            hostname="test-device",
            ip_address="192.168.1.100",
            device_type="server",
            status="active",
            ssh_port=22,
            monitoring_enabled=True
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        mock_session.execute.return_value = mock_result
        
        # Mock RemoteFileWatcher creation and start
        with patch('src.services.configuration_monitoring.RemoteFileWatcher') as mock_watcher_class:
            mock_watcher = AsyncMock()
            mock_watcher.start_monitoring.return_value = True
            mock_watcher_class.return_value = mock_watcher
            
            result = await monitoring_service.setup_device_monitoring(device_id)
            
            assert result is True
            assert device_id in monitoring_service.device_watchers
            mock_watcher.start_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_device_monitoring_device_not_found(self, monitoring_service, mock_db_session_factory):
        """Test device monitoring setup when device is not found"""
        device_id = uuid4()
        
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock device query returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await monitoring_service.setup_device_monitoring(device_id)
        
        assert result is False
        assert device_id not in monitoring_service.device_watchers

    @pytest.mark.asyncio
    async def test_setup_device_monitoring_with_custom_paths(self, monitoring_service, mock_db_session_factory):
        """Test device monitoring setup with custom watch paths"""
        device_id = uuid4()
        custom_paths = ["/custom/path1", "/custom/path2"]
        
        # Mock database session and device lookup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_session_factory.return_value.__aenter__.return_value = mock_session
        
        mock_device = Device(
            id=device_id,
            hostname="test-device",
            ip_address="192.168.1.100",
            device_type="server",
            status="active",
            ssh_port=22,
            monitoring_enabled=True
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        mock_session.execute.return_value = mock_result
        
        with patch('src.services.configuration_monitoring.RemoteFileWatcher') as mock_watcher_class:
            mock_watcher = AsyncMock()
            mock_watcher.start_monitoring.return_value = True
            mock_watcher_class.return_value = mock_watcher
            
            result = await monitoring_service.setup_device_monitoring(device_id, custom_paths)
            
            assert result is True
            # Verify custom paths were used
            mock_watcher_class.assert_called_once()
            call_args = mock_watcher_class.call_args
            assert call_args[1]['watch_paths'] == custom_paths

    @pytest.mark.asyncio
    async def test_stop_device_monitoring(self, monitoring_service):
        """Test stopping device monitoring"""
        device_id = uuid4()
        
        # Add a mock watcher to the service
        mock_watcher = AsyncMock()
        monitoring_service.device_watchers[device_id] = mock_watcher
        
        await monitoring_service.stop_device_monitoring(device_id)
        
        mock_watcher.stop_monitoring.assert_called_once()
        assert device_id not in monitoring_service.device_watchers

    @pytest.mark.asyncio
    async def test_stop_all_monitoring(self, monitoring_service):
        """Test stopping all device monitoring"""
        device_ids = [uuid4(), uuid4(), uuid4()]
        
        # Add mock watchers to the service
        mock_watchers = []
        for device_id in device_ids:
            mock_watcher = AsyncMock()
            mock_watchers.append(mock_watcher)
            monitoring_service.device_watchers[device_id] = mock_watcher
        
        await monitoring_service.stop_all_monitoring()
        
        # Verify all watchers were stopped
        for mock_watcher in mock_watchers:
            mock_watcher.stop_monitoring.assert_called_once()
        
        assert len(monitoring_service.device_watchers) == 0

    @pytest.mark.asyncio
    async def test_get_monitored_devices(self, monitoring_service):
        """Test getting list of monitored devices"""
        device_ids = [uuid4(), uuid4()]
        
        # Add devices to monitoring
        for device_id in device_ids:
            monitoring_service.device_watchers[device_id] = AsyncMock()
        
        monitored = await monitoring_service.get_monitored_devices()
        
        assert len(monitored) == 2
        assert all(device_id in monitored for device_id in device_ids)

    @pytest.mark.asyncio
    async def test_handle_config_change_modify_event(self, monitoring_service, mock_ssh_client, mock_db_session_factory):
        """Test handling configuration file modification event"""
        device_id = uuid4()
        filepath = "/mnt/appdata/swag/nginx/proxy-confs/service.conf"
        event_type = "MODIFY"
        
        # Mock file content reading
        file_content = """server {
    listen 443 ssl;
    server_name service.example.com;
    location / {
        proxy_pass http://192.168.1.100:8080;
    }
}"""
        mock_ssh_client.execute_command.return_value = CommandResult(
            return_code=0, stdout=file_content, stderr=""
        )
        
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_session_factory.return_value.__aenter__.return_value = mock_session
        
        await monitoring_service._handle_config_change(filepath, event_type, str(device_id))
        
        # Verify SSH command was called to read file
        mock_ssh_client.execute_command.assert_called_once_with(f"cat '{filepath}'")
        
        # Verify database session was used
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify ConfigurationSnapshot was created with correct data
        added_snapshot = mock_session.add.call_args[0][0]
        assert isinstance(added_snapshot, ConfigurationSnapshot)
        assert added_snapshot.device_id == device_id
        assert added_snapshot.config_type == "nginx_proxy"
        assert added_snapshot.file_path == filepath
        assert added_snapshot.raw_content == file_content
        assert added_snapshot.change_type == event_type
        assert added_snapshot.content_hash is not None

    @pytest.mark.asyncio
    async def test_handle_config_change_delete_event(self, monitoring_service, mock_db_session_factory):
        """Test handling configuration file deletion event"""
        device_id = uuid4()
        filepath = "/opt/docker-compose/service/docker-compose.yml"
        event_type = "DELETE"
        
        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_session_factory.return_value.__aenter__.return_value = mock_session
        
        await monitoring_service._handle_config_change(filepath, event_type, str(device_id))
        
        # Verify database session was used
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Verify ConfigurationSnapshot was created for deletion
        added_snapshot = mock_session.add.call_args[0][0]
        assert isinstance(added_snapshot, ConfigurationSnapshot)
        assert added_snapshot.device_id == device_id
        assert added_snapshot.config_type == "docker_compose"
        assert added_snapshot.file_path == filepath
        assert added_snapshot.raw_content == ""
        assert added_snapshot.content_hash == ""
        assert added_snapshot.change_type == event_type

    def test_determine_config_type(self, monitoring_service):
        """Test configuration type determination from file paths"""
        test_cases = [
            ("/mnt/appdata/swag/nginx/proxy-confs/service.conf", "nginx_proxy"),
            ("/etc/nginx/sites-available/default", "nginx_proxy"),
            ("/opt/docker-compose/service/docker-compose.yml", "docker_compose"),
            ("/home/user/docker-compose.yaml", "docker_compose"),
            ("/etc/traefik/traefik.yml", "traefik"),
            ("/etc/apache2/sites-available/000-default.conf", "apache"),
            ("/path/to/config.json", "json_config"),
            ("/path/to/config.yml", "yaml_config"),
            ("/path/to/service.conf", "generic_config"),
            ("/path/to/unknown.txt", "unknown"),
        ]
        
        for filepath, expected_type in test_cases:
            result = monitoring_service._determine_config_type(filepath)
            assert result == expected_type, f"Failed for {filepath}: expected {expected_type}, got {result}"

    @pytest.mark.asyncio
    async def test_parse_config_file(self, monitoring_service):
        """Test basic configuration file parsing"""
        filepath = "/test/config.yml"
        content = """
# Test configuration
server:
  host: localhost
  port: 8080
"""
        
        result = await monitoring_service._parse_config_file(filepath, content)
        
        assert result is not None
        assert "file_size" in result
        assert "line_count" in result
        assert "file_type" in result
        assert "parse_timestamp" in result
        assert result["file_size"] == len(content)
        assert result["file_type"] == ".yml"

    @pytest.mark.asyncio
    async def test_parse_config_file_empty_content(self, monitoring_service):
        """Test parsing empty or error content"""
        # Test empty content
        result = await monitoring_service._parse_config_file("/test/file", "")
        assert result is None
        
        # Test error content
        result = await monitoring_service._parse_config_file("/test/file", "ERROR_READING_FILE: permission denied")
        assert result is None


class TestServiceFactory:
    """Test the service factory function"""

    @pytest.mark.asyncio
    async def test_get_configuration_monitoring_service(self):
        """Test the service factory function"""
        mock_db_session_factory = AsyncMock(spec=async_sessionmaker)
        mock_ssh_client = AsyncMock(spec=SSHClient)
        mock_unified_data_service = AsyncMock(spec=UnifiedDataCollectionService)
        
        service = get_configuration_monitoring_service(
            db_session_factory=mock_db_session_factory,
            ssh_client=mock_ssh_client,
            unified_data_service=mock_unified_data_service
        )
        
        assert isinstance(service, ConfigurationMonitoringService)
        assert service.db_session_factory == mock_db_session_factory
        assert service.ssh_client == mock_ssh_client
        assert service.unified_data_service == mock_unified_data_service

    def test_get_configuration_monitoring_service_singleton(self):
        """Test that the service factory returns singleton instance"""
        mock_db_session_factory = AsyncMock(spec=async_sessionmaker)
        mock_ssh_client = AsyncMock(spec=SSHClient)
        mock_unified_data_service = AsyncMock(spec=UnifiedDataCollectionService)
        
        # Reset the global service instance
        import src.services.configuration_monitoring as config_monitoring_module
        config_monitoring_module._config_monitoring_service = None
        
        service1 = get_configuration_monitoring_service(
            db_session_factory=mock_db_session_factory,
            ssh_client=mock_ssh_client,
            unified_data_service=mock_unified_data_service
        )
        
        service2 = get_configuration_monitoring_service()
        
        assert service1 is service2

    def test_get_configuration_monitoring_service_missing_params(self):
        """Test service factory with missing parameters"""
        # Reset the global service instance
        import src.services.configuration_monitoring as config_monitoring_module
        config_monitoring_module._config_monitoring_service = None
        
        with pytest.raises(ValueError, match="All parameters required for first initialization"):
            get_configuration_monitoring_service()


class TestIntegrationScenarios:
    """Integration test scenarios"""

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_workflow(self):
        """Test complete monitoring workflow from setup to change detection"""
        device_id = uuid4()
        
        # Mock dependencies
        mock_db_session_factory = AsyncMock(spec=async_sessionmaker)
        mock_ssh_client = AsyncMock(spec=SSHClient)
        mock_unified_data_service = AsyncMock(spec=UnifiedDataCollectionService)
        
        # Create service
        service = ConfigurationMonitoringService(
            db_session_factory=mock_db_session_factory,
            ssh_client=mock_ssh_client,
            unified_data_service=mock_unified_data_service
        )
        
        # Mock database session and device lookup
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db_session_factory.return_value.__aenter__.return_value = mock_session
        
        mock_device = Device(
            id=device_id,
            hostname="test-device",
            ip_address="192.168.1.100",
            device_type="server",
            status="active",
            ssh_port=22,
            monitoring_enabled=True
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_device
        mock_session.execute.return_value = mock_result
        
        # Mock inotify unavailable (will use polling)
        mock_ssh_client.execute_command.side_effect = [
            CommandResult(return_code=1, stdout="", stderr=""),  # inotifywait not found
            CommandResult(return_code=0, stdout="/test/config.yml", stderr=""),  # find results
            CommandResult(return_code=0, stdout="", stderr=""),  # empty find results for other paths
            CommandResult(return_code=0, stdout="abc123 /test/config.yml", stderr=""),  # initial hash
        ]
        
        # Set up monitoring
        with patch('src.services.configuration_monitoring.RemoteFileWatcher') as mock_watcher_class:
            mock_watcher = AsyncMock()
            mock_watcher.start_monitoring.return_value = True
            mock_watcher_class.return_value = mock_watcher
            
            result = await service.setup_device_monitoring(device_id, ["/test"])
            assert result is True
            assert device_id in service.device_watchers
        
        # Simulate file change event
        file_content = "updated configuration content"
        mock_ssh_client.execute_command.return_value = CommandResult(
            return_code=0, stdout=file_content, stderr=""
        )
        
        await service._handle_config_change("/test/config.yml", "MODIFY", str(device_id))
        
        # Verify configuration snapshot was stored
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
        
        # Clean up
        await service.stop_device_monitoring(device_id)
        assert device_id not in service.device_watchers