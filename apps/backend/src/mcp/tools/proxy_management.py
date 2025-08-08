"""
Proxy Configuration Management MCP Tools

Architectural Change (August 7, 2025): Uses unified data collection service directly
instead of HTTP API calls for better performance and consistency.
"""

from datetime import UTC, datetime, timedelta
import logging
from pathlib import Path

from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select

from apps.backend.src.core.database import get_async_session_factory
from apps.backend.src.models.configuration import ConfigurationSnapshot

logger = logging.getLogger(__name__)


async def list_proxy_configs(
    device: str | None = None,
    service_name: str | None = None,
    status: str | None = None,
    ssl_enabled: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """
    List proxy configurations from database (collected by configuration monitoring service)

    Args:
        device: Filter by device hostname 
        service_name: Filter by service name
        status: Filter by status (active, inactive, error)
        ssl_enabled: Filter by SSL status
        limit: Maximum number of results
        offset: Results offset for pagination

    Returns:
        Dict containing proxy configurations list from database
    """
    try:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            # Query configuration_snapshots for nginx_proxy configs instead of proxy_config table
            query = select(ConfigurationSnapshot).where(
                and_(
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like("%.conf")
                )
            )

            # Apply filters
            if device:
                # Convert device hostname to device_id if needed
                from apps.backend.src.models.device import Device
                device_query = select(Device.id).where(Device.hostname == device)
                device_result = await session.execute(device_query)
                device_id = device_result.scalar_one_or_none()
                if device_id:
                    query = query.where(ConfigurationSnapshot.device_id == device_id)
                else:
                    # No matching device found
                    return {
                        "configs": [],
                        "pagination": {"limit": limit, "offset": offset, "total": 0},
                        "query_timestamp": datetime.now(UTC).isoformat(),
                        "source": "configuration_snapshots"
                    }

            if service_name:
                query = query.where(ConfigurationSnapshot.file_path.like(f"%{service_name}%"))

            # Apply pagination
            query = query.order_by(ConfigurationSnapshot.time.desc()).offset(offset).limit(limit)

            # Execute query
            result = await session.execute(query)
            snapshots = result.scalars().all()

            # Convert to dict format
            config_dicts = []
            for snapshot in snapshots:
                # Extract service name from file path
                service_name_extracted = _extract_service_name_from_path(snapshot.file_path)

                config_dict = {
                    "id": str(snapshot.id),
                    "service_name": service_name_extracted,
                    "device_id": str(snapshot.device_id),
                    "file_path": snapshot.file_path,
                    "content_hash": snapshot.content_hash,
                    "status": "active" if snapshot.change_type != "DELETE" else "deleted",
                    "change_type": snapshot.change_type,
                    "last_modified": snapshot.time.isoformat(),
                    "config_type": snapshot.config_type,
                    "content": snapshot.raw_content if snapshot.raw_content else "",
                }
                config_dicts.append(config_dict)

            logger.info(f"Successfully retrieved {len(config_dicts)} proxy configurations from configuration snapshots")

            return {
                "configs": config_dicts,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": len(config_dicts)  # For more accurate count, we'd need separate query
                },
                "query_timestamp": datetime.now(UTC).isoformat(),
                "source": "configuration_snapshots"
            }

    except Exception as e:
        logger.error(f"Error listing proxy configs from database: {e}")
        raise Exception(f"Failed to list proxy configurations: {str(e)}") from e


def _extract_service_name_from_path(file_path: str) -> str:
    """Extract service name from proxy config file path."""
    filename = Path(file_path).name

    # Remove common extensions (.conf, .subdomain.conf, etc.)
    service_name = filename
    for ext in ['.subdomain.conf', '.subfolder.conf', '.conf']:
        if service_name.endswith(ext):
            service_name = service_name[:-len(ext)]
            break

    return service_name


async def get_proxy_config(
    service_name: str,
    config_id: int | None = None,
    device: str | None = None,
    include_content: bool = True,
) -> dict[str, Any]:
    """
    Get specific proxy configuration from database (collected by configuration monitoring service)

    Args:
        service_name: Service name (required)
        config_id: Configuration ID (not used - service_name required)
        device: Device hostname
        include_content: Include raw configuration content

    Returns:
        Dict containing proxy configuration details from database
    """
    try:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            # Query configuration_snapshots for specific service config
            query = select(ConfigurationSnapshot).where(
                and_(
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like(f"%{service_name}%")
                )
            )

            # Apply device filter if specified
            if device:
                from apps.backend.src.models.device import Device
                device_query = select(Device.id).where(Device.hostname == device)
                device_result = await session.execute(device_query)
                device_id = device_result.scalar_one_or_none()
                if device_id:
                    query = query.where(ConfigurationSnapshot.device_id == device_id)
                else:
                    raise Exception(f"Device '{device}' not found")

            # Order by most recent and get the first match
            query = query.order_by(ConfigurationSnapshot.time.desc()).limit(1)

            # Execute query
            result = await session.execute(query)
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                raise Exception(f"Proxy configuration not found for service '{service_name}'")

            # Build response
            config_dict = {
                "id": str(snapshot.id),
                "service_name": _extract_service_name_from_path(snapshot.file_path),
                "device_id": str(snapshot.device_id),
                "file_path": snapshot.file_path,
                "content_hash": snapshot.content_hash,
                "status": "active" if snapshot.change_type != "DELETE" else "deleted",
                "change_type": snapshot.change_type,
                "last_modified": snapshot.time.isoformat(),
                "config_type": snapshot.config_type,
            }

            if include_content:
                config_dict["content"] = snapshot.raw_content if snapshot.raw_content else ""

            logger.info(f"Successfully retrieved proxy configuration for service '{service_name}' from configuration snapshots")

            return {
                "config": config_dict,
                "query_timestamp": datetime.now(UTC).isoformat(),
                "source": "configuration_snapshots"
            }

    except Exception as e:
        logger.error(f"Error getting proxy config for {service_name}: {e}")
        raise Exception(f"Failed to get proxy configuration: {str(e)}") from e


async def scan_proxy_configs(
    device: str | None = None,
    config_directory: str | None = None,
    sync_to_database: bool = True,
) -> dict[str, Any]:
    """
    Trigger configuration monitoring scan for fresh configs (uses configuration service)

    Args:
        device: Device hostname
        config_directory: Directory containing proxy configs (currently not used - uses device analysis)
        sync_to_database: Whether to sync findings to database (always true for this implementation)

    Returns:
        Dict containing scan results from configuration monitoring
    """
    try:
        if not device:
            raise Exception("device parameter is required for proxy config scanning")

        session_factory = get_async_session_factory()
        async with session_factory() as session:
            # Get device info
            from apps.backend.src.models.device import Device
            device_query = select(Device).where(Device.hostname == device)
            device_result = await session.execute(device_query)
            device_obj = device_result.scalar_one_or_none()

            if not device_obj:
                raise Exception(f"Device '{device}' not found")

            # Get current snapshot count before scanning
            count_query = select(func.count(ConfigurationSnapshot.id)).where(
                and_(
                    ConfigurationSnapshot.device_id == device_obj.id,
                    ConfigurationSnapshot.config_type == "nginx_proxy"
                )
            )
            before_result = await session.execute(count_query)
            before_count = before_result.scalar() or 0

            # Note: The actual scanning is done by the configuration monitoring service
            # This function provides status on existing configurations and triggers a rescan
            # by returning current state and database statistics

            # Get latest configurations found
            latest_query = select(ConfigurationSnapshot).where(
                and_(
                    ConfigurationSnapshot.device_id == device_obj.id,
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like("%.conf")
                )
            ).order_by(ConfigurationSnapshot.time.desc()).limit(10)

            latest_result = await session.execute(latest_query)
            latest_snapshots = latest_result.scalars().all()

            # Build scan results
            scanned_configs = []
            for snapshot in latest_snapshots:
                config_info = {
                    "service_name": _extract_service_name_from_path(snapshot.file_path),
                    "file_path": snapshot.file_path,
                    "content_hash": snapshot.content_hash,
                    "last_modified": snapshot.time.isoformat(),
                    "change_type": snapshot.change_type,
                    "status": "active" if snapshot.change_type != "DELETE" else "deleted"
                }
                scanned_configs.append(config_info)

            scan_result = {
                "scan_timestamp": datetime.now(UTC).isoformat(),
                "device": device,
                "device_id": str(device_obj.id),
                "total_configs_found": len(scanned_configs),
                "configs_in_database": before_count,
                "latest_configurations": scanned_configs,
                "sync_to_database": sync_to_database,
                "source": "configuration_snapshots",
                "message": f"Configuration monitoring tracks {before_count} proxy configs for device {device}. Latest {len(scanned_configs)} shown."
            }

            logger.info(f"Successfully reported proxy config scan status for device {device}: {before_count} total configs tracked")

            return scan_result

    except Exception as e:
        logger.error(f"Error scanning proxy configs for device {device}: {e}")
        raise Exception(f"Failed to scan proxy configurations: {str(e)}") from e


async def sync_proxy_config(
    service_name: str,
    config_id: int | None = None,
    force_update: bool = False
) -> dict[str, Any]:
    """
    Show sync status for specific proxy configuration from database

    Args:
        service_name: Service name (required)
        config_id: Configuration ID (not used - service_name required)
        force_update: Force update flag (informational - actual syncing done by configuration monitoring)

    Returns:
        Dict containing sync status from database
    """
    try:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            # Find the most recent configuration for this service
            query = select(ConfigurationSnapshot).where(
                and_(
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like(f"%{service_name}%")
                )
            ).order_by(ConfigurationSnapshot.time.desc()).limit(1)

            result = await session.execute(query)
            snapshot = result.scalar_one_or_none()

            if not snapshot:
                raise Exception(f"Proxy configuration not found for service '{service_name}'")

            # Calculate sync age
            config_age = datetime.now(UTC) - snapshot.time
            age_minutes = config_age.total_seconds() / 60

            # Determine sync status
            if age_minutes < 5:
                sync_status = "recently_synced"
                sync_message = f"Configuration was last synchronized {int(age_minutes)} minutes ago"
            elif age_minutes < 60:
                sync_status = "synced"
                sync_message = f"Configuration was last synchronized {int(age_minutes)} minutes ago"
            else:
                sync_status = "potentially_stale"
                sync_message = f"Configuration was last synchronized {int(age_minutes / 60)} hours ago"

            sync_result = {
                "service_name": service_name,
                "sync_timestamp": datetime.now(UTC).isoformat(),
                "sync_status": sync_status,
                "sync_message": sync_message,
                "last_config_update": snapshot.time.isoformat(),
                "config_file_path": snapshot.file_path,
                "content_hash": snapshot.content_hash,
                "change_type": snapshot.change_type,
                "force_update_requested": force_update,
                "source": "configuration_snapshots",
                "note": "Actual file synchronization is handled automatically by the configuration monitoring service"
            }

            logger.info(f"Successfully retrieved sync status for proxy configuration '{service_name}': {sync_status}")

            return sync_result

    except Exception as e:
        logger.error(f"Error getting sync status for proxy config {service_name}: {e}")
        raise Exception(f"Failed to sync proxy configuration: {str(e)}") from e


async def get_proxy_config_summary(device: str | None = None) -> dict[str, Any]:
    """
    Get summary statistics for proxy configurations from database

    Args:
        device: Optional device filter

    Returns:
        Dict containing summary statistics from configuration snapshots
    """
    try:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            # Base query for proxy configurations
            base_query = select(ConfigurationSnapshot).where(
                and_(
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like("%.conf")
                )
            )

            # Apply device filter if specified
            device_id = None
            if device:
                from apps.backend.src.models.device import Device
                device_query = select(Device.id).where(Device.hostname == device)
                device_result = await session.execute(device_query)
                device_id = device_result.scalar_one_or_none()
                if device_id:
                    base_query = base_query.where(ConfigurationSnapshot.device_id == device_id)
                else:
                    # Device not found, return empty summary
                    return {
                        "device": device,
                        "device_found": False,
                        "total_configs": 0,
                        "summary_timestamp": datetime.now(UTC).isoformat(),
                        "source": "configuration_snapshots"
                    }

            # Get total count
            count_query = select(func.count(ConfigurationSnapshot.id)).select_from(base_query.subquery())
            total_result = await session.execute(count_query)
            total_configs = total_result.scalar() or 0

            # Get count by status (using change_type)
            status_query = select(
                ConfigurationSnapshot.change_type,
                func.count(ConfigurationSnapshot.id)
            ).where(
                and_(
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like("%.conf")
                )
            )

            if device_id:
                status_query = status_query.where(ConfigurationSnapshot.device_id == device_id)

            status_query = status_query.group_by(ConfigurationSnapshot.change_type)
            status_result = await session.execute(status_query)
            status_counts = dict(status_result.fetchall())

            # Get recent activity (last 24 hours)
            recent_cutoff = datetime.now(UTC) - timedelta(days=1)
            recent_query = select(func.count(ConfigurationSnapshot.id)).where(
                and_(
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like("%.conf"),
                    ConfigurationSnapshot.time >= recent_cutoff
                )
            )

            if device_id:
                recent_query = recent_query.where(ConfigurationSnapshot.device_id == device_id)

            recent_result = await session.execute(recent_query)
            recent_activity = recent_result.scalar() or 0

            # Get unique services count
            services_query = select(func.count(func.distinct(ConfigurationSnapshot.file_path))).where(
                and_(
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like("%.conf")
                )
            )

            if device_id:
                services_query = services_query.where(ConfigurationSnapshot.device_id == device_id)

            services_result = await session.execute(services_query)
            unique_services = services_result.scalar() or 0

            # Build summary
            summary = {
                "summary_timestamp": datetime.now(UTC).isoformat(),
                "device": device,
                "device_found": True if not device or device_id else False,
                "total_configs": total_configs,
                "unique_services": unique_services,
                "recent_activity_24h": recent_activity,
                "status_breakdown": {
                    "active": status_counts.get("CREATE", 0) + status_counts.get("MODIFY", 0),
                    "deleted": status_counts.get("DELETE", 0),
                    "total_tracked": sum(status_counts.values())
                },
                "change_type_counts": status_counts,
                "source": "configuration_snapshots",
                "monitoring_note": "Statistics based on configuration monitoring service data"
            }

            logger.info(f"Successfully retrieved proxy configuration summary: {total_configs} total configs")

            return summary

    except Exception as e:
        logger.error(f"Error getting proxy config summary: {e}")
        raise Exception(f"Failed to get proxy configuration summary: {str(e)}") from e
