"""
VM Management API Endpoints

REST API endpoints for managing virtual machines and accessing VM logs
across infrastructure devices.
"""

import logging
from typing import Any, Dict
from uuid import UUID
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from apps.backend.src.api.common import get_current_user
from apps.backend.src.core.database import get_async_session_factory
from apps.backend.src.services.device_service import DeviceService
from apps.backend.src.services.unified_data_collection import get_unified_data_collection_service
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple, get_ssh_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{hostname}/logs")
async def get_vm_logs(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    live: bool = Query(False, description="Force fresh data collection"),
    current_user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get libvirtd daemon logs from a device"""
    try:
        # Get unified service
        session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=session_factory,
            ssh_client=ssh_client
        )

        # Get device ID from hostname
        async with session_factory() as db:
            device_service = DeviceService(db)
            device = await device_service.get_device_by_hostname(hostname)
            device_id = cast(UUID, device.id)

        # Define collection method for VM logs
        async def collect_vm_logs() -> Dict[str, Any]:
            # Get libvirtd.log or fallback to journalctl
            log_command = "cat /var/log/libvirt/libvirtd.log 2>/dev/null || journalctl -u libvirtd --no-pager -n 100"
            result = await execute_ssh_command_simple(hostname, log_command, timeout)

            if result.return_code == 0:
                log_content = result.stdout
            else:
                log_content = f"Error reading libvirt logs: {result.stderr}"

            return {
                "hostname": hostname,
                "log_source": "libvirtd.log or journalctl",
                "logs": log_content,
                "success": result.return_code == 0,
            }

        # Use unified service to collect data
        # VM logs change moderately so use appropriate cache TTL
        result: Dict[str, Any] = await unified_service.collect_and_store_data(
            data_type="vm_logs",
            device_id=device_id,
            collection_method=collect_vm_logs,
            force_refresh=live,
            correlation_id=f"vm_logs_{hostname}"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting VM logs for {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get VM logs: {str(e)}") from e


@router.get("/{hostname}/logs/{vm_name}")
async def get_vm_specific_logs(
    hostname: str = Path(..., description="Device hostname"),
    vm_name: str = Path(..., description="VM name"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    live: bool = Query(False, description="Force fresh data collection"),
    current_user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get logs for a specific VM"""
    try:
        # Get unified service
        session_factory = get_async_session_factory()
        ssh_client = get_ssh_client()
        unified_service = await get_unified_data_collection_service(
            db_session_factory=session_factory,
            ssh_client=ssh_client
        )

        # Get device ID from hostname
        async with session_factory() as db:
            device_service = DeviceService(db)
            device = await device_service.get_device_by_hostname(hostname)
            device_id = cast(UUID, device.id)

        # Define collection method for specific VM logs
        async def collect_vm_specific_logs() -> Dict[str, Any]:
            # Get specific VM log file
            log_command = (
                f"cat /var/log/libvirt/qemu/{vm_name}.log 2>/dev/null || echo 'VM log not found'"
            )
            result = await execute_ssh_command_simple(hostname, log_command, timeout)

            if result.return_code == 0:
                log_content = result.stdout
            else:
                log_content = f"Error reading VM logs: {result.stderr}"

            return {
                "hostname": hostname,
                "vm_name": vm_name,
                "log_source": f"qemu/{vm_name}.log",
                "logs": log_content,
                "success": result.return_code == 0,
            }

        # Use unified service to collect data
        # Specific VM logs change moderately
        result: Dict[str, Any] = await unified_service.collect_and_store_data(
            data_type="vm_specific_logs",
            device_id=device_id,
            collection_method=collect_vm_specific_logs,
            force_refresh=live,
            correlation_id=f"vm_specific_logs_{hostname}_{vm_name}"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting VM logs for {vm_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get VM logs: {str(e)}") from e
