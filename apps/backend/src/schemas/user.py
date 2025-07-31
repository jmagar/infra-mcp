"""
User authentication and authorization Pydantic schemas.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, field_validator
from apps.backend.src.schemas.common import PaginatedResponse


class UserBase(BaseModel):
    """Base user schema with common fields"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    bio: Optional[str] = Field(None, max_length=500, description="User bio")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar image URL")
    timezone: str = Field(default="UTC", max_length=50, description="User timezone")
    language: str = Field(default="en", max_length=10, description="Preferred language")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        # Username can contain letters, numbers, underscores, hyphens
        if not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, hyphens, and periods")
        return v.lower()
    
    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v):
        # Basic timezone validation - just check common formats
        common_timezones = [
            "UTC", "US/Eastern", "US/Central", "US/Mountain", "US/Pacific",
            "Europe/London", "Europe/Paris", "Europe/Berlin", "Asia/Tokyo",
            "Australia/Sydney", "America/New_York", "America/Chicago",
            "America/Denver", "America/Los_Angeles"
        ]
        if v not in common_timezones and not v.startswith("UTC"):
            raise ValueError(f"Timezone must be one of: {', '.join(common_timezones)} or UTC offset")
        return v
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        valid_languages = ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"]
        if v not in valid_languages:
            raise ValueError(f"Language must be one of: {', '.join(valid_languages)}")
        return v


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        # Password must contain at least one uppercase, one lowercase, one digit
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    email: Optional[EmailStr] = Field(None, description="Updated email address")
    full_name: Optional[str] = Field(None, max_length=100, description="Updated full name")
    bio: Optional[str] = Field(None, max_length=500, description="Updated bio")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Updated avatar URL")
    timezone: Optional[str] = Field(None, max_length=50, description="Updated timezone")
    language: Optional[str] = Field(None, max_length=10, description="Updated language")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Updated preferences")
    
    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v):
        if v is not None:
            # Basic timezone validation - just check common formats
            common_timezones = [
                "UTC", "US/Eastern", "US/Central", "US/Mountain", "US/Pacific",
                "Europe/London", "Europe/Paris", "Europe/Berlin", "Asia/Tokyo",
                "Australia/Sydney", "America/New_York", "America/Chicago",
                "America/Denver", "America/Los_Angeles"
            ]
            if v not in common_timezones and not v.startswith("UTC"):
                raise ValueError(f"Timezone must be one of: {', '.join(common_timezones)} or UTC offset")
        return v


class UserResponse(UserBase):
    """Schema for user response data"""
    id: UUID = Field(description="User unique identifier")
    is_active: bool = Field(description="Whether user account is active")
    is_superuser: bool = Field(description="Whether user has superuser privileges")
    is_verified: bool = Field(description="Whether user email is verified")
    created_at: datetime = Field(description="Account creation timestamp")
    updated_at: datetime = Field(description="Account last update timestamp")
    last_login_at: Optional[datetime] = Field(description="Last login timestamp")
    password_changed_at: datetime = Field(description="Password last changed timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class UserList(PaginatedResponse[UserResponse]):
    """Paginated list of users"""
    pass


class UserProfile(BaseModel):
    """Public user profile information"""
    id: UUID = Field(description="User unique identifier")
    username: str = Field(description="Username")
    full_name: Optional[str] = Field(description="Full name")
    bio: Optional[str] = Field(description="User bio")
    avatar_url: Optional[str] = Field(description="Avatar image URL")
    created_at: datetime = Field(description="Account creation timestamp")
    last_login_at: Optional[datetime] = Field(description="Last login timestamp")
    
    class Config:
        from_attributes = True


class UserLoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(default=False, description="Remember login session")
    device_fingerprint: Optional[str] = Field(None, description="Device fingerprint for security")


class UserLoginResponse(BaseModel):
    """Login response schema"""
    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")
    user: UserResponse = Field(description="User information")
    session_id: UUID = Field(description="Session identifier")


class UserRefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str = Field(..., description="Refresh token")


class UserChangePasswordRequest(BaseModel):
    """Change password request schema"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        # Same validation as UserCreate password
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserResetPasswordRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr = Field(..., description="User email address")


class UserResetPasswordConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        # Same validation as UserCreate password
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserEmailVerificationRequest(BaseModel):
    """Email verification request schema"""
    token: str = Field(..., description="Email verification token")


class UserSessionResponse(BaseModel):
    """User session information"""
    id: UUID = Field(description="Session unique identifier")
    user_id: UUID = Field(description="User identifier")
    ip_address: Optional[str] = Field(description="Session IP address")
    user_agent: Optional[str] = Field(description="User agent string")
    device_fingerprint: Optional[str] = Field(description="Device fingerprint")
    created_at: datetime = Field(description="Session creation timestamp")
    expires_at: datetime = Field(description="Session expiration timestamp")
    last_accessed_at: datetime = Field(description="Last access timestamp")
    is_active: bool = Field(description="Whether session is active")
    
    class Config:
        from_attributes = True


class UserSessionList(PaginatedResponse[UserSessionResponse]):
    """Paginated list of user sessions"""
    pass


class UserAPIKeyCreate(BaseModel):
    """Schema for creating API key"""
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    scopes: List[str] = Field(description="API key scopes/permissions")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")
    
    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v):
        valid_scopes = [
            "read:devices", "write:devices", "delete:devices",
            "read:metrics", "write:metrics",
            "read:containers", "write:containers",
            "read:backups", "write:backups",
            "read:users", "write:users", "admin:users",
            "admin:all"
        ]
        for scope in v:
            if scope not in valid_scopes:
                raise ValueError(f"Invalid scope: {scope}. Valid scopes: {', '.join(valid_scopes)}")
        return v


class UserAPIKeyResponse(BaseModel):
    """API key response schema"""
    id: UUID = Field(description="API key unique identifier")
    name: str = Field(description="API key name") 
    key_prefix: str = Field(description="API key prefix for identification")
    scopes: List[str] = Field(description="API key scopes")
    is_active: bool = Field(description="Whether API key is active")
    created_at: datetime = Field(description="API key creation timestamp")
    expires_at: Optional[datetime] = Field(description="API key expiration timestamp")
    last_used_at: Optional[datetime] = Field(description="Last usage timestamp")
    usage_count: int = Field(description="Usage count")
    
    class Config:
        from_attributes = True


class UserAPIKeyCreated(UserAPIKeyResponse):
    """API key created response with secret key"""
    api_key: str = Field(description="Full API key (only shown once)")


class UserAPIKeyList(PaginatedResponse[UserAPIKeyResponse]):
    """Paginated list of user API keys"""
    pass


class UserAuditLogResponse(BaseModel):
    """User audit log entry"""
    id: UUID = Field(description="Audit log entry identifier")
    user_id: Optional[UUID] = Field(description="User identifier")
    event_type: str = Field(description="Event type")
    event_category: str = Field(description="Event category")
    description: str = Field(description="Event description")
    ip_address: Optional[str] = Field(description="Request IP address")
    user_agent: Optional[str] = Field(description="User agent string")
    event_metadata: Dict[str, Any] = Field(description="Additional event metadata")
    severity: str = Field(description="Event severity")
    timestamp: datetime = Field(description="Event timestamp")
    
    class Config:
        from_attributes = True


class UserAuditLogList(PaginatedResponse[UserAuditLogResponse]):
    """Paginated list of audit log entries"""
    pass


class UserActivitySummary(BaseModel):
    """User activity summary"""
    user_id: UUID = Field(description="User identifier")
    username: str = Field(description="Username")
    total_logins: int = Field(description="Total number of logins")
    successful_logins: int = Field(description="Successful logins")
    failed_logins: int = Field(description="Failed login attempts")
    last_login_at: Optional[datetime] = Field(description="Last successful login")
    last_failed_login_at: Optional[datetime] = Field(description="Last failed login attempt")
    active_sessions: int = Field(description="Current active sessions")
    api_key_usage: int = Field(description="API key usage count")
    devices_managed: int = Field(description="Number of devices managed")
    recent_activities: List[str] = Field(description="Recent activity descriptions")
    account_created_at: datetime = Field(description="Account creation date")
    
    class Config:
        from_attributes = True


class UserSecuritySettings(BaseModel):
    """User security settings"""
    two_factor_enabled: bool = Field(default=False, description="Two-factor authentication enabled")
    login_notifications: bool = Field(default=True, description="Login notification emails")
    session_timeout_minutes: int = Field(default=480, ge=30, le=10080, description="Session timeout in minutes")
    api_key_expiry_days: int = Field(default=90, ge=1, le=365, description="Default API key expiry in days")
    allowed_ip_ranges: List[str] = Field(default_factory=list, description="Allowed IP address ranges")
    password_expiry_days: Optional[int] = Field(None, ge=30, le=365, description="Password expiry in days")
    
    @field_validator("allowed_ip_ranges")
    @classmethod
    def validate_ip_ranges(cls, v):
        if v:
            from ipaddress import ip_network
            for ip_range in v:
                try:
                    ip_network(ip_range)
                except ValueError:
                    raise ValueError(f"Invalid IP range: {ip_range}")
        return v