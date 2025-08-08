/**
 * User and authentication types
 */

export enum UserRole {
  ADMIN = 'admin',
  OPERATOR = 'operator',
  VIEWER = 'viewer',
  GUEST = 'guest'
}

export enum AuthProvider {
  LOCAL = 'local',
  LDAP = 'ldap',
  OAUTH = 'oauth',
  SAML = 'saml'
}

export interface UserBase {
  username: string;
  email: string;
  full_name?: string;
  role: UserRole;
  is_active: boolean;
  is_superuser?: boolean;
  auth_provider?: AuthProvider;
  avatar_url?: string;
  preferences?: UserPreferences;
  permissions?: string[];
  groups?: string[];
}

export interface UserCreate extends UserBase {
  password?: string; // For local auth
  external_id?: string; // For external auth providers
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  avatar_url?: string;
  preferences?: UserPreferences;
  permissions?: string[];
  groups?: string[];
  password?: string;
}

export interface UserResponse extends UserBase {
  id: string;
  last_login?: string;
  created_at: string;
  updated_at: string;
  session_count?: number;
  api_key_count?: number;
}

export interface UserPreferences {
  theme?: 'light' | 'dark' | 'auto';
  language?: string;
  timezone?: string;
  date_format?: string;
  time_format?: '12h' | '24h';
  notifications?: NotificationPreferences;
  dashboard?: DashboardPreferences;
  default_device_view?: 'grid' | 'list' | 'map';
  auto_refresh_interval?: number; // seconds
  compact_mode?: boolean;
}

export interface NotificationPreferences {
  email_enabled?: boolean;
  push_enabled?: boolean;
  alert_levels?: string[];
  device_status_changes?: boolean;
  container_events?: boolean;
  system_alerts?: boolean;
  maintenance_reminders?: boolean;
  security_events?: boolean;
}

export interface DashboardPreferences {
  default_view?: string;
  widgets?: DashboardWidget[];
  refresh_interval?: number;
  show_alerts?: boolean;
  show_metrics?: boolean;
  collapsed_sections?: string[];
}

export interface DashboardWidget {
  id: string;
  type: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  config?: Record<string, any>;
}

// Authentication
export interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
  mfa_code?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
  permissions?: string[];
  session_id?: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
}

export interface LogoutRequest {
  everywhere?: boolean; // Logout from all sessions
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
}

// API Keys
export interface APIKey {
  id: string;
  name: string;
  key_prefix: string; // First few characters for identification
  user_id: string;
  permissions?: string[];
  expires_at?: string;
  last_used?: string;
  created_at: string;
  is_active: boolean;
}

export interface APIKeyCreate {
  name: string;
  permissions?: string[];
  expires_in_days?: number;
}

export interface APIKeyResponse {
  id: string;
  name: string;
  key: string; // Full key, only shown once
  expires_at?: string;
  permissions?: string[];
}

// Sessions
export interface UserSession {
  id: string;
  user_id: string;
  user_agent?: string;
  ip_address?: string;
  location?: string;
  device_type?: string;
  browser?: string;
  os?: string;
  created_at: string;
  last_activity: string;
  expires_at: string;
  is_current: boolean;
}

export interface SessionList {
  sessions: UserSession[];
  total_count: number;
  active_count: number;
}

// Audit Log
export interface AuditLog {
  id: string;
  user_id?: string;
  username?: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  status: 'success' | 'failure';
  error_message?: string;
  timestamp: string;
}

export interface AuditLogFilter {
  user_id?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string;
  status?: 'success' | 'failure';
  start_time?: string;
  end_time?: string;
}

// Permissions
export interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  description?: string;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  permissions: Permission[];
  is_system?: boolean;
  created_at: string;
  updated_at: string;
}

export interface Group {
  id: string;
  name: string;
  description?: string;
  members: string[]; // User IDs
  permissions?: string[];
  created_at: string;
  updated_at: string;
}

// Multi-factor authentication
export interface MFASetupRequest {
  type: 'totp' | 'sms' | 'email';
  phone_number?: string; // For SMS
}

export interface MFASetupResponse {
  type: string;
  secret?: string; // For TOTP
  qr_code?: string; // Base64 encoded QR code for TOTP
  backup_codes?: string[];
  verification_required: boolean;
}

export interface MFAVerifyRequest {
  code: string;
  type?: 'totp' | 'sms' | 'email' | 'backup';
}

export interface MFAStatus {
  enabled: boolean;
  type?: 'totp' | 'sms' | 'email';
  backup_codes_remaining?: number;
  last_used?: string;
}

// OAuth/SSO
export interface OAuthProvider {
  name: string;
  display_name: string;
  icon_url?: string;
  authorization_url: string;
  enabled: boolean;
}

export interface OAuthLoginRequest {
  provider: string;
  code: string;
  state: string;
  redirect_uri: string;
}

// User activity
export interface UserActivity {
  user_id: string;
  username: string;
  last_active: string;
  current_status: 'online' | 'away' | 'offline';
  current_page?: string;
  session_count: number;
  recent_actions: RecentAction[];
}

export interface RecentAction {
  action: string;
  resource?: string;
  timestamp: string;
  details?: string;
}

// Notifications
export interface UserNotification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  read: boolean;
  action_url?: string;
  action_label?: string;
  metadata?: Record<string, any>;
  created_at: string;
  read_at?: string;
  expires_at?: string;
}

export interface NotificationList {
  notifications: UserNotification[];
  total_count: number;
  unread_count: number;
}

// User management
export interface UserInvite {
  email: string;
  role: UserRole;
  groups?: string[];
  expires_in_days?: number;
  send_email?: boolean;
}

export interface UserInviteResponse {
  id: string;
  email: string;
  token: string;
  expires_at: string;
  invite_url: string;
}

export interface UserBulkOperation {
  operation: 'activate' | 'deactivate' | 'delete' | 'change_role';
  user_ids: string[];
  role?: UserRole; // For change_role
}

export interface UserBulkOperationResponse {
  total_processed: number;
  successful: number;
  failed: number;
  results: Array<{
    user_id: string;
    success: boolean;
    error?: string;
  }>;
}