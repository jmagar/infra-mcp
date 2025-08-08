"""
Unified Data Collection Service

Central orchestrator for all infrastructure data collection, implementing intelligent
data freshness management and coordinated polling across different data sources.
"""

from datetime import UTC, datetime, timedelta
import logging

from typing import Any, Dict, List, Optional
from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import text

from apps.backend.src.core.exceptions import (
    CacheOperationError,
    DatabaseOperationError,
    DataCollectionError,
)
from apps.backend.src.utils.cache_manager import CacheManager, get_cache_manager
from apps.backend.src.utils.command_registry import get_unified_command_registry
from apps.backend.src.utils.ssh_client import SSHClient

logger = logging.getLogger(__name__)


class UnifiedDataCollectionService:
    """
    Central service for orchestrating all infrastructure data collection.
    
    This service implements intelligent data freshness management, coordinated
    polling, and provides a unified interface for collecting data from various
    infrastructure sources.
    """

    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        ssh_client: SSHClient,
        ssh_command_manager: Callable | None = None,
        cache_manager: CacheManager | None = None,
    ):
        """
        Initialize the UnifiedDataCollectionService.
        
        Args:
            db_session_factory: Factory for creating async database sessions
            ssh_client: SSH client for device communication
            ssh_command_manager: Optional command manager for SSH operations
            cache_manager: Optional cache manager for data caching
        """
        self.db_session_factory = db_session_factory
        self.ssh_client = ssh_client
        self.ssh_command_manager = ssh_command_manager
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize unified command registry
        self.command_registry = get_unified_command_registry()

        # Data freshness thresholds (in seconds)
        # These determine when data is considered stale and needs refreshing
        self.freshness_thresholds: dict[str, int] = {
            # Container data changes frequently
            "containers": 300,  # 5 minutes

            # System metrics should be relatively fresh
            "system_metrics": 600,  # 10 minutes

            # Drive health changes slowly
            "drive_health": 3600,  # 1 hour

            # Network configuration changes infrequently
            "network_config": 1800,  # 30 minutes

            # Service dependencies change rarely
            "service_dependencies": 3600,  # 1 hour

            # ZFS pool status changes moderately
            "zfs_pools": 900,  # 15 minutes

            # ZFS datasets change moderately
            "zfs_datasets": 1800,  # 30 minutes

            # ZFS snapshots change frequently if auto-snapshots are enabled
            "zfs_snapshots": 600,  # 10 minutes

            # Proxy configurations change rarely
            "proxy_configurations": 1800,  # 30 minutes

            # System logs are continuous but we cache recent entries
            "system_logs": 300,  # 5 minutes
        }

        self.logger.info(
            "UnifiedDataCollectionService initialized with freshness thresholds: %s",
            self.freshness_thresholds
        )

    async def get_fresh_data(
        self,
        data_type: str,
        device_id: UUID,
        force_refresh: bool = False,
        **kwargs: Any
    ) -> dict[str, Any]:
        """
        Get fresh data for a specific data type and device.
        
        Args:
            data_type: Type of data to collect (e.g., 'containers', 'system_metrics')
            device_id: UUID of the target device
            force_refresh: Force data collection even if cached data is fresh
            **kwargs: Additional parameters for data collection
            
        Returns:
            Dictionary containing the collected data
            
        Raises:
            DataCollectionError: If data collection fails
            DatabaseOperationError: If database operations fail
            SSHConnectionError: If SSH connection fails
        """
        try:
            self.logger.debug(
                "Requesting fresh data: type=%s, device_id=%s, force_refresh=%s",
                data_type, device_id, force_refresh
            )

            # Check if we have fresh cached data (unless force refresh is requested)
            if not force_refresh:
                cached_data = await self._get_cached_data(data_type, device_id)
                if cached_data and self._is_data_fresh(cached_data, data_type):
                    self.logger.debug(
                        "Returning cached data for %s on device %s",
                        data_type, device_id
                    )
                    return cached_data

            # Collect fresh data
            fresh_data = await self._collect_fresh_data(data_type, device_id, **kwargs)

            # Cache the fresh data
            await self._cache_data(data_type, device_id, fresh_data)

            self.logger.info(
                "Successfully collected fresh data: type=%s, device_id=%s",
                data_type, device_id
            )

            return fresh_data

        except Exception as e:
            self.logger.error(
                "Failed to get fresh data: type=%s, device_id=%s, error=%s",
                data_type, device_id, str(e)
            )
            raise DataCollectionError(
                f"Failed to collect {data_type} data for device {device_id}"
            ) from e

    async def collect_and_store_data(
        self,
        data_type: str,
        device_id: UUID,
        collection_method: Callable[[], Awaitable[dict[str, Any]]],
        force_refresh: bool = False,
        **kwargs: Any
    ) -> dict[str, Any]:
        """
        Universal data collection method implementing the complete lifecycle:
        1. Check cache
        2. If cache miss, execute collection method
        3. Store result in database for audit
        4. Populate cache
        5. Emit event (placeholder for now)
        
        Args:
            data_type: Type of data being collected
            device_id: UUID of the target device
            collection_method: Async function that returns collected data
            force_refresh: Force fresh collection even if cached data exists
            **kwargs: Additional parameters passed to collection method
            
        Returns:
            Dictionary containing the collected data
            
        Raises:
            DataCollectionError: If data collection fails
            DatabaseOperationError: If database operations fail
            CacheOperationError: If cache operations fail (non-fatal)
        """
        correlation_id = kwargs.get("correlation_id", f"collect_{data_type}_{device_id}")

        try:
            # Entry log (structured)
            self.logger.info(
                "collect.start",
                extra={
                    "data_type": data_type,
                    "device_id": str(device_id),
                    "force_refresh": force_refresh,
                    "correlation_id": correlation_id,
                },
            )

            start_time = datetime.now(UTC)

            # Step 1: Check cache (unless force refresh is requested)
            cached_data = None
            if not force_refresh and self.cache_manager:
                try:
                    cached_data = await self.cache_manager.get(data_type, device_id)
                    if cached_data and self._is_data_fresh(cached_data, data_type):
                        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
                        # Exit log for cache hit
                        self.logger.info(
                            "collect.success",
                            extra={
                                "data_type": data_type,
                                "device_id": str(device_id),
                                "duration_ms": duration_ms,
                                "source": "cache",
                                "correlation_id": correlation_id,
                            },
                        )
                        return self._strip_cache_metadata(cached_data)
                except CacheOperationError as e:
                    self.logger.warning(
                        "cache.get.failed",
                        extra={
                            "data_type": data_type,
                            "device_id": str(device_id),
                            "error": str(e),
                            "correlation_id": correlation_id,
                        },
                    )

            # Step 2: Collect fresh data via the provided collection method
            fresh_data = await collection_method()
            collection_duration = (datetime.now(UTC) - start_time).total_seconds()

            # Enrich data with collection metadata
            enriched_data = {
                **fresh_data,
                "collection_metadata": {
                    "data_type": data_type,
                    "device_id": str(device_id),
                    "collected_at": start_time.isoformat(),
                    "collection_duration_seconds": collection_duration,
                    "correlation_id": correlation_id,
                    "force_refresh": force_refresh,
                    "cache_hit": False,
                }
            }

            # Exit log for fresh collection
            self.logger.info(
                "collect.success",
                extra={
                    "data_type": data_type,
                    "device_id": str(device_id),
                    "duration_ms": int(collection_duration * 1000),
                    "source": "fresh",
                    "correlation_id": correlation_id,
                },
            )

            # Step 3: Store result in database for audit (async, non-blocking)
            try:
                await self._store_audit_record(data_type, device_id, enriched_data, correlation_id)
            except DatabaseOperationError as e:
                # Log error but don't fail the entire operation
                self.logger.error(
                    "audit.store.failed",
                    extra={
                        "data_type": data_type,
                        "device_id": str(device_id),
                        "error": str(e),
                        "correlation_id": correlation_id,
                    },
                )

            # Step 4: Populate cache with collected data
            if self.cache_manager:
                try:
                    cache_ttl = self.freshness_thresholds.get(data_type, 600)
                    success = await self.cache_manager.set(
                        data_type, device_id, enriched_data, ttl=cache_ttl
                    )
                    if success:
                        self.logger.debug(
                            "cache.set.success",
                            extra={
                                "data_type": data_type,
                                "device_id": str(device_id),
                                "ttl_seconds": cache_ttl,
                                "correlation_id": correlation_id,
                            },
                        )
                    else:
                        self.logger.warning(
                            "cache.set.failed",
                            extra={
                                "data_type": data_type,
                                "device_id": str(device_id),
                                "correlation_id": correlation_id,
                            },
                        )
                except CacheOperationError as e:
                    self.logger.warning(
                        "cache.set.exception",
                        extra={
                            "data_type": data_type,
                            "device_id": str(device_id),
                            "error": str(e),
                            "correlation_id": correlation_id,
                        },
                    )

            # Step 5: Emit event (placeholder for future implementation)
            self._emit_data_collection_event(data_type, device_id, enriched_data, correlation_id)

            # Return data without cache metadata for public consumption
            return self._strip_cache_metadata(enriched_data)

        except Exception as e:
            self.logger.error(
                "collect.error",
                exc_info=True,
                extra={
                    "data_type": data_type,
                    "device_id": str(device_id),
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
            )
            raise DataCollectionError(
                f"Failed to collect and store {data_type} data for device {device_id}"
            ) from e

    async def _get_cached_data(
        self, data_type: str, device_id: UUID
    ) -> dict[str, Any] | None:
        """
        Retrieve cached data from the database.
        
        Args:
            data_type: Type of data to retrieve
            device_id: UUID of the target device
            
        Returns:
            Cached data if available, None otherwise
        """
        # This will be implemented in subsequent tasks
        # For now, return None to always trigger fresh collection
        return None

    async def _collect_fresh_data(
        self, data_type: str, device_id: UUID, **kwargs: Any
    ) -> dict[str, Any]:
        """
        Collect fresh data from the target device.
        
        Args:
            data_type: Type of data to collect
            device_id: UUID of the target device
            **kwargs: Additional parameters for data collection
            
        Returns:
            Dictionary containing the collected data
        """
        # This will be implemented in subsequent tasks
        # For now, return placeholder data
        return {
            "data_type": data_type,
            "device_id": str(device_id),
            "collected_at": datetime.now(UTC).isoformat(),
            "status": "placeholder"
        }

    async def _cache_data(
        self, data_type: str, device_id: UUID, data: dict[str, Any]
    ) -> None:
        """
        Cache the collected data in the database.
        
        Args:
            data_type: Type of data being cached
            device_id: UUID of the target device
            data: Data to cache
        """
        # This will be implemented in subsequent tasks
        pass

    def _is_data_fresh(self, cached_data: dict[str, Any], data_type: str) -> bool:
        """
        Check if cached data is still fresh based on the freshness threshold.
        
        Args:
            cached_data: The cached data to check
            data_type: Type of data to check freshness for
            
        Returns:
            True if data is fresh, False otherwise
        """
        if not cached_data:
            return False

        # Try to get collected_at from collection_metadata first, then fallback to root level
        collected_at_str = None
        if "collection_metadata" in cached_data and "collected_at" in cached_data["collection_metadata"]:
            collected_at_str = cached_data["collection_metadata"]["collected_at"]
        elif "collected_at" in cached_data:
            collected_at_str = cached_data["collected_at"]

        if not collected_at_str:
            self.logger.debug("No collected_at timestamp found in cached data")
            return False

        try:
            collected_at = datetime.fromisoformat(collected_at_str.replace("Z", "+00:00"))
            if collected_at.tzinfo is None:
                collected_at = collected_at.replace(tzinfo=UTC)

            threshold_seconds = self.freshness_thresholds.get(data_type, 600)  # Default 10 minutes
            threshold = timedelta(seconds=threshold_seconds)

            age = datetime.now(UTC) - collected_at
            is_fresh = age < threshold

            self.logger.debug(
                "Data freshness check: type=%s, age=%s, threshold=%s, fresh=%s",
                data_type, age, threshold, is_fresh
            )

            return is_fresh

        except (ValueError, TypeError) as e:
            self.logger.warning(
                "Failed to parse collected_at timestamp: %s, error=%s",
                collected_at_str, str(e)
            )
            return False

    def get_freshness_threshold(self, data_type: str) -> int:
        """
        Get the freshness threshold for a specific data type.
        
        Args:
            data_type: Type of data to get threshold for
            
        Returns:
            Freshness threshold in seconds
        """
        return self.freshness_thresholds.get(data_type, 600)  # Default 10 minutes

    def set_freshness_threshold(self, data_type: str, threshold_seconds: int) -> None:
        """
        Set the freshness threshold for a specific data type.
        
        Args:
            data_type: Type of data to set threshold for
            threshold_seconds: Threshold in seconds
        """
        if threshold_seconds <= 0:
            raise ValueError("Freshness threshold must be positive")

        old_threshold = self.freshness_thresholds.get(data_type)
        self.freshness_thresholds[data_type] = threshold_seconds

        self.logger.info(
            "Updated freshness threshold: type=%s, old=%s, new=%s",
            data_type, old_threshold, threshold_seconds
        )

    async def _store_audit_record(
        self, data_type: str, device_id: UUID, data: dict[str, Any], correlation_id: str
    ) -> None:
        """
        Store audit record of data collection in the database.
        
        Args:
            data_type: Type of data collected
            device_id: UUID of the target device
            data: Collected data with metadata
            correlation_id: Correlation ID for tracking
        """
        try:
            async with self.db_session_factory() as session:
                # Store audit record in data_collection_audit table
                from datetime import datetime

                from sqlalchemy import text

                collected_at_str = data.get("collection_metadata", {}).get("collected_at")
                collected_at = datetime.fromisoformat(collected_at_str.replace('Z', '+00:00')) if collected_at_str else datetime.utcnow()

                insert_query = text("""
                    INSERT INTO data_collection_audit 
                    (data_type, device_id, correlation_id, collected_at, collection_duration_seconds, 
                     data_size, cache_hit, force_refresh, metadata_info)
                    VALUES (:data_type, :device_id, :correlation_id, :collected_at, :collection_duration_seconds,
                            :data_size, :cache_hit, :force_refresh, :metadata_info)
                """)

                import json

                await session.execute(insert_query, {
                    "data_type": data_type,
                    "device_id": device_id,
                    "correlation_id": correlation_id,
                    "collected_at": collected_at,
                    "collection_duration_seconds": data.get("collection_metadata", {}).get("collection_duration_seconds"),
                    "data_size": len(str(data)),
                    "cache_hit": data.get("collection_metadata", {}).get("cache_hit", False),
                    "force_refresh": data.get("collection_metadata", {}).get("force_refresh", False),
                    "metadata_info": json.dumps(data.get("collection_metadata", {}))
                })

                await session.commit()

                self.logger.debug(
                    "Audit record stored in database: type=%s, device_id=%s, correlation_id=%s",
                    data_type, device_id, correlation_id
                )

        except Exception as e:
            self.logger.error(
                "Failed to store audit record: type=%s, device_id=%s, error=%s",
                data_type, device_id, str(e)
            )
            raise DatabaseOperationError(
                f"Failed to store audit record for {data_type} collection",
                operation="store_audit_record"
            ) from e

    def _emit_data_collection_event(
        self, data_type: str, device_id: UUID, data: dict[str, Any], correlation_id: str
    ) -> None:
        """
        Emit event for data collection completion.
        
        This is a placeholder for future event system integration.
        
        Args:
            data_type: Type of data collected
            device_id: UUID of the target device
            data: Collected data with metadata
            correlation_id: Correlation ID for tracking
        """
        # Placeholder for event emission
        # Future implementation might integrate with EventBus, WebSocket notifications, etc.
        self.logger.debug(
            "Data collection event emitted: type=%s, device_id=%s, correlation_id=%s",
            data_type, device_id, correlation_id
        )

    def _strip_cache_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Remove cache-specific metadata from data before returning to caller.
        
        Args:
            data: Data potentially containing cache metadata
            
        Returns:
            Data with cache metadata removed
        """

        # Create a copy and remove cache metadata
        cleaned_data = {k: v for k, v in data.items() if k != "_cache_metadata"}

        # Update collection metadata to indicate cache hit if applicable
        if "_cache_metadata" in data and "collection_metadata" in cleaned_data:
            cleaned_data["collection_metadata"]["cache_hit"] = True
            # Use original collection time from cache metadata
            cache_meta = data["_cache_metadata"]
            if "cached_at" in cache_meta:
                cleaned_data["collection_metadata"]["served_from_cache_at"] = cache_meta["cached_at"]

        return cleaned_data

    async def health_check(self) -> dict[str, Any]:
        """
        Perform a health check of the service and its dependencies.
        
        Returns:
            Dictionary containing health status information
        """
        health_status: dict[str, Any] = {
            "service": "UnifiedDataCollectionService",
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "components": {}
        }

        # Check database connection
        try:
            async with self.db_session_factory() as session:
                await session.execute(text("SELECT 1"))
            health_status["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful"
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }
            health_status["status"] = "degraded"

        # Check SSH client
        if self.ssh_client:
            health_status["components"]["ssh_client"] = {
                "status": "healthy",
                "message": "SSH client available"
            }
        else:
            health_status["components"]["ssh_client"] = {
                "status": "unavailable",
                "message": "SSH client not configured"
            }

        return health_status


# Factory function for dependency injection
async def get_unified_data_collection_service(
    db_session_factory: async_sessionmaker[AsyncSession],
    ssh_client: SSHClient | None = None,
    ssh_command_manager: Callable | None = None,
    cache_manager: CacheManager | None = None,
) -> UnifiedDataCollectionService:
    """
    Factory function to create a UnifiedDataCollectionService instance.
    
    Args:
        db_session_factory: Factory for creating async database sessions
        ssh_client: Optional SSH client manager
        ssh_command_manager: Optional SSH command manager
        cache_manager: Optional cache manager (will create enhanced one if None)
        
    Returns:
        Configured UnifiedDataCollectionService instance with enhanced caching
    """
    # Initialize enhanced cache manager if not provided
    if cache_manager is None:
        # Use enhanced cache configuration optimized for infrastructure data
        cache_manager = await get_cache_manager(
            max_cache_size=2000,  # Higher limit for infrastructure monitoring
            max_memory_mb=200,    # 200MB memory limit
            eviction_batch_size=100,  # Larger batch eviction for efficiency
        )

    return UnifiedDataCollectionService(
        db_session_factory=db_session_factory,
        ssh_client=ssh_client,  # type: ignore[arg-type]
        ssh_command_manager=ssh_command_manager,
        cache_manager=cache_manager,
    )
