"""
ZFS Health Monitoring Service

Handles ZFS health checks, ARC statistics, and event monitoring.
"""

from datetime import UTC, datetime
import logging

from typing import Any, Dict, List, Optional

from apps.backend.src.core.exceptions import ZFSError

from .base import ZFSBaseService

logger = logging.getLogger(__name__)


class ZFSHealthService(ZFSBaseService):
    """Service for ZFS health monitoring operations"""

    async def check_zfs_health(self, hostname: str, timeout: int = 60) -> dict[str, Any]:
        """Comprehensive ZFS health check"""
        try:
            # Get pool status
            pools_output = await self._execute_zfs_command(hostname, "zpool status", timeout)

            # Get pool list with health
            pools_list = await self._execute_zfs_command(
                hostname, "zpool list -H -o name,health", timeout
            )

            # Check for errors
            pools_with_errors = []
            healthy_pools = []

            for line in pools_list.strip().split("\n"):
                if line.strip() and "\t" in line:
                    name, health = line.split("\t")
                    if health != "ONLINE":
                        pools_with_errors.append({"name": name, "health": health})
                    else:
                        healthy_pools.append(name)

            return {
                "healthy_pools": healthy_pools,
                "pools_with_errors": pools_with_errors,
                "detailed_status": pools_output,
                "overall_health": "healthy" if not pools_with_errors else "degraded",
                "checked_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error checking ZFS health on {hostname}: {e}")
            raise ZFSError(
                f"Failed to check ZFS health: {str(e)}", operation="check_health", hostname=hostname
            )

    async def get_arc_stats(self, hostname: str, timeout: int = 30) -> dict[str, Any]:
        """Get ZFS ARC (Adaptive Replacement Cache) statistics"""
        try:
            # Get ARC stats from /proc/spl/kstat/zfs/arcstats
            cmd = "cat /proc/spl/kstat/zfs/arcstats"
            output = await self._execute_zfs_command(hostname, cmd, timeout)

            arc_stats = {}
            for line in output.strip().split("\n"):
                if line.strip() and len(line.split()) >= 3:
                    parts = line.split()
                    if len(parts) >= 3:
                        key = parts[0]
                        value = parts[2]
                        try:
                            # Try to convert to int first
                            arc_stats[key] = int(value)
                        except ValueError:
                            # If that fails, keep as string
                            arc_stats[key] = str(value)

            # Calculate hit ratios
            hits = arc_stats.get("hits", 0)
            misses = arc_stats.get("misses", 0)
            total = hits + misses
            hit_ratio = (hits / total * 100) if total > 0 else 0

            return {
                "arc_stats": arc_stats,
                "hit_ratio_percent": round(hit_ratio, 2),
                "cache_size_bytes": arc_stats.get("size", 0),
                "cache_max_bytes": arc_stats.get("c_max", 0),
                "retrieved_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting ARC stats on {hostname}: {e}")
            raise ZFSError(
                f"Failed to get ARC stats: {str(e)}", operation="get_arc_stats", hostname=hostname
            )

    async def monitor_zfs_events(self, hostname: str, timeout: int = 30) -> dict[str, Any]:
        """Monitor ZFS events and error messages"""
        try:
            # Get recent ZFS events from dmesg or journalctl
            events_cmd = "journalctl -u zfs-import-cache.service -u zfs-mount.service -u zfs-share.service --since='1 hour ago' --no-pager"
            events_output = await self._execute_zfs_command(hostname, events_cmd, timeout)

            # Also check dmesg for ZFS messages
            dmesg_cmd = "dmesg | grep -i zfs | tail -20"
            dmesg_output = await self._execute_zfs_command(hostname, dmesg_cmd, timeout)

            return {
                "journal_events": events_output,
                "dmesg_events": dmesg_output,
                "monitored_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error monitoring ZFS events on {hostname}: {e}")
            raise ZFSError(
                f"Failed to monitor ZFS events: {str(e)}",
                operation="monitor_events",
                hostname=hostname,
            )

    async def scrub_pool(self, hostname: str, pool_name: str, timeout: int = 30) -> dict[str, Any]:
        """Start a ZFS scrub operation"""
        try:
            cmd = f"zpool scrub {pool_name}"
            await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "pool_name": pool_name,
                "operation": "scrub_started",
                "started_at": datetime.now(UTC).isoformat(),
                "status": "initiated",
            }

        except Exception as e:
            self.logger.error(f"Error starting scrub for pool {pool_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to start scrub: {str(e)}", operation="scrub_pool", hostname=hostname
            )

    async def get_scrub_status(
        self, hostname: str, pool_name: str, timeout: int = 30
    ) -> dict[str, Any]:
        """Get current scrub status for a pool"""
        try:
            cmd = f"zpool status {pool_name} | grep -A5 -B5 scrub"
            output = await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "pool_name": pool_name,
                "scrub_info": output,
                "checked_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting scrub status for pool {pool_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to get scrub status: {str(e)}",
                operation="get_scrub_status",
                hostname=hostname,
            )
