"""
Configuration Rollback API Endpoints

REST API endpoints for managing configuration rollbacks, including rollback
planning, execution, and rollback candidate discovery.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..core.exceptions import ValidationError
from ..schemas.common import APIResponse
from ..services.rollback_service import RollbackService
from ..api.common import get_current_user

router = APIRouter()


async def get_rollback_service_dependency() -> RollbackService:
    """Dependency to get rollback service instance."""
    from ..services.rollback_service import get_rollback_service

    return await get_rollback_service()


@router.get("/devices/{device_id}/rollback-candidates", response_model=APIResponse[list[dict]])
async def get_rollback_candidates(
    device_id: UUID = Path(..., description="Device UUID"),
    hours_back: int = Query(24, description="Hours to look back for changes", ge=1, le=168),
    session: AsyncSession = Depends(get_db_session),
    rollback_service: RollbackService = Depends(get_rollback_service_dependency),
    current_user=Depends(get_current_user),
):
    """Get potential rollback target times based on recent changes."""
    try:
        candidates = await rollback_service.get_rollback_candidates(session, device_id, hours_back)
        return APIResponse(
            success=True,
            data=candidates,
            message=f"Found {len(candidates)} rollback candidates",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get rollback candidates")


@router.post("/devices/{device_id}/rollback-plan", response_model=APIResponse[dict])
async def create_rollback_plan(
    device_id: UUID = Path(..., description="Device UUID"),
    target_time: str = Query(..., description="Target time to rollback to (ISO format)"),
    file_paths: str | None = Query(None, description="Comma-separated file paths to include"),
    session: AsyncSession = Depends(get_db_session),
    rollback_service: RollbackService = Depends(get_rollback_service_dependency),
    current_user=Depends(get_current_user),
):
    """Create a rollback plan for configuration changes after a target time."""
    try:
        from datetime import datetime

        target_datetime = datetime.fromisoformat(target_time.replace("Z", "+00:00"))

        file_path_list = None
        if file_paths:
            file_path_list = [path.strip() for path in file_paths.split(",")]

        plan = await rollback_service.create_rollback_plan(
            session, device_id, target_datetime, file_path_list
        )

        return APIResponse(
            success=True,
            data=plan,
            message=f"Rollback plan created with {plan['total_files']} files",
            errors=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid target time format: {e}")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create rollback plan")


@router.post("/rollback-plan/execute", response_model=APIResponse[dict])
async def execute_rollback_plan(
    plan: dict,
    dry_run: bool = Query(False, description="Validate plan without executing"),
    continue_on_error: bool = Query(True, description="Continue execution on step errors"),
    rollback_service: RollbackService = Depends(get_rollback_service_dependency),
    current_user=Depends(get_current_user),
):
    """Execute a rollback plan with optional dry-run mode."""
    try:
        results = await rollback_service.execute_rollback_plan(
            plan, dry_run=dry_run, continue_on_error=continue_on_error
        )

        message = (
            f"Rollback plan {'validated' if dry_run else 'executed'}: "
            f"{results['successful_steps']}/{results['total_steps']} successful"
        )

        return APIResponse(
            success=results["overall_success"],
            data=results,
            message=message,
            errors=results.get("errors", []) if not results["overall_success"] else None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to execute rollback plan")
