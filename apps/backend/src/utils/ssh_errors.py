"""
Infrastructure Management MCP Server - SSH Error Classification and Handling

This module provides comprehensive error classification, retry logic, and specialized
error handling for SSH operations in infrastructure monitoring environments.
"""

import re
import logging
from enum import Enum
from typing import Dict, List, Optional, Type, Union, Pattern
from dataclasses import dataclass

import asyncssh

logger = logging.getLogger(__name__)


class SSHErrorType(Enum):
    """Classification of SSH errors for appropriate handling"""

    # Connection errors
    CONNECTION_REFUSED = "connection_refused"
    CONNECTION_TIMEOUT = "connection_timeout"
    HOST_UNREACHABLE = "host_unreachable"
    DNS_RESOLUTION_FAILED = "dns_resolution_failed"
    NETWORK_ERROR = "network_error"

    # Authentication errors
    AUTH_FAILED = "authentication_failed"
    KEY_NOT_FOUND = "key_not_found"
    KEY_PERMISSION_DENIED = "key_permission_denied"
    PASSPHRASE_REQUIRED = "passphrase_required"
    USER_NOT_FOUND = "user_not_found"

    # Permission errors
    PERMISSION_DENIED = "permission_denied"
    COMMAND_NOT_FOUND = "command_not_found"
    ACCESS_DENIED = "access_denied"
    SUDO_REQUIRED = "sudo_required"

    # System errors
    DISK_FULL = "disk_full"
    OUT_OF_MEMORY = "out_of_memory"
    SYSTEM_OVERLOAD = "system_overload"
    SERVICE_UNAVAILABLE = "service_unavailable"

    # Command execution errors
    COMMAND_TIMEOUT = "command_timeout"
    COMMAND_FAILED = "command_failed"
    INVALID_COMMAND = "invalid_command"
    RESOURCE_BUSY = "resource_busy"

    # SSH protocol errors
    PROTOCOL_ERROR = "protocol_error"
    KEY_EXCHANGE_FAILED = "key_exchange_failed"
    CHANNEL_OPEN_FAILED = "channel_open_failed"

    # Infrastructure specific
    CONTAINER_NOT_RUNNING = "container_not_running"
    SERVICE_NOT_INSTALLED = "service_not_installed"
    MOUNT_POINT_UNAVAILABLE = "mount_point_unavailable"
    ZFS_POOL_UNAVAILABLE = "zfs_pool_unavailable"

    # Generic/Unknown
    UNKNOWN_ERROR = "unknown_error"
    TEMPORARY_FAILURE = "temporary_failure"


@dataclass
class SSHErrorInfo:
    """Information about an SSH error for handling decisions"""

    error_type: SSHErrorType
    is_retryable: bool
    retry_delay: float
    max_retries: int
    recovery_suggestion: Optional[str] = None
    escalation_required: bool = False


class SSHErrorClassifier:
    """
    Classify SSH errors and provide appropriate handling strategies.

    Uses pattern matching and exception type analysis to determine error types
    and suggest appropriate retry and recovery strategies.
    """

    # Error pattern mappings
    ERROR_PATTERNS: Dict[SSHErrorType, List[Pattern[str]]] = {
        SSHErrorType.CONNECTION_REFUSED: [
            re.compile(r"connection refused", re.IGNORECASE),
            re.compile(r"no route to host", re.IGNORECASE),
            re.compile(r"port (\d+): connection refused", re.IGNORECASE),
        ],
        SSHErrorType.CONNECTION_TIMEOUT: [
            re.compile(r"connection timed out", re.IGNORECASE),
            re.compile(r"timeout during connect", re.IGNORECASE),
            re.compile(r"connection timeout", re.IGNORECASE),
        ],
        SSHErrorType.HOST_UNREACHABLE: [
            re.compile(r"no route to host", re.IGNORECASE),
            re.compile(r"host unreachable", re.IGNORECASE),
            re.compile(r"network is unreachable", re.IGNORECASE),
        ],
        SSHErrorType.DNS_RESOLUTION_FAILED: [
            re.compile(r"name or service not known", re.IGNORECASE),
            re.compile(r"hostname lookup failed", re.IGNORECASE),
            re.compile(r"could not resolve hostname", re.IGNORECASE),
        ],
        SSHErrorType.AUTH_FAILED: [
            re.compile(r"authentication failed", re.IGNORECASE),
            re.compile(r"permission denied", re.IGNORECASE),
            re.compile(r"invalid user", re.IGNORECASE),
            re.compile(r"login incorrect", re.IGNORECASE),
        ],
        SSHErrorType.KEY_NOT_FOUND: [
            re.compile(r"no such file or directory.*\.pem", re.IGNORECASE),
            re.compile(r"key file not found", re.IGNORECASE),
            re.compile(r"could not load private key", re.IGNORECASE),
        ],
        SSHErrorType.PASSPHRASE_REQUIRED: [
            re.compile(r"passphrase required", re.IGNORECASE),
            re.compile(r"bad decrypt", re.IGNORECASE),
            re.compile(r"invalid format", re.IGNORECASE),
        ],
        SSHErrorType.COMMAND_NOT_FOUND: [
            re.compile(r"command not found", re.IGNORECASE),
            re.compile(r"no such file or directory", re.IGNORECASE),
            re.compile(r"not found", re.IGNORECASE),
        ],
        SSHErrorType.PERMISSION_DENIED: [
            re.compile(r"permission denied", re.IGNORECASE),
            re.compile(r"operation not permitted", re.IGNORECASE),
            re.compile(r"access denied", re.IGNORECASE),
        ],
        SSHErrorType.SUDO_REQUIRED: [
            re.compile(r"sudo: required", re.IGNORECASE),
            re.compile(r"must be root", re.IGNORECASE),
            re.compile(r"operation requires root", re.IGNORECASE),
        ],
        SSHErrorType.DISK_FULL: [
            re.compile(r"no space left on device", re.IGNORECASE),
            re.compile(r"disk full", re.IGNORECASE),
            re.compile(r"file system full", re.IGNORECASE),
        ],
        SSHErrorType.OUT_OF_MEMORY: [
            re.compile(r"out of memory", re.IGNORECASE),
            re.compile(r"cannot allocate memory", re.IGNORECASE),
            re.compile(r"memory allocation failed", re.IGNORECASE),
        ],
        SSHErrorType.SYSTEM_OVERLOAD: [
            re.compile(r"load average", re.IGNORECASE),
            re.compile(r"system overloaded", re.IGNORECASE),
            re.compile(r"too many processes", re.IGNORECASE),
        ],
        SSHErrorType.COMMAND_TIMEOUT: [
            re.compile(r"command timed out", re.IGNORECASE),
            re.compile(r"execution timeout", re.IGNORECASE),
            re.compile(r"timeout waiting", re.IGNORECASE),
        ],
        SSHErrorType.RESOURCE_BUSY: [
            re.compile(r"resource temporarily unavailable", re.IGNORECASE),
            re.compile(r"device or resource busy", re.IGNORECASE),
            re.compile(r"try again later", re.IGNORECASE),
        ],
        SSHErrorType.CONTAINER_NOT_RUNNING: [
            re.compile(r"container .* is not running", re.IGNORECASE),
            re.compile(r"no such container", re.IGNORECASE),
            re.compile(r"container not found", re.IGNORECASE),
        ],
        SSHErrorType.SERVICE_NOT_INSTALLED: [
            re.compile(r"systemctl: command not found", re.IGNORECASE),
            re.compile(r"service .* not found", re.IGNORECASE),
            re.compile(r"unit .* not found", re.IGNORECASE),
        ],
        SSHErrorType.ZFS_POOL_UNAVAILABLE: [
            re.compile(r"no such pool", re.IGNORECASE),
            re.compile(r"pool .* not found", re.IGNORECASE),
            re.compile(r"zfs: command not found", re.IGNORECASE),
        ],
    }

    # Error handling configurations
    ERROR_CONFIGS: Dict[SSHErrorType, SSHErrorInfo] = {
        SSHErrorType.CONNECTION_REFUSED: SSHErrorInfo(
            error_type=SSHErrorType.CONNECTION_REFUSED,
            is_retryable=True,
            retry_delay=5.0,
            max_retries=3,
            recovery_suggestion="Check if SSH service is running on target host",
        ),
        SSHErrorType.CONNECTION_TIMEOUT: SSHErrorInfo(
            error_type=SSHErrorType.CONNECTION_TIMEOUT,
            is_retryable=True,
            retry_delay=2.0,
            max_retries=3,
            recovery_suggestion="Check network connectivity and firewall rules",
        ),
        SSHErrorType.HOST_UNREACHABLE: SSHErrorInfo(
            error_type=SSHErrorType.HOST_UNREACHABLE,
            is_retryable=True,
            retry_delay=10.0,
            max_retries=2,
            recovery_suggestion="Verify host IP address and network routing",
        ),
        SSHErrorType.DNS_RESOLUTION_FAILED: SSHErrorInfo(
            error_type=SSHErrorType.DNS_RESOLUTION_FAILED,
            is_retryable=True,
            retry_delay=5.0,
            max_retries=2,
            recovery_suggestion="Check DNS configuration or use IP address",
        ),
        SSHErrorType.AUTH_FAILED: SSHErrorInfo(
            error_type=SSHErrorType.AUTH_FAILED,
            is_retryable=False,
            retry_delay=0.0,
            max_retries=0,
            recovery_suggestion="Verify SSH credentials and authentication method",
            escalation_required=True,
        ),
        SSHErrorType.KEY_NOT_FOUND: SSHErrorInfo(
            error_type=SSHErrorType.KEY_NOT_FOUND,
            is_retryable=False,
            retry_delay=0.0,
            max_retries=0,
            recovery_suggestion="Check SSH private key file path and permissions",
            escalation_required=True,
        ),
        SSHErrorType.PASSPHRASE_REQUIRED: SSHErrorInfo(
            error_type=SSHErrorType.PASSPHRASE_REQUIRED,
            is_retryable=False,
            retry_delay=0.0,
            max_retries=0,
            recovery_suggestion="Provide passphrase for encrypted private key",
            escalation_required=True,
        ),
        SSHErrorType.PERMISSION_DENIED: SSHErrorInfo(
            error_type=SSHErrorType.PERMISSION_DENIED,
            is_retryable=False,
            retry_delay=0.0,
            max_retries=0,
            recovery_suggestion="Check user permissions or use sudo",
            escalation_required=True,
        ),
        SSHErrorType.COMMAND_NOT_FOUND: SSHErrorInfo(
            error_type=SSHErrorType.COMMAND_NOT_FOUND,
            is_retryable=False,
            retry_delay=0.0,
            max_retries=0,
            recovery_suggestion="Install required command or check PATH",
        ),
        SSHErrorType.SUDO_REQUIRED: SSHErrorInfo(
            error_type=SSHErrorType.SUDO_REQUIRED,
            is_retryable=False,
            retry_delay=0.0,
            max_retries=0,
            recovery_suggestion="Run command with sudo or as root user",
        ),
        SSHErrorType.DISK_FULL: SSHErrorInfo(
            error_type=SSHErrorType.DISK_FULL,
            is_retryable=True,
            retry_delay=30.0,
            max_retries=2,
            recovery_suggestion="Free up disk space on target system",
            escalation_required=True,
        ),
        SSHErrorType.OUT_OF_MEMORY: SSHErrorInfo(
            error_type=SSHErrorType.OUT_OF_MEMORY,
            is_retryable=True,
            retry_delay=60.0,
            max_retries=2,
            recovery_suggestion="Wait for memory to be freed or restart services",
            escalation_required=True,
        ),
        SSHErrorType.SYSTEM_OVERLOAD: SSHErrorInfo(
            error_type=SSHErrorType.SYSTEM_OVERLOAD,
            is_retryable=True,
            retry_delay=30.0,
            max_retries=3,
            recovery_suggestion="Wait for system load to decrease",
        ),
        SSHErrorType.COMMAND_TIMEOUT: SSHErrorInfo(
            error_type=SSHErrorType.COMMAND_TIMEOUT,
            is_retryable=True,
            retry_delay=10.0,
            max_retries=2,
            recovery_suggestion="Increase timeout or check command efficiency",
        ),
        SSHErrorType.RESOURCE_BUSY: SSHErrorInfo(
            error_type=SSHErrorType.RESOURCE_BUSY,
            is_retryable=True,
            retry_delay=15.0,
            max_retries=3,
            recovery_suggestion="Wait for resource to become available",
        ),
        SSHErrorType.CONTAINER_NOT_RUNNING: SSHErrorInfo(
            error_type=SSHErrorType.CONTAINER_NOT_RUNNING,
            is_retryable=True,
            retry_delay=5.0,
            max_retries=2,
            recovery_suggestion="Start the container or check container status",
        ),
        SSHErrorType.SERVICE_NOT_INSTALLED: SSHErrorInfo(
            error_type=SSHErrorType.SERVICE_NOT_INSTALLED,
            is_retryable=False,
            retry_delay=0.0,
            max_retries=0,
            recovery_suggestion="Install required service or package",
        ),
        SSHErrorType.ZFS_POOL_UNAVAILABLE: SSHErrorInfo(
            error_type=SSHErrorType.ZFS_POOL_UNAVAILABLE,
            is_retryable=True,
            retry_delay=10.0,
            max_retries=2,
            recovery_suggestion="Check ZFS pool status and import if necessary",
        ),
        SSHErrorType.TEMPORARY_FAILURE: SSHErrorInfo(
            error_type=SSHErrorType.TEMPORARY_FAILURE,
            is_retryable=True,
            retry_delay=5.0,
            max_retries=3,
            recovery_suggestion="Temporary system issue, retry may succeed",
        ),
        SSHErrorType.UNKNOWN_ERROR: SSHErrorInfo(
            error_type=SSHErrorType.UNKNOWN_ERROR,
            is_retryable=True,
            retry_delay=5.0,
            max_retries=1,
            recovery_suggestion="Unknown error, check logs for details",
        ),
    }

    @classmethod
    def classify_error(
        cls,
        exception: Optional[Exception] = None,
        stderr: Optional[str] = None,
        return_code: Optional[int] = None,
        command: Optional[str] = None,
    ) -> SSHErrorInfo:
        """
        Classify an SSH error and return handling information.

        Args:
            exception: Exception that occurred
            stderr: Command stderr output
            return_code: Command return code
            command: Command that was executed

        Returns:
            SSHErrorInfo: Error classification and handling info
        """
        # Combine all error text for analysis
        error_text = ""

        if exception:
            error_text += str(exception) + " "
        if stderr:
            error_text += stderr + " "
        if command:
            error_text += f" (command: {command})"

        # Check exception types first
        if exception:
            error_type = cls._classify_by_exception_type(exception)
            if error_type != SSHErrorType.UNKNOWN_ERROR:
                return cls.ERROR_CONFIGS[error_type]

        # Check return code patterns
        if return_code is not None:
            error_type = cls._classify_by_return_code(return_code, command)
            if error_type != SSHErrorType.UNKNOWN_ERROR:
                return cls.ERROR_CONFIGS[error_type]

        # Pattern matching on error text
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(error_text):
                    logger.debug(f"Classified error as {error_type.value}: {error_text[:100]}")
                    return cls.ERROR_CONFIGS[error_type]

        # Default classification
        logger.debug(f"Unclassified error: {error_text[:100]}")
        return cls.ERROR_CONFIGS[SSHErrorType.UNKNOWN_ERROR]

    @classmethod
    def _classify_by_exception_type(cls, exception: Exception) -> SSHErrorType:
        """Classify error based on exception type"""
        exception_type = type(exception).__name__

        if isinstance(exception, asyncssh.ConnectionLost):
            return SSHErrorType.CONNECTION_TIMEOUT
        elif isinstance(exception, asyncssh.PermissionDenied):
            return SSHErrorType.AUTH_FAILED
        elif isinstance(exception, asyncssh.HostKeyNotVerifiable):
            return SSHErrorType.PROTOCOL_ERROR
        elif isinstance(exception, ConnectionRefusedError):
            return SSHErrorType.CONNECTION_REFUSED
        elif isinstance(exception, TimeoutError):
            return SSHErrorType.CONNECTION_TIMEOUT
        elif "DNS" in str(exception) or "resolve" in str(exception).lower():
            return SSHErrorType.DNS_RESOLUTION_FAILED

        return SSHErrorType.UNKNOWN_ERROR

    @classmethod
    def _classify_by_return_code(
        cls, return_code: int, command: Optional[str] = None
    ) -> SSHErrorType:
        """Classify error based on command return code"""
        # Common return codes
        if return_code == 1:
            # Generic error - need to check command context
            if command and any(cmd in command.lower() for cmd in ["docker", "container"]):
                return SSHErrorType.CONTAINER_NOT_RUNNING
            return SSHErrorType.COMMAND_FAILED

        elif return_code == 2:
            return SSHErrorType.INVALID_COMMAND

        elif return_code == 126:
            return SSHErrorType.PERMISSION_DENIED

        elif return_code == 127:
            return SSHErrorType.COMMAND_NOT_FOUND

        elif return_code == 130:
            return SSHErrorType.COMMAND_TIMEOUT

        elif return_code == 255:
            return SSHErrorType.CONNECTION_REFUSED

        return SSHErrorType.UNKNOWN_ERROR

    @classmethod
    def should_retry(cls, error_info: SSHErrorInfo, attempt: int) -> bool:
        """
        Determine if operation should be retried.

        Args:
            error_info: Error classification information
            attempt: Current attempt number (0-based)

        Returns:
            bool: True if retry should be attempted
        """
        return error_info.is_retryable and attempt < error_info.max_retries

    @classmethod
    def get_retry_delay(cls, error_info: SSHErrorInfo, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff.

        Args:
            error_info: Error classification information
            attempt: Current attempt number (0-based)

        Returns:
            float: Delay in seconds before retry
        """
        if not error_info.is_retryable:
            return 0.0

        # Exponential backoff: base_delay * (1.5 ^ attempt)
        return error_info.retry_delay * (1.5**attempt)


class SSHHealthChecker:
    """
    Health checking and diagnostics for SSH connections and infrastructure.

    Provides utilities to test connectivity, diagnose common issues,
    and suggest remediation steps.
    """

    @staticmethod
    def create_diagnostic_commands() -> Dict[str, List[str]]:
        """Get diagnostic commands for different system aspects"""
        return {
            "connectivity": [
                "ping -c 1 8.8.8.8",  # Internet connectivity
                "netstat -tulpn | grep :22",  # SSH service status
                "systemctl is-active sshd || service ssh status",  # SSH service
            ],
            "system_health": [
                "uptime",  # System load
                "df -h",  # Disk space
                "free -m",  # Memory usage
                "ps aux --sort=-%cpu | head -10",  # Top CPU processes
            ],
            "docker_health": [
                "docker version",  # Docker availability
                "docker ps --format 'table {{.Names}}\\t{{.Status}}'",  # Container status
                "docker system df",  # Docker disk usage
            ],
            "zfs_health": [
                "zpool status",  # ZFS pool status
                "zfs list -t filesystem -o name,avail,used",  # ZFS filesystems
                "zpool iostat -v 1 1",  # ZFS I/O stats
            ],
            "network_health": [
                "ip link show",  # Network interfaces
                "ss -tulpn",  # Network connections
                "iptables -L -n | head -20",  # Firewall rules
            ],
        }

    @staticmethod
    async def diagnose_connection_failure(
        ssh_client, connection_info, original_error: Exception
    ) -> Dict[str, any]:
        """
        Diagnose SSH connection failure and suggest solutions.

        Args:
            ssh_client: SSH client instance
            connection_info: Connection configuration
            original_error: Original connection error

        Returns:
            Dict containing diagnostic information and suggestions
        """
        diagnosis = {
            "original_error": str(original_error),
            "error_type": SSHErrorClassifier.classify_error(exception=original_error),
            "tests_performed": [],
            "issues_found": [],
            "suggestions": [],
            "connectivity_status": "unknown",
        }

        # Basic connectivity test
        try:
            # Try to connect with minimal timeout
            basic_result = await ssh_client.execute_command(
                connection_info, "echo 'basic_test'", timeout=10
            )
            if basic_result.success:
                diagnosis["connectivity_status"] = "connected"
                diagnosis["tests_performed"].append("basic_connectivity: PASS")
            else:
                diagnosis["connectivity_status"] = "command_failed"
                diagnosis["issues_found"].append(f"Command execution failed: {basic_result.stderr}")

        except Exception as e:
            diagnosis["connectivity_status"] = "connection_failed"
            diagnosis["issues_found"].append(f"Connection failed: {str(e)}")

        # Add suggestions based on error type
        error_info = diagnosis["error_type"]
        if error_info.recovery_suggestion:
            diagnosis["suggestions"].append(error_info.recovery_suggestion)

        # Add specific diagnostic suggestions
        if error_info.error_type == SSHErrorType.CONNECTION_REFUSED:
            diagnosis["suggestions"].extend(
                [
                    "Verify SSH service is running: systemctl status sshd",
                    f"Check if port {connection_info.port} is open",
                    "Check firewall rules on target host",
                ]
            )
        elif error_info.error_type == SSHErrorType.AUTH_FAILED:
            diagnosis["suggestions"].extend(
                [
                    "Verify SSH username and credentials",
                    "Check SSH key file permissions (should be 600)",
                    "Verify user exists on target system",
                ]
            )
        elif error_info.error_type == SSHErrorType.DNS_RESOLUTION_FAILED:
            diagnosis["suggestions"].extend(
                [
                    f"Try using IP address instead of hostname: {connection_info.host}",
                    "Check DNS configuration",
                    "Verify hostname spelling",
                ]
            )

        return diagnosis


def get_common_ssh_errors() -> Dict[str, str]:
    """Get common SSH errors and their descriptions"""
    return {
        error_type.value: config.recovery_suggestion or "No specific guidance available"
        for error_type, config in SSHErrorClassifier.ERROR_CONFIGS.items()
        if config.recovery_suggestion
    }


def is_infrastructure_command_available(command_output: str, command: str) -> bool:
    """
    Check if an infrastructure command is available based on output.

    Args:
        command_output: Output from attempting to run the command
        command: Command that was executed

    Returns:
        bool: True if command appears to be available
    """
    if not command_output:
        return False

    # Check for common "not found" patterns
    not_found_patterns = [
        "command not found",
        "not found",
        "no such file or directory",
        "permission denied",
    ]

    output_lower = command_output.lower()
    for pattern in not_found_patterns:
        if pattern in output_lower:
            return False

    # Special cases for specific commands
    if command.startswith("docker"):
        return "docker" in output_lower and "version" in output_lower
    elif command.startswith("zfs") or command.startswith("zpool"):
        return not any(x in output_lower for x in ["not found", "no such file"])
    elif command.startswith("systemctl"):
        return "systemctl" in output_lower or "active" in output_lower

    return True
