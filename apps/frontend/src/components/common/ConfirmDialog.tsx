/**
 * Confirmation Dialog Component
 * Provides consistent confirmation UX for destructive actions
 */

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { LoadingSpinner } from './LoadingSpinner';
import { AlertTriangle, Trash, AlertCircle } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isLoading?: boolean;
  variant?: 'danger' | 'warning' | 'info';
  icon?: React.ReactNode;
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isLoading = false,
  variant = 'danger',
  icon,
}: ConfirmDialogProps) {
  const handleConfirm = () => {
    if (!isLoading) {
      onConfirm();
    }
  };

  const getIcon = () => {
    if (icon) return icon;
    
    switch (variant) {
      case 'danger':
        return <Trash className="h-6 w-6 text-destructive" />;
      case 'warning':
        return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
      case 'info':
        return <AlertCircle className="h-6 w-6 text-blue-500" />;
      default:
        return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
    }
  };

  const getButtonVariant = () => {
    switch (variant) {
      case 'danger':
        return 'destructive';
      case 'warning':
        return 'default';
      case 'info':
        return 'default';
      default:
        return 'destructive';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            {getIcon()}
            <DialogTitle>{title}</DialogTitle>
          </div>
          {description && (
            <DialogDescription className="pl-9">
              {description}
            </DialogDescription>
          )}
        </DialogHeader>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            variant={getButtonVariant()}
            onClick={handleConfirm}
            disabled={isLoading}
            className="min-w-[100px]"
          >
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Processing...
              </>
            ) : (
              confirmLabel
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}