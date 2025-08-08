/**
 * System updates types
 */

import { PaginatedResponse } from './common';

export type PackageType = 
  | 'system'
  | 'container'
  | 'snap'
  | 'flatpak'
  | 'pip'
  | 'npm'
  | 'apt'
  | 'yum'
  | 'dnf'
  | 'zypper'
  | 'pacman'
  | 'homebrew'
  | 'custom';

export type UpdatePriority = 'critical' | 'high' | 'normal' | 'low';

export type UpdateStatus = 
  | 'available'
  | 'pending'
  | 'installed'
  | 'failed'
  | 'skipped'
  | 'ignored';

export interface SystemUpdateBase {
  package_type: PackageType;
  package_name: string;
  current_version?: string;
  available_version?: string;
  update_priority: UpdatePriority;
  security_update: boolean;
  release_date?: string;
  description?: string;
  changelog?: string;
  update_status: UpdateStatus;
  last_checked: string;
  extra_metadata: Record<string, any>;
}

export interface SystemUpdateCreate extends SystemUpdateBase {
  device_id: string;
}

export interface SystemUpdateUpdate {
  current_version?: string;
  available_version?: string;
  update_priority?: UpdatePriority;
  security_update?: boolean;
  description?: string;
  changelog?: string;
  update_status?: UpdateStatus;
  extra_metadata?: Record<string, any>;
}

export interface SystemUpdateResponse extends SystemUpdateBase {
  id: string;
  device_id: string;
  
  // Computed fields
  hostname?: string;
  days_since_release?: number;
  update_size_mb?: number;
  requires_reboot?: boolean;
  has_dependencies?: boolean;
}

export type SystemUpdateList = PaginatedResponse<SystemUpdateResponse>;

export interface UpdateSummary {
  device_id: string;
  hostname: string;
  total_updates: number;
  security_updates: number;
  critical_updates: number;
  high_priority_updates: number;
  updates_by_type: Record<PackageType, number>;
  pending_reboot: boolean;
  last_update_check: string;
  last_update_installed?: string;
  update_policy?: string;
  auto_updates_enabled: boolean;
}

export interface UpdateHealthOverview {
  total_devices: number;
  devices_with_updates: number;
  devices_up_to_date: number;
  total_available_updates: number;
  total_security_updates: number;
  total_critical_updates: number;
  devices_needing_reboot: number;
  updates_by_package_type: Record<PackageType, number>;
  devices_by_update_status: Record<UpdateStatus, number>;
  oldest_pending_update?: string;
  most_common_updates: Array<{
    package_name: string;
    count: number;
    version: string;
  }>;
  timestamp: string;
}

export interface UpdatePolicy {
  policy_id: string;
  policy_name: string;
  description?: string;
  
  // Scheduling
  auto_update: boolean;
  update_schedule?: string; // Cron expression
  maintenance_window?: {
    start_time: string;
    end_time: string;
    days_of_week: number[];
  };
  
  // Update selection
  include_security_updates: boolean;
  include_critical_updates: boolean;
  include_normal_updates: boolean;
  exclude_packages?: string[];
  include_packages?: string[];
  
  // Behavior
  auto_reboot: boolean;
  reboot_delay_minutes?: number;
  notify_before_update: boolean;
  notify_after_update: boolean;
  
  // Rollback
  create_snapshot_before_update: boolean;
  auto_rollback_on_failure: boolean;
  
  // Assignment
  device_ids: string[];
  device_groups?: string[];
  
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UpdateInstallation {
  installation_id: string;
  device_id: string;
  
  // Updates to install
  update_ids: string[];
  package_names: string[];
  
  // Status
  status: 'pending' | 'downloading' | 'installing' | 'completed' | 'failed' | 'cancelled';
  progress_percent?: number;
  current_package?: string;
  
  // Results
  packages_installed: string[];
  packages_failed: string[];
  error_messages: string[];
  
  // Timing
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  
  // System impact
  reboot_required: boolean;
  services_restarted: string[];
  
  // Rollback info
  snapshot_id?: string;
  rollback_available: boolean;
}

export interface UpdateHistory {
  history_id: string;
  device_id: string;
  package_name: string;
  package_type: PackageType;
  
  // Version info
  previous_version: string;
  installed_version: string;
  
  // Installation details
  installed_at: string;
  installed_by?: string;
  installation_method: 'manual' | 'auto' | 'policy';
  
  // Results
  success: boolean;
  error_message?: string;
  rollback_performed: boolean;
}

export interface UpdateNotification {
  notification_id: string;
  device_id: string;
  
  // Notification type
  type: 'new_updates' | 'security_alert' | 'reboot_required' | 'update_failed' | 'update_completed';
  
  // Content
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  
  // Updates involved
  update_count?: number;
  security_update_count?: number;
  package_names?: string[];
  
  // Status
  created_at: string;
  read: boolean;
  acknowledged: boolean;
  action_required: boolean;
}

export interface UpdateDependency {
  package_name: string;
  required_version?: string;
  current_version?: string;
  is_satisfied: boolean;
  is_available: boolean;
}

export interface UpdateConflict {
  package_name: string;
  conflicting_package: string;
  conflict_type: 'version' | 'file' | 'dependency';
  resolution?: 'upgrade' | 'downgrade' | 'remove' | 'skip';
}

export interface UpdateRollback {
  rollback_id: string;
  device_id: string;
  installation_id: string;
  
  // Rollback details
  packages_to_rollback: string[];
  snapshot_id?: string;
  
  // Status
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percent?: number;
  
  // Results
  packages_rolled_back: string[];
  packages_failed: string[];
  error_messages: string[];
  
  // Timing
  initiated_at: string;
  completed_at?: string;
}