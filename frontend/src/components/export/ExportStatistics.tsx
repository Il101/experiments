/**
 * Export Statistics Component
 * Dashboard showing export usage statistics
 */

import React from 'react';
import { BarChart3, TrendingUp, FileText, Clock, Download } from 'lucide-react';
import { useExportStore } from '../../store/useExportStore';

export const ExportStatistics: React.FC = () => {
  const { getStatistics } = useExportStore();
  const stats = getStatistics();
  
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };
  
  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };
  
  const statCards = [
    {
      label: 'Total Exports',
      value: stats.totalExports,
      icon: FileText,
      color: 'blue',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
      textColor: 'text-blue-600 dark:text-blue-400',
    },
    {
      label: 'Items Exported',
      value: stats.totalDataExported.toLocaleString(),
      icon: TrendingUp,
      color: 'purple',
      bgColor: 'bg-purple-50 dark:bg-purple-900/20',
      textColor: 'text-purple-600 dark:text-purple-400',
    },
    {
      label: 'Total Size',
      value: formatFileSize(stats.totalFileSize),
      icon: Download,
      color: 'green',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
      textColor: 'text-green-600 dark:text-green-400',
    },
    {
      label: 'Avg. Time',
      value: formatTime(stats.averageExportTime),
      icon: Clock,
      color: 'orange',
      bgColor: 'bg-orange-50 dark:bg-orange-900/20',
      textColor: 'text-orange-600 dark:text-orange-400',
    },
  ];
  
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Export Statistics</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Overview of your export activity
        </p>
      </div>
      
      {/* Stat Cards */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <div
            key={stat.label}
            className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{stat.label}</p>
                <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                  {stat.value}
                </p>
              </div>
              <div className={`rounded-lg p-3 ${stat.bgColor}`}>
                <stat.icon className={`h-6 w-6 ${stat.textColor}`} />
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* Exports by Format */}
      <div className="mb-8 rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
          <BarChart3 className="h-4 w-4" />
          Exports by Format
        </h3>
        
        {Object.keys(stats.exportsByFormat).length > 0 ? (
          <div className="space-y-3">
            {Object.entries(stats.exportsByFormat).map(([format, count]) => {
              const percentage = (count / stats.totalExports) * 100;
              const colors = {
                csv: { bg: 'bg-green-500', text: 'text-green-700 dark:text-green-400' },
                json: { bg: 'bg-purple-500', text: 'text-purple-700 dark:text-purple-400' },
                excel: { bg: 'bg-blue-500', text: 'text-blue-700 dark:text-blue-400' },
                pdf: { bg: 'bg-red-500', text: 'text-red-700 dark:text-red-400' },
              };
              const color = colors[format as keyof typeof colors] || colors.csv;
              
              return (
                <div key={format}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className={`font-medium ${color.text}`}>
                      {format.toUpperCase()}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      {count} ({percentage.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                    <div
                      className={`h-full ${color.bg}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-center text-sm text-gray-500 dark:text-gray-400">
            No exports yet
          </p>
        )}
      </div>
      
      {/* Exports by Type */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
          <TrendingUp className="h-4 w-4" />
          Exports by Data Type
        </h3>
        
        {Object.keys(stats.exportsByType).length > 0 ? (
          <div className="space-y-3">
            {Object.entries(stats.exportsByType).map(([type, count]) => {
              const percentage = (count / stats.totalExports) * 100;
              
              return (
                <div key={type}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium capitalize text-gray-900 dark:text-white">
                      {type}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      {count} ({percentage.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                    <div
                      className="h-full bg-blue-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-center text-sm text-gray-500 dark:text-gray-400">
            No exports yet
          </p>
        )}
      </div>
    </div>
  );
};
