"""
Service layer for device-related business logic.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from apps.backend.src.models.device import Device
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError, DatabaseOperationError, SSHConnectionError,
    ValidationError as CustomValidationError
)
from apps.backend.src.schemas.device import (
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceList,
    DeviceSummary, DeviceHealth, DeviceConnectionTest, DeviceMetricsOverview
)
from apps.backend.src.schemas.common import OperationResult, PaginationParams, DeviceStatus
from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo, test_ssh_connectivity_simple

logger = logging.getLogger(__name__)

class DeviceService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_device(self, device_data: DeviceCreate) -> Device:
        existing_device = await self.db.execute(
            select(Device).where(Device.hostname == device_data.hostname)
        )
        if existing_device.scalar_one_or_none():
            raise CustomValidationError(f"Device with hostname '{device_data.hostname}' already exists")

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
            last_seen=datetime.now(timezone.utc) if connectivity_status == "online" else None
        )

        try:
            self.db.add(device)
            await self.db.commit()
            await self.db.refresh(device)
            logger.info(f"Created device: {device.hostname} ({device.id})")
            return device
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error creating device: {e}")
            raise DatabaseOperationError(message="Failed to create device", operation="create_device", details={"error": str(e)})
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating device: {e}")
            raise

    async def list_devices(
        self,
        pagination: PaginationParams,
        device_type: Optional[str] = None,
        status: Optional[DeviceStatus] = None,
        monitoring_enabled: Optional[bool] = None,
        location: Optional[str] = None,
        search: Optional[str] = None,
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
                Device.hostname.ilike(f"%{search}%"),
                Device.description.ilike(f"%{search}%")
            )
            filters.append(search_filter)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(Device.hostname).offset(
            (pagination.page - 1) * pagination.page_size
        ).limit(pagination.page_size)

        result = await self.db.execute(query)
        devices = result.scalars().all()

        device_responses = [DeviceResponse.model_validate(device) for device in devices]
        total_pages = (total + pagination.page_size - 1) // pagination.page_size

        return DeviceList(
            items=device_responses,
            total_count=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1
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
                is_connected = await test_ssh_connectivity_simple(device.hostname)
                device.status = "online" if is_connected else "offline"
                if is_connected:
                    device.last_seen = datetime.now(timezone.utc)
            except Exception as e:
                logger.warning(f"SSH connectivity test failed for {device.hostname}: {e}")
                device.status = "offline"

        device.updated_at = datetime.now(timezone.utc)
        
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

    async def get_device_status(self, device_id: UUID, test_connectivity: bool) -> DeviceConnectionTest:
        device = await self.get_device(device_id)
        return await self._get_device_status_common(device, test_connectivity)

    async def get_device_status_by_hostname(self, hostname: str, test_connectivity: bool) -> DeviceConnectionTest:
        device = await self.get_device_by_hostname(hostname)
        return await self._get_device_status_common(device, test_connectivity)

    async def _get_device_status_common(self, device: Device, test_connectivity: bool) -> DeviceConnectionTest:
        connection_status = device.status
        response_time_ms = None
        error_message = None

        if test_connectivity and device.monitoring_enabled:
            try:
                import time
                start_time = time.time()
                
                # Use hostname directly - SSH config will handle IP, port, username
                is_connected = await test_ssh_connectivity_simple(device.hostname)
                
                response_time_ms = (time.time() - start_time) * 1000
                connection_status = "online" if is_connected else "offline"
                
                if device.status != connection_status:
                    device.status = connection_status
                    if is_connected:
                        device.last_seen = datetime.now(timezone.utc)
                    await self.db.commit()
                    
            except Exception as e:
                logger.warning(f"Connectivity test failed for {device.hostname}: {e}")
                connection_status = "error"
                error_message = str(e)
        
        return DeviceConnectionTest(
            device_id=device.id,
            hostname=device.hostname,
            ip_address=device.ip_address,
            ssh_port=device.ssh_port,
            connection_status=connection_status,
            response_time_ms=response_time_ms,
            error_message=error_message
        )

    async def get_device_summary(self, device_id: UUID) -> DeviceSummary:
        device = await self.get_device(device_id)
        return DeviceSummary.model_validate(device)

    async def get_device_summary_by_hostname(self, hostname: str) -> DeviceSummary:
        device = await self.get_device_by_hostname(hostname)
        return DeviceSummary.model_validate(device)