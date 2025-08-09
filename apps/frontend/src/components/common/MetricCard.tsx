import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus,
  AlertTriangle,
  CheckCircle,
  Activity
} from 'lucide-react';
import { cn, componentStyles, semanticColors } from '@/lib/design-system';
import { Card } from '@/components/ui/card';

const metricCardVariants = cva(
  [
    "relative overflow-hidden transition-all duration-300",
  ],
  {
    variants: {
      variant: {
        default: "hover:shadow-md",
        elevated: "shadow-lg hover:shadow-xl",
        gradient: "bg-gradient-to-br from-background to-muted/50",
        outlined: "border-2",
      },
      status: {
        normal: "",
        success: semanticColors.border.success + " " + semanticColors.background.success,
        warning: semanticColors.border.warning + " " + semanticColors.background.warning,
        error: semanticColors.border.error + " " + semanticColors.background.error,
        info: semanticColors.border.info + " " + semanticColors.background.info,
      },
      size: {
        sm: "p-4",
        default: "p-6",
        lg: "p-8",
      }
    },
    defaultVariants: {
      variant: "default",
      status: "normal",
      size: "default",
    },
  }
);

export interface MetricCardProps 
  extends Omit<React.ComponentProps<typeof Card>, 'variant'>,
    VariantProps<typeof metricCardVariants> {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ElementType;
  trend?: {
    value: number;
    label?: string;
    period?: string;
  };
  loading?: boolean;
  error?: boolean;
  unit?: string;
  description?: string;
  actions?: React.ReactNode;
  // Legacy props for backwards compatibility
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  loading = false,
  error = false,
  unit,
  description,
  actions,
  className,
  variant,
  status,
  size,
  // Legacy props
  change,
  changeType,
  ...props
}: MetricCardProps) {
  // Convert legacy props to new format
  const normalizedTrend = trend || (change !== undefined ? {
    value: changeType === 'increase' ? Math.abs(change) : changeType === 'decrease' ? -Math.abs(change) : 0,
    label: changeType === 'increase' ? 'increase' : changeType === 'decrease' ? 'decrease' : ''
  } : undefined);

  // Determine trend direction and icon
  const getTrendIcon = () => {
    if (!normalizedTrend || normalizedTrend.value === 0) return Minus;
    return normalizedTrend.value > 0 ? TrendingUp : TrendingDown;
  };

  const getTrendColor = () => {
    if (!normalizedTrend || normalizedTrend.value === 0) return "text-muted-foreground";
    return normalizedTrend.value > 0 ? semanticColors.status.success : semanticColors.status.error;
  };

  const getStatusIcon = () => {
    if (error) return AlertTriangle;
    if (status === 'success') return CheckCircle;
    if (status === 'warning') return AlertTriangle;
    if (status === 'error') return AlertTriangle;
    if (loading) return Activity;
    return null;
  };

  const StatusIcon = getStatusIcon();
  const TrendIcon = getTrendIcon();

  return (
    <Card
      className={cn(
        metricCardVariants({ variant, status, size }),
        "animate-scale-in",
        className
      )}
      {...props}
    >
      <div className="space-y-3">
        {/* Header with icon and actions */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {Icon && (
              <div className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                status === 'normal' ? "bg-primary/10 text-primary" : "",
                status === 'success' ? "bg-green-100 dark:bg-green-900/20 text-green-600 dark:text-green-400" : "",
                status === 'warning' ? "bg-yellow-100 dark:bg-yellow-900/20 text-yellow-600 dark:text-yellow-400" : "",
                status === 'error' ? "bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400" : "",
                status === 'info' ? "bg-blue-100 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400" : "",
              )}>
                <Icon className="h-5 w-5" />
              </div>
            )}
            <div className="space-y-1">
              <h3 className={componentStyles.typography.body.small + " font-medium uppercase tracking-wider"}>
                {title}
              </h3>
              {StatusIcon && (
                <div className="flex items-center gap-1">
                  <StatusIcon className={cn(
                    "h-4 w-4",
                    status === 'success' && semanticColors.status.success,
                    status === 'warning' && semanticColors.status.warning,
                    status === 'error' && semanticColors.status.error,
                    error && semanticColors.status.error,
                    loading && "animate-pulse " + semanticColors.status.info
                  )} />
                </div>
              )}
            </div>
          </div>
          {actions && (
            <div className="flex items-center gap-2">
              {actions}
            </div>
          )}
        </div>

        {/* Main value */}
        <div className="space-y-1">
          {loading ? (
            <div className="animate-pulse">
              <div className="h-8 bg-muted rounded-md w-24" />
            </div>
          ) : (
            <div className="flex items-baseline gap-2">
              <span className={componentStyles.typography.heading.section + " tabular-nums"}>
                {error ? '—' : value}
              </span>
              {unit && !error && (
                <span className={componentStyles.typography.body.small}>
                  {unit}
                </span>
              )}
            </div>
          )}
          
          {subtitle && (
            <p className={componentStyles.typography.body.small}>
              {subtitle}
            </p>
          )}
        </div>

        {/* Trend indicator */}
        {normalizedTrend && !loading && !error && (
          <div className="flex items-center gap-2">
            <div className={cn(
              "flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors",
              normalizedTrend.value > 0 && "bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-300",
              normalizedTrend.value < 0 && "bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-300",
              normalizedTrend.value === 0 && "bg-gray-100 dark:bg-gray-900/20 text-gray-800 dark:text-gray-300"
            )}>
              <TrendIcon className="h-3 w-3" />
              <span className="tabular-nums">
                {normalizedTrend.value > 0 ? '+' : ''}{normalizedTrend.value}%
              </span>
            </div>
            {normalizedTrend.label && (
              <span className={componentStyles.typography.body.xs}>
                {normalizedTrend.label}
                {normalizedTrend.period && ` ${normalizedTrend.period}`}
              </span>
            )}
          </div>
        )}

        {/* Description */}
        {description && (
          <p className={componentStyles.typography.body.xs}>
            {description}
          </p>
        )}
      </div>

      {/* Decorative accent */}
      {status !== 'normal' && (
        <div className={cn(
          "absolute bottom-0 left-0 h-1 w-full",
          status === 'success' && "bg-green-500",
          status === 'warning' && "bg-yellow-500",
          status === 'error' && "bg-red-500",
          status === 'info' && "bg-blue-500"
        )} />
      )}
    </Card>
  );
}

// Convenience component for percentage metrics
export function PercentageCard({
  value,
  ...props
}: Omit<MetricCardProps, 'value' | 'unit'> & { value: number }) {
  return (
    <MetricCard
      {...props}
      value={value}
      unit="%"
    />
  );
}

// Convenience component for loading states
export function MetricCardSkeleton({ 
  className,
  ...props 
}: Omit<MetricCardProps, 'title' | 'value'>) {
  return (
    <Card className={cn("p-6 space-y-3", className)} {...props}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 bg-muted rounded-lg animate-pulse" />
          <div className="space-y-2">
            <div className="h-4 w-16 bg-muted rounded animate-pulse" />
            <div className="h-3 w-12 bg-muted rounded animate-pulse" />
          </div>
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-8 w-24 bg-muted rounded animate-pulse" />
        <div className="h-4 w-20 bg-muted rounded animate-pulse" />
      </div>
    </Card>
  );
}

// Grid wrapper for multiple metric cards
export function MetricsGrid({ 
  children, 
  className,
  columns = 'auto'
}: { 
  children: React.ReactNode;
  className?: string;
  columns?: 'auto' | 1 | 2 | 3 | 4;
}) {
  return (
    <div className={cn(
      "grid gap-4",
      columns === 'auto' && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
      columns === 1 && "grid-cols-1",
      columns === 2 && "grid-cols-1 sm:grid-cols-2", 
      columns === 3 && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
      columns === 4 && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
      className
    )}>
      {children}
    </div>
  );
}