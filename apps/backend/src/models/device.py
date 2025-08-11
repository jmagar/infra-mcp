"""
Device models for infrastructure registry and management.
"""

from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
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
    ip_address = Column(INET, nullable=True, index=True)  # Optional - SSH config handles this
    ssh_port = Column(Integer, nullable=True)  # Optional - SSH config handles this
    ssh_username = Column(String(100), nullable=True)  # Optional - SSH config handles this

    # Device classification
    device_type = Column(
        String(50), default="server", index=True
    )  # server, container_host, storage, network
    description = Column(Text)
    location = Column(String(255))
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

    # Glances API configuration
    glances_enabled = Column(Boolean, default=True, nullable=False)
    glances_port = Column(Integer, default=61208, nullable=False)
    glances_url = Column(String(512), nullable=True)  # Optional custom URL override

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
    configuration_snapshots = relationship(
        "ConfigurationSnapshot", back_populates="device", cascade="all, delete-orphan"
    )
    audit_records = relationship(
        "DataCollectionAudit", back_populates="device", cascade="all, delete-orphan"
    )
    # Proxy configuration relationship
    proxy_configs = relationship(
        "ProxyConfig", back_populates="device", cascade="all, delete-orphan"
    )
    # Additional relationships defined in original models.py will be added here

    @property
    def glances_endpoint(self) -> str:
        """Get Glances API endpoint URL"""
        if self.glances_url:
            return self.glances_url
        return f"http://{self.hostname}:{self.glances_port}"
