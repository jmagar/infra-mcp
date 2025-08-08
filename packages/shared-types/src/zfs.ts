/**
 * ZFS-related types and interfaces
 */

import { HealthStatus, PaginatedResponse } from './common';

// ZFS Pool types
export interface ZFSPoolBase {
  name: string;
  size: number;
  allocated: number;
  free: number;
  capacity: number;
  dedupratio: number;
  health: string;
  altroot?: string;
  guid?: string;
  version?: string;
  bootfs?: string;
  delegation?: boolean;
  autoreplace?: boolean;
  cachefile?: string;
  readonly?: boolean;
  comment?: string;
}

export interface ZFSPoolCreate {
  name: string;
  vdevs: string[];
  raid_type?: 'stripe' | 'mirror' | 'raidz' | 'raidz2' | 'raidz3';
  mount_point?: string;
  properties?: Record<string, string>;
}

export interface ZFSPoolResponse extends ZFSPoolBase {
  id: string;
  device_id: string;
  fragmentation?: number;
  feature_flags?: Record<string, string>;
  scan_stats?: Record<string, any>;
  config_errors?: string[];
  created_at: string;
  updated_at: string;
}

export type ZFSPoolList = PaginatedResponse<ZFSPoolResponse>;

// ZFS Dataset types
export interface ZFSDatasetBase {
  name: string;
  type: 'filesystem' | 'volume' | 'snapshot';
  used: number;
  available: number;
  referenced: number;
  compressratio: number;
  mounted?: boolean;
  mountpoint?: string;
  quota?: number;
  reservation?: number;
  recordsize?: number;
  compression?: string;
  checksum?: string;
  atime?: boolean;
  devices?: boolean;
  exec?: boolean;
  setuid?: boolean;
  readonly?: boolean;
  zoned?: boolean;
  snapdir?: string;
  aclmode?: string;
  aclinherit?: string;
  canmount?: string;
  xattr?: boolean;
  copies?: number;
  version?: number;
  utf8only?: boolean;
  normalization?: string;
  casesensitivity?: string;
  vscan?: boolean;
  nbmand?: boolean;
  sharesmb?: string;
  sharenfs?: string;
  refquota?: number;
  refreservation?: number;
  primarycache?: string;
  secondarycache?: string;
  usedbysnapshots?: number;
  usedbydataset?: number;
  usedbychildren?: number;
  usedbyrefreservation?: number;
}

export interface ZFSDatasetCreate {
  name: string;
  dataset_type?: 'filesystem' | 'volume';
  properties?: Record<string, string>;
  size?: number; // For volumes
  sparse?: boolean; // For volumes
  blocksize?: number; // For volumes
}

export interface ZFSDatasetResponse extends ZFSDatasetBase {
  id: string;
  pool_name: string;
  device_id: string;
  origin?: string;
  written?: number;
  logicalused?: number;
  logicalreferenced?: number;
  volsize?: number;
  volblocksize?: number;
  creation_time?: string;
  clones?: string[];
  created_at: string;
  updated_at: string;
}

export type ZFSDatasetList = PaginatedResponse<ZFSDatasetResponse>;

// ZFS Snapshot types
export interface ZFSSnapshotBase {
  name: string;
  dataset_name: string;
  used: number;
  referenced: number;
  creation_time: string;
}

export interface ZFSSnapshotCreate {
  dataset_name: string;
  snapshot_name: string;
  recursive?: boolean;
  properties?: Record<string, string>;
}

export interface ZFSSnapshotResponse extends ZFSSnapshotBase {
  id: string;
  pool_name: string;
  device_id: string;
  guid?: string;
  clones?: string[];
  defer_destroy?: boolean;
  holds?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export type ZFSSnapshotList = PaginatedResponse<ZFSSnapshotResponse>;

// ZFS operations
export interface ZFSCloneRequest {
  snapshot_name: string;
  clone_name: string;
  properties?: Record<string, string>;
}

export interface ZFSSendRequest {
  snapshot_name: string;
  destination?: string;
  incremental?: boolean;
  from_snapshot?: string;
  recursive?: boolean;
  replicate?: boolean;
  deduplicate?: boolean;
  large_blocks?: boolean;
  embed_data?: boolean;
  compressed?: boolean;
  raw?: boolean;
  holds?: boolean;
  props?: boolean;
}

export interface ZFSReceiveRequest {
  dataset_name: string;
  force?: boolean;
  resumable?: boolean;
  verbose?: boolean;
  origin?: string;
  exclude?: string[];
  rename?: string;
}

export interface ZFSDiffResponse {
  path: string;
  change_type: '+' | '-' | 'M' | 'R';
  file_type?: 'F' | 'D' | 'L' | 'B' | 'C' | 'S' | 'P' | '/' | '@';
  old_path?: string; // For renames
}

// ZFS Health and monitoring
export interface ZFSHealthCheck {
  device_id: string;
  pools: ZFSPoolHealth[];
  overall_status: HealthStatus;
  total_pools: number;
  healthy_pools: number;
  degraded_pools: number;
  faulted_pools: number;
  total_capacity_bytes: number;
  used_capacity_bytes: number;
  free_capacity_bytes: number;
  deduplication_ratio: number;
  compression_ratio: number;
  fragmentation_percent?: number;
  last_scrub_time?: string;
  next_scrub_time?: string;
  recommendations: string[];
  timestamp: string;
}

export interface ZFSPoolHealth {
  name: string;
  state: string;
  status: HealthStatus;
  action?: string;
  scan?: ZFSScanInfo;
  config_errors?: string[];
  vdev_errors?: ZFSVdevError[];
  capacity_percent: number;
  fragmentation_percent?: number;
}

export interface ZFSScanInfo {
  type: 'scrub' | 'resilver';
  state: string;
  start_time?: string;
  end_time?: string;
  progress_percent?: number;
  data_processed?: number;
  data_to_process?: number;
  rate?: number;
  eta?: string;
  errors?: number;
}

export interface ZFSVdevError {
  vdev_name: string;
  vdev_type: string;
  state: string;
  read_errors: number;
  write_errors: number;
  checksum_errors: number;
}

export interface ZFSARCStats {
  size: number;
  target_size: number;
  min_size: number;
  max_size: number;
  hits: number;
  misses: number;
  hit_ratio: number;
  evicted: number;
  deleted: number;
  prefetch_hits: number;
  prefetch_misses: number;
  metadata_size: number;
  data_size: number;
  header_size: number;
  other_size: number;
  anon_size?: number;
  mru_size?: number;
  mfu_size?: number;
  ghost_size?: number;
}

export interface ZFSEvent {
  time: string;
  class: string;
  subclass?: string;
  pool?: string;
  vdev_guid?: string;
  vdev_path?: string;
  description: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
}

export interface ZFSReport {
  device_id: string;
  hostname: string;
  report_type: 'summary' | 'detailed' | 'performance' | 'capacity' | 'errors';
  pools: ZFSPoolReport[];
  datasets: ZFSDatasetReport[];
  snapshots: ZFSSnapshotReport[];
  arc_stats?: ZFSARCStats;
  io_stats?: Record<string, any>;
  recommendations: string[];
  generated_at: string;
}

export interface ZFSPoolReport {
  name: string;
  health: string;
  capacity: Record<string, number>;
  performance: Record<string, number>;
  errors: Record<string, number>;
  last_scrub?: ZFSScanInfo;
}

export interface ZFSDatasetReport {
  name: string;
  type: string;
  usage: Record<string, number>;
  compression: Record<string, number>;
  snapshot_count: number;
  quota_usage?: number;
}

export interface ZFSSnapshotReport {
  dataset: string;
  count: number;
  total_size: number;
  oldest?: string;
  newest?: string;
  retention_policy?: string;
}

export interface ZFSSnapshotUsageAnalysis {
  device_id: string;
  total_snapshots: number;
  total_size_bytes: number;
  datasets: ZFSDatasetSnapshotUsage[];
  cleanup_candidates: ZFSSnapshotCleanupCandidate[];
  estimated_reclaimable_bytes: number;
  recommendations: string[];
  analysis_timestamp: string;
}

export interface ZFSDatasetSnapshotUsage {
  dataset_name: string;
  snapshot_count: number;
  total_size: number;
  oldest_snapshot?: string;
  newest_snapshot?: string;
  growth_rate_daily?: number;
}

export interface ZFSSnapshotCleanupCandidate {
  snapshot_name: string;
  dataset_name: string;
  size: number;
  age_days: number;
  reason: string;
  priority: 'low' | 'medium' | 'high';
}

export interface ZFSOptimizationSuggestions {
  device_id: string;
  pools: ZFSPoolOptimization[];
  datasets: ZFSDatasetOptimization[];
  system_wide: ZFSSystemOptimization[];
  potential_savings: Record<string, number>;
  performance_improvements: Record<string, string>;
  generated_at: string;
}

export interface ZFSPoolOptimization {
  pool_name: string;
  suggestions: string[];
  property_changes?: Record<string, string>;
  estimated_impact: string;
}

export interface ZFSDatasetOptimization {
  dataset_name: string;
  suggestions: string[];
  property_changes?: Record<string, string>;
  estimated_space_savings?: number;
}

export interface ZFSSystemOptimization {
  category: 'arc' | 'compression' | 'deduplication' | 'snapshots' | 'scrub' | 'l2arc';
  current_value?: string;
  recommended_value?: string;
  description: string;
  commands?: string[];
}