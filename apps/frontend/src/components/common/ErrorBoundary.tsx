/**
 * Enhanced Error Boundary Component
 * Comprehensive error handling with better UX and logging
 */

import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw, Home, Bug, Copy, CheckCircle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  copied: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  private resetTimeout?: NodeJS.Timeout;

  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, copied: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, copied: false };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler
    this.props.onError?.(error, errorInfo);

    // Log to external service in production
    if (import.meta.env.PROD) {
      // TODO: Integrate with error tracking service (e.g., Sentry)
      console.error('Production error logged:', { error, errorInfo });
    }
  }

  componentWillUnmount() {
    if (this.resetTimeout) {
      clearTimeout(this.resetTimeout);
    }
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  private handleCopyError = async () => {
    const errorText = this.getErrorText();
    try {
      await navigator.clipboard.writeText(errorText);
      this.setState({ copied: true });
      
      // Reset copied state after 2 seconds
      this.resetTimeout = setTimeout(() => {
        this.setState({ copied: false });
      }, 2000);
    } catch (err) {
      console.error('Failed to copy error details:', err);
    }
  };

  private getErrorText = (): string => {
    const { error, errorInfo } = this.state;
    const timestamp = new Date().toISOString();
    
    return `
Infrastructure Error Report
=========================
Timestamp: ${timestamp}
URL: ${window.location.href}
User Agent: ${navigator.userAgent}

Error Message: ${error?.message || 'Unknown error'}

Stack Trace:
${error?.stack || 'No stack trace available'}

Component Stack:
${errorInfo?.componentStack || 'No component stack available'}

Additional Details:
- Environment: ${import.meta.env.MODE}
- React Version: ${React.version}
`.trim();
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background">
          <Card className="max-w-2xl w-full border-destructive/20 bg-destructive/5">
            <CardHeader className="text-center pb-4">
              <div className="flex justify-center mb-4">
                <div className="p-3 rounded-full bg-destructive/10">
                  <AlertTriangle className="w-8 h-8 text-destructive" />
                </div>
              </div>
              <CardTitle className="text-2xl text-destructive">
                Application Error
              </CardTitle>
              <p className="text-destructive/80">
                We encountered an unexpected error. Our team has been notified and will look into this issue.
              </p>
            </CardHeader>
            
            <CardContent className="space-y-6">
              {/* Error Details for Development */}
              {import.meta.env.DEV && this.state.error && (
                <div className="space-y-4">
                  <div className="p-4 bg-muted rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-sm flex items-center gap-2">
                        <Bug className="w-4 h-4" />
                        Error Details (Development Mode)
                      </h3>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={this.handleCopyError}
                        className="h-7 text-xs"
                      >
                        {this.state.copied ? (
                          <>
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3 mr-1" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                    
                    <div className="text-sm font-mono text-muted-foreground space-y-2 max-h-96 overflow-y-auto">
                      <div>
                        <strong className="text-foreground">Error:</strong> {this.state.error.message}
                      </div>
                      
                      <div>
                        <strong className="text-foreground">Location:</strong> {window.location.pathname}
                      </div>
                      
                      {this.state.error.stack && (
                        <div>
                          <strong className="text-foreground">Stack Trace:</strong>
                          <pre className="mt-1 text-xs bg-background p-2 rounded border overflow-auto">
                            {this.state.error.stack}
                          </pre>
                        </div>
                      )}
                      
                      {this.state.errorInfo?.componentStack && (
                        <div>
                          <strong className="text-foreground">Component Stack:</strong>
                          <pre className="mt-1 text-xs bg-background p-2 rounded border overflow-auto">
                            {this.state.errorInfo.componentStack}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button 
                  onClick={this.handleReset}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </Button>
                
                <Button 
                  onClick={this.handleReload}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Reload Page
                </Button>
                
                <Button 
                  onClick={this.handleGoHome}
                  className="flex items-center gap-2"
                >
                  <Home className="w-4 h-4" />
                  Go to Dashboard
                </Button>
              </div>

              {/* Help Text */}
              <div className="text-center text-sm text-muted-foreground space-y-1">
                <p>If this problem continues, please try:</p>
                <ul className="text-xs space-y-1">
                  <li>• Refreshing the page or clearing your browser cache</li>
                  <li>• Checking your internet connection</li>
                  <li>• Contacting support if the issue persists</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// Lightweight error boundary for components
interface SimpleErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

export function SimpleErrorBoundary({ children, fallback, onError }: SimpleErrorBoundaryProps) {
  return (
    <ErrorBoundary 
      onError={onError}
      fallback={
        fallback || (
          <div className="p-4 border border-destructive/20 rounded-lg bg-destructive/5">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="w-4 h-4" />
              <span className="font-medium">Component Error</span>
            </div>
            <p className="text-sm text-destructive/80 mt-1">
              This component encountered an error and could not be displayed properly.
            </p>
          </div>
        )
      }
    >
      {children}
    </ErrorBoundary>
  );
}