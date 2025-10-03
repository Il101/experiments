/**
 * BulkToolbar Component
 * Toolbar for bulk actions on selected items
 */

import React from 'react';
import {
  X,
  Trash2,
  Tag,
  Download,
  Power,
  PowerOff,
  Copy,
  CheckSquare,
  SquareStack,
} from 'lucide-react';
import { useBulkStore } from '../../store/useBulkStore';
import type { BulkAction, BulkActionType } from '../../types/bulk';

// ==================== Props ====================

interface BulkToolbarProps {
  itemType: 'position' | 'trade' | 'alert' | 'order';
  onAction: (action: BulkActionType, selectedIds: string[]) => Promise<void>;
  position?: 'top' | 'bottom' | 'floating';
}

// ==================== Component ====================

export const BulkToolbar: React.FC<BulkToolbarProps> = ({
  itemType,
  onAction,
  position = 'bottom',
}) => {
  const {
    toolbarVisible,
    getSelectedCount,
    getSelectedIds,
    clearSelection,
    openConfirmation,
  } = useBulkStore();
  
  const selectedCount = getSelectedCount(itemType);
  
  if (!toolbarVisible || selectedCount === 0) {
    return null;
  }
  
  const selectedIds = getSelectedIds(itemType);
  
  // Define available actions based on item type
  const getActions = (): BulkAction[] => {
    const baseActions: BulkAction[] = [
      {
        type: 'export',
        label: 'Export',
        icon: 'Download',
        color: 'blue',
        requiresConfirmation: false,
      },
      {
        type: 'tag',
        label: 'Tag',
        icon: 'Tag',
        color: 'blue',
        requiresConfirmation: false,
      },
    ];
    
    if (itemType === 'position') {
      return [
        {
          type: 'close',
          label: 'Close',
          icon: 'X',
          color: 'red',
          requiresConfirmation: true,
          confirmationMessage: `Are you sure you want to close ${selectedCount} position${selectedCount !== 1 ? 's' : ''}?`,
        },
        ...baseActions,
        {
          type: 'delete',
          label: 'Delete',
          icon: 'Trash2',
          color: 'red',
          requiresConfirmation: true,
          confirmationMessage: `Are you sure you want to delete ${selectedCount} position${selectedCount !== 1 ? 's' : ''}?`,
        },
      ];
    }
    
    if (itemType === 'alert') {
      return [
        {
          type: 'enable',
          label: 'Enable',
          icon: 'Power',
          color: 'green',
          requiresConfirmation: false,
        },
        {
          type: 'disable',
          label: 'Disable',
          icon: 'PowerOff',
          color: 'orange',
          requiresConfirmation: false,
        },
        {
          type: 'duplicate',
          label: 'Duplicate',
          icon: 'Copy',
          color: 'blue',
          requiresConfirmation: false,
        },
        ...baseActions,
        {
          type: 'delete',
          label: 'Delete',
          icon: 'Trash2',
          color: 'red',
          requiresConfirmation: true,
          confirmationMessage: `Are you sure you want to delete ${selectedCount} alert${selectedCount !== 1 ? 's' : ''}?`,
        },
      ];
    }
    
    if (itemType === 'trade') {
      return [
        ...baseActions,
        {
          type: 'delete',
          label: 'Delete',
          icon: 'Trash2',
          color: 'red',
          requiresConfirmation: true,
          confirmationMessage: `Are you sure you want to delete ${selectedCount} trade${selectedCount !== 1 ? 's' : ''}?`,
        },
      ];
    }
    
    if (itemType === 'order') {
      return [
        {
          type: 'cancel',
          label: 'Cancel',
          icon: 'X',
          color: 'red',
          requiresConfirmation: true,
          confirmationMessage: `Are you sure you want to cancel ${selectedCount} order${selectedCount !== 1 ? 's' : ''}?`,
        },
        ...baseActions,
      ];
    }
    
    return baseActions;
  };
  
  const actions = getActions();
  
  const handleAction = async (action: BulkAction) => {
    if (action.requiresConfirmation) {
      openConfirmation(
        action.type,
        selectedCount,
        action.confirmationMessage || `Perform ${action.label} on ${selectedCount} items?`,
        async () => {
          await onAction(action.type, selectedIds);
        }
      );
    } else {
      await onAction(action.type, selectedIds);
    }
  };
  
  const getIcon = (iconName: string) => {
    const icons: Record<string, any> = {
      X,
      Trash2,
      Tag,
      Download,
      Power,
      PowerOff,
      Copy,
      CheckSquare,
      SquareStack,
    };
    return icons[iconName] || CheckSquare;
  };
  
  const getColorClasses = (color: string) => {
    switch (color) {
      case 'red':
        return 'bg-red-600 hover:bg-red-700 text-white';
      case 'green':
        return 'bg-green-600 hover:bg-green-700 text-white';
      case 'blue':
        return 'bg-blue-600 hover:bg-blue-700 text-white';
      case 'orange':
        return 'bg-orange-600 hover:bg-orange-700 text-white';
      case 'gray':
        return 'bg-gray-600 hover:bg-gray-700 text-white';
      default:
        return 'bg-blue-600 hover:bg-blue-700 text-white';
    }
  };
  
  const positionClasses = {
    top: 'top-0 left-0 right-0 border-b',
    bottom: 'bottom-0 left-0 right-0 border-t',
    floating: 'bottom-4 left-1/2 transform -translate-x-1/2 rounded-lg shadow-lg',
  };
  
  return (
    <div
      className={`fixed ${positionClasses[position]} z-40 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 px-4 py-3`}
    >
      <div className="flex items-center justify-between gap-4 max-w-7xl mx-auto">
        {/* Selection Info */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <CheckSquare className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
              {selectedCount} selected
            </span>
          </div>
          
          <button
            onClick={() => clearSelection(itemType)}
            className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
          >
            Clear
          </button>
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-2">
          {actions.map((action) => {
            const Icon = getIcon(action.icon);
            return (
              <button
                key={action.type}
                onClick={() => handleAction(action)}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${getColorClasses(action.color)}`}
                disabled={action.disabled}
                title={action.disabledReason}
              >
                <Icon className="w-4 h-4" />
                {action.label}
              </button>
            );
          })}
        </div>
        
        {/* Close */}
        <button
          onClick={() => clearSelection(itemType)}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
      </div>
    </div>
  );
};
