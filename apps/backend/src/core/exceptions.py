"""
Infrastructure Management MCP Server - Custom Exceptions

This module defines custom exception classes for infrastructure-specific errors,
providing structured error handling with detailed context information.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class InfrastructureException(Exception):
    """Base exception class for infrastructure-related errors"""

    def __init__(
        self,
        message: str,
        error_code: str = "INFRASTRUCTURE_ERROR",
        details: Optional[Dict[str, Any]] = None,
        hostname: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.hostname = hostname
        self.operation = operation
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "hostname": self.hostname,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
        }


class DatabaseConnectionError(InfrastructureException):
    """Raised when database connection fails"""

    def __init__(
        self, message: str = "Database connection failed", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, error_code="DATABASE_CONNECTION_ERROR", details=details)


class DatabaseOperationError(InfrastructureException):
    """Raised when database operation fails"""

    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_OPERATION_ERROR",
            details=details,
            operation=operation,
        )


class SSHConnectionError(InfrastructureException):
    """Raised when SSH connection to device fails"""

    def __init__(
        self, message: str, hostname: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="SSH_CONNECTION_ERROR",
            details=details or {},
            hostname=hostname,
            operation="ssh_connect",
        )


class SSHCommandError(InfrastructureException):
    """Raised when SSH command execution fails"""

    def __init__(
        self,
        message: str,
        command: str,
        hostname: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
    ):
        details = {"command": command, "exit_code": exit_code, "stderr": stderr}

        super().__init__(
            message=message,
            error_code="SSH_COMMAND_ERROR",
            details=details,
            hostname=hostname,
            operation="ssh_execute",
        )


class SSHTimeoutError(InfrastructureException):
    """Raised when SSH operation times out"""

    def __init__(
        self,
        message: str = "SSH operation timed out",
        hostname: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        operation: Optional[str] = None,
    ):
        details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            error_code="SSH_TIMEOUT_ERROR",
            details=details,
            hostname=hostname,
            operation=operation or "ssh_operation",
        )


class DeviceNotFoundError(InfrastructureException):
    """Raised when device is not found in registry"""

    def __init__(self, device_identifier: str, search_type: str = "id"):
        message = f"Device not found: {device_identifier}"
        details = {"device_identifier": device_identifier, "search_type": search_type}

        super().__init__(
            message=message,
            error_code="DEVICE_NOT_FOUND",
            details=details,
            operation="device_lookup",
        )


class DeviceOfflineError(InfrastructureException):
    """Raised when attempting to access offline device"""

    def __init__(self, hostname: str, last_seen: Optional[datetime] = None):
        message = f"Device is offline: {hostname}"
        details = {}
        if last_seen:
            details["last_seen"] = last_seen.isoformat()

        super().__init__(
            message=message,
            error_code="DEVICE_OFFLINE",
            details=details,
            hostname=hostname,
            operation="device_access",
        )


class AuthenticationError(InfrastructureException):
    """Raised when authentication fails"""

    def __init__(
        self,
        message: str = "Authentication failed",
        auth_type: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["auth_type"] = auth_type

        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            operation="authentication",
        )


class AuthorizationError(InfrastructureException):
    """Raised when authorization fails (insufficient permissions)"""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
    ):
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
        if resource:
            details["resource"] = resource

        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            operation="authorization",
        )


class RateLimitError(InfrastructureException):
    """Raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        retry_after: Optional[int] = None,
    ):
        details = {}
        if limit:
            details["limit"] = limit
        if window_seconds:
            details["window_seconds"] = window_seconds
        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=details,
            operation="rate_limiting",
        )


class ValidationError(InfrastructureException):
    """Raised when data validation fails"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        validation_type: str = "schema",
    ):
        details = {"validation_type": validation_type}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
            operation="data_validation",
        )


class ServiceUnavailableError(InfrastructureException):
    """Raised when a required service is unavailable"""

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = message or f"Service unavailable: {service_name}"
        details = details or {}
        details["service_name"] = service_name

        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            details=details,
            operation="service_access",
        )


class ContainerError(InfrastructureException):
    """Raised when container operations fail"""

    def __init__(
        self,
        message: str,
        container_name: Optional[str] = None,
        container_id: Optional[str] = None,
        hostname: Optional[str] = None,
        operation: str = "container_operation",
    ):
        details = {}
        if container_name:
            details["container_name"] = container_name
        if container_id:
            details["container_id"] = container_id

        super().__init__(
            message=message,
            error_code="CONTAINER_ERROR",
            details=details,
            hostname=hostname,
            operation=operation,
        )


class ZFSError(InfrastructureException):
    """Raised when ZFS operations fail"""

    def __init__(
        self,
        message: str,
        pool_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
        hostname: Optional[str] = None,
        operation: str = "zfs_operation",
    ):
        details = {}
        if pool_name:
            details["pool_name"] = pool_name
        if dataset_name:
            details["dataset_name"] = dataset_name

        super().__init__(
            message=message,
            error_code="ZFS_ERROR",
            details=details,
            hostname=hostname,
            operation=operation,
        )


class NetworkError(InfrastructureException):
    """Raised when network operations fail"""

    def __init__(
        self,
        message: str,
        interface_name: Optional[str] = None,
        network_name: Optional[str] = None,
        hostname: Optional[str] = None,
        operation: str = "network_operation",
    ):
        details = {}
        if interface_name:
            details["interface_name"] = interface_name
        if network_name:
            details["network_name"] = network_name

        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            details=details,
            hostname=hostname,
            operation=operation,
        )


class BackupError(InfrastructureException):
    """Raised when backup operations fail"""

    def __init__(
        self,
        message: str,
        backup_name: Optional[str] = None,
        backup_type: Optional[str] = None,
        hostname: Optional[str] = None,
        operation: str = "backup_operation",
    ):
        details = {}
        if backup_name:
            details["backup_name"] = backup_name
        if backup_type:
            details["backup_type"] = backup_type

        super().__init__(
            message=message,
            error_code="BACKUP_ERROR",
            details=details,
            hostname=hostname,
            operation=operation,
        )


class ConfigurationError(InfrastructureException):
    """Raised when configuration is invalid or missing"""

    def __init__(
        self, message: str, config_key: Optional[str] = None, config_file: Optional[str] = None
    ):
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file

        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details,
            operation="configuration",
        )


class TimeoutError(InfrastructureException):
    """Raised when operations timeout"""

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[int] = None,
        operation: Optional[str] = None,
        hostname: Optional[str] = None,
    ):
        details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            error_code="OPERATION_TIMEOUT",
            details=details,
            hostname=hostname,
            operation=operation or "timeout_operation",
        )


class PermissionError(InfrastructureException):
    """Raised when file or system permissions are insufficient"""

    def __init__(
        self,
        message: str,
        resource_path: Optional[str] = None,
        required_permission: Optional[str] = None,
        hostname: Optional[str] = None,
    ):
        details = {}
        if resource_path:
            details["resource_path"] = resource_path
        if required_permission:
            details["required_permission"] = required_permission

        super().__init__(
            message=message,
            error_code="PERMISSION_ERROR",
            details=details,
            hostname=hostname,
            operation="permission_check",
        )


class ResourceNotFoundError(InfrastructureException):
    """Raised when a requested resource is not found"""

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        hostname: Optional[str] = None,
    ):
        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=details,
            hostname=hostname,
            operation="resource_lookup",
        )


class ResourceConflictError(InfrastructureException):
    """Raised when a resource conflict occurs (e.g., duplicate names)"""

    def __init__(
        self,
        message: str,
        resource_type: str,
        conflicting_value: Optional[str] = None,
        existing_resource_id: Optional[str] = None,
    ):
        details = {"resource_type": resource_type}
        if conflicting_value:
            details["conflicting_value"] = conflicting_value
        if existing_resource_id:
            details["existing_resource_id"] = existing_resource_id

        super().__init__(
            message=message,
            error_code="RESOURCE_CONFLICT",
            details=details,
            operation="resource_creation",
        )


class BusinessLogicError(InfrastructureException):
    """Raised when business logic validation fails"""

    def __init__(
        self,
        message: str,
        rule_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        details = {}
        if rule_name:
            details["rule_name"] = rule_name
        if context:
            details["context"] = context

        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=details,
            operation="business_validation",
        )


class ExternalServiceError(InfrastructureException):
    """Raised when external service calls fail"""

    def __init__(
        self,
        message: str,
        service_name: str,
        service_url: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        details = {"service_name": service_name}
        if service_url:
            details["service_url"] = service_url
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body[:1000]  # Limit response body size

        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details,
            operation="external_service_call",
        )


class SystemMonitoringError(InfrastructureException):
    """Raised when system monitoring operations fail"""

    def __init__(
        self,
        message: str,
        hostname: Optional[str] = None,
        operation: str = "system_monitoring",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="SYSTEM_MONITORING_ERROR",
            details=details or {},
            hostname=hostname,
            operation=operation,
        )
