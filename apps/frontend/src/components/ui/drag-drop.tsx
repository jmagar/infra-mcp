import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/design-system"
import { GripVertical, Move, Target, Check, X } from "lucide-react"

// Drag and Drop Context
interface DragDropContextType {
  draggedItem: any | null;
  draggedType: string | null;
  isDragging: boolean;
  dragOverTarget: string | null;
  setDraggedItem: (item: any, type?: string) => void;
  clearDraggedItem: () => void;
  setDragOverTarget: (target: string | null) => void;
  onDrop?: (draggedItem: any, targetId: string, targetType: string) => void;
}

const DragDropContext = React.createContext<DragDropContextType | null>(null);

export function DragDropProvider({ 
  children, 
  onDrop 
}: { 
  children: React.ReactNode;
  onDrop?: (draggedItem: any, targetId: string, targetType: string) => void;
}) {
  const [draggedItem, setDraggedItemState] = React.useState<any | null>(null);
  const [draggedType, setDraggedType] = React.useState<string | null>(null);
  const [isDragging, setIsDragging] = React.useState(false);
  const [dragOverTarget, setDragOverTarget] = React.useState<string | null>(null);

  const setDraggedItem = React.useCallback((item: any, type?: string) => {
    setDraggedItemState(item);
    setDraggedType(type || null);
    setIsDragging(!!item);
  }, []);

  const clearDraggedItem = React.useCallback(() => {
    setDraggedItemState(null);
    setDraggedType(null);
    setIsDragging(false);
    setDragOverTarget(null);
  }, []);

  const value: DragDropContextType = {
    draggedItem,
    draggedType,
    isDragging,
    dragOverTarget,
    setDraggedItem,
    clearDraggedItem,
    setDragOverTarget,
    onDrop
  };

  return (
    <DragDropContext.Provider value={value}>
      {children}
    </DragDropContext.Provider>
  );
}

export function useDragDrop() {
  const context = React.useContext(DragDropContext);
  if (!context) {
    throw new Error('useDragDrop must be used within a DragDropProvider');
  }
  return context;
}

// Draggable Item Variants
const draggableVariants = cva([
  "relative cursor-move select-none transition-all duration-200",
  "hover:shadow-lg hover:scale-[1.02]",
  "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
  "active:scale-95 active:cursor-grabbing"
], {
  variants: {
    state: {
      idle: "shadow-sm",
      dragging: [
        "opacity-50 shadow-xl scale-105 rotate-2 z-50",
        "ring-2 ring-primary ring-offset-2"
      ],
      dragOver: "ring-2 ring-orange-400 ring-offset-2"
    },
    variant: {
      card: "glass rounded-lg p-4 border border-border/50",
      list: "glass rounded-md p-3 border-l-4 border-primary/20",
      compact: "glass rounded p-2 text-sm"
    }
  },
  defaultVariants: {
    state: "idle",
    variant: "card"
  }
});

export interface DraggableProps extends 
  React.HTMLAttributes<HTMLDivElement>,
  VariantProps<typeof draggableVariants> {
  dragId: string;
  dragType: string;
  dragData: any;
  disabled?: boolean;
  showHandle?: boolean;
}

export function Draggable({
  dragId,
  dragType,
  dragData,
  disabled = false,
  showHandle = true,
  state,
  variant,
  className,
  children,
  ...props
}: DraggableProps) {
  const { 
    draggedItem, 
    isDragging, 
    setDraggedItem, 
    clearDraggedItem 
  } = useDragDrop();

  const isCurrentlyDragging = draggedItem?.id === dragId;
  const currentState = isCurrentlyDragging ? "dragging" : state;

  const handleDragStart = (e: React.DragEvent) => {
    if (disabled) {
      e.preventDefault();
      return;
    }

    setDraggedItem({ id: dragId, type: dragType, data: dragData }, dragType);
    
    // Set drag image
    const dragImage = e.currentTarget.cloneNode(true) as HTMLElement;
    dragImage.style.transform = "rotate(5deg)";
    dragImage.style.opacity = "0.8";
    e.dataTransfer.setDragImage(dragImage, 0, 0);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnd = () => {
    clearDraggedItem();
  };

  return (
    <div
      draggable={!disabled}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={cn(
        draggableVariants({ state: currentState, variant }),
        disabled && "opacity-50 cursor-not-allowed",
        isDragging && !isCurrentlyDragging && "pointer-events-none",
        className
      )}
      {...props}
    >
      {showHandle && !disabled && (
        <div className="absolute top-2 right-2 opacity-40 hover:opacity-80 transition-opacity">
          <GripVertical className="h-4 w-4" />
        </div>
      )}
      
      <div className={cn(
        "relative",
        isCurrentlyDragging && "pointer-events-none"
      )}>
        {children}
      </div>

      {/* Dragging Indicator */}
      {isCurrentlyDragging && (
        <div className="absolute inset-0 flex items-center justify-center glass-ultra rounded-lg">
          <div className="flex items-center gap-2 text-primary">
            <Move className="h-5 w-5 animate-pulse" />
            <span className="text-sm font-medium">Moving...</span>
          </div>
        </div>
      )}
    </div>
  );
}

// Drop Zone Variants
const dropZoneVariants = cva([
  "relative transition-all duration-200 border-2 border-dashed rounded-lg",
  "flex flex-col items-center justify-center gap-3 p-6 min-h-24"
], {
  variants: {
    state: {
      idle: "border-border/30 text-muted-foreground hover:border-border/60",
      dragOver: [
        "border-primary bg-primary/5 text-primary",
        "shadow-inner shadow-primary/20 scale-[1.02]"
      ],
      canDrop: "border-green-400 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400",
      cannotDrop: "border-red-400 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400"
    },
    size: {
      sm: "min-h-16 p-4 text-sm",
      md: "min-h-24 p-6",
      lg: "min-h-32 p-8 text-lg"
    },
    orientation: {
      vertical: "flex-col",
      horizontal: "flex-row"
    }
  },
  defaultVariants: {
    state: "idle",
    size: "md",
    orientation: "vertical"
  }
});

export interface DropZoneProps extends 
  React.HTMLAttributes<HTMLDivElement>,
  VariantProps<typeof dropZoneVariants> {
  dropId: string;
  dropType: string | string[];
  onDrop?: (draggedItem: any) => void;
  canDrop?: (draggedItem: any) => boolean;
  emptyMessage?: string;
  dragOverMessage?: string;
}

export function DropZone({
  dropId,
  dropType,
  onDrop,
  canDrop,
  emptyMessage = "Drop items here",
  dragOverMessage = "Drop to add",
  state,
  size,
  orientation,
  className,
  children,
  ...props
}: DropZoneProps) {
  const {
    draggedItem,
    draggedType,
    isDragging,
    dragOverTarget,
    setDragOverTarget,
    onDrop: globalOnDrop
  } = useDragDrop();

  const [isLocalDragOver, setIsLocalDragOver] = React.useState(false);
  
  const acceptedTypes = Array.isArray(dropType) ? dropType : [dropType];
  const canAcceptDrop = !draggedType || acceptedTypes.includes(draggedType);
  const canDropHere = !canDrop || (draggedItem && canDrop(draggedItem));
  
  const isValidDrop = canAcceptDrop && canDropHere;
  const isDraggedOver = dragOverTarget === dropId || isLocalDragOver;

  let currentState = state;
  if (isDragging && isDraggedOver) {
    currentState = isValidDrop ? "canDrop" : "cannotDrop";
  } else if (isDragging) {
    currentState = "dragOver";
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (isValidDrop) {
      e.dataTransfer.dropEffect = "move";
      setDragOverTarget(dropId);
      setIsLocalDragOver(true);
    } else {
      e.dataTransfer.dropEffect = "none";
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX;
    const y = e.clientY;
    
    if (x < rect.left || x >= rect.right || y < rect.top || y >= rect.bottom) {
      setDragOverTarget(null);
      setIsLocalDragOver(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    
    if (!draggedItem || !isValidDrop) {
      return;
    }

    // Call local onDrop first
    if (onDrop) {
      onDrop(draggedItem);
    }

    // Then call global onDrop
    if (globalOnDrop) {
      globalOnDrop(draggedItem, dropId, Array.isArray(dropType) ? dropType[0] : dropType);
    }

    setDragOverTarget(null);
    setIsLocalDragOver(false);
  };

  const getIcon = () => {
    if (isDragging && isDraggedOver) {
      return isValidDrop ? (
        <Check className="h-6 w-6 text-green-500" />
      ) : (
        <X className="h-6 w-6 text-red-500" />
      );
    }
    return <Target className="h-6 w-6" />;
  };

  const getMessage = () => {
    if (isDragging && isDraggedOver) {
      return isValidDrop ? dragOverMessage : "Cannot drop here";
    }
    return emptyMessage;
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(dropZoneVariants({ state: currentState, size, orientation }), className)}
      {...props}
    >
      {children || (
        <>
          {getIcon()}
          <span className="text-center font-medium">
            {getMessage()}
          </span>
        </>
      )}

      {/* Drop Effect Overlay */}
      {isDragging && isDraggedOver && (
        <div className={cn(
          "absolute inset-0 rounded-lg pointer-events-none",
          "flex items-center justify-center",
          "bg-gradient-to-br transition-all duration-300",
          isValidDrop 
            ? "from-green-500/10 to-blue-500/10" 
            : "from-red-500/10 to-red-500/5"
        )}>
          <div className={cn(
            "text-2xl animate-bounce",
            isValidDrop ? "text-green-500" : "text-red-500"
          )}>
            {isValidDrop ? "✓" : "✗"}
          </div>
        </div>
      )}
    </div>
  );
}

// Sortable List Component
export interface SortableListProps {
  items: any[];
  onReorder: (items: any[]) => void;
  renderItem: (item: any, index: number) => React.ReactNode;
  itemKey: (item: any) => string;
  className?: string;
  itemClassName?: string;
  gap?: "sm" | "md" | "lg";
}

export function SortableList({
  items,
  onReorder,
  renderItem,
  itemKey,
  className,
  itemClassName,
  gap = "md"
}: SortableListProps) {
  const gapClasses = {
    sm: "gap-2",
    md: "gap-4",
    lg: "gap-6"
  };

  const handleDrop = (draggedItem: any, targetIndex: number) => {
    const currentIndex = items.findIndex(item => itemKey(item) === itemKey(draggedItem.data));
    if (currentIndex === -1 || currentIndex === targetIndex) return;

    const newItems = [...items];
    const [removed] = newItems.splice(currentIndex, 1);
    newItems.splice(targetIndex, 0, removed);
    onReorder(newItems);
  };

  return (
    <div className={cn("flex flex-col", gapClasses[gap], className)}>
      {items.map((item, index) => (
        <div key={itemKey(item)} className="relative">
          <Draggable
            dragId={itemKey(item)}
            dragType="sortable-item"
            dragData={item}
            variant="list"
            className={itemClassName}
          >
            {renderItem(item, index)}
          </Draggable>
          
          {/* Drop Zone Between Items */}
          <DropZone
            dropId={`sort-${index}`}
            dropType="sortable-item"
            onDrop={(draggedItem) => handleDrop(draggedItem, index)}
            className="absolute -bottom-2 left-0 right-0 h-4 min-h-4 opacity-0 border-0"
            emptyMessage=""
            dragOverMessage=""
          />
        </div>
      ))}
      
      {/* Drop Zone at End */}
      <DropZone
        dropId={`sort-end`}
        dropType="sortable-item"
        onDrop={(draggedItem) => handleDrop(draggedItem, items.length)}
        size="sm"
        emptyMessage="Drop to add at end"
      />
    </div>
  );
}

// Bulk Actions Component
export interface BulkActionsProps {
  selectedItems: any[];
  onClearSelection: () => void;
  children: React.ReactNode;
  className?: string;
}

export function BulkActions({
  selectedItems,
  onClearSelection,
  children,
  className
}: BulkActionsProps) {
  const { isDragging } = useDragDrop();

  if (selectedItems.length === 0 && !isDragging) {
    return null;
  }

  return (
    <div className={cn(
      "fixed bottom-6 left-1/2 -translate-x-1/2 z-50",
      "glass-ultra border border-border/50 rounded-lg shadow-2xl",
      "flex items-center gap-3 px-4 py-3",
      "animate-in slide-in-from-bottom-2 fade-in-0 duration-300",
      className
    )}>
      {selectedItems.length > 0 && (
        <>
          <span className="text-sm font-medium">
            {selectedItems.length} selected
          </span>
          <div className="h-4 w-px bg-border" />
          {children}
          <div className="h-4 w-px bg-border" />
          <button
            onClick={onClearSelection}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Clear
          </button>
        </>
      )}
    </div>
  );
}