/**
 * Filter History Panel
 * Timeline of recently applied filters
 */

import React from 'react';
import { History, Clock, RefreshCw, Trash2, TrendingUp } from 'lucide-react';
import { useFilterStore } from '../../store/useFilterStore';
import type { FilterHistory, FilterContext } from '../../types/filters';

interface FilterHistoryPanelProps {
  context?: FilterContext;
  limit?: number;
  className?: string;
}

export const FilterHistoryPanel: React.FC<FilterHistoryPanelProps> = ({
  context,
  limit = 20,
  className = '',
}) => {
  const { history, clearHistory, setActiveFilter } = useFilterStore();

  // Filter history by context if provided
  const filteredHistory = context
    ? history.filter((h) => h.context === context)
    : history;

  // Apply limit
  const displayHistory = filteredHistory.slice(0, limit);

  const handleReapplyFilter = (historyEntry: FilterHistory) => {
    setActiveFilter(historyEntry.context, historyEntry.filter.id);
  };

  const handleClearHistory = () => {
    if (confirm('Are you sure you want to clear all filter history?')) {
      clearHistory();
    }
  };

  const formatTimeAgo = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return then.toLocaleDateString();
  };

  if (displayHistory.length === 0) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
        <div className="text-center">
          <History className="w-12 h-12 text-gray-300 dark:text-gray-700 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
            No Filter History
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Applied filters will appear here
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Filter History
          </h3>
          <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs font-medium rounded">
            {displayHistory.length}
          </span>
        </div>

        <button
          onClick={handleClearHistory}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          <span>Clear History</span>
        </button>
      </div>

      {/* History Timeline */}
      <div className="max-h-96 overflow-y-auto">
        <div className="p-4 space-y-3">
          {displayHistory.map((entry) => (
            <HistoryEntry
              key={entry.id}
              entry={entry}
              onReapply={() => handleReapplyFilter(entry)}
              formatTimeAgo={formatTimeAgo}
            />
          ))}
        </div>
      </div>

      {/* Footer */}
      {filteredHistory.length > displayHistory.length && (
        <div className="p-3 border-t border-gray-200 dark:border-gray-700 text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Showing {displayHistory.length} of {filteredHistory.length} entries
          </p>
        </div>
      )}
    </div>
  );
};

// ===== HISTORY ENTRY =====
interface HistoryEntryProps {
  entry: FilterHistory;
  onReapply: () => void;
  formatTimeAgo: (timestamp: string) => string;
}

const HistoryEntry: React.FC<HistoryEntryProps> = ({ entry, onReapply, formatTimeAgo }) => {
  const contextColors: Record<FilterContext, string> = {
    positions: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    orders: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    signals: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    candidates: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    logs: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  };

  return (
    <div className="group flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
      {/* Timeline Dot */}
      <div className="flex-shrink-0 mt-1">
        <div className="w-2 h-2 bg-blue-500 rounded-full" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Filter Name & Context */}
        <div className="flex items-center gap-2 mb-1">
          <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
            {entry.filter.name}
          </h4>
          <span className={`px-2 py-0.5 text-xs font-medium rounded capitalize ${contextColors[entry.context]}`}>
            {entry.context}
          </span>
        </div>

        {/* Description */}
        {entry.filter.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 line-clamp-1">
            {entry.filter.description}
          </p>
        )}

        {/* Stats */}
        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>{formatTimeAgo(entry.appliedAt)}</span>
          </div>
          <div className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            <span>{entry.resultsCount} results</span>
          </div>
        </div>
      </div>

      {/* Reapply Button */}
      <button
        onClick={onReapply}
        className="opacity-0 group-hover:opacity-100 flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all"
        title="Reapply this filter"
      >
        <RefreshCw className="w-3 h-3" />
        <span>Reapply</span>
      </button>
    </div>
  );
};
