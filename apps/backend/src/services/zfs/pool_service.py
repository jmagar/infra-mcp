"""
ZFS Pool Management Service

Handles ZFS pool operations including listing, status checks, and pool properties.
"""

from datetime import datetime, UTC
import logging
from typing import Any

from apps.backend.src.core.exceptions import ZFSError

from .base import ZFSBaseService

logger = logging.getLogger(__name__)


class ZFSPoolService(ZFSBaseService):
    """Service for ZFS pool management operations"""

    async def list_pools(self, hostname: str, timeout: int = 30) -> list[dict[str, Any]]:
        """List all ZFS pools on a device"""
        try:
            # Get basic pool list
            pools_output = await self._execute_zfs_command(
                hostname,
                "zpool list -H -o name,size,allocated,free,capacity,health,altroot",
                timeout,
            )

            pools = []
            for line in pools_output.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("\t")
                if len(parts) >= 6:
                    pool_data = {
                        "name": parts[0],
                        "size": parts[1],
                        "allocated": parts[2],
                        "free": parts[3],
                        "capacity": parts[4].rstrip("%"),
                        "health": parts[5],
                        "altroot": parts[6] if len(parts) > 6 else "-",
                    }
                    pools.append(pool_data)

            return pools

        except Exception as e:
            self.logger.error(f"Error listing ZFS pools on {hostname}: {e}")
            raise ZFSError(
                f"Failed to list ZFS pools: {str(e)}", operation="list_pools", hostname=hostname
            )

    async def get_pool_status(
        self, hostname: str, pool_name: str, timeout: int = 30
    ) -> dict[str, Any]:
        """Get detailed status for a specific ZFS pool"""
        try:
            # Get detailed pool status
            status_output = await self._execute_zfs_command(
                hostname, f"zpool status -v {pool_name}", timeout
            )

            # Get pool properties
            props_output = await self._execute_zfs_command(
                hostname, f"zpool get all {pool_name} -H -o property,value", timeout
            )

            # Parse pool properties
            properties = {}
            for line in props_output.strip().split("\n"):
                if line.strip() and "\t" in line:
                    prop, value = line.split("\t", 1)
                    properties[prop] = value

            return {
                "pool_name": pool_name,
                "status_output": status_output,
                "properties": properties,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting pool status for {pool_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to get pool status: {str(e)}",
                operation="get_pool_status",
                hostname=hostname,
            )

    async def get_pool_properties(
        self, hostname: str, pool_name: str, timeout: int = 30
    ) -> dict[str, Any]:
        """Get all properties for a specific pool"""
        try:
            output = await self._execute_zfs_command(
                hostname, f"zpool get all {pool_name} -H -o property,value,source", timeout
            )

            properties = {}
            for line in output.strip().split("\n"):
                if line.strip() and "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        properties[parts[0]] = {"value": parts[1], "source": parts[2]}

            return {
                "pool_name": pool_name,
                "properties": properties,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting pool properties for {pool_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to get pool properties: {str(e)}",
                operation="get_pool_properties",
                hostname=hostname,
            )
