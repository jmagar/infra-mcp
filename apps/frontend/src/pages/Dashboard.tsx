import { useEffect, useState } from 'react';
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
import { generateSampleSparklineData, type SparklineDataPoint } from '@/components/common/Sparkline';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { 
  MetricCardSkeleton, 
  CardSkeleton, 
  SkeletonGroup,
  LoadingState
} from '@/components/ui/skeleton';
import { useDashboardData } from '@/hooks/useDashboardData';
import { cn, componentStyles, chartColors } from '@/lib/design-system';

export function Dashboard() {
  const { 
    overview, 
    deviceMetrics, 
    healthData, 
    loading, 
    error, 
    isConnected: wsConnected, 
    refetch 
  } = useDashboardData();

  // Generate sparkline data for metrics
  const [sparklineData] = useState(() => ({
    devices: generateSampleSparklineData(20, overview?.onlineDevices || 10, 2, 0.1),
    containers: generateSampleSparklineData(20, overview?.runningContainers || 25, 3, 0.2),
    services: generateSampleSparklineData(20, 47, 5, -0.05),
    cpu: generateSampleSparklineData(20, overview?.avgCpuUsage || 45, 15, -0.1),
    memory: generateSampleSparklineData(20, overview?.avgMemoryUsage || 62, 10, 0.05),
    storage: generateSampleSparklineData(20, overview?.storageUsagePercent || 78, 8, 0.02),
    network: generateSampleSparklineData(20, 2.0, 0.5, 0.1),
    responseTime: generateSampleSparklineData(20, 145, 30, -0.15),
  }));

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

  // Handle metric card interactions
  const handleMetricClick = (metric: string) => {
    console.log(`Navigate to ${metric} details`);
    // TODO: Navigate to detailed view
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
        {/* Compact Metrics Grid - Skeleton */}
        <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8">
          <SkeletonGroup stagger={50}>
            {[...Array(8)].map((_, i) => (
              <MetricCardSkeleton 
                key={i} 
                showSparkline={true}
                className="animate-fade-in-up"
                style={{ animationDelay: `${i * 50}ms` }}
              />
            ))}
          </SkeletonGroup>
        </div>

        {/* System Overview Cards - Skeleton */}
        <div className="grid gap-6 grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
          <SkeletonGroup stagger={100}>
            <CardSkeleton className="col-span-1" />
            <CardSkeleton className="col-span-1" />
            <CardSkeleton className="col-span-1 lg:col-span-2 xl:col-span-1" />
          </SkeletonGroup>
        </div>

        {/* Device Status Grid - Skeleton */}
        <CardSkeleton>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="p-4 rounded-lg glass space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 bg-muted rounded-full animate-pulse" />
                    <div className="h-4 bg-muted rounded w-20 animate-pulse" />
                  </div>
                  <div className="h-5 bg-muted rounded w-12 animate-pulse" />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  {[...Array(3)].map((_, j) => (
                    <div key={j} className="text-center p-2 rounded-md bg-muted/30">
                      <div className="h-6 bg-muted rounded w-full animate-pulse mb-1" />
                      <div className="h-3 bg-muted rounded w-8 mx-auto animate-pulse" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardSkeleton>
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
          variant="glass"
          sparklineData={sparklineData.devices}
          showSparkline={true}
          onClick={() => handleMetricClick('devices')}
        />
        
        <MetricCard
          title="Containers"
          value={overview.runningContainers}
          subtitle={`${overview.totalContainers} total`}
          icon={Box}
          status={overview.runningContainers > 0 ? 'success' : 'warning'}
          trend={{ value: +12.1, label: 'vs last week' }}
          size="sm"
          variant="glass"
          sparklineData={sparklineData.containers}
          showSparkline={true}
          onClick={() => handleMetricClick('containers')}
        />

        <MetricCard
          title="Services"
          value={realtimeMetrics.activeServices}
          subtitle={`${realtimeMetrics.failedServices} failed`}
          icon={Zap}
          status={realtimeMetrics.failedServices === 0 ? 'success' : 'error'}
          size="sm"
          variant="glass"
          sparklineData={sparklineData.services}
          showSparkline={true}
          onClick={() => handleMetricClick('services')}
        />

        <MetricCard
          title="CPU Load"
          value={overview.avgCpuUsage}
          unit="%"
          icon={Cpu}
          status={overview.avgCpuUsage < 70 ? 'success' : overview.avgCpuUsage < 90 ? 'warning' : 'error'}
          trend={{ value: -2.3, label: 'vs last hour' }}
          size="sm"
          variant="glass"
          sparklineData={sparklineData.cpu}
          showSparkline={true}
          sparklineColor={overview.avgCpuUsage < 70 ? '#10b981' : overview.avgCpuUsage < 90 ? '#f59e0b' : '#ef4444'}
          onClick={() => handleMetricClick('cpu')}
        />

        <MetricCard
          title="Memory"
          value={overview.avgMemoryUsage}
          unit="%"
          icon={MemoryStick}
          status={overview.avgMemoryUsage < 80 ? 'success' : 'warning'}
          trend={{ value: +1.7, label: 'vs last hour' }}
          size="sm"
          variant="glass"
          sparklineData={sparklineData.memory}
          showSparkline={true}
          sparklineColor={overview.avgMemoryUsage < 80 ? '#10b981' : '#f59e0b'}
          onClick={() => handleMetricClick('memory')}
        />

        <MetricCard
          title="Storage"
          value={overview.storageUsagePercent}
          unit="%"
          icon={HardDrive}
          status={overview.storageUsagePercent < 80 ? 'success' : 'warning'}
          trend={{ value: +0.8, label: 'vs yesterday' }}
          size="sm"
          variant="glass"
          sparklineData={sparklineData.storage}
          showSparkline={true}
          sparklineColor={overview.storageUsagePercent < 80 ? '#10b981' : '#f59e0b'}
          onClick={() => handleMetricClick('storage')}
        />

        <MetricCard
          title="Network"
          value={(realtimeMetrics.networkTraffic.in + realtimeMetrics.networkTraffic.out).toFixed(1)}
          unit="Gbps"
          subtitle="Total I/O"
          icon={Network}
          status="success"
          size="sm"
          variant="glass"
          sparklineData={sparklineData.network}
          showSparkline={true}
          onClick={() => handleMetricClick('network')}
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
          variant="glass"
          sparklineData={sparklineData.responseTime}
          showSparkline={true}
          sparklineColor={realtimeMetrics.avgResponseTime < 200 ? '#10b981' : '#f59e0b'}
          onClick={() => handleMetricClick('response-time')}
        />
      </div>

      {/* System Overview Cards */}
      <div className="grid gap-6 grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
        {/* Real-time System Performance */}
        <Card className="col-span-1 glass-ultra hover:glass-tinted transition-all duration-300 hover-lift group">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors">
                <Activity className="h-5 w-5" />
              </div>
              <span className="gradient-text-primary">System Performance</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                <span className="text-sm text-muted-foreground">Load Average</span>
                <div className="text-right">
                  <div className="text-sm font-mono tabular-nums">
                    {realtimeMetrics.systemLoad[1].toFixed(2)} / {realtimeMetrics.systemLoad[5].toFixed(2)} / {realtimeMetrics.systemLoad[15].toFixed(2)}
                  </div>
                  <div className="text-xs text-muted-foreground">1m / 5m / 15m</div>
                </div>
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                <span className="text-sm text-muted-foreground">Disk I/O</span>
                <div className="text-right">
                  <div className="text-sm font-mono tabular-nums">
                    <span className="text-blue-500">↓{realtimeMetrics.diskIo.read}</span> / <span className="text-orange-500">↑{realtimeMetrics.diskIo.write}</span> {realtimeMetrics.diskIo.unit}
                  </div>
                  <div className="text-xs text-muted-foreground">read / write</div>
                </div>
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                <span className="text-sm text-muted-foreground">System Uptime</span>
                <div className="text-sm font-mono tabular-nums text-green-600 dark:text-green-400">{realtimeMetrics.uptime}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Top Processes */}
        <Card className="col-span-1 glass-ultra hover:glass-tinted transition-all duration-300 hover-lift group">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 group-hover:bg-orange-200 dark:group-hover:bg-orange-900/30 transition-colors">
                <Cpu className="h-5 w-5" />
              </div>
              <span className="gradient-text-orange">Top Processes</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {realtimeMetrics.topProcesses.map((process, index) => (
                <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-all duration-200 hover:scale-[1.02] cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "h-8 w-8 rounded-md flex items-center justify-center text-xs font-mono transition-colors",
                      index === 0 && "bg-gradient-to-br from-orange-400 to-red-500 text-white",
                      index === 1 && "bg-gradient-to-br from-yellow-400 to-orange-500 text-white",
                      index === 2 && "bg-gradient-to-br from-blue-400 to-cyan-500 text-white",
                    )}>
                      {index + 1}
                    </div>
                    <div>
                      <div className="text-sm font-medium font-mono">{process.name}</div>
                    </div>
                  </div>
                  <div className="text-right text-xs font-mono space-y-1">
                    <div className="flex items-center gap-1">
                      <span className="text-muted-foreground">CPU:</span>
                      <span className={cn(
                        "tabular-nums",
                        process.cpu > 10 ? "text-red-500" : process.cpu > 5 ? "text-yellow-500" : "text-green-500"
                      )}>
                        {process.cpu}%
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-muted-foreground">MEM:</span>
                      <span className={cn(
                        "tabular-nums",
                        process.memory > 15 ? "text-red-500" : process.memory > 8 ? "text-yellow-500" : "text-green-500"
                      )}>
                        {process.memory}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity Stream */}
        <Card className="col-span-1 lg:col-span-2 xl:col-span-1 glass-ultra hover:glass-tinted transition-all duration-300 hover-lift group">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 group-hover:bg-blue-200 dark:group-hover:bg-blue-900/30 transition-colors">
                <Globe className="h-5 w-5" />
              </div>
              <span className="gradient-text-blue">Recent Activity</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {realtimeMetrics.recentEvents.map((event, index) => (
                <div key={index} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-all duration-200 hover:scale-[1.01] cursor-pointer">
                  <div className={cn(
                    "h-3 w-3 rounded-full mt-1.5 flex-shrink-0 animate-pulse",
                    event.type === 'success' && "bg-green-500 shadow-glow shadow-green-500/50",
                    event.type === 'warning' && "bg-yellow-500 shadow-glow shadow-yellow-500/50",
                    event.type === 'info' && "bg-blue-500 shadow-glow shadow-blue-500/50",
                    event.type === 'error' && "bg-red-500 shadow-glow shadow-red-500/50"
                  )} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium leading-relaxed">{event.message}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <div className="flex items-center gap-1">
                        <Server className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs font-mono text-muted-foreground">{event.device}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">{event.time}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Device Status Grid */}
      <Card className="glass-ultra hover:glass-tinted transition-all duration-300 hover-lift group">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors">
              <Server className="h-5 w-5" />
            </div>
            <span className="gradient-text-primary">Device Status Overview</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {deviceMetrics && deviceMetrics.length > 0 ? (
            <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {deviceMetrics.slice(0, 8).map((device, index) => (
                <div key={index} className="p-4 rounded-lg glass hover:glass-tinted transition-all duration-200 hover:scale-[1.02] hover-lift cursor-pointer group/device">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        "h-3 w-3 rounded-full animate-pulse shadow-glow",
                        device.status === 'online' ? "bg-green-500 shadow-green-500/50" : 
                        device.status === 'warning' ? "bg-yellow-500 shadow-yellow-500/50" : "bg-red-500 shadow-red-500/50"
                      )} />
                      <span className="text-sm font-medium font-mono group-hover/device:text-primary transition-colors truncate">{device.hostname}</span>
                    </div>
                    <span className="text-xs text-muted-foreground px-2 py-1 rounded-md bg-muted/50">{device.type}</span>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div className="text-center p-2 rounded-md bg-muted/30 hover:bg-muted/50 transition-colors">
                      <div className={cn(
                        "font-mono text-base tabular-nums",
                        device.cpu > 80 ? "text-red-500" : device.cpu > 60 ? "text-yellow-500" : "text-green-500"
                      )}>
                        {device.cpu}%
                      </div>
                      <div className="text-muted-foreground mt-1">CPU</div>
                    </div>
                    <div className="text-center p-2 rounded-md bg-muted/30 hover:bg-muted/50 transition-colors">
                      <div className={cn(
                        "font-mono text-base tabular-nums",
                        device.memory > 85 ? "text-red-500" : device.memory > 70 ? "text-yellow-500" : "text-green-500"
                      )}>
                        {device.memory}%
                      </div>
                      <div className="text-muted-foreground mt-1">MEM</div>
                    </div>
                    <div className="text-center p-2 rounded-md bg-muted/30 hover:bg-muted/50 transition-colors">
                      <div className={cn(
                        "font-mono text-base tabular-nums",
                        device.disk > 90 ? "text-red-500" : device.disk > 75 ? "text-yellow-500" : "text-green-500"
                      )}>
                        {device.disk}%
                      </div>
                      <div className="text-muted-foreground mt-1">DISK</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-bounce mb-4">
                <Server className="h-12 w-12 text-muted-foreground/50" />
              </div>
              <PageEmpty
                title="No device data available"
                description="Waiting for device metrics to load..."
              />
            </div>
          )}
        </CardContent>
      </Card>
    </DashboardPage>
  );
}