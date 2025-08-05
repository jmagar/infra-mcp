"""
Approval Workflow Service

Core business logic for configuration change approval workflow system.
Handles change request lifecycle, approval processing, and workflow orchestration.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.events import event_bus
from ..core.exceptions import (
    ValidationError,
    ConfigurationError,
    ServiceUnavailableError,
    ResourceNotFoundError,
)
from ..models.approval_workflow import (
    ChangeRequest,
    ChangeRequestApproval,
    ApprovalPolicy,
    WorkflowExecution,
    ChangeRequestStatus,
    ApprovalStatus,
)
from ..models.device import Device
from ..schemas.approval_workflow import (
    ChangeRequestCreate,
    ChangeRequestUpdate,
    ChangeRequestApprovalCreate,
    ChangeRequestFilter,
    ApprovalWorkflowMetrics,
)
from ..schemas.common import PaginationParams
from ..services.configuration_service import get_configuration_service
from ..services.impact_analysis import get_impact_analysis_engine
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ApprovalWorkflowService:
    """
    Service for managing configuration change approval workflows.

    Features:
    - Change request creation and lifecycle management
    - Approval policy evaluation and enforcement
    - Automated impact analysis integration
    - Workflow step execution and tracking
    - Notification and escalation handling
    """

    def __init__(
        self,
        default_approval_timeout_hours: int | None = None,
        max_pending_requests_per_user: int | None = None,
    ):
        self.default_approval_timeout_hours = default_approval_timeout_hours or getattr(
            settings, "APPROVAL_DEFAULT_TIMEOUT_HOURS", 24
        )
        self.max_pending_requests_per_user = max_pending_requests_per_user or getattr(
            settings, "APPROVAL_MAX_PENDING_PER_USER", 10
        )

        self._configuration_service = None
        self._impact_analysis_service = None

        logger.info(
            f"ApprovalWorkflowService initialized - timeout: {self.default_approval_timeout_hours}h, "
            f"max_pending: {self.max_pending_requests_per_user}"
        )

    async def create_change_request(
        self, session: AsyncSession, request_data: ChangeRequestCreate, requested_by: str
    ) -> ChangeRequest:
        """
        Create a new change request with automatic impact analysis.

        Args:
            session: Database session
            request_data: Change request data
            requested_by: User creating the request

        Returns:
            Created change request
        """
        try:
            # Validate device exists
            device_result = await session.execute(
                select(Device).where(Device.id == request_data.device_id)
            )
            device = device_result.scalar_one_or_none()
            if not device:
                raise ValidationError(field="device_id", message="Device not found")

            # Check user's pending requests limit
            pending_count = await self._count_user_pending_requests(session, requested_by)
            if pending_count >= self.max_pending_requests_per_user:
                raise ValidationError(
                    field="requested_by",
                    message=f"User has too many pending requests ({pending_count}/{self.max_pending_requests_per_user})",
                )

            # Create change request
            change_request = ChangeRequest(
                title=request_data.title,
                description=request_data.description,
                requested_by=requested_by,
                device_id=request_data.device_id,
                config_type=request_data.config_type,
                file_path=request_data.file_path,
                proposed_content=request_data.proposed_content,
                change_type=request_data.change_type,
                change_reason=request_data.change_reason,
                emergency_change=request_data.emergency_change,
                status=ChangeRequestStatus.PENDING.value,
            )

            session.add(change_request)
            await session.flush()  # Get ID for further processing

            # Log workflow step
            await self._log_workflow_step(
                session,
                change_request.id,
                "request_created",
                "creation",
                {"requested_by": requested_by, "emergency": request_data.emergency_change},
                requested_by,
            )

            # Run impact analysis
            await self._run_impact_analysis(session, change_request)

            # Evaluate approval policies
            await self._evaluate_approval_policies(session, change_request)

            # Create approval records if needed
            if change_request.requires_approval:
                await self._create_approval_records(session, change_request)

            await session.commit()

            # Emit event
            await event_bus.emit(
                "approval_workflow.change_request.created",
                {
                    "change_request_id": str(change_request.id),
                    "device_id": str(request_data.device_id),
                    "requested_by": requested_by,
                    "emergency": request_data.emergency_change,
                    "requires_approval": change_request.requires_approval,
                    "risk_level": change_request.risk_level,
                },
            )

            logger.info(
                f"Created change request {change_request.id} for device {device.hostname} "
                f"by {requested_by} - risk: {change_request.risk_level}"
            )

            return change_request

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating change request: {e}")
            raise

    async def get_change_request(
        self, session: AsyncSession, request_id: UUID
    ) -> ChangeRequest | None:
        """Get a change request by ID with all related data."""
        try:
            result = await session.execute(
                select(ChangeRequest)
                .options(
                    selectinload(ChangeRequest.approvals),
                    selectinload(ChangeRequest.device),
                )
                .where(ChangeRequest.id == request_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error getting change request {request_id}: {e}")
            return None

    async def list_change_requests(
        self,
        session: AsyncSession,
        pagination: PaginationParams,
        filters: ChangeRequestFilter | None = None,
    ) -> tuple[list[ChangeRequest], int]:
        """List change requests with filtering and pagination."""
        try:
            query = select(ChangeRequest).options(
                selectinload(ChangeRequest.approvals),
                selectinload(ChangeRequest.device),
            )

            # Apply filters
            if filters:
                if filters.device_ids:
                    query = query.where(ChangeRequest.device_id.in_(filters.device_ids))

                if filters.statuses:
                    query = query.where(ChangeRequest.status.in_(filters.statuses))

                if filters.risk_levels:
                    query = query.where(ChangeRequest.risk_level.in_(filters.risk_levels))

                if filters.config_types:
                    query = query.where(ChangeRequest.config_type.in_(filters.config_types))

                if filters.requested_by:
                    query = query.where(ChangeRequest.requested_by == filters.requested_by)

                if filters.emergency_only:
                    query = query.where(ChangeRequest.emergency_change == True)

                if filters.pending_approval:
                    query = query.where(
                        and_(
                            ChangeRequest.status == ChangeRequestStatus.PENDING.value,
                            ChangeRequest.requires_approval == True,
                        )
                    )

                if filters.hours_back:
                    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=filters.hours_back)
                    query = query.where(ChangeRequest.created_at >= cutoff_time)

            # Get total count
            count_result = await session.execute(select(func.count()).select_from(query.subquery()))
            total_count = count_result.scalar()

            # Apply pagination and ordering
            query = (
                query.order_by(desc(ChangeRequest.created_at))
                .offset(pagination.offset)
                .limit(pagination.limit)
            )

            result = await session.execute(query)
            requests = result.scalars().all()

            return list(requests), total_count

        except Exception as e:
            logger.error(f"Error listing change requests: {e}")
            return [], 0

    async def approve_change_request(
        self,
        session: AsyncSession,
        request_id: UUID,
        approver_id: str,
        approver_name: str,
        approval_data: ChangeRequestApprovalCreate,
    ) -> ChangeRequestApproval:
        """Process an approval decision for a change request."""
        try:
            # Get change request
            change_request = await self.get_change_request(session, request_id)
            if not change_request:
                raise ResourceNotFoundError(
                    f"Change request not found: {request_id}", "change_request", str(request_id)
                )

            if change_request.status != ChangeRequestStatus.PENDING.value:
                raise ValidationError(
                    field="status", message="Change request is not pending approval"
                )

            # Find or create approval record
            approval = None
            for existing_approval in change_request.approvals:
                if existing_approval.approver_id == approver_id:
                    approval = existing_approval
                    break

            if not approval:
                # Create new approval record
                approval = ChangeRequestApproval(
                    change_request_id=request_id,
                    approver_id=approver_id,
                    approver_name=approver_name,
                    status=approval_data.status,
                    decision_at=datetime.now(timezone.utc),
                    comments=approval_data.comments,
                )
                session.add(approval)
            else:
                # Update existing approval
                approval.status = approval_data.status
                approval.decision_at = datetime.now(timezone.utc)
                approval.comments = approval_data.comments

            # Log workflow step
            await self._log_workflow_step(
                session,
                request_id,
                f"approval_{approval_data.status}",
                "approval",
                {
                    "approver_id": approver_id,
                    "approver_name": approver_name,
                    "comments": approval_data.comments,
                },
                approver_id,
            )

            # Check if all required approvals are received
            await self._check_approval_completion(session, change_request)

            await session.commit()

            # Emit event
            await event_bus.emit(
                f"approval_workflow.change_request.{approval_data.status}",
                {
                    "change_request_id": str(request_id),
                    "approver_id": approver_id,
                    "approver_name": approver_name,
                    "approval_status": approval_data.status,
                    "comments": approval_data.comments,
                },
            )

            logger.info(f"Change request {request_id} {approval_data.status} by {approver_name}")

            return approval

        except Exception as e:
            await session.rollback()
            logger.error(f"Error processing approval for {request_id}: {e}")
            raise

    async def execute_approved_change(
        self, session: AsyncSession, request_id: UUID, executed_by: str
    ) -> dict[str, Any]:
        """Execute an approved change request."""
        try:
            change_request = await self.get_change_request(session, request_id)
            if not change_request:
                raise ResourceNotFoundError(
                    f"Change request not found: {request_id}", "change_request", str(request_id)
                )

            if change_request.status != ChangeRequestStatus.APPROVED.value:
                raise ValidationError(
                    field="status", message="Change request is not approved for execution"
                )

            # Log execution start
            await self._log_workflow_step(
                session,
                request_id,
                "execution_started",
                "execution",
                {"executed_by": executed_by},
                executed_by,
            )

            if not self._configuration_service:
                self._configuration_service = await get_configuration_service()

            # Execute the configuration change
            execution_result = await self._execute_configuration_change(
                session, change_request, executed_by
            )

            # Update change request status
            if execution_result["success"]:
                change_request.status = ChangeRequestStatus.APPLIED.value
                change_request.applied_at = datetime.now(timezone.utc)
                change_request.applied_by = executed_by
                change_request.execution_results = execution_result
                change_request.snapshot_id = execution_result.get("snapshot_id")

                await self._log_workflow_step(
                    session,
                    request_id,
                    "execution_completed",
                    "execution",
                    execution_result,
                    executed_by,
                )
            else:
                change_request.status = ChangeRequestStatus.FAILED.value
                change_request.failure_reason = execution_result.get("error", "Unknown error")
                change_request.retry_count += 1
                change_request.execution_results = execution_result

                await self._log_workflow_step(
                    session,
                    request_id,
                    "execution_failed",
                    "execution",
                    execution_result,
                    executed_by,
                )

            await session.commit()

            # Emit event
            await event_bus.emit(
                f"approval_workflow.change_request.{'executed' if execution_result['success'] else 'failed'}",
                {
                    "change_request_id": str(request_id),
                    "executed_by": executed_by,
                    "success": execution_result["success"],
                    "execution_results": execution_result,
                },
            )

            logger.info(
                f"Change request {request_id} execution {'completed' if execution_result['success'] else 'failed'}"
            )

            return execution_result

        except Exception as e:
            await session.rollback()
            logger.error(f"Error executing change request {request_id}: {e}")
            raise

    async def get_workflow_metrics(
        self, session: AsyncSession, hours_back: int = 168
    ) -> ApprovalWorkflowMetrics:
        """Get approval workflow performance metrics."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

            # Basic counts
            result = await session.execute(
                select(
                    func.count().label("total"),
                    func.sum(func.case((ChangeRequest.status == "pending", 1), else_=0)).label(
                        "pending"
                    ),
                    func.sum(func.case((ChangeRequest.status == "approved", 1), else_=0)).label(
                        "approved"
                    ),
                    func.sum(func.case((ChangeRequest.status == "rejected", 1), else_=0)).label(
                        "rejected"
                    ),
                    func.sum(func.case((ChangeRequest.status == "applied", 1), else_=0)).label(
                        "applied"
                    ),
                    func.sum(func.case((ChangeRequest.status == "failed", 1), else_=0)).label(
                        "failed"
                    ),
                    func.sum(func.case((ChangeRequest.emergency_change == True, 1), else_=0)).label(
                        "emergency"
                    ),
                ).where(ChangeRequest.created_at >= cutoff_time)
            )
            counts = result.first()

            # Calculate approval rate
            total_decided = (counts.approved or 0) + (counts.rejected or 0)
            approval_rate = (counts.approved or 0) / total_decided * 100 if total_decided > 0 else 0

            # Get status distribution
            status_result = await session.execute(
                select(ChangeRequest.status, func.count())
                .where(ChangeRequest.created_at >= cutoff_time)
                .group_by(ChangeRequest.status)
            )
            requests_by_status = dict(status_result.all())

            # Get risk level distribution
            risk_result = await session.execute(
                select(ChangeRequest.risk_level, func.count())
                .where(
                    and_(
                        ChangeRequest.created_at >= cutoff_time,
                        ChangeRequest.risk_level.isnot(None),
                    )
                )
                .group_by(ChangeRequest.risk_level)
            )
            requests_by_risk_level = dict(risk_result.all())

            # Get config type distribution
            config_result = await session.execute(
                select(ChangeRequest.config_type, func.count())
                .where(ChangeRequest.created_at >= cutoff_time)
                .group_by(ChangeRequest.config_type)
            )
            requests_by_config_type = dict(config_result.all())

            return ApprovalWorkflowMetrics(
                total_requests=counts.total or 0,
                pending_requests=counts.pending or 0,
                approved_requests=counts.approved or 0,
                rejected_requests=counts.rejected or 0,
                applied_requests=counts.applied or 0,
                failed_requests=counts.failed or 0,
                emergency_requests=counts.emergency or 0,
                average_approval_time_hours=None,  # TODO: Calculate from workflow executions
                approval_rate=approval_rate,
                requests_by_status=requests_by_status,
                requests_by_risk_level=requests_by_risk_level,
                requests_by_config_type=requests_by_config_type,
                top_requesters=[],  # TODO: Implement top requesters query
                top_approvers=[],  # TODO: Implement top approvers query
            )

        except Exception as e:
            logger.error(f"Error getting workflow metrics: {e}")
            raise

    async def _count_user_pending_requests(self, session: AsyncSession, user_id: str) -> int:
        """Count pending requests for a user."""
        result = await session.execute(
            select(func.count()).where(
                and_(
                    ChangeRequest.requested_by == user_id,
                    ChangeRequest.status == ChangeRequestStatus.PENDING.value,
                )
            )
        )
        return result.scalar() or 0

    async def _run_impact_analysis(
        self, session: AsyncSession, change_request: ChangeRequest
    ) -> None:
        """Run impact analysis on a change request."""
        try:
            if not self._impact_analysis_service:
                self._impact_analysis_service = await get_impact_analysis_engine()

            analysis_result = await self._impact_analysis_service.analyze_configuration_change(
                device_id=change_request.device_id,
                config_type=change_request.config_type,
                file_path=change_request.file_path,
                proposed_content=change_request.proposed_content,
                change_type=change_request.change_type,
            )

            change_request.risk_level = analysis_result.get("risk_level", "MEDIUM")
            change_request.impact_analysis = analysis_result
            change_request.affected_services = analysis_result.get("affected_services", [])

            await self._log_workflow_step(
                session,
                change_request.id,
                "impact_analysis_completed",
                "validation",
                analysis_result,
                "system",
            )

        except Exception as e:
            logger.error(f"Error running impact analysis: {e}")
            # Set default values on failure
            change_request.risk_level = "HIGH"  # Conservative default
            change_request.impact_analysis = {"error": str(e)}

    async def _evaluate_approval_policies(
        self, session: AsyncSession, change_request: ChangeRequest
    ) -> None:
        """Evaluate approval policies to determine approval requirements."""
        try:
            # Get active policies
            result = await session.execute(
                select(ApprovalPolicy).where(ApprovalPolicy.active == True)
            )
            policies = result.scalars().all()

            # Find matching policies
            matching_policy = None
            for policy in policies:
                if self._policy_matches_request(policy, change_request):
                    matching_policy = policy
                    break

            if matching_policy:
                change_request.requires_approval = True
                change_request.approvals_required = matching_policy.approvals_required

                # Auto-approve emergency changes if policy allows
                if change_request.emergency_change and matching_policy.auto_approve_emergency:
                    change_request.status = ChangeRequestStatus.APPROVED.value
                    change_request.requires_approval = False

                    await self._log_workflow_step(
                        session,
                        change_request.id,
                        "auto_approved_emergency",
                        "approval",
                        {"policy_id": str(matching_policy.id)},
                        "system",
                    )
            else:
                # No matching policy - use defaults
                change_request.requires_approval = change_request.risk_level in ["HIGH", "CRITICAL"]
                change_request.approvals_required = 1

        except Exception as e:
            logger.error(f"Error evaluating approval policies: {e}")
            # Conservative defaults on error
            change_request.requires_approval = True
            change_request.approvals_required = 1

    def _policy_matches_request(
        self, policy: ApprovalPolicy, change_request: ChangeRequest
    ) -> bool:
        """Check if an approval policy matches a change request."""
        conditions = policy.conditions

        # Check risk level
        if "risk_level" in conditions:
            if change_request.risk_level not in conditions["risk_level"]:
                return False

        # Check config type
        if "config_type" in conditions:
            if change_request.config_type not in conditions["config_type"]:
                return False

        # Check change type
        if "change_type" in conditions:
            if change_request.change_type not in conditions["change_type"]:
                return False

        # Check emergency flag
        if "emergency_change" in conditions:
            if change_request.emergency_change != conditions["emergency_change"]:
                return False

        return True

    async def _create_approval_records(
        self, session: AsyncSession, change_request: ChangeRequest
    ) -> None:
        """Create approval records for a change request."""
        # For now, create a placeholder approval record
        # In a full implementation, this would determine actual approvers based on policies
        approval = ChangeRequestApproval(
            change_request_id=change_request.id,
            approver_id="admin",  # TODO: Get from policy or configuration
            approver_name="System Administrator",
            approver_role="admin",
            status=ApprovalStatus.PENDING.value,
        )
        session.add(approval)

        await self._log_workflow_step(
            session,
            change_request.id,
            "approval_required",
            "approval",
            {"approvals_required": change_request.approvals_required},
            "system",
        )

    async def _check_approval_completion(
        self, session: AsyncSession, change_request: ChangeRequest
    ) -> None:
        """Check if all required approvals are received."""
        approved_count = sum(
            1
            for approval in change_request.approvals
            if approval.status == ApprovalStatus.APPROVED.value
        )
        rejected_count = sum(
            1
            for approval in change_request.approvals
            if approval.status == ApprovalStatus.REJECTED.value
        )

        if rejected_count > 0:
            change_request.status = ChangeRequestStatus.REJECTED.value
            await self._log_workflow_step(
                session,
                change_request.id,
                "request_rejected",
                "approval",
                {"rejected_count": rejected_count},
                "system",
            )
        elif approved_count >= change_request.approvals_required:
            change_request.status = ChangeRequestStatus.APPROVED.value
            await self._log_workflow_step(
                session,
                change_request.id,
                "request_approved",
                "approval",
                {"approved_count": approved_count},
                "system",
            )

    async def _execute_configuration_change(
        self, session: AsyncSession, change_request: ChangeRequest, executed_by: str
    ) -> dict[str, Any]:
        """Execute the actual configuration change."""
        try:
            # Create configuration snapshot
            from ..schemas.configuration import ConfigurationSnapshotCreate

            snapshot_data = ConfigurationSnapshotCreate(
                device_id=change_request.device_id,
                config_type=change_request.config_type,
                file_path=change_request.file_path,
                raw_content=change_request.proposed_content,
                change_type=change_request.change_type,
                trigger_type="approval_workflow",
                trigger_metadata={
                    "change_request_id": str(change_request.id),
                    "executed_by": executed_by,
                },
            )

            snapshot = await self._configuration_service.create_snapshot(snapshot_data)

            return {
                "success": True,
                "snapshot_id": str(snapshot.id),
                "message": "Configuration change applied successfully",
                "executed_by": executed_by,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error executing configuration change: {e}")
            return {
                "success": False,
                "error": str(e),
                "executed_by": executed_by,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _log_workflow_step(
        self,
        session: AsyncSession,
        change_request_id: UUID,
        step_name: str,
        step_type: str,
        execution_data: dict[str, Any] | None,
        performer: str | None,
    ) -> None:
        """Log a workflow execution step."""
        workflow_execution = WorkflowExecution(
            change_request_id=change_request_id,
            step_name=step_name,
            step_type=step_type,
            status="completed",
            execution_data=execution_data,
            performer=performer,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(workflow_execution)


# Global singleton instance
_approval_workflow_service: ApprovalWorkflowService | None = None


async def get_approval_workflow_service() -> ApprovalWorkflowService:
    """Get the global approval workflow service instance."""
    global _approval_workflow_service

    if _approval_workflow_service is None:
        _approval_workflow_service = ApprovalWorkflowService()

    return _approval_workflow_service
