"""
Service layer for background device polling and metrics collection.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Set
from uuid import UUID

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_async_session
from apps.backend.src.core.config import get_settings
from apps.backend.src.models.device import Device
from apps.backend.src.models.metrics import SystemMetric, DriveHealth
from apps.backend.src.models.container import ContainerSnapshot
from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo, execute_ssh_command
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError, SSHConnectionError, SSHCommandError, DatabaseOperationError
)

logger = logging.getLogger(__name__)

class PollingService:
    def __init__(self):
        self.ssh_client = get_ssh_client()
        self.settings = get_settings()
        self.polling_tasks: Dict[UUID, asyncio.Task] = {}
        self.is_running = False
        self.db = None  # Will be initialized in start_polling
        # Set polling interval - default to 5 minutes if not configured
        if hasattr(self.settings, 'polling') and hasattr(self.settings.polling, 'poll_interval_seconds'):
            self.poll_interval = self.settings.polling.poll_interval_seconds
        else:
            self.poll_interval = 300  # 5 minutes default

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
        
        # Cancel all polling tasks
        for device_id, task in self.polling_tasks.items():
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
                    Device.monitoring_enabled == True,
                    Device.status.in_(["online", "unknown"])  # Don't poll offline devices
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
            task = self.polling_tasks.pop(device_id)
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
                task = asyncio.create_task(self._poll_device(device))
                self.polling_tasks[device.id] = task
                logger.info(f"Started polling for device {device.id} ({device.hostname})")

    async def _poll_device(self, device: Device) -> None:
        """Poll a single device for metrics and container data"""
        device_id = device.id
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while self.is_running and device_id in self.polling_tasks:
            try:
                # Update device status to online if we can connect
                await self._update_device_status(device, "online")
                
                # Collect system metrics
                await self._collect_system_metrics(device)
                
                # Collect drive health data
                await self._collect_drive_health(device)
                
                # Collect container data
                await self._collect_container_data(device)
                
                # Reset failure counter on success
                consecutive_failures = 0
                
                # Wait for next poll
                await asyncio.sleep(self.poll_interval)
                
            except SSHConnectionError:
                consecutive_failures += 1
                logger.warning(f"SSH connection failed for device {device.hostname} (attempt {consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    await self._update_device_status(device, "offline")
                    # Increase poll interval for offline devices
                    await asyncio.sleep(self.poll_interval * 2)
                else:
                    await asyncio.sleep(30)  # Short retry delay
                    
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error polling device {device.hostname}: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _update_device_status(self, device: Device, status: str) -> None:
        """Update device status and last seen timestamp"""
        try:
            device.status = status
            if status == "online":
                device.last_seen = datetime.now(timezone.utc)
            device.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating device status for {device.hostname}: {e}")

    async def _collect_system_metrics(self, device: Device) -> None:
        """Collect and store system metrics for a device"""
        ssh_info = SSHConnectionInfo(
            host=device.ip_address,
            port=device.ssh_port or 22,
            username=device.ssh_username or "root"
        )
        
        try:
            # Get system metrics via SSH commands
            commands = {
                'cpu': "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | sed 's/%us,//'",
                'memory': "free | grep Mem | awk '{printf \"%.2f\", ($3/$2) * 100.0}'",
                'disk': "df -h / | awk 'NR==2{print $5}' | sed 's/%//'",
                'load': "cat /proc/loadavg | awk '{print $1, $2, $3}'",
                'uptime': "cat /proc/uptime | awk '{print $1}'"
            }
            
            results = {}
            for key, cmd in commands.items():
                try:
                    result = await execute_ssh_command(ssh_info, cmd)
                    results[key] = result.stdout.strip() if result.stdout else ""
                except Exception as e:
                    logger.warning(f"Failed to get {key} metric for {device.hostname}: {e}")
                    results[key] = ""
            
            # Parse results
            cpu_usage = float(results['cpu']) if results['cpu'] else 0.0
            memory_usage = float(results['memory']) if results['memory'] else 0.0
            disk_usage = float(results['disk']) if results['disk'] else 0.0
            uptime_seconds = float(results['uptime']) if results['uptime'] else 0.0
            
            load_avg = results['load'].split() if results['load'] else ['0', '0', '0']
            load_1m = float(load_avg[0]) if len(load_avg) > 0 else 0.0
            load_5m = float(load_avg[1]) if len(load_avg) > 1 else 0.0
            load_15m = float(load_avg[2]) if len(load_avg) > 2 else 0.0
            
            # Create system metric record
            metric = SystemMetric(
                device_id=device.id,
                time=datetime.now(timezone.utc),
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory_usage,
                disk_usage_percent=disk_usage,
                load_average_1m=load_1m,
                load_average_5m=load_5m,
                load_average_15m=load_15m,
                uptime_seconds=int(uptime_seconds),
                network_bytes_sent=0,  # Would need additional commands
                network_bytes_recv=0,
                disk_bytes_read=0,
                disk_bytes_written=0
            )
            
            self.db.add(metric)
            await self.db.commit()
            
            logger.debug(f"Collected system metrics for {device.hostname}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error collecting system metrics for {device.hostname}: {e}")

    async def _collect_drive_health(self, device: Device) -> None:
        """Collect and store drive health data for a device"""
        ssh_info = SSHConnectionInfo(
            host=device.ip_address,
            port=device.ssh_port or 22,
            username=device.ssh_username or "root"
        )
        
        try:
            # Get list of drives
            cmd = "lsblk -dno NAME,SIZE | grep -E '^[s|n|h]d[a-z]|^nvme[0-9]'"
            result = await execute_ssh_command(ssh_info, cmd)
            
            if not result.stdout:
                return
            
            drives = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        drive_name = parts[0]
                        drive_size = parts[1]
                        
                        # Get SMART data if available
                        smart_cmd = f"smartctl -A /dev/{drive_name} 2>/dev/null || echo 'SMART not available'"
                        smart_result = await execute_ssh_command(ssh_info, smart_cmd)
                        
                        # Parse SMART data (simplified)
                        temperature = None
                        health_status = "unknown"
                        
                        if smart_result.stdout and "SMART not available" not in smart_result.stdout:
                            lines = smart_result.stdout.split('\n')
                            for line in lines:
                                if 'Temperature_Celsius' in line or 'Airflow_Temperature_Cel' in line:
                                    parts = line.split()
                                    if len(parts) >= 10:
                                        try:
                                            temperature = int(parts[9])
                                        except (ValueError, IndexError):
                                            pass
                                        break
                            health_status = "healthy"  # Simplified - would need proper SMART analysis
                        
                        # Create or update drive health record
                        drive_health = DriveHealth(
                            device_id=device.id,
                            time=datetime.now(timezone.utc),
                            device=f"/dev/{drive_name}",
                            model="Unknown",  # Would need additional parsing
                            serial_number="Unknown",
                            capacity_bytes=0,  # Would need to parse size
                            temperature_celsius=temperature,
                            health_status=health_status,
                            smart_status="PASSED" if health_status == "healthy" else "UNKNOWN",
                            power_on_hours=0,  # Would need SMART parsing
                            power_cycle_count=0,
                            reallocated_sectors=0,
                            pending_sectors=0,
                            uncorrectable_sectors=0
                        )
                        
                        drives.append(drive_health)
            
            # Add all drive records
            for drive in drives:
                self.db.add(drive)
            
            await self.db.commit()
            
            logger.debug(f"Collected drive health for {device.hostname}: {len(drives)} drives")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error collecting drive health for {device.hostname}: {e}")

    async def _collect_container_data(self, device: Device) -> None:
        """Collect and store container data for a device"""
        ssh_info = SSHConnectionInfo(
            host=device.ip_address,
            port=device.ssh_port or 22,
            username=device.ssh_username or "root"
        )
        
        try:
            # Check if Docker is available
            docker_check = await execute_ssh_command(ssh_info, "docker --version")
            if not docker_check.stdout:
                logger.debug(f"Docker not available on {device.hostname}")
                return
            
            # Get container list with stats
            cmd = "docker ps -a --format '{{json .}}'"
            result = await execute_ssh_command(ssh_info, cmd)
            
            if not result.stdout:
                return
            
            containers = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                try:
                    container_data = json.loads(line)
                    container_id = container_data.get('ID', '')
                    container_name = container_data.get('Names', '').lstrip('/')
                    
                    if not container_id:
                        continue
                    
                    # Get detailed stats for this container
                    stats_cmd = f"docker stats --no-stream --format '{{{{json .}}}}' {container_id}"
                    stats_result = await execute_ssh_command(ssh_info, stats_cmd)
                    
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
                        cpu_str = stats_data.get('CPUPerc', '0.00%').rstrip('%')
                        try:
                            cpu_usage = float(cpu_str)
                        except ValueError:
                            pass
                        
                        mem_usage = stats_data.get('MemUsage', '0B / 0B')
                        if ' / ' in mem_usage:
                            usage_str, limit_str = mem_usage.split(' / ')
                            memory_usage_bytes = self._parse_bytes(usage_str)
                            memory_limit_bytes = self._parse_bytes(limit_str)
                    
                    # Create container snapshot
                    snapshot = ContainerSnapshot(
                        device_id=device.id,
                        time=datetime.now(timezone.utc),
                        container_id=container_id,
                        container_name=container_name,
                        image=container_data.get('Image', ''),
                        status=container_data.get('Status', ''),
                        state=container_data.get('State', ''),
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
                        networks=[]
                    )
                    
                    containers.append(snapshot)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse container JSON: {line}")
                    continue
            
            # Add all container snapshots
            for container in containers:
                self.db.add(container)
            
            await self.db.commit()
            
            logger.debug(f"Collected container data for {device.hostname}: {len(containers)} containers")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error collecting container data for {device.hostname}: {e}")

    def _parse_bytes(self, size_str: str) -> int:
        """Parse size string to bytes"""
        size_str = size_str.strip()
        if not size_str or size_str == '--':
            return 0
        
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4
        }
        
        for suffix, multiplier in multipliers.items():
            if size_str.upper().endswith(suffix):
                try:
                    value = float(size_str[:-len(suffix)])
                    return int(value * multiplier)
                except ValueError:
                    break
        
        # Try to parse as plain number
        try:
            return int(float(size_str))
        except ValueError:
            return 0

    async def poll_device_once(self, device_id: UUID) -> Dict[str, Any]:
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Device polled successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in manual poll for device {device_id}: {e}")
            return {
                "device_id": str(device_id),
                "hostname": device.hostname,
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

    async def get_polling_status(self) -> Dict[str, Any]:
        """Get current polling service status"""
        return {
            "is_running": self.is_running,
            "poll_interval_seconds": self.poll_interval,
            "active_devices": len(self.polling_tasks),
            "device_ids": [str(device_id) for device_id in self.polling_tasks.keys()]
        }