"""
Service performance metrics models for tracking infrastructure service performance.
"""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB

from apps.backend.src.core.database import Base


class ServicePerformanceMetric(Base):
    """
    Service performance metrics table for tracking infrastructure service performance.

    This hypertable tracks performance metrics for various infrastructure services,
    providing insights into service health, performance trends, and operational efficiency.
    """

    __tablename__ = "service_performance_metrics"

    # Time-series primary key
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    service_name = Column(String(50), primary_key=True, nullable=False, index=True)

    # Operation counters
    operations_total = Column(Integer, default=0, nullable=False)
    operations_successful = Column(Integer, default=0, nullable=False)
    operations_failed = Column(Integer, default=0, nullable=False)

    # Duration metrics (in milliseconds)
    avg_duration_ms = Column(Numeric(10, 3))
    min_duration_ms = Column(Numeric(10, 3))
    max_duration_ms = Column(Numeric(10, 3))
    p95_duration_ms = Column(Numeric(10, 3))
    p99_duration_ms = Column(Numeric(10, 3))

    # Cache performance metrics
    cache_hit_count = Column(Integer, default=0, nullable=False)
    cache_miss_count = Column(Integer, default=0, nullable=False)

    # Error tracking counters
    error_count = Column(Integer, default=0, nullable=False)
    timeout_count = Column(Integer, default=0, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)

    # Performance metrics
    throughput_ops_per_sec = Column(Numeric(10, 3))
    concurrent_operations = Column(Integer)

    # Resource usage metrics
    memory_usage_bytes = Column(BigInteger)
    cpu_usage_percent = Column(Numeric(5, 2))
    network_io_bytes = Column(BigInteger)
    disk_io_bytes = Column(BigInteger)
    
    # Additional metadata (using different name to avoid SQLAlchemy conflict)
    performance_metadata = Column('metadata', JSONB, default=lambda: {})

    def __repr__(self) -> str:
        return (
            f"<ServicePerformanceMetric("
            f"time={self.time.isoformat() if self.time else None}, "
            f"service_name='{self.service_name}', "
            f"operations_total={self.operations_total}, "
            f"success_rate={self.success_rate:.2f}%, "
            f"avg_duration_ms={self.avg_duration_ms}"
            f")>"
        )

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.operations_total == 0:
            return 0.0
        return (self.operations_successful / self.operations_total) * 100.0

    @property
    def failure_rate(self) -> float:
        """Calculate the failure rate as a percentage."""
        return 100.0 - self.success_rate

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage (0.0 to 100.0)."""
        total_cache_ops = self.cache_hit_count + self.cache_miss_count
        if total_cache_ops == 0:
            return 0.0
        return (self.cache_hit_count / total_cache_ops) * 100.0

    @property
    def error_rate(self) -> float:
        """Calculate error rate as a percentage."""
        if self.operations_total == 0:
            return 0.0
        return (self.error_count / self.operations_total) * 100.0

    @property
    def timeout_rate(self) -> float:
        """Calculate timeout rate as a percentage."""
        if self.operations_total == 0:
            return 0.0
        return (self.timeout_count / self.operations_total) * 100.0

    @property
    def retry_rate(self) -> float:
        """Calculate retry rate as a percentage."""
        if self.operations_total == 0:
            return 0.0
        return (self.retry_count / self.operations_total) * 100.0

    @property
    def is_performing_well(self) -> bool:
        """
        Determine if the service is performing well based on key metrics.

        Criteria:
        - Success rate >= 95%
        - Average duration <= 5000ms
        - Cache hit ratio >= 50% (if applicable)
        """
        return (
            self.success_rate >= 95.0
            and (self.avg_duration_ms is None or self.avg_duration_ms <= 5000)
            and self.error_rate <= 5.0
        )

    @property
    def performance_grade(self) -> str:
        """
        Get a letter grade (A-F) based on overall performance.

        Grade criteria:
        A: Success rate >= 99%, avg duration <= 1000ms
        B: Success rate >= 95%, avg duration <= 3000ms
        C: Success rate >= 90%, avg duration <= 5000ms
        D: Success rate >= 80%, avg duration <= 10000ms
        F: Below D criteria
        """
        avg_duration = float(self.avg_duration_ms) if self.avg_duration_ms else 0.0

        if self.success_rate >= 99.0 and avg_duration <= 1000:
            return "A"
        elif self.success_rate >= 95.0 and avg_duration <= 3000:
            return "B"
        elif self.success_rate >= 90.0 and avg_duration <= 5000:
            return "C"
        elif self.success_rate >= 80.0 and avg_duration <= 10000:
            return "D"
        else:
            return "F"

    def get_top_error_types(self, limit: int = 5) -> list[dict[str, int | str]]:
        """
        Get the top error types sorted by occurrence count.

        Args:
            limit: Maximum number of error types to return

        Returns:
            List of error type dictionaries with 'error' and 'count' keys
        """
        error_types = self.performance_metadata.get("error_types", {}) if self.performance_metadata else {}
        if not error_types:
            return []

        sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)

        return [
            {"error": error_type, "count": count} for error_type, count in sorted_errors[:limit]
        ]

    @classmethod
    def create_metric_record(
        cls,
        service_name: str,
        operations_total: int = 0,
        operations_successful: int = 0,
        operations_failed: int = 0,
        operations_cached: int = 0,
        avg_duration_ms: float | None = None,
        max_duration_ms: int | None = None,
        min_duration_ms: int | None = None,
        ssh_connections_created: int = 0,
        ssh_connections_reused: int = 0,
        ssh_commands_executed: int = 0,
        cache_hit_ratio: float | None = None,
        cache_size_entries: int | None = None,
        cache_evictions: int = 0,
        data_collected_bytes: int = 0,
        database_writes: int = 0,
        error_types: dict[str, int] | None = None,
        top_errors: list[dict[str, int | str]] | None = None,
    ) -> "ServicePerformanceMetric":
        """
        Factory method to create a new service performance metric record.

        Args:
            service_name: Name of the service being measured
            operations_total: Total number of operations
            operations_successful: Number of successful operations
            operations_failed: Number of failed operations
            operations_cached: Number of operations served from cache
            avg_duration_ms: Average operation duration in milliseconds
            max_duration_ms: Maximum operation duration in milliseconds
            min_duration_ms: Minimum operation duration in milliseconds
            ssh_connections_created: Number of new SSH connections created
            ssh_connections_reused: Number of SSH connections reused
            ssh_commands_executed: Number of SSH commands executed
            cache_hit_ratio: Cache hit ratio as percentage (0.0 to 100.0)
            cache_size_entries: Number of entries in cache
            cache_evictions: Number of cache evictions
            data_collected_bytes: Total bytes of data collected
            database_writes: Number of database write operations
            error_types: Dictionary of error types and their counts
            top_errors: List of top errors with counts

        Returns:
            New ServicePerformanceMetric instance
        """
        return cls(
            time=datetime.now(UTC),
            service_name=service_name,
            operations_total=operations_total,
            operations_successful=operations_successful,
            operations_failed=operations_failed,
            avg_duration_ms=avg_duration_ms,
            max_duration_ms=max_duration_ms,
            min_duration_ms=min_duration_ms,
            performance_metadata={
                "operations_cached": operations_cached,
                "ssh_connections_created": ssh_connections_created,
                "ssh_connections_reused": ssh_connections_reused,
                "ssh_commands_executed": ssh_commands_executed,
                "cache_hit_ratio": cache_hit_ratio,
                "cache_size_entries": cache_size_entries,
                "cache_evictions": cache_evictions,
                "data_collected_bytes": data_collected_bytes,
                "database_writes": database_writes,
                "error_types": error_types or {},
                "top_errors": top_errors or [],
            }
        )
