# Destructive Action Manager - Patterns and Usage Guide

This document provides comprehensive documentation for the Destructive Action Protection System, including all supported patterns, usage examples, and integration guidelines.

## 🔒 System Overview

The Destructive Action Protection System is a multi-layered safety framework that:
- **Detects** potentially dangerous commands using 115+ regex patterns
- **Analyzes** risk based on device context and environment
- **Blocks** high-risk operations requiring explicit confirmation
- **Manages** the complete confirmation workflow with state tracking
- **Audits** all destructive actions for security and compliance

## 🎯 Supported Destructive Action Types (27 Categories)

### Container Operations
| Action Type | Description | Example Commands |
|-------------|-------------|------------------|
| `container_bulk_stop` | Stop multiple containers | `docker stop $(docker ps -q)` |
| `container_bulk_remove` | Remove multiple containers | `docker rm -f $(docker ps -aq)` |
| `container_bulk_kill` | Kill multiple containers | `docker kill $(docker ps -q)` |
| `image_bulk_remove` | Remove multiple images | `docker rmi $(docker images -q)` |
| `volume_bulk_remove` | Remove multiple volumes | `docker volume prune -f` |
| `network_bulk_remove` | Remove multiple networks | `docker network prune -f` |
| `system_prune` | Clean up Docker system | `docker system prune -af` |

### Filesystem Operations
| Action Type | Description | Example Commands |
|-------------|-------------|------------------|
| `filesystem_bulk_delete` | Delete files/directories | `rm -rf /var/lib/docker` |
| `filesystem_format` | Format filesystems | `mkfs.ext4 /dev/sdb1` |
| `filesystem_wipe` | Wipe disk/partition | `dd if=/dev/zero of=/dev/sdb` |
| `filesystem_recursive_delete` | Recursive deletions | `find /tmp -name "*.log" -delete` |

### Service Management
| Action Type | Description | Example Commands |
|-------------|-------------|------------------|
| `service_bulk_stop` | Stop multiple services | `systemctl stop *.service` |
| `service_bulk_disable` | Disable multiple services | `systemctl disable --now *.service` |
| `service_bulk_restart` | Restart multiple services | `systemctl restart *.service` |
| `service_bulk_reload` | Reload multiple services | `systemctl reload *.service` |

### ZFS Operations
| Action Type | Description | Example Commands |
|-------------|-------------|------------------|
| `zfs_pool_destroy` | Destroy ZFS pool | `zpool destroy tank` |
| `zfs_dataset_destroy` | Destroy ZFS dataset | `zfs destroy -r tank/data` |
| `zfs_snapshot_destroy_bulk` | Remove multiple snapshots | `zfs destroy tank/data@snap%` |

### System Power Operations
| Action Type | Description | Example Commands |
|-------------|-------------|------------------|
| `system_reboot` | Reboot system | `reboot`, `shutdown -r now` |
| `system_shutdown` | Shutdown system | `poweroff`, `shutdown -h now` |
| `system_halt` | Halt system | `halt` |

### Network Operations
| Action Type | Description | Example Commands |
|-------------|-------------|------------------|
| `firewall_flush` | Flush firewall rules | `iptables -F` |
| `network_interface_down` | Disable network interface | `ip link set eth0 down` |

### Package Management
| Action Type | Description | Example Commands |
|-------------|-------------|------------------|
| `package_bulk_remove` | Remove multiple packages | `apt purge $(dpkg -l | grep '^rc' | awk '{print $2}')` |
| `package_autoremove` | Auto-remove packages | `apt autoremove --purge` |

### User Management
| Action Type | Description | Example Commands |
|-------------|-------------|------------------|
| `user_bulk_delete` | Delete multiple users | `deluser --remove-all-files username` |

## 📝 Pattern Examples

### Container Bulk Operations
```regex
# Container bulk stop patterns
docker\s+stop\s+\$\(docker\s+ps\s+-q\)
docker\s+stop\s+`docker\s+ps\s+-q`
docker-compose\s+down
docker\s+container\s+stop\s+\$\(docker\s+container\s+ls\s+-q\)

# Container bulk remove patterns  
docker\s+rm\s+-f\s+\$\(docker\s+ps\s+-aq\)
docker\s+container\s+prune\s+-f
docker\s+rm\s+\$\(docker\s+ps\s+-aq\)

# System prune patterns
docker\s+system\s+prune\s+-af?
docker\s+system\s+prune\s+--all\s+--force
```

### Filesystem Operations
```regex
# Dangerous rm patterns
rm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-rf|-fr)\s+/(?!tmp/|var/tmp/)
rm\s+-rf\s+\*
rm\s+--recursive\s+--force\s+/

# Find with delete
find\s+.+\s+-delete
find\s+.+\s+-exec\s+rm\s+

# Format operations
mkfs\.(ext[234]|xfs|btrfs|ntfs)\s+/dev/
```

### Service Management
```regex
# Bulk service operations
systemctl\s+(stop|disable|restart)\s+\*\.service
systemctl\s+(stop|disable|restart)\s+.+\s+.+\s+.+
service\s+.+\s+(stop|restart)\s+\|\s+xargs

# Critical service operations
systemctl\s+(stop|disable)\s+(ssh|sshd|systemd|docker|postgresql)
```

### ZFS Operations
```regex
# Pool destruction
zpool\s+destroy\s+(-f\s+)?\w+
zfs\s+destroy\s+(-r\s+)?\w+/\w+

# Snapshot bulk operations
zfs\s+destroy\s+\w+@\w+%
zfs\s+list\s+-t\s+snapshot\s+\|\s+.+\s+\|\s+xargs\s+zfs\s+destroy
```

## 🎛️ Device-Specific Protection Rules

### Unraid Server Protection
```python
"unraid": {
    "max_bulk_operations": 5,
    "protected_paths": ["/mnt/user/", "/mnt/disk", "/boot/"],
    "critical_services": ["nginx", "php-fpm", "shfs", "mover"],
    "environment_type": "production",
    "special_checks": ["parity_operations", "array_status"]
}
```

### Ubuntu Server Protection
```python
"ubuntu": {
    "max_bulk_operations": 15,
    "protected_paths": ["/etc/", "/var/lib/docker", "/home/"],
    "critical_services": ["ssh", "systemd", "docker", "postgresql"],
    "environment_type": "production",
    "special_checks": ["package_locks", "service_dependencies"]
}
```

### WSL2 Development Protection
```python
"wsl2": {
    "max_bulk_operations": 25,
    "protected_paths": ["/mnt/c/"],
    "critical_services": ["docker"],
    "environment_type": "development",
    "special_checks": ["windows_interop"]
}
```

### Windows Docker Desktop Protection
```python
"windows": {
    "max_bulk_operations": 8,
    "protected_paths": ["C:\\Windows", "C:\\Program Files\\Docker"],
    "critical_services": ["Docker Desktop Service"],
    "environment_type": "development",
    "special_checks": ["hyper_v_status"]
}
```

## 📊 Risk Assessment Matrix

### Risk Levels
| Level | Criteria | Examples |
|-------|----------|----------|
| **LOW** | Single item, dev environment | `docker stop container1` |
| **MEDIUM** | Multiple items, or protected paths | `rm -rf /tmp/logs` |
| **HIGH** | Bulk operations, production env | `docker stop $(docker ps -q)` |
| **CRITICAL** | Irreversible, system-wide impact | `zpool destroy tank` |

### Risk Escalation Factors
- **Environment**: Production environments automatically escalate risk
- **Scale**: Operations affecting more than device threshold (5-25 items)
- **Protected Resources**: Operations affecting critical paths or services
- **Irreversibility**: Operations that cannot be undone (ZFS destroy, format)

## 🔄 Confirmation Workflow

### Dynamic Phrase Generation
```python
# Example generated phrases:
"yes, destroy 15 items via container_bulk_remove on production-server at 0541"
"yes, execute zfs_pool_destroy on storage-node at critical risk at 1423"
"yes, destroy 8 items via service_bulk_stop on web-server at 0756"
```

### Confirmation Process
1. **Action Detected** → Pattern matches destructive command
2. **Risk Assessed** → Context analysis with blast radius estimation
3. **Action Blocked** → Operation blocked with unique ID
4. **User Prompted** → Detailed confirmation instructions provided
5. **Phrase Required** → User must type exact confirmation phrase
6. **Validation** → Multi-attempt validation with rate limiting
7. **Execution** → Confirmed actions proceed with audit trail

### Confirmation Instructions Format
```
🚨 DESTRUCTIVE ACTION DETECTED

Action: container_bulk_remove
Risk Level: HIGH
Impact: This operation will affect 15 items including: container-0, container-1, container-2 and 12 more

⚠️  WARNINGS:
   ⚠️  PRODUCTION ENVIRONMENT - This action will affect live systems
   ⚠️  BULK OPERATION - This will affect 15 items (limit: 5)

💡 SAFER ALTERNATIVES:
   • Remove containers individually: docker rm <container_name>
   • Use docker container prune with filters
   • Stop containers first, then remove

📋 SAFETY CHECKLIST:
   [ ] I have read and understood the impact summary
   [ ] I have verified this is the correct device and environment
   [ ] I have checked that dependent services can handle this downtime
   [ ] I have notified relevant team members if applicable

To proceed, you must type the following phrase EXACTLY:
"yes, destroy 15 items via container_bulk_remove on production-server at 0541"
```

## 🛠️ Integration Examples

### API Integration
```python
from src.services.safety import (
    DestructiveActionDetector,
    DestructiveActionManager,
    CacheManager
)

# Initialize components
cache_manager = CacheManager()
await cache_manager.start()
detector = DestructiveActionDetector()
action_manager = DestructiveActionManager(cache_manager)

# Analyze potentially dangerous command
device_context = {
    "hostname": "web-server",
    "os_type": "ubuntu", 
    "environment": "production",
    "running_container_count": 15
}

# Check if command is destructive
analysis = await detector.analyze_command(
    "docker rm -f $(docker ps -aq)", 
    device_context
)

if analysis:
    # Block and require confirmation
    confirmation_response = await action_manager.block_and_require_confirmation(
        analysis, 
        {"user_agent": "web-interface", "user_id": "admin"}
    )
    
    # Return blocking response to user
    return {
        "blocked": True,
        "operation_id": confirmation_response["operation_id"],
        "confirmation_phrase": confirmation_response["confirmation_phrase"],
        "instructions": confirmation_response["confirmation_instructions"]
    }
```

### MCP Tool Integration
```python
@mcp_tool("confirm_destructive_action")
async def confirm_destructive_action(
    operation_id: str, 
    confirmation_phrase: str
) -> dict:
    """Confirm a previously blocked destructive action."""
    
    result = await action_manager.process_confirmation(
        operation_id, 
        confirmation_phrase,
        {"user_agent": "mcp-client"}
    )
    
    if result["status"] == "confirmed":
        # Execute the original command safely
        return await execute_confirmed_operation(result["analysis"])
    else:
        return result  # Return error details
```

## 📈 Monitoring and Analytics

### Key Metrics
- **Detection Rate**: Commands analyzed vs. destructive patterns matched
- **Confirmation Success Rate**: Successful confirmations vs. failed attempts
- **Risk Distribution**: Breakdown by risk level (LOW/MEDIUM/HIGH/CRITICAL)
- **Device Activity**: Most active devices and action types
- **User Behavior**: Users requiring most confirmations

### Audit Trail Fields
```python
{
    "timestamp": "2024-01-15T14:30:45Z",
    "operation_id": "op_abc123",
    "action_type": "container_bulk_remove", 
    "risk_level": "HIGH",
    "device_hostname": "production-server",
    "user_context": {"user_id": "admin", "source_ip": "192.168.1.100"},
    "command": "docker rm -f $(docker ps -aq)",
    "blast_radius": {"estimated_count": 15, "affected_items": ["container-0", "container-1"]},
    "confirmation_attempts": 2,
    "status": "executed",
    "execution_duration": 8.2
}
```

## 🔧 Configuration Options

### Cache Settings
```python
CONFIRMATION_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_CONFIRMATION_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 60  # 1 minute
RATE_LIMIT_MAX_ATTEMPTS = 10
```

### Detection Sensitivity
```python
PATTERN_MATCH_FLAGS = re.IGNORECASE | re.MULTILINE
FALSE_POSITIVE_THRESHOLD = 0.95
MINIMUM_RISK_FOR_BLOCKING = "MEDIUM"
```

### Device-Specific Overrides
```python
DEVICE_OVERRIDES = {
    "test-server": {
        "min_risk_level": "HIGH",  # Only block HIGH/CRITICAL on test server
        "confirmation_timeout": 600  # 10 minutes for test environment
    }
}
```

## 🚨 Emergency Procedures

### Bypassing Protection (Emergency Only)
```bash
# Emergency bypass (requires admin privileges)
export DESTRUCTIVE_ACTION_BYPASS="emergency-$(date +%s)"
# Command will execute without confirmation
```

### Recovery from Failed Operations
```bash
# Check operation status
operation_status op_abc123

# Cancel pending operation
cancel_operation op_abc123

# View audit trail
audit_trail --operation-id op_abc123
```

## 📚 Best Practices

### For Administrators
1. **Review Patterns Regularly**: Ensure patterns catch new dangerous command variations
2. **Monitor False Positives**: Adjust patterns that incorrectly flag safe commands
3. **Audit Trail Analysis**: Regularly review blocked actions for security insights
4. **Device Rule Tuning**: Adjust protection rules based on environment needs

### For Users
1. **Read Warnings Carefully**: Understand the full impact before confirming
2. **Use Alternatives**: Consider suggested safer alternatives when available
3. **Check Environment**: Verify you're operating on the intended device/environment
4. **Plan for Downtime**: Ensure dependent services can handle the disruption

### For Developers
1. **Test Integration**: Thoroughly test the confirmation workflow in your tools
2. **Handle Timeouts**: Implement proper timeout handling for blocked operations
3. **User Experience**: Provide clear feedback when operations are blocked
4. **Error Handling**: Gracefully handle confirmation failures and retries

---

## 📞 Support and Troubleshooting

### Common Issues

**Issue**: Command not detected as destructive
- **Solution**: Check if pattern exists in DESTRUCTIVE_COMMAND_PATTERNS
- **Debug**: Enable pattern matching logs

**Issue**: Confirmation phrase validation fails
- **Solution**: Copy phrase exactly including timestamps
- **Debug**: Check for extra spaces or case differences

**Issue**: Operation times out
- **Solution**: Operations expire after 5 minutes by default
- **Debug**: Check cache TTL settings

### Debug Commands
```bash
# List active operations
list_pending_operations

# Check pattern matching
test_pattern_detection "your command here"

# Validate confirmation phrase
validate_phrase op_abc123 "your phrase here"
```

This documentation provides comprehensive coverage of the Destructive Action Protection System's patterns, configuration, and usage guidelines for safe infrastructure management.