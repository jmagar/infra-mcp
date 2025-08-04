"""
Data collection audit models for tracking infrastructure data collection operations.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from apps.backend.src.core.database import Base


class DataCollectionAudit(Base):
    """
    Data collection audit table for tracking all infrastructure data collection operations.

    This hypertable tracks every data collection operation performed by the system,
    providing comprehensive visibility into data freshness, performance, and reliability.
    """

    __tablename__ = "data_collection_audit"

    # Time-series primary key components
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    operation_id = Column(PGUUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)

    # Collection operation metadata
    data_type = Column(String(50), nullable=False, index=True)
    collection_method = Column(String(50), nullable=False, index=True)
    collection_source = Column(String(100), index=True)

    # Collection behavior flags
    force_refresh = Column(Boolean, default=False, nullable=False)
    cache_hit = Column(Boolean, default=False, nullable=False)

    # Performance metrics
    duration_ms = Column(Integer)
    ssh_command_count = Column(Integer, default=0)
    data_size_bytes = Column(BigInteger)

    # Operation status and results
    status = Column(String(20), nullable=False, index=True)  # success, failed, partial, timeout
    error_message = Column(Text)
    warnings = Column(JSONB, default=list)

    # Data modification tracking
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)

    # Cache and freshness configuration
    freshness_threshold = Column(Integer)  # Freshness threshold in seconds

    # Relationships
    device = relationship("Device", back_populates="data_collection_audits")

    def __repr__(self) -> str:
        return (
            f"<DataCollectionAudit("
            f"time={self.time.isoformat() if self.time else None}, "
            f"device_id={self.device_id}, "
            f"operation_id={self.operation_id}, "
            f"data_type='{self.data_type}', "
            f"status='{self.status}', "
            f"duration_ms={self.duration_ms}"
            f")>"
        )

    @property
    def is_successful(self) -> bool:
        """Check if the collection operation was successful."""
        return self.status == "success"

    @property
    def has_warnings(self) -> bool:
        """Check if the collection operation had warnings."""
        return bool(self.warnings and len(self.warnings) > 0)

    @property
    def cache_hit_ratio(self) -> float | None:
        """Calculate cache hit ratio if applicable."""
        if self.cache_hit:
            return 1.0
        return 0.0 if self.cache_hit is not None else None

    @classmethod
    def create_operation_record(
        cls,
        device_id: UUID,
        data_type: str,
        collection_method: str,
        status: str,
        collection_source: str | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
        warnings: list[str] | None = None,
        records_created: int = 0,
        records_updated: int = 0,
        ssh_command_count: int = 0,
        data_size_bytes: int | None = None,
        force_refresh: bool = False,
        cache_hit: bool = False,
        freshness_threshold: int | None = None,
    ) -> "DataCollectionAudit":
        """
        Factory method to create a new data collection audit record.

        Args:
            device_id: UUID of the device being collected from
            data_type: Type of data being collected (e.g., 'system_metrics', 'containers')
            collection_method: Method used for collection (e.g., 'ssh', 'api', 'cache')
            status: Collection status ('success', 'failed', 'partial', 'timeout')
            collection_source: Source of the collection (e.g., service name)
            duration_ms: Collection duration in milliseconds
            error_message: Error message if collection failed
            warnings: List of warnings during collection
            records_created: Number of database records created
            records_updated: Number of database records updated
            ssh_command_count: Number of SSH commands executed
            data_size_bytes: Size of collected data in bytes
            force_refresh: Whether cache was bypassed
            cache_hit: Whether data was served from cache
            freshness_threshold: Freshness threshold used in seconds

        Returns:
            New DataCollectionAudit instance
        """
        return cls(
            time=datetime.now(UTC),
            device_id=device_id,
            operation_id=uuid4(),
            data_type=data_type,
            collection_method=collection_method,
            collection_source=collection_source,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
            warnings=warnings or [],
            records_created=records_created,
            records_updated=records_updated,
            ssh_command_count=ssh_command_count,
            data_size_bytes=data_size_bytes,
            force_refresh=force_refresh,
            cache_hit=cache_hit,
            freshness_threshold=freshness_threshold,
        )
