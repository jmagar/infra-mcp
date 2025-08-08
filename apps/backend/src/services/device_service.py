"""
Service layer for device-related business logic.
"""

from datetime import UTC, datetime
import logging
from uuid import UUID
from typing import Optional, cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.exceptions import (
    DatabaseOperationError,
    DeviceNotFoundError,
)
from apps.backend.src.core.exceptions import (
    ValidationError as CustomValidationError,
)
from apps.backend.src.mcp.tools.device_info import get_device_info
from apps.backend.src.models.device import Device
from apps.backend.src.schemas.common import DeviceStatus, PaginationParams
from apps.backend.src.schemas.device import (
    DeviceConnectionTest,
    DeviceCreate,
    DeviceList,
    DeviceResponse,
    DeviceSummary,
    DeviceUpdate,
)
from apps.backend.src.services.configuration_monitoring import get_configuration_monitoring_service
from apps.backend.src.utils.ssh_client import test_ssh_connectivity_simple

logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_device(self, device_data: DeviceCreate) -> Device:
        existing_device = await self.db.execute(
            select(Device).where(Device.hostname == device_data.hostname)
        )
        if existing_device.scalar_one_or_none():
            raise CustomValidationError(
                f"Device with hostname '{device_data.hostname}' already exists"
            )

        connectivity_status = "unknown"
        if device_data.monitoring_enabled:
            try:
                # Use hostname directly - SSH config will handle IP, port, username
                is_connected = await test_ssh_connectivity_simple(device_data.hostname)
                connectivity_status = "online" if is_connected else "offline"
            except Exception as e:
                logger.warning(f"SSH connectivity test failed for {device_data.hostname}: {e}")
                connectivity_status = "offline"

        device = Device(
            **device_data.model_dump(),
            status=connectivity_status,
            last_seen=datetime.now(UTC) if connectivity_status == "online" else None,
        )

        try:
            self.db.add(device)
            await self.db.commit()
            await self.db.refresh(device)
            logger.info(f"Created device: {device.hostname} ({device.id})")

            # Trigger automatic device analysis if the device is online and monitoring is enabled
            if connectivity_status == "online" and device_data.monitoring_enabled:
                try:
                    await self._trigger_device_analysis(cast(str, device.hostname))
                except Exception as e:
                    # Analysis failure should not fail device creation
                    logger.warning(f"Device analysis failed for {device.hostname}: {e}")

            return device
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error creating device: {e}")
            raise DatabaseOperationError(
                message="Failed to create device",
                operation="create_device",
                details={"error": str(e)},
            ) from e
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating device: {e}")
            raise

    async def list_devices(
        self,
        pagination: PaginationParams,
        device_type: str | None = None,
        status: DeviceStatus | None = None,
        monitoring_enabled: bool | None = None,
        location: str | None = None,
        search: str | None = None,
    ) -> DeviceList:
        query = select(Device)
        count_query = select(func.count(Device.id))

        filters = []
        if device_type:
            filters.append(Device.device_type == device_type)
        if status:
            filters.append(Device.status == status.value)
        if monitoring_enabled is not None:
            filters.append(Device.monitoring_enabled == monitoring_enabled)
        if location:
            filters.append(Device.location.ilike(f"%{location}%"))
        if search:
            search_filter = or_(
                Device.hostname.ilike(f"%{search}%"), Device.description.ilike(f"%{search}%")
            )
            filters.append(search_filter)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        total_int: int = int(total or 0)

        query = (
            query.order_by(Device.hostname)
            .offset((pagination.page - 1) * pagination.page_size)
            .limit(pagination.page_size)
        )

        result = await self.db.execute(query)
        devices = result.scalars().all()

        device_responses = [DeviceResponse.model_validate(device) for device in devices]
        total_pages = (total_int + pagination.page_size - 1) // pagination.page_size

        return DeviceList(
            items=device_responses,
            total_count=total_int,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        )

    async def get_device(self, device_id: UUID) -> Device:
        result = await self.db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        if not device:
            raise DeviceNotFoundError(str(device_id))
        return device

    async def get_device_by_hostname(self, hostname: str) -> Device:
        result = await self.db.execute(select(Device).where(Device.hostname == hostname))
        device = result.scalar_one_or_none()
        if not device:
            raise DeviceNotFoundError(hostname, "hostname")
        return device

    async def update_device(self, device_id: UUID, device_update: DeviceUpdate) -> Device:
        device = await self.get_device(device_id)
        return await self._update_device_common(device, device_update)

    async def update_device_by_hostname(self, hostname: str, device_update: DeviceUpdate) -> Device:
        device = await self.get_device_by_hostname(hostname)
        return await self._update_device_common(device, device_update)

    async def _update_device_common(self, device: Device, device_update: DeviceUpdate) -> Device:
        retest_connectivity = False
        update_data = device_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in ["ip_address", "ssh_port", "ssh_username", "monitoring_enabled"]:
                retest_connectivity = True
            if hasattr(device, field):
                setattr(device, field, value)

        if retest_connectivity and device.monitoring_enabled:
            try:
                # Use hostname directly - SSH config will handle IP, port, username
                is_connected = await test_ssh_connectivity_simple(cast(str, device.hostname))
                setattr(device, "status", "online" if is_connected else "offline")
                if is_connected:
                    setattr(device, "last_seen", datetime.now(UTC))
            except Exception as e:
                logger.warning(f"SSH connectivity test failed for {device.hostname}: {e}")
                setattr(device, "status", "offline")

        setattr(device, "updated_at", datetime.now(UTC))

        try:
            await self.db.commit()
            await self.db.refresh(device)
            logger.info(f"Updated device: {device.hostname} ({device.id})")
            return device
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating device {device.id}: {e}")
            raise

    async def delete_device(self, device_id: UUID) -> dict:
        device = await self.get_device(device_id)
        hostname = device.hostname

        await self.db.delete(device)
        await self.db.commit()

        logger.info(f"Deleted device: {hostname} ({device_id})")
        return {"device_id": str(device_id), "hostname": hostname}

    async def delete_device_by_hostname(self, hostname: str) -> dict:
        device = await self.get_device_by_hostname(hostname)
        device_id = device.id

        await self.db.delete(device)
        await self.db.commit()

        logger.info(f"Deleted device: {hostname} ({device_id})")
        return {"device_id": str(device_id), "hostname": hostname}

    async def get_device_status(
        self, device_id: UUID, test_connectivity: bool
    ) -> DeviceConnectionTest:
        device = await self.get_device(device_id)
        return await self._get_device_status_common(device, test_connectivity)

    async def get_device_status_by_hostname(
        self, hostname: str, test_connectivity: bool
    ) -> DeviceConnectionTest:
        device = await self.get_device_by_hostname(hostname)
        return await self._get_device_status_common(device, test_connectivity)

    async def _get_device_status_common(
        self, device: Device, test_connectivity: bool
    ) -> DeviceConnectionTest:
        connection_status = cast(str, device.status)
        response_time_ms: Optional[float] = None
        error_message: Optional[str] = None

        if test_connectivity and device.monitoring_enabled:
            try:
                import time

                start_time = time.time()

                # Use hostname directly - SSH config will handle IP, port, username
                is_connected = await test_ssh_connectivity_simple(cast(str, device.hostname))

                response_time_ms = (time.time() - start_time) * 1000
                connection_status = "online" if is_connected else "offline"

                if device.status != connection_status:
                    setattr(device, "status", connection_status)
                    if is_connected:
                        setattr(device, "last_seen", datetime.now(UTC))
                    await self.db.commit()

            except Exception as e:
                logger.warning(f"Connectivity test failed for {device.hostname}: {e}")
                connection_status = "error"
                error_message = str(e)

        return DeviceConnectionTest(
            device_id=cast(UUID, device.id),
            hostname=cast(str, device.hostname),
            ip_address=cast(Optional[str], device.ip_address),
            ssh_port=cast(Optional[int], device.ssh_port),
            connection_status=connection_status,
            response_time_ms=response_time_ms,
            error_message=error_message,
        )

    async def get_device_summary(self, device_id: UUID) -> DeviceSummary:
        device = await self.get_device(device_id)
        return DeviceSummary.model_validate(device)

    async def get_device_summary_by_hostname(self, hostname: str) -> DeviceSummary:
        device = await self.get_device_by_hostname(hostname)
        return DeviceSummary.model_validate(device)

    async def _trigger_device_analysis(self, hostname: str) -> None:
        """
        Trigger comprehensive device analysis after device creation.
        
        This method calls the get_device_info MCP tool which performs comprehensive
        device analysis and automatically stores the results in the device registry.
        After analysis completes, it triggers configuration monitoring setup.
        
        Args:
            hostname: Device hostname to analyze
            
        Note:
            This is an internal method that should not fail device creation.
            Analysis failures are logged but do not propagate.
        """
        try:
            logger.info(f"Triggering automatic device analysis for {hostname}")

            # Use the comprehensive device analysis tool
            # This will collect system info, Docker containers, ZFS pools, etc.
            # and automatically store the results in the device registry
            analysis_result = await get_device_info(
                device=hostname,
                timeout=60,  # Reasonable timeout for initial analysis
            )

            logger.info(
                f"Device analysis completed for {hostname}: "
                f"connectivity={analysis_result.get('connectivity', {}).get('ssh_accessible', 'unknown')}"
            )

            # After successful device analysis, set up configuration monitoring
            # This will use discovered paths from the analysis results
            await self._setup_configuration_monitoring(hostname)

        except Exception as e:
            # Don't let analysis failures break device creation
            logger.error(f"Device analysis failed for {hostname}: {e}")
            # Could optionally store analysis failure in device metadata
            # but for now we just log and continue

    async def _setup_configuration_monitoring(self, hostname: str) -> None:
        """
        Set up configuration monitoring for a device after analysis completes.
        
        This method gets the configuration monitoring service and sets up file watching
        for discovered configuration paths (SWAG configs, Docker Compose files, etc.)
        
        Args:
            hostname: Device hostname to set up monitoring for
        """
        try:
            logger.info(f"Setting up configuration monitoring for {hostname}")

            # Get the device from the database to access analysis results
            device = await self.get_device_by_hostname(hostname)

            # Get the configuration monitoring service
            config_service = get_configuration_monitoring_service()

            # Set up monitoring using discovered paths from device analysis
            # The service will extract paths from device.tags automatically
            monitoring_started = await config_service.setup_device_monitoring(
                device_id=cast(UUID, device.id),
                custom_watch_paths=None  # Let it use discovered paths
            )

            if monitoring_started:
                logger.info(f"Configuration monitoring started successfully for {hostname}")
            else:
                logger.warning(f"Configuration monitoring failed to start for {hostname}")

        except Exception as e:
            # Configuration monitoring failure should not fail device creation
            logger.error(f"Configuration monitoring setup failed for {hostname}: {e}")
            # Continue - this is not critical for device creation


# Convenience helper to centralize common pattern usage without manual service wiring
async def get_device_by_hostname(db_session: AsyncSession, hostname: str) -> Device:
    """Fetch a `Device` by hostname or raise `DeviceNotFoundError`.

    This centralizes the repeated query pattern:
        select(Device).where(Device.hostname == hostname)
    """
    service = DeviceService(db_session)
    return await service.get_device_by_hostname(hostname)
