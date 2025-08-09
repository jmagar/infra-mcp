import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/design-system"

const cardVariants = cva(
  [
    "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border shadow-sm transition-all duration-200",
  ],
  {
    variants: {
      variant: {
        default: "bg-card border-border",
        elevated: "shadow-lg hover:shadow-xl",
        glass: "glass border-border/50",
        gradient: "gradient-subtle border-border/30",
        outlined: "border-2 border-primary/20 bg-primary/5",
      },
      padding: {
        none: "p-0",
        sm: "p-4 gap-4",
        default: "py-6 gap-6",
        lg: "p-8 gap-8",
      },
      interactive: {
        none: "",
        hover: "hover:shadow-md hover:scale-[1.02] cursor-pointer",
        clickable: "hover:shadow-md hover:scale-[1.01] active:scale-[0.99] cursor-pointer",
      }
    },
    defaultVariants: {
      variant: "default",
      padding: "default",
      interactive: "none",
    },
  }
)

export interface CardProps 
  extends React.ComponentProps<"div">,
    VariantProps<typeof cardVariants> {}

function Card({ className, variant, padding, interactive, ...props }: CardProps) {
  return (
    <div
      data-slot="card"
      className={cn(cardVariants({ variant, padding, interactive, className }))}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-6",
        "has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6 [.border-b]:mb-6",
        className
      )}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }: React.ComponentProps<"h3">) {
  return (
    <h3
      data-slot="card-title"
      className={cn("text-lg font-semibold leading-tight tracking-tight text-card-foreground", className)}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="card-description"
      className={cn("text-sm text-muted-foreground leading-relaxed", className)}
      {...props}
    />
  )
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className
      )}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn("px-6", className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center px-6 [.border-t]:pt-6", className)}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
}
