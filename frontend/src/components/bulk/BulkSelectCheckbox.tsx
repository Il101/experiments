/**
 * BulkSelectCheckbox Component
 * Checkbox for selecting individual items
 */

import React from 'react';
import { Check, Minus } from 'lucide-react';
import { useBulkStore } from '../../store/useBulkStore';

// ==================== Props ====================

interface BulkSelectCheckboxProps {
  itemType: string;
  itemId: string;
  className?: string;
}

// ==================== Component ====================

export const BulkSelectCheckbox: React.FC<BulkSelectCheckboxProps> = ({
  itemType,
  itemId,
  className = '',
}) => {
  const { isSelected, toggleItem } = useBulkStore();
  
  const selected = isSelected(itemType, itemId);
  
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        toggleItem(itemType, itemId);
      }}
      className={`relative w-5 h-5 rounded border-2 transition-all ${
        selected
          ? 'bg-blue-600 border-blue-600'
          : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 hover:border-blue-400'
      } ${className}`}
      aria-label={selected ? 'Deselect item' : 'Select item'}
    >
      {selected && (
        <Check className="absolute inset-0 w-full h-full p-0.5 text-white" />
      )}
    </button>
  );
};

// ==================== Select All Checkbox ====================

interface BulkSelectAllCheckboxProps {
  itemType: string;
  itemIds: string[];
  className?: string;
}

export const BulkSelectAllCheckbox: React.FC<BulkSelectAllCheckboxProps> = ({
  itemType,
  itemIds,
  className = '',
}) => {
  const { getSelectedCount, selectAll, deselectAll } = useBulkStore();
  
  const selectedCount = getSelectedCount(itemType);
  const isAllSelected = selectedCount === itemIds.length && itemIds.length > 0;
  const isPartiallySelected = selectedCount > 0 && selectedCount < itemIds.length;
  
  const handleToggle = () => {
    if (isAllSelected) {
      deselectAll(itemType);
    } else {
      selectAll(itemType, itemIds);
    }
  };
  
  return (
    <button
      onClick={handleToggle}
      className={`relative w-5 h-5 rounded border-2 transition-all ${
        isAllSelected || isPartiallySelected
          ? 'bg-blue-600 border-blue-600'
          : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 hover:border-blue-400'
      } ${className}`}
      aria-label={isAllSelected ? 'Deselect all' : 'Select all'}
    >
      {isAllSelected && (
        <Check className="absolute inset-0 w-full h-full p-0.5 text-white" />
      )}
      {isPartiallySelected && !isAllSelected && (
        <Minus className="absolute inset-0 w-full h-full p-0.5 text-white" />
      )}
    </button>
  );
};
