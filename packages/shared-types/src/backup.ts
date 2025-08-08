/**
 * Backup-related types
 */

import { PaginatedResponse } from './common';

export type BackupType = 
  | 'system'
  | 'database'
  | 'container'
  | 'zfs'
  | 'file'
  | 'config'
  | 'docker-volume'
  | 'vm'
  | 'snapshot'
  | 'incremental'
  | 'full';

export type BackupStatus = 
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

export interface BackupStatusBase {
  backup_type: BackupType;
  backup_name: string;
  source_path?: string;
  destination_path?: string;
  status: BackupStatus;
  start_time?: string;
  end_time?: string;
  duration_seconds?: number;
  size_bytes?: number;
  compressed_size_bytes?: number;
  files_count?: number;
  success_count?: number;
  error_count?: number;
  warning_count?: number;
  error_message?: string;
  extra_metadata: Record<string, any>;
}

export interface BackupStatusCreate extends BackupStatusBase {
  device_id: string;
}

export interface BackupStatusUpdate {
  status?: BackupStatus;
  end_time?: string;
  duration_seconds?: number;
  size_bytes?: number;
  compressed_size_bytes?: number;
  files_count?: number;
  success_count?: number;
  error_count?: number;
  warning_count?: number;
  error_message?: string;
  extra_metadata?: Record<string, any>;
}

export interface BackupStatusResponse extends BackupStatusBase {
  id: string;
  device_id: string;
  created_at: string;
  
  // Computed fields
  hostname?: string;
  compression_ratio?: number;
  success_rate?: number;
  throughput_mbps?: number;
}

export type BackupStatusList = PaginatedResponse<BackupStatusResponse>;

export interface BackupSchedule {
  schedule_id: string;
  schedule_name: string;
  device_id: string;
  backup_type: BackupType;
  source_paths: string[];
  destination_path: string;
  cron_expression: string;
  retention_days: number;
  compression_enabled: boolean;
  encryption_enabled: boolean;
  exclude_patterns: string[];
  pre_backup_commands: string[];
  post_backup_commands: string[];
  notification_emails: string[];
  is_active: boolean;
  created_at: string;
  last_run?: string;
  next_run?: string;
}

export interface BackupPolicy {
  policy_id: string;
  policy_name: string;
  description?: string;
  device_ids: string[];
  backup_types: BackupType[];
  
  // Retention settings
  daily_retention: number;
  weekly_retention: number;
  monthly_retention: number;
  yearly_retention: number;
  
  // Performance settings
  max_concurrent_backups: number;
  bandwidth_limit_mbps?: number;
  cpu_limit_percent?: number;
  
  // Storage settings
  compression_level: number;
  encryption_enabled: boolean;
  deduplication_enabled: boolean;
  
  // Validation
  verify_after_backup: boolean;
  test_restore_frequency_days?: number;
  
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BackupRepository {
  repository_id: string;
  repository_name: string;
  repository_type: 'local' | 's3' | 'sftp' | 'nfs' | 'smb' | 'webdav';
  repository_url: string;
  
  // Capacity
  total_capacity_bytes?: number;
  used_capacity_bytes?: number;
  available_capacity_bytes?: number;
  
  // Performance
  read_bandwidth_mbps?: number;
  write_bandwidth_mbps?: number;
  
  // Authentication
  auth_type?: 'none' | 'password' | 'key' | 'token';
  
  // Status
  is_online: boolean;
  last_check: string;
  error_message?: string;
  
  created_at: string;
  updated_at: string;
}

export interface BackupJob {
  job_id: string;
  schedule_id?: string;
  device_id: string;
  backup_type: BackupType;
  source_paths: string[];
  destination_path: string;
  
  // Job status
  status: BackupStatus;
  progress_percent?: number;
  current_file?: string;
  
  // Statistics
  files_processed: number;
  files_total: number;
  bytes_processed: number;
  bytes_total: number;
  
  // Timing
  started_at: string;
  estimated_completion?: string;
  completed_at?: string;
  
  // Results
  success_count: number;
  error_count: number;
  warning_count: number;
  error_messages: string[];
  warning_messages: string[];
}

export interface BackupRestore {
  restore_id: string;
  backup_id: string;
  device_id: string;
  
  // Restore target
  restore_path: string;
  overwrite_existing: boolean;
  preserve_permissions: boolean;
  preserve_timestamps: boolean;
  
  // Selection
  selected_files?: string[];
  exclude_patterns?: string[];
  
  // Status
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress_percent?: number;
  
  // Statistics
  files_restored: number;
  bytes_restored: number;
  errors: string[];
  
  // Timing
  started_at: string;
  completed_at?: string;
}

export interface BackupValidation {
  validation_id: string;
  backup_id: string;
  
  // Validation type
  validation_type: 'checksum' | 'restore_test' | 'integrity' | 'full';
  
  // Results
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  
  // Statistics
  files_checked: number;
  files_corrupted: number;
  bytes_checked: number;
  
  // Timing
  started_at: string;
  completed_at: string;
  duration_seconds: number;
}

export interface BackupStatistics {
  device_id?: string;
  period_start: string;
  period_end: string;
  
  // Backup counts
  total_backups: number;
  successful_backups: number;
  failed_backups: number;
  
  // Data volumes
  total_data_backed_up_bytes: number;
  total_data_compressed_bytes: number;
  average_compression_ratio: number;
  
  // Performance
  average_backup_duration_seconds: number;
  average_throughput_mbps: number;
  
  // Breakdown by type
  backups_by_type: Record<BackupType, number>;
  data_by_type: Record<BackupType, number>;
  
  // Trends
  daily_backup_counts: number[];
  daily_data_volumes: number[];
}

export interface BackupAlert {
  alert_id: string;
  device_id: string;
  backup_id?: string;
  
  alert_type: 'failure' | 'warning' | 'success' | 'quota' | 'retention';
  severity: 'info' | 'warning' | 'error' | 'critical';
  
  title: string;
  message: string;
  details?: Record<string, any>;
  
  triggered_at: string;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
}