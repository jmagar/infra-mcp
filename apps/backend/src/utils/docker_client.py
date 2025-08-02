"""
Docker Command Execution Module for Infrastructure Management

This module provides a standardized interface for executing Docker CLI commands
over SSH connections with comprehensive error handling, JSON parsing, and
structured response formatting for all container management operations.
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable
from uuid import UUID

from apps.backend.src.utils.ssh_client import (
    SSHClient,
    SSHConnectionInfo,
    SSHExecutionResult,
    get_ssh_client,
)
from apps.backend.src.core.exceptions import (
    ContainerError,
    SSHConnectionError,
    SSHCommandError,
    DeviceNotFoundError,
)

logger = logging.getLogger(__name__)


class DockerCommandType(Enum):
    """Docker command types for categorized error handling"""

    LIST = "list"
    INSPECT = "inspect"
    LOGS = "logs"
    EXEC = "exec"
    NETWORK = "network"
    VOLUME = "volume"
    SYSTEM = "system"


@dataclass
class DockerExecutionResult:
    """Result of Docker command execution with parsed data"""

    command: str
    command_type: DockerCommandType
    raw_result: SSHExecutionResult
    parsed_data: Optional[Union[Dict, List]] = None
    error_category: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if command was successful"""
        return self.raw_result.success and self.error_category is None

    @property
    def error_message(self) -> Optional[str]:
        """Get formatted error message"""
        if self.raw_result.error_message:
            return self.raw_result.error_message
        if self.error_category:
            return f"Docker {self.command_type.value} error: {self.error_category}"
        return None


class DockerClient:
    """
    Docker CLI client for executing commands over SSH with standardized error handling
    and response parsing for infrastructure monitoring operations.
    """

    def __init__(self, ssh_client: Optional[SSHClient] = None):
        """
        Initialize Docker client.

        Args:
            ssh_client: Optional SSH client instance
        """
        self.ssh_client = ssh_client or get_ssh_client()

        # Docker command templates
        self._command_templates = {
            DockerCommandType.LIST: 'docker ps {flags} --format "{{{{json .}}}}"',
            DockerCommandType.INSPECT: "docker inspect {container_id}",
            DockerCommandType.LOGS: "docker logs {flags} {container_id}",
            DockerCommandType.NETWORK: 'docker network {subcommand} {flags} --format "{{{{json .}}}}"',
            DockerCommandType.VOLUME: 'docker volume {subcommand} {flags} --format "{{{{json .}}}}"',
            DockerCommandType.SYSTEM: 'docker system {subcommand} {flags} --format "{{{{json .}}}}"',
        }

        # Error pattern matching for categorization
        self._error_patterns = {
            "container_not_found": [
                r"No such container: (.+)",
                r"Error: No such container: (.+)",
                r"container (.+) not found",
            ],
            "docker_daemon_error": [
                r"Cannot connect to the Docker daemon",
                r"docker daemon not running",
                r"Is the docker daemon running\?",
            ],
            "permission_denied": [
                r"permission denied",
                r"Got permission denied while trying to connect",
            ],
            "invalid_container_id": [r"invalid container id", r"Error parsing reference"],
            "network_error": [r"network (.+) not found", r"No such network: (.+)"],
            "volume_error": [r"volume (.+) not found", r"No such volume: (.+)"],
        }

    def _categorize_error(self, stderr: str, command_type: DockerCommandType) -> Optional[str]:
        """
        Categorize Docker command errors based on stderr output.

        Args:
            stderr: Standard error output
            command_type: Type of Docker command that failed

        Returns:
            Error category string or None if no match
        """
        stderr_lower = stderr.lower()

        for category, patterns in self._error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, stderr_lower, re.IGNORECASE):
                    return category

        # Generic categorization based on command type
        if "not found" in stderr_lower:
            return f"{command_type.value}_not_found"
        elif "permission" in stderr_lower:
            return "permission_denied"
        elif "daemon" in stderr_lower:
            return "docker_daemon_error"

        return "unknown_docker_error"

    def _parse_json_output(
        self, output: str, command_type: DockerCommandType
    ) -> Optional[Union[Dict, List]]:
        """
        Parse output from Docker commands (JSON or custom format).

        Args:
            output: Raw output string
            command_type: Type of Docker command

        Returns:
            Parsed data or None if parsing fails
        """
        if not output or not output.strip():
            return None

        try:
            # Handle custom container format (docker inspect with --format)
            if command_type == DockerCommandType.LIST:
                containers = []
                # Split on '---' but handle the trailing separator
                container_blocks = [
                    block.strip() for block in output.strip().split("---") if block.strip()
                ]

                for block in container_blocks:
                    container = {}
                    lines = [line.strip() for line in block.split("\n") if line.strip()]

                    for line in lines:
                        if ":" in line:
                            key, value = line.split(":", 1)
                            field_name = key.strip().lower().replace(" ", "_")
                            field_value = value.strip()

                            # Map the custom format fields to expected container fields
                            if field_name == "name":
                                # Remove leading slash from container name
                                container["container_name"] = field_value.lstrip("/")
                            elif field_name == "image":
                                container["image"] = field_value
                            elif field_name == "status":
                                container["status"] = field_value
                                container["state"] = field_value
                                container["running"] = field_value.lower() == "running"
                            elif field_name == "networks":
                                container["networks"] = field_value.split() if field_value else []
                            elif field_name == "ports":
                                container["ports"] = field_value
                            elif field_name == "mounts":
                                container["mounts"] = field_value
                            elif field_name == "compose_path":
                                container["compose_path"] = field_value

                    if container:
                        containers.append(container)

                logger.info(f"Raw output length: {len(output)} chars")
                logger.info(f"Output preview: {output[:200]}...")
                logger.info(f"Container blocks found: {len(container_blocks)}")
                logger.info(f"Parsed {len(containers)} containers from custom format")
                if containers:
                    logger.info(f"First container: {containers[0]}")
                return containers

            # Handle regular JSON (docker inspect, system info, networks, volumes)
            else:
                return json.loads(output.strip())

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Docker output for {command_type.value}: {e}")
            logger.debug(f"Raw output: {output[:500]}...")
            return None

    def _build_command(self, command_type: DockerCommandType, flags: str = "", **kwargs) -> str:
        """
        Build Docker command avoiding string formatting issues with JSON templates.

        Args:
            command_type: Type of Docker command
            flags: Command flags
            **kwargs: Additional parameters for command template

        Returns:
            Formatted Docker command string
        """
        # Handle JSON format commands specially to avoid str.format() issues
        if command_type == DockerCommandType.LIST:
            # Use docker inspect with concise format for essential container info
            base_cmd = "docker inspect $(docker ps -aq) --format='Name: {{.Name}}\nImage: {{.Config.Image}}\nNetworks: {{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}\nPorts: {{.NetworkSettings.Ports}}\nMounts: {{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}\nCompose Path: {{index .Config.Labels \"com.docker.compose.project.working_dir\"}}\nStatus: {{.State.Status}}\n---'"
            return base_cmd

        elif command_type == DockerCommandType.NETWORK:
            # Build docker network command manually
            subcommand = kwargs.get("subcommand", "ls")
            base_cmd = f"docker network {subcommand}"
            if flags:
                base_cmd += f" {flags}"
            if subcommand == "ls":
                base_cmd += ' --format "{{json .}}"'
            return base_cmd

        elif command_type == DockerCommandType.VOLUME:
            # Build docker volume command manually
            subcommand = kwargs.get("subcommand", "ls")
            base_cmd = f"docker volume {subcommand}"
            if flags:
                base_cmd += f" {flags}"
            if subcommand == "ls":
                base_cmd += ' --format "{{json .}}"'
            return base_cmd

        elif command_type == DockerCommandType.SYSTEM:
            # Build docker system command manually
            subcommand = kwargs.get("subcommand", "info")
            base_cmd = f"docker system {subcommand}"
            if flags:
                base_cmd += f" {flags}"
            if subcommand in ["df", "events"]:
                base_cmd += ' --format "{{json .}}"'
            return base_cmd

        # For non-JSON commands, use traditional template approach
        template = self._command_templates.get(command_type)
        if not template:
            raise ValueError(f"No template defined for command type: {command_type}")

        # Build parameters
        params = {"flags": flags}
        params.update(kwargs)

        try:
            return template.format(**params)
        except KeyError as e:
            raise ValueError(f"Missing required parameter for {command_type.value} command: {e}")

    async def execute_docker_command(
        self,
        connection_info: SSHConnectionInfo,
        command_type: DockerCommandType,
        flags: str = "",
        timeout: Optional[int] = None,
        parse_json: bool = True,
        **kwargs,
    ) -> DockerExecutionResult:
        """
        Execute a Docker command with standardized error handling and parsing.

        Args:
            connection_info: SSH connection configuration
            command_type: Type of Docker command to execute
            flags: Command flags
            timeout: Command timeout in seconds
            parse_json: Whether to parse JSON output
            **kwargs: Additional parameters for command

        Returns:
            DockerExecutionResult with parsed data and error categorization
        """
        # Build the Docker command
        try:
            command = self._build_command(command_type, flags, **kwargs)
        except ValueError as e:
            # Return error result for invalid command construction
            dummy_result = SSHExecutionResult(
                command="invalid_docker_command",
                return_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=0.0,
                host=connection_info.host,
                success=False,
                error_message=str(e),
            )
            return DockerExecutionResult(
                command="invalid_docker_command",
                command_type=command_type,
                raw_result=dummy_result,
                error_category="invalid_command",
            )

        logger.debug(f"Executing Docker command on {connection_info.host}: {command}")
        logger.debug(f"Command type: {command_type.value}, Parse JSON: {parse_json}")

        try:
            # Execute the SSH command
            ssh_result = await self.ssh_client.execute_command(
                connection_info=connection_info,
                command=command,
                timeout=timeout,
                check=False,  # Don't raise on non-zero exit codes
            )

            # Create Docker result wrapper
            docker_result = DockerExecutionResult(
                command=command, command_type=command_type, raw_result=ssh_result
            )

            # Handle errors
            if not ssh_result.success:
                docker_result.error_category = self._categorize_error(
                    ssh_result.stderr, command_type
                )

                # Log specific error for debugging
                logger.error(
                    f"Docker {command_type.value} command failed on {connection_info.host}: "
                    f"{docker_result.error_category} - {ssh_result.stderr[:200]}"
                )

                return docker_result

            # Parse JSON output if requested and available
            if parse_json and ssh_result.stdout:
                # Debug: Log the raw stdout for troubleshooting
                logger.debug(f"Raw Docker stdout length: {len(ssh_result.stdout)} chars")
                logger.debug(f"Raw Docker stdout (first 200 chars): {ssh_result.stdout[:200]}")
                logger.debug(f"Stdout ends with: ...{ssh_result.stdout[-50:]}")

                docker_result.parsed_data = self._parse_json_output(ssh_result.stdout, command_type)

                if docker_result.parsed_data is None and ssh_result.stdout.strip():
                    docker_result.error_category = "json_parse_error"
                    logger.warning(f"Failed to parse JSON output for {command_type.value} command")
                    logger.warning(f"Raw stdout: {ssh_result.stdout[:500]}")
                else:
                    if isinstance(docker_result.parsed_data, list):
                        logger.debug(
                            f"Successfully parsed {len(docker_result.parsed_data)} JSON items"
                        )
                    else:
                        logger.debug(f"Successfully parsed JSON: {type(docker_result.parsed_data)}")

            logger.debug(
                f"Docker {command_type.value} command completed successfully on {connection_info.host}"
            )

            return docker_result

        except Exception as e:
            # Handle SSH connection/execution errors
            logger.error(f"SSH error executing Docker command on {connection_info.host}: {e}")

            # Create error result
            error_result = SSHExecutionResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=0.0,
                host=connection_info.host,
                success=False,
                error_message=str(e),
            )

            return DockerExecutionResult(
                command=command,
                command_type=command_type,
                raw_result=error_result,
                error_category="ssh_connection_error",
            )

    async def list_containers(
        self,
        connection_info: SSHConnectionInfo,
        all_containers: bool = True,
        timeout: Optional[int] = None,
    ) -> DockerExecutionResult:
        """
        List Docker containers on remote host.

        Args:
            connection_info: SSH connection configuration
            all_containers: Include stopped containers
            timeout: Command timeout in seconds

        Returns:
            DockerExecutionResult with list of container data
        """
        flags = "-a" if all_containers else ""
        return await self.execute_docker_command(
            connection_info=connection_info,
            command_type=DockerCommandType.LIST,
            flags=flags,
            timeout=timeout,
            parse_json=True,
        )

    async def inspect_container(
        self, connection_info: SSHConnectionInfo, container_id: str, timeout: Optional[int] = None
    ) -> DockerExecutionResult:
        """
        Inspect a specific Docker container.

        Args:
            connection_info: SSH connection configuration
            container_id: Container ID or name
            timeout: Command timeout in seconds

        Returns:
            DockerExecutionResult with container inspection data
        """
        return await self.execute_docker_command(
            connection_info=connection_info,
            command_type=DockerCommandType.INSPECT,
            container_id=container_id,
            timeout=timeout,
            parse_json=True,
        )

    async def get_container_logs(
        self,
        connection_info: SSHConnectionInfo,
        container_id: str,
        lines: int = 100,
        since: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> DockerExecutionResult:
        """
        Get logs from a Docker container.

        Args:
            connection_info: SSH connection configuration
            container_id: Container ID or name
            lines: Number of log lines to retrieve
            since: Get logs since timestamp/duration
            timeout: Command timeout in seconds

        Returns:
            DockerExecutionResult with container logs as raw text
        """
        flags_parts = [f"--tail {lines}"]
        if since:
            flags_parts.append(f"--since {since}")

        flags = " ".join(flags_parts)

        return await self.execute_docker_command(
            connection_info=connection_info,
            command_type=DockerCommandType.LOGS,
            flags=flags,
            container_id=container_id,
            timeout=timeout,
            parse_json=False,  # Logs are raw text
        )

    async def list_networks(
        self, connection_info: SSHConnectionInfo, timeout: Optional[int] = None
    ) -> DockerExecutionResult:
        """
        List Docker networks.

        Args:
            connection_info: SSH connection configuration
            timeout: Command timeout in seconds

        Returns:
            DockerExecutionResult with network list data
        """
        return await self.execute_docker_command(
            connection_info=connection_info,
            command_type=DockerCommandType.NETWORK,
            subcommand="ls",
            flags="",
            timeout=timeout,
            parse_json=True,
        )

    async def list_volumes(
        self, connection_info: SSHConnectionInfo, timeout: Optional[int] = None
    ) -> DockerExecutionResult:
        """
        List Docker volumes.

        Args:
            connection_info: SSH connection configuration
            timeout: Command timeout in seconds

        Returns:
            DockerExecutionResult with volume list data
        """
        return await self.execute_docker_command(
            connection_info=connection_info,
            command_type=DockerCommandType.VOLUME,
            subcommand="ls",
            flags="",
            timeout=timeout,
            parse_json=True,
        )

    async def get_system_info(
        self, connection_info: SSHConnectionInfo, timeout: Optional[int] = None
    ) -> DockerExecutionResult:
        """
        Get Docker system information.

        Args:
            connection_info: SSH connection configuration
            timeout: Command timeout in seconds

        Returns:
            DockerExecutionResult with system info data
        """
        return await self.execute_docker_command(
            connection_info=connection_info,
            command_type=DockerCommandType.SYSTEM,
            subcommand="info",
            flags="",
            timeout=timeout,
            parse_json=True,
        )

    def raise_docker_exception(self, result: DockerExecutionResult, operation: str):
        """
        Raise appropriate exception based on Docker execution result.

        Args:
            result: Docker execution result
            operation: Operation description for error message

        Raises:
            ContainerError: For Docker-specific errors
            SSHConnectionError: For SSH connectivity issues
            SSHCommandError: For SSH command execution errors
        """
        if not result.success:
            error_msg = result.error_message or f"Docker {operation} failed"

            # Determine appropriate exception type
            if result.error_category == "ssh_connection_error":
                raise SSHConnectionError(
                    message=f"SSH connection failed during {operation}",
                    device_id="unknown",
                    hostname=result.raw_result.host,
                    details={"original_error": error_msg},
                )
            elif result.error_category in ["container_not_found", "network_error", "volume_error"]:
                raise ContainerError(
                    message=error_msg,
                    container_id="unknown",
                    operation=operation,
                    details={
                        "error_category": result.error_category,
                        "stderr": result.raw_result.stderr,
                        "command": result.command,
                    },
                )
            else:
                raise SSHCommandError(
                    message=f"Docker command failed: {result.command}",
                    command=result.command,
                    exit_code=result.raw_result.return_code,
                    stderr=result.raw_result.stderr,
                    device_id="unknown",
                    hostname=result.raw_result.host,
                )


# Global Docker client instance
_docker_client: Optional[DockerClient] = None


def get_docker_client() -> DockerClient:
    """
    Get the global Docker client instance.

    Returns:
        DockerClient: Global Docker client instance
    """
    global _docker_client
    if _docker_client is None:
        _docker_client = DockerClient()
    return _docker_client


# Utility functions for common Docker operations
async def execute_docker_command_simple(
    host: str,
    command_type: DockerCommandType,
    flags: str = "",
    username: str = "root",
    port: int = 22,
    private_key_path: Optional[str] = None,
    password: Optional[str] = None,
    timeout: int = 120,
    **kwargs,
) -> DockerExecutionResult:
    """
    Convenience function to execute a Docker command.

    Args:
        host: Target hostname or IP address
        command_type: Type of Docker command
        flags: Command flags
        username: SSH username
        port: SSH port
        private_key_path: Path to private key file
        password: SSH password
        timeout: Command timeout in seconds
        **kwargs: Additional command parameters

    Returns:
        DockerExecutionResult: Command execution result with parsed data
    """
    connection_info = SSHConnectionInfo(
        host=host,
        port=port,
        username=username,
        private_key_path=private_key_path,
        password=password,
        command_timeout=timeout,
    )

    docker_client = get_docker_client()
    return await docker_client.execute_docker_command(
        connection_info=connection_info,
        command_type=command_type,
        flags=flags,
        timeout=timeout,
        **kwargs,
    )


async def test_docker_connectivity(
    host: str,
    username: str = "root",
    port: int = 22,
    private_key_path: Optional[str] = None,
    password: Optional[str] = None,
) -> bool:
    """
    Test Docker connectivity on a remote host.

    Args:
        host: Target hostname or IP address
        username: SSH username
        port: SSH port
        private_key_path: Path to private key file
        password: SSH password

    Returns:
        bool: True if Docker is accessible
    """
    try:
        result = await execute_docker_command_simple(
            host=host,
            command_type=DockerCommandType.SYSTEM,
            subcommand="info",
            flags="--format '{{.ServerVersion}}'",
            username=username,
            port=port,
            private_key_path=private_key_path,
            password=password,
            timeout=30,
            parse_json=False,
        )

        return result.success and bool(result.raw_result.stdout.strip())

    except Exception as e:
        logger.debug(f"Docker connectivity test failed for {host}: {e}")
        return False
