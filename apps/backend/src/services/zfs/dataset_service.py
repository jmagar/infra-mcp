"""
ZFS Dataset Management Service

Handles ZFS dataset operations including listing, properties, and dataset management.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from .base import ZFSBaseService
from apps.backend.src.core.exceptions import ZFSError

logger = logging.getLogger(__name__)


class ZFSDatasetService(ZFSBaseService):
    """Service for ZFS dataset management operations"""

    async def list_datasets(
        self, hostname: str, pool_name: Optional[str] = None, timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """List ZFS datasets, optionally filtered by pool"""
        try:
            cmd = "zfs list -H -o name,used,available,referenced,mountpoint,type,compression,dedup"
            if pool_name:
                cmd += f" -r {pool_name}"

            output = await self._execute_zfs_command(hostname, cmd, timeout)

            datasets = []
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("\t")
                if len(parts) >= 8:
                    dataset_data = {
                        "name": parts[0],
                        "used": parts[1],
                        "available": parts[2],
                        "referenced": parts[3],
                        "mountpoint": parts[4],
                        "type": parts[5],
                        "compression": parts[6],
                        "dedup": parts[7],
                    }
                    datasets.append(dataset_data)

            return datasets

        except Exception as e:
            self.logger.error(f"Error listing datasets on {hostname}: {e}")
            raise ZFSError(
                f"Failed to list datasets: {str(e)}", operation="list_datasets", hostname=hostname
            )

    async def get_dataset_properties(
        self, hostname: str, dataset_name: str, timeout: int = 30
    ) -> Dict[str, Any]:
        """Get all properties for a specific dataset"""
        try:
            output = await self._execute_zfs_command(
                hostname, f"zfs get all {dataset_name} -H -o property,value,source", timeout
            )

            properties = {}
            for line in output.strip().split("\n"):
                if line.strip() and "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        properties[parts[0]] = {"value": parts[1], "source": parts[2]}

            return {
                "dataset_name": dataset_name,
                "properties": properties,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            self.logger.error(
                f"Error getting dataset properties for {dataset_name} on {hostname}: {e}"
            )
            raise ZFSError(
                f"Failed to get dataset properties: {str(e)}",
                operation="get_dataset_properties",
                hostname=hostname,
            )

    async def create_dataset(
        self,
        hostname: str,
        dataset_name: str,
        properties: Optional[Dict[str, str]] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Create a new ZFS dataset"""
        try:
            cmd = f"zfs create"

            # Add properties if provided
            if properties:
                for prop, value in properties.items():
                    cmd += f" -o {prop}={value}"

            cmd += f" {dataset_name}"

            await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "dataset_name": dataset_name,
                "properties": properties or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "created",
            }

        except Exception as e:
            self.logger.error(f"Error creating dataset {dataset_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to create dataset: {str(e)}", operation="create_dataset", hostname=hostname
            )

    async def destroy_dataset(
        self, hostname: str, dataset_name: str, recursive: bool = False, timeout: int = 60
    ) -> Dict[str, Any]:
        """Destroy a ZFS dataset"""
        try:
            cmd = f"zfs destroy"
            if recursive:
                cmd += " -r"
            cmd += f" {dataset_name}"

            await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "dataset_name": dataset_name,
                "recursive": recursive,
                "destroyed_at": datetime.now(timezone.utc).isoformat(),
                "status": "destroyed",
            }

        except Exception as e:
            self.logger.error(f"Error destroying dataset {dataset_name} on {hostname}: {e}")
            raise ZFSError(
                f"Failed to destroy dataset: {str(e)}",
                operation="destroy_dataset",
                hostname=hostname,
            )

    async def set_dataset_property(
        self, hostname: str, dataset_name: str, property_name: str, value: str, timeout: int = 30
    ) -> Dict[str, Any]:
        """Set a property on a ZFS dataset"""
        try:
            cmd = f"zfs set {property_name}={value} {dataset_name}"
            await self._execute_zfs_command(hostname, cmd, timeout)

            return {
                "dataset_name": dataset_name,
                "property_name": property_name,
                "value": value,
                "set_at": datetime.now(timezone.utc).isoformat(),
                "status": "property_set",
            }

        except Exception as e:
            self.logger.error(
                f"Error setting property {property_name} on dataset {dataset_name} on {hostname}: {e}"
            )
            raise ZFSError(
                f"Failed to set dataset property: {str(e)}",
                operation="set_dataset_property",
                hostname=hostname,
            )
