import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/design-system"

const inputVariants = cva([
  "file:text-foreground placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground",
  "flex h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs outline-none",
  "file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium",
  "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
  "transition-all duration-200 ease-in-out",
  "relative",
  // Focus styles with enhanced animations
  "focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary",
  "focus:shadow-md focus:shadow-primary/10 focus:scale-[1.01]",
  // Hover styles
  "hover:border-primary/50 hover:shadow-sm",
  // Error states
  "aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  "aria-invalid:focus:ring-destructive/30 aria-invalid:focus:border-destructive",
], {
  variants: {
    variant: {
      default: [
        "border-input bg-background dark:bg-input/30"
      ],
      filled: [
        "border-transparent bg-muted hover:bg-muted/80 focus:bg-background focus:border-primary"
      ],
      ghost: [
        "border-transparent bg-transparent hover:bg-muted/50 focus:bg-muted/30 focus:border-primary/50"
      ],
      glass: [
        "border-border/50 bg-background/50 backdrop-blur-sm",
        "hover:bg-background/80 hover:border-border",
        "focus:bg-background/90 focus:border-primary focus:backdrop-blur-md"
      ]
    },
    size: {
      sm: "h-8 px-2 py-1 text-sm",
      default: "h-9 px-3 py-1",
      lg: "h-10 px-4 py-2 text-base"
    },
    animate: {
      none: "",
      subtle: "focus:animate-pulse-once",
      bounce: "focus:animate-bounce-subtle",
      glow: "focus:animate-glow-pulse"
    }
  },
  defaultVariants: {
    variant: "default",
    size: "default",
    animate: "subtle"
  }
})

export interface InputProps 
  extends React.ComponentProps<"input">,
    VariantProps<typeof inputVariants> {
  label?: string
  error?: string
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
}

function Input({ 
  className, 
  type, 
  variant,
  size,
  animate,
  label,
  error,
  icon,
  iconPosition = 'left',
  ...props 
}: InputProps) {
  const [isFocused, setIsFocused] = React.useState(false)
  const [hasValue, setHasValue] = React.useState(false)
  
  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(true)
    props.onFocus?.(e)
  }
  
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(false)
    props.onBlur?.(e)
  }
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setHasValue(e.target.value.length > 0)
    props.onChange?.(e)
  }

  React.useEffect(() => {
    if (props.value || props.defaultValue) {
      setHasValue(true)
    }
  }, [props.value, props.defaultValue])

  if (label) {
    return (
      <div className="relative space-y-2">
        {/* Floating label */}
        <label 
          className={cn(
            "absolute left-3 transition-all duration-200 pointer-events-none select-none",
            "text-muted-foreground text-sm",
            isFocused || hasValue 
              ? "top-0 -translate-y-1/2 bg-background px-2 text-xs text-primary z-10" 
              : "top-1/2 -translate-y-1/2"
          )}
        >
          {label}
        </label>
        
        {/* Input wrapper for icon support */}
        <div className="relative">
          {icon && iconPosition === 'left' && (
            <div className={cn(
              "absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors",
              isFocused && "text-primary"
            )}>
              {icon}
            </div>
          )}
          
          <input
            type={type}
            data-slot="input"
            className={cn(
              inputVariants({ variant, size, animate }),
              icon && iconPosition === 'left' && "pl-10",
              icon && iconPosition === 'right' && "pr-10",
              label && "pt-4",
              error && "border-destructive focus:border-destructive focus:ring-destructive/20",
              className
            )}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onChange={handleChange}
            {...props}
          />
          
          {icon && iconPosition === 'right' && (
            <div className={cn(
              "absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors",
              isFocused && "text-primary"
            )}>
              {icon}
            </div>
          )}
        </div>
        
        {/* Error message */}
        {error && (
          <p className="text-xs text-destructive animate-fade-in">
            {error}
          </p>
        )}
      </div>
    )
  }

  // Simple input without label
  return (
    <div className="relative">
      {icon && iconPosition === 'left' && (
        <div className={cn(
          "absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors",
          isFocused && "text-primary"
        )}>
          {icon}
        </div>
      )}
      
      <input
        type={type}
        data-slot="input"
        className={cn(
          inputVariants({ variant, size, animate }),
          icon && iconPosition === 'left' && "pl-10",
          icon && iconPosition === 'right' && "pr-10",
          error && "border-destructive focus:border-destructive focus:ring-destructive/20",
          className
        )}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onChange={handleChange}
        {...props}
      />
      
      {icon && iconPosition === 'right' && (
        <div className={cn(
          "absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors",
          isFocused && "text-primary"
        )}>
          {icon}
        </div>
      )}
      
      {error && (
        <p className="text-xs text-destructive mt-1 animate-fade-in">
          {error}
        </p>
      )}
    </div>
  )
}

export { Input }
