"""
Cache Manager with LRU Eviction

Provides intelligent caching with configurable freshness thresholds,
LRU eviction policy, and comprehensive performance tracking.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from dataclasses import dataclass, field
from collections import OrderedDict
import hashlib
import pickle
import asyncio
from threading import RLock

from ..core.exceptions import (
    CacheOperationError,
    ValidationError,
)

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Individual cache entry with metadata and LRU tracking."""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    hit_count: int = 0
    miss_count: int = 0
    data_type: str = "unknown"
    size_bytes: int = 0
    ttl_seconds: int | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate entry size and expiration if TTL is set."""
        if self.size_bytes == 0:
            try:
                self.size_bytes = len(pickle.dumps(self.value))
            except Exception:
                self.size_bytes = len(str(self.value).encode("utf-8"))

        if self.ttl_seconds and not self.expires_at:
            self.expires_at = self.created_at + timedelta(seconds=self.ttl_seconds)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def is_fresh(self, freshness_threshold_seconds: int) -> bool:
        """Check if entry is fresh enough based on threshold."""
        if self.is_expired():
            return False

        age_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age_seconds <= freshness_threshold_seconds

    def touch(self) -> None:
        """Update last access time and increment access count."""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1


@dataclass
class CacheStatistics:
    """Cache performance statistics."""

    total_entries: int = 0
    total_size_bytes: int = 0
    total_accesses: int = 0
    total_hits: int = 0
    total_misses: int = 0
    evictions: int = 0
    expired_evictions: int = 0
    lru_evictions: int = 0
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0
    average_entry_size: float = 0.0
    memory_utilization: float = 0.0
    oldest_entry_age_seconds: float | None = None
    newest_entry_age_seconds: float | None = None


class CacheManager:
    """
    Intelligent cache manager with LRU eviction and performance tracking.

    Features:
    - LRU (Least Recently Used) eviction policy
    - Configurable freshness thresholds per data type
    - Automatic expiration handling
    - Comprehensive performance metrics
    - Thread-safe operations
    - Memory usage monitoring
    """

    def __init__(
        self,
        max_entries: int = 1000,
        max_memory_bytes: int = 100 * 1024 * 1024,  # 100MB default
        default_ttl_seconds: int = 3600,  # 1 hour default
        cleanup_interval_seconds: int = 300,  # 5 minutes
    ):
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_bytes
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds

        # LRU cache storage - OrderedDict maintains insertion/access order
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()  # Thread-safe operations

        # Performance tracking
        self._stats = CacheStatistics()

        # Freshness thresholds by data type (seconds)
        self._freshness_thresholds: dict[str, int] = {
            "system_metrics": 300,  # 5 minutes
            "container_info": 30,  # 30 seconds
            "drive_health": 3600,  # 1 hour
            "zfs_pools": 1800,  # 30 minutes
            "network_stats": 60,  # 1 minute
            "process_list": 15,  # 15 seconds
            "service_status": 30,  # 30 seconds
            "docker_compose": 300,  # 5 minutes
            "nginx_config": 1800,  # 30 minutes
            "default": 600,  # 10 minutes
        }

        # Background cleanup task
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

        logger.info(
            f"CacheManager initialized - max_entries: {max_entries}, "
            f"max_memory: {max_memory_bytes // (1024 * 1024)}MB, "
            f"default_ttl: {default_ttl_seconds}s"
        )

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("CacheManager background cleanup started")

    async def stop(self) -> None:
        """Stop background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("CacheManager background cleanup stopped")

    def _generate_cache_key(
        self, operation: str, device_id: str, additional_params: dict[str, Any] | None = None
    ) -> str:
        """Generate consistent cache key from operation parameters."""
        key_parts = [operation, device_id]

        if additional_params:
            # Sort parameters for consistent key generation
            sorted_params = sorted(additional_params.items())
            param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            key_parts.append(param_str)

        key_string = "|".join(key_parts)

        # Use hash for very long keys to keep them manageable
        if len(key_string) > 200:
            return hashlib.sha256(key_string.encode()).hexdigest()

        return key_string

    def set_freshness_threshold(self, data_type: str, seconds: int) -> None:
        """Set freshness threshold for a specific data type."""
        with self._lock:
            self._freshness_thresholds[data_type] = seconds
            logger.debug(f"Set freshness threshold for {data_type}: {seconds}s")

    def get_freshness_threshold(self, data_type: str) -> int:
        """Get freshness threshold for a data type."""
        return self._freshness_thresholds.get(data_type, self._freshness_thresholds["default"])

    async def get(
        self,
        operation: str,
        device_id: str,
        data_type: str = "default",
        additional_params: dict[str, Any] | None = None,
        force_fresh: bool = False,
    ) -> tuple[Any | None, bool]:
        """
        Get cached value if fresh enough.

        Returns:
            Tuple of (value, is_hit) where is_hit indicates cache hit/miss
        """
        cache_key = self._generate_cache_key(operation, device_id, additional_params)

        with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._stats.total_misses += 1
                self._stats.total_accesses += 1
                self._update_hit_rate()
                logger.debug(f"Cache MISS: {cache_key}")
                return None, False

            # Check if expired
            if entry.is_expired():
                self._remove_entry(cache_key)
                self._stats.total_misses += 1
                self._stats.total_accesses += 1
                self._stats.expired_evictions += 1
                self._update_hit_rate()
                logger.debug(f"Cache EXPIRED: {cache_key}")
                return None, False

            # Check freshness unless force_fresh is disabled
            freshness_threshold = self.get_freshness_threshold(data_type)
            if force_fresh or not entry.is_fresh(freshness_threshold):
                self._stats.total_misses += 1
                self._stats.total_accesses += 1
                entry.miss_count += 1
                self._update_hit_rate()
                logger.debug(
                    f"Cache STALE: {cache_key} (age: {(datetime.now(timezone.utc) - entry.created_at).total_seconds():.1f}s)"
                )
                return None, False

            # Cache hit - move to end (most recently used)
            entry.touch()
            entry.hit_count += 1
            self._cache.move_to_end(cache_key)

            self._stats.total_hits += 1
            self._stats.total_accesses += 1
            self._update_hit_rate()

            logger.debug(f"Cache HIT: {cache_key}")
            return entry.value, True

    async def set(
        self,
        operation: str,
        device_id: str,
        value: Any,
        data_type: str = "default",
        additional_params: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store value in cache with TTL and metadata."""
        cache_key = self._generate_cache_key(operation, device_id, additional_params)
        current_time = datetime.now(timezone.utc)

        # Use default TTL if not specified
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl_seconds

        entry = CacheEntry(
            key=cache_key,
            value=value,
            created_at=current_time,
            last_accessed=current_time,
            data_type=data_type,
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

        with self._lock:
            # Remove existing entry if present
            if cache_key in self._cache:
                old_entry = self._cache[cache_key]
                self._stats.total_size_bytes -= old_entry.size_bytes
                self._stats.total_entries -= 1

            # Check if we need to evict entries
            await self._ensure_capacity(entry.size_bytes)

            # Add new entry
            self._cache[cache_key] = entry
            self._stats.total_entries += 1
            self._stats.total_size_bytes += entry.size_bytes

            logger.debug(
                f"Cache SET: {cache_key} ({entry.size_bytes} bytes, "
                f"TTL: {ttl_seconds}s, type: {data_type})"
            )

    async def invalidate(
        self, operation: str, device_id: str, additional_params: dict[str, Any] | None = None
    ) -> bool:
        """Remove specific entry from cache."""
        cache_key = self._generate_cache_key(operation, device_id, additional_params)

        with self._lock:
            if cache_key in self._cache:
                self._remove_entry(cache_key)
                logger.debug(f"Cache INVALIDATE: {cache_key}")
                return True
            return False

    async def invalidate_device(self, device_id: str) -> int:
        """Remove all entries for a specific device."""
        count = 0
        keys_to_remove = []

        with self._lock:
            for key, entry in self._cache.items():
                if device_id in key:  # Simple string matching
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                self._remove_entry(key)
                count += 1

        if count > 0:
            logger.info(f"Cache INVALIDATE_DEVICE: {device_id} ({count} entries)")

        return count

    async def invalidate_by_type(self, data_type: str) -> int:
        """Remove all entries of a specific data type."""
        count = 0
        keys_to_remove = []

        with self._lock:
            for key, entry in self._cache.items():
                if entry.data_type == data_type:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                self._remove_entry(key)
                count += 1

        if count > 0:
            logger.info(f"Cache INVALIDATE_TYPE: {data_type} ({count} entries)")

        return count

    async def clear(self) -> int:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats = CacheStatistics()

            if count > 0:
                logger.info(f"Cache CLEAR: {count} entries removed")

            return count

    def get_statistics(self) -> CacheStatistics:
        """Get current cache statistics."""
        with self._lock:
            stats = CacheStatistics(
                total_entries=self._stats.total_entries,
                total_size_bytes=self._stats.total_size_bytes,
                total_accesses=self._stats.total_accesses,
                total_hits=self._stats.total_hits,
                total_misses=self._stats.total_misses,
                evictions=self._stats.evictions,
                expired_evictions=self._stats.expired_evictions,
                lru_evictions=self._stats.lru_evictions,
                cache_hit_rate=self._stats.cache_hit_rate,
                cache_miss_rate=self._stats.cache_miss_rate,
                average_entry_size=self._stats.average_entry_size,
                memory_utilization=self._stats.memory_utilization,
            )

            # Calculate age statistics
            if self._cache:
                current_time = datetime.now(timezone.utc)
                ages = [
                    (current_time - entry.created_at).total_seconds()
                    for entry in self._cache.values()
                ]
                stats.oldest_entry_age_seconds = max(ages)
                stats.newest_entry_age_seconds = min(ages)

            # Update calculated fields
            if stats.total_entries > 0:
                stats.average_entry_size = stats.total_size_bytes / stats.total_entries
                stats.memory_utilization = (stats.total_size_bytes / self.max_memory_bytes) * 100

            return stats

    def get_entries_by_type(self) -> dict[str, int]:
        """Get count of entries by data type."""
        with self._lock:
            type_counts = {}
            for entry in self._cache.values():
                type_counts[entry.data_type] = type_counts.get(entry.data_type, 0) + 1
            return type_counts

    def get_top_accessed_keys(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most frequently accessed cache keys."""
        with self._lock:
            sorted_entries = sorted(
                self._cache.values(), key=lambda e: e.access_count, reverse=True
            )

            return [
                {
                    "cache_key": entry.key,
                    "access_count": entry.access_count,
                    "hit_count": entry.hit_count,
                    "data_type": entry.data_type,
                    "size_bytes": entry.size_bytes,
                    "age_seconds": (datetime.now(timezone.utc) - entry.created_at).total_seconds(),
                }
                for entry in sorted_entries[:limit]
            ]

    def _remove_entry(self, key: str) -> None:
        """Remove entry and update statistics."""
        entry = self._cache.pop(key, None)
        if entry:
            self._stats.total_entries -= 1
            self._stats.total_size_bytes -= entry.size_bytes

    async def _ensure_capacity(self, new_entry_size: int) -> None:
        """Ensure cache has capacity for new entry, evicting if necessary."""
        # Check memory limit
        while self._stats.total_size_bytes + new_entry_size > self.max_memory_bytes and self._cache:
            await self._evict_lru()

        # Check entry count limit
        while len(self._cache) >= self.max_entries and self._cache:
            await self._evict_lru()

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # OrderedDict: first item is least recently used
        lru_key, lru_entry = next(iter(self._cache.items()))
        self._remove_entry(lru_key)
        self._stats.evictions += 1
        self._stats.lru_evictions += 1

        logger.debug(f"Cache LRU_EVICT: {lru_key} ({lru_entry.size_bytes} bytes)")

    async def _cleanup_expired(self) -> int:
        """Remove expired entries."""
        current_time = datetime.now(timezone.utc)
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_entry(key)
                self._stats.evictions += 1
                self._stats.expired_evictions += 1

        if expired_keys:
            logger.debug(f"Cache CLEANUP: {len(expired_keys)} expired entries removed")

        return len(expired_keys)

    def _update_hit_rate(self) -> None:
        """Update cache hit/miss rates."""
        if self._stats.total_accesses > 0:
            self._stats.cache_hit_rate = (self._stats.total_hits / self._stats.total_accesses) * 100
            self._stats.cache_miss_rate = (
                self._stats.total_misses / self._stats.total_accesses
            ) * 100

    async def _cleanup_loop(self) -> None:
        """Background cleanup task for expired entries."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                if self._running:  # Check again after sleep
                    await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
