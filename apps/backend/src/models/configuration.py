"""
Configuration Snapshot models for infrastructure configuration monitoring.

This module defines models for storing historical configuration snapshots
and change events, providing the persistence layer for real-time configuration
monitoring functionality.
"""

from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from apps.backend.src.core.database import Base


class ConfigurationSnapshot(Base):
    """
    Configuration snapshot table for storing historical configuration data.
    
    This model stores snapshots of configuration files from devices, enabling
    tracking of configuration changes over time for audit and rollback purposes.
    """

    __tablename__ = "configuration_snapshots"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Device relationship
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Temporal information
    time = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
    )

    # Configuration metadata
    config_type = Column(
        String(100),
        nullable=False,
        index=True,
    )  # docker-compose, nginx-config, swag-proxy, etc.

    file_path = Column(
        String(1024),
        nullable=False,
        index=True,
    )  # Full path to the configuration file

    content_hash = Column(
        String(128),
        nullable=False,
        index=True,
    )  # SHA-256 hash of the configuration content

    # Configuration content
    raw_content = Column(
        Text,
        nullable=False,
    )  # Raw configuration file content

    parsed_data = Column(
        JSONB,
        nullable=True,
    )  # Parsed/structured configuration data

    # Change tracking
    change_type = Column(
        String(20),
        nullable=False,
        default="MODIFY",
        index=True,
    )  # CREATE, MODIFY, DELETE

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships
    device = relationship("Device", back_populates="configuration_snapshots")

    # Indexes for common query patterns
    __table_args__ = (
        # Index for time-based queries on specific devices
        Index(
            "ix_config_snapshots_device_time",
            "device_id",
            "time",
        ),
        # Index for finding latest snapshot of specific config type per device
        Index(
            "ix_config_snapshots_device_type_time",
            "device_id",
            "config_type",
            "time",
        ),
        # Index for content hash lookups (deduplication)
        Index(
            "ix_config_snapshots_hash_lookup",
            "device_id",
            "file_path",
            "content_hash",
        ),
        # Index for change type queries
        Index(
            "ix_config_snapshots_change_tracking",
            "device_id",
            "change_type",
            "time",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ConfigurationSnapshot(id={self.id}, device_id={self.device_id}, "
            f"config_type='{self.config_type}', file_path='{self.file_path}', "
            f"change_type='{self.change_type}', time={self.time})>"
        )

    def to_dict(self) -> dict:
        """Convert model instance to dictionary for serialization."""
        return {
            "id": str(self.id),
            "device_id": str(self.device_id),
            "time": self.time.isoformat() if self.time else None,
            "config_type": self.config_type,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "raw_content": self.raw_content,
            "parsed_data": self.parsed_data,
            "change_type": self.change_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
