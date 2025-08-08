import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/common';
import { useDashboardData } from '@/hooks/useDashboardData';
import { useResponsive } from '@/hooks/useResponsive';
import { gridConfigs, spacing, typography, layout } from '@/lib/responsive';
import { 
  Server as ServerIcon, 
  Box as CubeIcon, 
  Database as CircleStackIcon, 
  Heart as HeartIcon,
  Clock as ClockIcon,
  AlertTriangle as ExclamationTriangleIcon,
  CheckCircle as CheckCircleIcon 
} from 'lucide-react';

// Import API test utility for development
import { logAPITestResults } from '@/utils/api-test';

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
  const { isMobile, isTablet } = useResponsive();

  // Development: Test API integration on mount
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log('🚀 Dashboard loaded - running API tests...');
      logAPITestResults();
      
      // Log comprehensive data
      console.log('📊 Dashboard Overview:', overview);
      console.log('🖥️ Device Metrics:', deviceMetrics);
      console.log('💾 Health Data:', healthData);
    }
  }, [overview, deviceMetrics, healthData]);

  const getHealthStatusColor = (status: string) => {
    switch (status) {
      case 'excellent': return 'text-green-600';
      case 'good': return 'text-green-500';
      case 'warning': return 'text-yellow-600';
      case 'critical': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getHealthStatusIcon = (status: string) => {
    switch (status) {
      case 'excellent': return <CheckCircleIcon className="h-5 w-5" />;
      case 'good': return <HeartIcon className="h-5 w-5" />;
      case 'warning': return <ExclamationTriangleIcon className="h-5 w-5" />;
      case 'critical': return <ExclamationTriangleIcon className="h-5 w-5" />;
      default: return <HeartIcon className="h-5 w-5" />;
    }
  };

  // Get alerts from healthData or create empty array
  const alerts = healthData?.alerts || [];
  const recentAlerts = alerts.slice(0, 5); // Show last 5 alerts

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-indigo-900">
      <div className="px-3 sm:px-4 md:px-6 py-4 sm:py-6 md:py-8 max-w-7xl mx-auto">
        {/* Mobile-Optimized Header */}
        <div className="mb-4 sm:mb-6 md:mb-8">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl sm:rounded-2xl blur-xl"></div>
            <div className="relative bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-white/20 dark:border-slate-700/50 rounded-xl sm:rounded-2xl p-4 sm:p-6 md:p-8 shadow-xl">
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-1 sm:mb-2 leading-tight">
                Infrastructure Dashboard
              </h1>
              <p className="text-slate-600 dark:text-slate-300 text-sm sm:text-base md:text-lg leading-relaxed">
                Real-time monitoring and management of your infrastructure
              </p>
              
              {/* Mobile-Optimized Connection Status */}
              <div className="flex items-center justify-between mt-3 sm:mt-4">
                <div className="flex items-center space-x-2 sm:space-x-3">
                  <div className="relative">
                    <div className={`w-2 h-2 sm:w-3 sm:h-3 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-red-500'}`}>
                      {wsConnected && (
                        <div className="absolute inset-0 w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-emerald-500 animate-ping opacity-75"></div>
                      )}
                    </div>
                  </div>
                  <span className="text-slate-700 dark:text-slate-200 font-medium text-sm sm:text-base">
                    {wsConnected ? 'Live Data Stream Active' : 'Connection Lost'}
                  </span>
                </div>
                <span className="text-xs sm:text-sm text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 sm:px-3 py-1 rounded-full">
                  {overview.totalDevices} devices
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile-First Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6 mb-4 sm:mb-6 md:mb-8">
          {/* Devices Card */}
          <div className="group relative touch-manipulation">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-lg sm:rounded-xl blur opacity-75 group-active:opacity-100 transition duration-300"></div>
            <div className="relative bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/30 dark:border-slate-700/30 rounded-lg sm:rounded-xl p-3 sm:p-4 md:p-6 shadow-xl active:shadow-2xl transition-all duration-300 active:-translate-y-1">
              <div className="flex items-start justify-between mb-2 sm:mb-3 md:mb-4">
                <div className="p-2 sm:p-2.5 md:p-3 bg-blue-500/10 dark:bg-blue-400/10 rounded-md sm:rounded-lg">
                  <ServerIcon className="h-4 w-4 sm:h-5 sm:w-5 md:h-6 md:w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="text-right min-w-0 flex-1 ml-2 sm:ml-3">
                  <div className="text-lg sm:text-xl md:text-2xl font-bold text-slate-800 dark:text-slate-100 leading-tight">
                    {overview.onlineDevices}
                    <span className="text-xs sm:text-sm font-normal text-slate-500">/{overview.totalDevices}</span>
                  </div>
                  <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">online</div>
                </div>
              </div>
              <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 mb-2 leading-relaxed">Active devices on network</div>
              <div className="flex items-center">
                <div className="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 sm:h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all duration-500"
                    style={{ width: `${overview.totalDevices > 0 ? (overview.onlineDevices / overview.totalDevices) * 100 : 0}%` }}
                  />
                </div>
                <span className="ml-2 sm:ml-3 text-xs sm:text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                  {overview.totalDevices > 0 ? Math.round((overview.onlineDevices / overview.totalDevices) * 100) : 0}%
                </span>
              </div>
            </div>
          </div>

          {/* Containers Card */}
          <div className="group relative touch-manipulation">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-600/20 to-teal-600/20 rounded-lg sm:rounded-xl blur opacity-75 group-active:opacity-100 transition duration-300"></div>
            <div className="relative bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/30 dark:border-slate-700/30 rounded-lg sm:rounded-xl p-3 sm:p-4 md:p-6 shadow-xl active:shadow-2xl transition-all duration-300 active:-translate-y-1">
              <div className="flex items-start justify-between mb-2 sm:mb-3 md:mb-4">
                <div className="p-2 sm:p-2.5 md:p-3 bg-emerald-500/10 dark:bg-emerald-400/10 rounded-md sm:rounded-lg">
                  <CubeIcon className="h-4 w-4 sm:h-5 sm:w-5 md:h-6 md:w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="text-right min-w-0 flex-1 ml-2 sm:ml-3">
                  <div className="text-lg sm:text-xl md:text-2xl font-bold text-slate-800 dark:text-slate-100 leading-tight">
                    {overview.runningContainers}
                    <span className="text-xs sm:text-sm font-normal text-slate-500">/{overview.totalContainers}</span>
                  </div>
                  <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">running</div>
                </div>
              </div>
              <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 mb-2 leading-relaxed">Active containers</div>
              <div className="flex items-center">
                <div className="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 sm:h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500"
                    style={{ width: `${overview.totalContainers > 0 ? (overview.runningContainers / overview.totalContainers) * 100 : 0}%` }}
                  />
                </div>
                <span className="ml-2 sm:ml-3 text-xs sm:text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                  {overview.totalContainers > 0 ? Math.round((overview.runningContainers / overview.totalContainers) * 100) : 0}%
                </span>
              </div>
            </div>
          </div>

          {/* Storage Card */}
          <div className="group relative touch-manipulation">
            <div className="absolute inset-0 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-lg sm:rounded-xl blur opacity-75 group-active:opacity-100 transition duration-300"></div>
            <div className="relative bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/30 dark:border-slate-700/30 rounded-lg sm:rounded-xl p-3 sm:p-4 md:p-6 shadow-xl active:shadow-2xl transition-all duration-300 active:-translate-y-1">
              <div className="flex items-start justify-between mb-2 sm:mb-3 md:mb-4">
                <div className="p-2 sm:p-2.5 md:p-3 bg-purple-500/10 dark:bg-purple-400/10 rounded-md sm:rounded-lg">
                  <CircleStackIcon className="h-4 w-4 sm:h-5 sm:w-5 md:h-6 md:w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div className="text-right min-w-0 flex-1 ml-2 sm:ml-3">
                  <div className="text-lg sm:text-xl md:text-2xl font-bold text-slate-800 dark:text-slate-100 leading-tight truncate">
                    {overview.usedStorage}
                  </div>
                  <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 truncate">/ {overview.totalStorage}</div>
                </div>
              </div>
              <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 mb-2 leading-relaxed">Storage utilization</div>
              <div className="flex items-center">
                <div className="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 sm:h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500" 
                    style={{ width: `${overview.storageUsagePercent}%` }}
                  />
                </div>
                <span className="ml-2 sm:ml-3 text-xs sm:text-sm text-purple-600 dark:text-purple-400 font-medium">
                  {overview.storageUsagePercent.toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          {/* Health Card */}
          <div className="group relative touch-manipulation sm:col-span-2 lg:col-span-1">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-600/20 to-green-600/20 rounded-lg sm:rounded-xl blur opacity-75 group-active:opacity-100 transition duration-300"></div>
            <div className="relative bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/30 dark:border-slate-700/30 rounded-lg sm:rounded-xl p-3 sm:p-4 md:p-6 shadow-xl active:shadow-2xl transition-all duration-300 active:-translate-y-1">
              <div className="flex items-start justify-between mb-2 sm:mb-3 md:mb-4">
                <div className="p-2 sm:p-2.5 md:p-3 bg-emerald-500/10 dark:bg-emerald-400/10 rounded-md sm:rounded-lg">
                  <div className="h-4 w-4 sm:h-5 sm:w-5 md:h-6 md:w-6 text-emerald-600 dark:text-emerald-400">
                    {getHealthStatusIcon(overview.healthStatus)}
                  </div>
                </div>
                <div className="text-right min-w-0 flex-1 ml-2 sm:ml-3">
                  <div className={`text-lg sm:text-xl md:text-2xl font-bold leading-tight ${getHealthStatusColor(overview.healthStatus)}`}>
                    {overview.healthStatus.charAt(0).toUpperCase() + overview.healthStatus.slice(1)}
                  </div>
                  <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">system health</div>
                </div>
              </div>
              <div className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 mb-2 leading-relaxed">Overall system status</div>
              <div className="flex items-center">
                <div className="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 sm:h-2 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-emerald-500 to-green-500 rounded-full transition-all duration-500" 
                    style={{ 
                      width: `${
                        overview.healthStatus === 'excellent' ? 100 : 
                        overview.healthStatus === 'good' ? 85 :
                        overview.healthStatus === 'warning' ? 60 : 30
                      }%` 
                    }}
                  />
                </div>
                <span className="ml-2 sm:ml-3 text-xs sm:text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                  {overview.healthStatus === 'excellent' ? 100 : 
                   overview.healthStatus === 'good' ? 85 :
                   overview.healthStatus === 'warning' ? 60 : 30}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile-Optimized Performance Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 md:gap-6 mb-4 sm:mb-6 md:mb-8">
          <div className="group relative touch-manipulation">
            <div className="absolute inset-0 bg-gradient-to-r from-orange-600/20 to-red-600/20 rounded-lg sm:rounded-xl blur opacity-75 group-active:opacity-100 transition duration-300"></div>
            <div className="relative bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/30 dark:border-slate-700/30 rounded-lg sm:rounded-xl p-3 sm:p-4 md:p-6 shadow-xl active:shadow-2xl transition-all duration-300 active:-translate-y-1">
              <div className="flex items-center justify-between mb-2 sm:mb-3 md:mb-4">
                <div className="flex items-center space-x-2 sm:space-x-3 min-w-0 flex-1">
                  <div className="p-1.5 sm:p-2 bg-orange-500/10 rounded-md sm:rounded-lg flex-shrink-0">
                    <ClockIcon className="h-4 w-4 sm:h-5 sm:w-5 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-slate-800 dark:text-slate-200 text-sm sm:text-base leading-tight">CPU Usage</h3>
                    <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 truncate">Average across devices</p>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xl sm:text-2xl md:text-3xl font-bold text-slate-800 dark:text-slate-100 leading-none">
                    {overview.avgCpuUsage.toFixed(1)}%
                  </div>
                </div>
              </div>
              <div className="h-1.5 sm:h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-orange-500 to-red-500 rounded-full transition-all duration-700"
                  style={{ width: `${overview.avgCpuUsage}%` }}
                />
              </div>
            </div>
          </div>

          <div className="group relative touch-manipulation">
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-600/20 to-purple-600/20 rounded-lg sm:rounded-xl blur opacity-75 group-active:opacity-100 transition duration-300"></div>
            <div className="relative bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/30 dark:border-slate-700/30 rounded-lg sm:rounded-xl p-3 sm:p-4 md:p-6 shadow-xl active:shadow-2xl transition-all duration-300 active:-translate-y-1">
              <div className="flex items-center justify-between mb-2 sm:mb-3 md:mb-4">
                <div className="flex items-center space-x-2 sm:space-x-3 min-w-0 flex-1">
                  <div className="p-1.5 sm:p-2 bg-indigo-500/10 rounded-md sm:rounded-lg flex-shrink-0">
                    <CircleStackIcon className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-slate-800 dark:text-slate-200 text-sm sm:text-base leading-tight">Memory Usage</h3>
                    <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 truncate">Average across devices</p>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xl sm:text-2xl md:text-3xl font-bold text-slate-800 dark:text-slate-100 leading-none">
                    {overview.avgMemoryUsage.toFixed(1)}%
                  </div>
                </div>
              </div>
              <div className="h-1.5 sm:h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-700"
                  style={{ width: `${overview.avgMemoryUsage}%` }}
                />
              </div>
            </div>
          </div>
        </div>


        {/* Mobile-Optimized Activity Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 md:gap-6">
          {/* Mobile-Optimized Recent Alerts */}
          <div className="group relative touch-manipulation">
            <div className="absolute inset-0 bg-gradient-to-r from-rose-600/10 to-pink-600/10 rounded-lg sm:rounded-xl blur opacity-75"></div>
            <div className="relative bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/30 dark:border-slate-700/30 rounded-lg sm:rounded-xl p-3 sm:p-4 md:p-6 shadow-xl">
              <div className="flex items-center space-x-2 sm:space-x-3 mb-3 sm:mb-4 md:mb-6">
                <div className="p-1.5 sm:p-2 bg-rose-500/10 rounded-md sm:rounded-lg flex-shrink-0">
                  <ExclamationTriangleIcon className="h-4 w-4 sm:h-5 sm:w-5 text-rose-600 dark:text-rose-400" />
                </div>
                <h2 className="text-lg sm:text-xl font-semibold text-slate-800 dark:text-slate-200 leading-tight">Recent Alerts</h2>
              </div>
              
              {recentAlerts.length > 0 ? (
                <div className="space-y-2 sm:space-y-3">
                  {recentAlerts.map((alert, index) => (
                    <div key={index} className="flex items-start space-x-2 sm:space-x-3 p-2 sm:p-3 bg-white/40 dark:bg-slate-700/40 rounded-md sm:rounded-lg border border-white/20 dark:border-slate-600/30 touch-manipulation">
                      <div className={`flex-shrink-0 w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full mt-1.5 sm:mt-2 ${
                        alert.level === 'error' ? 'bg-red-500' : 
                        alert.level === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 truncate leading-relaxed">{alert.title}</p>
                        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 truncate leading-relaxed">{alert.message}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-500 mt-0.5">{alert.timestamp}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 sm:py-6 md:py-8">
                  <div className="p-2 sm:p-3 bg-slate-100 dark:bg-slate-700 rounded-full w-fit mx-auto mb-2 sm:mb-3">
                    <CheckCircleIcon className="h-6 w-6 sm:h-8 sm:w-8 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <p className="text-slate-600 dark:text-slate-300 font-medium text-sm sm:text-base">All systems running smoothly</p>
                  <p className="text-xs sm:text-sm text-slate-500">No recent alerts to display</p>
                </div>
              )}
            </div>
          </div>

          {/* Mobile-Optimized System Status */}
          <div className="group relative touch-manipulation">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-600/10 to-teal-600/10 rounded-lg sm:rounded-xl blur opacity-75"></div>
            <div className="relative bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/30 dark:border-slate-700/30 rounded-lg sm:rounded-xl p-3 sm:p-4 md:p-6 shadow-xl">
              <div className="flex items-center space-x-2 sm:space-x-3 mb-3 sm:mb-4 md:mb-6">
                <div className="p-1.5 sm:p-2 bg-emerald-500/10 rounded-md sm:rounded-lg flex-shrink-0">
                  <HeartIcon className="h-4 w-4 sm:h-5 sm:w-5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h2 className="text-lg sm:text-xl font-semibold text-slate-800 dark:text-slate-200 leading-tight">System Status</h2>
              </div>
              
              <div className="space-y-2 sm:space-y-3 md:space-y-4">
                <div className="flex items-center justify-between p-2 sm:p-3 bg-white/40 dark:bg-slate-700/40 rounded-md sm:rounded-lg border border-white/20 dark:border-slate-600/30 touch-manipulation">
                  <span className="text-slate-700 dark:text-slate-300 font-medium text-xs sm:text-sm leading-relaxed">Infrastructure Monitoring</span>
                  <div className="flex items-center space-x-1 sm:space-x-2 flex-shrink-0">
                    <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                    <span className="text-xs sm:text-sm font-medium text-emerald-600 dark:text-emerald-400">Active</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-2 sm:p-3 bg-white/40 dark:bg-slate-700/40 rounded-md sm:rounded-lg border border-white/20 dark:border-slate-600/30 touch-manipulation">
                  <span className="text-slate-700 dark:text-slate-300 font-medium text-xs sm:text-sm leading-relaxed">Data Collection</span>
                  <div className="flex items-center space-x-1 sm:space-x-2 flex-shrink-0">
                    <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                    <span className="text-xs sm:text-sm font-medium text-emerald-600 dark:text-emerald-400">Running</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-2 sm:p-3 bg-white/40 dark:bg-slate-700/40 rounded-md sm:rounded-lg border border-white/20 dark:border-slate-600/30 touch-manipulation">
                  <span className="text-slate-700 dark:text-slate-300 font-medium text-xs sm:text-sm leading-relaxed">Real-time Streaming</span>
                  <div className="flex items-center space-x-1 sm:space-x-2 flex-shrink-0">
                    <div className={`w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full ${wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div>
                    <span className={`text-xs sm:text-sm font-medium ${wsConnected ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                      {wsConnected ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-2 sm:p-3 bg-white/40 dark:bg-slate-700/40 rounded-md sm:rounded-lg border border-white/20 dark:border-slate-600/30 touch-manipulation">
                  <span className="text-slate-700 dark:text-slate-300 font-medium text-xs sm:text-sm leading-relaxed">Backup Status</span>
                  <div className="flex items-center space-x-1 sm:space-x-2 flex-shrink-0">
                    <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    <span className="text-xs sm:text-sm font-medium text-blue-600 dark:text-blue-400">Scheduled</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}