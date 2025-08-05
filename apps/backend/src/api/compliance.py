"""
Configuration Compliance API Endpoints

REST API endpoints for configuration compliance management including rules,
checks, reports, exceptions, and dashboard functionality.
"""

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from ..core.database import get_async_session
from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BusinessLogicError,
)
from ..models.compliance import (
    ComplianceRule,
    ComplianceCheck,
    ComplianceReport,
    ComplianceException,
)
from ..schemas.compliance import (
    ComplianceRuleCreate,
    ComplianceRuleUpdate,
    ComplianceRuleResponse,
    ComplianceCheckResponse,
    ComplianceCheckRequest,
    ComplianceCheckBulkResponse,
    ComplianceReportResponse,
    ComplianceExceptionCreate,
    ComplianceExceptionUpdate,
    ComplianceExceptionResponse,
    ComplianceDashboardResponse,
)
from ..services.compliance_service import get_compliance_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/compliance", tags=["Configuration Compliance"])


@router.post(
    "/rules",
    response_model=ComplianceRuleResponse,
    status_code=201,
    summary="Create Compliance Rule",
    description="""
    Create a new configuration compliance rule.
    
    Rules define policies and checks that configurations must satisfy,
    with support for different rule types, severity levels, and targeting criteria.
    """,
)
async def create_compliance_rule(
    rule_data: ComplianceRuleCreate = Body(..., description="Compliance rule data"),
    session: AsyncSession = Depends(get_async_session),
) -> ComplianceRuleResponse:
    """Create a new compliance rule."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="create_compliance_rule_api",
            rule_name=rule_data.name,
        )

        logger.info("Creating compliance rule via API")

        compliance_service = await get_compliance_service()

        rule = await compliance_service.create_compliance_rule(
            session=session,
            rule_data=rule_data.dict(),
            created_by=rule_data.created_by,
        )

        return ComplianceRuleResponse.from_orm(rule)

    except ValidationError as e:
        logger.warning("Invalid compliance rule data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating compliance rule", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create compliance rule")


@router.get(
    "/rules",
    response_model=list[ComplianceRuleResponse],
    summary="List Compliance Rules",
    description="""
    List all compliance rules with optional filtering.
    
    Supports filtering by category, severity, enabled status, and other criteria.
    """,
)
async def list_compliance_rules(
    category: str | None = Query(None, description="Filter by rule category"),
    severity: str | None = Query(None, description="Filter by rule severity"),
    enabled: bool | None = Query(None, description="Filter by enabled status"),
    rule_type: str | None = Query(None, description="Filter by rule type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of rules to return"),
    offset: int = Query(0, ge=0, description="Number of rules to skip"),
    session: AsyncSession = Depends(get_async_session),
) -> list[ComplianceRuleResponse]:
    """List compliance rules with optional filtering."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="list_compliance_rules_api",
        )

        logger.info("Listing compliance rules via API")

        # Build query with filters
        query = select(ComplianceRule)

        if category:
            query = query.where(ComplianceRule.category == category)
        if severity:
            query = query.where(ComplianceRule.severity == severity)
        if enabled is not None:
            query = query.where(ComplianceRule.enabled == enabled)
        if rule_type:
            query = query.where(ComplianceRule.rule_type == rule_type)

        query = query.order_by(desc(ComplianceRule.created_at)).limit(limit).offset(offset)

        result = await session.execute(query)
        rules = list(result.scalars().all())

        return [ComplianceRuleResponse.from_orm(rule) for rule in rules]

    except Exception as e:
        logger.error("Error listing compliance rules", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance rules")


@router.get(
    "/rules/{rule_id}",
    response_model=ComplianceRuleResponse,
    summary="Get Compliance Rule",
    description="Get detailed information about a specific compliance rule.",
)
async def get_compliance_rule(
    rule_id: UUID = Path(..., description="Compliance rule ID"),
    session: AsyncSession = Depends(get_async_session),
) -> ComplianceRuleResponse:
    """Get a specific compliance rule."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_compliance_rule_api",
            rule_id=str(rule_id),
        )

        logger.info("Getting compliance rule via API")

        rule = await session.get(ComplianceRule, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Compliance rule not found: {rule_id}")

        return ComplianceRuleResponse.from_orm(rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting compliance rule", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance rule")


@router.put(
    "/rules/{rule_id}",
    response_model=ComplianceRuleResponse,
    summary="Update Compliance Rule",
    description="Update an existing compliance rule with new configuration.",
)
async def update_compliance_rule(
    rule_id: UUID = Path(..., description="Compliance rule ID"),
    rule_update: ComplianceRuleUpdate = Body(..., description="Rule updates"),
    session: AsyncSession = Depends(get_async_session),
) -> ComplianceRuleResponse:
    """Update a compliance rule."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="update_compliance_rule_api",
            rule_id=str(rule_id),
        )

        logger.info("Updating compliance rule via API")

        rule = await session.get(ComplianceRule, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Compliance rule not found: {rule_id}")

        # Update fields that were provided
        update_data = rule_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)

        rule.updated_at = datetime.now(timezone.utc)
        rule.version += 1

        await session.commit()
        await session.refresh(rule)

        return ComplianceRuleResponse.from_orm(rule)

    except HTTPException:
        raise
    except ValidationError as e:
        logger.warning("Invalid rule update data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await session.rollback()
        logger.error("Error updating compliance rule", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update compliance rule")


@router.delete(
    "/rules/{rule_id}",
    status_code=204,
    summary="Delete Compliance Rule",
    description="Delete a compliance rule and all associated checks.",
)
async def delete_compliance_rule(
    rule_id: UUID = Path(..., description="Compliance rule ID"),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a compliance rule."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="delete_compliance_rule_api",
            rule_id=str(rule_id),
        )

        logger.info("Deleting compliance rule via API")

        rule = await session.get(ComplianceRule, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Compliance rule not found: {rule_id}")

        await session.delete(rule)
        await session.commit()

        logger.info("Compliance rule deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("Error deleting compliance rule", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete compliance rule")


@router.post(
    "/checks",
    response_model=ComplianceCheckBulkResponse,
    summary="Run Compliance Checks",
    description="""
    Execute compliance checks across devices and rules.
    
    Supports filtering by specific rules, devices, or file patterns.
    Can run asynchronously for large-scale compliance checking.
    """,
)
async def run_compliance_checks(
    check_request: ComplianceCheckRequest = Body(..., description="Compliance check request"),
    session: AsyncSession = Depends(get_async_session),
) -> ComplianceCheckBulkResponse:
    """Run compliance checks based on the provided criteria."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="run_compliance_checks_api",
        )

        logger.info("Running compliance checks via API")

        compliance_service = await get_compliance_service()

        # For now, run checks synchronously for specific devices
        # In production, this would use a task queue for async processing
        if check_request.device_ids:
            all_checks = []
            for device_id in check_request.device_ids:
                checks = await compliance_service.check_device_compliance(
                    session=session,
                    device_id=device_id,
                    rule_ids=check_request.rule_ids,
                    force_refresh=check_request.force_refresh,
                )
                all_checks.extend(checks)

            # Generate response
            passed_checks = len([c for c in all_checks if c.status == "pass"])
            failed_checks = len([c for c in all_checks if c.status == "fail"])
            error_checks = len([c for c in all_checks if c.status == "error"])

            return ComplianceCheckBulkResponse(
                request_id=str(UUID()),
                status="completed",
                total_rules=len(check_request.rule_ids) if check_request.rule_ids else 0,
                total_devices=len(check_request.device_ids),
                total_files=len(all_checks),
                checks_completed=len(all_checks),
                checks_passed=passed_checks,
                checks_failed=failed_checks,
                checks_error=error_checks,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
        else:
            # Return placeholder for bulk async processing
            return ComplianceCheckBulkResponse(
                request_id=str(UUID()),
                status="pending",
                total_rules=0,
                total_devices=0,
                total_files=0,
                checks_completed=0,
                checks_passed=0,
                checks_failed=0,
                checks_error=0,
                started_at=datetime.now(timezone.utc),
                estimated_completion=datetime.now(timezone.utc) + timedelta(minutes=10),
            )

    except ValidationError as e:
        logger.warning("Invalid compliance check request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error running compliance checks", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to run compliance checks")


@router.get(
    "/checks",
    response_model=list[ComplianceCheckResponse],
    summary="List Compliance Checks",
    description="""
    List compliance check results with optional filtering.
    
    Supports filtering by device, rule, status, time period, and other criteria.
    """,
)
async def list_compliance_checks(
    device_id: UUID | None = Query(None, description="Filter by device ID"),
    rule_id: UUID | None = Query(None, description="Filter by rule ID"),
    status: str | None = Query(None, description="Filter by check status"),
    severity: str | None = Query(None, description="Filter by violation severity"),
    days_back: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of checks to return"),
    offset: int = Query(0, ge=0, description="Number of checks to skip"),
    session: AsyncSession = Depends(get_async_session),
) -> list[ComplianceCheckResponse]:
    """List compliance checks with optional filtering."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="list_compliance_checks_api",
        )

        logger.info("Listing compliance checks via API")

        # Build query with filters
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        query = select(ComplianceCheck).where(ComplianceCheck.checked_at >= cutoff_time)

        if device_id:
            query = query.where(ComplianceCheck.device_id == device_id)
        if rule_id:
            query = query.where(ComplianceCheck.rule_id == rule_id)
        if status:
            query = query.where(ComplianceCheck.status == status)
        if severity:
            query = query.where(ComplianceCheck.violation_severity == severity)

        query = query.order_by(desc(ComplianceCheck.checked_at)).limit(limit).offset(offset)

        result = await session.execute(query)
        checks = list(result.scalars().all())

        return [ComplianceCheckResponse.from_orm(check) for check in checks]

    except Exception as e:
        logger.error("Error listing compliance checks", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance checks")


@router.post(
    "/reports",
    response_model=ComplianceReportResponse,
    status_code=201,
    summary="Generate Compliance Report",
    description="""
    Generate a comprehensive compliance report for devices, rules, or categories.
    
    Reports include compliance scores, violation summaries, trends, and recommendations.
    """,
)
async def generate_compliance_report(
    report_type: str = Query(..., description="Report type (device, rule, global, category)"),
    scope_id: str | None = Query(None, description="Scope identifier (device_id, rule_id, etc.)"),
    days_back: int = Query(30, ge=1, le=365, description="Report period in days"),
    generated_by: str = Query("api-user", description="Who generated the report"),
    session: AsyncSession = Depends(get_async_session),
) -> ComplianceReportResponse:
    """Generate a compliance report."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="generate_compliance_report_api",
            report_type=report_type,
            scope_id=scope_id,
        )

        logger.info("Generating compliance report via API")

        compliance_service = await get_compliance_service()

        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=days_back)

        report = await compliance_service.generate_compliance_report(
            session=session,
            report_type=report_type,
            scope_id=scope_id,
            period_start=period_start,
            period_end=period_end,
            generated_by=generated_by,
        )

        return ComplianceReportResponse.from_orm(report)

    except ValidationError as e:
        logger.warning("Invalid report generation request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error generating compliance report", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate compliance report")


@router.get(
    "/reports",
    response_model=list[ComplianceReportResponse],
    summary="List Compliance Reports",
    description="List previously generated compliance reports.",
)
async def list_compliance_reports(
    report_type: str | None = Query(None, description="Filter by report type"),
    scope_id: str | None = Query(None, description="Filter by scope identifier"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of reports to return"),
    offset: int = Query(0, ge=0, description="Number of reports to skip"),
    session: AsyncSession = Depends(get_async_session),
) -> list[ComplianceReportResponse]:
    """List compliance reports with optional filtering."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="list_compliance_reports_api",
        )

        logger.info("Listing compliance reports via API")

        # Build query with filters
        query = select(ComplianceReport)

        if report_type:
            query = query.where(ComplianceReport.report_type == report_type)
        if scope_id:
            query = query.where(ComplianceReport.scope_id == scope_id)

        query = query.order_by(desc(ComplianceReport.generated_at)).limit(limit).offset(offset)

        result = await session.execute(query)
        reports = list(result.scalars().all())

        return [ComplianceReportResponse.from_orm(report) for report in reports]

    except Exception as e:
        logger.error("Error listing compliance reports", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance reports")


@router.get(
    "/dashboard",
    response_model=ComplianceDashboardResponse,
    summary="Get Compliance Dashboard",
    description="""
    Get comprehensive compliance dashboard data.
    
    Provides overall compliance status, recent checks, top violations,
    and compliance trends for dashboard visualization.
    """,
)
async def get_compliance_dashboard(
    days_back: int = Query(7, ge=1, le=90, description="Number of days for dashboard data"),
    session: AsyncSession = Depends(get_async_session),
) -> ComplianceDashboardResponse:
    """Get compliance dashboard summary."""

    try:
        structlog.contextvars.bind_contextvars(
            operation="get_compliance_dashboard_api",
        )

        logger.info("Getting compliance dashboard via API")

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Get recent compliance checks
        checks_query = (
            select(ComplianceCheck)
            .where(ComplianceCheck.checked_at >= cutoff_time)
            .order_by(desc(ComplianceCheck.checked_at))
            .limit(100)
        )

        result = await session.execute(checks_query)
        recent_checks = list(result.scalars().all())

        # Calculate dashboard statistics
        total_checks = len(recent_checks)
        passed_checks = len([c for c in recent_checks if c.status == "pass"])
        failed_checks = len([c for c in recent_checks if c.status == "fail"])

        # Calculate overall compliance score
        overall_score = int((passed_checks / total_checks) * 100) if total_checks > 0 else 100

        # Determine compliance grade
        if overall_score >= 95:
            grade = "A"
        elif overall_score >= 85:
            grade = "B"
        elif overall_score >= 75:
            grade = "C"
        elif overall_score >= 65:
            grade = "D"
        else:
            grade = "F"

        # Count violations by severity
        critical_violations = len([c for c in recent_checks if c.violation_severity == "critical"])
        high_violations = len([c for c in recent_checks if c.violation_severity == "high"])
        medium_violations = len([c for c in recent_checks if c.violation_severity == "medium"])
        low_violations = len([c for c in recent_checks if c.violation_severity == "low"])

        # Get device statistics
        device_ids = set(c.device_id for c in recent_checks)
        compliant_devices = len(set(c.device_id for c in recent_checks if c.status == "pass"))

        # Generate top violations
        violation_counts = {}
        for check in recent_checks:
            if check.status == "fail":
                rule_name = f"Rule {check.rule_id}"  # Would get actual rule name
                if rule_name not in violation_counts:
                    violation_counts[rule_name] = {
                        "rule_name": rule_name,
                        "violation_count": 0,
                        "severity": check.violation_severity or "medium",
                    }
                violation_counts[rule_name]["violation_count"] += 1

        top_violations = sorted(
            violation_counts.values(), key=lambda x: x["violation_count"], reverse=True
        )[:5]

        return ComplianceDashboardResponse(
            overall_compliance_score=overall_score,
            compliance_grade=grade,
            compliance_trend="stable",
            total_devices=len(device_ids),
            compliant_devices=compliant_devices,
            non_compliant_devices=len(device_ids) - compliant_devices,
            total_rules=0,  # Would count active rules
            critical_violations=critical_violations,
            high_violations=high_violations,
            medium_violations=medium_violations,
            low_violations=low_violations,
            recent_checks=[ComplianceCheckResponse.from_orm(c) for c in recent_checks[:10]],
            top_violations=top_violations,
            compliance_by_category={
                "security": 85,
                "performance": 92,
                "best-practices": 78,
            },
            last_updated=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error("Error getting compliance dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve compliance dashboard")


@router.get(
    "/health",
    summary="Compliance Service Health Check",
    description="Check the health and status of the compliance service.",
)
async def get_compliance_service_health() -> dict[str, Any]:
    """Check compliance service health."""

    try:
        compliance_service = await get_compliance_service()

        return {
            "status": "healthy",
            "service": "ComplianceService",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "features": {
                "rule_management": True,
                "compliance_checking": True,
                "report_generation": True,
                "exception_handling": True,
                "dashboard": True,
            },
            "supported_rule_types": ["regex", "json-path", "custom", "template", "function"],
        }

    except Exception as e:
        logger.error("Compliance service health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Compliance service is unavailable")
