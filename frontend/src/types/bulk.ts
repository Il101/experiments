/**
 * Bulk Operations Type Definitions
 * Types for multi-select and bulk actions
 */

// ==================== Selection Types ====================

export interface SelectionState {
  selectedIds: Set<string>;
  isAllSelected: boolean;
  selectionMode: 'none' | 'partial' | 'all';
}

export interface SelectableItem {
  id: string;
  type: 'position' | 'trade' | 'alert' | 'order';
  data: any;
}

// ==================== Bulk Action Types ====================

export type BulkActionType =
  | 'close'           // Close positions
  | 'cancel'          // Cancel orders
  | 'tag'             // Add/remove tags
  | 'export'          // Export selected items
  | 'delete'          // Delete items
  | 'enable'          // Enable alerts
  | 'disable'         // Disable alerts
  | 'duplicate'       // Duplicate items
  | 'update_status'   // Update status
  | 'update_tags'     // Bulk update tags
  | 'update_notes';   // Bulk update notes

export interface BulkAction {
  type: BulkActionType;
  label: string;
  icon: string;
  color: 'blue' | 'green' | 'red' | 'orange' | 'gray';
  requiresConfirmation: boolean;
  confirmationMessage?: string;
  disabled?: boolean;
  disabledReason?: string;
}

// ==================== Bulk Operation Types ====================

export interface BulkOperation {
  id: string;
  type: BulkActionType;
  itemIds: string[];
  itemType: 'position' | 'trade' | 'alert' | 'order';
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  totalItems: number;
  processedItems: number;
  failedItems: number;
  startedAt: string;
  completedAt?: string;
  error?: string;
  results?: BulkOperationResult[];
  canUndo: boolean;
}

export interface BulkOperationResult {
  itemId: string;
  success: boolean;
  error?: string;
  rollbackData?: any; // Data needed to undo the operation
}

// ==================== Undo/Redo Types ====================

export interface UndoableAction {
  id: string;
  type: BulkActionType;
  timestamp: string;
  description: string;
  itemIds: string[];
  rollbackData: any;
  canUndo: boolean;
}

export interface UndoStack {
  actions: UndoableAction[];
  currentIndex: number;
  maxSize: number;
}

// ==================== Bulk Update Types ====================

export interface BulkUpdateRequest {
  itemIds: string[];
  updates: Record<string, any>;
  validateBefore?: boolean;
}

export interface BulkClosePositionsRequest {
  positionIds: string[];
  reason?: string;
  closePrice?: number;
}

export interface BulkTagUpdateRequest {
  itemIds: string[];
  tagsToAdd?: string[];
  tagsToRemove?: string[];
}

export interface BulkExportRequest {
  itemIds: string[];
  format: 'csv' | 'json' | 'excel' | 'pdf';
  fields?: string[];
  filename?: string;
}

// ==================== Progress Types ====================

export interface BulkProgressUpdate {
  operationId: string;
  progress: number;
  processedItems: number;
  failedItems: number;
  currentItem?: string;
  message?: string;
}

// ==================== Filter Integration ====================

export interface BulkSelectionFilter {
  applyFilters: boolean;
  filterConfig?: any;
  excludeIds?: string[];
}

// ==================== Statistics ====================

export interface BulkOperationStats {
  totalOperations: number;
  successfulOperations: number;
  failedOperations: number;
  totalItemsProcessed: number;
  averageProcessingTime: number; // milliseconds
  mostUsedAction: BulkActionType;
  recentOperations: BulkOperation[];
}

// ==================== UI State ====================

export interface BulkToolbarState {
  visible: boolean;
  position: 'top' | 'bottom' | 'floating';
  actions: BulkAction[];
  selectedCount: number;
}

export interface ConfirmationDialogState {
  open: boolean;
  action: BulkActionType;
  itemCount: number;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

// ==================== API Types ====================

export interface BulkOperationResponse {
  success: boolean;
  operationId: string;
  totalItems: number;
  successfulItems: number;
  failedItems: number;
  results: BulkOperationResult[];
  duration: number; // milliseconds
}

export interface BulkValidationResponse {
  valid: boolean;
  errors: Array<{
    itemId: string;
    error: string;
  }>;
  warnings: Array<{
    itemId: string;
    warning: string;
  }>;
}
