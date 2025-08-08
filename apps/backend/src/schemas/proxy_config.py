"""
Proxy Configuration Schemas

Pydantic models for SWAG reverse proxy configuration management
including file-based nginx configurations and database tracking.
"""

from datetime import datetime

from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProxyConfigStatus(str, Enum):
    """Status of proxy configuration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class ProxyConfigType(str, Enum):
    """Type of proxy configuration"""

    SUBDOMAIN = "subdomain"
    SUBFOLDER = "subfolder"
    PORT = "port"
    CUSTOM = "custom"


class NginxDirective(BaseModel):
    """Individual nginx directive"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Directive name (e.g., 'server_name', 'proxy_pass')")
    value: str = Field(..., description="Directive value")
    context: str = Field(
        ..., description="Context where directive appears (server, location, etc.)"
    )
    line_number: int | None = Field(None, description="Line number in config file")


class ProxyConfigParsed(BaseModel):
    """Parsed nginx configuration data"""

    model_config = ConfigDict(from_attributes=True)

    server_name: str | None = Field(None, description="Primary server name")
    server_names: list[str] = Field(default_factory=list, description="All server names")
    proxy_pass: str | None = Field(None, description="Upstream proxy destination")
    listen_ports: list[int] = Field(default_factory=list, description="Listen ports")
    ssl_enabled: bool = Field(False, description="SSL/TLS enabled")
    ssl_certificate: str | None = Field(None, description="SSL certificate path")
    ssl_certificate_key: str | None = Field(None, description="SSL certificate key path")
    locations: list[dict[str, Any]] = Field(default_factory=list, description="Location blocks")
    upstream_servers: list[str] = Field(
        default_factory=list, description="Upstream server definitions"
    )
    custom_directives: list[NginxDirective] = Field(
        default_factory=list, description="Custom nginx directives"
    )


class ProxyConfigBase(BaseModel):
    """Base proxy configuration model"""

    model_config = ConfigDict(from_attributes=True)

    service_name: str = Field(..., description="Service name (e.g., 'portainer', 'grafana')")
    subdomain: str = Field(..., description="Subdomain (e.g., 'portainer', 'grafana')")
    config_type: ProxyConfigType = Field(
        default=ProxyConfigType.SUBDOMAIN, description="Configuration type"
    )
    status: ProxyConfigStatus = Field(
        default=ProxyConfigStatus.ACTIVE, description="Configuration status"
    )
    file_path: str = Field(..., description="Full path to nginx config file")
    description: str | None = Field(None, description="Human-readable description")
    tags: dict[str, str] = Field(default_factory=dict, description="Custom tags for organization")


class ProxyConfigCreate(ProxyConfigBase):
    """Schema for creating proxy configurations"""

    raw_content: str = Field(..., description="Raw nginx configuration content")


class ProxyConfigUpdate(BaseModel):
    """Schema for updating proxy configurations"""

    model_config = ConfigDict(from_attributes=True)

    service_name: str | None = None
    subdomain: str | None = None
    config_type: ProxyConfigType | None = None
    status: ProxyConfigStatus | None = None
    description: str | None = None
    tags: dict[str, str] | None = None
    raw_content: str | None = None


class ProxyConfigResponse(ProxyConfigBase):
    """Complete proxy configuration response"""

    id: int = Field(..., description="Configuration ID")
    device_id: str = Field(..., description="Device hostname where config is located")
    file_size: int | None = Field(None, description="File size in bytes")
    file_hash: str | None = Field(None, description="SHA256 hash of file content")
    last_modified: datetime | None = Field(None, description="File last modified timestamp")
    parsed_config: ProxyConfigParsed | None = Field(
        None, description="Parsed configuration data"
    )
    raw_content: str | None = Field(None, description="Raw nginx configuration content")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")
    sync_status: str = Field(..., description="Sync status with file system")
    sync_last_checked: datetime | None = Field(None, description="Last sync check timestamp")


class ProxyConfigList(BaseModel):
    """List of proxy configurations with pagination"""

    model_config = ConfigDict(from_attributes=True)

    items: list[ProxyConfigResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProxyConfigSummary(BaseModel):
    """Summary statistics for proxy configurations"""

    model_config = ConfigDict(from_attributes=True)

    total_configs: int = Field(..., description="Total number of configurations")
    active_configs: int = Field(..., description="Number of active configurations")
    inactive_configs: int = Field(..., description="Number of inactive configurations")
    error_configs: int = Field(..., description="Number of configurations with errors")
    by_device: dict[str, int] = Field(default_factory=dict, description="Configurations per device")
    by_service_type: dict[str, int] = Field(
        default_factory=dict, description="Configurations per service type"
    )
    ssl_enabled_count: int = Field(0, description="Number of SSL-enabled configurations")
    last_sync: datetime | None = Field(None, description="Last successful sync timestamp")


class ProxyConfigFileInfo(BaseModel):
    """File information for direct file access"""

    model_config = ConfigDict(from_attributes=True)

    file_path: str = Field(..., description="Full path to config file")
    file_name: str = Field(..., description="Config file name")
    service_name: str = Field(..., description="Extracted service name")
    subdomain: str = Field(..., description="Extracted subdomain")
    file_size: int = Field(..., description="File size in bytes")
    last_modified: datetime = Field(..., description="File last modified timestamp")
    exists: bool = Field(..., description="File exists on filesystem")
    readable: bool = Field(..., description="File is readable")


class ProxyConfigValidation(BaseModel):
    """Nginx configuration validation result"""

    model_config = ConfigDict(from_attributes=True)

    is_valid: bool = Field(..., description="Configuration is syntactically valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    nginx_test_output: str | None = Field(None, description="Raw nginx -t output")
    validated_at: datetime = Field(..., description="Validation timestamp")


class ProxyConfigChange(BaseModel):
    """Tracked change in proxy configuration"""

    model_config = ConfigDict(from_attributes=True)

    config_id: int = Field(..., description="Configuration ID")
    change_type: str = Field(..., description="Type of change (created, modified, deleted)")
    old_hash: str | None = Field(None, description="Previous file hash")
    new_hash: str | None = Field(None, description="New file hash")
    changes_detected: list[str] = Field(
        default_factory=list, description="List of detected changes"
    )
    detected_at: datetime = Field(..., description="Change detection timestamp")


class ProxyConfigSync(BaseModel):
    """Sync operation result"""

    model_config = ConfigDict(from_attributes=True)

    total_files_found: int = Field(..., description="Total config files found")
    new_configs: int = Field(..., description="New configurations added")
    updated_configs: int = Field(..., description="Existing configurations updated")
    removed_configs: int = Field(..., description="Configurations marked as removed")
    errors: list[str] = Field(default_factory=list, description="Sync errors")
    sync_duration_ms: int = Field(..., description="Sync operation duration in milliseconds")
    synced_at: datetime = Field(..., description="Sync completion timestamp")


class ProxyConfigResource(BaseModel):
    """MCP Resource representation of proxy config"""

    model_config = ConfigDict(from_attributes=True)

    uri: str = Field(..., description="Resource URI")
    name: str = Field(..., description="Resource name")
    description: str = Field(..., description="Resource description")
    mime_type: str = Field(default="text/plain", description="MIME type")
    service_name: str = Field(..., description="Service name")
    subdomain: str = Field(..., description="Subdomain")
    device_id: str = Field(..., description="Device hostname")
    file_path: str = Field(..., description="File path")
    last_modified: datetime | None = Field(None, description="Last modified timestamp")


# Request/Response models for API endpoints
class ProxyConfigSearchRequest(BaseModel):
    """Search request for proxy configurations"""

    model_config = ConfigDict(from_attributes=True)

    service_name: str | None = Field(None, description="Filter by service name")
    subdomain: str | None = Field(None, description="Filter by subdomain")
    device_id: str | None = Field(None, description="Filter by device")
    status: ProxyConfigStatus | None = Field(None, description="Filter by status")
    config_type: ProxyConfigType | None = Field(None, description="Filter by type")
    ssl_enabled: bool | None = Field(None, description="Filter by SSL status")
    search_content: str | None = Field(None, description="Search within config content")
    tags: dict[str, str] | None = Field(None, description="Filter by tags")


class ProxyConfigBulkOperation(BaseModel):
    """Bulk operation request"""

    model_config = ConfigDict(from_attributes=True)

    config_ids: list[int] = Field(..., description="Configuration IDs to operate on")
    operation: str = Field(..., description="Operation to perform")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Operation parameters")


class ProxyConfigTemplate(BaseModel):
    """Template for generating proxy configurations"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    config_type: ProxyConfigType = Field(..., description="Configuration type")
    template_content: str = Field(..., description="Template content with placeholders")
    variables: list[str] = Field(default_factory=list, description="Template variables")
    example_values: dict[str, str] = Field(
        default_factory=dict, description="Example variable values"
    )
