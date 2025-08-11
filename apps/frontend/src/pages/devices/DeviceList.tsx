import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable, StatusBadge, FormModal, ConfirmDialog, ActionDropdown } from '@/components/common';
import { useDevices } from '@/hooks/useDevices';
import { useResponsive, useResponsiveTable } from '@/hooks/useResponsive';
import { gridConfigs, spacing, typography, layout } from '@/lib/responsive';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
// import {
//   Dialog,
//   DialogContent,
//   DialogDescription,
//   DialogFooter,
//   DialogHeader,
//   DialogTitle,
//   DialogTrigger,
// } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { 
  PlusIcon, 
  ServerIcon, 
  TrashIcon, 
  PencilIcon,
  EyeIcon,
  RefreshCwIcon,
  FilterIcon,
  SettingsIcon 
} from 'lucide-react';
import type { DeviceResponse, DeviceCreate } from '@infrastructor/shared-types';
import type { Column } from '@/components/common/DataTable';

export function DeviceList() {
  const navigate = useNavigate();
  const { devices, loading, createDevice, deleteDevice, refetch } = useDevices();
  const { isMobile } = useResponsive();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [deviceToDelete, setDeviceToDelete] = useState<string | null>(null);
  const [isDeleteLoading, setIsDeleteLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [newDevice, setNewDevice] = useState<DeviceCreate>({
    hostname: '',
    ip_address: '',
    ssh_username: 'root',
    ssh_port: 22,
    device_type: 'server',
    description: '',
    monitoring_enabled: true,
  });

  // Filter devices based on selected filters
  const filteredDevices = devices?.filter(device => {
    if (statusFilter !== 'all' && device.status !== statusFilter) return false;
    if (typeFilter !== 'all' && device.device_type !== typeFilter) return false;
    return true;
  }) || [];

  // Get unique device types and statuses for filter options
  const deviceTypes = [...new Set(devices?.map(d => d.device_type) || [])];
  const deviceStatuses = [...new Set(devices?.map(d => d.status) || [])];

  const handleAddDevice = async () => {
    if (!newDevice.hostname) return;
    
    const success = await createDevice(newDevice);
    if (success) {
      setIsAddDialogOpen(false);
      setNewDevice({
        hostname: '',
        ip_address: '',
        ssh_username: 'root',
        ssh_port: 22,
        device_type: 'server',
        description: '',
        monitoring_enabled: true,
      });
    }
  };

  const handleDeleteDevice = (hostname: string) => {
    setDeviceToDelete(hostname);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!deviceToDelete) return;
    
    setIsDeleteLoading(true);
    try {
      await deleteDevice(deviceToDelete);
      setIsDeleteDialogOpen(false);
      setDeviceToDelete(null);
    } finally {
      setIsDeleteLoading(false);
    }
  };

  const allColumns: Column<DeviceResponse>[] = [
    {
      key: 'hostname',
      title: 'Hostname',
      sortable: true,
      render: (value, device) => (
        <div className="flex items-center space-x-2">
          <ServerIcon className="h-4 w-4 text-gray-400" />
          <div>
            <div className="font-medium text-gray-900">{device.hostname}</div>
            {device.ip_address && (
              <div className="text-sm text-gray-500">{device.ip_address}</div>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'device_type',
      title: 'Type',
      sortable: true,
      hideOnMobile: true,
      render: (value) => (
        <Badge variant="secondary" className="capitalize">
          {value}
        </Badge>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (value) => <StatusBadge status={value} />,
    },
    {
      key: 'monitoring_enabled',
      title: 'Monitoring',
      hideOnMobile: true,
      render: (value) => (
        <Badge variant={value ? 'default' : 'secondary'}>
          {value ? 'Enabled' : 'Disabled'}
        </Badge>
      ),
    },
    {
      key: 'last_seen',
      title: 'Last Seen',
      sortable: true,
      hideOnTablet: true,
      render: (value) => {
        if (!value) return <span className="text-gray-400">Never</span>;
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
      key: 'description',
      title: 'Description',
      hideOnMobile: true,
      hideOnTablet: true,
      render: (value) => (
        <div className="max-w-xs truncate" title={value || ''}>
          {value || <span className="text-gray-400">No description</span>}
        </div>
      ),
    },
    {
      key: 'actions',
      title: 'Actions',
      render: (_, device) => (
        <ActionDropdown
          actions={[
            {
              label: 'View Details',
              icon: EyeIcon,
              onClick: () => navigate(`/devices/${device.hostname}`),
            },
            {
              label: 'Edit Device',
              icon: PencilIcon,
              onClick: () => navigate(`/devices/${device.hostname}/edit`),
            },
            {
              label: 'Settings',
              icon: SettingsIcon,
              onClick: () => navigate(`/devices/${device.hostname}/settings`),
              separator: true,
            },
            {
              label: 'Delete Device',
              icon: TrashIcon,
              onClick: () => handleDeleteDevice(device.hostname),
              variant: 'destructive',
            },
          ]}
        />
      ),
    },
  ];

  // Apply responsive filtering to columns
  const columns = useResponsiveTable(allColumns);

  return (
    <div className={`${spacing.padding.page} ${layout.sectionWrapper}`}>
      {/* Header */}
      <div className={layout.pageHeader.full}>
        <div>
          <h1 className={typography.heading.page}>Devices</h1>
          <p className={`${typography.body.normal} text-gray-600`}>
            Manage your infrastructure devices ({filteredDevices.length} total)
          </p>
        </div>
        <div className={layout.navButtons.full}>
          <Button variant="outline" onClick={refetch} size={isMobile ? "sm" : "default"}>
            <RefreshCwIcon className="h-4 w-4 mr-2" />
            {!isMobile && "Refresh"}
          </Button>
          <Button 
            size={isMobile ? "sm" : "default"}
            onClick={() => setIsAddDialogOpen(true)}
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            {isMobile ? "Add" : "Add Device"}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className={`${gridConfigs.dashboardMetrics.full} ${spacing.gap.full}`}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Devices</CardTitle>
            <ServerIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{devices?.length || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Online</CardTitle>
            <div className="h-2 w-2 bg-green-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {devices?.filter(d => d.status === 'online')?.length || 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Offline</CardTitle>
            <div className="h-2 w-2 bg-red-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {devices?.filter(d => d.status === 'offline')?.length || 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monitoring</CardTitle>
            <FilterIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {devices?.filter(d => d.monitoring_enabled)?.length || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className={typography.heading.card}>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`flex flex-wrap ${spacing.gap.mobile}`}>
            <div className="flex flex-col space-y-1">
              <Label className="text-xs">Status</Label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="flex h-8 w-32 rounded-md border border-input bg-background px-3 py-1 text-sm"
              >
                <option value="all">All Status</option>
                {deviceStatuses.map(status => (
                  <option key={status} value={status} className="capitalize">{status}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col space-y-1">
              <Label className="text-xs">Type</Label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="flex h-8 w-32 rounded-md border border-input bg-background px-3 py-1 text-sm"
              >
                <option value="all">All Types</option>
                {deviceTypes.map(type => (
                  <option key={type} value={type} className="capitalize">{type}</option>
                ))}
              </select>
            </div>
            {(statusFilter !== 'all' || typeFilter !== 'all') && (
              <div className="flex items-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setStatusFilter('all');
                    setTypeFilter('all');
                  }}
                >
                  Clear Filters
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Device Table */}
      <DataTable
        data={filteredDevices}
        columns={columns}
        loading={loading}
        searchable
        searchPlaceholder="Search devices..."
        pagination={{ pageSize: 10 }}
        onRowClick={(device) => navigate(`/devices/${device.hostname}`)}
        emptyMessage="No devices found. Add your first device to get started."
      />

      {/* Add Device Modal */}
      <FormModal
        isOpen={isAddDialogOpen}
        onClose={() => setIsAddDialogOpen(false)}
        onSubmit={handleAddDevice}
        title="Add New Device"
        description="Add a new device to your infrastructure for monitoring."
        isSubmitDisabled={!newDevice.hostname}
        size="md"
      >
        <div className="grid gap-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="hostname" className="text-right">
              Hostname *
            </Label>
            <Input
              id="hostname"
              value={newDevice.hostname}
              onChange={(e) => setNewDevice({ ...newDevice, hostname: e.target.value })}
              className="col-span-3"
              placeholder="server-01"
              required
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="ip_address" className="text-right">
              IP Address
            </Label>
            <Input
              id="ip_address"
              value={newDevice.ip_address || ''}
              onChange={(e) => setNewDevice({ ...newDevice, ip_address: e.target.value })}
              className="col-span-3"
              placeholder="192.168.1.100"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="device_type" className="text-right">
              Type
            </Label>
            <select
              id="device_type"
              value={newDevice.device_type}
              onChange={(e) => setNewDevice({ ...newDevice, device_type: e.target.value })}
              className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
            >
              <option value="server">Server</option>
              <option value="workstation">Workstation</option>
              <option value="vm">Virtual Machine</option>
              <option value="container">Container Host</option>
              <option value="network">Network Device</option>
              <option value="storage">Storage Device</option>
            </select>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="ssh_username" className="text-right">
              SSH User
            </Label>
            <Input
              id="ssh_username"
              value={newDevice.ssh_username || ''}
              onChange={(e) => setNewDevice({ ...newDevice, ssh_username: e.target.value })}
              className="col-span-3"
              placeholder="root"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="ssh_port" className="text-right">
              SSH Port
            </Label>
            <Input
              id="ssh_port"
              type="number"
              value={newDevice.ssh_port || 22}
              onChange={(e) => setNewDevice({ ...newDevice, ssh_port: parseInt(e.target.value) || 22 })}
              className="col-span-3"
              placeholder="22"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="description" className="text-right">
              Description
            </Label>
            <Input
              id="description"
              value={newDevice.description || ''}
              onChange={(e) => setNewDevice({ ...newDevice, description: e.target.value })}
              className="col-span-3"
              placeholder="Web server"
            />
          </div>
        </div>
      </FormModal>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        onClose={() => {
          setIsDeleteDialogOpen(false);
          setDeviceToDelete(null);
        }}
        onConfirm={confirmDelete}
        title="Delete Device"
        description={`Are you sure you want to delete device "${deviceToDelete}"? This action cannot be undone.`}
        confirmLabel="Delete Device"
        isLoading={isDeleteLoading}
        variant="danger"
      />
    </div>
  );
}