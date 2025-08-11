import * as React from "react"
import { Search, X, Filter, ChevronDown } from "lucide-react"
import { cn } from "@/lib/design-system"
import { Button } from "./button"
import { Input } from "./input"
import { Popover, PopoverContent, PopoverTrigger } from "./popover"
import { Badge } from "./badge"

export interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

export interface FilterGroup {
  key: string;
  label: string;
  options: FilterOption[];
  multiple?: boolean;
}

export interface TableFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  searchPlaceholder?: string;
  filterGroups?: FilterGroup[];
  activeFilters?: Record<string, string[]>;
  onFilterChange?: (filterKey: string, values: string[]) => void;
  onClearAllFilters?: () => void;
  className?: string;
  showFilterCount?: boolean;
}

export function TableFilters({
  searchQuery,
  onSearchChange,
  searchPlaceholder = "Search...",
  filterGroups = [],
  activeFilters = {},
  onFilterChange,
  onClearAllFilters,
  className,
  showFilterCount = true
}: TableFiltersProps) {
  const [searchFocused, setSearchFocused] = React.useState(false);
  
  const totalActiveFilters = Object.values(activeFilters).reduce(
    (count, filters) => count + filters.length, 
    0
  );

  const handleFilterToggle = (filterKey: string, value: string, multiple = false) => {
    if (!onFilterChange) return;

    const currentValues = activeFilters[filterKey] || [];
    let newValues: string[];

    if (multiple) {
      if (currentValues.includes(value)) {
        newValues = currentValues.filter(v => v !== value);
      } else {
        newValues = [...currentValues, value];
      }
    } else {
      newValues = currentValues.includes(value) ? [] : [value];
    }

    onFilterChange(filterKey, newValues);
  };

  const clearSearchAndFilters = () => {
    onSearchChange("");
    if (onClearAllFilters) {
      onClearAllFilters();
    }
  };

  return (
    <div className={cn("flex items-center gap-3 p-4 bg-background border-b", className)}>
      {/* Search Input */}
      <div className="relative flex-1 max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={searchPlaceholder}
          onFocus={() => setSearchFocused(true)}
          onBlur={() => setSearchFocused(false)}
          className={cn(
            "pl-10 pr-10 transition-all duration-200",
            searchFocused && "ring-2 ring-primary ring-offset-2",
            searchQuery && "pr-10"
          )}
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSearchChange("")}
            className="absolute right-1 top-1/2 h-6 w-6 -translate-y-1/2 p-0 hover:bg-muted"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>

      {/* Filter Groups */}
      <div className="flex items-center gap-2">
        {filterGroups.map((group) => {
          const activeValues = activeFilters[group.key] || [];
          const hasActiveFilters = activeValues.length > 0;

          return (
            <Popover key={group.key}>
              <PopoverTrigger asChild>
                <Button
                  variant={hasActiveFilters ? "secondary" : "outline"}
                  size="sm"
                  className={cn(
                    "h-9 gap-2 transition-all duration-200",
                    hasActiveFilters && "bg-primary/10 border-primary/20 text-primary hover:bg-primary/20"
                  )}
                >
                  <Filter className="h-3 w-3" />
                  <span>{group.label}</span>
                  {hasActiveFilters && showFilterCount && (
                    <Badge variant="secondary" className="ml-1 h-5 min-w-5 p-0 text-xs">
                      {activeValues.length}
                    </Badge>
                  )}
                  <ChevronDown className="h-3 w-3" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-56 p-0" align="start">
                <div className="p-3 border-b">
                  <h4 className="font-medium text-sm">{group.label}</h4>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {group.options.map((option) => {
                    const isActive = activeValues.includes(option.value);
                    
                    return (
                      <button
                        key={option.value}
                        onClick={() => handleFilterToggle(group.key, option.value, group.multiple)}
                        className={cn(
                          "w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-muted transition-colors text-left",
                          isActive && "bg-primary/10 text-primary"
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <div className={cn(
                            "h-4 w-4 rounded border-2 flex items-center justify-center transition-colors",
                            isActive 
                              ? "bg-primary border-primary text-primary-foreground" 
                              : "border-muted-foreground/30"
                          )}>
                            {isActive && (
                              <div className="h-2 w-2 bg-current rounded-sm" />
                            )}
                          </div>
                          <span className="truncate">{option.label}</span>
                        </div>
                        {option.count !== undefined && (
                          <span className="text-xs text-muted-foreground ml-2">
                            {option.count}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
                {activeValues.length > 0 && (
                  <div className="p-2 border-t">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onFilterChange?.(group.key, [])}
                      className="w-full justify-center text-xs h-7"
                    >
                      Clear {group.label}
                    </Button>
                  </div>
                )}
              </PopoverContent>
            </Popover>
          );
        })}

        {/* Clear All Filters */}
        {(totalActiveFilters > 0 || searchQuery) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearSearchAndFilters}
            className="h-9 gap-2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-3 w-3" />
            <span>Clear all</span>
            {(totalActiveFilters > 0 || searchQuery) && (
              <Badge variant="secondary" className="ml-1 h-5 min-w-5 p-0 text-xs">
                {totalActiveFilters + (searchQuery ? 1 : 0)}
              </Badge>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

export function ActiveFiltersBar({
  activeFilters = {},
  filterGroups = [],
  searchQuery,
  onFilterChange,
  onSearchChange,
  className
}: {
  activeFilters?: Record<string, string[]>;
  filterGroups?: FilterGroup[];
  searchQuery?: string;
  onFilterChange?: (filterKey: string, values: string[]) => void;
  onSearchChange?: (query: string) => void;
  className?: string;
}) {
  const hasActiveFilters = Object.values(activeFilters).some(filters => filters.length > 0);
  const hasSearchQuery = searchQuery && searchQuery.trim() !== "";

  if (!hasActiveFilters && !hasSearchQuery) {
    return null;
  }

  const removeFilter = (filterKey: string, value: string) => {
    if (!onFilterChange) return;
    const currentValues = activeFilters[filterKey] || [];
    const newValues = currentValues.filter(v => v !== value);
    onFilterChange(filterKey, newValues);
  };

  const getFilterLabel = (filterKey: string, value: string) => {
    const group = filterGroups.find(g => g.key === filterKey);
    const option = group?.options.find(o => o.value === value);
    return option?.label || value;
  };

  return (
    <div className={cn("flex items-center gap-2 px-4 py-2 bg-muted/30 border-b", className)}>
      <span className="text-sm text-muted-foreground">Active filters:</span>
      
      {hasSearchQuery && (
        <Badge 
          variant="secondary" 
          className="gap-1 pl-2 pr-1 hover:bg-secondary/80 transition-colors cursor-pointer"
          onClick={() => onSearchChange?.("")}
        >
          <Search className="h-3 w-3" />
          <span>"{searchQuery}"</span>
          <X className="h-3 w-3" />
        </Badge>
      )}

      {Object.entries(activeFilters).map(([filterKey, values]) =>
        values.map((value) => (
          <Badge
            key={`${filterKey}-${value}`}
            variant="secondary"
            className="gap-1 pl-2 pr-1 hover:bg-secondary/80 transition-colors cursor-pointer"
            onClick={() => removeFilter(filterKey, value)}
          >
            <span>{getFilterLabel(filterKey, value)}</span>
            <X className="h-3 w-3" />
          </Badge>
        ))
      )}
    </div>
  );
}