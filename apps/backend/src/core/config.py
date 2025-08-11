"""
Infrastructure Management MCP Server - Configuration Management

This module handles all configuration settings including database connections,
SSH settings, polling intervals, and environment-specific configurations.
"""

from functools import lru_cache
import os

from pydantic import Field, field_validator
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors_origins(v: str | list[str]) -> list[str]:
    """Parse CORS_ORIGINS from comma-separated string or return as-is if already a list.

    Ensures the return type is always a list[str].
    """
    if isinstance(v, str):
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    return v


class DatabaseSettings(BaseSettings):
    """Database configuration settings for PostgreSQL + TimescaleDB"""

    # Database Connection
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=9100, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="infrastructor", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="infrastructor", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="change_me_in_production", validation_alias="POSTGRES_PASSWORD")

    # Connection Pool Settings
    db_pool_size: int = Field(default=10, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, validation_alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, validation_alias="DB_POOL_RECYCLE")

    @property
    def database_url(self) -> str:
        """Generate async PostgreSQL database URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Generate sync PostgreSQL database URL for Alembic"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class RedisSettings(BaseSettings):
    """Redis configuration settings for caching and session storage"""

    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=9104, validation_alias="REDIS_PORT")
    redis_password: str | None = Field(default=None, validation_alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")

    # Connection Pool Settings
    redis_pool_size: int = Field(default=10, validation_alias="REDIS_POOL_SIZE")
    redis_max_connections: int = Field(default=20, validation_alias="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, validation_alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, validation_alias="REDIS_SOCKET_CONNECT_TIMEOUT")

    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class MCPServerSettings(BaseSettings):
    """FastMCP server configuration settings"""

    mcp_host: str = Field(default="0.0.0.0", validation_alias="MCP_HOST")
    mcp_port: int = Field(default=9102, validation_alias="MCP_PORT")
    mcp_path: str = Field(default="/mcp", validation_alias="MCP_PATH")
    mcp_log_level: str = Field(default="info", validation_alias="MCP_LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class WebSocketSettings(BaseSettings):
    """WebSocket server configuration for real-time streaming"""

    websocket_max_connections: int = Field(default=50, validation_alias="WEBSOCKET_MAX_CONNECTIONS")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class SSHSettings(BaseSettings):
    """SSH configuration for device communication"""

    ssh_connection_timeout: int = Field(default=10, validation_alias="SSH_CONNECTION_TIMEOUT")
    ssh_connect_timeout: int = Field(
        default=10, validation_alias="SSH_CONNECT_TIMEOUT"
    )  # Alias for compatibility
    ssh_command_timeout: int = Field(default=30, validation_alias="SSH_COMMAND_TIMEOUT")
    ssh_max_retries: int = Field(default=3, validation_alias="SSH_MAX_RETRIES")
    ssh_retry_delay: int = Field(default=5, validation_alias="SSH_RETRY_DELAY")
    ssh_max_connections_per_host: int = Field(default=5, validation_alias="SSH_MAX_CONNECTIONS_PER_HOST")
    ssh_key_path: str | None = Field(default=None, validation_alias="SSH_KEY_PATH")

    @property
    def default_ssh_key_path(self) -> str:
        """Get default SSH key path if not specified"""
        return self.ssh_key_path or os.path.expanduser("~/.ssh/id_ed25519")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class PollingSettings(BaseSettings):
    """Polling intervals and data collection settings"""

    polling_enabled: bool = Field(default=False, validation_alias="POLLING_ENABLED")
    polling_container_interval: int = Field(default=30, validation_alias="POLLING_CONTAINER_INTERVAL")
    polling_system_metrics_interval: int = Field(default=300, validation_alias="POLLING_SYSTEM_METRICS_INTERVAL")
    polling_drive_health_interval: int = Field(default=3600, validation_alias="POLLING_DRIVE_HEALTH_INTERVAL")
    polling_max_concurrent_devices: int = Field(default=10, validation_alias="POLLING_MAX_CONCURRENT_DEVICES")

    # Startup timing settings to reduce SSH congestion
    polling_startup_delay: int = Field(default=30, validation_alias="POLLING_STARTUP_DELAY")
    polling_device_stagger_delay: int = Field(default=30, validation_alias="POLLING_DEVICE_STAGGER_DELAY")
    polling_task_stagger_delay: int = Field(default=10, validation_alias="POLLING_TASK_STAGGER_DELAY")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class MonitoringSettings(BaseSettings):
    """Monitoring and data collection feature settings"""

    # SMART Drive Monitoring
    smart_monitoring_enabled: bool = Field(default=True, validation_alias="SMART_MONITORING_ENABLED")
    smart_command_timeout: int = Field(default=15, validation_alias="SMART_COMMAND_TIMEOUT")
    smart_graceful_fallback: bool = Field(default=True, validation_alias="SMART_GRACEFUL_FALLBACK")
    smart_require_sudo: bool = Field(default=False, validation_alias="SMART_REQUIRE_SUDO")

    # Other monitoring features
    container_monitoring_enabled: bool = Field(default=True, validation_alias="CONTAINER_MONITORING_ENABLED")
    system_metrics_enabled: bool = Field(default=True, validation_alias="SYSTEM_METRICS_ENABLED")
    network_monitoring_enabled: bool = Field(default=True, validation_alias="NETWORK_MONITORING_ENABLED")

    @field_validator("smart_command_timeout")
    def validate_smart_timeout(cls, v: int) -> int:
        if v < 5 or v > 300:
            raise ValueError("SMART command timeout must be between 5 and 300 seconds")
        return v

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class RetentionSettings(BaseSettings):
    """Data retention and compression settings"""

    retention_system_metrics_days: int = Field(default=30, validation_alias="RETENTION_SYSTEM_METRICS_DAYS")
    retention_drive_health_days: int = Field(default=90, validation_alias="RETENTION_DRIVE_HEALTH_DAYS")
    retention_container_snapshots_days: int = Field(
        default=30, validation_alias="RETENTION_CONTAINER_SNAPSHOTS_DAYS"
    )
    compression_after_days: int = Field(default=7, validation_alias="COMPRESSION_AFTER_DAYS")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class AuthSettings(BaseSettings):
    """Authentication and security settings"""

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-in-production", validation_alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, validation_alias="JWT_EXPIRE_MINUTES")

    # API Key Authentication
    api_key: str | None = Field(default=None, validation_alias="API_KEY")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class LoggingSettings(BaseSettings):
    """Logging configuration settings"""

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")
    log_file_path: str = Field(default="./logs/infrastructor.log", validation_alias="LOG_FILE_PATH")
    log_max_bytes: int = Field(default=10485760, validation_alias="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(default=5, validation_alias="LOG_BACKUP_COUNT")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class APISettings(BaseSettings):
    """FastAPI REST API server configuration settings"""

    # API Server Configuration
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=9101, validation_alias="API_PORT")
    api_log_level: str = Field(default="info", validation_alias="API_LOG_LEVEL")

    # CORS Configuration - avoid JSON parsing entirely
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
        ]
    )

    # Cache settings
    cache_enabled: bool = Field(default=True, validation_alias="CACHE_ENABLED")
    cache_ttl: int = Field(default=300, validation_alias="CACHE_TTL")
    cache_max_size: int = Field(default=1000, validation_alias="CACHE_MAX_SIZE")

    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=100, validation_alias="RATE_LIMIT_REQUESTS_PER_MINUTE")

    # SSH concurrency limits
    max_concurrent_ssh_connections: int = Field(default=50, validation_alias="MAX_CONCURRENT_SSH_CONNECTIONS")

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        # Handle CORS_ORIGINS environment variable manually after initialization
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env:
            self.cors_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class SWAGSettings(BaseSettings):
    """SWAG reverse proxy configuration settings"""

    # SWAG device and paths
    swag_device: str = Field(default="squirts", validation_alias="SWAG_DEVICE")
    swag_config_dir: str = Field(
        default="/mnt/appdata/swag/nginx/proxy-confs", validation_alias="SWAG_CONFIG_DIR"
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class GlancesSettings(BaseSettings):
    """Glances integration settings"""
    
    default_port: int = Field(default=61208, description="Default Glances API port")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")
    max_connections_per_device: int = Field(default=5, description="Max concurrent connections")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class ExternalIntegrationSettings(BaseSettings):
    """External service integration settings"""

    # Gotify Notifications
    gotify_url: str | None = Field(default=None, validation_alias="GOTIFY_URL")
    gotify_token: str | None = Field(default=None, validation_alias="GOTIFY_TOKEN")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


class ApplicationSettings(BaseSettings):
    """Main application settings combining all configuration sections"""

    # Environment
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    mcp_server: MCPServerSettings = Field(default_factory=MCPServerSettings)
    websocket: WebSocketSettings = Field(default_factory=WebSocketSettings)
    ssh: SSHSettings = Field(default_factory=SSHSettings)
    polling: PollingSettings = Field(default_factory=PollingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    retention: RetentionSettings = Field(default_factory=RetentionSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    api: APISettings = Field(default_factory=APISettings)
    swag: SWAGSettings = Field(default_factory=SWAGSettings)
    glances: GlancesSettings = Field(default_factory=GlancesSettings)
    external: ExternalIntegrationSettings = Field(default_factory=ExternalIntegrationSettings)

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() == "production"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> ApplicationSettings:
    """Get cached application settings instance"""
    return ApplicationSettings()


# Global settings instance for easy import
settings = get_settings()
