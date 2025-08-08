/**
 * Proxy configuration types (SWAG/Nginx)
 */

import { PaginatedResponse } from './common';

export enum ProxyConfigStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error',
  PENDING = 'pending',
  DISABLED = 'disabled'
}

export enum ProxyConfigType {
  SUBDOMAIN = 'subdomain',
  SUBFOLDER = 'subfolder',
  REDIRECT = 'redirect',
  STREAM = 'stream'
}

export enum SSLStatus {
  ENABLED = 'enabled',
  DISABLED = 'disabled',
  PENDING = 'pending',
  ERROR = 'error'
}

// Base proxy configuration
export interface ProxyConfigBase {
  service_name: string;
  domain?: string;
  subdomain?: string;
  path?: string;
  upstream_host: string;
  upstream_port: number;
  config_type: ProxyConfigType;
  ssl_enabled: boolean;
  force_ssl?: boolean;
  websocket_support?: boolean;
  http2_support?: boolean;
  basic_auth_enabled?: boolean;
  basic_auth_users?: string[];
  rate_limiting?: ProxyRateLimit;
  headers?: Record<string, string>;
  custom_locations?: ProxyLocation[];
  access_control?: ProxyAccessControl;
  cache_settings?: ProxyCacheSettings;
}

export interface ProxyConfigCreate extends ProxyConfigBase {
  device_id?: string;
  template?: string;
  auto_generate?: boolean;
}

export interface ProxyConfigUpdate {
  domain?: string;
  subdomain?: string;
  path?: string;
  upstream_host?: string;
  upstream_port?: number;
  ssl_enabled?: boolean;
  force_ssl?: boolean;
  websocket_support?: boolean;
  http2_support?: boolean;
  basic_auth_enabled?: boolean;
  basic_auth_users?: string[];
  rate_limiting?: ProxyRateLimit;
  headers?: Record<string, string>;
  custom_locations?: ProxyLocation[];
  access_control?: ProxyAccessControl;
  cache_settings?: ProxyCacheSettings;
  status?: ProxyConfigStatus;
  enabled?: boolean;
}

export interface ProxyConfigResponse extends ProxyConfigBase {
  id: string;
  device_id: string;
  status: ProxyConfigStatus;
  ssl_status?: SSLStatus;
  ssl_certificate?: SSLCertificateInfo;
  config_file_path?: string;
  config_file_content?: string;
  validation_errors?: string[];
  last_modified?: string;
  last_reloaded?: string;
  enabled: boolean;
  access_logs_enabled?: boolean;
  error_logs_enabled?: boolean;
  created_at: string;
  updated_at: string;
}

export type ProxyConfigList = PaginatedResponse<ProxyConfigResponse>;

// Proxy location configuration
export interface ProxyLocation {
  path: string;
  proxy_pass?: string;
  root?: string;
  index?: string[];
  try_files?: string[];
  return?: string;
  rewrite?: string;
  auth_basic?: string;
  auth_basic_user_file?: string;
  allow?: string[];
  deny?: string[];
  headers?: Record<string, string>;
  proxy_headers?: Record<string, string>;
  fastcgi_pass?: string;
  fastcgi_params?: Record<string, string>;
  uwsgi_pass?: string;
  uwsgi_params?: Record<string, string>;
  limit_except?: string[];
  client_max_body_size?: string;
  proxy_read_timeout?: string;
  proxy_connect_timeout?: string;
  proxy_send_timeout?: string;
  proxy_buffering?: boolean;
  proxy_buffers?: string;
  proxy_buffer_size?: string;
  proxy_busy_buffers_size?: string;
  proxy_temp_file_write_size?: string;
  proxy_max_temp_file_size?: string;
}

// Rate limiting configuration
export interface ProxyRateLimit {
  enabled: boolean;
  requests_per_second?: number;
  requests_per_minute?: number;
  requests_per_hour?: number;
  burst?: number;
  delay?: number;
  zone_name?: string;
  zone_size?: string;
  key?: string; // e.g., $binary_remote_addr, $http_x_forwarded_for
  whitelist?: string[];
  blacklist?: string[];
}

// Access control configuration
export interface ProxyAccessControl {
  allow_ips?: string[];
  deny_ips?: string[];
  allow_countries?: string[];
  deny_countries?: string[];
  require_auth?: boolean;
  auth_type?: 'basic' | 'oauth' | 'jwt' | 'ldap';
  auth_realm?: string;
  auth_users?: ProxyAuthUser[];
  cors_enabled?: boolean;
  cors_origins?: string[];
  cors_methods?: string[];
  cors_headers?: string[];
  cors_credentials?: boolean;
}

export interface ProxyAuthUser {
  username: string;
  password_hash?: string;
  groups?: string[];
  permissions?: string[];
}

// Cache settings
export interface ProxyCacheSettings {
  enabled: boolean;
  cache_methods?: string[];
  cache_key?: string;
  cache_valid?: ProxyCacheValid[];
  cache_bypass?: string[];
  cache_revalidate?: boolean;
  cache_min_uses?: number;
  cache_use_stale?: string[];
  cache_background_update?: boolean;
  cache_lock?: boolean;
  cache_lock_age?: string;
  cache_lock_timeout?: string;
  cache_path?: string;
  cache_zone?: string;
  cache_size?: string;
  cache_inactive?: string;
  cache_max_size?: string;
}

export interface ProxyCacheValid {
  code?: number | string; // e.g., 200, 301, "any"
  time: string; // e.g., "1h", "1d", "1m"
}

// SSL certificate information
export interface SSLCertificateInfo {
  subject: string;
  issuer: string;
  serial_number: string;
  not_before: string;
  not_after: string;
  signature_algorithm: string;
  public_key_algorithm: string;
  san?: string[]; // Subject Alternative Names
  is_wildcard: boolean;
  is_self_signed: boolean;
  days_until_expiry: number;
  is_expired: boolean;
  is_valid: boolean;
  validation_errors?: string[];
}

// Proxy statistics and monitoring
export interface ProxyStatistics {
  config_id: string;
  service_name: string;
  period_start: string;
  period_end: string;
  total_requests: number;
  successful_requests: number;
  error_requests: number;
  average_response_time_ms: number;
  max_response_time_ms: number;
  min_response_time_ms: number;
  percentile_95_response_time_ms: number;
  percentile_99_response_time_ms: number;
  bandwidth_in_bytes: number;
  bandwidth_out_bytes: number;
  unique_visitors: number;
  top_paths: ProxyPathStats[];
  status_codes: Record<number, number>;
  error_types: Record<string, number>;
  cache_stats?: ProxyCacheStats;
  rate_limit_stats?: ProxyRateLimitStats;
}

export interface ProxyPathStats {
  path: string;
  count: number;
  average_response_time_ms: number;
  bandwidth_bytes: number;
}

export interface ProxyCacheStats {
  hits: number;
  misses: number;
  bypasses: number;
  expired: number;
  stale: number;
  updating: number;
  revalidated: number;
  hit_ratio: number;
  bytes_served: number;
  bytes_written: number;
}

export interface ProxyRateLimitStats {
  total_limited: number;
  limited_by_second: number;
  limited_by_minute: number;
  limited_by_hour: number;
  unique_limited_ips: number;
  top_limited_ips: Array<{
    ip: string;
    count: number;
  }>;
}

// Proxy health check
export interface ProxyHealthCheck {
  config_id: string;
  service_name: string;
  upstream_url: string;
  method?: string;
  path?: string;
  interval_seconds?: number;
  timeout_seconds?: number;
  success_threshold?: number;
  failure_threshold?: number;
  expected_status?: number[];
  expected_body?: string;
  headers?: Record<string, string>;
}

export interface ProxyHealthStatus {
  config_id: string;
  service_name: string;
  is_healthy: boolean;
  last_check: string;
  consecutive_successes: number;
  consecutive_failures: number;
  response_time_ms?: number;
  status_code?: number;
  error?: string;
  next_check: string;
}

// Proxy configuration template
export interface ProxyTemplate {
  name: string;
  description?: string;
  template_type: ProxyConfigType;
  variables: ProxyTemplateVariable[];
  base_config: string;
  snippets?: Record<string, string>;
  default_values?: Record<string, any>;
  validation_rules?: ProxyTemplateValidation[];
}

export interface ProxyTemplateVariable {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  required: boolean;
  default?: any;
  description?: string;
  validation?: string; // Regex or validation expression
  options?: any[]; // For enum-like variables
}

export interface ProxyTemplateValidation {
  field: string;
  rule: string;
  message: string;
}

// Proxy configuration generation
export interface ProxyConfigGenerateRequest {
  service_name: string;
  upstream_port: number;
  device_hostname: string;
  domain?: string;
  subdomain?: string;
  template?: string;
  enable_ssl?: boolean;
  enable_websocket?: boolean;
  enable_http2?: boolean;
  custom_settings?: Record<string, any>;
}

export interface ProxyConfigGenerateResponse {
  config_content: string;
  config_type: ProxyConfigType;
  file_name: string;
  validation_warnings?: string[];
  required_actions?: string[];
}

// Bulk operations
export interface ProxyConfigBulkOperation {
  operation: 'enable' | 'disable' | 'reload' | 'validate' | 'delete';
  config_ids?: string[];
  service_names?: string[];
  filters?: ProxyConfigFilter;
}

export interface ProxyConfigFilter {
  status?: ProxyConfigStatus;
  ssl_enabled?: boolean;
  config_type?: ProxyConfigType;
  device_id?: string;
  domain?: string;
  enabled?: boolean;
}

export interface ProxyConfigBulkResponse {
  total_processed: number;
  successful: number;
  failed: number;
  results: Array<{
    config_id: string;
    service_name: string;
    success: boolean;
    error?: string;
  }>;
}

// Nginx configuration validation
export interface ProxyConfigValidation {
  config_id?: string;
  service_name?: string;
  config_content: string;
  is_valid: boolean;
  errors: ProxyValidationError[];
  warnings: ProxyValidationWarning[];
  suggestions: string[];
}

export interface ProxyValidationError {
  line?: number;
  column?: number;
  message: string;
  code?: string;
}

export interface ProxyValidationWarning {
  line?: number;
  message: string;
  suggestion?: string;
}

// Proxy reload and status
export interface ProxyReloadRequest {
  config_ids?: string[];
  service_names?: string[];
  force?: boolean;
  validate_first?: boolean;
}

export interface ProxyReloadResponse {
  success: boolean;
  reloaded_configs: string[];
  failed_configs: Array<{
    config_id: string;
    service_name: string;
    error: string;
  }>;
  nginx_status: string;
  reload_time: string;
}

export interface NginxStatus {
  is_running: boolean;
  pid?: number;
  version?: string;
  uptime_seconds?: number;
  config_test_passed: boolean;
  active_connections?: number;
  total_accepts?: number;
  total_handled?: number;
  total_requests?: number;
  reading?: number;
  writing?: number;
  waiting?: number;
  worker_processes?: number;
  worker_connections?: number;
  error_log_path?: string;
  access_log_path?: string;
  config_path?: string;
  last_reload?: string;
}

// Proxy configuration summary
export interface ProxyConfigSummary {
  total_configs: number;
  active_configs: number;
  inactive_configs: number;
  error_configs: number;
  ssl_enabled_configs: number;
  configs_by_type: Record<ProxyConfigType, number>;
  configs_by_device: Array<{
    device_id: string;
    hostname?: string;
    count: number;
  }>;
  domains: string[];
  subdomains: string[];
  ssl_certificates_expiring_soon: Array<{
    config_id: string;
    service_name: string;
    domain: string;
    expires_at: string;
    days_remaining: number;
  }>;
  recent_changes: Array<{
    config_id: string;
    service_name: string;
    action: string;
    timestamp: string;
  }>;
  health_summary: {
    healthy: number;
    unhealthy: number;
    unchecked: number;
  };
}