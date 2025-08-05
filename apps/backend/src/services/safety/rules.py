"""
Device-Specific Protection Rules

Configuration-as-code approach for defining safety rules tailored to different
operating systems and environments. These rules inform risk assessment and
provide contextual protection based on device capabilities and constraints.
"""

from typing import Any


# Device-specific protection rules configuration
DEVICE_PROTECTION_RULES: dict[str, dict[str, Any]] = {
    "unraid": {
        "max_bulk_operations": 5,
        "protected_paths": [
            "/mnt/user/",  # User share data
            "/mnt/disk[0-9]+/",  # Array disks
            "/mnt/cache/",  # Cache drive
            "/mnt/parity/",  # Parity drive
            "/boot/",  # Boot USB drive
            "/var/log/",  # System logs
        ],
        "critical_services": [
            "nginx",  # Web management interface
            "php-fpm",  # Web interface backend
            "shfs",  # Shared filesystem
            "mover",  # Cache to array mover
            "emhttp",  # Web management service
            "rc.nginx",  # Nginx management
            "rc.php-fpm",  # PHP-FPM management
            "mdcmd",  # Array management daemon
        ],
        "protected_processes": [
            "shfs",
            "mover",
            "emhttp",
            "nginx",
            "php-fpm",
        ],
        "pre_flight_checks": [
            "check_array_status",  # Ensure array is online
            "check_parity_operation",  # Check for parity check/rebuild
            "check_mover_status",  # Check if mover is running
            "check_docker_apps",  # Verify critical Docker apps
        ],
        "environment_type": "production",
        "backup_requirements": {
            "zfs_operations": True,
            "filesystem_operations": True,
            "container_operations": False,
        },
        "confirmation_escalation": {
            "critical_actions": ["zfs_pool_destroy", "filesystem_bulk_delete"],
            "requires_admin_approval": True,
            "max_confirmation_attempts": 3,
        },
    },
    "ubuntu": {
        "max_bulk_operations": 15,
        "protected_paths": [
            "/etc/",  # System configuration
            "/var/lib/docker/",  # Docker data
            "/var/lib/postgresql/",  # PostgreSQL data
            "/home/",  # User directories
            "/root/",  # Root home directory
            "/boot/",  # Boot files
            "/var/log/",  # System logs
        ],
        "critical_services": [
            "ssh",  # SSH daemon
            "sshd",  # SSH daemon (alternative name)
            "systemd",  # System manager
            "docker",  # Docker daemon
            "containerd",  # Container runtime
            "postgresql",  # Database server
            "nginx",  # Web server
            "apache2",  # Apache web server
            "mysql",  # MySQL database
            "mariadb",  # MariaDB database
            "networking",  # Network service
            "ufw",  # Firewall
        ],
        "protected_processes": [
            "systemd",
            "sshd",
            "dockerd",
            "containerd",
            "init",
        ],
        "pre_flight_checks": [
            "check_package_manager_lock",  # Check if apt is running
            "check_ssh_connections",  # Verify SSH connectivity
            "check_systemd_state",  # Ensure systemd is healthy
            "check_docker_daemon",  # Verify Docker is running
        ],
        "environment_type": "production",
        "backup_requirements": {
            "zfs_operations": True,
            "filesystem_operations": True,
            "container_operations": False,
        },
        "confirmation_escalation": {
            "critical_actions": ["service_bulk_stop", "filesystem_bulk_delete"],
            "requires_admin_approval": False,
            "max_confirmation_attempts": 5,
        },
    },
    "wsl2": {
        "max_bulk_operations": 20,
        "protected_paths": [
            "/mnt/c/",  # Windows C: drive mount
            "/mnt/d/",  # Windows D: drive mount
            "/init",  # WSL init process
            "/etc/wsl.conf",  # WSL configuration
        ],
        "critical_services": [
            "docker",  # Docker daemon
            "containerd",  # Container runtime
        ],
        "protected_processes": [
            "init",  # WSL init process
            "dockerd",
            "containerd",
        ],
        "pre_flight_checks": [
            "check_wsl_interop",  # Verify WSL interop services
            "check_windows_mount",  # Check Windows filesystem access
        ],
        "environment_type": "development",
        "backup_requirements": {
            "zfs_operations": False,
            "filesystem_operations": False,  # Less strict for dev environment
            "container_operations": False,
        },
        "confirmation_escalation": {
            "critical_actions": ["filesystem_bulk_delete"],
            "requires_admin_approval": False,
            "max_confirmation_attempts": 3,
        },
    },
    "windows": {
        "max_bulk_operations": 3,
        "protected_paths": [
            "C:\\Windows\\",  # Windows system directory
            "C:\\Program Files\\",  # Program files
            "C:\\Program Files (x86)\\",  # 32-bit program files
            "C:\\Users\\",  # User profiles
            "C:\\ProgramData\\",  # Application data
        ],
        "critical_services": [
            "Docker Desktop Service",  # Docker Desktop
            "com.docker.service",  # Docker service
            "docker",  # Docker CLI service
        ],
        "protected_processes": [
            "Docker Desktop.exe",
            "dockerd.exe",
            "containerd.exe",
        ],
        "pre_flight_checks": [
            "check_docker_desktop",  # Verify Docker Desktop status
            "check_hyper_v",  # Check Hyper-V availability
        ],
        "environment_type": "development",
        "backup_requirements": {
            "zfs_operations": False,
            "filesystem_operations": True,
            "container_operations": False,
        },
        "confirmation_escalation": {
            "critical_actions": ["filesystem_bulk_delete", "system_shutdown"],
            "requires_admin_approval": False,
            "max_confirmation_attempts": 2,
        },
    },
    "docker": {
        "max_bulk_operations": 10,
        "protected_paths": [
            "/var/lib/docker/",  # Docker data directory
            "/etc/docker/",  # Docker configuration
        ],
        "critical_services": [
            "docker",
            "containerd",
        ],
        "protected_processes": [
            "dockerd",
            "containerd",
        ],
        "pre_flight_checks": [
            "check_container_health",  # Verify running containers
        ],
        "environment_type": "container",
        "backup_requirements": {
            "zfs_operations": False,
            "filesystem_operations": False,
            "container_operations": False,
        },
        "confirmation_escalation": {
            "critical_actions": [],
            "requires_admin_approval": False,
            "max_confirmation_attempts": 2,
        },
    },
    "proxmox": {
        "max_bulk_operations": 3,
        "protected_paths": [
            "/etc/pve/",  # Proxmox configuration
            "/var/lib/vz/",  # VM/Container storage
            "/var/lib/pve/",  # PVE data
            "/boot/",  # Boot files
        ],
        "critical_services": [
            "pve-cluster",  # Cluster service
            "pvedaemon",  # PVE daemon
            "pveproxy",  # Web interface proxy
            "pvestatd",  # Statistics daemon
            "qemu-server",  # QEMU/KVM service
            "lxc",  # LXC container service
            "corosync",  # Cluster communication
            "pve-firewall",  # Firewall service
        ],
        "protected_processes": [
            "pvedaemon",
            "pveproxy",
            "qemu-system-x86_64",
            "kvm",
            "corosync",
        ],
        "pre_flight_checks": [
            "check_cluster_status",  # Verify cluster health
            "check_vm_status",  # Check running VMs
            "check_storage_status",  # Verify storage availability
        ],
        "environment_type": "production",
        "backup_requirements": {
            "zfs_operations": True,
            "filesystem_operations": True,
            "container_operations": True,
        },
        "confirmation_escalation": {
            "critical_actions": ["zfs_pool_destroy", "system_shutdown", "service_bulk_stop"],
            "requires_admin_approval": True,
            "max_confirmation_attempts": 2,
        },
    },
    # Default/fallback rules for unknown systems
    "default": {
        "max_bulk_operations": 5,
        "protected_paths": [
            "/etc/",
            "/var/",
            "/home/",
            "/root/",
            "/boot/",
        ],
        "critical_services": [
            "ssh",
            "sshd",
            "systemd",
            "networking",
        ],
        "protected_processes": [
            "systemd",
            "init",
            "sshd",
        ],
        "pre_flight_checks": [
            "check_ssh_connections",
        ],
        "environment_type": "unknown",
        "backup_requirements": {
            "zfs_operations": True,
            "filesystem_operations": True,
            "container_operations": True,
        },
        "confirmation_escalation": {
            "critical_actions": ["filesystem_bulk_delete", "system_shutdown", "zfs_pool_destroy"],
            "requires_admin_approval": True,
            "max_confirmation_attempts": 3,
        },
    },
}


def get_device_rules(device_type: str) -> dict[str, Any]:
    """
    Get protection rules for a specific device type.

    Args:
        device_type: Type of device (unraid, ubuntu, wsl2, windows, etc.)

    Returns:
        Dictionary containing protection rules for the device type
    """
    return DEVICE_PROTECTION_RULES.get(device_type.lower(), DEVICE_PROTECTION_RULES["default"])


def get_max_bulk_operations(device_type: str) -> int:
    """Get maximum allowed bulk operations for a device type."""
    rules = get_device_rules(device_type)
    return rules.get("max_bulk_operations", 5)


def get_protected_paths(device_type: str) -> list[str]:
    """Get list of protected filesystem paths for a device type."""
    rules = get_device_rules(device_type)
    return rules.get("protected_paths", [])


def get_critical_services(device_type: str) -> list[str]:
    """Get list of critical services for a device type."""
    rules = get_device_rules(device_type)
    return rules.get("critical_services", [])


def get_environment_type(device_type: str) -> str:
    """Get environment type (production, development, etc.) for a device type."""
    rules = get_device_rules(device_type)
    return rules.get("environment_type", "unknown")


def requires_backup_validation(device_type: str, operation_type: str) -> bool:
    """
    Check if an operation type requires backup validation for a device type.

    Args:
        device_type: Type of device
        operation_type: Type of operation (zfs_operations, filesystem_operations, etc.)

    Returns:
        True if backup validation is required
    """
    rules = get_device_rules(device_type)
    backup_reqs = rules.get("backup_requirements", {})
    return backup_reqs.get(operation_type, True)  # Default to requiring backup


def get_confirmation_escalation_rules(device_type: str) -> dict[str, Any]:
    """Get confirmation escalation rules for a device type."""
    rules = get_device_rules(device_type)
    return rules.get(
        "confirmation_escalation",
        {
            "critical_actions": [],
            "requires_admin_approval": False,
            "max_confirmation_attempts": 3,
        },
    )


def is_critical_action(device_type: str, action_type: str) -> bool:
    """Check if an action type is considered critical for a device type."""
    escalation_rules = get_confirmation_escalation_rules(device_type)
    critical_actions = escalation_rules.get("critical_actions", [])
    return action_type in critical_actions


def get_all_device_types() -> list[str]:
    """Get list of all supported device types."""
    return list(DEVICE_PROTECTION_RULES.keys())
