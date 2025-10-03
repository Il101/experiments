/**
 * Live PnL Display Component
 * Shows real-time profit/loss with animated updates
 */

import React from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useRealTimePrices, type PositionPnL } from '../../hooks/useRealTimePrices';
import type { Position } from '../../types';

interface LivePnLProps {
  positions: Position[];
  className?: string;
}

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatPercent = (value: number): string => {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
};

const PnLBadge: React.FC<{ value: number; showPercent?: boolean }> = ({ value, showPercent = false }) => {
  const isPositive = value >= 0;
  const isNeutral = Math.abs(value) < 0.01;

  return (
    <div
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium text-sm
        transition-all duration-300 animate-pulse-subtle
        ${
          isNeutral
            ? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
            : isPositive
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
        }
      `}
    >
      {!isNeutral && (
        <>
          {isPositive ? (
            <TrendingUp className="w-4 h-4" />
          ) : (
            <TrendingDown className="w-4 h-4" />
          )}
        </>
      )}
      <span className="font-mono">
        {showPercent ? formatPercent(value) : formatCurrency(value)}
      </span>
    </div>
  );
};

const PositionPnLRow: React.FC<{ pnl: PositionPnL }> = ({ pnl }) => {
  const priceChangePercent = pnl.unrealizedPnLPercent;
  const isPositive = priceChangePercent >= 0;

  return (
    <div className="flex items-center justify-between py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg transition-colors">
      {/* Symbol & Side */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <div
          className={`
            w-1.5 h-8 rounded-full
            ${pnl.side === 'long' ? 'bg-green-500' : 'bg-red-500'}
          `}
        />
        <div className="min-w-0">
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {pnl.symbol}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 capitalize">
            {pnl.side} • {pnl.quantity.toFixed(4)}
          </div>
        </div>
      </div>

      {/* Price Info */}
      <div className="text-right min-w-[100px] mr-4">
        <div className="font-mono text-sm text-gray-900 dark:text-gray-100">
          ${pnl.currentPrice.toFixed(2)}
        </div>
        <div
          className={`
            text-xs font-medium
            ${isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
          `}
        >
          {formatPercent(priceChangePercent)}
        </div>
      </div>

      {/* PnL */}
      <div className="text-right min-w-[120px]">
        <PnLBadge value={pnl.unrealizedPnL} />
        {pnl.rMultiple !== 0 && (
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 font-mono">
            {pnl.rMultiple.toFixed(2)}R
          </div>
        )}
      </div>
    </div>
  );
};

export const LivePnL: React.FC<LivePnLProps> = ({ positions, className = '' }) => {
  const { positionPnLs, getTotalPnL, isConnected } = useRealTimePrices(positions);
  const totalPnL = getTotalPnL();

  if (positions.length === 0) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
        <div className="text-center text-gray-500 dark:text-gray-400">
          <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No active positions</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header with Total PnL */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-gray-400" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              Live P&L
            </h3>
            {!isConnected && (
              <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded">
                Offline
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                Total Unrealized
              </div>
              <PnLBadge value={totalPnL.unrealized} />
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4 pt-3 border-t border-gray-100 dark:border-gray-800">
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Positions
            </div>
            <div className="font-mono font-medium text-gray-900 dark:text-gray-100">
              {positionPnLs.length}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Winners
            </div>
            <div className="font-mono font-medium text-green-600 dark:text-green-400">
              {positionPnLs.filter(p => p.unrealizedPnL > 0).length}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Losers
            </div>
            <div className="font-mono font-medium text-red-600 dark:text-red-400">
              {positionPnLs.filter(p => p.unrealizedPnL < 0).length}
            </div>
          </div>
        </div>
      </div>

      {/* Position List */}
      <div className="p-2 max-h-[400px] overflow-y-auto custom-scrollbar">
        {positionPnLs.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
            Waiting for price updates...
          </div>
        ) : (
          <div className="space-y-1">
            {positionPnLs
              .sort((a, b) => Math.abs(b.unrealizedPnL) - Math.abs(a.unrealizedPnL))
              .map((pnl) => (
                <PositionPnLRow key={pnl.positionId} pnl={pnl} />
              ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Utility: Add subtle pulse animation to CSS
const styles = `
@keyframes pulse-subtle {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.95; }
}

.animate-pulse-subtle {
  animation: pulse-subtle 2s ease-in-out infinite;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: #4b5563;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #6b7280;
}
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = styles;
  document.head.appendChild(styleSheet);
}
