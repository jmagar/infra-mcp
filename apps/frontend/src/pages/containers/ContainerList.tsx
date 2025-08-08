import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable, StatusBadge, MetricCard } from '@/components/common';
import { useContainers } from '@/hooks/useContainers';
import { useDevices } from '@/hooks/useDevices';
import { useResponsive, useResponsiveTable } from '@/hooks/useResponsive';
import { useNotificationEvents } from '@/hooks/useNotificationEvents';
import { gridConfigs, spacing, typography, layout } from '@/lib/responsive';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { 
  Box as CubeTransparentIcon,
  Play as PlayIcon,
  Pause as PauseIcon,
  RotateCw as ArrowPathIcon,
  Trash2 as TrashIcon,
  Eye as EyeIcon,
  RefreshCw as RefreshCwIcon,
  Filter as FilterIcon,
  Server as ServerIcon
} from 'lucide-react';
import type { ContainerResponse } from '@infrastructor/shared-types';
import type { Column } from '@/components/common/DataTable';

export function ContainerList() {
  const navigate = useNavigate();
  const { containers, loading, startContainer, stopContainer, restartContainer, removeContainer, refetch } = useContainers();
  const { devices } = useDevices();
  const { isMobile, isTablet } = useResponsive();
  const { notifyContainerAction } = useNotificationEvents();
  
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deviceFilter, setDeviceFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Filter containers based on selected filters and search
  const filteredContainers = containers?.filter(container => {
    if (statusFilter !== 'all' && container.status !== statusFilter) return false;
    if (deviceFilter !== 'all' && container.device_hostname !== deviceFilter) return false;
    if (searchTerm && !container.name.toLowerCase().includes(searchTerm.toLowerCase()) && 
        !container.image.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  }) || [];

  // Get unique device hostnames and container statuses for filter options
  const deviceHostnames = [...new Set(containers?.map(c => c.device_hostname) || [])];
  const containerStatuses = [...new Set(containers?.map(c => c.status) || [])];

  const handleContainerAction = async (action: 'start' | 'stop' | 'restart' | 'remove', deviceHostname: string, containerName: string) => {
    try {
      switch (action) {
        case 'start':
          await startContainer(deviceHostname, containerName);
          notifyContainerAction('start', containerName, deviceHostname, true);
          break;
        case 'stop':
          await stopContainer(deviceHostname, containerName);
          notifyContainerAction('stop', containerName, deviceHostname, true);
          break;
        case 'restart':
          await restartContainer(deviceHostname, containerName);
          notifyContainerAction('restart', containerName, deviceHostname, true);
          break;
        case 'remove':
          if (confirm(`Are you sure you want to remove container "${containerName}"?`)) {
            await removeContainer(deviceHostname, containerName);
            notifyContainerAction('remove', containerName, deviceHostname, true);
          }
          break;
      }
      await refetch();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`Failed to ${action} container:`, error);
      notifyContainerAction(action, containerName, deviceHostname, false, errorMessage);
    }
  };

  const allColumns: Column<ContainerResponse>[] = [
    {
      key: 'name',
      title: 'Container',
      sortable: true,
      render: (value, container) => (
        <div className="flex items-center space-x-2">
          <CubeTransparentIcon className="h-4 w-4 text-gray-400" />
          <div>
            <div className="font-medium text-gray-900">{container.name}</div>
            <div className="text-sm text-gray-500 truncate max-w-xs" title={container.image}>
              {container.image}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'device_hostname',
      title: 'Device',
      sortable: true,
      hideOnMobile: true,
      render: (value) => (
        <div className="flex items-center space-x-1">
          <ServerIcon className="h-3 w-3 text-gray-400" />
          <span className="text-sm font-medium">{value}</span>
        </div>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (value) => <StatusBadge status={value} />,
    },
    {
      key: 'ports',
      title: 'Ports',
      hideOnMobile: true,
      hideOnTablet: true,
      render: (value) => {
        if (!value || value.length === 0) return <span className="text-gray-400">None</span>;
        const portStrings = value.map(port => `${port.host_port}:${port.container_port}`);
        return (
          <div className="text-sm">
            {portStrings.length > 2 ? (
              <div title={portStrings.join(', ')}>
                {portStrings.slice(0, 2).join(', ')}
                <span className="text-gray-400"> +{portStrings.length - 2}</span>
              </div>
            ) : (
              portStrings.join(', ')
            )}
          </div>
        );
      },
    },
    {
      key: 'cpu_usage',
      title: 'CPU',
      hideOnMobile: true,
      render: (value) => {
        if (typeof value !== 'number') return <span className="text-gray-400">--</span>;
        return (
          <div className="flex items-center space-x-2">
            <div className="w-12 bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${value > 80 ? 'bg-red-500' : value > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
                style={{ width: `${Math.min(value, 100)}%` }}
              />
            </div>
            <span className="text-xs text-gray-600">{value.toFixed(1)}%</span>
          </div>
        );
      },
    },
    {
      key: 'memory_usage',
      title: 'Memory',
      hideOnMobile: true,
      render: (value) => {
        if (typeof value !== 'number') return <span className="text-gray-400">--</span>;
        return (
          <div className="flex items-center space-x-2">
            <div className="w-12 bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${value > 85 ? 'bg-red-500' : value > 70 ? 'bg-yellow-500' : 'bg-green-500'}`}
                style={{ width: `${Math.min(value, 100)}%` }}
              />
            </div>
            <span className="text-xs text-gray-600">{value.toFixed(1)}%</span>
          </div>
        );
      },
    },
    {
      key: 'created_at',
      title: 'Created',
      sortable: true,
      hideOnTablet: true,
      render: (value) => {
        if (!value) return <span className="text-gray-400">Unknown</span>;
        const date = new Date(value);
        return (
          <div>
            <div className="text-sm">{date.toLocaleDateString()}</div>
            <div className="text-xs text-gray-500">{date.toLocaleTimeString()}</div>
          </div>
        );
      },
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_, container) => (
        <div className="flex items-center space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/containers/${container.device_hostname}/${container.name}`)}
            title="View details"
          >
            <EyeIcon className="h-4 w-4" />
            {isMobile && <span className="ml-1 text-xs">View</span>}
          </Button>
          
          {!isMobile && (
            <>
              {container.status === 'running' ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleContainerAction('stop', container.device_hostname, container.name)}
                  title="Stop container"
                >
                  <PauseIcon className="h-4 w-4 text-yellow-600" />
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleContainerAction('start', container.device_hostname, container.name)}
                  title="Start container"
                >
                  <PlayIcon className="h-4 w-4 text-green-600" />
                </Button>
              )}
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleContainerAction('restart', container.device_hostname, container.name)}
                title="Restart container"
              >
                <ArrowPathIcon className="h-4 w-4 text-blue-600" />
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleContainerAction('remove', container.device_hostname, container.name)}
                className="text-red-600 hover:text-red-800"
                title="Remove container"
              >
                <TrashIcon className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  // Apply responsive filtering to columns
  const columns = useResponsiveTable(allColumns);

  // Calculate stats
  const totalContainers = containers?.length || 0;
  const runningContainers = containers?.filter(c => c.status === 'running')?.length || 0;
  const stoppedContainers = containers?.filter(c => c.status === 'exited')?.length || 0;
  const errorContainers = containers?.filter(c => c.status === 'failed' || c.status === 'error')?.length || 0;

  return (
    <div className={`${spacing.padding.page} ${layout.sectionWrapper}`}>
      {/* Header */}
      <div className={layout.pageHeader.full}>
        <div>
          <h1 className={typography.heading.page}>Containers</h1>
          <p className={`${typography.body.normal} text-gray-600`}>
            Manage Docker containers across your infrastructure ({filteredContainers.length} total)
          </p>
        </div>
        <div className={layout.navButtons.full}>
          <Button variant="outline" onClick={refetch} size={isMobile ? "sm" : "default"}>
            <RefreshCwIcon className="h-4 w-4 mr-2" />
            {!isMobile && "Refresh"}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className={`${gridConfigs.dashboardMetrics.full} ${spacing.gap.full}`}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Containers</CardTitle>
            <CubeTransparentIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalContainers}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <div className="h-2 w-2 bg-green-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningContainers}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Stopped</CardTitle>
            <div className="h-2 w-2 bg-gray-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stoppedContainers}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Errors</CardTitle>
            <div className="h-2 w-2 bg-red-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{errorContainers}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardHeader>
          <CardTitle className={typography.heading.card}>Search & Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`${layout.sectionWrapper} space-y-4`}>
            {/* Search */}
            <div>
              <Label htmlFor="search" className="text-xs">Search Containers</Label>
              <Input
                id="search"
                placeholder="Search by name or image..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="mt-1"
              />
            </div>
            
            {/* Filters */}
            <div className={`flex flex-wrap ${spacing.gap.mobile}`}>
              <div className="flex flex-col space-y-1">
                <Label className="text-xs">Status</Label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="flex h-8 w-32 rounded-md border border-input bg-background px-3 py-1 text-sm"
                >
                  <option value="all">All Status</option>
                  {containerStatuses.map(status => (
                    <option key={status} value={status} className="capitalize">{status}</option>
                  ))}
                </select>
              </div>
              
              <div className="flex flex-col space-y-1">
                <Label className="text-xs">Device</Label>
                <select
                  value={deviceFilter}
                  onChange={(e) => setDeviceFilter(e.target.value)}
                  className="flex h-8 w-40 rounded-md border border-input bg-background px-3 py-1 text-sm"
                >
                  <option value="all">All Devices</option>
                  {deviceHostnames.map(hostname => (
                    <option key={hostname} value={hostname}>{hostname}</option>
                  ))}
                </select>
              </div>
              
              {(statusFilter !== 'all' || deviceFilter !== 'all' || searchTerm) && (
                <div className="flex items-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setStatusFilter('all');
                      setDeviceFilter('all');
                      setSearchTerm('');
                    }}
                  >
                    Clear All
                  </Button>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Container Table */}
      <DataTable
        data={filteredContainers}
        columns={columns}
        loading={loading}
        searchable={false} // We have custom search
        pagination={{ pageSize: 15 }}
        onRowClick={(container) => navigate(`/containers/${container.device_hostname}/${container.name}`)}
        emptyMessage="No containers found. Deploy your first container to get started."
      />
    </div>
  );
}