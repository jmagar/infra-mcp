"""
ZFS Snapshot Management Service

Handles ZFS snapshot operations including creation, cloning, sending, receiving, and diffing.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .base import ZFSBaseService
from apps.backend.src.core.exceptions import ZFSError

logger = logging.getLogger(__name__)


class ZFSSnapshotService(ZFSBaseService):
    """Service for ZFS snapshot management operations"""

    def _get_current_utc_iso(self) -> str:
        """Helper function to get current UTC time in ISO format"""
        return datetime.now(timezone.utc).isoformat()

    async def list_snapshots(
        self, hostname: str, dataset_name: Optional[str] = None, timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """List ZFS snapshots, optionally filtered by dataset"""
        try:
            cmd = "zfs list -t snapshot -H -o name,used,referenced,creation"
            if dataset_name:
                cmd += f" -r {dataset_name}"

            output = await self._execute_zfs_command(hostname, cmd, timeout)

            snapshots = []
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("\t")
                if len(parts) >= 4:
                    snapshot_data = {
                        "name": parts[0],
                        "used": parts[1],
                        "referenced": parts[2],
                        "creation": parts[3],
                    }
                    snapshots.append(snapshot_data)

            return snapshots

        except Exception as e:
            self.logger.error(f"Error listing snapshots on {hostname}: {e}")
            raise ZFSError(
                f"Failed to list snapshots: {str(e)}", operation="list_snapshots", hostname=hostname
            )

    async def create_snapshot(
        self,
        hostname: str,
        dataset_name: str,
        snapshot_name: str,
        recursive: bool = False,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Create a ZFS snapshot"""
        try:
            full_snapshot_name = f"{dataset_name}@{snapshot_name}"
            cmd = f"zfs snapshot"
            if recursive:
                cmd += " -r"
            cmd += f" {full_snapshot_name}"

            await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "dataset_name": dataset_name,
                "snapshot_name": snapshot_name,
                "full_name": full_snapshot_name,
                "recursive": recursive,
                "created_at": self._get_current_utc_iso(),
                "status": "created",
            }

        except Exception as e:
            self.logger.error(
                f"Error creating snapshot {snapshot_name} for {dataset_name} on {hostname}: {e}"
            )
            raise ZFSError(
                f"Failed to create snapshot: {str(e)}",
                operation="create_snapshot",
                hostname=hostname,
            )

    async def destroy_snapshot(
        self, hostname: str, snapshot_name: str, recursive: bool = False, timeout: int = 60
    ) -> Dict[str, Any]:
        """Destroy a ZFS snapshot"""
        try:
            cmd = f"zfs destroy"
            if recursive:
                cmd += " -r"
            cmd += f" {snapshot_name}"

            await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "snapshot_name": snapshot_name,
                "recursive": recursive,
                "destroyed_at": self._get_current_utc_iso(),
                "status": "destroyed",
            }

        except Exception as e:
            self.logger.error(f"Error destroying snapshot {snapshot_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to destroy snapshot: {str(e)}",
                operation="destroy_snapshot",
                hostname=hostname,
            )

    async def clone_snapshot(
        self, hostname: str, snapshot_name: str, clone_name: str, timeout: int = 60
    ) -> Dict[str, Any]:
        """Clone a ZFS snapshot"""
        try:
            cmd = f"zfs clone {snapshot_name} {clone_name}"
            await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "source_snapshot": snapshot_name,
                "clone_name": clone_name,
                "created_at": self._get_current_utc_iso(),
                "status": "cloned",
            }

        except Exception as e:
            self.logger.error(
                f"Error cloning snapshot {snapshot_name} to {clone_name} on {hostname}: {e}"
            )
            raise ZFSError(
                f"Failed to clone snapshot: {str(e)}", operation="clone_snapshot", hostname=hostname
            )

    async def send_snapshot(
        self,
        hostname: str,
        snapshot_name: str,
        destination: Optional[str] = None,
        incremental: bool = False,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Send a ZFS snapshot (for replication/backup)"""
        try:
            cmd = f"zfs send"
            if incremental:
                cmd += " -i"
            cmd += f" {snapshot_name}"

            if destination:
                cmd += f" | ssh {destination} 'zfs receive'"

            output = await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "snapshot_name": snapshot_name,
                "destination": destination,
                "incremental": incremental,
                "output": output,
                "sent_at": self._get_current_utc_iso(),
                "status": "sent",
            }

        except Exception as e:
            self.logger.error(f"Error sending snapshot {snapshot_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to send snapshot: {str(e)}", operation="send_snapshot", hostname=hostname
            )

    async def receive_snapshot(
        self, hostname: str, dataset_name: str, timeout: int = 300
    ) -> Dict[str, Any]:
        """Receive a ZFS snapshot stream"""
        try:
            cmd = f"zfs receive {dataset_name}"
            output = await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "dataset_name": dataset_name,
                "output": output,
                "received_at": self._get_current_utc_iso(),
                "status": "received",
            }

        except Exception as e:
            self.logger.error(f"Error receiving snapshot for {dataset_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to receive snapshot: {str(e)}",
                operation="receive_snapshot",
                hostname=hostname,
            )

    async def diff_snapshots(
        self, hostname: str, snapshot1: str, snapshot2: str, timeout: int = 60
    ) -> Dict[str, Any]:
        """Compare differences between two snapshots"""
        try:
            cmd = f"zfs diff {snapshot1} {snapshot2}"
            output = await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "snapshot1": snapshot1,
                "snapshot2": snapshot2,
                "differences": output,
                "compared_at": self._get_current_utc_iso(),
            }

        except Exception as e:
            self.logger.error(
                f"Error diffing snapshots {snapshot1} and {snapshot2} on {hostname}: {e}"
            )
            raise ZFSError(
                f"Failed to diff snapshots: {str(e)}", operation="diff_snapshots", hostname=hostname
            )
