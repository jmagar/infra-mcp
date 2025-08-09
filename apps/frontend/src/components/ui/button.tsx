import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/design-system"

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium",
    "transition-all duration-200 ease-in-out disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
    "outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
    "active:scale-[0.98]"
  ],
  {
    variants: {
      variant: {
        default: [
          "bg-primary text-primary-foreground shadow-sm",
          "hover:bg-primary/90 hover:shadow-md",
          "focus-visible:ring-primary/20"
        ],
        destructive: [
          "bg-destructive text-white shadow-sm",
          "hover:bg-destructive/90 hover:shadow-md",
          "focus-visible:ring-destructive/20"
        ],
        outline: [
          "border border-input bg-background shadow-sm",
          "hover:bg-accent hover:text-accent-foreground hover:shadow-md",
          "focus-visible:ring-accent/20"
        ],
        secondary: [
          "bg-secondary text-secondary-foreground shadow-sm",
          "hover:bg-secondary/80 hover:shadow-md",
          "focus-visible:ring-secondary/20"
        ],
        ghost: [
          "hover:bg-accent hover:text-accent-foreground",
          "focus-visible:ring-accent/20"
        ],
        link: [
          "text-primary underline-offset-4 hover:underline",
          "shadow-none p-0 h-auto focus-visible:ring-primary/20"
        ],
        gradient: [
          "bg-gradient-to-r from-primary to-primary/80 text-primary-foreground shadow-lg",
          "hover:from-primary/90 hover:to-primary/70 hover:shadow-xl hover:-translate-y-0.5",
          "focus-visible:ring-primary/20"
        ],
        success: [
          "bg-green-600 text-white shadow-sm",
          "hover:bg-green-700 hover:shadow-md",
          "focus-visible:ring-green-600/20"
        ],
        warning: [
          "bg-yellow-600 text-white shadow-sm",
          "hover:bg-yellow-700 hover:shadow-md",
          "focus-visible:ring-yellow-600/20"
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
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {loading && loadingText ? loadingText : children}
    </Comp>
  )
}

export { Button, buttonVariants }
