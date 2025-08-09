/**
 * Real-Time Dashboard Page
 * Comprehensive live infrastructure monitoring with WebSocket integration
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  RealTimeDashboard as DashboardOverview,
  LiveMetricsChart,
  RealTimeLogsViewer,
} from '@/components/dashboard';
import {
  Activity,
  BarChart3,
  FileText,
  Settings,
  Maximize2,
  Layout,
} from 'lucide-react';
import { useDevices, useResponsive } from '@/hooks';

type DashboardLayout = 'default' | 'metrics-focused' | 'logs-focused' | 'custom';

export function RealTimeDashboardPage() {
  const [selectedLayout, setSelectedLayout] = useState<DashboardLayout>('default');
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [refreshInterval, setRefreshInterval] = useState<number>(5000);
  
  const { devices } = useDevices();
  const { isMobile, isTablet } = useResponsive();

  // Filter devices for real-time monitoring
  const monitoringDevices = devices?.filter(d => d.status === 'online') || [];
  const deviceIds = selectedDevices.length > 0 
    ? selectedDevices 
    : monitoringDevices.map(d => d.id);

  const handleDeviceSelection = (deviceId: string) => {
    setSelectedDevices(prev => 
      prev.includes(deviceId)
        ? prev.filter(id => id !== deviceId)
        : [...prev, deviceId]
    );
  };

  const handleSelectAllDevices = () => {
    setSelectedDevices(monitoringDevices.map(d => d.id));
  };

  const handleClearSelection = () => {
    setSelectedDevices([]);
  };

  // Layout configurations
  const layouts = {
    default: {
      title: 'Default Layout',
      description: 'Balanced overview with all components',
    },
    'metrics-focused': {
      title: 'Metrics Focused',
      description: 'Emphasizes real-time performance charts',
    },
    'logs-focused': {
      title: 'Logs Focused', 
      description: 'Emphasizes live log streaming',
    },
    custom: {
      title: 'Custom Layout',
      description: 'User-customized arrangement',
    },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Live Monitoring</h1>
          <p className="text-muted-foreground">
            Real-time infrastructure monitoring and analytics
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-2">
          <Select value={selectedLayout} onValueChange={(value) => setSelectedLayout(value as DashboardLayout)}>
            <SelectTrigger className="w-48">
              <Layout className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(layouts).map(([key, layout]) => (
                <SelectItem key={key} value={key}>
                  <div>
                    <div className="font-medium">{layout.title}</div>
                    <div className="text-xs text-muted-foreground">{layout.description}</div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={refreshInterval.toString()} onValueChange={(value) => setRefreshInterval(parseInt(value))}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1000">1 second</SelectItem>
              <SelectItem value="5000">5 seconds</SelectItem>
              <SelectItem value="10000">10 seconds</SelectItem>
              <SelectItem value="30000">30 seconds</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Device Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Device Selection</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="flex flex-wrap gap-2">
                {monitoringDevices.map(device => (
                  <Button
                    key={device.id}
                    variant={selectedDevices.includes(device.id) || selectedDevices.length === 0 ? "default" : "outline"}
                    size="sm"
                    onClick={() => handleDeviceSelection(device.id)}
                    className="flex items-center gap-2"
                  >
                    <div className={`w-2 h-2 rounded-full ${
                      device.status === 'online' ? 'bg-green-500' : 'bg-gray-400'
                    }`} />
                    {device.hostname}
                  </Button>
                ))}
              </div>
            </div>
            
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleSelectAllDevices}>
                Select All
              </Button>
              <Button variant="outline" size="sm" onClick={handleClearSelection}>
                Clear
              </Button>
            </div>
          </div>
          
          <p className="text-sm text-muted-foreground mt-2">
            {selectedDevices.length === 0 
              ? `Monitoring all ${monitoringDevices.length} online devices`
              : `Monitoring ${selectedDevices.length} selected devices`
            }
          </p>
        </CardContent>
      </Card>

      {/* Dashboard Content */}
      {selectedLayout === 'default' && (
        <div className="grid gap-6">
          {/* Overview Dashboard */}
          <DashboardOverview />
          
          {/* Charts and Logs Row */}
          <div className="grid lg:grid-cols-2 gap-6">
            <LiveMetricsChart
              deviceIds={deviceIds}
              updateInterval={refreshInterval}
              maxDataPoints={100}
            />
            <div className="h-96">
              <RealTimeLogsViewer
                deviceIds={deviceIds}
                maxLogs={200}
                autoScroll={true}
              />
            </div>
          </div>
        </div>
      )}

      {selectedLayout === 'metrics-focused' && (
        <div className="space-y-6">
          {/* Compact Overview */}
          <Card>
            <CardContent className="py-4">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold">{monitoringDevices.length}</div>
                  <div className="text-sm text-muted-foreground">Devices Online</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">
                    {monitoringDevices.filter(d => d.status === 'online').length}
                  </div>
                  <div className="text-sm text-muted-foreground">Healthy</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">--</div>
                  <div className="text-sm text-muted-foreground">Avg CPU</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-600">--</div>
                  <div className="text-sm text-muted-foreground">Avg Memory</div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          {/* Large Metrics Charts */}
          <div className="grid gap-6">
            <div className="h-96">
              <LiveMetricsChart
                deviceIds={deviceIds}
                updateInterval={refreshInterval}
                maxDataPoints={200}
              />
            </div>
            
            {/* Additional metric views can be added here */}
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="cpu">CPU Details</TabsTrigger>
                <TabsTrigger value="memory">Memory</TabsTrigger>
                <TabsTrigger value="network">Network</TabsTrigger>
              </TabsList>
              
              <TabsContent value="overview" className="space-y-4">
                <div className="h-64">
                  <LiveMetricsChart
                    deviceIds={deviceIds}
                    updateInterval={refreshInterval}
                    maxDataPoints={50}
                  />
                </div>
              </TabsContent>
              
              <TabsContent value="cpu" className="space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <p className="text-muted-foreground">Detailed CPU metrics view</p>
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="memory" className="space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <p className="text-muted-foreground">Detailed memory metrics view</p>
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="network" className="space-y-4">
                <Card>
                  <CardContent className="p-4">
                    <p className="text-muted-foreground">Detailed network metrics view</p>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      )}

      {selectedLayout === 'logs-focused' && (
        <div className="space-y-6">
          {/* Compact Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold">{monitoringDevices.length}</div>
                <div className="text-sm text-muted-foreground">Active Devices</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-blue-600">--</div>
                <div className="text-sm text-muted-foreground">Log Rate/min</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-red-600">--</div>
                <div className="text-sm text-muted-foreground">Errors</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-yellow-600">--</div>
                <div className="text-sm text-muted-foreground">Warnings</div>
              </CardContent>
            </Card>
          </div>
          
          {/* Large Logs Viewer */}
          <div className="h-[600px]">
            <RealTimeLogsViewer
              deviceIds={deviceIds}
              maxLogs={1000}
              autoScroll={true}
            />
          </div>
        </div>
      )}

      {selectedLayout === 'custom' && (
        <div className="space-y-6">
          <Card>
            <CardContent className="p-8 text-center">
              <Settings className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">Custom Layout</h3>
              <p className="text-muted-foreground mb-4">
                Create your own dashboard layout by dragging and arranging components.
              </p>
              <p className="text-sm text-muted-foreground">
                This feature is coming soon in a future update.
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}