"""
Configuration Export/Import Models

Database models for configuration export and import operations.
Supports archive-based backup and migration system for configurations.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Integer,
    BigInteger,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..core.database import Base


class ConfigurationExport(Base):
    """
    Configuration export operation record.

    Tracks the export of configuration snapshots into archive formats
    for backup, migration, or compliance purposes.
    """

    __tablename__ = "configuration_exports"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Export metadata
    export_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    export_type = Column(String(100), nullable=False, index=True)  # full, incremental, selective

    # Scope and filtering
    device_ids = Column(JSONB, nullable=True)  # Specific devices (null = all)
    file_patterns = Column(JSONB, nullable=True)  # File patterns to include
    date_range_start = Column(DateTime(timezone=True), nullable=True, index=True)
    date_range_end = Column(DateTime(timezone=True), nullable=True, index=True)
    include_metadata = Column(Boolean, nullable=False, default=True)
    include_content = Column(Boolean, nullable=False, default=True)

    # Export execution
    status = Column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Export results
    total_snapshots = Column(Integer, nullable=False, default=0)
    exported_snapshots = Column(Integer, nullable=False, default=0)
    failed_snapshots = Column(Integer, nullable=False, default=0)
    skipped_snapshots = Column(Integer, nullable=False, default=0)

    # Archive information
    archive_format = Column(String(50), nullable=False, default="tar.gz")  # tar.gz, zip, tar.xz
    archive_path = Column(String(1000), nullable=True)  # Path to created archive
    archive_size_bytes = Column(BigInteger, nullable=True)
    archive_checksum = Column(String(128), nullable=True)  # SHA256 checksum

    # Compression and encryption
    compression_level = Column(Integer, nullable=False, default=6)  # 0-9 compression level
    encrypted = Column(Boolean, nullable=False, default=False)
    encryption_algorithm = Column(String(100), nullable=True)  # AES-256-GCM, etc.

    # Export options
    export_options = Column(JSONB, nullable=True)  # Additional export configuration

    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Audit and tracking
    created_by = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Additional metadata
    additional_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    export_items = relationship(
        "ConfigurationExportItem",
        back_populates="export",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_config_exports_status_created", "status", "created_at"),
        Index("idx_config_exports_type_date", "export_type", "created_at"),
        Index("idx_config_exports_date_range", "date_range_start", "date_range_end"),
        Index("idx_config_exports_archive_path", "archive_path"),
        CheckConstraint(
            "export_type IN ('full', 'incremental', 'selective', 'device', 'compliance')",
            name="check_export_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="check_export_status",
        ),
        CheckConstraint(
            "archive_format IN ('tar.gz', 'zip', 'tar.xz', 'tar.bz2')",
            name="check_archive_format",
        ),
        CheckConstraint(
            "compression_level >= 0 AND compression_level <= 9",
            name="check_compression_level",
        ),
    )


class ConfigurationExportItem(Base):
    """
    Individual configuration item within an export operation.

    Tracks each configuration snapshot that was included in an export,
    with status and error information for granular tracking.
    """

    __tablename__ = "configuration_export_items"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key relationships
    export_id = Column(
        UUID(as_uuid=True), ForeignKey("configuration_exports.id"), nullable=False, index=True
    )
    snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("configuration_snapshots.id"), nullable=False, index=True
    )
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)

    # Item details
    file_path = Column(String(1000), nullable=False, index=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    content_hash = Column(String(128), nullable=True)

    # Export status for this item
    status = Column(String(50), nullable=False, default="pending", index=True)
    exported_at = Column(DateTime(timezone=True), nullable=True)

    # Archive location within the export
    archive_path = Column(String(1000), nullable=True)  # Path within the archive
    archive_offset = Column(BigInteger, nullable=True)  # Byte offset in archive
    compressed_size = Column(BigInteger, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Item metadata
    additional_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    export = relationship("ConfigurationExport", back_populates="export_items")
    snapshot = relationship("ConfigurationSnapshot")
    device = relationship("Device")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_export_items_export_status", "export_id", "status"),
        Index("idx_export_items_device_file", "device_id", "file_path"),
        Index("idx_export_items_snapshot_export", "snapshot_id", "export_id"),
        CheckConstraint(
            "status IN ('pending', 'exporting', 'completed', 'failed', 'skipped')",
            name="check_export_item_status",
        ),
    )


class ConfigurationImport(Base):
    """
    Configuration import operation record.

    Tracks the import of configuration archives back into the system
    for restoration, migration, or compliance verification.
    """

    __tablename__ = "configuration_imports"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Import metadata
    import_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    import_type = Column(String(100), nullable=False, index=True)  # restore, migrate, verify, merge

    # Source archive information
    archive_path = Column(String(1000), nullable=False)
    archive_format = Column(String(50), nullable=False)
    archive_size_bytes = Column(BigInteger, nullable=True)
    archive_checksum = Column(String(128), nullable=True)
    archive_checksum_verified = Column(Boolean, nullable=False, default=False)

    # Decryption information
    encrypted = Column(Boolean, nullable=False, default=False)
    decryption_algorithm = Column(String(100), nullable=True)
    decryption_key_id = Column(String(255), nullable=True)  # Reference to key store

    # Import execution
    status = Column(String(50), nullable=False, default="pending", index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Import results
    total_items = Column(Integer, nullable=False, default=0)
    imported_items = Column(Integer, nullable=False, default=0)
    failed_items = Column(Integer, nullable=False, default=0)
    skipped_items = Column(Integer, nullable=False, default=0)

    # Import options and strategy
    conflict_resolution = Column(
        String(50), nullable=False, default="skip"
    )  # skip, overwrite, merge, prompt
    target_device_mapping = Column(JSONB, nullable=True)  # Map source devices to target devices
    file_path_mapping = Column(JSONB, nullable=True)  # Map source paths to target paths
    import_options = Column(JSONB, nullable=True)

    # Validation and verification
    validate_before_import = Column(Boolean, nullable=False, default=True)
    validation_status = Column(String(50), nullable=True)  # passed, failed, skipped
    validation_errors = Column(JSONB, nullable=True)
    create_backup_before_import = Column(Boolean, nullable=False, default=True)
    backup_export_id = Column(
        UUID(as_uuid=True), ForeignKey("configuration_exports.id"), nullable=True
    )

    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Audit and tracking
    created_by = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Additional metadata
    additional_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    import_items = relationship(
        "ConfigurationImportItem",
        back_populates="import_op",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    backup_export = relationship("ConfigurationExport")

    # Indexes for performance
    __table_args__ = (
        Index("idx_config_imports_status_created", "status", "created_at"),
        Index("idx_config_imports_type_date", "import_type", "created_at"),
        Index("idx_config_imports_archive_path", "archive_path"),
        CheckConstraint(
            "import_type IN ('restore', 'migrate', 'verify', 'merge', 'compliance')",
            name="check_import_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'validating', 'running', 'completed', 'failed', 'cancelled')",
            name="check_import_status",
        ),
        CheckConstraint(
            "conflict_resolution IN ('skip', 'overwrite', 'merge', 'prompt', 'rename')",
            name="check_conflict_resolution",
        ),
        CheckConstraint(
            "validation_status IS NULL OR validation_status IN ('passed', 'failed', 'skipped')",
            name="check_validation_status",
        ),
    )


class ConfigurationImportItem(Base):
    """
    Individual configuration item within an import operation.

    Tracks each configuration snapshot that was processed during import,
    with conflict resolution and error information.
    """

    __tablename__ = "configuration_import_items"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key relationships
    import_id = Column(
        UUID(as_uuid=True), ForeignKey("configuration_imports.id"), nullable=False, index=True
    )

    # Source information (from archive)
    source_device_id = Column(String(255), nullable=False)  # Original device ID from archive
    source_file_path = Column(String(1000), nullable=False)
    source_content_hash = Column(String(128), nullable=True)
    source_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Target information (in current system)
    target_device_id = Column(
        UUID(as_uuid=True), ForeignKey("devices.id"), nullable=True, index=True
    )
    target_file_path = Column(String(1000), nullable=True)
    target_snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("configuration_snapshots.id"), nullable=True, index=True
    )

    # Import processing
    status = Column(String(50), nullable=False, default="pending", index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Conflict resolution
    conflict_detected = Column(Boolean, nullable=False, default=False)
    conflict_type = Column(
        String(100), nullable=True
    )  # file_exists, content_differs, device_not_found
    conflict_resolution_applied = Column(String(50), nullable=True)
    original_backup_path = Column(String(1000), nullable=True)  # Path to backed up original

    # Validation results
    validation_status = Column(String(50), nullable=True)
    validation_errors = Column(JSONB, nullable=True)

    # File information
    file_size_bytes = Column(BigInteger, nullable=True)
    content_preview = Column(Text, nullable=True)  # First few lines for verification

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Item metadata
    additional_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    import_op = relationship("ConfigurationImport", back_populates="import_items")
    target_device = relationship("Device")
    target_snapshot = relationship("ConfigurationSnapshot")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_import_items_import_status", "import_id", "status"),
        Index("idx_import_items_source_device_file", "source_device_id", "source_file_path"),
        Index("idx_import_items_target_device", "target_device_id"),
        Index("idx_import_items_conflict", "conflict_detected", "conflict_type"),
        CheckConstraint(
            "status IN ('pending', 'validating', 'importing', 'completed', 'failed', 'skipped')",
            name="check_import_item_status",
        ),
        CheckConstraint(
            "validation_status IS NULL OR validation_status IN ('passed', 'failed', 'skipped')",
            name="check_import_item_validation_status",
        ),
    )


class ConfigurationArchiveMetadata(Base):
    """
    Metadata about configuration archive files.

    Tracks information about archive files for quick lookup and validation
    without needing to open and inspect the archive contents.
    """

    __tablename__ = "configuration_archive_metadata"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Archive identification
    archive_path = Column(String(1000), nullable=False, unique=True, index=True)
    archive_name = Column(String(255), nullable=False, index=True)
    archive_format = Column(String(50), nullable=False)

    # Archive properties
    file_size_bytes = Column(BigInteger, nullable=False)
    checksum = Column(String(128), nullable=False)  # SHA256
    checksum_algorithm = Column(String(50), nullable=False, default="sha256")

    # Archive contents summary
    total_items = Column(Integer, nullable=False, default=0)
    device_count = Column(Integer, nullable=False, default=0)
    date_range_start = Column(DateTime(timezone=True), nullable=True)
    date_range_end = Column(DateTime(timezone=True), nullable=True)

    # Export information (if created by this system)
    export_id = Column(UUID(as_uuid=True), ForeignKey("configuration_exports.id"), nullable=True)
    created_by_system = Column(Boolean, nullable=False, default=False)

    # Archive structure
    device_list = Column(JSONB, nullable=True)  # List of devices in archive
    file_patterns = Column(JSONB, nullable=True)  # File patterns included
    content_summary = Column(JSONB, nullable=True)  # Summary of archive contents

    # Security information
    encrypted = Column(Boolean, nullable=False, default=False)
    encryption_algorithm = Column(String(100), nullable=True)
    signature_verified = Column(Boolean, nullable=False, default=False)
    signature_algorithm = Column(String(100), nullable=True)

    # Discovery and validation
    discovered_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_validated_at = Column(DateTime(timezone=True), nullable=True)
    validation_status = Column(String(50), nullable=False, default="unknown")
    validation_errors = Column(JSONB, nullable=True)

    # Access tracking
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(Integer, nullable=False, default=0)

    # Archive metadata
    archive_version = Column(String(50), nullable=True)  # Version of export format
    compatibility_version = Column(String(50), nullable=True)  # Minimum system version to import
    additional_metadata = Column("metadata", JSONB, nullable=True)

    # Relationships
    export = relationship("ConfigurationExport")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_archive_metadata_name_format", "archive_name", "archive_format"),
        Index("idx_archive_metadata_size_date", "file_size_bytes", "discovered_at"),
        Index("idx_archive_metadata_checksum", "checksum"),
        Index("idx_archive_metadata_validation", "validation_status", "last_validated_at"),
        Index("idx_archive_metadata_date_range", "date_range_start", "date_range_end"),
        CheckConstraint(
            "validation_status IN ('unknown', 'valid', 'invalid', 'corrupted', 'encrypted')",
            name="check_archive_validation_status",
        ),
    )
