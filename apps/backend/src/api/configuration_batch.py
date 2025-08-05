"""
Configuration Batch Deployment API

REST API endpoints for atomic multi-file configuration deployment management.
Provides endpoints for creating, monitoring, and managing batch deployments.
"""

import logging
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BusinessLogicError,
    ConfigurationError,
)
from ..services.configuration_batch_service import (
    get_configuration_batch_service,
    ConfigurationBatchService,
    ConfigurationBatchRequest,
    ConfigurationFileChange,
)
from ..schemas.configuration_batch import (
    ConfigurationBatchRequestCreate,
    ConfigurationBatchResponse,
    ConfigurationBatchStatusResponse,
    BatchDeploymentListResponse,
    BatchDeploymentCancelRequest,
    BatchDeploymentCancelResponse,
    BatchDeploymentFilter,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/configuration-batch", tags=["Configuration Batch Deployment"])


@router.post(
    "/deploy",
    response_model=ConfigurationBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create batch configuration deployment",
    description="Create and execute an atomic multi-file configuration deployment across multiple devices",
)
async def create_batch_deployment(
    request: ConfigurationBatchRequestCreate,
    session: AsyncSession = Depends(get_async_session),
    batch_service: ConfigurationBatchService = Depends(get_configuration_batch_service),
) -> ConfigurationBatchResponse:
    """
    Create and execute a batch configuration deployment.

    This endpoint allows for atomic deployment of multiple configuration files
    across multiple devices with validation, rollback capabilities, and comprehensive
    tracking of the deployment process.
    """
    try:
        structlog.contextvars.bind_contextvars(
            operation="batch_deployment_create",
            device_count=len(request.device_ids),
            change_count=len(request.changes),
            dry_run=request.dry_run,
        )

        logger.info(
            "Creating batch configuration deployment",
            device_ids=[str(d) for d in request.device_ids],
            changes=[c.change_id for c in request.changes],
        )

        # Convert Pydantic models to service models
        changes = [
            ConfigurationFileChange(
                change_id=change.change_id,
                file_path=change.file_path,
                content=change.content,
                metadata=change.metadata,
            )
            for change in request.changes
        ]

        service_request = ConfigurationBatchRequest(
            device_ids=request.device_ids,
            changes=changes,
            dry_run=request.dry_run,
            auto_rollback=request.auto_rollback,
            metadata=request.metadata,
        )

        # Execute the batch deployment
        result = await batch_service.create_batch_deployment(
            session=session,
            request=service_request,
            user_id="api_user",  # TODO: Get from authentication context
        )

        logger.info(
            "Batch deployment created",
            batch_id=result.batch_id,
            status=result.status,
        )

        return result

    except ValidationError as e:
        logger.error("Validation error in batch deployment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {str(e)}",
        )
    except ResourceNotFoundError as e:
        logger.error("Resource not found in batch deployment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Unexpected error in batch deployment", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during batch deployment",
        )


@router.get(
    "/{batch_id}/status",
    response_model=ConfigurationBatchResponse,
    summary="Get batch deployment status",
    description="Get the current status and detailed information about a batch deployment",
)
async def get_batch_deployment_status(
    batch_id: str,
    batch_service: ConfigurationBatchService = Depends(get_configuration_batch_service),
) -> ConfigurationBatchResponse:
    """
    Get the status of a batch deployment.
    """
    try:
        structlog.contextvars.bind_contextvars(
            operation="batch_deployment_status",
            batch_id=batch_id,
        )

        logger.info("Getting batch deployment status")

        result = await batch_service.get_batch_status(batch_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch deployment not found: {batch_id}",
            )

        return result

    except Exception as e:
        logger.error("Error getting batch deployment status", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting batch deployment status",
        )


@router.post(
    "/{batch_id}/cancel",
    response_model=BatchDeploymentCancelResponse,
    summary="Cancel batch deployment",
    description="Cancel an active batch deployment and optionally trigger rollback",
)
async def cancel_batch_deployment(
    batch_id: str,
    cancel_request: BatchDeploymentCancelRequest,
    session: AsyncSession = Depends(get_async_session),
    batch_service: ConfigurationBatchService = Depends(get_configuration_batch_service),
) -> BatchDeploymentCancelResponse:
    """
    Cancel an active batch deployment.
    """
    try:
        structlog.contextvars.bind_contextvars(
            operation="batch_deployment_cancel",
            batch_id=batch_id,
            force=cancel_request.force,
        )

        logger.info(
            "Cancelling batch deployment",
            reason=cancel_request.reason,
        )

        success = await batch_service.cancel_batch_deployment(
            session=session,
            batch_id=batch_id,
            user_id="api_user",  # TODO: Get from authentication context
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch deployment not found or cannot be cancelled: {batch_id}",
            )

        # Get updated status
        status_result = await batch_service.get_batch_status(batch_id)

        return BatchDeploymentCancelResponse(
            batch_id=batch_id,
            cancelled=True,
            status=status_result.status if status_result else "unknown",
            message="Batch deployment cancelled successfully",
            rollback_initiated=True if status_result and status_result.rollback_plan else False,
        )

    except Exception as e:
        logger.error("Error cancelling batch deployment", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error cancelling batch deployment",
        )


@router.get(
    "/deployments",
    response_model=BatchDeploymentListResponse,
    summary="List batch deployments",
    description="List batch deployments with optional filtering and pagination",
)
async def list_batch_deployments(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    status: list[str] | None = Query(default=None, description="Filter by status"),
    device_ids: list[UUID] | None = Query(default=None, description="Filter by device IDs"),
    dry_run: bool | None = Query(default=None, description="Filter by dry run flag"),
    batch_service: ConfigurationBatchService = Depends(get_configuration_batch_service),
) -> BatchDeploymentListResponse:
    """
    List batch deployments with filtering and pagination.
    """
    try:
        structlog.contextvars.bind_contextvars(
            operation="batch_deployment_list",
            page=page,
            page_size=page_size,
        )

        logger.info("Listing batch deployments")

        # For now, return active transactions from memory
        # In a production system, this would query a database table
        active_deployments = []
        total = 0

        for transaction in batch_service.active_transactions.values():
            # Apply filters
            if status and transaction.status not in status:
                continue
            if device_ids and not any(d in transaction.device_ids for d in device_ids):
                continue
            if dry_run is not None and transaction.dry_run != dry_run:
                continue

            # Convert to response format
            response = await batch_service._generate_batch_response(transaction)
            active_deployments.append(response)
            total += 1

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_deployments = active_deployments[start_idx:end_idx]

        return BatchDeploymentListResponse(
            deployments=paginated_deployments,
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error("Error listing batch deployments", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error listing batch deployments",
        )


@router.get(
    "/{batch_id}",
    response_model=ConfigurationBatchResponse,
    summary="Get batch deployment details",
    description="Get detailed information about a specific batch deployment",
)
async def get_batch_deployment(
    batch_id: str,
    batch_service: ConfigurationBatchService = Depends(get_configuration_batch_service),
) -> ConfigurationBatchResponse:
    """
    Get detailed information about a batch deployment.
    """
    try:
        structlog.contextvars.bind_contextvars(
            operation="batch_deployment_get",
            batch_id=batch_id,
        )

        logger.info("Getting batch deployment details")

        result = await batch_service.get_batch_status(batch_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch deployment not found: {batch_id}",
            )

        return result

    except Exception as e:
        logger.error("Error getting batch deployment details", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting batch deployment details",
        )


@router.post(
    "/validate",
    response_model=dict[str, Any],
    summary="Validate batch deployment",
    description="Validate a batch deployment configuration without executing it",
)
async def validate_batch_deployment(
    request: ConfigurationBatchRequestCreate,
    session: AsyncSession = Depends(get_async_session),
    batch_service: ConfigurationBatchService = Depends(get_configuration_batch_service),
) -> dict[str, Any]:
    """
    Validate a batch deployment configuration without executing it.

    This endpoint performs all validation steps that would occur during deployment
    but does not actually deploy any changes. Useful for pre-deployment validation.
    """
    try:
        structlog.contextvars.bind_contextvars(
            operation="batch_deployment_validate",
            device_count=len(request.device_ids),
            change_count=len(request.changes),
        )

        logger.info("Validating batch deployment configuration")

        # Convert to service models and force dry_run
        changes = [
            ConfigurationFileChange(
                change_id=change.change_id,
                file_path=change.file_path,
                content=change.content,
                metadata=change.metadata,
            )
            for change in request.changes
        ]

        service_request = ConfigurationBatchRequest(
            device_ids=request.device_ids,
            changes=changes,
            dry_run=True,  # Force dry run for validation
            auto_rollback=request.auto_rollback,
            metadata=request.metadata,
        )

        # Execute validation-only deployment
        result = await batch_service.create_batch_deployment(
            session=session,
            request=service_request,
            user_id="api_user",  # TODO: Get from authentication context
        )

        return {
            "valid": result.status in ["completed", "validated"],
            "batch_id": result.batch_id,
            "validation_results": [
                {
                    "device_id": str(vr.device_id),
                    "device_name": vr.device_name,
                    "status": vr.overall_status,
                    "errors": vr.validation_errors,
                    "file_validations": vr.file_validations,
                }
                for vr in result.validation_results
            ],
            "error_message": result.error_message,
        }

    except ValidationError as e:
        logger.error("Validation error in batch deployment validation", error=str(e))
        return {
            "valid": False,
            "error": str(e),
            "validation_results": [],
        }
    except Exception as e:
        logger.error("Error validating batch deployment", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error validating batch deployment",
        )
