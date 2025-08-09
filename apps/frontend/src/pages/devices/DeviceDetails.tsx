import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MetricCard, StatusBadge, DataTable, ActionDropdown, EmptyState } from '@/components/common';
import { useDevice } from '@/hooks/useDevices';
import { useContainers } from '@/hooks/useContainers';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';
import { useSystemLogs } from '@/hooks/useSystemMetrics';
// import { useDeviceMetrics } from '@/hooks/useWebSocket'; // TODO: Implement useDeviceMetrics hook
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeftIcon,
  ServerIcon,
  CpuIcon,
  MemoryStickIcon as MemoryIcon,
  HardDriveIcon,
  NetworkIcon,
  ActivityIcon,
  TerminalIcon,
  RefreshCw as RefreshCwIcon,
  PlayIcon,
  StopCircleIcon as StopIcon,
  RotateCcwIcon as RestartIcon,
  MonitorIcon,
  ShieldIcon,
  SettingsIcon,
  EditIcon
} from 'lucide-react';
import type { ContainerResponse } from '@infrastructor/shared-types';
import type { Column } from '@/components/common/DataTable';

export function DeviceDetails() {
  const { hostname } = useParams<{ hostname: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  
  const { device, loading: deviceLoading } = useDevice(hostname);
  const { containers, loading: containersLoading, startContainer, stopContainer, restartContainer } = useContainers(hostname);
  const { metrics, loading: metricsLoading } = useSystemMetrics(hostname);
  const { logs, loading: logsLoading } = useSystemLogs(hostname);
  // const { metrics: liveMetrics, isConnected } = useDeviceMetrics(hostname); // TODO: Implement useDeviceMetrics hook
  const liveMetrics = null;
  const isConnected = false;

  // Use live metrics if available, fall back to API metrics
  const currentMetrics = liveMetrics || metrics;

  if (deviceLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!device) {
    return (
      <div className="p-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Device Not Found</h1>
          <p className="text-gray-600 mb-4">The device "{hostname}" could not be found.</p>
          <Button onClick={() => navigate('/devices')}>
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Devices
          </Button>
        </div>
      </div>
    );
  }

  const containerColumns: Column<ContainerResponse>[] = [
    {
      key: 'name',
      title: 'Name',
      sortable: true,
      render: (value) => (
        <div className="font-medium text-gray-900">{value}</div>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (value) => <StatusBadge status={value} />,
    },
    {
      key: 'image',
      title: 'Image',
      render: (value) => (
        <div className="text-sm text-gray-600 max-w-xs truncate" title={value}>
          {value}
        </div>
      ),
    },
    {
      key: 'ports',
      title: 'Ports',
      render: (value) => (
        <div className="text-sm text-gray-600">
          {Array.isArray(value) && value.length > 0 
            ? value.map(port => port.public_port || port.private_port).join(', ')
            : '-'
          }
        </div>
      ),
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_, container) => (
        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => startContainer(hostname!, container.name)}
            disabled={container.status === 'running'}
            title="Start"
          >
            <PlayIcon className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => stopContainer(hostname!, container.name)}
            disabled={container.status !== 'running'}
            title="Stop"
          >
            <StopIcon className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => restartContainer(hostname!, container.name)}
            disabled={container.status !== 'running'}
            title="Restart"
          >
            <RestartIcon className="h-3 w-3" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="outline" onClick={() => navigate('/devices')}>
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <div className="flex items-center space-x-2">
              <ServerIcon className="h-6 w-6 text-gray-400" />
              <h1 className="text-3xl font-bold text-gray-900">{device.hostname}</h1>
              <StatusBadge status={device.status} />
            </div>
            <p className="text-gray-600">{device.description || 'No description'}</p>
            <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
              <span>Type: <Badge variant="secondary" className="capitalize">{device.device_type}</Badge></span>
              {device.ip_address && <span>IP: {device.ip_address}</span>}
              {isConnected && <span className="flex items-center"><div className="w-2 h-2 bg-green-500 rounded-full mr-1" />Live</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline">
            <RefreshCwIcon className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <ActionDropdown
            actions={[
              {
                label: 'Edit Device',
                icon: EditIcon,
                onClick: () => navigate(`/devices/${hostname}/edit`),
              },
              {
                label: 'Device Settings',
                icon: SettingsIcon,
                onClick: () => navigate(`/devices/${hostname}/settings`),
              },
              {
                label: 'Monitor Device',
                icon: MonitorIcon,
                onClick: () => setActiveTab('monitoring'),
                separator: true,
              },
              {
                label: 'Security Scan',
                icon: ShieldIcon,
                onClick: () => setActiveTab('security'),
              },
            ]}
          />
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="containers">Containers</TabsTrigger>
          <TabsTrigger value="storage">Storage</TabsTrigger>
          <TabsTrigger value="network">Network</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* System Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="CPU Usage"
              value={currentMetrics?.cpu?.usage_percent?.toFixed(1) || '0'}
              unit="%"
              icon={<CpuIcon className="h-5 w-5" />}
              loading={metricsLoading && !liveMetrics}
              changeType={
                !currentMetrics?.cpu?.usage_percent ? 'neutral' :
                currentMetrics.cpu.usage_percent > 80 ? 'decrease' : 
                currentMetrics.cpu.usage_percent > 60 ? 'neutral' : 'increase'
              }
            />

            <MetricCard
              title="Memory Usage"
              value={currentMetrics?.memory?.usage_percent?.toFixed(1) || '0'}
              unit="%"
              icon={<MemoryIcon className="h-5 w-5" />}
              loading={metricsLoading && !liveMetrics}
              changeType={
                !currentMetrics?.memory?.usage_percent ? 'neutral' :
                currentMetrics.memory.usage_percent > 85 ? 'decrease' : 
                currentMetrics.memory.usage_percent > 70 ? 'neutral' : 'increase'
              }
            />

            <MetricCard
              title="Disk Usage"
              value={currentMetrics?.disk?.usage_percent?.toFixed(1) || '0'}
              unit="%"
              icon={<HardDriveIcon className="h-5 w-5" />}
              loading={metricsLoading && !liveMetrics}
              changeType={
                !currentMetrics?.disk?.usage_percent ? 'neutral' :
                currentMetrics.disk.usage_percent > 90 ? 'decrease' : 
                currentMetrics.disk.usage_percent > 75 ? 'neutral' : 'increase'
              }
            />

            <MetricCard
              title="Network I/O"
              value={currentMetrics?.network?.bytes_sent ? `${(currentMetrics.network.bytes_sent / 1024 / 1024).toFixed(1)}` : '0'}
              unit="MB/s"
              icon={<NetworkIcon className="h-5 w-5" />}
              loading={metricsLoading && !liveMetrics}
              description="Outbound traffic"
            />
          </div>

          {/* Device Information */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Device Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Hostname</span>
                  <span className="text-sm font-medium">{device.hostname}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">IP Address</span>
                  <span className="text-sm font-medium">{device.ip_address || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Type</span>
                  <Badge variant="secondary" className="capitalize">{device.device_type}</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">SSH User</span>
                  <span className="text-sm font-medium">{device.ssh_username || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">SSH Port</span>
                  <span className="text-sm font-medium">{device.ssh_port || 22}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Monitoring</span>
                  <Badge variant={device.monitoring_enabled ? 'default' : 'secondary'}>
                    {device.monitoring_enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Last Seen</span>
                  <span className="text-sm font-medium">
                    {device.last_seen 
                      ? new Date(device.last_seen).toLocaleString()
                      : 'Never'
                    }
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>System Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">OS</span>
                  <span className="text-sm font-medium">{currentMetrics?.system?.os || 'Unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Architecture</span>
                  <span className="text-sm font-medium">{currentMetrics?.system?.arch || 'Unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">CPU Cores</span>
                  <span className="text-sm font-medium">{currentMetrics?.cpu?.cores || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Total Memory</span>
                  <span className="text-sm font-medium">
                    {currentMetrics?.memory?.total 
                      ? `${(currentMetrics.memory.total / 1024 / 1024 / 1024).toFixed(1)} GB`
                      : 'N/A'
                    }
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Total Disk</span>
                  <span className="text-sm font-medium">
                    {currentMetrics?.disk?.total
                      ? `${(currentMetrics.disk.total / 1024 / 1024 / 1024).toFixed(1)} GB`
                      : 'N/A'
                    }
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Uptime</span>
                  <span className="text-sm font-medium">{currentMetrics?.system?.uptime || 'N/A'}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="metrics" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <ActivityIcon className="h-5 w-5 mr-2" />
                Performance Metrics
                {isConnected && <Badge className="ml-2">Live</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {metricsLoading && !liveMetrics ? (
                <div className="text-center py-8">Loading metrics...</div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  Detailed metrics charts will be implemented here
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="containers" className="space-y-6">
          <DataTable
            data={containers || []}
            columns={containerColumns}
            loading={containersLoading}
            searchable
            searchPlaceholder="Search containers..."
            emptyMessage="No containers found on this device"
          />
        </TabsContent>

        <TabsContent value="storage" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Drive Health</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-gray-500">
                  Drive health monitoring will be implemented here
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Drive Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-gray-500">
                  Drive I/O statistics will be displayed here
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="network" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Network Ports</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-gray-500">
                  Network port information will be displayed here
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Network Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-gray-500">
                  Network configuration details will be shown here
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <TerminalIcon className="h-5 w-5 mr-2" />
                System Logs
              </CardTitle>
            </CardHeader>
            <CardContent>
              {logsLoading ? (
                <div className="text-center py-8">Loading logs...</div>
              ) : logs && logs.length > 0 ? (
                <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
                  {logs.map((line, index) => (
                    <div key={index} className="whitespace-pre-wrap">{line}</div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">No logs available</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}