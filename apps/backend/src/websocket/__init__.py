"""
WebSocket module for real-time infrastructure monitoring.

Provides WebSocket server implementation with connection management,
message protocol, and authentication for streaming live infrastructure data.
"""

from .connection_manager import ConnectionManager
from .message_protocol import MessageType, WebSocketMessage
from .server import websocket_router

__all__ = ["websocket_router", "ConnectionManager", "MessageType", "WebSocketMessage"]
