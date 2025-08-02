"""
Infrastructure Management MCP Server - Utilities Package

This package provides comprehensive utilities for SSH communication,
device management, error handling, and infrastructure monitoring.
"""

from .ssh_client import (
    SSHClient,
    SSHConnectionInfo,
    SSHExecutionResult,
    SSHConnectionPool,
    get_ssh_client,
    cleanup_ssh_client,
    execute_ssh_command,
    test_ssh_connectivity,
)

from .ssh_errors import (
    SSHErrorType,
    SSHErrorInfo,
    SSHErrorClassifier,
    SSHHealthChecker,
    get_common_ssh_errors,
    is_infrastructure_command_available,
)

from .device_manager import DeviceManager, get_device_manager

__all__ = [
    # SSH Client
    "SSHClient",
    "SSHConnectionInfo",
    "SSHExecutionResult",
    "SSHConnectionPool",
    "get_ssh_client",
    "cleanup_ssh_client",
    "execute_ssh_command",
    "test_ssh_connectivity",
    # SSH Error Handling
    "SSHErrorType",
    "SSHErrorInfo",
    "SSHErrorClassifier",
    "SSHHealthChecker",
    "get_common_ssh_errors",
    "is_infrastructure_command_available",
    # Device Management
    "DeviceManager",
    "get_device_manager",
]
