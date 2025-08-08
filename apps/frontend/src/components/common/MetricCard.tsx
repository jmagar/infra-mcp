import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { TrendingUpIcon, TrendingDownIcon, MinusIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  icon?: React.ReactNode;
  className?: string;
  loading?: boolean;
  description?: string;
}

export function MetricCard({
  title,
  value,
  unit = '',
  change,
  changeType,
  icon,
  className,
  loading = false,
  description,
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (change === undefined || changeType === 'neutral') {
      return <MinusIcon className="h-3 w-3 text-gray-400" />;
    }
    
    if (changeType === 'increase') {
      return <TrendingUpIcon className="h-3 w-3 text-green-600" />;
    }
    
    return <TrendingDownIcon className="h-3 w-3 text-red-600" />;
  };

  const getTrendColor = () => {
    if (change === undefined || changeType === 'neutral') {
      return 'text-gray-500';
    }
    
    return changeType === 'increase' ? 'text-green-600' : 'text-red-600';
  };

  if (loading) {
    return (
      <Card className={cn('', className)}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 className="text-sm font-medium text-gray-600">{title}</h3>
          {icon && <div className="text-gray-400">{icon}</div>}
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="h-8 bg-gray-200 rounded animate-pulse" />
            {change !== undefined && (
              <div className="h-4 bg-gray-100 rounded animate-pulse w-16" />
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('transition-all hover:shadow-md', className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {icon && <div className="text-gray-400">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          <div className="flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-gray-900">
              {value}
            </span>
            {unit && (
              <span className="text-sm text-gray-500">{unit}</span>
            )}
          </div>
          
          {change !== undefined && (
            <div className={cn('flex items-center space-x-1 text-xs', getTrendColor())}>
              {getTrendIcon()}
              <span>
                {Math.abs(change)}%{' '}
                {changeType === 'increase' ? 'increase' : changeType === 'decrease' ? 'decrease' : ''}
              </span>
            </div>
          )}
          
          {description && (
            <p className="text-xs text-gray-500 mt-1">{description}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}