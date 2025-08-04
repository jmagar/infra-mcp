"""
Configuration Management API Endpoints

REST API endpoints for managing infrastructure configuration snapshots,
change events, and configuration analysis.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_db_session
from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.schemas.configuration import (
    ConfigurationSnapshotCreate,
    ConfigurationSnapshotResponse,
    ConfigurationSnapshotList,
    ConfigurationChangeEventCreate,
    ConfigurationChangeEventResponse,
    ConfigurationChangeEventList,
    ConfigurationFilter,
    ConfigurationMetrics,
    ConfigurationAlert,
    ConfigurationRollbackRequest,
    ConfigurationRollbackResponse,
    ConfigurationDiff,
)
from apps.backend.src.schemas.common import PaginationParams, APIResponse
from apps.backend.src.services.configuration_service import ConfigurationService
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def get_configuration_service(db: AsyncSession = Depends(get_db_session)) -> ConfigurationService:
    """Dependency to get configuration service instance."""
    return ConfigurationService(db)


# Configuration Snapshots
@router.post("/snapshots", response_model=APIResponse[ConfigurationSnapshotResponse], status_code=201)
async def create_configuration_snapshot(
    snapshot_data: ConfigurationSnapshotCreate,
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Create a new configuration snapshot."""
    try:
        snapshot = await service.create_snapshot(snapshot_data)
        return APIResponse(
            success=True,
            data=snapshot,
            message="Configuration snapshot created successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots", response_model=APIResponse[ConfigurationSnapshotList])
async def list_configuration_snapshots(
    pagination: PaginationParams = Depends(),
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"),
    config_types: Optional[str] = Query(None, description="Comma-separated config types"),
    change_types: Optional[str] = Query(None, description="Comma-separated change types"),
    risk_levels: Optional[str] = Query(None, description="Comma-separated risk levels"),
    high_risk_only: Optional[bool] = Query(None, description="Show only HIGH/CRITICAL risk changes"),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """List configuration snapshots with filtering and pagination."""
    try:
        config_filter = ConfigurationFilter(
            device_ids=[UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None,
            config_types=config_types.split(",") if config_types else None,
            change_types=change_types.split(",") if change_types else None,
            risk_levels=risk_levels.split(",") if risk_levels else None,
            high_risk_only=high_risk_only,
        )
        
        snapshot_list = await service.list_snapshots(pagination, config_filter)
        return APIResponse(
            success=True,
            data=snapshot_list,
            message="Configuration snapshots retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing configuration snapshots: {e}")
        raise HTTPException(status_code=500, detail="Failed to list configuration snapshots")


@router.get("/snapshots/{snapshot_id}", response_model=APIResponse[ConfigurationSnapshotResponse])
async def get_configuration_snapshot(
    snapshot_id: UUID = Path(..., description="Configuration snapshot UUID"),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Get a specific configuration snapshot."""
    try:
        snapshot = await service.get_snapshot(snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Configuration snapshot not found")
        return APIResponse(
            success=True,
            data=snapshot,
            message="Configuration snapshot created successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting configuration snapshot {snapshot_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration snapshot")


# Configuration Change Events
@router.post("/events", response_model=APIResponse[ConfigurationChangeEventResponse], status_code=201)
async def create_configuration_change_event(
    event_data: ConfigurationChangeEventCreate,
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Create a new configuration change event."""
    try:
        event = await service.create_change_event(event_data)
        return APIResponse(
            success=True,
            data=event,
            message="Configuration change event retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events", response_model=APIResponse[ConfigurationChangeEventList])
async def list_configuration_change_events(
    pagination: PaginationParams = Depends(),
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"),
    config_types: Optional[str] = Query(None, description="Comma-separated config types"),
    unprocessed_only: Optional[bool] = Query(None, description="Show only unprocessed events"),
    high_risk_only: Optional[bool] = Query(None, description="Show only HIGH/CRITICAL risk events"),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """List configuration change events with filtering and pagination."""
    try:
        config_filter = ConfigurationFilter(
            device_ids=[UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None,
            config_types=config_types.split(",") if config_types else None,
            unprocessed_only=unprocessed_only,
            high_risk_only=high_risk_only,
        )
        
        event_list = await service.list_change_events(pagination, config_filter)
        return APIResponse(
            success=True,
            data=event_list,
            message="Configuration change events retrieved successfully",  
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing configuration change events: {e}")
        raise HTTPException(status_code=500, detail="Failed to list configuration change events")


@router.get("/events/{event_id}", response_model=APIResponse[ConfigurationChangeEventResponse])
async def get_configuration_change_event(
    event_id: UUID = Path(..., description="Configuration change event UUID"),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Get a specific configuration change event."""
    try:
        event = await service.get_change_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Configuration change event not found")
        return APIResponse(
            success=True,
            data=event,
            message="Configuration change event retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting configuration change event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration change event")


@router.patch("/events/{event_id}/process")
async def process_configuration_change_event(
    event_id: UUID = Path(..., description="Configuration change event UUID"),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Mark a configuration change event as processed."""
    try:
        success = await service.process_change_event(event_id)
        if not success:
            raise HTTPException(status_code=404, detail="Configuration change event not found")
        return {"status": "processed", "event_id": str(event_id)}
    except Exception as e:
        logger.error(f"Error processing configuration change event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process configuration change event")


# Configuration Metrics and Analysis
@router.get("/metrics", response_model=APIResponse[ConfigurationMetrics])
async def get_configuration_metrics(
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"),
    hours: int = Query(24, description="Number of hours to analyze", ge=1, le=720),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Get aggregated configuration management metrics."""
    try:
        device_id_list = [UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None
        metrics = await service.get_configuration_metrics(device_ids=device_id_list, hours=hours)
        return APIResponse(
            success=True,
            data=metrics,
            message="Configuration metrics retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting configuration metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration metrics")


@router.get("/alerts", response_model=APIResponse[list[ConfigurationAlert]])
async def get_configuration_alerts(
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"), 
    hours: int = Query(24, description="Number of hours to look back", ge=1, le=168),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Get configuration change alerts."""
    try:
        device_id_list = [UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None
        alerts = await service.get_configuration_alerts(device_ids=device_id_list, hours=hours)
        return APIResponse(
            success=True,
            data=alerts,
            message="Configuration alerts retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting configuration alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration alerts")


# Configuration Rollback
@router.post("/rollback", response_model=APIResponse[ConfigurationRollbackResponse])
async def rollback_configuration(
    rollback_request: ConfigurationRollbackRequest,
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Rollback a configuration to a previous snapshot."""
    try:
        rollback_result = await service.rollback_configuration(rollback_request)
        return APIResponse(
            success=True,
            data=rollback_result,
            message="Configuration rollback completed successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rolling back configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to rollback configuration")


# Configuration Diff
@router.get("/diff/{from_snapshot_id}/{to_snapshot_id}", response_model=APIResponse[ConfigurationDiff])
async def get_configuration_diff(
    from_snapshot_id: UUID = Path(..., description="Source snapshot UUID"),
    to_snapshot_id: UUID = Path(..., description="Target snapshot UUID"),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Get the difference between two configuration snapshots."""
    try:
        diff = await service.get_configuration_diff(from_snapshot_id, to_snapshot_id)
        return APIResponse(
            success=True,
            data=diff,
            message="Configuration diff retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting configuration diff: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration diff")


# Device-specific endpoints
@router.get("/devices/{device_id}/snapshots", response_model=APIResponse[ConfigurationSnapshotList])
async def get_device_configuration_snapshots(
    device_id: UUID = Path(..., description="Device UUID"),
    pagination: PaginationParams = Depends(),
    config_types: Optional[str] = Query(None, description="Comma-separated config types"),
    hours: int = Query(168, description="Number of hours to look back", ge=1, le=8760),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Get configuration snapshots for a specific device."""
    try:
        config_filter = ConfigurationFilter(
            device_ids=[device_id],
            config_types=config_types.split(",") if config_types else None,
        )
        
        snapshot_list = await service.list_snapshots(pagination, config_filter, hours=hours)
        return APIResponse(
            success=True,
            data=snapshot_list,
            message="Configuration snapshots retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting device configuration snapshots: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device configuration snapshots")


@router.get("/devices/{device_id}/events", response_model=APIResponse[ConfigurationChangeEventList])
async def get_device_configuration_events(
    device_id: UUID = Path(..., description="Device UUID"),
    pagination: PaginationParams = Depends(),
    unprocessed_only: Optional[bool] = Query(None, description="Show only unprocessed events"),
    hours: int = Query(168, description="Number of hours to look back", ge=1, le=8760),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """Get configuration change events for a specific device."""
    try:
        config_filter = ConfigurationFilter(
            device_ids=[device_id],
            unprocessed_only=unprocessed_only,
        )
        
        event_list = await service.list_change_events(pagination, config_filter, hours=hours)
        return APIResponse(
            success=True,
            data=event_list,
            message="Configuration change events retrieved successfully",  
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting device configuration events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device configuration events")