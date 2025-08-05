"""
Configuration Rollback Service

Provides safe, multi-file rollback capabilities for complex configuration changes.
Handles rollback planning, execution, and failure recovery.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from ..core.database import get_async_session
from ..core.events import event_bus
from ..core.exceptions import (
    ValidationError,
    ConfigurationError,
    ServiceUnavailableError,
)
from ..models.configuration import ConfigurationSnapshot, ConfigurationChangeEvent
from ..models.device import Device
from ..services.configuration_service import get_configuration_service
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RollbackService:
    """
    Configuration rollback service with multi-file rollback capabilities.

    Features:
    - Creates rollback plans for related configuration changes
    - Executes multi-file rollbacks with failure handling
    - Supports time-based and change-set-based rollbacks
    - Validates rollback feasibility before execution
    - Provides rollback preview and impact analysis
    """

    def __init__(
        self,
        max_rollback_age_days: int | None = None,
        max_files_per_rollback: int | None = None,
        rollback_window_minutes: int | None = None,
    ):
        self.max_rollback_age_days = max_rollback_age_days or getattr(
            settings, "ROLLBACK_MAX_AGE_DAYS", 30
        )
        self.max_files_per_rollback = max_files_per_rollback or getattr(
            settings, "ROLLBACK_MAX_FILES", 50
        )
        self.rollback_window_minutes = rollback_window_minutes or getattr(
            settings, "ROLLBACK_WINDOW_MINUTES", 5
        )

        self._configuration_service = None

        logger.info(
            f"RollbackService initialized - max_age: {self.max_rollback_age_days} days, "
            f"max_files: {self.max_files_per_rollback}, window: {self.rollback_window_minutes} min"
        )

    async def create_rollback_plan(
        self,
        session: AsyncSession,
        device_id: UUID,
        target_time: datetime,
        file_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a plan to roll back all changes after a certain time.

        Args:
            session: Database session
            device_id: Device to create rollback plan for
            target_time: Roll back all changes after this time
            file_paths: Optional list of specific file paths to include

        Returns:
            Rollback plan with steps and metadata
        """
        try:
            # Validate target time
            now = datetime.now(timezone.utc)
            max_age = timedelta(days=self.max_rollback_age_days)

            if target_time > now:
                raise ValidationError(
                    field="target_time", message="Target time cannot be in the future"
                )

            if (now - target_time) > max_age:
                raise ValidationError(
                    field="target_time",
                    message=f"Cannot rollback changes older than {self.max_rollback_age_days} days",
                )

            # Get device
            device_result = await session.execute(select(Device).where(Device.id == device_id))
            device = device_result.scalar_one_or_none()
            if not device:
                raise ValidationError(field="device_id", message=f"Device not found: {device_id}")

            # Find all snapshots created after the target time
            query = (
                select(ConfigurationSnapshot)
                .where(
                    and_(
                        ConfigurationSnapshot.device_id == device_id,
                        ConfigurationSnapshot.snapshot_timestamp > target_time,
                    )
                )
                .order_by(ConfigurationSnapshot.snapshot_timestamp.desc())
            )

            if file_paths:
                query = query.where(ConfigurationSnapshot.file_path.in_(file_paths))

            result = await session.execute(query)
            snapshots_to_revert = result.scalars().all()

            if not snapshots_to_revert:
                return {
                    "plan_id": str(UUID()),
                    "device_id": str(device_id),
                    "target_time": target_time.isoformat(),
                    "steps": [],
                    "total_files": 0,
                    "estimated_duration_seconds": 0,
                    "warnings": ["No changes found after target time"],
                    "can_execute": False,
                }

            # Group snapshots by file path and find restore targets
            plan_steps = []
            processed_files = set()
            warnings = []

            for snapshot in snapshots_to_revert:
                if snapshot.file_path in processed_files:
                    continue  # Already processed this file

                processed_files.add(snapshot.file_path)

                # Find the previous snapshot for this file (what to restore TO)
                previous_snapshot = await self._find_previous_snapshot(
                    session, device_id, snapshot.file_path, target_time
                )

                if previous_snapshot:
                    plan_steps.append(
                        {
                            "file_path": snapshot.file_path,
                            "from_snapshot_id": str(snapshot.id),
                            "to_snapshot_id": str(previous_snapshot.id),
                            "from_timestamp": snapshot.snapshot_timestamp.isoformat(),
                            "to_timestamp": previous_snapshot.snapshot_timestamp.isoformat(),
                            "config_type": snapshot.config_type,
                            "change_description": f"Restore to version from {previous_snapshot.snapshot_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                        }
                    )
                else:
                    warnings.append(
                        f"Cannot find previous version for {snapshot.file_path} - file will be deleted"
                    )
                    plan_steps.append(
                        {
                            "file_path": snapshot.file_path,
                            "from_snapshot_id": str(snapshot.id),
                            "to_snapshot_id": None,
                            "from_timestamp": snapshot.snapshot_timestamp.isoformat(),
                            "to_timestamp": None,
                            "config_type": snapshot.config_type,
                            "change_description": f"Delete file (no previous version found)",
                        }
                    )

            # Check file count limit
            if len(plan_steps) > self.max_files_per_rollback:
                raise ValidationError(
                    field="file_count",
                    message=f"Rollback plan exceeds maximum files limit ({self.max_files_per_rollback})",
                )

            # Calculate estimated duration (rough estimate: 2 seconds per file)
            estimated_duration = len(plan_steps) * 2

            plan = {
                "plan_id": str(UUID()),
                "device_id": str(device_id),
                "device_hostname": device.hostname,
                "target_time": target_time.isoformat(),
                "created_at": now.isoformat(),
                "steps": plan_steps,
                "total_files": len(plan_steps),
                "estimated_duration_seconds": estimated_duration,
                "warnings": warnings,
                "can_execute": len(plan_steps) > 0,
                "rollback_window_minutes": self.rollback_window_minutes,
            }

            logger.info(
                f"Created rollback plan for device {device.hostname}: "
                f"{len(plan_steps)} files, target_time: {target_time}"
            )

            return plan

        except Exception as e:
            logger.error(f"Error creating rollback plan: {e}")
            raise

    async def execute_rollback_plan(
        self, plan: dict[str, Any], dry_run: bool = False, continue_on_error: bool = True
    ) -> dict[str, Any]:
        """
        Execute the steps in a rollback plan.

        Args:
            plan: Rollback plan from create_rollback_plan
            dry_run: If True, validate plan but don't actually execute
            continue_on_error: If False, stop on first error

        Returns:
            Execution results with success/failure details
        """
        try:
            device_id = UUID(plan["device_id"])
            plan_id = plan["plan_id"]
            steps = plan["steps"]

            if not plan.get("can_execute", False):
                raise ValidationError(
                    field="plan", message="Plan cannot be executed (see warnings)"
                )

            if not self._configuration_service:
                self._configuration_service = await get_configuration_service()

            execution_results = {
                "plan_id": plan_id,
                "device_id": str(device_id),
                "dry_run": dry_run,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
                "total_steps": len(steps),
                "successful_steps": 0,
                "failed_steps": 0,
                "skipped_steps": 0,
                "step_results": [],
                "overall_success": False,
                "errors": [],
            }

            logger.info(
                f"{'Dry run' if dry_run else 'Executing'} rollback plan {plan_id}: "
                f"{len(steps)} steps"
            )

            # Execute each step
            for i, step in enumerate(steps):
                step_result = {
                    "step_number": i + 1,
                    "file_path": step["file_path"],
                    "from_snapshot_id": step["from_snapshot_id"],
                    "to_snapshot_id": step["to_snapshot_id"],
                    "success": False,
                    "error": None,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": None,
                }

                try:
                    if dry_run:
                        # Validate step but don't execute
                        await self._validate_rollback_step(step, device_id)
                        step_result["success"] = True
                        step_result["note"] = "Validation successful (dry run)"
                    else:
                        # Execute the rollback step
                        await self._execute_rollback_step(step, device_id)
                        step_result["success"] = True

                    execution_results["successful_steps"] += 1

                except Exception as e:
                    step_result["error"] = str(e)
                    execution_results["failed_steps"] += 1
                    execution_results["errors"].append(f"Step {i + 1}: {e}")

                    logger.error(f"Rollback step {i + 1} failed: {e}")

                    if not continue_on_error:
                        step_result["note"] = "Execution stopped due to error"
                        execution_results["step_results"].append(step_result)
                        break

                step_result["completed_at"] = datetime.now(timezone.utc).isoformat()
                execution_results["step_results"].append(step_result)

            # Mark remaining steps as skipped if we stopped early
            if not continue_on_error and execution_results["failed_steps"] > 0:
                remaining_steps = len(steps) - len(execution_results["step_results"])
                execution_results["skipped_steps"] = remaining_steps

            execution_results["completed_at"] = datetime.now(timezone.utc).isoformat()
            execution_results["overall_success"] = (
                execution_results["failed_steps"] == 0 and execution_results["successful_steps"] > 0
            )

            # Emit rollback event
            await event_bus.emit(
                "configuration.rollback.executed"
                if not dry_run
                else "configuration.rollback.validated",
                {
                    "plan_id": plan_id,
                    "device_id": str(device_id),
                    "success": execution_results["overall_success"],
                    "total_steps": execution_results["total_steps"],
                    "successful_steps": execution_results["successful_steps"],
                    "failed_steps": execution_results["failed_steps"],
                    "dry_run": dry_run,
                },
            )

            logger.info(
                f"Rollback plan {plan_id} {'validated' if dry_run else 'executed'}: "
                f"{execution_results['successful_steps']}/{execution_results['total_steps']} successful"
            )

            return execution_results

        except Exception as e:
            logger.error(f"Error executing rollback plan: {e}")
            raise

    async def get_rollback_candidates(
        self, session: AsyncSession, device_id: UUID, hours_back: int = 24
    ) -> list[dict[str, Any]]:
        """
        Get potential rollback target times based on recent changes.

        Args:
            session: Database session
            device_id: Device to analyze
            hours_back: How many hours back to look

        Returns:
            List of rollback candidates with timestamps and change summaries
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

            # Get all change events in the time window
            query = (
                select(ConfigurationChangeEvent)
                .where(
                    and_(
                        ConfigurationChangeEvent.device_id == device_id,
                        ConfigurationChangeEvent.timestamp >= cutoff_time,
                    )
                )
                .order_by(ConfigurationChangeEvent.timestamp.desc())
            )

            result = await session.execute(query)
            changes = result.scalars().all()

            if not changes:
                return []

            # Group changes into rollback windows
            candidates = []
            current_window = None

            for change in changes:
                if current_window is None:
                    # Start new window
                    current_window = {
                        "target_time": change.timestamp,
                        "changes": [change],
                        "file_count": 1,
                        "config_types": {change.config_type},
                    }
                else:
                    # Check if this change is within the rollback window
                    time_diff = (current_window["target_time"] - change.timestamp).total_seconds()

                    if time_diff <= (self.rollback_window_minutes * 60):
                        # Add to current window
                        current_window["changes"].append(change)
                        current_window["file_count"] += 1
                        current_window["config_types"].add(change.config_type)
                        current_window["target_time"] = change.timestamp  # Use earliest time
                    else:
                        # Close current window and start new one
                        candidates.append(self._format_rollback_candidate(current_window))
                        current_window = {
                            "target_time": change.timestamp,
                            "changes": [change],
                            "file_count": 1,
                            "config_types": {change.config_type},
                        }

            # Add the final window
            if current_window:
                candidates.append(self._format_rollback_candidate(current_window))

            return candidates

        except Exception as e:
            logger.error(f"Error getting rollback candidates: {e}")
            return []

    async def _find_previous_snapshot(
        self, session: AsyncSession, device_id: UUID, file_path: str, target_time: datetime
    ) -> ConfigurationSnapshot | None:
        """Find the most recent snapshot for a file before the target time."""
        try:
            query = (
                select(ConfigurationSnapshot)
                .where(
                    and_(
                        ConfigurationSnapshot.device_id == device_id,
                        ConfigurationSnapshot.file_path == file_path,
                        ConfigurationSnapshot.snapshot_timestamp < target_time,
                    )
                )
                .order_by(desc(ConfigurationSnapshot.snapshot_timestamp))
                .limit(1)
            )

            result = await session.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.debug(f"Error finding previous snapshot: {e}")
            return None

    async def _validate_rollback_step(self, step: dict[str, Any], device_id: UUID) -> None:
        """Validate that a rollback step can be executed."""
        to_snapshot_id = step.get("to_snapshot_id")

        if to_snapshot_id:
            # Validate that the target snapshot exists
            async with get_async_session() as session:
                snapshot_result = await session.execute(
                    select(ConfigurationSnapshot).where(
                        ConfigurationSnapshot.id == UUID(to_snapshot_id)
                    )
                )
                snapshot = snapshot_result.scalar_one_or_none()

                if not snapshot:
                    raise ConfigurationError(f"Target snapshot not found: {to_snapshot_id}")

        # Additional validation could be added here (e.g., file permissions, disk space)

    async def _execute_rollback_step(self, step: dict[str, Any], device_id: UUID) -> None:
        """Execute a single rollback step."""
        to_snapshot_id = step.get("to_snapshot_id")
        file_path = step["file_path"]

        if to_snapshot_id:
            # Restore file from snapshot
            result = await self._configuration_service.restore_configuration_snapshot(
                UUID(to_snapshot_id), device_id
            )

            if not result.get("success", False):
                raise ConfigurationError(
                    f"Failed to restore {file_path}: {result.get('error', 'Unknown error')}"
                )
        else:
            # Delete file (no previous version)
            # This would need SSH client to delete the file on the remote device
            logger.warning(f"File deletion not implemented for rollback: {file_path}")

    def _format_rollback_candidate(self, window: dict[str, Any]) -> dict[str, Any]:
        """Format a rollback candidate window."""
        changes = window["changes"]
        latest_change = changes[0]  # Changes are sorted by timestamp desc
        earliest_change = changes[-1]

        return {
            "target_time": window["target_time"].isoformat(),
            "window_start": earliest_change.timestamp.isoformat(),
            "window_end": latest_change.timestamp.isoformat(),
            "file_count": window["file_count"],
            "config_types": list(window["config_types"]),
            "change_summary": f"{window['file_count']} files changed",
            "latest_change_type": latest_change.change_type,
            "files_affected": list(set(change.file_path for change in changes))[
                :5
            ],  # First 5 files
        }


# Global singleton instance
_rollback_service: RollbackService | None = None


async def get_rollback_service() -> RollbackService:
    """Get the global rollback service instance."""
    global _rollback_service

    if _rollback_service is None:
        _rollback_service = RollbackService()

    return _rollback_service
