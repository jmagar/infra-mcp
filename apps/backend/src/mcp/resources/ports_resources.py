"""
MCP Resources for Network Ports

Provides access to network port information and listening processes via the ports:// URI scheme.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def get_ports_resource(uri: str) -> str:
    """
    Handle ports:// resource requests.
    
    URI format: ports://{device}
    Returns network port information and listening processes.
    """
    try:
        # Parse URI
        if not uri.startswith("ports://"):
            raise ValueError(f"Invalid URI scheme. Expected ports://, got: {uri}")
        
        path = uri[8:]  # Remove "ports://" prefix
        if not path:
            raise ValueError("Device name is required in URI")
        
        device = path.strip('/')
        if not device:
            raise ValueError("Device name cannot be empty")
        
        # Get ports via REST API
        import httpx
        from apps.backend.src.core.config import get_settings
        
        settings = get_settings()
        headers = {}
        if settings.auth.api_key:
            headers['Authorization'] = f"Bearer {settings.auth.api_key}"
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"http://localhost:9101/api/devices/{device}/ports",
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
        
        # Parse ss output
        output = result.get("raw_output", "")
        lines = output.strip().split('\n')
        
        # Skip header line and parse each line
        ports_data = []
        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue
                
            parts = line.split()
            if len(parts) >= 5:
                protocol = parts[0]
                state = parts[1] if protocol.upper() == 'TCP' else 'N/A'
                local_addr = parts[4]
                
                # Extract process info if available (last column)
                process_info = ""
                if len(parts) > 5:
                    process_info = parts[-1]
                
                # Parse local address into IP and port
                if ':' in local_addr:
                    ip, port = local_addr.rsplit(':', 1)
                    # Handle IPv6 addresses
                    if ip.startswith('[') and ip.endswith(']'):
                        ip = ip[1:-1]
                else:
                    ip = local_addr
                    port = "N/A"
                
                ports_data.append({
                    "protocol": protocol,
                    "state": state,
                    "ip": ip,
                    "port": port,
                    "local_address": local_addr,
                    "process": process_info
                })
        
        resource_data = {
            "device": device,
            "timestamp": result.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "command": "ss -tulpn",
            "total_ports": len(ports_data),
            "ports": ports_data,
            "raw_output": output
        }
        
        return json.dumps(resource_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting ports resource: {e}")
        error_data = {
            "error": str(e),
            "device": device if 'device' in locals() else "unknown", 
            "uri": uri
        }
        return json.dumps(error_data, ensure_ascii=False, indent=2)


async def list_ports_resources() -> list[dict[str, Any]]:
    """
    List available ports resources.
    This would typically list all devices that support port information.
    """
    try:
        from apps.backend.src.core.database import get_async_session
        from apps.backend.src.models.device import Device
        from sqlalchemy import select
        
        async with get_async_session() as session:
            query = select(Device).where(Device.monitoring_enabled == True)
            result = await session.execute(query)
            devices = result.scalars().all()
        
        resources = []
        for device in devices:
            resources.append({
                "uri": f"ports://{device.hostname}",
                "name": f"Network Ports - {device.hostname}",
                "description": f"Network port information and listening processes for {device.hostname}",
                "mime_type": "application/json"
            })
        
        return resources
        
    except Exception as e:
        logger.error(f"Error listing ports resources: {e}")
        return []