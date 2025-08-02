"""
Infrastructure Management MCP Server - SSH Communication Layer

This module provides comprehensive SSH communication capabilities for infrastructure monitoring,
including connection pooling, secure authentication, command execution, and error handling.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union, AsyncGenerator, Any
from urllib.parse import urlparse
import weakref

import asyncssh
from asyncssh import SSHClientConnection, SSHCompletedProcess

from apps.backend.src.core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SSHConnectionInfo:
    """SSH connection configuration for a device"""

    host: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None
    connect_timeout: int = 30
    command_timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class SSHExecutionResult:
    """Result of SSH command execution"""

    command: str
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    host: str
    success: bool
    error_message: Optional[str] = None

    @property
    def output(self) -> str:
        """Combined stdout and stderr output"""
        return f"{self.stdout}\n{self.stderr}".strip()


class SSHConnectionPool:
    """
    Async SSH connection pool with automatic cleanup and connection management.

    Manages connections to multiple devices with configurable limits and timeouts.
    """

    def __init__(self, max_connections_per_host: int = 3, connection_timeout: int = 30):
        """
        Initialize SSH connection pool.

        Args:
            max_connections_per_host: Maximum concurrent connections per host
            connection_timeout: Connection timeout in seconds
        """
        self.max_connections_per_host = max_connections_per_host
        self.connection_timeout = connection_timeout

        # Connection pool storage
        self._pools: Dict[str, List[SSHClientConnection]] = {}
        self._pool_locks: Dict[str, asyncio.Lock] = {}
        self._connection_counts: Dict[str, int] = {}
        self._last_used: Dict[str, float] = {}

        # Connection cleanup tracking
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False

        # Cleanup task will be started lazily when first needed

    def _start_cleanup_task(self):
        """Start the connection cleanup background task (lazy initialization)"""
        try:
            # Only start if there's a running event loop and task isn't already running
            asyncio.get_running_loop()
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_connections())
        except RuntimeError:
            # No event loop running, cleanup task will be started later when needed
            pass

    async def _cleanup_connections(self):
        """Background task to cleanup idle connections"""
        while not self._shutdown:
            try:
                current_time = time.time()
                cleanup_threshold = 300  # 5 minutes

                for host, connections in list(self._pools.items()):
                    if host in self._last_used:
                        idle_time = current_time - self._last_used[host]

                        if idle_time > cleanup_threshold and connections:
                            # Close idle connections
                            async with self._pool_locks.get(host, asyncio.Lock()):
                                if connections:
                                    connection = connections.pop()
                                    try:
                                        connection.close()
                                        await connection.wait_closed()
                                    except Exception as e:
                                        logger.debug(
                                            f"Error closing idle connection to {host}: {e}"
                                        )

                                    self._connection_counts[host] = max(
                                        0, self._connection_counts.get(host, 0) - 1
                                    )

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection cleanup task: {e}")
                await asyncio.sleep(60)

    def _get_host_key(self, connection_info: SSHConnectionInfo) -> str:
        """Generate unique key for host connection pool"""
        return connection_info.host

    async def _create_connection(self, connection_info: SSHConnectionInfo) -> SSHClientConnection:
        """Create a new SSH connection using system SSH configuration"""
        # Ensure host is a string
        if not isinstance(connection_info.host, str):
            raise TypeError(
                f"Host must be a string, got {type(connection_info.host)}: {connection_info.host}"
            )

        connect_kwargs = {
            "host": connection_info.host,
            "connect_timeout": connection_info.connect_timeout,
            "known_hosts": None,  # Disable host key checking for infrastructure monitoring
            "login_timeout": connection_info.connect_timeout,
        }

        # Let asyncssh use system SSH config entirely - don't override anything
        # This allows ~/.ssh/config to handle username, port, keys, etc.

        try:
            logger.debug(f"Attempting SSH connection with kwargs: {connect_kwargs}")
            connection = await asyncssh.connect(**connect_kwargs)
            logger.debug(f"Created SSH connection to {connection_info.host}")
            return connection

        except Exception as e:
            logger.error(f"Failed to create SSH connection to {connection_info.host}: {e}")
            raise

    @asynccontextmanager
    async def get_connection(
        self, connection_info: SSHConnectionInfo
    ) -> AsyncGenerator[SSHClientConnection, None]:
        """
        Get an SSH connection from the pool with automatic cleanup.

        Args:
            connection_info: SSH connection configuration

        Yields:
            SSHClientConnection: Active SSH connection
        """
        host_key = self._get_host_key(connection_info)

        # Ensure pool structures exist
        if host_key not in self._pools:
            self._pools[host_key] = []
            self._pool_locks[host_key] = asyncio.Lock()
            self._connection_counts[host_key] = 0

        connection = None

        try:
            # Try to get existing connection from pool
            async with self._pool_locks[host_key]:
                if self._pools[host_key]:
                    connection = self._pools[host_key].pop()

                    # Test if connection is still alive
                    try:
                        # Simple connectivity test
                        await asyncio.wait_for(
                            connection.run("echo 'test'", check=False), timeout=5.0
                        )
                    except Exception:
                        # Connection is dead, close it and create new one
                        try:
                            connection.close()
                            await connection.wait_closed()
                        except Exception:
                            pass
                        connection = None
                        self._connection_counts[host_key] = max(
                            0, self._connection_counts[host_key] - 1
                        )

            # Create new connection if needed
            if connection is None:
                # Check connection limit
                if self._connection_counts[host_key] >= self.max_connections_per_host:
                    # Wait for a connection to become available
                    while self._connection_counts[host_key] >= self.max_connections_per_host:
                        await asyncio.sleep(0.1)

                connection = await self._create_connection(connection_info)
                self._connection_counts[host_key] += 1

            # Update last used time
            self._last_used[host_key] = time.time()

            yield connection

        except Exception as e:
            # If connection failed, clean it up
            if connection:
                try:
                    connection.close()
                    await connection.wait_closed()
                except Exception:
                    pass
                self._connection_counts[host_key] = max(0, self._connection_counts[host_key] - 1)
            raise

        finally:
            # Return connection to pool if still alive
            if connection and not connection.is_closed():
                async with self._pool_locks[host_key]:
                    self._pools[host_key].append(connection)
            elif connection:
                # Connection is closed, decrease count
                self._connection_counts[host_key] = max(0, self._connection_counts[host_key] - 1)

    async def close_all_connections(self):
        """Close all connections in the pool"""
        self._shutdown = True

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all pooled connections
        for host_key, connections in self._pools.items():
            async with self._pool_locks[host_key]:
                while connections:
                    connection = connections.pop()
                    try:
                        connection.close()
                        await connection.wait_closed()
                    except Exception as e:
                        logger.debug(f"Error closing connection in pool cleanup: {e}")

        # Clear pool state
        self._pools.clear()
        self._connection_counts.clear()
        self._last_used.clear()

        logger.info("SSH connection pool closed")

    def get_pool_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get connection pool statistics"""
        stats = {}
        for host_key in self._pools:
            stats[host_key] = {
                "pooled_connections": len(self._pools[host_key]),
                "total_connections": self._connection_counts.get(host_key, 0),
                "last_used": self._last_used.get(host_key, 0),
                "max_connections": self.max_connections_per_host,
            }
        return stats


class SSHClient:
    """
    Advanced SSH client with connection pooling, error handling, and retry logic.

    Provides high-level interface for executing commands on remote infrastructure devices.
    """

    def __init__(self, connection_pool: Optional[SSHConnectionPool] = None):
        """
        Initialize SSH client.

        Args:
            connection_pool: Optional connection pool instance
        """
        settings = get_settings()

        self.connection_pool = connection_pool or SSHConnectionPool(
            max_connections_per_host=settings.ssh.ssh_max_connections_per_host,
            connection_timeout=settings.ssh.ssh_connect_timeout,
        )

        # Configuration from settings
        self.default_timeout = settings.ssh.ssh_command_timeout
        self.max_retries = settings.ssh.ssh_max_retries
        self.retry_delay = settings.ssh.ssh_retry_delay

        # Concurrent execution limits
        self._execution_semaphore = asyncio.Semaphore(settings.api.max_concurrent_ssh_connections)

        # Command execution statistics
        self._execution_stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
        }

    async def execute_command(
        self,
        connection_info: SSHConnectionInfo,
        command: str,
        timeout: Optional[int] = None,
        check: bool = True,
        retries: Optional[int] = None,
    ) -> SSHExecutionResult:
        """
        Execute a single command on a remote host.

        Args:
            connection_info: SSH connection configuration
            command: Command to execute
            timeout: Command timeout in seconds
            check: Whether to raise exception on non-zero exit codes
            retries: Number of retry attempts

        Returns:
            SSHExecutionResult: Command execution result

        Raises:
            Exception: If command execution fails and check=True
        """
        async with self._execution_semaphore:
            timeout = timeout or connection_info.command_timeout or self.default_timeout
            retries = retries if retries is not None else connection_info.max_retries

            last_exception = None

            for attempt in range(retries + 1):
                start_time = time.time()

                try:
                    async with self.connection_pool.get_connection(connection_info) as connection:
                        # Execute command with timeout
                        result = await asyncio.wait_for(
                            connection.run(command, check=False), timeout=timeout
                        )

                        execution_time = time.time() - start_time

                        # Update statistics
                        self._execution_stats["total_commands"] += 1
                        self._execution_stats["total_execution_time"] += execution_time

                        if result.returncode == 0:
                            self._execution_stats["successful_commands"] += 1
                        else:
                            self._execution_stats["failed_commands"] += 1

                        self._execution_stats["average_execution_time"] = self._execution_stats[
                            "total_execution_time"
                        ] / max(self._execution_stats["total_commands"], 1)

                        # Create result object
                        ssh_result = SSHExecutionResult(
                            command=command,
                            return_code=result.returncode,
                            stdout=result.stdout,
                            stderr=result.stderr,
                            execution_time=execution_time,
                            host=connection_info.host,
                            success=result.returncode == 0,
                        )

                        # Check for errors if requested
                        if check and result.returncode != 0:
                            error_msg = f"Command failed on {connection_info.host}: {command}"
                            if result.stderr:
                                error_msg += f"\nStderr: {result.stderr}"
                            ssh_result.error_message = error_msg
                            raise Exception(error_msg)

                        logger.debug(
                            f"Command executed on {connection_info.host} in {execution_time:.2f}s: {command[:50]}..."
                        )

                        return ssh_result

                except asyncio.TimeoutError as e:
                    execution_time = time.time() - start_time
                    last_exception = e
                    error_msg = (
                        f"Command timeout after {timeout}s on {connection_info.host}: {command}"
                    )

                    if attempt == retries:
                        self._execution_stats["failed_commands"] += 1
                        logger.error(error_msg)
                        return SSHExecutionResult(
                            command=command,
                            return_code=-1,
                            stdout="",
                            stderr=f"Timeout after {timeout}s",
                            execution_time=execution_time,
                            host=connection_info.host,
                            success=False,
                            error_message=error_msg,
                        )
                    else:
                        logger.warning(f"{error_msg} (attempt {attempt + 1}/{retries + 1})")
                        await asyncio.sleep(connection_info.retry_delay * (attempt + 1))

                except Exception as e:
                    execution_time = time.time() - start_time
                    last_exception = e
                    error_msg = f"SSH execution error on {connection_info.host}: {str(e)}"

                    if attempt == retries:
                        self._execution_stats["failed_commands"] += 1
                        logger.error(error_msg)
                        return SSHExecutionResult(
                            command=command,
                            return_code=-1,
                            stdout="",
                            stderr=str(e),
                            execution_time=execution_time,
                            host=connection_info.host,
                            success=False,
                            error_message=error_msg,
                        )
                    else:
                        logger.warning(f"{error_msg} (attempt {attempt + 1}/{retries + 1})")
                        await asyncio.sleep(connection_info.retry_delay * (attempt + 1))

            # Should not reach here, but handle it gracefully
            return SSHExecutionResult(
                command=command,
                return_code=-1,
                stdout="",
                stderr=f"Max retries exceeded: {str(last_exception)}",
                execution_time=0.0,
                host=connection_info.host,
                success=False,
                error_message=f"Max retries exceeded: {str(last_exception)}",
            )

    async def execute_commands(
        self,
        connection_info: SSHConnectionInfo,
        commands: List[str],
        timeout: Optional[int] = None,
        fail_fast: bool = True,
    ) -> List[SSHExecutionResult]:
        """
        Execute multiple commands sequentially on a remote host.

        Args:
            connection_info: SSH connection configuration
            commands: List of commands to execute
            timeout: Per-command timeout in seconds
            fail_fast: Stop execution on first failure

        Returns:
            List[SSHExecutionResult]: Results for each command
        """
        results = []

        for command in commands:
            try:
                result = await self.execute_command(
                    connection_info=connection_info,
                    command=command,
                    timeout=timeout,
                    check=fail_fast,
                )
                results.append(result)

                if fail_fast and not result.success:
                    break

            except Exception as e:
                if fail_fast:
                    # Add error result and stop
                    results.append(
                        SSHExecutionResult(
                            command=command,
                            return_code=-1,
                            stdout="",
                            stderr=str(e),
                            execution_time=0.0,
                            host=connection_info.host,
                            success=False,
                            error_message=str(e),
                        )
                    )
                    break
                else:
                    # Continue with next command
                    results.append(
                        SSHExecutionResult(
                            command=command,
                            return_code=-1,
                            stdout="",
                            stderr=str(e),
                            execution_time=0.0,
                            host=connection_info.host,
                            success=False,
                            error_message=str(e),
                        )
                    )

        return results

    async def execute_parallel(
        self, commands: List[tuple[SSHConnectionInfo, str]], timeout: Optional[int] = None
    ) -> List[SSHExecutionResult]:
        """
        Execute commands in parallel across multiple hosts.

        Args:
            commands: List of (connection_info, command) tuples
            timeout: Per-command timeout in seconds

        Returns:
            List[SSHExecutionResult]: Results for each command
        """
        tasks = []

        for connection_info, command in commands:
            task = asyncio.create_task(
                self.execute_command(
                    connection_info=connection_info,
                    command=command,
                    timeout=timeout,
                    check=False,  # Don't raise exceptions in parallel execution
                )
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                connection_info, command = commands[i]
                processed_results.append(
                    SSHExecutionResult(
                        command=command,
                        return_code=-1,
                        stdout="",
                        stderr=str(result),
                        execution_time=0.0,
                        host=connection_info.host,
                        success=False,
                        error_message=str(result),
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def test_connectivity(self, connection_info: SSHConnectionInfo) -> bool:
        """
        Test SSH connectivity to a host.

        Args:
            connection_info: SSH connection configuration

        Returns:
            bool: True if connection is successful
        """
        try:
            result = await self.execute_command(
                connection_info=connection_info,
                command="echo 'connectivity_test'",
                timeout=10,
                check=True,
            )
            return result.success and "connectivity_test" in result.stdout

        except Exception as e:
            logger.debug(f"Connectivity test failed for {connection_info.host}: {e}")
            return False

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get command execution statistics"""
        return self._execution_stats.copy()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return self.connection_pool.get_pool_stats()

    async def close(self):
        """Close SSH client and cleanup resources"""
        await self.connection_pool.close_all_connections()
        logger.info("SSH client closed")


# Global SSH client instance
_ssh_client: Optional[SSHClient] = None


def get_ssh_client() -> SSHClient:
    """
    Get the global SSH client instance.

    Returns:
        SSHClient: Global SSH client instance
    """
    global _ssh_client
    if _ssh_client is None:
        _ssh_client = SSHClient()
    return _ssh_client


async def cleanup_ssh_client():
    """Cleanup global SSH client"""
    global _ssh_client
    if _ssh_client is not None:
        await _ssh_client.close()
        _ssh_client = None


# Utility functions for common SSH operations
async def execute_ssh_command(
    host: str,
    command: str,
    username: str = "root",
    port: int = 22,
    private_key_path: Optional[str] = None,
    password: Optional[str] = None,
    timeout: int = 120,
) -> SSHExecutionResult:
    """
    Convenience function to execute a single SSH command.

    Args:
        host: Target hostname or IP address
        command: Command to execute
        username: SSH username
        port: SSH port
        private_key_path: Path to private key file
        password: SSH password
        timeout: Command timeout in seconds

    Returns:
        SSHExecutionResult: Command execution result
    """
    connection_info = SSHConnectionInfo(
        host=host,
        port=port,
        username=username,
        private_key_path=private_key_path,
        password=password,
        command_timeout=timeout,
    )

    ssh_client = get_ssh_client()
    return await ssh_client.execute_command(connection_info, command)


async def test_ssh_connectivity(
    host: str,
    username: str = "root",
    port: int = 22,
    private_key_path: Optional[str] = None,
    password: Optional[str] = None,
) -> bool:
    """
    Test SSH connectivity to a host.

    Args:
        host: Target hostname or IP address
        username: SSH username
        port: SSH port
        private_key_path: Path to private key file
        password: SSH password

    Returns:
        bool: True if connection is successful
    """
    connection_info = SSHConnectionInfo(
        host=host,
        port=port,
        username=username,
        private_key_path=private_key_path,
        password=password,
    )

    ssh_client = get_ssh_client()
    return await ssh_client.test_connectivity(connection_info)


# Simple SSH config-based functions
async def execute_ssh_command_simple(
    hostname: str, command: str, timeout: int = 120
) -> SSHExecutionResult:
    """
    Execute SSH command using only hostname - let SSH config handle connection details.

    Args:
        hostname: Device hostname (must be in ~/.ssh/config)
        command: Command to execute
        timeout: Command timeout in seconds

    Returns:
        SSHExecutionResult: Command execution result
    """
    # Ensure hostname is a string
    if not isinstance(hostname, str):
        raise TypeError(f"Hostname must be a string, got {type(hostname)}: {hostname}")

    connection_info = SSHConnectionInfo(
        host=hostname,
        command_timeout=timeout,
        # Let SSH config handle everything else (username, port, keys, etc.)
    )

    ssh_client = get_ssh_client()
    return await ssh_client.execute_command(connection_info, command)


async def test_ssh_connectivity_simple(hostname: str) -> bool:
    """
    Test SSH connectivity using only hostname - let SSH config handle connection details.

    Args:
        hostname: Device hostname (must be in ~/.ssh/config)

    Returns:
        bool: True if connection is successful
    """
    connection_info = SSHConnectionInfo(host=hostname)
    ssh_client = get_ssh_client()
    return await ssh_client.test_connectivity(connection_info)
