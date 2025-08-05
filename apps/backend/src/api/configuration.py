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
from apps.backend.src.services.rollback_service import RollbackService
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def get_configuration_service(db: AsyncSession = Depends(get_db_session)) -> ConfigurationService:
    """Dependency to get configuration service instance."""
    return ConfigurationService(db)


async def get_rollback_service_dependency() -> RollbackService:
    """Dependency to get rollback service instance."""
    from apps.backend.src.services.rollback_service import get_rollback_service

    return await get_rollback_service()


# Root endpoint - List recent configuration snapshots
@router.get("", response_model=APIResponse[ConfigurationSnapshotList])
async def list_configuration_snapshots(
    pagination: PaginationParams = Depends(),
    device_ids: Optional[str] = Query(None, description="Comma-separated device IDs"),
    config_types: Optional[str] = Query(None, description="Comma-separated configuration types"),
    service: ConfigurationService = Depends(get_configuration_service),
    current_user=Depends(get_current_user),
):
    """List configuration snapshots with filtering and pagination."""
    try:
        config_filter = ConfigurationFilter(
            device_ids=[UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None,
            config_types=config_types.split(",") if config_types else None,
        )

        snapshot_list = await service.list_configuration_snapshots(pagination, config_filter)
        return APIResponse(
            success=True,
            data=snapshot_list,
            message="Configuration snapshots retrieved successfully",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing configuration snapshots: {e}")
        raise HTTPException(status_code=500, detail="Failed to list configuration snapshots")


# Configuration Snapshots
@router.post(
    "/snapshots", response_model=APIResponse[ConfigurationSnapshotResponse], status_code=201
)
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
            errors=None,
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
    high_risk_only: Optional[bool] = Query(
        None, description="Show only HIGH/CRITICAL risk changes"
    ),
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
            errors=None,
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
            errors=None,
        )
    except Exception as e:
        logger.error(f"Error getting configuration snapshot {snapshot_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration snapshot")


# Configuration Change Events
@router.post(
    "/events", response_model=APIResponse[ConfigurationChangeEventResponse], status_code=201
)
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
            errors=None,
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
            errors=None,
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
            errors=None,
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
            errors=None,
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
            errors=None,
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
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rolling back configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to rollback configuration")


# Configuration Diff
@router.get(
    "/diff/{from_snapshot_id}/{to_snapshot_id}", response_model=APIResponse[ConfigurationDiff]
)
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
            errors=None,
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
            errors=None,
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
            errors=None,
        )
    except Exception as e:
        logger.error(f"Error getting device configuration events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device configuration events")


# Configuration Restoration
@router.post("/snapshots/{snapshot_id}/restore", response_model=APIResponse[dict])
async def restore_configuration_snapshot(
    snapshot_id: UUID = Path(..., description="Configuration snapshot UUID to restore"),
    device_id: UUID = Query(..., description="Device UUID for validation"),
    current_user=Depends(get_current_user),
):
    """
    Restore a configuration on a device from a specific snapshot.

    This endpoint writes the raw content from the specified snapshot
    back to the original file path on the remote device.
    """
    try:
        from apps.backend.src.services.configuration_service import restore_configuration_snapshot

        result = await restore_configuration_snapshot(snapshot_id, device_id)

        if not result["success"]:
            raise HTTPException(
                status_code=500, detail=result.get("message", "Configuration restoration failed")
            )

        return APIResponse(
            success=True, data=result, message="Configuration restored successfully", errors=None
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to restore configuration")


# Configuration Drift Detection
@router.post("/devices/{device_id}/drift-check", response_model=APIResponse[dict])
async def detect_device_configuration_drift(
    device_id: UUID = Path(..., description="Device UUID to check for drift"),
    file_paths: list[str] | None = Query(None, description="Specific file paths to check"),
    current_user=Depends(get_current_user),
):
    """
    Detect configuration drift for a device by comparing file hashes.

    Compares current file content on the device against the latest snapshots
    in the database to detect any configuration drift.
    """
    try:
        from apps.backend.src.services.configuration_service import detect_configuration_drift

        result = await detect_configuration_drift(device_id, file_paths)

        return APIResponse(
            success=True,
            data=result,
            message=f"Drift detection completed for device {device_id}",
            errors=None,
        )

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to detect configuration drift")


@router.post("/devices/{device_id}/reconcile-drift", response_model=APIResponse[dict])
async def reconcile_device_configuration_drift(
    device_id: UUID = Path(..., description="Device UUID"),
    file_path: str = Query(..., description="File path to reconcile"),
    reconciliation_mode: str = Query(
        "restore_latest", description="Reconciliation mode: restore_latest or create_snapshot"
    ),
    current_user=Depends(get_current_user),
):
    """
    Reconcile configuration drift for a specific file on a device.

    Two reconciliation modes:
    - restore_latest: Restore the latest known good configuration
    - create_snapshot: Accept the drift and create a new snapshot
    """
    try:
        from apps.backend.src.services.configuration_service import reconcile_configuration_drift

        if reconciliation_mode not in ["restore_latest", "create_snapshot"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid reconciliation mode. Use 'restore_latest' or 'create_snapshot'",
            )

        result = await reconcile_configuration_drift(device_id, file_path, reconciliation_mode)

        if not result["success"]:
            raise HTTPException(
                status_code=500, detail=result.get("message", "Configuration reconciliation failed")
            )

        return APIResponse(
            success=True,
            data=result,
            message="Configuration drift reconciled successfully",
            errors=None,
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to reconcile configuration drift")


# Configuration Sync Status Tracking (Task 38)
@router.get("/sync-status", response_model=APIResponse[dict])
async def get_configuration_sync_status(
    device_ids: str | None = Query(None, description="Comma-separated device UUIDs"),
    hours: int = Query(24, description="Number of hours to look back", ge=1, le=168),
    current_user=Depends(get_current_user),
):
    """
    Get configuration sync status across devices.

    Returns statistics on sync health, validation status, and error counts.
    """
    try:
        from apps.backend.src.services.configuration_service import get_configuration_service

        configuration_service = await get_configuration_service()
        device_id_list = [UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None

        # Get snapshots with errors
        error_snapshots = []
        if device_id_list:
            for device_id in device_id_list:
                device_errors = await configuration_service.get_snapshots_with_sync_errors(
                    device_id, hours
                )
                error_snapshots.extend(device_errors)
        else:
            error_snapshots = await configuration_service.get_snapshots_with_sync_errors(
                None, hours
            )

        # Calculate status statistics
        total_errors = len(error_snapshots)
        sync_errors = len([s for s in error_snapshots if s.sync_status == "error"])
        validation_errors = len([s for s in error_snapshots if s.validation_status == "error"])

        status_summary = {
            "period_hours": hours,
            "total_error_snapshots": total_errors,
            "sync_errors": sync_errors,
            "validation_errors": validation_errors,
            "devices_with_errors": len(set(s.device_id for s in error_snapshots)),
            "error_snapshots": [
                {
                    "snapshot_id": str(s.id),
                    "device_id": str(s.device_id),
                    "file_path": s.file_path,
                    "config_type": s.config_type,
                    "sync_status": s.sync_status,
                    "validation_status": s.validation_status,
                    "last_sync_error": s.last_sync_error,
                    "last_validation_output": s.last_validation_output,
                    "time": s.time.isoformat(),
                }
                for s in error_snapshots[:50]  # Limit to first 50 for API response size
            ],
        }

        return APIResponse(
            success=True,
            data=status_summary,
            message="Configuration sync status retrieved successfully",
            errors=None,
        )

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get configuration sync status")


@router.post("/snapshots/{snapshot_id}/retry-validation", response_model=APIResponse[dict])
async def retry_snapshot_validation(
    snapshot_id: UUID = Path(..., description="Configuration snapshot UUID"),
    current_user=Depends(get_current_user),
):
    """
    Retry validation for a specific configuration snapshot.

    Useful for re-running validation after fixing validation tools or infrastructure issues.
    """
    try:
        from apps.backend.src.services.configuration_service import get_configuration_service
        from apps.backend.src.core.database import get_async_session

        configuration_service = await get_configuration_service()

        async with get_async_session() as session:
            # Get the snapshot
            snapshot = await configuration_service.get_snapshot(snapshot_id)
            if not snapshot:
                raise HTTPException(status_code=404, detail="Configuration snapshot not found")

            # Get device for validation context
            from apps.backend.src.models.device import Device
            from sqlalchemy import select

            device_query = select(Device).where(Device.id == snapshot.device_id)
            device_result = await session.execute(device_query)
            device = device_result.scalar_one_or_none()

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            # Re-run validation
            validation_results = await configuration_service.validate_configuration(
                device=device,
                config_type=snapshot.config_type,
                content=snapshot.raw_content,
                file_path=snapshot.file_path,
            )

            # Update validation status
            validation_status = "valid" if validation_results.get("valid", False) else "invalid"
            validation_output = validation_results.get("output", "")

            await configuration_service.update_snapshot_validation_status(
                session, snapshot_id, validation_status, validation_output
            )
            await session.commit()

            return APIResponse(
                success=True,
                data={
                    "snapshot_id": str(snapshot_id),
                    "validation_status": validation_status,
                    "validation_output": validation_output,
                    "validation_results": validation_results,
                },
                message="Snapshot validation retried successfully",
                errors=None,
            )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to retry snapshot validation")
