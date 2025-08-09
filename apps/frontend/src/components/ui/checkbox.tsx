/**
 * Checkbox Component
 * Custom checkbox implementation without external dependencies
 */

import * as React from "react"
import { cn } from "@/lib/design-system"
import { Check } from "lucide-react"

export interface CheckboxProps {
  id?: string
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
  disabled?: boolean
  className?: string
  children?: React.ReactNode
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ id, checked = false, onCheckedChange, disabled = false, className, children, ...props }, ref) => {
    return (
      <div className="flex items-center space-x-2">
        <div className="relative">
          <input
            ref={ref}
            id={id}
            type="checkbox"
            checked={checked}
            onChange={(e) => onCheckedChange?.(e.target.checked)}
            disabled={disabled}
            className="sr-only"
            {...props}
          />
          <div
            className={cn(
              "peer h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
              checked && "bg-primary text-primary-foreground",
              !checked && "bg-background",
              className
            )}
            onClick={() => !disabled && onCheckedChange?.(!checked)}
          >
            {checked && (
              <Check className="h-4 w-4 text-primary-foreground" />
            )}
          </div>
        </div>
        {children && (
          <label
            htmlFor={id}
            className={cn(
              "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer",
              disabled && "cursor-not-allowed opacity-70"
            )}
            onClick={() => !disabled && onCheckedChange?.(!checked)}
          >
            {children}
          </label>
        )}
      </div>
    )
  }
)

Checkbox.displayName = "Checkbox"

export { Checkbox }