"""
Cache Manager for Infrastructure Data

Provides Redis-based caching functionality for infrastructure data collection,
implementing intelligent cache management with LRU eviction, performance metrics,
and memory-aware cache operations.
"""

from datetime import UTC, datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional, NamedTuple
from uuid import UUID

import redis.asyncio as redis
from redis.exceptions import RedisError

from apps.backend.src.core.exceptions import CacheOperationError

logger = logging.getLogger(__name__)


class CacheMetrics(NamedTuple):
    """Cache performance metrics"""
    hits: int
    misses: int
    evictions: int
    total_operations: int
    average_response_time_ms: float
    hit_ratio: float
    cache_size: int
    memory_usage_mb: float


class CacheManager:
    """
    Enhanced Redis-based cache manager for infrastructure data.
    
    Provides async cache operations with TTL support, LRU eviction policy,
    performance metrics tracking, and memory-aware cache management.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:9104/0",
        default_ttl: int = 300,
        key_prefix: str = "infra_cache:",
        max_cache_size: int = 1000,
        max_memory_mb: int = 100,
        eviction_batch_size: int = 50,
    ):
        """
        Initialize the enhanced CacheManager.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds for cached items
            key_prefix: Prefix for all cache keys to avoid conflicts
            max_cache_size: Maximum number of items in cache before eviction
            max_memory_mb: Maximum memory usage in MB before eviction
            eviction_batch_size: Number of items to evict at once when limits exceeded
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.max_cache_size = max_cache_size
        self.max_memory_mb = max_memory_mb
        self.eviction_batch_size = eviction_batch_size
        self.redis_client: redis.Redis | None = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # LRU tracking key names
        self.lru_zset_key = f"{key_prefix}lru_tracker"
        self.metrics_key = f"{key_prefix}metrics"

        # Performance metrics
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_operations": 0,
            "total_response_time_ms": 0.0,
        }

    async def connect(self) -> None:
        """Establish Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Successfully connected to Redis at %s", self.redis_url)
        except RedisError as e:
            self.logger.error("Failed to connect to Redis: %s", str(e))
            self.redis_client = None
            raise CacheOperationError(f"Redis connection failed: {str(e)}") from e

    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.aclose()
                self.logger.info("Redis connection closed")
            except Exception as e:
                self.logger.warning("Error closing Redis connection: %s", str(e))
            finally:
                self.redis_client = None

    def _build_cache_key(self, data_type: str, device_id: UUID, additional_key: str = "") -> str:
        """
        Build a standardized cache key.
        
        Args:
            data_type: Type of data being cached
            device_id: UUID of the target device
            additional_key: Optional additional key component
            
        Returns:
            Formatted cache key
        """
        key_parts = [self.key_prefix, data_type, str(device_id)]
        if additional_key:
            key_parts.append(additional_key)
        return ":".join(key_parts)

    async def get(
        self,
        data_type: str,
        device_id: UUID,
        additional_key: str = "",
    ) -> dict[str, Any] | None:
        """
        Retrieve data from cache with LRU tracking.
        
        Args:
            data_type: Type of data to retrieve
            device_id: UUID of the target device
            additional_key: Optional additional key component
            
        Returns:
            Cached data if found, None otherwise
        """
        start_time = time.time()

        if not self.redis_client:
            self.logger.warning("Redis client not connected, skipping cache get")
            return None

        cache_key = self._build_cache_key(data_type, device_id, additional_key)

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)

                # Update LRU tracker with current timestamp
                await self._update_lru_access(cache_key)

                # Update metrics
                await self._update_metrics("hit", time.time() - start_time)

                self.logger.debug(
                    "Cache hit for key %s, data age: %s",
                    cache_key,
                    self._calculate_data_age(data)
                )
                return dict(data)  # Explicit cast to ensure proper return type
            else:
                # Update metrics for miss
                await self._update_metrics("miss", time.time() - start_time)

                self.logger.debug("Cache miss for key %s", cache_key)
                return None

        except (RedisError, json.JSONDecodeError) as e:
            self.logger.warning(
                "Failed to retrieve from cache (key: %s): %s",
                cache_key, str(e)
            )
            await self._update_metrics("miss", time.time() - start_time)
            return None

    async def set(
        self,
        data_type: str,
        device_id: UUID,
        data: dict[str, Any],
        ttl: int | None = None,
        additional_key: str = "",
    ) -> bool:
        """
        Store data in cache with TTL and LRU tracking.
        
        Args:
            data_type: Type of data being cached
            device_id: UUID of the target device
            data: Data to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
            additional_key: Optional additional key component
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            self.logger.warning("Redis client not connected, skipping cache set")
            return False

        cache_key = self._build_cache_key(data_type, device_id, additional_key)
        cache_ttl = ttl if ttl is not None else self.default_ttl

        try:
            # Check if we need to evict before adding new data
            await self._enforce_cache_limits()

            # Add cache metadata to the data
            cached_data = {
                **data,
                "_cache_metadata": {
                    "cached_at": datetime.now(UTC).isoformat(),
                    "data_type": data_type,
                    "device_id": str(device_id),
                    "ttl": cache_ttl,
                }
            }

            serialized_data = json.dumps(cached_data, default=str)

            # Use pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                # Store the data
                await pipe.setex(cache_key, cache_ttl, serialized_data)

                # Update LRU tracker
                await pipe.zadd(self.lru_zset_key, {cache_key: time.time()})

                # Execute pipeline
                await pipe.execute()

            self.logger.debug(
                "Cached data for key %s with TTL %ds",
                cache_key, cache_ttl
            )
            return True

        except (RedisError, json.JSONDecodeError) as e:
            self.logger.error(
                "Failed to cache data (key: %s): %s",
                cache_key, str(e)
            )
            return False

    async def delete(
        self,
        data_type: str,
        device_id: UUID,
        additional_key: str = "",
    ) -> bool:
        """
        Delete data from cache and LRU tracking.
        
        Args:
            data_type: Type of data to delete
            device_id: UUID of the target device
            additional_key: Optional additional key component
            
        Returns:
            True if deleted or didn't exist, False on error
        """
        if not self.redis_client:
            self.logger.warning("Redis client not connected, skipping cache delete")
            return False

        cache_key = self._build_cache_key(data_type, device_id, additional_key)

        try:
            # Use pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                # Delete the cache entry
                await pipe.delete(cache_key)

                # Remove from LRU tracker
                await pipe.zrem(self.lru_zset_key, cache_key)

                # Execute pipeline
                results = await pipe.execute()

            deleted_count = results[0]  # Result from delete operation
            self.logger.debug(
                "Deleted cache key %s (existed: %s)",
                cache_key, deleted_count > 0
            )
            return True

        except RedisError as e:
            self.logger.error(
                "Failed to delete from cache (key: %s): %s",
                cache_key, str(e)
            )
            return False

    async def exists(
        self,
        data_type: str,
        device_id: UUID,
        additional_key: str = "",
    ) -> bool:
        """
        Check if data exists in cache.
        
        Args:
            data_type: Type of data to check
            device_id: UUID of the target device
            additional_key: Optional additional key component
            
        Returns:
            True if exists, False otherwise
        """
        if not self.redis_client:
            return False

        cache_key = self._build_cache_key(data_type, device_id, additional_key)

        try:
            exists = await self.redis_client.exists(cache_key)
            return bool(exists)
        except RedisError as e:
            self.logger.warning(
                "Failed to check cache existence (key: %s): %s",
                cache_key, str(e)
            )
            return False

    async def get_ttl(
        self,
        data_type: str,
        device_id: UUID,
        additional_key: str = "",
    ) -> int | None:
        """
        Get remaining TTL for cached data.
        
        Args:
            data_type: Type of data to check
            device_id: UUID of the target device
            additional_key: Optional additional key component
            
        Returns:
            Remaining TTL in seconds, None if key doesn't exist or on error
        """
        if not self.redis_client:
            return None

        cache_key = self._build_cache_key(data_type, device_id, additional_key)

        try:
            ttl = await self.redis_client.ttl(cache_key)
            return ttl if ttl > 0 else None
        except RedisError as e:
            self.logger.warning(
                "Failed to get TTL (key: %s): %s",
                cache_key, str(e)
            )
            return None

    async def clear_device_cache(self, device_id: UUID) -> int:
        """
        Clear all cached data for a specific device.
        
        Args:
            device_id: UUID of the device to clear cache for
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0

        pattern = self._build_cache_key("*", device_id)

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                self.logger.info(
                    "Cleared %d cache entries for device %s",
                    int(deleted_count), device_id
                )
                return int(deleted_count)
            return 0
        except RedisError as e:
            self.logger.error(
                "Failed to clear device cache for %s: %s",
                device_id, str(e)
            )
            return 0

    async def clear_data_type_cache(self, data_type: str) -> int:
        """
        Clear all cached data for a specific data type.
        
        Args:
            data_type: Type of data to clear
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0

        pattern = f"{self.key_prefix}{data_type}:*"

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                self.logger.info(
                    "Cleared %d cache entries for data type %s",
                    int(deleted_count), data_type
                )
                return int(deleted_count)
            return 0
        except RedisError as e:
            self.logger.error(
                "Failed to clear cache for data type %s: %s",
                data_type, str(e)
            )
            return 0

    async def _update_lru_access(self, cache_key: str) -> None:
        """
        Update LRU access time for a cache key.
        
        Args:
            cache_key: The cache key that was accessed
        """
        try:
            if self.redis_client:
                await self.redis_client.zadd(self.lru_zset_key, {cache_key: time.time()})
        except RedisError as e:
            self.logger.warning("Failed to update LRU access for key %s: %s", cache_key, str(e))

    async def _enforce_cache_limits(self) -> None:
        """
        Enforce cache size and memory limits by evicting LRU items if necessary.
        """
        if not self.redis_client:
            return

        try:
            # Check cache size limit
            cache_size = await self.redis_client.zcard(self.lru_zset_key)

            if cache_size > self.max_cache_size:
                evict_count = cache_size - self.max_cache_size + self.eviction_batch_size
                await self._evict_lru_items(evict_count)

            # TODO: Check memory limit (requires Redis memory inspection)
            # For now, we rely on cache size as a proxy for memory usage

        except RedisError as e:
            self.logger.error("Failed to enforce cache limits: %s", str(e))

    async def _evict_lru_items(self, count: int) -> int:
        """
        Evict the least recently used items from cache.
        
        Args:
            count: Number of items to evict
            
        Returns:
            Number of items actually evicted
        """
        if not self.redis_client:
            return 0
            
        try:
            # Get the oldest items from the sorted set
            oldest_keys = await self.redis_client.zrange(self.lru_zset_key, 0, count - 1)

            if not oldest_keys:
                return 0

            # Remove both the cached data and LRU entries
            async with self.redis_client.pipeline() as pipe:
                # Delete actual cache entries
                for key in oldest_keys:
                    await pipe.delete(key)

                # Remove from LRU tracker
                await pipe.zrem(self.lru_zset_key, *oldest_keys)

                await pipe.execute()

            # Update metrics
            await self._update_metrics("eviction", 0, len(oldest_keys))

            self.logger.info("Evicted %d LRU cache items", len(oldest_keys))
            return len(oldest_keys)

        except RedisError as e:
            self.logger.error("Failed to evict LRU items: %s", str(e))
            return 0

    async def _update_metrics(
        self,
        operation_type: str,
        response_time: float,
        eviction_count: int = 0
    ) -> None:
        """
        Update cache performance metrics.
        
        Args:
            operation_type: Type of operation ('hit', 'miss', 'eviction')
            response_time: Operation response time in seconds
            eviction_count: Number of items evicted (for eviction operations)
        """
        try:
            if operation_type == "hit":
                self._metrics["hits"] += 1
            elif operation_type == "miss":
                self._metrics["misses"] += 1
            elif operation_type == "eviction":
                self._metrics["evictions"] += eviction_count

            self._metrics["total_operations"] += 1
            self._metrics["total_response_time_ms"] += response_time * 1000

            # Periodically persist metrics to Redis (every 10 operations)
            if self._metrics["total_operations"] % 10 == 0:
                await self._persist_metrics()

        except Exception as e:
            self.logger.warning("Failed to update metrics: %s", str(e))

    async def _persist_metrics(self) -> None:
        """Persist current metrics to Redis"""
        try:
            if self.redis_client:
                metrics_data = json.dumps(self._metrics)
                await self.redis_client.setex(self.metrics_key, 3600, metrics_data)  # 1 hour TTL
        except RedisError as e:
            self.logger.warning("Failed to persist metrics: %s", str(e))

    async def get_metrics(self) -> CacheMetrics:
        """
        Get current cache performance metrics.
        
        Returns:
            CacheMetrics object with current performance data
        """
        try:
            # Load persisted metrics if available
            if self.redis_client:
                persisted = await self.redis_client.get(self.metrics_key)
                if persisted:
                    persisted_metrics = json.loads(persisted)
                    # Merge with current metrics
                    for key, value in persisted_metrics.items():
                        if key in self._metrics:
                            self._metrics[key] = max(self._metrics[key], value)

            # Calculate derived metrics
            total_ops = self._metrics["total_operations"]
            hits = self._metrics["hits"]
            hit_ratio = (hits / total_ops) if total_ops > 0 else 0.0
            avg_response = (self._metrics["total_response_time_ms"] / total_ops) if total_ops > 0 else 0.0

            # Get current cache size
            cache_size = 0
            memory_usage = 0.0
            if self.redis_client:
                cache_size = await self.redis_client.zcard(self.lru_zset_key)
                # Estimate memory usage (rough approximation)
                memory_usage = cache_size * 2.0  # Assume ~2KB per cache entry on average

            return CacheMetrics(
                hits=int(hits),
                misses=int(self._metrics["misses"]),
                evictions=int(self._metrics["evictions"]),
                total_operations=int(total_ops),
                average_response_time_ms=avg_response,
                hit_ratio=hit_ratio,
                cache_size=int(cache_size),
                memory_usage_mb=memory_usage / 1024,
            )

        except Exception as e:
            self.logger.error("Failed to get metrics: %s", str(e))
            # Return empty metrics on error
            return CacheMetrics(0, 0, 0, 0, 0.0, 0.0, 0, 0.0)

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check of the cache system including LRU metrics.
        
        Returns:
            Dictionary containing health status information
        """
        health_status = {
            "service": "EnhancedCacheManager",
            "timestamp": datetime.now(UTC).isoformat(),
            "redis_connected": False,
            "redis_info": {},
            "cache_metrics": {},
            "lru_config": {
                "max_cache_size": self.max_cache_size,
                "max_memory_mb": self.max_memory_mb,
                "eviction_batch_size": self.eviction_batch_size,
            }
        }

        if not self.redis_client:
            health_status["status"] = "disconnected"
            health_status["message"] = "Redis client not initialized"
            return health_status

        try:
            # Test basic operations
            await self.redis_client.ping()
            info = await self.redis_client.info()

            # Get cache metrics
            cache_metrics = await self.get_metrics()

            health_status["redis_connected"] = True
            health_status["redis_info"] = {
                "version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
            health_status["cache_metrics"] = {
                "hits": cache_metrics.hits,
                "misses": cache_metrics.misses,
                "hit_ratio": f"{cache_metrics.hit_ratio:.2%}",
                "evictions": cache_metrics.evictions,
                "cache_size": cache_metrics.cache_size,
                "estimated_memory_mb": f"{cache_metrics.memory_usage_mb:.2f}",
                "avg_response_time_ms": f"{cache_metrics.average_response_time_ms:.2f}",
            }
            health_status["status"] = "healthy"
            health_status["message"] = "Enhanced cache system operational with LRU eviction"

        except RedisError as e:
            health_status["status"] = "unhealthy"
            health_status["message"] = f"Redis error: {str(e)}"

        return health_status

    def _calculate_data_age(self, data: dict[str, Any]) -> str | None:
        """
        Calculate how old cached data is.
        
        Args:
            data: Cached data with metadata
            
        Returns:
            Human-readable age string or None if no metadata
        """
        try:
            cache_metadata = data.get("_cache_metadata", {})
            cached_at_str = cache_metadata.get("cached_at")

            if not cached_at_str:
                return None

            cached_at = datetime.fromisoformat(cached_at_str.replace("Z", "+00:00"))
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=UTC)

            age = datetime.now(UTC) - cached_at

            if age.total_seconds() < 60:
                return f"{int(age.total_seconds())}s"
            elif age.total_seconds() < 3600:
                return f"{int(age.total_seconds() / 60)}m"
            else:
                return f"{int(age.total_seconds() / 3600)}h"

        except (ValueError, TypeError, KeyError) as e:
            self.logger.debug("Failed to calculate data age: %s", str(e))
            return None


# Global cache manager instance
_cache_manager: CacheManager | None = None


async def get_cache_manager(
    redis_url: str = "redis://localhost:9104/0",
    default_ttl: int = 300,
    max_cache_size: int = 1000,
    max_memory_mb: int = 100,
    eviction_batch_size: int = 50,
) -> CacheManager:
    """
    Get or create the global enhanced cache manager instance.
    
    Args:
        redis_url: Redis connection URL
        default_ttl: Default TTL in seconds
        max_cache_size: Maximum number of items in cache
        max_memory_mb: Maximum memory usage in MB
        eviction_batch_size: Number of items to evict at once
        
    Returns:
        Configured enhanced CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(
            redis_url=redis_url,
            default_ttl=default_ttl,
            max_cache_size=max_cache_size,
            max_memory_mb=max_memory_mb,
            eviction_batch_size=eviction_batch_size,
        )
        await _cache_manager.connect()
    return _cache_manager


async def close_cache_manager() -> None:
    """Close the global cache manager connection"""
    global _cache_manager
    if _cache_manager:
        await _cache_manager.disconnect()
        _cache_manager = None
