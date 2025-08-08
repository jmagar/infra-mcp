/**
 * Container-related types and interfaces
 */

import { HealthStatus, PaginatedResponse } from './common';

// Container status enums
export enum ContainerStatus {
  RUNNING = 'running',
  EXITED = 'exited',
  PAUSED = 'paused',
  RESTARTING = 'restarting',
  REMOVING = 'removing',
  DEAD = 'dead',
  CREATED = 'created'
}

export enum ContainerRestartPolicy {
  NO = 'no',
  ON_FAILURE = 'on-failure',
  ALWAYS = 'always',
  UNLESS_STOPPED = 'unless-stopped'
}

// Container types
export interface ContainerBase {
  name: string;
  image: string;
  image_id: string;
  command?: string;
  status: ContainerStatus;
  state: string;
  health?: HealthStatus;
  ports: ContainerPort[];
  labels: Record<string, string>;
  environment: Record<string, string>;
  mounts: ContainerMount[];
  networks: ContainerNetwork[];
}

export interface ContainerPort {
  container_port: number;
  host_port?: number;
  protocol: 'tcp' | 'udp';
  host_ip?: string;
}

export interface ContainerMount {
  source: string;
  destination: string;
  mode: 'rw' | 'ro';
  type: 'bind' | 'volume' | 'tmpfs';
}

export interface ContainerNetwork {
  name: string;
  network_id: string;
  endpoint_id?: string;
  mac_address?: string;
  ipv4_address?: string;
  ipv6_address?: string;
  aliases?: string[];
}

export interface ContainerResponse extends ContainerBase {
  id: string;
  device_id: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  restart_count: number;
  restart_policy?: ContainerRestartPolicy;
  exit_code?: number;
  error?: string;
  pid?: number;
  platform?: string;
}

export type ContainerList = PaginatedResponse<ContainerResponse>;

export interface ContainerDetails extends ContainerResponse {
  config: ContainerConfig;
  host_config: ContainerHostConfig;
  network_settings: ContainerNetworkSettings;
  mounts_detail: ContainerMountDetail[];
  state_detail: ContainerStateDetail;
  graph_driver: Record<string, any>;
}

export interface ContainerConfig {
  hostname?: string;
  domainname?: string;
  user?: string;
  attach_stdin?: boolean;
  attach_stdout?: boolean;
  attach_stderr?: boolean;
  tty?: boolean;
  open_stdin?: boolean;
  stdin_once?: boolean;
  env?: string[];
  cmd?: string[];
  entrypoint?: string[];
  labels?: Record<string, string>;
  working_dir?: string;
  exposed_ports?: Record<string, any>;
  volumes?: Record<string, any>;
  healthcheck?: ContainerHealthcheck;
}

export interface ContainerHealthcheck {
  test?: string[];
  interval?: number;
  timeout?: number;
  retries?: number;
  start_period?: number;
}

export interface ContainerHostConfig {
  binds?: string[];
  container_id_file?: string;
  log_config?: ContainerLogConfig;
  network_mode?: string;
  port_bindings?: Record<string, any>;
  restart_policy?: ContainerRestartPolicyConfig;
  auto_remove?: boolean;
  volume_driver?: string;
  volumes_from?: string[];
  cap_add?: string[];
  cap_drop?: string[];
  dns?: string[];
  dns_options?: string[];
  dns_search?: string[];
  extra_hosts?: string[];
  group_add?: string[];
  ipc_mode?: string;
  cgroup?: string;
  links?: string[];
  oom_score_adj?: number;
  pid_mode?: string;
  privileged?: boolean;
  publish_all_ports?: boolean;
  readonly_rootfs?: boolean;
  security_opt?: string[];
  storage_opt?: Record<string, string>;
  tmpfs?: Record<string, string>;
  uts_mode?: string;
  userns_mode?: string;
  shm_size?: number;
  sysctls?: Record<string, string>;
  runtime?: string;
  cpu_shares?: number;
  memory?: number;
  memory_swap?: number;
  memory_swappiness?: number;
  memory_reservation?: number;
  kernel_memory?: number;
  cpu_percent?: number;
  cpu_quota?: number;
  cpu_period?: number;
  cpuset_cpus?: string;
  cpuset_mems?: string;
  devices?: any[];
  device_cgroup_rules?: string[];
  disk_quota?: number;
}

export interface ContainerLogConfig {
  type: string;
  config?: Record<string, string>;
}

export interface ContainerRestartPolicyConfig {
  name: ContainerRestartPolicy;
  maximum_retry_count?: number;
}

export interface ContainerNetworkSettings {
  bridge?: string;
  sandbox_id?: string;
  hairpin_mode?: boolean;
  link_local_ipv6_address?: string;
  link_local_ipv6_prefix_len?: number;
  ports?: Record<string, any>;
  sandbox_key?: string;
  secondary_ip_addresses?: any[];
  secondary_ipv6_addresses?: any[];
  endpoint_id?: string;
  gateway?: string;
  global_ipv6_address?: string;
  global_ipv6_prefix_len?: number;
  ip_address?: string;
  ip_prefix_len?: number;
  ipv6_gateway?: string;
  mac_address?: string;
  networks?: Record<string, ContainerNetworkEndpoint>;
}

export interface ContainerNetworkEndpoint {
  ipam_config?: any;
  links?: string[];
  aliases?: string[];
  network_id?: string;
  endpoint_id?: string;
  gateway?: string;
  ip_address?: string;
  ip_prefix_len?: number;
  ipv6_gateway?: string;
  global_ipv6_address?: string;
  global_ipv6_prefix_len?: number;
  mac_address?: string;
  driver_opts?: Record<string, string>;
}

export interface ContainerMountDetail {
  type: 'bind' | 'volume' | 'tmpfs';
  name?: string;
  source: string;
  destination: string;
  driver?: string;
  mode: string;
  rw: boolean;
  propagation: string;
}

export interface ContainerStateDetail {
  status: ContainerStatus;
  running: boolean;
  paused: boolean;
  restarting: boolean;
  oom_killed: boolean;
  dead: boolean;
  pid?: number;
  exit_code?: number;
  error?: string;
  started_at?: string;
  finished_at?: string;
  health?: ContainerHealthState;
}

export interface ContainerHealthState {
  status: HealthStatus;
  failing_streak?: number;
  log?: ContainerHealthLog[];
}

export interface ContainerHealthLog {
  start: string;
  end: string;
  exit_code: number;
  output: string;
}

// Container operations
export interface ContainerExecRequest {
  container_name: string;
  command: string;
  interactive?: boolean;
  tty?: boolean;
  user?: string;
  working_dir?: string;
  environment?: Record<string, string>;
  privileged?: boolean;
}

export interface ContainerExecResponse {
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
}

export interface ContainerLogsRequest {
  container_name: string;
  since?: string;
  until?: string;
  timestamps?: boolean;
  follow?: boolean;
  tail?: number;
  details?: boolean;
}

export interface ContainerLogsResponse {
  container_name: string;
  logs: string[];
  total_lines: number;
  truncated: boolean;
  from_time?: string;
  to_time?: string;
}

export interface ContainerStatsRequest {
  container_name: string;
  stream?: boolean;
}

export interface ContainerStats {
  container_id: string;
  container_name: string;
  cpu_percent: number;
  memory_usage_bytes: number;
  memory_limit_bytes: number;
  memory_percent: number;
  network_rx_bytes: number;
  network_tx_bytes: number;
  block_read_bytes: number;
  block_write_bytes: number;
  pids: number;
  timestamp: string;
}

export interface ContainerInspectResponse {
  id: string;
  created: string;
  path: string;
  args: string[];
  state: ContainerStateDetail;
  image: string;
  resolv_conf_path?: string;
  hostname_path?: string;
  hosts_path?: string;
  log_path?: string;
  name: string;
  restart_count: number;
  driver: string;
  platform?: string;
  mount_label?: string;
  process_label?: string;
  app_armor_profile?: string;
  exec_ids?: string[];
  host_config: ContainerHostConfig;
  graph_driver: Record<string, any>;
  size_rw?: number;
  size_root_fs?: number;
  mounts: ContainerMountDetail[];
  config: ContainerConfig;
  network_settings: ContainerNetworkSettings;
}

// Container management
export interface ContainerAction {
  action: 'start' | 'stop' | 'restart' | 'pause' | 'unpause' | 'kill' | 'remove';
  container_name: string;
  force?: boolean;
  timeout?: number;
  signal?: string; // For kill
  remove_volumes?: boolean; // For remove
}

export interface ContainerActionResponse {
  container_name: string;
  action: string;
  success: boolean;
  message?: string;
  new_status?: ContainerStatus;
  error?: string;
}

export interface ContainerBulkAction {
  action: 'start' | 'stop' | 'restart' | 'remove';
  container_names: string[];
  force?: boolean;
  parallel?: boolean;
}

export interface ContainerBulkActionResponse {
  total: number;
  successful: number;
  failed: number;
  results: ContainerActionResponse[];
}

// Container images
export interface ContainerImage {
  id: string;
  repo_tags: string[];
  repo_digests: string[];
  created: string;
  size: number;
  virtual_size: number;
  labels?: Record<string, string>;
  containers?: number;
}

export interface ContainerImageList {
  images: ContainerImage[];
  total_count: number;
  total_size: number;
}

// Container service dependencies
export interface ServiceDependency {
  service_name: string;
  depends_on: string[];
  health_check?: boolean;
  restart_policy?: ContainerRestartPolicy;
  startup_order?: number;
}

export interface ServiceDependencyGraph {
  services: ServiceNode[];
  edges: ServiceEdge[];
  cycles?: string[][];
  startup_sequence?: string[];
}

export interface ServiceNode {
  name: string;
  status: ContainerStatus;
  health?: HealthStatus;
  dependencies: string[];
  dependents: string[];
}

export interface ServiceEdge {
  from: string;
  to: string;
  required: boolean;
  health_check: boolean;
}

// Container resource limits
export interface ContainerResourceLimits {
  cpu_limit?: number;
  cpu_reservation?: number;
  memory_limit?: number;
  memory_reservation?: number;
  memory_swap?: number;
  pids_limit?: number;
  ulimits?: ContainerUlimit[];
}

export interface ContainerUlimit {
  name: string;
  soft: number;
  hard: number;
}

// Container update
export interface ContainerUpdateRequest {
  container_name: string;
  cpu_shares?: number;
  memory?: number;
  memory_swap?: number;
  memory_reservation?: number;
  kernel_memory?: number;
  cpu_period?: number;
  cpu_quota?: number;
  cpu_realtime_period?: number;
  cpu_realtime_runtime?: number;
  cpuset_cpus?: string;
  cpuset_mems?: string;
  devices?: any[];
  device_cgroup_rules?: string[];
  disk_quota?: number;
  blkio_weight?: number;
  blkio_weight_device?: any[];
  blkio_device_read_bps?: any[];
  blkio_device_write_bps?: any[];
  blkio_device_read_iops?: any[];
  blkio_device_write_iops?: any[];
  restart_policy?: ContainerRestartPolicyConfig;
}

export interface ContainerUpdateResponse {
  container_name: string;
  warnings?: string[];
}

// Container metrics
export interface ContainerMetrics {
  container_id: string;
  container_name: string;
  cpu_usage: ContainerCPUUsage;
  memory_usage: ContainerMemoryUsage;
  network_usage: ContainerNetworkUsage;
  block_io_usage: ContainerBlockIOUsage;
  pids_stats: ContainerPidsStats;
  timestamp: string;
}

export interface ContainerCPUUsage {
  total_usage: number;
  percpu_usage?: number[];
  usage_in_kernelmode: number;
  usage_in_usermode: number;
  system_cpu_usage?: number;
  online_cpus?: number;
  throttling_data?: ContainerThrottlingData;
}

export interface ContainerThrottlingData {
  periods: number;
  throttled_periods: number;
  throttled_time: number;
}

export interface ContainerMemoryUsage {
  usage: number;
  max_usage: number;
  limit: number;
  percent: number;
  cache?: number;
  rss?: number;
  rss_huge?: number;
  mapped_file?: number;
  pgpgin?: number;
  pgpgout?: number;
  pgfault?: number;
  pgmajfault?: number;
  active_anon?: number;
  inactive_anon?: number;
  active_file?: number;
  inactive_file?: number;
  unevictable?: number;
}

export interface ContainerNetworkUsage {
  rx_bytes: number;
  rx_packets: number;
  rx_errors: number;
  rx_dropped: number;
  tx_bytes: number;
  tx_packets: number;
  tx_errors: number;
  tx_dropped: number;
}

export interface ContainerBlockIOUsage {
  io_service_bytes_recursive?: ContainerBlockIOStat[];
  io_serviced_recursive?: ContainerBlockIOStat[];
  io_queue_recursive?: ContainerBlockIOStat[];
  io_service_time_recursive?: ContainerBlockIOStat[];
  io_wait_time_recursive?: ContainerBlockIOStat[];
  io_merged_recursive?: ContainerBlockIOStat[];
  io_time_recursive?: ContainerBlockIOStat[];
  sectors_recursive?: ContainerBlockIOStat[];
}

export interface ContainerBlockIOStat {
  major: number;
  minor: number;
  op: string;
  value: number;
}

export interface ContainerPidsStats {
  current?: number;
  limit?: number;
}