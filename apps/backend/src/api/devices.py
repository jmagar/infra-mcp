"""
Device Management API Endpoints

REST API endpoints for managing infrastructure devices including creation,
retrieval, updates, deletion, and status monitoring.

NOTE: This API is now primarily for device registration and optional database management.
The core SSH-based monitoring tools work directly with hostnames and don't require device registration.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_db_session
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError, DatabaseOperationError, ValidationError as CustomValidationError
)
from apps.backend.src.schemas.device import (
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceList,
    DeviceSummary, DeviceConnectionTest
)
from apps.backend.src.schemas.common import OperationResult, PaginationParams, DeviceStatus
from ..services.device_service import DeviceService
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

def get_device_service(db: AsyncSession = Depends(get_db_session)) -> DeviceService:
    return DeviceService(db)

@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    device_data: DeviceCreate,
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user)
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
    current_user=Depends(get_current_user)
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
    current_user=Depends(get_current_user)
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
    current_user=Depends(get_current_user)
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
    current_user=Depends(get_current_user)
):
    try:
        result = await service.delete_device_by_hostname(hostname)
        return OperationResult[dict](
            success=True,
            operation_type="delete_device",
            result=result,
            message=f"Device '{hostname}' deleted successfully"
        )
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting device {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete device.")

@router.get("/{hostname}/status", response_model=DeviceConnectionTest)
async def get_device_status_by_hostname(
    hostname: str = Path(..., description="Device hostname"),
    test_connectivity: bool = Query(True, description="Test SSH connectivity"),
    service: DeviceService = Depends(get_device_service),
    current_user=Depends(get_current_user)
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
    current_user=Depends(get_current_user)
):
    try:
        summary = await service.get_device_summary_by_hostname(hostname)
        return summary
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting device summary {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device summary.")
