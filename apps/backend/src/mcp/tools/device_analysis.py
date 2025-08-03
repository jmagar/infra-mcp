"""
Device Analysis MCP Tool

Comprehensive device analysis tool that runs a series of commands on target devices
to gather information about their capabilities and store the results in the device registry.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select

from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.device import Device

logger = logging.getLogger(__name__)


async def _store_analysis_results(device: str, analysis_results: dict[str, Any]) -> None:
    """Store analysis results in the device registry and update device fields."""

    # Input validation
    if not analysis_results:
        logger.warning(f"Empty analysis_results provided for device {device}, cannot store")
        return

    if "analysis_summary" not in analysis_results:
        logger.warning(
            f"Missing 'analysis_summary' key in analysis_results for device {device}, cannot store"
        )
        return

    analysis_summary = analysis_results["analysis_summary"]
    if not isinstance(analysis_summary, dict):
        logger.warning(
            f"Invalid 'analysis_summary' format for device {device}, expected dict got {type(analysis_summary)}"
        )
        return

    # Validate required top-level keys exist and are dictionaries
    required_keys = [
        "docker_info",
        "storage_info",
        "services",
        "virtualization",
        "hardware_info",
        "os_info",
        "connectivity",
    ]
    for key in required_keys:
        if key not in analysis_results:
            logger.warning(
                f"Missing '{key}' key in analysis_results for device {device}, initializing as empty dict"
            )
            analysis_results[key] = {}
        elif not isinstance(analysis_results[key], dict):
            logger.warning(
                f"Invalid '{key}' format for device {device}, expected dict got {type(analysis_results[key])}, initializing as empty dict"
            )
            analysis_results[key] = {}

    async with get_async_session() as session:
        # Find the device
        query = select(Device).where(Device.hostname == device)
        result = await session.execute(query)
        device_record = result.scalar_one_or_none()

        if not device_record:
            logger.warning(f"Device {device} not found in registry, cannot store analysis results")
            return

        # Initialize tags if not present
        if not device_record.tags:
            device_record.tags = {}

        # Store analysis summary and timestamp
        device_record.tags["last_analysis"] = analysis_results["analysis_summary"]
        device_record.tags["analysis_timestamp"] = analysis_results["analysis_summary"][
            "analysis_timestamp"
        ]

        # Update capability tags (docker, zfs, swag, vms, gpu)
        capability_tags = analysis_results["analysis_summary"].get("capability_tags", [])
        existing_tags = set(device_record.tags.keys())

        # Remove old capability tags that are no longer detected
        old_capability_tags = {"docker", "zfs", "swag", "vms", "gpu"}
        for old_tag in old_capability_tags:
            if old_tag in existing_tags and old_tag not in capability_tags:
                del device_record.tags[old_tag]

        # Add new capability tags
        for tag in capability_tags:
            device_record.tags[tag] = True

        # Update Docker-specific fields and paths
        if analysis_results["docker_info"].get("installed"):
            device_record.tags["docker_version"] = analysis_results["docker_info"].get("version")

            # Set primary docker_compose_path (first detected path)
            compose_paths = analysis_results["docker_info"].get("compose_base_paths", [])
            if compose_paths:
                device_record.docker_compose_path = compose_paths[0]
                device_record.tags["all_docker_compose_paths"] = compose_paths

            # Set primary docker_appdata_path (first detected path)
            appdata_paths = analysis_results["docker_info"].get("appdata_paths", [])
            if appdata_paths:
                device_record.docker_appdata_path = appdata_paths[0]
                device_record.tags["all_appdata_paths"] = appdata_paths

        # Update ZFS information
        if analysis_results["storage_info"].get("zfs_available"):
            zfs_pools = analysis_results["storage_info"].get("zfs_pools", [])
            device_record.tags["zfs_pools"] = [pool["name"] for pool in zfs_pools]
            device_record.tags["zfs_pool_count"] = len(zfs_pools)

        # Update SWAG/reverse proxy information
        if analysis_results["services"].get("reverse_proxy_detected"):
            device_record.tags["swag_containers"] = analysis_results["services"].get(
                "swag_containers", []
            )
            device_record.tags["swag_config_count"] = analysis_results["services"].get(
                "swag_config_count", 0
            )
            device_record.tags["swag_running"] = analysis_results["services"].get(
                "swag_running", False
            )

        # Update virtualization information
        if analysis_results["virtualization"].get("virsh_available"):
            vm_list = analysis_results["virtualization"].get("vm_list", [])
            device_record.tags["vm_count"] = len(vm_list)
            device_record.tags["hypervisor"] = "libvirt"

        # Update GPU information
        if analysis_results["hardware_info"].get("gpu_detected"):
            device_record.tags["gpu_info"] = analysis_results["hardware_info"].get("gpu_info", [])
            device_record.tags["gpu_count"] = len(
                analysis_results["hardware_info"].get("gpu_info", [])
            )

        # Update OS information
        if analysis_results["os_info"]:
            device_record.tags["os_name"] = analysis_results["os_info"].get("name", "unknown")
            device_record.tags["os_version"] = analysis_results["os_info"].get("version", "unknown")
            device_record.tags["kernel"] = analysis_results["os_info"].get("kernel", "unknown")

        # Update hardware information
        if analysis_results["hardware_info"]:
            cpu_info = analysis_results["hardware_info"].get("cpu", {})
            memory_info = analysis_results["hardware_info"].get("memory", {})

            if cpu_info:
                device_record.tags["cpu_model"] = cpu_info.get("model", "unknown")
                device_record.tags["cpu_cores"] = cpu_info.get("cores", "unknown")
                device_record.tags["cpu_architecture"] = cpu_info.get("architecture", "unknown")

            if memory_info:
                device_record.tags["memory_total"] = memory_info.get("total", "unknown")

        # Update device status and last seen
        if analysis_results["connectivity"].get("ssh", {}).get("status") == "success":
            device_record.status = "online"
            device_record.last_seen = datetime.now(timezone.utc)

        await session.commit()
        logger.info(f"Analysis results stored for device {device} with tags: {capability_tags}")
