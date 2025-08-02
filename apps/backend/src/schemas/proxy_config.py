"""
Proxy Configuration Schemas

Pydantic models for SWAG reverse proxy configuration management
including file-based nginx configurations and database tracking.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, validator


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
    line_number: Optional[int] = Field(None, description="Line number in config file")


class ProxyConfigParsed(BaseModel):
    """Parsed nginx configuration data"""

    model_config = ConfigDict(from_attributes=True)

    server_name: Optional[str] = Field(None, description="Primary server name")
    server_names: List[str] = Field(default_factory=list, description="All server names")
    proxy_pass: Optional[str] = Field(None, description="Upstream proxy destination")
    listen_ports: List[int] = Field(default_factory=list, description="Listen ports")
    ssl_enabled: bool = Field(False, description="SSL/TLS enabled")
    ssl_certificate: Optional[str] = Field(None, description="SSL certificate path")
    ssl_certificate_key: Optional[str] = Field(None, description="SSL certificate key path")
    locations: List[Dict[str, Any]] = Field(default_factory=list, description="Location blocks")
    upstream_servers: List[str] = Field(
        default_factory=list, description="Upstream server definitions"
    )
    custom_directives: List[NginxDirective] = Field(
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
    description: Optional[str] = Field(None, description="Human-readable description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags for organization")


class ProxyConfigCreate(ProxyConfigBase):
    """Schema for creating proxy configurations"""

    raw_content: str = Field(..., description="Raw nginx configuration content")


class ProxyConfigUpdate(BaseModel):
    """Schema for updating proxy configurations"""

    model_config = ConfigDict(from_attributes=True)

    service_name: Optional[str] = None
    subdomain: Optional[str] = None
    config_type: Optional[ProxyConfigType] = None
    status: Optional[ProxyConfigStatus] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    raw_content: Optional[str] = None


class ProxyConfigResponse(ProxyConfigBase):
    """Complete proxy configuration response"""

    id: int = Field(..., description="Configuration ID")
    device_id: str = Field(..., description="Device hostname where config is located")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_hash: Optional[str] = Field(None, description="SHA256 hash of file content")
    last_modified: Optional[datetime] = Field(None, description="File last modified timestamp")
    parsed_config: Optional[ProxyConfigParsed] = Field(
        None, description="Parsed configuration data"
    )
    raw_content: Optional[str] = Field(None, description="Raw nginx configuration content")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")
    sync_status: str = Field(..., description="Sync status with file system")
    sync_last_checked: Optional[datetime] = Field(None, description="Last sync check timestamp")


class ProxyConfigList(BaseModel):
    """List of proxy configurations with pagination"""

    model_config = ConfigDict(from_attributes=True)

    items: List[ProxyConfigResponse]
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
    by_device: Dict[str, int] = Field(default_factory=dict, description="Configurations per device")
    by_service_type: Dict[str, int] = Field(
        default_factory=dict, description="Configurations per service type"
    )
    ssl_enabled_count: int = Field(0, description="Number of SSL-enabled configurations")
    last_sync: Optional[datetime] = Field(None, description="Last successful sync timestamp")


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
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    nginx_test_output: Optional[str] = Field(None, description="Raw nginx -t output")
    validated_at: datetime = Field(..., description="Validation timestamp")


class ProxyConfigChange(BaseModel):
    """Tracked change in proxy configuration"""

    model_config = ConfigDict(from_attributes=True)

    config_id: int = Field(..., description="Configuration ID")
    change_type: str = Field(..., description="Type of change (created, modified, deleted)")
    old_hash: Optional[str] = Field(None, description="Previous file hash")
    new_hash: Optional[str] = Field(None, description="New file hash")
    changes_detected: List[str] = Field(
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
    errors: List[str] = Field(default_factory=list, description="Sync errors")
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
    last_modified: Optional[datetime] = Field(None, description="Last modified timestamp")


# Request/Response models for API endpoints
class ProxyConfigSearchRequest(BaseModel):
    """Search request for proxy configurations"""

    model_config = ConfigDict(from_attributes=True)

    service_name: Optional[str] = Field(None, description="Filter by service name")
    subdomain: Optional[str] = Field(None, description="Filter by subdomain")
    device_id: Optional[str] = Field(None, description="Filter by device")
    status: Optional[ProxyConfigStatus] = Field(None, description="Filter by status")
    config_type: Optional[ProxyConfigType] = Field(None, description="Filter by type")
    ssl_enabled: Optional[bool] = Field(None, description="Filter by SSL status")
    search_content: Optional[str] = Field(None, description="Search within config content")
    tags: Optional[Dict[str, str]] = Field(None, description="Filter by tags")


class ProxyConfigBulkOperation(BaseModel):
    """Bulk operation request"""

    model_config = ConfigDict(from_attributes=True)

    config_ids: List[int] = Field(..., description="Configuration IDs to operate on")
    operation: str = Field(..., description="Operation to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")


class ProxyConfigTemplate(BaseModel):
    """Template for generating proxy configurations"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    config_type: ProxyConfigType = Field(..., description="Configuration type")
    template_content: str = Field(..., description="Template content with placeholders")
    variables: List[str] = Field(default_factory=list, description="Template variables")
    example_values: Dict[str, str] = Field(
        default_factory=dict, description="Example variable values"
    )
