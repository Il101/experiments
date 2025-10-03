/**
 * BulkOperationProgress Component
 * Progress indicator for ongoing bulk operations
 */

import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle, XCircle, X } from 'lucide-react';
import { useBulkStore } from '../../store/useBulkStore';
import type { BulkOperation } from '../../types/bulk';

// ==================== Component ====================

export const BulkOperationProgress: React.FC = () => {
  const { operations, activeOperationId } = useBulkStore();
  const [visible, setVisible] = useState(false);
  
  const activeOperation = operations.find((op) => op.id === activeOperationId);
  const recentCompleted = operations
    .filter((op) => op.status === 'completed' || op.status === 'failed')
    .slice(-3);
  
  useEffect(() => {
    if (activeOperation || recentCompleted.length > 0) {
      setVisible(true);
    }
  }, [activeOperation, recentCompleted.length]);
  
  const handleDismiss = (_operationId: string) => {
    // Remove from UI (operation stays in store history)
    setVisible(false);
  };
  
  if (!visible) {
    return null;
  }
  
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
      {/* Active Operation */}
      {activeOperation && (
        <OperationCard
          operation={activeOperation}
          onDismiss={handleDismiss}
        />
      )}
      
      {/* Recent Completed */}
      {!activeOperation && recentCompleted.map((op) => (
        <OperationCard
          key={op.id}
          operation={op}
          onDismiss={handleDismiss}
        />
      ))}
    </div>
  );
};

// ==================== Operation Card ====================

interface OperationCardProps {
  operation: BulkOperation;
  onDismiss: (id: string) => void;
}

const OperationCard: React.FC<OperationCardProps> = ({ operation, onDismiss }) => {
  const getStatusIcon = () => {
    switch (operation.status) {
      case 'in_progress':
        return <Loader2 className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />;
      case 'cancelled':
        return <XCircle className="w-5 h-5 text-orange-600 dark:text-orange-400" />;
      default:
        return <Loader2 className="w-5 h-5 text-gray-600 dark:text-gray-400" />;
    }
  };
  
  const getStatusColor = () => {
    switch (operation.status) {
      case 'in_progress':
        return 'border-blue-500 dark:border-blue-400';
      case 'completed':
        return 'border-green-500 dark:border-green-400';
      case 'failed':
        return 'border-red-500 dark:border-red-400';
      case 'cancelled':
        return 'border-orange-500 dark:border-orange-400';
      default:
        return 'border-gray-500 dark:border-gray-400';
    }
  };
  
  const getStatusText = () => {
    switch (operation.status) {
      case 'in_progress':
        return 'In Progress';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'cancelled':
        return 'Cancelled';
      default:
        return 'Pending';
    }
  };
  
  const getActionLabel = () => {
    const labels: Record<string, string> = {
      close: 'Closing',
      cancel: 'Cancelling',
      delete: 'Deleting',
      export: 'Exporting',
      tag: 'Tagging',
      enable: 'Enabling',
      disable: 'Disabling',
      duplicate: 'Duplicating',
    };
    return labels[operation.type] || operation.type;
  };
  
  return (
    <div
      className={`bg-white dark:bg-gray-900 border-l-4 ${getStatusColor()} rounded-lg shadow-lg p-4 min-w-[320px]`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3">
          <div className="mt-0.5">{getStatusIcon()}</div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              {getActionLabel()} {operation.itemType}s
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              {getStatusText()}
            </p>
          </div>
        </div>
        
        {operation.status !== 'in_progress' && (
          <button
            onClick={() => onDismiss(operation.id)}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
          >
            <X className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
        )}
      </div>
      
      {/* Progress Bar */}
      {operation.status === 'in_progress' && (
        <div className="mb-3">
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-600 dark:bg-blue-400 h-full transition-all duration-300"
              style={{ width: `${operation.progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
            {operation.processedItems} of {operation.totalItems} items
          </p>
        </div>
      )}
      
      {/* Results */}
      {operation.status === 'completed' && (
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span>{operation.processedItems - operation.failedItems} succeeded</span>
          </div>
          {operation.failedItems > 0 && (
            <div className="flex items-center gap-1 text-red-600 dark:text-red-400">
              <XCircle className="w-3 h-3" />
              <span>{operation.failedItems} failed</span>
            </div>
          )}
        </div>
      )}
      
      {/* Error */}
      {operation.status === 'failed' && operation.error && (
        <p className="text-xs text-red-600 dark:text-red-400">
          {operation.error}
        </p>
      )}
    </div>
  );
};
