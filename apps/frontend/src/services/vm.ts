/**
 * VM Service
 * API service for VM management and logs
 */

import { api } from './api';

export interface VMLogsResponse {
  hostname: string;
  log_source: string;
  logs: string;
  success: boolean;
}

export interface VMSpecificLogsResponse extends VMLogsResponse {
  vm_name: string;
}

export const vmService = {
  /**
   * Get libvirt daemon logs from a device
   */
  async getLogs(hostname: string, timeout: number = 30, live: boolean = false): Promise<VMLogsResponse> {
    const params = new URLSearchParams({
      timeout: timeout.toString(),
      live: live.toString(),
    });

    const response = await api.get<VMLogsResponse>(`/vms/${hostname}/logs?${params}`);
    return response.data;
  },

  /**
   * Get logs for a specific VM
   */
  async getVMSpecificLogs(
    hostname: string,
    vmName: string,
    timeout: number = 30,
    live: boolean = false
  ): Promise<VMSpecificLogsResponse> {
    const params = new URLSearchParams({
      timeout: timeout.toString(),
      live: live.toString(),
    });

    const response = await api.get<VMSpecificLogsResponse>(`/vms/${hostname}/logs/${vmName}?${params}`);
    return response.data;
  },

  /**
   * List available VMs on a device (would need to be implemented in backend)
   */
  async listVMs(hostname: string, timeout: number = 30): Promise<{ vms: string[] }> {
    // This endpoint would need to be implemented in the backend
    // For now, return empty array
    return { vms: [] };
  },
};