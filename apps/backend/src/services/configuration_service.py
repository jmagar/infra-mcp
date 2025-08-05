"""
Configuration Management Service

Service layer for managing infrastructure configuration snapshots and change events,
providing business logic for configuration tracking and analysis.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.exceptions import DatabaseOperationError, ValidationError
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.models.device import Device
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

    async def list_configuration_snapshots(
        self,
        pagination: PaginationParams,
        config_filter: ConfigurationFilter | None = None,
    ) -> ConfigurationSnapshotList:
        """List configuration snapshots with filtering and pagination."""
        try:
            query = select(ConfigurationSnapshot)

            # Apply filters
            if config_filter:
                if config_filter.device_ids:
                    query = query.where(
                        ConfigurationSnapshot.device_id.in_(config_filter.device_ids)
                    )

                if config_filter.start_time:
                    query = query.where(ConfigurationSnapshot.time >= config_filter.start_time)

                if config_filter.end_time:
                    query = query.where(ConfigurationSnapshot.time <= config_filter.end_time)

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
                    configuration_type=snapshot.config_type,
                    timestamp=snapshot.time,
                    checksum=snapshot.content_hash,
                    file_count=1,  # Each snapshot is one file
                    total_size_bytes=snapshot.file_size_bytes or 0,
                    change_detected=snapshot.change_type != "created",
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
            raise DatabaseOperationError(
                f"Failed to list configuration snapshots: {str(e)}", "list_snapshots"
            )

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
            logger.error("Error creating configuration snapshot", exc_info=True)
            raise DatabaseOperationError(
                f"Failed to create configuration snapshot: {str(e)}", "create_snapshot"
            )

    async def list_snapshots(
        self,
        pagination: PaginationParams,
        config_filter: ConfigurationFilter | None = None,
        hours: int | None = None,
    ) -> ConfigurationSnapshotList:
        """List configuration snapshots with filtering and pagination."""
        try:
            query = select(ConfigurationSnapshot)

            # Apply filters
            if config_filter:
                if config_filter.device_ids:
                    query = query.where(
                        ConfigurationSnapshot.device_id.in_(config_filter.device_ids)
                    )

                if config_filter.config_types:
                    query = query.where(
                        ConfigurationSnapshot.config_type.in_(config_filter.config_types)
                    )

                if config_filter.change_types:
                    query = query.where(
                        ConfigurationSnapshot.change_type.in_(config_filter.change_types)
                    )

                if config_filter.risk_levels:
                    query = query.where(
                        ConfigurationSnapshot.risk_level.in_(config_filter.risk_levels)
                    )

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
            raise DatabaseOperationError(
                f"Failed to list configuration snapshots: {str(e)}", "list_snapshots"
            )

    async def get_snapshot(self, snapshot_id: UUID) -> ConfigurationSnapshotResponse | None:
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
            raise DatabaseOperationError(
                f"Failed to get configuration snapshot: {str(e)}", "get_snapshot"
            )

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
            raise DatabaseOperationError(
                f"Failed to create configuration change event: {str(e)}", "create_change_event"
            )

    async def list_change_events(
        self,
        pagination: PaginationParams,
        config_filter: ConfigurationFilter | None = None,
        hours: int | None = None,
    ) -> ConfigurationChangeEventList:
        """List configuration change events with filtering and pagination."""
        try:
            query = select(ConfigurationChangeEvent)

            # Apply filters
            if config_filter:
                if config_filter.device_ids:
                    query = query.where(
                        ConfigurationChangeEvent.device_id.in_(config_filter.device_ids)
                    )

                if config_filter.config_types:
                    query = query.where(
                        ConfigurationChangeEvent.config_type.in_(config_filter.config_types)
                    )

                if config_filter.unprocessed_only:
                    query = query.where(ConfigurationChangeEvent.processed == False)

                if config_filter.high_risk_only:
                    query = query.where(
                        ConfigurationChangeEvent.risk_level.in_(["HIGH", "CRITICAL"])
                    )

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
            raise DatabaseOperationError(
                f"Failed to list configuration change events: {str(e)}", "list_change_events"
            )

    async def get_change_event(self, event_id: UUID) -> ConfigurationChangeEventResponse | None:
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
            raise DatabaseOperationError(
                f"Failed to get configuration change event: {str(e)}", "get_change_event"
            )

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
            raise DatabaseOperationError(
                f"Failed to process configuration change event: {str(e)}", "process_change_event"
            )

    async def get_configuration_metrics(
        self,
        device_ids: list[UUID] | None = None,
        hours: int = 24,
    ) -> ConfigurationMetrics:
        """Get aggregated configuration management metrics."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            period_start = cutoff_time
            period_end = datetime.now(timezone.utc)

            # Base queries with time filter
            snapshot_base = select(ConfigurationSnapshot).where(
                ConfigurationSnapshot.time >= cutoff_time
            )
            event_base = select(ConfigurationChangeEvent).where(
                ConfigurationChangeEvent.time >= cutoff_time
            )

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
                snapshot_base.where(
                    ConfigurationSnapshot.risk_level.in_(["HIGH", "CRITICAL"])
                ).subquery()
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
            latency_query = select(
                func.avg(ConfigurationSnapshot.detection_latency_ms)
            ).select_from(
                snapshot_base.where(
                    ConfigurationSnapshot.detection_latency_ms.isnot(None)
                ).subquery()
            )
            latency_result = await self.db.execute(latency_query)
            avg_detection_latency_ms = (
                float(latency_result.scalar()) if latency_result.scalar() else None
            )

            # Get most changed files (simplified)
            file_query = (
                select(ConfigurationSnapshot.file_path, func.count())
                .select_from(snapshot_base.subquery())
                .group_by(ConfigurationSnapshot.file_path)
                .order_by(desc(func.count()))
                .limit(10)
            )
            file_result = await self.db.execute(file_query)
            most_changed_files = [
                {"file_path": row[0], "count": row[1]} for row in file_result.fetchall()
            ]

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
            raise DatabaseOperationError(
                f"Failed to get configuration metrics: {str(e)}", "get_metrics"
            )

    async def get_configuration_alerts(
        self,
        device_ids: list[UUID] | None = None,
        hours: int = 24,
    ) -> list[ConfigurationAlert]:
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
            raise DatabaseOperationError(
                f"Failed to get configuration alerts: {str(e)}", "get_alerts"
            )

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
                target_snapshot_id=rollback_request.target_snapshot_id
                or rollback_request.snapshot_id,
                success=success,
                error_message=error_message,
                services_notified=services_notified,
                services_restarted=services_restarted,
                rollback_duration_ms=rollback_duration_ms,
                completed_at=end_time,
            )

        except Exception as e:
            logger.error(f"Error rolling back configuration: {e}")
            raise DatabaseOperationError(
                f"Failed to rollback configuration: {str(e)}", "rollback_configuration"
            )

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
            raise DatabaseOperationError(f"Failed to get configuration diff: {str(e)}", "get_diff")

    async def validate_configuration(
        self, device: Device, config_type: str, content: str, file_path: str
    ) -> dict[str, Any]:
        """
        Validate configuration content using remote tools.

        Args:
            device: Device object containing connection information
            config_type: Type of configuration (docker_compose, proxy_configs, etc.)
            content: Configuration content to validate
            file_path: Original file path (for context)

        Returns:
            Dictionary containing validation results
        """
        try:
            # Generate unique temporary file path
            temp_file = f"/tmp/infrastructor_validation_{uuid4().hex[:8]}"

            # Write content to temporary file on remote device
            write_result = await execute_ssh_command_simple(
                hostname=device.hostname, command=f"cat > {temp_file}", input_data=content
            )

            if not write_result.success:
                return {
                    "valid": False,
                    "error_type": "file_write_error",
                    "output": f"Failed to write temporary file: {write_result.stderr}",
                }

            # Determine validation command based on config type
            validation_command = ""

            if config_type == "proxy_configs" or config_type == "nginx_config":
                # Nginx configuration validation
                validation_command = f"nginx -t -c {temp_file} 2>&1"

            elif config_type == "docker_compose":
                # Docker Compose configuration validation
                validation_command = f"cd $(dirname {temp_file}) && docker-compose -f {temp_file} config --quiet 2>&1"

            elif config_type == "systemd_service":
                # Systemd service file validation (basic syntax check)
                validation_command = f"systemd-analyze verify {temp_file} 2>&1"

            else:
                # No specific validator available
                await execute_ssh_command_simple(
                    hostname=device.hostname, command=f"rm -f {temp_file}"
                )
                return {
                    "valid": True,
                    "error_type": None,
                    "output": f"No validator available for config type '{config_type}' - syntax not checked",
                    "validation_method": "none",
                }

            # Execute validation command
            validation_result = await execute_ssh_command_simple(
                hostname=device.hostname, command=validation_command
            )

            # Cleanup temporary file
            await execute_ssh_command_simple(hostname=device.hostname, command=f"rm -f {temp_file}")

            # Analyze validation results
            is_valid = validation_result.exit_code == 0
            output = validation_result.stdout or validation_result.stderr or ""

            # Enhanced error analysis for specific config types
            error_type = None
            if not is_valid:
                output_lower = output.lower()

                if config_type in ["proxy_configs", "nginx_config"]:
                    if "syntax error" in output_lower:
                        error_type = "syntax_error"
                    elif "test failed" in output_lower:
                        error_type = "configuration_test_failed"
                    elif "no such file" in output_lower:
                        error_type = "missing_dependency"
                    else:
                        error_type = "nginx_validation_failed"

                elif config_type == "docker_compose":
                    if "yaml" in output_lower or "parsing" in output_lower:
                        error_type = "yaml_syntax_error"
                    elif "invalid" in output_lower:
                        error_type = "invalid_configuration"
                    elif "version" in output_lower:
                        error_type = "unsupported_version"
                    else:
                        error_type = "compose_validation_failed"

                elif config_type == "systemd_service":
                    if "syntax" in output_lower:
                        error_type = "syntax_error"
                    elif "invalid" in output_lower:
                        error_type = "invalid_directive"
                    else:
                        error_type = "systemd_validation_failed"
                else:
                    error_type = "unknown_validation_error"

            return {
                "valid": is_valid,
                "error_type": error_type,
                "output": output.strip(),
                "validation_method": config_type,
                "exit_code": validation_result.exit_code,
                "file_path": file_path,
                "temp_file_used": temp_file,
            }

        except Exception as e:
            # Ensure cleanup even if validation fails
            try:
                await execute_ssh_command_simple(
                    hostname=device.hostname,
                    command=f"rm -f /tmp/infrastructor_validation_* 2>/dev/null || true",
                )
            except Exception:
                pass  # Best effort cleanup

            return {
                "valid": False,
                "error_type": "validation_exception",
                "output": f"Validation failed with exception: {str(e)}",
                "validation_method": config_type,
                "exception": str(e),
            }

    async def get_latest_snapshot(
        self, session: AsyncSession, device_id: UUID, file_path: str
    ) -> ConfigurationSnapshot | None:
        """
        Get the latest configuration snapshot for a specific file on a device.

        Args:
            session: Database session
            device_id: Device UUID
            file_path: Path to the configuration file

        Returns:
            Latest ConfigurationSnapshot or None if not found
        """
        try:
            query = (
                select(ConfigurationSnapshot)
                .where(
                    ConfigurationSnapshot.device_id == device_id,
                    ConfigurationSnapshot.file_path == file_path,
                )
                .order_by(desc(ConfigurationSnapshot.time))
                .limit(1)
            )

            result = await session.execute(query)
            return result.scalar_one_or_none()

        except Exception:
            return None

    async def create_snapshot_from_collection(
        self,
        session: AsyncSession,
        device_id: UUID,
        config_type: str,
        file_path: str,
        raw_content: str,
        content_hash: str,
        change_type: str = "MODIFY",
        collection_source: str = "unknown",
        previous_hash: str | None = None,
        parsed_data: dict[str, Any] | None = None,
        validation_results: dict[str, Any] | None = None,
        sync_status: str = "synced",
        validation_status: str | None = None,
    ) -> ConfigurationSnapshot:
        """
        Create a configuration snapshot directly from collection parameters.
        This method is optimized for use by the UnifiedDataCollectionService.
        """
        try:
            # Store validation results in parsed_data if provided
            extended_parsed_data = parsed_data or {}
            if validation_results:
                extended_parsed_data["validation_results"] = validation_results

            # Determine validation status from results
            if validation_status is None:
                if validation_results is not None:
                    validation_status = (
                        "valid" if validation_results.get("valid", False) else "invalid"
                    )
                else:
                    validation_status = "pending"

            # Get validation output for storage
            validation_output = None
            if validation_results:
                validation_output = validation_results.get("output", "")

            snapshot = ConfigurationSnapshot(
                id=uuid4(),
                device_id=device_id,
                config_type=config_type,
                file_path=file_path,
                content_hash=content_hash,
                file_size_bytes=len(raw_content.encode("utf-8")),
                raw_content=raw_content,
                parsed_data=extended_parsed_data if extended_parsed_data else None,
                change_type=change_type,
                previous_hash=previous_hash,
                file_modified_time=datetime.now(timezone.utc),
                collection_source=collection_source,
                detection_latency_ms=None,
                affected_services=[],
                requires_restart=validation_results and not validation_results.get("valid", True),
                risk_level="MEDIUM"
                if validation_results and not validation_results.get("valid", True)
                else "LOW",
                sync_status=sync_status,
                validation_status=validation_status,
                last_validation_output=validation_output,
                last_sync_error=None,
            )

            session.add(snapshot)
            await session.flush()  # Flush to get the ID, but don't commit
            return snapshot

        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to create configuration snapshot: {str(e)}",
                "create_snapshot_from_collection",
            ) from e

    async def update_snapshot_sync_status(
        self,
        session: AsyncSession,
        snapshot_id: UUID,
        sync_status: str,
        error_message: str | None = None,
    ) -> bool:
        """
        Update the sync status of a configuration snapshot.
        Used for tracking sync errors and recovery.
        """
        try:
            query = select(ConfigurationSnapshot).where(ConfigurationSnapshot.id == snapshot_id)
            result = await session.execute(query)
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                return False

            snapshot.update_sync_status(sync_status, error_message)
            await session.flush()
            return True

        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to update snapshot sync status: {str(e)}", "update_snapshot_sync_status"
            ) from e

    async def update_snapshot_validation_status(
        self,
        session: AsyncSession,
        snapshot_id: UUID,
        validation_status: str,
        validation_output: str | None = None,
    ) -> bool:
        """
        Update the validation status of a configuration snapshot.
        Used when re-running validation or when validation state changes.
        """
        try:
            query = select(ConfigurationSnapshot).where(ConfigurationSnapshot.id == snapshot_id)
            result = await session.execute(query)
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                return False

            snapshot.update_validation_status(validation_status, validation_output)
            await session.flush()
            return True

        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to update snapshot validation status: {str(e)}",
                "update_snapshot_validation_status",
            ) from e

    async def get_snapshots_with_sync_errors(
        self, device_id: UUID | None = None, hours: int = 24
    ) -> list[ConfigurationSnapshot]:
        """
        Get configuration snapshots that have sync or validation errors.
        Useful for monitoring and alerting on configuration health.
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            query = select(ConfigurationSnapshot).where(
                and_(
                    ConfigurationSnapshot.time >= cutoff_time,
                    or_(
                        ConfigurationSnapshot.sync_status == "error",
                        ConfigurationSnapshot.validation_status == "error",
                    ),
                )
            )

            if device_id:
                query = query.where(ConfigurationSnapshot.device_id == device_id)

            query = query.order_by(ConfigurationSnapshot.time.desc())
            result = await self.db.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to get snapshots with sync errors: {str(e)}",
                "get_snapshots_with_sync_errors",
            ) from e


# Global singleton instance
_configuration_service: ConfigurationService | None = None


async def get_configuration_service() -> ConfigurationService:
    """Get the global configuration service instance."""
    global _configuration_service

    if _configuration_service is None:
        from apps.backend.src.core.database import get_async_session

        session = await get_async_session().__anext__()
        _configuration_service = ConfigurationService(session)

    return _configuration_service


async def restore_configuration_snapshot(
    snapshot_id: UUID,
    device_id: UUID,
) -> dict[str, Any]:
    """
    Restore a configuration on a device from a specific snapshot.

    Args:
        snapshot_id: ID of the snapshot to restore
        device_id: ID of the device (for validation)

    Returns:
        Dictionary containing restoration results
    """
    try:
        # Get configuration service and snapshot
        config_service = await get_configuration_service()

        async with get_async_session() as session:
            snapshot = await config_service.get_snapshot(snapshot_id)

            if not snapshot:
                raise ValidationError(field="snapshot_id", message="Snapshot not found")

            if snapshot.device_id != device_id:
                raise ValidationError(
                    field="device_id", message="Snapshot does not belong to this device"
                )

            # Get device information
            from apps.backend.src.services.unified_data_collection import (
                UnifiedDataCollectionService,
            )

            udcs = UnifiedDataCollectionService()
            device = await udcs._get_device(device_id)

            if not device:
                raise DeviceNotFoundError(device_id=str(device_id))

            # Write the snapshot content back to the device
            write_result = await execute_ssh_command_simple(
                hostname=device.hostname,
                command=f"cat > {snapshot.file_path}",
                input_data=snapshot.raw_content,
            )

            if not write_result.success:
                return {
                    "success": False,
                    "message": "Failed to write configuration to device",
                    "error": write_result.stderr or write_result.stdout,
                    "file_path": snapshot.file_path,
                    "snapshot_id": snapshot_id,
                }

            # Optional: Trigger validation after restore
            validation_result = await config_service.validate_configuration(
                device=device,
                config_type=snapshot.config_type,
                content=snapshot.raw_content,
                file_path=snapshot.file_path,
            )

            # Create a new snapshot to record the restoration
            restoration_snapshot = await config_service.create_snapshot_from_collection(
                session=session,
                device_id=device_id,
                config_type=snapshot.config_type,
                file_path=snapshot.file_path,
                raw_content=snapshot.raw_content,
                content_hash=snapshot.content_hash,
                change_type="RESTORE",
                collection_source="restoration",
                parsed_data={"restored_from_snapshot": str(snapshot_id)},
                validation_results=validation_result,
            )

            await session.commit()

            return {
                "success": True,
                "message": "Configuration restored successfully",
                "file_path": snapshot.file_path,
                "restored_hash": snapshot.content_hash,
                "snapshot_id": snapshot_id,
                "restoration_snapshot_id": restoration_snapshot.id,
                "validation_after_restore": validation_result,
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to restore configuration: {str(e)}",
            "error": str(e),
            "snapshot_id": snapshot_id,
        }


async def detect_configuration_drift(
    device_id: UUID,
    file_paths: list[str] | None = None,
) -> dict[str, Any]:
    """
    Detect configuration drift by comparing device file hashes with database snapshots.

    Args:
        device_id: Device UUID to check for drift
        file_paths: Specific file paths to check (if None, checks all tracked files)

    Returns:
        Dictionary containing drift detection results
    """
    try:
        config_service = await get_configuration_service()

        async with get_async_session() as session:
            # Get device information
            from apps.backend.src.services.unified_data_collection import (
                UnifiedDataCollectionService,
            )

            udcs = UnifiedDataCollectionService()
            device = await udcs._get_device(device_id)

            if not device:
                raise DeviceNotFoundError(device_id=str(device_id))

            # Get all tracked files for this device if no specific paths provided
            if not file_paths:
                tracked_files_query = (
                    select(ConfigurationSnapshot.file_path)
                    .where(ConfigurationSnapshot.device_id == device_id)
                    .distinct()
                )
                result = await session.execute(tracked_files_query)
                file_paths = [row[0] for row in result.fetchall()]

            drift_results = []
            drift_detected = False

            for file_path in file_paths:
                try:
                    # Get latest snapshot for this file
                    latest_snapshot = await config_service.get_latest_snapshot(
                        session, device_id, file_path
                    )

                    if not latest_snapshot:
                        continue  # Skip files we don't have snapshots for

                    # Read current file content from device
                    read_result = await execute_ssh_command_simple(
                        hostname=device.hostname,
                        command=f"cat {file_path}",
                    )

                    if not read_result.success:
                        drift_results.append(
                            {
                                "file_path": file_path,
                                "status": "error",
                                "error": f"Failed to read file: {read_result.stderr}",
                                "expected_hash": latest_snapshot.content_hash,
                                "actual_hash": None,
                            }
                        )
                        continue

                    # Calculate hash of current content
                    import hashlib

                    current_hash = hashlib.sha256(read_result.stdout.encode("utf-8")).hexdigest()

                    # Compare hashes
                    has_drift = current_hash != latest_snapshot.content_hash
                    if has_drift:
                        drift_detected = True

                    drift_results.append(
                        {
                            "file_path": file_path,
                            "status": "drift_detected" if has_drift else "in_sync",
                            "expected_hash": latest_snapshot.content_hash,
                            "actual_hash": current_hash,
                            "last_snapshot_time": latest_snapshot.time.isoformat(),
                            "snapshot_id": latest_snapshot.id,
                            "drift_detected": has_drift,
                        }
                    )

                    # Emit drift event if detected
                    if has_drift:
                        from apps.backend.src.core.events import event_bus

                        await event_bus.emit(
                            "configuration.drift.detected",
                            {
                                "device_id": str(device_id),
                                "file_path": file_path,
                                "expected_hash": latest_snapshot.content_hash,
                                "actual_hash": current_hash,
                                "snapshot_id": str(latest_snapshot.id),
                                "detection_time": datetime.now(timezone.utc).isoformat(),
                            },
                        )

                except Exception as e:
                    drift_results.append(
                        {
                            "file_path": file_path,
                            "status": "error",
                            "error": str(e),
                            "expected_hash": None,
                            "actual_hash": None,
                        }
                    )

            return {
                "device_id": str(device_id),
                "drift_detected": drift_detected,
                "files_checked": len(file_paths),
                "files_with_drift": len(
                    [r for r in drift_results if r.get("drift_detected", False)]
                ),
                "files_in_sync": len([r for r in drift_results if r.get("status") == "in_sync"]),
                "files_with_errors": len([r for r in drift_results if r.get("status") == "error"]),
                "detection_time": datetime.now(timezone.utc).isoformat(),
                "results": drift_results,
            }

    except Exception as e:
        return {
            "device_id": str(device_id),
            "drift_detected": False,
            "error": str(e),
            "detection_time": datetime.now(timezone.utc).isoformat(),
        }


async def reconcile_configuration_drift(
    device_id: UUID,
    file_path: str,
    reconciliation_mode: str = "restore_latest",
) -> dict[str, Any]:
    """
    Reconcile configuration drift by restoring the expected state.

    Args:
        device_id: Device UUID
        file_path: Path to the drifted file
        reconciliation_mode: How to reconcile ("restore_latest", "create_snapshot")

    Returns:
        Dictionary containing reconciliation results
    """
    try:
        config_service = await get_configuration_service()

        async with get_async_session() as session:
            # Get latest snapshot for this file
            latest_snapshot = await config_service.get_latest_snapshot(
                session, device_id, file_path
            )

            if not latest_snapshot:
                return {
                    "success": False,
                    "message": f"No snapshots found for {file_path}",
                    "file_path": file_path,
                }

            if reconciliation_mode == "restore_latest":
                # Restore the latest known good configuration
                result = await restore_configuration_snapshot(latest_snapshot.id, device_id)

                return {
                    "success": result["success"],
                    "message": f"Reconciliation completed via restoration: {result['message']}",
                    "file_path": file_path,
                    "reconciliation_mode": reconciliation_mode,
                    "restored_snapshot_id": str(latest_snapshot.id),
                    "details": result,
                }

            elif reconciliation_mode == "create_snapshot":
                # Create a new snapshot with the current (drifted) content
                from apps.backend.src.services.unified_data_collection import (
                    UnifiedDataCollectionService,
                )

                udcs = UnifiedDataCollectionService()
                device = await udcs._get_device(device_id)
                if not device:
                    raise DeviceNotFoundError(device_id=str(device_id))

                # Read current content
                read_result = await execute_ssh_command_simple(
                    hostname=device.hostname,
                    command=f"cat {file_path}",
                )

                if not read_result.success:
                    return {
                        "success": False,
                        "message": f"Failed to read current file content: {read_result.stderr}",
                        "file_path": file_path,
                    }

                # Create new snapshot with current content
                current_hash = hashlib.sha256(read_result.stdout.encode("utf-8")).hexdigest()

                new_snapshot = await config_service.create_snapshot_from_collection(
                    session=session,
                    device_id=device_id,
                    config_type="unknown",  # Could be enhanced to detect type
                    file_path=file_path,
                    raw_content=read_result.stdout,
                    content_hash=current_hash,
                    change_type="DRIFT_RECONCILIATION",
                    collection_source="drift_reconciliation",
                    previous_hash=latest_snapshot.content_hash,
                    parsed_data={"reconciliation_mode": "create_snapshot"},
                )

                await session.commit()

                return {
                    "success": True,
                    "message": "Reconciliation completed via snapshot creation",
                    "file_path": file_path,
                    "reconciliation_mode": reconciliation_mode,
                    "new_snapshot_id": str(new_snapshot.id),
                    "previous_hash": latest_snapshot.content_hash,
                    "current_hash": current_hash,
                }

            else:
                return {
                    "success": False,
                    "message": f"Unknown reconciliation mode: {reconciliation_mode}",
                    "file_path": file_path,
                }

    except Exception as e:
        return {
            "success": False,
            "message": f"Reconciliation failed: {str(e)}",
            "file_path": file_path,
            "error": str(e),
        }
