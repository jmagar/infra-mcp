/**
 * ZFS Management Page
 * Comprehensive interface for ZFS pool, dataset, and snapshot management
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { DataTable } from '@/components/common';
import { useZFS } from '@/hooks/useZFS';
import { useDevices } from '@/hooks/useDevices';
import { useResponsive } from '@/hooks/useResponsive';
import {
  Database as DatabaseIcon,
  HardDrive as HardDriveIcon,
  Camera as CameraIcon,
  Activity as ActivityIcon,
  TrendingUp as TrendingUpIcon,
  AlertTriangle as AlertTriangleIcon,
  CheckCircle as CheckCircleIcon,
  RefreshCw as RefreshCwIcon,
  Plus as PlusIcon,
  Eye as EyeIcon,
  Trash2 as Trash2Icon,
  Download as DownloadIcon,
  Upload as UploadIcon
} from 'lucide-react';
import type { 
  ZFSPoolResponse, 
  ZFSDatasetResponse, 
  ZFSSnapshotResponse,
  ZFSHealthCheck 
} from '@infrastructor/shared-types';
import type { Column } from '@/components/common/DataTable';

interface ZFSManagementProps {
  hostname?: string;
}

export function ZFSManagement({ hostname: propHostname }: ZFSManagementProps) {
  const { hostname: paramHostname } = useParams<{ hostname: string }>();
  const hostname = propHostname || paramHostname;
  const navigate = useNavigate();
  const { isMobile } = useResponsive();
  
  const {
    pools,
    datasets,
    snapshots,
    healthCheck,
    arcStats,
    loading,
    error,
    refetch,
    createSnapshot,
    deleteSnapshot,
    sendSnapshot,
    cloneSnapshot,
  } = useZFS(hostname);

  const [activeTab, setActiveTab] = useState('overview');

  if (!hostname) {
    return <ZFSDeviceSelection />;
  }

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`;
  };

  const getHealthColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
      case 'healthy':
        return 'text-green-600';
      case 'degraded':
        return 'text-yellow-600';
      case 'faulted':
      case 'offline':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
      case 'healthy':
        return <CheckCircleIcon className="h-4 w-4" />;
      case 'degraded':
        return <AlertTriangleIcon className="h-4 w-4" />;
      case 'faulted':
      case 'offline':
        return <AlertTriangleIcon className="h-4 w-4" />;
      default:
        return <ActivityIcon className="h-4 w-4" />;
    }
  };

  // Pool columns
  const poolColumns: Column<ZFSPoolResponse>[] = [
    {
      key: 'name',
      title: 'Pool Name',
      sortable: true,
      render: (value, pool) => (
        <div className="flex items-center space-x-2">
          <DatabaseIcon className="h-4 w-4 text-blue-500" />
          <div>
            <div className="font-medium">{pool.name}</div>
            <div className="text-sm text-muted-foreground">
              {pool.guid && `GUID: ${pool.guid.slice(0, 8)}...`}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'health',
      title: 'Health',
      sortable: true,
      render: (value) => (
        <div className={`flex items-center space-x-1 ${getHealthColor(value)}`}>
          {getHealthIcon(value)}
          <Badge variant={value === 'ONLINE' ? 'default' : 'destructive'}>
            {value}
          </Badge>
        </div>
      ),
    },
    {
      key: 'capacity',
      title: 'Capacity',
      hideOnMobile: true,
      render: (value, pool) => (
        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span>{formatBytes(pool.allocated)}</span>
            <span>{pool.capacity}%</span>
          </div>
          <Progress value={pool.capacity} className="h-2" />
          <div className="text-xs text-muted-foreground">
            {formatBytes(pool.free)} free of {formatBytes(pool.size)}
          </div>
        </div>
      ),
    },
    {
      key: 'dedupratio',
      title: 'Dedup Ratio',
      hideOnMobile: true,
      render: (value) => `${value.toFixed(2)}x`,
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_, pool) => (
        <div className="flex space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/zfs/${hostname}/pools/${pool.name}`)}
          >
            <EyeIcon className="h-4 w-4" />
            {!isMobile && <span className="ml-1">View</span>}
          </Button>
        </div>
      ),
    },
  ];

  // Dataset columns
  const datasetColumns: Column<ZFSDatasetResponse>[] = [
    {
      key: 'name',
      title: 'Dataset',
      sortable: true,
      render: (value, dataset) => (
        <div className="flex items-center space-x-2">
          <HardDriveIcon className="h-4 w-4 text-orange-500" />
          <div>
            <div className="font-medium">{dataset.name}</div>
            <div className="text-sm text-muted-foreground capitalize">
              {dataset.type}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'used',
      title: 'Used',
      sortable: true,
      render: (value) => formatBytes(value),
    },
    {
      key: 'available',
      title: 'Available',
      hideOnMobile: true,
      render: (value) => formatBytes(value),
    },
    {
      key: 'compressratio',
      title: 'Compression',
      hideOnMobile: true,
      render: (value) => `${value.toFixed(2)}x`,
    },
    {
      key: 'mounted',
      title: 'Mounted',
      hideOnTablet: true,
      render: (value) => (
        <Badge variant={value ? 'default' : 'secondary'}>
          {value ? 'Yes' : 'No'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_, dataset) => (
        <div className="flex space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/zfs/${hostname}/datasets/${dataset.name}`)}
          >
            <EyeIcon className="h-4 w-4" />
            {!isMobile && <span className="ml-1">View</span>}
          </Button>
        </div>
      ),
    },
  ];

  // Snapshot columns
  const snapshotColumns: Column<ZFSSnapshotResponse>[] = [
    {
      key: 'name',
      title: 'Snapshot',
      sortable: true,
      render: (value, snapshot) => (
        <div className="flex items-center space-x-2">
          <CameraIcon className="h-4 w-4 text-purple-500" />
          <div>
            <div className="font-medium">{snapshot.name}</div>
            <div className="text-sm text-muted-foreground">
              {snapshot.dataset_name}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'used',
      title: 'Size',
      sortable: true,
      render: (value) => formatBytes(value),
    },
    {
      key: 'creation_time',
      title: 'Created',
      sortable: true,
      hideOnMobile: true,
      render: (value) => {
        const date = new Date(value);
        return (
          <div>
            <div className="text-sm">{date.toLocaleDateString()}</div>
            <div className="text-xs text-muted-foreground">
              {date.toLocaleTimeString()}
            </div>
          </div>
        );
      },
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_, snapshot) => (
        <div className="flex space-x-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => cloneSnapshot(snapshot.name, `${snapshot.name}-clone`)}
            disabled={loading}
          >
            <DownloadIcon className="h-4 w-4" />
            {!isMobile && <span className="ml-1">Clone</span>}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => sendSnapshot(snapshot.name)}
            disabled={loading}
          >
            <UploadIcon className="h-4 w-4" />
            {!isMobile && <span className="ml-1">Send</span>}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => deleteSnapshot(snapshot.name)}
            className="text-red-600 hover:text-red-800"
            disabled={loading}
          >
            <Trash2Icon className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">ZFS Management</h1>
          <p className="text-muted-foreground">
            Manage ZFS pools, datasets, and snapshots on {hostname}
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={refetch} disabled={loading}>
            <RefreshCwIcon className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <AlertTriangleIcon className="h-4 w-4 text-red-600" />
              <span className="text-red-800">{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="pools">Pools</TabsTrigger>
          <TabsTrigger value="datasets">Datasets</TabsTrigger>
          <TabsTrigger value="snapshots">Snapshots</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Health Overview */}
          {healthCheck && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Overall Health</CardTitle>
                  <ActivityIcon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${getHealthColor(healthCheck.overall_status)}`}>
                    {healthCheck.overall_status}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {healthCheck.healthy_pools}/{healthCheck.total_pools} pools healthy
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Capacity</CardTitle>
                  <DatabaseIcon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatBytes(healthCheck.total_capacity_bytes)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatBytes(healthCheck.used_capacity_bytes)} used
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Compression Ratio</CardTitle>
                  <TrendingUpIcon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {healthCheck.compression_ratio.toFixed(2)}x
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Space savings from compression
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Dedup Ratio</CardTitle>
                  <TrendingUpIcon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {healthCheck.deduplication_ratio.toFixed(2)}x
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Space savings from deduplication
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Recommendations */}
          {healthCheck?.recommendations && healthCheck.recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {healthCheck.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <AlertTriangleIcon className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{rec}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="pools">
          <Card>
            <CardHeader>
              <CardTitle>ZFS Pools</CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                data={pools || []}
                columns={poolColumns}
                loading={loading}
                searchable
                searchPlaceholder="Search pools..."
                emptyMessage="No ZFS pools found"
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="datasets">
          <Card>
            <CardHeader>
              <CardTitle>ZFS Datasets</CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                data={datasets || []}
                columns={datasetColumns}
                loading={loading}
                searchable
                searchPlaceholder="Search datasets..."
                emptyMessage="No ZFS datasets found"
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="snapshots">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>ZFS Snapshots</CardTitle>
              <Button 
                onClick={() => {
                  // Create snapshot dialog would go here
                  console.log('Create snapshot dialog');
                }}
              >
                <PlusIcon className="h-4 w-4 mr-2" />
                Create Snapshot
              </Button>
            </CardHeader>
            <CardContent>
              <DataTable
                data={snapshots || []}
                columns={snapshotColumns}
                loading={loading}
                searchable
                searchPlaceholder="Search snapshots..."
                emptyMessage="No ZFS snapshots found"
                pagination={{ pageSize: 20 }}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance">
          {arcStats && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>ZFS ARC Statistics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div>
                      <h4 className="font-semibold mb-2">Cache Size</h4>
                      <div className="space-y-1">
                        <div className="flex justify-between">
                          <span>Current:</span>
                          <span>{formatBytes(arcStats.size)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Target:</span>
                          <span>{formatBytes(arcStats.target_size)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Max:</span>
                          <span>{formatBytes(arcStats.max_size)}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="font-semibold mb-2">Hit Ratio</h4>
                      <div className="space-y-1">
                        <div className="text-2xl font-bold text-green-600">
                          {(arcStats.hit_ratio * 100).toFixed(1)}%
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {arcStats.hits.toLocaleString()} hits, {arcStats.misses.toLocaleString()} misses
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="font-semibold mb-2">Data Distribution</h4>
                      <div className="space-y-1">
                        <div className="flex justify-between">
                          <span>Metadata:</span>
                          <span>{formatBytes(arcStats.metadata_size)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Data:</span>
                          <span>{formatBytes(arcStats.data_size)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Header:</span>
                          <span>{formatBytes(arcStats.header_size)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Device Selection Component for ZFS Management
function ZFSDeviceSelection() {
  const navigate = useNavigate();
  const { devices, loading } = useDevices();
  const { isMobile } = useResponsive();

  // Filter devices that might have ZFS support (servers, storage devices)
  const zfsCapableDevices = devices?.filter(device => 
    ['server', 'storage', 'nas'].includes(device.device_type.toLowerCase()) && 
    device.status === 'online'
  ) || [];

  return (
    <div className="space-y-6 p-6">
      <div className="text-center">
        <DatabaseIcon className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
        <h1 className="text-3xl font-bold text-gray-900">ZFS Management</h1>
        <p className="text-muted-foreground mt-2">
          Select a device to manage ZFS pools, datasets, and snapshots
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-muted rounded w-3/4 mb-2" />
                <div className="h-3 bg-muted rounded w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : zfsCapableDevices.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {zfsCapableDevices.map((device) => (
            <Card 
              key={device.id} 
              className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-primary/50"
              onClick={() => navigate(`/zfs/${device.hostname}`)}
            >
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-2">
                    <HardDriveIcon className="h-5 w-5 text-primary" />
                    <h3 className="font-semibold text-lg">{device.hostname}</h3>
                  </div>
                  <Badge variant={device.status === 'online' ? 'default' : 'secondary'}>
                    {device.status}
                  </Badge>
                </div>
                
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div className="flex justify-between">
                    <span>Type:</span>
                    <span className="capitalize">{device.device_type}</span>
                  </div>
                  {device.ip_address && (
                    <div className="flex justify-between">
                      <span>IP:</span>
                      <span>{device.ip_address}</span>
                    </div>
                  )}
                  {device.description && (
                    <div className="flex justify-between">
                      <span>Description:</span>
                      <span className="truncate max-w-[120px]" title={device.description}>
                        {device.description}
                      </span>
                    </div>
                  )}
                </div>
                
                <Button 
                  className="w-full mt-4" 
                  variant="outline"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/zfs/${device.hostname}`);
                  }}
                >
                  <DatabaseIcon className="w-4 h-4 mr-2" />
                  Manage ZFS
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-12 text-center">
            <AlertTriangleIcon className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No ZFS-Capable Devices Found</h3>
            <p className="text-muted-foreground mb-4">
              No online devices with ZFS support detected. Make sure your storage servers are properly configured and online.
            </p>
            <Button variant="outline" onClick={() => navigate('/devices')}>
              <PlusIcon className="w-4 h-4 mr-2" />
              Manage Devices
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}