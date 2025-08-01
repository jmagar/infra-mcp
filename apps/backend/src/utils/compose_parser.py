"""
Docker Compose Parser Utilities

YAML parsing and structure extraction for Docker Compose files,
similar to the nginx_parser.py for SWAG configurations.
"""

import logging
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

import yaml

logger = logging.getLogger(__name__)


class ComposeParseError(Exception):
    """Exception raised when Docker Compose parsing fails"""
    pass


class DockerComposeParser:
    """Parser for Docker Compose YAML files"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def parse_compose_content(self, content: str, file_path: str = None) -> Dict[str, Any]:
        """
        Parse Docker Compose YAML content and extract structured information
        
        Args:
            content: Raw YAML content string
            file_path: Optional file path for context
            
        Returns:
            Dict containing:
            - raw_content: Original YAML content
            - parsed_yaml: Parsed YAML structure
            - services: Extracted services information
            - networks: Extracted networks configuration
            - volumes: Extracted volumes configuration
            - secrets: Extracted secrets configuration
            - configs: Extracted configs configuration
            - metadata: File metadata and parsing info
            
        Raises:
            ComposeParseError: If YAML parsing fails
        """
        try:
            # Parse YAML content
            parsed_yaml = yaml.safe_load(content)
            
            if not isinstance(parsed_yaml, dict):
                raise ComposeParseError("Docker Compose file must contain a YAML object at root level")
            
            # Extract version information
            version = parsed_yaml.get('version', 'unknown')
            
            # Extract main sections
            services = parsed_yaml.get('services', {})
            networks = parsed_yaml.get('networks', {})
            volumes = parsed_yaml.get('volumes', {})
            secrets = parsed_yaml.get('secrets', {})
            configs = parsed_yaml.get('configs', {})
            
            # Process services for better structure
            processed_services = self._process_services(services)
            
            # Process networks
            processed_networks = self._process_networks(networks)
            
            # Process volumes
            processed_volumes = self._process_volumes(volumes)
            
            # Generate content hash
            content_hash = self.calculate_content_hash(content)
            
            # Build result structure
            result = {
                'raw_content': content,
                'content_hash': content_hash,
                'parsed_yaml': parsed_yaml,
                'version': version,
                'services': processed_services,
                'networks': processed_networks,
                'volumes': processed_volumes,
                'secrets': secrets,
                'configs': configs,
                'metadata': {
                    'file_path': file_path,
                    'total_services': len(services),
                    'total_networks': len(networks),
                    'total_volumes': len(volumes),
                    'total_secrets': len(secrets),
                    'total_configs': len(configs),
                    'parsed_at': datetime.now(timezone.utc).isoformat(),
                    'compose_version': version
                }
            }
            
            # Add validation info
            validation_result = self._validate_compose_structure(parsed_yaml)
            result['validation'] = validation_result
            
            return result
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in {file_path}: {e}")
            raise ComposeParseError(f"Invalid YAML syntax: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Compose parsing error in {file_path}: {e}")
            raise ComposeParseError(f"Failed to parse compose file: {str(e)}") from e
    
    def _process_services(self, services: Dict[str, Any]) -> Dict[str, Any]:
        """Process services section for better structure"""
        processed = {}
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue
                
            processed_service = {
                'name': service_name,
                'image': service_config.get('image'),
                'build': service_config.get('build'),
                'ports': self._extract_ports(service_config.get('ports', [])),
                'volumes': self._extract_volumes(service_config.get('volumes', [])),
                'environment': self._extract_environment(service_config.get('environment', {})),
                'networks': service_config.get('networks', []),
                'depends_on': service_config.get('depends_on', []),
                'restart': service_config.get('restart'),
                'command': service_config.get('command'),
                'entrypoint': service_config.get('entrypoint'),
                'working_dir': service_config.get('working_dir'),
                'user': service_config.get('user'),
                'labels': service_config.get('labels', {}),
                'expose': service_config.get('expose', []),
                'healthcheck': service_config.get('healthcheck'),
                'raw_config': service_config
            }
            
            processed[service_name] = processed_service
            
        return processed
    
    def _process_networks(self, networks: Dict[str, Any]) -> Dict[str, Any]:
        """Process networks section"""
        processed = {}
        
        for network_name, network_config in networks.items():
            if network_config is None:
                network_config = {}
            
            processed_network = {
                'name': network_name,
                'driver': network_config.get('driver'),
                'driver_opts': network_config.get('driver_opts', {}),
                'ipam': network_config.get('ipam'),
                'external': network_config.get('external', False),
                'labels': network_config.get('labels', {}),
                'raw_config': network_config
            }
            
            processed[network_name] = processed_network
            
        return processed
    
    def _process_volumes(self, volumes: Dict[str, Any]) -> Dict[str, Any]:
        """Process volumes section"""
        processed = {}
        
        for volume_name, volume_config in volumes.items():
            if volume_config is None:
                volume_config = {}
            
            processed_volume = {
                'name': volume_name,
                'driver': volume_config.get('driver'),
                'driver_opts': volume_config.get('driver_opts', {}),
                'external': volume_config.get('external', False),
                'labels': volume_config.get('labels', {}),
                'raw_config': volume_config
            }
            
            processed[volume_name] = processed_volume
            
        return processed
    
    def _extract_ports(self, ports: List[Any]) -> List[Dict[str, Any]]:
        """Extract and normalize port configurations"""
        extracted = []
        
        for port in ports:
            if isinstance(port, str):
                # Parse string format like "80:8080" or "8080"
                if ':' in port:
                    host_port, container_port = port.split(':', 1)
                    extracted.append({
                        'host_port': host_port,
                        'container_port': container_port,
                        'protocol': 'tcp',
                        'raw': port
                    })
                else:
                    extracted.append({
                        'host_port': port,
                        'container_port': port,
                        'protocol': 'tcp',
                        'raw': port
                    })
            elif isinstance(port, dict):
                # Long format
                extracted.append({
                    'host_port': port.get('published'),
                    'container_port': port.get('target'),
                    'protocol': port.get('protocol', 'tcp'),
                    'mode': port.get('mode'),
                    'raw': port
                })
        
        return extracted
    
    def _extract_volumes(self, volumes: List[Any]) -> List[Dict[str, Any]]:
        """Extract and normalize volume configurations"""
        extracted = []
        
        for volume in volumes:
            if isinstance(volume, str):
                # Parse string format like "/host/path:/container/path:ro"
                parts = volume.split(':')
                volume_info = {
                    'raw': volume,
                    'type': 'bind' if parts[0].startswith('/') else 'volume'
                }
                
                if len(parts) >= 2:
                    volume_info['source'] = parts[0]
                    volume_info['target'] = parts[1]
                    if len(parts) >= 3:
                        volume_info['mode'] = parts[2]
                else:
                    volume_info['target'] = parts[0]
                
                extracted.append(volume_info)
                
            elif isinstance(volume, dict):
                # Long format
                extracted.append({
                    'type': volume.get('type', 'volume'),
                    'source': volume.get('source'),
                    'target': volume.get('target'),
                    'mode': volume.get('bind', {}).get('propagation') if volume.get('type') == 'bind' else None,
                    'read_only': volume.get('read_only', False),
                    'raw': volume
                })
        
        return extracted
    
    def _extract_environment(self, environment: Union[Dict, List]) -> Dict[str, str]:
        """Extract and normalize environment variables"""
        if isinstance(environment, dict):
            return environment
        elif isinstance(environment, list):
            env_dict = {}
            for env_var in environment:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    env_dict[key] = value
                else:
                    env_dict[env_var] = ''
            return env_dict
        else:
            return {}
    
    def _validate_compose_structure(self, parsed_yaml: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Docker Compose structure and provide warnings"""
        validation = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check for required sections
        if 'services' not in parsed_yaml or not parsed_yaml['services']:
            validation['errors'].append("No services defined in compose file")
            validation['valid'] = False
        
        # Check version
        version = parsed_yaml.get('version')
        if not version:
            validation['warnings'].append("No version specified - Docker Compose will use legacy format")
        elif version.startswith('1.'):
            validation['warnings'].append(f"Docker Compose version {version} is legacy - consider upgrading")
        
        # Validate services
        services = parsed_yaml.get('services', {})
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                validation['errors'].append(f"Service '{service_name}' configuration must be an object")
                validation['valid'] = False
                continue
            
            # Check for image or build
            if not service_config.get('image') and not service_config.get('build'):
                validation['warnings'].append(f"Service '{service_name}' has no image or build specified")
            
            # Check port conflicts
            ports = service_config.get('ports', [])
            host_ports = []
            for port in ports:
                if isinstance(port, str) and ':' in port:
                    host_port = port.split(':')[0]
                    if host_port in host_ports:
                        validation['warnings'].append(f"Service '{service_name}' has duplicate host port: {host_port}")
                    host_ports.append(host_port)
        
        return validation
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of compose file content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def extract_service_names(self, content: str) -> List[str]:
        """Extract just the service names from compose content"""
        try:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict) and 'services' in parsed:
                return list(parsed['services'].keys())
            return []
        except yaml.YAMLError:
            return []
    
    def get_service_image(self, content: str, service_name: str) -> Optional[str]:
        """Get the image for a specific service"""
        try:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict) and 'services' in parsed:
                services = parsed['services']
                if service_name in services:
                    service_config = services[service_name]
                    return service_config.get('image')
            return None
        except yaml.YAMLError:
            return None
    
    def find_compose_files_pattern(self) -> List[str]:
        """Return common Docker Compose file patterns for searching"""
        return [
            'docker-compose.yml',
            'docker-compose.yaml', 
            'compose.yml',
            'compose.yaml',
            'docker-compose.override.yml',
            'docker-compose.override.yaml'
        ]


# Convenience function for quick parsing
def parse_compose_file_content(content: str, file_path: str = None) -> Dict[str, Any]:
    """
    Convenience function to parse Docker Compose content
    
    Args:
        content: Raw YAML content
        file_path: Optional file path for context
        
    Returns:
        Parsed compose structure
        
    Raises:
        ComposeParseError: If parsing fails
    """
    parser = DockerComposeParser()
    return parser.parse_compose_content(content, file_path)