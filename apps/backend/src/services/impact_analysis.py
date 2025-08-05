"""
Impact Analysis Engine

Analyzes the potential impact of configuration changes on infrastructure services
and provides risk assessment, affected services identification, and restart requirements.
"""

import logging
from typing import Any
from uuid import UUID

from apps.backend.src.models.configuration import ConfigurationSnapshot
from apps.backend.src.services.dependency_service import get_dependency_service
from apps.backend.src.core.database import get_async_session

logger = logging.getLogger(__name__)


class ImpactAnalysisEngine:
    """
    Analyzes the impact of configuration changes.

    Provides comprehensive impact analysis including:
    - Risk level assessment (LOW, MEDIUM, HIGH, CRITICAL)
    - Affected services identification
    - Restart requirement determination
    - Change summary and recommendations
    """

    def __init__(self):
        self.risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    async def analyze(
        self, new_snapshot: ConfigurationSnapshot, old_snapshot: ConfigurationSnapshot | None = None
    ) -> dict[str, Any]:
        """
        Analyze the impact of a configuration change.

        Args:
            new_snapshot: The new configuration snapshot
            old_snapshot: The previous configuration snapshot (optional)

        Returns:
            Dictionary containing impact analysis results
        """
        try:
            if new_snapshot.config_type == "docker_compose":
                return await self._analyze_compose_impact(new_snapshot, old_snapshot)
            elif (
                new_snapshot.config_type == "proxy_configs"
                or new_snapshot.config_type == "nginx_config"
            ):
                return await self._analyze_proxy_impact(new_snapshot, old_snapshot)
            elif new_snapshot.config_type == "systemd_service":
                return await self._analyze_systemd_impact(new_snapshot, old_snapshot)
            else:
                # Generic analysis for unknown configuration types
                return await self._analyze_generic_impact(new_snapshot, old_snapshot)

            # Enhance impact analysis with dependency information
            enhanced_impact = await self._enhance_with_dependencies(impact, new_snapshot)
            return enhanced_impact

        except Exception as e:
            return {
                "risk_level": "MEDIUM",
                "summary": f"Failed to analyze impact: {str(e)}",
                "affected_services": [],
                "requires_restart": True,
                "recommendations": ["Manual review required due to analysis failure"],
                "analysis_error": str(e),
            }

    async def _analyze_compose_impact(
        self, new_snapshot: ConfigurationSnapshot, old_snapshot: ConfigurationSnapshot | None
    ) -> dict[str, Any]:
        """Analyze impact of Docker Compose configuration changes."""
        new_data = new_snapshot.parsed_data or {}
        old_data = old_snapshot.parsed_data or {} if old_snapshot else {}

        impact = {
            "risk_level": "LOW",
            "summary": "Docker Compose configuration updated",
            "affected_services": [],
            "requires_restart": False,
            "recommendations": [],
            "change_details": {},
        }

        # Extract service information
        new_services = set(new_data.get("services", {}).keys())
        old_services = set(old_data.get("services", {}).keys())

        # Analyze service changes
        added_services = new_services - old_services
        removed_services = old_services - new_services
        common_services = new_services & old_services

        if added_services or removed_services:
            impact["risk_level"] = "HIGH"
            impact["requires_restart"] = True
            impact["affected_services"] = list(new_services | old_services)

            changes = []
            if added_services:
                changes.append(f"Added services: {', '.join(added_services)}")
            if removed_services:
                changes.append(f"Removed services: {', '.join(removed_services)}")

            impact["summary"] = "Docker Compose services changed: " + "; ".join(changes)
            impact["change_details"]["service_changes"] = {
                "added": list(added_services),
                "removed": list(removed_services),
            }

            if removed_services:
                impact["recommendations"].append(
                    "Ensure removed services are properly drained before applying changes"
                )
            if added_services:
                impact["recommendations"].append(
                    "Verify new services have proper health checks configured"
                )

        # Analyze changes in existing services
        service_modifications = []
        for service_name in common_services:
            old_service = old_data.get("services", {}).get(service_name, {})
            new_service = new_data.get("services", {}).get(service_name, {})

            service_changes = self._analyze_service_changes(service_name, old_service, new_service)
            if service_changes:
                service_modifications.extend(service_changes)
                if service_name not in impact["affected_services"]:
                    impact["affected_services"].append(service_name)

        if service_modifications:
            if impact["risk_level"] == "LOW":
                impact["risk_level"] = "MEDIUM"
            impact["requires_restart"] = True
            impact["change_details"]["service_modifications"] = service_modifications

            if len(service_modifications) > 5:
                impact["summary"] = (
                    f"Multiple service modifications detected ({len(service_modifications)} changes)"
                )
            else:
                impact["summary"] = "Service configuration modified: " + "; ".join(
                    [m["summary"] for m in service_modifications[:3]]
                )

        # Analyze network and volume changes
        network_changes = self._analyze_network_changes(old_data, new_data)
        volume_changes = self._analyze_volume_changes(old_data, new_data)

        if network_changes or volume_changes:
            if impact["risk_level"] in ["LOW", "MEDIUM"]:
                impact["risk_level"] = "MEDIUM"
            impact["requires_restart"] = True

            if network_changes:
                impact["change_details"]["network_changes"] = network_changes
                impact["recommendations"].append(
                    "Review network connectivity after applying changes"
                )
            if volume_changes:
                impact["change_details"]["volume_changes"] = volume_changes
                impact["recommendations"].append("Ensure volume data integrity during changes")

        # Set default affected services if none identified
        if not impact["affected_services"]:
            impact["affected_services"] = list(new_services)

        return impact

    async def _analyze_proxy_impact(
        self, new_snapshot: ConfigurationSnapshot, old_snapshot: ConfigurationSnapshot | None
    ) -> dict[str, Any]:
        """Analyze impact of proxy/nginx configuration changes."""
        impact = {
            "risk_level": "MEDIUM",
            "summary": "Proxy configuration updated",
            "affected_services": ["nginx", "proxy"],
            "requires_restart": False,  # Nginx usually supports reload
            "recommendations": ["Use nginx reload instead of restart to minimize downtime"],
            "change_details": {},
        }

        if not old_snapshot:
            impact["summary"] = "New proxy configuration created"
            impact["risk_level"] = "HIGH"
            impact["requires_restart"] = True
            return impact

        new_data = new_snapshot.parsed_data or {}
        old_data = old_snapshot.parsed_data or {}

        # Analyze server block changes
        new_servers = new_data.get("server_blocks", [])
        old_servers = old_data.get("server_blocks", [])

        if len(new_servers) != len(old_servers):
            impact["risk_level"] = "HIGH"
            impact["summary"] = (
                f"Server block count changed: {len(old_servers)} → {len(new_servers)}"
            )
            impact["change_details"]["server_count_change"] = {
                "old_count": len(old_servers),
                "new_count": len(new_servers),
            }

        # Analyze upstream changes
        new_upstreams = new_data.get("upstream_blocks", [])
        old_upstreams = old_data.get("upstream_blocks", [])

        if len(new_upstreams) != len(old_upstreams):
            impact["risk_level"] = "HIGH"
            impact["summary"] = f"Upstream configuration changed"
            impact["change_details"]["upstream_changes"] = {
                "old_count": len(old_upstreams),
                "new_count": len(new_upstreams),
            }
            impact["recommendations"].append("Test upstream connectivity after applying changes")

        # Check for SSL configuration changes
        ssl_changes = self._analyze_ssl_changes(old_data, new_data)
        if ssl_changes:
            impact["risk_level"] = "HIGH"
            impact["change_details"]["ssl_changes"] = ssl_changes
            impact["recommendations"].append("Verify SSL certificate validity and configuration")

        return impact

    async def _analyze_systemd_impact(
        self, new_snapshot: ConfigurationSnapshot, old_snapshot: ConfigurationSnapshot | None
    ) -> dict[str, Any]:
        """Analyze impact of systemd service configuration changes."""
        impact = {
            "risk_level": "MEDIUM",
            "summary": "Systemd service configuration updated",
            "affected_services": ["systemd"],
            "requires_restart": True,  # Systemd changes usually require restart
            "recommendations": ["Use systemctl daemon-reload after applying changes"],
            "change_details": {},
        }

        if not old_snapshot:
            impact["summary"] = "New systemd service created"
            impact["risk_level"] = "HIGH"
            impact["recommendations"].append("Enable and start the new service if needed")
            return impact

        new_data = new_snapshot.parsed_data or {}
        old_data = old_snapshot.parsed_data or {}

        # Analyze service type changes
        old_type = old_data.get("Service", {}).get("Type", "simple")
        new_type = new_data.get("Service", {}).get("Type", "simple")

        if old_type != new_type:
            impact["risk_level"] = "HIGH"
            impact["summary"] = f"Service type changed: {old_type} → {new_type}"
            impact["change_details"]["service_type_change"] = {
                "old_type": old_type,
                "new_type": new_type,
            }

        # Analyze restart policy changes
        old_restart = old_data.get("Service", {}).get("Restart", "no")
        new_restart = new_data.get("Service", {}).get("Restart", "no")

        if old_restart != new_restart:
            impact["change_details"]["restart_policy_change"] = {
                "old_policy": old_restart,
                "new_policy": new_restart,
            }

        # Analyze dependency changes
        old_deps = self._extract_systemd_dependencies(old_data)
        new_deps = self._extract_systemd_dependencies(new_data)

        if set(old_deps) != set(new_deps):
            impact["risk_level"] = "HIGH"
            impact["change_details"]["dependency_changes"] = {
                "added": list(set(new_deps) - set(old_deps)),
                "removed": list(set(old_deps) - set(new_deps)),
            }
            impact["recommendations"].append("Review service dependency order and timing")

        return impact

    async def _analyze_generic_impact(
        self, new_snapshot: ConfigurationSnapshot, old_snapshot: ConfigurationSnapshot | None
    ) -> dict[str, Any]:
        """Generic impact analysis for unknown configuration types."""
        impact = {
            "risk_level": "MEDIUM",
            "summary": f"Configuration file updated: {new_snapshot.file_path}",
            "affected_services": ["unknown"],
            "requires_restart": True,  # Conservative assumption
            "recommendations": ["Manual review required for unknown configuration type"],
            "change_details": {},
        }

        if not old_snapshot:
            impact["summary"] = f"New configuration file created: {new_snapshot.file_path}"
            impact["risk_level"] = "MEDIUM"
            return impact

        # Basic size-based analysis
        old_size = old_snapshot.content_size_bytes or 0
        new_size = new_snapshot.content_size_bytes or 0
        size_change_percent = abs(new_size - old_size) / max(old_size, 1) * 100

        if size_change_percent > 50:
            impact["risk_level"] = "HIGH"
            impact["summary"] = f"Significant size change detected: {size_change_percent:.1f}%"
            impact["change_details"]["size_change"] = {
                "old_size": old_size,
                "new_size": new_size,
                "change_percent": size_change_percent,
            }

        return impact

    def _analyze_service_changes(
        self, service_name: str, old_service: dict[str, Any], new_service: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze changes within a specific service definition."""
        changes = []

        # Check image changes
        old_image = old_service.get("image", "")
        new_image = new_service.get("image", "")
        if old_image != new_image:
            changes.append(
                {
                    "type": "image_change",
                    "service": service_name,
                    "summary": f"Image changed: {old_image} → {new_image}",
                    "impact": "HIGH" if "latest" in new_image else "MEDIUM",
                }
            )

        # Check port changes
        old_ports = old_service.get("ports", [])
        new_ports = new_service.get("ports", [])
        if old_ports != new_ports:
            changes.append(
                {
                    "type": "port_change",
                    "service": service_name,
                    "summary": "Port configuration changed",
                    "impact": "HIGH",
                }
            )

        # Check environment changes
        old_env = old_service.get("environment", {})
        new_env = new_service.get("environment", {})
        if old_env != new_env:
            changes.append(
                {
                    "type": "environment_change",
                    "service": service_name,
                    "summary": "Environment variables changed",
                    "impact": "MEDIUM",
                }
            )

        # Check volume changes
        old_volumes = old_service.get("volumes", [])
        new_volumes = new_service.get("volumes", [])
        if set(old_volumes) != set(new_volumes):
            changes.append(
                {
                    "type": "volume_change",
                    "service": service_name,
                    "summary": "Volume configuration changed",
                    "impact": "HIGH",
                }
            )

        return changes

    def _analyze_network_changes(
        self, old_data: dict[str, Any], new_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Analyze network configuration changes."""
        old_networks = set(old_data.get("networks", {}).keys())
        new_networks = set(new_data.get("networks", {}).keys())

        if old_networks != new_networks:
            return {
                "added_networks": list(new_networks - old_networks),
                "removed_networks": list(old_networks - new_networks),
            }
        return None

    def _analyze_volume_changes(
        self, old_data: dict[str, Any], new_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Analyze volume configuration changes."""
        old_volumes = set(old_data.get("volumes", {}).keys())
        new_volumes = set(new_data.get("volumes", {}).keys())

        if old_volumes != new_volumes:
            return {
                "added_volumes": list(new_volumes - old_volumes),
                "removed_volumes": list(old_volumes - new_volumes),
            }
        return None

    def _analyze_ssl_changes(
        self, old_data: dict[str, Any], new_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Analyze SSL/TLS configuration changes."""
        old_ssl_servers = [
            server
            for server in old_data.get("server_blocks", [])
            if server.get("ssl_enabled", False)
        ]
        new_ssl_servers = [
            server
            for server in new_data.get("server_blocks", [])
            if server.get("ssl_enabled", False)
        ]

        if len(old_ssl_servers) != len(new_ssl_servers):
            return {
                "ssl_server_count_change": {
                    "old_count": len(old_ssl_servers),
                    "new_count": len(new_ssl_servers),
                }
            }
        return None

    def _extract_systemd_dependencies(self, parsed_data: dict[str, Any]) -> list[str]:
        """Extract systemd unit dependencies."""
        dependencies = []
        unit_config = parsed_data.get("Unit", {})

        dependency_keys = [
            "Requires",
            "Wants",
            "Requisite",
            "BindsTo",
            "PartOf",
            "After",
            "Before",
            "Conflicts",
            "OnFailure",
        ]

        for key in dependency_keys:
            if key in unit_config:
                value = unit_config[key]
                if isinstance(value, list):
                    dependencies.extend(value)
                else:
                    dependencies.extend(value.split())

        return list(set(dependencies))

    async def _enhance_with_dependencies(
        self, impact: dict[str, Any], snapshot: ConfigurationSnapshot
    ) -> dict[str, Any]:
        """
        Enhance impact analysis with service dependency information.

        Args:
            impact: Initial impact analysis results
            snapshot: Configuration snapshot being analyzed

        Returns:
            Enhanced impact analysis with dependency information
        """
        try:
            dependency_service = await get_dependency_service()

            async with get_async_session() as session:
                # Get all affected services from initial analysis
                affected_services = set(impact.get("affected_services", []))

                # Find dependency-related impacts for each affected service
                all_dependent_services = set()
                dependency_details = []

                for service_name in list(affected_services):
                    # Get services that depend on this service (downstream impact)
                    downstream = await dependency_service.get_downstream_dependencies(
                        session, snapshot.device_id, service_name
                    )
                    all_dependent_services.update(downstream)

                    if downstream:
                        dependency_details.append(
                            {
                                "service": service_name,
                                "downstream_dependencies": downstream,
                                "impact_type": "downstream",
                            }
                        )

                    # Get services this service depends on (upstream context)
                    upstream = await dependency_service.get_upstream_dependencies(
                        session, snapshot.device_id, service_name
                    )

                    if upstream:
                        dependency_details.append(
                            {
                                "service": service_name,
                                "upstream_dependencies": upstream,
                                "impact_type": "upstream",
                            }
                        )

                # Update affected services to include dependent services
                enhanced_affected_services = list(affected_services | all_dependent_services)

                # Adjust risk level based on dependency count
                dependency_count = len(all_dependent_services)
                original_risk = impact.get("risk_level", "MEDIUM")

                if dependency_count > 0:
                    if dependency_count >= 5:
                        enhanced_risk = "CRITICAL"
                    elif dependency_count >= 3:
                        enhanced_risk = "HIGH"
                    elif dependency_count >= 1:
                        if original_risk in ["LOW", "MEDIUM"]:
                            enhanced_risk = "MEDIUM"
                        else:
                            enhanced_risk = original_risk
                    else:
                        enhanced_risk = original_risk
                else:
                    enhanced_risk = original_risk

                # Add dependency-specific recommendations
                enhanced_recommendations = list(impact.get("recommendations", []))

                if dependency_count > 0:
                    enhanced_recommendations.insert(
                        0,
                        f"Changes will affect {dependency_count} dependent service(s) - coordinate deployment",
                    )
                    enhanced_recommendations.append(
                        "Consider staged rollout to minimize impact on dependent services"
                    )

                if dependency_count >= 3:
                    enhanced_recommendations.append(
                        "High dependency count detected - consider maintenance window"
                    )

                # Update impact analysis with dependency information
                enhanced_impact = {
                    **impact,
                    "risk_level": enhanced_risk,
                    "affected_services": enhanced_affected_services,
                    "recommendations": enhanced_recommendations,
                    "dependency_analysis": {
                        "total_dependent_services": dependency_count,
                        "dependency_details": dependency_details,
                        "original_risk_level": original_risk,
                        "risk_elevated": enhanced_risk != original_risk,
                    },
                }

                # Update summary to mention dependencies
                if dependency_count > 0:
                    original_summary = impact.get("summary", "Configuration updated")
                    enhanced_impact["summary"] = (
                        f"{original_summary} (affects {dependency_count} dependent services)"
                    )

                return enhanced_impact

        except Exception as e:
            # Return original impact if dependency analysis fails
            return {
                **impact,
                "dependency_analysis": {
                    "error": f"Failed to analyze dependencies: {str(e)}",
                    "total_dependent_services": 0,
                    "dependency_details": [],
                },
            }


# Global singleton instance
_impact_analysis_engine: ImpactAnalysisEngine | None = None


async def get_impact_analysis_engine() -> ImpactAnalysisEngine:
    """Get the global impact analysis engine instance."""
    global _impact_analysis_engine

    if _impact_analysis_engine is None:
        _impact_analysis_engine = ImpactAnalysisEngine()

    return _impact_analysis_engine
