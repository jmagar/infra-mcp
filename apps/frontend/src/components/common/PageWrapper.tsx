import * as React from 'react';
import { cn, componentStyles } from '@/lib/design-system';
import { ChevronRight } from 'lucide-react';

export interface PageWrapperProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  description?: string;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  actions?: React.ReactNode;
  className?: string;
  contentClassName?: string;
  headerClassName?: string;
  variant?: 'default' | 'centered' | 'compact';
  fullWidth?: boolean;
}

export function PageWrapper({
  children,
  title,
  subtitle,
  description,
  breadcrumbs,
  actions,
  className,
  contentClassName,
  headerClassName,
  variant = 'default',
  fullWidth = false,
}: PageWrapperProps) {
  return (
    <div 
      className={cn(
        componentStyles.container.page,
        "animate-fade-in",
        className
      )}
    >
      <div 
        className={cn(
          componentStyles.container.section,
          !fullWidth && componentStyles.container.content,
          variant === 'centered' && "text-center",
          variant === 'compact' && "py-4"
        )}
      >
        {/* Page Header */}
        {(title || subtitle || description || breadcrumbs || actions) && (
          <header 
            className={cn(
              "space-y-4 pb-6 border-b border-border mb-8",
              variant === 'compact' && "pb-4 mb-6",
              headerClassName
            )}
          >
            {/* Breadcrumbs */}
            {breadcrumbs && breadcrumbs.length > 0 && (
              <nav className="flex items-center space-x-2 text-sm text-muted-foreground">
                {breadcrumbs.map((item, index) => (
                  <React.Fragment key={index}>
                    {index > 0 && (
                      <ChevronRight className="h-4 w-4 flex-shrink-0" />
                    )}
                    {item.href ? (
                      <a 
                        href={item.href}
                        className="hover:text-foreground transition-colors underline-offset-4 hover:underline"
                      >
                        {item.label}
                      </a>
                    ) : (
                      <span className={index === breadcrumbs.length - 1 ? "text-foreground font-medium" : ""}>
                        {item.label}
                      </span>
                    )}
                  </React.Fragment>
                ))}
              </nav>
            )}

            {/* Title and Actions */}
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div className="space-y-2">
                {title && (
                  <h1 
                    className={cn(
                      componentStyles.typography.heading.page,
                      variant === 'compact' && componentStyles.typography.heading.section
                    )}
                  >
                    {title}
                  </h1>
                )}
                {subtitle && (
                  <h2 className={componentStyles.typography.heading.subsection}>
                    {subtitle}
                  </h2>
                )}
                {description && (
                  <p className={componentStyles.typography.body.large}>
                    {description}
                  </p>
                )}
              </div>

              {/* Action buttons */}
              {actions && (
                <div className="flex-shrink-0">
                  <div className="flex items-center gap-3">
                    {actions}
                  </div>
                </div>
              )}
            </div>
          </header>
        )}

        {/* Page Content */}
        <main 
          className={cn(
            "animate-slide-up",
            contentClassName
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}

// Convenience wrapper for dashboard-style pages
export function DashboardPage({ 
  children, 
  className,
  ...props 
}: Omit<PageWrapperProps, 'variant'>) {
  return (
    <PageWrapper 
      {...props}
      variant="default"
      className={cn("min-h-screen", className)}
    >
      <div className={componentStyles.layout.grid.dashboard}>
        {children}
      </div>
    </PageWrapper>
  );
}

// Convenience wrapper for form pages
export function FormPage({
  children,
  className,
  ...props
}: Omit<PageWrapperProps, 'variant' | 'fullWidth'>) {
  return (
    <PageWrapper
      {...props}
      variant="centered"
      fullWidth={false}
      className={cn("min-h-screen", className)}
      contentClassName="max-w-2xl mx-auto"
    >
      {children}
    </PageWrapper>
  );
}

// Convenience wrapper for listing pages
export function ListPage({
  children,
  className,
  ...props
}: Omit<PageWrapperProps, 'variant'>) {
  return (
    <PageWrapper
      {...props}
      variant="default"
      className={cn("min-h-screen", className)}
    >
      <div className="space-y-6">
        {children}
      </div>
    </PageWrapper>
  );
}

// Convenience wrapper for detail pages
export function DetailPage({
  children,
  className,
  ...props
}: Omit<PageWrapperProps, 'variant'>) {
  return (
    <PageWrapper
      {...props}
      variant="default"
      className={cn("min-h-screen", className)}
    >
      <div className="grid gap-8 lg:grid-cols-3">
        {children}
      </div>
    </PageWrapper>
  );
}

// Loading state component
export function PageLoader({ 
  title = "Loading...",
  description = "Please wait while we fetch your data."
}: { 
  title?: string;
  description?: string;
}) {
  return (
    <PageWrapper>
      <div className={componentStyles.layout.flex.columnCenter + " py-12"}>
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mb-4" />
        <h2 className={componentStyles.typography.heading.subsection + " mb-2"}>
          {title}
        </h2>
        <p className={componentStyles.typography.body.base}>
          {description}
        </p>
      </div>
    </PageWrapper>
  );
}

// Error state component  
export function PageError({
  title = "Something went wrong",
  description = "We encountered an error while loading this page.",
  action,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <PageWrapper>
      <div className={componentStyles.layout.flex.columnCenter + " py-12"}>
        <div className="h-16 w-16 bg-destructive/10 text-destructive rounded-full flex items-center justify-center mb-4">
          <svg 
            className="h-8 w-8" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
            />
          </svg>
        </div>
        <h2 className={componentStyles.typography.heading.subsection + " mb-2"}>
          {title}
        </h2>
        <p className={componentStyles.typography.body.base + " mb-6"}>
          {description}
        </p>
        {action}
      </div>
    </PageWrapper>
  );
}

// Empty state component
export function PageEmpty({
  title = "No data found",
  description = "There's nothing to show here yet.",
  action,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className={componentStyles.layout.flex.columnCenter + " py-12"}>
      <div className="h-16 w-16 bg-muted text-muted-foreground rounded-full flex items-center justify-center mb-4">
        <svg 
          className="h-8 w-8" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
      </div>
      <h3 className={componentStyles.typography.heading.card + " mb-2"}>
        {title}
      </h3>
      <p className={componentStyles.typography.body.base + " mb-6"}>
        {description}
      </p>
      {action}
    </div>
  );
}