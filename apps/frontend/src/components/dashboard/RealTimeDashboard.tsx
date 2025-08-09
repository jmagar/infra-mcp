/**
 * Real-Time Dashboard Component
 * Comprehensive infrastructure overview with live WebSocket data
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import {
  Activity,
  Server,
  Container,
  HardDrive,
  Wifi,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Bell,
  Zap,
} from 'lucide-react';
import { useWebSocket, useMetricsStream, useAlertsStream } from '@/hooks';
import { useDevices } from '@/hooks';
import { cn } from '@/lib/design-system';

interface SystemMetrics {
  device_id: string;
  hostname: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_rx: number;
  network_tx: number;
  load_average: number[];
  uptime: number;
  timestamp: string;
  status: 'healthy' | 'warning' | 'critical' | 'offline';
}

interface AlertData {
  id: string;
  type: 'error' | 'warning' | 'info';
  title: string;
  message: string;
  device_id?: string;
  timestamp: string;
  acknowledged: boolean;
}

export function RealTimeDashboard() {
  const [selectedTimeRange, setSelectedTimeRange] = useState<'5m' | '1h' | '24h'>('1h');
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // WebSocket connections
  const { devices } = useDevices();
  const deviceIds = devices?.map(d => d.id) || [];
  const metricsStream = useMetricsStream(deviceIds);
  const alertsStream = useAlertsStream();

  // Handle incoming metrics data
  useEffect(() => {
    if (metricsStream.lastMessage?.type === 'metrics') {
      const data = metricsStream.lastMessage.data as SystemMetrics;
      setSystemMetrics(prev => {
        const filtered = prev.filter(m => m.device_id !== data.device_id);
        return [...filtered, data].sort((a, b) => a.hostname.localeCompare(b.hostname));
      });
    }
  }, [metricsStream.lastMessage]);

  // Calculate summary statistics
  const summary = React.useMemo(() => {
    if (!systemMetrics.length) return {
      totalDevices: 0,
      healthyDevices: 0,
      avgCpuUsage: 0,
      avgMemoryUsage: 0,
      totalAlerts: alertsStream.alerts.length,
      criticalAlerts: alertsStream.alerts.filter((a: any) => a.type === 'error').length,
    };

    const healthy = systemMetrics.filter(m => m.status === 'healthy').length;
    const avgCpu = systemMetrics.reduce((acc, m) => acc + m.cpu_usage, 0) / systemMetrics.length;
    const avgMemory = systemMetrics.reduce((acc, m) => acc + m.memory_usage, 0) / systemMetrics.length;

    return {
      totalDevices: systemMetrics.length,
      healthyDevices: healthy,
      avgCpuUsage: avgCpu,
      avgMemoryUsage: avgMemory,
      totalAlerts: alertsStream.alerts.length,
      criticalAlerts: alertsStream.alerts.filter((a: any) => a.type === 'error').length,
    };
  }, [systemMetrics, alertsStream.alerts]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Force reconnection to get fresh data
    metricsStream.disconnect();
    setTimeout(() => {
      metricsStream.connect();
      setIsRefreshing(false);
    }, 1000);
  };

  const getStatusColor = (status: SystemMetrics['status']) => {
    switch (status) {
      case 'healthy': return 'text-green-500';
      case 'warning': return 'text-yellow-500';
      case 'critical': return 'text-red-500';
      case 'offline': return 'text-gray-500';
    }
  };

  const getStatusIcon = (status: SystemMetrics['status']) => {
    switch (status) {
      case 'healthy': return CheckCircle;
      case 'warning': return AlertTriangle;
      case 'critical': return XCircle;
      case 'offline': return XCircle;
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Real-Time Dashboard</h1>
          <p className="text-muted-foreground">
            Live infrastructure monitoring and system overview
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className="flex items-center gap-2 text-sm">
            <div className={cn(
              "w-2 h-2 rounded-full",
              metricsStream.isConnected ? "bg-green-500" : "bg-red-500"
            )} />
            <span className="text-muted-foreground">
              {metricsStream.isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-blue-500" />
              <div>
                <p className="text-sm text-muted-foreground">Total Devices</p>
                <p className="text-xl font-bold">{summary.totalDevices}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <div>
                <p className="text-sm text-muted-foreground">Healthy</p>
                <p className="text-xl font-bold">{summary.healthyDevices}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-orange-500" />
              <div>
                <p className="text-sm text-muted-foreground">Avg CPU</p>
                <p className="text-xl font-bold">{summary.avgCpuUsage.toFixed(1)}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-purple-500" />
              <div>
                <p className="text-sm text-muted-foreground">Avg Memory</p>
                <p className="text-xl font-bold">{summary.avgMemoryUsage.toFixed(1)}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-yellow-500" />
              <div>
                <p className="text-sm text-muted-foreground">Total Alerts</p>
                <p className="text-xl font-bold">{summary.totalAlerts}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <div>
                <p className="text-sm text-muted-foreground">Critical</p>
                <p className="text-xl font-bold">{summary.criticalAlerts}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Live System Metrics */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Live System Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {systemMetrics.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Server className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No devices connected</p>
                <p className="text-sm">Waiting for real-time data...</p>
              </div>
            ) : (
              systemMetrics.map((metrics) => {
                const StatusIcon = getStatusIcon(metrics.status);
                return (
                  <div key={metrics.device_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <StatusIcon className={cn("w-4 h-4", getStatusColor(metrics.status))} />
                        <span className="font-medium">{metrics.hostname}</span>
                        <Badge variant={metrics.status === 'healthy' ? 'default' : 'destructive'}>
                          {metrics.status}
                        </Badge>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {formatUptime(metrics.uptime)}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div>
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span>CPU</span>
                          <span>{metrics.cpu_usage.toFixed(1)}%</span>
                        </div>
                        <Progress value={metrics.cpu_usage} className="h-2" />
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span>Memory</span>
                          <span>{metrics.memory_usage.toFixed(1)}%</span>
                        </div>
                        <Progress value={metrics.memory_usage} className="h-2" />
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span>Disk</span>
                          <span>{metrics.disk_usage.toFixed(1)}%</span>
                        </div>
                        <Progress value={metrics.disk_usage} className="h-2" />
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        ↑{formatBytes(metrics.network_tx)}/s
                      </span>
                      <span className="flex items-center gap-1">
                        <TrendingDown className="w-3 h-3" />
                        ↓{formatBytes(metrics.network_rx)}/s
                      </span>
                      <span>Load: {metrics.load_average?.[0]?.toFixed(2) || '0.00'}</span>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Real-Time Alerts */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5" />
                Live Alerts
              </CardTitle>
              {alertsStream.alerts.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={alertsStream.clearAlerts}
                >
                  Clear All
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-2 max-h-96 overflow-y-auto">
            {alertsStream.alerts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500 opacity-50" />
                <p>All systems healthy</p>
                <p className="text-sm">No active alerts</p>
              </div>
            ) : (
              (alertsStream.alerts as AlertData[]).map((alert) => (
                <div
                  key={alert.id}
                  className={cn(
                    "border rounded-lg p-3",
                    alert.type === 'error' && "border-red-200 bg-red-50",
                    alert.type === 'warning' && "border-yellow-200 bg-yellow-50",
                    alert.type === 'info' && "border-blue-200 bg-blue-50"
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        {alert.type === 'error' && <XCircle className="w-4 h-4 text-red-500" />}
                        {alert.type === 'warning' && <AlertTriangle className="w-4 h-4 text-yellow-500" />}
                        {alert.type === 'info' && <CheckCircle className="w-4 h-4 text-blue-500" />}
                        <span className="font-medium text-sm">{alert.title}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mb-1">{alert.message}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}