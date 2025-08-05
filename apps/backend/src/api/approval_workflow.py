"""
Approval Workflow API Endpoints

REST API endpoints for configuration change approval workflow system,
including change requests, approvals, policies, and workflow management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..core.exceptions import ValidationError, ResourceNotFoundError
from ..schemas.common import APIResponse, PaginationParams
from ..schemas.approval_workflow import (
    ChangeRequestCreate,
    ChangeRequestUpdate,
    ChangeRequestResponse,
    ChangeRequestList,
    ChangeRequestApprovalCreate,
    ChangeRequestApprovalResponse,
    ChangeRequestFilter,
    ApprovalPolicyCreate,
    ApprovalPolicyUpdate,
    ApprovalPolicyResponse,
    ApprovalPolicyList,
    ApprovalWorkflowMetrics,
    BulkApprovalRequest,
    BulkApprovalResponse,
    WorkflowExecutionResponse,
    WorkflowExecutionList,
)
from ..services.approval_workflow_service import get_approval_workflow_service
from ..api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_approval_workflow_service_dependency():
    """Dependency to get approval workflow service instance."""
    return await get_approval_workflow_service()


# Change Request Management
@router.post("/change-requests", response_model=APIResponse[ChangeRequestResponse], status_code=201)
async def create_change_request(
    request_data: ChangeRequestCreate,
    session: AsyncSession = Depends(get_db_session),
    approval_service=Depends(get_approval_workflow_service_dependency),
    current_user=Depends(get_current_user),
):
    """Create a new configuration change request."""
    try:
        # For now, use a simple user identifier - in production, extract from JWT
        requested_by = getattr(current_user, "username", "unknown_user")

        change_request = await approval_service.create_change_request(
            session, request_data, requested_by
        )

        return APIResponse(
            success=True,
            data=ChangeRequestResponse.from_orm(change_request),
            message="Change request created successfully",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating change request: {e}")
        raise HTTPException(status_code=500, detail="Failed to create change request")


@router.get("/change-requests", response_model=APIResponse[ChangeRequestList])
async def list_change_requests(
    pagination: PaginationParams = Depends(),
    device_ids: str | None = Query(None, description="Comma-separated device UUIDs"),
    statuses: str | None = Query(None, description="Comma-separated status values"),
    risk_levels: str | None = Query(None, description="Comma-separated risk levels"),
    config_types: str | None = Query(None, description="Comma-separated config types"),
    requested_by: str | None = Query(None, description="Filter by requester"),
    emergency_only: bool | None = Query(None, description="Show only emergency changes"),
    pending_approval: bool | None = Query(None, description="Show only changes pending approval"),
    hours_back: int | None = Query(
        None, ge=1, le=8760, description="Show changes from last N hours"
    ),
    session: AsyncSession = Depends(get_db_session),
    approval_service=Depends(get_approval_workflow_service_dependency),
    current_user=Depends(get_current_user),
):
    """List configuration change requests with filtering and pagination."""
    try:
        # Build filter
        filters = ChangeRequestFilter(
            device_ids=[UUID(id.strip()) for id in device_ids.split(",")] if device_ids else None,
            statuses=statuses.split(",") if statuses else None,
            risk_levels=risk_levels.split(",") if risk_levels else None,
            config_types=config_types.split(",") if config_types else None,
            requested_by=requested_by,
            emergency_only=emergency_only,
            pending_approval=pending_approval,
            hours_back=hours_back,
        )

        requests, total_count = await approval_service.list_change_requests(
            session, pagination, filters
        )

        request_list = ChangeRequestList(
            items=[ChangeRequestResponse.from_orm(req) for req in requests],
            total=total_count,
            page=pagination.page,
            limit=pagination.limit,
            pages=(total_count + pagination.limit - 1) // pagination.limit,
        )

        return APIResponse(
            success=True,
            data=request_list,
            message=f"Retrieved {len(requests)} change requests",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing change requests: {e}")
        raise HTTPException(status_code=500, detail="Failed to list change requests")


@router.get("/change-requests/{request_id}", response_model=APIResponse[ChangeRequestResponse])
async def get_change_request(
    request_id: UUID = Path(..., description="Change request UUID"),
    session: AsyncSession = Depends(get_db_session),
    approval_service=Depends(get_approval_workflow_service_dependency),
    current_user=Depends(get_current_user),
):
    """Get a specific change request."""
    try:
        change_request = await approval_service.get_change_request(session, request_id)
        if not change_request:
            raise HTTPException(status_code=404, detail="Change request not found")

        return APIResponse(
            success=True,
            data=ChangeRequestResponse.from_orm(change_request),
            message="Change request retrieved successfully",
            errors=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting change request {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get change request")


@router.put("/change-requests/{request_id}", response_model=APIResponse[ChangeRequestResponse])
async def update_change_request(
    request_id: UUID = Path(..., description="Change request UUID"),
    update_data: ChangeRequestUpdate = Body(...),
    session: AsyncSession = Depends(get_db_session),
    approval_service=Depends(get_approval_workflow_service_dependency),
    current_user=Depends(get_current_user),
):
    """Update a change request (only allowed if still pending)."""
    try:
        change_request = await approval_service.get_change_request(session, request_id)
        if not change_request:
            raise HTTPException(status_code=404, detail="Change request not found")

        if change_request.status != "pending":
            raise HTTPException(
                status_code=400, detail="Cannot update change request that is not pending"
            )

        # Update fields
        if update_data.title is not None:
            change_request.title = update_data.title
        if update_data.description is not None:
            change_request.description = update_data.description
        if update_data.proposed_content is not None:
            change_request.proposed_content = update_data.proposed_content
        if update_data.change_reason is not None:
            change_request.change_reason = update_data.change_reason
        if update_data.emergency_change is not None:
            change_request.emergency_change = update_data.emergency_change

        from datetime import datetime, timezone

        change_request.updated_at = datetime.now(timezone.utc)

        await session.commit()

        return APIResponse(
            success=True,
            data=ChangeRequestResponse.from_orm(change_request),
            message="Change request updated successfully",
            errors=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating change request {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update change request")


# Approval Management
@router.post(
    "/change-requests/{request_id}/approve",
    response_model=APIResponse[ChangeRequestApprovalResponse],
)
async def approve_change_request(
    request_id: UUID = Path(..., description="Change request UUID"),
    approval_data: ChangeRequestApprovalCreate = Body(...),
    session: AsyncSession = Depends(get_db_session),
    approval_service=Depends(get_approval_workflow_service_dependency),
    current_user=Depends(get_current_user),
):
    """Approve or reject a change request."""
    try:
        # For now, use a simple user identifier - in production, extract from JWT
        approver_id = getattr(current_user, "id", "unknown_user")
        approver_name = getattr(current_user, "username", "Unknown User")

        if approval_data.status not in ["approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

        approval = await approval_service.approve_change_request(
            session, request_id, approver_id, approver_name, approval_data
        )

        return APIResponse(
            success=True,
            data=ChangeRequestApprovalResponse.from_orm(approval),
            message=f"Change request {approval_data.status} successfully",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing approval for {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process approval")


@router.post("/change-requests/{request_id}/execute", response_model=APIResponse[dict])
async def execute_change_request(
    request_id: UUID = Path(..., description="Change request UUID"),
    session: AsyncSession = Depends(get_db_session),
    approval_service=Depends(get_approval_workflow_service_dependency),
    current_user=Depends(get_current_user),
):
    """Execute an approved change request."""
    try:
        executed_by = getattr(current_user, "username", "unknown_user")

        execution_result = await approval_service.execute_approved_change(
            session, request_id, executed_by
        )

        return APIResponse(
            success=execution_result["success"],
            data=execution_result,
            message="Change request execution completed"
            if execution_result["success"]
            else "Change request execution failed",
            errors=[execution_result.get("error")] if not execution_result["success"] else None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing change request {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute change request")


# Bulk Operations
@router.post("/change-requests/bulk-approval", response_model=APIResponse[BulkApprovalResponse])
async def bulk_approve_change_requests(
    bulk_request: BulkApprovalRequest,
    session: AsyncSession = Depends(get_db_session),
    approval_service=Depends(get_approval_workflow_service_dependency),
    current_user=Depends(get_current_user),
):
    """Perform bulk approval operations on multiple change requests."""
    try:
        if bulk_request.action not in ["approve", "reject", "cancel"]:
            raise HTTPException(
                status_code=400, detail="Action must be 'approve', 'reject', or 'cancel'"
            )

        approver_id = getattr(current_user, "id", "unknown_user")
        approver_name = getattr(current_user, "username", "Unknown User")

        results = []
        successful_operations = 0
        failed_operations = 0

        for request_id in bulk_request.change_request_ids:
            try:
                if bulk_request.action in ["approve", "reject"]:
                    approval_data = ChangeRequestApprovalCreate(
                        status=bulk_request.action + "d",  # approved/rejected
                        comments=bulk_request.comments,
                    )
                    await approval_service.approve_change_request(
                        session, request_id, approver_id, approver_name, approval_data
                    )
                    results.append(
                        {
                            "request_id": str(request_id),
                            "success": True,
                            "action": bulk_request.action,
                        }
                    )
                    successful_operations += 1
                else:  # cancel
                    # TODO: Implement cancel functionality
                    results.append(
                        {
                            "request_id": str(request_id),
                            "success": False,
                            "error": "Cancel operation not yet implemented",
                        }
                    )
                    failed_operations += 1

            except Exception as e:
                results.append(
                    {
                        "request_id": str(request_id),
                        "success": False,
                        "error": str(e),
                    }
                )
                failed_operations += 1

        bulk_response = BulkApprovalResponse(
            total_requests=len(bulk_request.change_request_ids),
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            results=results,
        )

        return APIResponse(
            success=successful_operations > 0,
            data=bulk_response,
            message=f"Bulk operation completed: {successful_operations} successful, {failed_operations} failed",
            errors=None,
        )
    except Exception as e:
        logger.error(f"Error in bulk approval operation: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform bulk approval operation")


# Metrics and Reporting
@router.get("/metrics", response_model=APIResponse[ApprovalWorkflowMetrics])
async def get_approval_workflow_metrics(
    hours_back: int = Query(168, ge=1, le=8760, description="Hours to look back for metrics"),
    session: AsyncSession = Depends(get_db_session),
    approval_service=Depends(get_approval_workflow_service_dependency),
    current_user=Depends(get_current_user),
):
    """Get approval workflow performance metrics."""
    try:
        metrics = await approval_service.get_workflow_metrics(session, hours_back)

        return APIResponse(
            success=True,
            data=metrics,
            message="Approval workflow metrics retrieved successfully",
            errors=None,
        )
    except Exception as e:
        logger.error(f"Error getting approval workflow metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get approval workflow metrics")


# Workflow Execution History
@router.get(
    "/change-requests/{request_id}/workflow", response_model=APIResponse[WorkflowExecutionList]
)
async def get_workflow_execution_history(
    request_id: UUID = Path(..., description="Change request UUID"),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Get workflow execution history for a change request."""
    try:
        from sqlalchemy import select, desc, func
        from ..models.approval_workflow import WorkflowExecution

        query = (
            select(WorkflowExecution)
            .where(WorkflowExecution.change_request_id == request_id)
            .order_by(desc(WorkflowExecution.started_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )

        result = await session.execute(query)
        executions = result.scalars().all()

        # Get total count
        count_query = select(func.count()).where(WorkflowExecution.change_request_id == request_id)
        count_result = await session.execute(count_query)
        total_count = count_result.scalar()

        execution_list = WorkflowExecutionList(
            items=[WorkflowExecutionResponse.from_orm(exec) for exec in executions],
            total=total_count,
            page=pagination.page,
            limit=pagination.limit,
            pages=(total_count + pagination.limit - 1) // pagination.limit,
        )

        return APIResponse(
            success=True,
            data=execution_list,
            message=f"Retrieved {len(executions)} workflow executions",
            errors=None,
        )
    except Exception as e:
        logger.error(f"Error getting workflow execution history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get workflow execution history")
