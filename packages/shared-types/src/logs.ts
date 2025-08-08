/**
 * System logs types
 */

import { LogLevel, PaginatedResponse, TimeRangeParams } from './common';

export type LogSource = 
  | 'systemd'
  | 'syslog'
  | 'kernel'
  | 'application'
  | 'security'
  | 'cron'
  | 'auth'
  | 'mail'
  | 'daemon'
  | 'docker'
  | 'nginx'
  | 'ssh'
  | string; // Allow custom sources

export type LogFacility = 
  | 'kern'
  | 'user'
  | 'mail'
  | 'daemon'
  | 'auth'
  | 'syslog'
  | 'lpr'
  | 'news'
  | 'uucp'
  | 'cron'
  | 'authpriv'
  | 'ftp'
  | 'local0'
  | 'local1'
  | 'local2'
  | 'local3'
  | 'local4'
  | 'local5'
  | 'local6'
  | 'local7';

export interface SystemLogBase {
  service_name?: string;
  log_level: LogLevel;
  source: LogSource;
  process_id?: number;
  user_name?: string;
  facility?: LogFacility;
  message: string;
  raw_message?: string;
  extra_metadata: Record<string, any>;
}

export interface SystemLogCreate extends SystemLogBase {
  device_id: string;
}

export interface SystemLogResponse extends SystemLogBase {
  time: string;
  device_id: string;
  hostname?: string;
  age_minutes?: number;
}

export type SystemLogList = PaginatedResponse<SystemLogResponse>;

export interface SystemLogQuery extends TimeRangeParams {
  device_ids?: string[];
  services?: string[];
  log_levels?: LogLevel[];
  sources?: LogSource[];
  search?: string;
  facilities?: LogFacility[];
  process_ids?: number[];
  limit?: number;
}

export interface SystemLogSummary {
  device_id: string;
  hostname?: string;
  total_logs: number;
  logs_by_level: Record<LogLevel, number>;
  logs_by_source: Record<LogSource, number>;
  logs_by_service: Record<string, number>;
  
  // Time-based metrics
  logs_per_hour: number[];
  error_rate: number;
  warning_rate: number;
  
  // Top entries
  top_errors: Array<{
    message: string;
    count: number;
    last_seen: string;
  }>;
  top_warnings: Array<{
    message: string;
    count: number;
    last_seen: string;
  }>;
  top_services: Array<{
    service: string;
    count: number;
  }>;
  
  // Metadata
  period_start: string;
  period_end: string;
  analysis_timestamp: string;
}

export interface LogPattern {
  pattern: string;
  description: string;
  severity: LogLevel;
  count: number;
  first_seen: string;
  last_seen: string;
  affected_devices: string[];
  sample_messages: string[];
}

export interface LogStream {
  device_id?: string;
  service?: string;
  log_level?: LogLevel;
  follow: boolean;
  tail?: number;
  filters?: string[];
}

export interface LogExport {
  format: 'json' | 'csv' | 'txt';
  filters: SystemLogQuery;
  include_metadata: boolean;
  compress: boolean;
}