"""
Docker Compose Configuration Parser

Specialized parser for Docker Compose YAML files with comprehensive
service analysis, security checks, and performance recommendations.
"""

import logging
import yaml
from typing import Any

from .base_parser import BaseConfigurationParser, ParsedConfiguration, ConfigurationError

logger = logging.getLogger(__name__)


class DockerComposeParser(BaseConfigurationParser):
    """
    Parser for Docker Compose configuration files.

    Provides comprehensive analysis of Docker Compose files including:
    - Service definitions and dependencies
    - Network and volume configurations
    - Security vulnerability detection
    - Performance optimization recommendations
    - Resource usage analysis
    """

    def __init__(self):
        super().__init__(parser_version="1.0")

    def get_supported_file_patterns(self) -> list[str]:
        """Get supported Docker Compose file patterns."""
        return [
            "docker-compose.yml",
            "docker-compose.yaml",
            "docker-compose.*.yml",
            "docker-compose.*.yaml",
            "compose.yml",
            "compose.yaml",
        ]

    def get_config_type(self) -> str:
        """Get configuration type."""
        return "docker_compose"

    async def parse(self, content: str, file_path: str) -> ParsedConfiguration:
        """Parse Docker Compose configuration content."""
        try:
            # Parse YAML content
            try:
                compose_data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ConfigurationError(
                    message=f"Invalid YAML syntax: {str(e)}",
                    file_path=file_path,
                    line_number=getattr(e, "problem_mark", {}).get("line", None),
                ) from e

            if not isinstance(compose_data, dict):
                raise ConfigurationError(
                    message="Docker Compose file must contain a YAML dictionary",
                    file_path=file_path,
                )

            # Create base configuration
            parsed_config = self._create_base_parsed_config(content, file_path, compose_data)

            # Validate Docker Compose structure
            validation_errors = self._validate_compose_structure(compose_data)
            parsed_config.validation_errors.extend(validation_errors)
            parsed_config.is_valid = len(validation_errors) == 0

            # Extract services information
            parsed_config.services = self._extract_services(compose_data)

            # Extract network information
            parsed_config.networks = self._extract_networks(compose_data)

            # Extract volume information
            parsed_config.volumes = self._extract_volumes(compose_data)

            # Extract exposed ports across all services
            parsed_config.exposed_ports = self._extract_all_ports(compose_data)

            # Extract all environment variables
            parsed_config.environment_variables = self._extract_all_environment_variables(
                compose_data
            )

            # Extract service dependencies
            parsed_config.dependencies = self._extract_dependencies(compose_data)

            # Calculate change impact score
            parsed_config.change_impact_score = self._calculate_change_impact_score(compose_data)

            # Identify affected services for changes
            parsed_config.affected_services = list(compose_data.get("services", {}).keys())

            # Determine if restart is required (usually true for compose changes)
            parsed_config.restart_required = self._requires_restart(compose_data)

            # Extract resource limits
            parsed_config.resource_limits = self._extract_resource_limits(compose_data)

            # Security analysis
            parsed_config.security_issues = self._analyze_docker_security_issues(compose_data)

            # Best practices analysis
            parsed_config.best_practice_violations = self._analyze_docker_best_practices(
                compose_data
            )

            # Performance recommendations
            parsed_config.performance_recommendations = (
                self._generate_docker_performance_recommendations(compose_data)
            )

            # Additional Docker Compose specific metadata
            parsed_config.parser_metadata = {
                "compose_version": compose_data.get("version", "unknown"),
                "service_count": len(compose_data.get("services", {})),
                "network_count": len(compose_data.get("networks", {})),
                "volume_count": len(compose_data.get("volumes", {})),
                "secret_count": len(compose_data.get("secrets", {})),
                "config_count": len(compose_data.get("configs", {})),
                "has_build_configs": self._has_build_configurations(compose_data),
                "has_healthchecks": self._has_health_checks(compose_data),
                "has_resource_limits": self._has_resource_limits(compose_data),
            }

            return parsed_config

        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to parse Docker Compose file: {str(e)}",
                file_path=file_path,
            ) from e

    def _validate_compose_structure(self, compose_data: dict[str, Any]) -> list[str]:
        """Validate Docker Compose file structure."""
        errors = []

        # Check for services section
        if "services" not in compose_data:
            errors.append("Missing required 'services' section")
        elif not isinstance(compose_data["services"], dict):
            errors.append("'services' section must be a dictionary")
        elif len(compose_data["services"]) == 0:
            errors.append("'services' section cannot be empty")

        # Check version if present
        if "version" in compose_data:
            version = compose_data["version"]
            if not isinstance(version, str):
                errors.append("'version' must be a string")
            else:
                # Validate supported versions
                supported_versions = [
                    "2",
                    "2.0",
                    "2.1",
                    "2.2",
                    "2.3",
                    "2.4",
                    "3",
                    "3.0",
                    "3.1",
                    "3.2",
                    "3.3",
                    "3.4",
                    "3.5",
                    "3.6",
                    "3.7",
                    "3.8",
                    "3.9",
                ]
                if version not in supported_versions:
                    errors.append(f"Unsupported or unknown compose version: {version}")

        # Validate services
        if "services" in compose_data and isinstance(compose_data["services"], dict):
            for service_name, service_config in compose_data["services"].items():
                if not isinstance(service_config, dict):
                    errors.append(f"Service '{service_name}' configuration must be a dictionary")
                    continue

                # Check for required image or build
                if "image" not in service_config and "build" not in service_config:
                    errors.append(
                        f"Service '{service_name}' must specify either 'image' or 'build'"
                    )

        return errors

    def _extract_services(self, compose_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract detailed service information."""
        services = []

        for service_name, service_config in compose_data.get("services", {}).items():
            if not isinstance(service_config, dict):
                continue

            service_info = {
                "name": service_name,
                "image": service_config.get("image"),
                "build": service_config.get("build"),
                "ports": self._extract_ports(service_config.get("ports", [])),
                "environment": self._extract_environment_variables(
                    service_config.get("environment", [])
                ),
                "volumes": service_config.get("volumes", []),
                "networks": list(service_config.get("networks", []))
                if isinstance(service_config.get("networks"), list)
                else list(service_config.get("networks", {}).keys())
                if isinstance(service_config.get("networks"), dict)
                else [],
                "depends_on": list(service_config.get("depends_on", []))
                if isinstance(service_config.get("depends_on"), list)
                else list(service_config.get("depends_on", {}).keys())
                if isinstance(service_config.get("depends_on"), dict)
                else [],
                "restart": service_config.get("restart", "no"),
                "command": service_config.get("command"),
                "entrypoint": service_config.get("entrypoint"),
                "working_dir": service_config.get("working_dir"),
                "user": service_config.get("user"),
                "privileged": service_config.get("privileged", False),
                "network_mode": service_config.get("network_mode"),
                "pid": service_config.get("pid"),
                "ipc": service_config.get("ipc"),
                "security_opt": service_config.get("security_opt", []),
                "cap_add": service_config.get("cap_add", []),
                "cap_drop": service_config.get("cap_drop", []),
                "devices": service_config.get("devices", []),
                "labels": service_config.get("labels", {}),
                "logging": service_config.get("logging", {}),
                "healthcheck": service_config.get("healthcheck"),
                "deploy": service_config.get("deploy", {}),
            }

            services.append(service_info)

        return services

    def _extract_networks(self, compose_data: dict[str, Any]) -> list[str]:
        """Extract network configurations."""
        networks = []

        # Networks defined at top level
        if "networks" in compose_data:
            networks.extend(compose_data["networks"].keys())

        # Default network if no networks defined
        if not networks:
            networks.append("default")

        return networks

    def _extract_volumes(self, compose_data: dict[str, Any]) -> list[str]:
        """Extract volume configurations."""
        volumes = []

        # Top-level volumes
        if "volumes" in compose_data:
            volumes.extend(compose_data["volumes"].keys())

        # Service-specific volumes
        for service_config in compose_data.get("services", {}).values():
            if isinstance(service_config, dict):
                service_volumes = service_config.get("volumes", [])
                for volume in service_volumes:
                    if isinstance(volume, str):
                        # Extract volume name from bind mount or named volume
                        if ":" in volume:
                            volume_part = volume.split(":")[0]
                            if not volume_part.startswith("/"):  # Named volume
                                volumes.append(volume_part)
                    elif isinstance(volume, dict):
                        # Long syntax volume
                        if "source" in volume:
                            volumes.append(volume["source"])

        return list(set(volumes))  # Remove duplicates

    def _extract_all_ports(self, compose_data: dict[str, Any]) -> list[int]:
        """Extract all exposed ports from all services."""
        all_ports = []

        for service_config in compose_data.get("services", {}).values():
            if isinstance(service_config, dict):
                ports = self._extract_ports(service_config.get("ports", []))
                all_ports.extend(ports)

        return sorted(list(set(all_ports)))

    def _extract_all_environment_variables(self, compose_data: dict[str, Any]) -> dict[str, str]:
        """Extract all environment variables from all services."""
        all_env_vars = {}

        for service_name, service_config in compose_data.get("services", {}).items():
            if isinstance(service_config, dict):
                env_vars = self._extract_environment_variables(
                    service_config.get("environment", [])
                )
                for key, value in env_vars.items():
                    # Prefix with service name to avoid conflicts
                    all_env_vars[f"{service_name}.{key}"] = value

        return all_env_vars

    def _extract_dependencies(self, compose_data: dict[str, Any]) -> list[str]:
        """Extract service dependencies."""
        dependencies = []

        for service_config in compose_data.get("services", {}).values():
            if isinstance(service_config, dict):
                depends_on = service_config.get("depends_on", [])
                if isinstance(depends_on, list):
                    dependencies.extend(depends_on)
                elif isinstance(depends_on, dict):
                    dependencies.extend(depends_on.keys())

        return list(set(dependencies))

    def _requires_restart(self, compose_data: dict[str, Any]) -> bool:
        """Determine if configuration changes require service restart."""
        # Most Docker Compose changes require restart
        # Could be more sophisticated based on specific changes
        return True

    def _analyze_docker_security_issues(self, compose_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Analyze Docker Compose configuration for security issues."""
        issues = []

        for service_name, service_config in compose_data.get("services", {}).items():
            if not isinstance(service_config, dict):
                continue

            # Check for privileged mode
            if service_config.get("privileged"):
                issues.append(
                    {
                        "severity": "high",
                        "type": "privileged_container",
                        "service": service_name,
                        "message": f"Service '{service_name}' runs in privileged mode",
                        "recommendation": "Remove privileged mode or use specific capabilities instead",
                    }
                )

            # Check for host networking
            if service_config.get("network_mode") == "host":
                issues.append(
                    {
                        "severity": "medium",
                        "type": "host_networking",
                        "service": service_name,
                        "message": f"Service '{service_name}' uses host networking",
                        "recommendation": "Use Docker networks instead of host networking",
                    }
                )

            # Check for host PID namespace
            if service_config.get("pid") == "host":
                issues.append(
                    {
                        "severity": "high",
                        "type": "host_pid_namespace",
                        "service": service_name,
                        "message": f"Service '{service_name}' shares host PID namespace",
                        "recommendation": "Remove pid: host unless absolutely necessary",
                    }
                )

            # Check for excessive capabilities
            cap_add = service_config.get("cap_add", [])
            dangerous_caps = ["SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "SYS_MODULE"]
            for cap in cap_add:
                if cap in dangerous_caps:
                    issues.append(
                        {
                            "severity": "medium",
                            "type": "dangerous_capability",
                            "service": service_name,
                            "message": f"Service '{service_name}' has dangerous capability: {cap}",
                            "recommendation": f"Remove capability {cap} unless absolutely necessary",
                        }
                    )

            # Check for device access
            devices = service_config.get("devices", [])
            if devices:
                issues.append(
                    {
                        "severity": "medium",
                        "type": "device_access",
                        "service": service_name,
                        "message": f"Service '{service_name}' has direct device access",
                        "recommendation": "Limit device access to only what's necessary",
                    }
                )

            # Check for bind mounts to sensitive paths
            volumes = service_config.get("volumes", [])
            sensitive_paths = ["/", "/etc", "/var/run/docker.sock", "/proc", "/sys"]
            for volume in volumes:
                if isinstance(volume, str) and ":" in volume:
                    host_path = volume.split(":")[0]
                    for sensitive_path in sensitive_paths:
                        if host_path.startswith(sensitive_path):
                            issues.append(
                                {
                                    "severity": "high",
                                    "type": "sensitive_bind_mount",
                                    "service": service_name,
                                    "message": f"Service '{service_name}' mounts sensitive path: {host_path}",
                                    "recommendation": "Avoid mounting sensitive system paths",
                                }
                            )
                            break

            # Check for hardcoded secrets in environment variables
            env_vars = self._extract_environment_variables(service_config.get("environment", []))
            secret_patterns = ["password", "secret", "key", "token", "api_key", "credential"]
            for env_key, env_value in env_vars.items():
                for pattern in secret_patterns:
                    if pattern.lower() in env_key.lower() and env_value:
                        issues.append(
                            {
                                "severity": "high",
                                "type": "hardcoded_secret",
                                "service": service_name,
                                "message": f"Service '{service_name}' has potential hardcoded secret: {env_key}",
                                "recommendation": "Use Docker secrets or external secret management",
                            }
                        )
                        break

        return issues

    def _analyze_docker_best_practices(self, compose_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Analyze Docker Compose configuration for best practice violations."""
        violations = []

        for service_name, service_config in compose_data.get("services", {}).items():
            if not isinstance(service_config, dict):
                continue

            # Check for missing health checks
            if "healthcheck" not in service_config:
                violations.append(
                    {
                        "severity": "low",
                        "type": "missing_healthcheck",
                        "service": service_name,
                        "message": f"Service '{service_name}' has no health check configured",
                        "recommendation": "Add health check for better monitoring and recovery",
                    }
                )

            # Check for missing resource limits
            deploy_config = service_config.get("deploy", {})
            if "resources" not in deploy_config:
                violations.append(
                    {
                        "severity": "medium",
                        "type": "missing_resource_limits",
                        "service": service_name,
                        "message": f"Service '{service_name}' has no resource limits",
                        "recommendation": "Add CPU and memory limits to prevent resource exhaustion",
                    }
                )

            # Check for using latest tag
            image = service_config.get("image", "")
            if image and (image.endswith(":latest") or ":" not in image):
                violations.append(
                    {
                        "severity": "medium",
                        "type": "latest_tag",
                        "service": service_name,
                        "message": f"Service '{service_name}' uses 'latest' or untagged image",
                        "recommendation": "Use specific version tags for reproducible deployments",
                    }
                )

            # Check for running as root
            user = service_config.get("user")
            if not user or user == "0" or user == "root":
                violations.append(
                    {
                        "severity": "medium",
                        "type": "running_as_root",
                        "service": service_name,
                        "message": f"Service '{service_name}' runs as root user",
                        "recommendation": "Create and use a non-root user in the container",
                    }
                )

            # Check for restart policy
            restart_policy = service_config.get("restart", "no")
            if restart_policy == "no":
                violations.append(
                    {
                        "severity": "low",
                        "type": "no_restart_policy",
                        "service": service_name,
                        "message": f"Service '{service_name}' has no restart policy",
                        "recommendation": "Consider using 'unless-stopped' or 'on-failure' restart policy",
                    }
                )

            # Check for logging configuration
            if "logging" not in service_config:
                violations.append(
                    {
                        "severity": "low",
                        "type": "no_logging_config",
                        "service": service_name,
                        "message": f"Service '{service_name}' has no logging configuration",
                        "recommendation": "Configure logging driver and options for better log management",
                    }
                )

        return violations

    def _generate_docker_performance_recommendations(
        self, compose_data: dict[str, Any]
    ) -> list[str]:
        """Generate Docker Compose specific performance recommendations."""
        recommendations = []

        # Count services without resource limits
        services_without_limits = 0
        services_without_healthchecks = 0
        total_services = len(compose_data.get("services", {}))

        for service_config in compose_data.get("services", {}).values():
            if isinstance(service_config, dict):
                if "deploy" not in service_config or "resources" not in service_config.get(
                    "deploy", {}
                ):
                    services_without_limits += 1

                if "healthcheck" not in service_config:
                    services_without_healthchecks += 1

        if services_without_limits > 0:
            recommendations.append(
                f"Add resource limits to {services_without_limits} service(s) to prevent resource contention"
            )

        if services_without_healthchecks > 0:
            recommendations.append(
                f"Add health checks to {services_without_healthchecks} service(s) for better monitoring"
            )

        # Check for inefficient volume mounts
        bind_mount_count = 0
        for service_config in compose_data.get("services", {}).values():
            if isinstance(service_config, dict):
                volumes = service_config.get("volumes", [])
                for volume in volumes:
                    if isinstance(volume, str) and ":" in volume and volume.startswith("/"):
                        bind_mount_count += 1

        if bind_mount_count > 5:
            recommendations.append(
                "Consider using named volumes instead of bind mounts for better performance"
            )

        # Check for network optimization
        if len(compose_data.get("networks", {})) == 0:
            recommendations.append(
                "Consider defining custom networks for better service isolation and performance"
            )

        return recommendations

    def _has_build_configurations(self, compose_data: dict[str, Any]) -> bool:
        """Check if any services have build configurations."""
        for service_config in compose_data.get("services", {}).values():
            if isinstance(service_config, dict) and "build" in service_config:
                return True
        return False

    def _has_health_checks(self, compose_data: dict[str, Any]) -> bool:
        """Check if any services have health checks."""
        for service_config in compose_data.get("services", {}).values():
            if isinstance(service_config, dict) and "healthcheck" in service_config:
                return True
        return False

    def _has_resource_limits(self, compose_data: dict[str, Any]) -> bool:
        """Check if any services have resource limits."""
        for service_config in compose_data.get("services", {}).values():
            if isinstance(service_config, dict):
                deploy_config = service_config.get("deploy", {})
                if "resources" in deploy_config:
                    return True
        return False
