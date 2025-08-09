/**
 * Network Monitor Component
 * Displays network ports, connections, and traffic information
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DataTable, LoadingSpinner, EmptyState, SearchInput } from '@/components/common';
import { 
  NetworkIcon,
  WifiIcon,
  ShieldIcon,
  ZapIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  RefreshCwIcon,
  ServerIcon,
  MonitorIcon,
  GlobeIcon
} from 'lucide-react';
import type { Column } from '@/components/common/DataTable';

interface NetworkPort {
  port: number;
  protocol: 'tcp' | 'udp';
  state: 'listening' | 'established' | 'closed' | 'time_wait';
  process: string;
  pid: number;
  address: string;
  remote_address?: string;
  remote_port?: number;
}

interface NetworkInterface {
  name: string;
  ip_address: string;
  mac_address: string;
  status: 'up' | 'down';
  speed: string;
  duplex: string;
  bytes_sent: number;
  bytes_received: number;
  packets_sent: number;
  packets_received: number;
  errors_in: number;
  errors_out: number;
  drops_in: number;
  drops_out: number;
}

interface NetworkConnection {
  local_address: string;
  local_port: number;
  remote_address: string;
  remote_port: number;
  state: string;
  protocol: string;
  process: string;
  pid: number;
}

interface NetworkMonitorProps {
  hostname: string;
  ports?: NetworkPort[];
  interfaces?: NetworkInterface[];
  connections?: NetworkConnection[];
  loading?: boolean;
  error?: string;
  onRefresh?: () => void;
}

export function NetworkMonitor({
  hostname,
  ports = [],
  interfaces = [],
  connections = [],
  loading = false,
  error,
  onRefresh,
}: NetworkMonitorProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [portFilter, setPortFilter] = useState<'all' | 'listening' | 'established'>('all');

  const formatBytes = (bytes: number) => {
    const gb = bytes / 1024 / 1024 / 1024;
    if (gb >= 1) return `${gb.toFixed(2)} GB`;
    const mb = bytes / 1024 / 1024;
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    const kb = bytes / 1024;
    return `${kb.toFixed(2)} KB`;
  };

  const getPortStateColor = (state: string) => {
    switch (state.toLowerCase()) {
      case 'listening':
        return 'bg-green-500';
      case 'established':
        return 'bg-blue-500';
      case 'closed':
        return 'bg-gray-500';
      case 'time_wait':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-400';
    }
  };

  const getInterfaceStatusIcon = (status: string) => {
    return status === 'up' 
      ? <CheckCircleIcon className="h-4 w-4 text-green-500" />
      : <XCircleIcon className="h-4 w-4 text-red-500" />;
  };

  const portColumns: Column<NetworkPort>[] = [
    {
      key: 'port',
      title: 'Port',
      sortable: true,
      render: (value) => <span className="font-mono font-medium">{value}</span>,
    },
    {
      key: 'protocol',
      title: 'Protocol',
      sortable: true,
      render: (value) => (
        <Badge variant="outline" className="uppercase">
          {value}
        </Badge>
      ),
    },
    {
      key: 'state',
      title: 'State',
      sortable: true,
      render: (value) => (
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${getPortStateColor(value)}`} />
          <span className="capitalize">{value}</span>
        </div>
      ),
    },
    {
      key: 'address',
      title: 'Address',
      sortable: true,
      render: (value) => <span className="font-mono text-sm">{value}</span>,
    },
    {
      key: 'process',
      title: 'Process',
      sortable: true,
      render: (value, row) => (
        <div>
          <div className="font-medium">{value}</div>
          <div className="text-xs text-gray-500">PID: {row.pid}</div>
        </div>
      ),
    },
    {
      key: 'remote_address',
      title: 'Remote',
      render: (value, row) => {
        if (value && row.remote_port) {
          return (
            <span className="font-mono text-sm">
              {value}:{row.remote_port}
            </span>
          );
        }
        return <span className="text-gray-400">-</span>;
      },
    },
  ];

  const interfaceColumns: Column<NetworkInterface>[] = [
    {
      key: 'name',
      title: 'Interface',
      sortable: true,
      render: (value, row) => (
        <div className="flex items-center space-x-2">
          {getInterfaceStatusIcon(row.status)}
          <span className="font-mono font-medium">{value}</span>
        </div>
      ),
    },
    {
      key: 'ip_address',
      title: 'IP Address',
      sortable: true,
      render: (value) => <span className="font-mono">{value}</span>,
    },
    {
      key: 'mac_address',
      title: 'MAC Address',
      render: (value) => <span className="font-mono text-sm">{value}</span>,
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (value) => (
        <Badge variant={value === 'up' ? 'default' : 'secondary'} className="capitalize">
          {value}
        </Badge>
      ),
    },
    {
      key: 'speed',
      title: 'Speed',
      render: (value) => <span className="text-sm">{value}</span>,
    },
    {
      key: 'bytes_received',
      title: 'RX',
      render: (value, row) => (
        <div className="text-sm">
          <div>{formatBytes(value)}</div>
          <div className="text-xs text-gray-500">
            {row.packets_received.toLocaleString()} pkts
          </div>
        </div>
      ),
    },
    {
      key: 'bytes_sent',
      title: 'TX',
      render: (value, row) => (
        <div className="text-sm">
          <div>{formatBytes(value)}</div>
          <div className="text-xs text-gray-500">
            {row.packets_sent.toLocaleString()} pkts
          </div>
        </div>
      ),
    },
  ];

  const connectionColumns: Column<NetworkConnection>[] = [
    {
      key: 'local_address',
      title: 'Local',
      render: (value, row) => (
        <span className="font-mono text-sm">
          {value}:{row.local_port}
        </span>
      ),
    },
    {
      key: 'remote_address',
      title: 'Remote',
      render: (value, row) => (
        <span className="font-mono text-sm">
          {value}:{row.remote_port}
        </span>
      ),
    },
    {
      key: 'state',
      title: 'State',
      sortable: true,
      render: (value) => (
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${getPortStateColor(value)}`} />
          <span className="capitalize">{value}</span>
        </div>
      ),
    },
    {
      key: 'protocol',
      title: 'Protocol',
      sortable: true,
      render: (value) => (
        <Badge variant="outline" className="uppercase">
          {value}
        </Badge>
      ),
    },
    {
      key: 'process',
      title: 'Process',
      render: (value, row) => (
        <div>
          <div className="font-medium">{value}</div>
          <div className="text-xs text-gray-500">PID: {row.pid}</div>
        </div>
      ),
    },
  ];

  // Filter ports based on search and state filter
  const filteredPorts = ports.filter(port => {
    const matchesSearch = searchQuery === '' || 
      port.port.toString().includes(searchQuery) ||
      port.process.toLowerCase().includes(searchQuery.toLowerCase()) ||
      port.address.includes(searchQuery);
    
    const matchesFilter = portFilter === 'all' || port.state === portFilter;
    
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <LoadingSpinner />
          <span className="ml-2">Loading network information...</span>
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
            <p className="text-red-600 mb-4">Failed to load network data</p>
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Network Monitor</h2>
          <p className="text-gray-600">Network interfaces, ports, and connections for {hostname}</p>
        </div>
        {onRefresh && (
          <Button variant="outline" onClick={onRefresh}>
            <RefreshCwIcon className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Interfaces</CardTitle>
            <WifiIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {interfaces.filter(i => i.status === 'up').length}
            </div>
            <p className="text-xs text-muted-foreground">
              {interfaces.length} total interfaces
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Listening Ports</CardTitle>
            <ServerIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {ports.filter(p => p.state === 'listening').length}
            </div>
            <p className="text-xs text-muted-foreground">
              {ports.length} total ports
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Established</CardTitle>
            <GlobeIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {connections.filter(c => c.state === 'ESTABLISHED').length}
            </div>
            <p className="text-xs text-muted-foreground">
              Active connections
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Traffic</CardTitle>
            <NetworkIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatBytes(interfaces.reduce((sum, iface) => sum + iface.bytes_sent + iface.bytes_received, 0))}
            </div>
            <p className="text-xs text-muted-foreground">
              Combined RX/TX
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Tabs */}
      <Tabs defaultValue="ports">
        <TabsList>
          <TabsTrigger value="ports">Network Ports</TabsTrigger>
          <TabsTrigger value="interfaces">Interfaces</TabsTrigger>
          <TabsTrigger value="connections">Connections</TabsTrigger>
        </TabsList>

        <TabsContent value="ports" className="space-y-4">
          {/* Port Filters */}
          <div className="flex items-center space-x-4">
            <SearchInput
              placeholder="Search ports, processes..."
              onSearch={setSearchQuery}
              className="max-w-sm"
            />
            <select
              value={portFilter}
              onChange={(e) => setPortFilter(e.target.value as any)}
              className="px-3 py-2 border rounded-md text-sm"
            >
              <option value="all">All States</option>
              <option value="listening">Listening Only</option>
              <option value="established">Established Only</option>
            </select>
          </div>

          <Card>
            <CardContent className="p-0">
              <DataTable
                data={filteredPorts}
                columns={portColumns}
                pagination={{ pageSize: 15 }}
                emptyMessage="No network ports found matching your criteria."
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="interfaces">
          <Card>
            <CardContent className="p-0">
              <DataTable
                data={interfaces}
                columns={interfaceColumns}
                searchable
                searchPlaceholder="Search interfaces..."
                emptyMessage="No network interfaces found."
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="connections">
          <Card>
            <CardContent className="p-0">
              <DataTable
                data={connections}
                columns={connectionColumns}
                searchable
                searchPlaceholder="Search connections..."
                pagination={{ pageSize: 15 }}
                emptyMessage="No active network connections found."
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}