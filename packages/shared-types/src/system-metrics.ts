/**
 * System metrics types and interfaces
 */

import { PaginatedResponse, TimeRangeParams, AggregationParams } from './common';

export interface SystemMetricBase {
  device_id: string;
  
  // CPU metrics
  cpu_usage_percent?: number;
  
  // Memory metrics
  memory_usage_percent?: number;
  memory_total_bytes?: number;
  memory_available_bytes?: number;
  
  // Load average metrics
  load_average_1m?: number;
  load_average_5m?: number;
  load_average_15m?: number;
  
  // Disk metrics
  disk_usage_percent?: number;
  disk_total_bytes?: number;
  disk_available_bytes?: number;
  
  // Network metrics
  network_bytes_sent?: number;
  network_bytes_recv?: number;
  
  // Process and uptime metrics
  uptime_seconds?: number;
  process_count?: number;
  
  // Additional metrics
  additional_metrics: Record<string, any>;
}

export interface SystemMetricCreate extends SystemMetricBase {
  time?: string;
}

export interface SystemMetricResponse extends SystemMetricBase {
  time: string;
}

export type SystemMetricsList = PaginatedResponse<SystemMetricResponse>;

export interface SystemMetricsQuery extends TimeRangeParams {
  device_ids?: string[];
  metrics?: string[];
  aggregation?: AggregationParams;
}

export interface SystemMetricsAggregated {
  time_bucket: string;
  device_id: string;
  
  // Aggregated CPU metrics
  avg_cpu_usage?: number;
  max_cpu_usage?: number;
  min_cpu_usage?: number;
  
  // Aggregated memory metrics
  avg_memory_usage?: number;
  max_memory_usage?: number;
  min_memory_usage?: number;
  avg_memory_total?: number;
  avg_memory_available?: number;
  
  // Aggregated load metrics
  avg_load_1m?: number;
  max_load_1m?: number;
  avg_load_5m?: number;
  avg_load_15m?: number;
  
  // Aggregated disk metrics
  avg_disk_usage?: number;
  max_disk_usage?: number;
  avg_disk_total?: number;
  avg_disk_available?: number;
  
  // Aggregated network metrics
  total_network_sent?: number;
  total_network_recv?: number;
  avg_network_sent?: number;
  avg_network_recv?: number;
  
  // Aggregated process metrics
  avg_process_count?: number;
  max_process_count?: number;
  
  // Aggregated uptime
  avg_uptime?: number;
  
  // Metadata
  sample_count: number;
  period_start: string;
  period_end: string;
}

export interface SystemMetricsAggregatedList {
  metrics: SystemMetricsAggregated[];
  total_count: number;
  query_params: SystemMetricsQuery;
  generated_at: string;
}

export interface SystemMetricsSummary {
  device_id: string;
  hostname?: string;
  
  // Current values (latest)
  current_cpu_usage?: number;
  current_memory_usage?: number;
  current_disk_usage?: number;
  current_load_1m?: number;
  current_uptime_hours?: number;
  current_process_count?: number;
  
  // 24-hour trends (min, max, avg)
  cpu_trend: Record<string, number>;
  memory_trend: Record<string, number>;
  disk_trend: Record<string, number>;
  load_trend: Record<string, number>;
  
  // Status indicators
  cpu_status: string;
  memory_status: string;
  disk_status: string;
  load_status: string;
  
  // Metadata
  last_updated: string;
  data_points_24h: number;
}

export interface SystemMetricsThresholds {
  cpu_warning: number;
  cpu_critical: number;
  memory_warning: number;
  memory_critical: number;
  disk_warning: number;
  disk_critical: number;
  load_warning: number;
  load_critical: number;
}

export interface SystemMetricsAlert {
  device_id: string;
  hostname: string;
  metric_name: string;
  current_value: number;
  threshold_value: number;
  severity: 'warning' | 'critical';
  message: string;
  triggered_at: string;
}