"""
Base Configuration Parser

Provides the abstract base class for all configuration file parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


class ConfigurationError(Exception):
    """Exception raised when configuration parsing fails."""

    def __init__(self, message: str, file_path: str = "", line_number: int | None = None):
        self.message = message
        self.file_path = file_path
        self.line_number = line_number
        super().__init__(message)


@dataclass
class ParsedConfiguration:
    """Comprehensive parsed configuration data with analysis results."""

    # Basic parsing information
    raw_content: str
    file_path: str
    parsed_data: dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)
    parsing_errors: list[str] = field(default_factory=list)

    # Service and infrastructure analysis
    services: list[dict[str, Any]] = field(default_factory=list)
    networks: list[str] = field(default_factory=list)
    volumes: list[str] = field(default_factory=list)
    exposed_ports: list[int] = field(default_factory=list)
    environment_variables: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    # Impact and risk assessment
    change_impact_score: float = 0.0
    affected_services: list[str] = field(default_factory=list)
    restart_required: bool = False
    resource_limits: dict[str, Any] = field(default_factory=dict)

    # Security and best practices analysis
    security_issues: list[dict[str, Any]] = field(default_factory=list)
    best_practice_violations: list[dict[str, Any]] = field(default_factory=list)
    performance_recommendations: list[str] = field(default_factory=list)

    # Parser metadata
    parser_version: str = "1.0"
    parser_metadata: dict[str, Any] = field(default_factory=dict)
    parsed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ParseResult:
    """Result of parsing a configuration file"""

    success: bool
    parsed_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Service analysis
    services_detected: list[str] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    ports_exposed: list[int] = field(default_factory=list)
    volumes_used: list[str] = field(default_factory=list)

    # Impact analysis
    risk_level: str = "MEDIUM"
    requires_restart: bool = False
    affected_services: list[str] = field(default_factory=list)

    # Validation
    syntax_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)

    parsed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseConfigurationParser(ABC):
    """Abstract base class for configuration file parsers"""

    def __init__(self, parser_version: str = "1.0"):
        self.supported_extensions: list[str] = []
        self.config_type: str = "generic"
        self.parser_version: str = parser_version

    @abstractmethod
    async def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse configuration content and return structured result"""
        pass

    @abstractmethod
    async def validate(self, content: str, file_path: str) -> ParseResult:
        """Validate configuration syntax and semantics"""
        pass

    @abstractmethod
    async def extract_services(self, parsed_data: dict[str, Any]) -> list[str]:
        """Extract service names from parsed configuration"""
        pass

    @abstractmethod
    async def analyze_dependencies(self, parsed_data: dict[str, Any]) -> dict[str, list[str]]:
        """Analyze service dependencies from configuration"""
        pass

    @abstractmethod
    async def assess_risk(self, old_content: str, new_content: str, file_path: str) -> str:
        """Assess risk level of configuration changes"""
        pass

    def supports_file(self, file_path: str) -> bool:
        """Check if this parser supports the given file"""
        if not self.supported_extensions:
            return False

        return any(file_path.endswith(ext) for ext in self.supported_extensions)

    def _create_base_result(self, success: bool = True) -> ParseResult:
        """Create a base ParseResult with common fields"""
        return ParseResult(success=success, parsed_at=datetime.now(timezone.utc))

    def _create_base_parsed_config(
        self, content: str, file_path: str, parsed_data: dict[str, Any]
    ) -> ParsedConfiguration:
        """Create a base ParsedConfiguration with common fields"""
        return ParsedConfiguration(
            raw_content=content,
            file_path=file_path,
            parsed_data=parsed_data,
            parser_version=self.parser_version,
        )

    def _extract_ports(self, ports_config: list[Any]) -> list[int]:
        """Extract port numbers from various port configuration formats."""
        ports = []
        for port_config in ports_config:
            if isinstance(port_config, int):
                ports.append(port_config)
            elif isinstance(port_config, str):
                # Handle "8080:80", "8080", "127.0.0.1:8080:80" formats
                if ":" in port_config:
                    parts = port_config.split(":")
                    # Take the first port (host port) if it's in host:container format
                    try:
                        ports.append(int(parts[0]))
                    except ValueError:
                        # If first part is IP, take second part
                        if len(parts) > 1:
                            try:
                                ports.append(int(parts[1]))
                            except ValueError:
                                pass
                else:
                    try:
                        ports.append(int(port_config))
                    except ValueError:
                        pass
            elif isinstance(port_config, dict):
                # Long syntax: {"target": 80, "published": 8080}
                if "published" in port_config:
                    ports.append(int(port_config["published"]))
                elif "target" in port_config:
                    ports.append(int(port_config["target"]))
        return ports

    def _extract_environment_variables(self, env_config: Any) -> dict[str, str]:
        """Extract environment variables from various configuration formats."""
        env_vars = {}

        if isinstance(env_config, dict):
            # Dictionary format: {"VAR": "value"}
            for key, value in env_config.items():
                env_vars[str(key)] = str(value) if value is not None else ""
        elif isinstance(env_config, list):
            # List format: ["VAR=value", "VAR2=value2"] or [{"VAR": "value"}]
            for item in env_config:
                if isinstance(item, str):
                    if "=" in item:
                        key, value = item.split("=", 1)
                        env_vars[key.strip()] = value.strip()
                elif isinstance(item, dict):
                    for key, value in item.items():
                        env_vars[str(key)] = str(value) if value is not None else ""
        elif isinstance(env_config, str):
            # Single string format: "VAR=value"
            if "=" in env_config:
                key, value = env_config.split("=", 1)
                env_vars[key.strip()] = value.strip()

        return env_vars

    def _calculate_change_impact_score(self, parsed_data: dict[str, Any]) -> float:
        """Calculate a base impact score for configuration changes."""
        score = 0.0

        # Base score for any configuration change
        score += 1.0

        # Additional scoring based on complexity
        if isinstance(parsed_data, dict):
            # More complex configurations have higher impact
            score += min(len(parsed_data) * 0.1, 2.0)

            # Nested structures increase complexity
            nested_count = sum(1 for v in parsed_data.values() if isinstance(v, (dict, list)))
            score += min(nested_count * 0.2, 1.5)

        return min(score, 10.0)  # Cap at 10.0

    def _extract_resource_limits(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Extract resource limits from configuration data."""
        limits = {}

        # This is a base implementation - subclasses should override for specific formats
        if "resources" in config_data:
            limits = config_data["resources"]
        elif "deploy" in config_data and "resources" in config_data["deploy"]:
            limits = config_data["deploy"]["resources"]

        return limits
