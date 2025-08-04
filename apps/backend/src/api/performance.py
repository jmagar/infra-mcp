"""
Service Performance Metrics API Endpoints

REST API endpoints for managing and querying service performance metrics,
providing insights into infrastructure service performance and trends.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_db_session
from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.schemas.performance import (
    ServicePerformanceMetricCreate,
    ServicePerformanceMetricResponse,
    ServicePerformanceMetricList,
    ServicePerformanceAggregation,
    ServicePerformanceFilter,
    ServicePerformanceComparison,
    ServicePerformanceAlert,
    ServicePerformanceTrend,
    ServicePerformanceReport,
)
from apps.backend.src.schemas.common import PaginationParams, APIResponse
from apps.backend.src.services.performance_service import PerformanceService
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def get_performance_service(db: AsyncSession = Depends(get_db_session)) -> PerformanceService:
    """Dependency to get performance service instance."""
    return PerformanceService(db)


@router.post("", response_model=APIResponse[ServicePerformanceMetricResponse], status_code=201)
async def create_performance_metric(
    metric_data: ServicePerformanceMetricCreate,
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """Create a new service performance metric entry."""
    try:
        metric = await service.create_performance_metric(metric_data)
        return APIResponse(
            success=True,
            data=metric,
            message="Performance metric created successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseOperationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=APIResponse[ServicePerformanceMetricList])
async def list_performance_metrics(
    pagination: PaginationParams = Depends(),
    service_names: Optional[str] = Query(None, description="Comma-separated service names"),
    performance_grades: Optional[str] = Query(None, description="Comma-separated performance grades (A,B,C,D,F)"),
    has_errors_only: Optional[bool] = Query(None, description="Show only services with errors"),
    low_performance_only: Optional[bool] = Query(None, description="Show only low-performing services"),
    hours: int = Query(24, description="Number of hours to look back", ge=1, le=720),
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """List service performance metrics with filtering and pagination."""
    try:
        perf_filter = ServicePerformanceFilter(
            service_names=service_names.split(",") if service_names else None,
            performance_grades=performance_grades.split(",") if performance_grades else None,
            has_errors_only=has_errors_only,
            low_performance_only=low_performance_only,
        )
        
        metric_list = await service.list_performance_metrics(pagination, perf_filter, hours=hours)
        return APIResponse(
            success=True,
            data=metric_list,
            message="Performance metrics retrieved successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to list performance metrics")


@router.get("/services/{service_name}", response_model=APIResponse[ServicePerformanceMetricList])
async def get_service_performance_metrics(
    service_name: str = Path(..., description="Service name"),
    pagination: PaginationParams = Depends(),
    hours: int = Query(168, description="Number of hours to look back", ge=1, le=8760),
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """Get performance metrics for a specific service."""
    try:
        perf_filter = ServicePerformanceFilter(service_names=[service_name])
        metric_list = await service.list_performance_metrics(pagination, perf_filter, hours=hours)
        return APIResponse(
            success=True,
            data=metric_list,
            message="Performance metrics retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting service performance metrics for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service performance metrics")


@router.get("/services/{service_name}/aggregation", response_model=APIResponse[ServicePerformanceAggregation])
async def get_service_performance_aggregation(
    service_name: str = Path(..., description="Service name"),
    hours: int = Query(168, description="Number of hours to aggregate", ge=1, le=8760),
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """Get aggregated performance metrics for a specific service."""
    try:
        aggregation = await service.get_service_aggregation(service_name, hours=hours)
        return APIResponse(
            success=True,
            data=aggregation,
            message="Service performance aggregation retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting service performance aggregation for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service performance aggregation")


@router.get("/services/{service_name}/trend", response_model=APIResponse[ServicePerformanceTrend])
async def get_service_performance_trend(
    service_name: str = Path(..., description="Service name"),
    days: int = Query(30, description="Number of days to analyze", ge=7, le=365),
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """Get performance trend analysis for a specific service."""
    try:
        trend = await service.get_service_trend(service_name, days=days)
        return APIResponse(
            success=True,
            data=trend,
            message="Service performance trend retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting service performance trend for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service performance trend")


@router.get("/comparison/{service_name}", response_model=APIResponse[ServicePerformanceComparison])
async def compare_service_performance(
    service_name: str = Path(..., description="Service name"),
    period1_hours: int = Query(24, description="First period hours", ge=1, le=720),
    period2_hours: int = Query(24, description="Second period hours", ge=1, le=720),
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """Compare service performance between two time periods."""
    try:
        comparison = await service.compare_service_performance(
            service_name, period1_hours, period2_hours
        )
        return APIResponse(
            success=True,
            data=comparison,
            message="Service performance comparison retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error comparing service performance for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare service performance")


@router.get("/alerts", response_model=APIResponse[list[ServicePerformanceAlert]])
async def get_performance_alerts(
    service_names: Optional[str] = Query(None, description="Comma-separated service names"),
    hours: int = Query(24, description="Number of hours to look back", ge=1, le=168),
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """Get performance alerts for services."""
    try:
        service_name_list = service_names.split(",") if service_names else None
        alerts = await service.get_performance_alerts(service_names=service_name_list, hours=hours)
        return APIResponse(
            success=True,
            data=alerts,
            message="Performance alerts retrieved successfully",
            errors=None
        )
    except Exception as e:
        logger.error(f"Error getting performance alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance alerts")


@router.get("/report", response_model=APIResponse[ServicePerformanceReport])
async def get_performance_report(
    service_name: Optional[str] = Query(None, description="Service name for service-specific report"),
    period: str = Query("last_24h", description="Report period (last_24h, last_week, last_month)"),
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """Generate a comprehensive service performance report."""
    try:
        report = await service.get_performance_report(service_name=service_name, period=period)
        return APIResponse(
            success=True,
            data=report,
            message="Performance report generated successfully",
            errors=None
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate performance report")


@router.delete("/cleanup", status_code=204)
async def cleanup_old_performance_metrics(
    older_than_days: int = Query(180, description="Delete metrics older than N days", ge=30, le=365),
    dry_run: bool = Query(True, description="Perform a dry run without actual deletion"),
    service: PerformanceService = Depends(get_performance_service),
    current_user=Depends(get_current_user),
):
    """Clean up old performance metrics to manage database size."""
    try:
        deleted_count = await service.cleanup_old_metrics(older_than_days, dry_run)
        logger.info(f"Performance metrics cleanup: {'Would delete' if dry_run else 'Deleted'} {deleted_count} metrics")
        return {"deleted_count": deleted_count, "dry_run": dry_run}
    except Exception as e:
        logger.error(f"Error during performance metrics cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup performance metrics")