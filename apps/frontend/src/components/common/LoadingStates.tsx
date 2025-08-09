/**
 * Loading States Components
 * Comprehensive loading indicators and skeleton components
 */

import React from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Container, Database, Activity, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/design-system';

// Basic loading spinner
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <Loader2 className={cn('animate-spin text-primary', sizeClasses[size], className)} />
  );
}

// Inline loading with text
interface InlineLoadingProps {
  text?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function InlineLoading({ text = 'Loading...', size = 'md', className }: InlineLoadingProps) {
  return (
    <div className={cn('flex items-center gap-2 text-muted-foreground', className)}>
      <LoadingSpinner size={size} />
      <span className={cn(
        size === 'sm' && 'text-sm',
        size === 'md' && 'text-base',
        size === 'lg' && 'text-lg'
      )}>
        {text}
      </span>
    </div>
  );
}

// Full page loading
interface PageLoadingProps {
  title?: string;
  description?: string;
  icon?: React.ElementType;
}

export function PageLoading({ 
  title = 'Loading...', 
  description = 'Please wait while we load your data',
  icon: Icon = Activity 
}: PageLoadingProps) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="flex justify-center">
          <div className="p-4 rounded-full bg-primary/10">
            <Icon className="w-8 h-8 text-primary" />
          </div>
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">{title}</h3>
          <p className="text-muted-foreground">{description}</p>
        </div>
        <LoadingSpinner size="lg" />
      </div>
    </div>
  );
}

// Card loading skeleton
export function CardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-3 bg-muted rounded animate-pulse w-2/3" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="h-3 bg-muted rounded animate-pulse" />
          <div className="h-3 bg-muted rounded animate-pulse w-4/5" />
          <div className="h-3 bg-muted rounded animate-pulse w-3/5" />
        </div>
      </CardContent>
    </Card>
  );
}

// Table loading skeleton
interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 4 }: TableSkeletonProps) {
  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, i) => (
          <div key={i} className="h-4 bg-muted rounded animate-pulse" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div key={colIndex} className="h-3 bg-muted rounded animate-pulse" />
          ))}
        </div>
      ))}
    </div>
  );
}

// Device list skeleton
export function DeviceListSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 6}).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 flex-1">
                <div className="w-10 h-10 bg-muted rounded-lg animate-pulse" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 bg-muted rounded animate-pulse w-1/3" />
                  <div className="h-3 bg-muted rounded animate-pulse w-1/2" />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-16 h-6 bg-muted rounded animate-pulse" />
                <div className="w-8 h-8 bg-muted rounded animate-pulse" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// Container list skeleton
export function ContainerListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 8}).map((_, i) => (
        <div key={i} className="flex items-center justify-between p-3 border rounded-lg">
          <div className="flex items-center gap-3 flex-1">
            <div className="w-2 h-2 bg-muted rounded-full animate-pulse" />
            <Container className="w-5 h-5 text-muted-foreground animate-pulse" />
            <div className="space-y-1 flex-1">
              <div className="h-4 bg-muted rounded animate-pulse w-1/4" />
              <div className="h-3 bg-muted rounded animate-pulse w-1/3" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-16 h-5 bg-muted rounded animate-pulse" />
            <div className="w-20 h-5 bg-muted rounded animate-pulse" />
            <div className="w-6 h-6 bg-muted rounded animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}

// Dashboard stats skeleton
export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4}).map((_, i) => (
        <Card key={i}>
          <CardContent className="p-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="h-3 bg-muted rounded animate-pulse w-1/2" />
                <div className="w-4 h-4 bg-muted rounded animate-pulse" />
              </div>
              <div className="h-6 bg-muted rounded animate-pulse w-1/3" />
              <div className="h-2 bg-muted rounded animate-pulse" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// Loading button state
interface LoadingButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  children: React.ReactNode;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg';
}

export function LoadingButton({ 
  loading = false, 
  children, 
  disabled, 
  variant = 'default',
  size = 'default',
  className,
  ...props 
}: LoadingButtonProps) {
  return (
    <Button
      {...props}
      variant={variant}
      size={size}
      disabled={loading || disabled}
      className={cn(className)}
    >
      {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {children}
    </Button>
  );
}

// Empty state component
interface EmptyStateProps {
  icon?: React.ElementType;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ 
  icon: Icon = Database, 
  title, 
  description, 
  action 
}: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <div className="flex justify-center mb-4">
        <div className="p-3 rounded-full bg-muted">
          <Icon className="w-8 h-8 text-muted-foreground" />
        </div>
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground mb-4 max-w-sm mx-auto">{description}</p>
      {action && (
        <Button onClick={action.onClick} variant="outline">
          {action.label}
        </Button>
      )}
    </div>
  );
}

// Loading overlay for components
interface LoadingOverlayProps {
  loading: boolean;
  children: React.ReactNode;
  text?: string;
}

export function LoadingOverlay({ loading, children, text = 'Loading...' }: LoadingOverlayProps) {
  return (
    <div className="relative">
      {children}
      {loading && (
        <div className="absolute inset-0 bg-background/50 backdrop-blur-sm flex items-center justify-center rounded-lg z-10">
          <div className="bg-background border rounded-lg p-4 shadow-lg">
            <InlineLoading text={text} />
          </div>
        </div>
      )}
    </div>
  );
}

// Progressive loading component
interface ProgressiveLoadingProps {
  steps: Array<{
    label: string;
    completed: boolean;
    loading?: boolean;
  }>;
  className?: string;
}

export function ProgressiveLoading({ steps, className }: ProgressiveLoadingProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {steps.map((step, index) => (
        <div key={index} className="flex items-center gap-3">
          <div className={cn(
            'w-6 h-6 rounded-full border-2 flex items-center justify-center',
            step.completed 
              ? 'bg-primary border-primary text-primary-foreground' 
              : step.loading
              ? 'border-primary'
              : 'border-muted-foreground/30'
          )}>
            {step.loading ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : step.completed ? (
              <span className="text-xs">✓</span>
            ) : (
              <span className="text-xs">{index + 1}</span>
            )}
          </div>
          <span className={cn(
            'text-sm',
            step.completed ? 'text-foreground' : 'text-muted-foreground'
          )}>
            {step.label}
          </span>
        </div>
      ))}
    </div>
  );
}

// Retry component for failed loads
interface RetryProps {
  onRetry: () => void;
  error?: string;
  loading?: boolean;
}

export function Retry({ onRetry, error = 'Something went wrong', loading = false }: RetryProps) {
  return (
    <div className="text-center py-8">
      <div className="flex justify-center mb-4">
        <div className="p-3 rounded-full bg-destructive/10">
          <RefreshCw className="w-6 h-6 text-destructive" />
        </div>
      </div>
      <h3 className="text-lg font-semibold mb-2">Failed to Load</h3>
      <p className="text-muted-foreground mb-4">{error}</p>
      <LoadingButton 
        onClick={onRetry} 
        loading={loading}
        variant="outline"
      >
        <RefreshCw className="w-4 h-4 mr-2" />
        Try Again
      </LoadingButton>
    </div>
  );
}