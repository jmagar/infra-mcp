"""
SSH configuration file parser for device import functionality.

Parses OpenSSH client configuration files to extract host information
for automatic device registration in the infrastructure registry.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SSHHostConfig(BaseModel):
    """Parsed SSH host configuration"""

    host_pattern: str = Field(description="Original Host pattern from config")
    hostname: Optional[str] = Field(None, description="Resolved hostname or IP")
    port: int = Field(default=22, description="SSH port")
    user: Optional[str] = Field(None, description="SSH username")
    identity_file: Optional[str] = Field(None, description="SSH private key path")
    proxy_command: Optional[str] = Field(None, description="ProxyCommand if present")

    # Additional fields that might be useful
    connect_timeout: Optional[int] = Field(None, description="Connection timeout")
    server_alive_interval: Optional[int] = Field(None, description="ServerAliveInterval")
    forward_x11: Optional[bool] = Field(None, description="X11 forwarding")

    def to_device_dict(self) -> Dict[str, Any]:
        """Convert SSH config to device creation dict"""
        # Use hostname if available, otherwise use host_pattern as hostname
        device_hostname = self.hostname or self.host_pattern

        # Remove wildcards and special patterns from hostname for device registry
        if "*" in device_hostname or "?" in device_hostname:
            # Skip wildcard patterns as they can't be direct devices
            return None

        return {
            "hostname": device_hostname.lower(),
            "ip_address": self.hostname
            if self.hostname and self.hostname != device_hostname
            else None,
            "ssh_port": self.port if self.port != 22 else None,
            "ssh_username": self.user,
            "device_type": "server",  # Default type, can be customized
            "description": f"Imported from SSH config: {self.host_pattern}",
            "tags": {"source": "ssh_config", "ssh_config_host": self.host_pattern},
        }


class SSHConfigParser:
    """Parser for OpenSSH client configuration files"""

    def __init__(self):
        self.global_config = {}
        self.host_configs = []

    def parse_file(self, config_path: str) -> List[SSHHostConfig]:
        """
        Parse SSH configuration file and return list of host configurations.

        Args:
            config_path: Path to SSH config file

        Returns:
            List of SSHHostConfig objects

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is malformed
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"SSH config file not found: {config_path}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError(f"SSH config file is not UTF-8 encoded: {config_path}")

        return self.parse_content(content)

    def parse_content(self, content: str) -> List[SSHHostConfig]:
        """
        Parse SSH configuration content.

        Args:
            content: SSH config file content as string

        Returns:
            List of SSHHostConfig objects
        """
        self.global_config = {}
        self.host_configs = []
        current_host = None
        current_config = {}

        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Remove comments and strip whitespace
            line = re.sub(r"#.*$", "", line).strip()
            if not line:
                continue

            # Parse key-value pairs
            match = re.match(r"^(\w+)\s+(.+)$", line)
            if not match:
                continue

            key = match.group(1).lower()
            value = match.group(2).strip()

            # Handle Host directive
            if key == "host":
                # Save previous host config if exists
                if current_host:
                    self._save_host_config(current_host, current_config)

                # Start new host config
                current_host = value
                current_config = self.global_config.copy()  # Inherit global settings
                continue

            # Store configuration value
            if current_host:
                current_config[key] = value
            else:
                # Global configuration
                self.global_config[key] = value

        # Save the last host config
        if current_host:
            self._save_host_config(current_host, current_config)

        return self.host_configs

    def _save_host_config(self, host_pattern: str, config: Dict[str, str]):
        """Save parsed host configuration"""
        try:
            # Parse configuration values
            hostname = config.get("hostname")
            port = int(config.get("port", 22))
            user = config.get("user")
            identity_file = config.get("identityfile")
            proxy_command = config.get("proxycommand")
            connect_timeout = int(config.get("connecttimeout", 0)) or None
            server_alive_interval = int(config.get("serveraliveinterval", 0)) or None

            # Parse boolean values
            forward_x11 = None
            if "forwardx11" in config:
                forward_x11 = config["forwardx11"].lower() in ("yes", "true", "1")

            # Expand tilde in identity file path
            if identity_file and identity_file.startswith("~"):
                identity_file = str(Path(identity_file).expanduser())

            host_config = SSHHostConfig(
                host_pattern=host_pattern,
                hostname=hostname,
                port=port,
                user=user,
                identity_file=identity_file,
                proxy_command=proxy_command,
                connect_timeout=connect_timeout,
                server_alive_interval=server_alive_interval,
                forward_x11=forward_x11,
            )

            self.host_configs.append(host_config)

        except (ValueError, TypeError) as e:
            # Skip malformed host configs rather than failing entirely
            print(f"Warning: Skipping malformed host config '{host_pattern}': {e}")

    def get_importable_hosts(self, config_path: str) -> List[Dict[str, Any]]:
        """
        Parse SSH config and return list of devices ready for import.

        Args:
            config_path: Path to SSH config file

        Returns:
            List of device dictionaries ready for database insertion
        """
        host_configs = self.parse_file(config_path)
        importable_devices = []

        for host_config in host_configs:
            device_dict = host_config.to_device_dict()
            if device_dict:  # Skip None results (wildcards, etc.)
                importable_devices.append(device_dict)

        return importable_devices


def parse_ssh_config(config_path: str) -> List[Dict[str, Any]]:
    """
    Convenience function to parse SSH config file and return importable devices.

    Args:
        config_path: Path to SSH config file (e.g., ~/.ssh/config)

    Returns:
        List of device dictionaries ready for import

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is malformed
    """
    parser = SSHConfigParser()
    return parser.get_importable_hosts(config_path)


# Example usage and testing
if __name__ == "__main__":
    # Example SSH config content for testing
    example_config = """
# Global settings
User defaultuser
Port 22

# Production servers
Host web01
    HostName 192.168.1.10
    User admin
    Port 2222
    IdentityFile ~/.ssh/web01_key

Host db01
    HostName db01.example.com
    User postgres
    
Host *.dev
    User developer
    Port 2222
    
Host backup-server
    HostName backup.local
    User backup
    IdentityFile ~/.ssh/backup_key
    ConnectTimeout 30
    """

    parser = SSHConfigParser()
    hosts = parser.parse_content(example_config)

    print("Parsed SSH hosts:")
    for host in hosts:
        print(f"  {host.host_pattern}: {host.hostname}:{host.port} ({host.user})")
        device = host.to_device_dict()
        if device:
            print(f"    -> Device: {device['hostname']}")
