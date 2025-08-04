"""
Cache Metadata API Endpoints

REST API endpoints for managing infrastructure data cache metadata,
providing insights into cache performance and efficiency.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_db_session
from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.schemas.cache import (
    CacheMetadataCreate,
    CacheMetadataResponse,
    CacheMetadataList,
    CacheMetrics,
    CachePerformanceAnalysis,
    CacheEfficiencyReport,
    CacheFilter,
)
from apps.backend.src.schemas.common import PaginationParams, APIResponse
from apps.backend.src.services.cache_service import CacheService
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def get_cache_service(db: AsyncSession = Depends(get_db_session)) -> CacheService:
    """Dependency to get cache service instance."""
    return CacheService(db)


@router.post("", response_model=APIResponse[CacheMetadataResponse], status_code=201)
async def create_cache_entry(
    cache_data: CacheMetadataCreate,
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Create a new cache metadata entry."""
    try:
        cache_entry = await service.create_cache_entry(cache_data)
        return APIResponse(
            success=True,
            data=cache_entry,
            message="Cache entry created successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=APIResponse[CacheMetadataList])
async def list_cache_entries(
    pagination: PaginationParams = Depends(),
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"),
    data_types: Optional[str] = Query(None, description="Comma-separated data types"),
    cache_tiers: Optional[str] = Query(None, description="Comma-separated cache tiers"),
    expired_only: Optional[bool] = Query(None, description="Show only expired entries"),
    recently_accessed_only: Optional[bool] = Query(None, description="Show only recently accessed entries"),
    low_hit_ratio_only: Optional[bool] = Query(None, description="Show only entries with low hit ratios"),
    hours: int = Query(24, description="Number of hours to look back", ge=1, le=720),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """List cache metadata entries with filtering and pagination."""
    try:
        cache_filter = CacheFilter(
            device_ids=[UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None,
            data_types=data_types.split(",") if data_types else None,
            cache_tiers=cache_tiers.split(",") if cache_tiers else None,
            expired_only=expired_only,
            recently_accessed_only=recently_accessed_only,
            low_hit_ratio_only=low_hit_ratio_only,
        )
        
        cache_list = await service.list_cache_entries(pagination, cache_filter, hours=hours)
        return APIResponse(
            success=True,
            data=cache_list,
            message="Cache entries retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing cache entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to list cache entries")


@router.get("/{cache_key}", response_model=APIResponse[CacheMetadataResponse])
async def get_cache_entry(
    cache_key: str = Path(..., description="Cache key"),
    device_id: Optional[UUID] = Query(None, description="Device UUID for device-specific cache"),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Get a specific cache entry."""
    try:
        cache_entry = await service.get_cache_entry(cache_key, device_id=device_id)
        if not cache_entry:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        return APIResponse(
            success=True,
            data=cache_entry,
            message="Cache entry created successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting cache entry {cache_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache entry")


@router.patch("/{cache_key}/access")
async def update_cache_access(
    cache_key: str = Path(..., description="Cache key"),
    hit: bool = Query(..., description="Whether this was a cache hit or miss"),
    device_id: Optional[UUID] = Query(None, description="Device UUID for device-specific cache"),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Update cache access statistics."""
    try:
        success = await service.update_cache_access(cache_key, hit=hit, device_id=device_id)
        if not success:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        return {"status": "updated", "cache_key": cache_key, "hit": hit}
    except Exception as e:
        logger.error(f"Error updating cache access for {cache_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update cache access")


@router.get("/metrics/overview", response_model=APIResponse[CacheMetrics])
async def get_cache_metrics(
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"),
    data_types: Optional[str] = Query(None, description="Comma-separated data types"),
    hours: int = Query(24, description="Number of hours to analyze", ge=1, le=720),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Get aggregated cache metrics."""
    try:
        device_id_list = [UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None
        data_type_list = data_types.split(",") if data_types else None
        
        metrics = await service.get_cache_metrics(
            device_ids=device_id_list, data_types=data_type_list, hours=hours
        )
        return APIResponse(
            success=True,
            data=metrics,
            message="Cache metrics retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache metrics")


@router.get("/analysis/performance", response_model=APIResponse[CachePerformanceAnalysis])
async def get_cache_performance_analysis(
    data_type: Optional[str] = Query(None, description="Data type to analyze"),
    hours: int = Query(168, description="Number of hours to analyze", ge=1, le=8760),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Get cache performance analysis."""
    try:
        analysis = await service.get_cache_performance_analysis(data_type=data_type, hours=hours)
        return APIResponse(
            success=True,
            data=analysis,
            message="Cache performance analysis retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting cache performance analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache performance analysis")


@router.get("/report/efficiency", response_model=APIResponse[CacheEfficiencyReport])
async def get_cache_efficiency_report(
    device_id: Optional[UUID] = Query(None, description="Device UUID for device-specific report"),
    period: str = Query("last_24h", description="Report period (last_24h, last_week, last_month)"),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Generate a cache efficiency report."""
    try:
        report = await service.get_cache_efficiency_report(device_id=device_id, period=period)
        return APIResponse(
            success=True,
            data=report,
            message="Cache efficiency report generated successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating cache efficiency report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate cache efficiency report")


@router.delete("/cleanup/expired", status_code=204)
async def cleanup_expired_cache_entries(
    dry_run: bool = Query(True, description="Perform a dry run without actual deletion"),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Clean up expired cache entries."""
    try:
        deleted_count = await service.cleanup_expired_entries(dry_run)
        logger.info(f"Cache expired cleanup: {'Would delete' if dry_run else 'Deleted'} {deleted_count} entries")
        return {"deleted_count": deleted_count, "dry_run": dry_run}
    except Exception as e:
        logger.error(f"Error during cache expired cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup expired cache entries")


@router.delete("/cleanup/old", status_code=204)
async def cleanup_old_cache_entries(
    older_than_days: int = Query(30, description="Delete entries older than N days", ge=7, le=365),
    dry_run: bool = Query(True, description="Perform a dry run without actual deletion"),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Clean up old cache metadata entries to manage database size."""
    try:
        deleted_count = await service.cleanup_old_entries(older_than_days, dry_run)
        logger.info(f"Cache old entries cleanup: {'Would delete' if dry_run else 'Deleted'} {deleted_count} entries")
        return {"deleted_count": deleted_count, "dry_run": dry_run}
    except Exception as e:
        logger.error(f"Error during cache old entries cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup old cache entries")


# Device-specific endpoints
@router.get("/devices/{device_id}/entries", response_model=APIResponse[CacheMetadataList])
async def get_device_cache_entries(
    device_id: UUID = Path(..., description="Device UUID"),
    pagination: PaginationParams = Depends(),
    data_types: Optional[str] = Query(None, description="Comma-separated data types"),
    expired_only: Optional[bool] = Query(None, description="Show only expired entries"),
    hours: int = Query(168, description="Number of hours to look back", ge=1, le=8760),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Get cache entries for a specific device."""
    try:
        cache_filter = CacheFilter(
            device_ids=[device_id],
            data_types=data_types.split(",") if data_types else None,
            expired_only=expired_only,
        )
        
        cache_list = await service.list_cache_entries(pagination, cache_filter, hours=hours)
        return APIResponse(
            success=True,
            data=cache_list,
            message="Cache entries retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting device cache entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device cache entries")


@router.get("/devices/{device_id}/metrics", response_model=APIResponse[CacheMetrics])
async def get_device_cache_metrics(
    device_id: UUID = Path(..., description="Device UUID"),
    data_types: Optional[str] = Query(None, description="Comma-separated data types"),
    hours: int = Query(168, description="Number of hours to analyze", ge=1, le=8760),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Get cache metrics for a specific device."""
    try:
        data_type_list = data_types.split(",") if data_types else None
        
        metrics = await service.get_cache_metrics(
            device_ids=[device_id], data_types=data_type_list, hours=hours
        )
        return APIResponse(
            success=True,
            data=metrics,
            message="Cache metrics retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting device cache metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device cache metrics")


@router.get("/data-types/{data_type}/metrics", response_model=APIResponse[CacheMetrics])
async def get_data_type_cache_metrics(
    data_type: str = Path(..., description="Data type to analyze"),
    device_ids: Optional[str] = Query(None, description="Comma-separated device UUIDs"),
    hours: int = Query(168, description="Number of hours to analyze", ge=1, le=8760),
    service: CacheService = Depends(get_cache_service),
    current_user=Depends(get_current_user),
):
    """Get cache metrics for a specific data type."""
    try:
        device_id_list = [UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None
        
        metrics = await service.get_cache_metrics(
            device_ids=device_id_list, data_types=[data_type], hours=hours
        )
        return APIResponse(
            success=True,
            data=metrics,
            message="Cache metrics retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting data type cache metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get data type cache metrics")