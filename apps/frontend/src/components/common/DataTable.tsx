import { useState, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  ChevronUpIcon, 
  ChevronDownIcon, 
  SearchIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from 'lucide-react';
import { cn } from '@/lib/design-system';
import { useResponsive } from '@/hooks';
import { dataTable, spacing, componentSizes, cards } from '@/lib/responsive';

export interface Column<T> {
  key: keyof T | string;
  title: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: T[keyof T], item: T, index: number) => React.ReactNode;
  className?: string;
  width?: string;
  hideOnMobile?: boolean;
  hideOnTablet?: boolean;
  priority?: number; // 1 = highest priority (always show), 5 = lowest
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  loading?: boolean;
  pagination?: {
    pageSize?: number;
    showSizeSelector?: boolean;
  };
  searchable?: boolean;
  searchPlaceholder?: string;
  onRowClick?: (item: T, index: number) => void;
  className?: string;
  emptyMessage?: string;
  selectedRows?: T[];
  onSelectionChange?: (selectedRows: T[]) => void;
  rowKey?: keyof T;
  mobileCardView?: boolean; // Enable card view on mobile
}

type SortDirection = 'asc' | 'desc' | null;

// Mobile card component for better mobile UX
function MobileCard<T>({ 
  item, 
  columns, 
  onRowClick, 
  rowKey, 
  index,
  isSelected,
  onSelectionChange,
}: { 
  item: T; 
  columns: Column<T>[]; 
  onRowClick?: (item: T, index: number) => void;
  rowKey?: keyof T;
  index: number;
  isSelected?: boolean;
  onSelectionChange?: (item: T, selected: boolean) => void;
}) {
  // Get the highest priority columns for mobile view
  const mobileColumns = columns
    .filter(col => !col.hideOnMobile)
    .sort((a, b) => (a.priority || 3) - (b.priority || 3))
    .slice(0, 4); // Show max 4 fields on mobile

  return (
    <div 
      className={cn(
        'border rounded-lg bg-card transition-colors',
        cards.padding,
        onRowClick ? 'cursor-pointer hover:bg-muted/50' : '',
        isSelected ? 'bg-blue-50 border-blue-200' : ''
      )}
      onClick={() => onRowClick?.(item, index)}
    >
      {onSelectionChange && rowKey && (
        <div className="flex items-center justify-between mb-3 pb-3 border-b">
          <span className="text-sm font-medium">Select Item</span>
          <input
            type="checkbox"
            checked={isSelected || false}
            onChange={(e) => {
              e.stopPropagation();
              onSelectionChange(item, e.target.checked);
            }}
            className="rounded border-gray-300"
          />
        </div>
      )}
      
      <div className="space-y-2">
        {mobileColumns.map((column) => {
          const value = column.render 
            ? column.render(item[column.key as keyof T], item, index)
            : String(item[column.key as keyof T] || '-');

          return (
            <div key={String(column.key)} className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground font-medium min-w-0 flex-1">
                {column.title}:
              </span>
              <span className="text-right ml-2 truncate flex-1">{value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  loading = false,
  pagination,
  searchable = false,
  searchPlaceholder = 'Search...',
  onRowClick,
  className,
  emptyMessage = 'No data available',
  selectedRows = [],
  onSelectionChange,
  rowKey,
  mobileCardView = true,
}: DataTableProps<T>) {
  const { isMobile, isTablet } = useResponsive();
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(pagination?.pageSize || 10);

  // Filter columns based on screen size
  const visibleColumns = useMemo(() => {
    return columns.filter(column => {
      if (isMobile && column.hideOnMobile) return false;
      if (isTablet && column.hideOnTablet) return false;
      return true;
    });
  }, [columns, isMobile, isTablet]);

  // Filter data based on search
  const filteredData = useMemo(() => {
    if (!searchable || !search.trim()) return data;
    
    return data.filter((item) =>
      Object.values(item).some((value) =>
        String(value).toLowerCase().includes(search.toLowerCase())
      )
    );
  }, [data, search, searchable]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return filteredData;
    
    return [...filteredData].sort((a, b) => {
      const aValue = a[sortKey];
      const bValue = b[sortKey];
      
      if (aValue === bValue) return 0;
      
      const comparison = aValue < bValue ? -1 : 1;
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [filteredData, sortKey, sortDirection]);

  // Paginate data
  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData;
    
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return sortedData.slice(startIndex, endIndex);
  }, [sortedData, currentPage, pageSize, pagination]);

  const totalPages = pagination ? Math.ceil(sortedData.length / pageSize) : 1;

  const handleSort = (key: string) => {
    const column = columns.find(col => col.key === key);
    if (!column?.sortable) return;
    
    if (sortKey === key) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortKey(null);
        setSortDirection(null);
      }
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const getSortIcon = (key: string) => {
    if (sortKey !== key) return null;
    
    return sortDirection === 'asc' ? (
      <ChevronUpIcon className="h-4 w-4" />
    ) : (
      <ChevronDownIcon className="h-4 w-4" />
    );
  };

  const handleRowSelection = (item: T, isSelected: boolean) => {
    if (!onSelectionChange || !rowKey) return;
    
    if (isSelected) {
      onSelectionChange([...selectedRows, item]);
    } else {
      onSelectionChange(selectedRows.filter(row => row[rowKey] !== item[rowKey]));
    }
  };

  const isRowSelected = (item: T) => {
    if (!rowKey) return false;
    return selectedRows.some(row => row[rowKey] === item[rowKey]);
  };

  if (loading) {
    return (
      <div className={cn('space-y-4', className)}>
        {searchable && <div className="h-10 bg-gray-200 rounded animate-pulse" />}
        {isMobile && mobileCardView ? (
          <div className={spacing.gap.full}>
            {[...Array(3)].map((_, i) => (
              <div key={i} className={cn("bg-gray-100 rounded-lg animate-pulse", cards.padding, "h-32")} />
            ))}
          </div>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            <div className="h-12 bg-gray-100 border-b animate-pulse" />
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-50 border-b animate-pulse" />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Search */}
      {searchable && (
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
          <Input
            placeholder={searchPlaceholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={cn("pl-10", componentSizes.input.full)}
          />
        </div>
      )}

      {/* Mobile Cards */}
      {isMobile && mobileCardView && paginatedData.length > 0 ? (
        <div className={spacing.gap.full}>
          {paginatedData.map((item, index) => (
            <MobileCard
              key={rowKey ? String(item[rowKey]) : index}
              item={item}
              columns={columns}
              onRowClick={onRowClick}
              rowKey={rowKey}
              index={index}
              isSelected={isRowSelected(item)}
              onSelectionChange={onSelectionChange ? (item, selected) => handleRowSelection(item, selected) : undefined}
            />
          ))}
        </div>
      ) : (
        /* Desktop/Tablet Table */
        <div className={dataTable.container}>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  {onSelectionChange && rowKey && (
                    <TableHead className="w-12">
                      <input
                        type="checkbox"
                        checked={selectedRows.length === paginatedData.length && paginatedData.length > 0}
                        onChange={(e) => {
                          if (e.target.checked) {
                            onSelectionChange([...selectedRows, ...paginatedData.filter(item => !isRowSelected(item))]);
                          } else {
                            onSelectionChange(selectedRows.filter(row => !paginatedData.some(item => item[rowKey] === row[rowKey])));
                          }
                        }}
                        className="rounded border-gray-300"
                      />
                    </TableHead>
                  )}
                  {visibleColumns.map((column) => (
                    <TableHead
                      key={String(column.key)}
                      className={cn(
                        column.sortable && 'cursor-pointer hover:bg-gray-50 select-none',
                        column.hideOnMobile && dataTable.hideOnMobile,
                        column.hideOnTablet && dataTable.hideOnTablet,
                        column.className
                      )}
                      style={{ width: column.width }}
                      onClick={() => handleSort(String(column.key))}
                    >
                      <div className="flex items-center space-x-2">
                        <span>{column.title}</span>
                        {column.sortable && getSortIcon(String(column.key))}
                      </div>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData.length === 0 ? (
                  <TableRow>
                    <TableCell 
                      colSpan={visibleColumns.length + (onSelectionChange && rowKey ? 1 : 0)} 
                      className="text-center py-8 text-gray-500"
                    >
                      {emptyMessage}
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedData.map((item, index) => (
                    <TableRow
                      key={rowKey ? String(item[rowKey]) : index}
                      className={cn(
                        onRowClick && 'cursor-pointer hover:bg-gray-50',
                        isRowSelected(item) && 'bg-blue-50'
                      )}
                      onClick={() => onRowClick?.(item, index)}
                    >
                      {onSelectionChange && rowKey && (
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={isRowSelected(item)}
                            onChange={(e) => handleRowSelection(item, e.target.checked)}
                            onClick={(e) => e.stopPropagation()}
                            className="rounded border-gray-300"
                          />
                        </TableCell>
                      )}
                      {visibleColumns.map((column) => (
                        <TableCell 
                          key={String(column.key)} 
                          className={cn(
                            column.hideOnMobile && dataTable.hideOnMobile,
                            column.hideOnTablet && dataTable.hideOnTablet,
                            column.className
                          )}
                        >
                          {column.render 
                            ? column.render(item[column.key as keyof T], item, index)
                            : String(item[column.key as keyof T] || '-')
                          }
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
      
      {/* Empty state for mobile */}
      {isMobile && mobileCardView && paginatedData.length === 0 && (
        <div className={cn("text-center py-8 text-gray-500", cards.padding)}>
          {emptyMessage}
        </div>
      )}

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <div className={cn(
          "flex items-center justify-between",
          isMobile ? "flex-col space-y-3" : ""
        )}>
          <div className="text-sm text-gray-500 text-center sm:text-left">
            Showing {Math.min((currentPage - 1) * pageSize + 1, sortedData.length)} to{' '}
            {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length} results
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(currentPage - 1)}
              disabled={currentPage === 1}
              className={componentSizes.button.full}
            >
              <ChevronLeftIcon className="h-4 w-4" />
              {!isMobile && <span className="ml-1">Previous</span>}
            </Button>
            
            {!isMobile && (
              <div className="flex items-center space-x-1">
                {[...Array(Math.min(5, totalPages))].map((_, i) => {
                  const pageNumber = Math.max(1, Math.min(currentPage - 2 + i, totalPages - 4 + i));
                  return (
                    <Button
                      key={pageNumber}
                      variant={currentPage === pageNumber ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(pageNumber)}
                      className="w-8 h-8 p-0"
                    >
                      {pageNumber}
                    </Button>
                  );
                })}
              </div>
            )}
            
            {/* Mobile page indicator */}
            {isMobile && (
              <div className="px-3 py-1 bg-gray-100 rounded text-sm">
                {currentPage} / {totalPages}
              </div>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              className={componentSizes.button.full}
            >
              {!isMobile && <span className="mr-1">Next</span>}
              <ChevronRightIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}