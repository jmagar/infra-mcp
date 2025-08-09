/**
 * VM Management Component
 * Comprehensive interface for virtual machine management and monitoring
 */

import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { DataTable, StatusBadge, ActionDropdown, ConfirmDialog, LoadingSpinner } from '@/components/common';
import { useDevices, useResponsive, useResponsiveTable } from '@/hooks';
import { useNotificationEvents } from '@/hooks/useNotificationEvents';
import { gridConfigs, spacing, typography, layout } from '@/lib/responsive';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  Monitor as MonitorIcon,
  Play as PlayIcon,
  Square as StopIcon,
  RotateCw as RestartIcon,
  Settings as SettingsIcon,
  Activity as ActivityIcon,
  HardDrive as HardDriveIcon,
  Cpu as CpuIcon,
  MemoryStick as MemoryIcon,
  Network as NetworkIcon,
  FileText as LogIcon,
  RefreshCw as RefreshCwIcon,
  Plus as PlusIcon,
  Trash2 as TrashIcon,
  Eye as EyeIcon,
  Terminal as TerminalIcon,
  Power as PowerIcon,
  Pause as PauseIcon
} from 'lucide-react';
import type { Column } from '@/components/common/DataTable';

interface VirtualMachine {
  id: string;
  name: string;
  hostname: string;
  device_hostname: string;
  status: 'running' | 'stopped' | 'paused' | 'suspended' | 'error';
  cpu_cores: number;
  memory_mb: number;
  disk_gb: number;
  ip_address?: string;
  os_type: string;
  created_at: string;
  last_started?: string;
  uptime?: number;
  cpu_usage?: number;
  memory_usage?: number;
  disk_usage?: number;
  network_rx?: number;
  network_tx?: number;
}

// Mock VM data for development
const mockVMs: VirtualMachine[] = [
  {
    id: '1',
    name: 'web-server-01',
    hostname: 'web01.local',
    device_hostname: 'server1',
    status: 'running',
    cpu_cores: 4,
    memory_mb: 8192,
    disk_gb: 100,
    ip_address: '192.168.1.50',
    os_type: 'Ubuntu 22.04 LTS',
    created_at: '2024-01-15T10:30:00Z',
    last_started: '2024-01-20T08:00:00Z',
    uptime: 432000,
    cpu_usage: 25.5,
    memory_usage: 65.2,
    disk_usage: 42.1,
    network_rx: 1024,
    network_tx: 2048,
  },
  {
    id: '2',
    name: 'database-01',
    hostname: 'db01.local',
    device_hostname: 'server1',
    status: 'running',
    cpu_cores: 8,
    memory_mb: 16384,
    disk_gb: 500,
    ip_address: '192.168.1.51',
    os_type: 'CentOS 8',
    created_at: '2024-01-10T14:20:00Z',
    last_started: '2024-01-18T09:15:00Z',
    uptime: 518400,
    cpu_usage: 45.8,
    memory_usage: 78.3,
    disk_usage: 67.9,
    network_rx: 4096,
    network_tx: 3072,
  },
  {
    id: '3',
    name: 'test-env',
    hostname: 'test01.local',
    device_hostname: 'server2',
    status: 'stopped',
    cpu_cores: 2,
    memory_mb: 4096,
    disk_gb: 50,
    ip_address: '192.168.1.52',
    os_type: 'Windows Server 2019',
    created_at: '2024-01-25T16:45:00Z',
    last_started: '2024-01-25T16:50:00Z',
    uptime: 0,
    cpu_usage: 0,
    memory_usage: 0,
    disk_usage: 35.4,
  }
];

export function VMManagement() {
  const navigate = useNavigate();
  const { hostname } = useParams<{ hostname?: string }>();
  const { devices } = useDevices();
  const { isMobile, isTablet } = useResponsive();
  const { notifySuccess, notifyError } = useNotificationEvents();

  const [vms, setVms] = useState<VirtualMachine[]>(mockVMs);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deviceFilter, setDeviceFilter] = useState<string>(hostname || 'all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTab, setSelectedTab] = useState('overview');
  
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    action: 'stop' | 'restart' | 'delete' | null;
    vmName: string;
    vmId: string;
    isLoading: boolean;
  }>({
    isOpen: false,
    action: null,
    vmName: '',
    vmId: '',
    isLoading: false,
  });

  // Filter VMs based on hostname parameter and filters
  const filteredVMs = vms.filter(vm => {
    if (hostname && vm.device_hostname !== hostname) return false;
    if (statusFilter !== 'all' && vm.status !== statusFilter) return false;
    if (deviceFilter !== 'all' && vm.device_hostname !== deviceFilter) return false;
    if (searchTerm && !vm.name.toLowerCase().includes(searchTerm.toLowerCase()) && 
        !vm.hostname.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  // Get unique device hostnames and VM statuses for filter options
  const deviceHostnames = [...new Set(vms.map(vm => vm.device_hostname))];
  const vmStatuses = [...new Set(vms.map(vm => vm.status))];

  const handleVMAction = async (action: 'start' | 'stop' | 'restart' | 'pause', vmId: string, vmName: string) => {
    try {
      setLoading(true);
      // TODO: Implement actual VM control API calls
      console.log(`${action} VM:`, vmId, vmName);
      
      // Mock action delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Update VM status
      setVms(prev => prev.map(vm => 
        vm.id === vmId 
          ? { ...vm, status: action === 'start' ? 'running' : action === 'stop' ? 'stopped' : 'paused' as any }
          : vm
      ));
      
      notifySuccess(`VM ${action}ed`, `Successfully ${action}ed "${vmName}"`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      notifyError(`VM ${action} Failed`, `Failed to ${action} "${vmName}": ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteVM = (vmId: string, vmName: string) => {
    setConfirmDialog({
      isOpen: true,
      action: 'delete',
      vmName,
      vmId,
      isLoading: false,
    });
  };

  const confirmVMAction = async () => {
    if (!confirmDialog.action || !confirmDialog.vmId) return;
    
    setConfirmDialog(prev => ({ ...prev, isLoading: true }));
    
    try {
      if (confirmDialog.action === 'delete') {
        setVms(prev => prev.filter(vm => vm.id !== confirmDialog.vmId));
        notifySuccess('VM Deleted', `Virtual machine "${confirmDialog.vmName}" has been deleted`);
      } else {
        await handleVMAction(confirmDialog.action, confirmDialog.vmId, confirmDialog.vmName);
      }
      
      setConfirmDialog({
        isOpen: false,
        action: null,
        vmName: '',
        vmId: '',
        isLoading: false,
      });
    } catch (error) {
      console.error('Failed to perform VM action:', error);
      setConfirmDialog(prev => ({ ...prev, isLoading: false }));
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatUptime = (seconds?: number): string => {
    if (!seconds) return 'Not running';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-green-500';
      case 'stopped': return 'bg-gray-500';
      case 'paused': return 'bg-yellow-500';
      case 'suspended': return 'bg-blue-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-400';
    }
  };

  const allColumns: Column<VirtualMachine>[] = [
    {
      key: 'name',
      title: 'Virtual Machine',
      sortable: true,
      render: (value, vm) => (
        <div className="flex items-center space-x-3">
          <div className={`h-3 w-3 rounded-full ${getStatusColor(vm.status)}`} />
          <div>
            <div className="font-medium text-gray-900">{vm.name}</div>
            <div className="text-sm text-gray-500">{vm.hostname}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'device_hostname',
      title: 'Host Device',
      sortable: true,
      hideOnMobile: true,
      render: (value) => (
        <span className="text-sm font-medium">{value}</span>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (value) => <StatusBadge status={value} />,
    },
    {
      key: 'resources',
      title: 'Resources',
      sortable: false,
      hideOnMobile: true,
      render: (_, vm) => (
        <div className="text-xs space-y-1">
          <div className="flex items-center space-x-1">
            <CpuIcon className="h-3 w-3 text-gray-400" />
            <span>{vm.cpu_cores} cores</span>
          </div>
          <div className="flex items-center space-x-1">
            <MemoryIcon className="h-3 w-3 text-gray-400" />
            <span>{formatBytes(vm.memory_mb * 1024 * 1024)}</span>
          </div>
          <div className="flex items-center space-x-1">
            <HardDriveIcon className="h-3 w-3 text-gray-400" />
            <span>{vm.disk_gb}GB</span>
          </div>
        </div>
      ),
    },
    {
      key: 'usage',
      title: 'Usage',
      sortable: false,
      hideOnTablet: true,
      render: (_, vm) => (
        <div className="text-xs space-y-1">
          <div className="flex items-center space-x-2">
            <span className="w-8">CPU:</span>
            <Progress value={vm.cpu_usage || 0} className="flex-1 h-1" />
            <span className="w-8 text-right">{vm.cpu_usage?.toFixed(0) || 0}%</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-8">RAM:</span>
            <Progress value={vm.memory_usage || 0} className="flex-1 h-1" />
            <span className="w-8 text-right">{vm.memory_usage?.toFixed(0) || 0}%</span>
          </div>
        </div>
      ),
    },
    {
      key: 'uptime',
      title: 'Uptime',
      sortable: false,
      hideOnTablet: true,
      render: (_, vm) => (
        <span className="text-sm">{formatUptime(vm.uptime)}</span>
      ),
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_, vm) => {
        const actions = [
          {
            label: 'View Details',
            icon: EyeIcon,
            onClick: () => navigate(`/vms/${vm.device_hostname}/${vm.id}`),
          },
          {
            label: 'View Logs',
            icon: LogIcon,
            onClick: () => navigate(`/vms/${vm.device_hostname}/${vm.id}/logs`),
          },
          {
            label: 'Console',
            icon: TerminalIcon,
            onClick: () => navigate(`/vms/${vm.device_hostname}/${vm.id}/console`),
            separator: true,
          },
          ...(vm.status === 'running' ? [
            {
              label: 'Stop VM',
              icon: StopIcon,
              onClick: () => setConfirmDialog({
                isOpen: true,
                action: 'stop',
                vmName: vm.name,
                vmId: vm.id,
                isLoading: false,
              }),
            },
            {
              label: 'Pause VM',
              icon: PauseIcon,
              onClick: () => handleVMAction('pause', vm.id, vm.name),
            },
            {
              label: 'Restart VM',
              icon: RestartIcon,
              onClick: () => setConfirmDialog({
                isOpen: true,
                action: 'restart',
                vmName: vm.name,
                vmId: vm.id,
                isLoading: false,
              }),
            }
          ] : [
            {
              label: 'Start VM',
              icon: PlayIcon,
              onClick: () => handleVMAction('start', vm.id, vm.name),
            }
          ]),
          {
            label: 'Delete VM',
            icon: TrashIcon,
            onClick: () => handleDeleteVM(vm.id, vm.name),
            variant: 'destructive' as const,
            separator: true,
          },
        ];

        return <ActionDropdown actions={actions} />;
      },
    },
  ];

  // Apply responsive filtering to columns
  const columns = useResponsiveTable(allColumns);

  // Calculate stats
  const totalVMs = filteredVMs.length;
  const runningVMs = filteredVMs.filter(vm => vm.status === 'running').length;
  const stoppedVMs = filteredVMs.filter(vm => vm.status === 'stopped').length;
  const avgCpuUsage = filteredVMs.reduce((acc, vm) => acc + (vm.cpu_usage || 0), 0) / totalVMs;
  const avgMemoryUsage = filteredVMs.reduce((acc, vm) => acc + (vm.memory_usage || 0), 0) / totalVMs;

  if (!hostname && filteredVMs.length === 0 && !loading) {
    return (
      <div className="text-center py-12">
        <MonitorIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold">No VMs Found</h2>
        <p className="text-gray-600">
          Select a device hostname to view virtual machines or create your first VM.
        </p>
      </div>
    );
  }

  return (
    <div className={`${spacing.padding.page} ${layout.sectionWrapper}`}>
      {/* Header */}
      <div className={layout.pageHeader.full}>
        <div>
          <h1 className={typography.heading.page}>Virtual Machines</h1>
          <p className={`${typography.body.normal} text-gray-600`}>
            Manage virtual machines {hostname ? `on ${hostname}` : 'across your infrastructure'} ({totalVMs} total)
          </p>
        </div>
        <div className={layout.navButtons.full}>
          <Button 
            onClick={() => navigate('/vms/create')} 
            size={isMobile ? "sm" : "default"}
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            {!isMobile && "New VM"}
          </Button>
          <Button variant="outline" onClick={() => setLoading(true)} size={isMobile ? "sm" : "default"}>
            <RefreshCwIcon className="h-4 w-4 mr-2" />
            {!isMobile && "Refresh"}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className={`${gridConfigs.dashboardMetrics.full} ${spacing.gap.full}`}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total VMs</CardTitle>
            <MonitorIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalVMs}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <div className="h-2 w-2 bg-green-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningVMs}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Stopped</CardTitle>
            <div className="h-2 w-2 bg-gray-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stoppedVMs}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg CPU</CardTitle>
            <CpuIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgCpuUsage.toFixed(1)}%</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Search and Filters */}
          <Card>
            <CardHeader>
              <CardTitle className={typography.heading.card}>Search & Filters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`${layout.sectionWrapper} space-y-4`}>
                {/* Search */}
                <div>
                  <Label htmlFor="search" className="text-xs">Search Virtual Machines</Label>
                  <Input
                    id="search"
                    placeholder="Search by name or hostname..."
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
                      {vmStatuses.map(status => (
                        <option key={status} value={status} className="capitalize">{status}</option>
                      ))}
                    </select>
                  </div>
                  
                  {!hostname && (
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
                  )}
                  
                  {(statusFilter !== 'all' || deviceFilter !== 'all' || searchTerm) && (
                    <div className="flex items-end">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setStatusFilter('all');
                          setDeviceFilter(hostname || 'all');
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

          {/* VM Table */}
          <DataTable
            data={filteredVMs}
            columns={columns}
            loading={loading}
            searchable={false} // We have custom search
            pagination={{ pageSize: 15 }}
            onRowClick={(vm) => navigate(`/vms/${vm.device_hostname}/${vm.id}`)}
            emptyMessage="No virtual machines found. Create your first VM to get started."
          />
        </TabsContent>

        <TabsContent value="performance" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>CPU Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {filteredVMs.filter(vm => vm.status === 'running').map(vm => (
                    <div key={vm.id} className="flex items-center space-x-4">
                      <span className="w-24 text-sm font-medium truncate">{vm.name}</span>
                      <Progress value={vm.cpu_usage || 0} className="flex-1" />
                      <span className="w-12 text-sm text-right">{vm.cpu_usage?.toFixed(1) || 0}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Memory Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {filteredVMs.filter(vm => vm.status === 'running').map(vm => (
                    <div key={vm.id} className="flex items-center space-x-4">
                      <span className="w-24 text-sm font-medium truncate">{vm.name}</span>
                      <Progress value={vm.memory_usage || 0} className="flex-1" />
                      <span className="w-12 text-sm text-right">{vm.memory_usage?.toFixed(1) || 0}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Virtual Machine Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                <LogIcon className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                <p>VM logs feature coming soon</p>
                <p className="text-sm">Real-time log streaming will be available here</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={`${confirmDialog.action === 'delete' ? 'Delete' : confirmDialog.action === 'stop' ? 'Stop' : 'Restart'} Virtual Machine`}
        description={
          confirmDialog.action === 'delete'
            ? `Are you sure you want to delete virtual machine "${confirmDialog.vmName}"? This action cannot be undone and will permanently remove the VM and all its data.`
            : confirmDialog.action === 'stop' 
            ? `Are you sure you want to stop virtual machine "${confirmDialog.vmName}"? This will gracefully shut down the VM.`
            : `Are you sure you want to restart virtual machine "${confirmDialog.vmName}"? This will stop and start the VM.`
        }
        confirmText={confirmDialog.action === 'delete' ? "Delete VM" : confirmDialog.action === 'stop' ? "Stop VM" : "Restart VM"}
        cancelText="Cancel"
        variant={confirmDialog.action === 'delete' ? "destructive" : "default"}
        onConfirm={confirmVMAction}
        onCancel={() => setConfirmDialog({
          isOpen: false,
          action: null,
          vmName: '',
          vmId: '',
          isLoading: false,
        })}
        isLoading={confirmDialog.isLoading}
      />
    </div>
  );
}