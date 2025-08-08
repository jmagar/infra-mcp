"""
Service layer for background device polling and metrics collection.
"""

import asyncio
import contextlib
from datetime import UTC, datetime
import json
import logging
from typing import Any, Callable, cast
from uuid import UUID

from sqlalchemy import and_, select

from apps.backend.src.core.config import get_settings
from apps.backend.src.core.events import (
    ContainerStatusEvent,
    DeviceStatusChangedEvent,
    DriveHealthEvent,
    MetricCollectedEvent,
    get_event_bus,
)
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    SSHConnectionError,
)
from apps.backend.src.models.container import ContainerSnapshot
from apps.backend.src.models.device import Device
from apps.backend.src.models.metrics import DriveHealth, SystemMetric
from apps.backend.src.services.unified_data_collection import (
    UnifiedDataCollectionService,
    get_unified_data_collection_service,
)
from apps.backend.src.utils.environment import WSL_DETECTION_COMMAND
from apps.backend.src.utils.ssh_client import SSHConnectionInfo, get_ssh_client
from apps.backend.src.utils.ssh_command_manager import get_ssh_command_manager

logger = logging.getLogger(__name__)


class PollingService:
    def __init__(self) -> None:
        self.ssh_client = get_ssh_client()
        self.ssh_command_manager = get_ssh_command_manager()
        self.settings = get_settings()
        self.event_bus = get_event_bus()
        self.polling_tasks: dict[
            UUID, dict[str, asyncio.Task]
        ] = {}  # device_id -> {task_type: task}
        self.is_running = False
        self.unified_data_service: UnifiedDataCollectionService | None = None  # Will be initialized in start_polling

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
        logger.info("polling.start", extra={})

        # Create database session factory for this service
        from apps.backend.src.core.database import get_async_session_factory

        self.session_factory = get_async_session_factory()

        # Initialize unified data collection service
        self.unified_data_service = await get_unified_data_collection_service(
            db_session_factory=self.session_factory,
            ssh_client=self.ssh_client,
            ssh_command_manager=self.ssh_command_manager  # type: ignore[arg-type]
        )

        # Start polling loop - it will manage its own database sessions
        asyncio.create_task(self._polling_loop())

    async def stop_polling(self) -> None:
        """Stop the background polling service"""
        if not self.is_running:
            return

        logger.info("Stopping device polling service")
        self.is_running = False

        # Cancel all polling tasks for all devices
        for _device_id, tasks in self.polling_tasks.items():
            for _task_type, task in tasks.items():
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

        self.polling_tasks.clear()

    async def _polling_loop(self) -> None:
        """Main polling loop that manages device polling tasks"""
        # Wait a bit after startup to let the system stabilize
        startup_delay = self.settings.polling.polling_startup_delay
        logger.info(
            "polling.loop.start",
            extra={"startup_delay_seconds": startup_delay},
        )
        await asyncio.sleep(startup_delay)

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

    async def _get_devices_to_poll(self) -> list[Device]:
        """Get all devices that should be actively polled"""
        async with self.session_factory() as db:
            query = select(Device).where(
                and_(
                    Device.monitoring_enabled,
                    Device.status.in_(["online", "unknown"]),  # Don't poll offline devices
                )
            )

            result = await db.execute(query)
            return list(result.scalars().all())

    async def _manage_polling_tasks(self, devices: list[Device]) -> None:
        """Start/stop polling tasks based on current devices"""
        from typing import cast
        current_device_ids = {cast(UUID, device.id) for device in devices}
        running_device_ids = set(self.polling_tasks.keys())

        # Stop polling for devices no longer in the list
        to_stop = running_device_ids - current_device_ids
        for device_id in to_stop:
            tasks = self.polling_tasks.pop(device_id)
            for _task_type, task in tasks.items():
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
            logger.info(f"Stopped polling for device {device_id}")

        # Start polling for new devices with staggered startup
        to_start = current_device_ids - running_device_ids
        device_delay = 0
        task_stagger = self.settings.polling.polling_task_stagger_delay
        device_stagger = self.settings.polling.polling_device_stagger_delay

        for device in devices:
            if device.id in to_start:
                # Create separate tasks for each data type with different intervals
                device_tasks = {
                    "containers": asyncio.create_task(self._poll_containers(device, device_delay)),
                    "metrics": asyncio.create_task(self._poll_system_metrics(device, device_delay + task_stagger)),
                    "drive_health": asyncio.create_task(self._poll_drive_health(device, device_delay + (task_stagger * 2))),
                }
                self.polling_tasks[cast(UUID, device.id)] = device_tasks
                logger.info(
                    f"Started staggered polling for device {device.id} ({device.hostname}) with {device_delay}s delay"
                )
                # Stagger device startups to avoid SSH congestion
                device_delay += device_stagger

    async def _poll_data_type(
        self,
        device: Device,
        collection_method: Callable,
        interval: int,
        data_type: str,
        startup_delay: int = 0
    ) -> None:
        """Generic method to continuously poll data for a device using unified service"""
        from typing import cast
        device_id = cast(UUID, device.id)
        consecutive_failures = 0
        max_consecutive_failures = 3

        # Initial startup delay to stagger device polling
        if startup_delay > 0:
            logger.debug(f"{data_type} polling for {device.hostname} waiting {startup_delay}s before starting")
            await asyncio.sleep(startup_delay)

        while self.is_running and device_id in self.polling_tasks:
            try:
                # Use unified data collection service with force_refresh=True for polling
                if self.unified_data_service:
                    await self.unified_data_service.collect_and_store_data(
                        data_type=data_type,
                        device_id=device_id,
                        collection_method=collection_method,
                        force_refresh=True,  # Polling always gets fresh data
                        correlation_id=f"polling_{data_type}_{device_id}"
                    )
                else:
                    logger.error(f"Unified data service not initialized for {data_type} polling")
                    await asyncio.sleep(interval)
                    continue

                consecutive_failures = 0
                await asyncio.sleep(interval)

            except SSHConnectionError:
                consecutive_failures += 1
                backoff_delay = min(30 * (2 ** (consecutive_failures - 1)), 300)  # Exponential backoff, max 5 minutes
                logger.warning(
                    f"SSH connection failed for {data_type} polling on {device.hostname} "
                    f"(attempt {consecutive_failures}/{max_consecutive_failures}) - waiting {backoff_delay}s"
                )
                if consecutive_failures >= max_consecutive_failures:
                    await self._update_device_status(device, "offline")
                    await asyncio.sleep(interval * 2)
                else:
                    await asyncio.sleep(backoff_delay)

            except Exception as e:
                consecutive_failures += 1
                backoff_delay = min(60 * consecutive_failures, 300)  # Linear backoff for other errors
                logger.error(f"Error polling {data_type} for {device.hostname}: {e} - waiting {backoff_delay}s")
                await asyncio.sleep(backoff_delay)

    async def _poll_containers(self, device: Device, startup_delay: int = 0) -> None:
        """Continuously poll container data for a device"""
        return await self._poll_data_type(
            device,
            lambda: self._collect_container_data_unified(device),
            self.container_interval,
            "containers",
            startup_delay
        )

    async def _poll_system_metrics(self, device: Device, startup_delay: int = 0) -> None:
        """Continuously poll system metrics for a device"""
        return await self._poll_data_type(
            device,
            lambda: self._collect_system_metrics_unified(device),
            self.metrics_interval,
            "system_metrics",
            startup_delay
        )

    async def _poll_drive_health(self, device: Device, startup_delay: int = 0) -> None:
        """Continuously poll drive health for a device"""
        return await self._poll_data_type(
            device,
            lambda: self._collect_drive_health_unified(device),
            self.drive_health_interval,
            "drive_health",
            startup_delay
        )

    async def _update_device_status(self, device: Device, status: str) -> None:
        """Update device status and last seen timestamp"""
        async with self.session_factory() as db:
            try:
                old_status = cast(str | None, device.status)
                # Assign to ORM attributes through an Any-typed alias to satisfy mypy
                dev = cast(Any, device)
                dev.status = status
                if status == "online":
                    dev.last_seen = datetime.now(UTC)
                dev.updated_at = datetime.now(UTC)

                await db.commit()

                # Emit device status change event if status actually changed
                if old_status != status:
                    event = DeviceStatusChangedEvent(
                        device_id=cast(UUID, device.id),
                        hostname=cast(str, device.hostname),
                        old_status=(old_status or "unknown"),
                        new_status=status
                    )
                    self.event_bus.emit_nowait(event)

            except Exception as e:
                await db.rollback()
                logger.error(f"Error updating device status for {device.hostname}: {e}")

    async def _collect_system_metrics_unified(self, device: Device) -> dict[str, Any]:
        """Collect system metrics for a device and return structured data"""
        ssh_info = SSHConnectionInfo(
            host=cast(str, device.hostname), port=cast(int, device.ssh_port) or 22, username=cast(str, device.ssh_username) or "root"
        )

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

        # Create system metric record and emit event
        metric = SystemMetric(
            device_id=cast(UUID, device.id),
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
            device_id=cast(UUID, device.id),
            hostname=cast(str, device.hostname),
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

        # Return structured data for unified service
        return {
            "device_id": str(device.id),
            "hostname": device.hostname,
            "metrics": {
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory_usage,
                "disk_usage_percent": disk_usage,
                "load_average_1m": load_1m,
                "load_average_5m": load_5m,
                "load_average_15m": load_15m,
                "uptime_seconds": int(uptime_seconds),
                "network_bytes_sent": 0,
                "network_bytes_recv": 0,
            },
            "status": "success"
        }

    async def _collect_drive_health_unified(self, device: Device) -> dict[str, Any]:
        """Collect drive health data for a device and return structured data"""
        ssh_info = SSHConnectionInfo(
            host=cast(str, device.hostname), port=cast(int, device.ssh_port) or 22, username=cast(str, device.ssh_username) or "root"
        )

        # Check if this is a WSL environment - skip drive health collection
        # Execute a simple remote command to detect WSL
        wsl_result = await self.ssh_client.execute_command(ssh_info, "cat /proc/version")

        if wsl_result.stdout and "WSL" in wsl_result.stdout:
            logger.debug(
                f"Skipping drive health collection for WSL environment: {device.hostname}"
            )
            return {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "drives": [],
                "status": "skipped_wsl",
                "message": "Drive health collection skipped for WSL environment"
            }

        # Use SSH Command Manager for robust drive listing
        try:
            drive_list = await self.ssh_command_manager.execute_command(
                "list_drives",
                ssh_info
            )
        except Exception as e:
            logger.warning(f"Failed to get drive list for {device.hostname}: {e}")
            return {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "drives": [],
                "status": "error",
                "message": f"Failed to get drive list: {str(e)}"
            }

        if not drive_list:
            return {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "drives": [],
                "status": "success",
                "message": "No drives found"
            }

        drives = []
        drive_data_list = []

        for drive_data in drive_list:
            drive_name = drive_data.get("name", "")

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
                                with contextlib.suppress(ValueError, IndexError):
                                    temperature = int(parts[9])
                                break
                    health_status = (
                        "healthy"  # Simplified - would need proper SMART analysis
                    )
            except Exception as e:
                logger.warning(f"Failed to get SMART data for {drive_name}: {e}")
                temperature = None
                health_status = "unknown"

            # Create drive health record
            drive_health = DriveHealth(
                device_id=cast(UUID, device.id),
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
            drive_data_list.append({
                "drive_name": f"/dev/{drive_name}",
                "health_status": health_status,
                "temperature_celsius": temperature,
                "smart_status": "PASSED" if health_status == "healthy" else "UNKNOWN"
            })

        # Add all drive records to database
        async with self.session_factory() as db:
            for drive in drives:
                db.add(drive)
            await db.commit()

        # Emit drive health events for real-time updates
        for drive in drives:
            event = DriveHealthEvent(
                device_id=cast(UUID, device.id),
                hostname=cast(str, device.hostname),
                drive_name=cast(str, drive.drive_name),
                health_status=cast(str, drive.health_status),
                temperature_celsius=cast(int | None, drive.temperature_celsius),
                model=cast(str | None, drive.model),
                serial_number=cast(str | None, drive.serial_number)
            )
            self.event_bus.emit_nowait(event)

        # Return structured data
        return {
            "device_id": str(device.id),
            "hostname": device.hostname,
            "drives": drive_data_list,
            "status": "success",
            "drive_count": len(drives)
        }

    async def _collect_container_data_unified(self, device: Device) -> dict[str, Any]:
        """Collect container data for a device and return structured data"""
        ssh_info = SSHConnectionInfo(
            host=cast(str, device.hostname), port=cast(int, device.ssh_port) or 22, username=cast(str, device.ssh_username) or "root"
        )

        # Check if Docker is available
        docker_check = await self.ssh_client.execute_command(ssh_info, "docker --version")
        if not docker_check.stdout:
            return {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "containers": [],
                "status": "docker_not_available",
                "message": "Docker not available on device"
            }

        # Use SSH Command Manager for robust container listing
        try:
            container_list = await self.ssh_command_manager.execute_command(
                "list_containers",
                ssh_info,
                parameters={"all": True}
            )
        except Exception as e:
            logger.warning(f"Failed to get container list for {device.hostname}: {e}")
            return {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "containers": [],
                "status": "error",
                "message": f"Failed to get container list: {str(e)}"
            }

        if not container_list:
            return {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "containers": [],
                "status": "success",
                "message": "No containers found"
            }

        containers = []
        container_data_list = []

        for container_data in container_list:
            container_id = container_data.get("ID", "")
            container_name = container_data.get("Names", "").lstrip("/")

            if not container_id or not container_id.strip():
                logger.debug(f"Skipping container with empty ID: {container_data}")
                continue

            # Get detailed stats for this container using SSH Command Manager
            try:
                stats_result = await self.ssh_command_manager.execute_raw_command(
                    f"docker stats --no-stream --format '{{{{json .}}}}' {container_id}",
                    ssh_info,
                    timeout=15
                )

                stats_data = {}
                if stats_result.stdout:
                    # Check if the output contains an error message instead of JSON
                    if "Error response from daemon" in stats_result.stdout or "No such container" in stats_result.stdout:
                        logger.debug(f"Container {container_id} no longer exists, skipping stats collection")
                        continue

                    try:
                        stats_data = json.loads(stats_result.stdout.strip())
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse stats for container {container_id}: {e}")
                        logger.debug(f"Raw stats output for {container_id}: {repr(stats_result.stdout)}")
                        # Continue with empty stats_data instead of failing

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

                # Create container snapshot with proper state handling
                state_value = container_data.get("State", "")
                # Convert state string to JSON object
                if isinstance(state_value, str):
                    state_json = {"status": state_value, "running": state_value.lower() == "running"}
                else:
                    state_json = state_value if state_value else {}

                snapshot = ContainerSnapshot(
                    device_id=cast(UUID, device.id),
                    time=datetime.now(UTC),
                    container_id=container_id,
                    container_name=container_name,
                    image=container_data.get("Image", ""),
                    status=container_data.get("Status", ""),
                    state=state_json,
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
                container_data_list.append({
                    "container_id": container_id,
                    "container_name": container_name,
                    "image": container_data.get("Image", ""),
                    "status": container_data.get("Status", ""),
                    "state": state_json,
                    "cpu_usage_percent": cpu_usage,
                    "memory_usage_bytes": memory_usage_bytes,
                    "memory_limit_bytes": memory_limit_bytes
                })

            except Exception as e:
                logger.warning(f"Failed to process container {container_id}: {e}")
                continue

        # Add all container snapshots to database
        async with self.session_factory() as db:
            for container in containers:
                db.add(container)
            await db.commit()

        # Emit container status events for real-time updates
        for container in containers:
            cpu_val = float(container.cpu_usage_percent) if getattr(container, "cpu_usage_percent", None) is not None else 0.0
            mem_used = int(container.memory_usage_bytes) if getattr(container, "memory_usage_bytes", None) is not None else 0
            mem_limit = int(container.memory_limit_bytes) if getattr(container, "memory_limit_bytes", None) is not None else 0
            event = ContainerStatusEvent(
                device_id=cast(UUID, device.id),
                hostname=cast(str, device.hostname),
                container_id=cast(str, container.container_id),
                container_name=cast(str, container.container_name),
                image=cast(str, container.image),
                status=cast(str, container.status),
                cpu_usage_percent=cpu_val,
                memory_usage_bytes=mem_used,
                memory_limit_bytes=mem_limit
            )
            self.event_bus.emit_nowait(event)

        # Return structured data
        return {
            "device_id": str(device.id),
            "hostname": device.hostname,
            "containers": container_data_list,
            "status": "success",
            "container_count": len(containers)
        }

    async def _collect_system_logs_unified(self, device: Device, service: str | None = None, since: str | None = None, lines: int = 100) -> dict[str, Any]:
        """Collect system logs for a device using SSH command manager"""
        ssh_info = SSHConnectionInfo(
            host=cast(str, device.hostname), port=cast(int, device.ssh_port) or 22, username=cast(str, device.ssh_username) or "root"
        )

        try:
            # Use SSH Command Manager for robust log collection
            if service:
                # Get logs for specific service
                logs_data = await self.ssh_command_manager.execute_raw_command(
                    f"journalctl --no-pager -u {service} -n {lines} --output=json" + (f" --since '{since}'" if since else ""),
                    ssh_info,
                    timeout=30
                )
            else:
                # Get recent system logs
                logs_data = await self.ssh_command_manager.execute_raw_command(
                    f"journalctl --no-pager -n {lines} --output=json" + (f" --since '{since}'" if since else ""),
                    ssh_info,
                    timeout=30
                )

            log_entries = []
            if logs_data.stdout:
                # Parse JSON log entries
                for line in logs_data.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            import json
                            log_entry = json.loads(line)
                            log_entries.append({
                                "timestamp": log_entry.get("__REALTIME_TIMESTAMP", ""),
                                "service": log_entry.get("_SYSTEMD_UNIT", service or "system"),
                                "priority": log_entry.get("PRIORITY", "6"),
                                "message": log_entry.get("MESSAGE", ""),
                                "hostname": cast(str, device.hostname)
                            })
                        except json.JSONDecodeError:
                            # Handle non-JSON lines (fallback for systems without JSON support)
                            log_entries.append({
                                "timestamp": datetime.now(UTC).isoformat(),
                                "service": service or "system",
                                "priority": "6",
                                "message": line.strip(),
                                "hostname": cast(str, device.hostname)
                            })

            # Return structured data for unified service
            return {
                "device_id": str(device.id),
                "hostname": cast(str, device.hostname),
                "logs": log_entries,
                "status": "success",
                "log_count": len(log_entries),
                "service": service,
                "since": since
            }

        except Exception as e:
            logger.warning(f"Failed to get system logs for {device.hostname}: {e}")
            return {
                "device_id": str(device.id),
                "hostname": cast(str, device.hostname),
                "logs": [],
                "status": "error",
                "message": f"Failed to get system logs: {str(e)}",
                "service": service,
                "since": since
            }

    async def _collect_drive_stats_unified(self, device: Device, drive: str | None = None) -> dict[str, Any]:
        """Collect drive usage statistics and I/O performance using SSH command manager"""
        ssh_info = SSHConnectionInfo(
            host=cast(str, device.hostname), port=cast(int, device.ssh_port) or 22, username=cast(str, device.ssh_username) or "root"
        )

        try:
            # Use SSH Command Manager for robust drive statistics collection
            drives_stats = []
            filesystem_usage = []

            if drive:
                # Check specific drive
                drives_to_check = [drive]
            else:
                # Get all available disk drives using SSH command manager
                try:
                    drive_list = await self.ssh_command_manager.execute_command(
                        "list_drives",
                        ssh_info,
                        parameters={}
                    )
                    drives_to_check = [d.get("name", "") for d in drive_list if d.get("name")]
                except Exception as e:
                    logger.warning(f"Failed to get drive list for stats on {device.hostname}: {e}")
                    drives_to_check = []

            # Get disk I/O stats from /proc/diskstats using SSH command manager
            try:
                diskstats_result = await self.ssh_command_manager.execute_raw_command(
                    "cat /proc/diskstats",
                    ssh_info,
                    timeout=10
                )

                diskstats_data = {}
                if diskstats_result.stdout:
                    for line in diskstats_result.stdout.strip().split('\n'):
                        fields = line.split()
                        if len(fields) >= 14:
                            device_name = fields[2]
                            diskstats_data[device_name] = {
                                "reads": int(fields[3]),
                                "reads_merged": int(fields[4]),
                                "sectors_read": int(fields[5]),
                                "time_reading": int(fields[6]),
                                "writes": int(fields[7]),
                                "writes_merged": int(fields[8]),
                                "sectors_written": int(fields[9]),
                                "time_writing": int(fields[10]),
                                "io_in_progress": int(fields[11]),
                                "time_io": int(fields[12]),
                                "weighted_time_io": int(fields[13])
                            }
            except Exception as e:
                logger.warning(f"Failed to get diskstats for {device.hostname}: {e}")
                diskstats_data = {}

            # Collect stats for each drive
            for drive_name in drives_to_check:
                if not drive_name:
                    continue

                drive_info = {
                    "drive_name": f"/dev/{drive_name}",
                    "usage_stats": diskstats_data.get(drive_name, {}),
                    "filesystem_usage": {},
                    "smart_available": False
                }

                # Get filesystem usage if the drive is mounted
                try:
                    df_result = await self.ssh_command_manager.execute_raw_command(
                        f"df -h /dev/{drive_name}* 2>/dev/null | grep -v 'Filesystem' || echo 'NOT_MOUNTED'",
                        ssh_info,
                        timeout=10
                    )

                    if df_result.stdout and "NOT_MOUNTED" not in df_result.stdout:
                        lines = [line for line in df_result.stdout.strip().split('\n') if line.strip()]
                        for line in lines:
                            fields = line.split()
                            if len(fields) >= 6:
                                filesystem_usage.append({
                                    "filesystem": fields[0],
                                    "size": fields[1],
                                    "used": fields[2],
                                    "available": fields[3],
                                    "use_percent": fields[4],
                                    "mounted_on": fields[5]
                                })
                                drive_info["filesystem_usage"] = {
                                    "size": fields[1],
                                    "used": fields[2],
                                    "available": fields[3],
                                    "use_percent": fields[4],
                                    "mounted_on": fields[5]
                                }
                except Exception as e:
                    logger.debug(f"Could not get filesystem usage for {drive_name}: {e}")

                drives_stats.append(drive_info)

            # Return structured data for unified service
            return {
                "device_id": str(device.id),
                "hostname": cast(str, device.hostname),
                "drives": drives_stats,
                "filesystem_usage": filesystem_usage,
                "status": "success",
                "drive_count": len(drives_stats),
                "timestamp": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.warning(f"Failed to get drive stats for {device.hostname}: {e}")
            return {
                "device_id": str(device.id),
                "hostname": cast(str, device.hostname),
                "drives": [],
                "filesystem_usage": [],
                "status": "error",
                "message": f"Failed to get drive stats: {str(e)}",
                "drive_count": 0
            }

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
        """Poll a single device once (for manual/on-demand polling) using unified service"""
        async with self.session_factory() as db:
            result = await db.execute(select(Device).where(Device.id == device_id))
            device = result.scalar_one_or_none()

            if not device:
                raise DeviceNotFoundError(str(device_id))

            if not self.unified_data_service:
                # Initialize unified service if not already done
                self.unified_data_service = await get_unified_data_collection_service(
                    db_session_factory=self.session_factory,
                    ssh_client=self.ssh_client,
                    ssh_command_manager=self.ssh_command_manager  # type: ignore[arg-type]
                )

            try:
                # Collect all data types using unified service
                results = {}

                # System metrics
                try:
                    results["system_metrics"] = await self.unified_data_service.collect_and_store_data(
                        data_type="system_metrics",
                        device_id=device_id,
                        collection_method=lambda: self._collect_system_metrics_unified(device),
                        force_refresh=True,
                        correlation_id=f"manual_poll_metrics_{device_id}"
                    )
                except Exception as e:
                    results["system_metrics"] = {"error": str(e)}

                # Drive health
                try:
                    results["drive_health"] = await self.unified_data_service.collect_and_store_data(
                        data_type="drive_health",
                        device_id=device_id,
                        collection_method=lambda: self._collect_drive_health_unified(device),
                        force_refresh=True,
                        correlation_id=f"manual_poll_drives_{device_id}"
                    )
                except Exception as e:
                    results["drive_health"] = {"error": str(e)}

                # Container data
                try:
                    results["containers"] = await self.unified_data_service.collect_and_store_data(
                        data_type="containers",
                        device_id=device_id,
                        collection_method=lambda: self._collect_container_data_unified(device),
                        force_refresh=True,
                        correlation_id=f"manual_poll_containers_{device_id}"
                    )
                except Exception as e:
                    results["containers"] = {"error": str(e)}

                return {
                    "device_id": str(device_id),
                    "hostname": cast(str, device.hostname),
                    "status": "success",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "message": "Device polled successfully",
                    "results": results
                }

            except Exception as e:
                logger.error(
                    "polling.manual.error",
                    exc_info=True,
                    extra={"device_id": str(device_id), "error": str(e)},
                )
                return {
                    "device_id": str(device_id),
                    "hostname": cast(str, device.hostname),
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
