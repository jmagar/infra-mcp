import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { DeviceStatus, HealthStatus } from '@infrastructor/shared-types';

interface StatusBadgeProps {
  status: DeviceStatus | HealthStatus | string;
  className?: string;
}

const statusConfig = {
  // Device statuses
  online: { color: 'bg-green-100 text-green-800 border-green-200', icon: '●' },
  offline: { color: 'bg-red-100 text-red-800 border-red-200', icon: '●' },
  unknown: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: '●' },
  
  // Health statuses
  healthy: { color: 'bg-green-100 text-green-800 border-green-200', icon: '✓' },
  warning: { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: '⚠' },
  error: { color: 'bg-red-100 text-red-800 border-red-200', icon: '✗' },
  critical: { color: 'bg-red-100 text-red-800 border-red-200', icon: '⚠' },
  
  // Container statuses
  running: { color: 'bg-green-100 text-green-800 border-green-200', icon: '▶' },
  stopped: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: '⏸' },
  paused: { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: '⏸' },
  restarting: { color: 'bg-blue-100 text-blue-800 border-blue-200', icon: '↻' },
  exited: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: '⏹' },
  dead: { color: 'bg-red-100 text-red-800 border-red-200', icon: '✗' },
  
  // Generic statuses
  active: { color: 'bg-green-100 text-green-800 border-green-200', icon: '●' },
  inactive: { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: '●' },
  pending: { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: '◐' },
  loading: { color: 'bg-blue-100 text-blue-800 border-blue-200', icon: '◐' },
} as const;

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const normalizedStatus = status.toLowerCase() as keyof typeof statusConfig;
  const config = statusConfig[normalizedStatus] || statusConfig.unknown;
  
  return (
    <Badge
      variant="outline"
      className={cn(
        config.color,
        'font-medium text-xs px-2 py-1 flex items-center gap-1 w-fit',
        className
      )}
    >
      <span className="text-xs">{config.icon}</span>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}