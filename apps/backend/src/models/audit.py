"""
Data Collection Audit Models

Models for tracking all data collection operations across the infrastructure
management system, providing complete audit trails and performance metrics.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from typing import Any, cast
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from apps.backend.src.core.database import Base


class DataCollectionAudit(Base):
    """
    Audit trail for all data collection operations (TimescaleDB Hypertable).
    
    This model tracks every data collection operation across polling, API, and MCP
    layers, providing complete audit trails and performance analysis.
    """
    __tablename__ = "data_collection_audit"

    # TimescaleDB primary key (time-based partitioning)
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False, default=func.now())
    device_id = Column(PGUUID(as_uuid=True), ForeignKey("devices.id"), primary_key=True, nullable=False)

    # Operation identification
    operation_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    data_type = Column(String(50), nullable=False, index=True)  # "containers", "metrics", etc.

    # Collection metadata
    collection_method = Column(String(50), nullable=False)  # "polling", "api", "mcp"
    collection_source = Column(String(100))  # Source service/endpoint
    force_refresh = Column(Boolean, default=False)
    cache_hit = Column(Boolean, default=False)

    # Timing and performance
    duration_ms = Column(Integer)  # Collection duration
    ssh_command_count = Column(Integer, default=0)  # SSH commands executed
    data_size_bytes = Column(BigInteger)  # Size of collected data

    # Status and errors
    status = Column(String(20), nullable=False, index=True)  # "success", "error", "partial"
    error_message = Column(Text)  # Error details if failed
    warnings = Column(JSON, default=list)  # Non-fatal warnings

    # Result metadata
    records_created = Column(Integer, default=0)  # Database records created
    records_updated = Column(Integer, default=0)  # Database records updated
    freshness_threshold = Column(Integer)  # Cache TTL used (seconds)

    # Request context
    correlation_id = Column(String(100))  # Request correlation ID
    user_agent = Column(String(200))  # API user agent if applicable
    request_ip = Column(String(45))  # Request IP if applicable

    # Relationships
    device = relationship("Device", back_populates="audit_records")

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_audit_device_type_time', 'device_id', 'data_type', 'time'),
        Index('idx_audit_method_status', 'collection_method', 'status'),
        Index('idx_audit_performance', 'duration_ms', 'time'),
        Index('idx_audit_correlation', 'correlation_id'),
        Index('idx_audit_cache_performance', 'cache_hit', 'data_type', 'time'),
    )

    def __repr__(self) -> str:
        return (
            f"<DataCollectionAudit(operation_id={self.operation_id}, "
            f"data_type={self.data_type}, device_id={self.device_id}, "
            f"status={self.status}, time={self.time})>"
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this operation type"""
        return 1.0 if self.status == "success" else 0.0

    @property
    def performance_score(self) -> float:
        """Calculate performance score based on duration and cache hit"""
        # Access ORM attributes via Any to avoid ColumnElement typing in mypy
        orm_self = cast(Any, self)
        if orm_self.duration_ms is None:
            return 0.0

        # Base score from duration (lower is better)
        duration_ms: int = int(orm_self.duration_ms)
        duration_score = max(0, 1000 - duration_ms) / 1000

        # Bonus for cache hits
        cache_bonus = 0.5 if bool(orm_self.cache_hit) else 0.0

        return min(1.0, duration_score + cache_bonus)


class ServicePerformanceMetric(Base):
    """
    Track performance of data collection services (TimescaleDB Hypertable).
    
    Aggregated performance metrics collected periodically to track service health
    and identify performance trends across the infrastructure management system.
    """
    __tablename__ = "service_performance_metrics"

    # TimescaleDB primary key
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False, default=func.now())
    service_name = Column(String(50), primary_key=True, nullable=False)  # "polling", "api", "mcp"

    # Performance metrics
    operations_total = Column(Integer, default=0)  # Total operations in period
    operations_successful = Column(Integer, default=0)  # Successful operations
    operations_failed = Column(Integer, default=0)  # Failed operations
    operations_cached = Column(Integer, default=0)  # Cache hits

    # Timing metrics
    avg_duration_ms = Column(Numeric(8, 2))  # Average operation duration
    max_duration_ms = Column(Integer)  # Maximum operation duration
    min_duration_ms = Column(Integer)  # Minimum operation duration
    p95_duration_ms = Column(Integer)  # 95th percentile duration

    # SSH performance
    ssh_connections_created = Column(Integer, default=0)  # New SSH connections
    ssh_connections_reused = Column(Integer, default=0)  # Reused SSH connections
    ssh_commands_executed = Column(Integer, default=0)  # Total SSH commands
    ssh_connection_failures = Column(Integer, default=0)  # SSH connection failures

    # Cache performance
    cache_hit_ratio = Column(Numeric(5, 2))  # Cache hit percentage
    cache_size_entries = Column(Integer)  # Current cache entries
    cache_evictions = Column(Integer, default=0)  # Cache evictions in period
    cache_memory_mb = Column(Numeric(8, 2))  # Cache memory usage

    # Data volume
    data_collected_bytes = Column(BigInteger, default=0)  # Total data collected
    database_writes = Column(Integer, default=0)  # Database write operations
    database_read_queries = Column(Integer, default=0)  # Database read queries

    # Error analysis
    error_types = Column(JSON, default=dict)  # Error type counts
    top_errors = Column(JSON, default=list)  # Most common errors
    warning_count = Column(Integer, default=0)  # Total warnings

    # Resource utilization
    cpu_usage_percent = Column(Numeric(5, 2))  # CPU usage during period
    memory_usage_mb = Column(Numeric(8, 2))  # Memory usage during period

    # Performance indexes
    __table_args__ = (
        Index('idx_service_perf_time', 'time'),
        Index('idx_service_perf_name_time', 'service_name', 'time'),
        Index('idx_service_perf_success_rate', 'operations_successful', 'operations_total'),
    )

    def __repr__(self) -> str:
        return (
            f"<ServicePerformanceMetric(service_name={self.service_name}, "
            f"time={self.time}, operations_total={self.operations_total})>"
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this service period"""
        orm_self = cast(Any, self)
        if int(orm_self.operations_total) == 0:
            return 0.0
        return float(orm_self.operations_successful) / float(orm_self.operations_total)

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate for this service period"""
        orm_self = cast(Any, self)
        if int(orm_self.operations_total) == 0:
            return 0.0
        return float(orm_self.operations_cached) / float(orm_self.operations_total)

    @property
    def ssh_connection_reuse_rate(self) -> float:
        """Calculate SSH connection reuse rate"""
        orm_self = cast(Any, self)
        total_connections = int(orm_self.ssh_connections_created) + int(
            orm_self.ssh_connections_reused
        )
        if total_connections == 0:
            return 0.0
        return float(orm_self.ssh_connections_reused) / float(total_connections)


class CacheMetadata(Base):
    """
    Track cache state and invalidation across all services.
    
    This model provides visibility into cache performance, tracks cache entries
    lifecycle, and supports cache invalidation strategies.
    """
    __tablename__ = "cache_metadata"

    # Primary identification
    cache_key = Column(String(255), primary_key=True)  # MD5 hash of cache key
    device_id = Column(PGUUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    data_type = Column(String(50), nullable=False, index=True)

    # Cache lifecycle
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_accessed = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Usage statistics
    access_count = Column(Integer, default=1)  # Number of cache hits
    data_size_bytes = Column(Integer)  # Cached data size
    ttl_seconds = Column(Integer, nullable=False)  # Cache TTL

    # Invalidation tracking
    invalidated = Column(Boolean, default=False, index=True)  # Manual invalidation flag
    invalidated_at = Column(DateTime(timezone=True))  # Invalidation timestamp
    invalidation_reason = Column(String(100))  # Why invalidated

    # Source tracking
    collection_method = Column(String(50))  # How data was collected
    command_hash = Column(String(64))  # SSH command fingerprint
    collection_duration_ms = Column(Integer)  # Time to collect original data

    # Performance tracking
    hit_rate = Column(Numeric(5, 2), default=0.0)  # Hit rate for this cache key
    avg_access_interval = Column(Integer)  # Average time between accesses

    # Relationships
    device = relationship("Device")

    # Efficient cleanup and monitoring indexes
    __table_args__ = (
        Index('idx_cache_device_type', 'device_id', 'data_type'),
        Index('idx_cache_expires_invalidated', 'expires_at', 'invalidated'),
        Index('idx_cache_access_pattern', 'last_accessed', 'access_count'),
        Index('idx_cache_performance', 'hit_rate', 'data_type'),
        Index('idx_cache_cleanup', 'expires_at', 'invalidated'),
    )

    def __repr__(self) -> str:
        return (
            f"<CacheMetadata(cache_key={self.cache_key[:16]}..., "
            f"data_type={self.data_type}, device_id={self.device_id}, "
            f"access_count={self.access_count})>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        orm_self = cast(Any, self)
        expires_at_dt = cast(datetime, orm_self.expires_at)
        return datetime.now(UTC) > expires_at_dt

    @property
    def age_seconds(self) -> int:
        """Get age of cache entry in seconds"""
        orm_self = cast(Any, self)
        return int((datetime.now(UTC) - orm_self.created_at).total_seconds())

    @property
    def time_to_expiry_seconds(self) -> int:
        """Get time until expiry in seconds"""
        orm_self = cast(Any, self)
        return max(0, int((orm_self.expires_at - datetime.now(UTC)).total_seconds()))

    def update_access_stats(self) -> None:
        """Update access statistics when cache is hit"""
        now = datetime.now(UTC)

        # Update access tracking
        orm_self = cast(Any, self)
        if int(orm_self.access_count) > 0:
            # Calculate average access interval
            total_time = (now - self.created_at).total_seconds()
            orm_self.avg_access_interval = int(total_time / int(orm_self.access_count))

        orm_self.access_count = int(orm_self.access_count) + 1
        orm_self.last_accessed = now

        # Update hit rate (simple calculation)
        if int(orm_self.access_count) > 1:
            orm_self.hit_rate = min(
                100.0,
                (int(orm_self.access_count) - 1) / float(orm_self.access_count) * 100,
            )
