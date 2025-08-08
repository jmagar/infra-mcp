"""
Container-related models for snapshots and metrics.
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from apps.backend.src.core.database import Base


class ContainerSnapshot(Base):
    """Container snapshots and metrics (hypertable)"""

    __tablename__ = "container_snapshots"

    # Time-series primary key
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Container identification
    container_id = Column(String(64), primary_key=True, nullable=False)
    container_name = Column(String(255), nullable=False)
    image = Column(String(255))

    # Container status
    status = Column(String(50))
    state = Column(JSONB, default=lambda: {})
    running = Column(Boolean)
    paused = Column(Boolean)
    restarting = Column(Boolean)
    oom_killed = Column(Boolean)
    dead = Column(Boolean)
    pid = Column(Integer)
    exit_code = Column(Integer)

    # Resource usage metrics
    cpu_usage_percent = Column(Numeric(5, 2))
    memory_usage_bytes = Column(BigInteger)
    memory_limit_bytes = Column(BigInteger)
    memory_cache_bytes = Column(BigInteger)

    # Network metrics
    network_bytes_sent = Column(BigInteger)
    network_bytes_recv = Column(BigInteger)

    # Block I/O metrics
    block_read_bytes = Column(BigInteger)
    block_write_bytes = Column(BigInteger)

    # Configuration data
    ports = Column(JSONB, default=lambda: [])
    environment = Column(JSONB, default=lambda: {})
    labels = Column(JSONB, default=lambda: {})
    volumes = Column(JSONB, default=lambda: [])
    networks = Column(JSONB, default=lambda: [])
    resource_limits = Column(JSONB, default=lambda: {})
    metadata_info = Column(JSONB, default=lambda: {})
    created_at = Column(DateTime(timezone=True))

    # Relationships
    device = relationship("Device", back_populates="container_snapshots")
