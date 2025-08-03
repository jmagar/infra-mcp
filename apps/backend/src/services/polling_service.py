"""
Service layer for background device polling and metrics collection.
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import List, Optional, Any, Set
from uuid import UUID

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_async_session
from apps.backend.src.core.config import get_settings
from apps.backend.src.core.events import (
    get_event_bus,
    MetricCollectedEvent,
    DeviceStatusChangedEvent,
    ContainerStatusEvent,
    DriveHealthEvent
)
from apps.backend.src.models.device import Device
from apps.backend.src.models.metrics import SystemMetric, DriveHealth
from apps.backend.src.models.container import ContainerSnapshot
from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo
from apps.backend.src.utils.ssh_command_manager import get_ssh_command_manager
from apps.backend.src.utils.environment import WSL_DETECTION_COMMAND
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    SSHConnectionError,
    SSHCommandError,
    DatabaseOperationError,
)

logger = logging.getLogger(__name__)


class PollingService:
    def __init__(self):
        self.ssh_client = get_ssh_client()
        self.ssh_command_manager = get_ssh_command_manager()
        self.settings = get_settings()
        self.event_bus = get_event_bus()
        self.polling_tasks: dict[
            UUID, dict[str, asyncio.Task]
        ] = {}  # device_id -> {task_type: task}
        self.is_running = False
        self.db = None  # Will be initialized in start_polling

        # Use configured intervals for different data types
        self.container_interval = self.settings.polling.polling_container_interval
        self.metrics_interval = self.settings.polling.polling_system_metrics_interval
        self.drive_health_interval = self.settings.polling.polling_drive_health_interval
        self.max_concurrent_devices = self.settings.polling.polling_max_concurrent_devices

    async def start_polling(self) -> None:
        """Start the background polling service"""
        if self.is_running:
            logger.warning("Polling service is already running")
            return

        self.is_running = True
        logger.info("Starting device polling service")

        # Create database session factory for this service
        from apps.backend.src.core.database import get_async_session_factory

        self.session_factory = get_async_session_factory()

        # Start polling loop - it will manage its own database sessions
        asyncio.create_task(self._polling_loop())

    async def stop_polling(self) -> None:
        """Stop the background polling service"""
        if not self.is_running:
            return

        logger.info("Stopping device polling service")
        self.is_running = False

        # Cancel all polling tasks for all devices
        for device_id, tasks in self.polling_tasks.items():
            for task_type, task in tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        self.polling_tasks.clear()

    async def _polling_loop(self) -> None:
        """Main polling loop that manages device polling tasks"""
        while self.is_running:
            try:
                # Get all devices that should be polled
                devices = await self._get_devices_to_poll()

                # Start/stop polling tasks as needed
                await self._manage_polling_tasks(devices)

                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute for device changes

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(60)

    async def _get_devices_to_poll(self) -> List[Device]:
        """Get all devices that should be actively polled"""
        async with self.session_factory() as db:
            query = select(Device).where(
                and_(
                    Device.monitoring_enabled,
                    Device.status.in_(["online", "unknown"]),  # Don't poll offline devices
                )
            )

            result = await db.execute(query)
            return result.scalars().all()

    async def _manage_polling_tasks(self, devices: List[Device]) -> None:
        """Start/stop polling tasks based on current devices"""
        current_device_ids = {device.id for device in devices}
        running_device_ids = set(self.polling_tasks.keys())

        # Stop polling for devices no longer in the list
        to_stop = running_device_ids - current_device_ids
        for device_id in to_stop:
            tasks = self.polling_tasks.pop(device_id)
            for task_type, task in tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            logger.info(f"Stopped polling for device {device_id}")

        # Start polling for new devices
        to_start = current_device_ids - running_device_ids
        for device in devices:
            if device.id in to_start:
                # Create separate tasks for each data type with different intervals
                device_tasks = {
                    "containers": asyncio.create_task(self._poll_containers(device)),
                    "metrics": asyncio.create_task(self._poll_system_metrics(device)),
                    "drive_health": asyncio.create_task(self._poll_drive_health(device)),
                }
                self.polling_tasks[device.id] = device_tasks
                logger.info(
                    f"Started polling for device {device.id} ({device.hostname}) with separate intervals"
                )

    async def _poll_containers(self, device: Device) -> None:
        """Continuously poll container data for a device"""
        device_id = device.id
        consecutive_failures = 0
        max_consecutive_failures = 3

        while self.is_running and device_id in self.polling_tasks:
            try:
                await self._collect_container_data(device)
                consecutive_failures = 0
                await asyncio.sleep(self.container_interval)

            except SSHConnectionError:
                consecutive_failures += 1
                logger.warning(
                    f"SSH connection failed for container polling on {device.hostname} (attempt {consecutive_failures})"
                )
                if consecutive_failures >= max_consecutive_failures:
                    await self._update_device_status(device, "offline")
                    await asyncio.sleep(self.container_interval * 2)
                else:
                    await asyncio.sleep(30)

            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error polling containers for {device.hostname}: {e}")
                await asyncio.sleep(60)

    async def _poll_system_metrics(self, device: Device) -> None:
        """Continuously poll system metrics for a device"""
        device_id = device.id
        consecutive_failures = 0
        max_consecutive_failures = 3

        while self.is_running and device_id in self.polling_tasks:
            try:
                await self._collect_system_metrics(device)
                consecutive_failures = 0
                await asyncio.sleep(self.metrics_interval)

            except SSHConnectionError:
                consecutive_failures += 1
                logger.warning(
                    f"SSH connection failed for metrics polling on {device.hostname} (attempt {consecutive_failures})"
                )
                if consecutive_failures >= max_consecutive_failures:
                    await self._update_device_status(device, "offline")
                    await asyncio.sleep(self.metrics_interval * 2)
                else:
                    await asyncio.sleep(30)

            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error polling system metrics for {device.hostname}: {e}")
                await asyncio.sleep(60)

    async def _poll_drive_health(self, device: Device) -> None:
        """Continuously poll drive health for a device"""
        device_id = device.id
        consecutive_failures = 0
        max_consecutive_failures = 3

        while self.is_running and device_id in self.polling_tasks:
            try:
                await self._collect_drive_health(device)
                consecutive_failures = 0
                await asyncio.sleep(self.drive_health_interval)

            except SSHConnectionError:
                consecutive_failures += 1
                logger.warning(
                    f"SSH connection failed for drive health polling on {device.hostname} (attempt {consecutive_failures})"
                )
                if consecutive_failures >= max_consecutive_failures:
                    await self._update_device_status(device, "offline")
                    await asyncio.sleep(self.drive_health_interval * 2)
                else:
                    await asyncio.sleep(30)

            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error polling drive health for {device.hostname}: {e}")
                await asyncio.sleep(60)

    async def _update_device_status(self, device: Device, status: str) -> None:
        """Update device status and last seen timestamp"""
        async with self.session_factory() as db:
            try:
                old_status = device.status
                device.status = status
                if status == "online":
                    device.last_seen = datetime.now(UTC)
                device.updated_at = datetime.now(UTC)

                await db.commit()

                # Emit device status change event if status actually changed
                if old_status != status:
                    event = DeviceStatusChangedEvent(
                        device_id=device.id,
                        hostname=device.hostname,
                        old_status=old_status or "unknown",
                        new_status=status
                    )
                    self.event_bus.emit_nowait(event)

            except Exception as e:
                await db.rollback()
                logger.error(f"Error updating device status for {device.hostname}: {e}")

    async def _collect_system_metrics(self, device: Device) -> None:
        """Collect and store system metrics for a device using SSH Command Manager"""
        ssh_info = SSHConnectionInfo(
            host=device.hostname, port=device.ssh_port or 22, username=device.ssh_username or "root"
        )

        try:
            # Use SSH Command Manager for robust system metrics collection
            metrics_data = await self.ssh_command_manager.execute_command(
                "system_metrics",
                ssh_info
            )
            
            # Extract parsed metrics
            cpu_usage = metrics_data.get("cpu_usage", 0.0)
            memory_usage = metrics_data.get("memory_usage", 0.0)
            disk_usage = metrics_data.get("disk_usage", 0.0)
            uptime_seconds = metrics_data.get("uptime", 0.0)
            
            load_avg = metrics_data.get("load_avg", ["0", "0", "0"])
            load_1m = float(load_avg[0]) if len(load_avg) > 0 else 0.0
            load_5m = float(load_avg[1]) if len(load_avg) > 1 else 0.0
            load_15m = float(load_avg[2]) if len(load_avg) > 2 else 0.0

            # Create system metric record
            metric = SystemMetric(
                device_id=device.id,
                time=datetime.now(UTC),
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory_usage,
                disk_usage_percent=disk_usage,
                load_average_1m=load_1m,
                load_average_5m=load_5m,
                load_average_15m=load_15m,
                uptime_seconds=int(uptime_seconds),
                network_bytes_sent=0,  # Would need additional commands
                network_bytes_recv=0,
            )

            async with self.session_factory() as db:
                db.add(metric)
                await db.commit()

                # Emit metric collected event for real-time updates
                event = MetricCollectedEvent(
                    device_id=device.id,
                    hostname=device.hostname,
                    cpu_usage_percent=cpu_usage,
                    memory_usage_percent=memory_usage,
                    disk_usage_percent=disk_usage,
                    load_average_1m=load_1m,
                    load_average_5m=load_5m,
                    load_average_15m=load_15m,
                    uptime_seconds=int(uptime_seconds),
                    network_bytes_sent=0,  # TODO: Implement network metrics
                    network_bytes_recv=0
                )
                self.event_bus.emit_nowait(event)

                # System metrics collected successfully

        except Exception as e:
            logger.error(f"Error collecting system metrics for {device.hostname}: {e}")

    async def _collect_drive_health(self, device: Device) -> None:
        """Collect and store drive health data for a device"""
        ssh_info = SSHConnectionInfo(
            host=device.hostname, port=device.ssh_port or 22, username=device.ssh_username or "root"
        )

        try:
            # Check if this is a WSL environment - skip drive health collection
            wsl_result = await self.ssh_client.execute_command(ssh_info, WSL_DETECTION_COMMAND)

            if wsl_result.stdout and "WSL" in wsl_result.stdout:
                logger.debug(
                    f"Skipping drive health collection for WSL environment: {device.hostname}"
                )
                return

            # Use SSH Command Manager for robust drive listing
            try:
                drive_list = await self.ssh_command_manager.execute_command(
                    "list_drives",
                    ssh_info
                )
            except Exception as e:
                logger.warning(f"Failed to get drive list for {device.hostname}: {e}")
                return

            if not drive_list:
                return

            drives = []
            for drive_data in drive_list:
                drive_name = drive_data.get("name", "")
                drive_size = drive_data.get("size", "")

                # Get SMART data if available using SSH Command Manager
                try:
                    smart_result = await self.ssh_command_manager.execute_raw_command(
                        f"smartctl -A /dev/{drive_name} 2>/dev/null || echo 'SMART not available'",
                        ssh_info,
                        timeout=10
                    )

                    # Parse SMART data (simplified)
                    temperature = None
                    health_status = "unknown"

                    if smart_result.stdout and "SMART not available" not in smart_result.stdout:
                        lines = smart_result.stdout.split("\n")
                        for line in lines:
                            if (
                                "Temperature_Celsius" in line
                                or "Airflow_Temperature_Cel" in line
                            ):
                                parts = line.split()
                                if len(parts) >= 10:
                                    try:
                                        temperature = int(parts[9])
                                    except (ValueError, IndexError):
                                        pass
                                    break
                        health_status = (
                            "healthy"  # Simplified - would need proper SMART analysis
                        )
                except Exception as e:
                    logger.warning(f"Failed to get SMART data for {drive_name}: {e}")
                    temperature = None
                    health_status = "unknown"

                # Create or update drive health record
                drive_health = DriveHealth(
                    device_id=device.id,
                    time=datetime.now(UTC),
                    drive_name=f"/dev/{drive_name}",
                    model="Unknown",  # Would need additional parsing
                    serial_number="Unknown",
                    capacity_bytes=0,  # Would need to parse size
                    temperature_celsius=temperature,
                    health_status=health_status,
                    smart_status="PASSED" if health_status == "healthy" else "UNKNOWN",
                    power_on_hours=0,  # Would need SMART parsing
                    reallocated_sectors=0,
                    pending_sectors=0,
                    uncorrectable_errors=0,
                )

                drives.append(drive_health)

            # Add all drive records
            async with self.session_factory() as db:
                for drive in drives:
                    db.add(drive)

                await db.commit()

                # Emit drive health events for real-time updates
                for drive in drives:
                    event = DriveHealthEvent(
                        device_id=device.id,
                        hostname=device.hostname,
                        drive_name=drive.drive_name,
                        health_status=drive.health_status,
                        temperature_celsius=drive.temperature_celsius,
                        model=drive.model,
                        serial_number=drive.serial_number
                    )
                    self.event_bus.emit_nowait(event)

                # Drive health collected successfully

        except Exception as e:
            logger.error(f"Error collecting drive health for {device.hostname}: {e}")

    async def _collect_container_data(self, device: Device) -> None:
        """Collect and store container data for a device"""
        ssh_info = SSHConnectionInfo(
            host=device.hostname, port=device.ssh_port or 22, username=device.ssh_username or "root"
        )

        try:
            # Check if Docker is available
            docker_check = await self.ssh_client.execute_command(ssh_info, "docker --version")
            if not docker_check.stdout:
                # Docker not available
                return

            # Use SSH Command Manager for robust container listing
            try:
                container_list = await self.ssh_command_manager.execute_command(
                    "list_containers",
                    ssh_info
                )
            except Exception as e:
                logger.warning(f"Failed to get container list for {device.hostname}: {e}")
                return

            if not container_list:
                return

            containers = []
            for container_data in container_list:
                container_id = container_data.get("ID", "")
                container_name = container_data.get("Names", "").lstrip("/")

                if not container_id:
                    continue

                # Get detailed stats for this container using SSH Command Manager
                try:
                    stats_result = await self.ssh_command_manager.execute_raw_command(
                        f"docker stats --no-stream --format '{{json .}}' {container_id}",
                        ssh_info,
                        timeout=15
                    )

                    stats_data = {}
                    if stats_result.stdout:
                        try:
                            stats_data = json.loads(stats_result.stdout.strip())
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse stats for container {container_id}")

                    # Parse resource usage
                    cpu_usage = 0.0
                    memory_usage_bytes = 0
                    memory_limit_bytes = 0

                    if stats_data:
                        cpu_str = stats_data.get("CPUPerc", "0.00%").rstrip("%")
                        try:
                            cpu_usage = float(cpu_str)
                        except ValueError:
                            pass

                        mem_usage = stats_data.get("MemUsage", "0B / 0B")
                        if " / " in mem_usage:
                            usage_str, limit_str = mem_usage.split(" / ")
                            memory_usage_bytes = self._parse_bytes(usage_str)
                            memory_limit_bytes = self._parse_bytes(limit_str)

                    # Create container snapshot
                    snapshot = ContainerSnapshot(
                        device_id=device.id,
                        time=datetime.now(UTC),
                        container_id=container_id,
                        container_name=container_name,
                        image=container_data.get("Image", ""),
                        status=container_data.get("Status", ""),
                        state=container_data.get("State", ""),
                        cpu_usage_percent=cpu_usage,
                        memory_usage_bytes=memory_usage_bytes,
                        memory_limit_bytes=memory_limit_bytes,
                        network_bytes_sent=0,  # Would need additional parsing
                        network_bytes_recv=0,
                        block_read_bytes=0,
                        block_write_bytes=0,
                        ports=[],  # Would need port parsing
                        environment={},
                        labels={},
                        volumes=[],
                        networks=[],
                    )

                    containers.append(snapshot)

                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse container JSON: {line}")
                    continue

            # Add all container snapshots
            async with self.session_factory() as db:
                for container in containers:
                    db.add(container)

                await db.commit()

                # Emit container status events for real-time updates
                for container in containers:
                    event = ContainerStatusEvent(
                        device_id=device.id,
                        hostname=device.hostname,
                        container_id=container.container_id,
                        container_name=container.container_name,
                        image=container.image,
                        status=container.status,
                        cpu_usage_percent=container.cpu_usage_percent or 0.0,
                        memory_usage_bytes=container.memory_usage_bytes or 0,
                        memory_limit_bytes=container.memory_limit_bytes or 0
                    )
                    self.event_bus.emit_nowait(event)

                # Container data collected successfully

        except Exception as e:
            logger.error(f"Error collecting container data for {device.hostname}: {e}")

    def _parse_bytes(self, size_str: str) -> int:
        """Parse size string to bytes"""
        size_str = size_str.strip()
        if not size_str or size_str == "--":
            return 0

        multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}

        for suffix, multiplier in multipliers.items():
            if size_str.upper().endswith(suffix):
                try:
                    value = float(size_str[: -len(suffix)])
                    return int(value * multiplier)
                except ValueError:
                    break

        # Try to parse as plain number
        try:
            return int(float(size_str))
        except ValueError:
            return 0

    async def poll_device_once(self, device_id: UUID) -> dict[str, Any]:
        """Poll a single device once (for manual/on-demand polling)"""
        result = await self.db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()

        if not device:
            raise DeviceNotFoundError(str(device_id))

        try:
            # Collect all data types
            await self._collect_system_metrics(device)
            await self._collect_drive_health(device)
            await self._collect_container_data(device)

            return {
                "device_id": str(device_id),
                "hostname": device.hostname,
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "message": "Device polled successfully",
            }

        except Exception as e:
            logger.error(f"Error in manual poll for device {device_id}: {e}")
            return {
                "device_id": str(device_id),
                "hostname": device.hostname,
                "status": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
            }

    async def get_polling_status(self) -> dict[str, Any]:
        """Get current polling service status"""
        return {
            "is_running": self.is_running,
            "metrics_interval_seconds": self.metrics_interval,
            "container_interval_seconds": self.container_interval,
            "drive_health_interval_seconds": self.drive_health_interval,
            "active_devices": len(self.polling_tasks),
            "device_ids": [str(device_id) for device_id in self.polling_tasks.keys()],
        }
