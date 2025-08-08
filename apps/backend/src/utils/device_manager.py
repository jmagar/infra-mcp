"""
Infrastructure Management MCP Server - Device Management Utilities

This module provides high-level device management capabilities, integrating SSH
communication with database operations for comprehensive infrastructure monitoring.
"""

import asyncio
from datetime import UTC, datetime
import logging

from typing import Any, Optional, cast
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy import func as sa_func

from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.device import Device
from apps.backend.src.schemas.device import DeviceCreate, DeviceResponse, DeviceUpdate
from apps.backend.src.services.device_service import (
    get_device_by_hostname as svc_get_device_by_hostname,
)
from apps.backend.src.core.exceptions import DeviceNotFoundError

from .ssh_client import SSHClient, SSHConnectionInfo, get_ssh_client
from .ssh_errors import SSHHealthChecker

logger = logging.getLogger(__name__)


class DeviceManager:
    """
    High-level device management with SSH integration.

    Provides unified interface for device registration, connectivity testing,
    health monitoring, and SSH operation management.
    """

    def __init__(self, ssh_client: SSHClient | None = None):
        """
        Initialize device manager.

        Args:
            ssh_client: Optional SSH client instance
        """
        self.ssh_client = ssh_client or get_ssh_client()
        self.health_checker = SSHHealthChecker()

    async def register_device(
        self, device_info: DeviceCreate, test_connectivity: bool = True
    ) -> DeviceResponse:
        """
        Register a new device in the system.

        Args:
            device_info: Device registration information
            test_connectivity: Whether to test SSH connectivity

        Returns:
            DeviceResponse: Registered device information

        Raises:
            Exception: If device registration fails
        """
        async with get_async_session() as session:
            # Check if device already exists
            existing_device = await session.execute(
                select(Device).where(Device.hostname == device_info.hostname)
            )
            if existing_device.scalar_one_or_none():
                raise ValueError(f"Device with hostname '{device_info.hostname}' already exists")

            # Create device record
            device = Device(
                hostname=device_info.hostname,
                ip_address=device_info.ip_address,
                ssh_port=device_info.ssh_port or 22,
                ssh_username=device_info.ssh_username or "root",
                device_type=device_info.device_type or "server",
                description=device_info.description,
                location=device_info.location,
                tags=device_info.tags or {},
                monitoring_enabled=device_info.monitoring_enabled,
                status="unknown",
            )

            session.add(device)
            await session.commit()
            await session.refresh(device)

            # Test connectivity if requested
            if test_connectivity:
                connectivity_result = await self.test_device_connectivity(cast(Any, device).id)
                orm_device = cast(Any, device)
                orm_device.status = "online" if connectivity_result["connected"] else "offline"
                orm_device.last_seen = (
                    datetime.now(UTC) if connectivity_result["connected"] else None
                )

                await session.commit()
                await session.refresh(device)

            logger.info(f"Registered device: {device.hostname} ({device.ip_address})")

            return DeviceResponse.model_validate(device)

    async def update_device(self, device_id: UUID, device_update: DeviceUpdate) -> DeviceResponse:
        """
        Update device information.

        Args:
            device_id: Device UUID
            device_update: Updated device information

        Returns:
            DeviceResponse: Updated device information

        Raises:
            ValueError: If device not found
        """
        async with get_async_session() as session:
            device = await session.get(Device, device_id)
            if not device:
                raise ValueError(f"Device with ID {device_id} not found")

            # Update fields
            update_data = device_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(device, field, value)

            orm_device = cast(Any, device)
            orm_device.updated_at = datetime.now(UTC)

            await session.commit()
            await session.refresh(device)

            logger.info(f"Updated device: {device.hostname}")

            return DeviceResponse.model_validate(device)

    async def get_device(self, device_id: UUID) -> DeviceResponse | None:
        """
        Get device by ID.

        Args:
            device_id: Device UUID

        Returns:
            DeviceResponse: Device information or None if not found
        """
        async with get_async_session() as session:
            device = await session.get(Device, device_id)
            if device:
                return DeviceResponse.model_validate(device)
            return None

    async def get_device_by_hostname(self, hostname: str) -> DeviceResponse | None:
        """
        Get device by hostname.

        Args:
            hostname: Device hostname

        Returns:
            DeviceResponse: Device information or None if not found
        """
        async with get_async_session() as session:
            try:
                device = await svc_get_device_by_hostname(session, hostname)
                return DeviceResponse.model_validate(device)
            except DeviceNotFoundError:
                return None

    async def list_devices(
        self,
        device_type: str | None = None,
        status: str | None = None,
        monitoring_enabled: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeviceResponse]:
        """
        List devices with optional filtering.

        Args:
            device_type: Filter by device type
            status: Filter by status
            monitoring_enabled: Filter by monitoring status
            limit: Maximum number of devices to return
            offset: Number of devices to skip

        Returns:
            List[DeviceResponse]: List of devices
        """
        async with get_async_session() as session:
            query = select(Device)

            # Apply filters
            conditions = []
            if device_type:
                conditions.append(Device.device_type == device_type)
            if status:
                conditions.append(Device.status == status)
            if monitoring_enabled is not None:
                conditions.append(Device.monitoring_enabled == monitoring_enabled)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.offset(offset).limit(limit).order_by(Device.hostname)

            result = await session.execute(query)
            devices = result.scalars().all()

            return [DeviceResponse.model_validate(device) for device in devices]

    async def delete_device(self, device_id: UUID) -> bool:
        """
        Delete a device.

        Args:
            device_id: Device UUID

        Returns:
            bool: True if device was deleted
        """
        async with get_async_session() as session:
            device = await session.get(Device, device_id)
            if not device:
                return False

            await session.delete(device)
            await session.commit()

            logger.info(f"Deleted device: {device.hostname}")
            return True

    def _create_ssh_connection_info(self, device: Device) -> SSHConnectionInfo:
        """Create SSH connection info from device record"""
        orm_device = cast(Any, device)
        return SSHConnectionInfo(
            host=str(orm_device.ip_address),
            port=int(orm_device.ssh_port),
            username=str(orm_device.ssh_username),
            # Note: In production, SSH keys and passwords should be securely managed
            # This is a placeholder for the SSH configuration
        )

    async def test_device_connectivity(self, device_id: UUID) -> dict[str, Any]:
        """
        Test SSH connectivity to a device.

        Args:
            device_id: Device UUID

        Returns:
            Dict containing connectivity test results
        """
        async with get_async_session() as session:
            device = await session.get(Device, device_id)
            if not device:
                return {
                    "connected": False,
                    "error": "Device not found",
                    "device_id": str(device_id),
                }

            connection_info = self._create_ssh_connection_info(device)

            try:
                # Test basic connectivity
                connected = await self.ssh_client.test_connectivity(connection_info)

                result = {
                    "device_id": str(device_id),
                    "hostname": device.hostname,
                    "ip_address": str(device.ip_address),
                    "connected": connected,
                    "tested_at": datetime.now(UTC).isoformat(),
                }

                if connected:
                    # Update device status
                    orm_device2 = cast(Any, device)
                    orm_device2.status = "online"
                    orm_device2.last_seen = datetime.now(UTC)
                    await session.commit()

                    result["status"] = "online"
                else:
                    result["error"] = "Connection failed"
                    result["status"] = "offline"

                return result

            except Exception as e:
                logger.error(f"Connectivity test failed for {device.hostname}: {e}")

                return {
                    "device_id": str(device_id),
                    "hostname": device.hostname,
                    "ip_address": str(device.ip_address),
                    "connected": False,
                    "error": str(e),
                    "status": "error",
                    "tested_at": datetime.now(UTC).isoformat(),
                }

    async def diagnose_device_issues(self, device_id: UUID) -> dict[str, Any]:
        """
        Perform comprehensive device diagnostics.

        Args:
            device_id: Device UUID

        Returns:
            Dict containing diagnostic information
        """
        async with get_async_session() as session:
            device = await session.get(Device, device_id)
            if not device:
                return {"error": "Device not found"}

            connection_info = self._create_ssh_connection_info(device)

            try:
                # Get diagnostic commands
                diagnostic_commands = self.health_checker.create_diagnostic_commands()

                diagnostics: dict[str, Any] = {
                    "device_id": str(device_id),
                    "hostname": cast(Any, device).hostname,
                    "ip_address": str(cast(Any, device).ip_address),
                    "diagnosis_time": datetime.now(UTC).isoformat(),
                    "categories": {},
                }
                categories: dict[str, list[dict[str, object]]] = {}

                # Run diagnostic commands by category
                for category, commands in diagnostic_commands.items():
                    cat_key = str(category)
                    category_results: list[dict[str, object]] = []

                    for command in commands:
                        try:
                            result = await self.ssh_client.execute_command(
                                connection_info=connection_info,
                                command=command,
                                timeout=30,
                                check=False,
                            )

                            category_results.append(
                                {
                                    "command": command,
                                    "success": bool(result.success),
                                    "output": result.stdout[:1000],  # Limit output size
                                    "error": result.stderr[:500] if result.stderr else None,
                                    "execution_time": float(result.execution_time),
                                }
                            )

                        except Exception as e:
                            category_results.append(
                                {
                                    "command": command,
                                    "success": False,
                                    "error": str(e),
                                    "execution_time": 0.0,
                                }
                            )

                    categories[cat_key] = category_results

                diagnostics["categories"] = categories

                return diagnostics

            except Exception as e:
                return {
                    "device_id": str(device_id),
                    "error": f"Diagnostic failed: {str(e)}",
                    "diagnosis_time": datetime.now(UTC).isoformat(),
                }

    async def execute_device_command(
        self, device_id: UUID, command: str, timeout: int = 120
    ) -> dict[str, Any]:
        """
        Execute a command on a specific device.

        Args:
            device_id: Device UUID
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Dict containing command execution results
        """
        async with get_async_session() as session:
            device = await session.get(Device, device_id)
            if not device:
                return {"error": "Device not found"}

            if not device.monitoring_enabled:
                return {"error": "Monitoring disabled for this device"}

            connection_info = self._create_ssh_connection_info(device)

            try:
                result = await self.ssh_client.execute_command(
                    connection_info=connection_info, command=command, timeout=timeout, check=False
                )

                # Update last seen time on successful connection
                if result.success:
                    orm_device3 = cast(Any, device)
                    orm_device3.last_seen = datetime.now(UTC)
                    orm_device3.status = "online"
                    await session.commit()

                return {
                    "device_id": str(device_id),
                    "hostname": device.hostname,
                    "command": command,
                    "success": result.success,
                    "return_code": result.return_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": result.execution_time,
                    "executed_at": datetime.now(UTC).isoformat(),
                }

            except Exception as e:
                logger.error(f"Command execution failed on {device.hostname}: {e}")

                return {
                    "device_id": str(device_id),
                    "hostname": device.hostname,
                    "command": command,
                    "success": False,
                    "error": str(e),
                    "executed_at": datetime.now(UTC).isoformat(),
                }

    async def bulk_connectivity_test(
        self, device_ids: list[UUID] | None = None, device_type: str | None = None
    ) -> list[dict[str, object]]:
        """
        Test connectivity to multiple devices in parallel.

        Args:
            device_ids: Specific device IDs to test (optional)
            device_type: Filter by device type (optional)

        Returns:
            List of connectivity test results
        """
        # Build list of device IDs to test
        ids_to_test: list[UUID] = []
        if device_ids:
            ids_to_test = list(device_ids)
        else:
            # Query devices by type and collect IDs
            device_responses = await self.list_devices(device_type=device_type, limit=100)
            ids_to_test = [d.id for d in device_responses]

        if not ids_to_test:
            return []

        # Create connectivity test tasks
        tasks: list[asyncio.Task[dict[str, Any]]] = []
        for dev_id in ids_to_test:
            task = asyncio.create_task(self.test_device_connectivity(dev_id))
            tasks.append(task)

        # Execute tests in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results: list[dict[str, object]] = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(
                    {"connected": False, "error": str(result), "status": "error"}
                )
            else:
                processed_results.append(cast(dict[str, object], result))

        return processed_results

    async def get_device_statistics(self) -> dict[str, Any]:
        """
        Get overall device statistics.

        Returns:
            Dict containing device statistics
        """
        async with get_async_session() as session:
            # Count devices by status
            status_counts: dict[str, int] = {}
            result = await session.execute(
                select(Device.status, sa_func.count(Device.id)).group_by(Device.status)
            )

            for status, count in result.fetchall():
                status_counts[status or "unknown"] = count

            # Count devices by type
            type_counts: dict[str, int] = {}
            result = await session.execute(
                select(Device.device_type, sa_func.count(Device.id)).group_by(Device.device_type)
            )

            for device_type, count in result.fetchall():
                type_counts[device_type or "unknown"] = count

            # Get total counts
            total_devices = await session.execute(select(sa_func.count(Device.id)))
            total_count = total_devices.scalar() or 0

            monitoring_enabled = await session.execute(
                select(sa_func.count(Device.id)).where(Device.monitoring_enabled == True)
            )
            monitoring_count = monitoring_enabled.scalar() or 0

            return {
                "total_devices": total_count,
                "monitoring_enabled": monitoring_count,
                "status_breakdown": status_counts,
                "type_breakdown": type_counts,
                "last_updated": datetime.now(UTC).isoformat(),
            }


# Global device manager instance
_device_manager: DeviceManager | None = None


def get_device_manager() -> DeviceManager:
    """
    Get the global device manager instance.

    Returns:
        DeviceManager: Global device manager instance
    """
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager
