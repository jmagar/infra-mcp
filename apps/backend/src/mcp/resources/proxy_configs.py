"""
Proxy Configuration MCP Resources

MCP resources for exposing SWAG reverse proxy configurations
with real-time file access and database integration.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
from urllib.parse import urlparse, parse_qs

from apps.backend.src.mcp.tools.proxy_management import (
    _get_real_time_file_info, _get_real_time_file_content
)
from apps.backend.src.utils.nginx_parser import NginxConfigParser
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.proxy_config import ProxyConfig
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)



async def get_proxy_config_resource(uri: str) -> dict[str, Any]:
    """
    Get SWAG proxy configuration resource content
    
    Resource URI formats:
    - swag://service_name - Direct access to service config (discovers device automatically)
    - swag://device/directory - Directory listing for specific device
    - swag://device/summary - Summary for specific device
    
    Args:
        uri: Resource URI
        
    Returns:
        Dict containing resource content
    """
    try:
        parsed_uri = urlparse(uri)
        device = parsed_uri.netloc
        path = parsed_uri.path.lstrip('/')
        query_params = parse_qs(parsed_uri.query)
        
        # Extract options
        force_refresh = query_params.get('force_refresh', ['false'])[0].lower() == 'true'
        include_parsed = query_params.get('include_parsed', ['true'])[0].lower() == 'true'
        format_type = query_params.get('format', ['raw'])[0]  # raw, json, yaml
        
        # Handle different URI patterns
        if not device and not path:
            raise ValueError("Invalid SWAG URI format. Use: swag://service_name or swag://device/directory")
        
        # Pattern 1: swag://service_name (most common)
        if device and not path:
            service_name = device  # device is actually the service name in this pattern
            # All SWAG configs are on "squirts" - the reverse proxy host
            swag_device = "squirts"
            
            # Handle special template requests
            if service_name == "subdomain-template":
                return await _get_template_resource(swag_device, "_template.subdomain.conf.sample", format_type, include_parsed)
            elif service_name == "subfolder-template":
                return await _get_template_resource(swag_device, "_template.subfolder.conf.sample", format_type, include_parsed)
            
            return await _get_service_config_resource(swag_device, service_name, force_refresh, include_parsed, format_type)
        
        # Pattern 2: swag://configs - Directory listing of all active configs
        elif device == 'configs' and not path:
            swag_device = "squirts"
            config_dir = query_params.get('dir', ['/mnt/appdata/swag/nginx/proxy-confs'])[0]
            return await _get_directory_listing_resource(swag_device, config_dir)
        
        # Pattern 3: swag://summary - Summary statistics  
        elif device == 'summary' and not path:
            swag_device = "squirts"
            return await _get_proxy_summary_resource(swag_device)
        
        # Pattern 4: swag://samples/filename
        elif device == 'samples' and path:
            swag_device = "squirts"
            return await _get_sample_resource(swag_device, path, format_type, include_parsed)
        
        # Pattern 5: swag://samples (directory listing of samples)
        elif device == 'samples' and not path:
            swag_device = "squirts"
            return await _get_samples_directory_resource(swag_device)
        
        else:
            raise ValueError(f"Unknown SWAG URI format: {uri}. Use swag://service_name, swag://configs, swag://summary, or swag://samples/")
        
    except Exception as e:
        logger.error(f"Error getting proxy config resource {uri}: {e}")
        return {
            'error': str(e),
            'uri': uri,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'error'
        }


async def _get_template_resource(
    device: str,
    template_filename: str,
    format_type: str = 'raw',
    include_parsed: bool = True
) -> dict[str, Any]:
    """Get SWAG template configuration file"""
    
    try:
        # SWAG template files are in the same directory as configs
        template_path = f"/mnt/appdata/swag/nginx/proxy-confs/{template_filename}"
        
        # Get real-time file info and content
        file_info = await _get_real_time_file_info(device, template_path)
        
        if not file_info.get('exists', False):
            return {
                'error': f'SWAG template file not found: {template_filename}',
                'template_filename': template_filename,
                'device': device,
                'file_path': template_path,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'resource_type': 'template_not_found'
            }
        
        # Get content
        content = await _get_real_time_file_content(device, template_path)
        
        if content is None:
            return {
                'error': 'Failed to read SWAG template file',
                'template_filename': template_filename,
                'device': device,
                'file_path': template_path,
                'file_info': file_info,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'resource_type': 'template_read_error'
            }
        
        # Determine template type
        template_type = 'subdomain' if 'subdomain' in template_filename else 'subfolder'
        
        resource_data = {
            'uri': f"swag://{template_type}-template",
            'template_type': template_type,
            'template_filename': template_filename,
            'device': device,
            'file_path': template_path,
            'file_info': file_info,
            'content_length': len(content),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'swag_template',
            'format': format_type
        }
        
        # Format content based on requested format
        if format_type == 'raw':
            resource_data['content'] = content
            resource_data['mime_type'] = 'text/plain'
            
        elif format_type == 'json':
            if include_parsed:
                parser = NginxConfigParser()
                parsed_config = parser.parse_config_content(content, template_path)
                resource_data['parsed_config'] = parsed_config
            
            resource_data['raw_content'] = content
            resource_data['mime_type'] = 'application/json'
            
        elif format_type == 'yaml':
            if include_parsed:
                parser = NginxConfigParser()
                parsed_config = parser.parse_config_content(content, template_path)
                resource_data['parsed_config'] = parsed_config
            
            resource_data['raw_content'] = content
            resource_data['mime_type'] = 'application/yaml'
        
        # Always include parsed config if requested
        if include_parsed and format_type == 'raw':
            parser = NginxConfigParser()
            parsed_config = parser.parse_config_content(content, template_path)
            resource_data['parsed_config'] = parsed_config
        
        return resource_data
        
    except Exception as e:
        logger.error(f"Error getting SWAG template {template_filename}: {e}")
        return {
            'error': str(e),
            'template_filename': template_filename,
            'device': device,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'template_error'
        }


async def _get_sample_resource(
    device: str,
    sample_filename: str,
    format_type: str = 'raw',
    include_parsed: bool = True
) -> dict[str, Any]:
    """Get individual SWAG sample configuration file"""
    
    try:
        # If full filename provided, use it directly
        if sample_filename.endswith('.sample'):
            sample_path = f"/mnt/appdata/swag/nginx/proxy-confs/{sample_filename}"
            file_info = await _get_real_time_file_info(device, sample_path)
        else:
            # Service name provided - find best matching sample file
            # Try in order of preference: subdomain, subfolder, then any match
            search_patterns = [
                f"{sample_filename}.subdomain.conf.sample",
                f"{sample_filename}.subfolder.conf.sample", 
                f"{sample_filename}.*.conf.sample"
            ]
            
            sample_path = None
            file_info = None
            actual_filename = None
            
            for pattern in search_patterns[:2]:  # Try exact patterns first
                test_path = f"/mnt/appdata/swag/nginx/proxy-confs/{pattern}"
                test_info = await _get_real_time_file_info(device, test_path)
                if test_info.get('exists', False):
                    sample_path = test_path
                    file_info = test_info
                    actual_filename = pattern
                    break
            
            # If no exact match, search with wildcards
            if not sample_path:
                ls_command = f"""
                find /mnt/appdata/swag/nginx/proxy-confs -name '{sample_filename}.*.conf.sample' -type f | head -1
                """
                from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
                result = await execute_ssh_command_simple(device, ls_command, timeout=10)
                output = result.stdout
                
                if output.strip():
                    sample_path = output.strip()
                    file_info = await _get_real_time_file_info(device, sample_path)
                    actual_filename = Path(sample_path).name
            
            # Update sample_filename to the actual found filename
            if actual_filename:
                sample_filename = actual_filename
        
        if not file_info or not file_info.get('exists', False):
            # Provide helpful error with search patterns attempted
            search_info = []
            if not sample_filename.endswith('.sample'):
                search_info = [
                    f"{sample_filename}.subdomain.conf.sample",
                    f"{sample_filename}.subfolder.conf.sample"
                ]
            
            return {
                'error': f'SWAG sample file not found: {sample_filename}',
                'sample_filename': sample_filename,
                'device': device,
                'file_path': sample_path,
                'searched_patterns': search_info if search_info else [sample_filename],
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'resource_type': 'sample_not_found'
            }
        
        # Get content
        content = await _get_real_time_file_content(device, sample_path)
        
        if content is None:
            return {
                'error': 'Failed to read SWAG sample file',
                'sample_filename': sample_filename,
                'device': device,
                'file_path': sample_path,
                'file_info': file_info,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'resource_type': 'sample_read_error'
            }
        
        # Parse sample info from filename
        path = Path(sample_path)
        base_name = path.stem  # removes .sample
        
        # Determine sample type and service name
        if base_name.startswith('_'):
            sample_type = 'template'
            service_name = base_name
        elif '.subdomain' in base_name:
            sample_type = 'subdomain'
            service_name = base_name.replace('.subdomain', '')
        elif '.subfolder' in base_name:
            sample_type = 'subfolder'
            service_name = base_name.replace('.subfolder', '')
        else:
            sample_type = 'unknown'
            service_name = base_name
        
        resource_data = {
            'uri': f"swag://samples/{sample_filename}",
            'sample_filename': sample_filename,
            'sample_type': sample_type,
            'service_name': service_name,
            'device': device,
            'file_path': sample_path,
            'file_info': file_info,
            'content_length': len(content),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'swag_sample',
            'format': format_type
        }
        
        # Format content based on requested format
        if format_type == 'raw':
            resource_data['content'] = content
            resource_data['mime_type'] = 'text/plain'
            
        elif format_type == 'json':
            if include_parsed:
                parser = NginxConfigParser()
                parsed_config = parser.parse_config_content(content, sample_path)
                resource_data['parsed_config'] = parsed_config
            
            resource_data['raw_content'] = content
            resource_data['mime_type'] = 'application/json'
            
        elif format_type == 'yaml':
            if include_parsed:
                parser = NginxConfigParser()
                parsed_config = parser.parse_config_content(content, sample_path)
                resource_data['parsed_config'] = parsed_config
            
            resource_data['raw_content'] = content
            resource_data['mime_type'] = 'application/yaml'
        
        # Always include parsed config if requested
        if include_parsed and format_type == 'raw':
            parser = NginxConfigParser()
            parsed_config = parser.parse_config_content(content, sample_path)
            resource_data['parsed_config'] = parsed_config
        
        return resource_data
        
    except Exception as e:
        logger.error(f"Error getting SWAG sample {sample_filename}: {e}")
        return {
            'error': str(e),
            'sample_filename': sample_filename,
            'device': device,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'sample_error'
        }


async def _get_samples_directory_resource(device: str) -> dict[str, Any]:
    """Get directory listing of all SWAG sample files"""
    
    try:
        # Execute directory listing for sample files only
        ls_command = f"""
        find /mnt/appdata/swag/nginx/proxy-confs -name '*.sample' -type f -exec stat -c '%n|%s|%Y|%A' {{}} \\; 2>/dev/null | sort
        """
        
        result = await execute_ssh_command_simple(device, ls_command, timeout=30)
        output = result.stdout
        
        samples = []
        for line in output.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 4:
                    file_path = parts[0]
                    file_size = int(parts[1])
                    mtime = int(parts[2])
                    permissions = parts[3]
                    
                    path = Path(file_path)
                    filename = path.name
                    base_name = path.stem  # removes .sample
                    
                    # Determine sample type and service name
                    if base_name.startswith('_'):
                        sample_type = 'template'
                        service_name = base_name
                        display_name = base_name.replace('_template.', '').replace('.conf', '').title() + ' Template'
                    elif '.subdomain' in base_name:
                        sample_type = 'subdomain'
                        service_name = base_name.replace('.subdomain', '')
                        display_name = f"{service_name.title()} Subdomain Sample"
                    elif '.subfolder' in base_name:
                        sample_type = 'subfolder'
                        service_name = base_name.replace('.subfolder', '')
                        display_name = f"{service_name.title()} Subfolder Sample"
                    else:
                        sample_type = 'unknown'
                        service_name = base_name
                        display_name = f"{service_name.title()} Sample"
                    
                    samples.append({
                        'filename': filename,
                        'display_name': display_name,
                        'sample_type': sample_type,
                        'service_name': service_name,
                        'file_path': file_path,
                        'file_size': file_size,
                        'last_modified': datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                        'permissions': permissions,
                        'readable': 'r' in permissions,
                        'resource_uri': f"swag://samples/{filename}"
                    })
        
        return {
            'uri': 'swag://samples/',
            'device': device,
            'samples_directory': '/mnt/appdata/swag/nginx/proxy-confs',
            'total_samples': len(samples),
            'samples': samples,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'swag_samples_directory'
        }
        
    except Exception as e:
        logger.error(f"Error getting samples directory for {device}: {e}")
        return {
            'error': str(e),
            'device': device,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'samples_directory_error'
        }


async def _get_service_config_resource(
    device: str,
    service_name: str,
    force_refresh: bool = False,
    include_parsed: bool = True,
    format_type: str = 'raw'
) -> dict[str, Any]:
    """Get service configuration with automatic device discovery and real-time content"""
    
    try:
        # Get database record if it exists (device is always "squirts" for SWAG configs)
        async with get_async_session() as session:
            query = select(ProxyConfig).where(ProxyConfig.service_name == service_name)
            result = await session.execute(query)
            config = result.scalar_one_or_none()
            
            if config:
                # Use database path
                file_path = config.file_path
            else:
                # Construct path based on SWAG convention: service.subdomain.conf
                file_path = f"/mnt/appdata/swag/nginx/proxy-confs/{service_name}.subdomain.conf"
        
        # Get real-time file info and content
        file_info = await _get_real_time_file_info(device, file_path)
        
        if not file_info.get('exists', False):
            # Try SWAG subfolder pattern if subdomain pattern doesn't exist
            subfolder_path = f"/mnt/appdata/swag/nginx/proxy-confs/{service_name}.subfolder.conf"
            subfolder_info = await _get_real_time_file_info(device, subfolder_path)
            
            if subfolder_info.get('exists', False):
                file_path = subfolder_path
                file_info = subfolder_info
            else:
                return {
                    'error': f'SWAG configuration file not found for service {service_name}',
                    'service_name': service_name,
                    'device': device,
                    'searched_paths': [
                        f"/mnt/appdata/swag/nginx/proxy-confs/{service_name}.subdomain.conf",
                        f"/mnt/appdata/swag/nginx/proxy-confs/{service_name}.subfolder.conf"
                    ],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'resource_type': 'service_not_found'
                }
        
        # Get content
        content = await _get_real_time_file_content(device, file_path)
        
        if content is None:
            return {
                'error': 'Failed to read service configuration file',
                'service_name': service_name,
                'device': device,
                'file_path': file_path,
                'file_info': file_info,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'resource_type': 'read_error'
            }
        
        # Parse service info from filename
        path = Path(file_path)
        filename = path.stem
        parts = filename.split('.')
        
        subdomain = parts[1] if len(parts) > 1 else service_name
        
        resource_data = {
            'uri': f"swag://{service_name}",
            'service_name': service_name,
            'device': device,
            'file_path': file_path,
            'file_name': path.name,
            'subdomain': subdomain,
            'file_info': file_info,
            'content_length': len(content),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'swag_service_config',
            'format': format_type
        }
        
        # Include database info if available
        if config:
            resource_data['database_info'] = {
                'config_id': config.id,
                'status': config.status,
                'created_at': config.created_at.isoformat(),
                'updated_at': config.updated_at.isoformat(),
                'file_hash': config.file_hash,
                'sync_status': config.sync_status,
                'sync_last_checked': config.sync_last_checked.isoformat() if config.sync_last_checked else None
            }
        
        # Format content based on requested format
        if format_type == 'raw':
            resource_data['content'] = content
            resource_data['mime_type'] = 'text/plain'
            
        elif format_type == 'json':
            if include_parsed:
                parser = NginxConfigParser()
                parsed_config = parser.parse_config_content(content, file_path)
                resource_data['parsed_config'] = parsed_config
            
            resource_data['raw_content'] = content
            resource_data['mime_type'] = 'application/json'
            
        elif format_type == 'yaml':
            if include_parsed:
                parser = NginxConfigParser()
                parsed_config = parser.parse_config_content(content, file_path)
                resource_data['parsed_config'] = parsed_config
            
            resource_data['raw_content'] = content
            resource_data['mime_type'] = 'application/yaml'
        
        # Always include parsed config if requested
        if include_parsed and format_type == 'raw':
            parser = NginxConfigParser()
            parsed_config = parser.parse_config_content(content, file_path)
            resource_data['parsed_config'] = parsed_config
        
        return resource_data
        
    except Exception as e:
        logger.error(f"Error getting service config resource for {service_name}: {e}")
        return {
            'error': str(e),
            'service_name': service_name,
            'device': device,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'service_error'
        }


async def _get_direct_file_resource(
    device: str, 
    file_path: str, 
    format_type: str = 'raw',
    include_parsed: bool = True
) -> dict[str, Any]:
    """Get direct file resource with real-time content"""
    
    # Ensure absolute path
    if not file_path.startswith('/'):
        file_path = f'/mnt/appdata/swag/nginx/proxy-confs/{file_path}'
    
    # Get file info and content
    file_info = await _get_real_time_file_info(device, file_path)
    
    if not file_info.get('exists', False):
        return {
            'error': 'File not found',
            'file_path': file_path,
            'device': device,
            'exists': False,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'file_not_found'
        }
    
    # Get content
    content = await _get_real_time_file_content(device, file_path)
    
    if content is None:
        return {
            'error': 'Failed to read file content',
            'file_path': file_path,
            'device': device,
            'file_info': file_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'read_error'
        }
    
    # Parse service info from filename
    path = Path(file_path)
    filename = path.stem
    parts = filename.split('.')
    
    service_name = parts[0] if parts else filename
    subdomain = parts[1] if len(parts) > 1 else parts[0]
    
    resource_data = {
        'uri': f"swag://{device}/{path.name}",
        'device': device,
        'file_path': file_path,
        'file_name': path.name,
        'service_name': service_name,
        'subdomain': subdomain,
        'file_info': file_info,
        'content_length': len(content),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'resource_type': 'swag_config_file',
        'format': format_type
    }
    
    # Format content based on requested format
    if format_type == 'raw':
        resource_data['content'] = content
        resource_data['mime_type'] = 'text/plain'
        
    elif format_type == 'json':
        if include_parsed:
            parser = NginxConfigParser()
            parsed_config = parser.parse_config_content(content, file_path)
            resource_data['parsed_config'] = parsed_config
        
        resource_data['raw_content'] = content
        resource_data['mime_type'] = 'application/json'
        
    elif format_type == 'yaml':
        if include_parsed:
            parser = NginxConfigParser()
            parsed_config = parser.parse_config_content(content, file_path)
            resource_data['parsed_config'] = parsed_config
        
        resource_data['raw_content'] = content
        resource_data['mime_type'] = 'application/yaml'
    
    # Always include parsed config if requested
    if include_parsed and format_type == 'raw':
        parser = NginxConfigParser()
        parsed_config = parser.parse_config_content(content, file_path)
        resource_data['parsed_config'] = parsed_config
    
    return resource_data


async def _get_database_config_resource(
    device: str,
    service_name: str,
    force_refresh: bool = False,
    include_parsed: bool = True
) -> dict[str, Any]:
    """Get configuration from database with real-time validation"""
    
    try:
        async with get_async_session() as session:
            # Find config in database
            query = select(ProxyConfig).where(
                and_(ProxyConfig.device_id == device, ProxyConfig.service_name == service_name)
            )
            result = await session.execute(query)
            config = result.scalar_one_or_none()
            
            if not config:
                return {
                    'error': 'Configuration not found in database',
                    'device': device,
                    'service_name': service_name,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'resource_type': 'config_not_found'
                }
            
            # Get real-time file info
            file_info = await _get_real_time_file_info(device, config.file_path)
            
            # Determine if refresh is needed
            needs_refresh = (
                force_refresh or
                not file_info.get('exists', False) or
                (file_info.get('last_modified') and config.last_modified and 
                 file_info['last_modified'] > config.last_modified)
            )
            
            resource_data = {
                'uri': f"swag://{device}/configs/{service_name}",
                'device': device,
                'service_name': service_name,
                'config_id': config.id,
                'subdomain': config.subdomain,
                'file_path': config.file_path,
                'status': config.status,
                'created_at': config.created_at.isoformat(),
                'updated_at': config.updated_at.isoformat(),
                'database_info': {
                    'file_hash': config.file_hash,
                    'file_size': config.file_size,
                    'last_modified': config.last_modified.isoformat() if config.last_modified else None,
                    'sync_status': config.sync_status,
                    'sync_last_checked': config.sync_last_checked.isoformat() if config.sync_last_checked else None
                },
                'real_time_info': file_info,
                'needs_refresh': needs_refresh,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'resource_type': 'swag_config_database'
            }
            
            # Include stored content and parsed config
            if config.raw_content:
                resource_data['stored_content'] = config.raw_content
            
            if config.parsed_config and include_parsed:
                resource_data['stored_parsed_config'] = config.parsed_config
            
            # Get real-time content if refresh needed or requested
            if needs_refresh and file_info.get('exists', False):
                real_time_content = await _get_real_time_file_content(device, config.file_path)
                if real_time_content:
                    resource_data['real_time_content'] = real_time_content
                    
                    # Parse real-time content if different
                    if real_time_content != config.raw_content and include_parsed:
                        parser = NginxConfigParser()
                        real_time_parsed = parser.parse_config_content(real_time_content, config.file_path)
                        resource_data['real_time_parsed_config'] = real_time_parsed
                        
                        # Calculate new hash
                        new_hash = parser.calculate_content_hash(real_time_content)
                        resource_data['real_time_hash'] = new_hash
                        resource_data['content_changed'] = new_hash != config.file_hash
            
            return resource_data
            
    except Exception as e:
        logger.error(f"Error getting database config resource: {e}")
        return {
            'error': str(e),
            'device': device,
            'service_name': service_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'database_error'
        }


async def _get_directory_listing_resource(device: str, config_dir: str) -> dict[str, Any]:
    """Get directory listing resource with file metadata"""
    
    try:
        # Execute directory listing with file details
        ls_command = f"""
        find {config_dir} -name '*.conf' -type f -exec stat -c '%n|%s|%Y|%A' {{}} \\; 2>/dev/null | sort
        """
        
        result = await execute_ssh_command_simple(device, ls_command, timeout=30)
        output = result.stdout
        
        files = []
        for line in output.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 4:
                    file_path = parts[0]
                    file_size = int(parts[1])
                    mtime = int(parts[2])
                    permissions = parts[3]
                    
                    path = Path(file_path)
                    filename = path.stem
                    
                    # Parse service info
                    name_parts = filename.split('.')
                    service_name = name_parts[0] if name_parts else filename
                    subdomain = name_parts[1] if len(name_parts) > 1 else name_parts[0]
                    
                    files.append({
                        'file_path': file_path,
                        'file_name': path.name,
                        'service_name': service_name,
                        'subdomain': subdomain,
                        'file_size': file_size,
                        'last_modified': datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                        'permissions': permissions,
                        'readable': 'r' in permissions,
                        'resource_uri': f"swag://{device}/{path.name}"
                    })
        
        return {
            'uri': f"swag://{device}/directory",
            'device': device,
            'config_directory': config_dir,
            'total_files': len(files),
            'files': files,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'swag_config_directory'
        }
        
    except Exception as e:
        logger.error(f"Error getting directory listing for {device}:{config_dir}: {e}")
        return {
            'error': str(e),
            'device': device,
            'config_directory': config_dir,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'directory_error'
        }


async def _get_proxy_summary_resource(device: str) -> dict[str, Any]:
    """Get proxy configuration summary resource"""
    
    try:
        # Get directory listing
        directory_resource = await _get_directory_listing_resource(
            device, '/mnt/appdata/swag/nginx/proxy-confs'
        )
        
        if 'files' not in directory_resource:
            return directory_resource  # Return error
        
        files = directory_resource['files']
        
        # Calculate summary statistics
        total_configs = len(files)
        services = {f['service_name'] for f in files}
        subdomains = {f['subdomain'] for f in files}
        
        # Get database info if available
        database_info = {}
        try:
            async with get_async_session() as session:
                query = select(ProxyConfig).where(ProxyConfig.device_id == device)
                result = await session.execute(query)
                db_configs = result.scalars().all()
                
                database_info = {
                    'total_in_database': len(db_configs),
                    'status_distribution': {},
                    'sync_status_distribution': {},
                    'last_sync': None
                }
                
                # Calculate distributions
                for config in db_configs:
                    status = config.status
                    sync_status = config.sync_status
                    
                    database_info['status_distribution'][status] = database_info['status_distribution'].get(status, 0) + 1
                    database_info['sync_status_distribution'][sync_status] = database_info['sync_status_distribution'].get(sync_status, 0) + 1
                    
                    if config.sync_last_checked and (not database_info['last_sync'] or config.sync_last_checked > database_info['last_sync']):
                        database_info['last_sync'] = config.sync_last_checked.isoformat()
        
        except Exception as db_error:
            database_info['error'] = str(db_error)
        
        # Calculate file size statistics
        file_sizes = [f['file_size'] for f in files]
        size_stats = {}
        if file_sizes:
            size_stats = {
                'total_size': sum(file_sizes),
                'average_size': sum(file_sizes) / len(file_sizes),
                'min_size': min(file_sizes),
                'max_size': max(file_sizes)
            }
        
        return {
            'uri': f"swag://{device}/summary",
            'device': device,
            'summary': {
                'total_configs': total_configs,
                'unique_services': len(services),
                'unique_subdomains': len(subdomains),
                'services': sorted(services),
                'subdomains': sorted(subdomains),
                'file_size_stats': size_stats
            },
            'database_info': database_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'swag_config_summary'
        }
        
    except Exception as e:
        logger.error(f"Error getting proxy summary for {device}: {e}")
        return {
            'error': str(e),
            'device': device,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'resource_type': 'summary_error'
        }


async def list_proxy_config_resources(device: str | None = None) -> list[dict[str, str]]:
    """
    List available proxy configuration resources
    
    Args:
        device: Optional device filter
        
    Returns:
        List of resource descriptors
    """
    resources = []
    
    try:
        # Add SWAG template resources (always available)
        resources.extend([
            {
                'uri': 'swag://subdomain-template',
                'name': 'SWAG Subdomain Template',
                'description': 'Template configuration for subdomain-based reverse proxy (_template.subdomain.conf.sample)',
                'mime_type': 'text/plain'
            },
            {
                'uri': 'swag://subfolder-template', 
                'name': 'SWAG Subfolder Template',
                'description': 'Template configuration for subfolder-based reverse proxy (_template.subfolder.conf.sample)',
                'mime_type': 'text/plain'
            },
            {
                'uri': 'swag://samples/',
                'name': 'SWAG Samples Directory',
                'description': 'Directory listing of all SWAG sample configuration files',
                'mime_type': 'application/json'
            },
            {
                'uri': 'swag://configs',
                'name': 'SWAG Configs Directory', 
                'description': 'Directory listing of all active SWAG configuration files',
                'mime_type': 'application/json'
            },
            {
                'uri': 'swag://summary',
                'name': 'SWAG Summary',
                'description': 'Summary statistics and overview of all SWAG configurations',
                'mime_type': 'application/json'
            }
        ])
        
        # Add individual sample file resources by discovering them
        try:
            swag_device = "squirts"
            samples_data = await _get_samples_directory_resource(swag_device)
            if 'samples' in samples_data:
                for sample in samples_data['samples']:
                    resources.append({
                        'uri': sample['resource_uri'],
                        'name': sample['display_name'],
                        'description': f"SWAG sample configuration for {sample['service_name']} ({sample['sample_type']})",
                        'mime_type': 'text/plain'
                    })
        except Exception as e:
            logger.error(f"Error discovering sample files: {e}")
        
        # Add individual active service configuration resources by discovering them
        try:
            swag_device = "squirts"
            # Discover all active .subdomain.conf and .subfolder.conf files
            ls_command = """
            find /mnt/appdata/swag/nginx/proxy-confs -name '*.subdomain.conf' -o -name '*.subfolder.conf' | grep -v '\.sample$' | sort
            """
            
            from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
            result = await execute_ssh_command_simple(swag_device, ls_command, timeout=30)
            output = result.stdout
            
            for line in output.strip().split('\n'):
                if line and '.conf' in line:
                    path = Path(line)
                    filename = path.stem  # removes .conf
                    
                    # Extract service name and type
                    if '.subdomain' in filename:
                        service_name = filename.replace('.subdomain', '')
                        config_type = 'subdomain'
                    elif '.subfolder' in filename:
                        service_name = filename.replace('.subfolder', '')  
                        config_type = 'subfolder'
                    else:
                        continue  # Skip if not matching expected pattern
                    
                    resources.append({
                        'uri': f'swag://{service_name}',
                        'name': f'{service_name.title()} Service',
                        'description': f'SWAG {config_type} configuration for {service_name} service',
                        'mime_type': 'text/plain'
                    })
                    
        except Exception as e:
            logger.error(f"Error discovering active service configs: {e}")
        
        # Static resources available for all devices
        if device:
            devices = [device]
        else:
            # Get all devices with proxy configs from database
            async with get_async_session() as session:
                query = select(ProxyConfig.device_id).distinct()
                result = await session.execute(query)
                devices = [row[0] for row in result.fetchall()]
        
        for device_id in devices:
            # Directory listing
            resources.append({
                'uri': f"swag://{device_id}/directory",
                'name': f"SWAG Config Directory - {device_id}",
                'description': f"Directory listing of SWAG proxy configurations on {device_id}",
                'mime_type': 'application/json'
            })
            
            # Summary
            resources.append({
                'uri': f"swag://{device_id}/summary", 
                'name': f"SWAG Config Summary - {device_id}",
                'description': f"Summary statistics for SWAG proxy configurations on {device_id}",
                'mime_type': 'application/json'
            })
            
            # Individual config files (get from database)
            try:
                async with get_async_session() as session:
                    query = select(ProxyConfig).where(ProxyConfig.device_id == device_id)
                    result = await session.execute(query)
                    configs = result.scalars().all()
                    
                    for config in configs:
                        # File resource
                        path = Path(config.file_path)
                        resources.append({
                            'uri': f"swag://{device_id}/{path.name}",
                            'name': f"{config.service_name}.{config.subdomain} Config",
                            'description': f"SWAG Nginx configuration for {config.service_name} service",
                            'mime_type': 'text/plain'
                        })
                        
                        # Database resource
                        resources.append({
                            'uri': f"swag://{device_id}/configs/{config.service_name}",
                            'name': f"{config.service_name} Database Record",
                            'description': f"Database record with real-time sync for {config.service_name}",
                            'mime_type': 'application/json'
                        })
            
            except Exception as e:
                logger.error(f"Error listing configs for device {device_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error listing proxy config resources: {e}")
    
    return resources
