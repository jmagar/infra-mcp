"""
WebSocket Message Protocol

Defines standardized message format and types for WebSocket communication
between the server and connected clients.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, AliasChoices


class MessageType(str, Enum):
    """WebSocket message types"""

    DATA = "data"  # Real-time metrics data
    EVENT = "event"  # Notification events
    SUBSCRIPTION = "subscription"  # Client subscription changes
    HEARTBEAT = "heartbeat"  # Connection keepalive
    ERROR = "error"  # Error messages
    AUTH = "auth"  # Authentication messages


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure"""

    type: MessageType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))
    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DataMessage(WebSocketMessage):
    """Real-time data streaming message"""

    type: MessageType = MessageType.DATA
    hostname: str = Field(validation_alias=AliasChoices("hostname", "device_id", "device"))
    metric_type: str  # 'system_metrics', 'container_snapshots', 'drive_health'

    # Coerce hostname to string to handle UUID and other types gracefully
    @field_validator("hostname", mode="before")
    @classmethod
    def _coerce_hostname(cls, v: Any) -> str:
        return str(v) if v is not None else "unknown"


class EventMessage(WebSocketMessage):
    """Event notification message"""

    type: MessageType = MessageType.EVENT
    event_type: str
    hostname: str | None = Field(default=None, validation_alias=AliasChoices("hostname", "device_id", "device"))
    severity: str = "info"  # info, warning, error, critical


class SubscriptionMessage(WebSocketMessage):
    """Client subscription management"""

    type: MessageType = MessageType.SUBSCRIPTION
    action: str  # 'subscribe', 'unsubscribe'
    topics: list[str] = Field(default_factory=list)


class HeartbeatMessage(WebSocketMessage):
    """Connection keepalive message"""

    type: MessageType = MessageType.HEARTBEAT
    client_id: str | None = None


class ErrorMessage(WebSocketMessage):
    """Error notification message"""

    type: MessageType = MessageType.ERROR
    error_code: str
    message: str
    details: dict[str, Any] | None = None


class AuthMessage(WebSocketMessage):
    """Authentication message"""

    type: MessageType = MessageType.AUTH
    token: str
    action: str = "authenticate"  # 'authenticate', 'refresh'


def create_error_message(error_code: str, message: str, details: dict[str, Any] | None = None) -> ErrorMessage:
    """Helper to create error messages"""
    return ErrorMessage(error_code=error_code, message=message, details=details)


# Subscription topic patterns
class SubscriptionTopics:
    """Predefined subscription topic patterns"""

    # Global topics
    ALL = "global"

    # Device-specific topics
    @staticmethod
    def device(device_id: str) -> str:
        return f"devices.{device_id}"

    @staticmethod
    def device_metrics(device_id: str) -> str:
        return f"devices.{device_id}.metrics"

    @staticmethod
    def device_containers(device_id: str) -> str:
        return f"devices.{device_id}.containers"

    @staticmethod
    def device_health(device_id: str) -> str:
        return f"devices.{device_id}.health"

    # Category-based topics
    @staticmethod
    def metric_type(metric_type: str) -> str:
        return f"metrics.{metric_type}"

    # Event topics
    @staticmethod
    def events(severity: str | None = None) -> str:
        if severity:
            return f"events.{severity}"
        return "events"


def create_data_message(
    hostname: str | None = None,
    metric_type: str = "",
    data: dict[str, Any] | None = None,
    *,
    device_id: str | None = None,
    device: str | None = None,
) -> DataMessage:
    """Helper to create data messages.

    Prefer hostname. For backward compatibility, supports legacy parameter names
    via keyword-only args device_id/device.
    """
    resolved_host = hostname or device or device_id or "unknown"
    return DataMessage(hostname=resolved_host, metric_type=metric_type, data=data or {})


def create_event_message(
    event_type: str, message: str, hostname: str | None = None, severity: str = "info", **kwargs: Any
) -> EventMessage:
    """Helper to create event messages"""
    return EventMessage(
        event_type=event_type,
        hostname=hostname,
        severity=severity,
        data={"message": message, **kwargs},
    )


 
