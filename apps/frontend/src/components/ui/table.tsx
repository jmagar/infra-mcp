import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react"

import { cn } from "@/lib/design-system"

function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div
      data-slot="table-container"
      className="relative w-full overflow-x-auto"
    >
      <table
        data-slot="table"
        className={cn("w-full caption-bottom text-sm", className)}
        {...props}
      />
    </div>
  )
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      data-slot="table-header"
      className={cn("[&_tr]:border-b", className)}
      {...props}
    />
  )
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return (
    <tbody
      data-slot="table-body"
      className={cn("[&_tr:last-child]:border-0", className)}
      {...props}
    />
  )
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        "bg-muted/50 border-t font-medium [&>tr]:last:border-b-0",
        className
      )}
      {...props}
    />
  )
}

const tableRowVariants = cva([
  "border-b transition-all duration-200",
  "hover:bg-muted/50 hover:shadow-sm hover:scale-[1.002]",
  "data-[state=selected]:bg-primary/5 data-[state=selected]:border-primary/20",
  "focus-within:bg-muted/30 focus-within:ring-1 focus-within:ring-primary/20"
]);

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn(tableRowVariants(), className)}
      {...props}
    />
  )
}

const sortableHeaderVariants = cva([
  "group inline-flex items-center gap-2 cursor-pointer select-none transition-all duration-200",
  "hover:text-foreground/80 active:scale-95",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:rounded-sm"
]);

export interface SortableHeaderProps {
  children: React.ReactNode;
  sortKey?: string;
  sortDirection?: 'asc' | 'desc' | null;
  onSort?: (key: string) => void;
  className?: string;
}

function SortableHeader({ 
  children, 
  sortKey, 
  sortDirection, 
  onSort, 
  className 
}: SortableHeaderProps) {
  const handleSort = () => {
    if (sortKey && onSort) {
      onSort(sortKey);
    }
  };

  return (
    <div 
      className={cn(sortableHeaderVariants(), className)}
      onClick={handleSort}
      tabIndex={sortKey ? 0 : -1}
      role={sortKey ? "button" : undefined}
      aria-sort={
        sortDirection === 'asc' ? 'ascending' : 
        sortDirection === 'desc' ? 'descending' : 
        sortKey ? 'none' : undefined
      }
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && sortKey) {
          e.preventDefault();
          handleSort();
        }
      }}
    >
      <span className="flex-1">{children}</span>
      {sortKey && (
        <div className="flex flex-col items-center justify-center w-4 h-4 opacity-60 group-hover:opacity-100 transition-opacity">
          {sortDirection === null && <ChevronsUpDown className="h-3 w-3" />}
          {sortDirection === 'asc' && <ChevronUp className="h-3 w-3 text-primary" />}
          {sortDirection === 'desc' && <ChevronDown className="h-3 w-3 text-primary" />}
        </div>
      )}
    </div>
  );
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
        className
      )}
      {...props}
    />
  )
}

const tableCellVariants = cva([
  "p-2 align-middle whitespace-nowrap transition-colors duration-150",
  "[&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
  "group-hover:text-foreground/90"
]);

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn(tableCellVariants(), className)}
      {...props}
    />
  )
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("text-muted-foreground mt-4 text-sm", className)}
      {...props}
    />
  )
}

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange?: (itemsPerPage: number) => void;
  showItemsPerPage?: boolean;
  showInfo?: boolean;
  className?: string;
}

function TablePagination({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
  showItemsPerPage = true,
  showInfo = true,
  className
}: PaginationProps) {
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  const getVisiblePages = () => {
    const delta = 2;
    const range = [];
    const rangeWithDots = [];

    for (let i = Math.max(2, currentPage - delta); i <= Math.min(totalPages - 1, currentPage + delta); i++) {
      range.push(i);
    }

    if (currentPage - delta > 2) {
      rangeWithDots.push(1, '...');
    } else {
      rangeWithDots.push(1);
    }

    rangeWithDots.push(...range);

    if (currentPage + delta < totalPages - 1) {
      rangeWithDots.push('...', totalPages);
    } else {
      if (totalPages > 1) rangeWithDots.push(totalPages);
    }

    return rangeWithDots;
  };

  const visiblePages = getVisiblePages();

  return (
    <div className={cn("flex items-center justify-between px-2 py-4", className)}>
      {showInfo && (
        <div className="flex items-center space-x-6 lg:space-x-8">
          <div className="text-sm text-muted-foreground">
            Showing {totalItems > 0 ? startItem : 0}-{endItem} of {totalItems} items
          </div>
          {showItemsPerPage && onItemsPerPageChange && (
            <div className="flex items-center space-x-2">
              <p className="text-sm text-muted-foreground">Items per page</p>
              <select
                value={itemsPerPage}
                onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
                className="h-8 w-16 rounded border border-input bg-background px-2 py-1 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                {[10, 20, 50, 100].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      <div className="flex items-center space-x-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="inline-flex items-center justify-center h-8 px-3 text-sm font-medium rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 transition-colors"
        >
          Previous
        </button>

        <div className="flex items-center space-x-1">
          {visiblePages.map((page, index) => (
            page === '...' ? (
              <span key={`dots-${index}`} className="px-2 py-1 text-sm text-muted-foreground">
                ...
              </span>
            ) : (
              <button
                key={page}
                onClick={() => onPageChange(page as number)}
                className={cn(
                  "inline-flex items-center justify-center h-8 w-8 text-sm font-medium rounded-md transition-colors",
                  currentPage === page
                    ? "bg-primary text-primary-foreground shadow hover:bg-primary/90"
                    : "border border-input bg-background hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                )}
              >
                {page}
              </button>
            )
          ))}
        </div>

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="inline-flex items-center justify-center h-8 px-3 text-sm font-medium rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  );
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
  SortableHeader,
  TablePagination,
}
