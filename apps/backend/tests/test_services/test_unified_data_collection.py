"""
Unit tests for UnifiedDataCollectionService
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.unified_data_collection import (
    UnifiedDataCollectionService,
    get_unified_data_collection_service,
)
from src.core.exceptions import DataCollectionError


@pytest.fixture
def mock_db_session_factory():
    """Mock database session factory"""
    factory = MagicMock()
    session = AsyncMock()
    factory.return_value.__aenter__.return_value = session
    factory.return_value.__aexit__.return_value = None
    return factory


@pytest.fixture
def mock_ssh_client():
    """Mock SSH client manager"""
    return MagicMock()


@pytest.fixture
def mock_ssh_command_manager():
    """Mock SSH command manager"""
    return MagicMock()


@pytest.fixture
def service(mock_db_session_factory, mock_ssh_client, mock_ssh_command_manager):
    """Create UnifiedDataCollectionService instance for testing"""
    return UnifiedDataCollectionService(
        db_session_factory=mock_db_session_factory,
        ssh_client=mock_ssh_client,
        ssh_command_manager=mock_ssh_command_manager,
    )


class TestUnifiedDataCollectionServiceInitialization:
    """Test service initialization"""

    def test_service_initialization_with_all_dependencies(
        self, mock_db_session_factory, mock_ssh_client, mock_ssh_command_manager
    ):
        """Test that service initializes correctly with all dependencies"""
        service = UnifiedDataCollectionService(
            db_session_factory=mock_db_session_factory,
            ssh_client=mock_ssh_client,
            ssh_command_manager=mock_ssh_command_manager,
        )
        
        assert service.db_session_factory == mock_db_session_factory
        assert service.ssh_client == mock_ssh_client
        assert service.ssh_command_manager == mock_ssh_command_manager
        assert isinstance(service.freshness_thresholds, dict)
        assert len(service.freshness_thresholds) > 0

    def test_service_initialization_with_minimal_dependencies(
        self, mock_db_session_factory, mock_ssh_client
    ):
        """Test that service initializes correctly with minimal dependencies"""
        service = UnifiedDataCollectionService(
            db_session_factory=mock_db_session_factory,
            ssh_client=mock_ssh_client,
        )
        
        assert service.db_session_factory == mock_db_session_factory
        assert service.ssh_client == mock_ssh_client
        assert service.ssh_command_manager is None

    def test_default_freshness_thresholds(self, service):
        """Test that default freshness thresholds are set correctly"""
        expected_thresholds = {
            "containers": 300,
            "system_metrics": 600,
            "drive_health": 3600,
            "network_config": 1800,
            "service_dependencies": 3600,
            "zfs_pools": 900,
            "zfs_datasets": 1800,
            "zfs_snapshots": 600,
            "proxy_configurations": 1800,
            "system_logs": 300,
        }
        
        for data_type, expected_threshold in expected_thresholds.items():
            assert service.freshness_thresholds[data_type] == expected_threshold


class TestFreshnessThresholdManagement:
    """Test freshness threshold management methods"""

    def test_get_freshness_threshold_existing_type(self, service):
        """Test getting freshness threshold for existing data type"""
        threshold = service.get_freshness_threshold("containers")
        assert threshold == 300

    def test_get_freshness_threshold_nonexistent_type(self, service):
        """Test getting freshness threshold for nonexistent data type returns default"""
        threshold = service.get_freshness_threshold("nonexistent_type")
        assert threshold == 600  # Default 10 minutes

    def test_set_freshness_threshold_valid(self, service):
        """Test setting valid freshness threshold"""
        service.set_freshness_threshold("containers", 120)
        assert service.freshness_thresholds["containers"] == 120

    def test_set_freshness_threshold_new_type(self, service):
        """Test setting freshness threshold for new data type"""
        service.set_freshness_threshold("new_data_type", 1200)
        assert service.freshness_thresholds["new_data_type"] == 1200

    def test_set_freshness_threshold_invalid_value(self, service):
        """Test setting invalid freshness threshold raises ValueError"""
        with pytest.raises(ValueError, match="Freshness threshold must be positive"):
            service.set_freshness_threshold("containers", 0)
        
        with pytest.raises(ValueError, match="Freshness threshold must be positive"):
            service.set_freshness_threshold("containers", -100)


class TestDataFreshnessChecking:
    """Test data freshness checking logic"""

    def test_is_data_fresh_with_fresh_data(self, service):
        """Test that fresh data is correctly identified as fresh"""
        now = datetime.now(timezone.utc)
        cached_data = {
            "collected_at": now.isoformat(),
            "data": "test_data"
        }
        
        assert service._is_data_fresh(cached_data, "containers") is True

    def test_is_data_fresh_with_stale_data(self, service):
        """Test that stale data is correctly identified as stale"""
        # Data collected 10 minutes ago, but containers threshold is 5 minutes
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        cached_data = {
            "collected_at": stale_time.isoformat(),
            "data": "test_data"
        }
        
        assert service._is_data_fresh(cached_data, "containers") is False

    def test_is_data_fresh_with_missing_timestamp(self, service):
        """Test that data without timestamp is considered stale"""
        cached_data = {"data": "test_data"}
        
        assert service._is_data_fresh(cached_data, "containers") is False

    def test_is_data_fresh_with_invalid_timestamp(self, service):
        """Test that data with invalid timestamp is considered stale"""
        cached_data = {
            "collected_at": "invalid_timestamp",
            "data": "test_data"
        }
        
        assert service._is_data_fresh(cached_data, "containers") is False

    def test_is_data_fresh_with_edge_case_timestamp(self, service):
        """Test edge case timestamp formats"""
        # Test with Z suffix
        now = datetime.now(timezone.utc)
        cached_data = {
            "collected_at": now.isoformat().replace("+00:00", "Z"),
            "data": "test_data"
        }
        
        assert service._is_data_fresh(cached_data, "containers") is True

    def test_is_data_fresh_with_naive_timestamp(self, service):
        """Test timestamp without timezone info (assumes UTC)"""
        now = datetime.now()  # Naive datetime
        cached_data = {
            "collected_at": now.isoformat(),
            "data": "test_data"
        }
        
        # Should still work by assuming UTC
        assert service._is_data_fresh(cached_data, "containers") is True


class TestGetFreshData:
    """Test the main get_fresh_data method"""

    @pytest.mark.asyncio
    async def test_get_fresh_data_force_refresh(self, service):
        """Test get_fresh_data with force_refresh=True"""
        device_id = uuid4()
        
        with patch.object(service, '_collect_fresh_data') as mock_collect, \
             patch.object(service, '_cache_data') as mock_cache:
            
            mock_collect.return_value = {"test": "data"}
            
            result = await service.get_fresh_data(
                "containers", device_id, force_refresh=True
            )
            
            assert result == {"test": "data"}
            mock_collect.assert_called_once_with("containers", device_id)
            mock_cache.assert_called_once_with("containers", device_id, {"test": "data"})

    @pytest.mark.asyncio
    async def test_get_fresh_data_uses_cache_when_fresh(self, service):
        """Test get_fresh_data uses cached data when fresh"""
        device_id = uuid4()
        cached_data = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "data": "cached_data"
        }
        
        with patch.object(service, '_get_cached_data') as mock_get_cache, \
             patch.object(service, '_is_data_fresh') as mock_is_fresh, \
             patch.object(service, '_collect_fresh_data') as mock_collect:
            
            mock_get_cache.return_value = cached_data
            mock_is_fresh.return_value = True
            
            result = await service.get_fresh_data("containers", device_id)
            
            assert result == cached_data
            mock_collect.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_fresh_data_collects_when_stale(self, service):
        """Test get_fresh_data collects fresh data when cache is stale"""
        device_id = uuid4()
        cached_data = {
            "collected_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "data": "stale_data"
        }
        fresh_data = {"data": "fresh_data"}
        
        with patch.object(service, '_get_cached_data') as mock_get_cache, \
             patch.object(service, '_is_data_fresh') as mock_is_fresh, \
             patch.object(service, '_collect_fresh_data') as mock_collect, \
             patch.object(service, '_cache_data') as mock_cache:
            
            mock_get_cache.return_value = cached_data
            mock_is_fresh.return_value = False
            mock_collect.return_value = fresh_data
            
            result = await service.get_fresh_data("containers", device_id)
            
            assert result == fresh_data
            mock_collect.assert_called_once_with("containers", device_id)
            mock_cache.assert_called_once_with("containers", device_id, fresh_data)

    @pytest.mark.asyncio
    async def test_get_fresh_data_handles_collection_error(self, service):
        """Test get_fresh_data handles collection errors properly"""
        device_id = uuid4()
        
        with patch.object(service, '_get_cached_data') as mock_get_cache, \
             patch.object(service, '_collect_fresh_data') as mock_collect:
            
            mock_get_cache.return_value = None
            mock_collect.side_effect = Exception("Collection failed")
            
            with pytest.raises(DataCollectionError):
                await service.get_fresh_data("containers", device_id)


class TestHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, service, mock_db_session_factory):
        """Test health check when all components are healthy"""
        # Mock successful database connection
        session = AsyncMock()
        mock_db_session_factory.return_value.__aenter__.return_value = session
        
        result = await service.health_check()
        
        assert result["service"] == "UnifiedDataCollectionService"
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert result["components"]["database"]["status"] == "healthy"
        assert result["components"]["ssh_client"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_database_unhealthy(self, service, mock_db_session_factory):
        """Test health check when database is unhealthy"""
        # Mock failed database connection
        mock_db_session_factory.side_effect = Exception("Database connection failed")
        
        result = await service.health_check()
        
        assert result["status"] == "degraded"
        assert result["components"]["database"]["status"] == "unhealthy"
        assert "Database connection failed" in result["components"]["database"]["message"]

    @pytest.mark.asyncio
    async def test_health_check_no_ssh_client(self, mock_db_session_factory):
        """Test health check when SSH client is not available"""
        service = UnifiedDataCollectionService(
            db_session_factory=mock_db_session_factory,
            ssh_client=None,
        )
        
        # Mock successful database connection
        session = AsyncMock()
        mock_db_session_factory.return_value.__aenter__.return_value = session
        
        result = await service.health_check()
        
        assert result["components"]["ssh_client"]["status"] == "unavailable"
        assert "not configured" in result["components"]["ssh_client"]["message"]


class TestFactoryFunction:
    """Test the factory function"""

    def test_get_unified_data_collection_service(self, mock_db_session_factory, mock_ssh_client):
        """Test factory function creates service correctly"""
        service = get_unified_data_collection_service(
            db_session_factory=mock_db_session_factory,
            ssh_client=mock_ssh_client,
        )
        
        assert isinstance(service, UnifiedDataCollectionService)
        assert service.db_session_factory == mock_db_session_factory
        assert service.ssh_client == mock_ssh_client

    def test_get_unified_data_collection_service_with_all_params(
        self, mock_db_session_factory, mock_ssh_client, mock_ssh_command_manager
    ):
        """Test factory function with all parameters"""
        service = get_unified_data_collection_service(
            db_session_factory=mock_db_session_factory,
            ssh_client=mock_ssh_client,
            ssh_command_manager=mock_ssh_command_manager,
        )
        
        assert isinstance(service, UnifiedDataCollectionService)
        assert service.db_session_factory == mock_db_session_factory
        assert service.ssh_client == mock_ssh_client
        assert service.ssh_command_manager == mock_ssh_command_manager