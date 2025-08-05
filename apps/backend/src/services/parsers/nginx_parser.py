"""
Nginx Configuration Parser

Specialized parser for Nginx configuration files with comprehensive
security analysis, performance optimization, and best practices validation.
"""

import logging
import re
from typing import Any

from .base_parser import BaseConfigurationParser, ParsedConfiguration, ConfigurationError

logger = logging.getLogger(__name__)


class NginxConfigParser(BaseConfigurationParser):
    """
    Parser for Nginx configuration files.

    Provides comprehensive analysis of Nginx configurations including:
    - Server block definitions and virtual hosts
    - SSL/TLS configuration analysis
    - Security header validation
    - Performance optimization recommendations
    - Load balancing and proxy configurations
    """

    def __init__(self):
        super().__init__(parser_version="1.0")

    def get_supported_file_patterns(self) -> list[str]:
        """Get supported Nginx configuration file patterns."""
        return [
            "nginx.conf",
            "*.conf",
            "sites-available/*",
            "sites-enabled/*",
            "conf.d/*.conf",
        ]

    def get_config_type(self) -> str:
        """Get configuration type."""
        return "nginx_config"

    async def parse(self, content: str, file_path: str) -> ParsedConfiguration:
        """Parse Nginx configuration content."""
        try:
            # Parse nginx configuration
            parsed_config = self._parse_nginx_config(content)

            # Create base configuration
            config = self._create_base_parsed_config(content, file_path, parsed_config)

            # Validate Nginx configuration structure
            validation_errors = self._validate_nginx_structure(parsed_config)
            config.validation_errors.extend(validation_errors)
            config.is_valid = len(validation_errors) == 0

            # Extract server information
            config.services = self._extract_servers(parsed_config)

            # Extract exposed ports
            config.exposed_ports = self._extract_nginx_ports(parsed_config)

            # Extract upstream servers and dependencies
            config.dependencies = self._extract_upstreams(parsed_config)

            # Calculate change impact score
            config.change_impact_score = self._calculate_nginx_impact_score(parsed_config)

            # Identify affected services
            config.affected_services = [server.get("name", "default") for server in config.services]

            # Nginx changes usually require reload, not full restart
            config.restart_required = False

            # Security analysis
            config.security_issues = self._analyze_nginx_security_issues(parsed_config)

            # Best practices analysis
            config.best_practice_violations = self._analyze_nginx_best_practices(parsed_config)

            # Performance recommendations
            config.performance_recommendations = self._generate_nginx_performance_recommendations(
                parsed_config
            )

            # Nginx-specific metadata
            config.parser_metadata = {
                "server_blocks": len(config.services),
                "upstream_blocks": len(config.dependencies),
                "ssl_enabled_servers": len(
                    [s for s in config.services if s.get("ssl_enabled", False)]
                ),
                "proxy_enabled_servers": len(
                    [s for s in config.services if s.get("has_proxy", False)]
                ),
                "has_rate_limiting": self._has_rate_limiting(parsed_config),
                "has_gzip": self._has_gzip_enabled(parsed_config),
                "has_security_headers": self._has_security_headers(parsed_config),
                "worker_processes": self._get_worker_processes(parsed_config),
            }

            return config

        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to parse Nginx configuration: {str(e)}",
                file_path=file_path,
            ) from e

    def _parse_nginx_config(self, content: str) -> dict[str, Any]:
        """Parse Nginx configuration content into structured data."""
        config = {
            "main_context": {},
            "http_context": {},
            "server_blocks": [],
            "upstream_blocks": [],
            "raw_directives": [],
        }

        # Remove comments
        content = re.sub(r"#.*$", "", content, flags=re.MULTILINE)

        # Split into lines and normalize
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        current_context = "main"
        server_block = None
        upstream_block = None
        brace_level = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Track brace levels
            brace_level += line.count("{") - line.count("}")

            # Parse server blocks
            if line.startswith("server") and "{" in line:
                server_block = {
                    "directives": [],
                    "locations": [],
                    "name": "default",
                    "ports": [],
                    "server_names": [],
                    "ssl_enabled": False,
                    "has_proxy": False,
                }
                current_context = "server"
                continue

            # Parse upstream blocks
            if line.startswith("upstream") and "{" in line:
                upstream_name = re.search(r"upstream\s+(\w+)", line)
                upstream_block = {
                    "name": upstream_name.group(1) if upstream_name else "unnamed",
                    "servers": [],
                    "directives": [],
                }
                current_context = "upstream"
                continue

            # End of block
            if line == "}" and brace_level >= 0:
                if current_context == "server" and server_block:
                    config["server_blocks"].append(server_block)
                    server_block = None
                elif current_context == "upstream" and upstream_block:
                    config["upstream_blocks"].append(upstream_block)
                    upstream_block = None
                current_context = "main"
                continue

            # Parse directives based on context
            if current_context == "server" and server_block is not None:
                self._parse_server_directive(line, server_block)
            elif current_context == "upstream" and upstream_block is not None:
                self._parse_upstream_directive(line, upstream_block)
            elif current_context == "main":
                self._parse_main_directive(line, config)

        return config

    def _parse_server_directive(self, line: str, server_block: dict[str, Any]) -> None:
        """Parse a directive within a server block."""
        line = line.rstrip(";")

        # Listen directive
        if line.startswith("listen"):
            listen_match = re.search(r"listen\s+([^;]+)", line)
            if listen_match:
                listen_value = listen_match.group(1).strip()
                # Extract port number
                port_match = re.search(r"(\d+)", listen_value)
                if port_match:
                    port = int(port_match.group(1))
                    server_block["ports"].append(port)

                # Check for SSL
                if "ssl" in listen_value:
                    server_block["ssl_enabled"] = True

        # Server name directive
        elif line.startswith("server_name"):
            name_match = re.search(r"server_name\s+([^;]+)", line)
            if name_match:
                names = name_match.group(1).strip().split()
                server_block["server_names"].extend(names)
                if names and names[0] != "_":
                    server_block["name"] = names[0]

        # Proxy directives
        elif "proxy_pass" in line:
            server_block["has_proxy"] = True

        # Location blocks
        elif line.startswith("location"):
            location_match = re.search(r"location\s+([^{]+)", line)
            if location_match:
                location_path = location_match.group(1).strip()
                server_block["locations"].append(location_path)

        # SSL directives
        elif line.startswith("ssl_"):
            server_block["ssl_enabled"] = True

        # Store all directives
        server_block["directives"].append(line)

    def _parse_upstream_directive(self, line: str, upstream_block: dict[str, Any]) -> None:
        """Parse a directive within an upstream block."""
        line = line.rstrip(";")

        if line.startswith("server"):
            server_match = re.search(r"server\s+([^;]+)", line)
            if server_match:
                upstream_block["servers"].append(server_match.group(1).strip())

        upstream_block["directives"].append(line)

    def _parse_main_directive(self, line: str, config: dict[str, Any]) -> None:
        """Parse a directive in the main context."""
        line = line.rstrip(";")

        if line.startswith("worker_processes"):
            config["main_context"]["worker_processes"] = line
        elif line.startswith("http"):
            config["http_context"] = {}

        config["raw_directives"].append(line)

    def _validate_nginx_structure(self, parsed_config: dict[str, Any]) -> list[str]:
        """Validate Nginx configuration structure."""
        errors = []

        # Check for at least one server block
        if not parsed_config.get("server_blocks"):
            errors.append("No server blocks found in configuration")

        # Validate server blocks
        for i, server_block in enumerate(parsed_config.get("server_blocks", [])):
            if not server_block.get("ports"):
                errors.append(f"Server block {i + 1} has no listen directive")

            # Check for conflicting SSL settings
            has_ssl_listen = any("ssl" in str(port) for port in server_block.get("ports", []))
            has_ssl_directives = server_block.get("ssl_enabled", False)

            if has_ssl_listen and not has_ssl_directives:
                errors.append(
                    f"Server block {i + 1} listens on SSL port but has no SSL configuration"
                )

        return errors

    def _extract_servers(self, parsed_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract server information from parsed config."""
        servers = []

        for server_block in parsed_config.get("server_blocks", []):
            server_info = {
                "name": server_block.get("name", "default"),
                "server_names": server_block.get("server_names", []),
                "ports": server_block.get("ports", []),
                "ssl_enabled": server_block.get("ssl_enabled", False),
                "has_proxy": server_block.get("has_proxy", False),
                "locations": server_block.get("locations", []),
                "directives_count": len(server_block.get("directives", [])),
            }
            servers.append(server_info)

        return servers

    def _extract_nginx_ports(self, parsed_config: dict[str, Any]) -> list[int]:
        """Extract all ports from Nginx configuration."""
        ports = []

        for server_block in parsed_config.get("server_blocks", []):
            ports.extend(server_block.get("ports", []))

        return sorted(list(set(ports)))

    def _extract_upstreams(self, parsed_config: dict[str, Any]) -> list[str]:
        """Extract upstream server dependencies."""
        upstreams = []

        for upstream_block in parsed_config.get("upstream_blocks", []):
            upstreams.append(upstream_block.get("name", "unnamed"))
            upstreams.extend(upstream_block.get("servers", []))

        return upstreams

    def _calculate_nginx_impact_score(self, parsed_config: dict[str, Any]) -> float:
        """Calculate impact score for Nginx configuration changes."""
        score = 0.0

        # Server count impact
        server_count = len(parsed_config.get("server_blocks", []))
        score += min(server_count * 0.5, 3.0)

        # SSL configuration has higher impact
        ssl_servers = sum(
            1
            for server in parsed_config.get("server_blocks", [])
            if server.get("ssl_enabled", False)
        )
        score += ssl_servers * 0.8

        # Proxy configuration impact
        proxy_servers = sum(
            1 for server in parsed_config.get("server_blocks", []) if server.get("has_proxy", False)
        )
        score += proxy_servers * 0.6

        # Upstream configuration impact
        upstream_count = len(parsed_config.get("upstream_blocks", []))
        score += upstream_count * 0.7

        return min(score, 10.0)

    def _analyze_nginx_security_issues(self, parsed_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Analyze Nginx configuration for security issues."""
        issues = []

        # Check for missing security headers
        has_security_headers = False
        for directive in parsed_config.get("raw_directives", []):
            if any(
                header in directive.lower()
                for header in [
                    "x-frame-options",
                    "x-content-type-options",
                    "x-xss-protection",
                    "strict-transport-security",
                    "content-security-policy",
                ]
            ):
                has_security_headers = True
                break

        if not has_security_headers:
            issues.append(
                {
                    "severity": "medium",
                    "type": "missing_security_headers",
                    "message": "Missing important security headers",
                    "recommendation": "Add security headers like X-Frame-Options, X-Content-Type-Options, etc.",
                }
            )

        # Check for SSL/TLS issues
        for server_block in parsed_config.get("server_blocks", []):
            server_name = server_block.get("name", "default")

            # Check for weak SSL protocols
            ssl_protocols_found = False
            for directive in server_block.get("directives", []):
                if "ssl_protocols" in directive.lower():
                    ssl_protocols_found = True
                    if any(
                        weak in directive.lower()
                        for weak in ["sslv2", "sslv3", "tlsv1.0", "tlsv1.1"]
                    ):
                        issues.append(
                            {
                                "severity": "high",
                                "type": "weak_ssl_protocol",
                                "service": server_name,
                                "message": f"Server '{server_name}' allows weak SSL/TLS protocols",
                                "recommendation": "Use only TLSv1.2 and TLSv1.3",
                            }
                        )

            # Check for SSL without HSTS
            if server_block.get("ssl_enabled", False):
                has_hsts = any(
                    "strict-transport-security" in directive.lower()
                    for directive in server_block.get("directives", [])
                )
                if not has_hsts:
                    issues.append(
                        {
                            "severity": "medium",
                            "type": "missing_hsts",
                            "service": server_name,
                            "message": f"SSL-enabled server '{server_name}' missing HSTS header",
                            "recommendation": "Add Strict-Transport-Security header for HTTPS sites",
                        }
                    )

        # Check for server_tokens exposure
        server_tokens_hidden = False
        for directive in parsed_config.get("raw_directives", []):
            if "server_tokens off" in directive.lower():
                server_tokens_hidden = True
                break

        if not server_tokens_hidden:
            issues.append(
                {
                    "severity": "low",
                    "type": "server_tokens_exposed",
                    "message": "Server version information is exposed",
                    "recommendation": "Add 'server_tokens off;' to hide nginx version",
                }
            )

        return issues

    def _analyze_nginx_best_practices(self, parsed_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Analyze Nginx configuration for best practice violations."""
        violations = []

        # Check for gzip compression
        if not self._has_gzip_enabled(parsed_config):
            violations.append(
                {
                    "severity": "medium",
                    "type": "missing_gzip",
                    "message": "Gzip compression is not enabled",
                    "recommendation": "Enable gzip compression to reduce bandwidth usage",
                }
            )

        # Check for rate limiting
        if not self._has_rate_limiting(parsed_config):
            violations.append(
                {
                    "severity": "low",
                    "type": "no_rate_limiting",
                    "message": "No rate limiting configured",
                    "recommendation": "Consider adding rate limiting to prevent abuse",
                }
            )

        # Check for access logs
        has_access_log = any(
            "access_log" in directive for directive in parsed_config.get("raw_directives", [])
        )
        if not has_access_log:
            violations.append(
                {
                    "severity": "low",
                    "type": "no_access_logging",
                    "message": "Access logging not configured",
                    "recommendation": "Enable access logging for monitoring and debugging",
                }
            )

        # Check server blocks
        for server_block in parsed_config.get("server_blocks", []):
            server_name = server_block.get("name", "default")

            # Check for default server without server_name
            if not server_block.get("server_names") or server_block.get("server_names") == ["_"]:
                violations.append(
                    {
                        "severity": "low",
                        "type": "default_server_block",
                        "service": server_name,
                        "message": f"Server block '{server_name}' appears to be a default catch-all",
                        "recommendation": "Specify explicit server_name directives for better organization",
                    }
                )

            # Check for missing error pages
            has_error_page = any(
                "error_page" in directive for directive in server_block.get("directives", [])
            )
            if not has_error_page:
                violations.append(
                    {
                        "severity": "low",
                        "type": "no_custom_error_pages",
                        "service": server_name,
                        "message": f"Server '{server_name}' has no custom error pages",
                        "recommendation": "Add custom error pages for better user experience",
                    }
                )

        return violations

    def _generate_nginx_performance_recommendations(
        self, parsed_config: dict[str, Any]
    ) -> list[str]:
        """Generate Nginx-specific performance recommendations."""
        recommendations = []

        # Check worker processes
        worker_processes = self._get_worker_processes(parsed_config)
        if not worker_processes or "auto" not in worker_processes:
            recommendations.append("Set worker_processes to 'auto' for optimal CPU utilization")

        # Check for keepalive
        has_keepalive = any(
            "keepalive" in directive for directive in parsed_config.get("raw_directives", [])
        )
        if not has_keepalive:
            recommendations.append("Enable keepalive connections to reduce connection overhead")

        # Check for sendfile
        has_sendfile = any(
            "sendfile on" in directive for directive in parsed_config.get("raw_directives", [])
        )
        if not has_sendfile:
            recommendations.append("Enable sendfile for efficient static file serving")

        # Check for client_max_body_size
        has_body_size_limit = any(
            "client_max_body_size" in directive
            for directive in parsed_config.get("raw_directives", [])
        )
        if not has_body_size_limit:
            recommendations.append("Set appropriate client_max_body_size to prevent large uploads")

        # Check for buffer optimization
        has_buffer_config = any(
            any(
                buffer_directive in directive
                for buffer_directive in [
                    "client_body_buffer_size",
                    "client_header_buffer_size",
                    "large_client_header_buffers",
                ]
            )
            for directive in parsed_config.get("raw_directives", [])
        )

        if not has_buffer_config:
            recommendations.append(
                "Configure buffer sizes for optimal memory usage and performance"
            )

        return recommendations

    def _has_rate_limiting(self, parsed_config: dict[str, Any]) -> bool:
        """Check if rate limiting is configured."""
        return any(
            "limit_req" in directive or "limit_conn" in directive
            for directive in parsed_config.get("raw_directives", [])
        )

    def _has_gzip_enabled(self, parsed_config: dict[str, Any]) -> bool:
        """Check if gzip compression is enabled."""
        return any("gzip on" in directive for directive in parsed_config.get("raw_directives", []))

    def _has_security_headers(self, parsed_config: dict[str, Any]) -> bool:
        """Check if security headers are configured."""
        security_headers = [
            "x-frame-options",
            "x-content-type-options",
            "x-xss-protection",
            "strict-transport-security",
            "content-security-policy",
        ]

        for directive in parsed_config.get("raw_directives", []):
            if any(header in directive.lower() for header in security_headers):
                return True

        return False

    def _get_worker_processes(self, parsed_config: dict[str, Any]) -> str | None:
        """Get worker_processes configuration value."""
        for directive in parsed_config.get("raw_directives", []):
            if directive.startswith("worker_processes"):
                return directive
        return None
