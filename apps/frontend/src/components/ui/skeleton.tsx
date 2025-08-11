import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/design-system';

const skeletonVariants = cva(
  [
    "animate-pulse bg-gradient-to-r from-muted via-muted/50 to-muted",
    "bg-[length:200%_100%] animate-shimmer rounded-md",
    "relative overflow-hidden"
  ],
  {
    variants: {
      variant: {
        default: "bg-muted",
        shimmer: [
          "bg-gradient-to-r from-muted via-background to-muted",
          "bg-[length:200%_100%] animate-shimmer",
          "before:absolute before:inset-0",
          "before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent",
          "before:translate-x-[-100%] before:animate-shimmer-wave"
        ],
        wave: [
          "bg-muted",
          "relative overflow-hidden",
          "before:absolute before:inset-0",
          "before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent",
          "before:-translate-x-full before:animate-wave"
        ],
        pulse: "animate-pulse bg-muted/80"
      },
      size: {
        xs: "h-3",
        sm: "h-4", 
        default: "h-5",
        lg: "h-6",
        xl: "h-8"
      },
      rounded: {
        none: "rounded-none",
        sm: "rounded-sm",
        default: "rounded-md",
        lg: "rounded-lg",
        xl: "rounded-xl",
        full: "rounded-full"
      }
    },
    defaultVariants: {
      variant: "shimmer",
      size: "default",
      rounded: "default"
    }
  }
);

export interface SkeletonProps 
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonVariants> {
  width?: string | number;
  height?: string | number;
}

export function Skeleton({
  className,
  variant,
  size,
  rounded,
  width,
  height,
  style,
  ...props
}: SkeletonProps) {
  return (
    <div
      className={cn(skeletonVariants({ variant, size, rounded }), className)}
      style={{
        width,
        height,
        ...style
      }}
      {...props}
    />
  );
}

// Pre-built skeleton variants for common UI patterns
export function MetricCardSkeleton({ 
  className,
  showSparkline = false,
  ...props 
}: { 
  className?: string;
  showSparkline?: boolean;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("p-6 space-y-4 glass", className)} {...props}>
      {/* Header with icon and title */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Skeleton variant="shimmer" rounded="lg" width={40} height={40} />
          <div className="space-y-2">
            <Skeleton variant="shimmer" size="sm" width={80} />
            <Skeleton variant="shimmer" size="xs" width={60} />
          </div>
        </div>
      </div>
      
      {/* Main value and sparkline */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton variant="shimmer" size="xl" width={120} />
          <Skeleton variant="shimmer" size="xs" width={90} />
        </div>
        {showSparkline && (
          <Skeleton variant="wave" rounded="sm" width={64} height={24} />
        )}
      </div>
      
      {/* Trend indicator */}
      <div className="flex items-center gap-2">
        <Skeleton variant="shimmer" rounded="full" width={80} height={24} />
        <Skeleton variant="shimmer" size="xs" width={60} />
      </div>
    </div>
  );
}

export function TextSkeleton({ 
  lines = 3,
  className,
  ...props
}: { 
  lines?: number;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("space-y-2", className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton 
          key={i}
          variant="shimmer" 
          size="default"
          width={i === lines - 1 ? "75%" : "100%"}
        />
      ))}
    </div>
  );
}

export function AvatarSkeleton({ 
  size = 40,
  className,
  ...props 
}: { 
  size?: number;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <Skeleton
      variant="shimmer"
      rounded="full"
      width={size}
      height={size}
      className={className}
      {...props}
    />
  );
}

export function TableSkeleton({ 
  rows = 5,
  columns = 4,
  className,
  ...props
}: { 
  rows?: number;
  columns?: number;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("space-y-3", className)} {...props}>
      {/* Header */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} variant="shimmer" size="sm" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div 
          key={rowIndex} 
          className="grid gap-4" 
          style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton 
              key={colIndex} 
              variant="wave" 
              size="default"
              style={{ animationDelay: `${(rowIndex * columns + colIndex) * 50}ms` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ 
  className,
  ...props 
}: { 
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("space-y-4", className)} {...props}>
      {/* Chart title */}
      <div className="flex items-center justify-between">
        <Skeleton variant="shimmer" size="lg" width={160} />
        <Skeleton variant="shimmer" size="sm" width={80} />
      </div>
      
      {/* Chart area */}
      <div className="relative h-64 flex items-end justify-between gap-2 px-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton
            key={i}
            variant="wave"
            width={20}
            height={Math.random() * 180 + 40}
            rounded="sm"
            style={{ animationDelay: `${i * 100}ms` }}
          />
        ))}
      </div>
      
      {/* Chart legend */}
      <div className="flex items-center justify-center gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <Skeleton variant="shimmer" rounded="full" width={12} height={12} />
            <Skeleton variant="shimmer" size="xs" width={60} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function CardSkeleton({ 
  children,
  className,
  ...props 
}: { 
  children?: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("p-6 glass space-y-4", className)} {...props}>
      {/* Card header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Skeleton variant="shimmer" rounded="lg" width={32} height={32} />
          <div className="space-y-2">
            <Skeleton variant="shimmer" size="lg" width={140} />
            <Skeleton variant="shimmer" size="xs" width={100} />
          </div>
        </div>
        <Skeleton variant="shimmer" rounded="md" width={24} height={24} />
      </div>
      
      {/* Card content */}
      {children || (
        <div className="space-y-3">
          <TextSkeleton lines={2} />
          <div className="flex items-center gap-4">
            <Skeleton variant="shimmer" rounded="md" width={60} height={20} />
            <Skeleton variant="shimmer" rounded="md" width={80} height={20} />
          </div>
        </div>
      )}
    </div>
  );
}

// Loading state wrapper component
export function LoadingState({ 
  children,
  loading,
  skeleton,
  className,
  ...props
}: {
  children: React.ReactNode;
  loading: boolean;
  skeleton: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("relative", className)} {...props}>
      {loading ? (
        <div className="animate-fade-in">
          {skeleton}
        </div>
      ) : (
        <div className="animate-fade-in">
          {children}
        </div>
      )}
    </div>
  );
}

// Staggered skeleton animation wrapper
export function SkeletonGroup({ 
  children,
  stagger = 100,
  className,
  ...props
}: {
  children: React.ReactNode;
  stagger?: number;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("space-y-4", className)} {...props}>
      {React.Children.map(children, (child, index) => (
        <div 
          key={index}
          style={{ animationDelay: `${index * stagger}ms` }}
          className="animate-fade-in-up"
        >
          {child}
        </div>
      ))}
    </div>
  );
}