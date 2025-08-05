"""
Unified Data Collection Service

Central orchestrator for all infrastructure data collection, implementing intelligent
data freshness management and coordinated polling across different data sources.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Callable, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.backend.src.utils.ssh_client import SSHClient, SSHConnectionInfo
from apps.backend.src.core.exceptions import (
    DatabaseOperationError,
    SSHConnectionError,
    DataCollectionError,
)

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
        ssh_command_manager: Optional[Callable] = None,
    ):
        """
        Initialize the UnifiedDataCollectionService.
        
        Args:
            db_session_factory: Factory for creating async database sessions
            ssh_client: SSH client for device communication
            ssh_command_manager: Optional command manager for SSH operations
        """
        self.db_session_factory = db_session_factory
        self.ssh_client = ssh_client
        self.ssh_command_manager = ssh_command_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Data freshness thresholds (in seconds)
        # These determine when data is considered stale and needs refreshing
        self.freshness_thresholds: Dict[str, int] = {
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
    ) -> Dict[str, Any]:
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

    async def _get_cached_data(
        self, data_type: str, device_id: UUID
    ) -> Optional[Dict[str, Any]]:
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
    ) -> Dict[str, Any]:
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
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "status": "placeholder"
        }

    async def _cache_data(
        self, data_type: str, device_id: UUID, data: Dict[str, Any]
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

    def _is_data_fresh(self, cached_data: Dict[str, Any], data_type: str) -> bool:
        """
        Check if cached data is still fresh based on the freshness threshold.
        
        Args:
            cached_data: The cached data to check
            data_type: Type of data to check freshness for
            
        Returns:
            True if data is fresh, False otherwise
        """
        if not cached_data or "collected_at" not in cached_data:
            return False
            
        try:
            collected_at = datetime.fromisoformat(cached_data["collected_at"].replace("Z", "+00:00"))
            if collected_at.tzinfo is None:
                collected_at = collected_at.replace(tzinfo=timezone.utc)
                
            threshold_seconds = self.freshness_thresholds.get(data_type, 600)  # Default 10 minutes
            threshold = timedelta(seconds=threshold_seconds)
            
            age = datetime.now(timezone.utc) - collected_at
            is_fresh = age < threshold
            
            self.logger.debug(
                "Data freshness check: type=%s, age=%s, threshold=%s, fresh=%s",
                data_type, age, threshold, is_fresh
            )
            
            return is_fresh
            
        except (ValueError, TypeError) as e:
            self.logger.warning(
                "Failed to parse collected_at timestamp: %s, error=%s",
                cached_data.get("collected_at"), str(e)
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

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the service and its dependencies.
        
        Returns:
            Dictionary containing health status information
        """
        health_status = {
            "service": "UnifiedDataCollectionService",
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {}
        }
        
        # Check database connection
        try:
            async with self.db_session_factory() as session:
                await session.execute("SELECT 1")
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
def get_unified_data_collection_service(
    db_session_factory: async_sessionmaker[AsyncSession],
    ssh_client: Optional[SSHClient] = None,
    ssh_command_manager: Optional[Callable] = None,
) -> UnifiedDataCollectionService:
    """
    Factory function to create a UnifiedDataCollectionService instance.
    
    Args:
        db_session_factory: Factory for creating async database sessions
        ssh_client: Optional SSH client manager
        ssh_command_manager: Optional SSH command manager
        
    Returns:
        Configured UnifiedDataCollectionService instance
    """
    return UnifiedDataCollectionService(
        db_session_factory=db_session_factory,
        ssh_client=ssh_client,
        ssh_command_manager=ssh_command_manager,
    )