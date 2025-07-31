"""
Pydantic schemas for request/response validation and API documentation.
"""

# Import all schemas
from .device import (
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceList,
    DeviceSummary, DeviceHealth, DeviceHealthList, DeviceConnectionTest,
    DeviceCredentials, DeviceMetricsOverview
)
from .system_metrics import SystemMetricCreate, SystemMetricResponse, SystemMetricsList
from .drive_health import DriveHealthCreate, DriveHealthResponse, DriveHealthList
from .container import ContainerSnapshotCreate, ContainerSnapshotResponse, ContainerSnapshotList
from .zfs import (
    ZFSStatusCreate, ZFSStatusResponse, ZFSStatusList,
    ZFSSnapshotCreate, ZFSSnapshotResponse, ZFSSnapshotList,
    ZFSPoolSummary, ZFSHealthOverview, ZFSDatasetInfo, ZFSIntegrityCheck,
    ZFSFilter, ZFSAggregatedMetrics
)
from .network import (
    NetworkInterfaceCreate, NetworkInterfaceResponse, NetworkInterfaceList,
    DockerNetworkCreate, DockerNetworkResponse, DockerNetworkList,
    NetworkTopologyNode, NetworkTopology, NetworkInterfaceMetrics,
    NetworkHealthOverview, NetworkFilter, NetworkPortScan, NetworkConnectivityTest
)
from .vm import (
    VMStatusCreate, VMStatusResponse, VMStatusList,
    VMSummary, VMHealthOverview, VMPerformanceMetrics, VMResourceAllocation,
    VMOperation, VMOperationResult, VMSnapshot, VMFilter, VMBackup
)
from .logs import (
    SystemLogCreate, SystemLogResponse, SystemLogList,
    LogAnalytics, LogPattern, LogAlert, LogAlertTrigger, LogSearch,
    LogExport, LogRetentionPolicy, LogAggregation, LogHealthMetrics
)
from .backup import (
    BackupStatusCreate, BackupStatusUpdate, BackupStatusResponse, BackupStatusList,
    BackupSchedule, BackupPolicy, BackupHealthOverview, BackupMetrics,
    BackupVerification, BackupRestore, BackupRestoreResult, BackupFilter
)
from .updates import (
    SystemUpdateCreate, SystemUpdateUpdate, SystemUpdateResponse, SystemUpdateList,
    UpdateSummary, UpdateHealthOverview, UpdateInstallation, UpdateInstallationResult,
    UpdatePolicy, UpdateSchedule, VulnerabilityInfo, ComplianceReport,
    UpdateFilter, UpdateMetrics
)
from .user import (
    UserCreate, UserUpdate, UserResponse, UserList, UserProfile,
    UserLoginRequest, UserLoginResponse, UserRefreshTokenRequest,
    UserChangePasswordRequest, UserResetPasswordRequest, UserResetPasswordConfirm,
    UserEmailVerificationRequest, UserSessionResponse, UserSessionList,
    UserAPIKeyCreate, UserAPIKeyResponse, UserAPIKeyCreated, UserAPIKeyList,
    UserAuditLogResponse, UserAuditLogList, UserActivitySummary, UserSecuritySettings
)
from apps.backend.src.schemas.common import (
    HealthCheckResponse, PaginationParams, TimeRangeParams, APIResponse, ErrorResponse,
    PaginatedResponse, DatabaseHealthInfo, DeviceFilter, TimeSeriesAggregation,
    TimeSeriesInterval, AggregationParams, MetricFilter, SortParams, BulkOperationResponse,
    DeviceStatus, LogLevel, HealthStatus, StatusResponse, CreatedResponse, UpdatedResponse,
    DeletedResponse, ValidationErrorResponse, HealthMetrics, OperationResult, SearchParams,
    RateLimitInfo, SystemInfo
)

__all__ = [
    # Device schemas
    "DeviceCreate", "DeviceUpdate", "DeviceResponse", "DeviceList",
    "DeviceSummary", "DeviceHealth", "DeviceHealthList", "DeviceConnectionTest",
    "DeviceCredentials", "DeviceMetricsOverview",
    
    # System metrics schemas
    "SystemMetricCreate", "SystemMetricResponse", "SystemMetricsList",
    
    # Drive health schemas
    "DriveHealthCreate", "DriveHealthResponse", "DriveHealthList",
    
    # Container schemas
    "ContainerSnapshotCreate", "ContainerSnapshotResponse", "ContainerSnapshotList",
    
    # ZFS schemas
    "ZFSStatusCreate", "ZFSStatusResponse", "ZFSStatusList",
    "ZFSSnapshotCreate", "ZFSSnapshotResponse", "ZFSSnapshotList",
    "ZFSPoolSummary", "ZFSHealthOverview", "ZFSDatasetInfo", "ZFSIntegrityCheck",
    "ZFSFilter", "ZFSAggregatedMetrics",
    
    # Network schemas
    "NetworkInterfaceCreate", "NetworkInterfaceResponse", "NetworkInterfaceList",
    "DockerNetworkCreate", "DockerNetworkResponse", "DockerNetworkList",
    "NetworkTopologyNode", "NetworkTopology", "NetworkInterfaceMetrics",
    "NetworkHealthOverview", "NetworkFilter", "NetworkPortScan", "NetworkConnectivityTest",
    
    # VM schemas
    "VMStatusCreate", "VMStatusResponse", "VMStatusList",
    "VMSummary", "VMHealthOverview", "VMPerformanceMetrics", "VMResourceAllocation",
    "VMOperation", "VMOperationResult", "VMSnapshot", "VMFilter", "VMBackup",
    
    # Log schemas
    "SystemLogCreate", "SystemLogResponse", "SystemLogList",
    "LogAnalytics", "LogPattern", "LogAlert", "LogAlertTrigger", "LogSearch",
    "LogExport", "LogRetentionPolicy", "LogAggregation", "LogHealthMetrics",
    
    # Backup schemas
    "BackupStatusCreate", "BackupStatusUpdate", "BackupStatusResponse", "BackupStatusList",
    "BackupSchedule", "BackupPolicy", "BackupHealthOverview", "BackupMetrics",
    "BackupVerification", "BackupRestore", "BackupRestoreResult", "BackupFilter",
    
    # Update schemas
    "SystemUpdateCreate", "SystemUpdateUpdate", "SystemUpdateResponse", "SystemUpdateList",
    "UpdateSummary", "UpdateHealthOverview", "UpdateInstallation", "UpdateInstallationResult",
    "UpdatePolicy", "UpdateSchedule", "VulnerabilityInfo", "ComplianceReport",
    "UpdateFilter", "UpdateMetrics",
    
    # User schemas
    "UserCreate", "UserUpdate", "UserResponse", "UserList", "UserProfile",
    "UserLoginRequest", "UserLoginResponse", "UserRefreshTokenRequest",
    "UserChangePasswordRequest", "UserResetPasswordRequest", "UserResetPasswordConfirm",
    "UserEmailVerificationRequest", "UserSessionResponse", "UserSessionList",
    "UserAPIKeyCreate", "UserAPIKeyResponse", "UserAPIKeyCreated", "UserAPIKeyList",
    "UserAuditLogResponse", "UserAuditLogList", "UserActivitySummary", "UserSecuritySettings",
    
    # Common schemas
    "HealthCheckResponse", "PaginationParams", "TimeRangeParams", "APIResponse", "ErrorResponse",
    "PaginatedResponse", "DatabaseHealthInfo", "DeviceFilter", "TimeSeriesAggregation",
    "TimeSeriesInterval", "AggregationParams", "MetricFilter", "SortParams", "BulkOperationResponse",
    "DeviceStatus", "LogLevel", "HealthStatus", "StatusResponse", "CreatedResponse", "UpdatedResponse",
    "DeletedResponse", "ValidationErrorResponse", "HealthMetrics", "OperationResult", "SearchParams",
    "RateLimitInfo", "SystemInfo"
]