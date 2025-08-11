import * as React from "react"
import { useDevices, useDevice } from "@/hooks/useDevices"
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
  TrendingDown,
  Database,
  Zap,
  RefreshCw,
  Settings
} from "lucide-react"
import { 
  ModernCard, 
  ModernCardHeader, 
  ModernCardContent, 
  Metric,
  ProgressBar,
  StatusIndicator 
} from "@/components/ui/modern-card"
import { Sparkline, generateSparklineData } from "@/components/ui/sparkline"
import { cn, spacing, typography, animations, statusColors, glassStyles } from "@/lib/modern-design-system"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function UnifiedDashboard() {
  const toIndicatorStatus = (
    s: string
  ): "online" | "offline" | "warning" | "running" | "stopped" | "pending" => {
    switch (s) {
      case "online":
        return "online";
      case "warning":
        return "warning";
      case "running":
        return "running";
      case "stopped":
        return "stopped";
      case "pending":
        return "pending";
      default:
        return "offline";
    }
  }
  const [selectedDeviceId, setSelectedDeviceId] = React.useState<string | null>(null)
  const [refreshing, setRefreshing] = React.useState(false)
  const [selectedTimeRange, setSelectedTimeRange] = React.useState("24h")
  
  const { devices, loading: devicesLoading, error: devicesError, fetchDevices } = useDevices()
  const { device: selectedDevice } = useDevice(selectedDeviceId || '')

  // Auto-select first online device if none selected
  React.useEffect(() => {
    if (!selectedDeviceId && devices.length > 0) {
      const onlineDevice = devices.find(d => d.status === 'online') || devices[0]
      setSelectedDeviceId(onlineDevice.id)
    }
  }, [devices, selectedDeviceId])

  // Calculate metrics from all devices
  const allDevicesMetrics = React.useMemo(() => {
    const onlineDevices = devices.filter(d => d.status === 'online').length
    const offlineDevices = devices.filter(d => d.status === 'offline').length
    const warningDevices = devices.filter(d => d.status === 'warning').length
    
    return {
      totalDevices: devices.length,
      onlineDevices,
      offlineDevices: offlineDevices + warningDevices,
      // Mock data for containers and services - will be replaced with real data
      totalContainers: 48,
      runningContainers: 42,
      stoppedContainers: 6,
      totalServices: 156,
      healthyServices: 142,
      unhealthyServices: 14,
    }
  }, [devices])

  // WebSocket subscription for real-time updates
  React.useEffect(() => {
    const unsubscribe = wsClient.subscribe('device_status', (data) => {
      console.log('Device status update:', data)
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

  const handleDeviceSwitch = (deviceId: string) => {
    setSelectedDeviceId(deviceId)
  }

  return (
    <div className={cn("min-h-screen bg-gradient-to-br from-slate-950 via-gray-950 to-zinc-950", spacing.container.lg, spacing.stack.xl)}>
      {/* Enhanced Header */}
      <header className={cn("relative z-10", animations.slideInFromTop)}>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 lg:gap-6">
          <div className={spacing.stack.sm}>
            <div className="flex items-center gap-3 lg:gap-4">
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl blur opacity-75"></div>
                <div className={cn("relative rounded-xl p-2 lg:p-3", glassStyles.elevated)}>
                  <Database className="h-6 w-6 lg:h-8 lg:w-8 text-blue-400" />
                </div>
              </div>
              <div>
                <h1 className={cn("text-2xl lg:text-4xl font-bold tracking-tight leading-tight text-white")}>
                  Unified Infrastructure Dashboard
                </h1>
                <p className={cn(typography.caption.lg, "text-slate-300 mt-1 hidden sm:block")}>
                  Centralized view of all your devices and services
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 lg:gap-4">
            {/* Device Selector */}
            <div className="flex items-center gap-2 lg:gap-3 w-full sm:w-auto">
              <label className={cn(typography.body.sm, "text-slate-200 font-medium hidden sm:inline")}>Device:</label>
              <Select value={selectedDeviceId || ""} onValueChange={handleDeviceSwitch}>
                <SelectTrigger className={cn("w-full sm:w-[180px] lg:w-[200px] text-white", glassStyles.interactive)}>
                  <SelectValue placeholder="Select device" />
                </SelectTrigger>
                <SelectContent className={cn(glassStyles.elevated, "text-white")}>
                  {devices.map((device) => (
                    <SelectItem key={device.id} value={device.id}>
                      <div className="flex items-center gap-2">
                        <div className={cn(
                          "w-2 h-2 rounded-full",
                          statusColors[device.status].indicator
                        )} />
                        <span>{device.hostname}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full sm:w-auto">
              <div className="flex items-center gap-2">
                <StatusIndicator 
                  status="online" 
                  label="Live Data" 
                  pulse 
                  size="md"
                />
                <div className="text-xs text-gray-300 dark:text-gray-300 font-medium">
                  Updated {new Date().toLocaleTimeString()}
                </div>
              </div>
              
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <select 
                  value={selectedTimeRange}
                  onChange={(e) => setSelectedTimeRange(e.target.value)}
                  className={cn(
                    "flex-1 sm:flex-none px-3 py-2 rounded-lg text-sm text-gray-100 dark:text-gray-100",
                    "bg-slate-800/60 backdrop-blur-md border border-gray-600/50",
                    "focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/60",
                    "hover:bg-slate-800/80 transition-colors"
                  )}
                >
                  <option value="1h" className="bg-slate-800 text-gray-100">Last Hour</option>
                  <option value="6h" className="bg-slate-800 text-gray-100">Last 6 Hours</option>
                  <option value="24h" className="bg-slate-800 text-gray-100">Last 24 Hours</option>
                  <option value="7d" className="bg-slate-800 text-gray-100">Last 7 Days</option>
                </select>
                
                <Button 
                  variant="secondary" 
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="gap-2 shrink-0"
                  size="sm"
                >
                  <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
                  <span className="hidden sm:inline">Refresh</span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Overall Infrastructure Metrics */}
      <section className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/8 to-pink-500/10 rounded-3xl -z-10 backdrop-blur-3xl"></div>
        
        <div className={spacing.stack.md}>
          <div className="flex items-center gap-3 mb-6">
            <div className="relative">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/50 to-purple-500/50 rounded-lg blur-sm opacity-75"></div>
              <div className="relative bg-slate-800/60 backdrop-blur-sm rounded-lg p-2 border border-blue-500/30">
                <Activity className="h-5 w-5 text-blue-400" />
              </div>
            </div>
            <h2 className={cn(typography.heading.lg, "text-white dark:text-white drop-shadow-sm")}>
              Infrastructure Overview
            </h2>
          </div>
          
          <div className={cn(
            "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4",
            spacing.gap.lg,
            animations.slideInFromBottom
          )}>
            <ModernCard variant="elevated" animation="scale" className="group hover:scale-[1.02] transition-transform duration-300">
              <ModernCardContent className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-full -translate-y-10 translate-x-10"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="relative">
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/40 to-cyan-500/40 rounded-lg blur-sm opacity-75"></div>
                      <div className="relative bg-slate-700/60 backdrop-blur-sm rounded-lg p-1.5 border border-blue-500/20">
                        <Server className="h-5 w-5 text-blue-400" />
                      </div>
                    </div>
                    <span className={cn(typography.caption.md, "uppercase tracking-wide text-blue-300 font-semibold")}>
                      Total Devices
                    </span>
                  </div>
                  <Metric
                    label="Infrastructure Devices"
                    value={allDevicesMetrics.totalDevices}
                    size="lg"
                    trend="up"
                    trendValue="+2"
                    status="running"
                  />
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/20">
                    <StatusIndicator status="online" label={`${allDevicesMetrics.onlineDevices} Online`} size="sm" />
                    <StatusIndicator status="offline" label={`${allDevicesMetrics.offlineDevices} Issues`} size="sm" />
                  </div>
                </div>
              </ModernCardContent>
            </ModernCard>

            <ModernCard variant="elevated" animation="scale" className="group hover:scale-[1.02] transition-transform duration-300">
              <ModernCardContent className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-emerald-500/20 to-green-500/20 rounded-full -translate-y-10 translate-x-10"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="relative">
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/40 to-green-500/40 rounded-lg blur-sm opacity-75"></div>
                      <div className="relative bg-slate-700/60 backdrop-blur-sm rounded-lg p-1.5 border border-emerald-500/20">
                        <Container className="h-5 w-5 text-emerald-400" />
                      </div>
                    </div>
                    <span className={cn(typography.caption.md, "uppercase tracking-wide text-emerald-300 font-semibold")}>
                      Containers
                    </span>
                  </div>
                  <Metric
                    label="Running Containers"
                    value={allDevicesMetrics.runningContainers}
                    unit={`of ${allDevicesMetrics.totalContainers}`}
                    size="lg"
                    trend="up"
                    trendValue="+8"
                    status="online"
                  />
                  <ProgressBar 
                    value={allDevicesMetrics.runningContainers}
                    max={allDevicesMetrics.totalContainers}
                    status="online"
                    className="mt-6"
                    size="lg"
                  />
                </div>
              </ModernCardContent>
            </ModernCard>

            <ModernCard variant="elevated" animation="scale" className="group hover:scale-[1.02] transition-transform duration-300">
              <ModernCardContent className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-full -translate-y-10 translate-x-10"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="relative">
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-500/40 to-pink-500/40 rounded-lg blur-sm opacity-75"></div>
                      <div className="relative bg-slate-700/60 backdrop-blur-sm rounded-lg p-1.5 border border-purple-500/20">
                        <CheckCircle className="h-5 w-5 text-purple-400" />
                      </div>
                    </div>
                    <span className={cn(typography.caption.md, "uppercase tracking-wide text-purple-300 font-semibold")}>
                      Services Health
                    </span>
                  </div>
                  <Metric
                    label="Healthy Services"
                    value={allDevicesMetrics.healthyServices}
                    unit={`of ${allDevicesMetrics.totalServices}`}
                    size="lg"
                    status="online"
                  />
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/20">
                    <StatusIndicator status="online" label={`${allDevicesMetrics.healthyServices} OK`} size="sm" />
                    <StatusIndicator status="warning" label={`${allDevicesMetrics.unhealthyServices} Issues`} size="sm" />
                  </div>
                </div>
              </ModernCardContent>
            </ModernCard>

            <ModernCard variant="elevated" animation="scale" className="group hover:scale-[1.02] transition-transform duration-300">
              <ModernCardContent className="relative overflow-hidden">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-orange-500/20 to-red-500/20 rounded-full -translate-y-10 translate-x-10"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="relative">
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-orange-500/40 to-red-500/40 rounded-lg blur-sm opacity-75"></div>
                      <div className="relative bg-slate-700/60 backdrop-blur-sm rounded-lg p-1.5 border border-orange-500/20">
                        <Zap className="h-5 w-5 text-orange-400" />
                      </div>
                    </div>
                    <span className={cn(typography.caption.md, "uppercase tracking-wide text-orange-300 font-semibold")}>
                      Performance
                    </span>
                  </div>
                  <Metric
                    label="Response Time"
                    value="142"
                    unit="ms"
                    size="lg"
                    trend="down"
                    trendValue="-12ms"
                    status="online"
                  />
                  <div className="flex items-center gap-2 mt-6 pt-4 border-t border-white/20">
                    <TrendingDown className="h-4 w-4 text-emerald-400" />
                    <span className={cn(typography.caption.md, "text-emerald-300 font-medium")}>
                      Performance improved
                    </span>
                  </div>
                </div>
              </ModernCardContent>
            </ModernCard>
          </div>
        </div>
      </section>

      {/* Device-Specific Metrics */}
      {selectedDevice && (
        <section className="relative">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/8 via-blue-500/6 to-purple-500/8 rounded-3xl -z-10 backdrop-blur-3xl"></div>
          <div className={spacing.stack.md}>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/50 to-blue-500/50 rounded-lg blur-sm opacity-75"></div>
                  <div className="relative bg-slate-800/60 backdrop-blur-sm rounded-lg p-2 border border-emerald-500/30">
                    <Server className="h-5 w-5 text-emerald-400" />
                  </div>
                </div>
                <h2 className={cn(typography.heading.lg, "text-white dark:text-white drop-shadow-sm")}>
                  {selectedDevice.hostname} Metrics
                </h2>
                <StatusIndicator 
                  status={toIndicatorStatus(String(selectedDevice.status))} 
                  label={String(selectedDevice.status)} 
                  pulse={String(selectedDevice.status) === 'online'}
                />
              </div>
              <Button variant="ghost" size="sm" className="backdrop-blur-md bg-slate-800/40 hover:bg-slate-700/60 border border-slate-600/50">
                <Settings className="h-4 w-4 text-gray-300" />
              </Button>
            </div>

            {/* Device-specific performance metrics */}
            <div className={cn(
              "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
              spacing.gap.lg,
              animations.fadeIn
            )}>
              <ModernCard variant="default" size="lg">
                <ModernCardHeader
                  title={
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/40 to-cyan-500/40 rounded-lg blur-sm opacity-75"></div>
                        <div className="relative bg-slate-700/60 backdrop-blur-sm rounded-lg p-1.5 border border-blue-500/20">
                          <Cpu className="h-5 w-5 text-blue-400" />
                        </div>
                      </div>
                      <span className="text-white dark:text-white font-semibold">CPU & Memory Usage</span>
                    </div>
                  }
                  description={`Real-time metrics for ${selectedDevice.hostname}`}
                />
                <ModernCardContent>
                  <div className={cn("grid grid-cols-1 md:grid-cols-2", spacing.gap.md)}>
                    <div className={cn(spacing.stack.sm, "relative group p-4 rounded-xl backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40")}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Cpu className={cn("h-4 w-4 text-blue-400", animations.iconBounce)} />
                          <span className={cn(typography.body.md, "text-gray-200 font-medium")}>CPU Usage</span>
                        </div>
                        <div className="opacity-60 group-hover:opacity-100 transition-opacity">
                          <Sparkline 
                            data={generateSparklineData(20, 'volatile')} 
                            width={60} 
                            height={20}
                            color="rgba(96, 165, 250, 0.9)"
                            animated
                          />
                        </div>
                      </div>
                      <Metric
                        label="Current usage"
                        value="N/A"
                        unit="%"
                        trend="neutral"
                        status="running"
                      />
                      <ProgressBar
                        value={0}
                        status="running"
                        className="mt-3"
                      />
                    </div>

                    <div className={cn(spacing.stack.sm, "relative group p-4 rounded-xl backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40")}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <MemoryStick className={cn("h-4 w-4 text-emerald-400", animations.iconBounce)} />
                          <span className={cn(typography.body.md, "text-gray-200 font-medium")}>Memory</span>
                        </div>
                        <div className="opacity-60 group-hover:opacity-100 transition-opacity">
                          <Sparkline 
                            data={generateSparklineData(20, 'up')} 
                            width={60} 
                            height={20}
                            color="rgba(52, 211, 153, 0.9)"
                            animated
                          />
                        </div>
                      </div>
                      <Metric
                        label="Memory usage"
                        value="N/A"
                        unit="%"
                        trend="up"
                        trendValue="+5%"
                        status="warning"
                      />
                      <ProgressBar
                        value={0}
                        status="warning"
                        className="mt-3"
                      />
                    </div>
                  </div>
                </ModernCardContent>
              </ModernCard>

              <ModernCard variant="default" size="lg">
                <ModernCardHeader
                  title={
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-500/40 to-pink-500/40 rounded-lg blur-sm opacity-75"></div>
                        <div className="relative bg-slate-700/60 backdrop-blur-sm rounded-lg p-1.5 border border-purple-500/20">
                          <HardDrive className="h-5 w-5 text-purple-400" />
                        </div>
                      </div>
                      <span className="text-white dark:text-white font-semibold">Storage & Network</span>
                    </div>
                  }
                  description="Storage and network utilization"
                />
                <ModernCardContent>
                  <div className={cn("grid grid-cols-1 md:grid-cols-2", spacing.gap.md)}>
                    <div className={cn(spacing.stack.sm, "relative group p-4 rounded-xl backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40")}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <HardDrive className={cn("h-4 w-4 text-purple-400", animations.iconBounce)} />
                          <span className={cn(typography.body.md, "text-gray-200 font-medium")}>Disk Usage</span>
                        </div>
                      </div>
                      <Metric
                        label="Disk utilization"
                        value="N/A"
                        unit="%"
                        status="online"
                      />
                      <ProgressBar
                        value={0}
                        status="online"
                        className="mt-3"
                      />
                    </div>

                    <div className={cn(spacing.stack.sm, "relative group p-4 rounded-xl backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40")}>
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Network className={cn("h-4 w-4 text-orange-400", animations.iconBounce)} />
                          <span className={cn(typography.body.md, "text-gray-200 font-medium")}>Network</span>
                        </div>
                      </div>
                      <Metric
                        label="Network I/O"
                        value="N/A"
                        unit="MB/s"
                        status="online"
                      />
                    </div>
                  </div>
                </ModernCardContent>
              </ModernCard>

              <ModernCard variant="default" size="lg">
                <ModernCardHeader
                  title={
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/40 to-teal-500/40 rounded-lg blur-sm opacity-75"></div>
                        <div className="relative bg-slate-700/60 backdrop-blur-sm rounded-lg p-1.5 border border-emerald-500/20">
                          <Activity className="h-5 w-5 text-emerald-400" />
                        </div>
                      </div>
                      <span className="text-white dark:text-white font-semibold">System Info</span>
                    </div>
                  }
                  description="Device information and status"
                />
                <ModernCardContent>
                  <div className={spacing.stack.sm}>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="p-3 rounded-lg backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40">
                        <span className="text-gray-300 font-medium">Type:</span>
                        <span className="ml-2 capitalize text-white font-mono">{selectedDevice.device_type}</span>
                      </div>
                      <div className="p-3 rounded-lg backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40">
                        <span className="text-gray-300 font-medium">IP:</span>
                        <span className="ml-2 font-mono text-blue-300">{selectedDevice.ip_address || 'N/A'}</span>
                      </div>
                      <div className="p-3 rounded-lg backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40">
                        <span className="text-gray-300 font-medium">SSH Port:</span>
                        <span className="ml-2 text-white font-mono">{selectedDevice.ssh_port || 22}</span>
                      </div>
                      <div className="p-3 rounded-lg backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40">
                        <span className="text-gray-300 font-medium">User:</span>
                        <span className="ml-2 text-purple-300 font-mono">{selectedDevice.ssh_username || 'N/A'}</span>
                      </div>
                      <div className="p-3 rounded-lg backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40 flex items-center gap-2">
                        <span className="text-gray-300 font-medium">Monitoring:</span>
                        <StatusIndicator 
                          status={selectedDevice.monitoring_enabled ? 'online' : 'offline'}
                          label={selectedDevice.monitoring_enabled ? 'Enabled' : 'Disabled'}
                          size="sm"
                        />
                      </div>
                      <div className="p-3 rounded-lg backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40">
                        <span className="text-gray-300 font-medium">Last Seen:</span>
                        <span className="ml-2 text-xs text-gray-300 font-mono">
                          {selectedDevice.last_seen 
                            ? new Date(selectedDevice.last_seen).toLocaleString()
                            : 'Never'
                          }
                        </span>
                      </div>
                    </div>
                    
                    {selectedDevice.description && (
                      <div className="mt-4 pt-4 border-t border-white/10 p-3 rounded-lg backdrop-blur-md bg-slate-800/30 dark:bg-slate-800/40">
                        <span className="text-gray-300 text-sm font-medium">Description:</span>
                        <p className="text-sm mt-1 text-gray-200">{selectedDevice.description}</p>
                      </div>
                    )}
                  </div>
                </ModernCardContent>
              </ModernCard>
            </div>
          </div>
        </section>
      )}

      {/* Loading State */}
      {devicesLoading && (
        <div className="text-center py-12">
          <div className="relative inline-block">
            <div className="absolute -inset-4 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-full blur-lg animate-pulse"></div>
            <div className="relative backdrop-blur-lg bg-slate-800/40 border border-slate-700/50 rounded-2xl p-8">
              <div className={cn(typography.body.lg, "text-gray-200 dark:text-gray-200")}>
                Loading devices...
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {devicesError && (
        <ModernCard variant="elevated" className="backdrop-blur-lg bg-red-900/20 border-red-500/30">
          <ModernCardContent>
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500/40 to-rose-500/40 rounded-lg blur-sm opacity-75"></div>
                <div className="relative bg-slate-800/60 backdrop-blur-sm rounded-lg p-2 border border-red-500/30">
                  <AlertTriangle className="h-5 w-5 text-red-400" />
                </div>
              </div>
              <div>
                <h3 className={cn(typography.heading.sm, "text-red-300 font-semibold")}>
                  Error Loading Data
                </h3>
                <p className={cn(typography.body.sm, "text-red-200/90 mt-1")}>
                  {devicesError}
                </p>
              </div>
            </div>
          </ModernCardContent>
        </ModernCard>
      )}
    </div>
  )
}