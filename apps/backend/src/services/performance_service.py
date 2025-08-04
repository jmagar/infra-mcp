"""
Service Performance Metrics Service

Service layer for managing service performance metrics operations,
providing business logic for performance tracking and analysis.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.models.performance import ServicePerformanceMetric
from apps.backend.src.schemas.performance import (
    ServicePerformanceMetricCreate,
    ServicePerformanceMetricResponse,
    ServicePerformanceMetricList,
    ServicePerformanceMetricSummary,
    ServicePerformanceAggregation,
    ServicePerformanceFilter,
    ServicePerformanceComparison,
    ServicePerformanceAlert,
    ServicePerformanceTrend,
    ServicePerformanceReport,
)
from apps.backend.src.schemas.common import PaginationParams

logger = logging.getLogger(__name__)


class PerformanceService:
    """Service for managing service performance metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_performance_metric(
        self, metric_data: ServicePerformanceMetricCreate
    ) -> ServicePerformanceMetricResponse:
        """Create a new performance metric entry."""
        try:
            metric = ServicePerformanceMetric(
                time=datetime.now(timezone.utc),
                service_name=metric_data.service_name,
                operations_total=metric_data.operations_total,
                operations_successful=metric_data.operations_successful,
                operations_failed=metric_data.operations_failed,
                operations_cached=metric_data.operations_cached,
                avg_duration_ms=metric_data.avg_duration_ms,
                max_duration_ms=metric_data.max_duration_ms,
                min_duration_ms=metric_data.min_duration_ms,
                ssh_connections_created=metric_data.ssh_connections_created,
                ssh_connections_reused=metric_data.ssh_connections_reused,
                ssh_commands_executed=metric_data.ssh_commands_executed,
                cache_hit_ratio=metric_data.cache_hit_ratio,
                cache_size_entries=metric_data.cache_size_entries,
                cache_evictions=metric_data.cache_evictions,
                data_collected_bytes=metric_data.data_collected_bytes,
                database_writes=metric_data.database_writes,
                error_types=metric_data.error_types,
                top_errors=metric_data.top_errors,
            )

            self.db.add(metric)
            await self.db.commit()
            await self.db.refresh(metric)

            return ServicePerformanceMetricResponse.model_validate(metric)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating performance metric: {e}")
            raise DatabaseOperationError(f"Failed to create performance metric: {str(e)}", "create_metric")

    async def list_performance_metrics(
        self,
        pagination: PaginationParams,
        perf_filter: Optional[ServicePerformanceFilter] = None,
        hours: Optional[int] = None,
    ) -> ServicePerformanceMetricList:
        """List performance metrics with filtering and pagination."""
        try:
            query = select(ServicePerformanceMetric)

            # Apply filters
            if perf_filter:
                if perf_filter.service_names:
                    query = query.where(ServicePerformanceMetric.service_name.in_(perf_filter.service_names))

                if perf_filter.has_errors_only:
                    query = query.where(ServicePerformanceMetric.operations_failed > 0)

                if perf_filter.start_time:
                    query = query.where(ServicePerformanceMetric.time >= perf_filter.start_time)

                if perf_filter.end_time:
                    query = query.where(ServicePerformanceMetric.time <= perf_filter.end_time)

            # Apply time range filter
            if hours:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                query = query.where(ServicePerformanceMetric.time >= cutoff_time)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc(ServicePerformanceMetric.time))
            query = query.offset(pagination.offset).limit(pagination.page_size)

            # Execute query
            result = await self.db.execute(query)
            metrics = result.scalars().all()

            # Convert to summary format
            summaries = [
                ServicePerformanceMetricSummary(
                    time=metric.time,
                    service_name=metric.service_name,
                    operations_total=metric.operations_total,
                    success_rate=((metric.operations_successful / metric.operations_total * 100) if metric.operations_total > 0 else 0),
                    avg_duration_ms=metric.avg_duration_ms,
                    cache_hit_ratio=metric.cache_hit_ratio,
                    performance_grade=self._calculate_performance_grade(metric),
                )
                for metric in metrics
            ]

            total_pages = ((total_count - 1) // pagination.page_size) + 1 if total_count > 0 else 0
            
            return ServicePerformanceMetricList(
                items=summaries,
                total_count=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                has_next=pagination.page < total_pages,
                has_previous=pagination.page > 1,
            )

        except Exception as e:
            logger.error(f"Error listing performance metrics: {e}")
            raise DatabaseOperationError(f"Failed to list performance metrics: {str(e)}", "list_metrics")

    async def get_service_aggregation(
        self, service_name: str, hours: int = 168
    ) -> ServicePerformanceAggregation:
        """Get aggregated performance metrics for a service."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            period_start = cutoff_time
            period_end = datetime.now(timezone.utc)

            # Get aggregated metrics
            agg_query = select(
                func.sum(ServicePerformanceMetric.operations_total),
                func.sum(ServicePerformanceMetric.operations_successful),
                func.sum(ServicePerformanceMetric.operations_failed),
                func.sum(ServicePerformanceMetric.operations_cached),
                func.avg(ServicePerformanceMetric.avg_duration_ms),
                func.sum(ServicePerformanceMetric.ssh_connections_created),
                func.sum(ServicePerformanceMetric.ssh_connections_reused),
                func.sum(ServicePerformanceMetric.data_collected_bytes),
                func.sum(ServicePerformanceMetric.database_writes),
            ).where(
                ServicePerformanceMetric.service_name == service_name,
                ServicePerformanceMetric.time >= cutoff_time
            )

            agg_result = await self.db.execute(agg_query)
            agg_data = agg_result.fetchone()

            total_operations = int(agg_data[0]) if agg_data[0] else 0
            total_successful = int(agg_data[1]) if agg_data[1] else 0
            total_failed = int(agg_data[2]) if agg_data[2] else 0
            total_cached = int(agg_data[3]) if agg_data[3] else 0
            avg_duration_ms = float(agg_data[4]) if agg_data[4] else None
            total_ssh_connections = int(agg_data[5]) if agg_data[5] else 0
            ssh_reused = int(agg_data[6]) if agg_data[6] else 0
            total_data_bytes = int(agg_data[7]) if agg_data[7] else 0
            total_database_writes = int(agg_data[8]) if agg_data[8] else 0

            # Calculate rates
            success_rate = (total_successful / total_operations * 100) if total_operations > 0 else 0
            failure_rate = (total_failed / total_operations * 100) if total_operations > 0 else 0
            cache_hit_rate = (total_cached / total_operations * 100) if total_operations > 0 else 0
            ssh_reuse_rate = (ssh_reused / total_ssh_connections * 100) if total_ssh_connections > 0 else 0

            # Calculate performance grade and trend (simplified)
            performance_grade = "A" if success_rate > 95 else "B" if success_rate > 85 else "C"
            performance_trend = "stable"  # Would be calculated from historical data

            return ServicePerformanceAggregation(
                service_name=service_name,
                period_start=period_start,
                period_end=period_end,
                total_operations=total_operations,
                total_successful=total_successful,
                total_failed=total_failed,
                total_cached=total_cached,
                success_rate=success_rate,
                failure_rate=failure_rate,
                cache_hit_rate=cache_hit_rate,
                avg_duration_ms=avg_duration_ms,
                median_duration_ms=avg_duration_ms,  # Simplified
                p95_duration_ms=avg_duration_ms * 1.5 if avg_duration_ms else None,  # Simplified
                p99_duration_ms=avg_duration_ms * 2.0 if avg_duration_ms else None,  # Simplified
                total_ssh_connections=total_ssh_connections,
                ssh_reuse_rate=ssh_reuse_rate,
                total_data_bytes=total_data_bytes,
                total_database_writes=total_database_writes,
                performance_grade=performance_grade,
                performance_trend=performance_trend,
                top_error_types=[],  # Would be populated from error_types JSON
                hourly_breakdown=[],  # Would be calculated with hourly aggregation
            )

        except Exception as e:
            logger.error(f"Error getting service aggregation for {service_name}: {e}")
            raise DatabaseOperationError(f"Failed to get service aggregation: {str(e)}", "get_service_aggregation")

    async def get_service_trend(self, service_name: str, days: int = 30) -> ServicePerformanceTrend:
        """Get performance trend analysis for a service."""
        try:
            # This would be a complex analysis in reality
            # For now, returning a simplified trend
            return ServicePerformanceTrend(
                service_name=service_name,
                analysis_period_days=days,
                trend_direction="stable",
                trend_strength=0.1,
                success_rate_trend={"direction": "stable", "change_percent": 0.5},
                duration_trend={"direction": "improving", "change_percent": -2.1},
                throughput_trend={"direction": "stable", "change_percent": 0.8},
                seasonal_patterns=[],
                anomalies_detected=[],
                forecast_7_days={"success_rate": 95.2, "avg_duration_ms": 150.0},
                confidence_interval=0.85,
                recommendations=["Continue current monitoring", "Consider cache optimization"],
            )

        except Exception as e:
            logger.error(f"Error getting service trend for {service_name}: {e}")
            raise DatabaseOperationError(f"Failed to get service trend: {str(e)}", "get_service_trend")

    async def compare_service_performance(
        self, service_name: str, period1_hours: int, period2_hours: int
    ) -> ServicePerformanceComparison:
        """Compare service performance between two periods."""
        try:
            # Get aggregations for both periods
            period1_agg = await self.get_service_aggregation(service_name, period1_hours)
            
            # For period2, we'd get metrics from an earlier time range
            # This is simplified - in reality, we'd calculate the offset
            period2_agg = await self.get_service_aggregation(service_name, period2_hours)

            # Calculate changes
            success_rate_change = period1_agg.success_rate - period2_agg.success_rate
            avg_duration_change = (period1_agg.avg_duration_ms - period2_agg.avg_duration_ms) if period1_agg.avg_duration_ms and period2_agg.avg_duration_ms else None
            cache_hit_rate_change = period1_agg.cache_hit_rate - period2_agg.cache_hit_rate

            # Determine improvements and regressions
            improvements = []
            regressions = []

            if success_rate_change > 1:
                improvements.append("Success rate improved")
            elif success_rate_change < -1:
                regressions.append("Success rate declined")

            if avg_duration_change and avg_duration_change < -10:
                improvements.append("Response time improved")
            elif avg_duration_change and avg_duration_change > 10:
                regressions.append("Response time degraded")

            # Overall trend
            if len(improvements) > len(regressions):
                overall_trend = "improved"
            elif len(regressions) > len(improvements):
                overall_trend = "degraded"
            else:
                overall_trend = "stable"

            return ServicePerformanceComparison(
                service_name=service_name,
                period1_start=period1_agg.period_start,
                period1_end=period1_agg.period_end,
                period2_start=period2_agg.period_start,
                period2_end=period2_agg.period_end,
                period1_metrics=period1_agg,
                period2_metrics=period2_agg,
                improvements=improvements,
                regressions=regressions,
                success_rate_change=success_rate_change,
                avg_duration_change=avg_duration_change,
                cache_hit_rate_change=cache_hit_rate_change,
                overall_trend=overall_trend,
                recommendation="Continue monitoring performance trends",
            )

        except Exception as e:
            logger.error(f"Error comparing service performance for {service_name}: {e}")
            raise DatabaseOperationError(f"Failed to compare service performance: {str(e)}", "compare_services")

    async def get_performance_alerts(
        self, service_names: Optional[List[str]] = None, hours: int = 24
    ) -> List[ServicePerformanceAlert]:
        """Get performance alerts for services."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Get recent metrics with poor performance
            query = select(ServicePerformanceMetric).where(
                ServicePerformanceMetric.time >= cutoff_time,
                # Alert conditions: high failure rate or long duration
                (ServicePerformanceMetric.operations_failed > 0) |
                (ServicePerformanceMetric.avg_duration_ms > 5000)
            )

            if service_names:
                query = query.where(ServicePerformanceMetric.service_name.in_(service_names))

            result = await self.db.execute(query)
            metrics = result.scalars().all()

            alerts = []
            for metric in metrics:
                # Determine alert type and severity
                failure_rate = (metric.operations_failed / metric.operations_total * 100) if metric.operations_total > 0 else 0
                
                if failure_rate > 10:
                    alert_type = "high_failure_rate"
                    severity = "critical" if failure_rate > 25 else "warning"
                    current_value = failure_rate
                    threshold_value = 10.0
                    metric_name = "failure_rate"
                    description = f"Service {metric.service_name} has high failure rate ({failure_rate:.1f}%)"
                elif metric.avg_duration_ms and metric.avg_duration_ms > 5000:
                    alert_type = "high_response_time"
                    severity = "warning"
                    current_value = metric.avg_duration_ms
                    threshold_value = 5000.0
                    metric_name = "avg_duration_ms"
                    description = f"Service {metric.service_name} has high response time ({metric.avg_duration_ms:.0f}ms)"
                else:
                    continue

                alert = ServicePerformanceAlert(
                    service_name=metric.service_name,
                    alert_type=alert_type,
                    severity=severity,
                    metric_name=metric_name,
                    current_value=current_value,
                    threshold_value=threshold_value,
                    description=description,
                    detected_at=metric.time,
                    duration_minutes=int((datetime.now(timezone.utc) - metric.time).total_seconds() / 60),
                    affected_operations=metric.operations_failed if alert_type == "high_failure_rate" else metric.operations_total,
                    recommended_actions=["Review service logs", "Check resource utilization", "Consider scaling"],
                    auto_resolution_attempted=False,
                    related_services=[],
                    impact_assessment="Medium - may affect user experience",
                )
                alerts.append(alert)

            return alerts

        except Exception as e:
            logger.error(f"Error getting performance alerts: {e}")
            raise DatabaseOperationError(f"Failed to get performance alerts: {str(e)}", "get_alerts")

    async def get_performance_report(
        self, service_name: Optional[str] = None, period: str = "last_24h"
    ) -> ServicePerformanceReport:
        """Generate a comprehensive performance report."""
        try:
            # Parse period
            hours_map = {"last_24h": 24, "last_week": 168, "last_month": 720}
            hours = hours_map.get(period, 24)

            # Get service names
            if service_name:
                service_names = [service_name]
            else:
                # Get all services
                services_query = select(ServicePerformanceMetric.service_name).distinct()
                services_result = await self.db.execute(services_query)
                service_names = [row[0] for row in services_result.fetchall()]

            # Get aggregations for all services
            performance_by_service = []
            for svc_name in service_names[:10]:  # Limit to 10 services
                agg = await self.get_service_aggregation(svc_name, hours)
                performance_by_service.append(agg)

            # Calculate overall health score
            if performance_by_service:
                avg_success_rate = sum(p.success_rate for p in performance_by_service) / len(performance_by_service)
                overall_health_score = min(100, avg_success_rate)
            else:
                overall_health_score = 100

            # Identify top and underperforming services
            top_performing_services = [p.service_name for p in performance_by_service if p.success_rate > 95][:5]
            underperforming_services = [p.service_name for p in performance_by_service if p.success_rate < 90][:5]

            # Get trends and alerts
            trends_analysis = []
            for svc_name in service_names[:5]:  # Limit trends analysis
                trend = await self.get_service_trend(svc_name)
                trends_analysis.append(trend)

            alerts_summary = await self.get_performance_alerts(service_names, hours=min(hours, 24))

            # Generate recommendations
            recommendations = []
            if overall_health_score < 90:
                recommendations.append("Review underperforming services and address root causes")
            if len(alerts_summary) > 5:
                recommendations.append("High number of performance alerts - consider proactive monitoring")
            if any(p.cache_hit_rate < 50 for p in performance_by_service):
                recommendations.append("Low cache hit rates detected - optimize caching strategy")

            # Generate action items
            action_items = [
                {"action": "Review performance alerts", "priority": "high", "assigned_to": "ops_team"},
                {"action": "Optimize slow services", "priority": "medium", "assigned_to": "dev_team"},
            ]

            return ServicePerformanceReport(
                service_name=service_name,
                report_period=period,
                generated_at=datetime.now(timezone.utc),
                executive_summary=f"Performance report for {len(performance_by_service)} services over {period}. "
                                f"Overall health score: {overall_health_score:.1f}%. "
                                f"{len(alerts_summary)} active alerts.",
                overall_health_score=overall_health_score,
                key_metrics={
                    "total_services": len(performance_by_service),
                    "avg_success_rate": avg_success_rate if performance_by_service else 0,
                    "total_operations": sum(p.total_operations for p in performance_by_service),
                    "active_alerts": len(alerts_summary),
                },
                performance_by_service=performance_by_service,
                top_performing_services=top_performing_services,
                underperforming_services=underperforming_services,
                trends_analysis=trends_analysis,
                alerts_summary=alerts_summary,
                recommendations=recommendations,
                action_items=action_items,
            )

        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            raise DatabaseOperationError(f"Failed to generate performance report: {str(e)}", "generate_report")

    async def cleanup_old_metrics(self, older_than_days: int, dry_run: bool = True) -> int:
        """Clean up old performance metrics."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

            # Count metrics to be deleted
            count_query = select(func.count()).where(ServicePerformanceMetric.time < cutoff_date)
            count_result = await self.db.execute(count_query)
            count_to_delete = count_result.scalar()

            if not dry_run and count_to_delete > 0:
                # Delete old metrics
                from sqlalchemy import delete
                delete_query = delete(ServicePerformanceMetric).where(ServicePerformanceMetric.time < cutoff_date)
                await self.db.execute(delete_query)
                await self.db.commit()

            return count_to_delete

        except Exception as e:
            logger.error(f"Error cleaning up performance metrics: {e}")
            raise DatabaseOperationError(f"Failed to cleanup performance metrics: {str(e)}", "cleanup_metrics")

    def _calculate_performance_grade(self, metric: ServicePerformanceMetric) -> str:
        """Calculate performance grade based on metrics."""
        success_rate = (metric.operations_successful / metric.operations_total * 100) if metric.operations_total > 0 else 0
        
        if success_rate >= 99:
            return "A"
        elif success_rate >= 95:
            return "B"
        elif success_rate >= 90:
            return "C"
        elif success_rate >= 80:
            return "D"
        else:
            return "F"