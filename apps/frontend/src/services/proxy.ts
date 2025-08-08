/**
 * Proxy Configuration Service
 * API methods for SWAG reverse proxy management
 */

import { api } from './api';
import type {
  ProxyConfigResponse,
  ProxyConfigList,
  ProxyConfigCreate,
  ProxyConfigUpdate,
  PaginationParams,
} from '@infrastructor/shared-types';

export const proxyService = {
  // List all proxy configurations with optional filters
  async list(params?: PaginationParams & { 
    device?: string; 
    service_name?: string; 
    ssl_enabled?: boolean; 
    status?: string;
  }): Promise<ProxyConfigList> {
    const response = await api.get<ProxyConfigList>('/proxies/configs', { params });
    return response.data || { items: [], total_count: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_previous: false };
  },

  // Get a specific proxy configuration
  async get(
    serviceName: string,
    params?: { device?: string; include_content?: boolean }
  ): Promise<ProxyConfigResponse | null> {
    const response = await api.get<ProxyConfigResponse>(`/proxy/configs/${serviceName}`, { params });
    return response.data || null;
  },

  // Create a new proxy configuration
  async create(config: ProxyConfigCreate): Promise<ProxyConfigResponse | null> {
    const response = await api.post<ProxyConfigResponse>('/proxy/configs', config);
    return response.data || null;
  },

  // Update an existing proxy configuration
  async update(serviceName: string, updates: ProxyConfigUpdate): Promise<ProxyConfigResponse | null> {
    const response = await api.put<ProxyConfigResponse>(`/proxy/configs/${serviceName}`, updates);
    return response.data || null;
  },

  // Delete a proxy configuration
  async delete(serviceName: string, device?: string): Promise<boolean> {
    const response = await api.delete<void>(`/proxy/configs/${serviceName}`, {
      params: { device }
    });
    return response.success;
  },

  // Scan and sync proxy configurations from file system
  async scan(params?: { device?: string; sync_to_database?: boolean }): Promise<{
    scanned_count: number;
    synced_count: number;
    errors: string[];
  }> {
    const response = await api.post<{
      scanned_count: number;
      synced_count: number;
      errors: string[];
    }>('/proxy/configs/scan', params);
    return response.data || { scanned_count: 0, synced_count: 0, errors: [] };
  },

  // Sync a specific proxy configuration with file system
  async sync(
    serviceName: string, 
    params?: { config_id?: number; force_update?: boolean }
  ): Promise<{ success: boolean; message?: string }> {
    const response = await api.post<{ success: boolean; message?: string }>(
      `/proxy/configs/${serviceName}/sync`,
      params
    );
    return response.data || { success: false, message: 'Sync failed' };
  },

  // Get proxy configuration summary statistics
  async getSummary(device?: string): Promise<{
    total_configs: number;
    enabled_configs: number;
    ssl_enabled_configs: number;
    configs_by_status: Record<string, number>;
    recent_changes: number;
  }> {
    const response = await api.get<{
      total_configs: number;
      enabled_configs: number;
      ssl_enabled_configs: number;
      configs_by_status: Record<string, number>;
      recent_changes: number;
    }>('/proxy/configs/summary', { params: { device } });
    return response.data || {
      total_configs: 0,
      enabled_configs: 0,
      ssl_enabled_configs: 0,
      configs_by_status: {},
      recent_changes: 0,
    };
  },

  // Generate proxy configuration for a service
  async generate(params: {
    service_name: string;
    upstream_port: number;
    device_hostname: string;
    domain?: string;
  }): Promise<{ success: boolean; config_content?: string; message?: string }> {
    const response = await api.post<{ 
      success: boolean; 
      config_content?: string; 
      message?: string;
    }>('/proxy/configs/generate', params);
    return response.data || { success: false, message: 'Generation failed' };
  },

  // Test proxy configuration
  async test(serviceName: string): Promise<{ 
    success: boolean; 
    status_code?: number; 
    response_time?: number; 
    message?: string;
  }> {
    const response = await api.post<{
      success: boolean;
      status_code?: number;
      response_time?: number;
      message?: string;
    }>(`/proxy/configs/${serviceName}/test`);
    return response.data || { success: false, message: 'Test failed' };
  },
};