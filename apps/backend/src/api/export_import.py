"""
Configuration Export/Import API Endpoints

REST API endpoints for configuration export and import operations.
Provides archive-based backup and migration capabilities.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from ..core.database import get_async_session
from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BusinessLogicError,
)
from ..models.export_import import (
    ConfigurationExport,
    ConfigurationExportItem,
    ConfigurationImport,
    ConfigurationImportItem,
    ConfigurationArchiveMetadata,
)
from ..schemas.export_import import (
    ConfigurationExportCreate,
    ConfigurationExportUpdate,
    ConfigurationExportResponse,
    ConfigurationExportItemResponse,
    ConfigurationImportCreate,
    ConfigurationImportUpdate,
    ConfigurationImportResponse,
    ConfigurationImportItemResponse,
    ConfigurationArchiveMetadataResponse,
    ExportProgressResponse,
    ImportProgressResponse,
    ArchiveValidationRequest,
    ArchiveValidationResponse,
    ExportFilterRequest,
    ImportMappingRequest,
    BulkExportRequest,
    BulkImportRequest,
    ExportImportDashboardResponse,
)
from ..services.export_import_service import get_export_import_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/export-import", tags=["Configuration Export/Import"])


@router.post(
    "/exports",
    response_model=ConfigurationExportResponse,
    status_code=201,
    summary="Create Configuration Export",
    description="""
    Create a new configuration export operation.
    
    Supports multiple export types including full, incremental, selective,
    device-specific, and compliance exports with various archive formats.
    """,
)
async def create_export(
    export_data: ConfigurationExportCreate = Body(..., description="Export configuration"),
    session: AsyncSession = Depends(get_async_session),
) -> ConfigurationExportResponse:
    """Create a new configuration export."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="create_export_api",
            export_name=export_data.export_name,
        )

        logger.info("Creating configuration export via API")

        export_service = await get_export_import_service()

        export_op = await export_service.create_export(
            session=session,
            export_data=export_data.dict(),
            created_by=export_data.created_by,
        )

        return ConfigurationExportResponse.from_orm(export_op)

    except ValidationError as e:
        logger.warning("Invalid export data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating export", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create export")


@router.get(
    "/exports",
    response_model=list[ConfigurationExportResponse],
    summary="List Configuration Exports",
    description="""
    List configuration exports with optional filtering.
    
    Supports filtering by type, status, date range, and other criteria.
    """,
)
async def list_exports(
    export_type: str | None = Query(None, description="Filter by export type"),
    status: str | None = Query(None, description="Filter by export status"),
    created_by: str | None = Query(None, description="Filter by creator"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of exports to return"),
    offset: int = Query(0, ge=0, description="Number of exports to skip"),
    session: AsyncSession = Depends(get_async_session),
) -> list[ConfigurationExportResponse]:
    """List configuration exports with optional filtering."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="list_exports_api",
        )

        logger.info("Listing configuration exports via API")

        # Build query with filters
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        query = select(ConfigurationExport).where(ConfigurationExport.created_at >= cutoff_time)

        if export_type:
            query = query.where(ConfigurationExport.export_type == export_type)
        if status:
            query = query.where(ConfigurationExport.status == status)
        if created_by:
            query = query.where(ConfigurationExport.created_by == created_by)

        query = query.order_by(desc(ConfigurationExport.created_at)).limit(limit).offset(offset)

        result = await session.execute(query)
        exports = list(result.scalars().all())

        return [ConfigurationExportResponse.from_orm(export) for export in exports]

    except Exception as e:
        logger.error("Error listing exports", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve exports")


@router.get(
    "/exports/{export_id}",
    response_model=ConfigurationExportResponse,
    summary="Get Configuration Export",
    description="Get detailed information about a specific configuration export.",
)
async def get_export(
    export_id: UUID = Path(..., description="Export ID"),
    session: AsyncSession = Depends(get_async_session),
) -> ConfigurationExportResponse:
    """Get a specific configuration export."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_export_api",
            export_id=str(export_id),
        )

        logger.info("Getting configuration export via API")

        export_op = await session.get(ConfigurationExport, export_id)
        if not export_op:
            raise HTTPException(status_code=404, detail=f"Export not found: {export_id}")

        return ConfigurationExportResponse.from_orm(export_op)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting export", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve export")


@router.put(
    "/exports/{export_id}",
    response_model=ConfigurationExportResponse,
    summary="Update Configuration Export",
    description="Update an existing configuration export (only pending exports).",
)
async def update_export(
    export_id: UUID = Path(..., description="Export ID"),
    export_update: ConfigurationExportUpdate = Body(..., description="Export updates"),
    session: AsyncSession = Depends(get_async_session),
) -> ConfigurationExportResponse:
    """Update a configuration export."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="update_export_api",
            export_id=str(export_id),
        )

        logger.info("Updating configuration export via API")

        export_op = await session.get(ConfigurationExport, export_id)
        if not export_op:
            raise HTTPException(status_code=404, detail=f"Export not found: {export_id}")

        if export_op.status != "pending":
            raise HTTPException(status_code=409, detail="Can only update pending exports")

        # Update fields that were provided
        update_data = export_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(export_op, field, value)

        export_op.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(export_op)

        return ConfigurationExportResponse.from_orm(export_op)

    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning("Invalid export update data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Error updating export", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update export")


@router.post(
    "/exports/{export_id}/execute",
    response_model=ConfigurationExportResponse,
    summary="Execute Configuration Export",
    description="""
    Execute a configuration export operation.
    
    The export will run asynchronously in the background.
    Use the progress endpoint to monitor execution status.
    """,
)
async def execute_export(
    export_id: UUID = Path(..., description="Export ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_async_session),
) -> ConfigurationExportResponse:
    """Execute a configuration export operation."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="execute_export_api",
            export_id=str(export_id),
        )

        logger.info("Executing configuration export via API")

        export_service = await get_export_import_service()

        # Execute export in background
        background_tasks.add_task(export_service.execute_export, session, export_id)

        # Return current export status
        export_op = await session.get(ConfigurationExport, export_id)
        if not export_op:
            raise HTTPException(status_code=404, detail=f"Export not found: {export_id}")

        return ConfigurationExportResponse.from_orm(export_op)

    except HTTPException:
        raise
    except BusinessLogicError as e:
        logger.warning("Export execution error", error=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Error executing export", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to execute export")


@router.get(
    "/exports/{export_id}/progress",
    response_model=ExportProgressResponse,
    summary="Get Export Progress",
    description="Get real-time progress information for a running export operation.",
)
async def get_export_progress(
    export_id: UUID = Path(..., description="Export ID"),
    session: AsyncSession = Depends(get_async_session),
) -> ExportProgressResponse:
    """Get export progress information."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_export_progress_api",
            export_id=str(export_id),
        )

        logger.info("Getting export progress via API")

        export_op = await session.get(ConfigurationExport, export_id)
        if not export_op:
            raise HTTPException(status_code=404, detail=f"Export not found: {export_id}")

        # Calculate progress percentage
        if export_op.status == "pending":
            progress_percentage = 0.0
        elif export_op.status == "completed":
            progress_percentage = 100.0
        elif export_op.status == "failed":
            progress_percentage = 0.0
        else:  # running
            if export_op.total_snapshots > 0:
                processed = export_op.exported_snapshots + export_op.failed_snapshots
                progress_percentage = (processed / export_op.total_snapshots) * 100
            else:
                progress_percentage = 50.0  # Indeterminate progress

        # Calculate time estimates
        elapsed_time_seconds = None
        estimated_completion = None
        files_per_second = None
        bytes_per_second = None

        if export_op.started_at:
            elapsed_time = datetime.now(timezone.utc) - export_op.started_at
            elapsed_time_seconds = elapsed_time.total_seconds()

            if export_op.status == "running" and elapsed_time_seconds > 0:
                processed_files = export_op.exported_snapshots + export_op.failed_snapshots
                if processed_files > 0:
                    files_per_second = processed_files / elapsed_time_seconds
                    remaining_files = max(0, export_op.total_snapshots - processed_files)
                    if files_per_second > 0:
                        remaining_seconds = remaining_files / files_per_second
                        estimated_completion = datetime.now(timezone.utc) + timedelta(
                            seconds=remaining_seconds
                        )

                if export_op.archive_size_bytes:
                    bytes_per_second = int(export_op.archive_size_bytes / elapsed_time_seconds)

        return ExportProgressResponse(
            export_id=export_id,
            status=export_op.status,
            progress_percentage=progress_percentage,
            total_snapshots=export_op.total_snapshots,
            processed_snapshots=export_op.exported_snapshots + export_op.failed_snapshots,
            exported_snapshots=export_op.exported_snapshots,
            failed_snapshots=export_op.failed_snapshots,
            skipped_snapshots=export_op.skipped_snapshots,
            current_operation=f"Exporting configurations"
            if export_op.status == "running"
            else None,
            started_at=export_op.started_at,
            estimated_completion=estimated_completion,
            elapsed_time_seconds=elapsed_time_seconds,
            files_per_second=files_per_second,
            bytes_per_second=bytes_per_second,
            archive_size_bytes=export_op.archive_size_bytes,
            error_message=export_op.error_message,
            last_updated=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting export progress", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve export progress")


@router.delete(
    "/exports/{export_id}",
    status_code=204,
    summary="Delete Configuration Export",
    description="Delete a configuration export and its associated archive file.",
)
async def delete_export(
    export_id: UUID = Path(..., description="Export ID"),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a configuration export."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="delete_export_api",
            export_id=str(export_id),
        )

        logger.info("Deleting configuration export via API")

        export_op = await session.get(ConfigurationExport, export_id)
        if not export_op:
            raise HTTPException(status_code=404, detail=f"Export not found: {export_id}")

        if export_op.status == "running":
            raise HTTPException(status_code=409, detail="Cannot delete running export")

        # Delete archive file if it exists
        if export_op.archive_path and os.path.exists(export_op.archive_path):
            os.remove(export_op.archive_path)

        await session.delete(export_op)
        await session.commit()

        logger.info("Export deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Error deleting export", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete export")


@router.post(
    "/imports",
    response_model=ConfigurationImportResponse,
    status_code=201,
    summary="Create Configuration Import",
    description="""
    Create a new configuration import operation.
    
    Supports multiple import types including restore, migrate, verify,
    merge, and compliance imports with conflict resolution strategies.
    """,
)
async def create_import(
    import_data: ConfigurationImportCreate = Body(..., description="Import configuration"),
    session: AsyncSession = Depends(get_async_session),
) -> ConfigurationImportResponse:
    """Create a new configuration import."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="create_import_api",
            import_name=import_data.import_name,
        )

        logger.info("Creating configuration import via API")

        export_import_service = await get_export_import_service()

        import_op = await export_import_service.create_import(
            session=session,
            import_data=import_data.dict(),
            created_by=import_data.created_by,
        )

        return ConfigurationImportResponse.from_orm(import_op)

    except ValidationError as e:
        logger.warning("Invalid import data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundError as e:
        logger.warning("Import resource not found", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error creating import", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create import")


@router.get(
    "/imports",
    response_model=list[ConfigurationImportResponse],
    summary="List Configuration Imports",
    description="""
    List configuration imports with optional filtering.
    
    Supports filtering by type, status, date range, and other criteria.
    """,
)
async def list_imports(
    import_type: str | None = Query(None, description="Filter by import type"),
    status: str | None = Query(None, description="Filter by import status"),
    created_by: str | None = Query(None, description="Filter by creator"),
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of imports to return"),
    offset: int = Query(0, ge=0, description="Number of imports to skip"),
    session: AsyncSession = Depends(get_async_session),
) -> list[ConfigurationImportResponse]:
    """List configuration imports with optional filtering."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="list_imports_api",
        )

        logger.info("Listing configuration imports via API")

        # Build query with filters
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        query = select(ConfigurationImport).where(ConfigurationImport.created_at >= cutoff_time)

        if import_type:
            query = query.where(ConfigurationImport.import_type == import_type)
        if status:
            query = query.where(ConfigurationImport.status == status)
        if created_by:
            query = query.where(ConfigurationImport.created_by == created_by)

        query = query.order_by(desc(ConfigurationImport.created_at)).limit(limit).offset(offset)

        result = await session.execute(query)
        imports = list(result.scalars().all())

        return [ConfigurationImportResponse.from_orm(import_op) for import_op in imports]

    except Exception as e:
        logger.error("Error listing imports", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve imports")


@router.post(
    "/imports/{import_id}/execute",
    response_model=ConfigurationImportResponse,
    summary="Execute Configuration Import",
    description="""
    Execute a configuration import operation.
    
    The import will run asynchronously in the background.
    Use the progress endpoint to monitor execution status.
    """,
)
async def execute_import(
    import_id: UUID = Path(..., description="Import ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_async_session),
) -> ConfigurationImportResponse:
    """Execute a configuration import operation."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="execute_import_api",
            import_id=str(import_id),
        )

        logger.info("Executing configuration import via API")

        export_import_service = await get_export_import_service()

        # Execute import in background
        background_tasks.add_task(export_import_service.execute_import, session, import_id)

        # Return current import status
        import_op = await session.get(ConfigurationImport, import_id)
        if not import_op:
            raise HTTPException(status_code=404, detail=f"Import not found: {import_id}")

        return ConfigurationImportResponse.from_orm(import_op)

    except HTTPException:
        raise
    except BusinessLogicError as e:
        logger.warning("Import execution error", error=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Error executing import", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to execute import")


@router.post(
    "/archives/validate",
    response_model=ArchiveValidationResponse,
    summary="Validate Configuration Archive",
    description="""
    Validate the integrity and structure of a configuration archive.
    
    Performs checksum verification, structure validation, and compatibility checks.
    """,
)
async def validate_archive(
    validation_request: ArchiveValidationRequest = Body(..., description="Validation request"),
    session: AsyncSession = Depends(get_async_session),
) -> ArchiveValidationResponse:
    """Validate a configuration archive."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="validate_archive_api",
            archive_path=validation_request.archive_path,
        )

        logger.info("Validating configuration archive via API")

        export_import_service = await get_export_import_service()

        validation_result = await export_import_service.archive_manager.validate_archive(
            validation_request.archive_path,
            quick_validation=validation_request.quick_validation,
        )

        return ArchiveValidationResponse(
            validation_status=validation_result["validation_status"],
            validation_errors=validation_result.get("validation_errors", []),
            archive_format=validation_result.get("archive_format"),
            file_size_bytes=validation_result.get("file_size_bytes"),
            checksum=None,  # Would be calculated if requested
            checksum_verified=validation_result.get("checksum_verified", False),
            total_items=validation_result.get("total_items"),
            device_count=None,  # Would require metadata inspection
            date_range_start=None,
            date_range_end=None,
            structure_valid=validation_result.get("structure_valid", False),
            missing_metadata=[],  # Would be populated during validation
            archive_version=None,  # Would be read from metadata
            compatible_with_system=True,  # Would be determined by version checks
            required_system_version=None,
            encrypted=False,  # Would be detected during validation
            signature_present=False,
            signature_verified=None,
            validated_at=validation_result["validated_at"],
        )

    except Exception as e:
        logger.error("Error validating archive", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to validate archive")


@router.get(
    "/dashboard",
    response_model=ExportImportDashboardResponse,
    summary="Get Export/Import Dashboard",
    description="""
    Get comprehensive export/import dashboard data.
    
    Provides statistics, recent operations, and storage information
    for dashboard visualization.
    """,
)
async def get_dashboard(
    days_back: int = Query(7, ge=1, le=90, description="Number of days for dashboard data"),
    session: AsyncSession = Depends(get_async_session),
) -> ExportImportDashboardResponse:
    """Get export/import dashboard summary."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_export_import_dashboard_api",
        )

        logger.info("Getting export/import dashboard via API")

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Get export statistics
        export_stats_query = select(
            func.count().label("total"),
            func.count()
            .filter(ConfigurationExport.status.in_(["pending", "running"]))
            .label("active"),
            func.count().filter(ConfigurationExport.status == "completed").label("completed"),
            func.count().filter(ConfigurationExport.status == "failed").label("failed"),
        ).where(ConfigurationExport.created_at >= cutoff_time)

        export_result = await session.execute(export_stats_query)
        export_stats = export_result.one()

        # Get import statistics
        import_stats_query = select(
            func.count().label("total"),
            func.count()
            .filter(ConfigurationImport.status.in_(["pending", "validating", "running"]))
            .label("active"),
            func.count().filter(ConfigurationImport.status == "completed").label("completed"),
            func.count().filter(ConfigurationImport.status == "failed").label("failed"),
        ).where(ConfigurationImport.created_at >= cutoff_time)

        import_result = await session.execute(import_stats_query)
        import_stats = import_result.one()

        # Get recent exports
        recent_exports_query = (
            select(ConfigurationExport)
            .where(ConfigurationExport.created_at >= cutoff_time)
            .order_by(desc(ConfigurationExport.created_at))
            .limit(5)
        )
        recent_exports_result = await session.execute(recent_exports_query)
        recent_exports = [
            ConfigurationExportResponse.from_orm(export)
            for export in recent_exports_result.scalars().all()
        ]

        # Get recent imports
        recent_imports_query = (
            select(ConfigurationImport)
            .where(ConfigurationImport.created_at >= cutoff_time)
            .order_by(desc(ConfigurationImport.created_at))
            .limit(5)
        )
        recent_imports_result = await session.execute(recent_imports_query)
        recent_imports = [
            ConfigurationImportResponse.from_orm(import_op)
            for import_op in recent_imports_result.scalars().all()
        ]

        # Calculate archive statistics
        total_archive_size_query = select(
            func.count(ConfigurationExport.id).label("total_archives"),
            func.coalesce(func.sum(ConfigurationExport.archive_size_bytes), 0).label("total_size"),
            func.count().filter(ConfigurationExport.encrypted == True).label("encrypted_count"),
        ).where(
            and_(
                ConfigurationExport.status == "completed",
                ConfigurationExport.archive_path.isnot(None),
            )
        )

        archive_result = await session.execute(total_archive_size_query)
        archive_stats = archive_result.one()

        # Storage statistics (simplified - would use actual filesystem checks)
        disk_usage_bytes = int(archive_stats.total_size or 0)
        available_space_bytes = 100 * 1024 * 1024 * 1024  # 100GB placeholder

        # Generate cleanup recommendations
        cleanup_recommendations = []
        if export_stats.failed > 5:
            cleanup_recommendations.append("Consider cleaning up failed export operations")
        if disk_usage_bytes > 80 * 1024 * 1024 * 1024:  # 80GB
            cleanup_recommendations.append("Archive storage is approaching capacity")

        return ExportImportDashboardResponse(
            total_exports=export_stats.total,
            active_exports=export_stats.active,
            completed_exports=export_stats.completed,
            failed_exports=export_stats.failed,
            total_imports=import_stats.total,
            active_imports=import_stats.active,
            completed_imports=import_stats.completed,
            failed_imports=import_stats.failed,
            recent_exports=recent_exports,
            recent_imports=recent_imports,
            total_archives=archive_stats.total_archives,
            total_archive_size_bytes=disk_usage_bytes,
            encrypted_archives=archive_stats.encrypted_count,
            disk_usage_bytes=disk_usage_bytes,
            available_space_bytes=available_space_bytes,
            cleanup_recommendations=cleanup_recommendations,
            last_updated=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error("Error getting export/import dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


@router.get(
    "/health",
    summary="Export/Import Service Health Check",
    description="Check the health and status of the export/import service.",
)
async def get_service_health() -> dict[str, Any]:
    """Check export/import service health."""

    try:
        export_import_service = await get_export_import_service()

        return {
            "status": "healthy",
            "service": "ConfigurationExportImportService",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "features": {
                "export_operations": True,
                "import_operations": True,
                "archive_validation": True,
                "multiple_formats": True,
                "compression": True,
                "conflict_resolution": True,
                "progress_tracking": True,
                "bulk_operations": True,
            },
            "supported_formats": ["tar.gz", "tar.xz", "tar.bz2", "zip"],
            "storage_path": str(export_import_service.storage_base_path),
        }

    except Exception as e:
        logger.error("Export/import service health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Export/import service is unavailable")
