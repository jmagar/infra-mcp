"""
Systemd Service Parser

Specialized parser for systemd service files with comprehensive
analysis of service configuration, dependencies, and security settings.
"""

import logging
import re
from typing import Any

from .base_parser import BaseConfigurationParser, ParsedConfiguration, ConfigurationError

logger = logging.getLogger(__name__)


class SystemdServiceParser(BaseConfigurationParser):
    """
    Parser for systemd service files.

    Provides comprehensive analysis of systemd configurations including:
    - Service unit definitions and dependencies
    - Security and sandboxing settings
    - Resource limits and restrictions
    - Service lifecycle and restart policies
    - Socket and timer configurations
    """

    def __init__(self):
        super().__init__(parser_version="1.0")

    def get_supported_file_patterns(self) -> list[str]:
        """Get supported systemd service file patterns."""
        return [
            "*.service",
            "*.socket",
            "*.timer",
            "*.target",
            "*.mount",
            "*.automount",
            "*.path",
            "*.slice",
            "*.scope",
        ]

    def get_config_type(self) -> str:
        """Get configuration type."""
        return "systemd_service"

    async def parse(self, content: str, file_path: str) -> ParsedConfiguration:
        """Parse systemd service configuration content."""
        try:
            # Parse systemd unit file
            parsed_config = self._parse_systemd_unit(content)

            # Create base configuration
            config = self._create_base_parsed_config(content, file_path, parsed_config)

            # Validate systemd unit structure
            validation_errors = self._validate_systemd_structure(parsed_config)
            config.validation_errors.extend(validation_errors)
            config.is_valid = len(validation_errors) == 0

            # Extract service information
            config.services = self._extract_services(parsed_config)

            # Extract dependencies
            config.dependencies = self._extract_systemd_dependencies(parsed_config)

            # Extract exposed ports (if socket unit)
            config.exposed_ports = self._extract_systemd_ports(parsed_config)

            # Extract environment variables
            config.environment_variables = self._extract_systemd_environment(parsed_config)

            # Calculate change impact score
            config.change_impact_score = self._calculate_systemd_impact_score(parsed_config)

            # Identify affected services
            config.affected_services = self._get_affected_services(parsed_config)

            # Systemd changes usually require restart
            config.restart_required = True

            # Extract resource limits
            config.resource_limits = self._extract_systemd_resource_limits(parsed_config)

            # Security analysis
            config.security_issues = self._analyze_systemd_security_issues(parsed_config)

            # Best practices analysis
            config.best_practice_violations = self._analyze_systemd_best_practices(parsed_config)

            # Performance recommendations
            config.performance_recommendations = self._generate_systemd_performance_recommendations(
                parsed_config
            )

            # Systemd-specific metadata
            config.parser_metadata = {
                "unit_type": self._get_unit_type(file_path),
                "service_type": parsed_config.get("Service", {}).get("Type", "simple"),
                "restart_policy": parsed_config.get("Service", {}).get("Restart", "no"),
                "has_security_settings": self._has_security_settings(parsed_config),
                "has_resource_limits": self._has_systemd_resource_limits(parsed_config),
                "user_service": self._is_user_service(parsed_config),
                "enabled_by_default": self._is_enabled_by_default(parsed_config),
                "socket_activated": self._is_socket_activated(parsed_config),
                "timer_activated": self._is_timer_activated(parsed_config),
            }

            return config

        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to parse systemd service file: {str(e)}",
                file_path=file_path,
            ) from e

    def _parse_systemd_unit(self, content: str) -> dict[str, Any]:
        """Parse systemd unit file content into structured data."""
        config = {}
        current_section = None

        # Split into lines and process
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#") or line.startswith(";"):
                continue

            # Section headers
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                config[current_section] = {}
                continue

            # Key-value pairs
            if "=" in line and current_section:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Handle multi-value keys (like ExecStart)
                if key in config[current_section]:
                    # Convert to list if not already
                    if not isinstance(config[current_section][key], list):
                        config[current_section][key] = [config[current_section][key]]
                    config[current_section][key].append(value)
                else:
                    config[current_section][key] = value

        return config

    def _validate_systemd_structure(self, parsed_config: dict[str, Any]) -> list[str]:
        """Validate systemd unit file structure."""
        errors = []

        # Check for Unit section
        if "Unit" not in parsed_config:
            errors.append("Missing required [Unit] section")

        # Check for main section based on unit type
        unit_sections = ["Service", "Socket", "Timer", "Target", "Mount", "Automount", "Path"]
        has_main_section = any(section in parsed_config for section in unit_sections)

        if not has_main_section:
            errors.append("Missing main unit section (Service, Socket, Timer, etc.)")

        # Validate Service section specifics
        if "Service" in parsed_config:
            service_config = parsed_config["Service"]

            # Check for ExecStart in most service types
            service_type = service_config.get("Type", "simple")
            if service_type not in ["oneshot"] and "ExecStart" not in service_config:
                errors.append("Service is missing ExecStart directive")

            # Validate Type values
            valid_types = ["simple", "exec", "forking", "oneshot", "dbus", "notify", "idle"]
            if service_type not in valid_types:
                errors.append(f"Invalid service Type: {service_type}")

        # Validate Install section if present
        if "Install" in parsed_config:
            install_config = parsed_config["Install"]
            if not any(key in install_config for key in ["WantedBy", "RequiredBy", "Alias"]):
                errors.append("Install section present but no installation targets defined")

        return errors

    def _extract_services(self, parsed_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract service information from parsed config."""
        services = []

        # Get unit name from file path or use generic name
        unit_name = "systemd-unit"

        service_info = {
            "name": unit_name,
            "type": self._get_unit_type_from_config(parsed_config),
            "description": parsed_config.get("Unit", {}).get("Description", ""),
            "service_type": parsed_config.get("Service", {}).get("Type", "simple"),
            "exec_start": self._get_exec_commands(parsed_config, "ExecStart"),
            "exec_stop": self._get_exec_commands(parsed_config, "ExecStop"),
            "exec_reload": self._get_exec_commands(parsed_config, "ExecReload"),
            "user": parsed_config.get("Service", {}).get("User"),
            "group": parsed_config.get("Service", {}).get("Group"),
            "working_directory": parsed_config.get("Service", {}).get("WorkingDirectory"),
            "restart_policy": parsed_config.get("Service", {}).get("Restart", "no"),
            "restart_sec": parsed_config.get("Service", {}).get("RestartSec"),
            "timeout_start": parsed_config.get("Service", {}).get("TimeoutStartSec"),
            "timeout_stop": parsed_config.get("Service", {}).get("TimeoutStopSec"),
            "pid_file": parsed_config.get("Service", {}).get("PIDFile"),
            "environment_files": self._get_environment_files(parsed_config),
            "wanted_by": self._get_install_targets(parsed_config, "WantedBy"),
            "required_by": self._get_install_targets(parsed_config, "RequiredBy"),
        }

        services.append(service_info)
        return services

    def _extract_systemd_dependencies(self, parsed_config: dict[str, Any]) -> list[str]:
        """Extract systemd unit dependencies."""
        dependencies = []

        unit_config = parsed_config.get("Unit", {})

        # Various dependency types
        dependency_keys = [
            "Requires",
            "Wants",
            "Requisite",
            "BindsTo",
            "PartOf",
            "After",
            "Before",
            "Conflicts",
            "OnFailure",
        ]

        for key in dependency_keys:
            if key in unit_config:
                value = unit_config[key]
                if isinstance(value, list):
                    dependencies.extend(value)
                else:
                    # Split on whitespace for multiple values
                    dependencies.extend(value.split())

        return list(set(dependencies))  # Remove duplicates

    def _extract_systemd_ports(self, parsed_config: dict[str, Any]) -> list[int]:
        """Extract ports from socket units."""
        ports = []

        if "Socket" in parsed_config:
            socket_config = parsed_config["Socket"]

            # ListenStream, ListenDatagram, etc.
            listen_keys = ["ListenStream", "ListenDatagram", "ListenSequentialPacket"]

            for key in listen_keys:
                if key in socket_config:
                    values = socket_config[key]
                    if not isinstance(values, list):
                        values = [values]

                    for value in values:
                        # Extract port from address:port format
                        port_match = re.search(r":(\d+)$", value)
                        if port_match:
                            ports.append(int(port_match.group(1)))
                        elif value.isdigit():
                            ports.append(int(value))

        return sorted(list(set(ports)))

    def _extract_systemd_environment(self, parsed_config: dict[str, Any]) -> dict[str, str]:
        """Extract environment variables from systemd config."""
        env_vars = {}

        if "Service" in parsed_config:
            service_config = parsed_config["Service"]

            # Environment directive
            if "Environment" in service_config:
                env_values = service_config["Environment"]
                if not isinstance(env_values, list):
                    env_values = [env_values]

                for env_value in env_values:
                    # Parse KEY=value format
                    if "=" in env_value:
                        key, value = env_value.split("=", 1)
                        env_vars[key.strip()] = value.strip().strip("\"'")

        return env_vars

    def _calculate_systemd_impact_score(self, parsed_config: dict[str, Any]) -> float:
        """Calculate impact score for systemd configuration changes."""
        score = 0.0

        # Service type impact
        service_type = parsed_config.get("Service", {}).get("Type", "simple")
        if service_type in ["forking", "notify"]:
            score += 1.0

        # Critical services have higher impact
        unit_config = parsed_config.get("Unit", {})
        description = unit_config.get("Description", "").lower()

        if any(keyword in description for keyword in ["network", "database", "web", "proxy"]):
            score += 2.0

        # Dependencies increase impact
        dependencies = self._extract_systemd_dependencies(parsed_config)
        score += min(len(dependencies) * 0.3, 2.0)

        # Security settings changes have medium impact
        if self._has_security_settings(parsed_config):
            score += 1.5

        # Socket activation increases impact
        if "Socket" in parsed_config:
            score += 1.0

        # Timer services have lower impact
        if "Timer" in parsed_config:
            score += 0.5

        return min(score, 10.0)

    def _get_affected_services(self, parsed_config: dict[str, Any]) -> list[str]:
        """Get list of services that might be affected by changes."""
        affected = []

        # The service itself
        affected.append("self")

        # Services that depend on this one (reverse dependencies)
        # This would require system-wide analysis in practice

        return affected

    def _extract_systemd_resource_limits(self, parsed_config: dict[str, Any]) -> dict[str, Any]:
        """Extract resource limits from systemd config."""
        limits = {}

        if "Service" in parsed_config:
            service_config = parsed_config["Service"]

            # CPU limits
            if "CPUShares" in service_config:
                limits["cpu_shares"] = service_config["CPUShares"]
            if "CPUQuota" in service_config:
                limits["cpu_quota"] = service_config["CPUQuota"]

            # Memory limits
            if "MemoryLimit" in service_config:
                limits["memory_limit"] = service_config["MemoryLimit"]
            if "MemoryMax" in service_config:
                limits["memory_max"] = service_config["MemoryMax"]

            # Task limits
            if "TasksMax" in service_config:
                limits["tasks_max"] = service_config["TasksMax"]

            # I/O limits
            if "IOWeight" in service_config:
                limits["io_weight"] = service_config["IOWeight"]
            if "BlockIOWeight" in service_config:
                limits["blockio_weight"] = service_config["BlockIOWeight"]

        return limits

    def _analyze_systemd_security_issues(
        self, parsed_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze systemd configuration for security issues."""
        issues = []

        service_config = parsed_config.get("Service", {})

        # Running as root
        user = service_config.get("User")
        if not user or user == "root" or user == "0":
            issues.append(
                {
                    "severity": "medium",
                    "type": "running_as_root",
                    "message": "Service runs as root user",
                    "recommendation": "Create dedicated user account for this service",
                }
            )

        # No sandboxing
        sandboxing_options = [
            "PrivateTmp",
            "PrivateDevices",
            "PrivateNetwork",
            "ProtectSystem",
            "ProtectHome",
            "NoNewPrivileges",
            "ProtectKernelTunables",
            "ProtectKernelModules",
            "ProtectControlGroups",
        ]

        has_sandboxing = any(option in service_config for option in sandboxing_options)
        if not has_sandboxing:
            issues.append(
                {
                    "severity": "medium",
                    "type": "no_sandboxing",
                    "message": "Service has no sandboxing options enabled",
                    "recommendation": "Enable appropriate sandboxing options like PrivateTmp, ProtectSystem",
                }
            )

        # Dangerous capabilities
        if "AmbientCapabilities" in service_config:
            caps = service_config["AmbientCapabilities"]
            dangerous_caps = ["CAP_SYS_ADMIN", "CAP_SYS_PTRACE", "CAP_SYS_MODULE"]

            caps_list = caps.split() if isinstance(caps, str) else [caps]
            for cap in caps_list:
                if cap in dangerous_caps:
                    issues.append(
                        {
                            "severity": "high",
                            "type": "dangerous_capability",
                            "message": f"Service has dangerous capability: {cap}",
                            "recommendation": f"Remove {cap} capability unless absolutely necessary",
                        }
                    )

        # World-writable directories
        working_dir = service_config.get("WorkingDirectory")
        if working_dir and working_dir in ["/tmp", "/var/tmp"]:
            issues.append(
                {
                    "severity": "medium",
                    "type": "unsafe_working_directory",
                    "message": f"Service uses world-writable working directory: {working_dir}",
                    "recommendation": "Use a dedicated directory with proper permissions",
                }
            )

        # Executable scripts in ExecStart
        exec_start = service_config.get("ExecStart")
        if exec_start:
            exec_commands = [exec_start] if isinstance(exec_start, str) else exec_start
            for cmd in exec_commands:
                if cmd and (cmd.endswith(".sh") or "/tmp/" in cmd):
                    issues.append(
                        {
                            "severity": "medium",
                            "type": "unsafe_executable",
                            "message": "Service executes scripts from unsafe locations",
                            "recommendation": "Move scripts to secure locations with proper permissions",
                        }
                    )

        return issues

    def _analyze_systemd_best_practices(
        self, parsed_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze systemd configuration for best practice violations."""
        violations = []

        service_config = parsed_config.get("Service", {})
        unit_config = parsed_config.get("Unit", {})

        # Missing description
        if not unit_config.get("Description"):
            violations.append(
                {
                    "severity": "low",
                    "type": "missing_description",
                    "message": "Service has no description",
                    "recommendation": "Add Description= in [Unit] section",
                }
            )

        # No restart policy
        restart = service_config.get("Restart", "no")
        if restart == "no":
            violations.append(
                {
                    "severity": "medium",
                    "type": "no_restart_policy",
                    "message": "Service has no restart policy",
                    "recommendation": "Consider using Restart=on-failure or Restart=always",
                }
            )

        # Missing timeout settings
        if "TimeoutStartSec" not in service_config:
            violations.append(
                {
                    "severity": "low",
                    "type": "missing_timeout",
                    "message": "Service has no start timeout configured",
                    "recommendation": "Set TimeoutStartSec= to prevent hanging services",
                }
            )

        # Type=forking without PidFile
        service_type = service_config.get("Type", "simple")
        if service_type == "forking" and "PIDFile" not in service_config:
            violations.append(
                {
                    "severity": "medium",
                    "type": "forking_without_pidfile",
                    "message": "Forking service without PIDFile",
                    "recommendation": "Add PIDFile= or consider changing to Type=simple",
                }
            )

        # No resource limits
        if not self._has_systemd_resource_limits(parsed_config):
            violations.append(
                {
                    "severity": "low",
                    "type": "no_resource_limits",
                    "message": "Service has no resource limits",
                    "recommendation": "Add MemoryMax= and CPUQuota= to prevent resource exhaustion",
                }
            )

        # Missing dependencies
        if not unit_config.get("After") and not unit_config.get("Wants"):
            violations.append(
                {
                    "severity": "low",
                    "type": "missing_dependencies",
                    "message": "Service has no explicit dependencies",
                    "recommendation": "Add After= and Wants= dependencies for proper ordering",
                }
            )

        # No install section for persistent services
        if "Install" not in parsed_config and service_type != "oneshot":
            violations.append(
                {
                    "severity": "medium",
                    "type": "missing_install_section",
                    "message": "Service has no [Install] section",
                    "recommendation": "Add [Install] section with WantedBy= to enable service",
                }
            )

        return violations

    def _generate_systemd_performance_recommendations(
        self, parsed_config: dict[str, Any]
    ) -> list[str]:
        """Generate systemd-specific performance recommendations."""
        recommendations = []

        service_config = parsed_config.get("Service", {})

        # Resource limits
        if not self._has_systemd_resource_limits(parsed_config):
            recommendations.append(
                "Add resource limits (MemoryMax, CPUQuota) to prevent resource contention"
            )

        # Service type optimization
        service_type = service_config.get("Type", "simple")
        if service_type == "forking":
            recommendations.append(
                "Consider changing from Type=forking to Type=simple for better performance"
            )

        # I/O scheduling
        if "IOSchedulingClass" not in service_config:
            recommendations.append("Consider setting IOSchedulingClass for I/O intensive services")

        # OOM handling
        if "OOMScoreAdjust" not in service_config:
            recommendations.append("Set OOMScoreAdjust to control OOM killer behavior")

        # Private namespaces
        if not service_config.get("PrivateTmp"):
            recommendations.append("Enable PrivateTmp for better isolation and performance")

        # Startup optimization
        restart_sec = service_config.get("RestartSec")
        if not restart_sec:
            recommendations.append(
                "Set RestartSec to control restart timing and prevent restart storms"
            )

        return recommendations

    def _get_unit_type(self, file_path: str) -> str:
        """Get unit type from file extension."""
        if file_path.endswith(".service"):
            return "service"
        elif file_path.endswith(".socket"):
            return "socket"
        elif file_path.endswith(".timer"):
            return "timer"
        elif file_path.endswith(".target"):
            return "target"
        elif file_path.endswith(".mount"):
            return "mount"
        elif file_path.endswith(".automount"):
            return "automount"
        elif file_path.endswith(".path"):
            return "path"
        elif file_path.endswith(".slice"):
            return "slice"
        elif file_path.endswith(".scope"):
            return "scope"
        else:
            return "unknown"

    def _get_unit_type_from_config(self, parsed_config: dict[str, Any]) -> str:
        """Get unit type from configuration sections."""
        if "Service" in parsed_config:
            return "service"
        elif "Socket" in parsed_config:
            return "socket"
        elif "Timer" in parsed_config:
            return "timer"
        elif "Target" in parsed_config:
            return "target"
        elif "Mount" in parsed_config:
            return "mount"
        elif "Automount" in parsed_config:
            return "automount"
        elif "Path" in parsed_config:
            return "path"
        else:
            return "unknown"

    def _get_exec_commands(self, parsed_config: dict[str, Any], key: str) -> list[str]:
        """Get exec commands from service config."""
        service_config = parsed_config.get("Service", {})
        if key not in service_config:
            return []

        value = service_config[key]
        if isinstance(value, list):
            return value
        else:
            return [value]

    def _get_environment_files(self, parsed_config: dict[str, Any]) -> list[str]:
        """Get environment file paths."""
        service_config = parsed_config.get("Service", {})
        env_files = []

        if "EnvironmentFile" in service_config:
            value = service_config["EnvironmentFile"]
            if isinstance(value, list):
                env_files.extend(value)
            else:
                env_files.append(value)

        return env_files

    def _get_install_targets(self, parsed_config: dict[str, Any], key: str) -> list[str]:
        """Get install targets from config."""
        install_config = parsed_config.get("Install", {})
        if key not in install_config:
            return []

        value = install_config[key]
        if isinstance(value, list):
            return value
        else:
            return value.split()

    def _has_security_settings(self, parsed_config: dict[str, Any]) -> bool:
        """Check if service has security/sandboxing settings."""
        service_config = parsed_config.get("Service", {})

        security_options = [
            "User",
            "Group",
            "PrivateTmp",
            "PrivateDevices",
            "PrivateNetwork",
            "ProtectSystem",
            "ProtectHome",
            "NoNewPrivileges",
            "ProtectKernelTunables",
            "ProtectKernelModules",
            "ProtectControlGroups",
            "ReadWritePaths",
            "ReadOnlyPaths",
            "InaccessiblePaths",
            "CapabilityBoundingSet",
            "AmbientCapabilities",
            "SecureBits",
        ]

        return any(option in service_config for option in security_options)

    def _has_systemd_resource_limits(self, parsed_config: dict[str, Any]) -> bool:
        """Check if service has resource limits configured."""
        service_config = parsed_config.get("Service", {})

        limit_options = [
            "MemoryLimit",
            "MemoryMax",
            "CPUShares",
            "CPUQuota",
            "TasksMax",
            "IOWeight",
            "BlockIOWeight",
            "LimitNOFILE",
            "LimitNPROC",
        ]

        return any(option in service_config for option in limit_options)

    def _is_user_service(self, parsed_config: dict[str, Any]) -> bool:
        """Check if this is a user service."""
        service_config = parsed_config.get("Service", {})
        user = service_config.get("User")
        return user is not None and user not in ["root", "0"]

    def _is_enabled_by_default(self, parsed_config: dict[str, Any]) -> bool:
        """Check if service is enabled by default."""
        install_config = parsed_config.get("Install", {})
        return bool(install_config.get("WantedBy") or install_config.get("RequiredBy"))

    def _is_socket_activated(self, parsed_config: dict[str, Any]) -> bool:
        """Check if service is socket activated."""
        return "Socket" in parsed_config

    def _is_timer_activated(self, parsed_config: dict[str, Any]) -> bool:
        """Check if service is timer activated."""
        return "Timer" in parsed_config
