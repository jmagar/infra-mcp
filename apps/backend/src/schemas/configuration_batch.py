"""
Configuration Batch Deployment Schemas

Pydantic schemas for configuration batch deployment API endpoints.
Provides validation and serialization for atomic multi-file deployments.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ConfigurationFileChangeSchema(BaseModel):
    """Schema for a single file change in a batch deployment."""

    change_id: str = Field(..., description="Unique identifier for this file change")
    file_path: str = Field(..., description="Absolute path to the configuration file")
    content: str = Field(..., description="New file content")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata for the change"
    )

    @validator("file_path")
    def validate_file_path(cls, v):
        """Validate that file path is absolute."""
        if not v.startswith("/"):
            raise ValueError("File path must be absolute")
        return v

    @validator("content")
    def validate_content(cls, v):
        """Validate that content is provided."""
        if not v.strip():
            raise ValueError("File content cannot be empty")
        return v

    class Config:
        schema_extra = {
            "example": {
                "change_id": "nginx-ssl-update-001",
                "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                "content": "server {\n    listen 443 ssl;\n    ...\n}",
                "metadata": {"description": "Enable SSL for mysite", "backup_required": True},
            }
        }


class ConfigurationBatchRequestCreate(BaseModel):
    """Schema for creating a new configuration batch deployment."""

    device_ids: list[UUID] = Field(..., description="List of device IDs to deploy to")
    changes: list[ConfigurationFileChangeSchema] = Field(
        ..., description="List of file changes to apply"
    )
    dry_run: bool = Field(
        default=False, description="Whether to perform a dry run (validation only)"
    )
    auto_rollback: bool = Field(
        default=True, description="Whether to automatically rollback on failure"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional deployment metadata"
    )

    @validator("device_ids")
    def validate_device_ids(cls, v):
        """Validate that at least one device is specified."""
        if not v:
            raise ValueError("At least one device ID must be specified")
        return v

    @validator("changes")
    def validate_changes(cls, v):
        """Validate that at least one change is specified."""
        if not v:
            raise ValueError("At least one file change must be specified")
        return v

    class Config:
        schema_extra = {
            "example": {
                "device_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "changes": [
                    {
                        "change_id": "nginx-ssl-update",
                        "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                        "content": "server { listen 443 ssl; ... }",
                        "metadata": {"description": "Enable SSL"},
                    }
                ],
                "dry_run": False,
                "auto_rollback": True,
                "metadata": {
                    "deployment_name": "SSL Certificate Update",
                    "requested_by": "admin",
                    "priority": "medium",
                },
            }
        }


class BatchValidationResultSchema(BaseModel):
    """Schema for batch deployment validation results for a single device."""

    device_id: UUID = Field(..., description="Device ID")
    device_name: str = Field(..., description="Device hostname")
    file_validations: list[dict[str, Any]] = Field(..., description="Per-file validation results")
    overall_status: str = Field(..., description="Overall validation status for this device")
    validation_errors: list[str] = Field(..., description="List of validation errors")

    class Config:
        schema_extra = {
            "example": {
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "device_name": "web01.example.com",
                "file_validations": [
                    {
                        "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                        "status": "valid",
                        "errors": [],
                        "warnings": [],
                    }
                ],
                "overall_status": "valid",
                "validation_errors": [],
            }
        }


class ConfigurationBatchResponse(BaseModel):
    """Schema for configuration batch deployment response."""

    batch_id: str = Field(..., description="Unique batch deployment ID")
    status: str = Field(..., description="Current batch deployment status")
    started_at: datetime = Field(..., description="When the deployment started")
    completed_at: datetime | None = Field(None, description="When the deployment completed")
    device_count: int = Field(..., description="Number of devices in the deployment")
    change_count: int = Field(..., description="Number of file changes in the deployment")
    applied_changes: list[dict[str, Any]] = Field(..., description="Successfully applied changes")
    failed_changes: list[dict[str, Any]] = Field(..., description="Failed changes")
    rollback_plan: list[dict[str, Any]] = Field(..., description="Rollback operations performed")
    validation_results: list[BatchValidationResultSchema] = Field(
        ..., description="Validation results"
    )
    error_message: str | None = Field(None, description="Error message if deployment failed")
    dry_run: bool = Field(..., description="Whether this was a dry run")

    class Config:
        schema_extra = {
            "example": {
                "batch_id": "batch-456789abc-def0-1234",
                "status": "completed",
                "started_at": "2025-01-08T10:30:00Z",
                "completed_at": "2025-01-08T10:32:15Z",
                "device_count": 3,
                "change_count": 2,
                "applied_changes": [
                    {
                        "device_id": "123e4567-e89b-12d3-a456-426614174000",
                        "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                        "change_id": "nginx-ssl-update",
                        "applied_at": "2025-01-08T10:31:00Z",
                    }
                ],
                "failed_changes": [],
                "rollback_plan": [],
                "validation_results": [
                    {
                        "device_id": "123e4567-e89b-12d3-a456-426614174000",
                        "device_name": "web01.example.com",
                        "file_validations": [
                            {
                                "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                                "status": "valid",
                                "errors": [],
                                "warnings": [],
                            }
                        ],
                        "overall_status": "valid",
                        "validation_errors": [],
                    }
                ],
                "error_message": None,
                "dry_run": False,
            }
        }


class ConfigurationBatchStatusResponse(BaseModel):
    """Schema for batch deployment status query response."""

    batch_id: str = Field(..., description="Batch deployment ID")
    status: str = Field(..., description="Current deployment status")
    progress: dict[str, Any] = Field(..., description="Deployment progress information")
    started_at: datetime = Field(..., description="When the deployment started")
    completed_at: datetime | None = Field(None, description="When the deployment completed")
    estimated_completion: datetime | None = Field(None, description="Estimated completion time")

    class Config:
        schema_extra = {
            "example": {
                "batch_id": "batch-456789abc-def0-1234",
                "status": "executing",
                "progress": {
                    "devices_completed": 2,
                    "devices_total": 3,
                    "files_applied": 4,
                    "files_total": 6,
                    "completion_percentage": 66.7,
                },
                "started_at": "2025-01-08T10:30:00Z",
                "completed_at": None,
                "estimated_completion": "2025-01-08T10:33:00Z",
            }
        }


class BatchDeploymentListResponse(BaseModel):
    """Schema for listing batch deployments."""

    deployments: list[ConfigurationBatchResponse] = Field(
        ..., description="List of batch deployments"
    )
    total: int = Field(..., description="Total number of deployments")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")

    class Config:
        schema_extra = {
            "example": {
                "deployments": [
                    {
                        "batch_id": "batch-456789abc-def0-1234",
                        "status": "completed",
                        "started_at": "2025-01-08T10:30:00Z",
                        "completed_at": "2025-01-08T10:32:15Z",
                        "device_count": 3,
                        "change_count": 2,
                        "applied_changes": [],
                        "failed_changes": [],
                        "rollback_plan": [],
                        "validation_results": [],
                        "error_message": None,
                        "dry_run": False,
                    }
                ],
                "total": 15,
                "page": 1,
                "page_size": 10,
            }
        }


class BatchDeploymentCancelRequest(BaseModel):
    """Schema for cancelling a batch deployment."""

    reason: str = Field(..., description="Reason for cancellation")
    force: bool = Field(
        default=False, description="Force cancellation even if deployment is in progress"
    )

    class Config:
        schema_extra = {
            "example": {
                "reason": "Emergency rollback required due to service outage",
                "force": True,
            }
        }


class BatchDeploymentCancelResponse(BaseModel):
    """Schema for batch deployment cancellation response."""

    batch_id: str = Field(..., description="Batch deployment ID")
    cancelled: bool = Field(..., description="Whether cancellation was successful")
    status: str = Field(..., description="Current deployment status after cancellation")
    message: str = Field(..., description="Cancellation result message")
    rollback_initiated: bool = Field(..., description="Whether rollback was initiated")

    class Config:
        schema_extra = {
            "example": {
                "batch_id": "batch-456789abc-def0-1234",
                "cancelled": True,
                "status": "cancelled",
                "message": "Batch deployment cancelled successfully",
                "rollback_initiated": True,
            }
        }


class BatchDeploymentFilter(BaseModel):
    """Schema for filtering batch deployments."""

    status: list[str] | None = Field(None, description="Filter by deployment status")
    device_ids: list[UUID] | None = Field(None, description="Filter by device IDs")
    started_after: datetime | None = Field(None, description="Filter by start time (after)")
    started_before: datetime | None = Field(None, description="Filter by start time (before)")
    user_id: str | None = Field(None, description="Filter by user who initiated deployment")
    dry_run: bool | None = Field(None, description="Filter by dry run flag")

    class Config:
        schema_extra = {
            "example": {
                "status": ["completed", "failed"],
                "device_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "started_after": "2025-01-01T00:00:00Z",
                "started_before": "2025-01-31T23:59:59Z",
                "user_id": "admin",
                "dry_run": False,
            }
        }
