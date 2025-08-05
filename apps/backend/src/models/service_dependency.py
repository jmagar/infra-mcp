"""
Service Dependency Model

Database model for tracking service dependencies and relationships
across different infrastructure services and configurations.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class ServiceDependency(Base):
    """
    Tracks dependencies between services for impact analysis.

    This model stores relationships between services to enable
    more accurate impact analysis when configurations change.
    Dependencies can be populated automatically (from docker-compose
    depends_on fields) or manually configured.
    """

    __tablename__ = "service_dependencies"

    # Primary key
    id = Column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key to device
    device_id = Column(
        PgUUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Service that has the dependency
    service_name = Column(String(255), nullable=False)

    # Service that is depended upon
    depends_on = Column(String(255), nullable=False)

    # Type of dependency (docker, network, config_file, etc.)
    dependency_type = Column(String(50), nullable=False)

    # Optional additional metadata about the dependency
    dependency_metadata = Column(String(1000), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    device = relationship("Device", back_populates="service_dependencies")

    # Indexes for performance
    __table_args__ = (
        # Unique constraint to prevent duplicate dependencies
        Index(
            "idx_service_deps_unique",
            "device_id",
            "service_name",
            "depends_on",
            unique=True,
        ),
        # Index for finding dependencies by service
        Index("idx_service_deps_service", "device_id", "service_name"),
        # Index for finding reverse dependencies
        Index("idx_service_deps_depends_on", "device_id", "depends_on"),
        # Index for filtering by dependency type
        Index("idx_service_deps_type", "dependency_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<ServiceDependency("
            f"id={self.id}, "
            f"device_id={self.device_id}, "
            f"service_name='{self.service_name}', "
            f"depends_on='{self.depends_on}', "
            f"dependency_type='{self.dependency_type}'"
            f")>"
        )
