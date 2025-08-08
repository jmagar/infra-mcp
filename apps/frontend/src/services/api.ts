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