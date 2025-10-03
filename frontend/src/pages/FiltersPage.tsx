/**
 * Filters Demo Page
 * Showcase all filter components
 */

import React, { useState } from 'react';
import { Filter as FilterIcon } from 'lucide-react';
import {
  FilterBuilder,
  QuickFiltersToolbar,
  FilterPresetSelector,
  FilterHistoryPanel,
  AppliedFiltersDisplay,
  AppliedFiltersWithDetails,
} from '../components/filters';
import type { Filter, FilterContext } from '../types/filters';

export const FiltersPage: React.FC = () => {
  const [showBuilder, setShowBuilder] = useState(false);
  const [context] = useState<FilterContext>('positions');

  const handleFilterSave = (filter: Filter) => {
    console.log('Filter saved:', filter);
    setShowBuilder(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
              <FilterIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Advanced Filtering System
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Create, save, and manage complex filters with AND/OR logic
              </p>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          {/* Quick Filters Toolbar */}
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              Quick Filters Toolbar
            </h3>
            <QuickFiltersToolbar
              context={context}
              onCreateQuickFilter={() => setShowBuilder(true)}
            />
          </div>

          {/* Applied Filters */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Compact Display */}
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Applied Filters (Compact)
              </h3>
              <AppliedFiltersDisplay
                context={context}
                onEditFilter={() => setShowBuilder(true)}
              />
            </div>

            {/* Detailed Display */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                Applied Filters (Detailed)
              </h3>
              <AppliedFiltersWithDetails
                context={context}
                onEditFilter={() => setShowBuilder(true)}
              />
            </div>
          </div>

          {/* Filter Builder */}
          {showBuilder ? (
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Filter Builder
              </h3>
              <FilterBuilder
                context={context}
                onSave={handleFilterSave}
                onCancel={() => setShowBuilder(false)}
              />
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 text-center">
              <FilterIcon className="w-12 h-12 text-gray-300 dark:text-gray-700 mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Filter Builder
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Create complex filters with AND/OR logic
              </p>
              <button
                onClick={() => setShowBuilder(true)}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
              >
                Open Filter Builder
              </button>
            </div>
          )}

          {/* Bottom Row: Presets & History */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Preset Selector */}
            <FilterPresetSelector
              context={context}
              onEditPreset={() => setShowBuilder(true)}
            />

            {/* History Panel */}
            <FilterHistoryPanel context={context} limit={10} />
          </div>
        </div>

        {/* Feature Info Banner */}
        <div className="mt-8 p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                <FilterIcon className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-purple-900 dark:text-purple-100 mb-1">
                Advanced Filtering Features
              </h4>
              <ul className="text-sm text-purple-700 dark:text-purple-300 space-y-1">
                <li>• <strong>Visual Builder:</strong> Create filters with drag-and-drop interface</li>
                <li>• <strong>AND/OR Logic:</strong> Combine conditions with flexible logic (up to 2 levels)</li>
                <li>• <strong>15+ Operators:</strong> equals, contains, greater than, between, and more</li>
                <li>• <strong>Quick Filters:</strong> 1-click access to frequently used filters</li>
                <li>• <strong>Presets Library:</strong> Save and reuse filter templates</li>
                <li>• <strong>History Tracking:</strong> View and reapply recent filters</li>
                <li>• <strong>Import/Export:</strong> Share filters with your team</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
