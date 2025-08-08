/**
 * System Monitoring Dashboard
 * Comprehensive monitoring interface combining all infrastructure components
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { DataTable } from '@/components/common';
import { useDevices } from '@/hooks/useDevices';
import { useContainers } from '@/hooks/useContainers';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';
import { useResponsive } from '@/hooks/useResponsive';
import {
  Activity,
  Server,
  Container,
  Database,
  HardDrive,
  Cpu,
  MemoryStick,
  Network,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Eye,
  Settings,
  BarChart3,
} from 'lucide-react';
import type { DeviceResponse, ContainerResponse } from '@infrastructor/shared-types';
import type { Column } from '@/components/common/DataTable';

export function SystemMonitoring() {
  const navigate = useNavigate();
  const { isMobile } = useResponsive();
  
  const { devices, loading: devicesLoading, refetch: refetchDevices } = useDevices();
  const { containers, loading: containersLoading, refetch: refetchContainers } = useContainers();
  const { metrics, loading: metricsLoading, refetch: refetchMetrics } = useSystemMetrics();
  
  const [activeTab, setActiveTab] = useState('overview');
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        refetchDevices();
        refetchContainers();
        refetchMetrics();
      }, 30000); // Refresh every 30 seconds
      
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refetchDevices, refetchContainers, refetchMetrics]);

  const loading = devicesLoading || containersLoading || metricsLoading;

  // Calculate system statistics
  const totalDevices = devices?.length || 0;
  const onlineDevices = devices?.filter(d => d.status === 'online')?.length || 0;
  const offlineDevices = devices?.filter(d => d.status === 'offline')?.length || 0;
  const totalContainers = containers?.length || 0;
  const runningContainers = containers?.filter(c => c.status === 'running')?.length || 0;
  const stoppedContainers = containers?.filter(c => c.status === 'exited' || c.status === 'stopped')?.length || 0;

  // Get system health status
  const getOverallHealth = () => {
    const deviceHealth = totalDevices > 0 ? onlineDevices / totalDevices : 1;
    const containerHealth = totalContainers > 0 ? runningContainers / totalContainers : 1;
    
    if (deviceHealth >= 0.9 && containerHealth >= 0.8) return 'excellent';
    if (deviceHealth >= 0.7 && containerHealth >= 0.6) return 'good';
    if (deviceHealth >= 0.5 || containerHealth >= 0.4) return 'warning';
    return 'critical';
  };

  const overallHealth = getOverallHealth();

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'excellent': return 'text-green-600';
      case 'good': return 'text-green-500';
      case 'warning': return 'text-yellow-600';
      case 'critical': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'excellent': return <CheckCircle className="h-5 w-5" />;
      case 'good': return <Activity className="h-5 w-5" />;
      case 'warning': return <AlertTriangle className="h-5 w-5" />;
      case 'critical': return <AlertTriangle className="h-5 w-5" />;
      default: return <Activity className="h-5 w-5" />;
    }
  };

  // Device columns for monitoring
  const deviceColumns: Column<DeviceResponse>[] = [
    {
      key: 'hostname',
      title: 'Device',
      sortable: true,
      render: (value, device) => (
        <div className="flex items-center space-x-2">
          <Server className="h-4 w-4 text-blue-500" />
          <div>
            <div className="font-medium">{device.hostname}</div>
            <div className="text-sm text-muted-foreground">{device.device_type}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (value) => (
        <Badge variant={value === 'online' ? 'default' : 'destructive'}>
          {value}
        </Badge>
      ),
    },
    {
      key: 'last_seen',
      title: 'Last Seen',
      hideOnMobile: true,
      render: (value) => {
        if (!value) return <span className="text-muted-foreground">Never</span>;
        const date = new Date(value);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return <span className="text-green-600">Just now</span>;
        if (diffMins < 60) return <span className="text-green-600">{diffMins}m ago</span>;
        if (diffMins < 1440) return <span className="text-yellow-600">{Math.floor(diffMins / 60)}h ago</span>;
        return <span className="text-red-600">{Math.floor(diffMins / 1440)}d ago</span>;
      },
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_, device) => (
        <div className="flex space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/devices/${device.hostname}`)}
          >
            <Eye className="h-4 w-4" />
            {!isMobile && <span className="ml-1">View</span>}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/zfs/${device.hostname}`)}
          >
            <Database className="h-4 w-4" />
            {!isMobile && <span className="ml-1">ZFS</span>}
          </Button>
        </div>
      ),
    },
  ];

  // Container columns for monitoring
  const containerColumns: Column<ContainerResponse>[] = [
    {
      key: 'name',
      title: 'Container',
      sortable: true,
      render: (value, container) => (
        <div className="flex items-center space-x-2">
          <Container className="h-4 w-4 text-purple-500" />
          <div>
            <div className="font-medium">{container.name}</div>
            <div className="text-sm text-muted-foreground">{container.device_id}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (value) => (
        <Badge variant={value === 'running' ? 'default' : 'secondary'}>
          {value}
        </Badge>
      ),
    },
    {
      key: 'image',
      title: 'Image',
      hideOnMobile: true,
      render: (value) => (
        <span className="font-mono text-sm">{value.split(':')[0]}</span>
      ),
    },
    {
      key: 'created_at',
      title: 'Created',
      hideOnMobile: true,
      render: (value) => {
        const date = new Date(value);
        return (
          <span className="text-sm">
            {date.toLocaleDateString()}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-6 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">System Monitoring</h1>
          <p className="text-muted-foreground">
            Real-time infrastructure monitoring and management
          </p>
        </div>
        <div className="flex space-x-2">
          <Button
            variant={autoRefresh ? "default" : "outline"}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Auto ON' : 'Auto OFF'}
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              refetchDevices();
              refetchContainers();
              refetchMetrics();
            }}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="devices">Devices</TabsTrigger>
          <TabsTrigger value="containers">Containers</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* System Health Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">System Health</CardTitle>
                <div className={getHealthColor(overallHealth)}>
                  {getHealthIcon(overallHealth)}
                </div>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${getHealthColor(overallHealth)}`}>
                  {overallHealth.charAt(0).toUpperCase() + overallHealth.slice(1)}
                </div>
                <p className="text-xs text-muted-foreground">
                  Overall system status
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Devices</CardTitle>
                <Server className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{onlineDevices}/{totalDevices}</div>
                <p className="text-xs text-muted-foreground">
                  {offlineDevices > 0 ? `${offlineDevices} offline` : 'All online'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Containers</CardTitle>
                <Container className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{runningContainers}/{totalContainers}</div>
                <p className="text-xs text-muted-foreground">
                  {stoppedContainers > 0 ? `${stoppedContainers} stopped` : 'All running'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Alerts</CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {offlineDevices + stoppedContainers}
                </div>
                <p className="text-xs text-muted-foreground">
                  Active alerts
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Button
                  variant="outline"
                  className="h-20 flex flex-col space-y-2"
                  onClick={() => navigate('/devices')}
                >
                  <Server className="h-6 w-6" />
                  <span>Manage Devices</span>
                </Button>
                <Button
                  variant="outline"
                  className="h-20 flex flex-col space-y-2"
                  onClick={() => navigate('/containers')}
                >
                  <Container className="h-6 w-6" />
                  <span>Containers</span>
                </Button>
                <Button
                  variant="outline"
                  className="h-20 flex flex-col space-y-2"
                  onClick={() => navigate('/zfs')}
                >
                  <Database className="h-6 w-6" />
                  <span>ZFS Management</span>
                </Button>
                <Button
                  variant="outline"
                  className="h-20 flex flex-col space-y-2"
                  onClick={() => navigate('/monitoring')}
                >
                  <BarChart3 className="h-6 w-6" />
                  <span>Monitoring</span>
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Device Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {devices?.slice(0, 5).map(device => (
                    <div key={device.id} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Server className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{device.hostname}</div>
                          <div className="text-sm text-muted-foreground">{device.device_type}</div>
                        </div>
                      </div>
                      <Badge variant={device.status === 'online' ? 'default' : 'destructive'}>
                        {device.status}
                      </Badge>
                    </div>
                  )) || (
                    <div className="text-center text-muted-foreground py-4">
                      No devices found
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Container Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {containers?.slice(0, 5).map(container => (
                    <div key={container.id} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Container className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <div className="font-medium">{container.name}</div>
                          <div className="text-sm text-muted-foreground">{container.image}</div>
                        </div>
                      </div>
                      <Badge variant={container.status === 'running' ? 'default' : 'secondary'}>
                        {container.status}
                      </Badge>
                    </div>
                  )) || (
                    <div className="text-center text-muted-foreground py-4">
                      No containers found
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="devices">
          <Card>
            <CardHeader>
              <CardTitle>Device Monitoring</CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                data={devices || []}
                columns={deviceColumns}
                loading={devicesLoading}
                searchable
                searchPlaceholder="Search devices..."
                emptyMessage="No devices found"
                onRowClick={(device) => navigate(`/devices/${device.hostname}`)}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="containers">
          <Card>
            <CardHeader>
              <CardTitle>Container Monitoring</CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                data={containers || []}
                columns={containerColumns}
                loading={containersLoading}
                searchable
                searchPlaceholder="Search containers..."
                emptyMessage="No containers found"
                pagination={{ pageSize: 20 }}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance">
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
                  <Cpu className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {metrics?.cpu_usage ? `${metrics.cpu_usage.toFixed(1)}%` : 'N/A'}
                  </div>
                  <Progress value={metrics?.cpu_usage || 0} className="mt-2" />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
                  <MemoryStick className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {metrics?.memory_usage ? `${metrics.memory_usage.toFixed(1)}%` : 'N/A'}
                  </div>
                  <Progress value={metrics?.memory_usage || 0} className="mt-2" />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Disk Usage</CardTitle>
                  <HardDrive className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {metrics?.disk_usage ? `${metrics.disk_usage.toFixed(1)}%` : 'N/A'}
                  </div>
                  <Progress value={metrics?.disk_usage || 0} className="mt-2" />
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center text-muted-foreground py-8">
                  <BarChart3 className="h-16 w-16 mx-auto mb-4" />
                  <p>Detailed performance charts would be displayed here</p>
                  <p className="text-sm">Integration with monitoring tools like Grafana recommended</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}