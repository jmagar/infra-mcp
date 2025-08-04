"""
Data Collection Audit Service

Service layer for managing data collection audit operations,
providing business logic for audit trail management and analysis.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.models.audit import DataCollectionAudit
from apps.backend.src.schemas.audit import (
    DataCollectionAuditCreate,
    DataCollectionAuditResponse,
    DataCollectionAuditList,
    DataCollectionAuditSummary,
    DataCollectionMetrics,
    DataCollectionPerformanceReport,
    DataCollectionFilter,
    BulkAuditResponse,
)
from apps.backend.src.schemas.common import PaginationParams

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing data collection audit operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_audit_entry(
        self, audit_data: DataCollectionAuditCreate
    ) -> DataCollectionAuditResponse:
        """Create a new audit entry."""
        try:
            # Generate operation_id if not provided
            if not audit_data.operation_id:
                from uuid import uuid4
                audit_data.operation_id = uuid4()

            # Create audit entry
            audit_entry = DataCollectionAudit(
                time=datetime.now(timezone.utc),
                device_id=audit_data.device_id,
                operation_id=audit_data.operation_id,
                data_type=audit_data.data_type,
                collection_method=audit_data.collection_method,
                collection_source=audit_data.collection_source,
                force_refresh=audit_data.force_refresh,
                cache_hit=audit_data.cache_hit,
                duration_ms=audit_data.duration_ms,
                ssh_command_count=audit_data.ssh_command_count,
                data_size_bytes=audit_data.data_size_bytes,
                status=audit_data.status,
                error_message=audit_data.error_message,
                warnings=audit_data.warnings,
                records_created=audit_data.records_created,
                records_updated=audit_data.records_updated,
                freshness_threshold=audit_data.freshness_threshold,
            )

            self.db.add(audit_entry)
            await self.db.commit()
            await self.db.refresh(audit_entry)

            return DataCollectionAuditResponse.model_validate(audit_entry)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating audit entry: {e}")
            raise DatabaseOperationError(f"Failed to create audit entry: {str(e)}", "create_audit_entry")

    async def create_bulk_audit_entries(
        self, audit_entries: List[DataCollectionAuditCreate]
    ) -> BulkAuditResponse:
        """Create multiple audit entries in bulk."""
        total_entries = len(audit_entries)
        successful_entries = 0
        failed_entries = 0
        errors = []
        created_operation_ids = []

        start_time = datetime.now(timezone.utc)

        try:
            for i, audit_data in enumerate(audit_entries):
                try:
                    # Generate operation_id if not provided
                    if not audit_data.operation_id:
                        from uuid import uuid4
                        audit_data.operation_id = uuid4()

                    audit_entry = DataCollectionAudit(
                        time=datetime.now(timezone.utc),
                        device_id=audit_data.device_id,
                        operation_id=audit_data.operation_id,
                        data_type=audit_data.data_type,
                        collection_method=audit_data.collection_method,
                        collection_source=audit_data.collection_source,
                        force_refresh=audit_data.force_refresh,
                        cache_hit=audit_data.cache_hit,
                        duration_ms=audit_data.duration_ms,
                        ssh_command_count=audit_data.ssh_command_count,
                        data_size_bytes=audit_data.data_size_bytes,
                        status=audit_data.status,
                        error_message=audit_data.error_message,
                        warnings=audit_data.warnings,
                        records_created=audit_data.records_created,
                        records_updated=audit_data.records_updated,
                        freshness_threshold=audit_data.freshness_threshold,
                    )

                    self.db.add(audit_entry)
                    successful_entries += 1
                    created_operation_ids.append(audit_data.operation_id)

                except Exception as e:
                    failed_entries += 1
                    errors.append({"index": i, "error": str(e)})
                    logger.error(f"Error creating audit entry {i}: {e}")

            await self.db.commit()

            end_time = datetime.now(timezone.utc)
            processing_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return BulkAuditResponse(
                total_entries=total_entries,
                successful_entries=successful_entries,
                failed_entries=failed_entries,
                errors=errors,
                created_operation_ids=created_operation_ids,
                processing_duration_ms=processing_duration_ms,
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error in bulk audit creation: {e}")
            raise DatabaseOperationError(f"Failed to create bulk audit entries: {str(e)}", "create_bulk_audit_entries")

    async def list_audit_entries(
        self,
        pagination: PaginationParams,
        audit_filter: Optional[DataCollectionFilter] = None,
        hours: Optional[int] = None,
    ) -> DataCollectionAuditList:
        """List audit entries with filtering and pagination."""
        try:
            query = select(DataCollectionAudit)

            # Apply filters
            if audit_filter:
                if audit_filter.device_ids:
                    query = query.where(DataCollectionAudit.device_id.in_(audit_filter.device_ids))

                if audit_filter.data_types:
                    query = query.where(DataCollectionAudit.data_type.in_(audit_filter.data_types))

                if audit_filter.collection_methods:
                    query = query.where(
                        DataCollectionAudit.collection_method.in_(audit_filter.collection_methods)
                    )

                if audit_filter.statuses:
                    query = query.where(DataCollectionAudit.status.in_(audit_filter.statuses))

                if audit_filter.errors_only:
                    query = query.where(DataCollectionAudit.status == "failed")

                if audit_filter.cache_hit_only:
                    query = query.where(DataCollectionAudit.cache_hit == True)

                if audit_filter.start_time:
                    query = query.where(DataCollectionAudit.time >= audit_filter.start_time)

                if audit_filter.end_time:
                    query = query.where(DataCollectionAudit.time <= audit_filter.end_time)

            # Apply time range filter
            if hours:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                query = query.where(DataCollectionAudit.time >= cutoff_time)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc(DataCollectionAudit.time))
            query = query.offset(pagination.offset).limit(pagination.page_size)

            # Execute query
            result = await self.db.execute(query)
            audit_entries = result.scalars().all()

            # Convert to summary format
            summaries = [
                DataCollectionAuditSummary(
                    time=entry.time,
                    device_id=entry.device_id,
                    operation_id=entry.operation_id,
                    data_type=entry.data_type,
                    collection_method=entry.collection_method,
                    status=entry.status,
                    duration_ms=entry.duration_ms,
                    cache_hit=entry.cache_hit,
                    records_created=entry.records_created,
                    records_updated=entry.records_updated,
                )
                for entry in audit_entries
            ]

            total_pages = ((total_count - 1) // pagination.page_size) + 1 if total_count > 0 else 0
            
            return DataCollectionAuditList(
                items=summaries,
                total_count=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                has_next=pagination.page < total_pages,
                has_previous=pagination.page > 1,
            )

        except Exception as e:
            logger.error(f"Error listing audit entries: {e}")
            raise DatabaseOperationError(f"Failed to list audit entries: {str(e)}", "list_audit_entries")

    async def get_audit_metrics(
        self,
        device_ids: Optional[List[UUID]] = None,
        data_types: Optional[List[str]] = None,
        hours: int = 24,
    ) -> DataCollectionMetrics:
        """Get aggregated metrics for audit entries."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            period_start = cutoff_time
            period_end = datetime.now(timezone.utc)

            # Base query with time filter
            base_query = select(DataCollectionAudit).where(DataCollectionAudit.time >= cutoff_time)

            # Apply additional filters
            if device_ids:
                base_query = base_query.where(DataCollectionAudit.device_id.in_(device_ids))
            if data_types:
                base_query = base_query.where(DataCollectionAudit.data_type.in_(data_types))

            # Get total operations
            total_query = select(func.count()).select_from(base_query.subquery())
            total_result = await self.db.execute(total_query)
            total_operations = total_result.scalar()

            # Get operations by status
            status_query = (
                select(DataCollectionAudit.status, func.count())
                .select_from(base_query.subquery())
                .group_by(DataCollectionAudit.status)
            )
            status_result = await self.db.execute(status_query)
            status_counts = dict(status_result.fetchall())

            successful_operations = status_counts.get("success", 0)
            failed_operations = status_counts.get("failed", 0)
            partial_operations = status_counts.get("partial", 0)
            timeout_operations = status_counts.get("timeout", 0)

            # Calculate rates
            success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
            failure_rate = (failed_operations / total_operations * 100) if total_operations > 0 else 0

            # Get cache metrics
            cache_hit_query = (
                select(func.count())
                .select_from(base_query.subquery())
                .where(DataCollectionAudit.cache_hit == True)
            )
            cache_hit_result = await self.db.execute(cache_hit_query)
            cache_hit_count = cache_hit_result.scalar()
            cache_hit_rate = (cache_hit_count / total_operations * 100) if total_operations > 0 else 0

            # Get aggregate metrics
            agg_query = select(
                func.avg(DataCollectionAudit.duration_ms),
                func.sum(DataCollectionAudit.duration_ms),
                func.sum(DataCollectionAudit.ssh_command_count),
                func.sum(DataCollectionAudit.data_size_bytes),
                func.sum(DataCollectionAudit.records_created),
                func.sum(DataCollectionAudit.records_updated),
            ).select_from(base_query.subquery())

            agg_result = await self.db.execute(agg_query)
            agg_data = agg_result.fetchone()

            avg_duration_ms = float(agg_data[0]) if agg_data[0] else None
            total_duration_ms = int(agg_data[1]) if agg_data[1] else 0
            total_ssh_commands = int(agg_data[2]) if agg_data[2] else 0
            total_data_bytes = int(agg_data[3]) if agg_data[3] else 0
            total_records_created = int(agg_data[4]) if agg_data[4] else 0
            total_records_updated = int(agg_data[5]) if agg_data[5] else 0

            # Get top data types
            data_type_query = (
                select(DataCollectionAudit.data_type, func.count())
                .select_from(base_query.subquery())
                .group_by(DataCollectionAudit.data_type)
                .order_by(desc(func.count()))
                .limit(10)
            )
            data_type_result = await self.db.execute(data_type_query)
            top_data_types = [{"data_type": row[0], "count": row[1]} for row in data_type_result.fetchall()]

            # Get top errors (simplified)
            error_query = (
                select(func.substr(DataCollectionAudit.error_message, 1, 100), func.count())
                .select_from(base_query.subquery())
                .where(DataCollectionAudit.error_message.isnot(None))
                .group_by(func.substr(DataCollectionAudit.error_message, 1, 100))
                .order_by(desc(func.count()))
                .limit(5)
            )
            error_result = await self.db.execute(error_query)
            top_errors = [{"error": row[0], "count": row[1]} for row in error_result.fetchall()]

            return DataCollectionMetrics(
                total_operations=total_operations,
                successful_operations=successful_operations,
                failed_operations=failed_operations,
                partial_operations=partial_operations,
                timeout_operations=timeout_operations,
                success_rate=success_rate,
                failure_rate=failure_rate,
                avg_duration_ms=avg_duration_ms,
                total_duration_ms=total_duration_ms,
                cache_hit_count=cache_hit_count,
                cache_hit_rate=cache_hit_rate,
                total_ssh_commands=total_ssh_commands,
                total_data_bytes=total_data_bytes,
                total_records_created=total_records_created,
                total_records_updated=total_records_updated,
                top_data_types=top_data_types,
                top_errors=top_errors,
                period_start=period_start,
                period_end=period_end,
            )

        except Exception as e:
            logger.error(f"Error getting audit metrics: {e}")
            raise DatabaseOperationError(f"Failed to get audit metrics: {str(e)}", "get_audit_metrics")

    async def get_performance_report(
        self, device_id: Optional[UUID] = None, period: str = "last_24h"
    ) -> DataCollectionPerformanceReport:
        """Generate a performance report for data collection operations."""
        try:
            # Parse period
            hours_map = {"last_24h": 24, "last_week": 168, "last_month": 720}
            hours = hours_map.get(period, 24)

            # Get overall metrics
            device_ids = [device_id] if device_id else None
            overall_metrics = await self.get_audit_metrics(device_ids=device_ids, hours=hours)

            # Get device hostname if specific device
            device_hostname = None
            if device_id:
                # This would require joining with device table
                # For now, just use the device_id as hostname
                device_hostname = str(device_id)

            # Create simplified breakdowns (in a real implementation, these would be more detailed)
            by_data_type = [
                {"data_type": item["data_type"], "count": item["count"], "success_rate": 95.0}
                for item in overall_metrics.top_data_types[:5]
            ]

            by_collection_method = [
                {"method": "ssh", "count": overall_metrics.total_operations, "avg_duration": overall_metrics.avg_duration_ms}
            ]

            by_hour = []  # Would be populated with hourly breakdown

            performance_trends = {
                "trend_direction": "stable",
                "success_rate_change": 0.0,
                "duration_change": 0.0,
            }

            recommendations = []
            if overall_metrics.failure_rate > 5:
                recommendations.append("High failure rate detected - review error logs")
            if overall_metrics.cache_hit_rate < 30:
                recommendations.append("Low cache hit rate - consider tuning cache policies")

            return DataCollectionPerformanceReport(
                device_id=device_id,
                device_hostname=device_hostname,
                report_period=period,
                generated_at=datetime.now(timezone.utc),
                overall_metrics=overall_metrics,
                by_data_type=by_data_type,
                by_collection_method=by_collection_method,
                by_hour=by_hour,
                performance_trends=performance_trends,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            raise DatabaseOperationError(f"Failed to generate performance report: {str(e)}", "get_performance_report")

    async def cleanup_old_entries(self, older_than_days: int, dry_run: bool = True) -> int:
        """Clean up old audit entries."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

            # Count entries to be deleted
            count_query = select(func.count()).where(DataCollectionAudit.time < cutoff_date)
            count_result = await self.db.execute(count_query)
            count_to_delete = count_result.scalar()

            if not dry_run and count_to_delete > 0:
                # Delete old entries
                from sqlalchemy import delete
                delete_query = delete(DataCollectionAudit).where(DataCollectionAudit.time < cutoff_date)
                await self.db.execute(delete_query)
                await self.db.commit()

            return count_to_delete

        except Exception as e:
            logger.error(f"Error cleaning up audit entries: {e}")
            raise DatabaseOperationError(f"Failed to cleanup audit entries: {str(e)}", "cleanup_old_entries")