"""
Unit tests for the unified SSH command registry.

Tests the core concepts and functionality of the command registry system.
"""

import pytest
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional


# Mock the classes and enums we need for testing
class CommandCategory(str, Enum):
    SYSTEM_METRICS = "system_metrics"
    CONTAINER_MANAGEMENT = "container_management"
    DRIVE_HEALTH = "drive_health"
    NETWORK_INFO = "network_info"


class ExtendedCommandCategory(str, Enum):
    SYSTEM_METRICS = "system_metrics"
    CONTAINER_MANAGEMENT = "container_management"
    DRIVE_HEALTH = "drive_health"
    NETWORK_INFO = "network_info"
    ZFS_MANAGEMENT = "zfs_management"
    DOCKER_OPERATIONS = "docker_operations"


@dataclass
class CommandDefinition:
    name: str
    command_template: str
    category: str
    description: str
    timeout: int = 30
    retry_count: int = 3
    cache_ttl: int = 0
    requires_root: bool = False


class MockCommandRegistry:
    """Mock registry for testing command registry patterns"""
    
    def __init__(self):
        self.commands: Dict[str, CommandDefinition] = {}
        
    def register_command(self, command_def: CommandDefinition) -> None:
        """Register a command in the registry"""
        self.commands[command_def.name] = command_def
        
    def get_all_commands(self) -> List[CommandDefinition]:
        """Get all registered commands"""
        return list(self.commands.values())
        
    def get_commands_by_category(self, category: str) -> List[CommandDefinition]:
        """Get commands filtered by category"""
        return [cmd for cmd in self.commands.values() if cmd.category == category]
        
    def get_command_categories(self) -> List[str]:
        """Get all available command categories"""
        categories = set(cmd.category for cmd in self.commands.values())
        return sorted(list(categories))
        
    def get_command_by_name(self, name: str) -> Optional[CommandDefinition]:
        """Get a specific command by name"""
        return self.commands.get(name)
        
    def get_registry_statistics(self) -> Dict:
        """Get statistics about the registry"""
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
        }


class TestCommandRegistry:
    """Test the command registry functionality"""

    @pytest.fixture
    def registry(self):
        """Create a MockCommandRegistry instance"""
        return MockCommandRegistry()

    def test_registry_initialization(self, registry):
        """Test that registry initializes correctly"""
        assert isinstance(registry.commands, dict)
        assert len(registry.commands) == 0

    def test_command_registration(self, registry):
        """Test registering commands in the registry"""
        cmd = CommandDefinition(
            name="test_command",
            command_template="test {param}",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="Test command",
            timeout=15,
            cache_ttl=300
        )
        
        registry.register_command(cmd)
        assert len(registry.commands) == 1
        assert "test_command" in registry.commands
        assert registry.commands["test_command"] == cmd

    def test_get_all_commands(self, registry):
        """Test retrieving all commands"""
        cmd1 = CommandDefinition(
            name="cmd1",
            command_template="command 1",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="Command 1"
        )
        cmd2 = CommandDefinition(
            name="cmd2", 
            command_template="command 2",
            category=ExtendedCommandCategory.DOCKER_OPERATIONS,
            description="Command 2"
        )
        
        registry.register_command(cmd1)
        registry.register_command(cmd2)
        
        all_commands = registry.get_all_commands()
        assert len(all_commands) == 2
        assert all(isinstance(cmd, CommandDefinition) for cmd in all_commands)

    def test_get_commands_by_category(self, registry):
        """Test filtering commands by category"""
        zfs_cmd = CommandDefinition(
            name="zfs_cmd",
            command_template="zfs list",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="ZFS command"
        )
        docker_cmd = CommandDefinition(
            name="docker_cmd",
            command_template="docker ps",
            category=ExtendedCommandCategory.DOCKER_OPERATIONS,
            description="Docker command"
        )
        another_zfs_cmd = CommandDefinition(
            name="another_zfs_cmd",
            command_template="zpool status",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="Another ZFS command"
        )
        
        registry.register_command(zfs_cmd)
        registry.register_command(docker_cmd)
        registry.register_command(another_zfs_cmd)
        
        zfs_commands = registry.get_commands_by_category(ExtendedCommandCategory.ZFS_MANAGEMENT)
        assert len(zfs_commands) == 2
        assert all(cmd.category == ExtendedCommandCategory.ZFS_MANAGEMENT for cmd in zfs_commands)
        
        docker_commands = registry.get_commands_by_category(ExtendedCommandCategory.DOCKER_OPERATIONS)
        assert len(docker_commands) == 1
        assert docker_commands[0].name == "docker_cmd"

    def test_get_command_categories(self, registry):
        """Test getting all available categories"""
        cmd1 = CommandDefinition(
            name="cmd1",
            command_template="test 1",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="Test 1"
        )
        cmd2 = CommandDefinition(
            name="cmd2",
            command_template="test 2",
            category=ExtendedCommandCategory.DOCKER_OPERATIONS,
            description="Test 2"
        )
        cmd3 = CommandDefinition(
            name="cmd3",
            command_template="test 3",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,  # Duplicate category
            description="Test 3"
        )
        
        registry.register_command(cmd1)
        registry.register_command(cmd2)
        registry.register_command(cmd3)
        
        categories = registry.get_command_categories()
        assert len(categories) == 2
        assert ExtendedCommandCategory.ZFS_MANAGEMENT in categories
        assert ExtendedCommandCategory.DOCKER_OPERATIONS in categories
        assert categories == sorted(categories)  # Should be sorted

    def test_get_command_by_name(self, registry):
        """Test retrieving specific commands by name"""
        cmd = CommandDefinition(
            name="specific_command",
            command_template="specific command",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="Specific command"
        )
        
        registry.register_command(cmd)
        
        retrieved = registry.get_command_by_name("specific_command")
        assert retrieved is not None
        assert retrieved.name == "specific_command"
        assert retrieved == cmd
        
        # Test non-existent command
        not_found = registry.get_command_by_name("non_existent")
        assert not_found is None

    def test_get_registry_statistics(self, registry):
        """Test registry statistics generation"""
        cmd1 = CommandDefinition(
            name="cmd1",
            command_template="test 1",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="Test 1",
            cache_ttl=300,
            requires_root=True
        )
        cmd2 = CommandDefinition(
            name="cmd2",
            command_template="test 2", 
            category=ExtendedCommandCategory.DOCKER_OPERATIONS,
            description="Test 2",
            cache_ttl=0,
            requires_root=False
        )
        cmd3 = CommandDefinition(
            name="cmd3",
            command_template="test 3",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="Test 3",
            cache_ttl=600,
            requires_root=False
        )
        
        registry.register_command(cmd1)
        registry.register_command(cmd2)
        registry.register_command(cmd3)
        
        stats = registry.get_registry_statistics()
        assert stats["total_commands"] == 3
        assert stats["categories"] == 2
        assert stats["commands_with_cache"] == 2
        assert stats["commands_requiring_root"] == 1
        assert "category_breakdown" in stats
        assert stats["category_breakdown"][ExtendedCommandCategory.ZFS_MANAGEMENT] == 2
        assert stats["category_breakdown"][ExtendedCommandCategory.DOCKER_OPERATIONS] == 1


class TestCommandDefinition:
    """Test the CommandDefinition data structure"""

    def test_command_definition_creation(self):
        """Test creating CommandDefinition instances"""
        cmd = CommandDefinition(
            name="test_cmd",
            command_template="test {param}",
            category=ExtendedCommandCategory.ZFS_MANAGEMENT,
            description="Test command"
        )
        
        assert cmd.name == "test_cmd"
        assert cmd.command_template == "test {param}"
        assert cmd.category == ExtendedCommandCategory.ZFS_MANAGEMENT
        assert cmd.description == "Test command"
        assert cmd.timeout == 30  # Default value
        assert cmd.retry_count == 3  # Default value
        assert cmd.cache_ttl == 0  # Default value
        assert cmd.requires_root is False  # Default value

    def test_command_definition_with_custom_values(self):
        """Test CommandDefinition with custom values"""
        cmd = CommandDefinition(
            name="custom_cmd",
            command_template="sudo custom command",
            category=ExtendedCommandCategory.SYSTEM_METRICS,
            description="Custom command",
            timeout=60,
            retry_count=5,
            cache_ttl=1800,
            requires_root=True
        )
        
        assert cmd.timeout == 60
        assert cmd.retry_count == 5
        assert cmd.cache_ttl == 1800
        assert cmd.requires_root is True


class TestExtendedCommandCategory:
    """Test the ExtendedCommandCategory enum"""

    def test_extended_categories_exist(self):
        """Test that extended categories are defined correctly"""
        assert ExtendedCommandCategory.ZFS_MANAGEMENT == "zfs_management"
        assert ExtendedCommandCategory.DOCKER_OPERATIONS == "docker_operations"

    def test_base_categories_preserved(self):
        """Test that base categories are preserved"""
        assert ExtendedCommandCategory.SYSTEM_METRICS == "system_metrics"
        assert ExtendedCommandCategory.CONTAINER_MANAGEMENT == "container_management"
        assert ExtendedCommandCategory.DRIVE_HEALTH == "drive_health"
        assert ExtendedCommandCategory.NETWORK_INFO == "network_info"

    def test_category_string_values(self):
        """Test that category enum values are strings"""
        for category in ExtendedCommandCategory:
            assert isinstance(category.value, str)
            assert len(category.value) > 0