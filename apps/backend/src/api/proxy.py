"""
Proxy Configuration API Endpoints

REST API endpoints for managing SWAG reverse proxy configurations
with real-time file access and database synchronization.
"""

from datetime import UTC, datetime
import logging
import time
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import and_, select

from apps.backend.src.core.database import get_async_session, get_async_session_factory
from apps.backend.src.mcp.resources.proxy_configs import get_proxy_config_resource
from apps.backend.src.models.device import Device
from apps.backend.src.schemas.proxy_config import (
    ProxyConfigList,
    ProxyConfigResponse,
    ProxyConfigSummary,
    ProxyConfigSync,
)
from apps.backend.src.services.device_service import DeviceService

# Import services and utilities for proxy management
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.utils.ssh_client import SSHConnectionInfo, get_ssh_client

logger = logging.getLogger(__name__)

router = APIRouter()


# Removed proxy service dependency - using MCP tools directly

# Cache SWAG device detection to prevent repeated expensive scans
_swag_device_cache: str | None = None
_swag_device_cache_timestamp: float = 0
SWAG_CACHE_TTL = 300  # 5 minutes

async def _detect_swag_device() -> str:
    """
    Detect the SWAG device by looking for running SWAG containers and */swag/nginx/* directories.
    
    Returns:
        str: SWAG device hostname
        
    Raises:
        HTTPException: If SWAG device cannot be determined
    """
    global _swag_device_cache, _swag_device_cache_timestamp

    # Check cache first
    current_time = time.time()
    if (_swag_device_cache is not None and
        (current_time - _swag_device_cache_timestamp) < SWAG_CACHE_TTL):
        logger.debug(f"Using cached SWAG device: {_swag_device_cache}")
        return _swag_device_cache

    # Search for devices with running SWAG containers
    try:
        async with get_async_session() as session:
            # Get all monitoring-enabled devices
            devices_result = await session.execute(
                select(Device).where(
                    Device.monitoring_enabled == True
                )
            )
            devices = devices_result.scalars().all()

            ssh_client = get_ssh_client()

            for device in devices:
                try:
                    # Check for running SWAG container AND */swag/nginx/* directory
                    swag_check_cmd = (
                        "docker ps --format '{{.Names}}' | grep -i swag && "
                        "find /*/swag/nginx/ -type d 2>/dev/null | head -1 || "
                        "find /mnt/*/swag/nginx/ -type d 2>/dev/null | head -1"
                    )

                    # Use only native-typed fields for SSH connection; rely on SSH config
                    connection_info = SSHConnectionInfo(
                        host=str(device.hostname),
                        connect_timeout=10,
                    )

                    ssh_exec = await ssh_client.execute_command(
                        connection_info, swag_check_cmd, timeout=15
                    )

                    if ssh_exec.return_code == 0 and ssh_exec.stdout.strip():
                        lines = ssh_exec.stdout.strip().split('\n')
                        has_running_container = any('swag' in line.lower() for line in lines if not line.startswith('/'))
                        has_nginx_dir = any(line.startswith('/') and 'swag/nginx' in line for line in lines)

                        if has_running_container and has_nginx_dir:
                            # Cache the result
                            _swag_device_cache = str(device.hostname)
                            _swag_device_cache_timestamp = current_time
                            logger.info(f"Found SWAG device: {device.hostname} (running container + nginx directory)")
                            return str(device.hostname)

                except Exception as e:
                    logger.debug(f"Could not check SWAG on device {device.hostname}: {e}")
                    continue

        # No SWAG device found
        raise HTTPException(
            status_code=404,
            detail="No SWAG device found with running container and nginx directory"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting SWAG device: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"SWAG device detection failed: {str(e)}"
        )


async def _get_proxy_configs_from_snapshots(
    device_id: UUID,
    service_name: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> dict[str, Any]:
    """
    Get proxy configurations from configuration_snapshots table (cached data from file watchers).
    """
    from sqlalchemy import and_, select

    from apps.backend.src.models.configuration import ConfigurationSnapshot

    async with get_async_session() as session:
        # Query for nginx_proxy configuration snapshots - only .conf files
        query = select(ConfigurationSnapshot).where(
            and_(
                ConfigurationSnapshot.device_id == device_id,
                ConfigurationSnapshot.config_type == "nginx_proxy",
                ConfigurationSnapshot.file_path.like("%.conf")
            )
        ).order_by(
            ConfigurationSnapshot.file_path,
            ConfigurationSnapshot.time.desc()
        ).limit(limit).offset(offset)

        result = await session.execute(query)
        snapshots = result.scalars().all()

        # Convert snapshots to proxy config format
        configs = []
        for snapshot in snapshots:
            file_path_str = str(snapshot.file_path)
            config = {
                "id": str(snapshot.id),
                "service_name": _extract_service_name_from_path(file_path_str),
                "file_path": file_path_str,
                "content": snapshot.raw_content,
                "content_hash": snapshot.content_hash,
                "last_modified": snapshot.time.isoformat(),
                "change_type": snapshot.change_type,
                "config_type": snapshot.config_type,
                "status": "active" if snapshot.change_type != "DELETE" else "deleted"
            }

            # Apply service_name filter if specified
            if service_name and config["service_name"] != service_name:
                continue

            configs.append(config)

        # Get total count for pagination - only .conf files
        total_query = select(ConfigurationSnapshot).where(
            and_(
                ConfigurationSnapshot.device_id == device_id,
                ConfigurationSnapshot.config_type == "nginx_proxy",
                ConfigurationSnapshot.file_path.like("%.conf")
            )
        )
        total_result = await session.execute(total_query)
        total = len(total_result.scalars().all())

        return {
            "configs": configs[:limit],  # Apply limit after filtering
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "page": (offset // limit) + 1,
                "total_pages": (total + limit - 1) // limit,
            },
            "source": "configuration_snapshots",
            "query_timestamp": datetime.now(UTC).isoformat(),
        }


def _extract_service_name_from_path(file_path: str) -> str:
    """Extract service name from proxy config file path."""
    from pathlib import Path
    filename = Path(file_path).name

    # Remove common extensions (.conf, .subdomain.conf, etc.)
    service_name = filename
    for ext in ['.subdomain.conf', '.subfolder.conf', '.conf']:
        if service_name.endswith(ext):
            service_name = service_name[:-len(ext)]
            break

    return service_name


async def _collect_proxy_configs_live(
    device: str,
    device_id: UUID,
    service_name: str | None = None,
    status: str | None = None,
    ssl_enabled: bool | None = None,
    limit: int = 100,
    offset: int = 0
) -> dict[str, Any]:
    """
    Live collection method for proxy configurations using unified data collection service.
    """
    # Get unified data collection service
    db_session_factory = get_async_session_factory()
    ssh_client = get_ssh_client()
    unified_service = await get_unified_data_collection_service(
        db_session_factory=db_session_factory,
        ssh_client=ssh_client
    )

    # Create collection method for proxy configs
    async def collect_proxy_configs() -> dict[str, Any]:
        # Implementation will collect proxy configs using SSH
        # For now, return minimal structure
        return {
            "configs": [],
            "pagination": {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "page": 1,
                "total_pages": 0
            },
            "device": device
        }

    # Use unified data collection
    result = await unified_service.collect_and_store_data(
        collection_method=collect_proxy_configs,
        device_id=device_id,
        data_type="proxy_configurations"
    )

    result["source"] = "live_collection"
    return result


@router.get("/configs", response_model=ProxyConfigList)
async def list_configs(
    device: str | None = Query(None, description="Device hostname (auto-detected if not provided)"),
    service_name: str | None = Query(None, description="Filter by service name"),
    status: str | None = Query(None, description="Filter by status"),
    ssl_enabled: bool | None = Query(None, description="Filter by SSL status"),
    limit: int = Query(100, description="Maximum number of results", ge=1, le=1000),
    offset: int = Query(0, description="Results offset for pagination", ge=0),
    live: bool = Query(False, description="Force fresh data collection"),
) -> ProxyConfigList:
    """List all proxy configurations - reads from cached file watcher data first, falls back to live collection"""
    try:
        # Auto-detect SWAG device if not provided
        if not device:
            device = await _detect_swag_device()

        # Get device ID from hostname
        session_factory = get_async_session_factory()
        async with session_factory() as db:
            device_service = DeviceService(db)
            device_obj = await device_service.get_device_by_hostname(device)
            device_uuid = cast(UUID, device_obj.id)

        result = None

        # Try cached data first (unless live is explicitly requested)
        if not live:
            try:
                result = await _get_proxy_configs_from_snapshots(
                    device_id=device_uuid,
                    service_name=service_name,
                    limit=limit,
                    offset=offset
                )

                # If we got results from snapshots, use them
                if result and result.get("configs"):
                    logger.info(f"Returning {len(result['configs'])} proxy configs from configuration snapshots")
                else:
                    logger.info("No proxy configs found in configuration snapshots, falling back to live collection")
                    result = None

            except Exception as e:
                logger.warning(f"Failed to read from configuration snapshots, falling back to live collection: {e}")
                result = None

        # Fall back to live collection if no cached data or if explicitly requested
        if result is None or live:
            logger.info("Performing live proxy config collection")
            result = await _collect_proxy_configs_live(
                device=device,
                device_id=device_uuid,
                service_name=service_name,
                status=status,
                ssl_enabled=ssl_enabled,
                limit=limit,
                offset=offset
            )

        # Transform the result to match ProxyConfigList schema
        pagination = result.get("pagination", {})
        return ProxyConfigList(
            items=result.get("configs", []),
            total=pagination.get("total", 0),
            page=pagination.get("page", 1),
            page_size=pagination.get("limit", limit),
            total_pages=pagination.get("total_pages", 0),
        )
    except Exception as e:
        logger.error(f"Error listing proxy configs: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/configs/{service_name}", response_model=ProxyConfigResponse)
async def get_config(
    service_name: str = Path(..., description="Service name"),
    device: str | None = Query(None, description="Device hostname (optional for disambiguation)"),
    include_content: bool = Query(True, description="Include raw configuration content"),
) -> dict:
    """Get specific proxy configuration from database"""
    try:
        from apps.backend.src.core.database import get_async_session
        from apps.backend.src.models.proxy_config import ProxyConfig

        async with get_async_session() as session:
            # Build query
            query = select(ProxyConfig).where(ProxyConfig.service_name == service_name)
            if device:
                query = query.where(ProxyConfig.device_hostname == device)

            # Execute query
            result = await session.execute(query)
            config = result.scalars().first()

            if not config:
                raise HTTPException(status_code=404, detail=f"Proxy configuration '{service_name}' not found")

            # Build response
            response = {
                "service_name": config.service_name,
                "device_hostname": config.device_hostname,
                "file_path": config.file_path,
                "ssl_enabled": config.ssl_enabled,
                "upstream_host": config.upstream_host,
                "upstream_port": config.upstream_port,
                "domain": config.domain,
                "subdomain": config.subdomain,
                "status": config.status,
                "last_modified": config.last_modified.isoformat() if config.last_modified else None,
                "created_at": config.created_at.isoformat() if config.created_at else None,
            }

            if include_content:
                # Get content from MCP resource if needed
                try:
                    from apps.backend.src.mcp.resources.proxy_configs import (
                        get_proxy_config_resource,
                    )
                    uri = f"swag://{service_name}"
                    resource_data = await get_proxy_config_resource(uri)
                    response["content"] = resource_data.get("content", "")
                except Exception as e:
                    logger.warning(f"Could not get content for {service_name}: {e}")
                    response["content"] = ""

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proxy config for {service_name}: {e}")
        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 500, detail=str(e)
        ) from e


@router.get("/configs/{service_name}/content", response_class=PlainTextResponse)
async def get_config_content(
    service_name: str = Path(..., description="Service name"),
    device: str | None = Query(None, description="Device hostname (auto-detected if not provided)"),
) -> str:
    """Get raw configuration file content"""
    try:
        # Use resource handler to get content
        uri = f"swag://{service_name}"
        resource_data = await get_proxy_config_resource(uri)

        if "error" in resource_data:
            raise HTTPException(status_code=404, detail=resource_data["error"])

        return str(resource_data.get("content", ""))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config content for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/scan", response_model=ProxyConfigSync)
async def scan_configs(
    device: str | None = Query(None, description="Device hostname (auto-detected if not provided)"),
    config_directory: str = Query(
        "/mnt/appdata/swag/nginx/proxy-confs", description="Configuration directory path"
    ),
    sync_to_database: bool = Query(True, description="Whether to sync findings to database"),
) -> dict:
    """Scan and synchronize proxy configurations"""
    try:
        # Auto-detect SWAG device if not provided
        device = device or await _detect_swag_device()

        # For now, return a basic response since scanning is handled by file watchers
        return {
            "message": f"Proxy config scanning initiated for device {device}",
            "device": device,
            "config_directory": config_directory,
            "sync_enabled": sync_to_database,
            "status": "initiated"
        }
    except Exception as e:
        logger.error(f"Error scanning proxy configs: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/configs/{service_name}/sync", response_model=ProxyConfigResponse)
async def sync_config(
    service_name: str = Path(..., description="Service name"),
    device: str | None = Query(None, description="Device hostname (optional)"),
) -> dict:
    """Synchronize specific proxy configuration"""
    try:
        # Auto-detect device if not provided
        device = device or await _detect_swag_device()

        # Return basic sync response - actual syncing is handled by file watchers
        return {
            "service_name": service_name,
            "device": device,
            "status": "sync_requested",
            "message": f"Sync requested for {service_name} on {device}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing proxy config for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/summary", response_model=ProxyConfigSummary)
async def get_summary(device: str | None = Query(None, description="Device hostname (auto-detected if not provided)")) -> dict:
    """Get proxy configuration summary statistics"""
    try:
        # Auto-detect SWAG device if not provided
        device = device or await _detect_swag_device()

        # Get summary from configuration snapshots
        from apps.backend.src.models.configuration import ConfigurationSnapshot
        async with get_async_session() as session:
            # Get device ID
            device_service = DeviceService(session)
            device_obj = await device_service.get_device_by_hostname(device)
            device_id = device_obj.id

            # Query configuration snapshots for summary stats - only .conf files in proxy-confs
            query = select(ConfigurationSnapshot).where(
                and_(
                    ConfigurationSnapshot.device_id == device_id,
                    ConfigurationSnapshot.config_type == "nginx_proxy",
                    ConfigurationSnapshot.file_path.like("%.conf")
                )
            )
            result = await session.execute(query)
            snapshots = result.scalars().all()

            # Calculate summary statistics - only count .conf files
            total_configs = len(snapshots)
            active_configs = len([s for s in snapshots if s.change_type != "DELETE"])

            return {
                "device": device,
                "total_configs": total_configs,
                "active_configs": active_configs,
                "monitoring_enabled": True,
                "last_scan": datetime.now(UTC).isoformat() if snapshots else None
            }
    except Exception as e:
        logger.error(f"Error getting proxy config summary: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/templates/{template_type}", response_class=PlainTextResponse)
async def get_template(
    template_type: str = Path(..., description="Template type: subdomain or subfolder"),
) -> str:
    """Get SWAG configuration template"""
    try:
        if template_type not in ["subdomain", "subfolder"]:
            raise HTTPException(
                status_code=400, detail="Template type must be 'subdomain' or 'subfolder'"
            )

        uri = f"swag://{template_type}-template"
        resource_data = await get_proxy_config_resource(uri)

        if "error" in resource_data:
            raise HTTPException(status_code=404, detail=resource_data["error"])

        return str(resource_data.get("content", ""))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/samples", response_model=dict)
async def list_samples() -> dict:
    """List all available SWAG sample configurations"""
    try:
        uri = "swag://samples/"
        resource_data = await get_proxy_config_resource(uri)

        if "error" in resource_data:
            raise HTTPException(status_code=500, detail=resource_data["error"])

        return resource_data
    except Exception as e:
        logger.error(f"Error listing samples: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/samples/{sample_name}", response_class=PlainTextResponse)
async def get_sample(
    sample_name: str = Path(
        ..., description="Sample name (e.g., 'nextcloud' or 'nextcloud.subdomain.sample')"
    ),
) -> str:
    """Get SWAG sample configuration content"""
    try:
        uri = f"swag://samples/{sample_name}"
        resource_data = await get_proxy_config_resource(uri)

        if "error" in resource_data:
            raise HTTPException(status_code=404, detail=resource_data["error"])

        return str(resource_data.get("content", ""))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sample {sample_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

