/**
 * Example: Positions List with Bulk Operations
 * Demonstrates how to integrate bulk operations into a list component
 */

import React, { useState } from 'react';
import {
  BulkToolbar,
  BulkSelectCheckbox,
  BulkSelectAllCheckbox,
  BulkConfirmationDialog,
  BulkOperationProgress,
  QuickSelectMenu,
} from '../components/bulk';
import { useBulkOperations } from '../hooks/useBulkOperations';
import { useBulkStore } from '../store/useBulkStore';

// ==================== Mock Data ====================

interface Position {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  tags: string[];
}

const mockPositions: Position[] = [
  {
    id: 'pos-1',
    symbol: 'BTCUSDT',
    side: 'long',
    size: 0.5,
    entryPrice: 50000,
    currentPrice: 51000,
    pnl: 500,
    tags: ['scalp'],
  },
  {
    id: 'pos-2',
    symbol: 'ETHUSDT',
    side: 'short',
    size: 2.0,
    entryPrice: 3000,
    currentPrice: 2950,
    pnl: 100,
    tags: ['swing'],
  },
  // Add more mock positions as needed
];

// ==================== Component ====================

export const PositionsListWithBulk: React.FC = () => {
  const [positions] = useState<Position[]>(mockPositions);
  const { selectAll, deselectAll, getSelectedCount } = useBulkStore();
  
  const { handleBulkAction } = useBulkOperations({
    itemType: 'position',
    onClose: async (itemIds) => {
      console.log('Closing positions:', itemIds);
      // Implement actual close logic
      await new Promise((resolve) => setTimeout(resolve, 1000));
    },
    onDelete: async (itemIds) => {
      console.log('Deleting positions:', itemIds);
      // Implement actual delete logic
      await new Promise((resolve) => setTimeout(resolve, 1000));
    },
    onTag: async (itemIds, tags) => {
      console.log('Tagging positions:', itemIds, tags);
      // Implement actual tag logic
      await new Promise((resolve) => setTimeout(resolve, 1000));
    },
    onExport: async (itemIds, format) => {
      console.log('Exporting positions:', itemIds, format);
      // Implement actual export logic
      await new Promise((resolve) => setTimeout(resolve, 1000));
    },
  });
  
  const selectedCount = getSelectedCount('position');
  const positionIds = positions.map((p) => p.id);
  
  return (
    <div className="flex flex-col h-full">
      {/* Header with Quick Select */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
            Positions
          </h2>
          <QuickSelectMenu
            onSelectAll={() => selectAll('position', positionIds)}
            onDeselectAll={() => deselectAll('position')}
            selectedCount={selectedCount}
            totalCount={positions.length}
          />
        </div>
        
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {positions.length} position{positions.length !== 1 ? 's' : ''}
        </div>
      </div>
      
      {/* Positions Table */}
      <div className="flex-1 overflow-y-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
            <tr>
              <th className="px-6 py-3 text-left">
                <BulkSelectAllCheckbox
                  itemType="position"
                  itemIds={positionIds}
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Symbol
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Side
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Size
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Entry
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Current
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                P&L
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Tags
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {positions.map((position) => (
              <tr
                key={position.id}
                className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <td className="px-6 py-4">
                  <BulkSelectCheckbox
                    itemType="position"
                    itemId={position.id}
                  />
                </td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                  {position.symbol}
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                    position.side === 'long'
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                      : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                  }`}>
                    {position.side.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-right text-gray-900 dark:text-gray-100">
                  {position.size}
                </td>
                <td className="px-6 py-4 text-sm text-right text-gray-900 dark:text-gray-100">
                  ${position.entryPrice.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-sm text-right text-gray-900 dark:text-gray-100">
                  ${position.currentPrice.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-sm text-right">
                  <span className={`font-medium ${
                    position.pnl >= 0
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}>
                    {position.pnl >= 0 ? '+' : ''}${position.pnl.toLocaleString()}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-1">
                    {position.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
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
      
      {/* Bulk Toolbar */}
      <BulkToolbar
        itemType="position"
        onAction={handleBulkAction}
        position="bottom"
      />
      
      {/* Confirmation Dialog */}
      <BulkConfirmationDialog />
      
      {/* Operation Progress */}
      <BulkOperationProgress />
    </div>
  );
};
