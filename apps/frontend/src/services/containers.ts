/**
 * Container Service
 * API methods for container management
 */

import { api } from './api';
import type {
  ContainerResponse,
  ContainerList,
  ContainerStats,
  ContainerLogs,
  PaginationParams,
} from '@infrastructor/shared-types';

export const containerService = {
  // List all containers across all devices
  async list(params?: PaginationParams & { device_id?: string; status?: string }): Promise<ContainerList> {
    try {
      // Use the aggregated containers endpoint that gets containers from all devices
      const response = await api.get<ContainerList>('/containers', { params });
      return response.data || { items: [], total_count: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_previous: false };
    } catch (error) {
      console.error('Failed to fetch containers:', error);
      return { items: [], total_count: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_previous: false };
    }
  },

  // Get containers for a specific device
  async getByDevice(deviceHostname: string, params?: PaginationParams): Promise<ContainerList> {
    const response = await api.get<ContainerList>(`/containers/${deviceHostname}`, { params });
    return response.data || { items: [], total_count: 0, page: 1, page_size: 20, total_pages: 0, has_next: false, has_previous: false };
  },

  // Get a specific container by ID
  async get(containerId: string): Promise<ContainerResponse | null> {
    const response = await api.get<ContainerResponse>(`/containers/${containerId}`);
    return response.data || null;
  },

  // Start a container
  async start(deviceId: string, containerName: string): Promise<{ success: boolean; message?: string }> {
    const response = await api.post<{ success: boolean; message?: string }>(
      `/containers/${deviceId}/${containerName}/start`
    );
    return response.data || { success: false, message: 'Failed to start container' };
  },

  // Stop a container
  async stop(deviceId: string, containerName: string, force?: boolean): Promise<{ success: boolean; message?: string }> {
    const response = await api.post<{ success: boolean; message?: string }>(
      `/containers/${deviceId}/${containerName}/stop`,
      { force }
    );
    return response.data || { success: false, message: 'Failed to stop container' };
  },

  // Restart a container
  async restart(deviceId: string, containerName: string): Promise<{ success: boolean; message?: string }> {
    const response = await api.post<{ success: boolean; message?: string }>(
      `/containers/${deviceId}/${containerName}/restart`
    );
    return response.data || { success: false, message: 'Failed to restart container' };
  },

  // Remove a container
  async remove(deviceId: string, containerName: string, force?: boolean, removeVolumes?: boolean): Promise<{ success: boolean; message?: string }> {
    const response = await api.delete<{ success: boolean; message?: string }>(
      `/containers/${deviceId}/${containerName}`,
      { params: { force, remove_volumes: removeVolumes } }
    );
    return response.data || { success: false, message: 'Failed to remove container' };
  },

  // Get container logs
  async getLogs(
    deviceId: string, 
    containerName: string, 
    params?: { tail?: number; since?: string }
  ): Promise<ContainerLogs> {
    const response = await api.get<ContainerLogs>(
      `/containers/${deviceId}/${containerName}/logs`,
      { params }
    );
    return response.data || { logs: [], container_id: containerName, truncated: false };
  },

  // Get container stats
  async getStats(deviceId: string, containerName: string): Promise<ContainerStats | null> {
    const response = await api.get<ContainerStats>(
      `/containers/${deviceId}/${containerName}/stats`
    );
    return response.data || null;
  },

  // Execute command in container
  async exec(
    deviceId: string,
    containerName: string,
    command: string,
    options?: { user?: string; workdir?: string; interactive?: boolean }
  ): Promise<{ stdout: string; stderr: string; exit_code: number }> {
    const response = await api.post<{ stdout: string; stderr: string; exit_code: number }>(
      `/containers/${deviceId}/${containerName}/exec`,
      { command, ...options }
    );
    return response.data || { stdout: '', stderr: '', exit_code: -1 };
  },
};