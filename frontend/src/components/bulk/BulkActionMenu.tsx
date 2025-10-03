/**
 * BulkActionMenu Component
 * Dropdown menu for bulk actions
 */

import React, { useState, useRef, useEffect } from 'react';
import { MoreVertical, Check } from 'lucide-react';
import type { BulkAction } from '../../types/bulk';

// ==================== Props ====================

interface BulkActionMenuProps {
  actions: BulkAction[];
  onAction: (action: BulkAction) => void;
  disabled?: boolean;
}

// ==================== Component ====================

export const BulkActionMenu: React.FC<BulkActionMenuProps> = ({
  actions,
  onAction,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);
  
  const handleAction = (action: BulkAction) => {
    setIsOpen(false);
    onAction(action);
  };
  
  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="More actions"
      >
        <MoreVertical className="w-4 h-4 text-gray-600 dark:text-gray-400" />
      </button>
      
      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 z-50">
          {actions.map((action) => (
            <button
              key={action.type}
              onClick={() => handleAction(action)}
              disabled={action.disabled}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={action.disabledReason}
            >
              <span className={`w-2 h-2 rounded-full ${
                action.color === 'red' ? 'bg-red-500' :
                action.color === 'green' ? 'bg-green-500' :
                action.color === 'blue' ? 'bg-blue-500' :
                action.color === 'orange' ? 'bg-orange-500' :
                'bg-gray-500'
              }`} />
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// ==================== Quick Select Menu ====================

interface QuickSelectMenuProps {
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onSelectFiltered?: () => void;
  selectedCount: number;
  totalCount: number;
}

export const QuickSelectMenu: React.FC<QuickSelectMenuProps> = ({
  onSelectAll,
  onDeselectAll,
  onSelectFiltered,
  selectedCount,
  totalCount,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);
  
  const handleAction = (action: () => void) => {
    setIsOpen(false);
    action();
  };
  
  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
      >
        <Check className="w-4 h-4" />
        <span>Select</span>
      </button>
      
      {isOpen && (
        <div className="absolute left-0 mt-2 w-56 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 z-50">
          <button
            onClick={() => handleAction(onSelectAll)}
            className="w-full flex items-center justify-between px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <span>Select All</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ({totalCount})
            </span>
          </button>
          
          {onSelectFiltered && (
            <button
              onClick={() => handleAction(onSelectFiltered)}
              className="w-full flex items-center justify-between px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <span>Select Filtered</span>
            </button>
          )}
          
          <button
            onClick={() => handleAction(onDeselectAll)}
            disabled={selectedCount === 0}
            className="w-full flex items-center justify-between px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span>Deselect All</span>
            {selectedCount > 0 && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                ({selectedCount})
              </span>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
