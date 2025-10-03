/**
 * Applied Filters Display
 * Shows currently active filters as removable chips
 */

import React from 'react';
import { X, Filter, Edit2, XCircle } from 'lucide-react';
import { useFilterStore } from '../../store/useFilterStore';
import type { FilterContext, Filter as FilterType } from '../../types/filters';

interface AppliedFiltersDisplayProps {
  context: FilterContext;
  onEditFilter?: (filter: FilterType) => void;
  className?: string;
}

export const AppliedFiltersDisplay: React.FC<AppliedFiltersDisplayProps> = ({
  context,
  onEditFilter,
  className = '',
}) => {
  const { getActiveFilter, clearActiveFilter } = useFilterStore();
  const activeFilter = getActiveFilter(context);

  if (!activeFilter) {
    return null;
  }

  const handleRemove = () => {
    clearActiveFilter(context);
  };

  const handleEdit = () => {
    if (onEditFilter && activeFilter) {
      onEditFilter(activeFilter);
    }
  };

  // Get filter summary (number of conditions)
  const countConditions = (filter: FilterType): number => {
    let count = filter.rootGroup.conditions.length;
    if (filter.rootGroup.groups) {
      filter.rootGroup.groups.forEach((group) => {
        count += group.conditions.length;
        if (group.groups) {
          group.groups.forEach((nestedGroup) => {
            count += nestedGroup.conditions.length;
          });
        }
      });
    }
    return count;
  };

  const conditionCount = countConditions(activeFilter);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Label */}
      <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
        <Filter className="w-4 h-4" />
        <span className="font-medium">Active Filter:</span>
      </div>

      {/* Filter Chip */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg">
        {/* Filter Info */}
        <div className="flex items-center gap-2">
          <span className="font-medium text-blue-700 dark:text-blue-300">
            {activeFilter.name}
          </span>
          <span className="text-xs text-blue-600 dark:text-blue-400">
            {conditionCount} condition{conditionCount !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 ml-1 border-l border-blue-200 dark:border-blue-800 pl-2">
          {onEditFilter && (
            <button
              onClick={handleEdit}
              className="p-1 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50 rounded transition-colors"
              title="Edit filter"
            >
              <Edit2 className="w-3 h-3" />
            </button>
          )}
          <button
            onClick={handleRemove}
            className="p-1 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50 rounded transition-colors"
            title="Remove filter"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
};

// ===== APPLIED FILTERS WITH DETAILS =====
interface AppliedFiltersWithDetailsProps {
  context: FilterContext;
  onEditFilter?: (filter: FilterType) => void;
  onRemoveCondition?: (conditionId: string) => void;
  className?: string;
}

export const AppliedFiltersWithDetails: React.FC<AppliedFiltersWithDetailsProps> = ({
  context,
  onEditFilter,
  onRemoveCondition,
  className = '',
}) => {
  const { getActiveFilter, clearActiveFilter } = useFilterStore();
  const activeFilter = getActiveFilter(context);

  if (!activeFilter) {
    return (
      <div className={`p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="text-center text-gray-500 dark:text-gray-400 text-sm">
          <Filter className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No filters applied</p>
        </div>
      </div>
    );
  }

  const handleClearAll = () => {
    clearActiveFilter(context);
  };

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-blue-500" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            Applied Filters
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {onEditFilter && (
            <button
              onClick={() => onEditFilter(activeFilter)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
            >
              <Edit2 className="w-4 h-4" />
              <span>Edit</span>
            </button>
          )}
          <button
            onClick={handleClearAll}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
          >
            <XCircle className="w-4 h-4" />
            <span>Clear All</span>
          </button>
        </div>
      </div>

      {/* Filter Details */}
      <div className="p-4">
        {/* Filter Name & Description */}
        <div className="mb-4">
          <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
            {activeFilter.name}
          </h4>
          {activeFilter.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {activeFilter.description}
            </p>
          )}
        </div>

        {/* Logic Indicator */}
        <div className="mb-3">
          <span className={`
            inline-block px-3 py-1 rounded-lg text-sm font-medium
            ${activeFilter.rootGroup.logic === 'AND' 
              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' 
              : 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'}
          `}>
            Match {activeFilter.rootGroup.logic === 'AND' ? 'ALL' : 'ANY'} conditions
          </span>
        </div>

        {/* Conditions */}
        <div className="space-y-2">
          {activeFilter.rootGroup.conditions.map((condition) => (
            <div
              key={condition.id}
              className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {condition.field}
                </span>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {condition.operator}
                </span>
                <span className="text-sm font-mono text-gray-900 dark:text-gray-100 truncate">
                  {Array.isArray(condition.value)
                    ? condition.value.join(', ')
                    : String(condition.value)}
                </span>
              </div>

              {onRemoveCondition && (
                <button
                  onClick={() => onRemoveCondition(condition.id)}
                  className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  title="Remove condition"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}

          {/* Nested Groups */}
          {activeFilter.rootGroup.groups?.map((group) => (
            <div key={group.id} className="ml-4 pl-4 border-l-2 border-gray-300 dark:border-gray-700">
              <div className="mb-2">
                <span className={`
                  inline-block px-2 py-0.5 rounded text-xs font-medium
                  ${group.logic === 'AND' 
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' 
                    : 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'}
                `}>
                  {group.logic}
                </span>
              </div>
              {group.conditions.map((condition) => (
                <div
                  key={condition.id}
                  className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg mb-2"
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0 text-sm">
                    <span className="font-medium text-gray-700 dark:text-gray-300">
                      {condition.field}
                    </span>
                    <span className="text-gray-500 dark:text-gray-400">
                      {condition.operator}
                    </span>
                    <span className="font-mono text-gray-900 dark:text-gray-100 truncate">
                      {Array.isArray(condition.value)
                        ? condition.value.join(', ')
                        : String(condition.value)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
