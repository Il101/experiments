/**
 * Quick Filters Toolbar
 * 1-click filter buttons for common filters
 */

import React, { useState } from 'react';
import { Star, StarOff, Filter, Plus, ChevronDown, Settings } from 'lucide-react';
import { useFilterStore } from '../../store/useFilterStore';
import type { FilterContext } from '../../types/filters';

interface QuickFiltersToolbarProps {
  context: FilterContext;
  onCreateQuickFilter?: () => void;
  className?: string;
}

export const QuickFiltersToolbar: React.FC<QuickFiltersToolbarProps> = ({
  context,
  onCreateQuickFilter,
  className = '',
}) => {
  const {
    getQuickFilters,
    activeFilters,
    setActiveFilter,
    toggleQuickFilter,
    getAllFilters,
  } = useFilterStore();

  const [showAllFilters, setShowAllFilters] = useState(false);
  const quickFilters = getQuickFilters();
  const activeFilterId = activeFilters[context];
  const allFilters = getAllFilters();

  const handleFilterClick = (filterId: string) => {
    // Toggle: if already active, clear it; otherwise, activate it
    if (activeFilterId === filterId) {
      setActiveFilter(context, null);
    } else {
      setActiveFilter(context, filterId);
    }
  };

  const handleToggleQuickFilter = (filterId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    toggleQuickFilter(filterId);
  };

  if (quickFilters.length === 0 && !onCreateQuickFilter) {
    return null;
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Quick Filter Label */}
      <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
        <Filter className="w-4 h-4" />
        <span className="font-medium">Quick Filters:</span>
      </div>

      {/* Quick Filter Buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        {quickFilters.map((filter) => {
          const isActive = activeFilterId === filter.id;

          return (
            <button
              key={filter.id}
              onClick={() => handleFilterClick(filter.id)}
              className={`
                group relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                transition-all duration-200
                ${
                  isActive
                    ? 'bg-blue-500 text-white shadow-md scale-105'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                }
              `}
            >
              {filter.name}
              
              {/* Pin/Unpin Button */}
              <button
                onClick={(e) => handleToggleQuickFilter(filter.id, e)}
                className={`
                  opacity-0 group-hover:opacity-100 transition-opacity
                  p-0.5 rounded hover:bg-white/20
                `}
                title="Remove from quick filters"
              >
                <StarOff className="w-3 h-3" />
              </button>

              {/* Active Indicator */}
              {isActive && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-green-400 rounded-full border-2 border-white dark:border-gray-900" />
              )}
            </button>
          );
        })}

        {/* Show All Filters Dropdown */}
        {allFilters.length > quickFilters.length && (
          <div className="relative">
            <button
              onClick={() => setShowAllFilters(!showAllFilters)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>More</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showAllFilters ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {showAllFilters && (
              <>
                {/* Backdrop */}
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowAllFilters(false)}
                />

                {/* Menu */}
                <div className="absolute top-full left-0 mt-2 w-64 max-h-80 overflow-y-auto bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-20">
                  <div className="p-2 space-y-1">
                    {allFilters
                      .filter((f) => !f.isQuickFilter)
                      .map((filter) => (
                        <button
                          key={filter.id}
                          onClick={() => {
                            handleFilterClick(filter.id);
                            setShowAllFilters(false);
                          }}
                          className="w-full flex items-center justify-between px-3 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors group"
                        >
                          <span className="flex-1 text-gray-700 dark:text-gray-300">
                            {filter.name}
                          </span>
                          
                          {/* Add to Quick Filters */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleQuickFilter(filter.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-all"
                            title="Add to quick filters"
                          >
                            <Star className="w-4 h-4 text-yellow-500" />
                          </button>
                        </button>
                      ))}

                    {allFilters.filter((f) => !f.isQuickFilter).length === 0 && (
                      <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400 text-center">
                        All filters are already quick filters
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Create Quick Filter Button */}
        {onCreateQuickFilter && (
          <button
            onClick={onCreateQuickFilter}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Create Filter</span>
          </button>
        )}

        {/* Settings Button */}
        <button
          className="p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          title="Filter settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>

      {/* No Quick Filters Message */}
      {quickFilters.length === 0 && (
        <div className="text-sm text-gray-500 dark:text-gray-400 italic">
          No quick filters yet. Create one to get started.
        </div>
      )}
    </div>
  );
};
