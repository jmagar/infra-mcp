"""
Command Registry

Central repository for all SSH command definitions, eliminating duplication
and providing a single source of truth for command configurations.
"""

import logging
from datetime import timedelta
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CommandCategory(str, Enum):
    """Command categories for organization and access control."""

    SYSTEM_INFO = "system_info"
    SYSTEM_MONITORING = "system_monitoring"
    CONTAINER_MANAGEMENT = "container_management"
    DOCKER_COMPOSE = "docker_compose"
    ZFS_MANAGEMENT = "zfs_management"
    DRIVE_HEALTH = "drive_health"
    NETWORK_INFO = "network_info"
    PROCESS_MANAGEMENT = "process_management"
    SERVICE_MANAGEMENT = "service_management"
    FILE_OPERATIONS = "file_operations"
    CONFIGURATION = "configuration"
    LOGS = "logs"


@dataclass
class CommandDefinition:
    """
    Comprehensive command definition with execution parameters and metadata.
    """

    name: str
    command: str
    category: CommandCategory
    description: str
    timeout_seconds: int = 30
    retry_count: int = 2
    retry_delay_seconds: int = 1
    expected_exit_codes: list[int] = field(default_factory=lambda: [0])
    requires_sudo: bool = False
    cache_ttl_seconds: int | None = None
    freshness_threshold_seconds: int = 300  # 5 minutes default
    parser_class: str | None = None
    validation_patterns: list[str] = field(default_factory=list)
    error_patterns: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate command definition."""
        if not self.name:
            raise ValueError("Command name is required")
        if not self.command:
            raise ValueError("Command string is required")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        if self.retry_count < 0:
            raise ValueError("Retry count cannot be negative")


class CommandRegistry:
    """
    Central registry for all SSH command definitions.

    Features:
    - Eliminates command duplication across the codebase
    - Provides consistent timeout, retry, and caching configurations
    - Supports command categorization and access control
    - Includes validation and error detection patterns
    - Manages cache TTL and freshness thresholds per command
    """

    def __init__(self):
        self._commands: dict[str, CommandDefinition] = {}
        self._categories: dict[CommandCategory, list[str]] = {}
        self._initialize_commands()

        logger.info(f"CommandRegistry initialized with {len(self._commands)} commands")

    def _initialize_commands(self) -> None:
        """Initialize all command definitions."""

        # System Information Commands
        self._register_system_info_commands()

        # System Monitoring Commands
        self._register_system_monitoring_commands()

        # Container Management Commands
        self._register_container_commands()

        # Docker Compose Commands
        self._register_docker_compose_commands()

        # ZFS Management Commands
        self._register_zfs_commands()

        # Drive Health Commands
        self._register_drive_health_commands()

        # Network Information Commands
        self._register_network_commands()

        # Process Management Commands
        self._register_process_commands()

        # Service Management Commands
        self._register_service_commands()

        # File Operations Commands
        self._register_file_commands()

        # Configuration Commands
        self._register_configuration_commands()

        # Logs Commands
        self._register_logs_commands()

    def _register_system_info_commands(self) -> None:
        """Register system information commands."""

        self.register(
            CommandDefinition(
                name="get_system_info",
                command="uname -a && cat /etc/os-release && uptime && free -h && df -h",
                category=CommandCategory.SYSTEM_INFO,
                description="Get comprehensive system information",
                timeout_seconds=15,
                cache_ttl_seconds=3600,  # 1 hour
                freshness_threshold_seconds=1800,  # 30 minutes
                validation_patterns=[r"Linux", r"PRETTY_NAME", r"load average"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_cpu_info",
                command="lscpu",
                category=CommandCategory.SYSTEM_INFO,
                description="Get detailed CPU information",
                timeout_seconds=10,
                cache_ttl_seconds=86400,  # 24 hours (rarely changes)
                freshness_threshold_seconds=43200,  # 12 hours
                validation_patterns=[r"Architecture:", r"CPU\(s\):"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_memory_info",
                command="cat /proc/meminfo",
                category=CommandCategory.SYSTEM_INFO,
                description="Get detailed memory information",
                timeout_seconds=5,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=60,  # 1 minute
                validation_patterns=[r"MemTotal:", r"MemFree:"],
            )
        )

    def _register_system_monitoring_commands(self) -> None:
        """Register system monitoring commands."""

        self.register(
            CommandDefinition(
                name="get_system_metrics",
                command="top -bn1 | head -20 && iostat -x 1 1 && free -m",
                category=CommandCategory.SYSTEM_MONITORING,
                description="Get real-time system performance metrics",
                timeout_seconds=20,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=60,  # 1 minute
                validation_patterns=[r"load average", r"Device", r"Mem:"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_disk_usage",
                command="df -h && du -sh /var/log /tmp /home 2>/dev/null || true",
                category=CommandCategory.SYSTEM_MONITORING,
                description="Get disk usage statistics",
                timeout_seconds=15,
                cache_ttl_seconds=600,  # 10 minutes
                freshness_threshold_seconds=300,  # 5 minutes
                validation_patterns=[r"Filesystem", r"Size", r"Used"],
            )
        )

    def _register_container_commands(self) -> None:
        """Register Docker container management commands."""

        self.register(
            CommandDefinition(
                name="list_containers",
                command="docker ps -a --format 'table {{.ID}}\\t{{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}'",
                category=CommandCategory.CONTAINER_MANAGEMENT,
                description="List all Docker containers",
                timeout_seconds=10,
                cache_ttl_seconds=30,  # 30 seconds
                freshness_threshold_seconds=15,  # 15 seconds
                validation_patterns=[r"CONTAINER ID", r"NAMES", r"STATUS"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_container_stats",
                command="docker stats --no-stream --format 'table {{.Container}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.NetIO}}\\t{{.BlockIO}}'",
                category=CommandCategory.CONTAINER_MANAGEMENT,
                description="Get container resource usage statistics",
                timeout_seconds=15,
                cache_ttl_seconds=60,  # 1 minute
                freshness_threshold_seconds=30,  # 30 seconds
                validation_patterns=[r"CONTAINER", r"CPU %", r"MEM USAGE"],
            )
        )

        self.register(
            CommandDefinition(
                name="inspect_container",
                command="docker inspect {container_name}",
                category=CommandCategory.CONTAINER_MANAGEMENT,
                description="Get detailed container information",
                timeout_seconds=10,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=120,  # 2 minutes
                validation_patterns=[r'"Config":', r'"State":'],
            )
        )

        self.register(
            CommandDefinition(
                name="get_container_logs",
                command="docker logs --tail {tail_lines} {container_name}",
                category=CommandCategory.CONTAINER_MANAGEMENT,
                description="Get container logs",
                timeout_seconds=30,
                cache_ttl_seconds=60,  # 1 minute
                freshness_threshold_seconds=30,  # 30 seconds
            )
        )

    def _register_docker_compose_commands(self) -> None:
        """Register Docker Compose commands."""

        self.register(
            CommandDefinition(
                name="compose_ps",
                command="cd {compose_path} && docker compose ps --format 'table {{.Name}}\\t{{.Status}}\\t{{.Ports}}'",
                category=CommandCategory.DOCKER_COMPOSE,
                description="List Docker Compose services",
                timeout_seconds=15,
                cache_ttl_seconds=60,  # 1 minute
                freshness_threshold_seconds=30,  # 30 seconds
                validation_patterns=[r"NAME", r"STATUS"],
            )
        )

        self.register(
            CommandDefinition(
                name="compose_config",
                command="cd {compose_path} && docker compose config",
                category=CommandCategory.DOCKER_COMPOSE,
                description="Get Docker Compose configuration",
                timeout_seconds=10,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=180,  # 3 minutes
                validation_patterns=[r"version:", r"services:"],
            )
        )

    def _register_zfs_commands(self) -> None:
        """Register ZFS management commands."""

        self.register(
            CommandDefinition(
                name="list_zfs_pools",
                command="zpool list -H -o name,size,alloc,free,expandsz,frag,cap,dedup,health,altroot",
                category=CommandCategory.ZFS_MANAGEMENT,
                description="List ZFS pools with detailed information",
                timeout_seconds=15,
                cache_ttl_seconds=1800,  # 30 minutes
                freshness_threshold_seconds=600,  # 10 minutes
                validation_patterns=[r"\t"],  # Tab-separated output
            )
        )

        self.register(
            CommandDefinition(
                name="get_zfs_pool_status",
                command="zpool status {pool_name}",
                category=CommandCategory.ZFS_MANAGEMENT,
                description="Get detailed ZFS pool status",
                timeout_seconds=20,
                cache_ttl_seconds=600,  # 10 minutes
                freshness_threshold_seconds=300,  # 5 minutes
                validation_patterns=[r"pool:", r"state:", r"config:"],
            )
        )

        self.register(
            CommandDefinition(
                name="list_zfs_datasets",
                command="zfs list -H -o name,used,avail,refer,mountpoint",
                category=CommandCategory.ZFS_MANAGEMENT,
                description="List ZFS datasets",
                timeout_seconds=15,
                cache_ttl_seconds=600,  # 10 minutes
                freshness_threshold_seconds=300,  # 5 minutes
                validation_patterns=[r"\t"],  # Tab-separated output
            )
        )

        self.register(
            CommandDefinition(
                name="list_zfs_snapshots",
                command="zfs list -H -t snapshot -o name,used,refer,creation",
                category=CommandCategory.ZFS_MANAGEMENT,
                description="List ZFS snapshots",
                timeout_seconds=30,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=180,  # 3 minutes
                validation_patterns=[r"@"],  # Snapshots contain @ symbol
            )
        )

    def _register_drive_health_commands(self) -> None:
        """Register drive health monitoring commands."""

        self.register(
            CommandDefinition(
                name="get_drive_health",
                command='lsblk -J && smartctl --scan && for drive in $(lsblk -nd -o NAME | grep -E \'^(sd|nvme)\'); do echo "=== $drive ==="; smartctl -a /dev/$drive 2>/dev/null || echo "No SMART data available"; done',
                category=CommandCategory.DRIVE_HEALTH,
                description="Get comprehensive drive health information",
                timeout_seconds=60,
                cache_ttl_seconds=3600,  # 1 hour
                freshness_threshold_seconds=1800,  # 30 minutes
                validation_patterns=[r"blockdevices", r"SMART"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_smart_status",
                command="smartctl -H {device_path}",
                category=CommandCategory.DRIVE_HEALTH,
                description="Get SMART health status for specific drive",
                timeout_seconds=15,
                cache_ttl_seconds=1800,  # 30 minutes
                freshness_threshold_seconds=900,  # 15 minutes
                validation_patterns=[r"SMART overall-health"],
            )
        )

    def _register_network_commands(self) -> None:
        """Register network information commands."""

        self.register(
            CommandDefinition(
                name="get_network_interfaces",
                command="ip addr show && ip route show",
                category=CommandCategory.NETWORK_INFO,
                description="Get network interface and routing information",
                timeout_seconds=15,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=120,  # 2 minutes
                validation_patterns=[r"inet ", r"default via"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_network_stats",
                command="ss -tuln && netstat -i",
                category=CommandCategory.NETWORK_INFO,
                description="Get network connections and interface statistics",
                timeout_seconds=10,
                cache_ttl_seconds=60,  # 1 minute
                freshness_threshold_seconds=30,  # 30 seconds
                validation_patterns=[r"LISTEN", r"RX-OK"],
            )
        )

    def _register_process_commands(self) -> None:
        """Register process management commands."""

        self.register(
            CommandDefinition(
                name="list_processes",
                command="ps aux --sort=-%cpu | head -20",
                category=CommandCategory.PROCESS_MANAGEMENT,
                description="List top CPU-consuming processes",
                timeout_seconds=10,
                cache_ttl_seconds=60,  # 1 minute
                freshness_threshold_seconds=30,  # 30 seconds
                validation_patterns=[r"USER", r"PID", r"%CPU"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_process_tree",
                command="pstree -p",
                category=CommandCategory.PROCESS_MANAGEMENT,
                description="Get process tree",
                timeout_seconds=10,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=120,  # 2 minutes
                validation_patterns=[r"systemd\(1\)"],
            )
        )

    def _register_service_commands(self) -> None:
        """Register service management commands."""

        self.register(
            CommandDefinition(
                name="list_systemd_services",
                command="systemctl list-units --type=service --state=running --no-pager",
                category=CommandCategory.SERVICE_MANAGEMENT,
                description="List running systemd services",
                timeout_seconds=15,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=120,  # 2 minutes
                validation_patterns=[r"UNIT", r"LOAD", r"ACTIVE"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_service_status",
                command="systemctl status {service_name} --no-pager -l",
                category=CommandCategory.SERVICE_MANAGEMENT,
                description="Get detailed service status",
                timeout_seconds=10,
                cache_ttl_seconds=60,  # 1 minute
                freshness_threshold_seconds=30,  # 30 seconds
                validation_patterns=[r"Active:", r"Main PID:"],
            )
        )

    def _register_file_commands(self) -> None:
        """Register file operation commands."""

        self.register(
            CommandDefinition(
                name="read_file",
                command="cat {file_path}",
                category=CommandCategory.FILE_OPERATIONS,
                description="Read file contents",
                timeout_seconds=30,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=180,  # 3 minutes
            )
        )

        self.register(
            CommandDefinition(
                name="list_directory",
                command="ls -la {directory_path}",
                category=CommandCategory.FILE_OPERATIONS,
                description="List directory contents",
                timeout_seconds=10,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=120,  # 2 minutes
                validation_patterns=[r"total ", r"drwx"],
            )
        )

        self.register(
            CommandDefinition(
                name="find_files",
                command="find {search_path} -name '{pattern}' -type f -ls 2>/dev/null | head -100",
                category=CommandCategory.FILE_OPERATIONS,
                description="Find files matching pattern",
                timeout_seconds=30,
                cache_ttl_seconds=600,  # 10 minutes
                freshness_threshold_seconds=300,  # 5 minutes
            )
        )

    def _register_configuration_commands(self) -> None:
        """Register configuration management commands."""

        self.register(
            CommandDefinition(
                name="check_nginx_config",
                command="nginx -t",
                category=CommandCategory.CONFIGURATION,
                description="Check nginx configuration syntax",
                timeout_seconds=10,
                cache_ttl_seconds=600,  # 10 minutes
                freshness_threshold_seconds=300,  # 5 minutes
                validation_patterns=[r"syntax is ok", r"test is successful"],
                error_patterns=[r"syntax error", r"test failed"],
            )
        )

        self.register(
            CommandDefinition(
                name="get_nginx_sites",
                command="ls -la /etc/nginx/sites-enabled/ && ls -la /etc/nginx/conf.d/",
                category=CommandCategory.CONFIGURATION,
                description="List nginx site configurations",
                timeout_seconds=10,
                cache_ttl_seconds=1800,  # 30 minutes
                freshness_threshold_seconds=600,  # 10 minutes
                validation_patterns=[r"total ", r"->"],
            )
        )

    def _register_logs_commands(self) -> None:
        """Register log management commands."""

        self.register(
            CommandDefinition(
                name="get_system_logs",
                command="journalctl --no-pager -n {lines} --since '{since}' --output=json",
                category=CommandCategory.LOGS,
                description="Get systemd journal logs",
                timeout_seconds=30,
                cache_ttl_seconds=300,  # 5 minutes
                freshness_threshold_seconds=60,  # 1 minute
                validation_patterns=[r'"MESSAGE":', r'"TIMESTAMP":'],
            )
        )

        self.register(
            CommandDefinition(
                name="get_service_logs",
                command="journalctl --no-pager -u {service_name} -n {lines} --output=json",
                category=CommandCategory.LOGS,
                description="Get logs for specific service",
                timeout_seconds=20,
                cache_ttl_seconds=180,  # 3 minutes
                freshness_threshold_seconds=60,  # 1 minute
                validation_patterns=[r'"MESSAGE":', r'"UNIT":'],
            )
        )

    def register(self, command: CommandDefinition) -> None:
        """Register a new command definition."""
        if command.name in self._commands:
            logger.warning(f"Overriding existing command: {command.name}")

        self._commands[command.name] = command

        # Add to category index
        if command.category not in self._categories:
            self._categories[command.category] = []

        if command.name not in self._categories[command.category]:
            self._categories[command.category].append(command.name)

        logger.debug(f"Registered command: {command.name} ({command.category})")

    def get_command(self, name: str) -> CommandDefinition | None:
        """Get command definition by name."""
        return self._commands.get(name)

    def get_commands_by_category(self, category: CommandCategory) -> list[CommandDefinition]:
        """Get all commands in a category."""
        command_names = self._categories.get(category, [])
        return [self._commands[name] for name in command_names if name in self._commands]

    def list_commands(self) -> list[str]:
        """List all registered command names."""
        return list(self._commands.keys())

    def list_categories(self) -> list[CommandCategory]:
        """List all command categories."""
        return list(self._categories.keys())

    def get_command_count(self) -> int:
        """Get total number of registered commands."""
        return len(self._commands)

    def get_category_count(self, category: CommandCategory) -> int:
        """Get number of commands in a category."""
        return len(self._categories.get(category, []))

    def format_command(self, name: str, **kwargs) -> str | None:
        """Format command with parameters."""
        command_def = self.get_command(name)
        if not command_def:
            return None

        try:
            return command_def.command.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing parameter for command {name}: {e}")
            return None

    def validate_command_output(self, name: str, output: str) -> bool:
        """Validate command output against expected patterns."""
        command_def = self.get_command(name)
        if not command_def or not command_def.validation_patterns:
            return True  # No validation patterns defined

        import re

        for pattern in command_def.validation_patterns:
            if not re.search(pattern, output):
                logger.warning(f"Command {name} output failed validation pattern: {pattern}")
                return False

        return True

    def check_for_errors(self, name: str, output: str) -> list[str]:
        """Check command output for known error patterns."""
        command_def = self.get_command(name)
        if not command_def or not command_def.error_patterns:
            return []

        import re

        errors = []
        for pattern in command_def.error_patterns:
            matches = re.findall(pattern, output)
            if matches:
                errors.extend(matches)

        return errors


# Global singleton instance
_command_registry: CommandRegistry | None = None


def get_command_registry() -> CommandRegistry:
    """Get the global command registry instance."""
    global _command_registry

    if _command_registry is None:
        _command_registry = CommandRegistry()

    return _command_registry
