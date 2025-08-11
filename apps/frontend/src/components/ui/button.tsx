import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/modern-design-system"
import { useRipple } from "@/hooks/useRipple"

const buttonVariants = cva(
  [
    "relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium",
    "transition-all duration-200 ease-in-out disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
    "outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
    "active:scale-[0.98] active:brightness-90",
    "overflow-hidden select-none",
    "before:absolute before:inset-0 before:bg-gradient-to-r before:from-white/0 before:via-white/10 before:to-white/0",
    "before:translate-x-[-100%] before:transition-transform before:duration-700 before:ease-out",
    "hover:before:translate-x-[100%]",
    "after:absolute after:inset-0 after:bg-current after:opacity-0 after:transition-opacity after:duration-150",
    "active:after:opacity-[0.08]"
  ],
  {
    variants: {
      variant: {
        default: [
          "bg-primary text-primary-foreground shadow-sm",
          "hover:bg-primary/90 hover:shadow-lg hover:-translate-y-0.5 hover:shadow-primary/25",
          "focus-visible:shadow-lg focus-visible:shadow-primary/25"
        ],
        destructive: [
          "bg-destructive text-white shadow-sm",
          "hover:bg-destructive/90 hover:shadow-lg hover:-translate-y-0.5 hover:shadow-red-500/25",
          "focus-visible:shadow-lg focus-visible:shadow-red-500/25"
        ],
        outline: [
          "border border-input bg-background shadow-sm",
          "hover:bg-accent hover:text-accent-foreground hover:shadow-md hover:border-primary/50",
          "focus-visible:border-primary focus-visible:shadow-md"
        ],
        secondary: [
          "bg-slate-700/60 dark:bg-slate-800/70 text-white border border-slate-600/40 dark:border-slate-600/50 shadow-sm",
          "hover:bg-slate-600/80 dark:hover:bg-slate-700/85 hover:border-slate-500/60 hover:shadow-md hover:-translate-y-0.5",
          "focus-visible:shadow-md focus-visible:border-slate-500/60"
        ],
        ghost: [
          "text-gray-300 dark:text-gray-300 hover:bg-slate-700/50 dark:hover:bg-slate-800/60 hover:text-white hover:scale-105",
          "active:scale-95"
        ],
        link: [
          "text-primary underline-offset-4 hover:underline hover:scale-105",
          "shadow-none p-0 h-auto active:scale-95"
        ],
        gradient: [
          "bg-gradient-to-r from-primary to-primary/80 text-primary-foreground shadow-lg",
          "hover:from-primary/90 hover:to-primary/70 hover:shadow-xl hover:-translate-y-1 hover:shadow-primary/30",
          "focus-visible:shadow-xl focus-visible:shadow-primary/30",
          "animate-gradient-x bg-[length:200%_200%]"
        ],
        success: [
          "bg-green-600 text-white shadow-sm",
          "hover:bg-green-700 hover:shadow-lg hover:-translate-y-0.5 hover:shadow-green-500/25",
          "focus-visible:shadow-lg focus-visible:shadow-green-500/25"
        ],
        warning: [
          "bg-yellow-600 text-white shadow-sm",
          "hover:bg-yellow-700 hover:shadow-lg hover:-translate-y-0.5 hover:shadow-yellow-500/25",
          "focus-visible:shadow-lg focus-visible:shadow-yellow-500/25"
        ],
        glass: [
          "bg-slate-800/60 dark:bg-slate-800/70 backdrop-blur-md border border-slate-600/50 dark:border-slate-600/60 text-white",
          "hover:bg-slate-700/80 dark:hover:bg-slate-700/85 hover:border-slate-500/70 hover:shadow-lg hover:-translate-y-0.5",
          "focus-visible:shadow-lg focus-visible:border-slate-500/70"
        ]
      },
      size: {
        sm: "h-8 rounded-md gap-1.5 px-3 text-xs font-medium has-[>svg]:px-2.5",
        default: "h-10 px-4 py-2 has-[>svg]:px-3",
        lg: "h-12 rounded-lg px-6 text-base has-[>svg]:px-4",
        xl: "h-14 rounded-xl px-8 text-lg has-[>svg]:px-6",
        icon: "size-10 p-0",
        "icon-sm": "size-8 p-0",
        "icon-lg": "size-12 p-0"
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps 
  extends React.ComponentProps<"button">,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
  loadingText?: string
  ripple?: boolean
  rippleColor?: string
}

function Button({
  className,
  variant,
  size,
  asChild = false,
  loading = false,
  loadingText,
  children,
  disabled,
  ripple = false,
  rippleColor,
  onMouseDown,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button"
  const rippleHook = useRipple({
    disabled: disabled || loading || !ripple,
    color: rippleColor,
  })

  const handleMouseDown = (event: React.MouseEvent<HTMLButtonElement>) => {
    if (ripple && !disabled && !loading) {
      rippleHook.onMouseDown(event as any)
    }
    onMouseDown?.(event)
  }

  if (asChild) {
    return (
      <Slot
        data-slot="button"
        className={cn(buttonVariants({ variant, size, className }))}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {loading && loadingText ? loadingText : children}
      </Slot>
    )
  }

  return (
    <Comp
      ref={ripple ? rippleHook.ref : undefined}
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={disabled || loading}
      onMouseDown={handleMouseDown}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {loading && loadingText ? loadingText : children}
    </Comp>
  )
}

export { Button }
