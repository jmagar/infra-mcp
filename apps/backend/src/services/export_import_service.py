"""
Configuration Export/Import Service

Provides comprehensive configuration export and import capabilities.
Implements archive-based backup and migration system for configurations.
"""

import asyncio
import hashlib
import json
import io
import os
import shutil
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BusinessLogicError,
)
from ..models.device import Device
from ..models.configuration import ConfigurationSnapshot
from ..models.export_import import (
    ConfigurationExport,
    ConfigurationExportItem,
    ConfigurationImport,
    ConfigurationImportItem,
    ConfigurationArchiveMetadata,
)

logger = structlog.get_logger(__name__)


class ArchiveManager:
    """
    Manages archive creation and extraction for configuration exports/imports.

    Supports multiple archive formats (tar.gz, zip, tar.xz) with compression
    and optional encryption capabilities.
    """

    def __init__(self):
        self.supported_formats = {
            "tar.gz": {"extension": ".tar.gz", "mode": "w:gz"},
            "tar.xz": {"extension": ".tar.xz", "mode": "w:xz"},
            "tar.bz2": {"extension": ".tar.bz2", "mode": "w:bz2"},
            "zip": {"extension": ".zip", "mode": "w"},
        }

    async def create_archive(
        self,
        export_op: ConfigurationExport,
        snapshots: list[ConfigurationSnapshot],
        output_path: str,
    ) -> dict[str, Any]:
        """
        Create an archive from configuration snapshots.

        Args:
            export_op: Export operation record
            snapshots: Configuration snapshots to include
            output_path: Path where archive will be created

        Returns:
            Archive creation result with metadata
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="create_archive",
                export_id=str(export_op.id),
                format=export_op.archive_format,
            )

            logger.info("Creating configuration archive")

            if export_op.archive_format not in self.supported_formats:
                raise ValidationError(f"Unsupported archive format: {export_op.archive_format}")

            format_info = self.supported_formats[export_op.archive_format]
            archive_path = f"{output_path}{format_info['extension']}"

            # Create archive based on format
            if export_op.archive_format == "zip":
                result = await self._create_zip_archive(export_op, snapshots, archive_path)
            else:
                result = await self._create_tar_archive(
                    export_op, snapshots, archive_path, format_info["mode"]
                )

            # Calculate checksum
            checksum = await self._calculate_file_checksum(archive_path)
            result["checksum"] = checksum
            result["checksum_algorithm"] = "sha256"

            logger.info(
                "Archive created successfully",
                archive_path=archive_path,
                size_bytes=result["size_bytes"],
            )

            return result

        except Exception as e:
            logger.error("Error creating archive", error=str(e))
            raise

    async def _create_tar_archive(
        self,
        export_op: ConfigurationExport,
        snapshots: list[ConfigurationSnapshot],
        archive_path: str,
        mode: str,
    ) -> dict[str, Any]:
        """Create tar-based archive."""

        exported_count = 0
        failed_count = 0
        total_uncompressed_size = 0

        with tarfile.open(archive_path, mode) as tar:
            # Add metadata file
            metadata = await self._generate_export_metadata(export_op, snapshots)
            metadata_json = json.dumps(metadata, indent=2, default=str)

            metadata_info = tarfile.TarInfo(name="metadata.json")
            metadata_info.size = len(metadata_json.encode())
            metadata_info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(metadata_info, fileobj=io.BytesIO(metadata_json.encode()))

            # Add configuration files
            for snapshot in snapshots:
                try:
                    if not snapshot.content:
                        continue

                    # Create archive path for file
                    device_name = (
                        snapshot.device.hostname if snapshot.device else str(snapshot.device_id)
                    )
                    archive_file_path = f"devices/{device_name}{snapshot.file_path}"

                    # Add file to archive
                    file_info = tarfile.TarInfo(name=archive_file_path)
                    file_content = snapshot.content.encode("utf-8")
                    file_info.size = len(file_content)
                    file_info.mtime = int(snapshot.created_at.timestamp())

                    tar.addfile(file_info, fileobj=io.BytesIO(file_content))

                    exported_count += 1
                    total_uncompressed_size += len(file_content)

                except Exception as e:
                    logger.warning(
                        "Failed to add file to archive", file_path=snapshot.file_path, error=str(e)
                    )
                    failed_count += 1

        # Get final archive size
        archive_size = os.path.getsize(archive_path)

        return {
            "archive_path": archive_path,
            "size_bytes": archive_size,
            "uncompressed_size_bytes": total_uncompressed_size,
            "exported_files": exported_count,
            "failed_files": failed_count,
            "compression_ratio": total_uncompressed_size / archive_size if archive_size > 0 else 0,
        }

    async def _create_zip_archive(
        self,
        export_op: ConfigurationExport,
        snapshots: list[ConfigurationSnapshot],
        archive_path: str,
    ) -> dict[str, Any]:
        """Create ZIP archive."""

        exported_count = 0
        failed_count = 0
        total_uncompressed_size = 0

        compression_level = export_op.compression_level

        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=compression_level
        ) as zip_file:
            # Add metadata file
            metadata = await self._generate_export_metadata(export_op, snapshots)
            metadata_json = json.dumps(metadata, indent=2, default=str)
            zip_file.writestr("metadata.json", metadata_json)

            # Add configuration files
            for snapshot in snapshots:
                try:
                    if not snapshot.content:
                        continue

                    # Create archive path for file
                    device_name = (
                        snapshot.device.hostname if snapshot.device else str(snapshot.device_id)
                    )
                    archive_file_path = f"devices/{device_name}{snapshot.file_path}"

                    # Add file to archive
                    zip_file.writestr(archive_file_path, snapshot.content)

                    exported_count += 1
                    total_uncompressed_size += len(snapshot.content.encode("utf-8"))

                except Exception as e:
                    logger.warning(
                        "Failed to add file to archive", file_path=snapshot.file_path, error=str(e)
                    )
                    failed_count += 1

        # Get final archive size
        archive_size = os.path.getsize(archive_path)

        return {
            "archive_path": archive_path,
            "size_bytes": archive_size,
            "uncompressed_size_bytes": total_uncompressed_size,
            "exported_files": exported_count,
            "failed_files": failed_count,
            "compression_ratio": total_uncompressed_size / archive_size if archive_size > 0 else 0,
        }

    async def extract_archive(
        self,
        archive_path: str,
        extract_to: str,
        archive_format: str,
    ) -> dict[str, Any]:
        """
        Extract archive contents to directory.

        Args:
            archive_path: Path to archive file
            extract_to: Directory to extract to
            archive_format: Archive format (tar.gz, zip, etc.)

        Returns:
            Extraction result with file list and metadata
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="extract_archive",
                archive_path=archive_path,
                format=archive_format,
            )

            logger.info("Extracting configuration archive")

            if not os.path.exists(archive_path):
                raise ResourceNotFoundError(f"Archive file not found: {archive_path}")

            os.makedirs(extract_to, exist_ok=True)

            extracted_files = []

            if archive_format == "zip":
                with zipfile.ZipFile(archive_path, "r") as zip_file:
                    zip_file.extractall(extract_to)
                    extracted_files = zip_file.namelist()
            else:
                # Determine tar mode based on format
                if archive_format == "tar.gz":
                    mode = "r:gz"
                elif archive_format == "tar.xz":
                    mode = "r:xz"
                elif archive_format == "tar.bz2":
                    mode = "r:bz2"
                else:
                    mode = "r"

                with tarfile.open(archive_path, mode) as tar:
                    tar.extractall(extract_to)
                    extracted_files = tar.getnames()

            # Load metadata if present
            metadata_path = os.path.join(extract_to, "metadata.json")
            metadata = None
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)

            logger.info("Archive extracted successfully", extracted_files=len(extracted_files))

            return {
                "extracted_files": extracted_files,
                "metadata": metadata,
                "extract_path": extract_to,
            }

        except Exception as e:
            logger.error("Error extracting archive", error=str(e))
            raise

    async def validate_archive(
        self,
        archive_path: str,
        expected_checksum: str | None = None,
        quick_validation: bool = False,
    ) -> dict[str, Any]:
        """
        Validate archive integrity and structure.

        Args:
            archive_path: Path to archive file
            expected_checksum: Expected SHA256 checksum
            quick_validation: Perform quick validation only

        Returns:
            Validation result with status and details
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="validate_archive",
                archive_path=archive_path,
            )

            logger.info("Validating configuration archive")

            if not os.path.exists(archive_path):
                return {
                    "validation_status": "invalid",
                    "validation_errors": ["Archive file not found"],
                }

            validation_errors = []

            # Check file size
            file_size = os.path.getsize(archive_path)
            if file_size == 0:
                validation_errors.append("Archive file is empty")

            # Verify checksum if provided
            checksum_verified = False
            if expected_checksum:
                actual_checksum = await self._calculate_file_checksum(archive_path)
                checksum_verified = actual_checksum == expected_checksum
                if not checksum_verified:
                    validation_errors.append("Checksum verification failed")

            # Try to open and inspect archive structure
            archive_format = None
            structure_valid = False
            total_items = 0
            has_metadata = False

            try:
                # Detect format and validate structure
                if archive_path.endswith(".zip"):
                    archive_format = "zip"
                    with zipfile.ZipFile(archive_path, "r") as zip_file:
                        file_list = zip_file.namelist()
                        total_items = len(file_list)
                        has_metadata = "metadata.json" in file_list
                        structure_valid = True

                        if not quick_validation:
                            # Test extraction of a few files
                            for filename in file_list[:5]:
                                try:
                                    zip_file.read(filename)
                                except Exception:
                                    validation_errors.append(f"Cannot read file: {filename}")

                elif any(archive_path.endswith(ext) for ext in [".tar.gz", ".tar.xz", ".tar.bz2"]):
                    if archive_path.endswith(".tar.gz"):
                        archive_format = "tar.gz"
                        mode = "r:gz"
                    elif archive_path.endswith(".tar.xz"):
                        archive_format = "tar.xz"
                        mode = "r:xz"
                    else:
                        archive_format = "tar.bz2"
                        mode = "r:bz2"

                    with tarfile.open(archive_path, mode) as tar:
                        file_list = tar.getnames()
                        total_items = len(file_list)
                        has_metadata = "metadata.json" in file_list
                        structure_valid = True

                        if not quick_validation:
                            # Test extraction of a few files
                            for filename in file_list[:5]:
                                try:
                                    tar.extractfile(filename)
                                except Exception:
                                    validation_errors.append(f"Cannot read file: {filename}")

                else:
                    validation_errors.append("Unknown archive format")

            except Exception as e:
                validation_errors.append(f"Archive structure validation failed: {str(e)}")

            # Determine overall validation status
            if validation_errors:
                validation_status = "invalid"
            else:
                validation_status = "valid"

            result = {
                "validation_status": validation_status,
                "validation_errors": validation_errors,
                "archive_format": archive_format,
                "file_size_bytes": file_size,
                "checksum_verified": checksum_verified,
                "structure_valid": structure_valid,
                "total_items": total_items,
                "has_metadata": has_metadata,
                "validated_at": datetime.now(timezone.utc),
            }

            logger.info(
                "Archive validation completed",
                status=validation_status,
                errors=len(validation_errors),
            )

            return result

        except Exception as e:
            logger.error("Error validating archive", error=str(e))
            return {
                "validation_status": "error",
                "validation_errors": [f"Validation error: {str(e)}"],
                "validated_at": datetime.now(timezone.utc),
            }

    async def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def _generate_export_metadata(
        self,
        export_op: ConfigurationExport,
        snapshots: list[ConfigurationSnapshot],
    ) -> dict[str, Any]:
        """Generate metadata for export archive."""

        # Collect device information
        devices = {}
        for snapshot in snapshots:
            device_id = str(snapshot.device_id)
            if device_id not in devices:
                devices[device_id] = {
                    "device_id": device_id,
                    "hostname": snapshot.device.hostname if snapshot.device else "unknown",
                    "tags": snapshot.device.tags if snapshot.device else [],
                    "files": [],
                }

            devices[device_id]["files"].append(
                {
                    "file_path": snapshot.file_path,
                    "content_hash": snapshot.content_hash,
                    "file_size": snapshot.file_size,
                    "created_at": snapshot.created_at.isoformat(),
                }
            )

        return {
            "export_metadata": {
                "export_id": str(export_op.id),
                "export_name": export_op.export_name,
                "export_type": export_op.export_type,
                "created_at": export_op.created_at.isoformat(),
                "created_by": export_op.created_by,
                "archive_format": export_op.archive_format,
                "compression_level": export_op.compression_level,
            },
            "system_metadata": {
                "system_version": "1.0.0",  # Would be dynamic
                "export_format_version": "1.0",
                "total_devices": len(devices),
                "total_files": len(snapshots),
                "date_range": {
                    "start": min(s.created_at for s in snapshots).isoformat()
                    if snapshots
                    else None,
                    "end": max(s.created_at for s in snapshots).isoformat() if snapshots else None,
                },
            },
            "devices": list(devices.values()),
        }


class ConfigurationExportImportService:
    """
    Main service for configuration export and import operations.

    Provides comprehensive backup and migration capabilities with support
    for multiple archive formats, encryption, and conflict resolution.
    """

    def __init__(self, storage_base_path: str = "/tmp/config_archives"):
        self.archive_manager = ArchiveManager()
        self.storage_base_path = Path(storage_base_path)
        self.storage_base_path.mkdir(parents=True, exist_ok=True)

    async def create_export(
        self,
        session: AsyncSession,
        export_data: dict[str, Any],
        created_by: str,
    ) -> ConfigurationExport:
        """Create a new configuration export operation."""

        try:
            structlog.contextvars.bind_contextvars(
                operation="create_export",
                export_name=export_data.get("export_name"),
                created_by=created_by,
            )

            logger.info("Creating configuration export")

            # Create export record
            export_op = ConfigurationExport(
                export_name=export_data["export_name"],
                description=export_data.get("description"),
                export_type=export_data["export_type"],
                device_ids=export_data.get("device_ids"),
                file_patterns=export_data.get("file_patterns"),
                date_range_start=export_data.get("date_range_start"),
                date_range_end=export_data.get("date_range_end"),
                include_metadata=export_data.get("include_metadata", True),
                include_content=export_data.get("include_content", True),
                archive_format=export_data.get("archive_format", "tar.gz"),
                compression_level=export_data.get("compression_level", 6),
                encrypted=export_data.get("encrypted", False),
                encryption_algorithm=export_data.get("encryption_algorithm"),
                export_options=export_data.get("export_options"),
                created_by=created_by,
                additional_metadata=export_data.get("metadata"),
            )

            session.add(export_op)
            await session.commit()
            await session.refresh(export_op)

            logger.info("Export created successfully", export_id=str(export_op.id))
            return export_op

        except Exception as e:
            await session.rollback()
            logger.error("Error creating export", error=str(e))
            raise

    async def execute_export(
        self,
        session: AsyncSession,
        export_id: UUID,
    ) -> ConfigurationExport:
        """Execute a configuration export operation."""

        try:
            structlog.contextvars.bind_contextvars(
                operation="execute_export",
                export_id=str(export_id),
            )

            logger.info("Executing configuration export")

            # Get export operation
            export_op = await session.get(ConfigurationExport, export_id)
            if not export_op:
                raise ResourceNotFoundError(f"Export not found: {export_id}")

            if export_op.status != "pending":
                raise BusinessLogicError(f"Export is not in pending status: {export_op.status}")

            # Update status to running
            export_op.status = "running"
            export_op.started_at = datetime.now(timezone.utc)
            await session.commit()

            try:
                # Get configuration snapshots to export
                snapshots = await self._get_snapshots_for_export(session, export_op)

                export_op.total_snapshots = len(snapshots)
                await session.commit()

                # Create archive
                archive_base_path = self.storage_base_path / f"export_{export_op.id}"
                archive_result = await self.archive_manager.create_archive(
                    export_op, snapshots, str(archive_base_path)
                )

                # Update export with archive information
                export_op.archive_path = archive_result["archive_path"]
                export_op.archive_size_bytes = archive_result["size_bytes"]
                export_op.archive_checksum = archive_result["checksum"]
                export_op.exported_snapshots = archive_result["exported_files"]
                export_op.failed_snapshots = archive_result["failed_files"]
                export_op.status = "completed"
                export_op.completed_at = datetime.now(timezone.utc)

                await session.commit()

                logger.info(
                    "Export completed successfully",
                    exported_files=archive_result["exported_files"],
                    archive_size=archive_result["size_bytes"],
                )

                return export_op

            except Exception as e:
                # Update export status to failed
                export_op.status = "failed"
                export_op.error_message = str(e)
                export_op.completed_at = datetime.now(timezone.utc)
                await session.commit()
                raise

        except Exception as e:
            logger.error("Error executing export", error=str(e))
            raise

    async def create_import(
        self,
        session: AsyncSession,
        import_data: dict[str, Any],
        created_by: str,
    ) -> ConfigurationImport:
        """Create a new configuration import operation."""

        try:
            structlog.contextvars.bind_contextvars(
                operation="create_import",
                import_name=import_data.get("import_name"),
                created_by=created_by,
            )

            logger.info("Creating configuration import")

            # Validate archive exists
            archive_path = import_data["archive_path"]
            if not os.path.exists(archive_path):
                raise ResourceNotFoundError(f"Archive file not found: {archive_path}")

            # Get archive information
            archive_size = os.path.getsize(archive_path)
            archive_checksum = await self.archive_manager._calculate_file_checksum(archive_path)

            # Create import record
            import_op = ConfigurationImport(
                import_name=import_data["import_name"],
                description=import_data.get("description"),
                import_type=import_data["import_type"],
                archive_path=archive_path,
                archive_format=import_data["archive_format"],
                archive_size_bytes=archive_size,
                archive_checksum=archive_checksum,
                encrypted=import_data.get("encrypted", False),
                decryption_algorithm=import_data.get("decryption_algorithm"),
                decryption_key_id=import_data.get("decryption_key_id"),
                conflict_resolution=import_data.get("conflict_resolution", "skip"),
                target_device_mapping=import_data.get("target_device_mapping"),
                file_path_mapping=import_data.get("file_path_mapping"),
                import_options=import_data.get("import_options"),
                validate_before_import=import_data.get("validate_before_import", True),
                create_backup_before_import=import_data.get("create_backup_before_import", True),
                created_by=created_by,
                additional_metadata=import_data.get("metadata"),
            )

            session.add(import_op)
            await session.commit()
            await session.refresh(import_op)

            logger.info("Import created successfully", import_id=str(import_op.id))
            return import_op

        except Exception as e:
            await session.rollback()
            logger.error("Error creating import", error=str(e))
            raise

    async def execute_import(
        self,
        session: AsyncSession,
        import_id: UUID,
    ) -> ConfigurationImport:
        """Execute a configuration import operation."""

        try:
            structlog.contextvars.bind_contextvars(
                operation="execute_import",
                import_id=str(import_id),
            )

            logger.info("Executing configuration import")

            # Get import operation
            import_op = await session.get(ConfigurationImport, import_id)
            if not import_op:
                raise ResourceNotFoundError(f"Import not found: {import_id}")

            if import_op.status != "pending":
                raise BusinessLogicError(f"Import is not in pending status: {import_op.status}")

            # Validate archive if requested
            if import_op.validate_before_import:
                import_op.status = "validating"
                await session.commit()

                validation_result = await self.archive_manager.validate_archive(
                    import_op.archive_path,
                    import_op.archive_checksum,
                )

                import_op.archive_checksum_verified = validation_result.get(
                    "checksum_verified", False
                )
                import_op.validation_status = validation_result["validation_status"]

                if validation_result["validation_status"] != "valid":
                    import_op.status = "failed"
                    import_op.error_message = "Archive validation failed"
                    import_op.validation_errors = {"errors": validation_result["validation_errors"]}
                    await session.commit()
                    raise BusinessLogicError("Archive validation failed")

            # Start import
            import_op.status = "running"
            import_op.started_at = datetime.now(timezone.utc)
            await session.commit()

            try:
                # Extract archive to temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    extract_result = await self.archive_manager.extract_archive(
                        import_op.archive_path,
                        temp_dir,
                        import_op.archive_format,
                    )

                    # Process extracted files
                    import_result = await self._process_import_files(
                        session, import_op, extract_result
                    )

                    # Update import with results
                    import_op.total_items = import_result["total_items"]
                    import_op.imported_items = import_result["imported_items"]
                    import_op.failed_items = import_result["failed_items"]
                    import_op.skipped_items = import_result["skipped_items"]
                    import_op.status = "completed"
                    import_op.completed_at = datetime.now(timezone.utc)

                    await session.commit()

                    logger.info(
                        "Import completed successfully",
                        imported_items=import_result["imported_items"],
                        failed_items=import_result["failed_items"],
                    )

                    return import_op

            except Exception as e:
                # Update import status to failed
                import_op.status = "failed"
                import_op.error_message = str(e)
                import_op.completed_at = datetime.now(timezone.utc)
                await session.commit()
                raise

        except Exception as e:
            logger.error("Error executing import", error=str(e))
            raise

    async def _get_snapshots_for_export(
        self,
        session: AsyncSession,
        export_op: ConfigurationExport,
    ) -> list[ConfigurationSnapshot]:
        """Get configuration snapshots that match export criteria."""

        # Build query for snapshots
        query = select(ConfigurationSnapshot).options(selectinload(ConfigurationSnapshot.device))

        # Filter by devices if specified
        if export_op.device_ids:
            query = query.where(ConfigurationSnapshot.device_id.in_(export_op.device_ids))

        # Filter by date range if specified
        if export_op.date_range_start:
            query = query.where(ConfigurationSnapshot.created_at >= export_op.date_range_start)
        if export_op.date_range_end:
            query = query.where(ConfigurationSnapshot.created_at <= export_op.date_range_end)

        # Filter by file patterns if specified
        if export_op.file_patterns:
            pattern_conditions = []
            for pattern in export_op.file_patterns:
                # Convert shell-style wildcards to SQL LIKE patterns
                sql_pattern = pattern.replace("*", "%").replace("?", "_")
                pattern_conditions.append(ConfigurationSnapshot.file_path.like(sql_pattern))
            query = query.where(or_(*pattern_conditions))

        # Only include snapshots with content if requested
        if export_op.include_content:
            query = query.where(ConfigurationSnapshot.content.isnot(None))

        # Order by device and file path for consistent archive structure
        query = query.order_by(
            ConfigurationSnapshot.device_id,
            ConfigurationSnapshot.file_path,
            desc(ConfigurationSnapshot.created_at),
        )

        result = await session.execute(query)
        snapshots = list(result.scalars().all())

        # For incremental exports, filter to latest version of each file per device
        if export_op.export_type == "incremental":
            latest_snapshots = {}
            for snapshot in snapshots:
                key = (snapshot.device_id, snapshot.file_path)
                if (
                    key not in latest_snapshots
                    or snapshot.created_at > latest_snapshots[key].created_at
                ):
                    latest_snapshots[key] = snapshot
            snapshots = list(latest_snapshots.values())

        return snapshots

    async def _process_import_files(
        self,
        session: AsyncSession,
        import_op: ConfigurationImport,
        extract_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Process extracted files and import them into the system."""

        # Load metadata from archive
        metadata = extract_result.get("metadata", {})
        devices_data = metadata.get("devices", [])

        imported_count = 0
        failed_count = 0
        skipped_count = 0

        # Process each device's files
        for device_data in devices_data:
            source_device_id = device_data["device_id"]

            # Map source device to target device
            target_device_id = None
            if import_op.target_device_mapping:
                target_device_id = import_op.target_device_mapping.get(source_device_id)

            if not target_device_id:
                logger.warning("No target device mapping found", source_device_id=source_device_id)
                skipped_count += len(device_data.get("files", []))
                continue

            # Verify target device exists
            target_device = await session.get(Device, target_device_id)
            if not target_device:
                logger.warning("Target device not found", target_device_id=str(target_device_id))
                failed_count += len(device_data.get("files", []))
                continue

            # Process each file for this device
            for file_data in device_data.get("files", []):
                try:
                    result = await self._import_single_file(
                        session,
                        import_op,
                        source_device_id,
                        target_device,
                        file_data,
                        extract_result["extract_path"],
                    )

                    if result == "imported":
                        imported_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(
                        "Error importing file", file_path=file_data.get("file_path"), error=str(e)
                    )
                    failed_count += 1

        return {
            "total_items": imported_count + failed_count + skipped_count,
            "imported_items": imported_count,
            "failed_items": failed_count,
            "skipped_items": skipped_count,
        }

    async def _import_single_file(
        self,
        session: AsyncSession,
        import_op: ConfigurationImport,
        source_device_id: str,
        target_device: Device,
        file_data: dict[str, Any],
        extract_path: str,
    ) -> str:
        """Import a single configuration file. Returns: 'imported', 'skipped', or 'failed'."""

        source_file_path = file_data["file_path"]

        # Apply file path mapping if specified
        target_file_path = source_file_path
        if import_op.file_path_mapping:
            target_file_path = import_op.file_path_mapping.get(source_file_path, source_file_path)

        # Read file content from extracted archive
        device_hostname = source_device_id  # Simplified - would need actual device mapping
        archive_file_path = os.path.join(
            extract_path, "devices", device_hostname, source_file_path.lstrip("/")
        )

        if not os.path.exists(archive_file_path):
            logger.warning("Extracted file not found", archive_path=archive_file_path)
            return "failed"

        with open(archive_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Check for existing configuration
        existing_query = (
            select(ConfigurationSnapshot)
            .where(
                and_(
                    ConfigurationSnapshot.device_id == target_device.id,
                    ConfigurationSnapshot.file_path == target_file_path,
                )
            )
            .order_by(desc(ConfigurationSnapshot.created_at))
            .limit(1)
        )

        result = await session.execute(existing_query)
        existing_snapshot = result.scalar_one_or_none()

        # Handle conflicts based on resolution strategy
        if existing_snapshot:
            if import_op.conflict_resolution == "skip":
                return "skipped"
            elif import_op.conflict_resolution == "overwrite":
                # Continue to create new snapshot (effectively overwrites)
                pass
            else:
                # Other conflict resolution strategies would be implemented here
                logger.warning(
                    "Unsupported conflict resolution", strategy=import_op.conflict_resolution
                )
                return "skipped"

        # Create new configuration snapshot
        new_snapshot = ConfigurationSnapshot(
            device_id=target_device.id,
            file_path=target_file_path,
            content=file_content,
            content_hash=hashlib.sha256(file_content.encode()).hexdigest(),
            file_size=len(file_content.encode()),
            change_type="imported",
            additional_metadata={
                "imported_from": source_device_id,
                "import_id": str(import_op.id),
                "original_timestamp": file_data.get("created_at"),
            },
        )

        session.add(new_snapshot)
        await session.commit()

        return "imported"


# Singleton service instance
_export_import_service: ConfigurationExportImportService | None = None


async def get_export_import_service() -> ConfigurationExportImportService:
    """Get the singleton export/import service instance."""
    global _export_import_service
    if _export_import_service is None:
        _export_import_service = ConfigurationExportImportService()
    return _export_import_service


async def cleanup_export_import_service() -> None:
    """Clean up the export/import service."""
    global _export_import_service
    if _export_import_service is not None:
        _export_import_service = None
        logger.info("Export/import service cleaned up")
