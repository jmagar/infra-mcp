"""
Notification Schemas

Simplified Pydantic schemas for Gotify-only configuration change notifications.
Focuses on configuration change alerts with risk-based priority mapping.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from ..models.notification import NotificationPriority, NotificationStatus


class NotificationBase(BaseModel):
    """Base notification schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


# Gotify Configuration Schemas
class GotifyConfigCreate(NotificationBase):
    """Schema for creating Gotify notification configuration."""

    name: str = Field(default="default", min_length=1, max_length=255)
    app_token: str = Field(..., min_length=1, max_length=255)
    gotify_url: str | None = Field(None, max_length=500)

    priority_mapping: dict[str, int] = Field(
        default={"low": 1, "medium": 4, "high": 7, "critical": 9, "urgent": 10},
        description="Mapping of risk levels to Gotify priority integers (0-10)",
    )
    rate_limit_per_hour: int = Field(default=60, ge=1, le=1000)


class GotifyConfigUpdate(NotificationBase):
    """Schema for updating Gotify notification configuration."""

    name: str | None = Field(None, min_length=1, max_length=255)
    app_token: str | None = Field(None, min_length=1, max_length=255)
    gotify_url: str | None = Field(None, max_length=500)
    priority_mapping: dict[str, int] | None = None
    rate_limit_per_hour: int | None = Field(None, ge=1, le=1000)
    active: bool | None = None


class GotifyConfigResponse(NotificationBase):
    """Schema for Gotify configuration responses."""

    id: UUID
    name: str
    app_token: str  # In production, this should be masked
    gotify_url: str | None
    priority_mapping: dict[str, int]
    rate_limit_per_hour: int
    active: bool
    last_test_at: datetime | None
    last_test_success: bool | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str


class GotifyConfigTest(NotificationBase):
    """Schema for testing Gotify configuration."""

    test_message: str = Field(
        default="Test notification from Infrastructor configuration monitoring", max_length=1000
    )
    test_priority: int = Field(default=1, ge=0, le=10)


# Configuration Alert Schemas
class ConfigurationChangeAlert(NotificationBase):
    """Schema for configuration change alert events."""

    event_id: str = Field(..., min_length=1, max_length=255)
    device_id: UUID
    device_name: str
    configuration_path: str
    change_type: str
    risk_level: str

    # Change details
    previous_hash: str | None = Field(None, max_length=64)
    current_hash: str = Field(..., max_length=64)
    diff_summary: str | None = Field(None, max_length=2000)
    affected_services: list[str] = Field(default_factory=list)
    rollback_available: bool = Field(default=False)

    # Context
    triggered_by: str | None = Field(None, max_length=255)
    trigger_source: str = Field(..., max_length=100)
    timestamp: datetime

    # Assessment
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.5)
    severity_factors: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    impact_summary: dict[str, Any] = Field(default_factory=dict)


class ConfigurationAlertCreate(NotificationBase):
    """Schema for creating configuration alerts manually."""

    event_id: str = Field(..., min_length=1, max_length=255)
    device_id: UUID
    configuration_path: str = Field(..., max_length=1000)
    change_type: str = Field(..., max_length=50)
    risk_level: str = Field(..., max_length=20)
    title: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1)
    alert_data: dict[str, Any] = Field(default_factory=dict)
    config_id: UUID


class ConfigurationAlertResponse(NotificationBase):
    """Schema for configuration alert responses."""

    id: UUID
    event_id: str
    device_id: UUID
    configuration_path: str
    change_type: str
    risk_level: str
    title: str
    message: str
    priority: int
    alert_data: dict[str, Any]

    # Gotify delivery tracking
    gotify_message_id: int | None
    status: str
    delivery_attempts: int
    sent_at: datetime | None
    failed_at: datetime | None
    next_retry_at: datetime | None
    error_message: str | None

    # Performance metrics
    processing_time_ms: int | None
    delivery_time_ms: int | None

    # Metadata
    created_at: datetime
    updated_at: datetime


# Alert Suppression Schemas
class AlertSuppressionCreate(NotificationBase):
    """Schema for creating alert suppression rules."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    device_id: UUID | None = None
    configuration_path_pattern: str | None = Field(None, max_length=1000)
    change_type: str | None = Field(None, max_length=50)
    min_risk_level: str | None = Field(None, max_length=20)

    suppression_window_minutes: dict[str, int] = Field(
        default={"low": 60, "medium": 30, "high": 15, "critical": 5, "urgent": 1}
    )
    max_alerts_in_window: dict[str, int] = Field(
        default={"low": 1, "medium": 2, "high": 3, "critical": 5, "urgent": 10}
    )
    active: bool = Field(default=True)


class AlertSuppressionUpdate(NotificationBase):
    """Schema for updating alert suppression rules."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    device_id: UUID | None = None
    configuration_path_pattern: str | None = Field(None, max_length=1000)
    change_type: str | None = Field(None, max_length=50)
    min_risk_level: str | None = Field(None, max_length=20)
    suppression_window_minutes: dict[str, int] | None = None
    max_alerts_in_window: dict[str, int] | None = None
    active: bool | None = None


class AlertSuppressionResponse(NotificationBase):
    """Schema for alert suppression responses."""

    id: UUID
    name: str
    description: str | None
    device_id: UUID | None
    configuration_path_pattern: str | None
    change_type: str | None
    min_risk_level: str | None
    suppression_window_minutes: dict[str, int]
    max_alerts_in_window: dict[str, int]
    active: bool
    last_triggered_at: datetime | None
    trigger_count: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str


# Filter and List Schemas
class AlertFilter(NotificationBase):
    """Schema for filtering configuration alerts."""

    device_ids: list[UUID] | None = None
    risk_levels: list[str] | None = None
    change_types: list[str] | None = None
    statuses: list[str] | None = None
    configuration_paths: list[str] | None = None
    hours_back: int | None = Field(None, ge=1, le=8760)
    include_suppressed: bool = Field(default=False)


class AlertStats(NotificationBase):
    """Schema for alert statistics."""

    total_alerts: int
    alerts_by_status: dict[str, int]
    alerts_by_risk_level: dict[str, int]
    alerts_by_change_type: dict[str, int]
    alerts_by_device: dict[str, int]
    delivery_success_rate: float
    average_delivery_time_ms: float | None
    failed_alerts: int
    suppressed_alerts: int
    hourly_alert_counts: dict[str, int]  # Last 24 hours


class ConfigurationAlertList(NotificationBase):
    """Schema for paginated configuration alert lists."""

    items: list[ConfigurationAlertResponse]
    total: int
    page: int
    limit: int
    pages: int


class GotifyConfigList(NotificationBase):
    """Schema for paginated Gotify configuration lists."""

    items: list[GotifyConfigResponse]
    total: int
    page: int
    limit: int
    pages: int


class AlertSuppressionList(NotificationBase):
    """Schema for paginated alert suppression lists."""

    items: list[AlertSuppressionResponse]
    total: int
    page: int
    limit: int
    pages: int


# API-specific schemas for proper naming
# These provide the exact naming expected by the API endpoints
GotifyNotificationConfigCreate = GotifyConfigCreate
GotifyNotificationConfigUpdate = GotifyConfigUpdate
GotifyNotificationConfigResponse = GotifyConfigResponse
NotificationTestRequest = GotifyConfigTest


class NotificationTestResponse(NotificationBase):
    """Schema for notification test responses."""

    success: bool
    message: str
    tested_at: datetime
