import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
  DialogClose
} from "./dialog"
import { Button } from "./button"
import { StatusBadge } from "./status-badge"
import { Badge } from "./badge"
import { cn, chartColors } from "@/lib/design-system"
import {
  Container,
  Server,
  Activity,
  Cpu,
  MemoryStick,
  HardDrive,
  Network,
  Calendar,
  Clock,
  User,
  Settings,
  Info,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Play,
  Square,
  RotateCcw,
  Trash2,
  ExternalLink,
  Copy,
  Download,
  MoreVertical
} from "lucide-react"

// Container Detail Modal
export interface ContainerDetailProps {
  container: {
    id: string;
    name: string;
    image: string;
    status: string;
    state: string;
    created: string;
    ports: Array<{ private: number; public?: number; type: string }>;
    environment: Record<string, string>;
    mounts: Array<{ source: string; destination: string; type: string }>;
    networks: string[];
    labels: Record<string, string>;
    stats?: {
      cpu: number;
      memory: number;
      memoryLimit: number;
      networkIn: number;
      networkOut: number;
    };
  };
  onAction?: (action: string, containerId: string) => void;
}

export function ContainerDetailModal({ 
  container, 
  onAction,
  children 
}: ContainerDetailProps & { children: React.ReactNode }) {
  const getStatusVariant = (status: string) => {
    if (status.includes('Up') || status === 'running') return 'running';
    if (status.includes('Exited')) return 'stopped';
    if (status === 'created') return 'pending';
    return 'unknown';
  };

  const handleAction = (action: string) => {
    if (onAction) {
      onAction(action, container.id);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent size="xl" className="max-h-[90vh] overflow-hidden">
        <DialogHeader showDivider>
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <DialogTitle className="flex items-center gap-2">
                <Container className="h-5 w-5 text-blue-500" />
                {container.name}
              </DialogTitle>
              <DialogDescription className="flex items-center gap-2">
                <StatusBadge 
                  status={getStatusVariant(container.status)} 
                  size="sm"
                  pulse={getStatusVariant(container.status) === 'running'}
                >
                  {container.status}
                </StatusBadge>
                <span>•</span>
                <span className="text-xs font-mono text-muted-foreground">
                  {container.image}
                </span>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-6 pr-2">
          {/* Quick Actions */}
          <div className="flex flex-wrap gap-2">
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => handleAction('start')}
              className="gap-2"
              disabled={getStatusVariant(container.status) === 'running'}
            >
              <Play className="h-3 w-3" />
              Start
            </Button>
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => handleAction('stop')}
              className="gap-2"
              disabled={getStatusVariant(container.status) === 'stopped'}
            >
              <Square className="h-3 w-3" />
              Stop
            </Button>
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => handleAction('restart')}
              className="gap-2"
            >
              <RotateCcw className="h-3 w-3" />
              Restart
            </Button>
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => handleAction('logs')}
              className="gap-2"
            >
              <Activity className="h-3 w-3" />
              Logs
            </Button>
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => copyToClipboard(container.id)}
              className="gap-2"
            >
              <Copy className="h-3 w-3" />
              Copy ID
            </Button>
          </div>

          {/* Resource Usage */}
          {container.stats && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">Resource Usage</h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="glass rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-blue-500" />
                    <span className="text-xs font-medium">CPU</span>
                  </div>
                  <div className="text-lg font-mono tabular-nums">{container.stats.cpu.toFixed(1)}%</div>
                </div>
                <div className="glass rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <MemoryStick className="h-4 w-4 text-green-500" />
                    <span className="text-xs font-medium">Memory</span>
                  </div>
                  <div className="text-lg font-mono tabular-nums">
                    {(container.stats.memory / 1024 / 1024).toFixed(0)}MB
                  </div>
                  <div className="text-xs text-muted-foreground">
                    / {(container.stats.memoryLimit / 1024 / 1024).toFixed(0)}MB
                  </div>
                </div>
                <div className="glass rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Network className="h-4 w-4 text-purple-500" />
                    <span className="text-xs font-medium">Network In</span>
                  </div>
                  <div className="text-lg font-mono tabular-nums">
                    {(container.stats.networkIn / 1024).toFixed(1)}KB
                  </div>
                </div>
                <div className="glass rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Network className="h-4 w-4 text-orange-500" />
                    <span className="text-xs font-medium">Network Out</span>
                  </div>
                  <div className="text-lg font-mono tabular-nums">
                    {(container.stats.networkOut / 1024).toFixed(1)}KB
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Container Info */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-foreground">Container Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">ID:</span>
                  <span className="font-mono text-xs">{container.id.substring(0, 12)}...</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Image:</span>
                  <span className="font-mono text-xs break-all">{container.image}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">State:</span>
                  <span className="font-medium">{container.state}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created:</span>
                  <span>{new Date(container.created).toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Port Mappings */}
          {container.ports.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">Port Mappings</h3>
              <div className="space-y-2">
                {container.ports.map((port, index) => (
                  <div key={index} className="glass rounded-lg p-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {port.type.toUpperCase()}
                      </Badge>
                      <span className="font-mono text-sm">
                        {port.public ? `${port.public}:${port.private}` : port.private}
                      </span>
                    </div>
                    {port.public && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => window.open(`http://localhost:${port.public}`, '_blank')}
                        className="gap-1"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Open
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Environment Variables */}
          {Object.keys(container.environment).length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">Environment Variables</h3>
              <div className="glass rounded-lg max-h-48 overflow-y-auto">
                {Object.entries(container.environment).map(([key, value]) => (
                  <div key={key} className="p-3 border-b border-border/30 last:border-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-sm text-foreground">{key}</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => copyToClipboard(`${key}=${value}`)}
                        className="shrink-0"
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className="text-xs text-muted-foreground font-mono break-all mt-1">
                      {value || '<empty>'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Mounts */}
          {container.mounts.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">Volume Mounts</h3>
              <div className="space-y-2">
                {container.mounts.map((mount, index) => (
                  <div key={index} className="glass rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary" className="text-xs">
                        {mount.type}
                      </Badge>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => copyToClipboard(`${mount.source}:${mount.destination}`)}
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Host:</span>
                        <span className="font-mono text-xs">{mount.source}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Container:</span>
                        <span className="font-mono text-xs">{mount.destination}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Networks */}
          {container.networks.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">Networks</h3>
              <div className="flex flex-wrap gap-2">
                {container.networks.map((network) => (
                  <Badge key={network} variant="outline" className="text-xs">
                    {network}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Labels */}
          {Object.keys(container.labels).length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">Labels</h3>
              <div className="glass rounded-lg max-h-32 overflow-y-auto">
                {Object.entries(container.labels).map(([key, value]) => (
                  <div key={key} className="p-2 border-b border-border/30 last:border-0 text-xs">
                    <div className="font-mono text-foreground">{key}</div>
                    <div className="text-muted-foreground break-all">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter showDivider className="gap-2">
          <DialogClose asChild>
            <Button variant="outline">Close</Button>
          </DialogClose>
          <Button 
            onClick={() => handleAction('remove')}
            variant="destructive"
            className="gap-2"
          >
            <Trash2 className="h-4 w-4" />
            Remove Container
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Device Detail Modal
export interface DeviceDetailProps {
  device: {
    id: string;
    hostname: string;
    ip_address: string;
    status: 'online' | 'offline' | 'warning';
    device_type: string;
    location?: string;
    description?: string;
    tags?: Record<string, string>;
    metrics?: {
      cpu: number;
      memory: number;
      disk: number;
      uptime: string;
      load_average: [number, number, number];
    };
    containers?: number;
    services?: number;
    last_seen: string;
  };
  onAction?: (action: string, deviceId: string) => void;
}

export function DeviceDetailModal({ 
  device, 
  onAction,
  children 
}: DeviceDetailProps & { children: React.ReactNode }) {
  const handleAction = (action: string) => {
    if (onAction) {
      onAction(action, device.id);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent size="lg" className="max-h-[90vh] overflow-hidden">
        <DialogHeader showDivider>
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <DialogTitle className="flex items-center gap-2">
                <Server className="h-5 w-5 text-primary" />
                {device.hostname}
              </DialogTitle>
              <DialogDescription className="flex items-center gap-3">
                <StatusBadge 
                  status={device.status} 
                  size="sm"
                  pulse={device.status === 'online'}
                >
                  {device.status.charAt(0).toUpperCase() + device.status.slice(1)}
                </StatusBadge>
                <span>•</span>
                <span className="text-xs font-mono">{device.ip_address}</span>
                <span>•</span>
                <Badge variant="outline" className="text-xs">
                  {device.device_type}
                </Badge>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-6 pr-2">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Container className="h-4 w-4 text-blue-500" />
                <span className="text-xs font-medium">Containers</span>
              </div>
              <div className="text-lg font-mono tabular-nums">{device.containers || 0}</div>
            </div>
            <div className="glass rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4 text-green-500" />
                <span className="text-xs font-medium">Services</span>
              </div>
              <div className="text-lg font-mono tabular-nums">{device.services || 0}</div>
            </div>
            <div className="glass rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-purple-500" />
                <span className="text-xs font-medium">Last Seen</span>
              </div>
              <div className="text-xs text-muted-foreground">
                {new Date(device.last_seen).toLocaleString()}
              </div>
            </div>
            <div className="glass rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-orange-500" />
                <span className="text-xs font-medium">Uptime</span>
              </div>
              <div className="text-xs font-mono">
                {device.metrics?.uptime || 'Unknown'}
              </div>
            </div>
          </div>

          {/* System Metrics */}
          {device.metrics && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">System Metrics</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glass rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-blue-500" />
                      <span className="text-sm font-medium">CPU</span>
                    </div>
                    <span className="text-lg font-mono tabular-nums">{device.metrics.cpu}%</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${device.metrics.cpu}%` }}
                    />
                  </div>
                </div>
                <div className="glass rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MemoryStick className="h-4 w-4 text-green-500" />
                      <span className="text-sm font-medium">Memory</span>
                    </div>
                    <span className="text-lg font-mono tabular-nums">{device.metrics.memory}%</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div 
                      className="bg-green-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${device.metrics.memory}%` }}
                    />
                  </div>
                </div>
                <div className="glass rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <HardDrive className="h-4 w-4 text-purple-500" />
                      <span className="text-sm font-medium">Disk</span>
                    </div>
                    <span className="text-lg font-mono tabular-nums">{device.metrics.disk}%</span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div 
                      className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${device.metrics.disk}%` }}
                    />
                  </div>
                </div>
              </div>
              
              {/* Load Average */}
              <div className="glass rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="h-4 w-4 text-orange-500" />
                  <span className="text-sm font-medium">Load Average</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <div className="space-y-1">
                    <div className="text-muted-foreground">1 min</div>
                    <div className="font-mono tabular-nums">{device.metrics.load_average[0].toFixed(2)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-muted-foreground">5 min</div>
                    <div className="font-mono tabular-nums">{device.metrics.load_average[1].toFixed(2)}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-muted-foreground">15 min</div>
                    <div className="font-mono tabular-nums">{device.metrics.load_average[2].toFixed(2)}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Device Information */}
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-foreground">Device Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Hostname:</span>
                  <span className="font-mono">{device.hostname}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">IP Address:</span>
                  <span className="font-mono">{device.ip_address}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Type:</span>
                  <Badge variant="outline">{device.device_type}</Badge>
                </div>
                {device.location && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Location:</span>
                    <span>{device.location}</span>
                  </div>
                )}
              </div>
            </div>
            {device.description && (
              <div className="glass rounded-lg p-3">
                <div className="text-sm font-medium mb-1">Description</div>
                <div className="text-sm text-muted-foreground">{device.description}</div>
              </div>
            )}
          </div>

          {/* Tags */}
          {device.tags && Object.keys(device.tags).length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(device.tags).map(([key, value]) => (
                  <Badge key={key} variant="outline" className="text-xs">
                    {key}: {value}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter showDivider>
          <DialogClose asChild>
            <Button variant="outline">Close</Button>
          </DialogClose>
          <Button onClick={() => handleAction('manage')}>
            Manage Device
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}