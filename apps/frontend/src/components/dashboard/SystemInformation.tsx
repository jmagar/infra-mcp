import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Info, Server, Cpu, HardDrive, Clock, Package } from 'lucide-react';
import { useEffect, useState } from 'react';
import { deviceApi, containerApi } from '@/services/api';

interface SystemInformationProps {
  deviceHostname?: string;
}

interface SystemInfo {
  hostname: string;
  device_type: string;
  status: string;
  last_seen: string | null;
  containers?: {
    running: number;
    total: number;
  };
  uptime?: string;
}

export function SystemInformation({ deviceHostname = 'tootie' }: SystemInformationProps) {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSystemInfo = async () => {
      try {
        // Get basic device info
        const deviceResponse = await deviceApi.get(deviceHostname);
        
        if (deviceResponse.success && deviceResponse.data) {
          const deviceData = deviceResponse.data;
          
          // Try to get container information
          let containerData = null;
          try {
            const containersResponse = await containerApi.list(deviceHostname);
            if (containersResponse.success && containersResponse.data?.containers) {
              const containers = containersResponse.data.containers;
              containerData = {
                total: containers.length,
                running: containers.filter((c: any) => c.state === 'running').length,
              };
            }
          } catch (containerError) {
            console.warn('Could not fetch container data:', containerError);
          }
          
          setSystemInfo({
            hostname: deviceData.hostname,
            device_type: deviceData.device_type,
            status: deviceData.status,
            last_seen: deviceData.last_seen,
            containers: containerData,
          });
        }
      } catch (error) {
        console.error('Failed to fetch system information:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSystemInfo();
  }, [deviceHostname]);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 GB';
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(2)} GB`;
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return `${days}d ${hours}h`;
  };

  const formatLastSeen = (lastSeen: string | null): string => {
    if (!lastSeen) return 'Never';
    const date = new Date(lastSeen);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  if (loading) {
    return (
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-gray-100">
            <Info className="h-4 w-4" />
            System Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-800 rounded w-3/4"></div>
            <div className="h-4 bg-gray-800 rounded w-1/2"></div>
            <div className="h-4 bg-gray-800 rounded w-2/3"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-gray-100">
          <Info className="h-4 w-4" />
          System Information
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 text-sm">
          {/* Hostname */}
          <div className="flex items-start gap-3">
            <Server className="h-4 w-4 text-gray-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-gray-400">Hostname</div>
              <div className="text-gray-200 font-medium">{systemInfo?.hostname || 'Unknown'}</div>
            </div>
          </div>

          {/* Device Type */}
          <div className="flex items-start gap-3">
            <Package className="h-4 w-4 text-gray-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-gray-400">Device Type</div>
              <div className="text-gray-200 font-medium">
                {systemInfo?.device_type || 'Unknown'}
              </div>
            </div>
          </div>

          {/* Status */}
          <div className="flex items-start gap-3">
            <Server className="h-4 w-4 text-gray-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-gray-400">Status</div>
              <div className={`font-medium ${
                systemInfo?.status === 'online' 
                  ? 'text-green-400' 
                  : systemInfo?.status === 'offline' 
                    ? 'text-red-400' 
                    : 'text-yellow-400'
              }`}>
                {systemInfo?.status || 'Unknown'}
              </div>
            </div>
          </div>

          {/* Containers */}
          {systemInfo?.containers && (
            <div className="flex items-start gap-3">
              <Package className="h-4 w-4 text-gray-400 mt-0.5" />
              <div className="flex-1">
                <div className="text-gray-400">Containers</div>
                <div className="text-gray-200 font-medium">
                  {systemInfo.containers.running} running / {systemInfo.containers.total} total
                </div>
              </div>
            </div>
          )}

          {/* Last Seen */}
          <div className="flex items-start gap-3">
            <Clock className="h-4 w-4 text-gray-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-gray-400">Last Seen</div>
              <div className="text-gray-200 font-medium">
                {formatLastSeen(systemInfo?.last_seen)}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}