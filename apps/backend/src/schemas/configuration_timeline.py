"""
Configuration Timeline Schemas

Pydantic schemas for configuration timeline and diff visualization API endpoints.
Provides validation and serialization for timeline data, version comparisons, and change analysis.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TimelineItemSchema(BaseModel):
    """Schema for a single timeline item (event or snapshot)."""

    type: str = Field(..., description="Type of timeline item (event or snapshot)")
    id: str = Field(..., description="Unique identifier for the item")
    timestamp: datetime = Field(..., description="When the item occurred")
    file_path: str = Field(..., description="Path to the configuration file")
    change_type: str = Field(..., description="Type of change")

    # Event-specific fields
    risk_level: str | None = Field(None, description="Risk level for events")
    triggered_by: str | None = Field(None, description="Who/what triggered the event")
    impact_summary: dict[str, Any] | None = Field(None, description="Impact analysis summary")
    affected_services: list[str] | None = Field(None, description="Services affected by change")
    confidence_score: float | None = Field(None, description="Confidence score for event")

    # Snapshot-specific fields
    content_hash: str | None = Field(None, description="SHA256 hash of content")
    file_size: int | None = Field(None, description="File size in bytes")
    content: str | None = Field(None, description="Full file content (optional)")

    # Diff data (if requested)
    diff: str | None = Field(None, description="Unified diff from previous version")
    diff_summary: dict[str, Any] | None = Field(None, description="Statistical summary of diff")

    class Config:
        schema_extra = {
            "example": {
                "type": "event",
                "id": "event-123",
                "timestamp": "2025-01-08T10:30:00Z",
                "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                "change_type": "modified",
                "risk_level": "medium",
                "triggered_by": "admin",
                "impact_summary": {"services_affected": 2, "estimated_downtime": 0},
                "affected_services": ["nginx", "web-app"],
                "confidence_score": 0.85,
            }
        }


class TimelineStatisticsSchema(BaseModel):
    """Schema for timeline statistics."""

    total_events: int = Field(..., description="Total number of events")
    total_snapshots: int = Field(..., description="Total number of snapshots")
    file_count: int = Field(..., description="Number of unique files")
    risk_distribution: dict[str, int] = Field(..., description="Count of events by risk level")
    change_type_distribution: dict[str, int] = Field(
        ..., description="Count of events by change type"
    )
    activity_by_hour: list[int] = Field(..., description="Activity count for each hour (0-23)")

    class Config:
        schema_extra = {
            "example": {
                "total_events": 25,
                "total_snapshots": 18,
                "file_count": 5,
                "risk_distribution": {"low": 10, "medium": 12, "high": 3},
                "change_type_distribution": {"modified": 20, "created": 3, "deleted": 2},
                "activity_by_hour": [
                    0,
                    0,
                    2,
                    1,
                    0,
                    0,
                    0,
                    0,
                    5,
                    8,
                    3,
                    2,
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ],
            }
        }


class ConfigurationTimelineResponse(BaseModel):
    """Schema for device configuration timeline response."""

    device_id: str = Field(..., description="Device UUID")
    device_name: str = Field(..., description="Device hostname")
    timeline: list[TimelineItemSchema] = Field(
        ..., description="Timeline items in chronological order"
    )
    statistics: TimelineStatisticsSchema = Field(..., description="Timeline statistics")
    generated_at: datetime = Field(..., description="When the timeline was generated")
    filters: dict[str, Any] = Field(..., description="Applied filters")

    class Config:
        schema_extra = {
            "example": {
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "device_name": "web01.example.com",
                "timeline": [],
                "statistics": {
                    "total_events": 25,
                    "total_snapshots": 18,
                    "file_count": 5,
                    "risk_distribution": {"low": 10, "medium": 12, "high": 3},
                    "change_type_distribution": {"modified": 20, "created": 3, "deleted": 2},
                    "activity_by_hour": [0] * 24,
                },
                "generated_at": "2025-01-08T10:30:00Z",
                "filters": {"file_path": None, "include_content": False, "include_diffs": True},
            }
        }


class FileVersionSchema(BaseModel):
    """Schema for a single file version."""

    version_id: str = Field(..., description="Snapshot UUID")
    timestamp: datetime = Field(..., description="When this version was created")
    change_type: str = Field(..., description="Type of change")
    content_hash: str = Field(..., description="SHA256 hash of content")
    file_size: int = Field(..., description="File size in bytes")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")
    content: str | None = Field(None, description="Full file content (optional)")
    diff: str | None = Field(None, description="Diff from previous version")
    changes_summary: dict[str, Any] | None = Field(None, description="Summary of changes")

    class Config:
        schema_extra = {
            "example": {
                "version_id": "snapshot-456",
                "timestamp": "2025-01-08T10:30:00Z",
                "change_type": "modified",
                "content_hash": "sha256:abc123...",
                "file_size": 2048,
                "metadata": {"backup_created": True},
                "content": "server { ... }",
                "diff": "@@ -10,3 +10,4 @@\n listen 80;\n+listen 443 ssl;",
                "changes_summary": {"lines_added": 1, "lines_removed": 0},
            }
        }


class FileHistoryResponse(BaseModel):
    """Schema for configuration file history response."""

    device_id: str = Field(..., description="Device UUID")
    device_name: str = Field(..., description="Device hostname")
    file_path: str = Field(..., description="Configuration file path")
    versions: list[FileVersionSchema] = Field(
        ..., description="File versions in reverse chronological order"
    )
    total_versions: int = Field(..., description="Total number of versions")
    first_seen: datetime | None = Field(None, description="When file was first seen")
    last_modified: datetime | None = Field(None, description="When file was last modified")
    related_events: list[dict[str, Any]] = Field(
        ..., description="Related configuration change events"
    )
    file_stats: dict[str, Any] = Field(..., description="File statistics")

    class Config:
        schema_extra = {
            "example": {
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "device_name": "web01.example.com",
                "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                "versions": [],
                "total_versions": 10,
                "first_seen": "2025-01-01T00:00:00Z",
                "last_modified": "2025-01-08T10:30:00Z",
                "related_events": [],
                "file_stats": {
                    "avg_size": 2048,
                    "min_size": 1500,
                    "max_size": 2500,
                    "change_frequency": 15,
                },
            }
        }


class VersionComparisonRequest(BaseModel):
    """Schema for version comparison request."""

    snapshot_id_1: UUID = Field(..., description="First snapshot ID (older)")
    snapshot_id_2: UUID = Field(..., description="Second snapshot ID (newer)")
    diff_format: str = Field(
        default="unified", description="Diff format (unified, side-by-side, json)"
    )

    class Config:
        schema_extra = {
            "example": {
                "snapshot_id_1": "123e4567-e89b-12d3-a456-426614174000",
                "snapshot_id_2": "987fcdeb-51a2-43d7-8765-426614174001",
                "diff_format": "unified",
            }
        }


class SnapshotInfoSchema(BaseModel):
    """Schema for snapshot information in comparison."""

    id: str = Field(..., description="Snapshot UUID")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    content_hash: str = Field(..., description="Content hash")
    file_size: int = Field(..., description="File size in bytes")
    change_type: str = Field(..., description="Type of change")

    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-01-08T10:30:00Z",
                "content_hash": "sha256:abc123...",
                "file_size": 2048,
                "change_type": "modified",
            }
        }


class DiffAnalysisSchema(BaseModel):
    """Schema for diff analysis results."""

    content_changed: bool = Field(..., description="Whether content actually changed")
    size_change: int = Field(..., description="Change in file size (bytes)")
    risk_assessment: str = Field(..., description="Assessed risk level of change")

    class Config:
        schema_extra = {
            "example": {"content_changed": True, "size_change": 100, "risk_assessment": "medium"}
        }


class VersionComparisonResponse(BaseModel):
    """Schema for version comparison response."""

    comparison_id: str = Field(..., description="Unique comparison identifier")
    snapshot1: SnapshotInfoSchema = Field(..., description="First snapshot info")
    snapshot2: SnapshotInfoSchema = Field(..., description="Second snapshot info")
    file_info: dict[str, Any] = Field(..., description="File information")
    diff: dict[str, Any] = Field(..., description="Diff content and statistics")
    analysis: DiffAnalysisSchema = Field(..., description="Change analysis")

    class Config:
        schema_extra = {
            "example": {
                "comparison_id": "snap1-snap2",
                "snapshot1": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "timestamp": "2025-01-08T10:00:00Z",
                    "content_hash": "sha256:old123...",
                    "file_size": 2000,
                    "change_type": "modified",
                },
                "snapshot2": {
                    "id": "987fcdeb-51a2-43d7-8765-426614174001",
                    "timestamp": "2025-01-08T10:30:00Z",
                    "content_hash": "sha256:new456...",
                    "file_size": 2100,
                    "change_type": "modified",
                },
                "file_info": {
                    "device_id": "123e4567-e89b-12d3-a456-426614174000",
                    "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                },
                "diff": {
                    "format": "unified",
                    "content": "@@ -10,3 +10,4 @@\n listen 80;\n+listen 443 ssl;",
                    "statistics": {"lines_added": 1, "lines_removed": 0},
                    "time_delta": 1800,
                },
                "analysis": {
                    "content_changed": True,
                    "size_change": 100,
                    "risk_assessment": "medium",
                },
            }
        }


class ChangeImpactResponse(BaseModel):
    """Schema for configuration change impact analysis."""

    event_id: str = Field(..., description="Change event UUID")
    device_id: str = Field(..., description="Device UUID")
    device_name: str = Field(..., description="Device hostname")
    timestamp: datetime = Field(..., description="When the change occurred")
    file_path: str = Field(..., description="Configuration file path")
    change_type: str = Field(..., description="Type of change")
    risk_level: str = Field(..., description="Risk level")
    triggered_by: str = Field(..., description="Who/what triggered the change")
    impact_summary: dict[str, Any] | None = Field(None, description="Impact analysis")
    affected_services: list[str] | None = Field(None, description="Affected services")
    rollback_available: bool = Field(..., description="Whether rollback is available")
    confidence_score: float = Field(..., description="Confidence in impact analysis")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")
    snapshot: dict[str, Any] | None = Field(None, description="Associated snapshot info")
    related_changes: list[dict[str, Any]] = Field(..., description="Related changes in time window")
    visualization: dict[str, Any] = Field(..., description="Data for visualization")

    class Config:
        schema_extra = {
            "example": {
                "event_id": "event-123",
                "device_id": "123e4567-e89b-12d3-a456-426614174000",
                "device_name": "web01.example.com",
                "timestamp": "2025-01-08T10:30:00Z",
                "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                "change_type": "modified",
                "risk_level": "medium",
                "triggered_by": "admin",
                "impact_summary": {"services_affected": 2},
                "affected_services": ["nginx", "web-app"],
                "rollback_available": True,
                "confidence_score": 0.85,
                "metadata": {},
                "snapshot": {
                    "id": "snap-456",
                    "content_hash": "sha256:abc123...",
                    "file_size": 2048,
                    "created_at": "2025-01-08T10:30:00Z",
                },
                "related_changes": [],
                "visualization": {
                    "timeline_position": {"position": 5, "total": 20, "percentage": 25.0},
                    "change_frequency": {"changes_in_14_days": 3, "frequency_score": "low"},
                    "risk_trend": {"trend": "stable", "recent_risk_levels": ["medium"]},
                },
            }
        }


class TimelineQueryParams(BaseModel):
    """Schema for timeline query parameters."""

    file_path: str | None = Field(None, description="Filter by specific file path")
    days_back: int = Field(default=30, ge=1, le=365, description="Number of days of history")
    include_content: bool = Field(default=False, description="Include full file content")
    include_diffs: bool = Field(default=True, description="Include diff calculations")

    class Config:
        schema_extra = {
            "example": {
                "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                "days_back": 30,
                "include_content": False,
                "include_diffs": True,
            }
        }


class FileHistoryQueryParams(BaseModel):
    """Schema for file history query parameters."""

    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of versions")
    include_content: bool = Field(default=True, description="Include full file content")

    class Config:
        schema_extra = {"example": {"limit": 50, "include_content": True}}
