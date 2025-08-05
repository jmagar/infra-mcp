"""
Rollback Plan Generator

Automatically generates rollback/recovery plans for destructive operations
to enable quick recovery if something goes wrong.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .patterns import DestructiveActionType

logger = logging.getLogger(__name__)


class RollbackCapability(Enum):
    """Capability levels for rollback operations."""

    FULL = "full"  # Complete rollback possible
    PARTIAL = "partial"  # Limited rollback possible
    IMPOSSIBLE = "impossible"  # Cannot be rolled back
    COMPLEX = "complex"  # Requires manual intervention


class RollbackPlanGenerator:
    """
    Generates automatic rollback plans for destructive operations.

    Features:
    - Action-specific rollback strategies
    - Device context awareness
    - Pre-operation state capture
    - Step-by-step recovery instructions
    - Risk assessment for rollback operations
    """

    def __init__(self):
        """Initialize the rollback plan generator."""
        logger.info("RollbackPlanGenerator initialized")

    async def generate_rollback_plan(
        self,
        action_type: DestructiveActionType,
        command: str,
        device_context: dict[str, Any],
        blast_radius: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a comprehensive rollback plan for a destructive action.

        Args:
            action_type: The type of destructive action
            command: The original destructive command
            device_context: Device and environment context
            blast_radius: Impact analysis results

        Returns:
            Complete rollback plan with instructions and metadata
        """
        logger.info(f"Generating rollback plan for {action_type.value}")

        # Determine rollback capability
        rollback_capability = self._assess_rollback_capability(action_type, command, device_context)

        # Generate action-specific rollback steps
        rollback_steps = await self._generate_rollback_steps(
            action_type, command, device_context, blast_radius
        )

        # Generate pre-operation data capture requirements
        pre_operation_capture = self._generate_capture_requirements(
            action_type, device_context, blast_radius
        )

        # Assess rollback risks
        rollback_risks = self._assess_rollback_risks(action_type, rollback_steps, device_context)

        # Generate recovery time estimate
        recovery_estimate = self._estimate_recovery_time(action_type, rollback_steps, blast_radius)

        plan = {
            "rollback_capability": rollback_capability.value,
            "rollback_possible": rollback_capability != RollbackCapability.IMPOSSIBLE,
            "rollback_steps": rollback_steps,
            "pre_operation_capture": pre_operation_capture,
            "rollback_risks": rollback_risks,
            "recovery_time_estimate": recovery_estimate,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "plan_version": "1.0",
            "requires_manual_intervention": rollback_capability == RollbackCapability.COMPLEX,
            "automation_level": self._determine_automation_level(
                rollback_capability, rollback_steps
            ),
        }

        logger.info(
            f"Rollback plan generated: {rollback_capability.value} rollback with "
            f"{len(rollback_steps)} steps"
        )

        return plan

    def _assess_rollback_capability(
        self,
        action_type: DestructiveActionType,
        command: str,
        device_context: dict[str, Any],
    ) -> RollbackCapability:
        """Assess how well the operation can be rolled back."""

        # Impossible rollbacks - data destruction
        if action_type in [
            DestructiveActionType.ZFS_POOL_DESTROY,
            DestructiveActionType.FILESYSTEM_WIPE,
            DestructiveActionType.FILESYSTEM_FORMAT,
        ]:
            return RollbackCapability.IMPOSSIBLE

        # Full rollbacks - easily reversible
        if action_type in [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_DISABLE,
        ]:
            return RollbackCapability.FULL

        # Partial rollbacks - some limitations
        if action_type in [
            DestructiveActionType.CONTAINER_BULK_REMOVE,
            DestructiveActionType.VOLUME_BULK_REMOVE,
            DestructiveActionType.NETWORK_BULK_REMOVE,
        ]:
            return RollbackCapability.PARTIAL

        # Complex rollbacks - need manual work
        if action_type in [
            DestructiveActionType.SYSTEM_REBOOT,
            DestructiveActionType.SYSTEM_SHUTDOWN,
            DestructiveActionType.SYSTEM_PRUNE,
        ]:
            return RollbackCapability.COMPLEX

        # Default to partial for unknown operations
        return RollbackCapability.PARTIAL

    async def _generate_rollback_steps(
        self,
        action_type: DestructiveActionType,
        command: str,
        device_context: dict[str, Any],
        blast_radius: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate specific rollback steps for the action type."""

        steps = []

        if action_type == DestructiveActionType.CONTAINER_BULK_STOP:
            steps = await self._generate_container_restart_steps(blast_radius, device_context)

        elif action_type == DestructiveActionType.CONTAINER_BULK_REMOVE:
            steps = await self._generate_container_recreation_steps(blast_radius, device_context)

        elif action_type in [
            DestructiveActionType.SERVICE_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_DISABLE,
        ]:
            steps = await self._generate_service_restart_steps(
                action_type, blast_radius, device_context
            )

        elif action_type == DestructiveActionType.SYSTEM_PRUNE:
            steps = await self._generate_system_restore_steps(blast_radius, device_context)

        elif action_type in [
            DestructiveActionType.SYSTEM_REBOOT,
            DestructiveActionType.SYSTEM_SHUTDOWN,
        ]:
            steps = await self._generate_system_recovery_steps(action_type, device_context)

        elif action_type == DestructiveActionType.FILESYSTEM_BULK_DELETE:
            steps = await self._generate_file_recovery_steps(blast_radius, device_context)

        else:
            # Generic rollback steps
            steps = [
                {
                    "step_number": 1,
                    "action": "manual_assessment",
                    "description": f"Manually assess the impact of {action_type.value}",
                    "command": None,
                    "automation_possible": False,
                    "estimated_duration": 300,  # 5 minutes
                    "risk_level": "medium",
                }
            ]

        return steps

    async def _generate_container_restart_steps(
        self, blast_radius: dict[str, Any], device_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate steps to restart stopped containers."""
        affected_items = blast_radius.get("affected_items", [])
        steps = []

        for i, container in enumerate(affected_items):
            steps.append(
                {
                    "step_number": i + 1,
                    "action": "container_start",
                    "description": f"Restart container {container}",
                    "command": f"docker start {container}",
                    "automation_possible": True,
                    "estimated_duration": 30,  # 30 seconds per container
                    "risk_level": "low",
                    "dependencies": [],
                    "validation_command": f"docker ps --filter name={container} --format '{{.Status}}'",
                    "expected_result": "Up ",
                }
            )

        # Add dependency ordering if we have service dependency info
        if blast_radius.get("service_dependencies"):
            steps = self._add_dependency_ordering(steps, blast_radius["service_dependencies"])

        return steps

    async def _generate_container_recreation_steps(
        self, blast_radius: dict[str, Any], device_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate steps to recreate removed containers."""
        affected_items = blast_radius.get("affected_items", [])
        steps = []

        # Warning step about data loss
        steps.append(
            {
                "step_number": 1,
                "action": "warning",
                "description": "⚠️ Container recreation may result in data loss for non-persistent volumes",
                "command": None,
                "automation_possible": False,
                "estimated_duration": 0,
                "risk_level": "high",
            }
        )

        # Pre-capture step
        steps.append(
            {
                "step_number": 2,
                "action": "capture_container_configs",
                "description": "Capture container configurations before removal",
                "command": "docker inspect $(docker ps -aq) > /tmp/container_configs_backup.json",
                "automation_possible": True,
                "estimated_duration": 60,
                "risk_level": "low",
            }
        )

        # Note about limited rollback capability
        steps.append(
            {
                "step_number": 3,
                "action": "manual_recreation",
                "description": "Container recreation requires original docker run commands or compose files",
                "command": None,
                "automation_possible": False,
                "estimated_duration": 600,  # 10 minutes per container
                "risk_level": "medium",
                "note": "Automatic recreation not possible without original configuration",
            }
        )

        return steps

    async def _generate_service_restart_steps(
        self,
        action_type: DestructiveActionType,
        blast_radius: dict[str, Any],
        device_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate steps to restart stopped/disabled services."""
        affected_items = blast_radius.get("affected_items", [])
        steps = []

        action_command = (
            "start" if action_type == DestructiveActionType.SERVICE_BULK_STOP else "enable --now"
        )

        for i, service in enumerate(affected_items):
            steps.append(
                {
                    "step_number": i + 1,
                    "action": "service_restart",
                    "description": f"Restart service {service}",
                    "command": f"systemctl {action_command} {service}",
                    "automation_possible": True,
                    "estimated_duration": 60,  # 1 minute per service
                    "risk_level": "low",
                    "validation_command": f"systemctl is-active {service}",
                    "expected_result": "active",
                }
            )

        return steps

    async def _generate_system_restore_steps(
        self, blast_radius: dict[str, Any], device_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate steps to restore system after prune operations."""
        return [
            {
                "step_number": 1,
                "action": "warning",
                "description": "⚠️ System prune operations cannot be fully rolled back",
                "command": None,
                "automation_possible": False,
                "estimated_duration": 0,
                "risk_level": "critical",
            },
            {
                "step_number": 2,
                "action": "restore_from_backup",
                "description": "Restore Docker objects from backup if available",
                "command": None,
                "automation_possible": False,
                "estimated_duration": 1800,  # 30 minutes
                "risk_level": "medium",
                "note": "Requires pre-existing backup strategy",
            },
            {
                "step_number": 3,
                "action": "rebuild_environment",
                "description": "Rebuild Docker environment from configuration files",
                "command": None,
                "automation_possible": False,
                "estimated_duration": 3600,  # 1 hour
                "risk_level": "high",
            },
        ]

    async def _generate_system_recovery_steps(
        self, action_type: DestructiveActionType, device_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate steps for system reboot/shutdown recovery."""
        if action_type == DestructiveActionType.SYSTEM_SHUTDOWN:
            return [
                {
                    "step_number": 1,
                    "action": "manual_power_on",
                    "description": "Manually power on the system",
                    "command": None,
                    "automation_possible": False,
                    "estimated_duration": 300,  # 5 minutes
                    "risk_level": "low",
                    "note": "Requires physical or remote management interface access",
                },
                {
                    "step_number": 2,
                    "action": "verify_services",
                    "description": "Verify all services started correctly after boot",
                    "command": "systemctl list-units --failed",
                    "automation_possible": True,
                    "estimated_duration": 120,  # 2 minutes
                    "risk_level": "medium",
                },
            ]
        else:  # SYSTEM_REBOOT
            return [
                {
                    "step_number": 1,
                    "action": "wait_for_reboot",
                    "description": "Wait for system to complete reboot",
                    "command": None,
                    "automation_possible": False,
                    "estimated_duration": 300,  # 5 minutes
                    "risk_level": "low",
                },
                {
                    "step_number": 2,
                    "action": "verify_services",
                    "description": "Verify all services started correctly after reboot",
                    "command": "systemctl list-units --failed",
                    "automation_possible": True,
                    "estimated_duration": 120,  # 2 minutes
                    "risk_level": "medium",
                },
            ]

    async def _generate_file_recovery_steps(
        self, blast_radius: dict[str, Any], device_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate steps for file recovery after bulk deletion."""
        return [
            {
                "step_number": 1,
                "action": "warning",
                "description": "⚠️ File deletion cannot be rolled back without backups",
                "command": None,
                "automation_possible": False,
                "estimated_duration": 0,
                "risk_level": "critical",
            },
            {
                "step_number": 2,
                "action": "restore_from_backup",
                "description": "Restore files from most recent backup",
                "command": None,
                "automation_possible": False,
                "estimated_duration": 1800,  # 30 minutes
                "risk_level": "medium",
                "note": "Success depends on backup availability and currency",
            },
            {
                "step_number": 3,
                "action": "data_recovery_tools",
                "description": "Attempt file recovery using specialized tools",
                "command": None,
                "automation_possible": False,
                "estimated_duration": 3600,  # 1 hour
                "risk_level": "high",
                "note": "Recovery success not guaranteed, may be partial",
            },
        ]

    def _generate_capture_requirements(
        self,
        action_type: DestructiveActionType,
        device_context: dict[str, Any],
        blast_radius: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate requirements for pre-operation state capture."""

        requirements = {
            "required": True,
            "capture_commands": [],
            "storage_location": "/tmp/rollback_data",
            "estimated_size_mb": 0,
            "retention_time": "24h",
        }

        if action_type in [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.CONTAINER_BULK_REMOVE,
        ]:
            requirements["capture_commands"].extend(
                [
                    {
                        "description": "Capture running container list",
                        "command": "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' > /tmp/rollback_data/running_containers.txt",
                        "size_mb": 1,
                    },
                    {
                        "description": "Capture container configurations",
                        "command": "docker inspect $(docker ps -q) > /tmp/rollback_data/container_configs.json",
                        "size_mb": 5,
                    },
                ]
            )
            requirements["estimated_size_mb"] = 6

        elif action_type in [
            DestructiveActionType.SERVICE_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_DISABLE,
        ]:
            requirements["capture_commands"].extend(
                [
                    {
                        "description": "Capture service states",
                        "command": "systemctl list-units --type=service --all > /tmp/rollback_data/service_states.txt",
                        "size_mb": 2,
                    },
                    {
                        "description": "Capture enabled services",
                        "command": "systemctl list-unit-files --type=service --state=enabled > /tmp/rollback_data/enabled_services.txt",
                        "size_mb": 1,
                    },
                ]
            )
            requirements["estimated_size_mb"] = 3

        elif action_type == DestructiveActionType.SYSTEM_PRUNE:
            requirements["capture_commands"].extend(
                [
                    {
                        "description": "Capture Docker system info",
                        "command": "docker system df > /tmp/rollback_data/docker_system_before.txt",
                        "size_mb": 1,
                    },
                    {
                        "description": "List all Docker objects",
                        "command": "docker system df -v > /tmp/rollback_data/docker_objects_detailed.txt",
                        "size_mb": 10,
                    },
                ]
            )
            requirements["estimated_size_mb"] = 11

        else:
            # Minimal capture for unknown operations
            requirements["required"] = False
            requirements["estimated_size_mb"] = 0

        return requirements

    def _assess_rollback_risks(
        self,
        action_type: DestructiveActionType,
        rollback_steps: list[dict[str, Any]],
        device_context: dict[str, Any],
    ) -> list[str]:
        """Assess risks associated with the rollback operation."""
        risks = []

        # Environment-based risks
        if device_context.get("environment") == "production":
            risks.append(
                "🏭 Production environment - rollback may cause additional service disruption"
            )

        # Action-specific risks
        if action_type == DestructiveActionType.CONTAINER_BULK_REMOVE:
            risks.append("💾 Data loss risk - non-persistent volumes will be lost")
            risks.append("🔧 Configuration risk - original container configurations required")

        if action_type in [
            DestructiveActionType.SYSTEM_REBOOT,
            DestructiveActionType.SYSTEM_SHUTDOWN,
        ]:
            risks.append("⏱️ Extended downtime - system will be offline during recovery")
            risks.append("🔌 Hardware dependency - requires physical or remote management access")

        if action_type == DestructiveActionType.SYSTEM_PRUNE:
            risks.append("🗑️ Irreversible data loss - pruned objects cannot be recovered")
            risks.append("🏗️ Environment rebuild - may require complete environment reconstruction")

        # Dependency-based risks
        automation_steps = [
            step for step in rollback_steps if step.get("automation_possible", False)
        ]
        manual_steps = [
            step for step in rollback_steps if not step.get("automation_possible", True)
        ]

        if len(manual_steps) > len(automation_steps):
            risks.append("👤 Manual intervention required - rollback cannot be fully automated")

        if any(step.get("risk_level") == "high" for step in rollback_steps):
            risks.append(
                "⚠️ High-risk recovery steps - rollback operation itself carries significant risk"
            )

        return risks

    def _estimate_recovery_time(
        self,
        action_type: DestructiveActionType,
        rollback_steps: list[dict[str, Any]],
        blast_radius: dict[str, Any],
    ) -> dict[str, Any]:
        """Estimate time required for rollback operation."""

        total_duration = sum(step.get("estimated_duration", 0) for step in rollback_steps)
        automation_duration = sum(
            step.get("estimated_duration", 0)
            for step in rollback_steps
            if step.get("automation_possible", False)
        )
        manual_duration = total_duration - automation_duration

        affected_count = blast_radius.get("estimated_count", 1)

        return {
            "total_minutes": total_duration // 60,
            "automated_minutes": automation_duration // 60,
            "manual_minutes": manual_duration // 60,
            "affected_items_count": affected_count,
            "complexity_factor": len(rollback_steps),
            "confidence_level": self._calculate_time_confidence(action_type, rollback_steps),
        }

    def _calculate_time_confidence(
        self, action_type: DestructiveActionType, rollback_steps: list[dict[str, Any]]
    ) -> str:
        """Calculate confidence level for time estimates."""

        if action_type in [
            DestructiveActionType.ZFS_POOL_DESTROY,
            DestructiveActionType.FILESYSTEM_WIPE,
            DestructiveActionType.FILESYSTEM_FORMAT,
        ]:
            return "impossible"

        automation_ratio = len(
            [s for s in rollback_steps if s.get("automation_possible", False)]
        ) / max(len(rollback_steps), 1)

        if automation_ratio >= 0.8:
            return "high"
        elif automation_ratio >= 0.5:
            return "medium"
        else:
            return "low"

    def _determine_automation_level(
        self, rollback_capability: RollbackCapability, rollback_steps: list[dict[str, Any]]
    ) -> str:
        """Determine the level of automation possible for the rollback."""

        if rollback_capability == RollbackCapability.IMPOSSIBLE:
            return "none"

        if not rollback_steps:
            return "none"

        automation_steps = len(
            [step for step in rollback_steps if step.get("automation_possible", False)]
        )
        total_steps = len(rollback_steps)

        automation_ratio = automation_steps / total_steps

        if automation_ratio >= 0.9:
            return "full"
        elif automation_ratio >= 0.6:
            return "high"
        elif automation_ratio >= 0.3:
            return "partial"
        else:
            return "minimal"

    def _add_dependency_ordering(
        self, steps: list[dict[str, Any]], service_dependencies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Add dependency ordering to rollback steps."""
        # This would analyze service dependencies and reorder steps
        # For now, return steps as-is but this could be enhanced
        # to respect service startup order based on dependencies
        return steps

    def get_supported_action_types(self) -> list[DestructiveActionType]:
        """Get list of action types that support rollback plan generation."""
        return [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.CONTAINER_BULK_REMOVE,
            DestructiveActionType.SERVICE_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_DISABLE,
            DestructiveActionType.SYSTEM_PRUNE,
            DestructiveActionType.SYSTEM_REBOOT,
            DestructiveActionType.SYSTEM_SHUTDOWN,
            DestructiveActionType.FILESYSTEM_BULK_DELETE,
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about rollback plan generation capabilities."""
        supported_actions = self.get_supported_action_types()

        full_rollback = [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_DISABLE,
        ]

        return {
            "supported_action_types": len(supported_actions),
            "full_rollback_actions": len(full_rollback),
            "partial_rollback_actions": len(supported_actions)
            - len(full_rollback)
            - 3,  # minus impossible
            "impossible_rollback_actions": 3,  # ZFS destroy, filesystem wipe/format
        }
