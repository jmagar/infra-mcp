"""
Enhanced Monitoring API Endpoints

Provides detailed health checks, polling status, and performance metrics
for comprehensive infrastructure monitoring capabilities.
"""

from datetime import UTC, datetime, timedelta
import logging
import time
import traceback
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from typing_extensions import TypedDict

from apps.backend.src.core.config import get_settings
from apps.backend.src.core.database import check_database_health, get_async_session_factory
from apps.backend.src.models.container import ContainerSnapshot
from apps.backend.src.models.device import Device
from apps.backend.src.models.metrics import SystemMetric
from apps.backend.src.utils.ssh_command_manager import get_ssh_command_manager

# Remove circular import - polling_service will be accessed via FastAPI app state

logger = logging.getLogger(__name__)


def get_polling_service(request: Request) -> Any:
    """Get the polling service instance from FastAPI application state."""
    return getattr(request.app.state, 'polling_service', None)


class PerformanceMetricsResponse(TypedDict):
    performance_metrics: dict[str, float | str]
    database_performance: dict[str, dict[str, int | float | str]]
    ssh_performance: dict[str, dict[str, Any] | int | float]
    system_configuration: dict[str, dict[str, int] | int]
    recommendations: list[str]


# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/health", tags=["monitoring"])


@router.get("/detailed")
@limiter.limit("5/minute")
async def detailed_health_check(request: Request) -> dict[str, Any]:
    """
    Comprehensive system health check with component-level details

    Returns detailed status for all system components including:
    - Database health and performance metrics
    - Polling service status and statistics
    - SSH Command Manager cache statistics
    - Device connectivity and monitoring status
    - Recent data collection statistics
    """
    try:
        start_time = time.time()

        # Database health check
        database_health = await check_database_health()

        # Polling service status
        settings = get_settings()
        # Get the polling service instance from FastAPI app state
        polling_service = get_polling_service(request)
        if polling_service:
            polling_status = await polling_service.get_polling_status()
        else:
            polling_status = {
                "is_running": False,
                "container_interval_seconds": settings.polling.polling_container_interval,
                "metrics_interval_seconds": settings.polling.polling_system_metrics_interval,
                "drive_health_interval_seconds": settings.polling.polling_drive_health_interval,
                "active_devices": 0,
                "device_ids": [],
            }

        # SSH Command Manager statistics
        ssh_cmd_manager = get_ssh_command_manager()
        cache_stats = ssh_cmd_manager.get_cache_stats()

        # Database queries using session factory
        session_factory = get_async_session_factory()

        async with session_factory() as db:
            # Device statistics
            device_stats_query = select(
                func.count(Device.id).label("total_devices"),
                func.count(Device.id).filter(Device.monitoring_enabled).label("monitored_devices"),
                func.count(Device.id).filter(Device.status == "online").label("online_devices"),
                func.count(Device.id).filter(Device.status == "offline").label("offline_devices"),
            )
            device_stats_result = await db.execute(device_stats_query)
            device_stats = device_stats_result.first()

            # Add null check for device_stats
            if device_stats is None:
                device_stats = type('DeviceStats', (), {
                    'total_devices': 0,
                    'monitored_devices': 0,
                    'online_devices': 0,
                    'offline_devices': 0
                })()

            # Recent data collection statistics (last 24 hours)
            recent_metrics_query = select(func.count(SystemMetric.time)).where(
                SystemMetric.time
                >= datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            )
            recent_metrics_result = await db.execute(recent_metrics_query)
            recent_metrics_count = recent_metrics_result.scalar() or 0

            recent_containers_query = select(func.count(ContainerSnapshot.time)).where(
                ContainerSnapshot.time
                >= datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            )
            recent_containers_result = await db.execute(recent_containers_query)
            recent_containers_count = recent_containers_result.scalar() or 0

        # Component health scoring
        components = {
            "database": {
                "status": "healthy" if database_health["status"] == "healthy" else "unhealthy",
                "score": 10 if database_health["status"] == "healthy" else 2,
                "details": database_health,
                "last_check": datetime.now(UTC).isoformat(),
            },
            "polling_service": {
                "status": "healthy" if polling_status["is_running"] else "stopped",
                "score": 10 if polling_status["is_running"] else 0,
                "details": {
                    "active_devices": polling_status["active_devices"],
                    "intervals": {
                        "containers": polling_status["container_interval_seconds"],
                        "metrics": polling_status["metrics_interval_seconds"],
                        "drive_health": polling_status["drive_health_interval_seconds"],
                    },
                },
                "last_check": datetime.now(UTC).isoformat(),
            },
            "ssh_commands": {
                "status": "healthy",
                "score": 9 if cache_stats["active_entries"] > 0 else 7,
                "details": {
                    "cache_stats": cache_stats,
                    "registry_commands": len(ssh_cmd_manager.command_registry),
                },
                "last_check": datetime.now(UTC).isoformat(),
            },
            "device_connectivity": {
                "status": "healthy" if device_stats.online_devices > 0 else "warning",
                "score": min(
                    10, (device_stats.online_devices / max(device_stats.total_devices, 1)) * 10
                ),
                "details": {
                    "total_devices": device_stats.total_devices,
                    "monitored_devices": device_stats.monitored_devices,
                    "online_devices": device_stats.online_devices,
                    "offline_devices": device_stats.offline_devices,
                    "connectivity_ratio": device_stats.online_devices
                    / max(device_stats.total_devices, 1),
                },
                "last_check": datetime.now(UTC).isoformat(),
            },
            "data_collection": {
                "status": "healthy" if recent_metrics_count > 0 else "warning",
                "score": min(10, recent_metrics_count / 100),  # Expect ~100 metrics per day minimum
                "details": {
                    "recent_metrics_24h": recent_metrics_count,
                    "recent_containers_24h": recent_containers_count,
                    "collection_rate": {
                        "metrics_per_hour": recent_metrics_count / 24,
                        "containers_per_hour": recent_containers_count / 24,
                    },
                },
                "last_check": datetime.now(UTC).isoformat(),
            },
        }

        # Overall health score
        total_score = sum(comp["score"] for comp in components.values())
        max_score = len(components) * 10
        overall_score = (total_score / max_score) * 10

        # Determine overall status
        if overall_score >= 8:
            overall_status = "healthy"
        elif overall_score >= 6:
            overall_status = "warning"
        else:
            overall_status = "unhealthy"

        response_time = time.time() - start_time

        return {
            "status": overall_status,
            "score": round(overall_score, 2),
            "components": components,
            "performance": {
                "response_time_ms": round(response_time * 1000, 2),
                "check_timestamp": datetime.now(UTC).isoformat(),
            },
            "summary": {
                "total_devices": device_stats.total_devices,
                "online_devices": device_stats.online_devices,
                "polling_active": polling_status["is_running"],
                "recent_data_points": recent_metrics_count + recent_containers_count,
            },
        }

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}") from e


@router.get("/polling")
@limiter.limit("10/minute")
async def polling_health_check(request: Request) -> dict[str, Any]:
    """
    Dedicated polling service health check with detailed statistics

    Returns comprehensive polling service status including:
    - Service running status and configuration
    - Per-device polling statistics
    - Recent collection success rates
    - Performance metrics and bottlenecks
    """
    try:
        settings = get_settings()
        # Get the polling service instance from FastAPI app state
        polling_service = get_polling_service(request)
        if polling_service:
            polling_status = await polling_service.get_polling_status()
        else:
            polling_status = {
                "is_running": False,
                "container_interval_seconds": settings.polling.polling_container_interval,
                "metrics_interval_seconds": settings.polling.polling_system_metrics_interval,
                "drive_health_interval_seconds": settings.polling.polling_drive_health_interval,
                "active_devices": 0,
                "device_ids": [],
            }

        # Get device-specific polling health
        session_factory = get_async_session_factory()

        async with session_factory() as db:
            device_query = select(Device).where(Device.monitoring_enabled)
            devices_result = await db.execute(device_query)
            monitored_devices = devices_result.scalars().all()

            device_health = []
            for device in monitored_devices:
                # Check recent metrics for this device (last hour)
                one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
                recent_metrics_query = select(func.count(SystemMetric.time)).where(
                    SystemMetric.device_id == device.id, SystemMetric.time >= one_hour_ago
                )
                recent_metrics_result = await db.execute(recent_metrics_query)
                recent_metrics = recent_metrics_result.scalar() or 0

                device_health.append(
                    {
                        "device_id": str(device.id),
                        "hostname": device.hostname,
                        "status": device.status,
                        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                        "recent_metrics_1h": recent_metrics,
                        "is_being_polled": str(device.id) in polling_status.get("device_ids", []),
                        "health_score": 10
                        if recent_metrics > 0 and device.status == "online"
                        else 0,
                    }
                )

        # Calculate polling efficiency
        total_expected_collections = len(monitored_devices) * 12  # Assuming 12 collections per hour
        actual_collections = sum(int(d["recent_metrics_1h"]) for d in device_health if isinstance(d["recent_metrics_1h"], (int, str)))
        efficiency = (actual_collections / max(total_expected_collections, 1)) * 100

        return {
            "polling_service": {
                "status": "healthy" if polling_status["is_running"] else "stopped",
                "is_running": polling_status["is_running"],
                "active_devices": polling_status["active_devices"],
                "configuration": {
                    "container_interval": polling_status["container_interval_seconds"],
                    "metrics_interval": polling_status["metrics_interval_seconds"],
                    "drive_health_interval": polling_status["drive_health_interval_seconds"],
                    "max_concurrent_devices": settings.polling.polling_max_concurrent_devices,
                },
            },
            "device_health": device_health,
            "performance_metrics": {
                "polling_efficiency_percent": round(efficiency, 2),
                "total_monitored_devices": len(monitored_devices),
                "actively_polling_devices": len([d for d in device_health if d["is_being_polled"]]),
                "online_devices": len([d for d in device_health if d["status"] == "online"]),
                "recent_collections_1h": actual_collections,
                "expected_collections_1h": total_expected_collections,
            },
            "health_summary": {
                "healthy_devices": len([
                    d for d in device_health 
                    if isinstance(d.get("health_score"), (int, float)) and 
                    isinstance(d.get("health_score"), (int, float)) and 
                    float(d.get("health_score", 0)) >= 8
                ]),
                "warning_devices": len([
                    d for d in device_health 
                    if isinstance(d.get("health_score"), (int, float)) and 
                    3 <= float(d.get("health_score", 0)) < 8
                ]),
                "unhealthy_devices": len([
                    d for d in device_health 
                    if isinstance(d.get("health_score"), (int, float)) and 
                    float(d.get("health_score", 0)) < 3
                ]),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"Polling health check failed: {e}", exc_info=True)
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Polling health check service temporarily unavailable. Please try again later.",
        ) from e


@router.get("/performance")
@limiter.limit("10/minute")
async def performance_metrics(request: Request) -> PerformanceMetricsResponse:
    """
    API and system performance metrics endpoint

    Returns performance statistics including:
    - Database query performance
    - SSH command execution metrics
    - Cache hit ratios and efficiency
    - System resource utilization
    """
    try:
        start_time = time.time()

        # Database performance test
        session_factory = get_async_session_factory()
        db_start = time.time()

        async with session_factory() as db:
            db_test_query = select(func.count(Device.id))
            await db.execute(db_test_query)

        db_query_time = (time.time() - db_start) * 1000

        # SSH Command Manager performance
        ssh_cmd_manager = get_ssh_command_manager()
        ssh_cache_stats = ssh_cmd_manager.get_cache_stats()

        # Calculate SSH cache hit ratio (estimated)
        ssh_cache_efficiency = 0
        if ssh_cache_stats["total_entries"] > 0:
            ssh_cache_efficiency = (ssh_cache_stats["active_entries"] / ssh_cache_stats["total_entries"]) * 100

        # Enhanced Cache Manager performance metrics
        from apps.backend.src.utils.cache_manager import get_cache_manager
        cache_manager = await get_cache_manager()
        cache_metrics = await cache_manager.get_metrics()
        cache_health = await cache_manager.health_check()

        # System performance metrics
        settings = get_settings()

        total_response_time = (time.time() - start_time) * 1000

        return PerformanceMetricsResponse(
            performance_metrics={
                "api_response_time_ms": round(total_response_time, 2),
                "database_query_time_ms": round(db_query_time, 2),
                "ssh_cache_efficiency_percent": round(ssh_cache_efficiency, 2),
                "enhanced_cache_hit_ratio_percent": round(cache_metrics.hit_ratio * 100, 2),
                "enhanced_cache_response_time_ms": round(cache_metrics.average_response_time_ms, 2),
                "measurement_timestamp": datetime.now(UTC).isoformat(),
            },
            database_performance={
                "connection_pool": {
                    "pool_size": settings.database.db_pool_size,
                    "query_response_time_ms": round(db_query_time, 2),
                    "status": "healthy" if db_query_time < 100 else "slow",
                }
            },
            ssh_performance={
                "command_cache": ssh_cache_stats,
                "registry_size": len(ssh_cmd_manager.command_registry),
                "cache_hit_ratio_estimate": round(ssh_cache_efficiency, 2),
            },
            system_configuration={
                "polling_intervals": {
                    "containers_seconds": settings.polling.polling_container_interval,
                    "metrics_seconds": settings.polling.polling_system_metrics_interval,
                    "drive_health_seconds": settings.polling.polling_drive_health_interval,
                },
                "concurrent_devices_limit": settings.polling.polling_max_concurrent_devices,
                "rate_limits": {
                    "default_requests_per_minute": settings.api.rate_limit_requests_per_minute
                },
            },
            recommendations=[
                "Database queries performing well"
                if db_query_time < 50
                else "Consider database optimization",
                "SSH cache working efficiently"
                if ssh_cache_efficiency > 50
                else "Consider increasing SSH cache TTL",
                "Enhanced cache performing excellently"
                if cache_metrics.hit_ratio > 0.8
                else "Enhanced cache building efficiency" if cache_metrics.total_operations < 100
                else "Consider reviewing cache configuration",
                "LRU eviction working effectively"
                if cache_metrics.evictions < cache_metrics.total_operations * 0.1
                else "Cache eviction rate may be high - consider increasing cache size",
                "System performance nominal"
                if total_response_time < 200
                else "Monitor API response times",
            ],
        )

    except Exception as e:
        logger.error(f"Performance metrics collection failed: {e}", exc_info=True)
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Performance metrics service temporarily unavailable. Please try again later.",
        ) from e


@router.get("/dashboard")
@limiter.limit("30/minute")  # Higher limit for dashboard data
async def monitoring_dashboard_data(request: Request, hours: int = 24) -> dict[str, Any]:
    """
    Comprehensive monitoring dashboard data endpoint

    Returns aggregated data for monitoring dashboard including:
    - Real-time system status overview
    - Historical data trends
    - Alert summaries and recommendations
    - Quick action items
    """
    try:
        # Limit hours to reasonable range
        hours = min(max(hours, 1), 168)  # 1 hour to 1 week

        # Time range for queries
        time_threshold = datetime.now(UTC) - timedelta(hours=hours)

        # Database queries using session factory
        session_factory = get_async_session_factory()

        async with session_factory() as db:
            # Overall system status
            device_summary_query = select(
                func.count(Device.id).label("total"),
                func.count(Device.id).filter(Device.status == "online").label("online"),
                func.count(Device.id).filter(Device.monitoring_enabled).label("monitored"),
            )
            device_summary = (await db.execute(device_summary_query)).first()

            # Add null check for device_summary
            if device_summary is None:
                device_summary = type('DeviceSummary', (), {
                    'total': 0,
                    'online': 0,
                    'monitored': 0
                })()

            # Data collection summary
            metrics_count_query = select(func.count(SystemMetric.time)).where(
                SystemMetric.time >= time_threshold
            )
            metrics_count = (await db.execute(metrics_count_query)).scalar() or 0

            containers_count_query = select(func.count(ContainerSnapshot.time)).where(
                ContainerSnapshot.time >= time_threshold
            )
            containers_count = (await db.execute(containers_count_query)).scalar() or 0

        # Polling service status
        polling_service = get_polling_service(request)
        if polling_service:
            polling_status = await polling_service.get_polling_status()
        else:
            settings = get_settings()
            polling_status = {
                "is_running": False,
                "container_interval_seconds": settings.polling.polling_container_interval,
                "metrics_interval_seconds": settings.polling.polling_system_metrics_interval,
                "drive_health_interval_seconds": settings.polling.polling_drive_health_interval,
                "active_devices": 0,
                "device_ids": [],
            }

        # Health indicators
        health_indicators = {
            "system_status": "healthy" if device_summary.online > 0 else "warning",
            "data_collection": "healthy" if metrics_count > 0 else "warning",
            "polling_service": "healthy" if polling_status["is_running"] else "error",
            "overall": "healthy",
        }

        # Quick stats for dashboard
        dashboard_data = {
            "overview": {
                "total_devices": device_summary.total,
                "online_devices": device_summary.online,
                "monitored_devices": device_summary.monitored,
                "offline_devices": device_summary.total - device_summary.online,
                "connectivity_percentage": round(
                    (device_summary.online / max(device_summary.total, 1)) * 100, 1
                ),
            },
            "data_collection": {
                f"metrics_last_{hours}h": metrics_count,
                f"containers_last_{hours}h": containers_count,
                "collection_rate_per_hour": round(metrics_count / hours, 1),
                "polling_active": polling_status["is_running"],
                "active_polling_devices": polling_status["active_devices"],
            },
            "health_indicators": health_indicators,
            "quick_actions": [
                "All systems operational"
                if all(status == "healthy" for status in health_indicators.values())
                else "Check system health for issues",
                f"Monitoring {device_summary.monitored} of {device_summary.total} devices",
                f"Collected {metrics_count + containers_count} data points in last {hours}h",
            ],
            "alerts": [
                {"level": "warning", "message": "Some devices offline"}
                if device_summary.total - device_summary.online > 0
                else None,
                {"level": "info", "message": "Polling service running normally"}
                if polling_status["is_running"]
                else {"level": "error", "message": "Polling service not running"},
            ],
            "timestamp": datetime.now(UTC).isoformat(),
            "data_range_hours": hours,
        }

        # Remove None alerts
        alerts_list = dashboard_data.get("alerts", [])
        if isinstance(alerts_list, list):
            dashboard_data["alerts"] = [
                alert for alert in alerts_list if alert is not None
            ]
        else:
            dashboard_data["alerts"] = []

        return dashboard_data

    except Exception as e:
        logger.error(f"Dashboard data collection failed: {e}", exc_info=True)
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Dashboard data service temporarily unavailable. Please try again later.",
        ) from e
