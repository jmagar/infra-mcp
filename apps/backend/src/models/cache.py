"""
Cache management models for tracking infrastructure data caching operations.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from apps.backend.src.core.database import Base


class CacheMetadata(Base):
    """
    Cache metadata table for managing infrastructure data caching operations.

    This table tracks cache entries for various infrastructure data types,
    providing cache invalidation, TTL management, and cache performance monitoring.
    """

    __tablename__ = "cache_metadata"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=lambda: uuid4())
    
    # Cache key (not primary key in actual schema)
    cache_key = Column(String(255), nullable=False, index=True)

    # Foreign key to device
    device_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Cache entry metadata
    data_type = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    last_accessed = Column(DateTime(timezone=True), index=True)
    expires_at = Column(DateTime(timezone=True), index=True)
    access_count = Column(Integer, default=0, nullable=False)
    hit_count = Column(Integer, default=0, nullable=False)
    miss_count = Column(Integer, default=0, nullable=False)
    data_size_bytes = Column(Integer)
    ttl_seconds = Column(Integer)

    # Cache status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    invalidated_at = Column(DateTime(timezone=True))
    invalidation_reason = Column(String(100))

    # Collection context stored as JSON metadata  
    cache_metadata = Column('metadata', JSONB, default=lambda: {})

    # Relationships
    device = relationship("Device", back_populates="cache_metadata")

    def __repr__(self) -> str:
        return (
            f"<CacheMetadata("
            f"cache_key='{self.cache_key}', "
            f"device_id={self.device_id}, "
            f"data_type='{self.data_type}', "
            f"expires_at={self.expires_at.isoformat() if self.expires_at else None}, "
            f"access_count={self.access_count}, "
            f"invalidated={self.invalidated}"
            f")>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the cache entry is valid (not expired and is active)."""
        return not self.is_expired and self.is_active

    @property
    def time_to_expiry_seconds(self) -> int:
        """Get the number of seconds until this cache entry expires."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.now(UTC)
        return max(0, int(delta.total_seconds()))

    @property
    def age_seconds(self) -> int:
        """Get the age of this cache entry in seconds."""
        delta = datetime.now(UTC) - self.created_at
        return int(delta.total_seconds())

    @property
    def last_access_age_seconds(self) -> int:
        """Get the number of seconds since this cache entry was last accessed."""
        delta = datetime.now(UTC) - self.last_accessed
        return int(delta.total_seconds())

    @property
    def hit_rate_score(self) -> float:
        """
        Calculate a hit rate score based on access count and age.
        Higher scores indicate frequently accessed, valuable cache entries.
        """
        if self.age_seconds == 0:
            return 0.0

        # Access rate per hour
        hours_old = max(1, self.age_seconds / 3600)
        accesses_per_hour = self.access_count / hours_old

        # Weight by freshness (newer entries get higher scores)
        freshness_factor = min(1.0, (self.ttl_seconds - self.age_seconds) / self.ttl_seconds)

        return accesses_per_hour * freshness_factor

    def mark_accessed(self) -> None:
        """Mark this cache entry as accessed, updating the access count and timestamp."""
        self.last_accessed = datetime.now(UTC)
        self.access_count += 1

    def invalidate(self, reason: str) -> None:
        """
        Invalidate this cache entry.

        Args:
            reason: Reason for invalidation (e.g., 'manual', 'data_changed', 'expired')
        """
        self.is_active = False
        self.invalidated_at = datetime.now(UTC)
        self.invalidation_reason = reason

    def extend_ttl(self, additional_seconds: int) -> None:
        """
        Extend the TTL of this cache entry.

        Args:
            additional_seconds: Number of seconds to add to the expiration time
        """
        from datetime import timedelta

        self.expires_at += timedelta(seconds=additional_seconds)
        self.ttl_seconds += additional_seconds

    @classmethod
    def create_cache_entry(
        cls,
        cache_key: str,
        device_id: UUID,
        data_type: str,
        ttl_seconds: int,
        data_size_bytes: int | None = None,
        collection_method: str | None = None,
        command_hash: str | None = None,
    ) -> "CacheMetadata":
        """
        Factory method to create a new cache metadata entry.

        Args:
            cache_key: Unique cache key identifier
            device_id: UUID of the device this cache entry relates to
            data_type: Type of data being cached (e.g., 'system_metrics', 'containers')
            ttl_seconds: Time-to-live in seconds
            data_size_bytes: Size of the cached data in bytes
            collection_method: Method used to collect the data
            command_hash: Hash of the command that generated this data

        Returns:
            New CacheMetadata instance
        """
        now = datetime.now(UTC)
        from datetime import timedelta

        return cls(
            cache_key=cache_key,
            device_id=device_id,
            data_type=data_type,
            created_at=now,
            last_accessed=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            ttl_seconds=ttl_seconds,
            data_size_bytes=data_size_bytes,
            collection_method=collection_method,
            command_hash=command_hash,
        )

    @classmethod
    def generate_cache_key(
        cls,
        device_id: UUID,
        data_type: str,
        operation: str,
        parameters: dict | None = None,
    ) -> str:
        """
        Generate a standardized cache key.

        Args:
            device_id: UUID of the device
            data_type: Type of data (e.g., 'system_metrics', 'containers')
            operation: Operation being performed (e.g., 'list', 'get', 'health')
            parameters: Optional parameters that affect the result

        Returns:
            Standardized cache key string
        """
        import hashlib

        # Base key components
        key_parts = [str(device_id), data_type, operation]

        # Add parameters if provided
        if parameters:
            # Sort parameters for consistent key generation
            param_str = str(sorted(parameters.items()))
            key_parts.append(param_str)

        # Create hash of the combined key parts
        key_string = ":".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]

        # Return readable format: device_type:operation:hash
        return f"{data_type}:{operation}:{key_hash}"
