/**
 * Docker Compose List Component
 * Displays available compose configurations and deployment options
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable, StatusBadge, ActionDropdown, ConfirmDialog } from '@/components/common';
import { DynamicFormModal } from '@/components/common/DynamicFormModal';
import { useCompose } from '@/hooks/useCompose';
import { useDevices } from '@/hooks/useDevices';
import { useResponsive, useResponsiveTable } from '@/hooks/useResponsive';
import { useNotificationEvents } from '@/hooks/useNotificationEvents';
import { gridConfigs, spacing, typography, layout } from '@/lib/responsive';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  FileTextIcon,
  PlayIcon,
  Square as StopIcon,
  RotateCwIcon,
  TrashIcon,
  EditIcon,
  UploadIcon,
  RefreshCwIcon,
  FilterIcon,
  ServerIcon,
  PackageIcon,
  ZapIcon
} from 'lucide-react';
import type { Column } from '@/components/common/DataTable';

interface ComposeStack {
  id: string;
  name: string;
  path: string;
  device_hostname: string;
  status: 'running' | 'stopped' | 'error' | 'deploying';
  services_count: number;
  last_deployed: string;
  created_at: string;
  compose_content?: string;
}

export function ComposeList() {
  const navigate = useNavigate();
  const { composeStacks, loading, deployStack, stopStack, removeStack, refetch } = useCompose();
  const { devices } = useDevices();
  const { isMobile, isTablet } = useResponsive();
  const { notifyComposeAction } = useNotificationEvents();
  
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deviceFilter, setDeviceFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    action: 'remove' | 'stop' | null;
    stackName: string;
    deviceHostname: string;
    isLoading: boolean;
  }>({
    isOpen: false,
    action: null,
    stackName: '',
    deviceHostname: '',
    isLoading: false,
  });
  
  const [deployModal, setDeployModal] = useState<{
    isOpen: boolean;
    isLoading: boolean;
  }>({
    isOpen: false,
    isLoading: false,
  });

  // Filter stacks based on selected filters and search
  const filteredStacks = composeStacks?.filter(stack => {
    if (statusFilter !== 'all' && stack.status !== statusFilter) return false;
    if (deviceFilter !== 'all' && stack.device_hostname !== deviceFilter) return false;
    if (searchTerm && !stack.name.toLowerCase().includes(searchTerm.toLowerCase()) && 
        !stack.path.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  }) || [];

  // Get unique device hostnames and stack statuses for filter options
  const deviceHostnames = [...new Set(composeStacks?.map(s => s.device_hostname) || [])];
  const stackStatuses = [...new Set(composeStacks?.map(s => s.status) || [])];

  const handleStackAction = async (action: 'start' | 'stop' | 'restart', deviceHostname: string, stackName: string) => {
    try {
      switch (action) {
        case 'start':
          await deployStack(deviceHostname, stackName);
          notifyComposeAction('deploy', stackName, deviceHostname, true);
          break;
        case 'stop':
          await stopStack(deviceHostname, stackName);
          notifyComposeAction('stop', stackName, deviceHostname, true);
          break;
        case 'restart':
          await stopStack(deviceHostname, stackName);
          await deployStack(deviceHostname, stackName);
          notifyComposeAction('restart', stackName, deviceHostname, true);
          break;
      }
      await refetch();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error(`Failed to ${action} stack:`, error);
      notifyComposeAction(action === 'start' ? 'deploy' : action, stackName, deviceHostname, false, errorMessage);
    }
  };

  const handleRemoveStack = (deviceHostname: string, stackName: string) => {
    setConfirmDialog({
      isOpen: true,
      action: 'remove',
      stackName,
      deviceHostname,
      isLoading: false,
    });
  };

  const confirmRemoveStack = async () => {
    setConfirmDialog(prev => ({ ...prev, isLoading: true }));
    
    try {
      await removeStack(confirmDialog.deviceHostname, confirmDialog.stackName);
      notifyComposeAction('remove', confirmDialog.stackName, confirmDialog.deviceHostname, true);
      await refetch();
      setConfirmDialog({
        isOpen: false,
        action: null,
        stackName: '',
        deviceHostname: '',
        isLoading: false,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to remove stack:', error);
      notifyComposeAction('remove', confirmDialog.stackName, confirmDialog.deviceHostname, false, errorMessage);
      setConfirmDialog(prev => ({ ...prev, isLoading: false }));
    }
  };

  const handleDeployNew = async (data: { name: string; device: string; content: string; path?: string }) => {
    setDeployModal(prev => ({ ...prev, isLoading: true }));
    
    try {
      await deployStack(data.device, data.name, data.content, data.path);
      notifyComposeAction('deploy', data.name, data.device, true);
      await refetch();
      setDeployModal({ isOpen: false, isLoading: false });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to deploy stack:', error);
      notifyComposeAction('deploy', data.name, data.device, false, errorMessage);
      setDeployModal(prev => ({ ...prev, isLoading: false }));
    }
  };

  const allColumns: Column<ComposeStack>[] = [
    {
      key: 'name',
      title: 'Stack',
      sortable: true,
      render: (value, stack) => (
        <div className="flex items-center space-x-2">
          <FileTextIcon className="h-4 w-4 text-gray-400" />
          <div>
            <div className="font-medium text-gray-900">{stack.name}</div>
            <div className="text-sm text-gray-500 truncate max-w-xs" title={stack.path}>
              {stack.path}
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
      key: 'services_count',
      title: 'Services',
      sortable: true,
      hideOnMobile: true,
      render: (value) => (
        <div className="flex items-center space-x-1">
          <PackageIcon className="h-3 w-3 text-gray-400" />
          <span className="text-sm font-medium">{value}</span>
        </div>
      ),
    },
    {
      key: 'last_deployed',
      title: 'Last Deployed',
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
      key: 'actions',
      title: 'Actions',
      render: (_, stack) => {
        const actions = [
          {
            label: 'Edit Configuration',
            icon: EditIcon,
            onClick: () => navigate(`/compose/${stack.device_hostname}/${stack.name}/edit`),
          },
          ...(stack.status === 'running' ? [
            {
              label: 'Stop Stack',
              icon: StopIcon,
              onClick: () => handleStackAction('stop', stack.device_hostname, stack.name),
            }
          ] : [
            {
              label: 'Deploy Stack',
              icon: PlayIcon,
              onClick: () => handleStackAction('start', stack.device_hostname, stack.name),
            }
          ]),
          {
            label: 'Restart Stack',
            icon: RotateCwIcon,
            onClick: () => handleStackAction('restart', stack.device_hostname, stack.name),
            separator: true,
          },
          {
            label: 'Remove Stack',
            icon: TrashIcon,
            onClick: () => handleRemoveStack(stack.device_hostname, stack.name),
            variant: 'destructive' as const,
          },
        ];

        return <ActionDropdown actions={actions} />;
      },
    },
  ];

  // Apply responsive filtering to columns
  const columns = useResponsiveTable(allColumns);

  // Calculate stats
  const totalStacks = composeStacks?.length || 0;
  const runningStacks = composeStacks?.filter(s => s.status === 'running')?.length || 0;
  const stoppedStacks = composeStacks?.filter(s => s.status === 'stopped')?.length || 0;
  const errorStacks = composeStacks?.filter(s => s.status === 'error')?.length || 0;

  return (
    <div className={`${spacing.padding.page} ${layout.sectionWrapper}`}>
      {/* Header */}
      <div className={layout.pageHeader.full}>
        <div>
          <h1 className={typography.heading.page}>Docker Compose</h1>
          <p className={`${typography.body.normal} text-gray-600`}>
            Manage Docker Compose stacks across your infrastructure ({filteredStacks.length} total)
          </p>
        </div>
        <div className={layout.navButtons.full}>
          <Button 
            onClick={() => setDeployModal({ isOpen: true, isLoading: false })} 
            size={isMobile ? "sm" : "default"}
          >
            <UploadIcon className="h-4 w-4 mr-2" />
            {!isMobile && "Deploy Stack"}
          </Button>
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
            <CardTitle className="text-sm font-medium">Total Stacks</CardTitle>
            <FileTextIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalStacks}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
            <div className="h-2 w-2 bg-green-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningStacks}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Stopped</CardTitle>
            <div className="h-2 w-2 bg-gray-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stoppedStacks}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Errors</CardTitle>
            <div className="h-2 w-2 bg-red-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{errorStacks}</div>
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
              <Label htmlFor="search" className="text-xs">Search Stacks</Label>
              <Input
                id="search"
                placeholder="Search by name or path..."
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
                  {stackStatuses.map(status => (
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

      {/* Compose Stack Table */}
      <DataTable
        data={filteredStacks}
        columns={columns}
        loading={loading}
        searchable={false} // We have custom search
        pagination={{ pageSize: 15 }}
        onRowClick={(stack) => navigate(`/compose/${stack.device_hostname}/${stack.name}`)}
        emptyMessage="No compose stacks found. Deploy your first stack to get started."
      />

      {/* Deploy New Stack Modal */}
      <DynamicFormModal
        isOpen={deployModal.isOpen}
        title="Deploy New Docker Compose Stack"
        description="Upload or paste your docker-compose.yml content to deploy a new stack"
        onClose={() => setDeployModal({ isOpen: false, isLoading: false })}
        onSubmit={handleDeployNew}
        isLoading={deployModal.isLoading}
        size="xl"
        fields={[
          {
            name: 'name',
            label: 'Stack Name',
            type: 'text',
            placeholder: 'my-app-stack',
            required: true,
          },
          {
            name: 'device',
            label: 'Target Device',
            type: 'select',
            options: devices?.map(device => ({
              value: device.hostname,
              label: device.hostname
            })) || [],
            required: true,
          },
          {
            name: 'path',
            label: 'Deployment Path (optional)',
            type: 'text',
            placeholder: '/opt/docker/my-app',
          },
          {
            name: 'content',
            label: 'Docker Compose Content',
            type: 'textarea',
            placeholder: 'version: "3.8"\nservices:\n  app:\n    image: nginx\n    ports:\n      - "80:80"',
            required: true,
            rows: 12,
          },
        ]}
      />

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.action === 'remove' ? "Remove Stack" : "Stop Stack"}
        description={
          confirmDialog.action === 'remove'
            ? `Are you sure you want to remove stack "${confirmDialog.stackName}" from ${confirmDialog.deviceHostname}? This will stop all services and remove the stack configuration.`
            : `Are you sure you want to stop stack "${confirmDialog.stackName}" on ${confirmDialog.deviceHostname}? This will stop all running services.`
        }
        confirmText={confirmDialog.action === 'remove' ? "Remove Stack" : "Stop Stack"}
        cancelText="Cancel"
        variant={confirmDialog.action === 'remove' ? "destructive" : "default"}
        onConfirm={confirmRemoveStack}
        onCancel={() => setConfirmDialog({
          isOpen: false,
          action: null,
          stackName: '',
          deviceHostname: '',
          isLoading: false,
        })}
        isLoading={confirmDialog.isLoading}
      />
    </div>
  );
}