/**
 * BulkOperationsStats Component
 * Display statistics about bulk operations
 */

import React from 'react';
import {
  BarChart3,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
} from 'lucide-react';
import { useBulkStore } from '../../store/useBulkStore';

// ==================== Component ====================

export const BulkOperationsStats: React.FC = () => {
  const { getStatistics } = useBulkStore();
  const stats = getStatistics();
  
  const statCards = [
    {
      label: 'Total Operations',
      value: stats.totalOperations,
      icon: BarChart3,
      color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    },
    {
      label: 'Successful',
      value: stats.successfulOperations,
      icon: CheckCircle,
      color: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    },
    {
      label: 'Failed',
      value: stats.failedOperations,
      icon: XCircle,
      color: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
    },
    {
      label: 'Items Processed',
      value: stats.totalItemsProcessed,
      icon: TrendingUp,
      color: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    },
    {
      label: 'Avg. Time',
      value: `${(stats.averageProcessingTime / 1000).toFixed(1)}s`,
      icon: Clock,
      color: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    },
  ];
  
  if (stats.totalOperations === 0) {
    return (
      <div className="text-center py-12">
        <BarChart3 className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">
          No bulk operations yet
        </p>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {statCards.map((stat) => (
          <div
            key={stat.label}
            className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-lg ${stat.color}`}>
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
              {stat.value}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {stat.label}
            </div>
          </div>
        ))}
      </div>
      
      {/* Recent Operations */}
      {stats.recentOperations.length > 0 && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Recent Operations
          </h3>
          <div className="space-y-3">
            {stats.recentOperations.map((op) => (
              <div
                key={op.id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  {op.status === 'completed' ? (
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                  ) : op.status === 'failed' ? (
                    <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                  ) : (
                    <Clock className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  )}
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {op.type.charAt(0).toUpperCase() + op.type.slice(1)} {op.itemType}s
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {op.processedItems} items • {new Date(op.startedAt).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-medium ${
                    op.status === 'completed' ? 'text-green-600 dark:text-green-400' :
                    op.status === 'failed' ? 'text-red-600 dark:text-red-400' :
                    'text-gray-600 dark:text-gray-400'
                  }`}>
                    {op.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Most Used Action */}
      {stats.mostUsedAction && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
            <TrendingUp className="w-5 h-5" />
            <span className="font-medium">Most Used Action:</span>
            <span className="font-semibold capitalize">{stats.mostUsedAction}</span>
          </div>
        </div>
      )}
    </div>
  );
};
