"""
Configuration Template Service

Business logic for configuration template management with Jinja2 support.
Handles template creation, validation, rendering, and instance management.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

import jinja2
from jinja2 import Environment, StrictUndefined, BaseLoader, TemplateError, UndefinedError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, update, delete
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.events import event_bus
from ..core.exceptions import (
    ValidationError,
    ConfigurationError,
    ResourceNotFoundError,
    BusinessLogicError,
)
from ..models.configuration_template import (
    ConfigurationTemplate,
    TemplateInstance,
    TemplateVariable,
    TemplateType,
    ValidationMode,
)
from ..models.device import Device
from ..schemas.configuration_template import (
    ConfigurationTemplateCreate,
    ConfigurationTemplateUpdate,
    TemplateInstanceCreate,
    TemplateInstanceUpdate,
    TemplateVariableCreate,
    TemplateVariableUpdate,
    TemplateFilter,
    InstanceFilter,
    TemplateValidationRequest,
    TemplateValidationResponse,
    TemplateRenderRequest,
    TemplateRenderResponse,
)
from ..schemas.common import PaginationParams
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ConfigurationTemplateService:
    """
    Service for configuration template management.

    Provides comprehensive template lifecycle management including creation,
    validation, rendering, versioning, and instance deployment tracking.
    """

    def __init__(self):
        self._jinja_env = None
        self._setup_jinja_environment()

    def _setup_jinja_environment(self) -> None:
        """Initialize Jinja2 environment with custom settings."""
        self._jinja_env = Environment(
            loader=BaseLoader(),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # Disable for config files
        )

        # Add custom filters for common template operations
        self._jinja_env.filters["env_default"] = self._env_default_filter
        self._jinja_env.filters["format_list"] = self._format_list_filter
        self._jinja_env.filters["yaml_indent"] = self._yaml_indent_filter

    def _env_default_filter(self, value: Any, env: str, default: Any = None) -> Any:
        """Custom filter for environment-specific defaults."""
        if isinstance(value, dict) and env in value:
            return value[env]
        return default

    def _format_list_filter(self, value: list, separator: str = ",") -> str:
        """Custom filter for formatting lists."""
        if not isinstance(value, list):
            return str(value)
        return separator.join(str(item) for item in value)

    def _yaml_indent_filter(self, value: str, indent: int = 2) -> str:
        """Custom filter for YAML indentation."""
        if not isinstance(value, str):
            return str(value)

        lines = value.split("\n")
        indented_lines = [(" " * indent) + line if line.strip() else line for line in lines]
        return "\n".join(indented_lines)

    # Template Management
    async def create_template(
        self, session: AsyncSession, template_data: ConfigurationTemplateCreate, created_by: str
    ) -> ConfigurationTemplate:
        """Create a new configuration template."""
        try:
            # Validate template content syntax
            validation_result = await self._validate_template_syntax(
                template_data.template_content, template_data.default_variables
            )

            if not validation_result["valid"]:
                raise ValidationError(
                    field="template_content",
                    message=f"Template validation failed: {', '.join(validation_result['errors'])}",
                )

            # Check for name/version uniqueness
            existing_query = select(ConfigurationTemplate).where(
                and_(
                    ConfigurationTemplate.name == template_data.name,
                    ConfigurationTemplate.version == template_data.version,
                )
            )
            existing_result = await session.execute(existing_query)
            if existing_result.scalar_one_or_none():
                raise ValidationError(
                    field="name",
                    message=f"Template with name '{template_data.name}' and version '{template_data.version}' already exists",
                )

            # Create template
            template = ConfigurationTemplate(
                name=template_data.name,
                description=template_data.description,
                template_type=template_data.template_type,
                category=template_data.category,
                version=template_data.version,
                template_content=template_data.template_content,
                default_variables=template_data.default_variables,
                required_variables=template_data.required_variables,
                variable_schema=template_data.variable_schema,
                validation_mode=template_data.validation_mode,
                auto_reload=template_data.auto_reload,
                source_path=template_data.source_path,
                tags=template_data.tags,
                environments=template_data.environments,
                supported_devices=template_data.supported_devices,
                validated=validation_result["valid"],
                validation_errors=validation_result.get("errors"),
                last_validated_at=datetime.now(timezone.utc),
                created_by=created_by,
                updated_by=created_by,
            )

            session.add(template)
            await session.commit()
            await session.refresh(template)

            # Emit event
            await event_bus.emit(
                "template_created",
                {
                    "template_id": str(template.id),
                    "name": template.name,
                    "type": template.template_type,
                    "created_by": created_by,
                },
            )

            logger.info(f"Created configuration template: {template.name} v{template.version}")
            return template

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating template: {e}")
            raise

    async def get_template(
        self, session: AsyncSession, template_id: UUID
    ) -> ConfigurationTemplate | None:
        """Get a configuration template by ID."""
        query = select(ConfigurationTemplate).where(ConfigurationTemplate.id == template_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        session: AsyncSession,
        pagination: PaginationParams,
        filters: TemplateFilter | None = None,
    ) -> tuple[list[ConfigurationTemplate], int]:
        """List configuration templates with filtering and pagination."""
        try:
            query = select(ConfigurationTemplate)

            # Apply filters
            if filters:
                conditions = []

                if filters.template_types:
                    conditions.append(
                        ConfigurationTemplate.template_type.in_(filters.template_types)
                    )

                if filters.categories:
                    conditions.append(ConfigurationTemplate.category.in_(filters.categories))

                if filters.tags:
                    # Check if any of the filter tags are in the template tags
                    for tag in filters.tags:
                        conditions.append(ConfigurationTemplate.tags.op("@>")([tag]))

                if filters.environments:
                    # Check if any of the filter environments are in the template environments
                    for env in filters.environments:
                        conditions.append(ConfigurationTemplate.environments.op("@>")([env]))

                if filters.active_only:
                    conditions.append(ConfigurationTemplate.active == True)

                if filters.validated_only:
                    conditions.append(ConfigurationTemplate.validated == True)

                if filters.name_search:
                    conditions.append(
                        or_(
                            ConfigurationTemplate.name.ilike(f"%{filters.name_search}%"),
                            ConfigurationTemplate.description.ilike(f"%{filters.name_search}%"),
                        )
                    )

                if filters.created_by:
                    conditions.append(ConfigurationTemplate.created_by == filters.created_by)

                if filters.hours_back:
                    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=filters.hours_back)
                    conditions.append(ConfigurationTemplate.created_at >= cutoff_time)

                if conditions:
                    query = query.where(and_(*conditions))

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await session.execute(count_query)
            total_count = count_result.scalar()

            # Apply pagination and ordering
            query = (
                query.order_by(desc(ConfigurationTemplate.created_at))
                .offset(pagination.offset)
                .limit(pagination.limit)
            )

            result = await session.execute(query)
            templates = result.scalars().all()

            return templates, total_count

        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            raise

    async def update_template(
        self,
        session: AsyncSession,
        template_id: UUID,
        update_data: ConfigurationTemplateUpdate,
        updated_by: str,
    ) -> ConfigurationTemplate:
        """Update a configuration template."""
        try:
            template = await self.get_template(session, template_id)
            if not template:
                raise ResourceNotFoundError(
                    f"Template not found: {template_id}", "template", str(template_id)
                )

            # Validate template content if updated
            if update_data.template_content:
                validation_result = await self._validate_template_syntax(
                    update_data.template_content,
                    update_data.default_variables or template.default_variables,
                )

                if not validation_result["valid"]:
                    raise ValidationError(
                        field="template_content",
                        message=f"Template validation failed: {', '.join(validation_result['errors'])}",
                    )

            # Update fields
            update_fields = {}
            for field, value in update_data.model_dump(exclude_unset=True).items():
                if hasattr(template, field):
                    setattr(template, field, value)
                    update_fields[field] = value

            # Update validation status if content changed
            if update_data.template_content:
                template.validated = validation_result["valid"]
                template.validation_errors = validation_result.get("errors")
                template.last_validated_at = datetime.now(timezone.utc)

            template.updated_at = datetime.now(timezone.utc)
            template.updated_by = updated_by

            await session.commit()
            await session.refresh(template)

            # Emit event
            await event_bus.emit(
                "template_updated",
                {
                    "template_id": str(template.id),
                    "name": template.name,
                    "updated_fields": list(update_fields.keys()),
                    "updated_by": updated_by,
                },
            )

            logger.info(f"Updated configuration template: {template.name}")
            return template

        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating template {template_id}: {e}")
            raise

    async def delete_template(self, session: AsyncSession, template_id: UUID) -> bool:
        """Delete a configuration template."""
        try:
            template = await self.get_template(session, template_id)
            if not template:
                return False

            # Check for active instances
            instances_query = select(func.count()).where(
                and_(TemplateInstance.template_id == template_id, TemplateInstance.deployed == True)
            )
            instances_result = await session.execute(instances_query)
            active_instances = instances_result.scalar()

            if active_instances > 0:
                raise BusinessLogicError(
                    message=f"Cannot delete template with {active_instances} active instances",
                    rule_name="template_deletion_check",
                )

            await session.delete(template)
            await session.commit()

            # Emit event
            await event_bus.emit(
                "template_deleted",
                {
                    "template_id": str(template_id),
                    "name": template.name,
                },
            )

            logger.info(f"Deleted configuration template: {template.name}")
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting template {template_id}: {e}")
            raise

    # Template Validation
    async def validate_template(
        self, session: AsyncSession, validation_request: TemplateValidationRequest
    ) -> TemplateValidationResponse:
        """Validate a template with provided variables."""
        try:
            validation_result = await self._validate_template_syntax(
                validation_request.template_content,
                validation_request.variables,
                validation_request.validation_mode,
            )

            return TemplateValidationResponse(
                valid=validation_result["valid"],
                errors=validation_result.get("errors", []),
                warnings=validation_result.get("warnings", []),
                rendered_content=validation_result.get("rendered_content"),
                missing_variables=validation_result.get("missing_variables", []),
                unused_variables=validation_result.get("unused_variables", []),
            )

        except Exception as e:
            logger.error(f"Error validating template: {e}")
            return TemplateValidationResponse(
                valid=False,
                errors=[str(e)],
                warnings=[],
                rendered_content=None,
                missing_variables=[],
                unused_variables=[],
            )

    async def _validate_template_syntax(
        self,
        template_content: str,
        variables: dict[str, Any] | None = None,
        validation_mode: str = "strict",
    ) -> dict[str, Any]:
        """Internal method to validate template syntax and rendering."""
        variables = variables or {}
        errors = []
        warnings = []
        rendered_content = None
        missing_variables = []
        unused_variables = []

        try:
            # Parse template
            template = self._jinja_env.from_string(template_content)

            # Get template variables
            template_vars = set()
            ast = self._jinja_env.parse(template_content)
            template_vars.update(jinja2.meta.find_undeclared_variables(ast))

            # Check for missing required variables in strict mode
            if validation_mode == "strict":
                missing_variables = [var for var in template_vars if var not in variables]
                if missing_variables:
                    errors.append(f"Missing required variables: {', '.join(missing_variables)}")

            # Check for unused variables
            provided_vars = set(variables.keys())
            unused_variables = list(provided_vars - template_vars)
            if unused_variables:
                warnings.append(f"Unused variables: {', '.join(unused_variables)}")

            # Try to render template
            if validation_mode != "syntax_only" and not missing_variables:
                try:
                    rendered_content = template.render(**variables)
                except UndefinedError as e:
                    if validation_mode == "strict":
                        errors.append(f"Template rendering failed: {str(e)}")
                    else:
                        rendered_content = template.render(**variables)
                        warnings.append(f"Undefined variable handled gracefully: {str(e)}")

        except TemplateError as e:
            errors.append(f"Template syntax error: {str(e)}")
        except Exception as e:
            errors.append(f"Template validation error: {str(e)}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "rendered_content": rendered_content,
            "missing_variables": missing_variables,
            "unused_variables": unused_variables,
        }

    # Template Rendering
    async def render_template(
        self, session: AsyncSession, render_request: TemplateRenderRequest
    ) -> TemplateRenderResponse:
        """Render a template with provided variables."""
        try:
            template_content = render_request.template_content
            variables = render_request.variables

            # If template_id is provided, load template
            if render_request.template_id:
                template = await self.get_template(session, render_request.template_id)
                if not template:
                    raise ResourceNotFoundError(
                        f"Template not found: {render_request.template_id}",
                        "template",
                        str(render_request.template_id),
                    )

                template_content = template.template_content

                # Merge with default variables
                merged_variables = template.default_variables.copy()
                merged_variables.update(variables)
                variables = merged_variables

                # Add environment-specific defaults if specified
                if render_request.environment:
                    for var_name, default_val in template.default_variables.items():
                        if (
                            isinstance(default_val, dict)
                            and render_request.environment in default_val
                        ):
                            variables[var_name] = default_val[render_request.environment]

            # Render template
            jinja_template = self._jinja_env.from_string(template_content)
            variables_used = {}

            # Track which variables are actually used during rendering
            class TrackingDict(dict):
                def __init__(self, data):
                    super().__init__(data)
                    self.accessed_keys = set()

                def __getitem__(self, key):
                    self.accessed_keys.add(key)
                    return super().__getitem__(key)

            tracking_vars = TrackingDict(variables)
            rendered_content = jinja_template.render(**tracking_vars)
            variables_used = {k: variables[k] for k in tracking_vars.accessed_keys}

            # Generate content hash
            content_hash = hashlib.sha256(rendered_content.encode()).hexdigest()

            return TemplateRenderResponse(
                rendered_content=rendered_content,
                variables_used=variables_used,
                content_hash=content_hash,
            )

        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            raise ValidationError(field="template_rendering", message=str(e))


# Singleton pattern for service management
_template_service_instance: ConfigurationTemplateService | None = None


async def get_configuration_template_service() -> ConfigurationTemplateService:
    """Get configuration template service instance."""
    global _template_service_instance
    if _template_service_instance is None:
        _template_service_instance = ConfigurationTemplateService()
    return _template_service_instance
