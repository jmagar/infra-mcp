/**
 * Device Service
 * API methods for device management
 */

import { deviceApi } from './api';
import type {
  DeviceResponse,
  DeviceList,
  DeviceCreate,
  DeviceUpdate,
  PaginationParams,
} from '@infrastructor/shared-types';

export const deviceService = {
  // List all devices
  async list(params?: PaginationParams): Promise<DeviceList> {
    try {
      const response = await deviceApi.list();
      if (response.success && response.data) {
        return response.data as DeviceList;
      }
      return { items: [], total_count: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_previous: false };
    } catch (error) {
      console.error('Failed to fetch devices:', error);
      return { items: [], total_count: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_previous: false };
    }
  },

  // Get a specific device by hostname
  async get(hostname: string): Promise<DeviceResponse | null> {
    try {
      const response = await deviceApi.get(hostname);
      if (response.success && response.data) {
        return response.data as DeviceResponse;
      }
      return null;
    } catch (error) {
      console.error(`Failed to fetch device ${hostname}:`, error);
      return null;
    }
  },

  // Create a new device
  async create(deviceData: DeviceCreate): Promise<DeviceResponse | null> {
    try {
      const response = await deviceApi.create(deviceData);
      if (response.success && response.data) {
        return response.data as DeviceResponse;
      }
      return null;
    } catch (error) {
      console.error('Failed to create device:', error);
      throw error;
    }
  },

  // Update a device
  async update(hostname: string, updates: DeviceUpdate): Promise<DeviceResponse | null> {
    try {
      const response = await deviceApi.update(hostname, updates);
      if (response.success && response.data) {
        return response.data as DeviceResponse;
      }
      return null;
    } catch (error) {
      console.error(`Failed to update device ${hostname}:`, error);
      throw error;
    }
  },

  // Delete a device
  async delete(hostname: string): Promise<boolean> {
    try {
      const response = await deviceApi.delete(hostname);
      return response.success;
    } catch (error) {
      console.error(`Failed to delete device ${hostname}:`, error);
      throw error;
    }
  },

  // Get device summary
  async getSummary(hostname: string): Promise<any> {
    try {
      const response = await deviceApi.getSummary(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get device summary for ${hostname}:`, error);
      return null;
    }
  },

  // Get device metrics
  async getMetrics(hostname: string, options?: { include_processes?: boolean; timeout?: number }): Promise<any> {
    try {
      const response = await deviceApi.getMetrics(hostname, options);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get device metrics for ${hostname}:`, error);
      return null;
    }
  },

  // Get device drives
  async getDrives(hostname: string): Promise<any> {
    try {
      const response = await deviceApi.getDrives(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get device drives for ${hostname}:`, error);
      return null;
    }
  },

  // Get device logs
  async getLogs(hostname: string): Promise<any> {
    try {
      const response = await deviceApi.getLogs(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get device logs for ${hostname}:`, error);
      return null;
    }
  },

  // Get device ports
  async getPorts(hostname: string): Promise<any> {
    try {
      const response = await deviceApi.getPorts(hostname);
      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to get device ports for ${hostname}:`, error);
      return null;
    }
  },
};