/**
 * Proxy Configuration List Component
 * Displays SWAG reverse proxy configurations and management options
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable, StatusBadge, ActionDropdown, ConfirmDialog } from '@/components/common';
import { DynamicFormModal } from '@/components/common/DynamicFormModal';
import { useProxyConfigs } from '@/hooks';
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
  GlobeIcon,
  ShieldIcon,
  EditIcon,
  TrashIcon,
  PlusIcon,
  RefreshCwIcon,
  SearchIcon,
  ServerIcon,
  LinkIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  XCircleIcon,
  FileTextIcon
} from 'lucide-react';
import type { Column } from '@/components/common/DataTable';
import type { ProxyConfigResponse } from '@infrastructor/shared-types';

export function ProxyList() {
  const navigate = useNavigate();
  const { configs: proxyConfigs, loading, createConfig, updateConfig, deleteConfig, refetch } = useProxyConfigs();
  const { devices } = useDevices();
  const { isMobile, isTablet } = useResponsive();
  const { notifySuccess, notifyError } = useNotificationEvents();
  
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [deviceFilter, setDeviceFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    configName: string;
    configId: string;
    isLoading: boolean;
  }>({
    isOpen: false,
    configName: '',
    configId: '',
    isLoading: false,
  });
  
  const [createModal, setCreateModal] = useState<{
    isOpen: boolean;
    isLoading: boolean;
  }>({
    isOpen: false,
    isLoading: false,
  });

  // Filter configs based on selected filters and search
  const filteredConfigs = proxyConfigs?.filter(config => {
    if (statusFilter !== 'all' && config.status !== statusFilter) return false;
    if (deviceFilter !== 'all' && config.device !== deviceFilter) return false;
    if (searchTerm && !config.service_name.toLowerCase().includes(searchTerm.toLowerCase()) && 
        !config.server_names?.some(name => name.toLowerCase().includes(searchTerm.toLowerCase()))) return false;
    return true;
  }) || [];

  // Get unique device hostnames and config statuses for filter options
  const deviceHostnames = [...new Set(proxyConfigs?.map(c => c.device) || [])];
  const configStatuses = [...new Set(proxyConfigs?.map(c => c.status) || [])];

  const handleDeleteConfig = (configId: number, configName: string) => {
    setConfirmDialog({
      isOpen: true,
      configName,
      configId: configId.toString(),
      isLoading: false,
    });
  };

  const confirmDeleteConfig = async () => {
    setConfirmDialog(prev => ({ ...prev, isLoading: true }));
    
    try {
      const success = await deleteConfig(parseInt(confirmDialog.configId));
      if (success) {
        setConfirmDialog({
          isOpen: false,
          configName: '',
          configId: '',
          isLoading: false,
        });
      } else {
        setConfirmDialog(prev => ({ ...prev, isLoading: false }));
      }
    } catch (error) {
      console.error('Failed to delete config:', error);
      setConfirmDialog(prev => ({ ...prev, isLoading: false }));
    }
  };

  const handleCreateConfig = async (data: Record<string, string>) => {
    setCreateModal(prev => ({ ...prev, isLoading: true }));
    
    try {
      const success = await createConfig({
        service_name: data.name,
        server_names: [data.domain],
        target_host: data.target_host,
        target_port: parseInt(data.target_port),
        device: data.device,
        ssl_enabled: data.ssl_enabled === 'true',
        auth_enabled: data.auth_enabled === 'true',
      });
      if (success) {
        setCreateModal({ isOpen: false, isLoading: false });
      } else {
        setCreateModal(prev => ({ ...prev, isLoading: false }));
      }
    } catch (error) {
      console.error('Failed to create config:', error);
      setCreateModal(prev => ({ ...prev, isLoading: false }));
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />;
      case 'inactive':
        return <AlertCircleIcon className="h-4 w-4 text-yellow-500" />;
      case 'error':
        return <XCircleIcon className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircleIcon className="h-4 w-4 text-gray-400" />;
    }
  };

  const allColumns: Column<ProxyConfigResponse>[] = [
    {
      key: 'service_name',
      title: 'Configuration',
      sortable: true,
      render: (value, config) => (
        <div className="flex items-center space-x-2">
          <FileTextIcon className="h-4 w-4 text-gray-400" />
          <div>
            <div className="font-medium text-gray-900">{config.service_name}</div>
            <div className="text-sm text-gray-500 flex items-center">
              <LinkIcon className="h-3 w-3 mr-1" />
              {config.server_names?.[0] || 'No domain'}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'target',
      title: 'Target',
      sortable: false,
      hideOnMobile: true,
      render: (_, config) => (
        <div className="text-sm font-mono">
          {config.target_host}:{config.target_port}
        </div>
      ),
    },
    {
      key: 'device',
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
      render: (value, config) => (
        <div className="flex items-center space-x-2">
          {getStatusIcon(value)}
          <StatusBadge status={value} />
        </div>
      ),
    },
    {
      key: 'features',
      title: 'Features',
      sortable: false,
      hideOnTablet: true,
      render: (_, config) => (
        <div className="flex space-x-1">
          {config.ssl_enabled && (
            <Badge variant="outline" className="text-xs">
              <ShieldIcon className="h-2 w-2 mr-1" />
              SSL
            </Badge>
          )}
          {config.auth_enabled && (
            <Badge variant="outline" className="text-xs">
              Auth
            </Badge>
          )}
        </div>
      ),
    },
    {
      key: 'updated_at',
      title: 'Last Updated',
      sortable: true,
      hideOnTablet: true,
      render: (value) => {
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
      render: (_, config) => {
        const actions = [
          {
            label: 'Edit Configuration',
            icon: EditIcon,
            onClick: () => navigate(`/proxies/${config.device}/${config.id}/edit`),
          },
          {
            label: 'View Details',
            icon: GlobeIcon,
            onClick: () => navigate(`/proxies/${config.device}/${config.id}`),
            separator: true,
          },
          {
            label: 'Delete Configuration',
            icon: TrashIcon,
            onClick: () => handleDeleteConfig(config.id, config.service_name),
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
  const totalConfigs = proxyConfigs?.length || 0;
  const activeConfigs = proxyConfigs?.filter(c => c.status === 'active')?.length || 0;
  const sslConfigs = proxyConfigs?.filter(c => c.ssl_enabled)?.length || 0;
  const authConfigs = proxyConfigs?.filter(c => c.auth_enabled)?.length || 0;

  return (
    <div className={`${spacing.padding.page} ${layout.sectionWrapper}`}>
      {/* Header */}
      <div className={layout.pageHeader.full}>
        <div>
          <h1 className={typography.heading.page}>Proxy Configurations</h1>
          <p className={`${typography.body.normal} text-gray-600`}>
            Manage SWAG reverse proxy configurations ({filteredConfigs.length} total)
          </p>
        </div>
        <div className={layout.navButtons.full}>
          <Button 
            onClick={() => setCreateModal({ isOpen: true, isLoading: false })} 
            size={isMobile ? "sm" : "default"}
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            {!isMobile && "New Config"}
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
            <CardTitle className="text-sm font-medium">Total Configs</CardTitle>
            <FileTextIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalConfigs}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active</CardTitle>
            <div className="h-2 w-2 bg-green-500 rounded-full"></div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeConfigs}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">SSL Enabled</CardTitle>
            <ShieldIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sslConfigs}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Auth Enabled</CardTitle>
            <GlobeIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{authConfigs}</div>
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
              <Label htmlFor="search" className="text-xs">Search Configurations</Label>
              <Input
                id="search"
                placeholder="Search by name or domain..."
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
                  {configStatuses.map(status => (
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

      {/* Proxy Configuration Table */}
      <DataTable
        data={filteredConfigs}
        columns={columns}
        loading={loading}
        searchable={false} // We have custom search
        pagination={{ pageSize: 15 }}
        onRowClick={(config) => navigate(`/proxies/${config.device}/${config.id}`)}
        emptyMessage="No proxy configurations found. Create your first configuration to get started."
      />

      {/* Create New Configuration Modal */}
      <DynamicFormModal
        isOpen={createModal.isOpen}
        title="Create New Proxy Configuration"
        description="Set up a new SWAG reverse proxy configuration"
        onClose={() => setCreateModal({ isOpen: false, isLoading: false })}
        onSubmit={handleCreateConfig}
        isLoading={createModal.isLoading}
        size="lg"
        fields={[
          {
            name: 'name',
            label: 'Configuration Name',
            type: 'text',
            placeholder: 'my-app',
            required: true,
          },
          {
            name: 'domain',
            label: 'Domain',
            type: 'text',
            placeholder: 'app.example.com',
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
            name: 'target_host',
            label: 'Target Host',
            type: 'text',
            placeholder: '192.168.1.100',
            required: true,
          },
          {
            name: 'target_port',
            label: 'Target Port',
            type: 'text',
            placeholder: '3000',
            required: true,
          },
          {
            name: 'ssl_enabled',
            label: 'Enable SSL',
            type: 'select',
            options: [
              { value: 'true', label: 'Enabled' },
              { value: 'false', label: 'Disabled' },
            ],
            required: true,
          },
          {
            name: 'auth_enabled',
            label: 'Enable Authentication',
            type: 'select',
            options: [
              { value: 'false', label: 'Disabled' },
              { value: 'true', label: 'Enabled' },
            ],
            required: true,
          },
        ]}
      />

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title="Delete Proxy Configuration"
        description={`Are you sure you want to delete the proxy configuration "${confirmDialog.configName}"? This action cannot be undone and will remove the configuration from the proxy server.`}
        confirmText="Delete Configuration"
        cancelText="Cancel"
        variant="destructive"
        onConfirm={confirmDeleteConfig}
        onCancel={() => setConfirmDialog({
          isOpen: false,
          configName: '',
          configId: '',
          isLoading: false,
        })}
        isLoading={confirmDialog.isLoading}
      />
    </div>
  );
}