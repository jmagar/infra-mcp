/**
 * Device-related types and interfaces
 */

import { DeviceStatus, PaginatedResponse } from './common';

export interface DeviceBase {
  hostname: string;
  ip_address?: string;
  ssh_port?: number;
  ssh_username?: string;
  device_type: string;
  description?: string;
  location?: string;
  tags: Record<string, any>;
  monitoring_enabled: boolean;
}

export interface DeviceCreate extends DeviceBase {}

export interface DeviceUpdate {
  hostname?: string;
  ip_address?: string;
  ssh_port?: number;
  ssh_username?: string;
  device_type?: string;
  description?: string;
  location?: string;
  tags?: Record<string, any>;
  monitoring_enabled?: boolean;
  status?: DeviceStatus;
}

export interface DeviceResponse extends DeviceBase {
  id: string;
  status: DeviceStatus;
  last_seen?: string;
  created_at: string;
  updated_at: string;
}

export type DeviceList = PaginatedResponse<DeviceResponse>;

export interface DeviceSummary {
  id: string;
  hostname: string;
  ip_address?: string;
  device_type: string;
  status: DeviceStatus;
  monitoring_enabled: boolean;
  last_seen?: string;
}

export interface DeviceHealth {
  device_id: string;
  hostname: string;
  status: DeviceStatus;
  last_seen?: string;
  connectivity_status: string;
  system_health?: string;
  cpu_usage?: number;
  memory_usage?: number;
  disk_usage?: number;
  uptime_hours?: number;
  active_containers?: number;
  alerts_count?: number;
}

export interface DeviceHealthList {
  devices: DeviceHealth[];
  summary: Record<string, number>;
  timestamp: string;
}

export interface DeviceConnectionTest {
  device_id: string;
  hostname: string;
  ip_address?: string;
  ssh_port?: number;
  connection_status: string;
  response_time_ms?: number;
  error_message?: string;
  test_timestamp: string;
}

export interface DeviceMetricsOverview {
  device_id: string;
  hostname: string;
  current_metrics: Record<string, any>;
  trend_data: Record<string, number[]>;
  alerts: string[];
  last_updated: string;
}

export interface DeviceImportRequest {
  ssh_config_path: string;
  dry_run?: boolean;
  update_existing?: boolean;
  default_device_type?: string;
  default_monitoring?: boolean;
  tag_prefix?: string;
}

export interface DeviceImportResult {
  hostname: string;
  action: 'created' | 'updated' | 'skipped' | 'error';
  device_id?: string;
  error_message?: string;
  changes: Record<string, any>;
}

export interface DeviceImportResponse {
  total_hosts_found: number;
  results: DeviceImportResult[];
  summary: Record<string, number>;
  dry_run: boolean;
  import_timestamp: string;
}