"""
Nginx Configuration Parser

Utilities for parsing and analyzing nginx configuration files
from SWAG reverse proxy setups.
"""

import re
import logging
from typing import Optional, Any
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class NginxConfigParser:
    """
    Parser for nginx configuration files with support for
    SWAG-specific patterns and structures.
    """
    
    def __init__(self):
        # Common nginx directive patterns
        self.directive_patterns = {
            'server_name': re.compile(r'server_name\s+([^;]+);'),
            'listen': re.compile(r'listen\s+([^;]+);'),
            'proxy_pass': re.compile(r'proxy_pass\s+([^;]+);'),
            'ssl_certificate': re.compile(r'ssl_certificate\s+([^;]+);'),
            'ssl_certificate_key': re.compile(r'ssl_certificate_key\s+([^;]+);'),
            'root': re.compile(r'root\s+([^;]+);'),
            'index': re.compile(r'index\s+([^;]+);'),
            'error_page': re.compile(r'error_page\s+([^;]+);'),
            'include': re.compile(r'include\s+([^;]+);'),
        }
        
        # Block patterns
        self.block_patterns = {
            'server': re.compile(r'server\s*\{'),
            'location': re.compile(r'location\s+([^{]+)\s*\{'),
            'upstream': re.compile(r'upstream\s+([^{]+)\s*\{'),
            'if': re.compile(r'if\s*\([^)]+\)\s*\{'),
        }
    
    def parse_config_file(self, file_path: str) -> dict[str, Any]:
        """
        Parse a complete nginx configuration file
        
        Args:
            file_path: Path to the nginx config file
            
        Returns:
            Dict containing parsed configuration data
        """
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()
            
            return self.parse_config_content(content, file_path)
            
        except Exception as e:
            logger.error(f"Failed to parse config file {file_path}: {e}")
            return {
                'error': str(e),
                'file_path': file_path,
                'parsed': False
            }
    
    def parse_config_content(self, content: str, file_path: Optional[str] = None) -> dict[str, Any]:
        """
        Parse nginx configuration content
        
        Args:
            content: Raw nginx configuration content
            file_path: Optional file path for reference
            
        Returns:
            Dict containing parsed configuration data
        """
        result = {
            'file_path': file_path,
            'parsed': True,
            'file_hash': self.calculate_content_hash(content),
            'server_name': None,
            'server_names': [],
            'proxy_pass': None,
            'listen_ports': [],
            'ssl_enabled': False,
            'ssl_certificate': None,
            'ssl_certificate_key': None,
            'locations': [],
            'upstream_servers': [],
            'custom_directives': [],
            'includes': [],
            'raw_directives': {},
            'blocks': {},
            'comments': [],
            'line_count': len(content.split('\n')),
        }
        
        try:
            # Clean content and split into lines
            lines = content.split('\n')
            result['line_count'] = len(lines)
            
            # Extract comments
            result['comments'] = self._extract_comments(content)
            
            # Parse basic directives
            self._parse_directives(content, result)
            
            # Parse server blocks
            result['blocks']['servers'] = self._parse_server_blocks(content)
            
            # Parse location blocks
            result['locations'] = self._parse_location_blocks(content)
            
            # Parse upstream blocks
            result['blocks']['upstreams'] = self._parse_upstream_blocks(content)
            
            # Determine service info from file path
            if file_path:
                service_info = self._extract_service_info_from_path(file_path)
                result.update(service_info)
            
            # Post-process results
            self._post_process_results(result)
            
        except Exception as e:
            logger.error(f"Error parsing nginx config: {e}")
            result['error'] = str(e)
            result['parsed'] = False
        
        return result
    
    def _parse_directives(self, content: str, result: dict[str, Any]) -> None:
        """Parse standard nginx directives"""
        for directive, pattern in self.directive_patterns.items():
            matches = pattern.findall(content)
            if matches and directive == 'server_name':
                    # Handle multiple server names
                    server_names = []
                    for match in matches:
                        names = [name.strip() for name in match.split()]
                        server_names.extend(names)
                    result['server_names'] = server_names
                    result['server_name'] = server_names[0] if server_names else None
                    
                elif directive == 'listen':
                    # Parse listen directives
                    ports = []
                    for match in matches:
                        port_info = self._parse_listen_directive(match)
                        ports.extend(port_info['ports'])
                        if port_info.get('ssl'):
                            result['ssl_enabled'] = True
                    result['listen_ports'] = sorted(set(ports))
                    
                elif directive in ['ssl_certificate', 'ssl_certificate_key']:
                    result[directive] = matches[0].strip()
                    result['ssl_enabled'] = True
                    
                elif directive == 'proxy_pass':
                    result['proxy_pass'] = matches[0].strip()
                    
                else:
                    result['raw_directives'][directive] = matches
    
    def _parse_listen_directive(self, listen_value: str) -> dict[str, Any]:
        """Parse a listen directive value"""
        result = {'ports': [], 'ssl': False, 'http2': False, 'ipv6': False}
        
        # Remove extra whitespace
        listen_value = listen_value.strip()
        
        # Check for SSL
        if 'ssl' in listen_value:
            result['ssl'] = True
        
        # Check for HTTP/2
        if 'http2' in listen_value:
            result['http2'] = True
        
        # Check for IPv6
        if '[::' in listen_value or 'ipv6' in listen_value:
            result['ipv6'] = True
        
        # Extract port numbers
        port_pattern = re.compile(r'(?:^|\s)(\d+)(?:\s|$|;)')
        ports = port_pattern.findall(listen_value)
        result['ports'] = [int(port) for port in ports]
        
        # Default ports if none specified
        if not result['ports']:
            result['ports'] = [443] if result['ssl'] else [80]
        
        return result
    
    def _parse_server_blocks(self, content: str) -> list[dict[str, Any]]:
        """Parse server blocks from nginx config"""
        servers = []
        
        # Find server block boundaries
        server_blocks = self._extract_blocks(content, 'server')
        
        for block_content in server_blocks:
            server_info = {
                'directives': {},
                'locations': [],
                'raw_content': block_content
            }
            
            # Parse directives within server block
            for directive, pattern in self.directive_patterns.items():
                matches = pattern.findall(block_content)
                if matches:
                    server_info['directives'][directive] = matches
            
            # Parse locations within server block
            server_info['locations'] = self._parse_location_blocks(block_content)
            
            servers.append(server_info)
        
        return servers
    
    def _parse_location_blocks(self, content: str) -> list[dict[str, Any]]:
        """Parse location blocks from nginx config"""
        locations = []
        
        # Find location blocks
        location_pattern = re.compile(r'location\s+([^{]+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.MULTILINE | re.DOTALL)
        matches = location_pattern.findall(content)
        
        for path, block_content in matches:
            location_info = {
                'path': path.strip(),
                'directives': {},
                'raw_content': block_content.strip()
            }
            
            # Parse directives within location block
            for directive, pattern in self.directive_patterns.items():
                directive_matches = pattern.findall(block_content)
                if directive_matches:
                    location_info['directives'][directive] = directive_matches
            
            locations.append(location_info)
        
        return locations
    
    def _parse_upstream_blocks(self, content: str) -> list[dict[str, Any]]:
        """Parse upstream blocks from nginx config"""
        upstreams = []
        
        # Find upstream blocks
        upstream_pattern = re.compile(r'upstream\s+([^{]+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.MULTILINE | re.DOTALL)
        matches = upstream_pattern.findall(content)
        
        for name, block_content in matches:
            upstream_info = {
                'name': name.strip(),
                'servers': [],
                'directives': {},
                'raw_content': block_content.strip()
            }
            
            # Parse server directives
            server_pattern = re.compile(r'server\s+([^;]+);')
            servers = server_pattern.findall(block_content)
            upstream_info['servers'] = [server.strip() for server in servers]
            
            # Parse other directives
            for directive, pattern in self.directive_patterns.items():
                if directive == 'server':
                    continue  # Already handled above
                directive_matches = pattern.findall(block_content)
                if directive_matches:
                    upstream_info['directives'][directive] = directive_matches
            
            upstreams.append(upstream_info)
        
        return upstreams
    
    def _extract_blocks(self, content: str, block_type: str) -> List[str]:
        """Extract complete blocks of a specific type"""
        blocks = []
        pattern = self.block_patterns.get(block_type)
        
        if not pattern:
            return blocks
        
        lines = content.split('\n')
        in_block = False
        brace_count = 0
        current_block = []
        
        for line in lines:
            if not in_block and pattern.search(line):
                in_block = True
                current_block = [line]
                brace_count = line.count('{') - line.count('}')
            elif in_block:
                current_block.append(line)
                brace_count += line.count('{') - line.count('}')
                
                if brace_count <= 0:
                    blocks.append('\n'.join(current_block))
                    in_block = False
                    current_block = []
                    brace_count = 0
        
        return blocks
    
    def _extract_comments(self, content: str) -> list[dict[str, Any]]:
        """Extract comments from nginx config"""
        comments = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            comment_match = re.search(r'#(.*)$', line)
            if comment_match:
                comments.append({
                    'line_number': line_num,
                    'content': comment_match.group(1).strip(),
                    'full_line': line.strip()
                })
        
        return comments
    
    def _extract_service_info_from_path(self, file_path: str) -> dict[str, str]:
        """Extract service information from SWAG config file path"""
        path = Path(file_path)
        filename = path.stem  # Remove .conf extension
        
        # SWAG naming convention: service.subdomain.conf
        parts = filename.split('.')
        
        if len(parts) >= 2:
            service_name = parts[0]
            subdomain = parts[1] if len(parts) > 1 else parts[0]
        else:
            service_name = filename
            subdomain = filename
        
        return {
            'service_name': service_name,
            'subdomain': subdomain,
            'config_filename': path.name
        }
    
    def _post_process_results(self, result: dict[str, Any]) -> None:
        """Post-process parsing results for consistency"""
        # Ensure SSL detection is comprehensive
        if not result['ssl_enabled']:
            # Check for SSL in listen ports
            ssl_ports = [443, 8443]
            if any(port in ssl_ports for port in result['listen_ports']):
                result['ssl_enabled'] = True
            
            # Check for SSL in locations
            for location in result['locations']:
                if any('ssl' in str(directive) for directive in location['directives'].values()):
                    result['ssl_enabled'] = True
                    break
        
        # Extract upstream servers for easy access
        upstream_servers = []
        for upstream in result['blocks'].get('upstreams', []):
            upstream_servers.extend(upstream['servers'])
        result['upstream_servers'] = upstream_servers
        
        # Clean up server names (remove duplicates, sort)
        result['server_names'] = sorted(set(result['server_names']))
        if result['server_names']:
            result['server_name'] = result['server_names'][0]
        
        # Clean up ports
        result['listen_ports'] = sorted(set(result['listen_ports']))
    
    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """Calculate SHA256 hash of config content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def validate_config_syntax(self, content: str) -> dict[str, Any]:
        """
        Perform basic syntax validation on nginx config
        
        Args:
            content: Nginx configuration content
            
        Returns:
            Dict with validation results
        """
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'syntax_check': True
        }
        
        try:
            # Check for balanced braces
            brace_count = content.count('{') - content.count('}')
            if brace_count != 0:
                validation['is_valid'] = False
                validation['errors'].append(f"Unbalanced braces: {abs(brace_count)} {'opening' if brace_count > 0 else 'closing'} braces")
            
            # Check for missing semicolons
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#') and not line.endswith((';', '{', '}')):
                    # Skip block declarations
                    if not any(block in line for block in ['server', 'location', 'upstream', 'if']):
                        validation['warnings'].append(f"Line {line_num}: Possible missing semicolon")
            
            # Check for common directive issues
            directive_patterns = [
                (r'server_name\s+[^;]*[^;]$', "server_name directive missing semicolon"),
                (r'listen\s+[^;]*[^;]$', "listen directive missing semicolon"),
                (r'proxy_pass\s+[^;]*[^;]$', "proxy_pass directive missing semicolon"),
            ]
            
            for pattern, error_msg in directive_patterns:
                if re.search(pattern, content, re.MULTILINE):
                    validation['warnings'].append(error_msg)
        
        except Exception as e:
            validation['is_valid'] = False
            validation['syntax_check'] = False
            validation['errors'].append(f"Syntax validation error: {str(e)}")
        
        return validation
    
    def extract_service_dependencies(self, content: str) -> list[dict[str, str]]:
        """
        Extract service dependencies from proxy_pass and upstream directives
        
        Args:
            content: Nginx configuration content
            
        Returns:
            List of service dependencies
        """
        dependencies = []
        
        # Extract from proxy_pass directives
        proxy_pass_pattern = re.compile(r'proxy_pass\s+([^;]+);')
        matches = proxy_pass_pattern.findall(content)
        
        for match in matches:
            match = match.strip()
            
            # Parse upstream references
            if match.startswith('http://') or match.startswith('https://'):
                # Extract host and port
                url_pattern = re.compile(r'https?://([^:/]+)(?::(\d+))?')
                url_match = url_pattern.search(match)
                if url_match:
                    host = url_match.group(1)
                    port = url_match.group(2) or ('443' if match.startswith('https://') else '80')
                    
                    dependencies.append({
                        'type': 'direct',
                        'host': host,
                        'port': port,
                        'full_url': match
                    })
            elif match.startswith('$'):
                # Variable reference
                dependencies.append({
                    'type': 'variable',
                    'reference': match,
                    'full_url': match
                })
            else:
                # Upstream reference
                dependencies.append({
                    'type': 'upstream',
                    'upstream_name': match,
                    'full_url': match
                })
        
        return dependencies


def parse_swag_config_directory(directory_path: str) -> dict[str, Any]:
    """
    Parse all nginx config files in a SWAG proxy-confs directory
    
    Args:
        directory_path: Path to the proxy-confs directory
        
    Returns:
        Dict containing all parsed configurations
    """
    parser = NginxConfigParser()
    results = {
        'directory': directory_path,
        'configs': {},
        'summary': {
            'total_files': 0,
            'parsed_successfully': 0,
            'parse_errors': 0,
            'ssl_enabled_count': 0,
            'services': []
        },
        'errors': []
    }
    
    try:
        config_dir = Path(directory_path)
        if not config_dir.exists():
            results['errors'].append(f"Directory does not exist: {directory_path}")
            return results
        
        # Find all .conf files
        conf_files = list(config_dir.glob('*.conf'))
        results['summary']['total_files'] = len(conf_files)
        
        for conf_file in conf_files:
            try:
                config_data = parser.parse_config_file(str(conf_file))
                results['configs'][conf_file.name] = config_data
                
                if config_data.get('parsed', False):
                    results['summary']['parsed_successfully'] += 1
                    
                    if config_data.get('ssl_enabled', False):
                        results['summary']['ssl_enabled_count'] += 1
                    
                    service_name = config_data.get('service_name')
                    if service_name:
                        results['summary']['services'].append(service_name)
                else:
                    results['summary']['parse_errors'] += 1
                    
            except Exception as e:
                results['summary']['parse_errors'] += 1
                results['errors'].append(f"Error parsing {conf_file.name}: {str(e)}")
        
        # Deduplicate services
        results['summary']['services'] = sorted(set(results['summary']['services']))
        
    except Exception as e:
        results['errors'].append(f"Error accessing directory: {str(e)}")
    
    return results
