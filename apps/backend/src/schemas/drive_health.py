"""
Drive health Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from apps.backend.src.schemas.common import PaginatedResponse, TimeRangeParams, HealthStatus


class DriveHealthBase(BaseModel):
    """Base drive health schema"""
    device_id: UUID = Field(description="Device identifier")
    drive_name: str = Field(..., max_length=100, description="Drive name (e.g., /dev/sda)")
    
    # Drive information
    drive_type: Optional[str] = Field(None, description="Drive type (ssd, hdd, nvme)")
    model: Optional[str] = Field(None, max_length=255, description="Drive model")
    serial_number: Optional[str] = Field(None, max_length=255, description="Drive serial number")
    capacity_bytes: Optional[int] = Field(None, ge=0, description="Drive capacity in bytes")
    
    # Health metrics
    temperature_celsius: Optional[int] = Field(None, description="Drive temperature in Celsius")
    power_on_hours: Optional[int] = Field(None, ge=0, description="Power-on hours")
    total_lbas_written: Optional[int] = Field(None, ge=0, description="Total LBAs written")
    total_lbas_read: Optional[int] = Field(None, ge=0, description="Total LBAs read")
    reallocated_sectors: Optional[int] = Field(None, ge=0, description="Reallocated sectors count")
    pending_sectors: Optional[int] = Field(None, ge=0, description="Pending sectors count")
    uncorrectable_errors: Optional[int] = Field(None, ge=0, description="Uncorrectable errors count")
    
    # Status indicators
    smart_status: Optional[str] = Field(None, description="SMART status (PASSED/FAILED/UNKNOWN)")
    smart_attributes: Dict[str, Any] = Field(default_factory=dict, description="SMART attributes")
    health_status: HealthStatus = Field(default=HealthStatus.UNKNOWN, description="Overall health status")
    
    @field_validator("drive_name")
    @classmethod
    def validate_drive_name(cls, v):
        # Basic validation for drive names
        if not v.startswith(("/dev/", "nvme", "sd", "hd")):
            if not any(v.startswith(prefix) for prefix in ["/dev/", "C:", "D:", "nvme"]):
                raise ValueError("Invalid drive name format")
        return v
    
    @field_validator("drive_type")
    @classmethod
    def validate_drive_type(cls, v):
        if v is not None:
            valid_types = ["ssd", "hdd", "nvme", "unknown"]
            if v.lower() not in valid_types:
                raise ValueError(f"Drive type must be one of: {', '.join(valid_types)}")
            return v.lower()
        return v
    
    @field_validator("smart_status")
    @classmethod
    def validate_smart_status(cls, v):
        if v is not None:
            valid_statuses = ["PASSED", "FAILED", "UNKNOWN"]
            if v.upper() not in valid_statuses:
                raise ValueError(f"SMART status must be one of: {', '.join(valid_statuses)}")
            return v.upper()
        return v
    
    @field_validator("temperature_celsius")
    @classmethod
    def validate_temperature(cls, v):
        if v is not None:
            if v < -40 or v > 100:  # Reasonable temperature range for drives
                raise ValueError("Temperature must be between -40 and 100 degrees Celsius")
        return v


class DriveHealthCreate(DriveHealthBase):
    """Schema for creating drive health record"""
    time: datetime = Field(default_factory=datetime.utcnow, description="Measurement timestamp")


class DriveHealthResponse(DriveHealthBase):
    """Schema for drive health response"""
    time: datetime = Field(description="Measurement timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class DriveHealthList(PaginatedResponse[DriveHealthResponse]):
    """Paginated list of drive health records"""
    pass


class DriveHealthQuery(TimeRangeParams):
    """Query parameters for drive health data"""
    device_ids: Optional[List[UUID]] = Field(None, description="Filter by device IDs")
    drive_names: Optional[List[str]] = Field(None, description="Filter by drive names")
    drive_types: Optional[List[str]] = Field(None, description="Filter by drive types")
    health_status: Optional[List[HealthStatus]] = Field(None, description="Filter by health status")
    smart_status: Optional[List[str]] = Field(None, description="Filter by SMART status")
    min_temperature: Optional[int] = Field(None, description="Minimum temperature filter")
    max_temperature: Optional[int] = Field(None, description="Maximum temperature filter")


class DriveHealthSummary(BaseModel):
    """Drive health summary for dashboard"""
    device_id: UUID = Field(description="Device identifier")
    hostname: Optional[str] = Field(description="Device hostname")
    drive_name: str = Field(description="Drive name")
    drive_type: Optional[str] = Field(description="Drive type")
    model: Optional[str] = Field(description="Drive model")
    capacity_gb: Optional[float] = Field(description="Drive capacity in GB")
    
    # Current status
    health_status: HealthStatus = Field(description="Overall health status")
    smart_status: Optional[str] = Field(description="SMART status")
    current_temperature: Optional[int] = Field(description="Current temperature")
    
    # Wear indicators
    power_on_hours: Optional[int] = Field(description="Total power-on hours")
    reallocated_sectors: Optional[int] = Field(description="Reallocated sectors")
    pending_sectors: Optional[int] = Field(description="Pending sectors")
    uncorrectable_errors: Optional[int] = Field(description="Uncorrectable errors")
    
    # Trends (24-hour)
    temperature_trend: Dict[str, float] = Field(description="24-hour temperature trend")
    wear_trend: Dict[str, float] = Field(description="Wear indicator trends")
    
    # Alerts
    active_alerts: List[str] = Field(description="Active health alerts")
    
    # Metadata
    last_updated: datetime = Field(description="Last health check timestamp")
    data_points_24h: int = Field(description="Number of data points in last 24 hours")
    
    class Config:
        from_attributes = True


class DriveHealthTrends(BaseModel):
    """Drive health trends over time"""
    device_id: UUID = Field(description="Device identifier")
    drive_name: str = Field(description="Drive name")
    
    # Weekly trends
    power_on_hours_weekly: List[int] = Field(description="Weekly power-on hours progression")
    temperature_weekly: List[float] = Field(description="Weekly average temperatures")
    lbas_written_weekly: List[int] = Field(description="Weekly LBAs written progression")
    lbas_read_weekly: List[int] = Field(description="Weekly LBAs read progression")
    
    # Health status history
    health_status_history: List[Dict[str, Any]] = Field(description="Health status changes over time")
    smart_status_history: List[Dict[str, Any]] = Field(description="SMART status changes over time")
    
    # Predictive indicators
    estimated_remaining_life: Optional[float] = Field(description="Estimated remaining life percentage")
    wear_leveling_indicator: Optional[float] = Field(description="Wear leveling indicator")
    
    # Metadata
    trend_period_days: int = Field(description="Trend analysis period in days")
    last_analysis: datetime = Field(description="Last trend analysis timestamp")
    
    class Config:
        from_attributes = True


class DriveHealthAlert(BaseModel):
    """Drive health alert"""
    device_id: UUID = Field(description="Device identifier")
    hostname: str = Field(description="Device hostname")
    drive_name: str = Field(description="Drive name")
    alert_type: str = Field(description="Alert type (temperature, smart, wear, etc.)")
    severity: str = Field(description="Alert severity (warning/critical)")
    message: str = Field(description="Alert message")
    current_value: Optional[float] = Field(description="Current metric value")
    threshold_value: Optional[float] = Field(description="Threshold that was exceeded")
    triggered_at: datetime = Field(description="Alert trigger timestamp")
    acknowledged: bool = Field(default=False, description="Whether alert has been acknowledged")
    
    class Config:
        from_attributes = True


class DriveHealthThresholds(BaseModel):
    """Drive health thresholds for alerting"""
    # Temperature thresholds
    temperature_warning: int = Field(default=55, description="Temperature warning threshold (°C)")
    temperature_critical: int = Field(default=70, description="Temperature critical threshold (°C)")
    
    # Sector thresholds
    reallocated_sectors_warning: int = Field(default=5, description="Reallocated sectors warning threshold")
    reallocated_sectors_critical: int = Field(default=20, description="Reallocated sectors critical threshold")
    pending_sectors_warning: int = Field(default=1, description="Pending sectors warning threshold")
    pending_sectors_critical: int = Field(default=5, description="Pending sectors critical threshold")
    
    # Error thresholds
    uncorrectable_errors_warning: int = Field(default=0, description="Uncorrectable errors warning threshold")
    uncorrectable_errors_critical: int = Field(default=1, description="Uncorrectable errors critical threshold")
    
    # Wear thresholds (for SSDs)
    wear_leveling_warning: int = Field(default=80, description="Wear leveling warning threshold (%)")
    wear_leveling_critical: int = Field(default=90, description="Wear leveling critical threshold (%)")
    
    @field_validator("temperature_critical")
    @classmethod
    def validate_temperature_critical(cls, v, info):
        if "temperature_warning" in info.data and v <= info.data["temperature_warning"]:
            raise ValueError("Temperature critical threshold must be higher than warning threshold")
        return v
    
    @field_validator("reallocated_sectors_critical")
    @classmethod
    def validate_reallocated_critical(cls, v, info):
        if "reallocated_sectors_warning" in info.data and v <= info.data["reallocated_sectors_warning"]:
            raise ValueError("Reallocated sectors critical threshold must be higher than warning threshold")
        return v


class DriveInventory(BaseModel):
    """Drive inventory summary"""
    device_id: UUID = Field(description="Device identifier")
    hostname: str = Field(description="Device hostname")
    drives: List[Dict[str, Any]] = Field(description="List of drives on the device")
    total_capacity_bytes: int = Field(description="Total storage capacity")
    total_drives: int = Field(description="Total number of drives")
    drives_by_type: Dict[str, int] = Field(description="Drive count by type")
    drives_by_health: Dict[str, int] = Field(description="Drive count by health status")
    last_inventory: datetime = Field(description="Last inventory update timestamp")
    
    class Config:
        from_attributes = True


class SmartAttribute(BaseModel):
    """Individual SMART attribute"""
    id: int = Field(description="SMART attribute ID")
    name: str = Field(description="Attribute name")
    value: int = Field(description="Current value")
    worst: int = Field(description="Worst value recorded")
    threshold: int = Field(description="Failure threshold")
    raw_value: int = Field(description="Raw value")
    when_failed: Optional[str] = Field(description="When the attribute failed (if applicable)")
    flags: str = Field(description="Attribute flags")


class SmartData(BaseModel):
    """Complete SMART data for a drive"""
    device_id: UUID = Field(description="Device identifier")
    drive_name: str = Field(description="Drive name")
    smart_status: str = Field(description="Overall SMART status")
    model_name: str = Field(description="Drive model name")
    serial_number: str = Field(description="Drive serial number")
    capacity: int = Field(description="Drive capacity in bytes")
    attributes: List[SmartAttribute] = Field(description="SMART attributes")
    self_test_log: List[Dict[str, Any]] = Field(description="Self-test log entries")
    error_log: List[Dict[str, Any]] = Field(description="Error log entries")
    collected_at: datetime = Field(description="Data collection timestamp")
    
    class Config:
        from_attributes = True