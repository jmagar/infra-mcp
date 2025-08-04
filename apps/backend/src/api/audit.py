"""
Data Collection Audit API Endpoints

REST API endpoints for managing and querying data collection audit trails,
providing visibility into all infrastructure data collection operations.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_db_session
from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.schemas.audit import (
    DataCollectionAuditCreate,
    DataCollectionAuditListResponse,
    DataCollectionAuditDetailResponse,
    DataCollectionMetricsResponse,
    DataCollectionPerformanceReportResponse,
    BulkAuditCreate,
    BulkAuditOperationResponse,
    DataCollectionFilter,
)
from apps.backend.src.schemas.common import PaginationParams
from apps.backend.src.services.audit_service import AuditService
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def get_audit_service(db: AsyncSession = Depends(get_db_session)) -> AuditService:
    """Dependency to get audit service instance."""
    return AuditService(db)


@router.post("", response_model=DataCollectionAuditDetailResponse, status_code=201)
async def create_audit_entry(
    audit_data: DataCollectionAuditCreate,
    service: AuditService = Depends(get_audit_service),
    current_user=Depends(get_current_user),
):
    """Create a new data collection audit entry."""
    try:
        audit_entry = await service.create_audit_entry(audit_data)
        return DataCollectionAuditDetailResponse(
            success=True,
            data=audit_entry,
            message="Audit entry created successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=BulkAuditOperationResponse, status_code=201)
async def create_bulk_audit_entries(
    bulk_data: BulkAuditCreate,
    service: AuditService = Depends(get_audit_service),
    current_user=Depends(get_current_user),
):
    """Create multiple audit entries in a single operation."""
    try:
        result = await service.create_bulk_audit_entries(bulk_data.entries)
        return BulkAuditOperationResponse(bulk_result=result)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=DataCollectionAuditListResponse)
async def list_audit_entries(
    pagination: PaginationParams = Depends(),
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"),
    data_types: Optional[str] = Query(None, description="Comma-separated data types"),
    collection_methods: Optional[str] = Query(None, description="Comma-separated collection methods"),
    statuses: Optional[str] = Query(None, description="Comma-separated status values"),
    errors_only: Optional[bool] = Query(None, description="Show only failed operations"),
    cache_hit_only: Optional[bool] = Query(None, description="Show only cache hit operations"),
    service: AuditService = Depends(get_audit_service),
    current_user=Depends(get_current_user),
):
    """List data collection audit entries with filtering and pagination."""
    try:
        # Parse comma-separated filter parameters
        audit_filter = DataCollectionFilter(
            device_ids=[UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None,
            data_types=data_types.split(",") if data_types else None,
            collection_methods=collection_methods.split(",") if collection_methods else None,
            statuses=statuses.split(",") if statuses else None,
            errors_only=errors_only,
            cache_hit_only=cache_hit_only,
        )
        
        audit_list = await service.list_audit_entries(pagination, audit_filter)
        return DataCollectionAuditListResponse(
            success=True,
            data=audit_list,
            message="Audit entries retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing audit entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to list audit entries")


@router.get("/metrics", response_model=DataCollectionMetricsResponse)
async def get_audit_metrics(
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"),
    data_types: Optional[str] = Query(None, description="Comma-separated data types"),
    hours: int = Query(24, description="Number of hours to analyze", ge=1, le=720),
    service: AuditService = Depends(get_audit_service),
    current_user=Depends(get_current_user),
):
    """Get aggregated metrics for data collection operations."""
    try:
        # Parse filter parameters
        device_id_list = [UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None
        data_type_list = data_types.split(",") if data_types else None
        
        metrics = await service.get_audit_metrics(
            device_ids=device_id_list,
            data_types=data_type_list,
            hours=hours
        )
        return DataCollectionMetricsResponse(data=metrics)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting audit metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit metrics")


@router.get("/performance-report", response_model=DataCollectionPerformanceReportResponse)
async def get_performance_report(
    device_id: Optional[UUID] = Query(None, description="Device UUID for device-specific report"),
    period: str = Query("last_24h", description="Report period (last_24h, last_week, last_month)"),
    service: AuditService = Depends(get_audit_service),
    current_user=Depends(get_current_user),
):
    """Generate a comprehensive performance report for data collection operations."""
    try:
        report = await service.get_performance_report(device_id=device_id, period=period)
        return DataCollectionPerformanceReportResponse(data=report)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate performance report")


@router.get("/devices/{device_id}", response_model=DataCollectionAuditListResponse)
async def get_device_audit_entries(
    device_id: UUID = Path(..., description="Device UUID"),
    pagination: PaginationParams = Depends(),
    data_types: Optional[str] = Query(None, description="Comma-separated data types"),
    hours: int = Query(24, description="Number of hours to look back", ge=1, le=720),
    service: AuditService = Depends(get_audit_service),
    current_user=Depends(get_current_user),
):
    """Get audit entries for a specific device."""
    try:
        audit_filter = DataCollectionFilter(
            device_ids=[device_id],
            data_types=data_types.split(",") if data_types else None,
        )
        
        audit_list = await service.list_audit_entries(pagination, audit_filter, hours=hours)
        return DataCollectionAuditListResponse(data=audit_list)
    except Exception as e:
        logger.error(f"Error getting device audit entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device audit entries")


@router.delete("/cleanup", status_code=204)
async def cleanup_old_audit_entries(
    older_than_days: int = Query(90, description="Delete entries older than N days", ge=7, le=365),
    dry_run: bool = Query(True, description="Perform a dry run without actual deletion"),
    service: AuditService = Depends(get_audit_service),
    current_user=Depends(get_current_user),
):
    """Clean up old audit entries to manage database size."""
    try:
        deleted_count = await service.cleanup_old_entries(older_than_days, dry_run)
        logger.info(f"Audit cleanup: {'Would delete' if dry_run else 'Deleted'} {deleted_count} entries")
        return {"deleted_count": deleted_count, "dry_run": dry_run}
    except Exception as e:
        logger.error(f"Error during audit cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup audit entries")