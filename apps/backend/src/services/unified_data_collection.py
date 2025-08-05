"""
Unified Data Collection Service

The core orchestrator for all infrastructure data collection operations.
Provides a single, consistent interface for data collection with intelligent
caching, comprehensive audit trails, and performance tracking.
"""

import logging
import asyncio
import hashlib
from apps.backend.src.services.dependency_service import get_dependency_service
from apps.backend.src.services.parsers import DockerComposeParser
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_async_session
from apps.backend.src.core.exceptions import (
    DatabaseOperationError,
    SSHConnectionError,
    SSHCommandError,
    SSHTimeoutError,
    DeviceNotFoundError,
    DeviceOfflineError,
    ValidationError,
    CacheOperationError,
    ServiceUnavailableError,
)
from apps.backend.src.models.audit import DataCollectionAudit
from apps.backend.src.models.performance import ServicePerformanceMetric
from apps.backend.src.models.device import Device
from apps.backend.src.services.cache_manager import CacheManager
from apps.backend.src.services.command_registry import get_command_registry, CommandDefinition
from apps.backend.src.utils.ssh_client import get_ssh_client, cleanup_ssh_client
from apps.backend.src.core.events import event_bus

logger = logging.getLogger(__name__)


@dataclass
class DataCollectionRequest:
    """Request for data collection operation."""

    operation_name: str
    device_id: str | UUID
    parameters: dict[str, Any] = field(default_factory=dict)
    force_refresh: bool = False
    timeout_override: int | None = None
    cache_override: bool | None = None
    audit_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataCollectionResult:
    """Result of data collection operation."""

    operation_id: str
    operation_name: str
    device_id: str
    success: bool
    data: Any = None
    cached: bool = False
    execution_time_ms: float = 0.0
    error_message: str | None = None
    error_code: str | None = None
    command_used: str | None = None
    validation_passed: bool = True
    audit_id: int | None = None
    performance_metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedDataCollectionService:
    """
    Unified service for all infrastructure data collection operations.

    This service is the single entry point for all data collection operations
    across the infrastructure management platform. It provides:

    - Intelligent caching with configurable freshness thresholds
    - Comprehensive audit trails for all operations
    - Performance tracking and metrics collection
    - Centralized SSH connection management
    - Consistent error handling and retry logic
    - Real-time event emission for data changes
    """

    def __init__(
        self,
        cache_manager: CacheManager | None = None,
        max_concurrent_operations: int = 10,
        default_timeout_seconds: int = 30,
        enable_performance_tracking: bool = True,
        enable_audit_trail: bool = True,
    ):
        self.cache_manager = cache_manager or CacheManager()
        self.command_registry = get_command_registry()
        self.max_concurrent_operations = max_concurrent_operations
        self.default_timeout_seconds = default_timeout_seconds
        self.enable_performance_tracking = enable_performance_tracking
        self.enable_audit_trail = enable_audit_trail

        # Connection pool management
        self._ssh_connections: dict[str, Any] = {}
        self._connection_semaphore = asyncio.Semaphore(max_concurrent_operations)

        # Operation tracking
        self._active_operations: dict[str, DataCollectionRequest] = {}
        self._operation_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "cached_operations": 0,
            "avg_execution_time_ms": 0.0,
        }

        logger.info(
            f"UnifiedDataCollectionService initialized - "
            f"max_concurrent: {max_concurrent_operations}, "
            f"caching: {cache_manager is not None}, "
            f"audit_trail: {enable_audit_trail}, "
            f"performance_tracking: {enable_performance_tracking}"
        )

    async def start(self) -> None:
        """Start the service and initialize dependencies."""
        try:
            if self.cache_manager:
                await self.cache_manager.start()

            logger.info("UnifiedDataCollectionService started successfully")

        except Exception as e:
            logger.error(f"Failed to start UnifiedDataCollectionService: {e}")
            raise ServiceUnavailableError(
                service_name="unified_data_collection",
                message="Failed to start service",
                details={"startup_error": str(e)},
            ) from e

    async def stop(self) -> None:
        """Stop the service and cleanup resources."""
        try:
            # Stop cache manager
            if self.cache_manager:
                await self.cache_manager.stop()

            # Cleanup SSH connections
            await cleanup_ssh_client()
            self._ssh_connections.clear()

            # Clear active operations
            self._active_operations.clear()

            logger.info("UnifiedDataCollectionService stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping UnifiedDataCollectionService: {e}")

    async def collect_data(
        self,
        operation_name: str,
        device_id: str | UUID,
        parameters: dict[str, Any] | None = None,
        force_refresh: bool = False,
        timeout_override: int | None = None,
        audit_metadata: dict[str, Any] | None = None,
    ) -> DataCollectionResult:
        """
        Collect data from infrastructure device with intelligent caching.

        This is the primary method for all data collection operations.
        It handles caching, command execution, audit trails, and performance tracking.
        """
        # Generate unique operation ID
        operation_id = str(uuid4())
        start_time = datetime.now(timezone.utc)

        # Create request object
        request = DataCollectionRequest(
            operation_name=operation_name,
            device_id=str(device_id),
            parameters=parameters or {},
            force_refresh=force_refresh,
            timeout_override=timeout_override,
            audit_metadata=audit_metadata or {},
        )

        # Track active operation
        self._active_operations[operation_id] = request

        try:
            # Get command definition
            command_def = self.command_registry.get_command(operation_name)
            if not command_def:
                raise ValidationError(
                    field="operation_name",
                    message=f"Unknown operation: {operation_name}",
                    details={"available_operations": self.command_registry.list_commands()},
                )

            # Check cache first (unless force refresh is requested)
            cached_data = None
            cache_hit = False

            if self.cache_manager and not force_refresh:
                cached_data, cache_hit = await self.cache_manager.get(
                    operation=operation_name,
                    device_id=str(device_id),
                    data_type=command_def.category.value,
                    additional_params=parameters,
                    force_fresh=False,
                )

            if cache_hit and cached_data is not None:
                # Return cached data
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                result = DataCollectionResult(
                    operation_id=operation_id,
                    operation_name=operation_name,
                    device_id=str(device_id),
                    success=True,
                    data=cached_data,
                    cached=True,
                    execution_time_ms=execution_time,
                    command_used=command_def.command,
                    metadata={"cache_hit": True, "command_category": command_def.category.value},
                )

                # Update statistics
                self._update_operation_stats(result)

                # Create audit record if enabled
                if self.enable_audit_trail:
                    result.audit_id = await self._create_audit_record(request, result)

                return result

            # Execute command on device
            result = await self._execute_command(operation_id, request, command_def)

            # Store result in cache if successful
            if result.success and self.cache_manager and result.data is not None:
                await self.cache_manager.set(
                    operation=operation_name,
                    device_id=str(device_id),
                    value=result.data,
                    data_type=command_def.category.value,
                    additional_params=parameters,
                    ttl_seconds=command_def.cache_ttl_seconds,
                    metadata={
                        "operation_id": operation_id,
                        "execution_time_ms": result.execution_time_ms,
                        "command_category": command_def.category.value,
                    },
                )

            # Create audit record if enabled
            if self.enable_audit_trail:
                result.audit_id = await self._create_audit_record(request, result)

            # Create performance metrics if enabled
            if self.enable_performance_tracking:
                await self._create_performance_metrics(request, result, command_def)

            # Emit data change event
            await self._emit_data_change_event(request, result)

            # Update statistics
            self._update_operation_stats(result)

            return result

        except Exception as e:
            # Handle execution errors
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            error_code = getattr(e, "error_code", type(e).__name__.upper())
            error_message = str(e)

            result = DataCollectionResult(
                operation_id=operation_id,
                operation_name=operation_name,
                device_id=str(device_id),
                success=False,
                execution_time_ms=execution_time,
                error_message=error_message,
                error_code=error_code,
                metadata={"exception_type": type(e).__name__},
            )

            # Create audit record for failure
            if self.enable_audit_trail:
                result.audit_id = await self._create_audit_record(request, result)

            # Update statistics
            self._update_operation_stats(result)

            logger.error(
                f"Data collection failed - operation: {operation_name}, "
                f"device: {device_id}, error: {error_message}"
            )

            return result

        finally:
            # Remove from active operations
            self._active_operations.pop(operation_id, None)

    async def _execute_command(
        self,
        operation_id: str,
        request: DataCollectionRequest,
        command_def: CommandDefinition,
    ) -> DataCollectionResult:
        """Execute SSH command on target device."""
        start_time = datetime.now(timezone.utc)

        # Get device information
        device = await self._get_device(request.device_id)
        if not device:
            raise DeviceNotFoundError(
                device_id=request.device_id, message=f"Device not found: {request.device_id}"
            )

        # Format command with parameters
        formatted_command = self.command_registry.format_command(
            request.operation_name, **request.parameters
        )
        if not formatted_command:
            raise ValidationError(
                field="parameters",
                message=f"Failed to format command {request.operation_name}",
                details={"parameters": request.parameters},
            )

        # Determine timeout
        timeout_seconds = (
            request.timeout_override or command_def.timeout_seconds or self.default_timeout_seconds
        )

        try:
            # Acquire connection semaphore
            async with self._connection_semaphore:
                # Execute command via SSH
                ssh_client = await get_ssh_client()

                command_result = await ssh_client.execute_command(
                    hostname=device.hostname,
                    command=formatted_command,
                    timeout=timeout_seconds,
                    retry_count=command_def.retry_count,
                    retry_delay=command_def.retry_delay_seconds,
                )

                # Validate command output
                validation_passed = self.command_registry.validate_command_output(
                    request.operation_name, command_result.stdout
                )

                # Check for known error patterns
                detected_errors = self.command_registry.check_for_errors(
                    request.operation_name, command_result.stdout
                )

                # Calculate execution time
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                # Determine success based on exit code and validation
                success = (
                    command_result.exit_code in command_def.expected_exit_codes
                    and validation_passed
                    and not detected_errors
                )

                return DataCollectionResult(
                    operation_id=operation_id,
                    operation_name=request.operation_name,
                    device_id=request.device_id,
                    success=success,
                    data=command_result.stdout if success else None,
                    execution_time_ms=execution_time,
                    command_used=formatted_command,
                    validation_passed=validation_passed,
                    error_message=command_result.stderr if not success else None,
                    error_code="COMMAND_EXECUTION_FAILED" if not success else None,
                    metadata={
                        "exit_code": command_result.exit_code,
                        "expected_exit_codes": command_def.expected_exit_codes,
                        "detected_errors": detected_errors,
                        "command_category": command_def.category.value,
                        "device_hostname": device.hostname,
                        "retry_attempts": getattr(command_result, "retry_attempts", 0),
                    },
                )

        except asyncio.TimeoutError as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            raise SSHTimeoutError(
                device_id=request.device_id,
                command=formatted_command,
                timeout_seconds=timeout_seconds,
                message=f"Command execution timed out after {timeout_seconds}s",
            ) from e

        except ConnectionError as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            raise SSHConnectionError(
                device_id=request.device_id,
                hostname=device.hostname,
                message=f"SSH connection failed: {str(e)}",
            ) from e

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            raise SSHCommandError(
                device_id=request.device_id,
                command=formatted_command,
                message=f"Command execution failed: {str(e)}",
            ) from e

    async def _get_device(self, device_id: str | UUID) -> Device | None:
        """Get device information from database."""
        try:
            async with get_async_session() as session:
                from sqlalchemy import select

                if isinstance(device_id, str):
                    # Try to convert to UUID, otherwise search by hostname
                    try:
                        device_uuid = UUID(device_id)
                        stmt = select(Device).where(Device.id == device_uuid)
                    except ValueError:
                        stmt = select(Device).where(Device.hostname == device_id)
                else:
                    stmt = select(Device).where(Device.id == device_id)

                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error fetching device {device_id}: {e}")
            return None

    async def _create_audit_record(
        self, request: DataCollectionRequest, result: DataCollectionResult
    ) -> int | None:
        """Create audit trail record for the operation."""
        try:
            async with get_async_session() as session:
                audit_record = DataCollectionAudit.create_operation_record(
                    operation_type=request.operation_name,
                    device_id=UUID(request.device_id),
                    success=result.success,
                    execution_time_ms=result.execution_time_ms,
                    data_size_bytes=len(str(result.data)) if result.data else 0,
                    cached=result.cached,
                    command_used=result.command_used,
                    error_message=result.error_message,
                    metadata={
                        **request.audit_metadata,
                        **result.metadata,
                        "operation_id": result.operation_id,
                        "validation_passed": result.validation_passed,
                    },
                )

                session.add(audit_record)
                await session.commit()
                await session.refresh(audit_record)

                return audit_record.id

        except Exception as e:
            logger.error(f"Failed to create audit record: {e}")
            return None

    async def _create_performance_metrics(
        self,
        request: DataCollectionRequest,
        result: DataCollectionResult,
        command_def: CommandDefinition,
    ) -> None:
        """Create performance metrics for the operation."""
        try:
            async with get_async_session() as session:
                performance_metric = ServicePerformanceMetric(
                    time=datetime.now(timezone.utc),
                    service_name="unified_data_collection",
                    operations_total=1,
                    operations_successful=1 if result.success else 0,
                    operations_failed=0 if result.success else 1,
                    avg_duration_ms=result.execution_time_ms,
                    max_duration_ms=result.execution_time_ms,
                    min_duration_ms=result.execution_time_ms,
                    p95_duration_ms=result.execution_time_ms,
                    p99_duration_ms=result.execution_time_ms,
                    cache_hit_count=1 if result.cached else 0,
                    cache_miss_count=0 if result.cached else 1,
                    error_count=0 if result.success else 1,
                    timeout_count=1 if result.error_code == "SSH_TIMEOUT_ERROR" else 0,
                    retry_count=result.metadata.get("retry_attempts", 0),
                    performance_metadata={
                        "operation_name": request.operation_name,
                        "device_id": request.device_id,
                        "command_category": command_def.category.value,
                        "validation_passed": result.validation_passed,
                        "cache_enabled": self.cache_manager is not None,
                    },
                )

                session.add(performance_metric)
                await session.commit()

        except Exception as e:
            logger.error(f"Failed to create performance metrics: {e}")

    async def _emit_data_change_event(
        self,
        request: DataCollectionRequest,
        result: DataCollectionResult,
    ) -> None:
        """Emit data change event for real-time updates."""
        try:
            if result.success and not result.cached:
                await event_bus.emit(
                    "data_collected",
                    {
                        "operation_id": result.operation_id,
                        "operation_name": request.operation_name,
                        "device_id": request.device_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data_type": result.metadata.get("command_category"),
                        "execution_time_ms": result.execution_time_ms,
                    },
                )

        except Exception as e:
            logger.error(f"Failed to emit data change event: {e}")

    def _update_operation_stats(self, result: DataCollectionResult) -> None:
        """Update internal operation statistics."""
        self._operation_stats["total_operations"] += 1

        if result.success:
            self._operation_stats["successful_operations"] += 1
        else:
            self._operation_stats["failed_operations"] += 1

        if result.cached:
            self._operation_stats["cached_operations"] += 1

        # Update average execution time
        total_ops = self._operation_stats["total_operations"]
        current_avg = self._operation_stats["avg_execution_time_ms"]
        new_avg = ((current_avg * (total_ops - 1)) + result.execution_time_ms) / total_ops
        self._operation_stats["avg_execution_time_ms"] = new_avg

    def get_operation_statistics(self) -> dict[str, Any]:
        """Get current operation statistics."""
        return {
            **self._operation_stats,
            "active_operations": len(self._active_operations),
            "cache_statistics": self.cache_manager.get_statistics() if self.cache_manager else None,
            "command_registry_stats": {
                "total_commands": self.command_registry.get_command_count(),
                "categories": len(self.command_registry.list_categories()),
            },
        }

    async def invalidate_cache(
        self,
        operation_name: str | None = None,
        device_id: str | UUID | None = None,
        data_type: str | None = None,
    ) -> int:
        """Invalidate cache entries based on criteria."""
        if not self.cache_manager:
            return 0

        if device_id and not operation_name:
            # Invalidate all entries for device
            return await self.cache_manager.invalidate_device(str(device_id))
        elif data_type and not device_id and not operation_name:
            # Invalidate all entries of specific type
            return await self.cache_manager.invalidate_by_type(data_type)
        elif operation_name and device_id:
            # Invalidate specific operation for device
            return 1 if await self.cache_manager.invalidate(operation_name, str(device_id)) else 0
        else:
            # Clear entire cache
            return await self.cache_manager.clear()

    async def get_active_operations(self) -> list[dict[str, Any]]:
        """Get list of currently active operations."""
        return [
            {
                "operation_id": op_id,
                "operation_name": request.operation_name,
                "device_id": request.device_id,
                "parameters": request.parameters,
                "force_refresh": request.force_refresh,
                "start_time": datetime.now(timezone.utc).isoformat(),
            }
            for op_id, request in self._active_operations.items()
        ]

    async def _detect_and_store_config_change(
        self,
        device_id: UUID,
        config_type: str,
        file_path: str,
        content: str,
        change_type: str = "MODIFY",
        source: str = "polling",
    ) -> Any:
        """
        Detects if content has changed using hash comparison and stores a new snapshot.
        """
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        try:
            async with get_async_session() as session:
                # Get the last known snapshot for this file
                from apps.backend.src.services.configuration_service import (
                    get_configuration_service,
                )

                configuration_service = await get_configuration_service()
                last_snapshot = await configuration_service.get_latest_snapshot(
                    session, device_id, file_path
                )

                if last_snapshot and last_snapshot.content_hash == content_hash:
                    # Content hasn't changed, update the last checked timestamp
                    return None

                # Get device information for validation
                device = await self._get_device(device_id)
                if not device:
                    raise DeviceNotFoundError(device_id=str(device_id))

                # Validate configuration content before storing snapshot
                validation_results = await configuration_service.validate_configuration(
                    device=device, config_type=config_type, content=content, file_path=file_path
                )
        except Exception as collection_error:
            # If there's an error during collection or validation, create a snapshot with error status
            async with get_async_session() as session:
                configuration_service = await get_configuration_service()
                error_snapshot = await configuration_service.create_snapshot_from_collection(
                    session=session,
                    device_id=device_id,
                    config_type=config_type,
                    file_path=file_path,
                    raw_content="",  # No content due to error
                    content_hash="",  # No hash due to error
                    change_type="ERROR",
                    collection_source=source,
                    sync_status="error",
                    validation_status="error",
                )
                # Update the snapshot with error details
                await configuration_service.update_snapshot_sync_status(
                    session, error_snapshot.id, "error", str(collection_error)
                )
                await session.commit()
                raise collection_error

        # Parse configuration and extract dependencies if docker-compose
        parsed_data = None
        if config_type == "docker_compose":
            try:
                parser = DockerComposeParser()
                parsed_config = await parser.parse(content, file_path)
                parsed_data = parsed_config.parsed_data

                # Extract and store service dependencies
                if parsed_data and parsed_config.is_valid:
                    dependency_service = await get_dependency_service()
                    await dependency_service.build_dependencies_from_compose(device_id, parsed_data)

            except Exception:
                # Continue with snapshot creation even if parsing fails
                pass

        # Determine sync and validation status based on the collection and validation process
        sync_status = "synced"  # Successfully collected from device
        validation_status = None  # Will be determined by create_snapshot_from_collection

        # If there were validation errors, mark as validation error
        if validation_results and not validation_results.get("valid", True):
            sync_status = "synced"  # Still synced from device, but validation failed
            validation_status = "error"

        # Create the snapshot with validation results and status tracking
        new_snapshot = await configuration_service.create_snapshot_from_collection(
            session=session,
            device_id=device_id,
            config_type=config_type,
            file_path=file_path,
            raw_content=content,
            content_hash=content_hash,
            change_type=change_type,
            collection_source=source,
            previous_hash=last_snapshot.content_hash if last_snapshot else None,
            parsed_data=parsed_data,
            validation_results=validation_results,
            sync_status=sync_status,
            validation_status=validation_status,
        )

        return new_snapshot


# Global singleton instance
_unified_service: UnifiedDataCollectionService | None = None


async def get_unified_data_collection_service() -> UnifiedDataCollectionService:
    """Get the global unified data collection service instance."""
    global _unified_service

    if _unified_service is None:
        _unified_service = UnifiedDataCollectionService()
        await _unified_service.start()

    return _unified_service


async def shutdown_unified_data_collection_service() -> None:
    """Shutdown the global service instance."""
    global _unified_service

    if _unified_service is not None:
        await _unified_service.stop()
        _unified_service = None
