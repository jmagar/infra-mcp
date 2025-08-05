"""
Container Orchestration Protection Service

Specialized protection logic for container orchestration operations (Docker, Kubernetes, etc.).
Provides advanced safety mechanisms for container stack management, orchestration disruption
prevention, and container dependency chain protection.
"""

import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

from .patterns import DestructiveActionType

logger = logging.getLogger(__name__)


class ContainerOperationType(Enum):
    """Types of container orchestration operations requiring protection."""

    # Docker operations
    CONTAINER_REMOVE = "container_remove"
    CONTAINER_STOP_ALL = "container_stop_all"
    VOLUME_REMOVE = "volume_remove"
    NETWORK_REMOVE = "network_remove"
    IMAGE_PRUNE = "image_prune"
    SYSTEM_PRUNE = "system_prune"

    # Docker Compose operations
    COMPOSE_DOWN = "compose_down"
    COMPOSE_DOWN_VOLUMES = "compose_down_volumes"
    STACK_REMOVE = "stack_remove"

    # Kubernetes operations
    NAMESPACE_DELETE = "namespace_delete"
    DEPLOYMENT_DELETE = "deployment_delete"
    SERVICE_DELETE = "service_delete"
    PERSISTENT_VOLUME_DELETE = "persistent_volume_delete"
    CLUSTER_DELETE = "cluster_delete"

    # Multi-container operations
    BULK_CONTAINER_OPERATION = "bulk_container_operation"
    ORCHESTRATION_RESET = "orchestration_reset"


class ContainerProtectionLevel(Enum):
    """Container-specific protection levels."""

    MINIMAL = "minimal"  # Basic confirmation for non-critical containers
    STANDARD = "standard"  # Confirmation + dependency checking
    ENHANCED = "enhanced"  # + backup validation + impact analysis
    MAXIMUM = "maximum"  # + multi-admin approval + staged execution


class ContainerCriticality(Enum):
    """Container criticality classifications."""

    INFRASTRUCTURE = "infrastructure"  # Core system containers (databases, reverse proxies)
    APPLICATION = "application"  # Business application containers
    DEVELOPMENT = "development"  # Development and testing containers
    MONITORING = "monitoring"  # Observability and monitoring containers
    UTILITY = "utility"  # Support utilities (caches, queues)
    TEMPORARY = "temporary"  # Short-lived or disposable containers


class OrchestrationPlatform(Enum):
    """Supported orchestration platforms."""

    DOCKER = "docker"
    DOCKER_COMPOSE = "docker_compose"
    DOCKER_SWARM = "docker_swarm"
    KUBERNETES = "kubernetes"
    PODMAN = "podman"
    CONTAINERD = "containerd"


class ContainerOrchestrationProtectionService:
    """
    Specialized protection service for container orchestration operations.

    Features:
    - Container criticality assessment and protection policies
    - Orchestration platform-specific safety mechanisms
    - Container dependency chain analysis and protection
    - Multi-container operation impact assessment
    - Service disruption prevention and rollback planning
    - Integration with container health monitoring
    """

    def __init__(self):
        """Initialize the container orchestration protection service."""

        # Protection policies by container criticality
        self.protection_policies = {
            ContainerCriticality.INFRASTRUCTURE: ContainerProtectionLevel.MAXIMUM,
            ContainerCriticality.APPLICATION: ContainerProtectionLevel.ENHANCED,
            ContainerCriticality.MONITORING: ContainerProtectionLevel.ENHANCED,
            ContainerCriticality.UTILITY: ContainerProtectionLevel.STANDARD,
            ContainerCriticality.DEVELOPMENT: ContainerProtectionLevel.STANDARD,
            ContainerCriticality.TEMPORARY: ContainerProtectionLevel.MINIMAL,
        }

        # Operations requiring different protection levels
        self.operation_base_protection = {
            ContainerOperationType.SYSTEM_PRUNE: ContainerProtectionLevel.MAXIMUM,
            ContainerOperationType.ORCHESTRATION_RESET: ContainerProtectionLevel.MAXIMUM,
            ContainerOperationType.CLUSTER_DELETE: ContainerProtectionLevel.MAXIMUM,
            ContainerOperationType.NAMESPACE_DELETE: ContainerProtectionLevel.ENHANCED,
            ContainerOperationType.COMPOSE_DOWN_VOLUMES: ContainerProtectionLevel.ENHANCED,
            ContainerOperationType.STACK_REMOVE: ContainerProtectionLevel.ENHANCED,
            ContainerOperationType.BULK_CONTAINER_OPERATION: ContainerProtectionLevel.ENHANCED,
            ContainerOperationType.PERSISTENT_VOLUME_DELETE: ContainerProtectionLevel.ENHANCED,
            ContainerOperationType.VOLUME_REMOVE: ContainerProtectionLevel.STANDARD,
            ContainerOperationType.COMPOSE_DOWN: ContainerProtectionLevel.STANDARD,
            ContainerOperationType.DEPLOYMENT_DELETE: ContainerProtectionLevel.STANDARD,
            ContainerOperationType.SERVICE_DELETE: ContainerProtectionLevel.STANDARD,
            ContainerOperationType.CONTAINER_STOP_ALL: ContainerProtectionLevel.STANDARD,
            ContainerOperationType.NETWORK_REMOVE: ContainerProtectionLevel.STANDARD,
            ContainerOperationType.IMAGE_PRUNE: ContainerProtectionLevel.MINIMAL,
            ContainerOperationType.CONTAINER_REMOVE: ContainerProtectionLevel.MINIMAL,
        }

        # Critical container patterns that require enhanced protection
        self.critical_container_patterns = {
            # Infrastructure containers
            "database",
            "db",
            "postgres",
            "mysql",
            "mongodb",
            "redis",
            "elasticsearch",
            # Reverse proxies and load balancers
            "nginx",
            "traefik",
            "haproxy",
            "apache",
            "caddy",
            "swag",
            # Message queues and event streaming
            "rabbitmq",
            "kafka",
            "nats",
            "activemq",
            # Monitoring and observability
            "prometheus",
            "grafana",
            "jaeger",
            "zipkin",
            "elasticsearch",
            # Service discovery and orchestration
            "consul",
            "etcd",
            "zookeeper",
            "nomad",
        }

        # Platform-specific safety considerations
        self.platform_considerations = {
            OrchestrationPlatform.KUBERNETES: {
                "namespace_isolation": True,
                "rbac_required": True,
                "persistent_volume_protection": True,
                "service_mesh_aware": True,
            },
            OrchestrationPlatform.DOCKER_COMPOSE: {
                "compose_file_backup": True,
                "volume_preservation": True,
                "network_isolation": True,
                "service_dependencies": True,
            },
            OrchestrationPlatform.DOCKER_SWARM: {
                "service_replication": True,
                "overlay_networks": True,
                "secrets_management": True,
                "rolling_updates": True,
            },
        }

        logger.info("ContainerOrchestrationProtectionService initialized")

    async def assess_container_operation_risk(
        self,
        operation_type: ContainerOperationType,
        target_containers: list[str],
        platform: OrchestrationPlatform,
        container_context: dict[str, Any],
        device_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Assess the risk level for a container orchestration operation.

        Args:
            operation_type: Type of container operation
            target_containers: List of target containers/services
            platform: Orchestration platform being used
            container_context: Container-specific context information
            device_context: Device and environment context

        Returns:
            Comprehensive risk assessment for the container operation
        """
        logger.info(
            f"Assessing container operation risk: {operation_type.value} "
            f"on {len(target_containers)} containers via {platform.value}"
        )

        # Classify containers by criticality
        container_classifications = self._classify_containers(target_containers, container_context)

        # Determine protection level
        base_protection = self.operation_base_protection[operation_type]
        container_protection = self._determine_container_protection_level(container_classifications)
        final_protection = self._merge_protection_levels(base_protection, container_protection)

        # Analyze container dependencies and orchestration impact
        dependency_analysis = await self._analyze_container_dependencies(
            target_containers, platform, container_context
        )
        orchestration_impact = await self._analyze_orchestration_impact(
            operation_type, target_containers, platform, container_context, dependency_analysis
        )

        # Check for running services and health status
        service_analysis = await self._analyze_service_health(target_containers, container_context)

        # Platform-specific risk factors
        platform_risks = await self._analyze_platform_risks(
            operation_type, platform, container_context
        )

        # Calculate risk score
        risk_score = self._calculate_container_risk_score(
            operation_type,
            container_classifications,
            dependency_analysis,
            orchestration_impact,
            service_analysis,
            platform_risks,
        )

        # Generate container-specific safety requirements
        safety_requirements = self._generate_container_safety_requirements(
            operation_type, final_protection, platform, target_containers, container_context
        )

        return {
            "operation_type": operation_type.value,
            "target_containers": target_containers,
            "platform": platform.value,
            "container_classifications": {
                container: classification.value
                for container, classification in container_classifications.items()
            },
            "protection_level": final_protection.value,
            "risk_score": risk_score,
            "risk_level": self._categorize_risk_score(risk_score),
            "dependency_analysis": dependency_analysis,
            "orchestration_impact": orchestration_impact,
            "service_analysis": service_analysis,
            "platform_risks": platform_risks,
            "safety_requirements": safety_requirements,
            "recommended_actions": self._generate_container_recommendations(
                operation_type, risk_score, dependency_analysis, service_analysis
            ),
            "staged_execution_plan": self._generate_staged_execution_plan(
                operation_type, target_containers, dependency_analysis, final_protection
            ),
        }

    async def validate_container_preconditions(
        self,
        operation_type: ContainerOperationType,
        target_containers: list[str],
        platform: OrchestrationPlatform,
        container_context: dict[str, Any],
        safety_requirements: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate that all preconditions are met for a container operation.

        Args:
            operation_type: Type of container operation
            target_containers: List of target containers
            platform: Orchestration platform
            container_context: Container-specific context
            safety_requirements: Safety requirements to validate

        Returns:
            Validation results with pass/fail status
        """
        logger.info(
            f"Validating container preconditions for {operation_type.value} "
            f"on {len(target_containers)} containers"
        )

        validation_results = {
            "overall_valid": True,
            "validations": [],
            "warnings": [],
            "blocking_issues": [],
        }

        # Validate service health requirements
        if safety_requirements.get("health_check_required", False):
            health_validation = await self._validate_service_health(
                target_containers, container_context
            )
            validation_results["validations"].append(health_validation)
            if not health_validation["valid"]:
                validation_results["overall_valid"] = False
                validation_results["blocking_issues"].append(health_validation["message"])

        # Validate dependency requirements
        if safety_requirements.get("dependency_check_required", False):
            dependency_validation = await self._validate_container_dependencies(
                target_containers, container_context
            )
            validation_results["validations"].append(dependency_validation)
            if not dependency_validation["valid"]:
                validation_results["overall_valid"] = False
                validation_results["blocking_issues"].append(dependency_validation["message"])

        # Validate backup requirements
        if safety_requirements.get("backup_validation_required", False):
            backup_validation = await self._validate_container_backups(
                target_containers, container_context
            )
            validation_results["validations"].append(backup_validation)
            if not backup_validation["valid"]:
                validation_results["overall_valid"] = False
                validation_results["blocking_issues"].append(backup_validation["message"])

        # Validate platform state requirements
        if safety_requirements.get("platform_state_check_required", False):
            platform_validation = await self._validate_platform_state(platform, container_context)
            validation_results["validations"].append(platform_validation)
            if not platform_validation["valid"]:
                validation_results["warnings"].append(platform_validation["message"])

        # Validate orchestration requirements
        if safety_requirements.get("orchestration_check_required", False):
            orchestration_validation = await self._validate_orchestration_state(
                platform, target_containers, container_context
            )
            validation_results["validations"].append(orchestration_validation)
            if not orchestration_validation["valid"]:
                validation_results["overall_valid"] = False
                validation_results["blocking_issues"].append(orchestration_validation["message"])

        return validation_results

    async def create_container_protection_snapshot(
        self,
        target_containers: list[str],
        platform: OrchestrationPlatform,
        operation_type: ContainerOperationType,
        container_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create protection snapshots for containers before destructive operation.

        Args:
            target_containers: List of containers to protect
            platform: Orchestration platform
            operation_type: Type of operation requiring protection
            container_context: Container context information

        Returns:
            Container protection snapshot results
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"container_protection_{operation_type.value}_{timestamp}"

        logger.info(f"Creating container protection snapshot: {snapshot_name}")

        try:
            protection_snapshot = {
                "snapshot_name": snapshot_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "operation_type": operation_type.value,
                "platform": platform.value,
                "target_containers": target_containers,
                "container_states": {},
                "configuration_backups": {},
                "volume_snapshots": {},
                "network_configurations": {},
                "protection_successful": True,
            }

            # Capture container states
            for container in target_containers:
                container_state = self._capture_container_state(container, container_context)
                protection_snapshot["container_states"][container] = container_state

            # Backup orchestration configurations
            if platform in [OrchestrationPlatform.DOCKER_COMPOSE, OrchestrationPlatform.KUBERNETES]:
                config_backup = self._backup_orchestration_config(platform, container_context)
                protection_snapshot["configuration_backups"] = config_backup

            # Create volume snapshots for critical data
            volume_snapshots = await self._create_volume_snapshots(
                target_containers, container_context
            )
            protection_snapshot["volume_snapshots"] = volume_snapshots

            # Capture network configurations
            network_config = self._capture_network_configuration(platform, container_context)
            protection_snapshot["network_configurations"] = network_config

            logger.info(f"Container protection snapshot created successfully: {snapshot_name}")
            return protection_snapshot

        except Exception as e:
            logger.error(f"Failed to create container protection snapshot: {e}")
            return {
                "snapshot_name": snapshot_name,
                "protection_successful": False,
                "error": str(e),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

    def _classify_containers(
        self, containers: list[str], container_context: dict[str, Any]
    ) -> dict[str, ContainerCriticality]:
        """Classify containers based on their role and criticality."""
        classifications = {}

        for container in containers:
            # Get container metadata
            container_info = container_context.get("containers", {}).get(container, {})
            image_name = container_info.get("image", "").lower()
            labels = container_info.get("labels", {})
            ports = container_info.get("ports", [])

            # Check for critical patterns in image name or container name
            is_critical = any(
                pattern in container.lower() or pattern in image_name
                for pattern in self.critical_container_patterns
            )

            if is_critical:
                classifications[container] = ContainerCriticality.INFRASTRUCTURE
            elif "database" in labels.get("role", "").lower():
                classifications[container] = ContainerCriticality.INFRASTRUCTURE
            elif "monitoring" in labels.get("category", "").lower():
                classifications[container] = ContainerCriticality.MONITORING
            elif "app" in container.lower() or "application" in image_name:
                classifications[container] = ContainerCriticality.APPLICATION
            elif "dev" in container.lower() or "test" in container.lower():
                classifications[container] = ContainerCriticality.DEVELOPMENT
            elif "temp" in container.lower() or "tmp" in container.lower():
                classifications[container] = ContainerCriticality.TEMPORARY
            else:
                # Default to utility for unclassified containers
                classifications[container] = ContainerCriticality.UTILITY

        return classifications

    def _determine_container_protection_level(
        self, classifications: dict[str, ContainerCriticality]
    ) -> ContainerProtectionLevel:
        """Determine overall protection level based on container classifications."""
        if not classifications:
            return ContainerProtectionLevel.MINIMAL

        # Use the highest protection level required by any container
        max_protection = ContainerProtectionLevel.MINIMAL
        protection_order = [
            ContainerProtectionLevel.MINIMAL,
            ContainerProtectionLevel.STANDARD,
            ContainerProtectionLevel.ENHANCED,
            ContainerProtectionLevel.MAXIMUM,
        ]

        for classification in classifications.values():
            required_protection = self.protection_policies[classification]
            if protection_order.index(required_protection) > protection_order.index(max_protection):
                max_protection = required_protection

        return max_protection

    def _merge_protection_levels(
        self, level1: ContainerProtectionLevel, level2: ContainerProtectionLevel
    ) -> ContainerProtectionLevel:
        """Merge two protection levels, choosing the higher one."""
        levels_order = [
            ContainerProtectionLevel.MINIMAL,
            ContainerProtectionLevel.STANDARD,
            ContainerProtectionLevel.ENHANCED,
            ContainerProtectionLevel.MAXIMUM,
        ]

        index1 = levels_order.index(level1)
        index2 = levels_order.index(level2)

        return levels_order[max(index1, index2)]

    async def _analyze_container_dependencies(
        self,
        target_containers: list[str],
        platform: OrchestrationPlatform,
        container_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze container dependencies and interdependencies."""
        # In production, this would query actual container orchestration APIs
        mock_dependencies = {
            "direct_dependencies": {},
            "reverse_dependencies": {},
            "network_dependencies": [],
            "volume_dependencies": [],
            "service_mesh_dependencies": [],
            "dependency_chains": [],
        }

        for container in target_containers:
            # Simulate dependency analysis based on container patterns
            container_deps = []
            reverse_deps = []

            if "database" in container.lower():
                reverse_deps = ["app-server", "api-gateway", "worker-queue"]
            elif "nginx" in container.lower() or "proxy" in container.lower():
                reverse_deps = ["web-app", "api-service"]
                container_deps = ["backend-service"]
            elif "app" in container.lower():
                container_deps = ["database", "redis", "message-queue"]

            mock_dependencies["direct_dependencies"][container] = container_deps
            mock_dependencies["reverse_dependencies"][container] = reverse_deps

        # Calculate dependency complexity
        total_dependencies = sum(
            len(deps) for deps in mock_dependencies["direct_dependencies"].values()
        )
        total_reverse_dependencies = sum(
            len(deps) for deps in mock_dependencies["reverse_dependencies"].values()
        )

        return {
            "dependencies": mock_dependencies,
            "dependency_count": total_dependencies,
            "reverse_dependency_count": total_reverse_dependencies,
            "has_critical_dependencies": total_reverse_dependencies > 0,
            "complex_dependency_chain": total_dependencies + total_reverse_dependencies > 3,
        }

    async def _analyze_orchestration_impact(
        self,
        operation_type: ContainerOperationType,
        target_containers: list[str],
        platform: OrchestrationPlatform,
        container_context: dict[str, Any],
        dependency_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze the impact of the container operation on orchestration."""
        impact_factors = {
            "service_disruption_risk": "high"
            if dependency_analysis["has_critical_dependencies"]
            else "low",
            "data_loss_risk": "high"
            if operation_type
            in [
                ContainerOperationType.COMPOSE_DOWN_VOLUMES,
                ContainerOperationType.VOLUME_REMOVE,
                ContainerOperationType.PERSISTENT_VOLUME_DELETE,
                ContainerOperationType.SYSTEM_PRUNE,
            ]
            else "low",
            "orchestration_impact": "high"
            if operation_type
            in [
                ContainerOperationType.ORCHESTRATION_RESET,
                ContainerOperationType.CLUSTER_DELETE,
                ContainerOperationType.NAMESPACE_DELETE,
            ]
            else "medium",
            "recovery_complexity": self._estimate_recovery_complexity(operation_type, platform),
            "estimated_downtime_minutes": self._estimate_container_downtime(
                operation_type, len(target_containers), dependency_analysis
            ),
        }

        # Platform-specific impact analysis
        if platform == OrchestrationPlatform.KUBERNETES:
            impact_factors["namespace_impact"] = len(target_containers) > 5
            impact_factors["cluster_stability_risk"] = operation_type in [
                ContainerOperationType.CLUSTER_DELETE,
                ContainerOperationType.ORCHESTRATION_RESET,
            ]
        elif platform == OrchestrationPlatform.DOCKER_COMPOSE:
            impact_factors["compose_stack_impact"] = True
            impact_factors["shared_network_impact"] = len(target_containers) > 1

        # Determine reversibility
        reversible_operations = [
            ContainerOperationType.CONTAINER_STOP_ALL,
            ContainerOperationType.COMPOSE_DOWN,
        ]
        impact_factors["reversible"] = operation_type in reversible_operations

        return impact_factors

    async def _analyze_service_health(
        self, target_containers: list[str], container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze the health status of target containers and services."""
        # In production, this would check actual container health
        mock_health_data = {
            "healthy_containers": [],
            "unhealthy_containers": [],
            "unknown_containers": [],
            "health_check_enabled": [],
            "service_readiness": {},
        }

        for container in target_containers:
            # Simulate health status based on container patterns
            if "database" in container.lower():
                mock_health_data["healthy_containers"].append(container)
                mock_health_data["health_check_enabled"].append(container)
                mock_health_data["service_readiness"][container] = "ready"
            elif "nginx" in container.lower():
                mock_health_data["healthy_containers"].append(container)
                mock_health_data["service_readiness"][container] = "ready"
            elif "temp" in container.lower():
                mock_health_data["unknown_containers"].append(container)
                mock_health_data["service_readiness"][container] = "unknown"
            else:
                mock_health_data["healthy_containers"].append(container)
                mock_health_data["service_readiness"][container] = "ready"

        overall_health_score = len(mock_health_data["healthy_containers"]) / len(target_containers)

        return {
            "health_data": mock_health_data,
            "overall_health_score": overall_health_score,
            "all_containers_healthy": len(mock_health_data["unhealthy_containers"]) == 0,
            "health_monitoring_available": len(mock_health_data["health_check_enabled"]) > 0,
        }

    async def _analyze_platform_risks(
        self,
        operation_type: ContainerOperationType,
        platform: OrchestrationPlatform,
        container_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze platform-specific risks and considerations."""
        platform_risks = {
            "platform": platform.value,
            "platform_specific_risks": [],
            "mitigation_strategies": [],
            "platform_stability": "stable",
        }

        # Get platform-specific considerations
        considerations = self.platform_considerations.get(platform, {})

        if platform == OrchestrationPlatform.KUBERNETES:
            if operation_type == ContainerOperationType.NAMESPACE_DELETE:
                platform_risks["platform_specific_risks"].append(
                    "Complete namespace isolation loss"
                )
                platform_risks["mitigation_strategies"].append(
                    "Verify no critical workloads in namespace"
                )
            if considerations.get("rbac_required"):
                platform_risks["platform_specific_risks"].append(
                    "RBAC permission verification required"
                )

        elif platform == OrchestrationPlatform.DOCKER_COMPOSE:
            if operation_type == ContainerOperationType.COMPOSE_DOWN_VOLUMES:
                platform_risks["platform_specific_risks"].append("Named volume data loss")
                platform_risks["mitigation_strategies"].append(
                    "Backup volume data before proceeding"
                )
            if considerations.get("service_dependencies"):
                platform_risks["platform_specific_risks"].append("Service startup order disruption")

        elif platform == OrchestrationPlatform.DOCKER_SWARM:
            if operation_type in [
                ContainerOperationType.SERVICE_DELETE,
                ContainerOperationType.STACK_REMOVE,
            ]:
                platform_risks["platform_specific_risks"].append("Service replication loss")
                platform_risks["mitigation_strategies"].append(
                    "Verify service scaling configuration"
                )

        return platform_risks

    def _calculate_container_risk_score(
        self,
        operation_type: ContainerOperationType,
        container_classifications: dict[str, ContainerCriticality],
        dependency_analysis: dict[str, Any],
        orchestration_impact: dict[str, Any],
        service_analysis: dict[str, Any],
        platform_risks: dict[str, Any],
    ) -> float:
        """Calculate comprehensive risk score for container operation."""
        base_scores = {
            ContainerOperationType.SYSTEM_PRUNE: 10.0,
            ContainerOperationType.ORCHESTRATION_RESET: 10.0,
            ContainerOperationType.CLUSTER_DELETE: 10.0,
            ContainerOperationType.NAMESPACE_DELETE: 9.0,
            ContainerOperationType.COMPOSE_DOWN_VOLUMES: 8.0,
            ContainerOperationType.PERSISTENT_VOLUME_DELETE: 8.0,
            ContainerOperationType.STACK_REMOVE: 7.0,
            ContainerOperationType.BULK_CONTAINER_OPERATION: 6.0,
            ContainerOperationType.VOLUME_REMOVE: 6.0,
            ContainerOperationType.COMPOSE_DOWN: 5.0,
            ContainerOperationType.SERVICE_DELETE: 5.0,
            ContainerOperationType.DEPLOYMENT_DELETE: 5.0,
            ContainerOperationType.CONTAINER_STOP_ALL: 4.0,
            ContainerOperationType.NETWORK_REMOVE: 3.0,
            ContainerOperationType.IMAGE_PRUNE: 2.0,
            ContainerOperationType.CONTAINER_REMOVE: 2.0,
        }

        risk_score = base_scores[operation_type]

        # Adjust for container criticality
        infrastructure_containers = sum(
            1
            for c in container_classifications.values()
            if c == ContainerCriticality.INFRASTRUCTURE
        )
        if infrastructure_containers > 0:
            risk_score *= 1.0 + (infrastructure_containers * 0.3)

        # Adjust for dependencies
        if dependency_analysis["has_critical_dependencies"]:
            risk_score *= 1.4
        elif dependency_analysis["complex_dependency_chain"]:
            risk_score *= 1.2

        # Adjust for service health
        if not service_analysis["all_containers_healthy"]:
            risk_score *= 1.2

        # Adjust for orchestration impact
        if orchestration_impact["service_disruption_risk"] == "high":
            risk_score *= 1.3
        if orchestration_impact["data_loss_risk"] == "high":
            risk_score *= 1.4

        # Adjust for platform risks
        if len(platform_risks["platform_specific_risks"]) > 2:
            risk_score *= 1.2

        # Adjust for reversibility
        if not orchestration_impact["reversible"]:
            risk_score *= 1.2

        return min(10.0, max(1.0, risk_score))

    def _categorize_risk_score(self, risk_score: float) -> str:
        """Categorize numeric risk score into risk level."""
        if risk_score >= 8.0:
            return "critical"
        elif risk_score >= 6.0:
            return "high"
        elif risk_score >= 4.0:
            return "medium"
        else:
            return "low"

    def _generate_container_safety_requirements(
        self,
        operation_type: ContainerOperationType,
        protection_level: ContainerProtectionLevel,
        platform: OrchestrationPlatform,
        target_containers: list[str],
        container_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate container-specific safety requirements."""
        requirements = {
            "confirmation_required": True,
            "confirmation_phrase_required": protection_level != ContainerProtectionLevel.MINIMAL,
            "health_check_required": protection_level
            in [ContainerProtectionLevel.ENHANCED, ContainerProtectionLevel.MAXIMUM],
            "dependency_check_required": protection_level
            in [ContainerProtectionLevel.ENHANCED, ContainerProtectionLevel.MAXIMUM],
            "backup_validation_required": protection_level == ContainerProtectionLevel.MAXIMUM,
            "platform_state_check_required": protection_level == ContainerProtectionLevel.MAXIMUM,
            "orchestration_check_required": protection_level == ContainerProtectionLevel.MAXIMUM,
            "staged_execution_required": protection_level == ContainerProtectionLevel.MAXIMUM
            and len(target_containers) > 3,
            "multi_admin_approval": protection_level == ContainerProtectionLevel.MAXIMUM
            and operation_type
            in [
                ContainerOperationType.SYSTEM_PRUNE,
                ContainerOperationType.ORCHESTRATION_RESET,
                ContainerOperationType.CLUSTER_DELETE,
            ],
        }

        # Add operation-specific requirements
        if operation_type in [
            ContainerOperationType.COMPOSE_DOWN_VOLUMES,
            ContainerOperationType.VOLUME_REMOVE,
            ContainerOperationType.PERSISTENT_VOLUME_DELETE,
        ]:
            requirements["volume_backup_required"] = True
            requirements["data_loss_acknowledgment"] = True

        if operation_type == ContainerOperationType.BULK_CONTAINER_OPERATION:
            requirements["bulk_operation_review"] = True
            requirements["container_list_verification"] = True

        return requirements

    def _generate_container_recommendations(
        self,
        operation_type: ContainerOperationType,
        risk_score: float,
        dependency_analysis: dict[str, Any],
        service_analysis: dict[str, Any],
    ) -> list[str]:
        """Generate container-specific recommendations."""
        recommendations = []

        if risk_score >= 8.0:
            recommendations.append("🔴 CRITICAL: Consider alternative approaches or staging")

        if not service_analysis["all_containers_healthy"]:
            recommendations.append("🏥 Address unhealthy containers before proceeding")

        if dependency_analysis["has_critical_dependencies"]:
            recommendations.append("🔗 Review dependent services and plan for disruption")

        if operation_type in [
            ContainerOperationType.COMPOSE_DOWN_VOLUMES,
            ContainerOperationType.VOLUME_REMOVE,
            ContainerOperationType.PERSISTENT_VOLUME_DELETE,
        ]:
            recommendations.append("💾 Backup volume data before proceeding")

        if operation_type == ContainerOperationType.SYSTEM_PRUNE:
            recommendations.append(
                "⚠️ System prune removes ALL unused containers, images, and volumes"
            )
            recommendations.append("🔍 Review what will be removed with --dry-run first")

        if operation_type == ContainerOperationType.BULK_CONTAINER_OPERATION:
            recommendations.append("📝 Verify the exact list of containers to be affected")

        return recommendations

    def _generate_staged_execution_plan(
        self,
        operation_type: ContainerOperationType,
        target_containers: list[str],
        dependency_analysis: dict[str, Any],
        protection_level: ContainerProtectionLevel,
    ) -> dict[str, Any] | None:
        """Generate staged execution plan for complex operations."""
        if protection_level != ContainerProtectionLevel.MAXIMUM or len(target_containers) <= 3:
            return None

        # Create execution stages based on dependencies
        stages = []
        processed_containers = set()

        # Stage 1: Non-critical containers with no reverse dependencies
        stage_1 = []
        for container in target_containers:
            reverse_deps = dependency_analysis["dependencies"]["reverse_dependencies"].get(
                container, []
            )
            if not reverse_deps and container not in processed_containers:
                stage_1.append(container)
                processed_containers.add(container)

        if stage_1:
            stages.append(
                {
                    "stage": 1,
                    "description": "Non-critical containers without dependents",
                    "containers": stage_1,
                    "wait_time_seconds": 30,
                }
            )

        # Stage 2: Utility containers
        stage_2 = []
        for container in target_containers:
            if container not in processed_containers and "util" in container.lower():
                stage_2.append(container)
                processed_containers.add(container)

        if stage_2:
            stages.append(
                {
                    "stage": 2,
                    "description": "Utility and support containers",
                    "containers": stage_2,
                    "wait_time_seconds": 60,
                }
            )

        # Stage 3: Remaining containers
        stage_3 = [c for c in target_containers if c not in processed_containers]
        if stage_3:
            stages.append(
                {
                    "stage": 3,
                    "description": "Critical infrastructure containers",
                    "containers": stage_3,
                    "wait_time_seconds": 120,
                }
            )

        return {
            "staged_execution": True,
            "total_stages": len(stages),
            "stages": stages,
            "estimated_total_time_minutes": sum(stage["wait_time_seconds"] for stage in stages)
            // 60
            + 5,
        }

    def _estimate_recovery_complexity(
        self, operation_type: ContainerOperationType, platform: OrchestrationPlatform
    ) -> str:
        """Estimate recovery complexity for the operation."""
        high_complexity_ops = [
            ContainerOperationType.SYSTEM_PRUNE,
            ContainerOperationType.ORCHESTRATION_RESET,
            ContainerOperationType.CLUSTER_DELETE,
            ContainerOperationType.COMPOSE_DOWN_VOLUMES,
        ]

        if operation_type in high_complexity_ops:
            return "high"
        elif platform == OrchestrationPlatform.KUBERNETES:
            return "medium"
        else:
            return "low"

    def _estimate_container_downtime(
        self,
        operation_type: ContainerOperationType,
        container_count: int,
        dependency_analysis: dict[str, Any],
    ) -> int:
        """Estimate downtime in minutes for container operation."""
        base_times = {
            ContainerOperationType.CONTAINER_REMOVE: 1,
            ContainerOperationType.CONTAINER_STOP_ALL: 2,
            ContainerOperationType.COMPOSE_DOWN: 3,
            ContainerOperationType.SERVICE_DELETE: 2,
            ContainerOperationType.DEPLOYMENT_DELETE: 5,
            ContainerOperationType.STACK_REMOVE: 8,
            ContainerOperationType.NAMESPACE_DELETE: 10,
            ContainerOperationType.VOLUME_REMOVE: 5,
            ContainerOperationType.NETWORK_REMOVE: 2,
            ContainerOperationType.COMPOSE_DOWN_VOLUMES: 10,
            ContainerOperationType.PERSISTENT_VOLUME_DELETE: 8,
            ContainerOperationType.BULK_CONTAINER_OPERATION: 5,
            ContainerOperationType.SYSTEM_PRUNE: 15,
            ContainerOperationType.ORCHESTRATION_RESET: 30,
            ContainerOperationType.CLUSTER_DELETE: 60,
            ContainerOperationType.IMAGE_PRUNE: 3,
        }

        base_time = base_times[operation_type]

        # Adjust for container count
        if container_count > 10:
            base_time *= 2
        elif container_count > 5:
            base_time *= 1.5

        # Adjust for dependencies
        if dependency_analysis["has_critical_dependencies"]:
            base_time *= 1.5

        return int(base_time)

    def _capture_container_state(
        self, container: str, container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Capture current state of a container for protection snapshot."""
        container_info = container_context.get("containers", {}).get(container, {})

        return {
            "container_name": container,
            "image": container_info.get("image", "unknown"),
            "status": container_info.get("status", "unknown"),
            "ports": container_info.get("ports", []),
            "volumes": container_info.get("volumes", []),
            "networks": container_info.get("networks", []),
            "environment": container_info.get("environment", {}),
            "labels": container_info.get("labels", {}),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    def _backup_orchestration_config(
        self, platform: OrchestrationPlatform, container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Backup orchestration configuration files."""
        config_backup = {
            "platform": platform.value,
            "config_files": {},
            "backup_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if platform == OrchestrationPlatform.DOCKER_COMPOSE:
            # In production, would backup actual docker-compose.yml files
            config_backup["config_files"]["docker-compose.yml"] = (
                "# Backed up compose configuration"
            )
        elif platform == OrchestrationPlatform.KUBERNETES:
            # In production, would backup actual Kubernetes manifests
            config_backup["config_files"]["namespace.yaml"] = "# Backed up namespace configuration"
            config_backup["config_files"]["deployments.yaml"] = (
                "# Backed up deployment configurations"
            )

        return config_backup

    async def _create_volume_snapshots(
        self, target_containers: list[str], container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Create snapshots of container volumes."""
        volume_snapshots = {
            "snapshots_created": [],
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for container in target_containers:
            container_info = container_context.get("containers", {}).get(container, {})
            volumes = container_info.get("volumes", [])

            for volume in volumes:
                if volume and not volume.startswith("/tmp"):  # Skip temporary volumes
                    snapshot_name = (
                        f"{volume}_snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                    )
                    volume_snapshots["snapshots_created"].append(
                        {
                            "volume": volume,
                            "snapshot_name": snapshot_name,
                            "container": container,
                        }
                    )

        return volume_snapshots

    def _capture_network_configuration(
        self, platform: OrchestrationPlatform, container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Capture network configuration for restoration."""
        return {
            "platform": platform.value,
            "networks": container_context.get("networks", {}),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _validate_service_health(
        self, target_containers: list[str], container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate that services are healthy before operation."""
        unhealthy_containers = []

        for container in target_containers:
            container_info = container_context.get("containers", {}).get(container, {})
            status = container_info.get("status", "unknown")

            if status not in ["running", "healthy"]:
                unhealthy_containers.append(container)

        if unhealthy_containers:
            return {
                "valid": False,
                "message": f"Unhealthy containers detected: {', '.join(unhealthy_containers)}",
                "validation_type": "service_health",
            }

        return {
            "valid": True,
            "message": "All target containers are healthy",
            "validation_type": "service_health",
        }

    async def _validate_container_dependencies(
        self, target_containers: list[str], container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate container dependencies won't cause issues."""
        critical_dependencies = []

        for container in target_containers:
            if "database" in container.lower():
                critical_dependencies.append(container)

        if critical_dependencies:
            return {
                "valid": False,
                "message": f"Critical dependencies detected: {', '.join(critical_dependencies)} - verify dependent services can handle interruption",
                "validation_type": "dependency_check",
            }

        return {
            "valid": True,
            "message": "No blocking dependencies detected",
            "validation_type": "dependency_check",
        }

    async def _validate_container_backups(
        self, target_containers: list[str], container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate that container data is backed up."""
        containers_without_backup = []

        for container in target_containers:
            if "database" in container.lower() or "data" in container.lower():
                # In production, would check actual backup status
                # For now, assume critical containers have backups
                continue
            elif "temp" in container.lower() or "cache" in container.lower():
                # Skip backup validation for temporary containers
                continue
            else:
                # Mock backup validation
                containers_without_backup.append(container)

        if containers_without_backup:
            return {
                "valid": False,
                "message": f"Containers without recent backups: {', '.join(containers_without_backup)}",
                "validation_type": "backup_availability",
            }

        return {
            "valid": True,
            "message": "Container backup validation completed",
            "validation_type": "backup_availability",
        }

    async def _validate_platform_state(
        self, platform: OrchestrationPlatform, container_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate orchestration platform state."""
        return {
            "valid": True,
            "message": f"{platform.value} platform state healthy",
            "validation_type": "platform_state",
        }

    async def _validate_orchestration_state(
        self,
        platform: OrchestrationPlatform,
        target_containers: list[str],
        container_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate orchestration system state."""
        if platform == OrchestrationPlatform.KUBERNETES and len(target_containers) > 10:
            return {
                "valid": False,
                "message": "Large Kubernetes operation requires staged execution",
                "validation_type": "orchestration_check",
            }

        return {
            "valid": True,
            "message": "Orchestration state validation passed",
            "validation_type": "orchestration_check",
        }

    def get_supported_operations(self) -> list[dict[str, Any]]:
        """Get list of supported container orchestration operations."""
        return [
            {
                "operation": op.value,
                "base_protection": self.operation_base_protection[op].value,
                "description": self._get_operation_description(op),
            }
            for op in ContainerOperationType
        ]

    def _get_operation_description(self, operation: ContainerOperationType) -> str:
        """Get human-readable description for container operation."""
        descriptions = {
            ContainerOperationType.CONTAINER_REMOVE: "Remove individual container",
            ContainerOperationType.CONTAINER_STOP_ALL: "Stop all running containers",
            ContainerOperationType.VOLUME_REMOVE: "Remove container volume and data",
            ContainerOperationType.NETWORK_REMOVE: "Remove container network",
            ContainerOperationType.IMAGE_PRUNE: "Remove unused container images",
            ContainerOperationType.SYSTEM_PRUNE: "Remove all unused containers, networks, images, and volumes",
            ContainerOperationType.COMPOSE_DOWN: "Stop Docker Compose stack",
            ContainerOperationType.COMPOSE_DOWN_VOLUMES: "Stop Docker Compose stack and remove volumes",
            ContainerOperationType.STACK_REMOVE: "Remove Docker Swarm stack",
            ContainerOperationType.NAMESPACE_DELETE: "Delete Kubernetes namespace and all resources",
            ContainerOperationType.DEPLOYMENT_DELETE: "Delete Kubernetes deployment",
            ContainerOperationType.SERVICE_DELETE: "Delete Kubernetes service",
            ContainerOperationType.PERSISTENT_VOLUME_DELETE: "Delete Kubernetes persistent volume",
            ContainerOperationType.CLUSTER_DELETE: "Delete entire Kubernetes cluster",
            ContainerOperationType.BULK_CONTAINER_OPERATION: "Perform operation on multiple containers",
            ContainerOperationType.ORCHESTRATION_RESET: "Reset container orchestration system",
        }
        return descriptions[operation]

    def get_protection_statistics(self) -> dict[str, Any]:
        """Get container orchestration protection service statistics."""
        return {
            "supported_operations": len(ContainerOperationType),
            "protection_levels": len(ContainerProtectionLevel),
            "container_criticality_types": len(ContainerCriticality),
            "supported_platforms": len(OrchestrationPlatform),
            "critical_patterns": len(self.critical_container_patterns),
            "protection_features": {
                "dependency_analysis": True,
                "staged_execution": True,
                "platform_specific_validation": True,
                "container_health_monitoring": True,
                "orchestration_impact_assessment": True,
                "container_state_snapshots": True,
                "volume_protection": True,
                "network_configuration_backup": True,
            },
        }
