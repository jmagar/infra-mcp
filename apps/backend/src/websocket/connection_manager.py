"""
WebSocket Connection Manager

Manages client connections, subscriptions, and message broadcasting
for real-time infrastructure monitoring.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, UTC
from typing import Any, Optional
from uuid import uuid4

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from apps.backend.src.core.events import (
    BaseEvent,
    ContainerStatusEvent,
    DeviceStatusChangedEvent,
    DriveHealthEvent,
    MetricCollectedEvent,
    get_event_bus,
)

from .message_protocol import (
    DataMessage,
    HeartbeatMessage,
    SubscriptionMessage,
    SubscriptionTopics,
    WebSocketMessage,
    create_error_message,
    MessageType,
)

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Represents a single WebSocket connection with metadata"""

    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.subscriptions: set[str] = set()
        self.authenticated = False
        self.user_id: Optional[str] = None
        self.last_heartbeat = asyncio.get_event_loop().time()
        self.heartbeat_message: Optional[HeartbeatMessage] = None

    async def send_message(self, message: WebSocketMessage) -> None:
        """Send a message to this connection"""
        try:
            # Check if WebSocket is still open before sending
            if self.websocket.client_state != WebSocketState.CONNECTED:
                logger.debug(f"WebSocket {self.client_id} not connected, skipping message")
                return

            # Serialize message with error handling
            try:
                message_json = message.model_dump_json()
            except Exception as e:
                logger.error(f"Failed to serialize message for {self.client_id}: {e}")
                # Send a simple error message instead
                error_json = json.dumps(
                    {
                        "type": "error",
                        "error_code": "SERIALIZATION_ERROR",
                        "message": "Failed to serialize message",
                    }
                )
                await self.websocket.send_text(error_json)
                return

            await self.websocket.send_text(message_json)
        except Exception as e:
            logger.error(f"Failed to send message to {self.client_id}: {e}")
            raise

    async def send_error(
        self, error_code: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        """Send an error message to this connection"""
        error_msg = create_error_message(error_code, message, details)
        await self.send_message(error_msg)

    def update_subscriptions(self, action: str, topics: list[str]) -> None:
        """Update connection subscriptions"""
        if action == "subscribe":
            self.subscriptions.update(topics)
        elif action == "unsubscribe":
            self.subscriptions.difference_update(topics)
        elif action == "replace":
            self.subscriptions = set(topics)

    def matches_topic(self, topic: str) -> bool:
        """Check if connection is subscribed to a topic"""
        # Direct topic match
        if topic in self.subscriptions:
            return True

        # Global subscription
        if SubscriptionTopics.ALL in self.subscriptions:
            return True

        # Pattern matching for hierarchical topics
        for subscription in self.subscriptions:
            if self._topic_matches_pattern(topic, subscription):
                return True

        return False

    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if topic matches subscription pattern"""
        # Support wildcard patterns
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix)

        return topic == pattern


class ConnectionManager:
    """Manages all WebSocket connections and message broadcasting"""

    def __init__(self) -> None:
        self.active_connections: dict[WebSocket, dict[str, Any]] = {}
        self.connection_topics: dict[WebSocket, set[str]] = {}
        self.start_time = datetime.now(UTC)
        self.event_bus = get_event_bus()
        self._event_handlers_registered = False

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)

    def get_connections_by_topic(self, topic: str) -> list[WebSocket]:
        """Get all connections subscribed to a specific topic"""
        return [conn for conn, topics in self.connection_topics.items() if topic in topics]

    def get_topics_for_connection(self, websocket: WebSocket) -> set[str]:
        """Get all topics a connection is subscribed to"""
        return self.connection_topics.get(websocket, set())

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> str:
        """Accept a new WebSocket connection and initialize it"""
        await websocket.accept()
        
        # Generate client ID if not provided
        if client_id is None:
            client_id = f"client_{len(self.active_connections)}_{int(time.time())}"
        
        # Store connection info
        self.active_connections[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.now(UTC),
            "last_ping": datetime.now(UTC)
        }
        self.connection_topics[websocket] = set()
        
        logger.info(f"WebSocket client connected: {client_id}")
        
        # Send welcome message
        welcome_message = DataMessage(
            hostname="system",
            metric_type="connection",
            type=MessageType.DATA,
            data={"status": "connected", "client_id": client_id},
            timestamp=datetime.now(UTC)
        )
        await self.send_personal_message(welcome_message, websocket)

        return client_id

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection and clean up"""
        if websocket in self.active_connections:
            client_info = self.active_connections[websocket]
            client_id = client_info.get("client_id", "unknown")
            
            # Clean up connection data
            del self.active_connections[websocket]
            if websocket in self.connection_topics:
                del self.connection_topics[websocket]
            
            logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_personal_message(self, message: WebSocketMessage, websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)

    async def subscribe_to_topic(self, websocket: WebSocket, topic: str) -> None:
        """Subscribe a connection to a specific topic"""
        if websocket in self.connection_topics:
            self.connection_topics[websocket].add(topic)
            client_id = self.active_connections.get(websocket, {}).get("client_id", "unknown")
            logger.debug(f"Client {client_id} subscribed to topic: {topic}")

    async def unsubscribe_from_topic(self, websocket: WebSocket, topic: str) -> None:
        """Unsubscribe a connection from a specific topic"""
        if websocket in self.connection_topics:
            self.connection_topics[websocket].discard(topic)
            client_id = self.active_connections.get(websocket, {}).get("client_id", "unknown")
            logger.debug(f"Client {client_id} unsubscribed from topic: {topic}")

    async def broadcast_to_topic(self, message: WebSocketMessage, topic: str) -> None:
        """Broadcast a message to all connections subscribed to a topic"""
        connections = self.get_connections_by_topic(topic)
        if connections:
            logger.debug(f"Broadcasting to {len(connections)} connections on topic: {topic}")
            await asyncio.gather(
                *[self.send_personal_message(message, conn) for conn in connections],
                return_exceptions=True
            )

    async def broadcast_to_all(self, message: WebSocketMessage) -> None:
        """Broadcast a message to all active connections"""
        if self.active_connections:
            logger.debug(f"Broadcasting to {len(self.active_connections)} connections")
            await asyncio.gather(
                *[self.send_personal_message(message, conn) for conn in self.active_connections],
                return_exceptions=True
            )

    async def handle_monitoring_event(self, event: BaseEvent) -> None:
        """Handle incoming monitoring events and broadcast to appropriate topics"""
        try:
            # Convert monitoring event to WebSocket message
            message = self._convert_event_to_websocket_message(event)
            if not message:
                return
            
            # Determine topic for routing
            topic = self._get_topic_for_event(event)
            
            # Broadcast to topic subscribers
            await self.broadcast_to_topic(message, topic)
            
        except Exception as e:
            logger.error(f"Error handling monitoring event: {e}")

    def get_connection_stats(self) -> dict[str, Any]:
        """Get statistics about active connections"""
        topic_counts: dict[str, int] = {}
        for topics in self.connection_topics.values():
            for topic in topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        return {
            "total_connections": len(self.active_connections),
            "topic_subscriptions": topic_counts,
            "uptime_seconds": (datetime.now(UTC) - self.start_time).total_seconds()
        }

    async def cleanup_stale_connections(self) -> None:
        """Remove connections that haven't responded to pings"""
        stale_connections = []
        current_time = datetime.now(UTC)
        
        for websocket, info in self.active_connections.items():
            last_ping = info.get("last_ping", current_time)
            if (current_time - last_ping).total_seconds() > 300:  # 5 minutes
                stale_connections.append(websocket)
        
        for websocket in stale_connections:
            await self.disconnect(websocket)

    def _register_event_handlers(self) -> None:
        """Register event handlers with the event bus"""
        if self._event_handlers_registered:
            return

        # Subscribe to all monitoring events
        self.event_bus.subscribe(
            ["metric_collected", "device_status_changed", "container_status", "drive_health"],
            self._handle_monitoring_event,
            priority=10  # High priority for real-time updates
        )

        self._event_handlers_registered = True
        logger.info("WebSocket event handlers registered")

    async def _handle_monitoring_event(self, event: BaseEvent) -> None:
        """Handle monitoring events and broadcast to WebSocket clients"""
        try:
            # Convert event to WebSocket message
            websocket_message = self._convert_event_to_websocket_message(event)

            # Determine topic for broadcasting
            topic = self._get_topic_for_event(event)

            # Broadcast to subscribed clients
            await self.broadcast_to_topic(websocket_message, topic)

        except Exception as e:
            logger.error(f"Error handling monitoring event {event.event_type}: {e}")

    def _convert_event_to_websocket_message(self, event: BaseEvent) -> DataMessage:
        """Convert an event to a WebSocket message"""
        # Prefer human-friendly hostname for routing/identity
        hostname = getattr(event, 'hostname', None) or 'unknown'

        # Determine metric type based on event type
        metric_type = self._get_metric_type_for_event(event)

        # Create data message with event information
        return DataMessage(
            hostname=hostname,
            metric_type=metric_type,
            type=MessageType.DATA,
            data=event.model_dump(),
            timestamp=event.timestamp
        )

    def _get_metric_type_for_event(self, event: BaseEvent) -> str:
        """Determine the metric type for an event"""
        if isinstance(event, MetricCollectedEvent):
            return "system_metrics"
        elif isinstance(event, ContainerStatusEvent):
            return "container_snapshots"
        elif isinstance(event, DriveHealthEvent):
            return "drive_health"
        elif isinstance(event, DeviceStatusChangedEvent):
            return "device_status"
        else:
            return "events"

    def _get_topic_for_event(self, event: BaseEvent) -> str:
        """Determine the WebSocket topic for an event"""
        # Prefer human-friendly hostname for topic formatting
        device_id = getattr(event, 'hostname', None) or 'unknown'
        
        if isinstance(event, MetricCollectedEvent):
            return f"devices.{device_id}.metrics"
        elif isinstance(event, DeviceStatusChangedEvent):
            return f"devices.{device_id}.status"
        elif isinstance(event, ContainerStatusEvent):
            return f"devices.{device_id}.containers"
        elif isinstance(event, DriveHealthEvent):
            return f"devices.{device_id}.drives"
        else:
            return f"devices.{device_id}.events"

    # --- Methods used by server.py ---
    async def authenticate_connection(self, client_id: str, user_id: str) -> None:
        """Record authentication info for a connected client."""
        for ws, info in self.active_connections.items():
            if info.get("client_id") == client_id:
                info["user_id"] = user_id
                info["authenticated"] = True
                return

    async def handle_subscription(self, client_id: str, msg: SubscriptionMessage) -> None:
        """Apply subscription changes for a client."""
        # Find websocket for client_id
        target_ws: WebSocket | None = None
        for ws, info in self.active_connections.items():
            if info.get("client_id") == client_id:
                target_ws = ws
                break
        if target_ws is None:
            return
        # Apply subscription changes
        if msg.action == "subscribe":
            for t in msg.topics:
                await self.subscribe_to_topic(target_ws, t)
        elif msg.action == "unsubscribe":
            for t in msg.topics:
                await self.unsubscribe_from_topic(target_ws, t)
        elif msg.action == "replace":
            self.connection_topics[target_ws] = set(msg.topics)

    async def handle_heartbeat(self, client_id: str) -> None:
        """Update last ping timestamp for a client."""
        for ws, info in self.active_connections.items():
            if info.get("client_id") == client_id:
                info["last_ping"] = datetime.now(UTC)
                return


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    return connection_manager
