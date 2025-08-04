"""
Configuration management models for tracking infrastructure configuration changes.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from apps.backend.src.core.database import Base


class ConfigurationSnapshot(Base):
    """
    Configuration snapshots table for storing infrastructure configuration file snapshots.

    This hypertable stores snapshots of configuration files over time, enabling
    change tracking, rollback capabilities, and configuration drift detection.
    """

    __tablename__ = "configuration_snapshots"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key and time for hypertable
    device_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    time = Column(DateTime(timezone=True), nullable=False, index=True)

    # Configuration file metadata
    config_type = Column(String(50), nullable=False, index=True)  # docker-compose, nginx, etc.
    file_path = Column(String(1024), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, index=True)
    file_size_bytes = Column(Integer)

    # File content storage
    raw_content = Column(Text, nullable=False)
    parsed_data = Column(JSONB, default=dict)

    # Change tracking
    change_type = Column(String(20), nullable=False, index=True)  # created, modified, deleted
    previous_hash = Column(String(64))
    file_modified_time = Column(DateTime(timezone=True))

    # Collection metadata
    collection_source = Column(String(50), nullable=False)
    detection_latency_ms = Column(Integer)

    # Impact analysis
    affected_services = Column(JSONB, default=list)
    requires_restart = Column(Boolean, default=False)
    risk_level = Column(String(20), default="MEDIUM", index=True)  # LOW, MEDIUM, HIGH, CRITICAL

    # Relationships
    device = relationship("Device", back_populates="configuration_snapshots")
    change_events = relationship(
        "ConfigurationChangeEvent", back_populates="snapshot", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<ConfigurationSnapshot("
            f"id={self.id}, "
            f"device_id={self.device_id}, "
            f"config_type='{self.config_type}', "
            f"file_path='{self.file_path}', "
            f"change_type='{self.change_type}', "
            f"risk_level='{self.risk_level}'"
            f")>"
        )

    @property
    def is_high_risk(self) -> bool:
        """Check if this configuration change is high risk."""
        return self.risk_level in ("HIGH", "CRITICAL")

    @property
    def needs_service_restart(self) -> bool:
        """Check if this configuration change requires service restart."""
        return self.requires_restart and bool(self.affected_services)

    @classmethod
    def create_snapshot(
        cls,
        device_id: UUID,
        config_type: str,
        file_path: str,
        content_hash: str,
        raw_content: str,
        change_type: str,
        collection_source: str,
        parsed_data: dict | None = None,
        file_size_bytes: int | None = None,
        previous_hash: str | None = None,
        file_modified_time: datetime | None = None,
        detection_latency_ms: int | None = None,
        affected_services: list[str] | None = None,
        requires_restart: bool = False,
        risk_level: str = "MEDIUM",
    ) -> "ConfigurationSnapshot":
        """
        Factory method to create a new configuration snapshot.

        Args:
            device_id: UUID of the device
            config_type: Type of configuration (e.g., 'docker-compose', 'nginx')
            file_path: Path to the configuration file
            content_hash: Hash of the file content
            raw_content: Raw file content
            change_type: Type of change ('created', 'modified', 'deleted')
            collection_source: Source of the snapshot collection
            parsed_data: Parsed configuration data
            file_size_bytes: Size of the file in bytes
            previous_hash: Hash of the previous version
            file_modified_time: When the file was last modified
            detection_latency_ms: Time taken to detect the change
            affected_services: List of services affected by this change
            requires_restart: Whether services need to be restarted
            risk_level: Risk level of the change

        Returns:
            New ConfigurationSnapshot instance
        """
        return cls(
            device_id=device_id,
            time=datetime.now(UTC),
            config_type=config_type,
            file_path=file_path,
            content_hash=content_hash,
            raw_content=raw_content,
            parsed_data=parsed_data or {},
            change_type=change_type,
            collection_source=collection_source,
            file_size_bytes=file_size_bytes,
            previous_hash=previous_hash,
            file_modified_time=file_modified_time,
            detection_latency_ms=detection_latency_ms,
            affected_services=affected_services or [],
            requires_restart=requires_restart,
            risk_level=risk_level,
        )


class ConfigurationChangeEvent(Base):
    """
    Configuration change events table for tracking processed configuration changes.

    This hypertable tracks events generated from configuration snapshots,
    providing workflow management and notification tracking capabilities.
    """

    __tablename__ = "configuration_change_events"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys and time for hypertable
    device_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("configuration_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    time = Column(DateTime(timezone=True), nullable=False, index=True)

    # Event metadata (duplicated from snapshot for querying efficiency)
    config_type = Column(String(50), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    change_type = Column(String(20), nullable=False, index=True)

    # Service impact analysis
    affected_services = Column(JSONB, default=list)
    service_dependencies = Column(JSONB, default=list)
    requires_restart = Column(Boolean, default=False)
    restart_services = Column(JSONB, default=list)

    # Change analysis
    changes_summary = Column(JSONB, default=dict)
    risk_level = Column(String(20), default="MEDIUM", index=True)
    confidence_score = Column(Numeric(3, 2))  # 0.00 to 1.00

    # Event processing status
    processed = Column(Boolean, default=False, index=True)
    notifications_sent = Column(JSONB, default=list)

    # Relationships
    device = relationship("Device", back_populates="configuration_change_events")
    snapshot = relationship("ConfigurationSnapshot", back_populates="change_events")

    def __repr__(self) -> str:
        return (
            f"<ConfigurationChangeEvent("
            f"id={self.id}, "
            f"device_id={self.device_id}, "
            f"config_type='{self.config_type}', "
            f"change_type='{self.change_type}', "
            f"processed={self.processed}, "
            f"risk_level='{self.risk_level}'"
            f")>"
        )

    @property
    def is_critical_change(self) -> bool:
        """Check if this is a critical configuration change."""
        return self.risk_level == "CRITICAL" or (
            self.confidence_score is not None and self.confidence_score >= 0.9
        )

    @property
    def needs_immediate_attention(self) -> bool:
        """Check if this change needs immediate attention."""
        return self.is_critical_change and not self.processed and self.requires_restart

    @property
    def notification_channels_used(self) -> list[str]:
        """Get list of notification channels that were used."""
        if not self.notifications_sent:
            return []
        return [notif.get("channel") for notif in self.notifications_sent if notif.get("channel")]

    def mark_as_processed(self) -> None:
        """Mark this change event as processed."""
        self.processed = True

    def add_notification_sent(
        self, channel: str, status: str, message_id: str | None = None
    ) -> None:
        """
        Add a notification sent record.

        Args:
            channel: Notification channel used (e.g., 'email', 'slack', 'webhook')
            status: Notification status ('sent', 'failed', 'pending')
            message_id: Optional message ID from the notification service
        """
        if not self.notifications_sent:
            self.notifications_sent = []

        self.notifications_sent.append(
            {
                "channel": channel,
                "status": status,
                "message_id": message_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    @classmethod
    def create_from_snapshot(
        cls,
        snapshot: ConfigurationSnapshot,
        changes_summary: dict | None = None,
        confidence_score: float | None = None,
        service_dependencies: list[str] | None = None,
        restart_services: list[str] | None = None,
    ) -> "ConfigurationChangeEvent":
        """
        Factory method to create a change event from a configuration snapshot.

        Args:
            snapshot: ConfigurationSnapshot instance
            changes_summary: Summary of what changed
            confidence_score: Confidence in the change analysis (0.0 to 1.0)
            service_dependencies: List of dependent services
            restart_services: List of services that need restart

        Returns:
            New ConfigurationChangeEvent instance
        """
        return cls(
            device_id=snapshot.device_id,
            snapshot_id=snapshot.id,
            time=datetime.now(UTC),
            config_type=snapshot.config_type,
            file_path=snapshot.file_path,
            change_type=snapshot.change_type,
            affected_services=snapshot.affected_services or [],
            service_dependencies=service_dependencies or [],
            requires_restart=snapshot.requires_restart,
            restart_services=restart_services or [],
            changes_summary=changes_summary or {},
            risk_level=snapshot.risk_level,
            confidence_score=confidence_score,
        )
