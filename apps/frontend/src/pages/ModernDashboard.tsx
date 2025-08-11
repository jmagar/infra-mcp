import * as React from "react"
import { useDevices } from "@/hooks/useDevices"
import { useSystemMetrics } from "@/hooks/useSystemMetrics"
import { wsClient } from "@/services/ws"
import { 
  Server, 
  Container, 
  Activity, 
  HardDrive, 
  Cpu, 
  MemoryStick, 
  Network,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  Clock,
  Users,
  Database,
  Zap
} from "lucide-react"
import { 
  ModernCard, 
  ModernCardHeader, 
  ModernCardContent, 
  ModernCardFooter,
  Metric,
  ProgressBar,
  StatusIndicator 
} from "@/components/ui/modern-card"
import { Sparkline, generateSparklineData } from "@/components/ui/sparkline"
import { cn, spacing, typography, animations, statusColors, glassStyles } from "@/lib/modern-design-system"
import { Button } from "@/components/ui/button"

// Mock data with proper structure (will be replaced with real data)
const systemMetricsData = {
  overview: {
    totalDevices: 12,
    onlineDevices: 10,
    offlineDevices: 2,
    totalContainers: 48,
    runningContainers: 42,
    stoppedContainers: 6,
    totalServices: 156,
    healthyServices: 142,
    unhealthyServices: 14,
  },
  performance: {
    avgCpuUsage: 34.2,
    avgMemoryUsage: 67.8,
    avgDiskUsage: 45.1,
    networkThroughput: 2.4, // GB/s
    responseTime: 145, // ms
    uptime: 99.7, // percentage
  },
  sparklines: {
    cpu: generateSparklineData(24, 'volatile'),
    memory: generateSparklineData(24, 'up'),
    disk: generateSparklineData(24, 'up'),
    network: generateSparklineData(24, 'volatile'),
    response: generateSparklineData(24, 'down'),
  },
  alerts: [
    {
      id: 1,
      type: "warning",
      message: "High memory usage on database server",
      device: "db-server-01",
      timestamp: new Date(Date.now() - 300000), // 5 min ago
      severity: "medium"
    },
    {
      id: 2, 
      type: "error",
      message: "Container failed to start",
      device: "app-server-02",
      timestamp: new Date(Date.now() - 900000), // 15 min ago
      severity: "high"
    },
    {
      id: 3,
      type: "info", 
      message: "Backup completed successfully",
      device: "backup-server",
      timestamp: new Date(Date.now() - 3600000), // 1 hour ago
      severity: "low"
    }
  ]
}

const deviceStatus = [
  {
    hostname: "web-server-01",
    ip: "192.168.1.10",
    status: "online" as const,
    cpu: 23.4,
    memory: 45.2,
    disk: 67.8,
    uptime: "15d 4h 32m",
    containers: 8,
    services: 12
  },
  {
    hostname: "app-server-01", 
    ip: "192.168.1.11",
    status: "online" as const,
    cpu: 67.1,
    memory: 78.9,
    disk: 34.5,
    uptime: "12d 18h 45m",
    containers: 12,
    services: 18
  },
  {
    hostname: "db-server-01",
    ip: "192.168.1.12", 
    status: "warning" as const,
    cpu: 89.3,
    memory: 92.1,
    disk: 56.7,
    uptime: "8d 22h 15m",
    containers: 4,
    services: 6
  },
  {
    hostname: "backup-server",
    ip: "192.168.1.15",
    status: "online" as const,
    cpu: 12.7,
    memory: 23.4,
    disk: 89.2,
    uptime: "25d 6h 12m", 
    containers: 2,
    services: 4
  },
  {
    hostname: "staging-01",
    ip: "192.168.1.20",
    status: "offline" as const,
    cpu: 0,
    memory: 0,
    disk: 45.6,
    uptime: "0d 0h 0m",
    containers: 0,
    services: 0
  }
]

const topProcesses = [
  { name: "nginx", cpu: 12.4, memory: 156.7, device: "web-server-01" },
  { name: "postgres", cpu: 34.2, memory: 2048.3, device: "db-server-01" },
  { name: "redis", cpu: 8.9, memory: 512.1, device: "app-server-01" },
  { name: "docker", cpu: 15.6, memory: 234.8, device: "web-server-01" },
  { name: "node", cpu: 23.1, memory: 445.2, device: "app-server-01" },
]

export function ModernDashboard() {
  const [refreshing, setRefreshing] = React.useState(false)
  const [selectedTimeRange, setSelectedTimeRange] = React.useState("24h")
  const { devices, loading: devicesLoading, error: devicesError, fetchDevices } = useDevices()
  const [systemMetrics, setSystemMetrics] = React.useState(systemMetricsData)

  // Calculate real metrics from devices
  const realMetrics = React.useMemo(() => {
    const onlineDevices = devices.filter(d => d.status === 'online').length
    const offlineDevices = devices.filter(d => d.status === 'offline').length
    const warningDevices = devices.filter(d => d.status === 'warning').length
    
    return {
      overview: {
        totalDevices: devices.length,
        onlineDevices,
        offlineDevices: offlineDevices + warningDevices,
        totalContainers: systemMetricsData.overview.totalContainers,
        runningContainers: systemMetricsData.overview.runningContainers,
        stoppedContainers: systemMetricsData.overview.stoppedContainers,
        totalServices: systemMetricsData.overview.totalServices,
        healthyServices: systemMetricsData.overview.healthyServices,
        unhealthyServices: systemMetricsData.overview.unhealthyServices,
      },
      performance: systemMetricsData.performance,
      sparklines: systemMetricsData.sparklines,
      alerts: systemMetricsData.alerts,
    }
  }, [devices])

  // WebSocket subscription for real-time updates
  React.useEffect(() => {
    const unsubscribe = wsClient.subscribe('device_status', (data) => {
      console.log('Device status update:', data)
      // Refresh devices when we get updates
      fetchDevices()
    })

    return unsubscribe
  }, [fetchDevices])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await fetchDevices()
      // TODO: Add system metrics refresh here
    } catch (error) {
      console.error('Error refreshing data:', error)
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className={cn("min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-zinc-900", spacing.container.lg, spacing.stack.xl)}>
      {/* Enhanced Header with better hierarchy */}
      <header className={cn("relative z-10", animations.slideInFromTop)}>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className={spacing.stack.sm}>
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg blur opacity-75"></div>
                <div className="relative bg-gray-900 rounded-lg p-2">
                  <Activity className="h-8 w-8 text-blue-500" />
                </div>
              </div>
              <div>
                <h1 className={cn(typography.display.lg, "bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent")}>
                  Infrastructure Dashboard
                </h1>
                <p className={cn(typography.caption.lg, "text-gray-400 mt-1")}>
                  Real-time overview of your infrastructure health and performance
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="flex items-center gap-3">
              <StatusIndicator 
                status="online" 
                label="Live Data" 
                pulse 
                size="md"
              />
              <div className="text-xs text-gray-400">
                Updated {new Date().toLocaleTimeString()}
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <select 
                value={selectedTimeRange}
                onChange={(e) => setSelectedTimeRange(e.target.value)}
                className={cn(
                  "px-3 py-2 rounded-lg text-sm",
                  glassStyles.card,
                  "focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                )}
              >
                <option value="1h">Last Hour</option>
                <option value="6h">Last 6 Hours</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
              </select>
              
              <Button 
                variant="secondary" 
                onClick={handleRefresh}
                disabled={refreshing}
                className="gap-2"
              >
                <Activity className={cn("h-4 w-4", refreshing && "animate-spin")} />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Enhanced Key Metrics Section */}
      <section className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/5 via-purple-600/5 to-pink-600/5 rounded-3xl -z-10"></div>
        
        <div className={spacing.stack.md}>
          <div className="flex items-center gap-3 mb-6">
            <Database className="h-5 w-5 text-blue-500" />
            <h2 className={cn(typography.heading.lg, "text-gray-100")}>
              Key Infrastructure Metrics
            </h2>
          </div>
          
          <div className={cn(
            "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4",
            spacing.gap.lg,
            animations.slideInFromBottom
          )}>
            <ModernCard variant="elevated" animation="scale" className="group hover:scale-[1.02] transition-transform duration-300">
              <ModernCardContent className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-full -translate-y-10 translate-x-10"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-4">
                    <Server className="h-5 w-5 text-blue-500" />
                    <span className={cn(typography.caption.md, "uppercase tracking-wide text-blue-400")}>
                      Infrastructure
                    </span>
                  </div>
                  <Metric
                    label="Total Devices"
                    value={realMetrics.overview.totalDevices}
                    size="lg"
                    trend="up"
                    trendValue="+2"
                    status="running"
                  />
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
                    <StatusIndicator status="online" label={`${realMetrics.overview.onlineDevices} Online`} size="sm" />
                    <StatusIndicator status="offline" label={`${realMetrics.overview.offlineDevices} Offline`} size="sm" />
                  </div>
                </div>
              </ModernCardContent>
            </ModernCard>

            <ModernCard variant="elevated" animation="scale" className="group hover:scale-[1.02] transition-transform duration-300">
              <ModernCardContent className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-full -translate-y-10 translate-x-10"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-4">
                    <Container className="h-5 w-5 text-green-500" />
                    <span className={cn(typography.caption.md, "uppercase tracking-wide text-green-400")}>
                      Containers
                    </span>
                  </div>
                  <Metric
                    label="Running Containers"
                    value={realMetrics.overview.runningContainers}
                    unit={`of ${realMetrics.overview.totalContainers}`}
                    size="lg"
                    trend="up"
                    trendValue="+8"
                    status="online"
                  />
                  <ProgressBar 
                    value={realMetrics.overview.runningContainers}
                    max={realMetrics.overview.totalContainers}
                    status="online"
                    className="mt-6"
                    size="lg"
                  />
                </div>
              </ModernCardContent>
            </ModernCard>

            <ModernCard variant="elevated" animation="scale" className="group hover:scale-[1.02] transition-transform duration-300">
              <ModernCardContent className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-full -translate-y-10 translate-x-10"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-4">
                    <CheckCircle className="h-5 w-5 text-purple-500" />
                    <span className={cn(typography.caption.md, "uppercase tracking-wide text-purple-400")}>
                      System Health
                    </span>
                  </div>
                  <Metric
                    label="Overall Uptime"
                    value={realMetrics.performance.uptime}
                    unit="%"
                    size="lg"
                    status="online"
                  />
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
                    <StatusIndicator status="online" label={`${realMetrics.overview.healthyServices} Healthy`} size="sm" />
                    <StatusIndicator status="warning" label={`${realMetrics.overview.unhealthyServices} Issues`} size="sm" />
                  </div>
                </div>
              </ModernCardContent>
            </ModernCard>

            <ModernCard variant="elevated" animation="scale" className="group hover:scale-[1.02] transition-transform duration-300">
              <ModernCardContent className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-orange-500/10 to-red-500/10 rounded-full -translate-y-10 translate-x-10"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-4">
                    <Zap className="h-5 w-5 text-orange-500" />
                    <span className={cn(typography.caption.md, "uppercase tracking-wide text-orange-400")}>
                      Performance
                    </span>
                  </div>
                  <Metric
                    label="Avg Response Time"
                    value={realMetrics.performance.responseTime}
                    unit="ms"
                    size="lg"
                    trend="down"
                    trendValue="-12ms"
                    status="online"
                  />
                  <div className="flex items-center gap-2 mt-6 pt-4 border-t border-white/10">
                    <TrendingDown className="h-4 w-4 text-green-500" />
                    <span className={cn(typography.caption.md, "text-green-500 font-medium")}>
                      Performance improved
                    </span>
                  </div>
                </div>
              </ModernCardContent>
            </ModernCard>
          </div>
        </div>
      </section>

      {/* Main Content Grid */}
      <div className={cn(
        "grid grid-cols-1 xl:grid-cols-3",
        spacing.gap.lg,
        animations.fadeIn
      )}>
        {/* System Performance */}
        <div className="xl:col-span-2 space-y-6">
          <ModernCard variant="default" size="lg">
            <ModernCardHeader
              title={
                <div className="flex items-center gap-3">
                  <Activity className="h-5 w-5 text-blue-500" />
                  System Performance
                </div>
              }
              description="Real-time resource utilization across all systems"
              actions={
                <Button variant="ghost" size="sm">
                  <TrendingUp className="h-4 w-4" />
                </Button>
              }
            />
            <ModernCardContent>
              <div className={cn("grid grid-cols-1 md:grid-cols-3", spacing.gap.lg)}>
                <div className={cn(spacing.stack.sm, "relative group")}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Cpu className={cn("h-4 w-4 text-blue-500", animations.iconBounce)} />
                      <span className={typography.body.md}>CPU Usage</span>
                    </div>
                    <div className="opacity-60 group-hover:opacity-100 transition-opacity">
                      <Sparkline 
                        data={realMetrics.sparklines.cpu} 
                        width={60} 
                        height={20}
                        color="rgba(59, 130, 246, 0.8)"
                        animated
                      />
                    </div>
                  </div>
                  <Metric
                    label="Average across all systems"
                    value={realMetrics.performance.avgCpuUsage}
                    unit="%"
                    trend="neutral"
                    status="running"
                  />
                  <ProgressBar
                    value={realMetrics.performance.avgCpuUsage}
                    status="running"
                    className="mt-3"
                  />
                </div>

                <div className={cn(spacing.stack.sm, "relative group")}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <MemoryStick className={cn("h-4 w-4 text-green-500", animations.iconBounce)} />
                      <span className={typography.body.md}>Memory Usage</span>
                    </div>
                    <div className="opacity-60 group-hover:opacity-100 transition-opacity">
                      <Sparkline 
                        data={realMetrics.sparklines.memory} 
                        width={60} 
                        height={20}
                        color="rgba(34, 197, 94, 0.8)"
                        animated
                      />
                    </div>
                  </div>
                  <Metric
                    label="Average across all systems"
                    value={realMetrics.performance.avgMemoryUsage}
                    unit="%"
                    trend="up"
                    trendValue="+5%"
                    status="warning"
                  />
                  <ProgressBar
                    value={realMetrics.performance.avgMemoryUsage}
                    status="warning"
                    className="mt-3"
                  />
                </div>

                <div className={cn(spacing.stack.sm, "relative group")}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <HardDrive className={cn("h-4 w-4 text-purple-500", animations.iconBounce)} />
                      <span className={typography.body.md}>Storage Usage</span>
                    </div>
                    <div className="opacity-60 group-hover:opacity-100 transition-opacity">
                      <Sparkline 
                        data={realMetrics.sparklines.disk} 
                        width={60} 
                        height={20}
                        color="rgba(168, 85, 247, 0.8)"
                        animated
                      />
                    </div>
                  </div>
                  <Metric
                    label="Average across all systems"
                    value={realMetrics.performance.avgDiskUsage}
                    unit="%"
                    trend="up"
                    trendValue="+2%"
                    status="online"
                  />
                  <ProgressBar
                    value={realMetrics.performance.avgDiskUsage}
                    status="online"
                    className="mt-3"
                  />
                </div>
              </div>
            </ModernCardContent>
          </ModernCard>

          {/* Device Status Overview */}
          <ModernCard variant="default" size="auto">
            <ModernCardHeader
              title={
                <div className="flex items-center gap-3">
                  <Server className="h-5 w-5 text-primary" />
                  Device Status Overview
                </div>
              }
              description="Current status and metrics for all infrastructure devices"
            />
            <ModernCardContent>
              <div className={spacing.stack.md}>
                {devices.length > 0 ? devices.map((device, index) => (
                  <div
                    key={device.hostname}
                    className={cn(
                      "relative overflow-hidden rounded-xl p-4",
                      statusColors[device.status].bg,
                      statusColors[device.status].border,
                      "border",
                      animations.fadeIn
                    )}
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <StatusIndicator
                          status={device.status}
                          pulse={device.status === 'online'}
                          size="md"
                        />
                        <div>
                          <h4 className={cn(typography.heading.sm, "font-mono")}>
                            {device.hostname}
                          </h4>
                          <p className={cn(typography.caption.md, "text-muted-foreground")}>
                            {device.ip_address || 'No IP'} • {device.device_type}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-center">
                          <div className={cn(typography.body.sm, "font-mono", statusColors[device.status].text)}>
                            N/A
                          </div>
                          <div className={typography.caption.sm}>CPU</div>
                        </div>
                        <div className="text-center">
                          <div className={cn(typography.body.sm, "font-mono", statusColors[device.status].text)}>
                            N/A
                          </div>
                          <div className={typography.caption.sm}>RAM</div>
                        </div>
                        <div className="text-center">
                          <div className={cn(typography.body.sm, "font-mono", statusColors[device.status].text)}>
                            N/A
                          </div>
                          <div className={typography.caption.sm}>Disk</div>
                        </div>
                        <div className="text-center">
                          <div className={cn(typography.body.sm, statusColors[device.status].text)}>
                            N/A
                          </div>
                          <div className={typography.caption.sm}>Containers</div>
                        </div>
                      </div>
                    </div>
                  </div>
                )) : (
                  <div className="text-center py-8">
                    <div className={cn(typography.body.md, "text-gray-400")}>
                      {devicesLoading ? 'Loading devices...' : 'No devices found'}
                    </div>
                    {devicesError && (
                      <div className={cn(typography.caption.md, "text-red-400 mt-2")}>
                        Error: {devicesError}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </ModernCardContent>
          </ModernCard>
        </div>

        {/* Right Sidebar */}
        <div className={spacing.stack.lg}>
          {/* Alerts */}
          <ModernCard variant="elevated">
            <ModernCardHeader
              title={
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                  Recent Alerts
                </div>
              }
              actions={
                <Button variant="ghost" size="sm">
                  View All
                </Button>
              }
            />
            <ModernCardContent>
              <div className={spacing.stack.sm}>
                {realMetrics.alerts.map((alert, index) => (
                  <div
                    key={alert.id}
                    className={cn(
                      "relative p-3 rounded-lg border-l-4",
                      alert.type === 'error' && statusColors.offline.bg + " border-l-red-500",
                      alert.type === 'warning' && statusColors.warning.bg + " border-l-amber-500",
                      alert.type === 'info' && statusColors.online.bg + " border-l-blue-500",
                      animations.fadeIn
                    )}
                    style={{ animationDelay: `${index * 150}ms` }}
                  >
                    <div className={spacing.stack.xs}>
                      <div className="flex items-center justify-between">
                        <StatusIndicator
                          status={alert.type === 'error' ? 'offline' : alert.type === 'warning' ? 'warning' : 'online'}
                          size="sm"
                        />
                        <span className={typography.caption.sm}>
                          {alert.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                      <p className={typography.body.sm}>{alert.message}</p>
                      <p className={cn(typography.caption.sm, "text-muted-foreground font-mono")}>
                        {alert.device}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ModernCardContent>
          </ModernCard>

          {/* Top Processes */}
          <ModernCard variant="default">
            <ModernCardHeader
              title={
                <div className="flex items-center gap-3">
                  <Zap className="h-5 w-5 text-orange-500" />
                  Top Processes
                </div>
              }
              description="Highest resource consuming processes"
            />
            <ModernCardContent>
              <div className={spacing.stack.sm}>
                {topProcesses.map((process, index) => (
                  <div
                    key={process.name}
                    className={cn(
                      "flex items-center justify-between p-3 rounded-lg bg-white/5",
                      animations.fadeIn
                    )}
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <div>
                      <div className={cn(typography.body.sm, "font-mono font-semibold")}>
                        {process.name}
                      </div>
                      <div className={cn(typography.caption.sm, "text-muted-foreground")}>
                        {process.device}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={cn(typography.body.sm, "font-mono")}>
                        {process.cpu.toFixed(1)}%
                      </div>
                      <div className={cn(typography.caption.sm, "text-muted-foreground")}>
                        {process.memory.toFixed(0)}MB
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ModernCardContent>
          </ModernCard>
        </div>
      </div>
    </div>
  )
}