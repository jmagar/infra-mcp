/**
 * Common types and interfaces used across the application
 */

// Enums
export enum DeviceStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  UNKNOWN = 'unknown',
  MAINTENANCE = 'maintenance'
}

export enum LogLevel {
  EMERGENCY = 'emergency',
  ALERT = 'alert',
  CRITICAL = 'critical',
  ERROR = 'error',
  WARNING = 'warning',
  NOTICE = 'notice',
  INFO = 'info',
  DEBUG = 'debug'
}

export enum HealthStatus {
  HEALTHY = 'healthy',
  WARNING = 'warning',
  CRITICAL = 'critical',
  UNKNOWN = 'unknown'
}

export enum TimeSeriesAggregation {
  AVG = 'avg',
  MIN = 'min',
  MAX = 'max',
  SUM = 'sum',
  COUNT = 'count',
  FIRST = 'first',
  LAST = 'last'
}

export enum TimeSeriesInterval {
  MINUTE = '1m',
  FIVE_MINUTES = '5m',
  FIFTEEN_MINUTES = '15m',
  HOUR = '1h',
  SIX_HOURS = '6h',
  DAY = '1d',
  WEEK = '1w'
}

// Base interfaces
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface TimeRangeParams {
  start_time?: string; // ISO 8601
  end_time?: string; // ISO 8601
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface HealthCheckResponse {
  status: string;
  version: string;
  environment: string;
  database: Record<string, any>;
  services: Record<string, string>;
  timestamp: string;
}

export interface DeviceFilter {
  hostname?: string;
  device_type?: string;
  status?: DeviceStatus;
  monitoring_enabled?: boolean;
  tags?: Record<string, string>;
}

export interface AggregationParams {
  interval: TimeSeriesInterval;
  aggregation: TimeSeriesAggregation;
}

export interface MetricFilter {
  device_ids?: string[];
  metric_names?: string[];
  threshold_min?: number;
  threshold_max?: number;
}

export interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface BulkOperationResponse {
  total_processed: number;
  successful: number;
  failed: number;
  errors: string[];
  duration_ms: number;
}

export interface StatusResponse {
  status: string;
  message?: string;
  timestamp: string;
}

export interface CreatedResponse<T> {
  id: string;
  resource_type: string;
  data?: T;
  message: string;
  timestamp: string;
}

export interface UpdatedResponse<T> {
  id: string;
  resource_type: string;
  data?: T;
  changes: Record<string, any>;
  message: string;
  timestamp: string;
}

export interface DeletedResponse {
  id: string;
  resource_type: string;
  message: string;
  timestamp: string;
}

export interface HealthMetrics {
  cpu_usage_percent?: number;
  memory_usage_percent?: number;
  disk_usage_percent?: number;
  network_latency_ms?: number;
  active_connections?: number;
  error_rate_percent?: number;
  uptime_seconds?: number;
  last_health_check?: string;
}

export interface OperationResult<T> {
  success: boolean;
  operation_id?: string;
  operation_type: string;
  result?: T;
  error_message?: string;
  warnings: string[];
  execution_time_ms?: number;
  timestamp: string;
}

export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset_time: string;
  window_seconds: number;
}

export interface SystemInfo {
  hostname: string;
  platform: string;
  architecture: string;
  python_version: string;
  app_version: string;
  startup_time: string;
  current_time: string;
}