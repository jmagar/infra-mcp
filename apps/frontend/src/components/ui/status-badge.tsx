import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/design-system"

const statusBadgeVariants = cva([
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-all duration-200",
  "border shadow-sm",
  "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
], {
  variants: {
    status: {
      online: [
        "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300",
        "border-green-200 dark:border-green-800",
        "hover:bg-green-100 dark:hover:bg-green-900/30"
      ],
      offline: [
        "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300",
        "border-red-200 dark:border-red-800",
        "hover:bg-red-100 dark:hover:bg-red-900/30"
      ],
      warning: [
        "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300",
        "border-yellow-200 dark:border-yellow-800",
        "hover:bg-yellow-100 dark:hover:bg-yellow-900/30"
      ],
      running: [
        "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300",
        "border-blue-200 dark:border-blue-800",
        "hover:bg-blue-100 dark:hover:bg-blue-900/30"
      ],
      stopped: [
        "bg-gray-50 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300",
        "border-gray-200 dark:border-gray-800",
        "hover:bg-gray-100 dark:hover:bg-gray-900/30"
      ],
      pending: [
        "bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300",
        "border-orange-200 dark:border-orange-800",
        "hover:bg-orange-100 dark:hover:bg-orange-900/30"
      ],
      healthy: [
        "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300",
        "border-emerald-200 dark:border-emerald-800",
        "hover:bg-emerald-100 dark:hover:bg-emerald-900/30"
      ],
      unhealthy: [
        "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300",
        "border-red-200 dark:border-red-800",
        "hover:bg-red-100 dark:hover:bg-red-900/30"
      ],
      unknown: [
        "bg-slate-50 dark:bg-slate-900/20 text-slate-700 dark:text-slate-300",
        "border-slate-200 dark:border-slate-800",
        "hover:bg-slate-100 dark:hover:bg-slate-900/30"
      ]
    },
    size: {
      sm: "text-xs px-2 py-0.5",
      md: "text-sm px-2.5 py-1",
      lg: "text-sm px-3 py-1.5"
    },
    variant: {
      solid: "",
      outline: "bg-transparent border-2",
      soft: "border-transparent"
    }
  },
  defaultVariants: {
    status: "unknown",
    size: "sm",
    variant: "solid"
  }
})

export interface StatusBadgeProps 
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof statusBadgeVariants> {
  showIndicator?: boolean;
  pulse?: boolean;
}

const StatusBadge = React.forwardRef<HTMLDivElement, StatusBadgeProps>(
  ({ className, status, size, variant, showIndicator = true, pulse = false, children, ...props }, ref) => {
    const getIndicatorColor = (status: string | null | undefined) => {
      switch (status) {
        case 'online':
        case 'running':
        case 'healthy':
          return "bg-green-500";
        case 'offline':
        case 'unhealthy':
          return "bg-red-500";
        case 'warning':
          return "bg-yellow-500";
        case 'pending':
          return "bg-orange-500";
        case 'stopped':
          return "bg-gray-500";
        default:
          return "bg-slate-500";
      }
    };

    return (
      <div
        ref={ref}
        className={cn(statusBadgeVariants({ status, size, variant }), className)}
        {...props}
      >
        {showIndicator && (
          <div 
            className={cn(
              "h-2 w-2 rounded-full flex-shrink-0",
              getIndicatorColor(status),
              pulse && "animate-pulse"
            )}
          />
        )}
        <span className="truncate">{children}</span>
      </div>
    )
  }
)
StatusBadge.displayName = "StatusBadge"

export { StatusBadge, statusBadgeVariants }