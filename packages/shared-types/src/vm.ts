/**
 * Virtual Machine types
 */

import { PaginatedResponse } from './common';

export type HypervisorType = 
  | 'kvm'
  | 'qemu'
  | 'xen'
  | 'vmware'
  | 'virtualbox'
  | 'hyper-v'
  | 'bhyve'
  | 'lxc'
  | 'docker'
  | 'openvz';

export type VMStatus = 
  | 'running'
  | 'paused'
  | 'shutdown'
  | 'shutoff'
  | 'crashed'
  | 'dying'
  | 'pmsuspended'
  | 'starting'
  | 'stopping';

export interface VMStatusBase {
  vm_id: string;
  vm_name: string;
  hypervisor: HypervisorType;
  status: VMStatus;
  vcpus?: number;
  memory_mb?: number;
  memory_usage_mb?: number;
  cpu_usage_percent?: number;
  disk_usage_bytes?: number;
  network_bytes_sent?: number;
  network_bytes_recv?: number;
  uptime_seconds?: number;
  boot_time?: string;
  config: Record<string, any>;
}

export interface VMStatusCreate extends VMStatusBase {
  device_id: string;
}

export interface VMStatusResponse extends VMStatusBase {
  time: string;
  device_id: string;
  
  // Computed fields
  memory_usage_percent?: number;
  uptime_hours?: number;
  cpu_cores_used?: number;
}

export type VMStatusList = PaginatedResponse<VMStatusResponse>;

export interface VMSummary {
  device_id: string;
  vm_id: string;
  vm_name: string;
  hypervisor: HypervisorType;
  status: VMStatus;
  vcpus?: number;
  memory_mb?: number;
  cpu_usage_percent?: number;
  memory_usage_percent?: number;
  uptime_hours?: number;
  network_active: boolean;
  health_status: string;
  last_updated: string;
}

export interface VMHealthOverview {
  total_vms: number;
  running_vms: number;
  paused_vms: number;
  shutdown_vms: number;
  crashed_vms: number;
  total_vcpus: number;
  total_memory_gb: number;
  average_cpu_usage: number;
  average_memory_usage: number;
  vms_by_hypervisor: Record<HypervisorType, number>;
  vms_by_device: Record<string, number>;
  high_resource_vms: string[];
  problematic_vms: string[];
  timestamp: string;
}

export interface VMSnapshot {
  snapshot_id: string;
  vm_id: string;
  snapshot_name: string;
  description?: string;
  state: 'disk-only' | 'memory' | 'full';
  created_at: string;
  size_bytes: number;
  parent_snapshot?: string;
}

export interface VMBackup {
  backup_id: string;
  vm_id: string;
  backup_type: 'full' | 'incremental' | 'differential';
  backup_path: string;
  size_bytes: number;
  compression_ratio?: number;
  created_at: string;
  completed_at?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  error_message?: string;
}

export interface VMMigration {
  migration_id: string;
  vm_id: string;
  source_device: string;
  target_device: string;
  migration_type: 'live' | 'offline' | 'storage';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress_percent?: number;
  started_at: string;
  completed_at?: string;
  downtime_ms?: number;
  error_message?: string;
}

export interface VMResourceUsage {
  vm_id: string;
  timestamp: string;
  
  // CPU metrics
  cpu_usage_percent: number;
  cpu_steal_percent?: number;
  cpu_wait_percent?: number;
  
  // Memory metrics
  memory_used_mb: number;
  memory_available_mb: number;
  memory_cache_mb?: number;
  memory_swap_mb?: number;
  
  // Disk metrics
  disk_read_bytes: number;
  disk_write_bytes: number;
  disk_iops_read: number;
  disk_iops_write: number;
  
  // Network metrics
  network_rx_bytes: number;
  network_tx_bytes: number;
  network_rx_packets: number;
  network_tx_packets: number;
  network_rx_errors: number;
  network_tx_errors: number;
}

export interface VMConsoleAccess {
  vm_id: string;
  console_type: 'vnc' | 'spice' | 'rdp' | 'serial' | 'web';
  connection_url?: string;
  host?: string;
  port?: number;
  password?: string;
  token?: string;
  expires_at?: string;
}

export interface VMAction {
  vm_id: string;
  action: 'start' | 'stop' | 'restart' | 'pause' | 'resume' | 'reset' | 'destroy';
  force?: boolean;
  timeout_seconds?: number;
}

export interface VMActionResult {
  vm_id: string;
  action: string;
  success: boolean;
  new_status?: VMStatus;
  message?: string;
  error?: string;
}

export interface VMTemplate {
  template_id: string;
  template_name: string;
  description?: string;
  hypervisor: HypervisorType;
  os_type: string;
  os_version?: string;
  vcpus: number;
  memory_mb: number;
  disk_gb: number;
  network_interfaces: number;
  created_at: string;
  updated_at: string;
}

export interface VMProvisionRequest {
  template_id?: string;
  vm_name: string;
  hypervisor: HypervisorType;
  device_id: string;
  
  // Resources
  vcpus: number;
  memory_mb: number;
  disk_gb: number;
  
  // Networking
  network_interfaces?: Array<{
    type: 'bridge' | 'nat' | 'host' | 'none';
    bridge_name?: string;
    mac_address?: string;
    ip_address?: string;
  }>;
  
  // OS configuration
  os_type?: string;
  os_version?: string;
  iso_path?: string;
  cloud_init?: Record<string, any>;
  
  // Options
  auto_start?: boolean;
  enable_vnc?: boolean;
  enable_snapshots?: boolean;
}