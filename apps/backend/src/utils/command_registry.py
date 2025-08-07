"""
Unified SSH Command Registry

This module provides a comprehensive registry of all SSH commands used throughout
the infrastructure management system. It expands upon the existing SSHCommandManager
with a complete catalog of commands organized by categories.

Task Master Task 2: Implement Unified SSH Command Registry
"""

import json
import logging
from enum import Enum
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone

from .ssh_command_manager import (
    CommandDefinition,
    CommandCategory,
    SSHCommandManager,
    CommandParser,
    SystemMetricsParser,
    ContainerStatsParser,
    DriveHealthParser,
)

logger = logging.getLogger(__name__)


class ExtendedCommandCategory(str, Enum):
    """Extended categories for comprehensive SSH command organization"""
    # Existing categories from ssh_command_manager
    SYSTEM_METRICS = "system_metrics"
    CONTAINER_MANAGEMENT = "container_management"
    DRIVE_HEALTH = "drive_health"
    NETWORK_INFO = "network_info"
    PROCESS_INFO = "process_info"
    FILE_OPERATIONS = "file_operations"
    
    # New categories for comprehensive coverage
    ZFS_MANAGEMENT = "zfs_management"
    SYSTEM_LOGS = "system_logs"
    HARDWARE_INFO = "hardware_info"
    SYSTEM_STATUS = "system_status"
    DOCKER_OPERATIONS = "docker_operations"
    COMPOSE_MANAGEMENT = "compose_management"


class ZFSParser(CommandParser):
    """Parser for ZFS commands"""
    
    def parse(self, output: str) -> Any:
        """Parse ZFS command output"""
        lines = output.strip().split('\n')
        if not lines or not lines[0].strip():
            return []
            
        # Handle tabulated ZFS output
        results = []
        for line in lines:
            if line.strip() and '\t' in line:
                parts = line.split('\t')
                results.append(parts)
            elif line.strip():
                # Handle space-separated output
                results.append(line.split())
        
        return results
    
    def validate(self, output: str) -> bool:
        """Validate ZFS output format"""
        return len(output.strip()) > 0


class SystemInfoParser(CommandParser):
    """Parser for system information commands"""
    
    def parse(self, output: str) -> Dict[str, Any]:
        """Parse system info output into structured data"""
        try:
            lines = output.strip().split('\n')
            if not lines:
                return {}
                
            # Handle different system info formats
            result = {}
            for i, line in enumerate(lines):
                if line.strip():
                    result[f"line_{i}"] = line.strip()
            
            return result
        except Exception as e:
            logger.error(f"Failed to parse system info: {e}")
            return {"raw_output": output}
    
    def validate(self, output: str) -> bool:
        """Validate system info output"""
        return len(output.strip()) > 0


class UnifiedCommandRegistry:
    """
    Unified registry containing all SSH commands used throughout the infrastructure system.
    Extends SSHCommandManager with comprehensive command definitions.
    """
    
    def __init__(self, ssh_command_manager: SSHCommandManager):
        self.ssh_manager = ssh_command_manager
        # Create parser mappings including existing ones from ssh_command_manager
        self.parsers = {}
        
        # Copy existing parsers from ssh_command_manager (using string keys)
        for category_enum, parser in ssh_command_manager.parsers.items():
            self.parsers[category_enum] = parser
        
        # Add new extended parsers
        self.parsers[ExtendedCommandCategory.ZFS_MANAGEMENT] = ZFSParser()
        self.parsers[ExtendedCommandCategory.SYSTEM_LOGS] = SystemInfoParser()
        self.parsers[ExtendedCommandCategory.HARDWARE_INFO] = SystemInfoParser()
        self.parsers[ExtendedCommandCategory.SYSTEM_STATUS] = SystemInfoParser()
        self.parsers[ExtendedCommandCategory.DOCKER_OPERATIONS] = ContainerStatsParser()
        self.parsers[ExtendedCommandCategory.COMPOSE_MANAGEMENT] = SystemInfoParser()
        self.parsers[ExtendedCommandCategory.PROCESS_INFO] = SystemInfoParser()
        self.parsers[ExtendedCommandCategory.FILE_OPERATIONS] = SystemInfoParser()
        self._register_comprehensive_commands()
    
    def _get_parser_for_category(self, category: ExtendedCommandCategory):
        """Safely get parser for category, with fallback"""
        return self.parsers.get(category, self.parsers.get(ExtendedCommandCategory.SYSTEM_STATUS))
    
    def _register_comprehensive_commands(self) -> None:
        """Register all SSH commands discovered throughout the codebase"""
        
        # ZFS Management Commands
        zfs_commands = [
            CommandDefinition(
                name="zfs_list_pools",
                command_template="zpool list -H -o name,size,allocated,free,capacity,health,altroot",
                category=ExtendedCommandCategory.ZFS_MANAGEMENT,
                description="List all ZFS pools with detailed information",
                timeout=30,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.ZFS_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="zfs_pool_status",
                command_template="zpool status -v {pool_name}",
                category=ExtendedCommandCategory.ZFS_MANAGEMENT,
                description="Get detailed status for specific ZFS pool",
                timeout=30,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.ZFS_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="zfs_pool_properties",
                command_template="zpool get all {pool_name} -H -o property,value,source",
                category=ExtendedCommandCategory.ZFS_MANAGEMENT,
                description="Get all properties for a ZFS pool",
                timeout=20,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.ZFS_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="zfs_list_datasets",
                command_template="zfs list -H -o name,used,avail,refer,mountpoint,type",
                category=ExtendedCommandCategory.ZFS_MANAGEMENT,
                description="List all ZFS datasets",
                timeout=20,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.ZFS_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="zfs_list_snapshots",
                command_template="zfs list -t snapshot -H -o name,used,creation",
                category=ExtendedCommandCategory.ZFS_MANAGEMENT,
                description="List ZFS snapshots",
                timeout=30,
                cache_ttl=120,
                parser=self._get_parser_for_category(ExtendedCommandCategory.ZFS_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="zfs_dataset_properties",
                command_template="zfs get all {dataset_name} -H -o property,value,source",
                category=ExtendedCommandCategory.ZFS_MANAGEMENT,
                description="Get all properties for a ZFS dataset",
                timeout=15,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.ZFS_MANAGEMENT).parse
            ),
        ]
        
        # Docker Operations Commands
        docker_commands = [
            CommandDefinition(
                name="docker_version",
                command_template="docker --version",
                category=ExtendedCommandCategory.DOCKER_OPERATIONS,
                description="Get Docker version information",
                timeout=10,
                cache_ttl=3600,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DOCKER_OPERATIONS).parse
            ),
            CommandDefinition(
                name="docker_info",
                command_template="docker info --format json",
                category=ExtendedCommandCategory.DOCKER_OPERATIONS,
                description="Get Docker daemon information in JSON format",
                timeout=15,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DOCKER_OPERATIONS).parse
            ),
            CommandDefinition(
                name="docker_ps_ids",
                command_template="docker ps -q",
                category=ExtendedCommandCategory.DOCKER_OPERATIONS,
                description="Get Docker container IDs only",
                timeout=10,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DOCKER_OPERATIONS).parse
            ),
            CommandDefinition(
                name="docker_inspect_multiple",
                command_template="docker inspect {container_ids}",
                category=ExtendedCommandCategory.DOCKER_OPERATIONS,
                description="Inspect multiple Docker containers",
                timeout=20,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DOCKER_OPERATIONS).parse
            ),
            CommandDefinition(
                name="docker_ps_all_format",
                command_template="docker ps -a --format '{{{{json .}}}}'",
                category=ExtendedCommandCategory.DOCKER_OPERATIONS,
                description="List all containers with JSON format",
                timeout=15,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DOCKER_OPERATIONS).parse
            ),
            CommandDefinition(
                name="docker_images_count",
                command_template="docker images -q | wc -l",
                category=ExtendedCommandCategory.DOCKER_OPERATIONS,
                description="Count Docker images",
                timeout=10,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DOCKER_OPERATIONS).parse
            ),
            CommandDefinition(
                name="docker_container_status_summary",
                command_template="docker ps -a --format '{{.Status}}' | sort | uniq -c",
                category=ExtendedCommandCategory.DOCKER_OPERATIONS,
                description="Get container status summary",
                timeout=10,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DOCKER_OPERATIONS).parse
            ),
        ]
        
        # System Hardware Commands
        hardware_commands = [
            CommandDefinition(
                name="cpu_count",
                command_template="nproc",
                category=ExtendedCommandCategory.HARDWARE_INFO,
                description="Get number of CPU cores",
                timeout=5,
                cache_ttl=3600,
                parser=self._get_parser_for_category(ExtendedCommandCategory.HARDWARE_INFO).parse
            ),
            CommandDefinition(
                name="kernel_info",
                command_template="uname -a",
                category=ExtendedCommandCategory.HARDWARE_INFO,
                description="Get kernel and system information",
                timeout=5,
                cache_ttl=3600,
                parser=self._get_parser_for_category(ExtendedCommandCategory.HARDWARE_INFO).parse
            ),
            CommandDefinition(
                name="hardware_summary",
                command_template="lscpu | grep -E 'Model name|CPU\\(s\\)|Architecture'; free -h | grep 'Mem:'; lspci | grep -i vga; lspci | grep -i nvidia; df -h / | tail -1",
                category=ExtendedCommandCategory.HARDWARE_INFO,
                description="Get comprehensive hardware summary",
                timeout=15,
                cache_ttl=3600,
                parser=self._get_parser_for_category(ExtendedCommandCategory.HARDWARE_INFO).parse
            ),
            CommandDefinition(
                name="memory_info_detailed",
                command_template="cat /proc/meminfo",
                category=ExtendedCommandCategory.HARDWARE_INFO,
                description="Get detailed memory information from /proc/meminfo",
                timeout=5,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.HARDWARE_INFO).parse
            ),
            CommandDefinition(
                name="cpu_stats",
                command_template="cat /proc/stat | head -1",
                category=ExtendedCommandCategory.HARDWARE_INFO,
                description="Get CPU statistics from /proc/stat",
                timeout=5,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.HARDWARE_INFO).parse
            ),
            CommandDefinition(
                name="load_average",
                command_template="cat /proc/loadavg",
                category=ExtendedCommandCategory.HARDWARE_INFO,
                description="Get system load average",
                timeout=5,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.HARDWARE_INFO).parse
            ),
        ]
        
        # System Status Commands
        status_commands = [
            CommandDefinition(
                name="uptime_info",
                command_template="cat /proc/uptime",
                category=ExtendedCommandCategory.SYSTEM_STATUS,
                description="Get system uptime from /proc/uptime",
                timeout=5,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_STATUS).parse
            ),
            CommandDefinition(
                name="uptime_pretty",
                command_template="uptime -p",
                category=ExtendedCommandCategory.SYSTEM_STATUS,
                description="Get pretty formatted uptime",
                timeout=5,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_STATUS).parse
            ),
            CommandDefinition(
                name="process_count",
                command_template="ps aux | wc -l",
                category=ExtendedCommandCategory.PROCESS_INFO,
                description="Count total number of processes",
                timeout=10,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.PROCESS_INFO).parse
            ),
            CommandDefinition(
                name="top_cpu_processes",
                command_template="ps aux --sort=-%cpu | head -11",
                category=ExtendedCommandCategory.PROCESS_INFO,
                description="Get top 10 CPU-consuming processes",
                timeout=10,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.PROCESS_INFO).parse
            ),
        ]
        
        # Storage and Drive Commands
        storage_commands = [
            CommandDefinition(
                name="disk_list",
                command_template="lsblk -d -n -o NAME,TYPE | grep disk",
                category=ExtendedCommandCategory.DRIVE_HEALTH,
                description="List disk devices",
                timeout=10,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DRIVE_HEALTH).parse
            ),
            CommandDefinition(
                name="disk_info",
                command_template="lsblk {drive_path} -o NAME,SIZE,MODEL,SERIAL -n",
                category=ExtendedCommandCategory.DRIVE_HEALTH,
                description="Get detailed disk information",
                timeout=10,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DRIVE_HEALTH).parse
            ),
            CommandDefinition(
                name="smartctl_health",
                command_template="smartctl -H {drive_path}",
                category=ExtendedCommandCategory.DRIVE_HEALTH,
                description="Get SMART health status for drive",
                timeout=15,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DRIVE_HEALTH).parse
            ),
            CommandDefinition(
                name="smartctl_attributes",
                command_template="smartctl -A {drive_path}",
                category=ExtendedCommandCategory.DRIVE_HEALTH,
                description="Get SMART attributes for drive",
                timeout=20,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DRIVE_HEALTH).parse
            ),
            CommandDefinition(
                name="smartctl_full_sudo",
                command_template="sudo smartctl -a {drive_path}",
                category=ExtendedCommandCategory.DRIVE_HEALTH,
                description="Get full SMART data with sudo",
                timeout=25,
                cache_ttl=300,
                requires_root=True,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DRIVE_HEALTH).parse
            ),
            CommandDefinition(
                name="smartctl_graceful",
                command_template="sudo smartctl -a {drive_path} 2>/dev/null || smartctl -a {drive_path} 2>/dev/null || echo 'SMART_ACCESS_DENIED'",
                category=ExtendedCommandCategory.DRIVE_HEALTH,
                description="Get SMART data with graceful fallback",
                timeout=30,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DRIVE_HEALTH).parse
            ),
        ]
        
        # Filesystem Commands
        filesystem_commands = [
            CommandDefinition(
                name="filesystem_usage",
                command_template="df -h --output=source,size,used,avail,pcent,target | grep -E '^/dev/'",
                category=ExtendedCommandCategory.SYSTEM_STATUS,
                description="Get filesystem usage for device filesystems",
                timeout=10,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_STATUS).parse
            ),
            CommandDefinition(
                name="root_filesystem_usage",
                command_template="df -h / | tail -1",
                category=ExtendedCommandCategory.SYSTEM_STATUS,
                description="Get root filesystem usage",
                timeout=5,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_STATUS).parse
            ),
            CommandDefinition(
                name="disk_stats",
                command_template="cat /proc/diskstats",
                category=ExtendedCommandCategory.DRIVE_HEALTH,
                description="Get disk I/O statistics from /proc/diskstats",
                timeout=5,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DRIVE_HEALTH).parse
            ),
            CommandDefinition(
                name="inode_usage",
                command_template="df -i {mountpoint} | tail -1",
                category=ExtendedCommandCategory.SYSTEM_STATUS,
                description="Get inode usage for mountpoint",
                timeout=5,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_STATUS).parse
            ),
        ]
        
        # Network Commands
        network_commands = [
            CommandDefinition(
                name="network_interfaces_json",
                command_template="ip -j addr show",
                category=ExtendedCommandCategory.NETWORK_INFO,
                description="Get network interface information in JSON format",
                timeout=10,
                cache_ttl=120,
                parser=self._get_parser_for_category(ExtendedCommandCategory.NETWORK_INFO).parse
            ),
            CommandDefinition(
                name="network_ports_comprehensive",
                command_template="ss -tulpn",
                category=ExtendedCommandCategory.NETWORK_INFO,
                description="Get comprehensive network port information",
                timeout=15,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.NETWORK_INFO).parse
            ),
            CommandDefinition(
                name="network_dev_stats",
                command_template="cat /proc/net/dev",
                category=ExtendedCommandCategory.NETWORK_INFO,
                description="Get network device statistics from /proc/net/dev",
                timeout=5,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.NETWORK_INFO).parse
            ),
        ]
        
        # System Logs Commands
        logs_commands = [
            CommandDefinition(
                name="journalctl_recent",
                command_template="journalctl --no-pager -n {lines} --output=json",
                category=ExtendedCommandCategory.SYSTEM_LOGS,
                description="Get recent journal entries in JSON format",
                timeout=20,
                cache_ttl=0,  # Logs should not be cached
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_LOGS).parse
            ),
            CommandDefinition(
                name="journalctl_service",
                command_template="journalctl --no-pager -u {service} -n {lines} --output=json",
                category=ExtendedCommandCategory.SYSTEM_LOGS,
                description="Get journal entries for specific service",
                timeout=20,
                cache_ttl=0,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_LOGS).parse
            ),
            CommandDefinition(
                name="systemctl_status",
                command_template="systemctl status {service} --no-pager",
                category=ExtendedCommandCategory.SYSTEM_LOGS,
                description="Get systemctl status for service",
                timeout=15,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_LOGS).parse
            ),
        ]
        
        # Docker Compose Commands
        compose_commands = [
            CommandDefinition(
                name="find_compose_files",
                command_template="find /home /opt /srv -name 'docker-compose.yml' -o -name 'docker-compose.yaml' 2>/dev/null | head -10",
                category=ExtendedCommandCategory.COMPOSE_MANAGEMENT,
                description="Find Docker Compose files on system",
                timeout=30,
                cache_ttl=3600,
                parser=self._get_parser_for_category(ExtendedCommandCategory.COMPOSE_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="compose_stop",
                command_template="cd '{compose_dir}' && docker-compose -f '{compose_file}' stop {services}",
                category=ExtendedCommandCategory.COMPOSE_MANAGEMENT,
                description="Stop Docker Compose services",
                timeout=60,
                cache_ttl=0,
                parser=self._get_parser_for_category(ExtendedCommandCategory.COMPOSE_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="compose_pull",
                command_template="cd '{compose_dir}' && docker-compose -f '{compose_file}' pull",
                category=ExtendedCommandCategory.COMPOSE_MANAGEMENT,
                description="Pull Docker Compose images",
                timeout=300,
                cache_ttl=0,
                parser=self._get_parser_for_category(ExtendedCommandCategory.COMPOSE_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="compose_up",
                command_template="cd '{compose_dir}' && docker-compose -f '{compose_file}' up -d {recreate_flag} {services}",
                category=ExtendedCommandCategory.COMPOSE_MANAGEMENT,
                description="Start Docker Compose services",
                timeout=120,
                cache_ttl=0,
                parser=self._get_parser_for_category(ExtendedCommandCategory.COMPOSE_MANAGEMENT).parse
            ),
            CommandDefinition(
                name="compose_ps",
                command_template="cd '{compose_dir}' && docker-compose -f '{compose_file}' ps",
                category=ExtendedCommandCategory.COMPOSE_MANAGEMENT,
                description="Show Docker Compose service status",
                timeout=15,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.COMPOSE_MANAGEMENT).parse
            ),
        ]
        
        # Additional System Status Commands
        system_commands = [
            CommandDefinition(
                name="memory_usage_percentage",
                command_template="free | grep Mem | awk '{printf \"%.1f\", $3/$2 * 100.0}'",
                category=ExtendedCommandCategory.SYSTEM_STATUS,
                description="Get memory usage percentage",
                timeout=5,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_STATUS).parse
            ),
            CommandDefinition(
                name="disk_usage_percentage",
                command_template="df / | tail -1 | awk '{print $5}' | sed 's/%//'",
                category=ExtendedCommandCategory.SYSTEM_STATUS,
                description="Get root disk usage percentage",
                timeout=5,
                cache_ttl=60,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_STATUS).parse
            ),
            CommandDefinition(
                name="load_average_1min",
                command_template="uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//'",
                category=ExtendedCommandCategory.SYSTEM_STATUS,
                description="Get 1-minute load average",
                timeout=5,
                cache_ttl=30,
                parser=self._get_parser_for_category(ExtendedCommandCategory.SYSTEM_STATUS).parse
            ),
        ]
        
        # Special purpose commands
        special_commands = [
            CommandDefinition(
                name="swag_detection",
                command_template="docker ps --format '{{.Names}}' | grep -i swag; ls -la /mnt/appdata/swag/nginx/proxy-confs 2>/dev/null | wc -l || echo 'NO_SWAG_FOUND'",
                category=ExtendedCommandCategory.DOCKER_OPERATIONS,
                description="Detect SWAG reverse proxy configuration",
                timeout=15,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.DOCKER_OPERATIONS).parse
            ),
            CommandDefinition(
                name="zfs_comprehensive_check",
                command_template="zpool list -H -o name,size,alloc,free,health 2>/dev/null && echo '---SNAPSHOTS---' && zfs list -t snapshot -H -o name,used,creation 2>/dev/null | head -20 || echo 'ZFS_NOT_AVAILABLE'",
                category=ExtendedCommandCategory.ZFS_MANAGEMENT,
                description="Comprehensive ZFS availability and snapshot check",
                timeout=30,
                cache_ttl=300,
                parser=self._get_parser_for_category(ExtendedCommandCategory.ZFS_MANAGEMENT).parse
            ),
        ]
        
        # Register all command groups
        command_groups = [
            zfs_commands,
            docker_commands,
            hardware_commands,
            status_commands,
            storage_commands,
            filesystem_commands,
            network_commands,
            logs_commands,
            compose_commands,
            system_commands,
            special_commands,
        ]
        
        total_registered = 0
        for command_group in command_groups:
            for command_def in command_group:
                self.ssh_manager.register_command(command_def)
                total_registered += 1
        
        logger.info(f"Registered {total_registered} comprehensive SSH commands in unified registry")
    
    def get_all_commands(self) -> List[CommandDefinition]:
        """Get all registered commands from the unified registry"""
        return list(self.ssh_manager.command_registry.values())
    
    def get_commands_by_category(self, category: ExtendedCommandCategory) -> List[CommandDefinition]:
        """Get commands filtered by category"""
        return [
            cmd for cmd in self.get_all_commands() 
            if cmd.category == category
        ]
    
    def get_command_categories(self) -> List[str]:
        """Get all available command categories"""
        categories = set()
        for command in self.get_all_commands():
            categories.add(command.category)
        return sorted(list(categories))
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """Get statistics about the command registry"""
        all_commands = self.get_all_commands()
        category_counts = {}
        
        for command in all_commands:
            category = command.category
            if category not in category_counts:
                category_counts[category] = 0
            category_counts[category] += 1
        
        return {
            "total_commands": len(all_commands),
            "categories": len(category_counts),
            "category_breakdown": category_counts,
            "commands_with_cache": len([c for c in all_commands if c.cache_ttl > 0]),
            "commands_requiring_root": len([c for c in all_commands if c.requires_root]),
            "average_timeout": sum(c.timeout for c in all_commands) / len(all_commands),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def export_registry_json(self) -> str:
        """Export the entire registry as JSON for documentation"""
        registry_data = {
            "metadata": self.get_registry_statistics(),
            "commands": []
        }
        
        for command in self.get_all_commands():
            command_data = {
                "name": command.name,
                "command_template": command.command_template,
                "category": command.category,
                "description": command.description,
                "timeout": command.timeout,
                "retry_count": command.retry_count,
                "cache_ttl": command.cache_ttl,
                "requires_root": command.requires_root,
                "environment_vars": command.environment_vars,
                "has_parser": command.parser is not None,
                "has_validator": command.validator is not None,
            }
            registry_data["commands"].append(command_data)
        
        return json.dumps(registry_data, indent=2, ensure_ascii=False)


# Global unified registry instance
_unified_registry: Optional[UnifiedCommandRegistry] = None


def get_unified_command_registry() -> UnifiedCommandRegistry:
    """Get or create the global unified command registry instance"""
    global _unified_registry
    if _unified_registry is None:
        from .ssh_command_manager import get_ssh_command_manager
        ssh_manager = get_ssh_command_manager()
        _unified_registry = UnifiedCommandRegistry(ssh_manager)
    return _unified_registry


def get_command_by_name(name: str) -> Optional[CommandDefinition]:
    """Get a specific command by name from the unified registry"""
    registry = get_unified_command_registry()
    return registry.ssh_manager.get_command(name)


def list_all_commands() -> List[CommandDefinition]:
    """List all commands in the unified registry"""
    registry = get_unified_command_registry()
    return registry.get_all_commands()


def get_commands_by_category(category: ExtendedCommandCategory) -> List[CommandDefinition]:
    """Get commands by category from the unified registry"""
    registry = get_unified_command_registry()
    return registry.get_commands_by_category(category)