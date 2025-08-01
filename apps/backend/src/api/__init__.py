"""
Infrastructure Management API - FastAPI routers and endpoints.

This package contains all REST API endpoints organized by resource type,
providing comprehensive infrastructure monitoring and management capabilities.
"""

from fastapi import APIRouter
from apps.backend.src.api.common import router as common_router
from .devices import router as devices_router
from .containers import router as containers_router
from .proxy import router as proxy_router

# Create main API router (no prefix since it's mounted at /api in main.py)
api_router = APIRouter(tags=["API"])

# Include common endpoints at the API root level
api_router.include_router(common_router, tags=["Common"])

# Include resource-specific routers
api_router.include_router(devices_router, prefix="/devices", tags=["Devices"])
api_router.include_router(containers_router, prefix="/containers", tags=["Containers"])
api_router.include_router(proxy_router, prefix="/proxy", tags=["Proxy"])

__all__ = ["api_router", "common_router", "devices_router", "containers_router", "proxy_router"]
