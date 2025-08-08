/**
 * Comprehensive Dashboard Data Hook
 * Aggregates all infrastructure data for dashboard display
 */

import { useEffect, useState } from 'react';
import { useDevices } from './useDevices';
import { useContainers } from './useContainers';
import { useSystemMetrics } from './useSystemMetrics';
import { useAlertsStream } from './useWebSocket';
import { healthRequest } from '@/services/api';
import type { 
  DeviceResponse,
  ContainerResponse,
  SystemMetricResponse,
} from '@infrastructor/shared-types';

export interface DashboardOverview {
  // Device metrics
  totalDevices: number;
  onlineDevices: number;
  offlineDevices: number;
  
  // Container metrics
  totalContainers: number;
  runningContainers: number;
  stoppedContainers: number;
  containersByDevice: Record<string, number>;
  
  // System metrics
  avgCpuUsage: number;
  avgMemoryUsage: number;
  maxCpuUsage: number;
  maxMemoryUsage: number;
  
  // Storage metrics
  totalStorage: string;
  usedStorage: string;
  storageUsagePercent: number;
  
  // Health status
  healthStatus: 'excellent' | 'good' | 'warning' | 'critical';
  criticalAlerts: number;
  warningAlerts: number;
  
  // Data collection stats
  metricsCollected24h: number;
  containerDataPoints24h: number;
  lastDataUpdate: string;
}

export interface DeviceMetrics {
  hostname: string;
  status: 'online' | 'offline';
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  containers: number;
  runningContainers: number;
  uptime: string;
  lastSeen: string;
}

export function useDashboardData() {
  const { devices, loading: devicesLoading } = useDevices();
  const { containers, loading: containersLoading } = useContainers();
  const { alerts, isConnected } = useAlertsStream();
  
  const [overview, setOverview] = useState<DashboardOverview>({
    totalDevices: 0,
    onlineDevices: 0,
    offlineDevices: 0,
    totalContainers: 0,
    runningContainers: 0,
    stoppedContainers: 0,
    containersByDevice: {},
    avgCpuUsage: 0,
    avgMemoryUsage: 0,
    maxCpuUsage: 0,
    maxMemoryUsage: 0,
    totalStorage: '0 TB',
    usedStorage: '0 TB',
    storageUsagePercent: 0,
    healthStatus: 'good',
    criticalAlerts: 0,
    warningAlerts: 0,
    metricsCollected24h: 0,
    containerDataPoints24h: 0,
    lastDataUpdate: new Date().toISOString(),
  });
  
  const [deviceMetrics, setDeviceMetrics] = useState<DeviceMetrics[]>([]);
  const [healthData, setHealthData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch comprehensive health data from backend
  const fetchHealthData = async () => {
    try {
      const healthResponse = await healthRequest<{
        overview: {
          total_devices: number;
          online_devices: number;
          offline_devices: number;
          connectivity_percentage: number;
        };
        data_collection: {
          metrics_last_24h: number;
          containers_last_24h: number;
          collection_rate_per_hour: number;
          polling_active: boolean;
          active_polling_devices: number;
        };
        health_indicators: {
          system_status: string;
          data_collection: string;
          polling_service: string;
          overall: string;
        };
        quick_actions: string[];
        alerts: Array<{ level: string; message: string }>;
        timestamp: string;
        data_range_hours: number;
      }>('http://localhost:9101/health/dashboard');
      
      if (healthResponse) {
        setHealthData(healthResponse);
      }
    } catch (error) {
      console.error('Failed to fetch health data:', error);
      setError('Failed to fetch dashboard data');
    }
  };

  // Aggregate all dashboard metrics
  useEffect(() => {
    if (!devices || !containers) return;
    
    setLoading(true);
    
    try {
      // Device calculations
      const totalDevices = devices.length;
      const onlineDevices = devices.filter(d => d.status === 'online').length;
      const offlineDevices = totalDevices - onlineDevices;
      
      // Container calculations
      const totalContainers = containers.length;
      const runningContainers = containers.filter(c => c.status === 'running').length;
      const stoppedContainers = totalContainers - runningContainers;
      
      // Container by device mapping
      const containersByDevice: Record<string, number> = {};
      containers.forEach(container => {
        if (container.device_hostname) {
          containersByDevice[container.device_hostname] = 
            (containersByDevice[container.device_hostname] || 0) + 1;
        }
      });
      
      // Health status calculation
      let healthStatus: DashboardOverview['healthStatus'] = 'good';
      const deviceHealthRatio = totalDevices > 0 ? onlineDevices / totalDevices : 1;
      const containerHealthRatio = totalContainers > 0 ? runningContainers / totalContainers : 1;
      
      if (deviceHealthRatio > 0.9 && containerHealthRatio > 0.85) {
        healthStatus = 'excellent';
      } else if (deviceHealthRatio > 0.75 && containerHealthRatio > 0.7) {
        healthStatus = 'good';
      } else if (deviceHealthRatio > 0.5 || containerHealthRatio > 0.5) {
        healthStatus = 'warning';
      } else {
        healthStatus = 'critical';
      }
      
      // Alert calculations
      const criticalAlerts = alerts.filter(a => a.level === 'error' || a.level === 'critical').length;
      const warningAlerts = alerts.filter(a => a.level === 'warning').length;
      
      // Use health data if available, otherwise use calculated values
      const newOverview: DashboardOverview = {
        totalDevices,
        onlineDevices,
        offlineDevices,
        totalContainers,
        runningContainers,
        stoppedContainers,
        containersByDevice,
        avgCpuUsage: 0, // TODO: Get from system metrics summary
        avgMemoryUsage: 0, // TODO: Get from system metrics summary
        maxCpuUsage: 0, // TODO: Get from system metrics summary
        maxMemoryUsage: 0, // TODO: Get from system metrics summary
        totalStorage: '0 TB', // TODO: Get from system metrics summary
        usedStorage: '0 TB', // TODO: Get from system metrics summary
        storageUsagePercent: 0, // TODO: Get from system metrics summary
        healthStatus,
        criticalAlerts,
        warningAlerts,
        metricsCollected24h: healthData?.data_collection?.metrics_last_24h || 0,
        containerDataPoints24h: healthData?.data_collection?.containers_last_24h || 0,
        lastDataUpdate: new Date().toISOString(),
      };
      
      setOverview(newOverview);
      
      // Device-specific metrics - build from devices data
      if (devices && devices.length > 0) {
        const deviceMetricsData: DeviceMetrics[] = devices.map((device) => ({
          hostname: device.hostname,
          status: device.status as 'online' | 'offline',
          cpuUsage: 0, // TODO: Get from device metrics
          memoryUsage: 0, // TODO: Get from device metrics  
          diskUsage: 0, // TODO: Get from device metrics
          containers: containersByDevice[device.hostname] || 0,
          runningContainers: containers?.filter(c => 
            c.device_hostname === device.hostname && c.status === 'running'
          ).length || 0,
          uptime: 'Unknown', // TODO: Get from device metrics
          lastSeen: 'Recently', // TODO: Get from device metrics
        }));
        setDeviceMetrics(deviceMetricsData);
      }
      
    } catch (error) {
      console.error('Error calculating dashboard metrics:', error);
      setError('Failed to calculate dashboard metrics');
    } finally {
      setLoading(false);
    }
  }, [devices, containers, alerts, healthData]);

  // Fetch health data periodically
  useEffect(() => {
    fetchHealthData();
    
    const interval = setInterval(fetchHealthData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const refetch = async () => {
    await fetchHealthData();
  };

  return {
    overview,
    deviceMetrics,
    healthData,
    loading: loading || devicesLoading || containersLoading,
    error,
    isConnected,
    refetch,
  };
}