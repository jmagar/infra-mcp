"""
Container-related models for snapshots and metrics.
"""

from sqlalchemy import Column, DateTime, ForeignKey, String, BigInteger, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    state = Column(String(50))

    # Resource usage metrics
    cpu_usage_percent = Column(Numeric(5, 2))
    memory_usage_bytes = Column(BigInteger)
    memory_limit_bytes = Column(BigInteger)

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

    # Relationships
    device = relationship("Device", back_populates="container_snapshots")
