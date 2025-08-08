import { useEffect, useState } from 'react';
import { systemMetricsService, deviceService } from '@/services';
import { useUIStore } from '@/store/uiStore';
import type { 
  SystemMetricResponse,
  DriveHealthResponse,
  APIResponse 
} from '@infrastructor/shared-types';

export function useSystemMetrics(deviceHostname?: string) {
  const [metrics, setMetrics] = useState<SystemMetricResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useUIStore();

  const fetchMetrics = async (hostname?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const metricData = hostname 
        ? await systemMetricsService.getCurrent(hostname)
        : await systemMetricsService.getSummary();
      
      setMetrics(metricData as any);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setError(errorMessage);
      addNotification({
        type: 'error',
        title: 'Network error',
        message: 'Failed to connect to the server',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics(deviceHostname);
  }, [deviceHostname]);

  return {
    metrics,
    loading,
    error,
    fetchMetrics,
    refetch: () => fetchMetrics(deviceHostname),
  };
}

export function useDriveHealth(deviceHostname?: string) {
  const [driveHealth, setDriveHealth] = useState<DriveHealthResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useUIStore();

  const fetchDriveHealth = async (hostname?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const endpoint = hostname ? `/devices/${hostname}/drives/health` : '/system/drives/health';
      const response = await api.get<{ drives: DriveHealthResponse[] }>(endpoint);
      
      if (response.success && response.data) {
        setDriveHealth(response.data.drives || []);
      } else {
        setError(response.message || 'Failed to fetch drive health');
        addNotification({
          type: 'error',
          title: 'Error fetching drive health',
          message: response.message,
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setError(errorMessage);
      addNotification({
        type: 'error',
        title: 'Network error',
        message: 'Failed to connect to the server',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDriveHealth(deviceHostname);
  }, [deviceHostname]);

  return {
    driveHealth,
    loading,
    error,
    fetchDriveHealth,
    refetch: () => fetchDriveHealth(deviceHostname),
  };
}

export function useSystemLogs(deviceHostname?: string) {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useUIStore();

  const fetchLogs = async (
    hostname?: string, 
    options?: { lines?: number; service?: string; since?: string }
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (options?.lines) params.set('lines', options.lines.toString());
      if (options?.service) params.set('service', options.service);
      if (options?.since) params.set('since', options.since);
      
      const queryString = params.toString();
      const endpoint = hostname 
        ? `/devices/${hostname}/logs${queryString ? `?${queryString}` : ''}`
        : `/system/logs${queryString ? `?${queryString}` : ''}`;
      
      const response = await api.get<{ logs: string[] }>(endpoint);
      
      if (response.success && response.data) {
        setLogs(response.data.logs || []);
      } else {
        setError(response.message || 'Failed to fetch system logs');
        addNotification({
          type: 'error',
          title: 'Error fetching system logs',
          message: response.message,
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setError(errorMessage);
      addNotification({
        type: 'error',
        title: 'Network error',
        message: 'Failed to connect to the server',
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchLogsWithOptions = (options?: { lines?: number; service?: string; since?: string }) => {
    return fetchLogs(deviceHostname, options);
  };

  useEffect(() => {
    fetchLogs(deviceHostname);
  }, [deviceHostname]);

  return {
    logs,
    loading,
    error,
    fetchLogs: fetchLogsWithOptions,
    refetch: () => fetchLogs(deviceHostname),
  };
}