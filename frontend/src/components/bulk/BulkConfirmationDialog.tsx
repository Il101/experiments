/**
 * BulkConfirmationDialog Component
 * Confirmation dialog for destructive bulk actions
 */

import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useBulkStore } from '../../store/useBulkStore';

// ==================== Component ====================

export const BulkConfirmationDialog: React.FC = () => {
  const { confirmationDialog, closeConfirmation } = useBulkStore();
  
  if (!confirmationDialog.open) {
    return null;
  }
  
  const handleConfirm = () => {
    if (confirmationDialog.onConfirm) {
      confirmationDialog.onConfirm();
    }
    closeConfirmation();
  };
  
  const handleCancel = () => {
    closeConfirmation();
  };
  
  const getActionColor = () => {
    switch (confirmationDialog.action) {
      case 'close':
      case 'delete':
      case 'cancel':
        return 'red';
      case 'disable':
        return 'orange';
      default:
        return 'blue';
    }
  };
  
  const color = getActionColor();
  
  const colorClasses = {
    red: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-600 dark:text-red-400',
      button: 'bg-red-600 hover:bg-red-700',
    },
    orange: {
      bg: 'bg-orange-100 dark:bg-orange-900/30',
      text: 'text-orange-600 dark:text-orange-400',
      button: 'bg-orange-600 hover:bg-orange-700',
    },
    blue: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-600 dark:text-blue-400',
      button: 'bg-blue-600 hover:bg-blue-700',
    },
  };
  
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50"
        onClick={handleCancel}
      />
      
      {/* Dialog */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${colorClasses[color].bg}`}>
                <AlertTriangle className={`w-5 h-5 ${colorClasses[color].text}`} />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Confirm Action
              </h3>
            </div>
            <button
              onClick={handleCancel}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
          
          {/* Content */}
          <div className="p-6">
            <p className="text-gray-700 dark:text-gray-300 mb-4">
              {confirmationDialog.message}
            </p>
            
            <div className={`p-3 rounded-lg ${colorClasses[color].bg}`}>
              <p className={`text-sm font-medium ${colorClasses[color].text}`}>
                {confirmationDialog.itemCount} item{confirmationDialog.itemCount !== 1 ? 's' : ''} will be affected
              </p>
            </div>
            
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-4">
              This action cannot be undone.
            </p>
          </div>
          
          {/* Actions */}
          <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors ${colorClasses[color].button}`}
            >
              Confirm
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
