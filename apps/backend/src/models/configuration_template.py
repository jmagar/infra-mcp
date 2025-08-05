"""
Configuration Template Models

Database models for configuration template management with Jinja2 support.
Enables templated configuration files with variable substitution and validation.
"""

from datetime import datetime, timezone
from uuid import uuid4, UUID
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class TemplateType(Enum):
    """Template type enumeration."""

    DOCKER_COMPOSE = "docker_compose"
    PROXY_CONFIG = "proxy_config"
    SYSTEMD_SERVICE = "systemd_service"
    NGINX_CONFIG = "nginx_config"
    ENVIRONMENT_FILE = "environment_file"
    SHELL_SCRIPT = "shell_script"
    CONFIG_FILE = "config_file"
    YAML_CONFIG = "yaml_config"
    JSON_CONFIG = "json_config"


class ValidationMode(Enum):
    """Template validation mode enumeration."""

    STRICT = "strict"  # All variables must be defined
    PERMISSIVE = "permissive"  # Allow undefined variables
    SYNTAX_ONLY = "syntax_only"  # Only check Jinja2 syntax


class ConfigurationTemplate(Base):
    """
    Configuration template model with Jinja2 support.

    Stores reusable configuration templates that can be instantiated
    with different variable sets across multiple devices and environments.
    """

    __tablename__ = "configuration_templates"

    # Primary identification
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Template metadata
    template_type = Column(String(50), nullable=False)  # TemplateType enum
    category = Column(String(100), nullable=True)  # User-defined category
    version = Column(String(50), nullable=False, default="1.0.0")

    # Template content
    template_content = Column(Text, nullable=False)  # Jinja2 template
    default_variables = Column(JSON, nullable=False, default=dict)  # Default variable values
    required_variables = Column(JSON, nullable=False, default=list)  # Required variable names
    variable_schema = Column(JSON, nullable=True)  # JSON schema for variables

    # Template configuration
    validation_mode = Column(String(20), nullable=False, default=ValidationMode.STRICT.value)
    auto_reload = Column(Boolean, nullable=False, default=False)  # Auto-reload from source
    source_path = Column(String(500), nullable=True)  # Optional source file path

    # Template metadata
    tags = Column(JSON, nullable=False, default=list)  # Template tags
    environments = Column(JSON, nullable=False, default=list)  # Target environments
    supported_devices = Column(JSON, nullable=True)  # Device type restrictions

    # Status and lifecycle
    active = Column(Boolean, nullable=False, default=True)
    validated = Column(Boolean, nullable=False, default=False)
    validation_errors = Column(JSON, nullable=True)  # Validation error details
    last_validated_at = Column(DateTime(timezone=True), nullable=True)

    # Usage statistics
    usage_count = Column(JSON, nullable=False, default=dict)  # Usage per device/env
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(String(255), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_by = Column(String(255), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_template_name_version"),
        Index("ix_configuration_templates_name", "name"),
        Index("ix_configuration_templates_type", "template_type"),
        Index("ix_configuration_templates_category", "category"),
        Index("ix_configuration_templates_active", "active"),
        Index("ix_configuration_templates_created_at", "created_at"),
        Index("ix_configuration_templates_tags", "tags", postgresql_using="gin"),
        Index("ix_configuration_templates_environments", "environments", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return (
            f"<ConfigurationTemplate(id={self.id}, name='{self.name}', version='{self.version}')>"
        )


class TemplateInstance(Base):
    """
    Template instance model.

    Represents a specific instantiation of a template with resolved variables
    and deployment information.
    """

    __tablename__ = "template_instances"

    # Primary identification
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    template_id = Column(PG_UUID(as_uuid=True), nullable=False)
    device_id = Column(PG_UUID(as_uuid=True), nullable=False)

    # Instance metadata
    name = Column(String(255), nullable=False)  # Instance name
    description = Column(Text, nullable=True)
    environment = Column(String(100), nullable=False)  # Deployment environment

    # Variable resolution
    variables = Column(JSON, nullable=False, default=dict)  # Resolved variables
    rendered_content = Column(Text, nullable=True)  # Final rendered content
    content_hash = Column(String(64), nullable=True)  # SHA-256 of rendered content

    # Deployment information
    target_path = Column(String(500), nullable=False)  # Target file path
    file_mode = Column(String(10), nullable=True)  # File permissions (e.g., "0644")
    file_owner = Column(String(100), nullable=True)  # File owner
    file_group = Column(String(100), nullable=True)  # File group

    # Status and validation
    deployed = Column(Boolean, nullable=False, default=False)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    deployed_by = Column(String(255), nullable=True)
    validation_status = Column(String(20), nullable=True)  # valid, invalid, pending
    validation_errors = Column(JSON, nullable=True)

    # Change tracking
    drift_detected = Column(Boolean, nullable=False, default=False)
    last_drift_check = Column(DateTime(timezone=True), nullable=True)
    drift_details = Column(JSON, nullable=True)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(String(255), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_by = Column(String(255), nullable=False)

    # Foreign key relationships (defined as strings to avoid circular imports)
    # template = relationship("ConfigurationTemplate", back_populates="instances")
    # device = relationship("Device", back_populates="template_instances")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "template_id", "device_id", "target_path", name="uq_instance_template_device_path"
        ),
        Index("ix_template_instances_template_id", "template_id"),
        Index("ix_template_instances_device_id", "device_id"),
        Index("ix_template_instances_environment", "environment"),
        Index("ix_template_instances_deployed", "deployed"),
        Index("ix_template_instances_created_at", "created_at"),
        Index("ix_template_instances_target_path", "target_path"),
    )

    def __repr__(self) -> str:
        return f"<TemplateInstance(id={self.id}, template_id={self.template_id}, device_id={self.device_id})>"


class TemplateVariable(Base):
    """
    Template variable definition model.

    Defines available variables for templates with metadata, validation rules,
    and default values for different environments.
    """

    __tablename__ = "template_variables"

    # Primary identification
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    template_id = Column(PG_UUID(as_uuid=True), nullable=False)

    # Variable definition
    name = Column(String(255), nullable=False)  # Variable name
    description = Column(Text, nullable=True)
    variable_type = Column(String(50), nullable=False)  # string, number, boolean, json, etc.

    # Validation and constraints
    required = Column(Boolean, nullable=False, default=False)
    validation_regex = Column(String(500), nullable=True)  # Regex pattern
    allowed_values = Column(JSON, nullable=True)  # List of allowed values
    min_length = Column(JSON, nullable=True)  # Minimum length (for strings)
    max_length = Column(JSON, nullable=True)  # Maximum length (for strings)

    # Default values per environment
    default_value = Column(JSON, nullable=True)  # Default value
    environment_defaults = Column(JSON, nullable=False, default=dict)  # Per-env defaults

    # Metadata
    sensitive = Column(Boolean, nullable=False, default=False)  # Mark as sensitive
    documentation = Column(Text, nullable=True)  # Extended documentation
    examples = Column(JSON, nullable=True)  # Example values

    # Audit fields
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(String(255), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Foreign key relationships
    # template = relationship("ConfigurationTemplate", back_populates="variables")

    # Constraints
    __table_args__ = (
        UniqueConstraint("template_id", "name", name="uq_template_variable_name"),
        Index("ix_template_variables_template_id", "template_id"),
        Index("ix_template_variables_name", "name"),
        Index("ix_template_variables_required", "required"),
        Index("ix_template_variables_sensitive", "sensitive"),
    )

    def __repr__(self) -> str:
        return (
            f"<TemplateVariable(id={self.id}, template_id={self.template_id}, name='{self.name}')>"
        )
