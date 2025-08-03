"""
Proxy Configuration Management MCP Tools

MCP tools for managing SWAG reverse proxy configurations with
real-time file access and database synchronization.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, Boolean
from sqlalchemy.orm import selectinload

from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.proxy_config import ProxyConfig, ProxyConfigChange
from apps.backend.src.schemas.proxy_config import (
    ProxyConfigResponse,
    ProxyConfigList,
    ProxyConfigSummary,
    ProxyConfigFileInfo,
    ProxyConfigSync,
)
from apps.backend.src.utils.nginx_parser import NginxConfigParser, parse_swag_config_directory
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    SSHConnectionError,
    SSHCommandError,
    ResourceNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


async def list_proxy_configs(
    device: Optional[str] = None,
    service_name: Optional[str] = None,
    status: Optional[str] = None,
    ssl_enabled: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List proxy configurations with real-time sync check

    Args:
        device: Filter by device hostname
        service_name: Filter by service name
        status: Filter by status (active, inactive, error)
        ssl_enabled: Filter by SSL status
        limit: Maximum number of results
        offset: Results offset for pagination

    Returns:
        Dict containing proxy configurations list
    """
    try:
        async with get_async_session() as session:
            # Build query with filters
            query = select(ProxyConfig).options(selectinload(ProxyConfig.device))

            conditions = []
            if device:
                conditions.append(ProxyConfig.device_id == device)
            if service_name:
                conditions.append(ProxyConfig.service_name.ilike(f"%{service_name}%"))
            if status:
                conditions.append(ProxyConfig.status == status)
            if ssl_enabled is not None:
                if ssl_enabled:
                    conditions.append(
                        ProxyConfig.parsed_config["ssl_enabled"].as_string().cast(Boolean) == True
                    )
                else:
                    conditions.append(
                        or_(
                            ProxyConfig.parsed_config["ssl_enabled"].as_string().cast(Boolean)
                            == False,
                            ProxyConfig.parsed_config["ssl_enabled"].is_(None),
                        )
                    )

            if conditions:
                query = query.where(and_(*conditions))

            # Order by device, then service name
            query = query.order_by(ProxyConfig.device_id, ProxyConfig.service_name)

            # Apply pagination
            total_query = select(func.count()).select_from(query.subquery())
            total_count = await session.scalar(total_query)

            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            configs = result.scalars().all()

            # Convert to response format
            config_responses = []
            for config in configs:
                # Check if file exists and get real-time info
                file_info = await _get_real_time_file_info(config.device_id, config.file_path)

                config_dict = {
                    "id": config.id,
                    "device_id": config.device_id,
                    "service_name": config.service_name,
                    "subdomain": config.subdomain,
                    "config_type": config.config_type,
                    "status": config.status,
                    "file_path": config.file_path,
                    "file_size": file_info.get("file_size", config.file_size),
                    "file_hash": config.file_hash,
                    "last_modified": file_info.get("last_modified", config.last_modified),
                    "parsed_config": config.parsed_config,
                    "description": config.description,
                    "tags": config.tags,
                    "created_at": config.created_at,
                    "updated_at": config.updated_at,
                    "sync_status": _determine_sync_status(config, file_info),
                    "sync_last_checked": datetime.now(timezone.utc),
                    "file_exists": file_info.get("exists", False),
                    "file_readable": file_info.get("readable", False),
                }
                config_responses.append(config_dict)

            return {
                "configs": config_responses,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "page": (offset // limit) + 1 if limit > 0 else 1,
                    "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1,
                },
                "query_timestamp": datetime.now(timezone.utc).isoformat(),
                "real_time_check": True,
            }

    except Exception as e:
        logger.error(f"Error listing proxy configs: {e}")
        raise Exception(f"Failed to list proxy configurations: {str(e)}")


async def get_proxy_config(
    config_id: Optional[int] = None,
    device: Optional[str] = None,
    service_name: Optional[str] = None,
    include_content: bool = True,
) -> Dict[str, Any]:
    """
    Get specific proxy configuration with real-time file content

    Args:
        config_id: Configuration ID
        device: Device hostname (optional, for disambiguation)
        service_name: Service name (unique identifier from filename)
        include_content: Include raw configuration content

    Returns:
        Dict containing proxy configuration details
    """
    try:
        async with get_async_session() as session:
            # Build query - service_name should be sufficient as it's unique
            if config_id:
                query = select(ProxyConfig).where(ProxyConfig.id == config_id)
            elif service_name:
                # Service name is unique across the system (from filename)
                if device:
                    # If device is provided, use both for safety
                    query = select(ProxyConfig).where(
                        and_(
                            ProxyConfig.device_id == device,
                            ProxyConfig.service_name == service_name,
                        )
                    )
                else:
                    # Service name alone should be sufficient
                    query = select(ProxyConfig).where(ProxyConfig.service_name == service_name)
            else:
                raise ValidationError("Must provide either config_id or service_name")

            query = query.options(selectinload(ProxyConfig.device))
            result = await session.execute(query)
            config = result.scalar_one_or_none()

            if not config:
                raise ResourceNotFoundError(
                    f"Proxy configuration not found for service '{service_name}'"
                )

            # Get real-time file information and content
            file_info = await _get_real_time_file_info(config.device_id, config.file_path)

            real_time_content = None
            if include_content and file_info.get("exists", False):
                real_time_content = await _get_real_time_file_content(
                    config.device_id, config.file_path
                )

                # Parse content if it's different from stored version
                if real_time_content and real_time_content != config.raw_content:
                    parser = NginxConfigParser()
                    parsed_config = parser.parse_config_content(real_time_content, config.file_path)
                    file_info["content_changed"] = True
                    file_info["parsed_config"] = parsed_config

            # Get recent changes (handle missing table gracefully)
            recent_changes = []
            try:
                changes_query = (
                    select(ProxyConfigChange)
                    .where(ProxyConfigChange.config_id == config.id)
                    .order_by(desc(ProxyConfigChange.time))
                    .limit(10)
                )

                changes_result = await session.execute(changes_query)
                recent_changes = changes_result.scalars().all()
            except Exception as e:
                # Table doesn't exist yet, continue without changes
                logger.warning(f"Could not fetch proxy config changes: {e}")
                recent_changes = []

            return {
                "id": config.id,
                "device_id": config.device_id,
                "service_name": config.service_name,
                "subdomain": config.subdomain,
                "config_type": config.config_type,
                "status": config.status,
                "file_path": config.file_path,
                "file_size": file_info.get("file_size", config.file_size),
                "file_hash": config.file_hash,
                "last_modified": file_info.get("last_modified", config.last_modified),
                "parsed_config": file_info.get("parsed_config", config.parsed_config),
                "raw_content": real_time_content if include_content else None,
                "stored_content": config.raw_content
                if include_content and real_time_content != config.raw_content
                else None,
                "description": config.description,
                "tags": config.tags,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
                "sync_status": _determine_sync_status(config, file_info),
                "sync_last_checked": datetime.now(timezone.utc),
                "file_info": file_info,
                "recent_changes": [
                    {
                        "id": change.id,
                        "change_type": change.change_type,
                        "time": change.time,
                        "change_summary": change.change_summary,
                        "triggered_by": change.triggered_by,
                    }
                    for change in recent_changes
                ],
                "query_timestamp": datetime.now(timezone.utc).isoformat(),
                "real_time_check": True,
            }

    except Exception as e:
        logger.error(f"Error getting proxy config: {e}")
        raise Exception(f"Failed to get proxy configuration: {str(e)}")


async def scan_proxy_configs(
    device: str,
    config_directory: str = "/mnt/appdata/swag/nginx/proxy-confs",
    sync_to_database: bool = True,
) -> Dict[str, Any]:
    """
    Scan proxy configuration directory for fresh configs

    Args:
        device: Device hostname
        config_directory: Directory containing proxy configs
        sync_to_database: Whether to sync findings to database

    Returns:
        Dict containing scan results
    """
    try:
        scan_start = datetime.now(timezone.utc)

        # Execute remote directory listing
        ls_command = (
            f"find {config_directory} -name '*.conf' -type f -exec stat -c '%n|%s|%Y' {{}} \\;"
        )

        try:
            ls_result = await execute_ssh_command_simple(device, ls_command, timeout=30)
            ls_output = ls_result.stdout
        except (SSHConnectionError, SSHCommandError) as e:
            raise Exception(f"Failed to access device {device}: {str(e)}")

        # Parse file listing
        files_found = []
        file_info = {}

        for line in ls_output.strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    file_path = parts[0]
                    file_size = int(parts[1])
                    mtime = int(parts[2])
                    last_modified = datetime.fromtimestamp(mtime, tz=timezone.utc)

                    files_found.append(file_path)
                    file_info[file_path] = {
                        "file_path": file_path,
                        "file_size": file_size,
                        "last_modified": last_modified,
                        "exists": True,
                        "readable": True,  # Assume readable if stat succeeded
                    }

        # Parse service names from file paths
        configs_found = []
        for file_path in files_found:
            path = Path(file_path)
            filename = path.stem

            # SWAG naming: service.subdomain.conf
            parts = filename.split(".")
            if len(parts) >= 2:
                service_name = parts[0]
                subdomain = parts[1]
            else:
                service_name = filename
                subdomain = filename

            config_info = file_info[file_path].copy()
            config_info.update(
                {"service_name": service_name, "subdomain": subdomain, "config_filename": path.name}
            )
            configs_found.append(config_info)

        scan_result = {
            "device": device,
            "config_directory": config_directory,
            "scan_timestamp": scan_start.isoformat(),
            "total_files_found": len(files_found),
            "configs_found": configs_found,
            "sync_to_database": sync_to_database,
            "scan_duration_ms": int(
                (datetime.now(timezone.utc) - scan_start).total_seconds() * 1000
            ),
        }

        # Sync to database if requested
        if sync_to_database:
            sync_result = await _sync_configs_to_database(device, configs_found)
            scan_result["sync_result"] = sync_result

        return scan_result

    except Exception as e:
        logger.error(f"Error scanning proxy configs on {device}: {e}")
        raise Exception(f"Failed to scan proxy configurations: {str(e)}")


async def sync_proxy_config(config_id: int, force_update: bool = False) -> Dict[str, Any]:
    """
    Sync specific proxy configuration with file system

    Args:
        config_id: Configuration ID to sync
        force_update: Force update even if hashes match

    Returns:
        Dict containing sync results
    """
    try:
        sync_start = datetime.now(timezone.utc)

        async with get_async_session() as session:
            # Get configuration
            query = select(ProxyConfig).where(ProxyConfig.id == config_id)
            result = await session.execute(query)
            config = result.scalar_one_or_none()

            if not config:
                raise ResourceNotFoundError(f"Proxy configuration {config_id} not found")

            # Get real-time file info and content
            file_info = await _get_real_time_file_info(config.device_id, config.file_path)

            sync_result = {
                "config_id": config_id,
                "device": config.device_id,
                "service_name": config.service_name,
                "file_path": config.file_path,
                "sync_timestamp": sync_start.isoformat(),
                "file_exists": file_info.get("exists", False),
                "changes_detected": [],
                "updated": False,
                "error": None,
            }

            if not file_info.get("exists", False):
                # File no longer exists
                config.status = "error"
                config.sync_status = "error"
                config.sync_last_error = "File not found"
                config.updated_at = sync_start

                # Record change (handle missing table gracefully)
                try:
                    change = ProxyConfigChange(
                        config_id=config.id,
                        change_type="deleted",
                        old_hash=config.file_hash,
                        new_hash=None,
                        change_summary="Configuration file deleted",
                        triggered_by="sync_check",
                        time=sync_start,
                    )
                    session.add(change)
                except Exception as e:
                    logger.warning(f"Could not record proxy config change: {e}")

                sync_result["changes_detected"].append("File deleted")
                sync_result["updated"] = True

            else:
                # Get file content
                real_time_content = await _get_real_time_file_content(
                    config.device_id, config.file_path
                )

                if real_time_content:
                    parser = NginxConfigParser()
                    current_hash = parser.calculate_content_hash(real_time_content)

                    # Check if content changed
                    if current_hash != config.file_hash or force_update:
                        # Parse new content
                        parsed_config = parser.parse_config_content(
                            real_time_content, config.file_path
                        )

                        # Update config
                        old_hash = config.file_hash
                        config.raw_content = real_time_content
                        config.file_hash = current_hash
                        config.file_size = file_info.get("file_size")
                        config.last_modified = file_info.get("last_modified")
                        config.parsed_config = parsed_config
                        config.sync_status = "synced"
                        config.sync_last_error = None
                        config.updated_at = sync_start

                        # Record change (handle missing table gracefully)
                        try:
                            change = ProxyConfigChange(
                                config_id=config.id,
                                change_type="modified",
                                old_hash=old_hash,
                                new_hash=current_hash,
                                change_summary="Configuration file updated",
                                triggered_by="sync_check",
                                time=sync_start,
                            )
                            session.add(change)
                        except Exception as e:
                            logger.warning(f"Could not record proxy config change: {e}")

                        sync_result["changes_detected"].append("Content modified")
                        sync_result["updated"] = True
                        sync_result["old_hash"] = old_hash
                        sync_result["new_hash"] = current_hash

                    else:
                        # No changes, just update sync timestamp
                        config.sync_last_checked = sync_start

            await session.commit()

            sync_result["sync_duration_ms"] = int(
                (datetime.now(timezone.utc) - sync_start).total_seconds() * 1000
            )
            return sync_result

    except Exception as e:
        logger.error(f"Error syncing proxy config {config_id}: {e}")
        raise Exception(f"Failed to sync proxy configuration: {str(e)}")


async def get_proxy_config_summary(device: Optional[str] = None) -> Dict[str, Any]:
    """
    Get summary statistics for proxy configurations

    Args:
        device: Optional device filter

    Returns:
        Dict containing summary statistics
    """
    try:
        async with get_async_session() as session:
            # Base query
            base_query = select(ProxyConfig)
            if device:
                base_query = base_query.where(ProxyConfig.device_id == device)

            # Total configs
            total_query = select(func.count()).select_from(base_query.subquery())
            total_configs = await session.scalar(total_query)

            # Status counts
            status_query = select(ProxyConfig.status, func.count()).group_by(ProxyConfig.status)
            if device:
                status_query = status_query.where(ProxyConfig.device_id == device)

            status_result = await session.execute(status_query)
            status_counts = dict(status_result.fetchall())

            # Device counts (if not filtering by device)
            device_counts = {}
            if not device:
                device_query = select(ProxyConfig.device_id, func.count()).group_by(
                    ProxyConfig.device_id
                )

                device_result = await session.execute(device_query)
                device_counts = dict(device_result.fetchall())

            # SSL enabled count
            ssl_query = select(func.count()).where(
                ProxyConfig.parsed_config["ssl_enabled"].as_string().cast(Boolean) == True
            )
            if device:
                ssl_query = ssl_query.where(ProxyConfig.device_id == device)

            ssl_count = await session.scalar(ssl_query) or 0

            # Service type distribution
            service_query = select(ProxyConfig.service_name, func.count()).group_by(
                ProxyConfig.service_name
            )
            if device:
                service_query = service_query.where(ProxyConfig.device_id == device)

            service_result = await session.execute(service_query)
            service_counts = dict(service_result.fetchall())

            # Last sync time
            last_sync_query = select(func.max(ProxyConfig.sync_last_checked))
            if device:
                last_sync_query = last_sync_query.where(ProxyConfig.device_id == device)

            last_sync = await session.scalar(last_sync_query)

            return {
                "total_configs": total_configs,
                "active_configs": status_counts.get("active", 0),
                "inactive_configs": status_counts.get("inactive", 0),
                "error_configs": status_counts.get("error", 0),
                "by_device": device_counts,
                "by_service_type": service_counts,
                "ssl_enabled_count": ssl_count,
                "last_sync": last_sync,
                "status_distribution": status_counts,
                "query_timestamp": datetime.now(timezone.utc).isoformat(),
                "device_filter": device,
            }

    except Exception as e:
        logger.error(f"Error getting proxy config summary: {e}")
        raise Exception(f"Failed to get proxy configuration summary: {str(e)}")


# Helper functions


async def _get_real_time_file_info(device: str, file_path: str) -> Dict[str, Any]:
    """Get real-time file information via SSH"""
    try:
        # Use stat command to get file info
        stat_command = f"stat -c '%s|%Y|%A' '{file_path}' 2>/dev/null || echo 'NOT_FOUND'"

        result = await execute_ssh_command_simple(device, stat_command, timeout=10)
        output = result.stdout
        output = output.strip()

        if output == "NOT_FOUND":
            return {"exists": False, "readable": False, "file_size": None, "last_modified": None}

        # Parse stat output: size|mtime|permissions
        parts = output.split("|")
        if len(parts) >= 3:
            file_size = int(parts[0])
            mtime = int(parts[1])
            permissions = parts[2]
            last_modified = datetime.fromtimestamp(mtime, tz=timezone.utc)

            # Check if readable (owner, group, or other has read permission)
            readable = "r" in permissions

            return {
                "exists": True,
                "readable": readable,
                "file_size": file_size,
                "last_modified": last_modified,
                "permissions": permissions,
            }

        return {"exists": False, "readable": False, "file_size": None, "last_modified": None}

    except Exception as e:
        logger.error(f"Error getting file info for {file_path} on {device}: {e}")
        return {
            "exists": False,
            "readable": False,
            "file_size": None,
            "last_modified": None,
            "error": str(e),
        }


async def _get_real_time_file_content(device: str, file_path: str) -> Optional[str]:
    """Get real-time file content via SSH"""
    try:
        # Read file content
        cat_command = f"cat '{file_path}'"
        result = await execute_ssh_command_simple(device, cat_command, timeout=30)
        content = result.stdout
        return content

    except Exception as e:
        logger.error(f"Error reading file content for {file_path} on {device}: {e}")
        return None


def _determine_sync_status(config: ProxyConfig, file_info: Dict[str, Any]) -> str:
    """Determine sync status based on config and real-time file info"""
    if not file_info.get("exists", False):
        return "error"

    if file_info.get("error"):
        return "error"

    # Compare file modification time
    file_mtime = file_info.get("last_modified")
    if file_mtime and config.last_modified and file_mtime > config.last_modified:
        return "out_of_sync"

    # Compare file size
    file_size = file_info.get("file_size")
    if file_size and config.file_size and file_size != config.file_size:
        return "out_of_sync"

    return "synced"


async def _sync_configs_to_database(
    device: str, configs_found: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Sync found configurations to database"""
    sync_result = {"new_configs": 0, "updated_configs": 0, "errors": [], "synced_configs": []}

    try:
        async with get_async_session() as session:
            for config_info in configs_found:
                try:
                    # Check if config exists using the actual unique constraint
                    query = select(ProxyConfig).where(
                        and_(
                            ProxyConfig.device_id == device,
                            ProxyConfig.service_name == config_info["service_name"],
                        )
                    )
                    result = await session.execute(query)
                    existing_config = result.scalar_one_or_none()

                    if existing_config:
                        # Update existing
                        existing_config.file_path = config_info["file_path"]
                        existing_config.file_size = config_info["file_size"]
                        existing_config.last_modified = config_info["last_modified"]
                        existing_config.sync_last_checked = datetime.now(timezone.utc)
                        existing_config.sync_status = "synced"

                        sync_result["updated_configs"] += 1
                        sync_result["synced_configs"].append(
                            {
                                "action": "updated",
                                "service_name": config_info["service_name"],
                                "subdomain": config_info["subdomain"],
                            }
                        )
                    else:
                        # Create new
                        new_config = ProxyConfig(
                            device_id=device,
                            service_name=config_info["service_name"],
                            subdomain=config_info["subdomain"],
                            file_path=config_info["file_path"],
                            file_size=config_info["file_size"],
                            last_modified=config_info["last_modified"],
                            sync_last_checked=datetime.now(timezone.utc),
                            sync_status="pending",  # Will be synced later
                        )
                        session.add(new_config)

                        sync_result["new_configs"] += 1
                        sync_result["synced_configs"].append(
                            {
                                "action": "created",
                                "service_name": config_info["service_name"],
                                "subdomain": config_info["subdomain"],
                            }
                        )

                except Exception as e:
                    error_msg = (
                        f"Error syncing {config_info.get('service_name', 'unknown')}: {str(e)}"
                    )
                    sync_result["errors"].append(error_msg)
                    logger.error(error_msg)

            await session.commit()

    except Exception as e:
        error_msg = f"Database sync error: {str(e)}"
        sync_result["errors"].append(error_msg)
        logger.error(error_msg)

    return sync_result
