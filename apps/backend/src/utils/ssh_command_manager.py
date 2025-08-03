"""
SSH Command Manager

Enhanced SSH command execution with registry pattern, robust parsing,
retry logic, and result caching. Improves reliability of SSH operations
in the infrastructure monitoring system.
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union, Callable
from datetime import datetime, timedelta, timezone

from apps.backend.src.utils.ssh_client import SSHClient, SSHConnectionInfo, SSHExecutionResult
from apps.backend.src.core.exceptions import SSHCommandError, SSHConnectionError

logger = logging.getLogger(__name__)


class CommandCategory(str, Enum):
    """Categories for SSH command organization"""
    SYSTEM_METRICS = "system_metrics"
    CONTAINER_MANAGEMENT = "container_management"
    DRIVE_HEALTH = "drive_health"
    NETWORK_INFO = "network_info"
    PROCESS_INFO = "process_info"
    FILE_OPERATIONS = "file_operations"


@dataclass
class CommandDefinition:
    """Definition of an SSH command with metadata and parsing logic"""
    
    name: str
    command_template: str
    category: CommandCategory
    description: str
    timeout: int = 30
    retry_count: int = 3
    cache_ttl: int = 0  # Cache TTL in seconds, 0 = no cache
    parser: Callable[[str], Any] | None = None
    validator: Callable[[str], bool] | None = None
    requires_root: bool = False
    environment_vars: dict[str, str] = field(default_factory=dict)


@dataclass
class CachedResult:
    """Cached command execution result"""
    
    result: Any
    timestamp: datetime
    ttl: int
    command_hash: str
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl <= 0:
            return True
        return datetime.now(timezone.utc) > self.timestamp + timedelta(seconds=self.ttl)


class CommandParser(ABC):
    """Abstract base class for command result parsers"""
    
    @abstractmethod
    def parse(self, output: str) -> Any:
        """Parse command output into structured data"""
        pass
    
    @abstractmethod
    def validate(self, output: str) -> bool:
        """Validate command output format"""
        pass


class SystemMetricsParser(CommandParser):
    """Parser for system metrics commands"""
    
    def parse(self, output: str) -> dict[str, Any]:
        """Parse system metrics output"""
        try:
            lines = output.strip().split('\n')
            if len(lines) < 5:
                raise ValueError("Insufficient system metrics data")
            
            return {
                "cpu_usage": float(lines[0]) if lines[0] else 0.0,
                "memory_usage": float(lines[1]) if lines[1] else 0.0,
                "disk_usage": float(lines[2]) if lines[2] else 0.0,
                "load_avg": lines[3].split() if lines[3] else ["0", "0", "0"],
                "uptime": float(lines[4]) if lines[4] else 0.0
            }
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse system metrics: {e}")
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "load_avg": ["0", "0", "0"],
                "uptime": 0.0
            }
    
    def validate(self, output: str) -> bool:
        """Validate system metrics output"""
        lines = output.strip().split('\n')
        return len(lines) >= 5


class ContainerStatsParser(CommandParser):
    """Parser for Docker container statistics"""
    
    def parse(self, output: str) -> list[dict[str, Any]]:
        """Parse Docker container stats JSON output"""
        try:
            containers = []
            for line in output.strip().split('\n'):
                if line.strip():
                    try:
                        container_data = json.loads(line)
                        containers.append(container_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse container stats line: {e}")
                        logger.error(f"Problematic line: {repr(line)}")
                        logger.error(f"Line length: {len(line)}, First 50 chars: {repr(line[:50])}")
                        # Skip this line and continue with others
                        continue
            return containers
        except Exception as e:
            logger.error(f"Failed to parse container stats output: {e}")
            logger.debug(f"Raw output: {repr(output)}")
            return []
    
    def validate(self, output: str) -> bool:
        """Validate container stats JSON format"""
        try:
            for line in output.strip().split('\n'):
                if line.strip():
                    json.loads(line)
            return True
        except json.JSONDecodeError:
            return False


class DriveHealthParser(CommandParser):
    """Parser for drive health and SMART data"""
    
    def parse(self, output: str) -> list[dict[str, Any]]:
        """Parse drive listing and SMART data"""
        try:
            drives = []
            lines = output.strip().split('\n')
            
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        drives.append({
                            "name": parts[0],
                            "size": parts[1],
                            "available": True
                        })
            
            return drives
        except Exception as e:
            logger.error(f"Failed to parse drive health: {e}")
            return []
    
    def validate(self, output: str) -> bool:
        """Validate drive health output format"""
        lines = output.strip().split('\n')
        return len(lines) > 0 and all(len(line.split()) >= 2 for line in lines if line.strip())


class SSHCommandManager:
    """Enhanced SSH command manager with registry, caching, and retry logic"""
    
    def __init__(self, ssh_client: SSHClient):
        self.ssh_client = ssh_client
        self.command_registry: dict[str, CommandDefinition] = {}
        self.cache: dict[str, CachedResult] = {}
        self.parsers: dict[CommandCategory, CommandParser] = {
            CommandCategory.SYSTEM_METRICS: SystemMetricsParser(),
            CommandCategory.CONTAINER_MANAGEMENT: ContainerStatsParser(),
            CommandCategory.DRIVE_HEALTH: DriveHealthParser(),
        }
        self._register_default_commands()
    
    def _register_default_commands(self) -> None:
        """Register default SSH commands"""
        
        # System metrics command
        self.register_command(CommandDefinition(
            name="system_metrics",
            command_template=(
                "echo $(top -bn1 | grep 'Cpu(s)' | awk '{{print $2}}' | sed 's/%us,//'); "
                "echo $(free | grep Mem | awk '{{printf \"%.2f\", ($3/$2) * 100.0}}'); "
                "echo $(df -h / | awk 'NR==2{{print $5}}' | sed 's/%//'); "
                "echo $(cat /proc/loadavg | awk '{{print $1, $2, $3}}'); "
                "echo $(cat /proc/uptime | awk '{{print $1}}')"
            ),
            category=CommandCategory.SYSTEM_METRICS,
            description="Collect comprehensive system metrics",
            timeout=15,
            cache_ttl=60,
            parser=self.parsers[CommandCategory.SYSTEM_METRICS].parse
        ))
        
        # Container listing command
        self.register_command(CommandDefinition(
            name="list_containers",
            command_template="docker ps -a --format '{{{{json .}}}}'",
            category=CommandCategory.CONTAINER_MANAGEMENT,
            description="List all Docker containers with JSON output",
            timeout=10,
            cache_ttl=30,
            parser=self.parsers[CommandCategory.CONTAINER_MANAGEMENT].parse
        ))
        
        # Drive health command
        self.register_command(CommandDefinition(
            name="list_drives",
            command_template="lsblk -dno NAME,SIZE | grep -E '^[s|n|h]d[a-z]|^nvme[0-9]'",
            category=CommandCategory.DRIVE_HEALTH,
            description="List available storage drives",
            timeout=10,
            cache_ttl=300,
            parser=self.parsers[CommandCategory.DRIVE_HEALTH].parse
        ))
        
        # Network interface information
        self.register_command(CommandDefinition(
            name="network_interfaces",
            command_template="ip -j addr show",
            category=CommandCategory.NETWORK_INFO,
            description="Get network interface information in JSON format",
            timeout=10,
            cache_ttl=120
        ))
        
        # Memory information
        self.register_command(CommandDefinition(
            name="memory_info",
            command_template="free -b | grep Mem",
            category=CommandCategory.SYSTEM_METRICS,
            description="Get detailed memory information",
            timeout=5,
            cache_ttl=60
        ))
        
        # Docker container stats
        self.register_command(CommandDefinition(
            name="container_stats",
            command_template="docker stats --no-stream --format '{{{{json .}}}}' {container_id}",
            category=CommandCategory.CONTAINER_MANAGEMENT,
            description="Get real-time stats for specific container",
            timeout=15,
            cache_ttl=10
        ))
    
    def register_command(self, command_def: CommandDefinition) -> None:
        """Register a new command definition"""
        self.command_registry[command_def.name] = command_def
        logger.debug(f"Registered SSH command: {command_def.name}")
    
    def get_command(self, name: str) -> Optional[CommandDefinition]:
        """Get command definition by name"""
        return self.command_registry.get(name)
    
    def list_commands(self, category: Optional[CommandCategory] = None) -> list[CommandDefinition]:
        """List all registered commands, optionally filtered by category"""
        commands = list(self.command_registry.values())
        if category:
            commands = [cmd for cmd in commands if cmd.category == category]
        return commands
    
    def _generate_cache_key(self, command: str, connection_info: SSHConnectionInfo) -> str:
        """Generate cache key for command and connection"""
        key_data = f"{connection_info.host}:{connection_info.port}:{command}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available and not expired"""
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if not cached.is_expired:
                logger.debug(f"Using cached result for key: {cache_key}")
                return cached.result
            else:
                # Remove expired cache entry
                del self.cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Any, ttl: int) -> None:
        """Cache command result with TTL"""
        if ttl > 0:
            self.cache[cache_key] = CachedResult(
                result=result,
                timestamp=datetime.now(timezone.utc),
                ttl=ttl,
                command_hash=cache_key
            )
            logger.debug(f"Cached result for key: {cache_key}, TTL: {ttl}s")
    
    async def execute_command(
        self,
        command_name: str,
        connection_info: SSHConnectionInfo,
        parameters: Optional[dict[str, Any]] = None,
        force_refresh: bool = False
    ) -> Any:
        """
        Execute a registered command with enhanced error handling and caching
        
        Args:
            command_name: Name of registered command
            connection_info: SSH connection details
            parameters: Template parameters for command
            force_refresh: Skip cache and force command execution
            
        Returns:
            Parsed command result or raw output
        """
        command_def = self.get_command(command_name)
        if not command_def:
            raise SSHCommandError(
                f"Unknown command: {command_name}",
                command=command_name,
                hostname=connection_info.host
            )
        
        # Format command with parameters
        parameters = parameters or {}
        try:
            formatted_command = command_def.command_template.format(**parameters)
        except KeyError as e:
            raise SSHCommandError(
                f"Missing parameter for command {command_name}: {e}",
                command=command_def.command_template,
                hostname=connection_info.host
            )
        
        # Check cache first
        cache_key = self._generate_cache_key(formatted_command, connection_info)
        if not force_refresh and command_def.cache_ttl > 0:
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
        
        # Execute command with retry logic
        last_exception = None
        for attempt in range(command_def.retry_count):
            try:
                # Apply command-specific timeout
                connection_info_with_timeout = SSHConnectionInfo(
                    host=connection_info.host,
                    port=connection_info.port,
                    username=connection_info.username,
                    password=connection_info.password,
                    private_key_path=connection_info.private_key_path,
                    private_key_passphrase=connection_info.private_key_passphrase,
                    connect_timeout=connection_info.connect_timeout,
                    command_timeout=command_def.timeout,
                    max_retries=1  # We handle retries here
                )
                
                # Execute the command
                result = await self.ssh_client.execute_command(
                    connection_info_with_timeout,
                    formatted_command
                )
                
                # Validate output if validator exists
                if command_def.validator and not command_def.validator(result.stdout):
                    logger.warning(f"Command output validation failed for {command_name}")
                
                # Parse result if parser exists
                parsed_result = result.stdout
                if command_def.parser:
                    try:
                        parsed_result = command_def.parser(result.stdout)
                    except Exception as e:
                        logger.warning(f"Failed to parse command output for {command_name}: {e}")
                        # Return raw output if parsing fails
                        parsed_result = result.stdout
                
                # Cache successful result
                self._cache_result(cache_key, parsed_result, command_def.cache_ttl)
                
                logger.debug(f"Successfully executed command {command_name} on {connection_info.host}")
                return parsed_result
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Command execution failed (attempt {attempt + 1}/{command_def.retry_count}) "
                    f"for {command_name} on {connection_info.host}: {e}"
                )
                
                if attempt < command_def.retry_count - 1:
                    # Exponential backoff
                    delay = 2 ** attempt
                    await asyncio.sleep(delay)
        
        # All retries failed
        raise SSHCommandError(
            f"Command {command_name} failed after {command_def.retry_count} attempts: {last_exception}",
            command=formatted_command,
            hostname=connection_info.host
        ) from last_exception
    
    async def execute_raw_command(
        self,
        command: str,
        connection_info: SSHConnectionInfo,
        timeout: int = 30,
        retry_count: int = 1
    ) -> SSHExecutionResult:
        """Execute a raw command without registry (for ad-hoc operations)"""
        last_exception = None
        
        for attempt in range(retry_count):
            try:
                # Apply timeout parameter
                connection_info_with_timeout = SSHConnectionInfo(
                    host=connection_info.host,
                    port=connection_info.port,
                    username=connection_info.username,
                    password=connection_info.password,
                    private_key_path=connection_info.private_key_path,
                    private_key_passphrase=connection_info.private_key_passphrase,
                    connect_timeout=connection_info.connect_timeout,
                    command_timeout=timeout,
                    max_retries=1  # We handle retries here
                )
                
                result = await self.ssh_client.execute_command(connection_info_with_timeout, command)
                logger.debug(f"Successfully executed raw command on {connection_info.host}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Raw command execution failed (attempt {attempt + 1}/{retry_count}) "
                    f"on {connection_info.host}: {e}"
                )
                
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
        
        raise SSHCommandError(
            f"Raw command failed after {retry_count} attempts: {last_exception}",
            command=command,
            hostname=connection_info.host
        ) from last_exception
    
    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries
        
        Args:
            pattern: Optional pattern to match cache keys (contains match)
            
        Returns:
            Number of entries cleared
        """
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared all {count} cache entries")
            return count
        
        keys_to_remove = [key for key in self.cache if pattern in key]
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Cleared {len(keys_to_remove)} cache entries matching pattern: {pattern}")
        return len(keys_to_remove)
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.cache)
        expired_entries: int = sum(1 for cached in self.cache.values() if cached.is_expired)
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "cache_keys": list(self.cache.keys())
        }


# Global instance for easy access
_ssh_command_manager: Optional[SSHCommandManager] = None


def get_ssh_command_manager() -> SSHCommandManager:
    """Get or create global SSH command manager instance"""
    global _ssh_command_manager
    if _ssh_command_manager is None:
        from apps.backend.src.utils.ssh_client import get_ssh_client
        _ssh_command_manager = SSHCommandManager(get_ssh_client())
    return _ssh_command_manager
