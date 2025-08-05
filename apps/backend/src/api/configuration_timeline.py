"""
Configuration Timeline API Endpoints

REST API endpoints for configuration timeline visualization, diff analysis, and change impact tracking.
Provides comprehensive timeline data, file history, version comparisons, and impact analysis.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BusinessLogicError,
)
from ..schemas.configuration_timeline import (
    ConfigurationTimelineResponse,
    FileHistoryResponse,
    VersionComparisonRequest,
    VersionComparisonResponse,
    ChangeImpactResponse,
    TimelineQueryParams,
    FileHistoryQueryParams,
)
from ..services.configuration_timeline_service import get_configuration_timeline_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/configuration-timeline", tags=["Configuration Timeline"])


@router.get(
    "/{device_id}",
    response_model=ConfigurationTimelineResponse,
    summary="Get Device Configuration Timeline",
    description="""
    Get comprehensive configuration timeline for a specific device.
    
    Returns chronological view of configuration changes with events, snapshots,
    and optional diff calculations. Supports filtering by file path and time range.
    """,
)
async def get_device_configuration_timeline(
    device_id: UUID = Path(..., description="Device ID to get timeline for"),
    file_path: str | None = Query(None, description="Filter by specific file path"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days of history to include"),
    include_content: bool = Query(
        False, description="Whether to include full file content in snapshots"
    ),
    include_diffs: bool = Query(
        True, description="Whether to include diff calculations between versions"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> ConfigurationTimelineResponse:
    """Get configuration timeline for a specific device."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_device_timeline_api",
            device_id=str(device_id),
        )

        logger.info("Getting device configuration timeline via API")

        timeline_service = await get_configuration_timeline_service()

        timeline_data = await timeline_service.get_device_configuration_timeline(
            session=session,
            device_id=device_id,
            file_path=file_path,
            days_back=days_back,
            include_content=include_content,
            include_diffs=include_diffs,
        )

        return ConfigurationTimelineResponse(**timeline_data)

    except ResourceNotFoundError as e:
        logger.warning("Device not found for timeline", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        logger.warning("Invalid timeline request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error getting device timeline", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration timeline")


@router.get(
    "/{device_id}/files/{file_path:path}/history",
    response_model=FileHistoryResponse,
    summary="Get Configuration File History",
    description="""
    Get detailed version history for a specific configuration file.
    
    Returns chronological list of file versions with content, diffs,
    related events, and file statistics.
    """,
)
async def get_configuration_file_history(
    device_id: UUID = Path(..., description="Device ID"),
    file_path: str = Path(..., description="Configuration file path"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of versions to return"),
    include_content: bool = Query(True, description="Whether to include full file content"),
    session: AsyncSession = Depends(get_async_session),
) -> FileHistoryResponse:
    """Get detailed history for a specific configuration file."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_file_history_api",
            device_id=str(device_id),
            file_path=file_path,
        )

        logger.info("Getting configuration file history via API")

        timeline_service = await get_configuration_timeline_service()

        history_data = await timeline_service.get_configuration_file_history(
            session=session,
            device_id=device_id,
            file_path=file_path,
            limit=limit,
            include_content=include_content,
        )

        return FileHistoryResponse(**history_data)

    except ResourceNotFoundError as e:
        logger.warning("Device or file not found for history", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        logger.warning("Invalid file history request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error getting file history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration file history")


@router.post(
    "/compare",
    response_model=VersionComparisonResponse,
    summary="Compare Configuration Versions",
    description="""
    Compare two configuration snapshots and generate detailed diff analysis.
    
    Supports multiple diff formats (unified, side-by-side, json) with
    comprehensive change analysis and risk assessment.
    """,
)
async def compare_configuration_versions(
    comparison_request: VersionComparisonRequest = Body(
        ..., description="Version comparison request"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> VersionComparisonResponse:
    """Compare two configuration snapshots."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="compare_versions_api",
            snapshot_1=str(comparison_request.snapshot_id_1),
            snapshot_2=str(comparison_request.snapshot_id_2),
        )

        logger.info("Comparing configuration versions via API")

        timeline_service = await get_configuration_timeline_service()

        comparison_data = await timeline_service.compare_configuration_versions(
            session=session,
            snapshot_id_1=comparison_request.snapshot_id_1,
            snapshot_id_2=comparison_request.snapshot_id_2,
            diff_format=comparison_request.diff_format,
        )

        return VersionComparisonResponse(**comparison_data)

    except ResourceNotFoundError as e:
        logger.warning("Snapshot not found for comparison", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        logger.warning("Invalid version comparison request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error comparing versions", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to compare configuration versions")


@router.get(
    "/events/{event_id}/impact",
    response_model=ChangeImpactResponse,
    summary="Get Configuration Change Impact",
    description="""
    Get comprehensive impact analysis for a configuration change event.
    
    Returns detailed analysis including affected services, rollback availability,
    related changes, and visualization data for understanding change impact.
    """,
)
async def get_configuration_change_impact(
    event_id: UUID = Path(..., description="Configuration change event ID"),
    session: AsyncSession = Depends(get_async_session),
) -> ChangeImpactResponse:
    """Get detailed impact analysis for a configuration change event."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_change_impact_api",
            event_id=str(event_id),
        )

        logger.info("Getting configuration change impact via API")

        timeline_service = await get_configuration_timeline_service()

        impact_data = await timeline_service.get_configuration_change_impact(
            session=session,
            change_event_id=event_id,
        )

        return ChangeImpactResponse(**impact_data)

    except ResourceNotFoundError as e:
        logger.warning("Change event not found for impact analysis", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        logger.warning("Invalid change impact request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error getting change impact", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve configuration change impact"
        )


@router.get(
    "/devices/{device_id}/activity-summary",
    summary="Get Device Configuration Activity Summary",
    description="""
    Get summarized configuration activity for a device over time.
    
    Returns high-level statistics, recent changes, and activity trends
    without detailed timeline data for dashboard use.
    """,
)
async def get_device_activity_summary(
    device_id: UUID = Path(..., description="Device ID"),
    days_back: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get summarized configuration activity for a device."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_activity_summary_api",
            device_id=str(device_id),
        )

        logger.info("Getting device activity summary via API")

        timeline_service = await get_configuration_timeline_service()

        # Get timeline data without content/diffs for efficiency
        timeline_data = await timeline_service.get_device_configuration_timeline(
            session=session,
            device_id=device_id,
            days_back=days_back,
            include_content=False,
            include_diffs=False,
        )

        # Extract summary information
        timeline = timeline_data["timeline"]
        stats = timeline_data["statistics"]

        # Get recent activity (last 5 items)
        recent_activity = timeline[:5]

        # Calculate activity trends
        activity_trend = "stable"
        if stats["total_events"] > 0:
            recent_events = [item for item in timeline[:10] if item["type"] == "event"]
            older_events = [item for item in timeline[10:20] if item["type"] == "event"]

            if len(recent_events) > len(older_events) * 1.5:
                activity_trend = "increasing"
            elif len(recent_events) < len(older_events) * 0.5:
                activity_trend = "decreasing"

        summary = {
            "device_id": str(device_id),
            "device_name": timeline_data["device_name"],
            "analysis_period": {
                "days_back": days_back,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "activity_stats": {
                "total_events": stats["total_events"],
                "total_snapshots": stats["total_snapshots"],
                "unique_files": stats["file_count"],
                "activity_trend": activity_trend,
            },
            "risk_summary": {
                "distribution": stats["risk_distribution"],
                "highest_risk": max(
                    stats["risk_distribution"].keys(),
                    key=lambda k: stats["risk_distribution"].get(k, 0),
                )
                if stats["risk_distribution"]
                else "none",
            },
            "recent_activity": recent_activity,
            "change_patterns": {
                "change_types": stats["change_type_distribution"],
                "peak_hour": stats["activity_by_hour"].index(max(stats["activity_by_hour"]))
                if any(stats["activity_by_hour"])
                else None,
            },
        }

        return summary

    except ResourceNotFoundError as e:
        logger.warning("Device not found for activity summary", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error getting activity summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve device activity summary")


@router.get(
    "/health",
    summary="Configuration Timeline Service Health Check",
    description="Check the health and status of the configuration timeline service.",
)
async def get_timeline_service_health() -> dict[str, Any]:
    """Check configuration timeline service health."""

    try:
        timeline_service = await get_configuration_timeline_service()

        return {
            "status": "healthy",
            "service": "ConfigurationTimelineService",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "features": {
                "timeline_visualization": True,
                "diff_analysis": True,
                "impact_analysis": True,
                "version_comparison": True,
                "activity_summaries": True,
            },
            "diff_formats": ["unified", "side-by-side", "json"],
        }

    except Exception as e:
        logger.error("Timeline service health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Configuration timeline service is unavailable")
