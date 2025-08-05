# **Phase 3: Destructive Action Protection System ⭐ (Weeks 5-6)**

This phase introduces the **tentpole feature** of the infrastructure management platform: a multi-layered, device-aware safety system designed to prevent accidental and catastrophic infrastructure changes. It transforms potentially dangerous operations into safe, auditable, and confirmation-based workflows.

## **TENTPOLE FEATURE: Multi-layered Safety System**

This section details the core components of the protection system, from detecting dangerous commands to managing the entire confirmation and execution lifecycle.

### **48. Create `DestructiveActionDetector` with sophisticated pattern recognition**

**Objective:** To accurately identify potentially destructive operations from raw command strings or high-level API calls before they are executed.

**Architecture:** A `DestructiveActionDetector` class will serve as the primary entry point for the safety system. It will use a registry of regular expressions tailored to common CLI tools (`docker`, `rm`, `systemctl`, `zpool`) and infrastructure patterns. The detector will not just match commands but also analyze arguments to differentiate between single-target operations and bulk, wildcard-based destructive actions.

```python
# apps/backend/src/services/safety/destructive_action_detector.py

import re
from typing import Optional, Dict, Any, List
from enum import Enum

class DestructiveActionType(Enum):
    """Enumeration of all detectable destructive action types."""
    CONTAINER_BULK_STOP = "container_bulk_stop"
    CONTAINER_BULK_REMOVE = "container_bulk_remove"
    SYSTEM_PRUNE = "system_prune"
    SERVICE_BULK_DISABLE = "service_bulk_disable"
    FILESYSTEM_BULK_DELETE = "filesystem_bulk_delete"
    ZFS_POOL_DESTROY = "zfs_pool_destroy"
    SYSTEM_REBOOT = "system_reboot"
    SYSTEM_SHUTDOWN = "system_shutdown"
    # ... add all 16+ types

class DestructiveActionDetector:
    """Analyzes commands to detect potentially destructive operations."""

    # This will be expanded significantly in the next task
    DESTRUCTIVE_PATTERNS = {
        DestructiveActionType.CONTAINER_BULK_STOP: [
            r"docker\s+stop\s+\$\(docker\s+ps\s+-q\)",
            r"docker-compose\s+down"
        ],
        DestructiveActionType.CONTAINER_BULK_REMOVE: [
            r"docker\s+rm\s+-f\s+\$\(docker\s+ps\s+-aq\)",
            r"docker\s+system\s+prune\s+-af"
        ],
        DestructiveActionType.FILESYSTEM_BULK_DELETE: [
            r"rm\s+-rf\s+/(?!tmp|var/tmp)"
        ],
        DestructiveActionType.SYSTEM_REBOOT: [
            r"\breboot\b",
            r"shutdown\s+-r"
        ],
        DestructiveActionType.SYSTEM_SHUTDOWN: [
            r"\bpoweroff\b",
            r"\bhalt\b",
            r"shutdown\s+-h"
        ],
    }

    def __init__(self, risk_assessment_engine):
        self.risk_assessment_engine = risk_assessment_engine

    async def analyze_command(self, command: str, device_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyzes a command and, if destructive, returns a full risk analysis.

        Args:
            command: The command string to analyze.
            device_context: Rich context about the target device, including OS,
                            running services, environment (prod/dev), etc.

        Returns:
            A dictionary containing the full analysis and confirmation requirements,
            or None if the command is deemed safe.
        """
        for action_type, patterns in self.DESTRUCTIVE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    # Pattern matched, now perform a deep risk analysis
                    analysis = await self.risk_assessment_engine.assess(
                        action_type, command, device_context
                    )
                    
                    # Only block if the risk is above a certain threshold
                    if analysis.get("requires_confirmation"):
                        return analysis
        
        return None
```

### **49. Implement command pattern analysis for 16+ destructive action types**

**Objective:** To build a comprehensive and robust library of patterns that can detect a wide range of dangerous commands with high accuracy.

**Architecture:** The `DESTRUCTIVE_PATTERNS` dictionary within the `DestructiveActionDetector` will be significantly expanded. Each pattern will be crafted to be specific enough to avoid false positives but broad enough to catch variations. The patterns will cover `docker`, `docker-compose`, `systemd`, `service`, `rm`, `find`, `zfs`, `zpool`, `reboot`, `shutdown`, `poweroff`, `halt`, `mkfs`, and more.

```python
# apps/backend/src/services/safety/patterns.py

# This dictionary will be the central registry for all destructive patterns.
# It's separated into its own file for maintainability.

DESTRUCTIVE_COMMAND_PATTERNS = {
    # Container Operations
    "CONTAINER_BULK_STOP": [r"docker\s+stop\s+`docker\s+ps\s+-q`", r"docker\s+stop\s+\$\(docker\s+ps\s+-q\)", r"docker-compose\s+down"],
    "CONTAINER_BULK_REMOVE": [r"docker\s+rm\s+-f\s+\$\(docker\s+ps\s+-aq\)", r"docker\s+container\s+prune\s+-f"],
    "IMAGE_BULK_REMOVE": [r"docker\s+image\s+prune\s+-af"],
    "VOLUME_BULK_REMOVE": [r"docker\s+volume\s+prune\s+-f"],
    "NETWORK_BULK_REMOVE": [r"docker\s+network\s+prune\s+-f"],
    "SYSTEM_PRUNE": [r"docker\s+system\s+prune\s+-af"],

    # Filesystem Operations
    "FILESYSTEM_BULK_DELETE": [r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*|-rf)\s+/\w*", r"find\s+.+\s+-delete"],
    "FILESYSTEM_FORMAT": [r"mkfs\.(ext4|xfs|btrfs)\s+/dev/sd[a-z]+"],
    
    # Service Management
    "SERVICE_BULK_STOP": [r"systemctl\s+stop\s+\*\.service", r"service\s+--status-all\s+\|\s+awk\s+\{\s*print\s+\$3\s*\}\s+\|\s+xargs\s+-I\{\}\s+service\s+\{\}\s+stop"],
    "SERVICE_BULK_DISABLE": [r"systemctl\s+disable\s+--now\s+\*\.service"],

    # ZFS Operations
    "ZFS_POOL_DESTROY": [r"zpool\s+destroy\s+-f\s+\w+"],
    "ZFS_DATASET_DESTROY": [r"zfs\s+destroy\s+-r\s+\w+/\w+"],
    
    # System Power Operations
    "SYSTEM_REBOOT": [r"\breboot\b", r"shutdown\s+-r", r"systemctl\s+reboot"],
    "SYSTEM_SHUTDOWN": [r"shutdown\s+-h\s+now", r"\bpoweroff\b", r"\bhalt\b", r"systemctl\s+poweroff"],
    
    # Networking
    "FIREWALL_FLUSH": [r"iptables\s+-F", r"ufw\s+reset"],
    
    # User Management
    "USER_BULK_DELETE": [r"deluser\s+--remove-all-files"]
}
```

### **50. Create risk assessment engine with device-specific protection rules**

**Objective:** To assess the true risk of a detected action by considering the context of the target device. A `docker system prune` is low-risk on a WSL2 dev environment but critical on a production Unraid server.

**Architecture:** A `RiskAssessmentEngine` will be created. When the detector finds a match, it will pass the action type and device context to this engine. The engine will:
1.  Load a set of device-specific protection rules (see Task 52).
2.  Estimate the "blast radius" (e.g., how many containers will be stopped, which services will be affected).
3.  Combine this information to assign a `RiskLevel` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
4.  Generate a summary, warnings, and determine if confirmation is required.

```python
# apps/backend/src/services/safety/risk_assessment_engine.py

from .rules import DEVICE_PROTECTION_RULES

class RiskAssessmentEngine:
    async def assess(self, action_type: DestructiveActionType, command: str, device_context: Dict) -> Dict:
        """
        Performs a detailed risk analysis of a destructive action.
        """
        device_type = device_context.get("os_type", "ubuntu")
        rules = DEVICE_PROTECTION_RULES.get(device_type, {})
        
        # Estimate blast radius
        blast_radius = await self._estimate_blast_radius(action_type, device_context)
        
        # Determine risk level
        risk_level = self._calculate_risk_level(action_type, blast_radius, device_context, rules)
        
        # Generate safety warnings
        warnings = self._generate_warnings(action_type, blast_radius, device_context, rules)
        
        return {
            "action_type": action_type.value,
            "risk_level": risk_level,
            "impact_summary": f"This action will affect {blast_radius['count']} items, including: {', '.join(blast_radius['examples'][:3])}",
            "affected_count": blast_radius["count"],
            "safety_warnings": warnings,
            "requires_confirmation": risk_level in ["MEDIUM", "HIGH", "CRITICAL"],
        }

    async def _estimate_blast_radius(self, action_type, context) -> Dict:
        # In a real implementation, this would query the UnifiedDataCollectionService
        # to get live data (e.g., list of running containers).
        if action_type in [DestructiveActionType.CONTAINER_BULK_STOP, DestructiveActionType.CONTAINER_BULK_REMOVE]:
            count = context.get("running_container_count", 10)
            return {"count": count, "examples": [f"container-{i}" for i in range(count)]}
        return {"count": 1, "examples": ["unknown_resource"]}

    def _calculate_risk_level(self, action_type, blast_radius, context, rules) -> str:
        if context.get("environment") == "production":
            return "CRITICAL"
        if blast_radius["count"] > rules.get("max_bulk_operations", 10):
            return "HIGH"
        if blast_radius["count"] > 3:
            return "MEDIUM"
        return "LOW"

    def _generate_warnings(self, action_type, blast_radius, context, rules) -> List[str]:
        warnings = []
        if context.get("environment") == "production":
            warnings.append("⚠️ This is a PRODUCTION environment.")
        
        protected_items = rules.get("protected_items", [])
        affected_protected = [item for item in blast_radius["examples"] if any(p in item for p in protected_items)]
        if affected_protected:
            warnings.append(f"Action affects protected resources: {', '.join(affected_protected)}")
            
        return warnings
```

### **51. Implement `DestructiveActionManager` with multi-step confirmation flows**

**Objective:** To manage the entire lifecycle of a blocked destructive action, from generating the confirmation prompt to processing the user's response.

**Architecture:** A `DestructiveActionManager` will be the central state machine.
1.  When an action is blocked, it generates a unique `operation_id` and stores the analysis results and context in a temporary cache (e.g., Redis) with a TTL.
2.  It formats a detailed, user-friendly response explaining the risk, the impact, and the exact phrase required for confirmation.
3.  It provides a separate `confirm_destructive_action` tool/endpoint that takes the `operation_id` and confirmation phrase.
4.  It validates the phrase, checks for timeouts, and manages retry attempts.

```python
# apps/backend/src/services/safety/action_manager.py

import time
import uuid

class DestructiveActionManager:
    def __init__(self, cache_service):
        self.cache = cache_service # Redis-backed cache
        self.confirmation_timeout_sec = 300 # 5 minutes

    async def block_and_require_confirmation(self, analysis: Dict) -> Dict:
        """
        Blocks an action and returns a structured response demanding confirmation.
        """
        operation_id = f"op_{uuid.uuid4()}"
        confirmation_phrase = self._generate_confirmation_phrase(analysis)
        
        # Store the context for later confirmation
        await self.cache.set(
            f"destructive_op:{operation_id}",
            {"analysis": analysis, "confirmation_phrase": confirmation_phrase},
            expire=self.confirmation_timeout_sec
        )
        
        analysis["operation_id"] = operation_id
        analysis["confirmation_phrase"] = confirmation_phrase
        analysis["expires_in_sec"] = self.confirmation_timeout_sec
        
        return analysis

    async def process_confirmation(self, operation_id: str, user_phrase: str) -> Dict:
        """
        Processes a user's confirmation attempt.
        """
        stored_op = await self.cache.get(f"destructive_op:{operation_id}")
        if not stored_op:
            return {"status": "error", "message": "Operation not found or expired."}

        if user_phrase.lower().strip() != stored_op["confirmation_phrase"].lower().strip():
            return {"status": "error", "message": "Confirmation phrase does not match."}
            
        # Confirmation successful, remove from cache and return context for execution
        await self.cache.delete(f"destructive_op:{operation_id}")
        return {"status": "confirmed", "analysis": stored_op["analysis"]}

    def _generate_confirmation_phrase(self, analysis: Dict) -> str:
        return f"yes, i am sure i want to {analysis['action_type']} on {analysis.get('device_name', 'device')}"
```

### **52. Create device-specific protection rules (Unraid, Ubuntu, WSL2, Windows)**

**Objective:** To encode expert knowledge about different operating systems and environments into a structured rule set that the `RiskAssessmentEngine` can use.

**Architecture:** A Python dictionary or YAML file (`device_rules.py` or `device_rules.yaml`) will define the protection rules. This configuration-as-code approach makes the rules easy to read, maintain, and extend. The rules will specify things like protected paths, critical service names, and thresholds for bulk operations.

```python
# apps/backend/src/services/safety/rules.py

DEVICE_PROTECTION_RULES = {
    "unraid": {
        "max_bulk_operations": 5,
        "protected_paths": ["/mnt/user/", "/mnt/disk", "/boot/"],
        "critical_services": ["nginx", "php-fpm", "shfs", "mover"],
        "pre_flight_checks": ["check_array_status", "check_parity_operation"],
    },
    "ubuntu": {
        "max_bulk_operations": 15,
        "protected_paths": ["/etc/", "/var/lib/docker"],
        "critical_services": ["ssh", "systemd", "docker", "postgresql"],
        "pre_flight_checks": ["check_package_manager_lock"],
    },
    "wsl2": {
        "max_bulk_operations": 10,
        "protected_paths": ["/mnt/c/"],
        "critical_services": ["docker"],
        "pre_flight_checks": [], # Less stringent checks for dev environments
    },
    "windows": {
        "max_bulk_operations": 3,
        "protected_paths": ["C:\\Windows"],
        "critical_services": ["Docker Desktop Service"],
        "pre_flight_checks": [],
    }
}
```

### **53. Implement confirmation phrase generation and validation system**

**Objective:** To ensure the user has read and understood the risk by requiring them to type a specific, dynamically generated phrase.

**Architecture:** The `DestructiveActionManager` will generate this phrase. It will be constructed from key elements of the risk analysis, such as the action type, the number of affected items, and the device name. This makes it unique to each operation, preventing accidental confirmation via command history. The validation is a simple but case-insensitive string comparison.

### **54. Create safety checklist generation for pre-execution validation**

**Objective:** To guide the user through a mental checklist of best practices before they confirm a high-risk action.

**Architecture:** The `RiskAssessmentEngine` will generate a dynamic checklist based on the action and device context. For example, a `ZFS_POOL_DESTROY` action would generate a checklist item: `[ ] Have you backed up all data on this pool?`. This checklist is for display purposes in the confirmation prompt to encourage safer practices.

### **55. Implement alternative action suggestion engine**

**Objective:** To help users achieve their goals more safely by suggesting less destructive alternatives.

**Architecture:** A suggestion engine, likely a function within the `RiskAssessmentEngine`, will map destructive action types to safer alternatives. For `CONTAINER_BULK_STOP`, it might suggest stopping containers one by one or by a `docker-compose` project name. For `rm -rf`, it might suggest `mv` to a trash directory.

### **56. Create impact analysis with service dependency mapping**

**Objective:** To provide a more accurate impact assessment by understanding the relationships between services.

**Architecture:** This task integrates the `DependencyService` (from Phase 2) into the `RiskAssessmentEngine`. When assessing the impact of stopping a container (e.g., a database), the engine will query the dependency graph to identify all other services that rely on it, adding them to the list of affected services and increasing the risk score.

### **57. Implement timeout and attempt limiting for confirmation processes**

**Objective:** To enhance security by preventing confirmation prompts from lingering indefinitely and to thwart brute-force confirmation attempts.

**Architecture:** This is handled by the `DestructiveActionManager`. The use of a Redis cache with a `TTL` (Time To Live) naturally handles the timeout. The manager will also store an attempt counter within the cached data, incrementing it on each failed confirmation and deleting the entry if the maximum number of attempts is reached.

### **58. Create audit trail for all destructive action attempts and confirmations**

**Objective:** To maintain a complete, immutable log of all high-risk operations for security audits and incident reviews.

**Architecture:** A new `AuditService` will be created with a dedicated `destructive_actions_log` table. The `DestructiveActionManager` will log every stage of the process:
1.  `action_blocked`: When an action is first detected and blocked.
2.  `confirmation_failed`: When a user provides an incorrect phrase.
3.  `confirmation_expired`: When the timeout is reached.
4.  `action_confirmed`: When the user successfully confirms.
5.  `action_executed`: When the command is finally sent for execution.

### **59. Implement automatic rollback plan generation**

**Objective:** To prepare for the worst-case scenario by automatically generating a plan to undo a destructive action, where possible.

**Architecture:** The `RiskAssessmentEngine` will generate a rollback plan as part of its analysis.
*   For a `CONTAINER_BULK_STOP`, the plan is simple: a list of `docker start <container_id>` commands.
*   For a `FILESYSTEM_BULK_DELETE`, rollback might be impossible, which would be noted in the plan (`"rollback_possible": false`), increasing the risk score.
*   For a configuration change, it would involve restoring the previous `ConfigurationSnapshot`.

### **60. Create destructive action recovery procedures and validation**

**Objective:** To provide tools and automated procedures to recover from a destructive action, whether it was confirmed accidentally or had unintended consequences.

**Architecture:** This involves creating a `RecoveryService` and a new set of `recover_*` MCP tools. For example, a `recover_stopped_containers` tool would take an `operation_id` from the audit log, retrieve the list of containers that were stopped, and execute the `docker start` commands from the generated rollback plan.

### **61. Implement escalation procedures for failed confirmations**

**Objective:** To alert administrators when a user repeatedly fails to confirm a high-risk action, which could indicate a confused user or a potential security incident.

**Architecture:** The `DestructiveActionManager`, upon reaching the maximum confirmation attempts, will not only delete the pending operation but also fire an event to the `NotificationService`. The `NotificationService` will have a specific policy for `confirmation_failed_max_attempts` events, likely triggering a high-priority alert to an admin channel.

### **62. Create destructive action reporting and analytics**

**Objective:** To provide insights into how often destructive actions are attempted, by whom, and on which devices, helping to identify operational hotspots or training needs.

**Architecture:** This involves creating API endpoints and a service to query the `destructive_actions_log` table. It can generate reports on:
*   Most frequently blocked actions.
*   Users who most frequently trigger the protection system.
*   Devices that are common targets of risky operations.
*   Confirmation success/failure rates.

---

## **Device-Aware Protection Features**

This section details the implementation of specific protection rules for different environments, making the safety system contextually intelligent.

### **63. Implement Unraid-specific protection (parity operations, array status)**

**Objective:** To prevent operations that could corrupt the Unraid array or interfere with critical array operations like parity checks.

**Architecture:** A `check_unraid_parity_status` function will be added to the `RiskAssessmentEngine`. Before allowing a container or disk operation, it will execute `mdcmd status` via SSH. If a parity check, rebuild, or clear operation is running, it will add a critical warning and may automatically block the action.

### **64. Create Ubuntu server protection rules (critical services, package locks)**

**Objective:** To protect the core services and package management system of a standard Ubuntu server.

**Architecture:** The `DEVICE_PROTECTION_RULES` for `ubuntu` will list critical services like `ssh`, `systemd`, and `docker`. The `RiskAssessmentEngine` will also implement a check for `fuser /var/lib/dpkg/lock` to see if `apt` is running, preventing conflicting operations.

### **65. Implement WSL2 development environment protection**

**Objective:** To provide a less stringent but still safe set of rules for development environments running under WSL2, recognizing that developers need more flexibility.

**Architecture:** The `wsl2` rules will have a higher `max_bulk_operations` threshold and fewer critical services listed. It will add specific checks to avoid disrupting the WSL2 interop services (`/init`) or the Windows filesystem mounted at `/mnt/c`.

### **66. Create Windows Docker Desktop protection mechanisms**

**Objective:** To tailor protection to the specifics of Docker Desktop on Windows, which has a different architecture from Docker on Linux.

**Architecture:** The `windows` rules will recognize that `Docker Desktop Service` is the single most critical service. It will also understand that filesystem operations need to be handled with care due to NTFS permissions and the Hyper-V virtual disk.

### **67. Implement ZFS pool and dataset protection logic**

**Objective:** To prevent the accidental destruction of ZFS pools and datasets, which is an irreversible action.

**Architecture:** The `ZFS_POOL_DESTROY` and `ZFS_DATASET_DESTROY` action types will be hard-coded to have a `CRITICAL` risk level. The `RiskAssessmentEngine` will attempt to get a list of snapshots for the target dataset and warn the user that all snapshots will also be destroyed, adding this to the impact summary.

### **68. Create container orchestration safety validation**

**Objective:** To add a layer of safety for `docker-compose` operations, such as warning against `down` commands that would remove persistent volumes.

**Architecture:** The `RiskAssessmentEngine`'s `_analyze_container_bulk_action` method will be enhanced. When it detects `docker-compose down`, it will parse the corresponding `docker-compose.yml` file and check if any volumes are defined as `external: false`. If so, it will add a critical warning that persistent data will be lost.

### **69. Implement service dependency chain protection**

**Objective:** To prevent a user from stopping a service without understanding the full downstream impact.

**Architecture:** This integrates the `DependencyService` into the safety system. When a user tries to stop a service (e.g., a database container), the `RiskAssessmentEngine` will query for all downstream dependencies and list them in the impact summary, providing a much clearer picture of the potential outage.

### **70. Create backup validation before destructive operations**

**Objective:** To ensure a valid backup exists before allowing a potentially data-destroying operation.

**Architecture:** A new `BackupService` will be created to track the status of system backups. The `RiskAssessmentEngine` will call this service as a pre-flight check for actions like `ZFS_POOL_DESTROY` or `FILESYSTEM_FORMAT`. If no recent, successful backup is found for the target resource, it will add a critical warning to the confirmation prompt, and for the highest-risk actions, it may block them entirely until a backup is completed.