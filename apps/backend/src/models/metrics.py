"""
Time-series metrics models for system and drive health.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from apps.backend.src.core.database import Base


class SystemMetric(Base):
    """System metrics time-series data (hypertable)"""

    __tablename__ = "system_metrics"

    # Time-series primary key
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # CPU metrics
    cpu_usage_percent = Column(Numeric(5, 2))

    # Memory metrics
    memory_usage_percent = Column(Numeric(5, 2))
    memory_total_bytes = Column(BigInteger)
    memory_available_bytes = Column(BigInteger)

    # Load average metrics
    load_average_1m = Column(Numeric(6, 2))
    load_average_5m = Column(Numeric(6, 2))
    load_average_15m = Column(Numeric(6, 2))

    # Disk metrics
    disk_usage_percent = Column(Numeric(5, 2))
    disk_total_bytes = Column(BigInteger)
    disk_available_bytes = Column(BigInteger)

    # Network metrics
    network_bytes_sent = Column(BigInteger)
    network_bytes_recv = Column(BigInteger)

    # Process and uptime metrics
    uptime_seconds = Column(BigInteger)
    process_count = Column(Integer)

    # Additional metrics as JSON
    additional_metrics = Column(JSONB, default={})

    # Relationships
    device = relationship("Device", back_populates="system_metrics")


class DriveHealth(Base):
    """Drive health monitoring data (hypertable)"""

    __tablename__ = "drive_health"

    # Time-series primary key
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    drive_name = Column(
        String(100), primary_key=True, nullable=False
    )  # /dev/sda, /dev/nvme0n1, etc.

    # Drive information
    drive_type = Column(String(20))  # ssd, hdd, nvme
    model = Column(String(255))
    serial_number = Column(String(255))
    capacity_bytes = Column(BigInteger)

    # Health metrics
    temperature_celsius = Column(Integer)
    power_on_hours = Column(Integer)
    total_lbas_written = Column(BigInteger)
    total_lbas_read = Column(BigInteger)
    reallocated_sectors = Column(Integer)
    pending_sectors = Column(Integer)
    uncorrectable_errors = Column(Integer)

    # Status indicators
    smart_status = Column(String(20), index=True)  # PASSED, FAILED, UNKNOWN
    smart_attributes = Column(JSONB, default={})
    health_status = Column(
        String(20), default="unknown", index=True
    )  # healthy, warning, critical, unknown

    # Relationships
    device = relationship("Device", back_populates="drive_health")
