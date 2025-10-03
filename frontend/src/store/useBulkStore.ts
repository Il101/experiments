/**
 * Bulk Operations Store
 * Zustand store for managing bulk selections and operations
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  SelectionState,
  BulkOperation,
  UndoableAction,
  BulkActionType,
  BulkOperationResult,
  BulkOperationStats,
} from '../types/bulk';

// ==================== Store State ====================

interface BulkStoreState {
  // Selection state
  selections: Map<string, SelectionState>; // key: itemType (position, trade, etc.)
  activeItemType: 'position' | 'trade' | 'alert' | 'order' | null;
  
  // Operations
  operations: BulkOperation[];
  activeOperationId: string | null;
  
  // Undo/Redo
  undoStack: UndoableAction[];
  redoStack: UndoableAction[];
  maxUndoSize: number;
  
  // UI State
  toolbarVisible: boolean;
  confirmationDialog: {
    open: boolean;
    action: BulkActionType | null;
    itemCount: number;
    message: string;
    onConfirm: (() => void) | null;
  };
  
  // Selection Actions
  selectItem: (itemType: string, itemId: string) => void;
  deselectItem: (itemType: string, itemId: string) => void;
  toggleItem: (itemType: string, itemId: string) => void;
  selectAll: (itemType: string, itemIds: string[]) => void;
  deselectAll: (itemType: string) => void;
  clearSelection: (itemType: string) => void;
  getSelectedIds: (itemType: string) => string[];
  getSelectedCount: (itemType: string) => number;
  isSelected: (itemType: string, itemId: string) => boolean;
  
  // Operation Actions
  startOperation: (operation: Omit<BulkOperation, 'id' | 'status' | 'progress' | 'startedAt'>) => string;
  updateOperationProgress: (operationId: string, progress: number, processedItems: number, failedItems: number) => void;
  completeOperation: (operationId: string, results: BulkOperationResult[]) => void;
  failOperation: (operationId: string, error: string) => void;
  cancelOperation: (operationId: string) => void;
  getOperation: (operationId: string) => BulkOperation | undefined;
  clearOperations: () => void;
  
  // Undo/Redo Actions
  addUndoableAction: (action: Omit<UndoableAction, 'id' | 'timestamp'>) => void;
  undo: () => Promise<void>;
  redo: () => Promise<void>;
  canUndo: () => boolean;
  canRedo: () => boolean;
  clearUndoStack: () => void;
  
  // UI Actions
  showToolbar: () => void;
  hideToolbar: () => void;
  toggleToolbar: () => void;
  openConfirmation: (action: BulkActionType, itemCount: number, message: string, onConfirm: () => void) => void;
  closeConfirmation: () => void;
  
  // Statistics
  getStatistics: () => BulkOperationStats;
}

// ==================== Store Implementation ====================

export const useBulkStore = create<BulkStoreState>()(
  persist(
    (set, get) => ({
      // Initial state
      selections: new Map(),
      activeItemType: null,
      operations: [],
      activeOperationId: null,
      undoStack: [],
      redoStack: [],
      maxUndoSize: 50,
      toolbarVisible: false,
      confirmationDialog: {
        open: false,
        action: null,
        itemCount: 0,
        message: '',
        onConfirm: null,
      },
      
      // Selection Actions
      selectItem: (itemType, itemId) => {
        set((state) => {
          const selections = new Map(state.selections);
          const current = selections.get(itemType) || {
            selectedIds: new Set<string>(),
            isAllSelected: false,
            selectionMode: 'none' as const,
          };
          
          current.selectedIds.add(itemId);
          current.selectionMode = current.selectedIds.size > 0 ? 'partial' : 'none';
          selections.set(itemType, current);
          
          return {
            selections,
            activeItemType: itemType as any,
            toolbarVisible: current.selectedIds.size > 0,
          };
        });
      },
      
      deselectItem: (itemType, itemId) => {
        set((state) => {
          const selections = new Map(state.selections);
          const current = selections.get(itemType);
          if (!current) return state;
          
          current.selectedIds.delete(itemId);
          current.isAllSelected = false;
          current.selectionMode = current.selectedIds.size > 0 ? 'partial' : 'none';
          selections.set(itemType, current);
          
          return {
            selections,
            toolbarVisible: current.selectedIds.size > 0,
          };
        });
      },
      
      toggleItem: (itemType, itemId) => {
        const isSelected = get().isSelected(itemType, itemId);
        if (isSelected) {
          get().deselectItem(itemType, itemId);
        } else {
          get().selectItem(itemType, itemId);
        }
      },
      
      selectAll: (itemType, itemIds) => {
        set((state) => {
          const selections = new Map(state.selections);
          selections.set(itemType, {
            selectedIds: new Set(itemIds),
            isAllSelected: true,
            selectionMode: 'all',
          });
          
          return {
            selections,
            activeItemType: itemType as any,
            toolbarVisible: itemIds.length > 0,
          };
        });
      },
      
      deselectAll: (itemType) => {
        get().clearSelection(itemType);
      },
      
      clearSelection: (itemType) => {
        set((state) => {
          const selections = new Map(state.selections);
          selections.set(itemType, {
            selectedIds: new Set<string>(),
            isAllSelected: false,
            selectionMode: 'none',
          });
          
          return {
            selections,
            toolbarVisible: false,
          };
        });
      },
      
      getSelectedIds: (itemType) => {
        const selection = get().selections.get(itemType);
        return selection ? Array.from(selection.selectedIds) : [];
      },
      
      getSelectedCount: (itemType) => {
        const selection = get().selections.get(itemType);
        return selection ? selection.selectedIds.size : 0;
      },
      
      isSelected: (itemType, itemId) => {
        const selection = get().selections.get(itemType);
        return selection ? selection.selectedIds.has(itemId) : false;
      },
      
      // Operation Actions
      startOperation: (operation) => {
        const id = `bulk_op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const newOperation: BulkOperation = {
          ...operation,
          id,
          status: 'in_progress',
          progress: 0,
          processedItems: 0,
          failedItems: 0,
          startedAt: new Date().toISOString(),
        };
        
        set((state) => ({
          operations: [...state.operations, newOperation],
          activeOperationId: id,
        }));
        
        return id;
      },
      
      updateOperationProgress: (operationId, progress, processedItems, failedItems) => {
        set((state) => ({
          operations: state.operations.map((op) =>
            op.id === operationId
              ? { ...op, progress, processedItems, failedItems }
              : op
          ),
        }));
      },
      
      completeOperation: (operationId, results) => {
        set((state) => ({
          operations: state.operations.map((op) =>
            op.id === operationId
              ? {
                  ...op,
                  status: 'completed' as const,
                  progress: 100,
                  completedAt: new Date().toISOString(),
                  results,
                }
              : op
          ),
          activeOperationId: null,
        }));
      },
      
      failOperation: (operationId, error) => {
        set((state) => ({
          operations: state.operations.map((op) =>
            op.id === operationId
              ? {
                  ...op,
                  status: 'failed' as const,
                  completedAt: new Date().toISOString(),
                  error,
                }
              : op
          ),
          activeOperationId: null,
        }));
      },
      
      cancelOperation: (operationId) => {
        set((state) => ({
          operations: state.operations.map((op) =>
            op.id === operationId
              ? {
                  ...op,
                  status: 'cancelled' as const,
                  completedAt: new Date().toISOString(),
                }
              : op
          ),
          activeOperationId: null,
        }));
      },
      
      getOperation: (operationId) => {
        return get().operations.find((op) => op.id === operationId);
      },
      
      clearOperations: () => {
        set({ operations: [], activeOperationId: null });
      },
      
      // Undo/Redo Actions
      addUndoableAction: (action) => {
        set((state) => {
          const id = `undo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          const newAction: UndoableAction = {
            ...action,
            id,
            timestamp: new Date().toISOString(),
          };
          
          const undoStack = [...state.undoStack, newAction];
          if (undoStack.length > state.maxUndoSize) {
            undoStack.shift();
          }
          
          return {
            undoStack,
            redoStack: [], // Clear redo stack when new action is added
          };
        });
      },
      
      undo: async () => {
        const state = get();
        if (state.undoStack.length === 0) return;
        
        const action = state.undoStack[state.undoStack.length - 1];
        
        // TODO: Implement actual undo logic based on action type
        console.log('Undoing action:', action);
        
        set((state) => ({
          undoStack: state.undoStack.slice(0, -1),
          redoStack: [...state.redoStack, action],
        }));
      },
      
      redo: async () => {
        const state = get();
        if (state.redoStack.length === 0) return;
        
        const action = state.redoStack[state.redoStack.length - 1];
        
        // TODO: Implement actual redo logic based on action type
        console.log('Redoing action:', action);
        
        set((state) => ({
          undoStack: [...state.undoStack, action],
          redoStack: state.redoStack.slice(0, -1),
        }));
      },
      
      canUndo: () => {
        return get().undoStack.length > 0;
      },
      
      canRedo: () => {
        return get().redoStack.length > 0;
      },
      
      clearUndoStack: () => {
        set({ undoStack: [], redoStack: [] });
      },
      
      // UI Actions
      showToolbar: () => {
        set({ toolbarVisible: true });
      },
      
      hideToolbar: () => {
        set({ toolbarVisible: false });
      },
      
      toggleToolbar: () => {
        set((state) => ({ toolbarVisible: !state.toolbarVisible }));
      },
      
      openConfirmation: (action, itemCount, message, onConfirm) => {
        set({
          confirmationDialog: {
            open: true,
            action,
            itemCount,
            message,
            onConfirm,
          },
        });
      },
      
      closeConfirmation: () => {
        set({
          confirmationDialog: {
            open: false,
            action: null,
            itemCount: 0,
            message: '',
            onConfirm: null,
          },
        });
      },
      
      // Statistics
      getStatistics: () => {
        const state = get();
        const completedOps = state.operations.filter((op) => op.status === 'completed');
        const failedOps = state.operations.filter((op) => op.status === 'failed');
        
        const totalProcessed = completedOps.reduce((sum, op) => sum + op.processedItems, 0);
        const totalDuration = completedOps.reduce((sum, op) => {
          if (op.completedAt && op.startedAt) {
            return sum + (new Date(op.completedAt).getTime() - new Date(op.startedAt).getTime());
          }
          return sum;
        }, 0);
        
        const actionCounts = state.operations.reduce((acc, op) => {
          acc[op.type] = (acc[op.type] || 0) + 1;
          return acc;
        }, {} as Record<BulkActionType, number>);
        
        const mostUsedAction = Object.entries(actionCounts).sort((a, b) => b[1] - a[1])[0]?.[0] as BulkActionType;
        
        return {
          totalOperations: state.operations.length,
          successfulOperations: completedOps.length,
          failedOperations: failedOps.length,
          totalItemsProcessed: totalProcessed,
          averageProcessingTime: completedOps.length > 0 ? totalDuration / completedOps.length : 0,
          mostUsedAction,
          recentOperations: state.operations.slice(-10).reverse(),
        };
      },
    }),
    {
      name: 'bulk-operations-storage',
      partialize: (state) => ({
        operations: state.operations.filter((op) => op.status === 'completed'), // Only persist completed
        undoStack: state.undoStack.slice(-20), // Keep last 20 undo actions
      }),
    }
  )
);
