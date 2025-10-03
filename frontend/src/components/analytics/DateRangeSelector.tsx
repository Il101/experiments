/**
 * DateRangeSelector Component
 * Preset date ranges with custom picker
 */

import React, { useState } from 'react';
import { Calendar, ChevronDown } from 'lucide-react';
import type { DateRange, DateRangePreset } from '../../types/analytics';

// ==================== Interfaces ====================

interface DateRangeSelectorProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
}

// ==================== Component ====================

export const DateRangeSelector: React.FC<DateRangeSelectorProps> = ({
  value,
  onChange,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);

  // Calculate preset ranges
  const getPresetRange = (preset: DateRangePreset): DateRange => {
    const end = new Date();
    const start = new Date();

    switch (preset) {
      case '7D':
        start.setDate(end.getDate() - 7);
        return { start, end, label: 'Last 7 Days', preset };
      
      case '30D':
        start.setDate(end.getDate() - 30);
        return { start, end, label: 'Last 30 Days', preset };
      
      case '90D':
        start.setDate(end.getDate() - 90);
        return { start, end, label: 'Last 90 Days', preset };
      
      case 'YTD':
        start.setMonth(0, 1); // Jan 1
        return { start, end, label: 'Year to Date', preset };
      
      case '1Y':
        start.setFullYear(end.getFullYear() - 1);
        return { start, end, label: 'Last Year', preset };
      
      case 'ALL':
        start.setFullYear(2000, 0, 1);
        return { start, end, label: 'All Time', preset };
      
      case 'CUSTOM':
        return { start: value.start, end: value.end, label: 'Custom Range', preset };
      
      default:
        return { start, end, label: 'Last 30 Days', preset: '30D' };
    }
  };

  const presets: DateRangePreset[] = ['7D', '30D', '90D', 'YTD', '1Y', 'ALL'];

  const handlePresetClick = (preset: DateRangePreset) => {
    const range = getPresetRange(preset);
    onChange(range);
    setIsOpen(false);
  };

  const formatDateRange = (range: DateRange): string => {
    if (range.preset === 'ALL') return 'All Time';
    
    const formatDate = (date: Date) => {
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
      });
    };

    return `${formatDate(range.start)} - ${formatDate(range.end)}`;
  };

  return (
    <div className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        <Calendar className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {value.label}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          ({formatDateRange(value)})
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform ${
          isOpen ? 'rotate-180' : ''
        }`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20">
            <div className="p-2">
              {presets.map((preset) => {
                const range = getPresetRange(preset);
                const isActive = value.preset === preset;

                return (
                  <button
                    key={preset}
                    onClick={() => handlePresetClick(preset)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      isActive
                        ? 'bg-blue-500 text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    {range.label}
                  </button>
                );
              })}
              
              {/* Custom Range (future enhancement) */}
              <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                <button
                  className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  disabled
                >
                  Custom Range (Coming Soon)
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
