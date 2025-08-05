"""
Notification Models

Simplified notification models for Gotify-only configuration change alerts.
Focuses on configuration change tracking with risk-based priority mapping.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class NotificationPriority(str, Enum):
    """Notification priority levels mapped to Gotify priorities."""

    LOW = "low"  # Gotify priority 0-2
    MEDIUM = "medium"  # Gotify priority 3-5
    HIGH = "high"  # Gotify priority 6-7
    CRITICAL = "critical"  # Gotify priority 8-9
    URGENT = "urgent"  # Gotify priority 10


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class GotifyNotificationConfig(Base):
    """
    Gotify notification configuration.

    Stores the Gotify server connection details and app token
    for sending configuration change notifications.
    """

    __tablename__ = "gotify_notification_config"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True, default="default")

    # Gotify configuration
    app_token = Column(String(255), nullable=False)
    gotify_url = Column(String(500), nullable=True)  # Optional if using MCP

    # Priority mapping for risk levels
    priority_mapping = Column(
        JSON,
        nullable=False,
        default={"low": 1, "medium": 4, "high": 7, "critical": 9, "urgent": 10},
    )

    # Rate limiting
    rate_limit_per_hour = Column(Integer, nullable=False, default=60)

    # Status
    active = Column(Boolean, nullable=False, default=True)
    last_test_at = Column(DateTime(timezone=True), nullable=True)
    last_test_success = Column(Boolean, nullable=True)
    last_error = Column(Text, nullable=True)

    # Metadata
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(String(255), nullable=False, default="system")
    updated_by = Column(String(255), nullable=False, default="system")


class ConfigurationAlert(Base):
    """
    Configuration change alert records.

    Tracks configuration change alerts sent to Gotify with
    delivery status and performance metrics.
    """

    __tablename__ = "configuration_alerts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Alert details
    event_id = Column(String(255), nullable=False)  # Reference to ConfigurationChangeEvent
    device_id = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    configuration_path = Column(String(1000), nullable=False)
    change_type = Column(String(50), nullable=False)
    risk_level = Column(String(20), nullable=False)

    # Notification content
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False)

    # Alert context data
    alert_data = Column(JSON, nullable=False, default=dict)

    # Gotify delivery tracking
    gotify_message_id = Column(Integer, nullable=True)  # Gotify message ID after send
    status = Column(String(20), nullable=False, default="pending")
    delivery_attempts = Column(Integer, nullable=False, default=0)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Performance metrics
    processing_time_ms = Column(Integer, nullable=True)
    delivery_time_ms = Column(Integer, nullable=True)

    # Relationships
    device = relationship("Device", back_populates="configuration_alerts")
    config = relationship("GotifyNotificationConfig")
    config_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("gotify_notification_config.id"), nullable=False
    )

    # Metadata
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class AlertSuppression(Base):
    """
    Alert suppression rules to prevent notification spam.

    Suppresses duplicate or similar alerts within specified time windows
    based on device, configuration path, and risk level.
    """

    __tablename__ = "alert_suppressions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Suppression rule
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Rule criteria (None means applies to all)
    device_id = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True)
    configuration_path_pattern = Column(String(1000), nullable=True)  # Glob pattern
    change_type = Column(String(50), nullable=True)  # Specific change type
    min_risk_level = Column(String(20), nullable=True)  # Minimum risk level to suppress

    # Suppression settings by risk level
    suppression_window_minutes = Column(
        JSON,
        nullable=False,
        default={"low": 60, "medium": 30, "high": 15, "critical": 5, "urgent": 1},
    )
    max_alerts_in_window = Column(
        JSON,
        nullable=False,
        default={"low": 1, "medium": 2, "high": 3, "critical": 5, "urgent": 10},
    )

    # Rule status
    active = Column(Boolean, nullable=False, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(JSON, nullable=False, default=dict)  # Recent trigger stats

    # Metadata
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(String(255), nullable=False, default="system")
    updated_by = Column(String(255), nullable=False, default="system")
