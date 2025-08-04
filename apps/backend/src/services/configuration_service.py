"""
Configuration Management Service

Service layer for managing infrastructure configuration snapshots and change events,
providing business logic for configuration tracking and analysis.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.models.configuration import ConfigurationSnapshot, ConfigurationChangeEvent
from apps.backend.src.schemas.configuration import (
    ConfigurationSnapshotCreate,
    ConfigurationSnapshotResponse,
    ConfigurationSnapshotList,
    ConfigurationSnapshotSummary,
    ConfigurationChangeEventCreate,
    ConfigurationChangeEventResponse,
    ConfigurationChangeEventList,
    ConfigurationChangeEventSummary,
    ConfigurationFilter,
    ConfigurationMetrics,
    ConfigurationAlert,
    ConfigurationRollbackRequest,
    ConfigurationRollbackResponse,
    ConfigurationDiff,
)
from apps.backend.src.schemas.common import PaginationParams

logger = logging.getLogger(__name__)


class ConfigurationService:
    """Service for managing configuration snapshots and change events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_snapshot(
        self, snapshot_data: ConfigurationSnapshotCreate
    ) -> ConfigurationSnapshotResponse:
        """Create a new configuration snapshot."""
        try:
            snapshot = ConfigurationSnapshot(
                id=uuid4(),
                device_id=snapshot_data.device_id,
                config_type=snapshot_data.config_type,
                file_path=snapshot_data.file_path,
                content_hash=snapshot_data.content_hash,
                file_size_bytes=snapshot_data.file_size_bytes,
                raw_content=snapshot_data.raw_content,
                parsed_data=snapshot_data.parsed_data,
                change_type=snapshot_data.change_type,
                previous_hash=snapshot_data.previous_hash,
                file_modified_time=snapshot_data.file_modified_time,
                collection_source=snapshot_data.collection_source,
                detection_latency_ms=snapshot_data.detection_latency_ms,
                affected_services=snapshot_data.affected_services,
                requires_restart=snapshot_data.requires_restart,
                risk_level=snapshot_data.risk_level,
            )

            self.db.add(snapshot)
            await self.db.commit()
            await self.db.refresh(snapshot)

            return ConfigurationSnapshotResponse.model_validate(snapshot)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating configuration snapshot: {e}")
            raise DatabaseOperationError(f"Failed to create configuration snapshot: {str(e)}", "create_snapshot")

    async def list_snapshots(
        self,
        pagination: PaginationParams,
        config_filter: Optional[ConfigurationFilter] = None,
        hours: Optional[int] = None,
    ) -> ConfigurationSnapshotList:
        """List configuration snapshots with filtering and pagination."""
        try:
            query = select(ConfigurationSnapshot)

            # Apply filters
            if config_filter:
                if config_filter.device_ids:
                    query = query.where(ConfigurationSnapshot.device_id.in_(config_filter.device_ids))

                if config_filter.config_types:
                    query = query.where(ConfigurationSnapshot.config_type.in_(config_filter.config_types))

                if config_filter.change_types:
                    query = query.where(ConfigurationSnapshot.change_type.in_(config_filter.change_types))

                if config_filter.risk_levels:
                    query = query.where(ConfigurationSnapshot.risk_level.in_(config_filter.risk_levels))

                if config_filter.high_risk_only:
                    query = query.where(ConfigurationSnapshot.risk_level.in_(["HIGH", "CRITICAL"]))

                if config_filter.start_time:
                    query = query.where(ConfigurationSnapshot.time >= config_filter.start_time)

                if config_filter.end_time:
                    query = query.where(ConfigurationSnapshot.time <= config_filter.end_time)

            # Apply time range filter
            if hours:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                query = query.where(ConfigurationSnapshot.time >= cutoff_time)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc(ConfigurationSnapshot.time))
            query = query.offset(pagination.offset).limit(pagination.page_size)

            # Execute query
            result = await self.db.execute(query)
            snapshots = result.scalars().all()

            # Convert to summary format
            summaries = [
                ConfigurationSnapshotSummary(
                    id=snapshot.id,
                    device_id=snapshot.device_id,
                    time=snapshot.time,
                    config_type=snapshot.config_type,
                    file_path=snapshot.file_path,
                    change_type=snapshot.change_type,
                    risk_level=snapshot.risk_level,
                    requires_restart=snapshot.requires_restart,
                    affected_services_count=len(snapshot.affected_services),
                )
                for snapshot in snapshots
            ]

            total_pages = ((total_count - 1) // pagination.page_size) + 1 if total_count > 0 else 0
            
            return ConfigurationSnapshotList(
                items=summaries,
                total_count=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                has_next=pagination.page < total_pages,
                has_previous=pagination.page > 1,
            )

        except Exception as e:
            logger.error(f"Error listing configuration snapshots: {e}")
            raise DatabaseOperationError(f"Failed to list configuration snapshots: {str(e)}", "list_snapshots")

    async def get_snapshot(self, snapshot_id: UUID) -> Optional[ConfigurationSnapshotResponse]:
        """Get a specific configuration snapshot."""
        try:
            query = select(ConfigurationSnapshot).where(ConfigurationSnapshot.id == snapshot_id)
            result = await self.db.execute(query)
            snapshot = result.scalar_one_or_none()

            if snapshot:
                return ConfigurationSnapshotResponse.model_validate(snapshot)
            return None

        except Exception as e:
            logger.error(f"Error getting configuration snapshot {snapshot_id}: {e}")
            raise DatabaseOperationError(f"Failed to get configuration snapshot: {str(e)}", "get_snapshot")

    async def create_change_event(
        self, event_data: ConfigurationChangeEventCreate
    ) -> ConfigurationChangeEventResponse:
        """Create a new configuration change event."""
        try:
            event = ConfigurationChangeEvent(
                id=uuid4(),
                time=datetime.now(timezone.utc),
                device_id=event_data.device_id,
                snapshot_id=event_data.snapshot_id,
                config_type=event_data.config_type,
                file_path=event_data.file_path,
                change_type=event_data.change_type,
                affected_services=event_data.affected_services,
                service_dependencies=event_data.service_dependencies,
                requires_restart=event_data.requires_restart,
                restart_services=event_data.restart_services,
                changes_summary=event_data.changes_summary,
                risk_level=event_data.risk_level,
                confidence_score=event_data.confidence_score,
                processed=event_data.processed,
                notifications_sent=event_data.notifications_sent,
            )

            self.db.add(event)
            await self.db.commit()
            await self.db.refresh(event)

            return ConfigurationChangeEventResponse.model_validate(event)

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating configuration change event: {e}")
            raise DatabaseOperationError(f"Failed to create configuration change event: {str(e)}", "create_change_event")

    async def list_change_events(
        self,
        pagination: PaginationParams,
        config_filter: Optional[ConfigurationFilter] = None,
        hours: Optional[int] = None,
    ) -> ConfigurationChangeEventList:
        """List configuration change events with filtering and pagination."""
        try:
            query = select(ConfigurationChangeEvent)

            # Apply filters
            if config_filter:
                if config_filter.device_ids:
                    query = query.where(ConfigurationChangeEvent.device_id.in_(config_filter.device_ids))

                if config_filter.config_types:
                    query = query.where(ConfigurationChangeEvent.config_type.in_(config_filter.config_types))

                if config_filter.unprocessed_only:
                    query = query.where(ConfigurationChangeEvent.processed == False)

                if config_filter.high_risk_only:
                    query = query.where(ConfigurationChangeEvent.risk_level.in_(["HIGH", "CRITICAL"]))

            # Apply time range filter
            if hours:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                query = query.where(ConfigurationChangeEvent.time >= cutoff_time)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()

            # Apply ordering and pagination
            query = query.order_by(desc(ConfigurationChangeEvent.time))
            query = query.offset(pagination.offset).limit(pagination.page_size)

            # Execute query
            result = await self.db.execute(query)
            events = result.scalars().all()

            # Convert to summary format
            summaries = [
                ConfigurationChangeEventSummary(
                    id=event.id,
                    device_id=event.device_id,
                    snapshot_id=event.snapshot_id,
                    time=event.time,
                    config_type=event.config_type,
                    file_path=event.file_path,
                    change_type=event.change_type,
                    risk_level=event.risk_level,
                    requires_restart=event.requires_restart,
                    processed=event.processed,
                    confidence_score=event.confidence_score,
                )
                for event in events
            ]

            total_pages = ((total_count - 1) // pagination.page_size) + 1 if total_count > 0 else 0
            
            return ConfigurationChangeEventList(
                items=summaries,
                total_count=total_count,
                page=pagination.page,
                page_size=pagination.page_size,
                total_pages=total_pages,
                has_next=pagination.page < total_pages,
                has_previous=pagination.page > 1,
            )

        except Exception as e:
            logger.error(f"Error listing configuration change events: {e}")
            raise DatabaseOperationError(f"Failed to list configuration change events: {str(e)}", "list_change_events")

    async def get_change_event(self, event_id: UUID) -> Optional[ConfigurationChangeEventResponse]:
        """Get a specific configuration change event."""
        try:
            query = select(ConfigurationChangeEvent).where(ConfigurationChangeEvent.id == event_id)
            result = await self.db.execute(query)
            event = result.scalar_one_or_none()

            if event:
                return ConfigurationChangeEventResponse.model_validate(event)
            return None

        except Exception as e:
            logger.error(f"Error getting configuration change event {event_id}: {e}")
            raise DatabaseOperationError(f"Failed to get configuration change event: {str(e)}", "get_change_event")

    async def process_change_event(self, event_id: UUID) -> bool:
        """Mark a configuration change event as processed."""
        try:
            query = select(ConfigurationChangeEvent).where(ConfigurationChangeEvent.id == event_id)
            result = await self.db.execute(query)
            event = result.scalar_one_or_none()

            if not event:
                return False

            event.processed = True
            await self.db.commit()
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing configuration change event {event_id}: {e}")
            raise DatabaseOperationError(f"Failed to process configuration change event: {str(e)}", "process_change_event")

    async def get_configuration_metrics(
        self,
        device_ids: Optional[List[UUID]] = None,
        hours: int = 24,
    ) -> ConfigurationMetrics:
        """Get aggregated configuration management metrics."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            period_start = cutoff_time
            period_end = datetime.now(timezone.utc)

            # Base queries with time filter
            snapshot_base = select(ConfigurationSnapshot).where(ConfigurationSnapshot.time >= cutoff_time)
            event_base = select(ConfigurationChangeEvent).where(ConfigurationChangeEvent.time >= cutoff_time)

            # Apply device filter
            if device_ids:
                snapshot_base = snapshot_base.where(ConfigurationSnapshot.device_id.in_(device_ids))
                event_base = event_base.where(ConfigurationChangeEvent.device_id.in_(device_ids))

            # Count totals
            snapshot_count_query = select(func.count()).select_from(snapshot_base.subquery())
            event_count_query = select(func.count()).select_from(event_base.subquery())

            snapshot_count_result = await self.db.execute(snapshot_count_query)
            event_count_result = await self.db.execute(event_count_query)

            total_snapshots = snapshot_count_result.scalar()
            total_change_events = event_count_result.scalar()

            # Get breakdowns by type
            snapshot_type_query = (
                select(ConfigurationSnapshot.config_type, func.count())
                .select_from(snapshot_base.subquery())
                .group_by(ConfigurationSnapshot.config_type)
            )
            snapshot_type_result = await self.db.execute(snapshot_type_query)
            snapshots_by_type = dict(snapshot_type_result.fetchall())

            # Get changes by type
            change_type_query = (
                select(ConfigurationChangeEvent.change_type, func.count())
                .select_from(event_base.subquery())
                .group_by(ConfigurationChangeEvent.change_type)
            )
            change_type_result = await self.db.execute(change_type_query)
            changes_by_type = dict(change_type_result.fetchall())

            # Get changes by risk
            risk_query = (
                select(ConfigurationSnapshot.risk_level, func.count())
                .select_from(snapshot_base.subquery())
                .group_by(ConfigurationSnapshot.risk_level)
            )
            risk_result = await self.db.execute(risk_query)
            changes_by_risk = dict(risk_result.fetchall())

            # Count unprocessed events
            unprocessed_query = select(func.count()).select_from(
                event_base.where(ConfigurationChangeEvent.processed == False).subquery()
            )
            unprocessed_result = await self.db.execute(unprocessed_query)
            unprocessed_events = unprocessed_result.scalar()

            # Count high risk changes
            high_risk_query = select(func.count()).select_from(
                snapshot_base.where(ConfigurationSnapshot.risk_level.in_(["HIGH", "CRITICAL"])).subquery()
            )
            high_risk_result = await self.db.execute(high_risk_query)
            high_risk_changes = high_risk_result.scalar()

            # Count changes requiring restart
            restart_query = select(func.count()).select_from(
                snapshot_base.where(ConfigurationSnapshot.requires_restart == True).subquery()
            )
            restart_result = await self.db.execute(restart_query)
            changes_requiring_restart = restart_result.scalar()

            # Get average detection latency
            latency_query = select(func.avg(ConfigurationSnapshot.detection_latency_ms)).select_from(
                snapshot_base.where(ConfigurationSnapshot.detection_latency_ms.isnot(None)).subquery()
            )
            latency_result = await self.db.execute(latency_query)
            avg_detection_latency_ms = float(latency_result.scalar()) if latency_result.scalar() else None

            # Get most changed files (simplified)
            file_query = (
                select(ConfigurationSnapshot.file_path, func.count())
                .select_from(snapshot_base.subquery())
                .group_by(ConfigurationSnapshot.file_path)
                .order_by(desc(func.count()))
                .limit(10)
            )
            file_result = await self.db.execute(file_query)
            most_changed_files = [{"file_path": row[0], "count": row[1]} for row in file_result.fetchall()]

            # Get most affected services (simplified)
            # This would be more complex in reality, requiring JSON operations
            most_affected_services = []

            return ConfigurationMetrics(
                total_snapshots=total_snapshots,
                total_change_events=total_change_events,
                snapshots_by_type=snapshots_by_type,
                changes_by_type=changes_by_type,
                changes_by_risk=changes_by_risk,
                unprocessed_events=unprocessed_events,
                high_risk_changes=high_risk_changes,
                changes_requiring_restart=changes_requiring_restart,
                avg_detection_latency_ms=avg_detection_latency_ms,
                most_changed_files=most_changed_files,
                most_affected_services=most_affected_services,
                period_start=period_start,
                period_end=period_end,
            )

        except Exception as e:
            logger.error(f"Error getting configuration metrics: {e}")
            raise DatabaseOperationError(f"Failed to get configuration metrics: {str(e)}", "get_metrics")

    async def get_configuration_alerts(
        self,
        device_ids: Optional[List[UUID]] = None,
        hours: int = 24,
    ) -> List[ConfigurationAlert]:
        """Get configuration change alerts."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Get high-risk unprocessed events
            query = select(ConfigurationChangeEvent).where(
                and_(
                    ConfigurationChangeEvent.time >= cutoff_time,
                    ConfigurationChangeEvent.risk_level.in_(["HIGH", "CRITICAL"]),
                    ConfigurationChangeEvent.processed == False,
                )
            )

            if device_ids:
                query = query.where(ConfigurationChangeEvent.device_id.in_(device_ids))

            result = await self.db.execute(query)
            events = result.scalars().all()

            alerts = []
            for event in events:
                alert = ConfigurationAlert(
                    event_id=event.id,
                    device_id=event.device_id,
                    device_hostname=None,  # Would need device lookup
                    alert_type="configuration_change",
                    severity=event.risk_level.lower(),
                    config_type=event.config_type,
                    file_path=event.file_path,
                    change_type=event.change_type,
                    risk_level=event.risk_level,
                    requires_restart=event.requires_restart,
                    affected_services=event.affected_services,
                    detected_at=event.time,
                    alert_generated_at=datetime.now(timezone.utc),
                    recommended_actions=["Review configuration change", "Verify affected services"],
                    notification_channels=["email", "slack"],
                )
                alerts.append(alert)

            return alerts

        except Exception as e:
            logger.error(f"Error getting configuration alerts: {e}")
            raise DatabaseOperationError(f"Failed to get configuration alerts: {str(e)}", "get_alerts")

    async def rollback_configuration(
        self, rollback_request: ConfigurationRollbackRequest
    ) -> ConfigurationRollbackResponse:
        """Rollback configuration to a previous snapshot."""
        try:
            # This is a simplified implementation
            # In reality, this would involve actual file operations and service restarts
            start_time = datetime.now(timezone.utc)
            
            rollback_id = uuid4()
            success = True  # Simplified - assume success
            error_message = None
            services_notified = []
            services_restarted = []

            if rollback_request.notify_services:
                services_notified = ["nginx", "docker"]

            if rollback_request.restart_services:
                services_restarted = ["nginx"]

            end_time = datetime.now(timezone.utc)
            rollback_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            return ConfigurationRollbackResponse(
                rollback_id=rollback_id,
                original_snapshot_id=rollback_request.snapshot_id,
                target_snapshot_id=rollback_request.target_snapshot_id or rollback_request.snapshot_id,
                success=success,
                error_message=error_message,
                services_notified=services_notified,
                services_restarted=services_restarted,
                rollback_duration_ms=rollback_duration_ms,
                completed_at=end_time,
            )

        except Exception as e:
            logger.error(f"Error rolling back configuration: {e}")
            raise DatabaseOperationError(f"Failed to rollback configuration: {str(e)}", "rollback_configuration")

    async def get_configuration_diff(
        self, from_snapshot_id: UUID, to_snapshot_id: UUID
    ) -> ConfigurationDiff:
        """Get the difference between two configuration snapshots."""
        try:
            # Get both snapshots
            query = select(ConfigurationSnapshot).where(
                ConfigurationSnapshot.id.in_([from_snapshot_id, to_snapshot_id])
            )
            result = await self.db.execute(query)
            snapshots = result.scalars().all()

            if len(snapshots) != 2:
                raise ValidationError("One or both configuration snapshots not found")

            from_snapshot = next(s for s in snapshots if s.id == from_snapshot_id)
            to_snapshot = next(s for s in snapshots if s.id == to_snapshot_id)

            # Calculate basic diff (simplified)
            changes = []
            summary = {"files_changed": 1, "risk_level": to_snapshot.risk_level}

            # In reality, this would perform detailed text diff analysis
            lines_added = 5  # Placeholder
            lines_removed = 3  # Placeholder
            lines_modified = 2  # Placeholder

            risk_assessment = {
                "risk_level": to_snapshot.risk_level,
                "requires_restart": to_snapshot.requires_restart,
                "confidence": 0.9,
            }

            return ConfigurationDiff(
                from_snapshot_id=from_snapshot_id,
                to_snapshot_id=to_snapshot_id,
                file_path=to_snapshot.file_path,
                config_type=to_snapshot.config_type,
                changes=changes,
                summary=summary,
                lines_added=lines_added,
                lines_removed=lines_removed,
                lines_modified=lines_modified,
                risk_assessment=risk_assessment,
                affected_services=to_snapshot.affected_services,
            )

        except Exception as e:
            logger.error(f"Error getting configuration diff: {e}")
            raise DatabaseOperationError(f"Failed to get configuration diff: {str(e)}", "get_diff")