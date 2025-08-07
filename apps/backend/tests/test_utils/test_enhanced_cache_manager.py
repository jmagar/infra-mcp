"""
Tests for Enhanced CacheManager with LRU Eviction and Metrics

This module tests the enhanced CacheManager functionality including:
- LRU eviction policy
- Performance metrics tracking
- Memory management
- Cache operations with tracking
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from src.core.exceptions import CacheOperationError
from src.utils.cache_manager import CacheManager, CacheMetrics, get_cache_manager


@pytest.fixture
def sample_device_id():
    """Sample device UUID for testing"""
    return uuid4()


@pytest.fixture
def sample_data():
    """Sample data for caching tests"""
    return {
        "containers": [
            {"name": "test-container", "status": "running", "cpu": 25.5},
            {"name": "other-container", "status": "stopped", "cpu": 0.0}
        ],
        "timestamp": "2024-01-01T10:00:00Z",
        "collection_metadata": {
            "collection_duration_seconds": 1.5,
            "cache_hit": False,
            "force_refresh": False
        }
    }


@pytest_asyncio.fixture
async def cache_manager():
    """Create a test cache manager with small limits for testing"""
    manager = CacheManager(
        redis_url="redis://localhost:9104/1",  # Use different DB for tests
        default_ttl=60,
        max_cache_size=3,  # Small size for eviction testing
        max_memory_mb=1,   # Small memory limit
        eviction_batch_size=2,
        key_prefix="test_cache:",
    )
    
    # Mock Redis client for testing
    mock_redis = AsyncMock()
    manager.redis_client = mock_redis
    manager.logger = MagicMock()
    
    yield manager
    
    # Cleanup
    await manager.disconnect()


class TestEnhancedCacheManager:
    """Test suite for enhanced CacheManager functionality"""
    
    async def test_cache_manager_initialization(self):
        """Test CacheManager initialization with LRU parameters"""
        manager = CacheManager(
            max_cache_size=1000,
            max_memory_mb=50,
            eviction_batch_size=25,
        )
        
        assert manager.max_cache_size == 1000
        assert manager.max_memory_mb == 50
        assert manager.eviction_batch_size == 25
        assert manager.lru_zset_key == "infra_cache:lru_tracker"
        assert manager.metrics_key == "infra_cache:metrics"
        assert manager._metrics["hits"] == 0
        assert manager._metrics["misses"] == 0
    
    async def test_cache_set_with_lru_tracking(self, cache_manager, sample_device_id, sample_data):
        """Test cache set operation with LRU tracking"""
        # Mock Redis operations
        cache_manager.redis_client.zcard.return_value = 0  # Empty cache
        cache_manager.redis_client.pipeline.return_value.__aenter__.return_value = cache_manager.redis_client
        cache_manager.redis_client.pipeline.return_value.__aexit__.return_value = None
        cache_manager.redis_client.execute.return_value = [True, 1]
        
        result = await cache_manager.set("containers", sample_device_id, sample_data)
        
        assert result is True
        
        # Verify Redis operations were called
        cache_manager.redis_client.pipeline.assert_called()
        cache_manager.redis_client.setex.assert_called()
        cache_manager.redis_client.zadd.assert_called()
        
        # Check that zadd was called with LRU tracker key
        zadd_calls = cache_manager.redis_client.zadd.call_args_list
        assert any(call[0][0] == "test_cache:lru_tracker" for call in zadd_calls)
    
    async def test_cache_get_with_lru_update(self, cache_manager, sample_device_id, sample_data):
        """Test cache get operation with LRU access tracking"""
        # Mock cache hit
        cached_data_with_metadata = {
            **sample_data,
            "_cache_metadata": {
                "cached_at": "2024-01-01T10:00:00Z",
                "data_type": "containers",
                "device_id": str(sample_device_id),
                "ttl": 60,
            }
        }
        cache_manager.redis_client.get.return_value = json.dumps(cached_data_with_metadata)
        cache_manager.redis_client.zadd.return_value = 1
        
        result = await cache_manager.get("containers", sample_device_id)
        
        assert result is not None
        assert "containers" in result
        
        # Verify LRU access was updated
        cache_manager.redis_client.zadd.assert_called()
        zadd_call = cache_manager.redis_client.zadd.call_args
        assert zadd_call[0][0] == "test_cache:lru_tracker"
    
    async def test_cache_miss_metrics_tracking(self, cache_manager, sample_device_id):
        """Test metrics tracking for cache misses"""
        # Mock cache miss
        cache_manager.redis_client.get.return_value = None
        
        result = await cache_manager.get("containers", sample_device_id)
        
        assert result is None
        assert cache_manager._metrics["misses"] == 1
        assert cache_manager._metrics["total_operations"] == 1
    
    async def test_cache_hit_metrics_tracking(self, cache_manager, sample_device_id, sample_data):
        """Test metrics tracking for cache hits"""
        # Mock cache hit
        cached_data_with_metadata = {
            **sample_data,
            "_cache_metadata": {
                "cached_at": "2024-01-01T10:00:00Z",
                "data_type": "containers",
                "device_id": str(sample_device_id),
                "ttl": 60,
            }
        }
        cache_manager.redis_client.get.return_value = json.dumps(cached_data_with_metadata)
        cache_manager.redis_client.zadd.return_value = 1
        
        result = await cache_manager.get("containers", sample_device_id)
        
        assert result is not None
        assert cache_manager._metrics["hits"] == 1
        assert cache_manager._metrics["total_operations"] == 1
    
    async def test_lru_eviction_enforcement(self, cache_manager, sample_device_id):
        """Test LRU eviction when cache size limit is exceeded"""
        # Mock cache size exceeding limit
        cache_manager.redis_client.zcard.return_value = 5  # Exceeds max_cache_size=3
        
        # Mock oldest keys for eviction
        oldest_keys = ["old_key_1", "old_key_2", "old_key_3"]
        cache_manager.redis_client.zrange.return_value = oldest_keys
        
        # Mock pipeline operations
        cache_manager.redis_client.pipeline.return_value.__aenter__.return_value = cache_manager.redis_client
        cache_manager.redis_client.pipeline.return_value.__aexit__.return_value = None
        cache_manager.redis_client.execute.return_value = [1, 1, 1, 3]  # Delete results
        
        await cache_manager._enforce_cache_limits()
        
        # Should attempt to evict items
        cache_manager.redis_client.zrange.assert_called()
        cache_manager.redis_client.delete.assert_called()
        cache_manager.redis_client.zrem.assert_called()
    
    async def test_evict_lru_items(self, cache_manager):
        """Test LRU item eviction functionality"""
        oldest_keys = ["key1", "key2", "key3"]
        cache_manager.redis_client.zrange.return_value = oldest_keys
        
        # Mock pipeline operations
        cache_manager.redis_client.pipeline.return_value.__aenter__.return_value = cache_manager.redis_client
        cache_manager.redis_client.pipeline.return_value.__aexit__.return_value = None
        cache_manager.redis_client.execute.return_value = [1, 1, 1, 3]
        
        evicted_count = await cache_manager._evict_lru_items(3)
        
        assert evicted_count == 3
        assert cache_manager._metrics["evictions"] == 3
        
        # Verify Redis operations
        cache_manager.redis_client.zrange.assert_called_with("test_cache:lru_tracker", 0, 2)
        cache_manager.redis_client.zrem.assert_called_with("test_cache:lru_tracker", *oldest_keys)
    
    async def test_cache_delete_with_lru_cleanup(self, cache_manager, sample_device_id):
        """Test cache delete operation removes LRU tracking"""
        # Mock pipeline operations
        cache_manager.redis_client.pipeline.return_value.__aenter__.return_value = cache_manager.redis_client
        cache_manager.redis_client.pipeline.return_value.__aexit__.return_value = None
        cache_manager.redis_client.execute.return_value = [1, 1]  # Delete and zrem results
        
        result = await cache_manager.delete("containers", sample_device_id)
        
        assert result is True
        
        # Verify both cache data and LRU entry were removed
        cache_manager.redis_client.delete.assert_called()
        cache_manager.redis_client.zrem.assert_called()
    
    async def test_get_metrics(self, cache_manager):
        """Test cache metrics retrieval"""
        # Set up some metrics
        cache_manager._metrics = {
            "hits": 10,
            "misses": 5,
            "evictions": 2,
            "total_operations": 15,
            "total_response_time_ms": 150.0,
        }
        
        # Mock Redis operations for cache size
        cache_manager.redis_client.get.return_value = None  # No persisted metrics
        cache_manager.redis_client.zcard.return_value = 8   # Current cache size
        
        metrics = await cache_manager.get_metrics()
        
        assert isinstance(metrics, CacheMetrics)
        assert metrics.hits == 10
        assert metrics.misses == 5
        assert metrics.evictions == 2
        assert metrics.total_operations == 15
        assert metrics.hit_ratio == 10/15  # 66.67%
        assert metrics.average_response_time_ms == 10.0  # 150/15
        assert metrics.cache_size == 8
        assert metrics.memory_usage_mb == 8 * 2.0 / 1024  # ~0.016 MB
    
    async def test_enhanced_health_check(self, cache_manager):
        """Test enhanced health check with LRU metrics"""
        # Mock Redis operations
        cache_manager.redis_client.ping.return_value = True
        cache_manager.redis_client.info.return_value = {
            "redis_version": "6.2.0",
            "used_memory_human": "1.5M",
            "connected_clients": "2",
            "uptime_in_seconds": "3600"
        }
        
        # Mock metrics
        cache_manager._metrics = {
            "hits": 100,
            "misses": 20,
            "evictions": 5,
            "total_operations": 120,
            "total_response_time_ms": 1200.0,
        }
        cache_manager.redis_client.get.return_value = None  # No persisted metrics
        cache_manager.redis_client.zcard.return_value = 50
        
        health_status = await cache_manager.health_check()
        
        assert health_status["service"] == "EnhancedCacheManager"
        assert health_status["status"] == "healthy"
        assert health_status["redis_connected"] is True
        assert "cache_metrics" in health_status
        assert "lru_config" in health_status
        
        cache_metrics = health_status["cache_metrics"]
        assert cache_metrics["hits"] == 100
        assert cache_metrics["misses"] == 20
        assert cache_metrics["evictions"] == 5
        assert cache_metrics["cache_size"] == 50
        assert "83.33%" in cache_metrics["hit_ratio"]  # 100/120
        assert "10.00" in cache_metrics["avg_response_time_ms"]  # 1200/120
        
        lru_config = health_status["lru_config"]
        assert lru_config["max_cache_size"] == 3
        assert lru_config["max_memory_mb"] == 1
        assert lru_config["eviction_batch_size"] == 2
    
    async def test_metrics_persistence(self, cache_manager):
        """Test metrics persistence to Redis"""
        cache_manager.redis_client.setex.return_value = True
        
        # Trigger metrics persistence (every 10 operations)
        cache_manager._metrics["total_operations"] = 10
        
        await cache_manager._persist_metrics()
        
        # Verify metrics were persisted
        cache_manager.redis_client.setex.assert_called()
        setex_call = cache_manager.redis_client.setex.call_args
        assert setex_call[0][0] == "test_cache:metrics"  # Key
        assert setex_call[0][1] == 3600  # TTL (1 hour)
        
        # Verify the data is JSON serialized metrics
        metrics_data = setex_call[0][2]
        parsed_metrics = json.loads(metrics_data)
        assert "total_operations" in parsed_metrics
    
    async def test_factory_function_enhanced_config(self):
        """Test factory function creates enhanced cache manager"""
        with patch('src.utils.cache_manager.CacheManager') as mock_cache_class:
            mock_instance = AsyncMock()
            mock_cache_class.return_value = mock_instance
            
            manager = await get_cache_manager(
                max_cache_size=500,
                max_memory_mb=50,
                eviction_batch_size=25,
            )
            
            # Verify CacheManager was created with enhanced parameters
            mock_cache_class.assert_called_once()
            call_kwargs = mock_cache_class.call_args[1]
            assert call_kwargs["max_cache_size"] == 500
            assert call_kwargs["max_memory_mb"] == 50
            assert call_kwargs["eviction_batch_size"] == 25
            
            # Verify connect was called
            mock_instance.connect.assert_called_once()


class TestLRUEvictionScenarios:
    """Test specific LRU eviction scenarios"""
    
    async def test_sequential_access_pattern(self, cache_manager):
        """Test LRU behavior with sequential access pattern"""
        # Mock cache operations for sequential access
        cache_manager.redis_client.zcard.return_value = 0  # Start empty
        cache_manager.redis_client.pipeline.return_value.__aenter__.return_value = cache_manager.redis_client
        cache_manager.redis_client.pipeline.return_value.__aexit__.return_value = None
        cache_manager.redis_client.execute.return_value = [True, 1]
        
        # Add items sequentially
        device_ids = [uuid4() for _ in range(5)]
        
        for i, device_id in enumerate(device_ids):
            # Mock cache size check (gradually increasing)
            cache_manager.redis_client.zcard.return_value = i
            await cache_manager.set("containers", device_id, {"data": f"container_{i}"})
        
        # Verify LRU tracker was updated for each item
        assert cache_manager.redis_client.zadd.call_count >= 5
    
    async def test_mixed_access_pattern(self, cache_manager, sample_data):
        """Test LRU behavior with mixed read/write access pattern"""
        device_id = uuid4()
        
        # Mock cache hit scenario
        cached_data_with_metadata = {
            **sample_data,
            "_cache_metadata": {
                "cached_at": "2024-01-01T10:00:00Z",
                "data_type": "containers",
                "device_id": str(device_id),
                "ttl": 60,
            }
        }
        cache_manager.redis_client.get.return_value = json.dumps(cached_data_with_metadata)
        cache_manager.redis_client.zadd.return_value = 1
        
        # Perform mixed operations
        await cache_manager.get("containers", device_id)  # Read (should update LRU)
        
        # Verify LRU was updated on read
        cache_manager.redis_client.zadd.assert_called()
        
        # Check metrics were updated
        assert cache_manager._metrics["hits"] == 1
        assert cache_manager._metrics["total_operations"] == 1
    
    async def test_eviction_under_pressure(self, cache_manager):
        """Test cache behavior under eviction pressure"""
        # Simulate cache at capacity
        cache_manager.redis_client.zcard.return_value = 10  # Well over limit of 3
        
        # Mock eviction process
        oldest_keys = [f"old_key_{i}" for i in range(7)]  # 7 items to evict
        cache_manager.redis_client.zrange.return_value = oldest_keys
        
        # Mock pipeline operations
        cache_manager.redis_client.pipeline.return_value.__aenter__.return_value = cache_manager.redis_client
        cache_manager.redis_client.pipeline.return_value.__aexit__.return_value = None
        cache_manager.redis_client.execute.return_value = [1] * len(oldest_keys) + [len(oldest_keys)]
        
        await cache_manager._enforce_cache_limits()
        
        # Should evict enough items to get below limit + batch size
        # (10 - 3 + 2 = 9 items to evict, but only 7 returned)
        cache_manager.redis_client.zrange.assert_called_with("test_cache:lru_tracker", 0, 8)  # 9 items - 1
        
        # Verify eviction metrics were updated
        assert cache_manager._metrics["evictions"] == 7


# Integration test with real Redis (requires running Redis)
@pytest.mark.integration
class TestCacheManagerIntegration:
    """Integration tests with real Redis instance"""
    
    @pytest_asyncio.fixture
    async def real_cache_manager(self):
        """Create cache manager with real Redis connection"""
        manager = CacheManager(
            redis_url="redis://localhost:9104/15",  # Use test DB
            default_ttl=10,  # Short TTL for testing
            max_cache_size=5,
            max_memory_mb=1,
            eviction_batch_size=2,
            key_prefix="integration_test:",
        )
        
        try:
            await manager.connect()
            yield manager
        finally:
            # Cleanup test data
            if manager.redis_client:
                await manager.redis_client.flushdb()
            await manager.disconnect()
    
    async def test_real_lru_eviction(self, real_cache_manager):
        """Test LRU eviction with real Redis"""
        device_ids = [uuid4() for _ in range(7)]  # More than max_cache_size=5
        
        # Fill cache beyond capacity
        for i, device_id in enumerate(device_ids):
            await real_cache_manager.set("test", device_id, {"index": i})
        
        # Check that some eviction occurred
        metrics = await real_cache_manager.get_metrics()
        assert metrics.cache_size <= 5  # Should not exceed limit
        assert metrics.evictions > 0  # Some items should have been evicted
    
    async def test_real_metrics_tracking(self, real_cache_manager):
        """Test metrics tracking with real Redis operations"""
        device_id = uuid4()
        test_data = {"test": "data", "timestamp": time.time()}
        
        # Perform cache operations
        await real_cache_manager.set("test", device_id, test_data)  # Cache set
        result1 = await real_cache_manager.get("test", device_id)   # Cache hit
        result2 = await real_cache_manager.get("missing", device_id)  # Cache miss
        
        assert result1 is not None
        assert result2 is None
        
        # Check metrics
        metrics = await real_cache_manager.get_metrics()
        assert metrics.hits >= 1
        assert metrics.misses >= 1
        assert metrics.total_operations >= 2
        assert metrics.hit_ratio > 0