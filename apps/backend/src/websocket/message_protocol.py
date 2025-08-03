"""
WebSocket Message Protocol

Defines standardized message format and types for WebSocket communication
between the server and connected clients.
"""

from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types"""
    DATA = "data"           # Real-time metrics data
    EVENT = "event"         # Notification events  
    SUBSCRIPTION = "subscription"  # Client subscription changes
    HEARTBEAT = "heartbeat" # Connection keepalive
    ERROR = "error"         # Error messages
    AUTH = "auth"           # Authentication messages


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure"""
    type: MessageType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataMessage(WebSocketMessage):
    """Real-time data streaming message"""
    type: MessageType = MessageType.DATA
    device_id: str
    metric_type: str  # 'system_metrics', 'container_snapshots', 'drive_health'
    
    
class EventMessage(WebSocketMessage):
    """Event notification message"""
    type: MessageType = MessageType.EVENT
    event_type: str
    device_id: Optional[str] = None
    severity: str = "info"  # info, warning, error, critical


class SubscriptionMessage(WebSocketMessage):
    """Client subscription management"""
    type: MessageType = MessageType.SUBSCRIPTION
    action: str  # 'subscribe', 'unsubscribe'
    topics: List[str] = Field(default_factory=list)


class HeartbeatMessage(WebSocketMessage):
    """Connection keepalive message"""
    type: MessageType = MessageType.HEARTBEAT
    client_id: Optional[str] = None


class ErrorMessage(WebSocketMessage):
    """Error notification message"""
    type: MessageType = MessageType.ERROR
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class AuthMessage(WebSocketMessage):
    """Authentication message"""
    type: MessageType = MessageType.AUTH
    token: str
    action: str = "authenticate"  # 'authenticate', 'refresh'


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
    def events(severity: Optional[str] = None) -> str:
        if severity:
            return f"events.{severity}"
        return "events"


def create_data_message(device_id: str, metric_type: str, data: Dict[str, Any]) -> DataMessage:
    """Helper to create data messages"""
    return DataMessage(
        device_id=device_id,
        metric_type=metric_type,
        data=data
    )


def create_event_message(event_type: str, message: str, device_id: Optional[str] = None, 
                        severity: str = "info", **kwargs) -> EventMessage:
    """Helper to create event messages"""
    return EventMessage(
        event_type=event_type,
        device_id=device_id,
        severity=severity,
        data={"message": message, **kwargs}
    )


def create_error_message(error_code: str, message: str, details: Optional[Dict[str, Any]] = None) -> ErrorMessage:
    """Helper to create error messages"""
    return ErrorMessage(
        error_code=error_code,
        message=message,
        details=details
    )