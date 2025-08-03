"""
WebSocket Connection Manager

Manages client connections, subscriptions, and message broadcasting
for real-time infrastructure monitoring.
"""

import logging
import asyncio
import json
from typing import Dict, Set, List, Optional, Any
from uuid import uuid4
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer

from .message_protocol import (
    WebSocketMessage, MessageType, SubscriptionMessage, HeartbeatMessage,
    ErrorMessage, create_error_message, SubscriptionTopics
)

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Represents a single WebSocket connection with metadata"""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.subscriptions: Set[str] = set()
        self.authenticated = False
        self.user_id: Optional[str] = None
        self.last_heartbeat = asyncio.get_event_loop().time()
        
    async def send_message(self, message: WebSocketMessage):
        """Send a message to this connection"""
        try:
            # Check if WebSocket is still open before sending
            if self.websocket.client_state.name != "CONNECTED":
                logger.debug(f"WebSocket {self.client_id} not connected, skipping message")
                return
                
            await self.websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to send message to {self.client_id}: {e}")
            raise
    
    async def send_error(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Send an error message to this connection"""
        error_msg = create_error_message(error_code, message, details)
        await self.send_message(error_msg)
    
    def update_subscriptions(self, action: str, topics: List[str]):
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
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task: Optional[asyncio.Task] = None
        
    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        client_id = str(uuid4())
        connection = WebSocketConnection(websocket, client_id)
        self.connections[client_id] = connection
        
        logger.info(f"New WebSocket connection: {client_id}")
        
        # Start heartbeat task if this is the first connection
        if len(self.connections) == 1 and not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        return client_id
    
    async def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.connections:
            connection = self.connections.pop(client_id)
            logger.info(f"WebSocket disconnected: {client_id}")
            
            # Stop heartbeat task if no connections remain
            if not self.connections and self.heartbeat_task:
                self.heartbeat_task.cancel()
                self.heartbeat_task = None
    
    async def authenticate_connection(self, client_id: str, user_id: str):
        """Mark a connection as authenticated"""
        if client_id in self.connections:
            self.connections[client_id].authenticated = True
            self.connections[client_id].user_id = user_id
            logger.info(f"WebSocket authenticated: {client_id} for user {user_id}")
    
    async def handle_subscription(self, client_id: str, subscription_msg: SubscriptionMessage):
        """Handle client subscription changes"""
        if client_id not in self.connections:
            return
        
        connection = self.connections[client_id]
        
        # Require authentication for subscriptions
        if not connection.authenticated:
            await connection.send_error("AUTH_REQUIRED", "Authentication required for subscriptions")
            return
        
        connection.update_subscriptions(subscription_msg.action, subscription_msg.topics)
        # Subscription updated
    
    async def handle_heartbeat(self, client_id: str, heartbeat_msg: HeartbeatMessage):
        """Handle client heartbeat"""
        if client_id in self.connections:
            self.connections[client_id].last_heartbeat = asyncio.get_event_loop().time()
    
    async def broadcast_to_topic(self, topic: str, message: WebSocketMessage):
        """Broadcast message to all connections subscribed to a topic"""
        if not self.connections:
            return
        
        # Find matching connections
        target_connections = [
            conn for conn in self.connections.values()
            if conn.authenticated and conn.matches_topic(topic)
        ]
        
        if not target_connections:
            return
        
        # Send to all matching connections
        failed_connections = []
        for connection in target_connections:
            try:
                await connection.send_message(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection.client_id}: {e}")
                failed_connections.append(connection.client_id)
        
        # Clean up failed connections
        for client_id in failed_connections:
            await self.disconnect(client_id)
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all authenticated connections"""
        await self.broadcast_to_topic(SubscriptionTopics.ALL, message)
    
    async def send_to_client(self, client_id: str, message: WebSocketMessage):
        """Send message to specific client"""
        if client_id in self.connections:
            try:
                await self.connections[client_id].send_message(message)
            except Exception as e:
                logger.error(f"Failed to send to {client_id}: {e}")
                await self.disconnect(client_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        total_connections = len(self.connections)
        authenticated_connections = sum(1 for conn in self.connections.values() if conn.authenticated)
        
        # Count subscriptions by topic
        topic_counts = {}
        for connection in self.connections.values():
            for topic in connection.subscriptions:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        return {
            "total_connections": total_connections,
            "authenticated_connections": authenticated_connections,
            "unauthenticated_connections": total_connections - authenticated_connections,
            "topic_subscriptions": topic_counts,
            "heartbeat_interval": self.heartbeat_interval
        }
    
    async def _heartbeat_loop(self):
        """Background task to send heartbeats and check connection health"""
        try:
            while self.connections:
                current_time = asyncio.get_event_loop().time()
                stale_connections = []
                
                # Check for stale connections and send heartbeats
                for client_id, connection in self.connections.items():
                    time_since_heartbeat = current_time - connection.last_heartbeat
                    
                    if time_since_heartbeat > (self.heartbeat_interval * 3):
                        # Connection is stale
                        stale_connections.append(client_id)
                    elif connection.authenticated:
                        # Send heartbeat only to authenticated connections
                        try:
                            heartbeat = HeartbeatMessage(client_id=client_id)
                            await connection.send_message(heartbeat)
                        except Exception:
                            stale_connections.append(client_id)
                
                # Clean up stale connections
                for client_id in stale_connections:
                    await self.disconnect(client_id)
                
                await asyncio.sleep(self.heartbeat_interval)
                
        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    return connection_manager