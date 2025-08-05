"""
Destructive Command Patterns

Comprehensive library of regular expression patterns for detecting potentially
destructive operations across various CLI tools and infrastructure commands.
"""

from enum import Enum


class DestructiveActionType(Enum):
    """Enumeration of all detectable destructive action types."""

    # Container Operations
    CONTAINER_BULK_STOP = "container_bulk_stop"
    CONTAINER_BULK_REMOVE = "container_bulk_remove"
    CONTAINER_BULK_KILL = "container_bulk_kill"
    IMAGE_BULK_REMOVE = "image_bulk_remove"
    VOLUME_BULK_REMOVE = "volume_bulk_remove"
    NETWORK_BULK_REMOVE = "network_bulk_remove"
    SYSTEM_PRUNE = "system_prune"

    # Docker Compose Operations
    COMPOSE_DOWN_VOLUMES = "compose_down_volumes"
    COMPOSE_DESTROY = "compose_destroy"

    # Filesystem Operations
    FILESYSTEM_BULK_DELETE = "filesystem_bulk_delete"
    FILESYSTEM_FORMAT = "filesystem_format"
    FILESYSTEM_WIPE = "filesystem_wipe"

    # Service Management
    SERVICE_BULK_STOP = "service_bulk_stop"
    SERVICE_BULK_DISABLE = "service_bulk_disable"
    SERVICE_BULK_RESTART = "service_bulk_restart"

    # ZFS Operations
    ZFS_POOL_DESTROY = "zfs_pool_destroy"
    ZFS_DATASET_DESTROY = "zfs_dataset_destroy"
    ZFS_SNAPSHOT_DESTROY_BULK = "zfs_snapshot_destroy_bulk"

    # System Power Operations
    SYSTEM_REBOOT = "system_reboot"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_HALT = "system_halt"

    # Network Operations
    FIREWALL_FLUSH = "firewall_flush"
    NETWORK_INTERFACE_DOWN = "network_interface_down"

    # Process Management
    PROCESS_BULK_KILL = "process_bulk_kill"

    # User Management
    USER_BULK_DELETE = "user_bulk_delete"

    # Package Management
    PACKAGE_BULK_REMOVE = "package_bulk_remove"
    PACKAGE_AUTOREMOVE = "package_autoremove"


# Comprehensive destructive command patterns
DESTRUCTIVE_COMMAND_PATTERNS: dict[DestructiveActionType, list[str]] = {
    # Container Operations
    DestructiveActionType.CONTAINER_BULK_STOP: [
        r"docker\s+stop\s+`docker\s+ps\s+-q`",
        r"docker\s+stop\s+\$\(docker\s+ps\s+-q\)",
        r"docker\s+stop\s+\$\(docker\s+ps\s+.*-q.*\)",
        r"docker\s+ps\s+.*\|\s*xargs\s+.*docker\s+stop",
        r"docker\s+container\s+stop\s+--all",
        r"docker-compose\s+stop\s*$",
        r"docker-compose\s+down\s*$",
    ],
    DestructiveActionType.CONTAINER_BULK_REMOVE: [
        r"docker\s+rm\s+-f\s+\$\(docker\s+ps\s+-aq\)",
        r"docker\s+rm\s+.*\$\(docker\s+ps\s+.*-q.*\)",
        r"docker\s+container\s+rm\s+.*--all",
        r"docker\s+ps\s+.*\|\s*xargs\s+.*docker\s+rm",
        r"docker\s+container\s+prune\s+-f",
        r"docker\s+container\s+prune\s+--force",
    ],
    DestructiveActionType.CONTAINER_BULK_KILL: [
        r"docker\s+kill\s+\$\(docker\s+ps\s+-q\)",
        r"docker\s+ps\s+.*\|\s*xargs\s+.*docker\s+kill",
        r"docker\s+container\s+kill\s+.*--all",
        r"killall\s+docker",
    ],
    DestructiveActionType.IMAGE_BULK_REMOVE: [
        r"docker\s+rmi\s+\$\(docker\s+images\s+-q\)",
        r"docker\s+image\s+rm\s+\$\(docker\s+images\s+-q\)",
        r"docker\s+image\s+prune\s+-af?",
        r"docker\s+image\s+prune\s+--all\s+--force",
        r"docker\s+images\s+.*\|\s*xargs\s+.*docker\s+rmi",
    ],
    DestructiveActionType.VOLUME_BULK_REMOVE: [
        r"docker\s+volume\s+rm\s+\$\(docker\s+volume\s+ls\s+-q\)",
        r"docker\s+volume\s+prune\s+-f",
        r"docker\s+volume\s+prune\s+--force",
        r"docker\s+volume\s+ls\s+.*\|\s*xargs\s+.*docker\s+volume\s+rm",
    ],
    DestructiveActionType.NETWORK_BULK_REMOVE: [
        r"docker\s+network\s+rm\s+\$\(docker\s+network\s+ls\s+-q\)",
        r"docker\s+network\s+prune\s+-f",
        r"docker\s+network\s+prune\s+--force",
    ],
    DestructiveActionType.SYSTEM_PRUNE: [
        r"docker\s+system\s+prune\s+-af?",
        r"docker\s+system\s+prune\s+--all\s+--force",
        r"docker\s+system\s+prune\s+--volumes\s+--force",
    ],
    # Docker Compose Operations
    DestructiveActionType.COMPOSE_DOWN_VOLUMES: [
        r"docker-compose\s+down\s+.*-v",
        r"docker-compose\s+down\s+.*--volumes",
        r"docker\s+compose\s+down\s+.*-v",
        r"docker\s+compose\s+down\s+.*--volumes",
    ],
    DestructiveActionType.COMPOSE_DESTROY: [
        r"docker-compose\s+down\s+.*--rmi\s+all",
        r"docker\s+compose\s+down\s+.*--rmi\s+all",
        r"docker-compose\s+rm\s+-fsv",
    ],
    # Filesystem Operations
    DestructiveActionType.FILESYSTEM_BULK_DELETE: [
        r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*|-rf)\s+/(?!tmp/|var/tmp/|proc/|dev/|sys/)",
        r"rm\s+-rf\s+\*",
        r"rm\s+-rf\s+~",
        r"find\s+.*-delete",
        r"find\s+.*-exec\s+rm",
        r"shred\s+-vfz\s+.*\*",
        r"dd\s+.*if=/dev/zero\s+of=/dev/sd[a-z]+",
    ],
    DestructiveActionType.FILESYSTEM_FORMAT: [
        r"mkfs\.(ext[234]|xfs|btrfs|ntfs|fat32)\s+/dev/sd[a-z]+",
        r"mkfs\s+-t\s+(ext[234]|xfs|btrfs|ntfs|fat32)\s+/dev/sd[a-z]+",
        r"fdisk\s+.*-w\s+.*never",
    ],
    DestructiveActionType.FILESYSTEM_WIPE: [
        r"wipefs\s+-af?\s+/dev/sd[a-z]+",
        r"sgdisk\s+.*--zap-all\s+/dev/sd[a-z]+",
        r"dd\s+.*if=/dev/urandom.*of=/dev/sd[a-z]+",
    ],
    # Service Management
    DestructiveActionType.SERVICE_BULK_STOP: [
        r"systemctl\s+stop\s+\*\.service",
        r"systemctl\s+stop\s+.*--all",
        r"service\s+--status-all\s+\|\s+awk.*\|\s+xargs.*stop",
        r"systemctl\s+list-units.*\|\s+xargs.*systemctl\s+stop",
        r"killall\s+-9\s+systemd",
    ],
    DestructiveActionType.SERVICE_BULK_DISABLE: [
        r"systemctl\s+disable\s+--now\s+\*\.service",
        r"systemctl\s+mask\s+\*\.service",
        r"systemctl\s+disable\s+.*--all",
    ],
    DestructiveActionType.SERVICE_BULK_RESTART: [
        r"systemctl\s+restart\s+\*\.service",
        r"systemctl\s+restart\s+.*--all",
        r"service\s+--status-all.*\|\s+xargs.*restart",
    ],
    # ZFS Operations
    DestructiveActionType.ZFS_POOL_DESTROY: [
        r"zpool\s+destroy\s+-f\s+\w+",
        r"zpool\s+destroy\s+\w+",
        r"zpool\s+export\s+-f\s+\w+",
    ],
    DestructiveActionType.ZFS_DATASET_DESTROY: [
        r"zfs\s+destroy\s+-r\s+[\w/]+",
        r"zfs\s+destroy\s+-R\s+[\w/]+",
        r"zfs\s+destroy\s+-f\s+[\w/]+",
    ],
    DestructiveActionType.ZFS_SNAPSHOT_DESTROY_BULK: [
        r"zfs\s+destroy\s+.*%.*",
        r"zfs\s+list.*snapshot.*\|\s+xargs.*zfs\s+destroy",
        r"zfs\s+destroy\s+-r.*@.*",
    ],
    # System Power Operations
    DestructiveActionType.SYSTEM_REBOOT: [
        r"\breboot\b",
        r"shutdown\s+-r",
        r"systemctl\s+reboot",
        r"init\s+6",
        r"/sbin/reboot",
    ],
    DestructiveActionType.SYSTEM_SHUTDOWN: [
        r"shutdown\s+-h\s+now",
        r"shutdown\s+now",
        r"systemctl\s+poweroff",
        r"systemctl\s+halt",
        r"init\s+0",
        r"/sbin/shutdown",
    ],
    DestructiveActionType.SYSTEM_HALT: [
        r"\bpoweroff\b",
        r"\bhalt\b",
        r"systemctl\s+halt",
        r"/sbin/halt",
    ],
    # Network Operations
    DestructiveActionType.FIREWALL_FLUSH: [
        r"iptables\s+-F",
        r"iptables\s+--flush",
        r"ufw\s+reset",
        r"ufw\s+--force\s+reset",
        r"firewall-cmd\s+.*--complete-reload",
        r"nft\s+flush\s+ruleset",
    ],
    DestructiveActionType.NETWORK_INTERFACE_DOWN: [
        r"ifconfig\s+\w+\s+down",
        r"ip\s+link\s+set\s+\w+\s+down",
        r"nmcli\s+connection\s+down\s+\w+",
        r"systemctl\s+stop\s+networking",
    ],
    # Process Management
    DestructiveActionType.PROCESS_BULK_KILL: [
        r"killall\s+-9\s+.*",
        r"pkill\s+-9\s+.*",
        r"kill\s+-9\s+\$\(.*\)",
        r"ps\s+aux\s+\|\s+grep.*\|\s+awk.*\|\s+xargs\s+kill",
        r"kill\s+-KILL\s+.*",
    ],
    # User Management
    DestructiveActionType.USER_BULK_DELETE: [
        r"deluser\s+--remove-all-files",
        r"userdel\s+-r\s+\w+",
        r"getent\s+passwd.*\|\s+xargs.*userdel",
    ],
    # Package Management
    DestructiveActionType.PACKAGE_BULK_REMOVE: [
        r"apt\s+remove\s+.*\*",
        r"apt\s+purge\s+.*\*",
        r"yum\s+remove\s+.*\*",
        r"dnf\s+remove\s+.*\*",
        r"pacman\s+-R.*",
        r"zypper\s+remove\s+.*\*",
    ],
    DestructiveActionType.PACKAGE_AUTOREMOVE: [
        r"apt\s+autoremove\s+--purge",
        r"yum\s+autoremove",
        r"dnf\s+autoremove",
        r"pacman\s+-Rs\s+\$\(pacman\s+-Qtdq\)",
    ],
}


def get_patterns_for_action_type(action_type: DestructiveActionType) -> list[str]:
    """Get patterns for a specific destructive action type."""
    return DESTRUCTIVE_COMMAND_PATTERNS.get(action_type, [])


def get_all_patterns() -> dict[DestructiveActionType, list[str]]:
    """Get all destructive command patterns."""
    return DESTRUCTIVE_COMMAND_PATTERNS.copy()


def get_action_types_by_category() -> dict[str, list[DestructiveActionType]]:
    """Group action types by category for easier management."""
    return {
        "container": [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.CONTAINER_BULK_REMOVE,
            DestructiveActionType.CONTAINER_BULK_KILL,
            DestructiveActionType.IMAGE_BULK_REMOVE,
            DestructiveActionType.VOLUME_BULK_REMOVE,
            DestructiveActionType.NETWORK_BULK_REMOVE,
            DestructiveActionType.SYSTEM_PRUNE,
            DestructiveActionType.COMPOSE_DOWN_VOLUMES,
            DestructiveActionType.COMPOSE_DESTROY,
        ],
        "filesystem": [
            DestructiveActionType.FILESYSTEM_BULK_DELETE,
            DestructiveActionType.FILESYSTEM_FORMAT,
            DestructiveActionType.FILESYSTEM_WIPE,
        ],
        "services": [
            DestructiveActionType.SERVICE_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_DISABLE,
            DestructiveActionType.SERVICE_BULK_RESTART,
        ],
        "zfs": [
            DestructiveActionType.ZFS_POOL_DESTROY,
            DestructiveActionType.ZFS_DATASET_DESTROY,
            DestructiveActionType.ZFS_SNAPSHOT_DESTROY_BULK,
        ],
        "system": [
            DestructiveActionType.SYSTEM_REBOOT,
            DestructiveActionType.SYSTEM_SHUTDOWN,
            DestructiveActionType.SYSTEM_HALT,
        ],
        "network": [
            DestructiveActionType.FIREWALL_FLUSH,
            DestructiveActionType.NETWORK_INTERFACE_DOWN,
        ],
        "processes": [
            DestructiveActionType.PROCESS_BULK_KILL,
        ],
        "users": [
            DestructiveActionType.USER_BULK_DELETE,
        ],
        "packages": [
            DestructiveActionType.PACKAGE_BULK_REMOVE,
            DestructiveActionType.PACKAGE_AUTOREMOVE,
        ],
    }
