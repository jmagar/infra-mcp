"""
Docker Compose Deployment Service

Service for modifying docker-compose files for target device deployment,
including path updates, port management, network configuration, and SWAG proxy setup.
"""

import hashlib
import logging
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.device import Device
from apps.backend.src.models.proxy_config import ProxyConfig
from apps.backend.src.schemas.compose_deployment import (
    ComposeModificationRequest,
    ComposeModificationResult,
    ComposeDeploymentRequest, 
    ComposeDeploymentResult,
    PortScanRequest,
    PortScanResult,
    NetworkScanRequest,
    NetworkScanResult,
    ComposeServicePort,
    ComposeServiceVolume,
    ComposeServiceNetwork,
)
from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
from apps.backend.src.core.exceptions import (
    DeviceNotFoundError,
    ValidationError,
    SSHConnectionError,
    SSHCommandError,
)

logger = logging.getLogger(__name__)


class ComposeDeploymentService:
    """Service for Docker Compose deployment operations."""

    def __init__(self):
        self.logger = logger

    async def modify_compose_for_device(
        self, request: ComposeModificationRequest
    ) -> ComposeModificationResult:
        """
        Modify docker-compose content for deployment on target device.
        
        Args:
            request: Compose modification request
            
        Returns:
            ComposeModificationResult with all modifications applied
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get device configuration
            device_config = await self._get_device_config(request.target_device)
            
            # Parse original compose
            compose_data = self._parse_compose_content(request.compose_content)
            original_hash = self._calculate_content_hash(request.compose_content)
            
            # Initialize result
            result = ComposeModificationResult(
                device=request.target_device,
                service_name=request.service_name,
                timestamp=start_time,
                success=False,
                execution_time_ms=0,
                modified_compose="",
                original_compose_hash=original_hash,
                modified_compose_hash="",
                device_info={
                    "hostname": device_config.hostname,
                    "docker_appdata_path": device_config.docker_appdata_path,
                    "docker_compose_path": device_config.docker_compose_path,
                }
            )
            
            # Apply modifications
            if request.update_appdata_paths:
                await self._update_volume_paths(compose_data, device_config, request, result)
            
            if request.auto_assign_ports:
                await self._assign_ports(compose_data, device_config, request, result)
            
            if request.update_networks:
                await self._configure_networks(compose_data, device_config, request, result)
            
            if request.generate_proxy_configs:
                await self._generate_proxy_configs(compose_data, device_config, request, result)
            
            # Generate modified compose content
            modified_content = self._compose_to_yaml(compose_data)
            result.modified_compose = modified_content
            result.modified_compose_hash = self._calculate_content_hash(modified_content)
            
            # Set deployment path
            if request.deployment_path:
                result.deployment_path = request.deployment_path
            elif device_config.docker_compose_path:
                result.deployment_path = device_config.docker_compose_path
            else:
                result.deployment_path = "/opt/docker-compose"
            
            result.success = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error modifying compose for device {request.target_device}: {e}")
            result.success = False
            result.errors.append(str(e))
            return result
            
        finally:
            result.execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

    async def deploy_compose_to_device(
        self, request: ComposeDeploymentRequest
    ) -> ComposeDeploymentResult:
        """
        Deploy docker-compose content to target device.
        
        Args:
            request: Compose deployment request
            
        Returns:
            ComposeDeploymentResult with deployment status
        """
        start_time = datetime.now(timezone.utc)
        
        result = ComposeDeploymentResult(
            device=request.device,
            deployment_path=request.deployment_path,
            timestamp=start_time,
            success=False,
            execution_time_ms=0,
        )
        
        try:
            # Create directories if requested
            if request.create_directories:
                await self._create_deployment_directories(request.device, request.deployment_path, result)
            
            # Backup existing compose file if requested
            if request.backup_existing:
                await self._backup_existing_compose(request.device, request.deployment_path, result)
            
            # Write compose file to device
            await self._write_compose_file(request.device, request.deployment_path, request.compose_content, result)
            
            # Stop services if requested
            if request.services_to_stop:
                await self._stop_services(request.device, request.deployment_path, request.services_to_stop, result)
            
            # Pull images if requested  
            if request.pull_images:
                await self._pull_images(request.device, request.deployment_path, result)
            
            # Start services
            if request.start_services:
                services = request.services_to_start or []
                await self._start_services(request.device, request.deployment_path, services, request.recreate_containers, result)
            
            # Get final service status
            await self._get_service_status(request.device, request.deployment_path, result)
            
            result.success = True
            
        except Exception as e:
            self.logger.error(f"Error deploying compose to device {request.device}: {e}")
            result.errors.append(str(e))
            result.success = False
            
        finally:
            result.execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            
        return result

    async def scan_available_ports(self, request: PortScanRequest) -> PortScanResult:
        """
        Scan for available ports on target device.
        
        Args:
            request: Port scan request
            
        Returns:
            PortScanResult with port availability information
        """
        start_time = datetime.now(timezone.utc)
        
        result = PortScanResult(
            device=request.device,
            port_range_start=request.port_range_start,
            port_range_end=request.port_range_end,
            timestamp=start_time,
            execution_time_ms=0,
            total_scanned=request.port_range_end - request.port_range_start + 1,
        )
        
        try:
            # Scan system ports using netstat
            await self._scan_system_ports(request.device, request.port_range_start, request.port_range_end, result)
            
            # Scan Docker container ports
            await self._scan_docker_ports(request.device, result)
            
            # Determine available ports
            all_used_ports = set(result.system_port_usage.keys()) | set(result.docker_port_usage.keys())
            all_ports = set(range(request.port_range_start, request.port_range_end + 1))
            
            result.available_ports = sorted(list(all_ports - all_used_ports))
            result.used_ports = sorted(list(all_used_ports))
            
        except Exception as e:
            self.logger.error(f"Error scanning ports on device {request.device}: {e}")
            
        finally:
            result.execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            
        return result

    async def scan_docker_networks(self, request: NetworkScanRequest) -> NetworkScanResult:
        """
        Scan Docker networks on target device.
        
        Args:
            request: Network scan request
            
        Returns:
            NetworkScanResult with network information
        """
        start_time = datetime.now(timezone.utc)
        
        result = NetworkScanResult(
            device=request.device,
            timestamp=start_time,
            execution_time_ms=0,
        )
        
        try:
            # Get Docker networks
            cmd = "docker network ls --format '{{.ID}}|{{.Name}}|{{.Driver}}|{{.Scope}}'"
            network_result = await execute_ssh_command_simple(request.device, cmd, timeout=30)
            
            if network_result.success:
                # Parse network list
                for line in network_result.stdout.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 4:
                            network_id, name, driver, scope = parts[:4]
                            
                            # Skip system networks if not requested
                            if not request.include_system_networks and name in ['bridge', 'host', 'none']:
                                continue
                            
                            # Get detailed network info
                            network_detail = await self._get_network_details(request.device, network_id)
                            result.networks.append(network_detail)
            
            # Find containers by network
            await self._map_containers_to_networks(request.device, result)
            
            # Suggest recommended network
            result.recommended_network = self._suggest_recommended_network(result.networks)
            
        except Exception as e:
            self.logger.error(f"Error scanning networks on device {request.device}: {e}")
            
        finally:
            result.execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            
        return result

    # Private helper methods

    async def _get_device_config(self, hostname: str) -> Device:
        """Get device configuration from database."""
        async with get_async_session() as session:
            query = select(Device).where(Device.hostname == hostname)
            result = await session.execute(query)
            device = result.scalar_one_or_none()
            
            if not device:
                raise DeviceNotFoundError(hostname, "hostname")
                
            return device

    def _parse_compose_content(self, content: str) -> Dict[str, Any]:
        """Parse docker-compose YAML content."""
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid docker-compose YAML: {e}")

    def _compose_to_yaml(self, compose_data: Dict[str, Any]) -> str:
        """Convert compose data back to YAML string."""
        return yaml.dump(compose_data, default_flow_style=False, sort_keys=False)

    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def _update_volume_paths(
        self, 
        compose_data: Dict[str, Any], 
        device_config: Device, 
        request: ComposeModificationRequest,
        result: ComposeModificationResult
    ):
        """Update volume paths to use device appdata path."""
        services = compose_data.get('services', {})
        base_appdata_path = request.custom_appdata_path or device_config.docker_appdata_path or "/mnt/appdata"
        
        for service_name, service_config in services.items():
            if request.service_name and service_name != request.service_name:
                continue
                
            volumes = service_config.get('volumes', [])
            updated_volumes = []
            service_volume_updates = []
            
            for volume in volumes:
                if isinstance(volume, str):
                    # Parse volume string (host:container:mode)
                    parts = volume.split(':')
                    if len(parts) >= 2:
                        host_path, container_path = parts[0], parts[1]
                        mode = parts[2] if len(parts) > 2 else "rw"
                        
                        # Update host path if it looks like an appdata path
                        if self._is_appdata_path(host_path):
                            old_host_path = host_path
                            new_host_path = self._update_appdata_path(host_path, base_appdata_path)
                            updated_volume = f"{new_host_path}:{container_path}:{mode}"
                            updated_volumes.append(updated_volume)
                            
                            service_volume_updates.append(ComposeServiceVolume(
                                host_path=new_host_path,
                                container_path=container_path,
                                mode=mode,
                                type="bind"
                            ))
                            
                            result.changes_applied.append(
                                f"Updated {service_name} volume: {old_host_path} -> {new_host_path}"
                            )
                        else:
                            updated_volumes.append(volume)
                    else:
                        updated_volumes.append(volume)
                else:
                    updated_volumes.append(volume)
            
            if updated_volumes != volumes:
                service_config['volumes'] = updated_volumes
                result.volume_updates[service_name] = service_volume_updates

    async def _assign_ports(
        self,
        compose_data: Dict[str, Any],
        device_config: Device,
        request: ComposeModificationRequest,
        result: ComposeModificationResult
    ):
        """Assign available ports to services."""
        # Scan for available ports
        port_scan_request = PortScanRequest(
            device=request.target_device,
            port_range_start=request.port_range_start,
            port_range_end=request.port_range_end
        )
        port_scan_result = await self.scan_available_ports(port_scan_request)
        
        available_ports = iter(port_scan_result.available_ports)
        services = compose_data.get('services', {})
        
        for service_name, service_config in services.items():
            if request.service_name and service_name != request.service_name:
                continue
                
            ports = service_config.get('ports', [])
            updated_ports = []
            service_port_assignments = []
            
            for port in ports:
                if isinstance(port, str):
                    # Parse port string (host:container or just container)
                    if ':' in port:
                        host_part, container_part = port.split(':', 1)
                        try:
                            container_port = int(container_part.split('/')[0])
                            protocol = container_part.split('/')[1] if '/' in container_part else 'tcp'
                            
                            # Check for custom mapping first
                            if request.custom_port_mappings and service_name in request.custom_port_mappings:
                                new_host_port = request.custom_port_mappings[service_name]
                            else:
                                # Assign next available port
                                try:
                                    new_host_port = next(available_ports)
                                except StopIteration:
                                    result.warnings.append(f"No available ports for {service_name}")
                                    new_host_port = int(host_part) if host_part.isdigit() else 8000
                            
                            updated_port = f"{new_host_port}:{container_port}"
                            if protocol != 'tcp':
                                updated_port += f"/{protocol}"
                            updated_ports.append(updated_port)
                            
                            service_port_assignments.append(ComposeServicePort(
                                host_port=new_host_port,
                                container_port=container_port,
                                protocol=protocol
                            ))
                            
                            result.changes_applied.append(
                                f"Assigned port {new_host_port} to {service_name} (container port {container_port})"
                            )
                            
                        except (ValueError, IndexError):
                            updated_ports.append(port)
                    else:
                        updated_ports.append(port)
                else:
                    updated_ports.append(port)
            
            if updated_ports != ports:
                service_config['ports'] = updated_ports
                result.port_assignments[service_name] = service_port_assignments

    async def _configure_networks(
        self,
        compose_data: Dict[str, Any],
        device_config: Device,
        request: ComposeModificationRequest,
        result: ComposeModificationResult
    ):
        """Configure Docker networks for services."""
        # Scan existing networks
        network_scan_request = NetworkScanRequest(device=request.target_device)
        network_scan_result = await self.scan_docker_networks(network_scan_request)
        
        # Use specified network or recommended one
        target_network = request.default_network or network_scan_result.recommended_network or "bridge"
        
        services = compose_data.get('services', {})
        
        for service_name, service_config in services.items():
            if request.service_name and service_name != request.service_name:
                continue
            
            # Update networks configuration
            networks_config = service_config.get('networks', [])
            if isinstance(networks_config, list):
                # Convert to dict format for more control
                networks_config = {target_network: {}}
            elif isinstance(networks_config, dict):
                # Update existing networks
                if target_network not in networks_config:
                    networks_config[target_network] = {}
            
            service_config['networks'] = networks_config
            
            result.network_configs[service_name] = ComposeServiceNetwork(
                name=target_network
            )
            
            result.changes_applied.append(f"Configured {service_name} to use network: {target_network}")
        
        # Ensure networks section exists in compose
        if 'networks' not in compose_data:
            compose_data['networks'] = {}
        
        if target_network not in compose_data['networks']:
            compose_data['networks'][target_network] = {'external': True}

    async def _generate_proxy_configs(
        self,
        compose_data: Dict[str, Any],
        device_config: Device,
        request: ComposeModificationRequest,
        result: ComposeModificationResult
    ):
        """Generate SWAG proxy configurations for services."""
        services = compose_data.get('services', {})
        base_domain = request.base_domain or "example.com"
        
        for service_name, service_config in services.items():
            if request.service_name and service_name != request.service_name:
                continue
                
            ports = service_config.get('ports', [])
            if not ports:
                continue
                
            # Extract first HTTP port
            http_port = None
            for port in ports:
                if isinstance(port, str) and ':' in port:
                    host_port = port.split(':')[0]
                    if host_port.isdigit():
                        http_port = int(host_port)
                        break
            
            if http_port:
                # Generate basic SWAG proxy config
                proxy_config = self._generate_swag_config(
                    service_name=service_name,
                    upstream_port=http_port,
                    domain=f"{service_name}.{base_domain}",
                    device_hostname=device_config.hostname
                )
                
                result.proxy_configs.append({
                    'service_name': service_name,
                    'subdomain': service_name,
                    'upstream_port': http_port,
                    'domain': f"{service_name}.{base_domain}",
                    'config_content': proxy_config
                })
                
                result.changes_applied.append(f"Generated proxy config for {service_name}")

    def _is_appdata_path(self, path: str) -> bool:
        """Check if path looks like an appdata path that should be updated."""
        appdata_indicators = ['/appdata/', '/mnt/appdata/', './appdata/', '../appdata/']
        return any(indicator in path for indicator in appdata_indicators)

    def _update_appdata_path(self, original_path: str, base_appdata_path: str) -> str:
        """Update appdata path to use device-specific base path."""
        # Extract the relative appdata portion
        for indicator in ['/appdata/', '/mnt/appdata/', './appdata/', '../appdata/']:
            if indicator in original_path:
                relative_part = original_path.split(indicator)[1]
                return f"{base_appdata_path.rstrip('/')}/{relative_part}"
        
        # Fallback: assume entire path should be under appdata
        return f"{base_appdata_path.rstrip('/')}/{Path(original_path).name}"

    def _generate_swag_config(self, service_name: str, upstream_port: int, domain: str, device_hostname: str) -> str:
        """Generate basic SWAG proxy configuration."""
        return f"""# {service_name} proxy configuration
# Generated automatically for deployment on {device_hostname}

server {{
    listen 443 ssl;
    listen [::]:443 ssl;
    
    server_name {domain};
    
    include /config/nginx/ssl.conf;
    
    client_max_body_size 0;
    
    location / {{
        include /config/nginx/proxy.conf;
        include /config/nginx/resolver.conf;
        set $upstream_app {device_hostname};
        set $upstream_port {upstream_port};
        set $upstream_proto http;
        proxy_pass $upstream_proto://$upstream_app:$upstream_port;
    }}
}}
"""

    async def _scan_system_ports(self, device: str, start_port: int, end_port: int, result: PortScanResult):
        """Scan system ports using netstat."""
        try:
            cmd = f"netstat -tulpn | grep ':{start_port}\\|:{end_port}' | grep LISTEN"
            netstat_result = await execute_ssh_command_simple(device, cmd, timeout=30)
            
            if netstat_result.success:
                for line in netstat_result.stdout.strip().split('\n'):
                    if ':' in line and 'LISTEN' in line:
                        # Extract port from line like "tcp 0.0.0.0:8080 0.0.0.0:* LISTEN 1234/process"
                        match = re.search(r':(\d+)\s+.*LISTEN\s+(\d+)/(\S+)', line)
                        if match:
                            port = int(match.group(1))
                            if start_port <= port <= end_port:
                                pid = match.group(2)
                                process = match.group(3)
                                result.system_port_usage[port] = f"{process} (PID: {pid})"
                                
        except Exception as e:
            self.logger.warning(f"Error scanning system ports: {e}")

    async def _scan_docker_ports(self, device: str, result: PortScanResult):
        """Scan Docker container port mappings."""
        try:
            cmd = "docker ps --format '{{.Names}}|{{.Ports}}'"
            docker_result = await execute_ssh_command_simple(device, cmd, timeout=30)
            
            if docker_result.success:
                for line in docker_result.stdout.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|', 1)
                        if len(parts) == 2:
                            container_name, ports_str = parts
                            
                            # Parse port mappings like "0.0.0.0:8080->80/tcp"
                            port_matches = re.findall(r'(?:0.0.0.0:)?(\d+)->', ports_str)
                            for port_str in port_matches:
                                port = int(port_str)
                                if result.port_range_start <= port <= result.port_range_end:
                                    result.docker_port_usage[port] = container_name
                                    
        except Exception as e:
            self.logger.warning(f"Error scanning Docker ports: {e}")

    async def _get_network_details(self, device: str, network_id: str) -> Dict[str, Any]:
        """Get detailed information about a Docker network."""
        try:
            cmd = f"docker network inspect {network_id}"
            inspect_result = await execute_ssh_command_simple(device, cmd, timeout=15)
            
            if inspect_result.success:
                import json
                network_data = json.loads(inspect_result.stdout)[0]
                return {
                    'id': network_data.get('Id', '')[:12],
                    'name': network_data.get('Name', ''),
                    'driver': network_data.get('Driver', ''),
                    'scope': network_data.get('Scope', ''),
                    'ipam': network_data.get('IPAM', {}),
                    'containers': network_data.get('Containers', {}),
                    'options': network_data.get('Options', {}),
                    'labels': network_data.get('Labels', {})
                }
        except Exception as e:
            self.logger.warning(f"Error getting network details for {network_id}: {e}")
            
        return {'id': network_id, 'name': 'unknown', 'driver': 'unknown'}

    async def _map_containers_to_networks(self, device: str, result: NetworkScanResult):
        """Map containers to their networks."""
        for network in result.networks:
            network_name = network.get('name', '')
            containers = network.get('containers', {})
            container_names = [info.get('Name', '') for info in containers.values()]
            result.containers_by_network[network_name] = container_names

    def _suggest_recommended_network(self, networks: List[Dict[str, Any]]) -> Optional[str]:
        """Suggest the best network to use for new deployments."""
        # Prefer custom networks over default bridge
        custom_networks = [n for n in networks if n.get('name') not in ['bridge', 'host', 'none']]
        
        if custom_networks:
            # Find network with fewest containers (less congested)
            return min(custom_networks, key=lambda n: len(n.get('containers', {}))).get('name')
        
        return 'bridge'  # Fallback to default

    async def _create_deployment_directories(self, device: str, deployment_path: str, result: ComposeDeploymentResult):
        """Create necessary directories on the target device."""
        try:
            path_obj = Path(deployment_path)
            parent_dir = str(path_obj.parent)
            
            cmd = f"mkdir -p '{parent_dir}'"
            mkdir_result = await execute_ssh_command_simple(device, cmd, timeout=30)
            
            if mkdir_result.success:
                result.directories_created.append(parent_dir)
            else:
                result.warnings.append(f"Failed to create directory {parent_dir}: {mkdir_result.stderr}")
                
        except Exception as e:
            result.warnings.append(f"Error creating directories: {e}")

    async def _backup_existing_compose(self, device: str, deployment_path: str, result: ComposeDeploymentResult):
        """Backup existing compose file if it exists."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{deployment_path}.backup_{timestamp}"
            
            cmd = f"[ -f '{deployment_path}' ] && cp '{deployment_path}' '{backup_path}' || true"
            backup_result = await execute_ssh_command_simple(device, cmd, timeout=30)
            
            if backup_result.success:
                # Check if backup was actually created
                check_cmd = f"[ -f '{backup_path}' ] && echo 'EXISTS' || echo 'NOT_EXISTS'"
                check_result = await execute_ssh_command_simple(device, check_cmd, timeout=10)
                
                if check_result.success and 'EXISTS' in check_result.stdout:
                    result.backup_file_path = backup_path
                    
        except Exception as e:
            result.warnings.append(f"Error backing up existing compose file: {e}")

    async def _write_compose_file(self, device: str, deployment_path: str, content: str, result: ComposeDeploymentResult):
        """Write compose content to file on device."""
        try:
            # Use cat with here-doc to write content safely
            cmd = f"cat > '{deployment_path}' << 'COMPOSE_EOF'\n{content}\nCOMPOSE_EOF"
            write_result = await execute_ssh_command_simple(device, cmd, timeout=60)
            
            if write_result.success:
                result.compose_file_created = True
            else:
                raise Exception(f"Failed to write compose file: {write_result.stderr}")
                
        except Exception as e:
            result.errors.append(f"Error writing compose file: {e}")
            raise

    async def _stop_services(self, device: str, deployment_path: str, services: List[str], result: ComposeDeploymentResult):
        """Stop specified services."""
        try:
            services_str = ' '.join(services)
            cmd = f"cd '{Path(deployment_path).parent}' && docker-compose -f '{deployment_path}' stop {services_str}"
            stop_result = await execute_ssh_command_simple(device, cmd, timeout=120)
            
            result.docker_compose_output += f"STOP OUTPUT:\n{stop_result.stdout}\n{stop_result.stderr}\n"
            
            if stop_result.success:
                result.containers_stopped.extend(services)
            else:
                result.warnings.append(f"Some services may not have stopped cleanly: {stop_result.stderr}")
                
        except Exception as e:
            result.warnings.append(f"Error stopping services: {e}")

    async def _pull_images(self, device: str, deployment_path: str, result: ComposeDeploymentResult):
        """Pull latest images for all services."""
        try:
            cmd = f"cd '{Path(deployment_path).parent}' && docker-compose -f '{deployment_path}' pull"
            pull_result = await execute_ssh_command_simple(device, cmd, timeout=300)
            
            result.docker_compose_output += f"PULL OUTPUT:\n{pull_result.stdout}\n{pull_result.stderr}\n"
            
            if pull_result.success:
                # Extract pulled images from output
                pulled_images = re.findall(r'Pulling (\S+)', pull_result.stdout)
                result.images_pulled.extend(pulled_images)
            else:
                result.warnings.append(f"Some images may not have been pulled: {pull_result.stderr}")
                
        except Exception as e:
            result.warnings.append(f"Error pulling images: {e}")

    async def _start_services(self, device: str, deployment_path: str, services: List[str], recreate: bool, result: ComposeDeploymentResult):
        """Start services using docker-compose."""
        try:
            services_str = ' '.join(services) if services else ''
            recreate_flag = '--force-recreate' if recreate else ''
            
            cmd = f"cd '{Path(deployment_path).parent}' && docker-compose -f '{deployment_path}' up -d {recreate_flag} {services_str}"
            start_result = await execute_ssh_command_simple(device, cmd, timeout=300)
            
            result.docker_compose_output += f"START OUTPUT:\n{start_result.stdout}\n{start_result.stderr}\n"
            
            if start_result.success:
                # Extract started containers from output
                started_containers = re.findall(r'Starting (\S+)', start_result.stdout)
                created_containers = re.findall(r'Creating (\S+)', start_result.stdout)
                
                result.containers_started.extend(started_containers)
                result.containers_created.extend(created_containers)
            else:
                result.errors.append(f"Failed to start services: {start_result.stderr}")
                
        except Exception as e:
            result.errors.append(f"Error starting services: {e}")

    async def _get_service_status(self, device: str, deployment_path: str, result: ComposeDeploymentResult):
        """Get final status of all services."""
        try:
            cmd = f"cd '{Path(deployment_path).parent}' && docker-compose -f '{deployment_path}' ps"
            status_result = await execute_ssh_command_simple(device, cmd, timeout=60)
            
            if status_result.success:
                # Parse service status from docker-compose ps output
                lines = status_result.stdout.strip().split('\n')[2:]  # Skip header lines
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            service_name = parts[0].split('_')[1] if '_' in parts[0] else parts[0]
                            status = parts[-1]  # Last column is usually status
                            result.service_status[service_name] = status
                            
        except Exception as e:
            result.warnings.append(f"Error getting service status: {e}")