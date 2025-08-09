/**
 * Drive Health Monitor Component
 * Displays S.M.A.R.T. data and drive health status
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DataTable, LoadingSpinner, EmptyState } from '@/components/common';
import { 
  HardDriveIcon,
  ThermometerIcon,
  ZapIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  RefreshCwIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  InfoIcon
} from 'lucide-react';
import type { Column } from '@/components/common/DataTable';

interface SMARTAttribute {
  id: number;
  attribute_name: string;
  current_value: number;
  worst_value: number;
  threshold: number;
  raw_value: number;
  status: 'good' | 'warning' | 'critical';
}

interface DriveInfo {
  device: string;
  model: string;
  serial: string;
  size: string;
  health_status: 'healthy' | 'warning' | 'critical' | 'failed';
  temperature: number;
  power_on_hours: number;
  power_cycle_count: number;
  smart_attributes: SMARTAttribute[];
  test_results: {
    short_test: {
      status: 'passed' | 'failed' | 'running' | 'never';
      completion: string;
    };
    long_test: {
      status: 'passed' | 'failed' | 'running' | 'never';
      completion: string;
    };
  };
}

interface DriveHealthMonitorProps {
  hostname: string;
  drives?: DriveInfo[];
  loading?: boolean;
  error?: string;
  onRefresh?: () => void;
  onRunTest?: (device: string, testType: 'short' | 'long') => void;
}

export function DriveHealthMonitor({
  hostname,
  drives = [],
  loading = false,
  error,
  onRefresh,
  onRunTest,
}: DriveHealthMonitorProps) {
  const [selectedDrive, setSelectedDrive] = useState<string | null>(
    drives.length > 0 ? drives[0].device : null
  );

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'warning':
        return <AlertTriangleIcon className="h-5 w-5 text-yellow-500" />;
      case 'critical':
        return <XCircleIcon className="h-5 w-5 text-red-500" />;
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-600" />;
      default:
        return <InfoIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  const getHealthBadgeVariant = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'passed':
        return 'default';
      case 'warning':
        return 'secondary';
      case 'critical':
      case 'failed':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const formatUptime = (hours: number) => {
    const days = Math.floor(hours / 24);
    const years = Math.floor(days / 365);
    
    if (years > 0) {
      return `${years}y ${Math.floor((days % 365) / 30)}m`;
    } else if (days > 30) {
      return `${Math.floor(days / 30)}m ${days % 30}d`;
    } else {
      return `${days}d ${hours % 24}h`;
    }
  };

  const smartColumns: Column<SMARTAttribute>[] = [
    {
      key: 'id',
      title: 'ID',
      sortable: true,
      render: (value) => <span className="font-mono text-sm">{value}</span>,
    },
    {
      key: 'attribute_name',
      title: 'Attribute',
      sortable: true,
      render: (value) => (
        <div>
          <div className="font-medium">{value}</div>
        </div>
      ),
    },
    {
      key: 'current_value',
      title: 'Current',
      sortable: true,
      render: (value) => <span className="font-mono">{value}</span>,
    },
    {
      key: 'worst_value',
      title: 'Worst',
      sortable: true,
      render: (value) => <span className="font-mono">{value}</span>,
    },
    {
      key: 'threshold',
      title: 'Threshold',
      sortable: true,
      render: (value) => <span className="font-mono">{value}</span>,
    },
    {
      key: 'raw_value',
      title: 'Raw Value',
      sortable: true,
      render: (value) => <span className="font-mono text-sm">{value.toLocaleString()}</span>,
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (value) => (
        <Badge variant={getHealthBadgeVariant(value)} className="capitalize">
          {value}
        </Badge>
      ),
    },
  ];

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <LoadingSpinner />
          <span className="ml-2">Loading drive health data...</span>
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
            <p className="text-red-600 mb-4">Failed to load drive health</p>
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

  if (drives.length === 0) {
    return (
      <EmptyState
        icon={<HardDriveIcon className="h-12 w-12 text-muted-foreground" />}
        title="No Drives Found"
        description="No drive health information available for this device."
        action={onRefresh ? {
          label: "Refresh",
          onClick: onRefresh
        } : undefined}
      />
    );
  }

  const currentDrive = selectedDrive 
    ? drives.find(d => d.device === selectedDrive)
    : drives[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Drive Health Monitor</h2>
          <p className="text-gray-600">S.M.A.R.T. monitoring for {hostname}</p>
        </div>
        {onRefresh && (
          <Button variant="outline" onClick={onRefresh}>
            <RefreshCwIcon className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        )}
      </div>

      {/* Drive Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {drives.map((drive) => (
          <Card
            key={drive.device}
            className={`cursor-pointer transition-colors ${
              selectedDrive === drive.device
                ? 'ring-2 ring-blue-500 border-blue-200'
                : 'hover:border-gray-300'
            }`}
            onClick={() => setSelectedDrive(drive.device)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{drive.device}</CardTitle>
                {getHealthIcon(drive.health_status)}
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-sm text-gray-600">
                <div className="font-medium">{drive.model}</div>
                <div>Size: {drive.size}</div>
                <div>Temp: {drive.temperature}°C</div>
              </div>
              <Badge 
                variant={getHealthBadgeVariant(drive.health_status)}
                className="capitalize"
              >
                {drive.health_status}
              </Badge>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Detailed Drive Information */}
      {currentDrive && (
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="smart">S.M.A.R.T. Data</TabsTrigger>
            <TabsTrigger value="tests">Health Tests</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Drive Information */}
              <Card>
                <CardHeader>
                  <CardTitle>Drive Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Device</span>
                    <span className="text-sm font-mono">{currentDrive.device}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Model</span>
                    <span className="text-sm font-medium">{currentDrive.model}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Serial</span>
                    <span className="text-sm font-mono">{currentDrive.serial}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Size</span>
                    <span className="text-sm font-medium">{currentDrive.size}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Health Status</span>
                    <Badge 
                      variant={getHealthBadgeVariant(currentDrive.health_status)}
                      className="capitalize"
                    >
                      {currentDrive.health_status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              {/* Performance & Health Metrics */}
              <Card>
                <CardHeader>
                  <CardTitle>Performance & Health</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 flex items-center">
                      <ThermometerIcon className="h-4 w-4 mr-1" />
                      Temperature
                    </span>
                    <span className="text-sm font-medium">{currentDrive.temperature}°C</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Power On Hours</span>
                    <span className="text-sm font-medium">
                      {formatUptime(currentDrive.power_on_hours)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Power Cycles</span>
                    <span className="text-sm font-medium">
                      {currentDrive.power_cycle_count.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Critical Attributes</span>
                    <span className="text-sm font-medium">
                      {currentDrive.smart_attributes.filter(attr => attr.status === 'critical').length}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="smart">
            <Card>
              <CardHeader>
                <CardTitle>S.M.A.R.T. Attributes</CardTitle>
              </CardHeader>
              <CardContent>
                <DataTable
                  data={currentDrive.smart_attributes}
                  columns={smartColumns}
                  searchable
                  searchPlaceholder="Search attributes..."
                  pagination={{ pageSize: 20 }}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="tests">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Short Self-Test</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Status</span>
                    <Badge variant={getHealthBadgeVariant(currentDrive.test_results.short_test.status)}>
                      {currentDrive.test_results.short_test.status}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Last Completion</span>
                    <span className="text-sm">{currentDrive.test_results.short_test.completion}</span>
                  </div>
                  {onRunTest && (
                    <Button
                      onClick={() => onRunTest(currentDrive.device, 'short')}
                      className="w-full"
                      disabled={currentDrive.test_results.short_test.status === 'running'}
                    >
                      {currentDrive.test_results.short_test.status === 'running' 
                        ? 'Test Running...' 
                        : 'Run Short Test'
                      }
                    </Button>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Extended Self-Test</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Status</span>
                    <Badge variant={getHealthBadgeVariant(currentDrive.test_results.long_test.status)}>
                      {currentDrive.test_results.long_test.status}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Last Completion</span>
                    <span className="text-sm">{currentDrive.test_results.long_test.completion}</span>
                  </div>
                  {onRunTest && (
                    <Button
                      onClick={() => onRunTest(currentDrive.device, 'long')}
                      className="w-full"
                      disabled={currentDrive.test_results.long_test.status === 'running'}
                    >
                      {currentDrive.test_results.long_test.status === 'running' 
                        ? 'Test Running...' 
                        : 'Run Extended Test'
                      }
                    </Button>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}