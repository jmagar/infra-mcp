"""
Configuration Export/Import Schemas

Pydantic schemas for configuration export and import operations.
Provides validation and serialization for archive-based backup and migration.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ConfigurationExportBase(BaseModel):
    """Base schema for configuration export data."""

    export_name: str = Field(..., min_length=1, max_length=255, description="Export name")
    description: str | None = Field(None, description="Export description")
    export_type: str = Field(
        ..., description="Export type (full, incremental, selective, device, compliance)"
    )

    # Scope and filtering
    device_ids: list[UUID] | None = Field(
        None, description="Specific devices to export (null = all)"
    )
    file_patterns: list[str] | None = Field(None, description="File patterns to include")
    date_range_start: datetime | None = Field(None, description="Start date for snapshot range")
    date_range_end: datetime | None = Field(None, description="End date for snapshot range")
    include_metadata: bool = Field(default=True, description="Include configuration metadata")
    include_content: bool = Field(default=True, description="Include file content")

    # Archive options
    archive_format: str = Field(default="tar.gz", description="Archive format")
    compression_level: int = Field(default=6, ge=0, le=9, description="Compression level (0-9)")
    encrypted: bool = Field(default=False, description="Whether to encrypt the archive")
    encryption_algorithm: str | None = Field(None, description="Encryption algorithm")

    # Export options
    export_options: dict[str, Any] | None = Field(
        None, description="Additional export configuration"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    @validator("export_type")
    def validate_export_type(cls, v):
        allowed = ["full", "incremental", "selective", "device", "compliance"]
        if v not in allowed:
            raise ValueError(f"Export type must be one of: {allowed}")
        return v

    @validator("archive_format")
    def validate_archive_format(cls, v):
        allowed = ["tar.gz", "zip", "tar.xz", "tar.bz2"]
        if v not in allowed:
            raise ValueError(f"Archive format must be one of: {allowed}")
        return v


class ConfigurationExportCreate(ConfigurationExportBase):
    """Schema for creating a new configuration export."""

    created_by: str = Field(..., description="User who created the export")


class ConfigurationExportUpdate(BaseModel):
    """Schema for updating an existing configuration export."""

    export_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    export_options: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ConfigurationExportResponse(ConfigurationExportBase):
    """Schema for configuration export API responses."""

    id: UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None

    # Export results
    total_snapshots: int
    exported_snapshots: int
    failed_snapshots: int
    skipped_snapshots: int

    # Archive information
    archive_path: str | None
    archive_size_bytes: int | None
    archive_checksum: str | None

    # Error information
    error_message: str | None
    retry_count: int

    # Timestamps
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConfigurationExportItemResponse(BaseModel):
    """Schema for configuration export item responses."""

    id: UUID
    export_id: UUID
    snapshot_id: UUID
    device_id: UUID

    file_path: str
    file_size_bytes: int | None
    content_hash: str | None

    status: str
    exported_at: datetime | None

    # Archive location
    archive_path: str | None
    archive_offset: int | None
    compressed_size: int | None

    error_message: str | None
    retry_count: int
    metadata: dict[str, Any] | None

    class Config:
        from_attributes = True


class ConfigurationImportBase(BaseModel):
    """Base schema for configuration import data."""

    import_name: str = Field(..., min_length=1, max_length=255, description="Import name")
    description: str | None = Field(None, description="Import description")
    import_type: str = Field(
        ..., description="Import type (restore, migrate, verify, merge, compliance)"
    )

    # Archive information
    archive_path: str = Field(..., description="Path to archive file")
    archive_format: str = Field(..., description="Archive format")

    # Decryption information
    encrypted: bool = Field(default=False, description="Whether archive is encrypted")
    decryption_algorithm: str | None = Field(None, description="Decryption algorithm")
    decryption_key_id: str | None = Field(None, description="Reference to decryption key")

    # Import options
    conflict_resolution: str = Field(default="skip", description="Conflict resolution strategy")
    target_device_mapping: dict[str, UUID] | None = Field(
        None, description="Map source devices to targets"
    )
    file_path_mapping: dict[str, str] | None = Field(
        None, description="Map source paths to targets"
    )
    import_options: dict[str, Any] | None = Field(None, description="Additional import options")

    # Validation options
    validate_before_import: bool = Field(default=True, description="Validate before importing")
    create_backup_before_import: bool = Field(
        default=True, description="Create backup before import"
    )

    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    @validator("import_type")
    def validate_import_type(cls, v):
        allowed = ["restore", "migrate", "verify", "merge", "compliance"]
        if v not in allowed:
            raise ValueError(f"Import type must be one of: {allowed}")
        return v

    @validator("conflict_resolution")
    def validate_conflict_resolution(cls, v):
        allowed = ["skip", "overwrite", "merge", "prompt", "rename"]
        if v not in allowed:
            raise ValueError(f"Conflict resolution must be one of: {allowed}")
        return v


class ConfigurationImportCreate(ConfigurationImportBase):
    """Schema for creating a new configuration import."""

    created_by: str = Field(..., description="User who created the import")


class ConfigurationImportUpdate(BaseModel):
    """Schema for updating an existing configuration import."""

    import_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    conflict_resolution: str | None = None
    target_device_mapping: dict[str, UUID] | None = None
    file_path_mapping: dict[str, str] | None = None
    import_options: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ConfigurationImportResponse(ConfigurationImportBase):
    """Schema for configuration import API responses."""

    id: UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None

    # Archive information
    archive_size_bytes: int | None
    archive_checksum: str | None
    archive_checksum_verified: bool

    # Import results
    total_items: int
    imported_items: int
    failed_items: int
    skipped_items: int

    # Validation results
    validation_status: str | None
    validation_errors: dict[str, Any] | None
    backup_export_id: UUID | None

    # Error information
    error_message: str | None
    retry_count: int

    # Timestamps
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConfigurationImportItemResponse(BaseModel):
    """Schema for configuration import item responses."""

    id: UUID
    import_id: UUID

    # Source information
    source_device_id: str
    source_file_path: str
    source_content_hash: str | None
    source_timestamp: datetime | None

    # Target information
    target_device_id: UUID | None
    target_file_path: str | None
    target_snapshot_id: UUID | None

    status: str
    processed_at: datetime | None

    # Conflict information
    conflict_detected: bool
    conflict_type: str | None
    conflict_resolution_applied: str | None
    original_backup_path: str | None

    # Validation results
    validation_status: str | None
    validation_errors: dict[str, Any] | None

    # File information
    file_size_bytes: int | None
    content_preview: str | None

    error_message: str | None
    retry_count: int
    metadata: dict[str, Any] | None

    class Config:
        from_attributes = True


class ConfigurationArchiveMetadataResponse(BaseModel):
    """Schema for configuration archive metadata responses."""

    id: UUID
    archive_path: str
    archive_name: str
    archive_format: str

    # Archive properties
    file_size_bytes: int
    checksum: str
    checksum_algorithm: str

    # Archive contents summary
    total_items: int
    device_count: int
    date_range_start: datetime | None
    date_range_end: datetime | None

    # Export information
    export_id: UUID | None
    created_by_system: bool

    # Archive structure
    device_list: list[str] | None
    file_patterns: list[str] | None
    content_summary: dict[str, Any] | None

    # Security information
    encrypted: bool
    encryption_algorithm: str | None
    signature_verified: bool
    signature_algorithm: str | None

    # Discovery and validation
    discovered_at: datetime
    last_validated_at: datetime | None
    validation_status: str
    validation_errors: dict[str, Any] | None

    # Access tracking
    last_accessed_at: datetime | None
    access_count: int

    # Archive metadata
    archive_version: str | None
    compatibility_version: str | None
    metadata: dict[str, Any] | None

    class Config:
        from_attributes = True


class ExportProgressResponse(BaseModel):
    """Schema for export progress responses."""

    export_id: UUID
    status: str
    progress_percentage: float = Field(..., ge=0, le=100, description="Export progress (0-100)")

    # Current stats
    total_snapshots: int
    processed_snapshots: int
    exported_snapshots: int
    failed_snapshots: int
    skipped_snapshots: int

    # Current operation
    current_operation: str | None = Field(None, description="Current operation description")
    current_file: str | None = Field(None, description="Currently processing file")

    # Time estimates
    started_at: datetime | None
    estimated_completion: datetime | None
    elapsed_time_seconds: float | None

    # Performance metrics
    files_per_second: float | None
    bytes_per_second: int | None
    archive_size_bytes: int | None

    error_message: str | None
    last_updated: datetime


class ImportProgressResponse(BaseModel):
    """Schema for import progress responses."""

    import_id: UUID
    status: str
    progress_percentage: float = Field(..., ge=0, le=100, description="Import progress (0-100)")

    # Current stats
    total_items: int
    processed_items: int
    imported_items: int
    failed_items: int
    skipped_items: int

    # Current operation
    current_operation: str | None = Field(None, description="Current operation description")
    current_file: str | None = Field(None, description="Currently processing file")

    # Conflict tracking
    conflicts_detected: int
    conflicts_resolved: int

    # Validation results
    validation_status: str | None
    validation_errors_count: int

    # Time estimates
    started_at: datetime | None
    estimated_completion: datetime | None
    elapsed_time_seconds: float | None

    # Performance metrics
    items_per_second: float | None
    bytes_processed: int | None

    error_message: str | None
    last_updated: datetime


class ArchiveValidationRequest(BaseModel):
    """Schema for archive validation requests."""

    archive_path: str = Field(..., description="Path to archive file")
    verify_checksum: bool = Field(default=True, description="Verify archive checksum")
    verify_structure: bool = Field(default=True, description="Verify archive structure")
    quick_validation: bool = Field(default=False, description="Perform quick validation only")


class ArchiveValidationResponse(BaseModel):
    """Schema for archive validation responses."""

    validation_status: str  # valid, invalid, corrupted, encrypted, unknown
    validation_errors: list[str] = Field(default=[], description="Validation error messages")

    # Archive properties
    archive_format: str | None
    file_size_bytes: int | None
    checksum: str | None
    checksum_verified: bool

    # Contents summary
    total_items: int | None
    device_count: int | None
    date_range_start: datetime | None
    date_range_end: datetime | None

    # Structure validation
    structure_valid: bool
    missing_metadata: list[str] = Field(default=[], description="Missing required metadata")

    # Compatibility
    archive_version: str | None
    compatible_with_system: bool
    required_system_version: str | None

    # Security
    encrypted: bool
    signature_present: bool
    signature_verified: bool | None

    validated_at: datetime


class ExportFilterRequest(BaseModel):
    """Schema for export filtering requests."""

    device_ids: list[UUID] | None = Field(None, description="Filter by specific devices")
    file_patterns: list[str] | None = Field(None, description="File patterns to include")

    # Date range filtering
    date_range_start: datetime | None = Field(None, description="Start date for snapshots")
    date_range_end: datetime | None = Field(None, description="End date for snapshots")

    # Content filtering
    include_empty_files: bool = Field(default=True, description="Include empty configuration files")
    min_file_size: int | None = Field(None, ge=0, description="Minimum file size to include")
    max_file_size: int | None = Field(None, ge=1, description="Maximum file size to include")

    # Change-based filtering
    only_changed_files: bool = Field(default=False, description="Only include files that changed")
    changes_since: datetime | None = Field(None, description="Only include changes since date")

    # Tag-based filtering
    device_tags: list[str] | None = Field(None, description="Filter by device tags")
    exclude_device_tags: list[str] | None = Field(None, description="Exclude devices with tags")


class ImportMappingRequest(BaseModel):
    """Schema for import device/path mapping requests."""

    # Device mapping
    device_mapping: dict[str, UUID] = Field(
        ..., description="Map source device IDs to target device IDs"
    )

    # Path mapping (optional)
    path_mapping: dict[str, str] | None = Field(
        None, description="Map source paths to target paths"
    )

    # Mapping validation
    validate_targets: bool = Field(default=True, description="Validate target devices exist")
    create_missing_paths: bool = Field(
        default=False, description="Create missing target directories"
    )


class BulkExportRequest(BaseModel):
    """Schema for bulk export requests."""

    exports: list[ConfigurationExportCreate] = Field(
        ..., min_items=1, max_items=10, description="Export operations to create"
    )

    # Execution options
    run_sequentially: bool = Field(default=True, description="Run exports sequentially vs parallel")
    stop_on_first_error: bool = Field(default=False, description="Stop all exports if one fails")

    # Notification options
    notify_on_completion: bool = Field(default=True, description="Send notification when complete")
    notification_channels: list[str] | None = Field(
        None, description="Notification channels to use"
    )


class BulkImportRequest(BaseModel):
    """Schema for bulk import requests."""

    imports: list[ConfigurationImportCreate] = Field(
        ..., min_items=1, max_items=5, description="Import operations to create"
    )

    # Execution options
    run_sequentially: bool = Field(default=True, description="Run imports sequentially vs parallel")
    stop_on_first_error: bool = Field(default=True, description="Stop all imports if one fails")

    # Validation options
    validate_all_before_import: bool = Field(
        default=True, description="Validate all archives before importing any"
    )

    # Notification options
    notify_on_completion: bool = Field(default=True, description="Send notification when complete")
    notification_channels: list[str] | None = Field(
        None, description="Notification channels to use"
    )


class ExportImportDashboardResponse(BaseModel):
    """Schema for export/import dashboard summary."""

    # Export statistics
    total_exports: int
    active_exports: int
    completed_exports: int
    failed_exports: int

    # Import statistics
    total_imports: int
    active_imports: int
    completed_imports: int
    failed_imports: int

    # Recent operations
    recent_exports: list[ConfigurationExportResponse] = Field(
        default=[], description="Recent export operations"
    )
    recent_imports: list[ConfigurationImportResponse] = Field(
        default=[], description="Recent import operations"
    )

    # Archive statistics
    total_archives: int
    total_archive_size_bytes: int
    encrypted_archives: int

    # Storage statistics
    disk_usage_bytes: int
    available_space_bytes: int | None
    cleanup_recommendations: list[str] = Field(
        default=[], description="Storage cleanup recommendations"
    )

    last_updated: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "total_exports": 15,
                "active_exports": 2,
                "completed_exports": 12,
                "failed_exports": 1,
                "total_imports": 8,
                "active_imports": 1,
                "completed_imports": 6,
                "failed_imports": 1,
                "recent_exports": [],
                "recent_imports": [],
                "total_archives": 20,
                "total_archive_size_bytes": 5368709120,
                "encrypted_archives": 3,
                "disk_usage_bytes": 5368709120,
                "available_space_bytes": 107374182400,
                "cleanup_recommendations": ["Delete exports older than 90 days"],
                "last_updated": "2025-01-08T10:30:00Z",
            }
        }
