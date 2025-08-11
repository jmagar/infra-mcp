/**
 * VM Service
 * API methods for VM management and log access
 */

import { vmApi } from './api';

export const vmService = {
  // Get VM logs for a device
  async getLogs(
    hostname: string, 
    params?: { 
      service?: string; 
      since?: string; 
      lines?: number 
    }
  ): Promise<{ logs: string[]; truncated: boolean } | null> {
    try {
      const response = await vmApi.getLogs(hostname, params);
      if (response.success && response.data) {
        return response.data as { logs: string[]; truncated: boolean };
      }
      return null;
    } catch (error) {
      console.error(`Failed to get VM logs for ${hostname}:`, error);
      return null;
    }
  },

  // Get logs for a specific VM
  async getVMLogs(
    hostname: string,
    vmName: string,
    params?: { 
      since?: string; 
      lines?: number 
    }
  ): Promise<{ logs: string[]; truncated: boolean } | null> {
    try {
      const response = await vmApi.getVMLogs(hostname, vmName, params);
      if (response.success && response.data) {
        return response.data as { logs: string[]; truncated: boolean };
      }
      return null;
    } catch (error) {
      console.error(`Failed to get VM logs for ${hostname}/${vmName}:`, error);
      return null;
    }
  },
};