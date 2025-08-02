"""
MCP tool for importing devices from SSH configuration files.

Provides a convenient interface for importing infrastructure devices
from SSH configuration files through the MCP protocol.
"""

import logging
from typing import Any
from fastmcp import FastMCP

from apps.backend.src.utils.ssh_config_parser import parse_ssh_config
from apps.backend.src.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
)
from apps.backend.src.services.device_service import DeviceService
from apps.backend.src.core.database import get_db_session

logger = logging.getLogger(__name__)


async def import_devices(
    ssh_config_path: str,
    dry_run: bool = False,
    update_existing: bool = True,
    default_device_type: str = "server",
    default_monitoring: bool = True,
    tag_prefix: str | None = None,
) -> dict[str, Any]:
    """
    Import devices from SSH configuration file.

    Parses the specified SSH config file to extract host information and
    creates or updates devices in the registry. Supports dry-run mode
    to preview changes before applying them.

    Args:
        ssh_config_path: Path to SSH configuration file (e.g., ~/.ssh/config)
        dry_run: If true, return what would be imported without saving
        update_existing: Whether to update existing devices with new information
        default_device_type: Default device type for imported devices
        default_monitoring: Default monitoring state for imported devices
        tag_prefix: Prefix to add to imported device tags

    Returns:
        Dictionary containing import results and summary

    Raises:
        FileNotFoundError: If SSH config file doesn't exist
        ValueError: If SSH config file is malformed
    """
    try:
        # Parse SSH config file
        importable_devices = parse_ssh_config(ssh_config_path)

        if not importable_devices:
            return {
                "total_hosts_found": 0,
                "results": [],
                "summary": {"created": 0, "updated": 0, "skipped": 0, "errors": 0},
                "dry_run": dry_run,
                "message": "No importable devices found in SSH config",
            }

        results = []

        # Get database session
        async with get_db_session() as db:
            service = DeviceService(db)

            for device_data in importable_devices:
                # Apply user preferences
                device_data["device_type"] = default_device_type
                device_data["monitoring_enabled"] = default_monitoring

                # Add tag prefix if specified
                if tag_prefix:
                    device_data["tags"]["import_prefix"] = tag_prefix

                try:
                    hostname = device_data["hostname"]

                    if dry_run:
                        # Check if device exists without modifying
                        existing_device = await service.get_device_by_hostname(hostname)
                        if existing_device:
                            action = "would_update" if update_existing else "would_skip"
                        else:
                            action = "would_create"

                        results.append(
                            {
                                "hostname": hostname,
                                "action": action,
                                "device_id": str(existing_device.id) if existing_device else None,
                                "changes": device_data,
                                "error_message": None,
                            }
                        )
                    else:
                        # Actually import the device
                        existing_device = await service.get_device_by_hostname(hostname)

                        if existing_device:
                            if update_existing:
                                # Update existing device
                                update_data = DeviceUpdate(
                                    **{k: v for k, v in device_data.items() if v is not None}
                                )
                                updated_device = await service.update_device(hostname, update_data)

                                results.append(
                                    {
                                        "hostname": hostname,
                                        "action": "updated",
                                        "device_id": str(updated_device.id),
                                        "changes": device_data,
                                        "error_message": None,
                                    }
                                )
                            else:
                                # Skip existing device
                                results.append(
                                    {
                                        "hostname": hostname,
                                        "action": "skipped",
                                        "device_id": str(existing_device.id),
                                        "changes": {},
                                        "error_message": "Device already exists and update_existing=False",
                                    }
                                )
                        else:
                            # Create new device
                            create_data = DeviceCreate(**device_data)
                            new_device = await service.create_device(create_data)

                            results.append(
                                {
                                    "hostname": hostname,
                                    "action": "created",
                                    "device_id": str(new_device.id),
                                    "changes": device_data,
                                    "error_message": None,
                                }
                            )

                except Exception as e:
                    logger.error(
                        f"Error importing device {device_data.get('hostname', 'unknown')}: {e}"
                    )
                    results.append(
                        {
                            "hostname": device_data.get("hostname", "unknown"),
                            "action": "error",
                            "device_id": None,
                            "changes": {},
                            "error_message": str(e),
                        }
                    )

        # Create summary
        summary = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
        for result in results:
            action = result["action"]
            if action in summary:
                summary[action] += 1
            elif action == "error":
                summary["errors"] += 1

        return {
            "total_hosts_found": len(importable_devices),
            "results": results,
            "summary": summary,
            "dry_run": dry_run,
            "message": f"Import {'preview' if dry_run else 'completed'}: {summary}",
        }

    except FileNotFoundError:
        error_msg = f"SSH config file not found: {ssh_config_path}"
        logger.error(error_msg)
        return {
            "total_hosts_found": 0,
            "results": [],
            "summary": {"created": 0, "updated": 0, "skipped": 0, "errors": 1},
            "dry_run": dry_run,
            "error": error_msg,
        }
    except ValueError as e:
        error_msg = f"Invalid SSH config file: {str(e)}"
        logger.error(error_msg)
        return {
            "total_hosts_found": 0,
            "results": [],
            "summary": {"created": 0, "updated": 0, "skipped": 0, "errors": 1},
            "dry_run": dry_run,
            "error": error_msg,
        }
    except Exception as e:
        error_msg = f"Device import failed: {str(e)}"
        logger.error(error_msg)
        return {
            "total_hosts_found": 0,
            "results": [],
            "summary": {"created": 0, "updated": 0, "skipped": 0, "errors": 1},
            "dry_run": dry_run,
            "error": error_msg,
        }


# FastMCP tool registration
def register_device_import_tools(mcp_server: FastMCP):
    """Register device import tools with the MCP server"""

    @mcp_server.tool()
    async def import_devices_from_ssh_config(
        ssh_config_path: str,
        dry_run: bool = False,
        update_existing: bool = True,
        default_device_type: str = "server",
        default_monitoring: bool = True,
        tag_prefix: str | None = None,
    ) -> dict[str, Any]:
        """
        Import devices from SSH configuration file.

        Parses the specified SSH config file to extract host information and
        creates or updates devices in the registry. Supports dry-run mode
        to preview changes before applying them.

        Args:
            ssh_config_path: Path to SSH configuration file (e.g., ~/.ssh/config)
            dry_run: If true, return what would be imported without saving
            update_existing: Whether to update existing devices with new information
            default_device_type: Default device type for imported devices
            default_monitoring: Default monitoring state for imported devices
            tag_prefix: Prefix to add to imported device tags

        Returns:
            Dictionary containing import results and summary
        """
        return await import_devices(
            ssh_config_path=ssh_config_path,
            dry_run=dry_run,
            update_existing=update_existing,
            default_device_type=default_device_type,
            default_monitoring=default_monitoring,
            tag_prefix=tag_prefix,
        )

    logger.info("Registered device import MCP tools")
