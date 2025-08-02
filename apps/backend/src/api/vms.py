"""
VM Management API Endpoints

REST API endpoints for managing virtual machines and accessing VM logs
across infrastructure devices.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{hostname}/logs")
async def get_vm_logs(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Get libvirtd daemon logs from a device"""
    try:
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
            "execution_time": result.execution_time,
        }
    except Exception as e:
        logger.error(f"Error getting VM logs for {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get VM logs: {str(e)}") from e


@router.get("/{hostname}/logs/{vm_name}")
async def get_vm_specific_logs(
    hostname: str = Path(..., description="Device hostname"),
    vm_name: str = Path(..., description="VM name"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    current_user=Depends(get_current_user),
):
    """Get logs for a specific VM"""
    try:
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
            "execution_time": result.execution_time,
        }
    except Exception as e:
        logger.error(f"Error getting VM logs for {vm_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get VM logs: {str(e)}") from e