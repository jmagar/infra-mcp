"""
Environment Detection Utilities

Provides utilities for detecting different system environments and their capabilities.
"""

import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Environment detection commands
WSL_DETECTION_COMMAND = (
    "grep -q microsoft /proc/version 2>/dev/null && echo 'WSL' || echo 'NOT_WSL'"
)
CONTAINER_DETECTION_COMMAND = "[ -f /.dockerenv ] && echo 'CONTAINER' || echo 'NOT_CONTAINER'"
SYSTEMD_DETECTION_COMMAND = (
    "systemctl is-system-running >/dev/null 2>&1 && echo 'SYSTEMD' || echo 'NOT_SYSTEMD'"
)


@dataclass
class EnvironmentInfo:
    """Information about the detected environment"""

    is_wsl: bool = False
    is_container: bool = False
    has_systemd: bool = False
    detected_os: Optional[str] = None

    @property
    def supports_drive_health(self) -> bool:
        """Check if environment supports drive health monitoring"""
        # WSL and containers typically don't support physical drive access
        return not (self.is_wsl or self.is_container)

    @property
    def supports_systemd(self) -> bool:
        """Check if environment supports systemd operations"""
        return self.has_systemd and not self.is_container


class EnvironmentDetector:
    """Utility class for detecting system environment characteristics"""

    @staticmethod
    def is_wsl_environment(proc_version_content: str) -> bool:
        """
        Detect if running in WSL environment based on /proc/version content

        Args:
            proc_version_content: Content of /proc/version file

        Returns:
            True if WSL environment detected
        """
        if not proc_version_content:
            return False

        # WSL typically has "microsoft" or "Microsoft" in /proc/version
        return "microsoft" in proc_version_content.lower()

    @staticmethod
    def is_container_environment(
        dockerenv_exists: bool = None, proc_cgroup_content: str = None
    ) -> bool:
        """
        Detect if running in a container environment

        Args:
            dockerenv_exists: Whether /.dockerenv file exists
            proc_cgroup_content: Content of /proc/1/cgroup file

        Returns:
            True if container environment detected
        """
        # Check for Docker environment file
        if dockerenv_exists:
            return True

        # Check cgroup for container indicators
        if proc_cgroup_content:
            container_indicators = ["docker", "lxc", "kubepods", "containerd"]
            content_lower = proc_cgroup_content.lower()
            return any(indicator in content_lower for indicator in container_indicators)

        return False

    @staticmethod
    def get_detection_commands() -> dict:
        """
        Get all environment detection commands

        Returns:
            Dictionary of detection commands by type
        """
        return {
            "wsl": WSL_DETECTION_COMMAND,
            "container": CONTAINER_DETECTION_COMMAND,
            "systemd": SYSTEMD_DETECTION_COMMAND,
        }


def should_skip_drive_health_monitoring(environment_info: EnvironmentInfo) -> bool:
    """
    Determine if drive health monitoring should be skipped based on environment

    Args:
        environment_info: Detected environment information

    Returns:
        True if drive health monitoring should be skipped
    """
    if environment_info.is_wsl:
        logger.debug("Skipping drive health monitoring: WSL environment detected")
        return True

    if environment_info.is_container:
        logger.debug("Skipping drive health monitoring: Container environment detected")
        return True

    return False


def get_environment_specific_commands(environment_info: EnvironmentInfo) -> dict:
    """
    Get environment-specific command variations

    Args:
        environment_info: Detected environment information

    Returns:
        Dictionary of adjusted commands for the environment
    """
    commands = {}

    # Adjust commands based on environment
    if environment_info.is_wsl:
        # WSL-specific command adjustments
        commands["drive_list"] = "lsblk -dno NAME,SIZE 2>/dev/null || echo 'No drives available'"
        commands["memory_info"] = "free -h"

    elif environment_info.is_container:
        # Container-specific command adjustments
        commands["drive_list"] = "df -h /"
        commands["memory_info"] = "cat /proc/meminfo"

    else:
        # Standard Linux commands
        commands["drive_list"] = "lsblk -dno NAME,SIZE | grep -E '^[s|n|h]d[a-z]|^nvme[0-9]'"
        commands["memory_info"] = "free -h"

    return commands
