"""
Service layer for metrics-related business logic.
"""

from datetime import UTC, datetime, timedelta
import json
import logging
from typing import Any

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    SSHCommandError,
)
from apps.backend.src.models.device import Device
from apps.backend.src.models.metrics import DriveHealth, SystemMetric
from apps.backend.src.schemas.backup import BackupStatusResponse
from apps.backend.src.schemas.common import PaginationParams
from apps.backend.src.schemas.drive_health import (
    DriveHealthList,
    DriveHealthResponse,
    DriveInventory,
)
from apps.backend.src.schemas.network import NetworkInterfaceResponse
from apps.backend.src.schemas.system_metrics import SystemMetricResponse, SystemMetricsList
from apps.backend.src.schemas.updates import UpdateSummary
from apps.backend.src.services.unified_data_collection import UnifiedDataCollectionService
from apps.backend.src.schemas.vm import VMStatusList, VMStatusResponse
from apps.backend.src.schemas.zfs import ZFSSnapshotList, ZFSSnapshotResponse, ZFSStatusResponse
from apps.backend.src.utils.ssh_client import SSHConnectionInfo, get_ssh_client

logger = logging.getLogger(__name__)


class MetricsService:
    def __init__(self, db_session: AsyncSession, unified_data_service: UnifiedDataCollectionService | None = None):
        self.db = db_session
        self.ssh_client = get_ssh_client()
        self.unified_data_service = unified_data_service

    async def get_device_by_id(self, device_id: UUID) -> Device:
        result = await self.db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        if not device:
            raise DeviceNotFoundError(str(device_id))
        return device

    def create_ssh_connection_info(self, device: Device) -> SSHConnectionInfo:
        return SSHConnectionInfo(
            host=str(device.hostname), 
            port=int(device.ssh_port or 22), 
            username=str(device.ssh_username or "root")
        )


    async def get_device_metrics(
        self,
        device_id: UUID,
        live: bool = False,
        time_range: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> SystemMetricResponse | SystemMetricsList:
        """Get system metrics for a device using unified data collection service with Glances"""
        device = await self.get_device_by_id(device_id)

        if live:
            # Use unified data collection service if available
            if self.unified_data_service:
                try:
                    # Get system metrics via unified data collection service
                    metrics_data = await self.unified_data_service.get_fresh_data(
                        data_type="system_metrics",
                        device_id=device_id,
                        force_refresh=True  # Live data should always be fresh
                    )
                    
                    # Convert to our response format
                    cpu_data = metrics_data.get("cpu", {})
                    memory_data = metrics_data.get("memory", {})
                    load_data = metrics_data.get("load", {})
                    
                    return SystemMetricResponse(
                        device_id=device_id,
                        cpu_usage_percent=cpu_data.get("total", 0.0),
                        memory_usage_percent=memory_data.get("percent", 0.0),
                        disk_usage_percent=0.0,  # Will be calculated from filesystem data
                        load_average_1m=load_data.get("min1", 0.0),
                        load_average_5m=load_data.get("min5", 0.0),
                        load_average_15m=load_data.get("min15", 0.0),
                        uptime_seconds=0,  # Could parse uptime string for actual value
                        time=datetime.fromisoformat(metrics_data.get("timestamp", datetime.now(UTC).isoformat())),
                    )
                    
                except Exception as e:
                    logger.error(f"Error getting metrics via unified data collection for device {device_id}: {e}")
                    raise SSHCommandError("unified_data_collection", f"Failed to get system metrics: {str(e)}")
            else:
                # Fallback to direct Glances service if unified service not available
                from apps.backend.src.services.glances_service import GlancesService
                glances_service = GlancesService(device)
                
                try:
                    if not await glances_service.test_connectivity():
                        raise DeviceNotFoundError(f"Glances API not accessible on {device.hostname}")
                    
                    metrics = await glances_service.get_system_metrics()
                    
                    return SystemMetricResponse(
                        device_id=device_id,
                        cpu_usage_percent=metrics.cpu.total,
                        memory_usage_percent=metrics.memory.percent,
                        disk_usage_percent=0.0,
                        load_average_1m=metrics.load.min1,
                        load_average_5m=metrics.load.min5,
                        load_average_15m=metrics.load.min15,
                        uptime_seconds=0,
                        time=metrics.timestamp,
                    )
                    
                except Exception as e:
                    logger.error(f"Error getting Glances metrics for device {device_id}: {e}")
                    raise SSHCommandError("glances", f"Failed to get Glances metrics: {str(e)}")
                finally:
                    await glances_service.close()

        else:
            # Get historical metrics from database
            query = select(SystemMetric).where(SystemMetric.device_id == device_id)

            if time_range:
                time_delta = self._parse_time_range(time_range)
                since = datetime.now(UTC) - time_delta
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
                page=pagination.page if pagination else 1,
                page_size=pagination.page_size if pagination else len(metrics),
                total_pages=1,
                has_next=False,
                has_previous=False,
            )

    async def get_device_drives(
        self,
        device_id: UUID,
        live: bool = False,
        drive_name: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> DriveInventory | DriveHealthList:
        """Get drive health and inventory for a device"""
        device = await self.get_device_by_id(device_id)

        if live:
            ssh_info = self.create_ssh_connection_info(device)

            try:
                # Get drive list and health info
                drives_cmd = "lsblk -J -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL"
                smart_cmd = "smartctl --scan | awk '{print $1}'"

                drives_result = await self.ssh_client.execute_command(ssh_info, drives_cmd)
                smart_result = await self.ssh_client.execute_command(ssh_info, smart_cmd)

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
                    hostname=str(device.hostname),
                    drives=drives,
                    total_drives=len(drives),
                    time=datetime.now(UTC),
                )

            except Exception as e:
                logger.error(f"Error getting live drive data for device {device_id}: {e}")
                raise SSHCommandError("ssh", f"Failed to get drive data: {str(e)}")

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
            drives_list = list(result.scalars().all())

            return DriveHealthList(
                items=[DriveHealthResponse.model_validate(drive) for drive in drives_list],
                page=pagination.page if pagination else 1,
                page_size=pagination.page_size if pagination else len(drives_list),
                total_pages=1,
                has_next=False,
                has_previous=False,
            )

    async def get_device_network(
        self,
        device_id: UUID,
        interface_name: str | None = None,
    ) -> list[NetworkInterfaceResponse]:
        """Get network interfaces and statistics using unified data collection service with Glances"""
        device = await self.get_device_by_id(device_id)

        # Use unified data collection service if available
        if self.unified_data_service:
            try:
                # Get network stats via unified data collection service
                network_data = await self.unified_data_service.get_fresh_data(
                    data_type="network_stats",
                    device_id=device_id,
                    force_refresh=True
                )
                
                # Convert to our response format
                interfaces = []
                for iface_data in network_data.get("interfaces", []):
                    # Filter by interface name if specified
                    if interface_name and iface_data.get("interface_name") != interface_name:
                        continue
                        
                    interfaces.append(
                        NetworkInterfaceResponse(
                            device_id=device_id,
                            interface_name=iface_data.get("interface_name", "unknown"),
                            state="up" if iface_data.get("is_up", False) else "down",
                            mtu=0,  # Not available in Glances network stats
                            mac_address="",  # Not available in Glances network stats
                            ip_addresses=[],  # Not available in Glances network stats
                            rx_bytes=iface_data.get("rx", 0),
                            tx_bytes=iface_data.get("tx", 0),
                            rx_packets=0,  # Not available in basic Glances network stats
                            tx_packets=0,  # Not available in basic Glances network stats
                            time=datetime.now(UTC),
                        )
                    )

                return interfaces

            except Exception as e:
                logger.error(f"Error getting network stats via unified data collection for device {device_id}: {e}")
                raise SSHCommandError("unified_data_collection", f"Failed to get network statistics: {str(e)}")
        else:
            # Fallback to direct Glances service if unified service not available
            from apps.backend.src.services.glances_service import GlancesService
            glances_service = GlancesService(device)

            try:
                if not await glances_service.test_connectivity():
                    raise DeviceNotFoundError(f"Glances API not accessible on {device.hostname}")
                
                network_stats = await glances_service.get_network_stats()
                
                # Filter by interface name if specified
                if interface_name:
                    network_stats = [iface for iface in network_stats if iface.interface_name == interface_name]
                
                interfaces = []
                for iface in network_stats:
                    interfaces.append(
                        NetworkInterfaceResponse(
                            device_id=device_id,
                            interface_name=iface.interface_name,
                            state="up" if iface.is_up else "down",
                            mtu=0,
                            mac_address="",
                            ip_addresses=[],
                            rx_bytes=iface.rx,
                            tx_bytes=iface.tx,
                            rx_packets=0,
                            tx_packets=0,
                            time=datetime.now(UTC),
                        )
                    )

                return interfaces

            except Exception as e:
                logger.error(f"Error getting Glances network stats for device {device_id}: {e}")
                raise SSHCommandError("glances", f"Failed to get network statistics: {str(e)}")
            finally:
                await glances_service.close()

    async def get_device_zfs_status(
        self,
        device_id: UUID,
        pool_name: str | None = None,
    ) -> list[ZFSStatusResponse]:
        """Get ZFS pool status and health"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            if pool_name:
                cmd = f"zpool status {pool_name}"
            else:
                cmd = "zpool status"

            result = await self.ssh_client.execute_command(ssh_info, cmd)

            # Parse zpool status output (simplified)
            pools = []
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                current_pool = None

                for line in lines:
                    if line.strip().startswith("pool:"):
                        pool_name_found = line.split(":")[1].strip()
                        current_pool = {
                            "pool_name": pool_name_found,
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
                                pool_name=current_pool["pool_name"],
                                state=current_pool["state"],
                                status=current_pool["status"],
                                scan=current_pool["scan"],
                                errors=current_pool["errors"],
                                time=datetime.now(UTC),
                            )
                        )

            return pools

        except Exception as e:
            logger.error(f"Error getting ZFS status for device {device_id}: {e}")
            raise SSHCommandError("ssh", f"Failed to get ZFS status: {str(e)}")

    async def get_device_zfs_snapshots(
        self,
        device_id: UUID,
        dataset: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> ZFSSnapshotList:
        """Get ZFS snapshots"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            if dataset:
                cmd = f"zfs list -t snapshot -H -o name,used,creation {dataset}"
            else:
                cmd = "zfs list -t snapshot -H -o name,used,creation"

            result = await self.ssh_client.execute_command(ssh_info, cmd)

            snapshots = []
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if line.strip():
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            snapshots.append(
                                ZFSSnapshotResponse(
                                    name=parts[0],
                                    used=parts[1],
                                    creation=parts[2],
                                    dataset=parts[0].split("@")[0] if "@" in parts[0] else "",
                                    snapshot=parts[0].split("@")[1]
                                    if "@" in parts[0]
                                    else parts[0],
                                )
                            )

            return ZFSSnapshotList(
                items=snapshots,
                page=pagination.page if pagination else 1,
                page_size=pagination.page_size if pagination else len(snapshots),
                total_pages=1,
                has_next=False,
                has_previous=False,
            )

        except Exception as e:
            logger.error(f"Error getting ZFS snapshots for device {device_id}: {e}")
            raise SSHCommandError("ssh", f"Failed to get ZFS snapshots: {str(e)}")

    async def get_device_vms(
        self,
        device_id: UUID,
        vm_name: str | None = None,
        state: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> VMStatusList:
        """Get virtual machine status"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            # Try different VM systems
            vms = []

            # Check for QEMU/KVM VMs
            cmd = "virsh list --all"
            result = await self.ssh_client.execute_command(ssh_info, cmd)

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
                                    vm_id=vm_id or vm_name_found,
                                    cpu_count=0,
                                    memory_mb=0,
                                    time=datetime.now(UTC),
                                )
                            )

            return VMStatusList(
                items=vms,
                page=pagination.page if pagination else 1,
                page_size=pagination.page_size if pagination else len(vms),
                total_pages=1,
                has_next=False,
                has_previous=False,
            )

        except Exception as e:
            logger.error(f"Error getting VMs for device {device_id}: {e}")
            raise SSHCommandError("ssh", f"Failed to get VMs: {str(e)}")


    async def get_device_backups(
        self,
        device_id: UUID,
        backup_type: str | None = None,
        status: str | None = None,
    ) -> list[BackupStatusResponse]:
        """Get backup status and history"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)

        try:
            # This would depend on the backup system in use
            # For now, return a placeholder response
            backups = [
                BackupStatusResponse(
                    device_id=device_id,
                    backup_type=backup_type or "full",
                    status=status or "completed",
                    start_time=datetime.now(UTC) - timedelta(hours=1),
                    end_time=datetime.now(UTC),
                    size_bytes=1024 * 1024 * 1024,  # 1GB
                    destination_path="/backup/location",
                    error_message=None,
                )
            ]

            return backups

        except Exception as e:
            logger.error(f"Error getting backup status for device {device_id}: {e}")
            raise SSHCommandError("ssh", f"Failed to get backup status: {str(e)}")

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
            package_updates: list[dict[str, Any]] = []

            # Try apt (Debian/Ubuntu)
            try:
                cmd = "apt list --upgradable 2>/dev/null | wc -l"
                result = await self.ssh_client.execute_command(ssh_info, cmd)
                if result.stdout.strip().isdigit():
                    updates_available = int(result.stdout.strip()) - 1  # Subtract header line
            except:
                pass

            # Try yum/dnf (RHEL/CentOS/Fedora)
            if updates_available == 0:
                try:
                    cmd = "yum check-update --quiet; echo $?"
                    result = await self.ssh_client.execute_command(ssh_info, cmd)
                    # Non-zero exit code means updates available
                except:
                    pass

            return UpdateSummary(
                device_id=device_id,
                hostname=str(device.hostname),
                total_updates=updates_available,
                security_updates=security_updates,
                auto_updates_enabled=False,
            )

        except Exception as e:
            logger.error(f"Error checking updates for device {device_id}: {e}")
            raise SSHCommandError("ssh", f"Failed to check updates: {str(e)}")

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
