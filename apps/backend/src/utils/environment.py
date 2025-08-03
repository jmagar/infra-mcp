"""
Environment Detection Utilities

Provides utilities for detecting different system environments and their capabilities.
"""

import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Environment detection commands as argument lists for safe execution
WSL_DETECTION_COMMAND = {
    "check_file": ["cat", "/proc/version"],
    "condition": "contains_microsoft"
}
CONTAINER_DETECTION_COMMAND = {
    "check_file": ["test", "-f", "/.dockerenv"],
    "condition": "file_exists"
}
SYSTEMD_DETECTION_COMMAND = {
    "check_command": ["systemctl", "is-system-running"],
    "condition": "exit_code_zero"
}


@dataclass
class EnvironmentInfo:
    """Information about the detected environment"""

    is_wsl: bool = False
    is_container: bool = False
    has_systemd: bool = False
    detected_os: str | None = None

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
    Get environment-specific command variations as argument lists for safe execution

    Args:
        environment_info: Detected environment information

    Returns:
        Dictionary of adjusted commands for the environment as argument lists
    """
    commands = {}

    # Adjust commands based on environment
    if environment_info.is_wsl:
        # WSL-specific command adjustments
        # For complex commands with fallback, we need to handle them specially
        commands["drive_list"] = {
            "primary": ["lsblk", "-dno", "NAME,SIZE"],
            "fallback": ["echo", "No drives available"],
            "error_handling": "fallback_on_error"
        }
        commands["memory_info"] = ["free", "-h"]

    elif environment_info.is_container:
        # Container-specific command adjustments
        commands["drive_list"] = ["df", "-h", "/"]
        commands["memory_info"] = ["cat", "/proc/meminfo"]

    else:
        # Standard Linux commands
        # For piped commands, we'll need to handle them as separate processes
        commands["drive_list"] = {
            "primary": ["lsblk", "-dno", "NAME,SIZE"],
            "filter": {
                "command": ["grep", "-E", "^[s|n|h]d[a-z]|^nvme[0-9]"],
                "stdin_from_primary": True
            }
        }
        commands["memory_info"] = ["free", "-h"]

    return commands


def execute_safe_command(command_spec: list | dict, timeout: int = 10) -> tuple[bool, str, str]:
    """
    Safely execute a command specification without shell injection risks
    
    Args:
        command_spec: Either a list of command arguments or a dict with complex command structure
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        if isinstance(command_spec, list):
            # Simple command execution
            result = subprocess.run(
                command_spec,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
            
        elif isinstance(command_spec, dict):
            if "primary" in command_spec:
                # Handle complex command with potential piping or fallback
                try:
                    # Execute primary command
                    primary_result = subprocess.run(
                        command_spec["primary"],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    
                    if primary_result.returncode == 0:
                        stdout = primary_result.stdout
                        
                        # Handle filtering if specified
                        if "filter" in command_spec:
                            filter_spec = command_spec["filter"]
                            filter_result = subprocess.run(
                                filter_spec["command"],
                                input=stdout,
                                capture_output=True,
                                text=True,
                                timeout=timeout
                            )
                            if filter_result.returncode == 0:
                                return True, filter_result.stdout, filter_result.stderr
                            else:
                                return False, stdout, filter_result.stderr
                        
                        return True, stdout, primary_result.stderr
                    
                    elif "fallback" in command_spec and command_spec.get("error_handling") == "fallback_on_error":
                        # Execute fallback command
                        fallback_result = subprocess.run(
                            command_spec["fallback"],
                            capture_output=True,
                            text=True,
                            timeout=timeout
                        )
                        return fallback_result.returncode == 0, fallback_result.stdout, fallback_result.stderr
                    
                    else:
                        return False, "", primary_result.stderr
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"Command timeout: {command_spec}")
                    return False, "", "Command timeout"
                    
            elif "check_file" in command_spec or "check_command" in command_spec:
                # Handle detection command
                cmd = command_spec.get("check_file") or command_spec.get("check_command")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return result.returncode == 0, result.stdout, result.stderr
                
    except subprocess.SubprocessError as e:
        logger.error(f"Command execution error: {e}")
        return False, "", str(e)
    except Exception as e:
        logger.error(f"Unexpected error executing command: {e}")
        return False, "", str(e)
    
    return False, "", "Invalid command specification"
