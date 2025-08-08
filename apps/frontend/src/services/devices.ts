/**
 * Device Service
 * API methods for device management
 */

import { api } from './api';
import type {
  DeviceResponse,
  DeviceList,
  DeviceCreate,
  DeviceUpdate,
  DeviceHealth,
  DeviceHealthList,
  DeviceImportRequest,
  DeviceImportResponse,
  PaginationParams,
  DeviceFilter,
} from '@infrastructor/shared-types';

export const deviceService = {
  // List all devices with optional filters
  async list(params?: PaginationParams & DeviceFilter): Promise<DeviceList> {
    const response = await api.get<DeviceList>('/devices', { params });
    return response.data || { items: [], total_count: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_previous: false };
  },

  // Get a specific device by ID
  async get(deviceId: string): Promise<DeviceResponse | null> {
    const response = await api.get<DeviceResponse>(`/devices/${deviceId}`);
    return response.data || null;
  },

  // Create a new device
  async create(device: DeviceCreate): Promise<DeviceResponse | null> {
    const response = await api.post<DeviceResponse>('/devices', device);
    return response.data || null;
  },

  // Update an existing device
  async update(deviceId: string, updates: DeviceUpdate): Promise<DeviceResponse | null> {
    const response = await api.put<DeviceResponse>(`/devices/${deviceId}`, updates);
    return response.data || null;
  },

  // Delete a device
  async delete(deviceId: string): Promise<boolean> {
    const response = await api.delete<void>(`/devices/${deviceId}`);
    return response.success;
  },

  // Get device health status
  async health(deviceId?: string): Promise<DeviceHealthList | DeviceHealth | null> {
    const url = deviceId ? `/devices/${deviceId}/health` : '/devices/health';
    const response = await api.get<DeviceHealthList | DeviceHealth>(url);
    return response.data || null;
  },

  // Test device connection
  async testConnection(deviceId: string): Promise<{ success: boolean; message?: string }> {
    const response = await api.post<{ success: boolean; message?: string }>(
      `/devices/${deviceId}/test-connection`
    );
    return response.data || { success: false, message: 'Connection test failed' };
  },

  // Analyze device capabilities and configuration
  async analyze(deviceId: string): Promise<any> {
    const response = await api.post<any>(`/devices/${deviceId}/analyze`);
    return response.data;
  },

  // Import devices from SSH config
  async importFromSSH(request: DeviceImportRequest): Promise<DeviceImportResponse | null> {
    const response = await api.post<DeviceImportResponse>('/devices/import-ssh', request);
    return response.data || null;
  },

  // Get device metrics
  async getMetrics(
    deviceId: string,
    params?: { start_time?: string; end_time?: string }
  ): Promise<any> {
    const response = await api.get<any>(`/devices/${deviceId}/metrics`, { params });
    return response.data;
  },

  // Get device logs
  async getLogs(
    deviceId: string,
    params?: {
      lines?: number;
      since?: string;
      service?: string;
    }
  ): Promise<{ logs: string[]; truncated: boolean }> {
    const response = await api.get<{ logs: string[]; truncated: boolean }>(
      `/devices/${deviceId}/logs`,
      { params }
    );
    return response.data || { logs: [], truncated: false };
  },

  // Execute command on device
  async executeCommand(
    deviceId: string,
    command: string,
    timeout?: number
  ): Promise<{ stdout: string; stderr: string; exit_code: number }> {
    const response = await api.post<{ stdout: string; stderr: string; exit_code: number }>(
      `/devices/${deviceId}/execute`,
      { command, timeout }
    );
    return response.data || { stdout: '', stderr: '', exit_code: -1 };
  },
};