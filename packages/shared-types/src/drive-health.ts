/**
 * Drive health monitoring types
 */

import { HealthStatus, PaginatedResponse, TimeRangeParams } from './common';

export enum DriveType {
  SSD = 'ssd',
  HDD = 'hdd',
  NVME = 'nvme',
  UNKNOWN = 'unknown'
}

export enum SmartStatus {
  PASSED = 'PASSED',
  FAILED = 'FAILED',
  UNKNOWN = 'UNKNOWN'
}

export interface DriveHealthBase {
  device_id: string;
  drive_name: string;
  
  // Drive information
  drive_type?: DriveType;
  model?: string;
  serial_number?: string;
  capacity_bytes?: number;
  
  // Health metrics
  temperature_celsius?: number;
  power_on_hours?: number;
  total_lbas_written?: number;
  total_lbas_read?: number;
  reallocated_sectors?: number;
  pending_sectors?: number;
  uncorrectable_errors?: number;
  
  // Status indicators
  smart_status?: SmartStatus;
  smart_attributes: Record<string, any>;
  health_status: HealthStatus;
}

export interface DriveHealthCreate extends DriveHealthBase {
  time?: string;
}

export interface DriveHealthResponse extends DriveHealthBase {
  time: string;
}

export type DriveHealthList = PaginatedResponse<DriveHealthResponse>;

export interface DriveHealthQuery extends TimeRangeParams {
  device_ids?: string[];
  drive_names?: string[];
  drive_types?: DriveType[];
  health_status?: HealthStatus[];
  smart_status?: SmartStatus[];
  min_temperature?: number;
  max_temperature?: number;
}

export interface DriveHealthSummary {
  device_id: string;
  hostname?: string;
  drive_name: string;
  drive_type?: DriveType;
  model?: string;
  capacity_gb?: number;
  
  // Current status
  health_status: HealthStatus;
  smart_status?: SmartStatus;
  current_temperature?: number;
  
  // Wear indicators
  power_on_hours?: number;
  reallocated_sectors?: number;
  pending_sectors?: number;
  uncorrectable_errors?: number;
  
  // Trends (24-hour)
  temperature_trend: Record<string, number>;
  wear_trend: Record<string, number>;
  
  // Alerts
  active_alerts: string[];
  
  // Metadata
  last_updated: string;
  data_points_24h: number;
}

export interface DriveHealthTrends {
  device_id: string;
  drive_name: string;
  
  // Weekly trends
  power_on_hours_weekly: number[];
  temperature_weekly: number[];
  lbas_written_weekly: number[];
  lbas_read_weekly: number[];
  
  // Health status history
  health_status_history: Array<{
    timestamp: string;
    status: HealthStatus;
    reason?: string;
  }>;
  smart_status_history: Array<{
    timestamp: string;
    status: SmartStatus;
    details?: string;
  }>;
  
  // Predictive indicators
  estimated_remaining_life?: number;
  wear_leveling_indicator?: number;
  
  // Metadata
  trend_period_days: number;
  last_analysis: string;
}

export interface DriveHealthAlert {
  device_id: string;
  hostname: string;
  drive_name: string;
  alert_type: 'temperature' | 'smart' | 'wear' | 'error' | 'capacity';
  severity: 'warning' | 'critical';
  message: string;
  current_value?: number;
  threshold_value?: number;
  triggered_at: string;
  acknowledged: boolean;
}

export interface DriveHealthThresholds {
  // Temperature thresholds
  temperature_warning: number;
  temperature_critical: number;
  
  // Sector thresholds
  reallocated_sectors_warning: number;
  reallocated_sectors_critical: number;
  pending_sectors_warning: number;
  pending_sectors_critical: number;
  
  // Error thresholds
  uncorrectable_errors_warning: number;
  uncorrectable_errors_critical: number;
  
  // Wear thresholds (for SSDs)
  wear_leveling_warning: number;
  wear_leveling_critical: number;
}

export interface DriveInventory {
  device_id: string;
  hostname: string;
  drives: Array<{
    name: string;
    type: DriveType;
    model: string;
    serial: string;
    capacity_bytes: number;
    health: HealthStatus;
    smart: SmartStatus;
  }>;
  total_capacity_bytes: number;
  total_drives: number;
  drives_by_type: Record<DriveType, number>;
  drives_by_health: Record<HealthStatus, number>;
  last_inventory: string;
}

export interface SmartAttribute {
  id: number;
  name: string;
  value: number;
  worst: number;
  threshold: number;
  raw_value: number;
  when_failed?: string;
  flags: string;
}

export interface SmartData {
  device_id: string;
  drive_name: string;
  smart_status: SmartStatus;
  model_name: string;
  serial_number: string;
  capacity: number;
  attributes: SmartAttribute[];
  self_test_log: Array<{
    num: number;
    type: string;
    status: string;
    remaining: number;
    lifetime_hours: number;
    lba_first_error?: number;
  }>;
  error_log: Array<{
    error_num: number;
    lifetime_hours: number;
    state: string;
    type: string;
    details: string;
  }>;
  collected_at: string;
}