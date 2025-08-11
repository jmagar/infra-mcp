import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn, glassStyles, typography, spacing, statusColors, animations } from "@/lib/modern-design-system"

// Modern Card Variants
const cardVariants = cva([
  "relative overflow-hidden",
  "transition-all duration-300 ease-out",
], {
  variants: {
    variant: {
      default: glassStyles.card,
      elevated: glassStyles.elevated,
      interactive: glassStyles.interactive,
      subtle: glassStyles.subtle,
    },
    size: {
      sm: [spacing.container.sm, "min-h-[120px]"].join(" "),
      md: [spacing.container.md, "min-h-[160px]"].join(" "),
      lg: [spacing.container.lg, "min-h-[200px]"].join(" "),
      xl: [spacing.container.xl, "min-h-[240px]"].join(" "),
      auto: spacing.container.md,
    },
    animation: {
      none: "",
      fade: animations.fadeIn,
      slide: animations.slideInFromBottom,
      scale: animations.scaleIn,
    }
  },
  defaultVariants: {
    variant: "default",
    size: "md",
    animation: "fade",
  }
})

export interface ModernCardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  gradient?: keyof typeof statusColors | string;
  loading?: boolean;
}

const ModernCard = React.forwardRef<HTMLDivElement, ModernCardProps>(
  ({ className, variant, size, animation, gradient, loading, children, ...props }, ref) => {
    const gradientClass = gradient && gradient in statusColors 
      ? statusColors[gradient as keyof typeof statusColors].gradient
      : gradient || "";

    return (
      <div
        ref={ref}
        className={cn(
          cardVariants({ variant, size, animation }),
          gradientClass && `${gradientClass}`,
          loading && animations.shimmer,
          className
        )}
        {...props}
      >
        {children}
        {loading && (
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
        )}
      </div>
    )
  }
)
ModernCard.displayName = "ModernCard"

// Modern Card Header
const ModernCardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    title?: React.ReactNode;
    description?: React.ReactNode;
    actions?: React.ReactNode;
    status?: keyof typeof statusColors;
  }
>(({ className, title, description, actions, status, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("flex items-start justify-between", spacing.stack.sm, className)}
      {...props}
    >
      <div className={cn("flex-1 min-w-0", spacing.stack.xs)}>
        {title && (
          <h3 className={cn(
            typography.heading.md,
            "flex items-center gap-3 text-white dark:text-gray-100"
          )}>
            {status && (
              <div className={cn(
                "w-2 h-2 rounded-full flex-shrink-0",
                statusColors[status].indicator,
                status === 'online' && "animate-pulse"
              )} />
            )}
            <span className="truncate">{title}</span>
          </h3>
        )}
        {description && (
          <p className={cn(typography.caption.md, "truncate text-gray-300 dark:text-gray-300")}>
            {description}
          </p>
        )}
        {children}
      </div>
      {actions && (
        <div className="flex items-center gap-2 flex-shrink-0 ml-4">
          {actions}
        </div>
      )}
    </div>
  )
})
ModernCardHeader.displayName = "ModernCardHeader"

// Modern Card Content
const ModernCardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn("flex-1", spacing.stack.md, className)}
      {...props}
    >
      {children}
    </div>
  )
})
ModernCardContent.displayName = "ModernCardContent"

// Modern Card Footer  
const ModernCardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={cn(
        "flex items-center justify-between pt-4 mt-4 border-t border-white/10",
        spacing.inline.sm,
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
})
ModernCardFooter.displayName = "ModernCardFooter"

// Metric Display Component
export interface MetricProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  size?: "sm" | "md" | "lg";
  status?: keyof typeof statusColors;
}

const Metric = React.forwardRef<HTMLDivElement, MetricProps & React.HTMLAttributes<HTMLDivElement>>(
  ({ label, value, unit, trend, trendValue, size = "md", status, className, ...props }, ref) => {
    const sizeStyles = {
      sm: {
        value: typography.heading.sm,
        label: typography.caption.sm,
        trend: "text-xs",
      },
      md: {
        value: typography.heading.lg,
        label: typography.caption.md,
        trend: "text-sm",
      },
      lg: {
        value: typography.display.sm,
        label: typography.caption.lg,  
        trend: "text-base",
      },
    }

    const trendColors = {
      up: "text-green-500 dark:text-green-400",
      down: "text-red-500 dark:text-red-400", 
      neutral: "text-gray-500 dark:text-gray-400",
    }

    return (
      <div
        ref={ref}
        className={cn("flex flex-col group", spacing.stack.xs, className)}
        {...props}
      >
        <div className="flex items-baseline gap-2">
          <span className={cn(
            sizeStyles[size].value,
            "font-mono tabular-nums transition-colors duration-200",
            status && statusColors[status].text,
            !status && "text-white dark:text-gray-100",
            "group-hover:scale-105 transition-transform duration-200 inline-block"
          )}>
            {value}
          </span>
          {unit && (
            <span className={cn(typography.caption.md, "text-gray-400 dark:text-gray-400 transition-colors duration-200")}>
              {unit}
            </span>
          )}
          {trend && trendValue && (
            <span className={cn(
              sizeStyles[size].trend,
              "font-medium transition-all duration-200",
              trendColors[trend],
              "group-hover:scale-110 inline-block"
            )}>
              <span className={cn("inline-block transition-transform duration-200", 
                trend === "up" && "group-hover:rotate-12",
                trend === "down" && "group-hover:-rotate-12"
              )}>
                {trend === "up" ? "↗" : trend === "down" ? "↘" : "→"}
              </span> {trendValue}
            </span>
          )}
        </div>
        <p className={cn(sizeStyles[size].label, "truncate transition-colors duration-200 text-gray-300 dark:text-gray-300")}>
          {label}
        </p>
      </div>
    )
  }
)
Metric.displayName = "Metric"

// Progress Bar Component
export interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  status?: keyof typeof statusColors;
  size?: "sm" | "md" | "lg";
}

const ProgressBar = React.forwardRef<HTMLDivElement, ProgressBarProps & React.HTMLAttributes<HTMLDivElement>>(
  ({ value, max = 100, label, showValue = true, status, size = "md", className, ...props }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    
    const sizeStyles = {
      sm: "h-1.5",
      md: "h-2", 
      lg: "h-3",
    }

    // Auto-determine status based on value
    const autoStatus = status || (
      percentage >= 90 ? "warning" :
      percentage >= 70 ? "running" : 
      "online"
    );

    return (
      <div
        ref={ref}
        className={cn("w-full", spacing.stack.xs, className)}
        {...props}
      >
        {(label || showValue) && (
          <div className="flex items-center justify-between">
            {label && (
              <span className={cn(typography.caption.md, "text-gray-300 dark:text-gray-300")}>
                {label}
              </span>
            )}
            {showValue && (
              <span className={cn(
                typography.caption.md,
                "font-mono tabular-nums",
                statusColors[autoStatus].text
              )}>
                {percentage.toFixed(1)}%
              </span>
            )}
          </div>
        )}
        <div className={cn(
          "relative overflow-hidden rounded-full bg-slate-700/60 dark:bg-slate-800/80 border border-slate-600/20 dark:border-slate-600/25",
          sizeStyles[size]
        )}>
          <div
            className={cn(
              "h-full rounded-full transition-all duration-1000 ease-out",
              statusColors[autoStatus].indicator
            )}
            style={{ width: `${percentage}%` }}
          />
          {/* Shine effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -skew-x-12 animate-shimmer" />
        </div>
      </div>
    )
  }
)
ProgressBar.displayName = "ProgressBar"

// Status Indicator Component
export interface StatusIndicatorProps {
  status: keyof typeof statusColors;
  label?: string;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
}

const StatusIndicator = React.forwardRef<HTMLDivElement, StatusIndicatorProps & React.HTMLAttributes<HTMLDivElement>>(
  ({ status, label, size = "md", pulse, className, ...props }, ref) => {
    const sizeStyles = {
      sm: { dot: "w-2 h-2", text: typography.caption.sm },
      md: { dot: "w-3 h-3", text: typography.caption.md },
      lg: { dot: "w-4 h-4", text: typography.body.sm },
    }

    return (
      <div
        ref={ref}
        className={cn("flex items-center gap-2", className)}
        {...props}
      >
        <div className={cn(
          "rounded-full flex-shrink-0",
          sizeStyles[size].dot,
          statusColors[status].indicator,
          pulse && "animate-pulse"
        )} />
        {label && (
          <span className={cn(
            sizeStyles[size].text,
            statusColors[status].text,
            "font-medium truncate"
          )}>
            {label}
          </span>
        )}
      </div>
    )
  }
)
StatusIndicator.displayName = "StatusIndicator"

export {
  ModernCard,
  ModernCardHeader,
  ModernCardContent, 
  ModernCardFooter,
  Metric,
  ProgressBar,
  StatusIndicator,
}