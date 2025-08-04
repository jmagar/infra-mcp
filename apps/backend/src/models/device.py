"""
Device models for infrastructure registry and management.
"""

from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from apps.backend.src.core.database import Base


class Device(Base):
    """Device registry table for infrastructure nodes"""

    __tablename__ = "devices"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Basic device information
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    
    # Device classification
    device_type = Column(
        String(50), default="server", index=True
    )  # server, container_host, storage, network
    description = Column(Text)
    location = Column(String(255))
    device_metadata = Column(JSONB, default={})  # Device-specific metadata
    tags = Column(JSONB, default={})

    # Docker configuration paths
    docker_compose_path = Column(String(512), nullable=True)  # Primary docker-compose project path
    docker_appdata_path = Column(String(512), nullable=True)  # Primary appdata directory path

    # Monitoring configuration
    monitoring_enabled = Column(Boolean, default=True, index=True)
    last_seen = Column(DateTime(timezone=True), index=True)
    status = Column(
        String(20), default="unknown", index=True
    )  # online, offline, unknown, maintenance
    
    # Phase 1: Data collection status tracking
    last_successful_collection = Column(DateTime(timezone=True), index=True)
    last_collection_status = Column(String(20), default="never", index=True)  # never, success, failed, timeout
    collection_error_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships (will be imported to avoid circular imports)
    system_metrics = relationship(
        "SystemMetric", back_populates="device", cascade="all, delete-orphan"
    )
    drive_health = relationship(
        "DriveHealth", back_populates="device", cascade="all, delete-orphan"
    )
    container_snapshots = relationship(
        "ContainerSnapshot", back_populates="device", cascade="all, delete-orphan"
    )
    
    # Phase 1: New audit and configuration relationships
    data_collection_audits = relationship(
        "DataCollectionAudit", back_populates="device", cascade="all, delete-orphan"
    )
    configuration_snapshots = relationship(
        "ConfigurationSnapshot", back_populates="device", cascade="all, delete-orphan"
    )
    configuration_change_events = relationship(
        "ConfigurationChangeEvent", back_populates="device", cascade="all, delete-orphan"
    )
    cache_metadata = relationship(
        "CacheMetadata", back_populates="device", cascade="all, delete-orphan"
    )
