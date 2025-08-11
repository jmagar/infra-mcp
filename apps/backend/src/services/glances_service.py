"""
Glances API Service Layer

Provides comprehensive system monitoring via Glances API endpoints
with unified data collection integration and error handling.
"""

from datetime import UTC, datetime
import logging
from typing import Any, Optional

import httpx
from apps.backend.src.models.device import Device
from apps.backend.src.schemas.glances import (
    GlancesSystemMetricsResponse,
    GlancesCPUResponse,
    GlancesMemoryResponse,
    GlancesLoadResponse,
    GlancesUptimeResponse,
    GlancesNetworkResponse,
    GlancesProcessResponse,
    GlancesFileSystemResponse,
    GlancesDiskIOResponse,
    GlancesGPUResponse,
    GlancesSensorResponse,
)
from apps.backend.src.utils.glances_client import get_glances_client
from apps.backend.src.core.exceptions import DataCollectionError, DeviceNotFoundError, SSHConnectionError

logger = logging.getLogger(__name__)


class GlancesService:
    """Service layer for Glances API integration"""
    
    def __init__(self, device: Device):
        self.device = device
        self.base_url = device.glances_endpoint
        self.client = get_glances_client(self.base_url)
    
    async def get_system_metrics(self) -> GlancesSystemMetricsResponse:
        """Get comprehensive system metrics (CPU, memory, load, uptime)"""
        try:
            # Get all required metrics in parallel
            endpoints = ['cpu', 'mem', 'load', 'uptime', 'processcount']
            data = await self.client.get_multiple_endpoints(endpoints)
            
            # Validate we got all required data
            missing_endpoints = [ep for ep, result in data.items() if result is None]
            if missing_endpoints:
                raise DataCollectionError(
                    f"Failed to get data from endpoints: {missing_endpoints}"
                )
            
            # Parse CPU data
            cpu_data = data['cpu']
            if isinstance(cpu_data, list) and len(cpu_data) > 0:
                cpu_data = cpu_data[0]  # Take first CPU entry for overall stats
            
            cpu = GlancesCPUResponse(
                total=cpu_data.get('total', 0.0),
                user=cpu_data.get('user', 0.0),
                system=cpu_data.get('system', 0.0),
                idle=cpu_data.get('idle', 0.0),
                iowait=cpu_data.get('iowait'),
                steal=cpu_data.get('steal')
            )
            
            # Parse memory data
            mem_data = data['mem']
            memory = GlancesMemoryResponse(
                total=mem_data.get('total', 0),
                available=mem_data.get('available', 0),
                percent=mem_data.get('percent', 0.0),
                used=mem_data.get('used', 0),
                free=mem_data.get('free', 0),
                active=mem_data.get('active'),
                inactive=mem_data.get('inactive'),
                buffers=mem_data.get('buffers'),
                cached=mem_data.get('cached')
            )
            
            # Parse load data
            load_data = data['load']
            load = GlancesLoadResponse(
                min1=load_data.get('min1', 0.0),
                min5=load_data.get('min5', 0.0),
                min15=load_data.get('min15', 0.0),
                cpucore=load_data.get('cpucore', 1)
            )
            
            # Parse uptime data
            uptime_data = data['uptime']
            uptime = GlancesUptimeResponse(
                uptime=uptime_data if isinstance(uptime_data, str) else str(uptime_data)
            )
            
            # Parse process count
            process_count = data['processcount']
            if isinstance(process_count, dict):
                process_count = process_count.get('total', 0)
            elif isinstance(process_count, list):
                process_count = len(process_count)
            
            return GlancesSystemMetricsResponse(
                device_hostname=self.device.hostname,
                timestamp=datetime.now(UTC),
                cpu=cpu,
                memory=memory,
                load=load,
                uptime=uptime,
                process_count=process_count
            )
            
        except Exception as e:
            logger.error(f"Failed to get system metrics for {self.device.hostname}: {str(e)}")
            raise DataCollectionError(f"Failed to collect system metrics: {str(e)}")
    
    async def get_network_stats(self) -> list[GlancesNetworkResponse]:
        """Get network interface statistics"""
        try:
            data = await self.client.get_endpoint('network')
            
            if not isinstance(data, list):
                logger.warning(f"Expected list for network data, got {type(data)}")
                return []
            
            interfaces = []
            for interface in data:
                if not isinstance(interface, dict):
                    continue
                    
                interfaces.append(GlancesNetworkResponse(
                    interface_name=interface.get('interface_name', 'unknown'),
                    rx=interface.get('rx', 0),
                    tx=interface.get('tx', 0),
                    rx_per_sec=interface.get('rx_per_sec'),
                    tx_per_sec=interface.get('tx_per_sec'),
                    cumulative_rx=interface.get('cumulative_rx', interface.get('rx', 0)),
                    cumulative_tx=interface.get('cumulative_tx', interface.get('tx', 0)),
                    speed=interface.get('speed'),
                    is_up=interface.get('is_up', True)
                ))
            
            return interfaces
            
        except Exception as e:
            logger.error(f"Failed to get network stats for {self.device.hostname}: {str(e)}")
            raise DataCollectionError(f"Failed to collect network statistics: {str(e)}")
    
    async def get_process_list(self, sort_by: str = "cpu_percent") -> list[GlancesProcessResponse]:
        """Get running processes with optional sorting"""
        try:
            data = await self.client.get_endpoint('processlist')
            
            if not isinstance(data, list):
                logger.warning(f"Expected list for process data, got {type(data)}")
                return []
            
            processes = []
            for process in data:
                if not isinstance(process, dict):
                    continue
                    
                processes.append(GlancesProcessResponse(
                    pid=process.get('pid', 0),
                    name=process.get('name', 'unknown'),
                    username=process.get('username', 'unknown'),
                    cpu_percent=process.get('cpu_percent', 0.0),
                    memory_percent=process.get('memory_percent', 0.0),
                    memory_info=process.get('memory_info'),
                    status=process.get('status', 'unknown'),
                    cmdline=process.get('cmdline', [])
                ))
            
            # Sort processes by specified field
            if sort_by in ['cpu_percent', 'memory_percent']:
                processes.sort(key=lambda p: getattr(p, sort_by), reverse=True)
            
            return processes
            
        except Exception as e:
            logger.error(f"Failed to get process list for {self.device.hostname}: {str(e)}")
            raise DataCollectionError(f"Failed to collect process list: {str(e)}")
    
    async def get_file_system_usage(self) -> list[GlancesFileSystemResponse]:
        """Get file system usage for all mount points"""
        try:
            data = await self.client.get_endpoint('fs')
            
            if not isinstance(data, list):
                logger.warning(f"Expected list for filesystem data, got {type(data)}")
                return []
            
            filesystems = []
            for fs in data:
                if not isinstance(fs, dict):
                    continue
                    
                filesystems.append(GlancesFileSystemResponse(
                    device_name=fs.get('device_name', 'unknown'),
                    mnt_point=fs.get('mnt_point', '/'),
                    fs_type=fs.get('fs_type', 'unknown'),
                    size=fs.get('size', 0),
                    used=fs.get('used', 0),
                    free=fs.get('free', 0),
                    percent=fs.get('percent', 0.0)
                ))
            
            return filesystems
            
        except Exception as e:
            logger.error(f"Failed to get filesystem usage for {self.device.hostname}: {str(e)}")
            raise DataCollectionError(f"Failed to collect filesystem usage: {str(e)}")
    
    async def get_disk_io_stats(self) -> list[GlancesDiskIOResponse]:
        """Get disk I/O statistics"""
        try:
            data = await self.client.get_endpoint('diskio')
            
            if not isinstance(data, list):
                logger.warning(f"Expected list for diskio data, got {type(data)}")
                return []
            
            disks = []
            for disk in data:
                if not isinstance(disk, dict):
                    continue
                    
                disks.append(GlancesDiskIOResponse(
                    disk_name=disk.get('disk_name', 'unknown'),
                    read_count=disk.get('read_count', 0),
                    write_count=disk.get('write_count', 0),
                    read_bytes=disk.get('read_bytes', 0),
                    write_bytes=disk.get('write_bytes', 0),
                    time_since_update=disk.get('time_since_update', 0.0)
                ))
            
            return disks
            
        except Exception as e:
            logger.error(f"Failed to get disk I/O stats for {self.device.hostname}: {str(e)}")
            raise DataCollectionError(f"Failed to collect disk I/O statistics: {str(e)}")
    
    async def get_gpu_stats(self) -> list[GlancesGPUResponse]:
        """Get GPU statistics (if available)"""
        try:
            data = await self.client.get_endpoint('gpu')
            
            if not isinstance(data, list):
                # GPU data might not be available on all systems
                return []
            
            gpus = []
            for gpu in data:
                if not isinstance(gpu, dict):
                    continue
                    
                gpus.append(GlancesGPUResponse(
                    gpu_id=gpu.get('gpu_id', 0),
                    name=gpu.get('name', 'Unknown GPU'),
                    mem=gpu.get('mem'),
                    proc=gpu.get('proc'),
                    temperature=gpu.get('temperature'),
                    fan_speed=gpu.get('fan_speed')
                ))
            
            return gpus
            
        except Exception as e:
            logger.debug(f"GPU stats not available for {self.device.hostname}: {str(e)}")
            return []  # GPU stats are optional
    
    async def get_sensor_data(self) -> list[GlancesSensorResponse]:
        """Get sensor data (temperature, fans, power)"""
        try:
            data = await self.client.get_endpoint('sensors')
            
            if not isinstance(data, list):
                # Sensor data might not be available on all systems
                return []
            
            sensors = []
            for sensor in data:
                if not isinstance(sensor, dict):
                    continue
                    
                sensors.append(GlancesSensorResponse(
                    label=sensor.get('label', 'Unknown'),
                    value=sensor.get('value', 0.0),
                    warning=sensor.get('warning'),
                    critical=sensor.get('critical'),
                    unit=sensor.get('unit', ''),
                    type=sensor.get('type', 'unknown')
                ))
            
            return sensors
            
        except Exception as e:
            logger.debug(f"Sensor data not available for {self.device.hostname}: {str(e)}")
            return []  # Sensor data is optional
    
    async def get_all_system_data(self) -> dict[str, Any]:
        """Get all system data in a single optimized call"""
        try:
            # Get all available endpoints in parallel
            endpoints = [
                'cpu', 'mem', 'load', 'uptime', 'processcount',
                'network', 'processlist', 'fs', 'diskio', 'gpu', 'sensors'
            ]
            
            data = await self.client.get_multiple_endpoints(endpoints)
            
            # Process and structure the data
            result = {
                'system_metrics': None,
                'network_stats': [],
                'process_list': [],
                'filesystem_usage': [],
                'disk_io_stats': [],
                'gpu_stats': [],
                'sensor_data': []
            }
            
            # Build system metrics if we have the required data
            required_for_system = ['cpu', 'mem', 'load', 'uptime', 'processcount']
            if all(data.get(ep) is not None for ep in required_for_system):
                # Parse CPU data
                cpu_data = data['cpu']
                if isinstance(cpu_data, list) and len(cpu_data) > 0:
                    cpu_data = cpu_data[0]  # Take first CPU entry for overall stats
                
                cpu = GlancesCPUResponse(
                    total=cpu_data.get('total', 0.0),
                    user=cpu_data.get('user', 0.0),
                    system=cpu_data.get('system', 0.0),
                    idle=cpu_data.get('idle', 0.0),
                    iowait=cpu_data.get('iowait'),
                    steal=cpu_data.get('steal')
                )
                
                # Parse memory data
                mem_data = data['mem']
                memory = GlancesMemoryResponse(
                    total=mem_data.get('total', 0),
                    available=mem_data.get('available', 0),
                    percent=mem_data.get('percent', 0.0),
                    used=mem_data.get('used', 0),
                    free=mem_data.get('free', 0),
                    active=mem_data.get('active'),
                    inactive=mem_data.get('inactive'),
                    buffers=mem_data.get('buffers'),
                    cached=mem_data.get('cached')
                )
                
                # Parse load data
                load_data = data['load']
                load = GlancesLoadResponse(
                    min1=load_data.get('min1', 0.0),
                    min5=load_data.get('min5', 0.0),
                    min15=load_data.get('min15', 0.0),
                    cpucore=load_data.get('cpucore', 1)
                )
                
                # Parse uptime data
                uptime_data = data['uptime']
                uptime = GlancesUptimeResponse(
                    uptime=uptime_data if isinstance(uptime_data, str) else str(uptime_data)
                )
                
                # Parse process count
                process_count = data['processcount']
                if isinstance(process_count, dict):
                    process_count = process_count.get('total', 0)
                elif isinstance(process_count, list):
                    process_count = len(process_count)
                
                result['system_metrics'] = GlancesSystemMetricsResponse(
                    device_hostname=self.device.hostname,
                    timestamp=datetime.now(UTC),
                    cpu=cpu,
                    memory=memory,
                    load=load,
                    uptime=uptime,
                    process_count=process_count
                )
            
            # Process optional data
            if data.get('network'):
                result['network_stats'] = await self.get_network_stats()
            if data.get('processlist'):
                result['process_list'] = await self.get_process_list()
            if data.get('fs'):
                result['filesystem_usage'] = await self.get_file_system_usage()
            if data.get('diskio'):
                result['disk_io_stats'] = await self.get_disk_io_stats()
            if data.get('gpu'):
                result['gpu_stats'] = await self.get_gpu_stats()
            if data.get('sensors'):
                result['sensor_data'] = await self.get_sensor_data()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all system data for {self.device.hostname}: {str(e)}")
            raise DataCollectionError(f"Failed to collect system data: {str(e)}")
    
    async def test_connectivity(self) -> bool:
        """Test if Glances API is accessible"""
        try:
            return await self.client.test_connectivity()
        except Exception as e:
            logger.error(f"Connectivity test failed for {self.device.hostname}: {str(e)}")
            return False
    
    async def close(self) -> None:
        """Close client connections"""
        await self.client.close()