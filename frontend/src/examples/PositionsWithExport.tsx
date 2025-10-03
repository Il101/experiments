/**
 * Export Integration Example
 * Shows how to integrate export functionality with bulk operations
 */

import React, { useState } from 'react';
import { Download, FileText } from 'lucide-react';
import { useExportStore } from '../../store/useExportStore';
import { useBulkStore } from '../../store/useBulkStore';
import { ExportDialog } from '../export/ExportDialog';
import { ExportProgress } from '../export/ExportProgress';
import type { ExportDataType } from '../../types/export';

// Mock position data
const mockPositions = [
  {
    id: '1',
    symbol: 'BTCUSDT',
    side: 'LONG',
    size: 0.5,
    entryPrice: 45000,
    currentPrice: 45500,
    pnl: 250,
    roi: 1.11,
    margin: 5000,
    leverage: 10,
    liquidationPrice: 40500,
    tags: ['breakout', 'high-volume'],
  },
  {
    id: '2',
    symbol: 'ETHUSDT',
    side: 'SHORT',
    size: 2,
    entryPrice: 3000,
    currentPrice: 2950,
    pnl: 100,
    roi: 1.67,
    margin: 600,
    leverage: 5,
    liquidationPrice: 3600,
    tags: ['reversal'],
  },
];

export const PositionsWithExport: React.FC = () => {
  const { openExportDialog, exportDialogOpen, closeExportDialog } = useExportStore();
  const { getSelectedIds, getSelectedCount } = useBulkStore();
  const [dataType] = useState<ExportDataType>('positions');
  
  const selectedIds = Array.from(getSelectedIds('position'));
  const selectedCount = getSelectedCount('position');
  
  const handleExportAll = () => {
    openExportDialog();
  };
  
  const handleExportSelected = () => {
    if (selectedCount > 0) {
      openExportDialog();
    }
  };
  
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Positions</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage and export your trading positions
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Export All Button */}
          <button
            onClick={handleExportAll}
            className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <FileText className="h-4 w-4" />
            Export All
          </button>
          
          {/* Export Selected Button */}
          {selectedCount > 0 && (
            <button
              onClick={handleExportSelected}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Download className="h-4 w-4" />
              Export Selected ({selectedCount})
            </button>
          )}
        </div>
      </div>
      
      {/* Positions Table */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
        <table className="w-full">
          <thead className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                Symbol
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                Side
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400">
                Size
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400">
                Entry
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400">
                Current
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400">
                P&L
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                Tags
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {mockPositions.map((position) => (
              <tr key={position.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                  {position.symbol}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                      position.side === 'LONG'
                        ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                    }`}
                  >
                    {position.side}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-sm text-gray-600 dark:text-gray-400">
                  {position.size}
                </td>
                <td className="px-4 py-3 text-right text-sm text-gray-600 dark:text-gray-400">
                  ${position.entryPrice.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right text-sm text-gray-600 dark:text-gray-400">
                  ${position.currentPrice.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right text-sm">
                  <span
                    className={
                      position.pnl >= 0
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }
                  >
                    {position.pnl >= 0 ? '+' : ''}${position.pnl.toFixed(2)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {position.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Export Dialog */}
      {exportDialogOpen && (
        <ExportDialog
          dataType={dataType}
          defaultItemIds={selectedCount > 0 ? selectedIds : undefined}
          onClose={closeExportDialog}
        />
      )}
      
      {/* Export Progress */}
      <ExportProgress />
      
      {/* Info Card */}
      <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-900/20">
        <div className="flex items-start gap-3">
          <Download className="mt-0.5 h-5 w-5 text-blue-600 dark:text-blue-400" />
          <div>
            <h3 className="text-sm font-medium text-blue-900 dark:text-blue-300">
              Export Your Data
            </h3>
            <p className="mt-1 text-sm text-blue-800 dark:text-blue-400">
              Export positions to CSV, Excel, JSON, or PDF. Select specific positions or export all.
              Use templates for quick exports with predefined settings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
