/**
 * Export History Component
 * Shows history of past exports with download links
 */

import React from 'react';
import { FileText, Download, Calendar, Trash2, Filter } from 'lucide-react';
import { useExportStore } from '../../store/useExportStore';
import type { ExportFormat } from '../../types/export';

export const ExportHistory: React.FC = () => {
  const { history, clearHistory } = useExportStore();
  const [formatFilter, setFormatFilter] = React.useState<ExportFormat | 'all'>('all');
  
  const filteredHistory = formatFilter === 'all'
    ? history
    : history.filter((item) => item.format === formatFilter);
  
  const formatCounts = history.reduce((acc, item) => {
    acc[item.format] = (acc[item.format] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const handleDownload = (item: any) => {
    if (item.downloadUrl) {
      const link = document.createElement('a');
      link.href = item.downloadUrl;
      link.download = item.fileName;
      link.click();
    }
  };
  
  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Export History</h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Download previous exports or clear history
          </p>
        </div>
        {history.length > 0 && (
          <button
            onClick={clearHistory}
            className="flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-600 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            <Trash2 className="h-4 w-4" />
            Clear History
          </button>
        )}
      </div>
      
      {/* Format Filter */}
      {history.length > 0 && (
        <div className="mb-6 flex items-center gap-3">
          <Filter className="h-4 w-4 text-gray-400" />
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFormatFilter('all')}
              className={`rounded-lg px-3 py-1 text-sm font-medium ${
                formatFilter === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
              }`}
            >
              All ({history.length})
            </button>
            {(['csv', 'json', 'excel', 'pdf'] as ExportFormat[]).map((format) => (
              formatCounts[format] && (
                <button
                  key={format}
                  onClick={() => setFormatFilter(format)}
                  className={`rounded-lg px-3 py-1 text-sm font-medium ${
                    formatFilter === format
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
                  }`}
                >
                  {format.toUpperCase()} ({formatCounts[format]})
                </button>
              )
            ))}
          </div>
        </div>
      )}
      
      {/* History List */}
      {filteredHistory.length > 0 ? (
        <div className="space-y-3">
          {filteredHistory.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
            >
              <div className="flex items-start gap-4">
                <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/20">
                  <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                
                <div>
                  <div className="mb-1 flex items-center gap-2">
                    <h4 className="font-medium text-gray-900 dark:text-white">{item.fileName}</h4>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      item.status === 'success'
                        ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                    }`}>
                      {item.status}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(item.exportedAt).toLocaleDateString()}
                    </span>
                    <span>{(item.fileSize / 1024).toFixed(1)} KB</span>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium dark:bg-gray-800">
                      {item.format.toUpperCase()}
                    </span>
                  </div>
                  
                  {item.error && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{item.error}</p>
                  )}
                </div>
              </div>
              
              {item.downloadUrl && item.status === 'success' && (
                <button
                  onClick={() => handleDownload(item)}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  <Download className="h-4 w-4" />
                  Download
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center dark:border-gray-700">
          <FileText className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            {formatFilter === 'all' ? 'No exports yet' : `No ${formatFilter.toUpperCase()} exports`}
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Export history will appear here after your first export
          </p>
        </div>
      )}
    </div>
  );
};
