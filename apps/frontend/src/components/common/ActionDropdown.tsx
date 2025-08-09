/**
 * Action Dropdown Component
 * Provides a consistent dropdown menu for table/list actions
 */

import React from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { Button } from '../ui/button';
import { MoreVertical, LucideIcon } from 'lucide-react';

export interface ActionItem {
  label: string;
  icon?: LucideIcon;
  onClick: () => void;
  variant?: 'default' | 'destructive';
  disabled?: boolean;
  separator?: boolean; // Add separator after this item
}

interface ActionDropdownProps {
  actions: ActionItem[];
  trigger?: React.ReactNode;
  disabled?: boolean;
}

export function ActionDropdown({
  actions,
  trigger,
  disabled = false,
}: ActionDropdownProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild disabled={disabled}>
        {trigger || (
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <MoreVertical className="h-4 w-4" />
            <span className="sr-only">Open menu</span>
          </Button>
        )}
      </DropdownMenuTrigger>
      
      <DropdownMenuContent align="end" className="w-48">
        {actions.map((action, index) => (
          <React.Fragment key={index}>
            <DropdownMenuItem
              onClick={action.onClick}
              disabled={action.disabled}
              className={action.variant === 'destructive' ? 'text-destructive focus:text-destructive' : ''}
            >
              {action.icon && (
                <action.icon className="mr-2 h-4 w-4" />
              )}
              {action.label}
            </DropdownMenuItem>
            {action.separator && index < actions.length - 1 && (
              <DropdownMenuSeparator />
            )}
          </React.Fragment>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}