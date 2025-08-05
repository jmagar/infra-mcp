"""
Gotify MCP Tools

Wrapper tools for Gotify notification operations.
Provides a simple interface for sending notifications via HTTP.
"""

import logging
import structlog
import httpx
from datetime import datetime, timezone
from typing import Any

logger = structlog.get_logger(__name__)


async def create_message(
    app_token: str,
    message: str,
    title: str | None = None,
    priority: int | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Send a message to Gotify using the MCP tools.

    Args:
        app_token: Gotify application token
        message: Message content
        title: Optional message title
        priority: Optional priority (0-10)
        extras: Optional extra data

    Returns:
        Gotify response with message ID if successful, None if failed
    """
    try:
        structlog.contextvars.bind_contextvars(
            operation="gotify_send",
            app_token=app_token[:12] + "...",  # Mask token
            message_length=len(message),
            priority=priority,
        )

        logger.info(
            "Sending Gotify notification",
            title=title or "Infrastructor",
            message_preview=message[:100],
        )

        # Get Gotify configuration from environment
        import os

        gotify_url = os.getenv("GOTIFY_URL")
        http_timeout = int(os.getenv("HTTP_TIMEOUT", "30"))

        if not gotify_url:
            logger.error("GOTIFY_URL not configured in environment")
            return None

        # Set correlation ID for request tracing
        import uuid

        correlation_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Prepare the request
        url = f"{gotify_url.rstrip('/')}/message"
        headers = {"Content-Type": "application/json"}

        payload = {
            "message": message,
            "title": title or "Infrastructor",
            "priority": priority or 0,
        }

        if extras:
            payload["extras"] = extras

        # Add app token to URL parameters
        params = {"token": app_token}

        # Send the notification
        async with httpx.AsyncClient(timeout=http_timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                result = response.json()
                logger.info("Gotify notification sent successfully", message_id=result.get("id"))
                return result
            else:
                logger.error(
                    "Failed to send Gotify notification",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return None

    except Exception as e:
        logger.error("Error sending Gotify notification", error=str(e))
        return None


async def test_connection(app_token: str) -> bool:
    """
    Test Gotify connection by sending a test message.

    Args:
        app_token: Gotify application token

    Returns:
        True if test message sent successfully, False otherwise
    """
    result = await create_message(
        app_token=app_token,
        message="Test message from Infrastructor notification service",
        title="Infrastructor Test",
        priority=1,
    )

    return result is not None and "id" in result
