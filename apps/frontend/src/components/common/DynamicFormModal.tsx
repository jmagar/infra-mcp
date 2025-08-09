/**
 * Dynamic Form Modal Component
 * Provides a form modal with dynamic field generation
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { LoadingSpinner } from './LoadingSpinner';

interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'textarea' | 'select';
  placeholder?: string;
  required?: boolean;
  rows?: number;
  options?: { value: string; label: string }[];
}

interface DynamicFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: Record<string, string>) => void | Promise<void>;
  title: string;
  description?: string;
  fields: FormField[];
  submitLabel?: string;
  cancelLabel?: string;
  isLoading?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export function DynamicFormModal({
  isOpen,
  onClose,
  onSubmit,
  title,
  description,
  fields,
  submitLabel = 'Submit',
  cancelLabel = 'Cancel',
  isLoading = false,
  size = 'md',
}: DynamicFormModalProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});

  const handleInputChange = (name: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoading) {
      await onSubmit(formData);
    }
  };

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  const renderField = (field: FormField) => {
    const value = formData[field.name] || '';

    switch (field.type) {
      case 'textarea':
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Textarea
              id={field.name}
              placeholder={field.placeholder}
              value={value}
              onChange={(e) => handleInputChange(field.name, e.target.value)}
              required={field.required}
              rows={field.rows || 4}
            />
          </div>
        );

      case 'select':
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <select
              id={field.name}
              value={value}
              onChange={(e) => handleInputChange(field.name, e.target.value)}
              required={field.required}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="">Select {field.label}</option>
              {field.options?.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        );

      default:
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={field.name}
              type={field.type}
              placeholder={field.placeholder}
              value={value}
              onChange={(e) => handleInputChange(field.name, e.target.value)}
              required={field.required}
            />
          </div>
        );
    }
  };

  // Reset form data when modal closes
  React.useEffect(() => {
    if (!isOpen) {
      setFormData({});
    }
  }, [isOpen]);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className={`${sizeClasses[size]} max-h-[80vh] overflow-y-auto`}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && (
            <DialogDescription>{description}</DialogDescription>
          )}
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="py-4 space-y-4">
            {fields.map(renderField)}
          </div>

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
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Submitting...
                </>
              ) : (
                submitLabel
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}