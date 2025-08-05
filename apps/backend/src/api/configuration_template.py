"""
Configuration Template API Endpoints

REST API endpoints for configuration template management with Jinja2 support.
Provides template CRUD operations, validation, rendering, and instance management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..core.exceptions import ValidationError, ResourceNotFoundError, BusinessLogicError
from ..schemas.common import APIResponse, PaginationParams
from ..schemas.configuration_template import (
    ConfigurationTemplateCreate,
    ConfigurationTemplateUpdate,
    ConfigurationTemplateResponse,
    ConfigurationTemplateList,
    TemplateInstanceCreate,
    TemplateInstanceUpdate,
    TemplateInstanceResponse,
    TemplateInstanceList,
    TemplateVariableCreate,
    TemplateVariableUpdate,
    TemplateVariableResponse,
    TemplateValidationRequest,
    TemplateValidationResponse,
    TemplateRenderRequest,
    TemplateRenderResponse,
    TemplateFilter,
    InstanceFilter,
    BulkTemplateOperation,
    BulkTemplateOperationResponse,
)
from ..services.configuration_template_service import get_configuration_template_service
from ..api.common import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_template_service_dependency():
    """Dependency to get configuration template service instance."""
    return await get_configuration_template_service()


# Configuration Template Management
@router.post(
    "/templates", response_model=APIResponse[ConfigurationTemplateResponse], status_code=201
)
async def create_template(
    template_data: ConfigurationTemplateCreate,
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """Create a new configuration template."""
    try:
        created_by = getattr(current_user, "username", "unknown_user")

        template = await template_service.create_template(session, template_data, created_by)

        return APIResponse(
            success=True,
            data=ConfigurationTemplateResponse.from_orm(template),
            message="Configuration template created successfully",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create configuration template")


@router.get("/templates", response_model=APIResponse[ConfigurationTemplateList])
async def list_templates(
    pagination: PaginationParams = Depends(),
    template_types: str | None = Query(None, description="Comma-separated template types"),
    categories: str | None = Query(None, description="Comma-separated categories"),
    tags: str | None = Query(None, description="Comma-separated tags"),
    environments: str | None = Query(None, description="Comma-separated environments"),
    active_only: bool | None = Query(None, description="Show only active templates"),
    validated_only: bool | None = Query(None, description="Show only validated templates"),
    name_search: str | None = Query(None, description="Search in template names and descriptions"),
    created_by: str | None = Query(None, description="Filter by creator"),
    hours_back: int | None = Query(
        None, ge=1, le=8760, description="Show templates from last N hours"
    ),
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """List configuration templates with filtering and pagination."""
    try:
        # Build filter
        filters = TemplateFilter(
            template_types=template_types.split(",") if template_types else None,
            categories=categories.split(",") if categories else None,
            tags=tags.split(",") if tags else None,
            environments=environments.split(",") if environments else None,
            active_only=active_only,
            validated_only=validated_only,
            name_search=name_search,
            created_by=created_by,
            hours_back=hours_back,
        )

        templates, total_count = await template_service.list_templates(session, pagination, filters)

        template_list = ConfigurationTemplateList(
            items=[ConfigurationTemplateResponse.from_orm(template) for template in templates],
            total=total_count,
            page=pagination.page,
            limit=pagination.limit,
            pages=(total_count + pagination.limit - 1) // pagination.limit,
        )

        return APIResponse(
            success=True,
            data=template_list,
            message=f"Retrieved {len(templates)} configuration templates",
            errors=None,
        )
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to list configuration templates")


@router.get("/templates/{template_id}", response_model=APIResponse[ConfigurationTemplateResponse])
async def get_template(
    template_id: UUID = Path(..., description="Template UUID"),
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """Get a specific configuration template."""
    try:
        template = await template_service.get_template(session, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Configuration template not found")

        return APIResponse(
            success=True,
            data=ConfigurationTemplateResponse.from_orm(template),
            message="Configuration template retrieved successfully",
            errors=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get configuration template")


@router.put("/templates/{template_id}", response_model=APIResponse[ConfigurationTemplateResponse])
async def update_template(
    template_id: UUID = Path(..., description="Template UUID"),
    update_data: ConfigurationTemplateUpdate = Body(...),
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """Update a configuration template."""
    try:
        updated_by = getattr(current_user, "username", "unknown_user")

        template = await template_service.update_template(
            session, template_id, update_data, updated_by
        )

        return APIResponse(
            success=True,
            data=ConfigurationTemplateResponse.from_orm(template),
            message="Configuration template updated successfully",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration template")


@router.delete("/templates/{template_id}", response_model=APIResponse[dict])
async def delete_template(
    template_id: UUID = Path(..., description="Template UUID"),
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """Delete a configuration template."""
    try:
        deleted = await template_service.delete_template(session, template_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Configuration template not found")

        return APIResponse(
            success=True,
            data={"deleted": True, "template_id": str(template_id)},
            message="Configuration template deleted successfully",
            errors=None,
        )
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete configuration template")


# Template Validation
@router.post("/templates/validate", response_model=APIResponse[TemplateValidationResponse])
async def validate_template(
    validation_request: TemplateValidationRequest,
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """Validate a template with provided variables."""
    try:
        validation_response = await template_service.validate_template(session, validation_request)

        return APIResponse(
            success=validation_response.valid,
            data=validation_response,
            message="Template validation completed",
            errors=validation_response.errors if not validation_response.valid else None,
        )
    except Exception as e:
        logger.error(f"Error validating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate template")


# Template Rendering
@router.post("/templates/render", response_model=APIResponse[TemplateRenderResponse])
async def render_template(
    render_request: TemplateRenderRequest,
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """Render a template with provided variables."""
    try:
        render_response = await template_service.render_template(session, render_request)

        return APIResponse(
            success=True,
            data=render_response,
            message="Template rendered successfully",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        raise HTTPException(status_code=500, detail="Failed to render template")


@router.post("/templates/{template_id}/render", response_model=APIResponse[TemplateRenderResponse])
async def render_template_by_id(
    template_id: UUID = Path(..., description="Template UUID"),
    variables: dict = Body({}, description="Template variables"),
    environment: str | None = Body(None, description="Target environment"),
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """Render a specific template with provided variables."""
    try:
        render_request = TemplateRenderRequest(
            template_id=template_id,
            variables=variables,
            environment=environment,
        )

        render_response = await template_service.render_template(session, render_request)

        return APIResponse(
            success=True,
            data=render_response,
            message="Template rendered successfully",
            errors=None,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error rendering template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to render template")


# Template Types and Categories
@router.get("/templates/types", response_model=APIResponse[dict])
async def get_template_types(
    current_user=Depends(get_current_user),
):
    """Get available template types and their descriptions."""
    template_types = {
        "docker_compose": {
            "name": "Docker Compose",
            "description": "Docker Compose service definitions",
            "extensions": [".yml", ".yaml"],
        },
        "proxy_config": {
            "name": "Proxy Configuration",
            "description": "Reverse proxy configuration files",
            "extensions": [".conf"],
        },
        "systemd_service": {
            "name": "Systemd Service",
            "description": "Systemd service unit files",
            "extensions": [".service"],
        },
        "nginx_config": {
            "name": "Nginx Configuration",
            "description": "Nginx server configuration files",
            "extensions": [".conf"],
        },
        "environment_file": {
            "name": "Environment File",
            "description": "Environment variable files",
            "extensions": [".env"],
        },
        "shell_script": {
            "name": "Shell Script",
            "description": "Shell script templates",
            "extensions": [".sh", ".bash"],
        },
        "config_file": {
            "name": "Configuration File",
            "description": "Generic configuration files",
            "extensions": [".conf", ".cfg", ".ini"],
        },
        "yaml_config": {
            "name": "YAML Configuration",
            "description": "YAML configuration files",
            "extensions": [".yml", ".yaml"],
        },
        "json_config": {
            "name": "JSON Configuration",
            "description": "JSON configuration files",
            "extensions": [".json"],
        },
    }

    return APIResponse(
        success=True,
        data={"template_types": template_types},
        message="Template types retrieved successfully",
        errors=None,
    )


# Template Statistics
@router.get("/templates/stats", response_model=APIResponse[dict])
async def get_template_statistics(
    session: AsyncSession = Depends(get_db_session),
    template_service=Depends(get_template_service_dependency),
    current_user=Depends(get_current_user),
):
    """Get template usage and performance statistics."""
    try:
        from sqlalchemy import select, func
        from ..models.configuration_template import ConfigurationTemplate, TemplateInstance

        # Get basic template counts
        template_count_query = select(func.count()).select_from(ConfigurationTemplate)
        template_count_result = await session.execute(template_count_query)
        total_templates = template_count_result.scalar()

        active_template_query = select(func.count()).where(ConfigurationTemplate.active == True)
        active_result = await session.execute(active_template_query)
        active_templates = active_result.scalar()

        validated_query = select(func.count()).where(ConfigurationTemplate.validated == True)
        validated_result = await session.execute(validated_query)
        validated_templates = validated_result.scalar()

        # Get instance counts
        instance_count_query = select(func.count()).select_from(TemplateInstance)
        instance_count_result = await session.execute(instance_count_query)
        total_instances = instance_count_result.scalar()

        deployed_instance_query = select(func.count()).where(TemplateInstance.deployed == True)
        deployed_result = await session.execute(deployed_instance_query)
        deployed_instances = deployed_result.scalar()

        # Get template type distribution
        type_distribution_query = select(
            ConfigurationTemplate.template_type, func.count().label("count")
        ).group_by(ConfigurationTemplate.template_type)
        type_result = await session.execute(type_distribution_query)
        type_distribution = {row.template_type: row.count for row in type_result}

        stats = {
            "templates": {
                "total": total_templates,
                "active": active_templates,
                "validated": validated_templates,
                "validation_rate": (validated_templates / total_templates * 100)
                if total_templates > 0
                else 0,
            },
            "instances": {
                "total": total_instances,
                "deployed": deployed_instances,
                "deployment_rate": (deployed_instances / total_instances * 100)
                if total_instances > 0
                else 0,
            },
            "type_distribution": type_distribution,
        }

        return APIResponse(
            success=True,
            data=stats,
            message="Template statistics retrieved successfully",
            errors=None,
        )
    except Exception as e:
        logger.error(f"Error getting template statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get template statistics")
