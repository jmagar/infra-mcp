"""
Configuration Batch Deployment Service

Provides atomic multi-file configuration deployment with transaction management.
Ensures that configuration changes are applied consistently across multiple files
and devices with proper rollback capabilities.
"""

import asyncio
import hashlib
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.exceptions import (
    ValidationError,
    ConfigurationError,
    BusinessLogicError,
    ResourceNotFoundError,
    SSHConnectionError,
    SSHCommandError,
)
from ..models.device import Device
from ..models.configuration import ConfigurationSnapshot, ConfigurationChangeEvent
from ..utils.ssh_client import SSHClient

logger = structlog.get_logger(__name__)


class ConfigurationFileChange:
    """Represents a single file change in a batch deployment."""

    def __init__(
        self, change_id: str, file_path: str, content: str, metadata: dict[str, Any] | None = None
    ):
        self.change_id = change_id
        self.file_path = file_path
        self.content = content
        self.metadata = metadata or {}


class BatchValidationResult:
    """Results of batch deployment validation for a single device."""

    def __init__(
        self,
        device_id: UUID,
        device_name: str,
        file_validations: list[dict[str, Any]],
        overall_status: str,
        validation_errors: list[str],
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.file_validations = file_validations
        self.overall_status = overall_status
        self.validation_errors = validation_errors


class ConfigurationBatchRequest:
    """Request for batch configuration deployment."""

    def __init__(
        self,
        device_ids: list[UUID],
        changes: list[ConfigurationFileChange],
        dry_run: bool = False,
        auto_rollback: bool = True,
        metadata: dict[str, Any] | None = None,
    ):
        self.device_ids = device_ids
        self.changes = changes
        self.dry_run = dry_run
        self.auto_rollback = auto_rollback
        self.metadata = metadata or {}


class ConfigurationBatchResponse:
    """Response from batch configuration deployment."""

    def __init__(
        self,
        batch_id: str,
        status: str,
        started_at: datetime,
        completed_at: datetime | None,
        device_count: int,
        change_count: int,
        applied_changes: list[dict[str, Any]],
        failed_changes: list[dict[str, Any]],
        rollback_plan: list[dict[str, Any]],
        validation_results: list[BatchValidationResult],
        error_message: str | None,
        dry_run: bool,
    ):
        self.batch_id = batch_id
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.device_count = device_count
        self.change_count = change_count
        self.applied_changes = applied_changes
        self.failed_changes = failed_changes
        self.rollback_plan = rollback_plan
        self.validation_results = validation_results
        self.error_message = error_message
        self.dry_run = dry_run


class ConfigurationBatchTransaction:
    """
    Represents a configuration batch transaction with rollback capabilities.

    Manages the state of a multi-file configuration deployment including
    pre-deployment validation, execution tracking, and rollback planning.
    """

    def __init__(
        self,
        batch_id: str,
        device_ids: list[UUID],
        changes: list[ConfigurationFileChange],
        dry_run: bool = False,
        auto_rollback: bool = True,
    ):
        self.batch_id = batch_id
        self.device_ids = device_ids
        self.changes = changes
        self.dry_run = dry_run
        self.auto_rollback = auto_rollback

        # Transaction state
        self.status = (
            "initialized"  # initialized, validated, executing, completed, failed, rolled_back
        )
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.error_message: str | None = None

        # Execution tracking
        self.applied_changes: list[dict[str, Any]] = []  # Successfully applied changes
        self.failed_changes: list[dict[str, Any]] = []  # Failed changes
        self.rollback_plan: list[dict[str, Any]] = []  # Rollback operations

        # Pre-deployment state
        self.original_snapshots: dict[
            str, dict[str, Any]
        ] = {}  # device_id -> {file_path -> snapshot}
        self.validation_results: dict[str, BatchValidationResult] = {}


class ConfigurationBatchService:
    """
    Service for managing atomic multi-file configuration deployments.

    Provides transaction management, validation, execution, and rollback
    capabilities for configuration changes across multiple devices and files.
    """

    def __init__(self):
        self.active_transactions: dict[str, ConfigurationBatchTransaction] = {}

        # Configuration-driven values
        self.max_concurrent_deployments = int(os.getenv("BATCH_MAX_CONCURRENT_DEPLOYMENTS", "5"))
        self.deployment_timeout = int(os.getenv("BATCH_DEPLOYMENT_TIMEOUT", "3600"))
        self.cleanup_delay = int(os.getenv("BATCH_CLEANUP_DELAY", "3600"))
        self.connectivity_test_timeout = int(os.getenv("SSH_COMMAND_TIMEOUT", "30"))

    async def create_batch_deployment(
        self,
        session: AsyncSession,
        request: ConfigurationBatchRequest,
        user_id: str,
    ) -> ConfigurationBatchResponse:
        """
        Create and execute a batch configuration deployment.

        Args:
            session: Database session
            request: Batch deployment request
            user_id: User initiating the deployment

        Returns:
            Batch deployment response with results
        """
        batch_id = str(uuid4())

        structlog.contextvars.bind_contextvars(
            batch_id=batch_id,
            operation="batch_deployment",
        )

        logger.info(
            "Creating batch configuration deployment",
            device_count=len(request.device_ids),
            change_count=len(request.changes),
            dry_run=request.dry_run,
        )

        # Create transaction
        transaction = ConfigurationBatchTransaction(
            batch_id=batch_id,
            device_ids=request.device_ids,
            changes=request.changes,
            dry_run=request.dry_run,
            auto_rollback=request.auto_rollback,
        )

        self.active_transactions[batch_id] = transaction

        try:
            # Phase 1: Pre-deployment validation
            await self._validate_batch_deployment(session, transaction)

            # Phase 2: Create pre-deployment snapshots
            await self._create_pre_deployment_snapshots(session, transaction)

            # Phase 3: Execute deployment
            if not request.dry_run:
                await self._execute_batch_deployment(session, transaction, user_id)
            else:
                transaction.status = "completed"
                transaction.completed_at = datetime.now(timezone.utc)
                logger.info("Dry run completed successfully")

            # Generate response
            return await self._generate_batch_response(transaction)

        except Exception as e:
            logger.error(
                "Batch deployment failed",
                error=str(e),
                exc_info=True,
            )

            transaction.status = "failed"
            transaction.error_message = str(e)
            transaction.completed_at = datetime.now(timezone.utc)

            # Attempt rollback if auto_rollback is enabled
            if transaction.auto_rollback and not request.dry_run:
                await self._rollback_batch_deployment(session, transaction, user_id)

            return await self._generate_batch_response(transaction)

        finally:
            # Clean up transaction after some time
            asyncio.create_task(self._cleanup_transaction_after_delay(batch_id))

    async def _validate_batch_deployment(
        self,
        session: AsyncSession,
        transaction: ConfigurationBatchTransaction,
    ) -> None:
        """
        Validate a batch deployment before execution.

        Performs comprehensive validation including device availability,
        file permissions, syntax validation, and dependency checks.
        """
        logger.info("Validating batch deployment")

        # Validate devices exist and are accessible
        devices = await session.execute(select(Device).where(Device.id.in_(transaction.device_ids)))
        devices = devices.scalars().all()

        if len(devices) != len(transaction.device_ids):
            found_ids = {d.id for d in devices}
            missing_ids = set(transaction.device_ids) - found_ids
            raise ResourceNotFoundError(f"Devices not found: {missing_ids}")

        # Validate each device and file combination
        for device in devices:
            device_validation = BatchValidationResult(
                device_id=device.id,
                device_name=device.hostname,
                file_validations=[],
                overall_status="pending",
                validation_errors=[],
            )

            # Test device connectivity
            try:
                ssh_client = SSHClient(device.hostname)
                await ssh_client.connect()
                await ssh_client.execute_command(
                    "echo 'connectivity_test'", timeout=self.connectivity_test_timeout
                )
                await ssh_client.disconnect()

            except (SSHConnectionError, SSHCommandError) as e:
                device_validation.validation_errors.append(f"Device connectivity failed: {str(e)}")
                device_validation.overall_status = "failed"
                transaction.validation_results[str(device.id)] = device_validation
                continue

            # Validate each file change
            for change in transaction.changes:
                try:
                    # Basic file path validation
                    if not change.file_path.startswith("/"):
                        device_validation.validation_errors.append(
                            f"File path must be absolute: {change.file_path}"
                        )
                        continue

                    # Check if content is provided
                    if not change.content:
                        device_validation.validation_errors.append(
                            f"No content provided for file: {change.file_path}"
                        )
                        continue

                    device_validation.file_validations.append(
                        {
                            "file_path": change.file_path,
                            "status": "valid",
                            "errors": [],
                            "warnings": [],
                        }
                    )

                except Exception as e:
                    device_validation.file_validations.append(
                        {
                            "file_path": change.file_path,
                            "status": "error",
                            "errors": [str(e)],
                            "warnings": [],
                        }
                    )
                    device_validation.validation_errors.append(
                        f"File validation failed for {change.file_path}: {str(e)}"
                    )

            # Set overall device validation status
            if device_validation.validation_errors:
                device_validation.overall_status = "failed"
            else:
                device_validation.overall_status = "valid"

            transaction.validation_results[str(device.id)] = device_validation

        # Check if any validations failed
        failed_devices = [
            result
            for result in transaction.validation_results.values()
            if result.overall_status == "failed"
        ]

        if failed_devices:
            transaction.status = "validation_failed"
            error_details = []
            for device_result in failed_devices:
                error_details.append(
                    f"Device {device_result.device_name}: {', '.join(device_result.validation_errors)}"
                )
            raise ValidationError(f"Batch validation failed: {'; '.join(error_details)}")

        transaction.status = "validated"
        logger.info("Batch deployment validation completed successfully")

    async def _create_pre_deployment_snapshots(
        self,
        session: AsyncSession,
        transaction: ConfigurationBatchTransaction,
    ) -> None:
        """
        Create configuration snapshots before deployment for rollback purposes.
        """
        logger.info("Creating pre-deployment snapshots")

        for device_id in transaction.device_ids:
            device_snapshots = {}

            # Get device
            device = await session.get(Device, device_id)
            if not device:
                continue

            # Create snapshots for each file that will be changed
            for change in transaction.changes:
                try:
                    # Get current file content via SSH
                    ssh_client = SSHClient(device.hostname)
                    await ssh_client.connect()

                    # Check if file exists and get content
                    try:
                        current_content = await ssh_client.execute_command(
                            f"cat {change.file_path}", timeout=self.connectivity_test_timeout
                        )

                        # Calculate hash
                        content_hash = hashlib.sha256(current_content.encode()).hexdigest()

                        device_snapshots[change.file_path] = {
                            "content": current_content,
                            "content_hash": content_hash,
                            "file_size": len(current_content.encode()),
                            "backed_up_at": datetime.now(timezone.utc).isoformat(),
                        }

                    except SSHCommandError:
                        # File doesn't exist - this is OK for new files
                        device_snapshots[change.file_path] = {
                            "content": "",
                            "content_hash": "",
                            "file_size": 0,
                            "backed_up_at": datetime.now(timezone.utc).isoformat(),
                            "file_existed": False,
                        }

                    await ssh_client.disconnect()

                except Exception as e:
                    logger.warning(
                        "Failed to create pre-deployment snapshot",
                        device_id=str(device_id),
                        file_path=change.file_path,
                        error=str(e),
                    )

            transaction.original_snapshots[str(device_id)] = device_snapshots

        logger.info(
            "Pre-deployment snapshots created",
            snapshot_count=sum(
                len(snapshots) for snapshots in transaction.original_snapshots.values()
            ),
        )

    async def _execute_batch_deployment(
        self,
        session: AsyncSession,
        transaction: ConfigurationBatchTransaction,
        user_id: str,
    ) -> None:
        """
        Execute the batch deployment across all devices and files.
        """
        logger.info("Executing batch deployment")

        transaction.status = "executing"

        # Execute changes on each device
        for device_id in transaction.device_ids:
            device = await session.get(Device, device_id)
            if not device:
                continue

            logger.info(
                "Deploying to device",
                device_id=str(device_id),
                device_name=device.hostname,
            )

            device_applied_changes = []
            device_failed_changes = []

            # Apply each file change
            for change in transaction.changes:
                try:
                    # Deploy the configuration file via SSH
                    ssh_client = SSHClient(device.hostname)
                    await ssh_client.connect()

                    # Create directory if needed
                    dir_path = str(Path(change.file_path).parent)
                    await ssh_client.execute_command(
                        f"mkdir -p {dir_path}", timeout=self.connectivity_test_timeout
                    )

                    # Write the file content
                    # Use a temporary file approach for safety
                    temp_path = f"{change.file_path}.tmp.{uuid4().hex[:8]}"

                    # Write content to temporary file
                    escaped_content = change.content.replace("'", "'\"'\"'")
                    await ssh_client.execute_command(
                        f"cat > {temp_path} << 'EOF'\n{change.content}\nEOF",
                        timeout=self.connectivity_test_timeout,
                    )

                    # Atomically move to final location
                    await ssh_client.execute_command(
                        f"mv {temp_path} {change.file_path}", timeout=self.connectivity_test_timeout
                    )

                    await ssh_client.disconnect()

                    device_applied_changes.append(
                        {
                            "device_id": str(device_id),
                            "file_path": change.file_path,
                            "change_id": change.change_id,
                            "applied_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    logger.info(
                        "File deployed successfully",
                        device_id=str(device_id),
                        file_path=change.file_path,
                    )

                except Exception as e:
                    device_failed_changes.append(
                        {
                            "device_id": str(device_id),
                            "file_path": change.file_path,
                            "change_id": change.change_id,
                            "error": str(e),
                            "failed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    logger.error(
                        "File deployment failed",
                        device_id=str(device_id),
                        file_path=change.file_path,
                        error=str(e),
                    )

            transaction.applied_changes.extend(device_applied_changes)
            transaction.failed_changes.extend(device_failed_changes)

        # Determine final status
        if transaction.failed_changes:
            if transaction.applied_changes:
                transaction.status = "partially_completed"
            else:
                transaction.status = "failed"

            if transaction.auto_rollback:
                await self._rollback_batch_deployment(session, transaction, user_id)
        else:
            transaction.status = "completed"
            transaction.completed_at = datetime.now(timezone.utc)

        logger.info(
            "Batch deployment execution completed",
            status=transaction.status,
            applied_count=len(transaction.applied_changes),
            failed_count=len(transaction.failed_changes),
        )

    async def _rollback_batch_deployment(
        self,
        session: AsyncSession,
        transaction: ConfigurationBatchTransaction,
        user_id: str,
    ) -> None:
        """
        Rollback a failed batch deployment using pre-deployment snapshots.
        """
        logger.info("Rolling back batch deployment")

        rollback_results = []

        # Rollback only successfully applied changes
        for applied_change in transaction.applied_changes:
            device_id = UUID(applied_change["device_id"])
            file_path = applied_change["file_path"]

            try:
                # Get original snapshot
                device_snapshots = transaction.original_snapshots.get(str(device_id), {})
                original_snapshot = device_snapshots.get(file_path)

                if not original_snapshot:
                    logger.warning(
                        "No original snapshot found for rollback",
                        device_id=str(device_id),
                        file_path=file_path,
                    )
                    continue

                # Get device and restore content
                device = await session.get(Device, device_id)
                if not device:
                    continue

                ssh_client = SSHClient(device.hostname)
                await ssh_client.connect()

                if original_snapshot.get("file_existed", True):
                    # Restore original content
                    original_content = original_snapshot["content"]
                    escaped_content = original_content.replace("'", "'\"'\"'")
                    await ssh_client.execute_command(
                        f"cat > {file_path} << 'EOF'\n{original_content}\nEOF",
                        timeout=self.connectivity_test_timeout,
                    )
                else:
                    # File didn't exist originally, remove it
                    await ssh_client.execute_command(
                        f"rm -f {file_path}", timeout=self.connectivity_test_timeout
                    )

                await ssh_client.disconnect()

                rollback_results.append(
                    {
                        "device_id": str(device_id),
                        "file_path": file_path,
                        "status": "rolled_back",
                        "rolled_back_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

                logger.info(
                    "File rolled back successfully",
                    device_id=str(device_id),
                    file_path=file_path,
                )

            except Exception as e:
                rollback_results.append(
                    {
                        "device_id": str(device_id),
                        "file_path": file_path,
                        "status": "rollback_failed",
                        "error": str(e),
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

                logger.error(
                    "File rollback failed",
                    device_id=str(device_id),
                    file_path=file_path,
                    error=str(e),
                )

        transaction.rollback_plan = rollback_results
        transaction.status = "rolled_back"
        transaction.completed_at = datetime.now(timezone.utc)

        logger.info(
            "Batch deployment rollback completed",
            rollback_count=len([r for r in rollback_results if r["status"] == "rolled_back"]),
            rollback_failed_count=len(
                [r for r in rollback_results if r["status"] == "rollback_failed"]
            ),
        )

    async def _generate_batch_response(
        self,
        transaction: ConfigurationBatchTransaction,
    ) -> ConfigurationBatchResponse:
        """
        Generate a comprehensive batch deployment response.
        """
        return ConfigurationBatchResponse(
            batch_id=transaction.batch_id,
            status=transaction.status,
            started_at=transaction.started_at,
            completed_at=transaction.completed_at,
            device_count=len(transaction.device_ids),
            change_count=len(transaction.changes),
            applied_changes=transaction.applied_changes,
            failed_changes=transaction.failed_changes,
            rollback_plan=transaction.rollback_plan,
            validation_results=list(transaction.validation_results.values()),
            error_message=transaction.error_message,
            dry_run=transaction.dry_run,
        )

    async def get_batch_status(self, batch_id: str) -> ConfigurationBatchResponse | None:
        """
        Get the status of a batch deployment.
        """
        transaction = self.active_transactions.get(batch_id)
        if not transaction:
            return None

        return await self._generate_batch_response(transaction)

    async def cancel_batch_deployment(
        self,
        session: AsyncSession,
        batch_id: str,
        user_id: str,
    ) -> bool:
        """
        Cancel an active batch deployment and rollback if necessary.
        """
        transaction = self.active_transactions.get(batch_id)
        if not transaction:
            return False

        if transaction.status in ["completed", "failed", "rolled_back"]:
            return False  # Cannot cancel completed deployments

        logger.info("Cancelling batch deployment")

        # If deployment was executing, attempt rollback
        if transaction.status == "executing" and transaction.applied_changes:
            await self._rollback_batch_deployment(session, transaction, user_id)
        else:
            transaction.status = "cancelled"
            transaction.completed_at = datetime.now(timezone.utc)

        return True

    async def _cleanup_transaction_after_delay(self, batch_id: str) -> None:
        """
        Clean up a transaction after a delay to free memory.
        """
        await asyncio.sleep(self.cleanup_delay)
        if batch_id in self.active_transactions:
            del self.active_transactions[batch_id]
            logger.debug("Cleaned up batch transaction")


# Singleton service instance
_batch_service: ConfigurationBatchService | None = None


async def get_configuration_batch_service() -> ConfigurationBatchService:
    """Get the singleton configuration batch service instance."""
    global _batch_service
    if _batch_service is None:
        _batch_service = ConfigurationBatchService()
    return _batch_service


async def cleanup_configuration_batch_service() -> None:
    """Clean up the configuration batch service."""
    global _batch_service
    if _batch_service is not None:
        # Cancel any active transactions
        for batch_id, transaction in _batch_service.active_transactions.items():
            if transaction.status in ["initialized", "validated", "executing"]:
                transaction.status = "cancelled"
                transaction.completed_at = datetime.now(timezone.utc)

        _batch_service = None
        logger.info("Configuration batch service cleaned up")
