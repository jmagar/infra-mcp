/**
 * Empty State Component
 * Provides consistent empty state UX across the application
 */

import React, { ReactNode } from 'react';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { Database, Server, Container, HardDrive, Network, Users } from 'lucide-react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  variant?: 'default' | 'devices' | 'containers' | 'storage' | 'network' | 'users';
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  variant = 'default',
}: EmptyStateProps) {
  const getDefaultIcon = () => {
    switch (variant) {
      case 'devices':
        return <Server className="h-12 w-12 text-muted-foreground" />;
      case 'containers':
        return <Container className="h-12 w-12 text-muted-foreground" />;
      case 'storage':
        return <HardDrive className="h-12 w-12 text-muted-foreground" />;
      case 'network':
        return <Network className="h-12 w-12 text-muted-foreground" />;
      case 'users':
        return <Users className="h-12 w-12 text-muted-foreground" />;
      default:
        return <Database className="h-12 w-12 text-muted-foreground" />;
    }
  };

  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <div className="mb-4">
          {icon || getDefaultIcon()}
        </div>
        
        <h3 className="text-lg font-semibold text-foreground mb-2">
          {title}
        </h3>
        
        {description && (
          <p className="text-sm text-muted-foreground mb-6 max-w-sm">
            {description}
          </p>
        )}
        
        {action && (
          <Button onClick={action.onClick} className="mt-2">
            {action.label}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}