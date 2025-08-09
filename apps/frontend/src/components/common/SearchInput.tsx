/**
 * Search Input Component
 * Provides a consistent search interface with debouncing
 */

import React, { useState, useEffect } from 'react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Search, X } from 'lucide-react';

interface SearchInputProps {
  placeholder?: string;
  onSearch: (query: string) => void;
  debounceMs?: number;
  className?: string;
  initialValue?: string;
}

export function SearchInput({
  placeholder = 'Search...',
  onSearch,
  debounceMs = 300,
  className = '',
  initialValue = '',
}: SearchInputProps) {
  const [query, setQuery] = useState(initialValue);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(query);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [query, onSearch, debounceMs]);

  const handleClear = () => {
    setQuery('');
  };

  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        type="text"
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="pl-9 pr-9"
      />
      {query && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClear}
          className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0 hover:bg-transparent"
        >
          <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
        </Button>
      )}
    </div>
  );
}