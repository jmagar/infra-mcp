import { useEffect } from 'react';
import { 
  Server, 
  Box, 
  Database, 
  Cpu, 
  MemoryStick, 
  HardDrive,
  Network,
  Activity,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Users,
  Clock,
  Zap,
  Shield,
  Globe
} from 'lucide-react';
import { 
  DashboardPage,
  MetricCard,
  MetricsGrid,
  PageEmpty
} from '@/components/common';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { useDashboardData } from '@/hooks/useDashboardData';
import { cn, componentStyles, chartColors } from '@/lib/design-system';

export function EnhancedDashboard() {
  const { 
    overview, 
    deviceMetrics, 
    healthData, 
    loading, 
    error, 
    isConnected: wsConnected, 
    refetch 
  } = useDashboardData();

  // Mock real-time data for demonstration (replace with actual data)
  const realtimeMetrics = {
    networkTraffic: { in: 1.2, out: 0.8, unit: 'Gbps' },
    activeServices: 47,
    failedServices: 2,
    avgResponseTime: 145,
    topProcesses: [
      { name: 'nginx', cpu: 12.3, memory: 4.2 },
      { name: 'postgres', cpu: 8.7, memory: 15.6 },
      { name: 'redis', cpu: 3.1, memory: 2.8 },
    ],
    recentEvents: [
      { type: 'info', message: 'Backup completed successfully', time: '2m ago', device: 'srv-01' },
      { type: 'warning', message: 'High memory usage detected', time: '5m ago', device: 'srv-03' },
      { type: 'success', message: 'Service deployment completed', time: '8m ago', device: 'srv-02' },
    ],
    systemLoad: { 1: 0.45, 5: 0.52, 15: 0.38 },
    diskIo: { read: 45.2, write: 23.7, unit: 'MB/s' },
    uptime: '45d 12h 34m'
  };

  if (loading) {
    return (
      <DashboardPage
        title="Infrastructure Dashboard"
        description="Complete overview of your infrastructure health and status"
        actions={
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Activity className="h-4 w-4 animate-pulse" />
              Loading...
            </div>
          </div>
        }
      >
        <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="space-y-2">
                  <div className="h-4 bg-muted rounded w-1/3" />
                  <div className="h-8 bg-muted rounded w-1/2" />
                  <div className="h-3 bg-muted rounded w-2/3" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </DashboardPage>
    );
  }

  if (error) {
    return (
      <DashboardPage
        title="Infrastructure Dashboard"
        description="Unable to load dashboard data"
        actions={
          <button 
            onClick={refetch}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            <Activity className="h-4 w-4" />
            Retry
          </button>
        }
      >
        <PageEmpty
          title="Failed to load dashboard data"
          description={error}
          action={
            <button 
              onClick={refetch}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              Retry Loading
            </button>
          }
        />
      </DashboardPage>
    );
  }

  return (
    <DashboardPage
      title="Infrastructure Dashboard"
      description="Real-time overview of your infrastructure health and performance"
      actions={
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <div className={cn(
              "h-2 w-2 rounded-full",
              wsConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
            )} />
            <span className="text-muted-foreground">
              {wsConnected ? 'Live Data' : 'Offline'}
            </span>
          </div>
          <button 
            onClick={refetch}
            className="flex items-center gap-2 px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-md text-sm transition-colors"
          >
            <Activity className="h-4 w-4" />
            Refresh
          </button>
        </div>
      }
    >
      {/* Compact Metrics Grid - High Information Density */}
      <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8">
        {/* Infrastructure Status */}
        <MetricCard
          title="Devices"
          value={overview.onlineDevices}
          subtitle={`${overview.totalDevices} total`}
          icon={Server}
          status={overview.onlineDevices === overview.totalDevices ? 'success' : 'warning'}
          trend={{ value: +5.2, label: 'vs last week' }}
          size="sm"
          variant="elevated"
        />
        
        <MetricCard
          title="Containers"
          value={overview.runningContainers}
          subtitle={`${overview.totalContainers} total`}
          icon={Box}
          status={overview.runningContainers > 0 ? 'success' : 'warning'}
          trend={{ value: +12.1, label: 'vs last week' }}
          size="sm"
          variant="elevated"
        />

        <MetricCard
          title="Services"
          value={realtimeMetrics.activeServices}
          subtitle={`${realtimeMetrics.failedServices} failed`}
          icon={Zap}
          status={realtimeMetrics.failedServices === 0 ? 'success' : 'error'}
          size="sm"
          variant="elevated"
        />

        <MetricCard
          title="CPU Load"
          value={overview.avgCpuUsage}
          unit="%"
          icon={Cpu}
          status={overview.avgCpuUsage < 70 ? 'success' : overview.avgCpuUsage < 90 ? 'warning' : 'error'}
          trend={{ value: -2.3, label: 'vs last hour' }}
          size="sm"
          variant="elevated"
        />

        <MetricCard
          title="Memory"
          value={overview.avgMemoryUsage}
          unit="%"
          icon={MemoryStick}
          status={overview.avgMemoryUsage < 80 ? 'success' : 'warning'}
          trend={{ value: +1.7, label: 'vs last hour' }}
          size="sm"
          variant="elevated"
        />

        <MetricCard
          title="Storage"
          value={overview.storageUsagePercent}
          unit="%"
          icon={HardDrive}
          status={overview.storageUsagePercent < 80 ? 'success' : 'warning'}
          trend={{ value: +0.8, label: 'vs yesterday' }}
          size="sm"
          variant="elevated"
        />

        <MetricCard
          title="Network"
          value={realtimeMetrics.networkTraffic.in + realtimeMetrics.networkTraffic.out}
          unit="Gbps"
          subtitle="Total I/O"
          icon={Network}
          status="success"
          size="sm"
          variant="elevated"
        />

        <MetricCard
          title="Response"
          value={realtimeMetrics.avgResponseTime}
          unit="ms"
          subtitle="Avg time"
          icon={Clock}
          status={realtimeMetrics.avgResponseTime < 200 ? 'success' : 'warning'}
          trend={{ value: -8.4, label: 'improved' }}
          size="sm"
          variant="elevated"
        />
      </div>

      {/* System Overview Cards */}
      <div className="grid gap-6 grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
        {/* Real-time System Performance */}
        <Card variant="elevated" className="col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              System Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Load Average</span>
                <div className="text-right">
                  <div className="text-sm font-mono">
                    {realtimeMetrics.systemLoad[1].toFixed(2)} / {realtimeMetrics.systemLoad[5].toFixed(2)} / {realtimeMetrics.systemLoad[15].toFixed(2)}
                  </div>
                  <div className="text-xs text-muted-foreground">1m / 5m / 15m</div>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Disk I/O</span>
                <div className="text-right">
                  <div className="text-sm font-mono">
                    ↓{realtimeMetrics.diskIo.read} / ↑{realtimeMetrics.diskIo.write} {realtimeMetrics.diskIo.unit}
                  </div>
                  <div className="text-xs text-muted-foreground">read / write</div>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">System Uptime</span>
                <div className="text-sm font-mono">{realtimeMetrics.uptime}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Top Processes */}
        <Card variant="elevated" className="col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-orange-500" />
              Top Processes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {realtimeMetrics.topProcesses.map((process, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 bg-muted rounded-md flex items-center justify-center">
                      <span className="text-xs font-mono">{index + 1}</span>
                    </div>
                    <div>
                      <div className="text-sm font-medium">{process.name}</div>
                    </div>
                  </div>
                  <div className="text-right text-xs font-mono space-y-1">
                    <div>CPU: {process.cpu}%</div>
                    <div className="text-muted-foreground">MEM: {process.memory}%</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity Stream */}
        <Card variant="elevated" className="col-span-1 lg:col-span-2 xl:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-blue-500" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {realtimeMetrics.recentEvents.map((event, index) => (
                <div key={index} className="flex items-start gap-3 py-2">
                  <div className={cn(
                    "h-2 w-2 rounded-full mt-2 flex-shrink-0",
                    event.type === 'success' && "bg-green-500",
                    event.type === 'warning' && "bg-yellow-500",
                    event.type === 'info' && "bg-blue-500",
                    event.type === 'error' && "bg-red-500"
                  )} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{event.message}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">{event.device}</span>
                      <span className="text-xs text-muted-foreground">•</span>
                      <span className="text-xs text-muted-foreground">{event.time}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Device Status Grid */}
      <Card variant="elevated">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5 text-primary" />
            Device Status Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          {deviceMetrics && deviceMetrics.length > 0 ? (
            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {deviceMetrics.slice(0, 8).map((device, index) => (
                <div key={index} className="p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        "h-2 w-2 rounded-full",
                        device.status === 'online' ? "bg-green-500" : 
                        device.status === 'warning' ? "bg-yellow-500" : "bg-red-500"
                      )} />
                      <span className="text-sm font-medium truncate">{device.hostname}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{device.type}</span>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="text-center">
                      <div className="font-mono">{device.cpu}%</div>
                      <div className="text-muted-foreground">CPU</div>
                    </div>
                    <div className="text-center">
                      <div className="font-mono">{device.memory}%</div>
                      <div className="text-muted-foreground">MEM</div>
                    </div>
                    <div className="text-center">
                      <div className="font-mono">{device.disk}%</div>
                      <div className="text-muted-foreground">DISK</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <PageEmpty
              title="No device data available"
              description="Waiting for device metrics to load..."
            />
          )}
        </CardContent>
      </Card>
    </DashboardPage>
  );
}