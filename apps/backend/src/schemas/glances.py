"""
Glances API Response Schemas

Pydantic models for all Glances API responses with validation
and transformation support for unified data collection.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


class GlancesCPUResponse(BaseModel):
    """CPU usage statistics from Glances"""
    total: float = Field(..., description="Total CPU usage percentage")
    user: float = Field(..., description="User space CPU usage")
    system: float = Field(..., description="System CPU usage")
    idle: float = Field(..., description="Idle CPU percentage")
    iowait: Optional[float] = Field(None, description="I/O wait percentage")
    steal: Optional[float] = Field(None, description="Steal time percentage")


class GlancesMemoryResponse(BaseModel):
    """Memory usage statistics from Glances"""
    total: int = Field(..., description="Total memory in bytes")
    available: int = Field(..., description="Available memory in bytes")
    percent: float = Field(..., description="Memory usage percentage")
    used: int = Field(..., description="Used memory in bytes")
    free: int = Field(..., description="Free memory in bytes")
    active: Optional[int] = Field(None, description="Active memory in bytes")
    inactive: Optional[int] = Field(None, description="Inactive memory in bytes")
    buffers: Optional[int] = Field(None, description="Buffer memory in bytes")
    cached: Optional[int] = Field(None, description="Cached memory in bytes")


class GlancesLoadResponse(BaseModel):
    """System load average from Glances"""
    min1: float = Field(..., description="1-minute load average")
    min5: float = Field(..., description="5-minute load average")
    min15: float = Field(..., description="15-minute load average")
    cpucore: int = Field(..., description="Number of CPU cores")


class GlancesUptimeResponse(BaseModel):
    """System uptime from Glances"""
    uptime: str = Field(..., description="System uptime string")


class GlancesProcessResponse(BaseModel):
    """Process information from Glances"""
    pid: int = Field(..., description="Process ID")
    name: str = Field(..., description="Process name")
    username: str = Field(..., description="Process owner")
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    memory_info: Optional[dict[str, int]] = Field(None, description="Detailed memory info")
    status: str = Field(..., description="Process status")
    cmdline: list[str] = Field(default_factory=list, description="Command line arguments")


class GlancesNetworkResponse(BaseModel):
    """Network interface statistics from Glances"""
    interface_name: str = Field(..., description="Network interface name")
    rx: int = Field(..., description="Bytes received")
    tx: int = Field(..., description="Bytes transmitted")
    rx_per_sec: Optional[float] = Field(None, description="Receive rate per second")
    tx_per_sec: Optional[float] = Field(None, description="Transmit rate per second")
    cumulative_rx: int = Field(..., description="Cumulative bytes received")
    cumulative_tx: int = Field(..., description="Cumulative bytes transmitted")
    speed: Optional[int] = Field(None, description="Interface speed in Mbps")
    is_up: bool = Field(..., description="Interface status")


class GlancesFileSystemResponse(BaseModel):
    """File system usage from Glances"""
    device_name: str = Field(..., description="Device name")
    mnt_point: str = Field(..., description="Mount point")
    fs_type: str = Field(..., description="File system type")
    size: int = Field(..., description="Total size in bytes")
    used: int = Field(..., description="Used space in bytes")
    free: int = Field(..., description="Free space in bytes")
    percent: float = Field(..., description="Usage percentage")


class GlancesDiskIOResponse(BaseModel):
    """Disk I/O statistics from Glances"""
    disk_name: str = Field(..., description="Disk name")
    read_count: int = Field(..., description="Number of read operations")
    write_count: int = Field(..., description="Number of write operations")
    read_bytes: int = Field(..., description="Bytes read")
    write_bytes: int = Field(..., description="Bytes written")
    time_since_update: float = Field(..., description="Time since last update")


class GlancesGPUResponse(BaseModel):
    """GPU statistics from Glances (if available)"""
    gpu_id: int = Field(..., description="GPU ID")
    name: str = Field(..., description="GPU name")
    mem: Optional[float] = Field(None, description="Memory usage percentage")
    proc: Optional[float] = Field(None, description="Processor usage percentage")
    temperature: Optional[int] = Field(None, description="Temperature in Celsius")
    fan_speed: Optional[int] = Field(None, description="Fan speed percentage")


class GlancesSensorResponse(BaseModel):
    """Hardware sensor data from Glances"""
    label: str = Field(..., description="Sensor label")
    value: float = Field(..., description="Sensor value")
    warning: Optional[float] = Field(None, description="Warning threshold")
    critical: Optional[float] = Field(None, description="Critical threshold")
    unit: str = Field(..., description="Unit of measurement")
    type: str = Field(..., description="Sensor type (temperature, fan, etc.)")


class GlancesSystemMetricsResponse(BaseModel):
    """Combined system metrics response"""
    device_hostname: str = Field(..., description="Device hostname")
    timestamp: datetime = Field(..., description="Collection timestamp")
    cpu: GlancesCPUResponse
    memory: GlancesMemoryResponse
    load: GlancesLoadResponse
    uptime: GlancesUptimeResponse
    process_count: int = Field(..., description="Total number of processes")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Compatibility aliases for existing schemas
SystemMetricResponse = GlancesSystemMetricsResponse
NetworkInterfaceResponse = GlancesNetworkResponse