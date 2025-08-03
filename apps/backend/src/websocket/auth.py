"""
WebSocket Authentication

Handles authentication for WebSocket connections using Bearer tokens
consistent with the REST API authentication system.
"""

import logging
from typing import Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from apps.backend.src.core.config import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


class WebSocketAuthenticator:
    """Handles WebSocket authentication using Bearer tokens"""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def authenticate_token(self, token: str) -> Optional[str]:
        """
        Authenticate a Bearer token and return user ID if valid
        
        For now, this uses a simple API key check.
        In production, this would validate JWT tokens.
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Simple API key validation (matches REST API auth)
            if token == self.settings.auth.api_key:
                return "system"  # Return a user ID
            
            # TODO: Add JWT token validation here
            # jwt_payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
            # return jwt_payload.get("sub")
            
            return None
            
        except Exception as e:
            logger.warning(f"Token authentication failed: {e}")
            return None
    
    async def authenticate_websocket_message(self, token: str) -> Optional[str]:
        """Authenticate token from WebSocket auth message"""
        return await self.authenticate_token(token)


def get_websocket_authenticator() -> WebSocketAuthenticator:
    """Get WebSocket authenticator instance"""
    return WebSocketAuthenticator()


async def verify_websocket_token(token: str) -> str:
    """
    Verify WebSocket token and return user ID
    Raises HTTPException if invalid
    """
    authenticator = get_websocket_authenticator()
    user_id = await authenticator.authenticate_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id