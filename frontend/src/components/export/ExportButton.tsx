/**
 * Export Button Component
 * Quick export button for bulk operations integration
 */

import React from 'react';
import { Download } from 'lucide-react';
import { useExportStore } from '../../store/useExportStore';
import type { ExportDataType } from '../../types/export';

interface ExportButtonProps {
  dataType: ExportDataType;
  itemIds?: string[];
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
}

export const ExportButton: React.FC<ExportButtonProps> = ({
  dataType: _dataType,
  itemIds,
  variant = 'primary',
  size = 'md',
  disabled = false,
}) => {
  const { openExportDialog } = useExportStore();
  
  const handleClick = () => {
    openExportDialog();
  };
  
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700',
    outline: 'border-2 border-blue-600 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20',
  };
  
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };
  
  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };
  
  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className={`inline-flex items-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variantClasses[variant]} ${sizeClasses[size]}`}
    >
      <Download className={iconSizes[size]} />
      Export
      {itemIds && itemIds.length > 0 && (
        <span className="rounded-full bg-white/20 px-2 py-0.5 text-xs">
          {itemIds.length}
        </span>
      )}
    </button>
  );
};
