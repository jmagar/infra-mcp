/**
 * Reusable Form Modal Component
 * Provides a consistent modal interface for create/edit operations
 * Enhanced with responsive design for optimal mobile/desktop experience
 */

import React, { ReactNode } from 'react';
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
import { useResponsive } from '@/hooks';
import { modals, componentSizes, forms, spacing } from '@/lib/responsive';

interface FormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  submitLabel?: string;
  cancelLabel?: string;
  isLoading?: boolean;
  isSubmitDisabled?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'auto';
}

export function FormModal({
  isOpen,
  onClose,
  onSubmit,
  title,
  description,
  children,
  submitLabel = 'Save',
  cancelLabel = 'Cancel',
  isLoading = false,
  isSubmitDisabled = false,
  size = 'auto',
}: FormModalProps) {
  const { isMobile } = useResponsive();
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoading && !isSubmitDisabled) {
      onSubmit();
    }
  };

  // Responsive size classes
  const getSizeClasses = () => {
    if (size === 'auto') {
      return isMobile ? 'w-full max-w-[95vw] mx-2' : modals.container;
    }
    
    const sizeClasses = {
      sm: isMobile ? 'w-full max-w-[95vw] mx-2' : 'max-w-md',
      md: isMobile ? 'w-full max-w-[95vw] mx-2' : 'max-w-lg',
      lg: isMobile ? 'w-full max-w-[95vw] mx-2' : 'max-w-2xl',
      xl: isMobile ? 'w-full max-w-[95vw] mx-2' : 'max-w-4xl',
    };
    
    return sizeClasses[size as keyof typeof sizeClasses] || sizeClasses.md;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className={`
        ${getSizeClasses()} 
        max-h-[90vh] 
        overflow-y-auto
        ${isMobile ? 'fixed bottom-0 top-auto translate-x-[-50%] translate-y-0 rounded-t-lg rounded-b-none' : ''}
      `}>
        <DialogHeader className={spacing.padding.card}>
          <DialogTitle className={isMobile ? 'text-lg' : 'text-xl'}>
            {title}
          </DialogTitle>
          {description && (
            <DialogDescription className={isMobile ? 'text-sm' : ''}>
              {description}
            </DialogDescription>
          )}
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex-1 flex flex-col">
          <div className={`flex-1 ${spacing.padding.card} ${forms.grid.single}`}>
            {children}
          </div>

          <DialogFooter className={`${spacing.padding.card} border-t ${
            isMobile ? 'pt-4' : ''
          }`}>
            <div className={forms.buttons}>
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isLoading}
                className={componentSizes.button.full}
              >
                {cancelLabel}
              </Button>
              <Button
                type="submit"
                disabled={isLoading || isSubmitDisabled}
                className={`${componentSizes.button.full} ${isMobile ? 'min-w-[120px]' : 'min-w-[100px]'}`}
              >
                {isLoading ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    {isMobile ? 'Saving...' : 'Saving...'}
                  </>
                ) : (
                  submitLabel
                )}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}