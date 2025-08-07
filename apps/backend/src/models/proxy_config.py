"""
Proxy Configuration Database Models

SQLAlchemy models for storing SWAG reverse proxy configurations
with TimescaleDB integration for change tracking.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from apps.backend.src.core.database import Base


class ProxyConfig(Base):
    """
    Main table for reverse proxy configurations

    Stores nginx configuration files from SWAG with parsed metadata
    and sync tracking information.
    """

    __tablename__ = "proxy_configs"

    # Primary fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(255), ForeignKey("devices.hostname"), nullable=False, index=True)
    service_name = Column(String(255), nullable=False, index=True)
    subdomain = Column(String(255), nullable=False, index=True)
    config_type = Column(String(50), nullable=False, default="subdomain", index=True)
    status = Column(String(50), nullable=False, default="active", index=True)

    # File information
    file_path = Column(String(1024), nullable=False, unique=True)
    file_size = Column(Integer)
    file_hash = Column(String(64), index=True)  # SHA256 hash
    last_modified = Column(DateTime(timezone=True))

    # Configuration content
    raw_content = Column(Text)  # Raw nginx config
    parsed_config = Column(JSON)  # Parsed configuration data

    # Metadata
    description = Column(Text)
    tags = Column(JSON, default=dict)  # Custom tags as JSON

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )

    # Sync tracking
    sync_status = Column(String(50), nullable=False, default="synced", index=True)
    sync_last_checked = Column(DateTime(timezone=True))
    sync_error_count = Column(Integer, default=0)
    sync_last_error = Column(Text)

    # Relationships
    device = relationship("Device", back_populates="proxy_configs")
    changes = relationship(
        "ProxyConfigChange", back_populates="config", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "device_id", "service_name", name="proxy_configs_device_id_service_name_key"
        ),
        CheckConstraint(
            "config_type IN ('subdomain', 'subfolder', 'port', 'custom')",
            name="ck_proxy_config_type",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'error', 'pending')", name="ck_proxy_config_status"
        ),
        CheckConstraint(
            "sync_status IN ('synced', 'out_of_sync', 'error', 'pending')",
            name="ck_proxy_config_sync_status",
        ),
        Index("ix_proxy_configs_device_status", "device_id", "status"),
        Index("ix_proxy_configs_service_subdomain", "service_name", "subdomain"),
        Index("ix_proxy_configs_sync", "sync_status", "sync_last_checked"),
        Index("ix_proxy_configs_file_hash", "file_hash"),
    )

    @validates("service_name", "subdomain")
    def validate_names(self, key, value):
        """Validate service and subdomain names"""
        if not value or not value.strip():
            raise ValueError(f"{key} cannot be empty")

        # Basic validation for DNS-compatible names
        if not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"{key} must contain only alphanumeric characters, hyphens, and underscores"
            )

        return value.strip().lower()

    @validates("file_path")
    def validate_file_path(self, key, value):
        """Validate file path format"""
        if not value or not value.strip():
            raise ValueError("file_path cannot be empty")

        # Ensure it's an absolute path to a .conf file
        if not value.startswith("/"):
            raise ValueError("file_path must be an absolute path")

        if not value.endswith(".conf"):
            raise ValueError("file_path must point to a .conf file")

        return value.strip()

    def __repr__(self):
        return f"<ProxyConfig(id={self.id}, service='{self.service_name}', subdomain='{self.subdomain}')>"


class ProxyConfigChange(Base):
    """
    Time-series table for tracking changes to proxy configurations

    This will be a TimescaleDB hypertable for efficient storage
    and querying of configuration change history.
    """

    __tablename__ = "proxy_config_changes"

    # Primary fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        Integer, ForeignKey("proxy_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Change information
    change_type = Column(
        String(50), nullable=False, index=True
    )  # created, modified, deleted, synced
    old_hash = Column(String(64))
    new_hash = Column(String(64))
    changes_detected = Column(JSON, default=list)  # List of specific changes

    # File metadata at time of change
    file_size_before = Column(Integer)
    file_size_after = Column(Integer)
    last_modified_before = Column(DateTime(timezone=True))
    last_modified_after = Column(DateTime(timezone=True))

    # Change details
    change_summary = Column(Text)
    triggered_by = Column(String(255))  # polling, manual, api, etc.

    # Timestamps (time column for TimescaleDB partitioning)
    time = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    # Relationships
    config = relationship("ProxyConfig", back_populates="changes")

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('created', 'modified', 'deleted', 'synced', 'error')",
            name="ck_proxy_change_type",
        ),
        Index("ix_proxy_config_changes_time", "time"),
        Index("ix_proxy_config_changes_config_time", "config_id", "time"),
        Index("ix_proxy_config_changes_type_time", "change_type", "time"),
    )

    def __repr__(self):
        return f"<ProxyConfigChange(id={self.id}, config_id={self.config_id}, type='{self.change_type}')>"


class ProxyConfigTemplate(Base):
    """
    Templates for generating proxy configurations

    Stores reusable nginx configuration templates with variables
    for common service patterns.
    """

    __tablename__ = "proxy_config_templates"

    # Primary fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)

    # Template configuration
    config_type = Column(String(50), nullable=False, default="subdomain", index=True)
    template_content = Column(Text, nullable=False)
    variables = Column(JSON, default=list)  # List of variable names
    example_values = Column(JSON, default=dict)  # Example values for variables

    # Metadata
    category = Column(String(100), index=True)  # web, api, database, etc.
    tags = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True, index=True)
    usage_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )
    created_by = Column(String(255))

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "config_type IN ('subdomain', 'subfolder', 'port', 'custom')",
            name="ck_template_config_type",
        ),
        Index("ix_proxy_templates_category", "category"),
        Index("ix_proxy_templates_active", "is_active"),
    )

    @validates("name")
    def validate_name(self, key, value):
        """Validate template name"""
        if not value or not value.strip():
            raise ValueError("Template name cannot be empty")

        return value.strip()

    def __repr__(self):
        return f"<ProxyConfigTemplate(id={self.id}, name='{self.name}', type='{self.config_type}')>"


class ProxyConfigValidation(Base):
    """
    Nginx configuration validation results

    Stores results of nginx -t validation checks
    for configuration files.
    """

    __tablename__ = "proxy_config_validations"

    # Primary fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        Integer, ForeignKey("proxy_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Validation results
    is_valid = Column(Boolean, nullable=False, index=True)
    errors = Column(JSON, default=list)  # List of error messages
    warnings = Column(JSON, default=list)  # List of warning messages
    nginx_test_output = Column(Text)  # Raw nginx -t output

    # Validation metadata
    nginx_version = Column(String(100))
    validation_method = Column(String(50), default="nginx_test")  # nginx_test, syntax_check, etc.
    config_hash = Column(String(64))  # Hash of config at validation time

    # Timestamps
    validated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)

    # Relationships
    config = relationship("ProxyConfig")

    # Constraints
    __table_args__ = (
        Index("ix_proxy_validations_config_time", "config_id", "validated_at"),
        Index("ix_proxy_validations_valid", "is_valid", "validated_at"),
    )

    def __repr__(self):
        return f"<ProxyConfigValidation(id={self.id}, config_id={self.config_id}, valid={self.is_valid})>"


# Proxy config relationship is now defined directly in the Device model
