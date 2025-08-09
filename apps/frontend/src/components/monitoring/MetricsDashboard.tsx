/**
 * Comprehensive Metrics Dashboard Component
 * Displays real-time system metrics with charts and alerts
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MetricCard, LoadingSpinner } from '@/components/common';
import { 
  CpuIcon,
  MemoryStickIcon as MemoryIcon,
  HardDriveIcon,
  NetworkIcon,
  ThermometerIcon,
  ZapIcon,
  ActivityIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  AlertTriangleIcon,
  RefreshCwIcon
} from 'lucide-react';

interface SystemMetrics {
  cpu: {
    usage_percent: number;
    cores: number;
    temperature?: number;
    load_average?: number[];
  };
  memory: {
    usage_percent: number;
    total: number;
    used: number;
    available: number;
  };
  disk: {
    usage_percent: number;
    total: number;
    used: number;
    available: number;
    io_read_bytes?: number;
    io_write_bytes?: number;
  };
  network: {
    bytes_sent: number;
    bytes_received: number;
    packets_sent: number;
    packets_received: number;
  };
  system: {
    uptime: string;
    boot_time: string;
    processes: number;
    users: number;
  };
}

interface MetricsDashboardProps {
  hostname: string;
  metrics?: SystemMetrics;
  loading?: boolean;
  error?: string;
  onRefresh?: () => void;
  realTimeEnabled?: boolean;
}

export function MetricsDashboard({
  hostname,
  metrics,
  loading = false,
  error,
  onRefresh,
  realTimeEnabled = false,
}: MetricsDashboardProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const [autoRefresh, setAutoRefresh] = useState(false);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (autoRefresh && onRefresh) {
      interval = setInterval(() => {
        onRefresh();
      }, 5000); // Refresh every 5 seconds
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [autoRefresh, onRefresh]);

  const getMetricStatus = (value: number, warning: number, critical: number) => {
    if (value >= critical) return 'critical';
    if (value >= warning) return 'warning';
    return 'healthy';
  };

  const formatBytes = (bytes: number) => {
    const gb = bytes / 1024 / 1024 / 1024;
    if (gb >= 1) return `${gb.toFixed(1)} GB`;
    const mb = bytes / 1024 / 1024;
    if (mb >= 1) return `${mb.toFixed(1)} MB`;
    const kb = bytes / 1024;
    return `${kb.toFixed(1)} KB`;
  };

  const formatNetworkSpeed = (bytesPerSec: number) => {
    const mbps = bytesPerSec / 1024 / 1024;
    if (mbps >= 1) return `${mbps.toFixed(1)} MB/s`;
    const kbps = bytesPerSec / 1024;
    return `${kbps.toFixed(1)} KB/s`;
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <LoadingSpinner />
          <span className="ml-2">Loading metrics...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12 text-center">
          <div>
            <AlertTriangleIcon className="h-8 w-8 text-red-500 mx-auto mb-2" />
            <p className="text-red-600 mb-4">Failed to load metrics</p>
            <p className="text-sm text-gray-500 mb-4">{error}</p>
            {onRefresh && (
              <Button onClick={onRefresh} variant="outline">
                <RefreshCwIcon className="h-4 w-4 mr-2" />
                Retry
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!metrics) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <p className="text-gray-500">No metrics available</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">System Metrics</h2>
          <p className="text-gray-600">Real-time performance monitoring for {hostname}</p>
        </div>
        <div className="flex items-center space-x-2">
          {realTimeEnabled && (
            <Badge variant="default" className="bg-green-600">
              <div className="w-2 h-2 bg-white rounded-full mr-1 animate-pulse" />
              Live
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={autoRefresh ? 'bg-blue-50 border-blue-300' : ''}
          >
            <ActivityIcon className="h-4 w-4 mr-2" />
            Auto Refresh {autoRefresh ? 'On' : 'Off'}
          </Button>
          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCwIcon className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="CPU Usage"
          value={metrics.cpu.usage_percent.toFixed(1)}
          unit="%"
          icon={<CpuIcon className="h-5 w-5" />}
          description={`${metrics.cpu.cores} cores`}
          changeType={
            getMetricStatus(metrics.cpu.usage_percent, 70, 90) === 'critical' ? 'decrease' :
            getMetricStatus(metrics.cpu.usage_percent, 70, 90) === 'warning' ? 'neutral' : 'increase'
          }
        />

        <MetricCard
          title="Memory Usage"
          value={metrics.memory.usage_percent.toFixed(1)}
          unit="%"
          icon={<MemoryIcon className="h-5 w-5" />}
          description={`${formatBytes(metrics.memory.used)} / ${formatBytes(metrics.memory.total)}`}
          changeType={
            getMetricStatus(metrics.memory.usage_percent, 80, 95) === 'critical' ? 'decrease' :
            getMetricStatus(metrics.memory.usage_percent, 80, 95) === 'warning' ? 'neutral' : 'increase'
          }
        />

        <MetricCard
          title="Disk Usage"
          value={metrics.disk.usage_percent.toFixed(1)}
          unit="%"
          icon={<HardDriveIcon className="h-5 w-5" />}
          description={`${formatBytes(metrics.disk.used)} / ${formatBytes(metrics.disk.total)}`}
          changeType={
            getMetricStatus(metrics.disk.usage_percent, 85, 95) === 'critical' ? 'decrease' :
            getMetricStatus(metrics.disk.usage_percent, 85, 95) === 'warning' ? 'neutral' : 'increase'
          }
        />

        <MetricCard
          title="Network I/O"
          value={formatNetworkSpeed(metrics.network.bytes_sent)}
          unit="out"
          icon={<NetworkIcon className="h-5 w-5" />}
          description={`${formatNetworkSpeed(metrics.network.bytes_received)} in`}
          changeType="neutral"
        />
      </div>

      {/* Detailed Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="cpu">CPU</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="disk">Disk</TabsTrigger>
          <TabsTrigger value="network">Network</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Performance Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Performance Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm">CPU Load</span>
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full ${
                      getMetricStatus(metrics.cpu.usage_percent, 70, 90) === 'critical' ? 'bg-red-500' :
                      getMetricStatus(metrics.cpu.usage_percent, 70, 90) === 'warning' ? 'bg-yellow-500' : 'bg-green-500'
                    }`} />
                    <Badge variant={
                      getMetricStatus(metrics.cpu.usage_percent, 70, 90) === 'critical' ? 'destructive' :
                      getMetricStatus(metrics.cpu.usage_percent, 70, 90) === 'warning' ? 'secondary' : 'default'
                    }>
                      {getMetricStatus(metrics.cpu.usage_percent, 70, 90)}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Memory Load</span>
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full ${
                      getMetricStatus(metrics.memory.usage_percent, 80, 95) === 'critical' ? 'bg-red-500' :
                      getMetricStatus(metrics.memory.usage_percent, 80, 95) === 'warning' ? 'bg-yellow-500' : 'bg-green-500'
                    }`} />
                    <Badge variant={
                      getMetricStatus(metrics.memory.usage_percent, 80, 95) === 'critical' ? 'destructive' :
                      getMetricStatus(metrics.memory.usage_percent, 80, 95) === 'warning' ? 'secondary' : 'default'
                    }>
                      {getMetricStatus(metrics.memory.usage_percent, 80, 95)}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Disk Space</span>
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full ${
                      getMetricStatus(metrics.disk.usage_percent, 85, 95) === 'critical' ? 'bg-red-500' :
                      getMetricStatus(metrics.disk.usage_percent, 85, 95) === 'warning' ? 'bg-yellow-500' : 'bg-green-500'
                    }`} />
                    <Badge variant={
                      getMetricStatus(metrics.disk.usage_percent, 85, 95) === 'critical' ? 'destructive' :
                      getMetricStatus(metrics.disk.usage_percent, 85, 95) === 'warning' ? 'secondary' : 'default'
                    }>
                      {getMetricStatus(metrics.disk.usage_percent, 85, 95)}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* System Info */}
            <Card>
              <CardHeader>
                <CardTitle>System Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Uptime</span>
                  <span className="text-sm font-medium">{metrics.system.uptime}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Processes</span>
                  <span className="text-sm font-medium">{metrics.system.processes}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Users</span>
                  <span className="text-sm font-medium">{metrics.system.users}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Boot Time</span>
                  <span className="text-sm font-medium">{new Date(metrics.system.boot_time).toLocaleString()}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Individual metric tabs would go here with more detailed charts */}
        <TabsContent value="cpu">
          <Card>
            <CardHeader>
              <CardTitle>CPU Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                Detailed CPU metrics and charts will be implemented here
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Other tabs similar structure... */}
      </Tabs>
    </div>
  );
}