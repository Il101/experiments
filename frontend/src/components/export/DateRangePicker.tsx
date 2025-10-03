/**
 * Date Range Picker Component
 * Allows selection of date range for export filtering
 */

import React from 'react';

interface DateRangePickerProps {
  value: { start: string; end: string } | null;
  onChange: (value: { start: string; end: string } | null) => void;
}

export const DateRangePicker: React.FC<DateRangePickerProps> = ({ value, onChange }) => {
  const [enabled, setEnabled] = React.useState(!!value);
  
  const handleToggle = () => {
    if (enabled) {
      setEnabled(false);
      onChange(null);
    } else {
      setEnabled(true);
      const today = new Date();
      const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
      onChange({
        start: thirtyDaysAgo.toISOString().split('T')[0],
        end: today.toISOString().split('T')[0],
      });
    }
  };
  
  const handleStartChange = (start: string) => {
    if (value) {
      onChange({ ...value, start });
    }
  };
  
  const handleEndChange = (end: string) => {
    if (value) {
      onChange({ ...value, end });
    }
  };
  
  // Quick preset buttons
  const handlePreset = (days: number) => {
    const end = new Date();
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    onChange({
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
    });
    setEnabled(true);
  };
  
  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <input
          type="checkbox"
          checked={enabled}
          onChange={handleToggle}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <span className="text-sm text-gray-700 dark:text-gray-300">Filter by date range</span>
      </div>
      
      {enabled && (
        <>
          {/* Quick Presets */}
          <div className="mb-3 flex flex-wrap gap-2">
            <button
              onClick={() => handlePreset(7)}
              className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              Last 7 days
            </button>
            <button
              onClick={() => handlePreset(30)}
              className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              Last 30 days
            </button>
            <button
              onClick={() => handlePreset(90)}
              className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              Last 90 days
            </button>
            <button
              onClick={() => {
                const end = new Date();
                const start = new Date(end.getFullYear(), 0, 1);
                onChange({
                  start: start.toISOString().split('T')[0],
                  end: end.toISOString().split('T')[0],
                });
              }}
              className="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              This Year
            </button>
          </div>
          
          {/* Date Inputs */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                Start Date
              </label>
              <input
                type="date"
                value={value?.start || ''}
                onChange={(e) => handleStartChange(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                End Date
              </label>
              <input
                type="date"
                value={value?.end || ''}
                onChange={(e) => handleEndChange(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
};
