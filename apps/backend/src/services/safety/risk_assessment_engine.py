"""
Risk Assessment Engine

Context-aware risk analysis for destructive operations, integrating device-specific
protection rules, blast radius estimation, and intelligent safety warnings.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .patterns import DestructiveActionType
from .rules import (
    get_device_rules,
    get_max_bulk_operations,
    get_protected_paths,
    get_critical_services,
    get_environment_type,
    is_critical_action,
    get_confirmation_escalation_rules,
)
from .rollback_plan_generator import RollbackPlanGenerator
from ..dependency_service import get_dependency_service

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for destructive actions."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskAssessmentEngine:
    """
    Assesses the risk level of destructive operations based on device context.

    Features:
    - Device-specific protection rules
    - Blast radius estimation
    - Environment-aware risk calculation
    - Safety warning generation
    - Service dependency analysis
    """

    def __init__(self):
        """Initialize the risk assessment engine."""
        logger.info("RiskAssessmentEngine initialized")

    async def assess(
        self,
        action_type: DestructiveActionType,
        command: str,
        device_context: dict[str, Any],
        matched_pattern: str | None = None,
        match_details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Perform comprehensive risk analysis of a destructive action.

        Args:
            action_type: The type of destructive action detected
            command: The original command string
            device_context: Rich context about the target device
            matched_pattern: The regex pattern that matched (optional)
            match_details: Details about the pattern match (optional)

        Returns:
            Complete risk analysis with recommendations and requirements
        """
        device_type = device_context.get("os_type", "default").lower()
        device_rules = get_device_rules(device_type)

        logger.info(f"Assessing risk for {action_type.value} on device type: {device_type}")

        # Estimate impact and blast radius
        blast_radius = await self._estimate_blast_radius(action_type, device_context, command)

        # Calculate base risk level
        risk_level = self._calculate_risk_level(
            action_type, blast_radius, device_context, device_rules
        )

        # Generate contextual warnings
        warnings = await self._generate_warnings(
            action_type, blast_radius, device_context, device_rules
        )

        # Generate safety checklist
        safety_checklist = self._generate_safety_checklist(
            action_type, device_context, device_rules
        )

        # Suggest alternatives
        alternative_suggestions = self._suggest_alternatives(action_type, command, device_context)

        # Generate confirmation requirements
        confirmation_requirements = self._determine_confirmation_requirements(
            action_type, risk_level, device_context, device_rules
        )

        # Create impact summary
        impact_summary = self._create_impact_summary(
            action_type, blast_radius, device_context, warnings
        )

        # Generate rollback plan
        rollback_generator = RollbackPlanGenerator()
        rollback_plan = await rollback_generator.generate_rollback_plan(
            action_type, command, device_context, blast_radius
        )

        analysis = {
            "action_type": action_type.value,
            "risk_level": risk_level.value,
            "device_type": device_type,
            "environment_type": get_environment_type(device_type),
            "impact_summary": impact_summary,
            "blast_radius": blast_radius,
            "safety_warnings": warnings,
            "safety_checklist": safety_checklist,
            "alternative_suggestions": alternative_suggestions,
            "requires_confirmation": confirmation_requirements["required"],
            "confirmation_escalation": confirmation_requirements["escalation"],
            "rollback_plan": rollback_plan,
            "assessment_timestamp": datetime.now(timezone.utc).isoformat(),
            "matched_pattern": matched_pattern,
            "match_details": match_details or {},
        }

        logger.info(
            f"Risk assessment complete: {risk_level.value} risk for {action_type.value} "
            f"affecting {blast_radius.get('estimated_count', 0)} items"
        )

        return analysis

    async def _get_dependency_service(self):
        """Get the dependency service instance (lazy initialization)."""
        if not hasattr(self, "_dependency_service") or self._dependency_service is None:
            self._dependency_service = await get_dependency_service()
        return self._dependency_service

    async def _analyze_service_dependencies(
        self, device_id: str, service_name: str, device_context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze service dependencies to understand cascade impact.

        Args:
            device_id: Device UUID as string
            service_name: Name of the service being affected
            device_context: Device context information

        Returns:
            Dictionary with dependency analysis results
        """
        try:
            from uuid import UUID
            from ...core.database import get_async_session

            dependency_service = await self._get_dependency_service()
            device_uuid = UUID(device_id)

            async with get_async_session() as session:
                # Get all services affected by changes to this service
                affected_services = await dependency_service.get_all_affected_services(
                    session, device_uuid, service_name, max_depth=3
                )

                upstream_services = affected_services.get("upstream", [])
                downstream_services = affected_services.get("downstream", [])

                return {
                    "service_name": service_name,
                    "upstream_dependencies": upstream_services,
                    "downstream_dependencies": downstream_services,
                    "total_affected_services": len(upstream_services) + len(downstream_services),
                    "cascade_analysis": {
                        "will_lose_dependencies": len(upstream_services) > 0,
                        "will_break_dependents": len(downstream_services) > 0,
                        "impact_description": self._generate_dependency_impact_description(
                            service_name, upstream_services, downstream_services
                        ),
                    },
                }

        except Exception as e:
            logger.warning(f"Failed to analyze service dependencies for {service_name}: {e}")
            return {
                "service_name": service_name,
                "upstream_dependencies": [],
                "downstream_dependencies": [],
                "total_affected_services": 0,
                "cascade_analysis": {
                    "will_lose_dependencies": False,
                    "will_break_dependents": False,
                    "impact_description": "Dependency analysis unavailable",
                },
            }

    def _generate_dependency_impact_description(
        self, service_name: str, upstream: list[str], downstream: list[str]
    ) -> str:
        """Generate human-readable description of dependency impact."""
        if not upstream and not downstream:
            return f"No service dependencies detected for {service_name}"

        descriptions = []

        if upstream:
            upstream_list = ", ".join(upstream[:3])
            if len(upstream) > 3:
                upstream_list += f" and {len(upstream) - 3} more"
            descriptions.append(f"depends on: {upstream_list}")

        if downstream:
            downstream_list = ", ".join(downstream[:3])
            if len(downstream) > 3:
                downstream_list += f" and {len(downstream) - 3} more"
            descriptions.append(f"required by: {downstream_list}")

        return f"Service {service_name} {' and '.join(descriptions)}"

    async def _estimate_blast_radius(
        self, action_type: DestructiveActionType, device_context: dict[str, Any], command: str
    ) -> dict[str, Any]:
        """
        Estimate the blast radius (scope of impact) for the destructive action.

        In a production implementation, this would query live system data
        via the UnifiedDataCollectionService.
        """
        blast_radius = {
            "estimated_count": 0,
            "affected_items": [],
            "protected_items_affected": [],
            "critical_services_affected": [],
            "estimation_method": "heuristic",
        }

        # Container-related operations
        if action_type in [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.CONTAINER_BULK_REMOVE,
            DestructiveActionType.CONTAINER_BULK_KILL,
        ]:
            running_containers = device_context.get("running_container_count", 5)
            affected_containers = [f"container-{i}" for i in range(min(running_containers, 10))]

            # Analyze service dependencies for affected containers
            service_dependencies = []
            if device_context.get("device_id"):
                for container in affected_containers[:3]:  # Analyze first few containers
                    try:
                        dep_analysis = await self._analyze_service_dependencies(
                            device_context["device_id"], container, device_context
                        )
                        if dep_analysis["total_affected_services"] > 0:
                            service_dependencies.append(dep_analysis)
                    except Exception as e:
                        logger.debug(f"Could not analyze dependencies for {container}: {e}")

            blast_radius.update(
                {
                    "estimated_count": running_containers,
                    "affected_items": affected_containers,
                    "estimation_method": "container_count_from_context",
                    "service_dependencies": service_dependencies,
                    "dependency_cascade_count": sum(
                        dep["total_affected_services"] for dep in service_dependencies
                    ),
                }
            )

        # System prune operations
        elif action_type == DestructiveActionType.SYSTEM_PRUNE:
            blast_radius.update(
                {
                    "estimated_count": device_context.get("docker_objects_count", 20),
                    "affected_items": [
                        "unused_containers",
                        "unused_images",
                        "unused_volumes",
                        "unused_networks",
                    ],
                    "estimation_method": "docker_objects_estimate",
                }
            )

        # Service operations
        elif action_type in [
            DestructiveActionType.SERVICE_BULK_STOP,
            DestructiveActionType.SERVICE_BULK_DISABLE,
            DestructiveActionType.SERVICE_BULK_RESTART,
        ]:
            services = device_context.get("available_services", [])
            critical_services = get_critical_services(device_context.get("os_type", "default"))
            affected_critical = [svc for svc in services if svc in critical_services]

            # Analyze service dependencies for affected services
            service_dependencies = []
            total_cascade_count = 0

            if device_context.get("device_id"):
                for service in services[:5]:  # Analyze first few services to avoid overwhelming
                    try:
                        dep_analysis = await self._analyze_service_dependencies(
                            device_context["device_id"], service, device_context
                        )
                        service_dependencies.append(dep_analysis)
                        total_cascade_count += dep_analysis["total_affected_services"]
                    except Exception as e:
                        logger.debug(f"Could not analyze dependencies for {service}: {e}")

            blast_radius.update(
                {
                    "estimated_count": len(services)
                    + total_cascade_count,  # Include cascade impact
                    "affected_items": services[:10],  # Limit for display
                    "critical_services_affected": affected_critical,
                    "estimation_method": "service_list_with_dependency_analysis",
                    "service_dependencies": service_dependencies,
                    "dependency_cascade_count": total_cascade_count,
                }
            )

        # Filesystem operations
        elif action_type in [
            DestructiveActionType.FILESYSTEM_BULK_DELETE,
            DestructiveActionType.FILESYSTEM_FORMAT,
            DestructiveActionType.FILESYSTEM_WIPE,
        ]:
            # Analyze command for paths
            protected_paths = get_protected_paths(device_context.get("os_type", "default"))
            affected_protected = []

            for path in protected_paths:
                if path.lower() in command.lower():
                    affected_protected.append(path)

            blast_radius.update(
                {
                    "estimated_count": len(affected_protected) if affected_protected else 1,
                    "affected_items": affected_protected or ["filesystem_target"],
                    "protected_items_affected": affected_protected,
                    "estimation_method": "path_analysis",
                }
            )

        # ZFS operations
        elif action_type in [
            DestructiveActionType.ZFS_POOL_DESTROY,
            DestructiveActionType.ZFS_DATASET_DESTROY,
            DestructiveActionType.ZFS_SNAPSHOT_DESTROY_BULK,
        ]:
            blast_radius.update(
                {
                    "estimated_count": device_context.get("zfs_objects_count", 3),
                    "affected_items": ["zfs_pool_or_dataset"],
                    "estimation_method": "zfs_context_estimate",
                }
            )

        # System power operations
        elif action_type in [
            DestructiveActionType.SYSTEM_REBOOT,
            DestructiveActionType.SYSTEM_SHUTDOWN,
            DestructiveActionType.SYSTEM_HALT,
        ]:
            running_containers = device_context.get("running_container_count", 0)
            blast_radius.update(
                {
                    "estimated_count": running_containers + 1,  # +1 for the system itself
                    "affected_items": ["entire_system", "all_running_services"],
                    "critical_services_affected": get_critical_services(
                        device_context.get("os_type", "default")
                    ),
                    "estimation_method": "system_wide_impact",
                }
            )

        # Default case
        else:
            blast_radius.update(
                {
                    "estimated_count": 1,
                    "affected_items": ["unknown_target"],
                    "estimation_method": "default_minimal",
                }
            )

        return blast_radius

    def _calculate_risk_level(
        self,
        action_type: DestructiveActionType,
        blast_radius: dict[str, Any],
        device_context: dict[str, Any],
        device_rules: dict[str, Any],
    ) -> RiskLevel:
        """Calculate the risk level based on multiple factors."""

        # Start with base risk assessment
        environment_type = device_context.get(
            "environment", get_environment_type(device_context.get("os_type", "default"))
        )
        affected_count = blast_radius.get("estimated_count", 1)

        # Critical actions are always high risk or higher
        if is_critical_action(device_context.get("os_type", "default"), action_type.value):
            base_risk = RiskLevel.HIGH
        else:
            base_risk = RiskLevel.LOW

        # Environment multipliers
        if environment_type == "production":
            if base_risk == RiskLevel.LOW:
                base_risk = RiskLevel.HIGH
            elif base_risk == RiskLevel.MEDIUM:
                base_risk = RiskLevel.CRITICAL
            elif base_risk == RiskLevel.HIGH:
                base_risk = RiskLevel.CRITICAL

        # Scale-based risk escalation
        max_bulk_ops = get_max_bulk_operations(device_context.get("os_type", "default"))
        if affected_count > max_bulk_ops:
            if base_risk == RiskLevel.LOW:
                base_risk = RiskLevel.MEDIUM
            elif base_risk == RiskLevel.MEDIUM:
                base_risk = RiskLevel.HIGH

        # Protected items escalation
        if blast_radius.get("protected_items_affected") or blast_radius.get(
            "critical_services_affected"
        ):
            if base_risk == RiskLevel.LOW:
                base_risk = RiskLevel.MEDIUM
            elif base_risk == RiskLevel.MEDIUM:
                base_risk = RiskLevel.HIGH

        # Service dependency escalation
        dependency_cascade_count = blast_radius.get("dependency_cascade_count", 0)
        if dependency_cascade_count > 0:
            if dependency_cascade_count >= 10:  # Many dependent services
                if base_risk == RiskLevel.LOW:
                    base_risk = RiskLevel.HIGH
                elif base_risk == RiskLevel.MEDIUM:
                    base_risk = RiskLevel.CRITICAL
            elif dependency_cascade_count >= 3:  # Some dependent services
                if base_risk == RiskLevel.LOW:
                    base_risk = RiskLevel.MEDIUM
                elif base_risk == RiskLevel.MEDIUM:
                    base_risk = RiskLevel.HIGH

        # Special case escalations
        if action_type in [
            DestructiveActionType.ZFS_POOL_DESTROY,
            DestructiveActionType.FILESYSTEM_WIPE,
            DestructiveActionType.SYSTEM_SHUTDOWN,
        ]:
            base_risk = RiskLevel.CRITICAL

        return base_risk

    async def _generate_warnings(
        self,
        action_type: DestructiveActionType,
        blast_radius: dict[str, Any],
        device_context: dict[str, Any],
        device_rules: dict[str, Any],
    ) -> list[str]:
        """Generate contextual safety warnings."""
        warnings = []

        # Environment warnings
        environment = device_context.get(
            "environment", get_environment_type(device_context.get("os_type", "default"))
        )
        if environment == "production":
            warnings.append("⚠️  PRODUCTION ENVIRONMENT - This action will affect live systems")

        # Scale warnings
        affected_count = blast_radius.get("estimated_count", 0)
        max_bulk_ops = get_max_bulk_operations(device_context.get("os_type", "default"))
        if affected_count > max_bulk_ops:
            warnings.append(
                f"⚠️  BULK OPERATION - This will affect {affected_count} items (limit: {max_bulk_ops})"
            )

        # Protected resources warnings
        protected_items = blast_radius.get("protected_items_affected", [])
        if protected_items:
            warnings.append(
                f"🔒 PROTECTED RESOURCES - Affects protected paths: {', '.join(protected_items[:3])}"
            )

        # Critical services warnings
        critical_services = blast_radius.get("critical_services_affected", [])
        if critical_services:
            warnings.append(
                f"🚨 CRITICAL SERVICES - Will impact: {', '.join(critical_services[:3])}"
            )

        # Action-specific warnings
        if action_type == DestructiveActionType.ZFS_POOL_DESTROY:
            warnings.append("💀 IRREVERSIBLE - ZFS pool destruction cannot be undone")

        if action_type in [
            DestructiveActionType.FILESYSTEM_WIPE,
            DestructiveActionType.FILESYSTEM_FORMAT,
        ]:
            warnings.append("💀 DATA LOSS - All data on target filesystem will be permanently lost")

        if action_type in [
            DestructiveActionType.SYSTEM_SHUTDOWN,
            DestructiveActionType.SYSTEM_REBOOT,
        ]:
            warnings.append("🔌 SYSTEM OFFLINE - Device will become unavailable during operation")

        # Service dependency warnings
        dependency_cascade_count = blast_radius.get("dependency_cascade_count", 0)
        service_dependencies = blast_radius.get("service_dependencies", [])

        if dependency_cascade_count > 0:
            if dependency_cascade_count == 1:
                warnings.append(f"🔗 SERVICE DEPENDENCY - 1 additional service will be affected")
            else:
                warnings.append(
                    f"🔗 SERVICE DEPENDENCIES - {dependency_cascade_count} additional services will be affected"
                )

        # Add specific dependency details for high-impact cases
        if dependency_cascade_count >= 5:
            dependent_services = []
            for dep in service_dependencies:
                downstream = dep.get("downstream_dependencies", [])
                dependent_services.extend(downstream[:2])  # Add first 2 from each

            if dependent_services:
                dependent_list = ", ".join(
                    list(set(dependent_services))[:3]
                )  # Remove duplicates, limit to 3
                if len(set(dependent_services)) > 3:
                    dependent_list += f" and {len(set(dependent_services)) - 3} more"
                warnings.append(
                    f"⚠️  DEPENDENT SERVICES - These services depend on the affected ones: {dependent_list}"
                )

        # Device-specific warnings
        device_type = device_context.get("os_type", "default").lower()
        if device_type == "unraid" and action_type in [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.SYSTEM_REBOOT,
        ]:
            warnings.append(
                "🗄️  UNRAID - Check that parity operations are not running before proceeding"
            )

        return warnings

    def _generate_safety_checklist(
        self,
        action_type: DestructiveActionType,
        device_context: dict[str, Any],
        device_rules: dict[str, Any],
    ) -> list[str]:
        """Generate a safety checklist for the user to review."""
        checklist = []

        # Common checks
        checklist.append("[ ] I have read and understood the impact summary")
        checklist.append("[ ] I have verified this is the correct device and environment")

        # Action-specific checks
        if action_type in [
            DestructiveActionType.ZFS_POOL_DESTROY,
            DestructiveActionType.FILESYSTEM_WIPE,
            DestructiveActionType.FILESYSTEM_FORMAT,
        ]:
            checklist.append("[ ] I have confirmed that a recent backup exists")
            checklist.append("[ ] I have verified that no critical data will be lost")

        if action_type in [
            DestructiveActionType.CONTAINER_BULK_STOP,
            DestructiveActionType.CONTAINER_BULK_REMOVE,
            DestructiveActionType.SERVICE_BULK_STOP,
        ]:
            checklist.append("[ ] I have checked that dependent services can handle this downtime")
            checklist.append("[ ] I have notified relevant team members if applicable")

        if action_type in [
            DestructiveActionType.SYSTEM_REBOOT,
            DestructiveActionType.SYSTEM_SHUTDOWN,
        ]:
            checklist.append("[ ] I have saved all work and notified users of the planned downtime")
            checklist.append("[ ] I have verified that the system will restart properly")

        # Environment-specific checks
        environment = device_context.get(
            "environment", get_environment_type(device_context.get("os_type", "default"))
        )
        if environment == "production":
            checklist.append("[ ] I have approval for this production change")
            checklist.append("[ ] I have a rollback plan ready")

        return checklist

    def _suggest_alternatives(
        self, action_type: DestructiveActionType, command: str, device_context: dict[str, Any]
    ) -> list[str]:
        """Suggest safer alternatives to the destructive action."""
        suggestions = []

        if action_type == DestructiveActionType.CONTAINER_BULK_STOP:
            suggestions.extend(
                [
                    "Stop containers individually: docker stop <container_name>",
                    "Use docker-compose to stop a specific project: docker-compose down",
                    "Pause containers instead: docker pause <container_name>",
                ]
            )

        elif action_type == DestructiveActionType.CONTAINER_BULK_REMOVE:
            suggestions.extend(
                [
                    "Remove containers individually: docker rm <container_name>",
                    "Use docker container prune with filters: docker container prune --filter 'label=project=test'",
                    "Stop containers first, then remove: docker stop <name> && docker rm <name>",
                ]
            )

        elif action_type == DestructiveActionType.FILESYSTEM_BULK_DELETE:
            suggestions.extend(
                [
                    "Move files to trash instead: mv <files> ~/.trash/",
                    "Use find with confirmation: find <path> -name '<pattern>' -ok rm {} \\;",
                    "Delete files individually after review",
                ]
            )

        elif action_type == DestructiveActionType.SERVICE_BULK_STOP:
            suggestions.extend(
                [
                    "Stop services individually: systemctl stop <service_name>",
                    "Use service dependencies: systemctl stop <main_service> (stops dependencies)",
                    "Check service status first: systemctl status <service_name>",
                ]
            )

        elif action_type in [
            DestructiveActionType.SYSTEM_REBOOT,
            DestructiveActionType.SYSTEM_SHUTDOWN,
        ]:
            suggestions.extend(
                [
                    "Schedule the operation: shutdown -r +10 'Rebooting in 10 minutes'",
                    "Use systemctl with delay: systemctl reboot --message='Planned reboot'",
                    "Consider if a service restart would suffice instead",
                ]
            )

        return suggestions

    def _determine_confirmation_requirements(
        self,
        action_type: DestructiveActionType,
        risk_level: RiskLevel,
        device_context: dict[str, Any],
        device_rules: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine what level of confirmation is required."""
        escalation_rules = get_confirmation_escalation_rules(
            device_context.get("os_type", "default")
        )

        # Base confirmation requirement
        requires_confirmation = risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

        # Escalation for critical actions
        requires_admin_approval = is_critical_action(
            device_context.get("os_type", "default"), action_type.value
        ) or escalation_rules.get("requires_admin_approval", False)

        max_attempts = escalation_rules.get("max_confirmation_attempts", 3)

        # Adjust based on risk level
        if risk_level == RiskLevel.CRITICAL:
            max_attempts = min(max_attempts, 2)  # Fewer attempts for critical actions

        return {
            "required": requires_confirmation,
            "escalation": {
                "requires_admin_approval": requires_admin_approval,
                "max_attempts": max_attempts,
                "risk_level": risk_level.value,
            },
        }

    def _create_impact_summary(
        self,
        action_type: DestructiveActionType,
        blast_radius: dict[str, Any],
        device_context: dict[str, Any],
        warnings: list[str],
    ) -> str:
        """Create a human-readable impact summary."""
        affected_count = blast_radius.get("estimated_count", 0)
        affected_items = blast_radius.get("affected_items", [])

        device_name = device_context.get("hostname", "unknown device")

        if affected_count == 0:
            return f"This {action_type.value} operation on {device_name} will have minimal impact."

        if affected_count == 1:
            item_desc = affected_items[0] if affected_items else "item"
            return f"This {action_type.value} operation on {device_name} will affect 1 {item_desc}."

        examples = ", ".join(affected_items[:3])
        if len(affected_items) > 3:
            examples += f" and {len(affected_items) - 3} more"

        # Base impact description
        base_impact = (
            f"This {action_type.value} operation on {device_name} will affect "
            f"{affected_count} items including: {examples}."
        )

        # Add dependency cascade information if present
        dependency_cascade_count = blast_radius.get("dependency_cascade_count", 0)
        if dependency_cascade_count > 0:
            cascade_info = f" Additionally, {dependency_cascade_count} dependent services will be indirectly affected through service dependencies."
            base_impact += cascade_info

        return base_impact

    def get_supported_action_types(self) -> list[DestructiveActionType]:
        """Get list of all supported action types for risk assessment."""
        return list(DestructiveActionType)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the risk assessment engine."""
        return {
            "supported_action_types": len(DestructiveActionType),
            "supported_device_types": len(
                ["unraid", "ubuntu", "wsl2", "windows", "proxmox", "docker", "default"]
            ),
            "risk_levels": len(RiskLevel),
        }
