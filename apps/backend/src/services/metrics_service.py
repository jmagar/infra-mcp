"""
Service layer for metrics-related business logic.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_async_session
from apps.backend.src.core.config import get_settings
from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo, execute_ssh_command
from apps.backend.src.models.device import Device
from apps.backend.src.models.metrics import SystemMetric, DriveHealth
from apps.backend.src.schemas.system_metrics import SystemMetricResponse, SystemMetricsList
from apps.backend.src.schemas.drive_health import (
    DriveHealthResponse,
    DriveHealthList,
    DriveInventory,
)
from apps.backend.src.schemas.zfs import ZFSStatusResponse, ZFSSnapshotList
from apps.backend.src.schemas.network import NetworkInterfaceResponse
from apps.backend.src.schemas.vm import VMStatusResponse, VMStatusList
from apps.backend.src.schemas.logs import SystemLogResponse
from apps.backend.src.schemas.backup import BackupStatusResponse
from apps.backend.src.schemas.updates import UpdateSummary
from apps.backend.src.schemas.common import PaginationParams, HealthStatus
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    SSHConnectionError,
    SSHCommandError,
    DatabaseOperationError,
)

logger = logging.getLogger(__name__)


class MetricsService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.ssh_client = get_ssh_client()

    async def get_device_by_id(self, device_id: UUID) -> Device:
        result = await self.db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        if not device:
            raise DeviceNotFoundError(str(device_id))
        return device

    def create_ssh_connection_info(self, device: Device) -> SSHConnectionInfo:
        return SSHConnectionInfo(
            host=device.hostname, port=device.ssh_port or 22, username=device.ssh_username or "root"
        )

    async def get_device_metrics(
        self,
        device_id: UUID,
        live: bool = False,
        time_range: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> Union[SystemMetricResponse, SystemMetricsList]:
        """Get system metrics for a device"""
        device = await self.get_device_by_id(device_id)

        if live:
            # Get live metrics via SSH
            ssh_info = self.create_ssh_connection_info(device)

            try:
                # Get CPU, memory, disk usage via SSH
                cpu_cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | sed 's/%us,//'"
                memory_cmd = "free | grep Mem | awk '{printf \"%.2f\", ($3/$2) * 100.0}'"
                disk_cmd = "df -h / | awk 'NR==2{print $5}' | sed 's/%//'"
                load_cmd = "cat /proc/loadavg | awk '{print $1, $2, $3}'"
                uptime_cmd = "uptime -s"

                cpu_result = await execute_ssh_command(ssh_info, cpu_cmd)
                memory_result = await execute_ssh_command(ssh_info, memory_cmd)
                disk_result = await execute_ssh_command(ssh_info, disk_cmd)
                load_result = await execute_ssh_command(ssh_info, load_cmd)
                uptime_result = await execute_ssh_command(ssh_info, uptime_cmd)

                # Parse results
                cpu_usage = float(cpu_result.stdout.strip()) if cpu_result.stdout.strip() else 0.0
                memory_usage = (
                    float(memory_result.stdout.strip()) if memory_result.stdout.strip() else 0.0
                )
                disk_usage = (
                    float(disk_result.stdout.strip()) if disk_result.stdout.strip() else 0.0
                )
                load_avg = load_result.stdout.strip().split()

                return SystemMetricResponse(
                    device_id=device_id,
                    hostname=device.hostname,
                    cpu_usage_percent=cpu_usage,
                    memory_usage_percent=memory_usage,
                    disk_usage_percent=disk_usage,
                    load_average_1m=float(load_avg[0]) if len(load_avg) > 0 else 0.0,
                    load_average_5m=float(load_avg[1]) if len(load_avg) > 1 else 0.0,
                    load_average_15m=float(load_avg[2]) if len(load_avg) > 2 else 0.0,
                    uptime_seconds=0,  # Could parse uptime_result for actual value
                    timestamp=datetime.now(timezone.utc),
                )

            except Exception as e:
                logger.error(f"Error getting live metrics for device {device_id}: {e}")
                raise SSHCommandError(f"Failed to get live metrics: {str(e)}")

        else:
            # Get historical metrics from database
            query = select(SystemMetric).where(SystemMetric.device_id == device_id)

            if time_range:
                time_delta = self._parse_time_range(time_range)
                since = datetime.now(timezone.utc) - time_delta
                query = query.where(SystemMetric.time >= since)

            query = query.order_by(desc(SystemMetric.time))

            if pagination:
                query = query.offset((pagination.page - 1) * pagination.page_size).limit(
                    pagination.page_size
                )

            result = await self.db.execute(query)
            metrics = result.scalars().all()

            return SystemMetricsList(
                items=[SystemMetricResponse.model_validate(metric) for metric in metrics],
                total=len(metrics),
                page=pagination.page if pagination else 1,
                page_size=pagination.page_size if pagination else len(metrics),
                total_pages=1,
                has_next=False,
                has_prev=False,
            )

    async def get_device_drives(
        self,
        device_id: UUID,
        live: bool = False,
        drive_name: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> Union[DriveInventory, DriveHealthList]:
        """Get drive health and inventory for a device"""
        device = await self.get_device_by_id(device_id)

        if live:
            ssh_info = self.create_ssh_connection_info(device)

            try:
                # Get drive list and health info
                drives_cmd = "lsblk -J -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL"
                smart_cmd = "smartctl --scan | awk '{print $1}'"

                drives_result = await execute_ssh_command(ssh_info, drives_cmd)
                smart_result = await execute_ssh_command(ssh_info, smart_cmd)

                drives_data = (
                    json.loads(drives_result.stdout)
                    if drives_result.stdout
                    else {"blockdevices": []}
                )
                smart_devices = (
                    smart_result.stdout.strip().split("\n") if smart_result.stdout.strip() else []
                )

                drives = []
                for drive in drives_data.get("blockdevices", []):
                    if drive.get("type") == "disk":
                        drives.append(
                            {
                                "device": f"/dev/{drive['name']}",
                                "model": drive.get("model", "Unknown"),
                                "size": drive.get("size", "Unknown"),
                                "health_status": "unknown",
                                "temperature": None,
                                "smart_status": "unknown",
                            }
                        )

                return DriveInventory(
                    device_id=device_id,
                    hostname=device.hostname,
                    drives=drives,
                    total_drives=len(drives),
                    healthy_drives=0,
                    failed_drives=0,
                    last_updated=datetime.now(timezone.utc),
                )

            except Exception as e:
                logger.error(f"Error getting live drive data for device {device_id}: {e}")
                raise SSHCommandError(f"Failed to get drive data: {str(e)}")

        else:
            # Get from database
            query = select(DriveHealth).where(DriveHealth.device_id == device_id)

            if drive_name:
                query = query.where(DriveHealth.device.ilike(f"%{drive_name}%"))

            if pagination:
                query = query.offset((pagination.page - 1) * pagination.page_size).limit(
                    pagination.page_size
                )

            result = await self.db.execute(query)
            drives = result.scalars().all()

            return DriveHealthList(
                items=[DriveHealthResponse.model_validate(drive) for drive in drives],
                total=len(drives),
                page=pagination.page if pagination else 1,
                page_size=pagination.page_size if pagination else len(drives),
                total_pages=1,
                has_next=False,
                has_prev=False,
            )

    async def get_device_network(
        self,
        device_id: UUID,
        interface_name: Optional[str] = None,
    ) -> List[NetworkInterfaceResponse]:
        """Get network interfaces and statistics"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            # Get network interface info
            if interface_name:
                cmd = f"ip -j addr show {interface_name}"
            else:
                cmd = "ip -j addr show"

            result = await execute_ssh_command(ssh_info, cmd)
            interfaces_data = json.loads(result.stdout) if result.stdout else []

            interfaces = []
            for iface in interfaces_data:
                interfaces.append(
                    NetworkInterfaceResponse(
                        device_id=device_id,
                        interface_name=iface.get("ifname", "unknown"),
                        state=iface.get("operstate", "unknown"),
                        mtu=iface.get("mtu", 0),
                        mac_address=iface.get("address", ""),
                        ip_addresses=[addr.get("local", "") for addr in iface.get("addr_info", [])],
                        rx_bytes=0,  # Would need additional parsing from /proc/net/dev
                        tx_bytes=0,
                        rx_packets=0,
                        tx_packets=0,
                        timestamp=datetime.now(timezone.utc),
                    )
                )

            return interfaces

        except Exception as e:
            logger.error(f"Error getting network interfaces for device {device_id}: {e}")
            raise SSHCommandError(f"Failed to get network interfaces: {str(e)}")

    async def get_device_zfs_status(
        self,
        device_id: UUID,
        pool_name: Optional[str] = None,
    ) -> List[ZFSStatusResponse]:
        """Get ZFS pool status and health"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            if pool_name:
                cmd = f"zpool status {pool_name}"
            else:
                cmd = "zpool status"

            result = await execute_ssh_command(ssh_info, cmd)

            # Parse zpool status output (simplified)
            pools = []
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                current_pool = None

                for line in lines:
                    if line.strip().startswith("pool:"):
                        pool_name = line.split(":")[1].strip()
                        current_pool = {
                            "pool_name": pool_name,
                            "state": "unknown",
                            "status": "unknown",
                            "scan": "none",
                            "errors": "none",
                        }
                    elif line.strip().startswith("state:") and current_pool:
                        current_pool["state"] = line.split(":")[1].strip()
                    elif line.strip().startswith("status:") and current_pool:
                        current_pool["status"] = line.split(":")[1].strip()
                        pools.append(
                            ZFSStatusResponse(
                                device_id=device_id,
                                **current_pool,
                                last_scrub=None,
                                next_scrub=None,
                                timestamp=datetime.now(timezone.utc),
                            )
                        )

            return pools

        except Exception as e:
            logger.error(f"Error getting ZFS status for device {device_id}: {e}")
            raise SSHCommandError(f"Failed to get ZFS status: {str(e)}")

    async def get_device_zfs_snapshots(
        self,
        device_id: UUID,
        dataset: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> ZFSSnapshotList:
        """Get ZFS snapshots"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            if dataset:
                cmd = f"zfs list -t snapshot -H -o name,used,creation {dataset}"
            else:
                cmd = "zfs list -t snapshot -H -o name,used,creation"

            result = await execute_ssh_command(ssh_info, cmd)

            snapshots = []
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.strip():
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            snapshots.append(
                                {
                                    "name": parts[0],
                                    "used": parts[1],
                                    "creation": parts[2],
                                    "dataset": parts[0].split("@")[0] if "@" in parts[0] else "",
                                    "snapshot": parts[0].split("@")[1]
                                    if "@" in parts[0]
                                    else parts[0],
                                }
                            )

            return ZFSSnapshotList(
                items=snapshots,
                total=len(snapshots),
                page=pagination.page if pagination else 1,
                page_size=pagination.page_size if pagination else len(snapshots),
                total_pages=1,
                has_next=False,
                has_prev=False,
            )

        except Exception as e:
            logger.error(f"Error getting ZFS snapshots for device {device_id}: {e}")
            raise SSHCommandError(f"Failed to get ZFS snapshots: {str(e)}")

    async def get_device_vms(
        self,
        device_id: UUID,
        vm_name: Optional[str] = None,
        state: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> VMStatusList:
        """Get virtual machine status"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            # Try different VM systems
            vms = []

            # Check for QEMU/KVM VMs
            cmd = "virsh list --all"
            result = await execute_ssh_command(ssh_info, cmd)

            if result.stdout and "Id" in result.stdout:
                lines = result.stdout.strip().split("\n")[2:]  # Skip header
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            vm_id = parts[0] if parts[0] != "-" else None
                            vm_name_found = parts[1]
                            vm_state = " ".join(parts[2:])

                            if vm_name and vm_name.lower() not in vm_name_found.lower():
                                continue
                            if state and state.lower() not in vm_state.lower():
                                continue

                            vms.append(
                                VMStatusResponse(
                                    device_id=device_id,
                                    vm_id=vm_id,
                                    name=vm_name_found,
                                    state=vm_state,
                                    cpu_count=0,
                                    memory_mb=0,
                                    disk_gb=0,
                                    uptime=None,
                                    ip_address=None,
                                    timestamp=datetime.now(timezone.utc),
                                )
                            )

            return VMStatusList(
                items=vms,
                total=len(vms),
                page=pagination.page if pagination else 1,
                page_size=pagination.page_size if pagination else len(vms),
                total_pages=1,
                has_next=False,
                has_prev=False,
            )

        except Exception as e:
            logger.error(f"Error getting VMs for device {device_id}: {e}")
            raise SSHCommandError(f"Failed to get VMs: {str(e)}")

    async def get_device_logs(
        self,
        device_id: UUID,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        since: Optional[str] = "1h",
        lines: int = 100,
    ) -> List[SystemLogResponse]:
        """Get system logs"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            cmd_parts = ["journalctl", "--no-pager", f"--lines={lines}"]

            if since:
                cmd_parts.extend(["--since", f"'{since}'"])

            if service:
                cmd_parts.extend(["-u", service])

            if severity:
                priority_map = {
                    "emergency": "0",
                    "alert": "1",
                    "critical": "2",
                    "error": "3",
                    "warning": "4",
                    "notice": "5",
                    "info": "6",
                    "debug": "7",
                }
                if severity.lower() in priority_map:
                    cmd_parts.extend(["-p", priority_map[severity.lower()]])

            cmd = " ".join(cmd_parts)
            result = await execute_ssh_command(ssh_info, cmd)

            logs = []
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.strip():
                        logs.append(
                            SystemLogResponse(
                                device_id=device_id,
                                timestamp=datetime.now(
                                    timezone.utc
                                ),  # Would parse actual timestamp
                                service=service or "system",
                                severity=severity or "info",
                                message=line.strip(),
                                hostname=device.hostname,
                            )
                        )

            return logs

        except Exception as e:
            logger.error(f"Error getting logs for device {device_id}: {e}")
            raise SSHCommandError(f"Failed to get logs: {str(e)}")

    async def get_device_backups(
        self,
        device_id: UUID,
        backup_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[BackupStatusResponse]:
        """Get backup status and history"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            # This would depend on the backup system in use
            # For now, return a placeholder response
            backups = [
                BackupStatusResponse(
                    device_id=device_id,
                    backup_id="backup-001",
                    backup_type=backup_type or "full",
                    status=status or "completed",
                    start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                    end_time=datetime.now(timezone.utc),
                    size_bytes=1024 * 1024 * 1024,  # 1GB
                    destination="/backup/location",
                    success=True,
                    error_message=None,
                    timestamp=datetime.now(timezone.utc),
                )
            ]

            return backups

        except Exception as e:
            logger.error(f"Error getting backup status for device {device_id}: {e}")
            raise SSHCommandError(f"Failed to get backup status: {str(e)}")

    async def get_device_updates(
        self,
        device_id: UUID,
        check_type: str = "all",
    ) -> UpdateSummary:
        """Get available system updates"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            # Check for updates based on system type
            updates_available = 0
            security_updates = 0
            package_updates = []

            # Try apt (Debian/Ubuntu)
            try:
                cmd = "apt list --upgradable 2>/dev/null | wc -l"
                result = await execute_ssh_command(ssh_info, cmd)
                if result.stdout.strip().isdigit():
                    updates_available = int(result.stdout.strip()) - 1  # Subtract header line
            except:
                pass

            # Try yum/dnf (RHEL/CentOS/Fedora)
            if updates_available == 0:
                try:
                    cmd = "yum check-update --quiet; echo $?"
                    result = await execute_ssh_command(ssh_info, cmd)
                    # Non-zero exit code means updates available
                except:
                    pass

            return UpdateSummary(
                device_id=device_id,
                hostname=device.hostname,
                total_updates=updates_available,
                security_updates=security_updates,
                package_updates=package_updates,
                last_check=datetime.now(timezone.utc),
                next_check=datetime.now(timezone.utc) + timedelta(hours=24),
                auto_update_enabled=False,
                reboot_required=False,
            )

        except Exception as e:
            logger.error(f"Error checking updates for device {device_id}: {e}")
            raise SSHCommandError(f"Failed to check updates: {str(e)}")

    def _parse_time_range(self, time_range: str) -> timedelta:
        """Parse time range string to timedelta"""
        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            return timedelta(hours=hours)
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            return timedelta(days=days)
        elif time_range.endswith("m"):
            minutes = int(time_range[:-1])
            return timedelta(minutes=minutes)
        else:
            # Default to 1 hour
            return timedelta(hours=1)
