"""
WebSocket Server

Main WebSocket server implementation for real-time infrastructure monitoring.
Provides WebSocket endpoints for client connections and message handling.
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from .auth import WebSocketAuthenticator, get_websocket_authenticator
from .connection_manager import ConnectionManager, get_connection_manager
from .message_protocol import (
    HeartbeatMessage,
    MessageType,
    SubscriptionMessage,
    create_error_message,
    DataMessage,
)

logger = logging.getLogger(__name__)

# Create WebSocket router
websocket_router = APIRouter(prefix="/ws", tags=["websocket"])


@websocket_router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    authenticator: WebSocketAuthenticator = Depends(get_websocket_authenticator),
) -> None:
    """
    Main WebSocket endpoint for real-time infrastructure monitoring

    Protocol:
    1. Client connects
    2. Client sends auth message with Bearer token
    3. Server authenticates and responds
    4. Client can subscribe to topics
    5. Server streams real-time data
    """
    client_id = await connection_manager.connect(websocket)

    try:
        # Wait for authentication
        auth_timeout = 30  # seconds

        try:
            # Wait for authentication message
            auth_data = await asyncio.wait_for(websocket.receive_text(), timeout=auth_timeout)
            auth_message = json.loads(auth_data)

            # Validate auth message format
            if auth_message.get("type") != MessageType.AUTH:
                await connection_manager.send_personal_message(
                    create_error_message(
                        "AUTH_REQUIRED", "Authentication required as first message"
                    ),
                    websocket,
                )
                return

            # Authenticate token
            token = auth_message.get("token", "")
            user_id = await authenticator.authenticate_token(token)

            if user_id:
                # Note: authenticate_connection method needs to be implemented in ConnectionManager
                if hasattr(connection_manager, 'authenticate_connection'):
                    await connection_manager.authenticate_connection(client_id, user_id)

                # Send auth success
                await connection_manager.send_personal_message(
                    DataMessage(
                        hostname="system",
                        metric_type="auth",
                        type=MessageType.DATA,
                        data={
                            "status": "authenticated",
                            "client_id": client_id,
                            "user_id": user_id,
                        },
                        timestamp=datetime.now(UTC),
                    ),
                    websocket,
                )

                logger.info(f"WebSocket client {client_id} authenticated as {user_id}")
            else:
                await connection_manager.send_personal_message(
                    create_error_message("AUTH_FAILED", "Invalid authentication token"),
                    websocket,
                )
                return

        except TimeoutError:
            await connection_manager.send_personal_message(
                create_error_message(
                    "AUTH_TIMEOUT",
                    f"Authentication timeout: No authentication message received within {auth_timeout} seconds. Please send an auth message immediately after connecting.",
                ),
                websocket,
            )
            return
        except json.JSONDecodeError:
            await connection_manager.send_personal_message(
                create_error_message("INVALID_MESSAGE", "Invalid JSON message"),
                websocket,
            )
            return

        # Main message loop for authenticated connection
        while True:
            try:
                # Receive message from client
                raw_message = await websocket.receive_text()
                message_data = json.loads(raw_message)

                # Handle different message types
                message_type = message_data.get("type")

                if message_type == MessageType.SUBSCRIPTION:
                    subscription_msg = SubscriptionMessage(**message_data)
                    # Note: handle_subscription method needs to be implemented in ConnectionManager
                    if hasattr(connection_manager, 'handle_subscription'):
                        await connection_manager.handle_subscription(client_id, subscription_msg)

                elif message_type == MessageType.HEARTBEAT:
                    # Validate heartbeat message format
                    HeartbeatMessage(**message_data)
                    # Note: handle_heartbeat method needs to be implemented in ConnectionManager
                    if hasattr(connection_manager, 'handle_heartbeat'):
                        await connection_manager.handle_heartbeat(client_id)

                else:
                    logger.warning(f"Unknown message type from {client_id}: {message_type}")
                    await connection_manager.send_personal_message(
                        create_error_message(
                            "UNKNOWN_MESSAGE_TYPE", f"Unknown message type: {message_type}"
                        ),
                        websocket,
                    )

            except json.JSONDecodeError:
                await connection_manager.send_personal_message(
                    create_error_message("INVALID_JSON", "Invalid JSON message"),
                    websocket,
                )
            except WebSocketDisconnect:
                # Client disconnected normally, exit loop
                break
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                await connection_manager.send_personal_message(
                    create_error_message("MESSAGE_ERROR", str(e)),
                    websocket,
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        await connection_manager.disconnect(websocket)


@websocket_router.get("/status")
async def websocket_status(connection_manager: ConnectionManager = Depends(get_connection_manager)) -> dict[str, Any]:
    """Get WebSocket server status and connection statistics"""
    stats = connection_manager.get_connection_stats()

    return {
        "websocket_server": "running",
        "connections": stats,
        "endpoints": {"stream": "/ws/stream", "status": "/ws/status"},
        "supported_message_types": [
            MessageType.AUTH,
            MessageType.SUBSCRIPTION,
            MessageType.HEARTBEAT,
            MessageType.DATA,
            MessageType.EVENT,
            MessageType.ERROR,
        ],
    }


# Health check endpoint
@websocket_router.get("/health")
async def websocket_health() -> dict[str, str]:
    """WebSocket server health check"""
    return {"status": "healthy", "service": "websocket_server"}

