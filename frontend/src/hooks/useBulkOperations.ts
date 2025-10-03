/**
 * useBulkOperations Hook
 * Composable hook for handling bulk operations
 */

import { useState, useCallback } from 'react';
import { useBulkStore } from '../store/useBulkStore';
import type { BulkActionType, BulkOperationResult } from '../types/bulk';

// ==================== Hook ====================

export interface UseBulkOperationsOptions {
  itemType: 'position' | 'trade' | 'alert' | 'order';
  onClose?: (itemIds: string[]) => Promise<void>;
  onCancel?: (itemIds: string[]) => Promise<void>;
  onDelete?: (itemIds: string[]) => Promise<void>;
  onTag?: (itemIds: string[], tags: string[]) => Promise<void>;
  onExport?: (itemIds: string[], format: string) => Promise<void>;
  onEnable?: (itemIds: string[]) => Promise<void>;
  onDisable?: (itemIds: string[]) => Promise<void>;
  onDuplicate?: (itemIds: string[]) => Promise<void>;
}

export const useBulkOperations = (options: UseBulkOperationsOptions) => {
  const {
    itemType,
    onClose,
    onCancel,
    onDelete,
    onTag,
    onExport,
    onEnable,
    onDisable,
    onDuplicate,
  } = options;
  
  const {
    getSelectedIds,
    clearSelection,
    startOperation,
    updateOperationProgress,
    completeOperation,
    failOperation,
    addUndoableAction,
  } = useBulkStore();
  
  const [isProcessing, setIsProcessing] = useState(false);
  
  const executeOperation = useCallback(
    async (
      action: BulkActionType,
      selectedIds: string[],
      handler?: (itemIds: string[]) => Promise<void>
    ) => {
      if (!handler || selectedIds.length === 0) {
        return;
      }
      
      setIsProcessing(true);
      
      const operationId = startOperation({
        type: action,
        itemIds: selectedIds,
        itemType,
        totalItems: selectedIds.length,
        processedItems: 0,
        failedItems: 0,
        canUndo: ['close', 'delete', 'tag', 'enable', 'disable'].includes(action),
      });
      
      try {
        const results: BulkOperationResult[] = [];
        let processed = 0;
        let failed = 0;
        
        // Process items in batches
        const batchSize = 10;
        for (let i = 0; i < selectedIds.length; i += batchSize) {
          const batch = selectedIds.slice(i, i + batchSize);
          
          try {
            await handler(batch);
            
            // Mark batch as successful
            batch.forEach((id) => {
              results.push({ itemId: id, success: true });
              processed++;
            });
          } catch (error) {
            // Mark batch as failed
            batch.forEach((id) => {
              results.push({
                itemId: id,
                success: false,
                error: error instanceof Error ? error.message : 'Unknown error',
              });
              failed++;
            });
          }
          
          // Update progress
          const progress = Math.round(((i + batch.length) / selectedIds.length) * 100);
          updateOperationProgress(operationId, progress, processed, failed);
          
          // Small delay between batches
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        
        // Complete operation
        completeOperation(operationId, results);
        
        // Add to undo stack if supported
        if (['close', 'delete', 'tag', 'enable', 'disable'].includes(action)) {
          addUndoableAction({
            type: action,
            description: `${action} ${selectedIds.length} ${itemType}(s)`,
            itemIds: selectedIds,
            rollbackData: results,
            canUndo: true,
          });
        }
        
        // Clear selection
        clearSelection(itemType);
      } catch (error) {
        failOperation(
          operationId,
          error instanceof Error ? error.message : 'Operation failed'
        );
      } finally {
        setIsProcessing(false);
      }
    },
    [
      itemType,
      startOperation,
      updateOperationProgress,
      completeOperation,
      failOperation,
      addUndoableAction,
      clearSelection,
    ]
  );
  
  const handleBulkAction = useCallback(
    async (action: BulkActionType, selectedIds: string[]) => {
      switch (action) {
        case 'close':
          await executeOperation(action, selectedIds, onClose);
          break;
        case 'cancel':
          await executeOperation(action, selectedIds, onCancel);
          break;
        case 'delete':
          await executeOperation(action, selectedIds, onDelete);
          break;
        case 'tag':
          // Tag requires additional input - handled separately
          if (onTag) {
            await executeOperation(action, selectedIds, async (ids) => {
              await onTag(ids, []); // Empty tags for now
            });
          }
          break;
        case 'export':
          // Export requires format selection - handled separately
          if (onExport) {
            await executeOperation(action, selectedIds, async (ids) => {
              await onExport(ids, 'csv');
            });
          }
          break;
        case 'enable':
          await executeOperation(action, selectedIds, onEnable);
          break;
        case 'disable':
          await executeOperation(action, selectedIds, onDisable);
          break;
        case 'duplicate':
          await executeOperation(action, selectedIds, onDuplicate);
          break;
        default:
          console.warn(`Unhandled bulk action: ${action}`);
      }
    },
    [
      executeOperation,
      onClose,
      onCancel,
      onDelete,
      onTag,
      onExport,
      onEnable,
      onDisable,
      onDuplicate,
    ]
  );
  
  return {
    isProcessing,
    selectedIds: getSelectedIds(itemType),
    handleBulkAction,
    clearSelection: () => clearSelection(itemType),
  };
};
