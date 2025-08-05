"""
Service Dependency Management Service

Manages service dependencies and relationships for accurate impact analysis.
Automatically extracts dependencies from configuration files like docker-compose.yml
and provides dependency graph traversal capabilities.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.src.core.database import get_async_session
from apps.backend.src.models.service_dependency import ServiceDependency
from apps.backend.src.models.device import Device

logger = logging.getLogger(__name__)


class DependencyService:
    """
    Service for managing service dependencies and relationships.

    Provides functionality to:
    - Extract dependencies from configuration files
    - Store and manage dependency relationships
    - Query dependency graphs for impact analysis
    - Find upstream and downstream dependencies
    """

    def __init__(self):
        self.dependency_types = {
            "docker": "Docker container dependency",
            "network": "Network dependency",
            "config_file": "Configuration file dependency",
            "volume": "Volume dependency",
            "port": "Port dependency",
            "env_var": "Environment variable dependency",
            "manual": "Manually configured dependency",
        }

    async def get_downstream_dependencies(
        self, session: AsyncSession, device_id: UUID, service_name: str
    ) -> list[str]:
        """
        Find all services that depend on the given service.

        Args:
            session: Database session
            device_id: Device UUID
            service_name: Name of the service to find dependencies for

        Returns:
            List of service names that depend on the given service
        """
        try:
            # Query for services that depend on the given service
            stmt = (
                select(ServiceDependency.service_name)
                .where(
                    ServiceDependency.device_id == device_id,
                    ServiceDependency.depends_on == service_name,
                )
                .distinct()
            )

            result = await session.execute(stmt)
            downstream_services = [row[0] for row in result.fetchall()]

            return downstream_services

        except Exception as e:
            logger.error(f"Error finding downstream dependencies: {e}")
            return []

    async def get_upstream_dependencies(
        self, session: AsyncSession, device_id: UUID, service_name: str
    ) -> list[str]:
        """
        Find all services that the given service depends on.

        Args:
            session: Database session
            device_id: Device UUID
            service_name: Name of the service to find dependencies for

        Returns:
            List of service names that the given service depends on
        """
        try:
            # Query for services that the given service depends on
            stmt = (
                select(ServiceDependency.depends_on)
                .where(
                    ServiceDependency.device_id == device_id,
                    ServiceDependency.service_name == service_name,
                )
                .distinct()
            )

            result = await session.execute(stmt)
            upstream_services = [row[0] for row in result.fetchall()]

            return upstream_services

        except Exception as e:
            logger.error(f"Error finding upstream dependencies: {e}")
            return []

    async def get_all_affected_services(
        self, session: AsyncSession, device_id: UUID, service_name: str, max_depth: int = 5
    ) -> dict[str, list[str]]:
        """
        Get all services affected by changes to the given service (recursive).

        Args:
            session: Database session
            device_id: Device UUID
            service_name: Name of the service that changed
            max_depth: Maximum recursion depth to prevent infinite loops

        Returns:
            Dictionary with 'upstream' and 'downstream' service lists
        """
        upstream = set()
        downstream = set()
        visited = set()

        # Get direct dependencies
        direct_upstream = await self.get_upstream_dependencies(session, device_id, service_name)
        direct_downstream = await self.get_downstream_dependencies(session, device_id, service_name)

        upstream.update(direct_upstream)
        downstream.update(direct_downstream)
        visited.add(service_name)

        # Recursively find dependencies (with depth limit)
        for depth in range(max_depth):
            new_services = set()

            # Expand upstream dependencies
            for service in list(upstream - visited):
                if service not in visited:
                    deps = await self.get_upstream_dependencies(session, device_id, service)
                    upstream.update(deps)
                    new_services.add(service)

            # Expand downstream dependencies
            for service in list(downstream - visited):
                if service not in visited:
                    deps = await self.get_downstream_dependencies(session, device_id, service)
                    downstream.update(deps)
                    new_services.add(service)

            visited.update(new_services)

            # Stop if no new services found
            if not new_services:
                break

        return {"upstream": list(upstream), "downstream": list(downstream)}

    async def build_dependencies_from_compose(
        self, device_id: UUID, parsed_compose: dict[str, Any]
    ) -> int:
        """
        Parse a docker-compose file and create dependency records.

        Args:
            device_id: Device UUID
            parsed_compose: Parsed docker-compose configuration

        Returns:
            Number of dependencies created
        """
        dependencies_created = 0

        async with get_async_session() as session:
            try:
                services = parsed_compose.get("services", {})

                for service_name, service_config in services.items():
                    # Extract depends_on dependencies
                    depends_on = service_config.get("depends_on", [])
                    if isinstance(depends_on, dict):
                        # New docker-compose format: {service: {condition: ...}}
                        depends_on = list(depends_on.keys())
                    elif isinstance(depends_on, str):
                        # Single string dependency
                        depends_on = [depends_on]

                    # Create dependency records
                    for dependency in depends_on:
                        await self._create_dependency(
                            session,
                            device_id=device_id,
                            service_name=service_name,
                            depends_on=dependency,
                            dependency_type="docker",
                            metadata="extracted from docker-compose depends_on",
                        )
                        dependencies_created += 1

                    # Extract network dependencies
                    networks = service_config.get("networks", [])
                    if isinstance(networks, dict):
                        networks = list(networks.keys())
                    elif isinstance(networks, str):
                        networks = [networks]

                    for network in networks:
                        if network != "default":
                            await self._create_dependency(
                                session,
                                device_id=device_id,
                                service_name=service_name,
                                depends_on=f"network:{network}",
                                dependency_type="network",
                                metadata="extracted from docker-compose networks",
                            )
                            dependencies_created += 1

                    # Extract volume dependencies
                    volumes = service_config.get("volumes", [])
                    for volume in volumes:
                        if isinstance(volume, str) and ":" in volume:
                            # Parse volume format: "host:container" or "volume:container"
                            volume_name = volume.split(":")[0]
                            if not volume_name.startswith("/"):  # Named volume, not bind mount
                                await self._create_dependency(
                                    session,
                                    device_id=device_id,
                                    service_name=service_name,
                                    depends_on=f"volume:{volume_name}",
                                    dependency_type="volume",
                                    metadata="extracted from docker-compose volumes",
                                )
                                dependencies_created += 1

                await session.commit()

            except Exception as e:
                await session.rollback()
                logger.error(f"Error building dependencies from compose: {e}")
                raise

        return dependencies_created

    async def _create_dependency(
        self,
        session: AsyncSession,
        device_id: UUID,
        service_name: str,
        depends_on: str,
        dependency_type: str,
        metadata: str | None = None,
    ) -> ServiceDependency | None:
        """
        Create a service dependency record if it doesn't already exist.

        Args:
            session: Database session
            device_id: Device UUID
            service_name: Service that has the dependency
            depends_on: Service that is depended upon
            dependency_type: Type of dependency
            metadata: Optional metadata about the dependency

        Returns:
            Created ServiceDependency instance or None if already exists
        """
        try:
            # Check if dependency already exists
            existing = await session.execute(
                select(ServiceDependency).where(
                    ServiceDependency.device_id == device_id,
                    ServiceDependency.service_name == service_name,
                    ServiceDependency.depends_on == depends_on,
                )
            )

            if existing.scalar_one_or_none():
                return None  # Already exists

            # Create new dependency
            dependency = ServiceDependency(
                device_id=device_id,
                service_name=service_name,
                depends_on=depends_on,
                dependency_type=dependency_type,
                metadata=metadata,
            )

            session.add(dependency)
            return dependency

        except Exception as e:
            logger.error(f"Error creating dependency: {e}")
            return None

    async def add_manual_dependency(
        self,
        device_id: UUID,
        service_name: str,
        depends_on: str,
        dependency_type: str = "manual",
        metadata: str | None = None,
    ) -> ServiceDependency | None:
        """
        Manually add a service dependency.

        Args:
            device_id: Device UUID
            service_name: Service that has the dependency
            depends_on: Service that is depended upon
            dependency_type: Type of dependency
            metadata: Optional metadata about the dependency

        Returns:
            Created ServiceDependency instance or None if failed
        """
        async with get_async_session() as session:
            try:
                dependency = await self._create_dependency(
                    session,
                    device_id=device_id,
                    service_name=service_name,
                    depends_on=depends_on,
                    dependency_type=dependency_type,
                    metadata=metadata,
                )

                if dependency:
                    await session.commit()
                    return dependency
                else:
                    return None

            except Exception as e:
                await session.rollback()
                logger.error(f"Error adding manual dependency: {e}")
                return None

    async def remove_dependencies_for_service(self, device_id: UUID, service_name: str) -> int:
        """
        Remove all dependencies for a given service.

        Args:
            device_id: Device UUID
            service_name: Service name

        Returns:
            Number of dependencies removed
        """
        async with get_async_session() as session:
            try:
                # Remove dependencies where service is the dependent
                stmt = delete(ServiceDependency).where(
                    ServiceDependency.device_id == device_id,
                    ServiceDependency.service_name == service_name,
                )

                result = await session.execute(stmt)
                removed_count = result.rowcount

                await session.commit()
                return removed_count

            except Exception as e:
                await session.rollback()
                logger.error(f"Error removing dependencies: {e}")
                return 0

    async def get_dependency_graph(self, device_id: UUID) -> dict[str, Any]:
        """
        Get the complete dependency graph for a device.

        Args:
            device_id: Device UUID

        Returns:
            Dictionary containing nodes and edges for dependency visualization
        """
        async with get_async_session() as session:
            try:
                # Get all dependencies for the device
                stmt = (
                    select(ServiceDependency)
                    .where(ServiceDependency.device_id == device_id)
                    .order_by(ServiceDependency.service_name)
                )

                result = await session.execute(stmt)
                dependencies = result.scalars().all()

                # Build nodes and edges
                nodes = set()
                edges = []

                for dep in dependencies:
                    nodes.add(dep.service_name)
                    nodes.add(dep.depends_on)
                    edges.append(
                        {
                            "from": dep.depends_on,
                            "to": dep.service_name,
                            "type": dep.dependency_type,
                            "metadata": dep.metadata,
                        }
                    )

                return {
                    "nodes": list(nodes),
                    "edges": edges,
                    "total_dependencies": len(dependencies),
                }

            except Exception as e:
                logger.error(f"Error getting dependency graph: {e}")
                return {"nodes": [], "edges": [], "total_dependencies": 0}


# Global singleton instance
_dependency_service: DependencyService | None = None


async def get_dependency_service() -> DependencyService:
    """Get the global dependency service instance."""
    global _dependency_service

    if _dependency_service is None:
        _dependency_service = DependencyService()

    return _dependency_service
