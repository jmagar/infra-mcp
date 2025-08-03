"""
WebSocket Server

Main WebSocket server implementation for real-time infrastructure monitoring.
Provides WebSocket endpoints for client connections and message handling.
"""

import asyncio
import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from .connection_manager import get_connection_manager, ConnectionManager
from .message_protocol import (
    MessageType,
    SubscriptionMessage,
    HeartbeatMessage,
)
from .auth import get_websocket_authenticator, WebSocketAuthenticator

logger = logging.getLogger(__name__)

# Create WebSocket router
websocket_router = APIRouter(prefix="/ws", tags=["websocket"])


@websocket_router.websocket("/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    authenticator: WebSocketAuthenticator = Depends(get_websocket_authenticator),
):
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
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": MessageType.ERROR,
                            "error_code": "AUTH_REQUIRED",
                            "message": "Authentication required as first message",
                        }
                    )
                )
                return

            # Authenticate token
            token = auth_message.get("token", "")
            user_id = await authenticator.authenticate_token(token)

            if user_id:
                await connection_manager.authenticate_connection(client_id, user_id)

                # Send auth success
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": MessageType.AUTH,
                            "action": "authenticated",
                            "client_id": client_id,
                            "user_id": user_id,
                        }
                    )
                )

                logger.info(f"WebSocket client {client_id} authenticated as {user_id}")
            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": MessageType.ERROR,
                            "error_code": "AUTH_FAILED",
                            "message": "Invalid authentication token",
                        }
                    )
                )
                return

        except TimeoutError:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": MessageType.ERROR,
                        "error_code": "AUTH_TIMEOUT",
                        "message": f"Authentication timeout - no auth message received within {auth_timeout} seconds",
                    }
                )
            )
            return
        except json.JSONDecodeError:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": MessageType.ERROR,
                        "error_code": "INVALID_MESSAGE",
                        "message": "Invalid JSON message",
                    }
                )
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
                    await connection_manager.handle_subscription(client_id, subscription_msg)

                    # Send subscription confirmation
                    try:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": MessageType.SUBSCRIPTION,
                                    "action": "confirmed",
                                    "topics": subscription_msg.topics,
                                }
                            )
                        )
                    except Exception as e:
                        logger.debug(
                            f"Failed to send subscription confirmation to {client_id}: {e}"
                        )
                        break

                elif message_type == MessageType.HEARTBEAT:
                    heartbeat_msg = HeartbeatMessage(**message_data)
                    await connection_manager.handle_heartbeat(client_id)

                    # Echo heartbeat back
                    try:
                        await websocket.send_text(
                            json.dumps({"type": MessageType.HEARTBEAT, "client_id": client_id})
                        )
                    except Exception as e:
                        logger.debug(f"Failed to send heartbeat to {client_id}: {e}")
                        break

                else:
                    logger.warning(f"Unknown message type from {client_id}: {message_type}")
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": MessageType.ERROR,
                                "error_code": "UNKNOWN_MESSAGE_TYPE",
                                "message": f"Unknown message type: {message_type}",
                            }
                        )
                    )

            except json.JSONDecodeError:
                try:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": MessageType.ERROR,
                                "error_code": "INVALID_JSON",
                                "message": "Invalid JSON message",
                            }
                        )
                    )
                except Exception:
                    break  # Connection closed, exit loop
            except WebSocketDisconnect:
                # Client disconnected normally, exit loop
                break
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                try:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": MessageType.ERROR,
                                "error_code": "MESSAGE_ERROR",
                                "message": str(e),
                            }
                        )
                    )
                except Exception:
                    break  # Connection closed, exit loop

    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        await connection_manager.disconnect(client_id)


@websocket_router.get("/status")
async def websocket_status(connection_manager: ConnectionManager = Depends(get_connection_manager)):
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
async def websocket_health():
    """WebSocket server health check"""
    return {"status": "healthy", "service": "websocket_server"}

