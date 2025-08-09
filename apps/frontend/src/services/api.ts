/**
 * API Client Configuration
 * Main API client for communicating with the Infrastructor backend
 */

import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import type { APIResponse, ErrorResponse } from '@infrastructor/shared-types';

// API configuration from environment variables
// API and WS are on the same port; during dev we rely on Vite proxy for /api
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 30000;
const API_KEY = import.meta.env.VITE_API_KEY || 'your-api-key-for-authentication';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`,
  },
});

// Authentication is handled via Bearer token using API key from environment

// Request interceptor for adding auth and logging
apiClient.interceptors.request.use(
  (config) => {
    // Log request in development
    if (import.meta.env.DEV) {
      const method = (config.method || 'GET').toString().toUpperCase();
      console.log(`[API] ${method} ${config.url}`, {
        params: config.params,
        data: config.data,
      });
    }
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    // Log response in development
    if (import.meta.env.DEV) {
      console.log(`[API] Response:`, response.data);
    }
    return response;
  },
  async (error: AxiosError<ErrorResponse>) => {
    const { response } = error;

    if (response) {
      // Handle specific error statuses
      switch (response.status) {
        case 401:
        case 403:
          // Authentication/authorization error
          console.error('[API] Access denied - check API key configuration:', response.data);
          break;
        case 404:
          // Not found
          console.error('[API] Resource not found:', response.config?.url);
          break;
        case 429:
          // Rate limited
          console.error('[API] Rate limited. Try again later.');
          break;
        case 500:
        case 502:
        case 503:
        case 504:
          // Server errors
          console.error('[API] Server error:', response.data);
          break;
        default:
          console.error('[API] Error:', response.data);
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('[API] Network error - no response received');
    } else {
      // Error in request configuration
      console.error('[API] Request configuration error:', error.message);
    }

    return Promise.reject(error);
  }
);

// Generic request function with proper typing
export async function apiRequest<T>(
  config: AxiosRequestConfig
): Promise<APIResponse<T>> {
  try {
    const response = await apiClient.request<T>(config);
    
    // Backend returns data directly, so we wrap it in APIResponse format
    return {
      success: true,
      data: response.data,
      message: 'Request successful',
    };
  } catch (error) {
    const axiosError = error as AxiosError<ErrorResponse>;
    
    // Convert error to APIResponse format
    return {
      success: false,
      message: axiosError.response?.data?.message || axiosError.message || 'An error occurred',
      errors: axiosError.response?.data?.details 
        ? Object.values(axiosError.response.data.details).flat() as string[]
        : [axiosError.message],
    };
  }
}

// Helpers to ensure path parameters are provided
function assertNonEmpty(name: string, value: string | undefined | null): asserts value is string {
  if (!value) {
    const msg = `[API] Missing required parameter: ${name}`;
    if (import.meta.env.DEV) console.warn(msg);
    throw new Error(msg);
  }
}

// Convenience methods
export const api = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, method: 'GET', url }),
  
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, method: 'POST', url, data }),
  
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, method: 'PUT', url, data }),
  
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, method: 'PATCH', url, data }),
  
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    apiRequest<T>({ ...config, method: 'DELETE', url }),
};

// Export the raw axios instance for advanced use cases
export { apiClient };

// API endpoints for devices
export const deviceApi = {
  list: () => api.get('/devices'),
  get: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/devices/${hostname}`);
  },
  getSummary: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/devices/${hostname}/summary`);
  },
  getStatus: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/devices/${hostname}/status`);
  },
  getLogs: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/devices/${hostname}/logs`);
  },
  getDrives: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/devices/${hostname}/drives`);
  },
  getPorts: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/devices/${hostname}/ports`);
  },
  getMetrics: (hostname: string, params?: { include_processes?: boolean; timeout?: number }) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/devices/${hostname}/metrics`, { params });
  },
  getDriveStats: (hostname: string, params?: { drive?: string; timeout?: number }) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/devices/${hostname}/drives/stats`, { params });
  },
  import: (data: unknown) => api.post('/devices/import', data),
  create: (data: unknown) => api.post('/devices', data),
  update: (hostname: string, data: unknown) => {
    assertNonEmpty('hostname', hostname);
    return api.put(`/devices/${hostname}`, data);
  },
  delete: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.delete(`/devices/${hostname}`);
  },
};

// API endpoints for containers
export const containerApi = {
  list: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/containers/${hostname}`);
  },
  get: (hostname: string, containerName: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('containerName', containerName);
    return api.get(`/containers/${hostname}/${containerName}`);
  },
  getLogs: (hostname: string, containerName: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('containerName', containerName);
    return api.get(`/containers/${hostname}/${containerName}/logs`);
  },
  getStats: (hostname: string, containerName: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('containerName', containerName);
    return api.get(`/containers/${hostname}/${containerName}/stats`);
  },
  start: (hostname: string, containerName: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('containerName', containerName);
    return api.post(`/containers/${hostname}/${containerName}/start`, {} as Record<string, never>);
  },
  stop: (hostname: string, containerName: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('containerName', containerName);
    return api.post(`/containers/${hostname}/${containerName}/stop`, {} as Record<string, never>);
  },
  restart: (hostname: string, containerName: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('containerName', containerName);
    return api.post(`/containers/${hostname}/${containerName}/restart`, {} as Record<string, never>);
  },
  exec: (hostname: string, containerName: string, command: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('containerName', containerName);
    return api.post(`/containers/${hostname}/${containerName}/exec`, { command });
  },
  remove: (hostname: string, containerName: string, options?: { force?: boolean; remove_volumes?: boolean }) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('containerName', containerName);
    return api.delete(`/containers/${hostname}/${containerName}`, { params: options });
  },
};

// API endpoints for Docker Compose
export const composeApi = {
  modify: (data: unknown) => api.post('/compose/modify', data),
  deploy: (data: unknown) => api.post('/compose/deploy', data),
  modifyAndDeploy: (data: unknown) => api.post('/compose/modify-and-deploy', data),
  scanPorts: (data: unknown) => api.post('/compose/scan-ports', data),
  scanNetworks: (data: unknown) => api.post('/compose/scan-networks', data),
  downloadModified: (device: string) => {
    assertNonEmpty('device', device);
    return api.get(`/compose/download-modified/${device}`);
  },
  getProxyConfigs: (device: string, serviceName: string) => {
    assertNonEmpty('device', device);
    assertNonEmpty('serviceName', serviceName);
    return api.get(`/compose/proxy-configs/${device}/${serviceName}`);
  },
};

// API endpoints for Proxy Configuration
export const proxyApi = {
  listConfigs: (params?: { device?: string; service_name?: string; ssl_enabled?: boolean; status?: string }) => 
    api.get('/proxies/configs', { params }),
  getConfig: (serviceName: string) => {
    assertNonEmpty('serviceName', serviceName);
    return api.get(`/proxies/configs/${serviceName}`);
  },
  getConfigContent: (serviceName: string) => {
    assertNonEmpty('serviceName', serviceName);
    return api.get(`/proxies/configs/${serviceName}/content`);
  },
  syncConfig: (serviceName: string) => {
    assertNonEmpty('serviceName', serviceName);
    return api.post(`/proxies/configs/${serviceName}/sync`, {});
  },
  scan: () => api.post('/proxies/scan', {}),
  getSummary: () => api.get('/proxies/summary'),
  listSamples: () => api.get('/proxies/samples'),
  getSample: (sampleName: string) => {
    assertNonEmpty('sampleName', sampleName);
    return api.get(`/proxies/samples/${sampleName}`);
  },
  getTemplate: (templateType: string) => {
    assertNonEmpty('templateType', templateType);
    return api.get(`/proxies/templates/${templateType}`);
  },
};

// API endpoints for ZFS Management
export const zfsApi = {
  listPools: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/zfs/${hostname}/pools`);
  },
  getPoolStatus: (hostname: string, poolName: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('poolName', poolName);
    return api.get(`/zfs/${hostname}/pools/${poolName}/status`);
  },
  listDatasets: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/zfs/${hostname}/datasets`);
  },
  getDatasetProperties: (hostname: string, datasetName: string) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('datasetName', datasetName);
    return api.get(`/zfs/${hostname}/datasets/${datasetName}/properties`);
  },
  listSnapshots: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/zfs/${hostname}/snapshots`);
  },
  createSnapshot: (hostname: string, data: unknown) => {
    assertNonEmpty('hostname', hostname);
    return api.post(`/zfs/${hostname}/snapshots`, data);
  },
  cloneSnapshot: (hostname: string, snapshotName: string, data: unknown) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('snapshotName', snapshotName);
    return api.post(`/zfs/${hostname}/snapshots/${snapshotName}/clone`, data);
  },
  sendSnapshot: (hostname: string, snapshotName: string, data: unknown) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('snapshotName', snapshotName);
    return api.post(`/zfs/${hostname}/snapshots/${snapshotName}/send`, data);
  },
  diffSnapshots: (hostname: string, snapshotName: string, data: unknown) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('snapshotName', snapshotName);
    return api.post(`/zfs/${hostname}/snapshots/${snapshotName}/diff`, data);
  },
  receiveSnapshot: (hostname: string, data: unknown) => {
    assertNonEmpty('hostname', hostname);
    return api.post(`/zfs/${hostname}/receive`, data);
  },
  getHealth: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/zfs/${hostname}/health`);
  },
  getARCStats: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/zfs/${hostname}/arc-stats`);
  },
  getEvents: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/zfs/${hostname}/events`);
  },
  getReport: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/zfs/${hostname}/report`);
  },
  getSnapshotUsage: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/zfs/${hostname}/snapshots/usage`);
  },
  optimize: (hostname: string) => {
    assertNonEmpty('hostname', hostname);
    return api.post(`/zfs/${hostname}/optimize`, {});
  },
};

// API endpoints for VM Management  
export const vmApi = {
  getLogs: (hostname: string, params?: { service?: string; since?: string; lines?: number }) => {
    assertNonEmpty('hostname', hostname);
    return api.get(`/vms/${hostname}/logs`, { params });
  },
  getVMLogs: (hostname: string, vmName: string, params?: { since?: string; lines?: number }) => {
    assertNonEmpty('hostname', hostname);
    assertNonEmpty('vmName', vmName);
    return api.get(`/vms/${hostname}/logs/${vmName}`, { params });
  },
};

// API endpoints for System Information
export const systemApi = {
  getStatus: () => api.get('/status'),
  getSystemInfo: () => api.get('/system-info'),
  testError: () => api.get('/test-error'),
};

// Health check function
export async function checkAPIHealth(): Promise<boolean> {
  try {
    const response = await axios.get('/health', {
      timeout: 5000,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
      },
    });
    return response.status === 200;
  } catch {
    return false;
  }
}

// Special health endpoint request (bypasses /api prefix)
export async function healthRequest<T>(endpoint: string): Promise<T | null> {
  try {
    const response = await axios.get<T>(endpoint, {
      timeout: 10000,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
    });
    return response.data;
  } catch (error) {
    console.error(`Health request failed for ${endpoint}:`, error);
    return null;
  }
}