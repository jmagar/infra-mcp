"""
Configuration Template Schemas

Pydantic models for configuration template API requests and responses.
Handles validation, serialization, and documentation for template management.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, validator

from .common import PaginatedResponse


# Enums
class TemplateTypeSchema(BaseModel):
    """Template type enumeration schema."""

    DOCKER_COMPOSE: str = "docker_compose"
    PROXY_CONFIG: str = "proxy_config"
    SYSTEMD_SERVICE: str = "systemd_service"
    NGINX_CONFIG: str = "nginx_config"
    ENVIRONMENT_FILE: str = "environment_file"
    SHELL_SCRIPT: str = "shell_script"
    CONFIG_FILE: str = "config_file"
    YAML_CONFIG: str = "yaml_config"
    JSON_CONFIG: str = "json_config"


class ValidationModeSchema(BaseModel):
    """Validation mode enumeration schema."""

    STRICT: str = "strict"
    PERMISSIVE: str = "permissive"
    SYNTAX_ONLY: str = "syntax_only"


# Template Variable Schemas
class TemplateVariableCreate(BaseModel):
    """Schema for creating a template variable."""

    name: str = Field(..., min_length=1, max_length=255, description="Variable name")
    description: str | None = Field(None, description="Variable description")
    variable_type: str = Field(..., description="Variable type (string, number, boolean, json)")
    required: bool = Field(False, description="Whether variable is required")
    validation_regex: str | None = Field(
        None, max_length=500, description="Validation regex pattern"
    )
    allowed_values: list[Any] | None = Field(None, description="List of allowed values")
    min_length: int | None = Field(None, ge=0, description="Minimum length for strings")
    max_length: int | None = Field(None, ge=0, description="Maximum length for strings")
    default_value: Any | None = Field(None, description="Default value")
    environment_defaults: dict[str, Any] = Field(
        default_factory=dict, description="Per-environment defaults"
    )
    sensitive: bool = Field(False, description="Mark as sensitive data")
    documentation: str | None = Field(None, description="Extended documentation")
    examples: list[Any] | None = Field(None, description="Example values")

    @validator("variable_type")
    def validate_variable_type(cls, v):
        valid_types = ["string", "number", "boolean", "json", "array", "object"]
        if v not in valid_types:
            raise ValueError(f"Variable type must be one of: {', '.join(valid_types)}")
        return v


class TemplateVariableUpdate(BaseModel):
    """Schema for updating a template variable."""

    description: str | None = None
    variable_type: str | None = None
    required: bool | None = None
    validation_regex: str | None = None
    allowed_values: list[Any] | None = None
    min_length: int | None = None
    max_length: int | None = None
    default_value: Any | None = None
    environment_defaults: dict[str, Any] | None = None
    sensitive: bool | None = None
    documentation: str | None = None
    examples: list[Any] | None = None


class TemplateVariableResponse(BaseModel):
    """Schema for template variable response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    name: str
    description: str | None
    variable_type: str
    required: bool
    validation_regex: str | None
    allowed_values: list[Any] | None
    min_length: int | None
    max_length: int | None
    default_value: Any | None
    environment_defaults: dict[str, Any]
    sensitive: bool
    documentation: str | None
    examples: list[Any] | None
    created_at: datetime
    created_by: str
    updated_at: datetime


# Configuration Template Schemas
class ConfigurationTemplateCreate(BaseModel):
    """Schema for creating a configuration template."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: str | None = Field(None, description="Template description")
    template_type: str = Field(..., description="Template type")
    category: str | None = Field(None, max_length=100, description="Template category")
    version: str = Field("1.0.0", max_length=50, description="Template version")
    template_content: str = Field(..., min_length=1, description="Jinja2 template content")
    default_variables: dict[str, Any] = Field(
        default_factory=dict, description="Default variable values"
    )
    required_variables: list[str] = Field(
        default_factory=list, description="Required variable names"
    )
    variable_schema: dict[str, Any] | None = Field(None, description="JSON schema for variables")
    validation_mode: str = Field("strict", description="Template validation mode")
    auto_reload: bool = Field(False, description="Auto-reload from source")
    source_path: str | None = Field(None, max_length=500, description="Source file path")
    tags: list[str] = Field(default_factory=list, description="Template tags")
    environments: list[str] = Field(default_factory=list, description="Target environments")
    supported_devices: list[UUID] | None = Field(None, description="Device type restrictions")

    @validator("template_type")
    def validate_template_type(cls, v):
        valid_types = [
            "docker_compose",
            "proxy_config",
            "systemd_service",
            "nginx_config",
            "environment_file",
            "shell_script",
            "config_file",
            "yaml_config",
            "json_config",
        ]
        if v not in valid_types:
            raise ValueError(f"Template type must be one of: {', '.join(valid_types)}")
        return v

    @validator("validation_mode")
    def validate_validation_mode(cls, v):
        valid_modes = ["strict", "permissive", "syntax_only"]
        if v not in valid_modes:
            raise ValueError(f"Validation mode must be one of: {', '.join(valid_modes)}")
        return v


class ConfigurationTemplateUpdate(BaseModel):
    """Schema for updating a configuration template."""

    name: str | None = None
    description: str | None = None
    template_type: str | None = None
    category: str | None = None
    version: str | None = None
    template_content: str | None = None
    default_variables: dict[str, Any] | None = None
    required_variables: list[str] | None = None
    variable_schema: dict[str, Any] | None = None
    validation_mode: str | None = None
    auto_reload: bool | None = None
    source_path: str | None = None
    tags: list[str] | None = None
    environments: list[str] | None = None
    supported_devices: list[UUID] | None = None
    active: bool | None = None


class ConfigurationTemplateResponse(BaseModel):
    """Schema for configuration template response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    template_type: str
    category: str | None
    version: str
    template_content: str
    default_variables: dict[str, Any]
    required_variables: list[str]
    variable_schema: dict[str, Any] | None
    validation_mode: str
    auto_reload: bool
    source_path: str | None
    tags: list[str]
    environments: list[str]
    supported_devices: list[UUID] | None
    active: bool
    validated: bool
    validation_errors: dict[str, Any] | None
    last_validated_at: datetime | None
    usage_count: dict[str, Any]
    last_used_at: datetime | None
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class ConfigurationTemplateList(PaginatedResponse):
    """Schema for paginated template list response."""

    items: list[ConfigurationTemplateResponse]


# Template Instance Schemas
class TemplateInstanceCreate(BaseModel):
    """Schema for creating a template instance."""

    template_id: UUID = Field(..., description="Template UUID")
    device_id: UUID = Field(..., description="Target device UUID")
    name: str = Field(..., min_length=1, max_length=255, description="Instance name")
    description: str | None = Field(None, description="Instance description")
    environment: str = Field(..., max_length=100, description="Deployment environment")
    variables: dict[str, Any] = Field(default_factory=dict, description="Variable values")
    target_path: str = Field(..., max_length=500, description="Target file path")
    file_mode: str | None = Field(None, max_length=10, description="File permissions")
    file_owner: str | None = Field(None, max_length=100, description="File owner")
    file_group: str | None = Field(None, max_length=100, description="File group")


class TemplateInstanceUpdate(BaseModel):
    """Schema for updating a template instance."""

    name: str | None = None
    description: str | None = None
    environment: str | None = None
    variables: dict[str, Any] | None = None
    target_path: str | None = None
    file_mode: str | None = None
    file_owner: str | None = None
    file_group: str | None = None


class TemplateInstanceResponse(BaseModel):
    """Schema for template instance response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    device_id: UUID
    name: str
    description: str | None
    environment: str
    variables: dict[str, Any]
    rendered_content: str | None
    content_hash: str | None
    target_path: str
    file_mode: str | None
    file_owner: str | None
    file_group: str | None
    deployed: bool
    deployed_at: datetime | None
    deployed_by: str | None
    validation_status: str | None
    validation_errors: dict[str, Any] | None
    drift_detected: bool
    last_drift_check: datetime | None
    drift_details: dict[str, Any] | None
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class TemplateInstanceList(PaginatedResponse):
    """Schema for paginated template instance list response."""

    items: list[TemplateInstanceResponse]


# Template Validation Schemas
class TemplateValidationRequest(BaseModel):
    """Schema for template validation request."""

    template_content: str = Field(..., description="Template content to validate")
    variables: dict[str, Any] = Field(default_factory=dict, description="Variables for validation")
    validation_mode: str = Field("strict", description="Validation mode")

    @validator("validation_mode")
    def validate_validation_mode(cls, v):
        valid_modes = ["strict", "permissive", "syntax_only"]
        if v not in valid_modes:
            raise ValueError(f"Validation mode must be one of: {', '.join(valid_modes)}")
        return v


class TemplateValidationResponse(BaseModel):
    """Schema for template validation response."""

    valid: bool = Field(..., description="Whether template is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    rendered_content: str | None = Field(None, description="Rendered template content")
    missing_variables: list[str] = Field(
        default_factory=list, description="Missing required variables"
    )
    unused_variables: list[str] = Field(
        default_factory=list, description="Unused provided variables"
    )


# Template Rendering Schemas
class TemplateRenderRequest(BaseModel):
    """Schema for template rendering request."""

    template_id: UUID | None = Field(None, description="Template UUID (if using existing template)")
    template_content: str | None = Field(
        None, description="Template content (if not using existing)"
    )
    variables: dict[str, Any] = Field(default_factory=dict, description="Variables for rendering")
    environment: str | None = Field(None, description="Target environment")

    @validator("template_content")
    def validate_template_source(cls, v, values):
        if not v and not values.get("template_id"):
            raise ValueError("Either template_id or template_content must be provided")
        return v


class TemplateRenderResponse(BaseModel):
    """Schema for template rendering response."""

    rendered_content: str = Field(..., description="Rendered template content")
    variables_used: dict[str, Any] = Field(..., description="Variables used in rendering")
    content_hash: str = Field(..., description="SHA-256 hash of rendered content")


# Bulk Operations
class BulkTemplateOperation(BaseModel):
    """Schema for bulk template operations."""

    template_ids: list[UUID] = Field(..., min_items=1, description="Template UUIDs")
    action: str = Field(..., description="Action to perform")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action parameters")

    @validator("action")
    def validate_action(cls, v):
        valid_actions = ["activate", "deactivate", "validate", "delete", "export"]
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        return v


class BulkTemplateOperationResponse(BaseModel):
    """Schema for bulk template operation response."""

    total_templates: int = Field(..., description="Total number of templates")
    successful_operations: int = Field(..., description="Number of successful operations")
    failed_operations: int = Field(..., description="Number of failed operations")
    results: list[dict[str, Any]] = Field(..., description="Detailed results for each template")


# Filter Schemas
class TemplateFilter(BaseModel):
    """Schema for filtering templates."""

    template_types: list[str] | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    environments: list[str] | None = None
    active_only: bool | None = None
    validated_only: bool | None = None
    name_search: str | None = None
    created_by: str | None = None
    hours_back: int | None = Field(None, ge=1, le=8760)


class InstanceFilter(BaseModel):
    """Schema for filtering template instances."""

    template_ids: list[UUID] | None = None
    device_ids: list[UUID] | None = None
    environments: list[str] | None = None
    deployed_only: bool | None = None
    drift_detected: bool | None = None
    validation_status: list[str] | None = None
