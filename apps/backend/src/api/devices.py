"""
Device Management API Endpoints

REST API endpoints for managing infrastructure devices including creation,
retrieval, updates, deletion, and status monitoring.

NOTE: This API is now primarily for device registration and optional database management.
The core SSH-based monitoring tools work directly with hostnames and don't require device registration.
"""

import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_db_session
from apps.backend.src.utils.ssh_config_parser import parse_ssh_config
from apps.backend.src.schemas.device import DeviceImportResult
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    DatabaseOperationError,
    ValidationError as CustomValidationError,
    SSHCommandError,
    SSHConnectionError,
)
from apps.backend.src.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceList,
    DeviceSummary,
    DeviceConnectionTest,
    DeviceImportRequest,
    DeviceImportResponse,
)
from apps.backend.src.schemas.common import OperationResult, PaginationParams, DeviceStatus
from ..services.device_service import DeviceService
from apps.backend.src.api.common import get_current_user
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.core.logging_config import (
    set_correlation_id,
    set_operation_context,
    set_device_context,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_device_service(db: AsyncSession = Depends(get_db_session)) -> DeviceService:
    return DeviceService(db)


async def get_unified_service():
    """Dependency to get UnifiedDataCollectionService instance"""
    return await get_unified_data_collection_service()


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    device_data: DeviceCreate,
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user),
):
    try:
        device = await service.create_device(device_data)
        return DeviceResponse.model_validate(device)
    except CustomValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating device: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.get("", response_model=DeviceList)
async def list_devices(
    pagination: PaginationParams = Depends(),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[DeviceStatus] = Query(None, description="Filter by device status"),
    monitoring_enabled: Optional[bool] = Query(None, description="Filter by monitoring status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    search: Optional[str] = Query(None, description="Search in hostname and description"),
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user),
):
    try:
        return await service.list_devices(
            pagination=pagination,
            device_type=device_type,
            status=status,
            monitoring_enabled=monitoring_enabled,
            location=location,
            search=search,
        )
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail="Failed to list devices.")


@router.get("/{hostname}", response_model=DeviceResponse)
async def get_device_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user),
):
    try:
        device = await service.get_device_by_hostname(hostname)
        return DeviceResponse.model_validate(device)
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving device {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve device.")


@router.put("/{hostname}", response_model=DeviceResponse)
async def update_device_by_hostname(
    device_update: DeviceUpdate,
    hostname: str = Path(..., description="Device hostname"),
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user),
):
    try:
        device = await service.update_device_by_hostname(hostname, device_update)
        return DeviceResponse.model_validate(device)
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating device {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update device.")


@router.delete("/{hostname}", response_model=OperationResult[dict])
async def delete_device_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user),
):
    start_time = time.time()
    operation_id = str(uuid.uuid4())

    try:
        result = await service.delete_device_by_hostname(hostname)
        execution_time_ms = int((time.time() - start_time) * 1000)

        return OperationResult[dict](
            success=True,
            operation_id=operation_id,
            operation_type="delete_device",
            result=result,
            error_message=None,
            warnings=[],
            execution_time_ms=execution_time_ms,
            message=f"Device '{hostname}' deleted successfully",
        )
    except DeviceNotFoundError as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error deleting device {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete device.") from e


@router.get("/{hostname}/status", response_model=DeviceConnectionTest)
async def get_device_status_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    test_connectivity: bool = Query(True, description="Test SSH connectivity"),
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user),
):
    try:
        return await service.get_device_status_by_hostname(hostname, test_connectivity)
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting device status {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device status.")


@router.get("/{hostname}/summary", response_model=DeviceSummary)
async def get_device_summary_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user),
):
    try:
        summary = await service.get_device_summary_by_hostname(hostname)
        return summary
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting device summary {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device summary.")


# System Monitoring Endpoints
@router.get("/{hostname}/metrics")
async def get_device_metrics_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    include_processes: bool = Query(False, description="Include process information"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Get comprehensive system performance metrics from a device"""
    # TODO: This endpoint needs to be updated to use the new granular monitoring functions
    # or removed if deprecated. The get_device_info function is no longer available.
    raise HTTPException(
        status_code=501,
        detail="This endpoint is temporarily unavailable during refactoring. Use specific endpoints like /drives, /logs, etc.",
    )


@router.get("/{hostname}/drives")
async def get_device_drives_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    drive: str | None = Query(None, description="Filter by specific drive name"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Get S.M.A.R.T. drive health information and disk status"""
    try:
        return await get_drive_health(hostname, drive, timeout)
    except SSHCommandError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error getting drive health for {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get drive health.") from e


@router.get("/{hostname}/drives/stats")
async def get_device_drives_stats_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    drive: str | None = Query(None, description="Filter by specific drive name (e.g., 'sda')"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Get drive usage statistics, I/O performance, and utilization metrics"""
    try:
        return await get_drive_stats(hostname, drive, timeout)
    except SSHCommandError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error getting drive stats for {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get drive stats.") from e


@router.get("/{hostname}/logs")
async def get_device_logs_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    service: str | None = Query(None, description="Filter by service name"),
    since: str | None = Query("1h", description="Time range (1h, 6h, 24h, 7d)"),
    lines: int = Query(100, ge=1, le=1000, description="Number of log lines to return"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
) -> dict:
    """Get system logs from journald or traditional syslog"""
    try:
        return await get_system_logs(hostname, service, since, lines, timeout)
    except SSHCommandError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error getting system logs for {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system logs.") from e


@router.get("/{hostname}/ports")
async def get_device_ports_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
) -> dict:
    """Get network port information and listening processes"""
    try:
        return await get_network_ports(hostname, timeout)
    except SSHCommandError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error getting network ports for {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get network ports.") from e


@router.post("/import", response_model=DeviceImportResponse, status_code=200)
async def import_devices_from_ssh_config(
    import_request: DeviceImportRequest,
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user),
):
    """
    Import devices from SSH configuration file.

    Parses the specified SSH config file to extract host information and
    creates or updates devices in the registry. Supports dry-run mode
    to preview changes before applying them.
    """
    try:
        # Parse SSH config file
        try:
            importable_devices = parse_ssh_config(import_request.ssh_config_path)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"SSH config file not found: {import_request.ssh_config_path}",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid SSH config file: {str(e)}") from e

        if not importable_devices:
            return DeviceImportResponse(
                total_hosts_found=0,
                results=[],
                summary={"created": 0, "updated": 0, "skipped": 0, "errors": 0},
                dry_run=import_request.dry_run,
            )

        results = []

        for device_data in importable_devices:
            # Apply user preferences
            device_data["device_type"] = import_request.default_device_type
            device_data["monitoring_enabled"] = import_request.default_monitoring

            # Add tag prefix if specified
            if import_request.tag_prefix:
                device_data["tags"]["import_prefix"] = import_request.tag_prefix

            try:
                hostname = device_data["hostname"]

                if import_request.dry_run:
                    # Check if device exists without modifying
                    existing_device = await service.get_device_by_hostname(hostname)
                    if existing_device:
                        action = "would_update" if import_request.update_existing else "would_skip"
                    else:
                        action = "would_create"

                    results.append(
                        DeviceImportResult(
                            hostname=hostname,
                            action=action,
                            device_id=existing_device.id if existing_device else None,
                            changes=device_data,
                        )
                    )
                else:
                    # Actually import the device
                    existing_device = await service.get_device_by_hostname(hostname)

                    if existing_device:
                        if import_request.update_existing:
                            # Update existing device
                            update_data = DeviceUpdate(
                                **{k: v for k, v in device_data.items() if v is not None}
                            )
                            updated_device = await service.update_device(hostname, update_data)

                            results.append(
                                DeviceImportResult(
                                    hostname=hostname,
                                    action="updated",
                                    device_id=updated_device.id,
                                    changes=device_data,
                                )
                            )
                        else:
                            # Skip existing device
                            results.append(
                                DeviceImportResult(
                                    hostname=hostname,
                                    action="skipped",
                                    device_id=existing_device.id,
                                    error_message="Device already exists and update_existing=False",
                                )
                            )
                    else:
                        # Create new device
                        create_data = DeviceCreate(**device_data)
                        new_device = await service.create_device(create_data)

                        results.append(
                            DeviceImportResult(
                                hostname=hostname,
                                action="created",
                                device_id=new_device.id,
                                changes=device_data,
                            )
                        )

            except Exception as e:
                logger.error(
                    f"Error importing device {device_data.get('hostname', 'unknown')}: {e}"
                )
                results.append(
                    DeviceImportResult(
                        hostname=device_data.get("hostname", "unknown"),
                        action="error",
                        error_message=str(e),
                    )
                )

        # Create summary
        summary = DeviceImportResponse.create_summary(results)

        return DeviceImportResponse(
            total_hosts_found=len(importable_devices),
            results=results,
            summary=summary,
            dry_run=import_request.dry_run,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during device import: {e}")
        raise HTTPException(status_code=500, detail="Device import failed") from e
