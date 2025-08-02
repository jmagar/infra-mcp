"""
ZFS Base Service

Common functionality and SSH connection management for all ZFS services.
"""

import logging
from typing import Optional

from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.core.exceptions import SSHConnectionError, SSHCommandError, ZFSError

logger = logging.getLogger(__name__)


class ZFSBaseService:
    """Base service for ZFS operations via SSH"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def _execute_zfs_command(self, hostname: str, command: str, timeout: int = 30) -> str:
        """Execute ZFS command via SSH and return output"""
        try:
            result = await execute_ssh_command_simple(hostname, command, timeout)
            if result.return_code != 0:
                error_msg = result.stderr or f"Command failed with exit code {result.return_code}"
                raise ZFSError(
                    f"ZFS command failed: {error_msg}", operation="zfs_command", hostname=hostname
                )

            return result.stdout.strip()

        except SSHConnectionError as e:
            raise SSHConnectionError(f"Failed to connect to {hostname}: {str(e)}")
        except SSHCommandError as e:
            raise ZFSError(
                f"ZFS command error on {hostname}: {str(e)}",
                operation="zfs_command",
                hostname=hostname,
            )

    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes for comparison"""
        if not size_str or size_str == "-":
            return 0

        # Handle different size units
        multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}

        size_str = size_str.upper().strip()
        for unit, multiplier in multipliers.items():
            if size_str.endswith(unit):
                try:
                    return int(float(size_str[:-1]) * multiplier)
                except ValueError:
                    return 0

        # Try to parse as plain number
        try:
            return int(size_str)
        except ValueError:
            return 0
