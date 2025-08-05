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
from .zfs import router as zfs_router
from .compose_deployment import router as compose_deployment_router
from .vms import router as vms_router

# Phase 1 - Database-first architecture endpoints
from .audit import router as audit_router
from .configuration import router as configuration_router
from .rollback import router as rollback_router
from .performance import router as performance_router
from .cache import router as cache_router
from .approval_workflow import router as approval_workflow_router
from .configuration_template import router as configuration_template_router
from .notifications import router as notifications_router
from .configuration_batch import router as configuration_batch_router
from .configuration_timeline import router as configuration_timeline_router
from .compliance import router as compliance_router
from .export_import import router as export_import_router

# Create main API router (no prefix since it's mounted at /api in main.py)
api_router = APIRouter(tags=["API"])

# Include common endpoints at the API root level
api_router.include_router(common_router, tags=["Common"])

# Include resource-specific routers
# Note: Using plural resource names (/devices, /containers, /proxies) for REST API consistency
api_router.include_router(devices_router, prefix="/devices", tags=["Devices"])
api_router.include_router(containers_router, prefix="/containers", tags=["Containers"])
api_router.include_router(proxy_router, prefix="/proxies", tags=["Proxy"])
api_router.include_router(zfs_router, prefix="/zfs", tags=["ZFS"])
api_router.include_router(compose_deployment_router, prefix="/compose", tags=["Compose Deployment"])
api_router.include_router(vms_router, prefix="/vms", tags=["VMs"])

# Phase 1 - Database-first architecture endpoints
api_router.include_router(audit_router, prefix="/audit", tags=["Data Collection Audit"])
api_router.include_router(
    configuration_router, prefix="/configuration", tags=["Configuration Management"]
)
api_router.include_router(rollback_router, prefix="/rollback", tags=["Configuration Rollback"])
api_router.include_router(performance_router, prefix="/performance", tags=["Service Performance"])
api_router.include_router(cache_router, prefix="/cache", tags=["Cache Management"])
api_router.include_router(
    approval_workflow_router, prefix="/approval-workflow", tags=["Approval Workflow"]
)
api_router.include_router(
    configuration_template_router, prefix="/templates", tags=["Configuration Templates"]
)
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(
    configuration_batch_router, prefix="/configuration-batch", tags=["Configuration Batch"]
)
api_router.include_router(
    configuration_timeline_router, prefix="/configuration-timeline", tags=["Configuration Timeline"]
)
api_router.include_router(
    compliance_router, prefix="/compliance", tags=["Configuration Compliance"]
)
api_router.include_router(
    export_import_router, prefix="/export-import", tags=["Configuration Export/Import"]
)

__all__ = [
    "api_router",
    "common_router",
    "devices_router",
    "containers_router",
    "proxy_router",
    "zfs_router",
    "compose_deployment_router",
    "vms_router",
    # Phase 1 routers
    "audit_router",
    "configuration_router",
    "rollback_router",
    "performance_router",
    "cache_router",
    "approval_workflow_router",
    "configuration_template_router",
    "notifications_router",
    "configuration_batch_router",
    "configuration_timeline_router",
    "compliance_router",
    "export_import_router",
]
