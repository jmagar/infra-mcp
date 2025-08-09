/**
 * Docker Compose Deployment Component
 * Handles deployment management and monitoring
 */

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useCompose } from '@/hooks/useCompose';
import { useContainers } from '@/hooks/useContainers';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DataTable, StatusBadge, LoadingSpinner } from '@/components/common';
import {
  PlayIcon,
  Square as StopIcon,
  RotateCwIcon,
  ActivityIcon,
  FileTextIcon,
  PackageIcon,
  ClockIcon,
  ServerIcon,
  EyeIcon,
  RefreshCwIcon
} from 'lucide-react';
import type { Column } from '@/components/common/DataTable';
import type { ContainerResponse } from '@infrastructor/shared-types';

export function ComposeDeployment() {
  const { deviceHostname, stackName } = useParams<{
    deviceHostname: string;
    stackName: string;
  }>();
  
  const { composeStacks, loading: stackLoading, deployStack, stopStack } = useCompose();
  const { containers, loading: containerLoading, refetch: refetchContainers } = useContainers();
  
  const [actionLoading, setActionLoading] = useState(false);

  // Get current stack data
  const currentStack = composeStacks.find(
    s => s.name === stackName && s.device_hostname === deviceHostname
  );

  // Get containers for this stack
  const stackContainers = containers?.filter(
    c => c.device_hostname === deviceHostname && 
        c.labels?.['com.docker.compose.project'] === stackName
  ) || [];

  const handleStackAction = async (action: 'start' | 'stop' | 'restart') => {
    if (!deviceHostname || !stackName) return;
    
    setActionLoading(true);
    try {
      switch (action) {
        case 'start':
          await deployStack(deviceHostname, stackName);
          break;
        case 'stop':
          await stopStack(deviceHostname, stackName);
          break;
        case 'restart':
          await stopStack(deviceHostname, stackName);
          await deployStack(deviceHostname, stackName);
          break;
      }
      await refetchContainers();
    } catch (error) {
      console.error(`Failed to ${action} stack:`, error);
    } finally {
      setActionLoading(false);
    }
  };

  const containerColumns: Column<ContainerResponse>[] = [
    {
      key: 'name',
      title: 'Service',
      render: (value, container) => (
        <div>
          <div className="font-medium">{container.labels?.['com.docker.compose.service'] || value}</div>
          <div className="text-sm text-gray-500">{value}</div>
        </div>
      ),
    },
    {
      key: 'image',
      title: 'Image',
      render: (value) => (
        <span className="font-mono text-sm">{value}</span>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      render: (value) => <StatusBadge status={value} />,
    },
    {
      key: 'ports',
      title: 'Ports',
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
      key: 'actions',
      title: 'Actions',
      render: (_, container) => (
        <Button variant="outline" size="sm">
          <EyeIcon className="h-3 w-3 mr-1" />
          Logs
        </Button>
      ),
    },
  ];

  if (stackLoading || containerLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
        <span className="ml-2">Loading stack deployment...</span>
      </div>
    );
  }

  if (!currentStack) {
    return (
      <div className="text-center py-12">
        <FileTextIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold">Stack Not Found</h2>
        <p className="text-gray-600">The requested stack could not be found.</p>
      </div>
    );
  }

  const runningContainers = stackContainers.filter(c => c.status === 'running').length;
  const totalServices = stackContainers.length;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{currentStack.name}</h1>
          <p className="text-gray-600">
            Docker Compose Stack on {currentStack.device_hostname}
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={() => refetchContainers()}>
            <RefreshCwIcon className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          
          {currentStack.status === 'running' ? (
            <Button 
              variant="outline" 
              onClick={() => handleStackAction('stop')}
              disabled={actionLoading}
            >
              <StopIcon className="h-4 w-4 mr-2" />
              Stop Stack
            </Button>
          ) : (
            <Button 
              onClick={() => handleStackAction('start')}
              disabled={actionLoading}
            >
              <PlayIcon className="h-4 w-4 mr-2" />
              Start Stack
            </Button>
          )}
          
          <Button 
            variant="outline"
            onClick={() => handleStackAction('restart')}
            disabled={actionLoading}
          >
            <RotateCwIcon className="h-4 w-4 mr-2" />
            Restart
          </Button>
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Stack Status</CardTitle>
            <ActivityIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <StatusBadge status={currentStack.status} />
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Services</CardTitle>
            <PackageIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningContainers}/{totalServices}</div>
            <p className="text-xs text-muted-foreground">Running/Total</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Last Deployed</CardTitle>
            <ClockIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-medium">
              {currentStack.last_deployed 
                ? new Date(currentStack.last_deployed).toLocaleDateString()
                : 'Never'
              }
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Device</CardTitle>
            <ServerIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-medium">{currentStack.device_hostname}</div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Tabs */}
      <Tabs defaultValue="services">
        <TabsList>
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="configuration">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="services">
          <Card>
            <CardHeader>
              <CardTitle>Service Containers</CardTitle>
            </CardHeader>
            <CardContent>
              {stackContainers.length > 0 ? (
                <DataTable
                  data={stackContainers}
                  columns={containerColumns}
                  searchable
                  searchPlaceholder="Search services..."
                  emptyMessage="No containers found for this stack."
                />
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <PackageIcon className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <p>No services deployed yet</p>
                  <p className="text-sm">Deploy the stack to see services here</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle>Stack Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-gray-500">
                <FileTextIcon className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                <p>Stack logs feature coming soon</p>
                <p className="text-sm">Real-time log streaming will be available here</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="configuration">
          <Card>
            <CardHeader>
              <CardTitle>Stack Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium">Stack Name</Label>
                    <p className="text-sm text-gray-600 mt-1">{currentStack.name}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Deployment Path</Label>
                    <p className="text-sm text-gray-600 mt-1 font-mono">
                      {currentStack.path || '/default/path'}
                    </p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Created</Label>
                    <p className="text-sm text-gray-600 mt-1">
                      {new Date(currentStack.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Services Count</Label>
                    <p className="text-sm text-gray-600 mt-1">{currentStack.services_count}</p>
                  </div>
                </div>
                
                {currentStack.compose_content && (
                  <div>
                    <Label className="text-sm font-medium">Docker Compose Content</Label>
                    <pre className="mt-2 bg-gray-50 border rounded-md p-4 text-xs font-mono overflow-x-auto max-h-96">
                      {currentStack.compose_content}
                    </pre>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}