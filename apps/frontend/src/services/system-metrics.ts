/**
 * System Metrics Service
 * API methods for system monitoring and metrics
 */

import { api, healthRequest } from './api';
import type {
  SystemMetricResponse,
  SystemMetricsList,
  SystemMetricsSummary,
  PaginationParams,
} from '@infrastructor/shared-types';

export const systemMetricsService = {
  // Get system metrics for all devices or a specific device
  async list(params?: PaginationParams & { 
    device_id?: string; 
    start_time?: string; 
    end_time?: string; 
    metric_type?: string;
  }): Promise<SystemMetricsList> {
    const response = await api.get<SystemMetricsList>('/system/metrics', { params });
    return response.data || { items: [], total_count: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_previous: false };
  },

  // Get metrics for a specific device
  async getByDevice(
    deviceId: string, 
    params?: { 
      start_time?: string; 
      end_time?: string; 
      metric_type?: string;
      limit?: number;
    }
  ): Promise<SystemMetricResponse[]> {
    const response = await api.get<SystemMetricResponse[]>(`/system/metrics/device/${deviceId}`, { params });
    return response.data || [];
  },

  // Get latest metrics summary for all devices
  async getSummary(): Promise<SystemMetricsSummary> {
    const response = await api.get<SystemMetricsSummary>('/system/metrics/summary');
    return response.data || { devices: [], total_devices: 0, healthy_devices: 0, warning_devices: 0, critical_devices: 0 };
  },

  // Get current system metrics for a device
  async getCurrent(deviceId: string): Promise<SystemMetricResponse | null> {
    const response = await api.get<SystemMetricResponse>(`/system/metrics/device/${deviceId}/current`);
    return response.data || null;
  },

  // Get system health overview
  async getHealth(): Promise<{
    status: string;
    devices_online: number;
    devices_total: number;
    critical_alerts: number;
    warning_alerts: number;
  }> {
    const healthData = await healthRequest<{
      overview: {
        total_devices: number;
        online_devices: number;
        offline_devices: number;
      };
      health_indicators: {
        overall: string;
      };
      alerts: Array<{ level: string; message: string }>;
    }>('/health/dashboard');
    
    if (!healthData) {
      return {
        status: 'unknown',
        devices_online: 0,
        devices_total: 0,
        critical_alerts: 0,
        warning_alerts: 0,
      };
    }
    
    // Transform backend health data to match expected frontend interface
    const criticalAlerts = (healthData.alerts || []).filter(a => a.level === 'critical' || a.level === 'error').length;
    const warningAlerts = (healthData.alerts || []).filter(a => a.level === 'warning').length;
    
    return {
      status: healthData.health_indicators.overall,
      devices_online: healthData.overview.online_devices,
      devices_total: healthData.overview.total_devices,
      critical_alerts: criticalAlerts,
      warning_alerts: warningAlerts,
    };
  },

  // Get historical metrics for charting
  async getHistorical(
    deviceId: string,
    timeRange: '1h' | '6h' | '24h' | '7d' | '30d' = '24h',
    metrics: string[] = ['cpu_percent', 'memory_percent', 'disk_percent']
  ): Promise<{
    timestamps: string[];
    data: Record<string, number[]>;
  }> {
    const response = await api.get<{
      timestamps: string[];
      data: Record<string, number[]>;
    }>(`/system/metrics/device/${deviceId}/historical`, {
      params: { time_range: timeRange, metrics: metrics.join(',') }
    });
    return response.data || { timestamps: [], data: {} };
  },
};