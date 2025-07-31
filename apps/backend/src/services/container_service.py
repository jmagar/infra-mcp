"""
Service layer for container-related business logic.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.models.device import Device
from apps.backend.src.models.container import ContainerSnapshot
from apps.backend.src.schemas.container import (
    ContainerSnapshotList, ContainerSummary, ContainerDetails, ContainerLogs,
    ContainerSnapshotResponse
)
from apps.backend.src.schemas.common import PaginationParams
from apps.backend.src.utils.ssh_client import get_ssh_client, SSHConnectionInfo, execute_ssh_command
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError, ContainerError, SSHConnectionError, SSHCommandError, DatabaseOperationError
)

logger = logging.getLogger(__name__)

class ContainerService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.ssh_client = get_ssh_client()

    async def get_device_by_id(self, device_id: UUID) -> Device:
        """Get device by ID or raise DeviceNotFoundError"""
        result = await self.db.execute(select(Device).where(Device.id == device_id))
        device = result.scalar_one_or_none()
        if not device:
            raise DeviceNotFoundError(str(device_id))
        return device

    def create_ssh_connection_info(self, device: Device) -> SSHConnectionInfo:
        """Create SSH connection info from device"""
        return SSHConnectionInfo(
            host=device.ip_address,
            port=device.ssh_port or 22,
            username=device.ssh_username or "root"
        )

    async def list_containers(
        self,
        pagination: PaginationParams,
        device_ids: Optional[List[UUID]] = None,
        container_names: Optional[List[str]] = None,
        images: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        states: Optional[List[str]] = None,
        since: Optional[str] = None,
        search: Optional[str] = None,
    ) -> ContainerSnapshotList:
        """List container snapshots with filtering and pagination"""
        
        query = select(ContainerSnapshot)
        count_query = select(func.count(ContainerSnapshot.container_id))
        
        filters = []
        
        if device_ids:
            filters.append(ContainerSnapshot.device_id.in_(device_ids))
        
        if container_names:
            filters.append(ContainerSnapshot.container_name.in_(container_names))
        
        if images:
            filters.append(ContainerSnapshot.image.in_(images))
        
        if statuses:
            filters.append(ContainerSnapshot.status.in_(statuses))
        
        if states:
            filters.append(ContainerSnapshot.state.in_(states))
        
        if since:
            # Parse since time (simplified)
            try:
                since_dt = datetime.fromisoformat(since)
                filters.append(ContainerSnapshot.time >= since_dt)
            except ValueError:
                logger.warning(f"Invalid since parameter: {since}")
        
        if search:
            search_filter = or_(
                ContainerSnapshot.container_name.ilike(f"%{search}%"),
                ContainerSnapshot.image.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(desc(ContainerSnapshot.time)).offset(
            (pagination.page - 1) * pagination.page_size
        ).limit(pagination.page_size)
        
        result = await self.db.execute(query)
        containers = result.scalars().all()
        
        # Convert to response models
        container_responses = [ContainerSnapshotResponse.model_validate(container) for container in containers]
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return ContainerSnapshotList(
            items=container_responses,
            total_count=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1
        )

    async def list_device_containers(
        self,
        device_id: UUID,
        live_data: bool = False
    ) -> List[ContainerSummary]:
        """List containers for a specific device"""
        device = await self.get_device_by_id(device_id)
        
        if live_data:
            # Get live container data via SSH
            ssh_info = self.create_ssh_connection_info(device)
            
            try:
                # Get container list
                cmd = "docker ps -a --format '{{json .}}'"
                result = await execute_ssh_command(ssh_info, cmd)
                
                containers = []
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            try:
                                container_data = json.loads(line)
                                
                                # Get additional stats
                                stats_cmd = f"docker stats --no-stream --format '{{{{json .}}}}' {container_data.get('ID', '')}"
                                stats_result = await execute_ssh_command(ssh_info, stats_cmd)
                                
                                stats_data = {}
                                if stats_result.stdout:
                                    try:
                                        stats_data = json.loads(stats_result.stdout.strip())
                                    except json.JSONDecodeError:
                                        logger.warning(f"Failed to parse stats for container {container_data.get('ID')}")
                                
                                # Parse CPU and memory usage
                                cpu_usage = 0.0
                                memory_usage_mb = 0.0
                                memory_limit_mb = 0.0
                                
                                if stats_data:
                                    cpu_str = stats_data.get('CPUPerc', '0.00%').rstrip('%')
                                    try:
                                        cpu_usage = float(cpu_str)
                                    except ValueError:
                                        pass
                                    
                                    mem_usage = stats_data.get('MemUsage', '0B / 0B')
                                    if ' / ' in mem_usage:
                                        usage_str, limit_str = mem_usage.split(' / ')
                                        memory_usage_mb = self._parse_memory_size(usage_str)
                                        memory_limit_mb = self._parse_memory_size(limit_str)
                                
                                containers.append(ContainerSummary(
                                    device_id=device_id,
                                    hostname=device.hostname,
                                    container_id=container_data.get('ID', ''),
                                    container_name=container_data.get('Names', '').lstrip('/'),
                                    image=container_data.get('Image', ''),
                                    status=container_data.get('Status', ''),
                                    state=container_data.get('State', ''),
                                    uptime=container_data.get('RunningFor', ''),
                                    cpu_usage_percent=cpu_usage,
                                    memory_usage_mb=memory_usage_mb,
                                    memory_limit_mb=memory_limit_mb,
                                    memory_usage_percent=(memory_usage_mb / memory_limit_mb * 100) if memory_limit_mb > 0 else 0.0,
                                    network_io_mb={"rx": 0.0, "tx": 0.0},  # Would need additional parsing
                                    block_io_mb={"read": 0.0, "write": 0.0},  # Would need additional parsing
                                    exposed_ports=container_data.get('Ports', '').split(', ') if container_data.get('Ports') else [],
                                    health_status=None,
                                    restart_count=0,  # Would need additional parsing
                                    created_at=None,  # Would need additional parsing
                                    last_updated=datetime.now(timezone.utc)
                                ))
                                
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse container JSON: {line}")
                                continue
                
                return containers
                
            except Exception as e:
                logger.error(f"Error getting live container data for device {device_id}: {e}")
                raise SSHCommandError(f"Failed to get container data: {str(e)}")
        
        else:
            # Get from database
            query = select(ContainerSnapshot).where(ContainerSnapshot.device_id == device_id)
            query = query.order_by(desc(ContainerSnapshot.time))
            
            result = await self.db.execute(query)
            containers = result.scalars().all()
            
            # Convert to summary format
            summaries = []
            for container in containers:
                summaries.append(ContainerSummary(
                    device_id=container.device_id,
                    hostname=device.hostname,
                    container_id=container.container_id,
                    container_name=container.container_name,
                    image=container.image,
                    status=container.status,
                    state=container.state,
                    uptime=None,
                    cpu_usage_percent=container.cpu_usage_percent,
                    memory_usage_mb=container.memory_usage_bytes / (1024 * 1024) if container.memory_usage_bytes else 0.0,
                    memory_limit_mb=container.memory_limit_bytes / (1024 * 1024) if container.memory_limit_bytes else 0.0,
                    memory_usage_percent=(container.memory_usage_bytes / container.memory_limit_bytes * 100) if container.memory_limit_bytes and container.memory_usage_bytes else 0.0,
                    network_io_mb={
                        "rx": container.network_bytes_recv / (1024 * 1024) if container.network_bytes_recv else 0.0,
                        "tx": container.network_bytes_sent / (1024 * 1024) if container.network_bytes_sent else 0.0
                    },
                    block_io_mb={
                        "read": container.block_read_bytes / (1024 * 1024) if container.block_read_bytes else 0.0,
                        "write": container.block_write_bytes / (1024 * 1024) if container.block_write_bytes else 0.0
                    },
                    exposed_ports=[f"{port['HostPort']}:{port['PrivatePort']}" for port in container.ports if port.get('HostPort')],
                    health_status=None,
                    restart_count=0,
                    created_at=None,
                    last_updated=container.time
                ))
            
            return summaries

    async def get_container_info(
        self,
        device_id: UUID,
        container_name: str,
        live_data: bool = False
    ) -> ContainerDetails:
        """Get detailed information about a specific container"""
        device = await self.get_device_by_id(device_id)
        
        if live_data:
            # Get live container details via SSH
            ssh_info = self.create_ssh_connection_info(device)
            
            try:
                # Get detailed container information
                cmd = f"docker inspect {container_name}"
                result = await execute_ssh_command(ssh_info, cmd)
                
                if not result.stdout:
                    raise ContainerError(f"Container '{container_name}' not found")
                
                try:
                    container_data = json.loads(result.stdout)[0]  # docker inspect returns an array
                except (json.JSONDecodeError, IndexError):
                    raise ContainerError(f"Failed to parse container details for '{container_name}'")
                
                # Extract container details
                config = container_data.get('Config', {})
                state = container_data.get('State', {})
                network_settings = container_data.get('NetworkSettings', {})
                host_config = container_data.get('HostConfig', {})
                
                return ContainerDetails(
                    device_id=device_id,
                    hostname=device.hostname,
                    container_id=container_data.get('Id', ''),
                    container_name=container_data.get('Name', '').lstrip('/'),
                    image=config.get('Image', ''),
                    image_id=container_data.get('Image', ''),
                    status=state.get('Status', ''),
                    state='running' if state.get('Running') else 'stopped',
                    running=state.get('Running', False),
                    paused=state.get('Paused', False),
                    restarting=state.get('Restarting', False),
                    oom_killed=state.get('OOMKilled', False),
                    dead=state.get('Dead', False),
                    pid=state.get('Pid'),
                    exit_code=state.get('ExitCode'),
                    error=state.get('Error'),
                    created_at=datetime.fromisoformat(container_data.get('Created', '').replace('Z', '+00:00')) if container_data.get('Created') else None,
                    started_at=datetime.fromisoformat(state.get('StartedAt', '').replace('Z', '+00:00')) if state.get('StartedAt') and state.get('StartedAt') != '0001-01-01T00:00:00Z' else None,
                    finished_at=datetime.fromisoformat(state.get('FinishedAt', '').replace('Z', '+00:00')) if state.get('FinishedAt') and state.get('FinishedAt') != '0001-01-01T00:00:00Z' else None,
                    command=config.get('Cmd', []),
                    args=[],  # Args are typically included in Cmd
                    working_dir=config.get('WorkingDir'),
                    entrypoint=config.get('Entrypoint', []),
                    user=config.get('User'),
                    environment={env.split('=', 1)[0]: env.split('=', 1)[1] if '=' in env else '' for env in config.get('Env', [])},
                    labels=config.get('Labels', {}),
                    network_mode=host_config.get('NetworkMode'),
                    networks=network_settings.get('Networks', {}),
                    ports=network_settings.get('Ports', {}),
                    mounts=container_data.get('Mounts', []),
                    memory_limit=host_config.get('Memory'),
                    cpu_limit=host_config.get('CpuQuota', 0) / 100000.0 if host_config.get('CpuQuota') and host_config.get('CpuQuota') > 0 else None,
                    health_status=state.get('Health', {}).get('Status') if state.get('Health') else None,
                    health_check=config.get('Healthcheck'),
                    restart_policy=host_config.get('RestartPolicy', {}),
                    restart_count=container_data.get('RestartCount', 0)
                )
                
            except Exception as e:
                logger.error(f"Error getting container details for {container_name} on device {device_id}: {e}")
                raise SSHCommandError(f"Failed to get container details: {str(e)}")
        
        else:
            # Get from database (latest snapshot)
            query = select(ContainerSnapshot).where(
                and_(
                    ContainerSnapshot.device_id == device_id,
                    ContainerSnapshot.container_name == container_name
                )
            ).order_by(desc(ContainerSnapshot.time)).limit(1)
            
            result = await self.db.execute(query)
            container = result.scalar_one_or_none()
            
            if not container:
                raise ContainerError(f"Container '{container_name}' not found in database")
            
            # Convert snapshot to details format
            return ContainerDetails(
                device_id=container.device_id,
                hostname=device.hostname,
                container_id=container.container_id,
                container_name=container.container_name,
                image=container.image,
                image_id=None,
                status=container.status,
                state=container.state,
                running=container.status == 'running',
                paused=container.state == 'paused',
                restarting=container.state == 'restarting',
                oom_killed=False,
                dead=container.state == 'dead',
                pid=None,
                exit_code=None,
                error=None,
                created_at=None,
                started_at=None,
                finished_at=None,
                command=[],
                args=[],
                working_dir=None,
                entrypoint=[],
                user=None,
                environment=container.environment,
                labels=container.labels,
                network_mode=None,
                networks=container.networks,
                ports=container.ports,
                mounts=container.volumes,
                memory_limit=container.memory_limit_bytes,
                cpu_limit=None,
                health_status=None,
                health_check=None,
                restart_policy={},
                restart_count=0
            )

    async def get_container_logs(
        self,
        device_id: UUID,
        container_name: str,
        since: Optional[str] = None,
        tail: Optional[int] = 100,
        timestamps: bool = True
    ) -> ContainerLogs:
        """Get logs for a specific container"""
        device = await self.get_device_by_id(device_id)
        ssh_info = self.create_ssh_connection_info(device)
        
        try:
            # Build docker logs command
            cmd_parts = ["docker", "logs"]
            
            if timestamps:
                cmd_parts.append("-t")
            
            if since:
                cmd_parts.extend(["--since", since])
            
            if tail:
                cmd_parts.extend(["--tail", str(tail)])
            
            cmd_parts.append(container_name)
            cmd = " ".join(cmd_parts)
            
            result = await execute_ssh_command(ssh_info, cmd)
            
            # Parse log lines
            log_entries = []
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        # Simple log parsing - in practice you'd want more sophisticated parsing
                        log_entries.append({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "message": line.strip(),
                            "stream": "stdout"  # Docker logs mix stdout/stderr
                        })
            
            return ContainerLogs(
                container_id="",  # Would need to resolve from name
                container_name=container_name,
                logs=log_entries,
                total_lines=len(log_entries),
                since=datetime.fromisoformat(since.replace('Z', '+00:00')) if since else None,
                until=None,
                tail=tail,
                timestamps=timestamps
            )
            
        except Exception as e:
            logger.error(f"Error getting container logs for {container_name} on device {device_id}: {e}")
            raise SSHCommandError(f"Failed to get container logs: {str(e)}")

    def _parse_memory_size(self, size_str: str) -> float:
        """Parse memory size string to MB"""
        size_str = size_str.strip()
        if not size_str or size_str == '--':
            return 0.0
        
        # Remove any non-numeric suffix and convert
        multipliers = {
            'B': 1 / (1024 * 1024),
            'KB': 1 / 1024,
            'MB': 1,
            'GB': 1024,
            'TB': 1024 * 1024
        }
        
        for suffix, multiplier in multipliers.items():
            if size_str.upper().endswith(suffix):
                try:
                    value = float(size_str[:-len(suffix)])
                    return value * multiplier
                except ValueError:
                    break
        
        # Try to parse as plain number (bytes)
        try:
            return float(size_str) / (1024 * 1024)
        except ValueError:
            return 0.0