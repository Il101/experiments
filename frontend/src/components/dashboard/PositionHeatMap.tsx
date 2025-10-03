/**
 * Position Heat Map Component
 * Visual representation of position performance and risk exposure
 */

import React, { useMemo } from 'react';
import { AlertCircle } from 'lucide-react';
import { useRealTimePrices } from '../../hooks/useRealTimePrices';
import type { Position } from '../../types';

interface PositionHeatMapProps {
  positions: Position[];
  className?: string;
}

interface HeatMapCell {
  positionId: string;
  symbol: string;
  side: 'long' | 'short';
  pnlPercent: number;
  pnlUsd: number;
  size: number;
  rMultiple: number;
  intensity: number; // 0-100 for color intensity
}

const getColorFromPnL = (pnlPercent: number, intensity: number): string => {
  if (Math.abs(pnlPercent) < 0.1) {
    return `rgba(156, 163, 175, ${intensity / 100})`; // Gray for neutral
  }
  
  if (pnlPercent > 0) {
    // Green gradient from light to dark
    const r = Math.max(0, 34 - intensity);
    const g = Math.min(255, 197 + (intensity / 2));
    const b = Math.max(0, 94 - intensity);
    return `rgba(${r}, ${g}, ${b}, ${Math.min(1, 0.3 + intensity / 150)})`;
  } else {
    // Red gradient from light to dark
    const r = Math.min(255, 239 + (intensity / 4));
    const g = Math.max(0, 68 - intensity);
    const b = Math.max(0, 68 - intensity);
    return `rgba(${r}, ${g}, ${b}, ${Math.min(1, 0.3 + intensity / 150)})`;
  }
};

const HeatMapCell: React.FC<{ cell: HeatMapCell; onClick?: () => void }> = ({ cell, onClick }) => {
  const isPositive = cell.pnlPercent >= 0;
  
  const bgColor = getColorFromPnL(cell.pnlPercent, cell.intensity);
  
  return (
    <div
      onClick={onClick}
      className="relative group cursor-pointer transition-all duration-200 hover:scale-105 hover:z-10"
      style={{
        backgroundColor: bgColor,
        minWidth: '80px',
        minHeight: '80px',
        padding: '8px',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
      }}
    >
      {/* Position Info */}
      <div className="flex flex-col h-full justify-between">
        <div className="flex items-start justify-between">
          <div className="text-xs font-medium text-gray-900 dark:text-white truncate">
            {cell.symbol}
          </div>
          <div
            className={`
              text-[10px] px-1.5 py-0.5 rounded
              ${cell.side === 'long' ? 'bg-green-500/20 text-green-700 dark:text-green-300' : 'bg-red-500/20 text-red-700 dark:text-red-300'}
            `}
          >
            {cell.side === 'long' ? 'L' : 'S'}
          </div>
        </div>
        
        <div className="mt-1">
          <div className={`text-sm font-bold ${isPositive ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
            {cell.pnlPercent >= 0 ? '+' : ''}{cell.pnlPercent.toFixed(1)}%
          </div>
          <div className="text-[10px] text-gray-700 dark:text-gray-300 font-mono">
            ${Math.abs(cell.pnlUsd).toFixed(0)}
          </div>
        </div>
      </div>

      {/* Hover Tooltip */}
      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
        <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg whitespace-nowrap">
          <div className="font-semibold mb-1">{cell.symbol}</div>
          <div className="space-y-0.5">
            <div>Side: <span className="font-mono">{cell.side}</span></div>
            <div>P&L: <span className="font-mono">{cell.pnlPercent >= 0 ? '+' : ''}{cell.pnlPercent.toFixed(2)}%</span></div>
            <div>USD: <span className="font-mono">${cell.pnlUsd.toFixed(2)}</span></div>
            <div>Size: <span className="font-mono">{cell.size.toFixed(4)}</span></div>
            {cell.rMultiple !== 0 && (
              <div>R: <span className="font-mono">{cell.rMultiple.toFixed(2)}R</span></div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export const PositionHeatMap: React.FC<PositionHeatMapProps> = ({ positions, className = '' }) => {
  const { positionPnLs, getTotalPnL, isConnected } = useRealTimePrices(positions);
  const totalPnL = getTotalPnL();

  const heatMapCells = useMemo((): HeatMapCell[] => {
    if (positionPnLs.length === 0) return [];

    // Calculate max absolute PnL for intensity scaling
    const maxAbsPnL = Math.max(...positionPnLs.map(p => Math.abs(p.unrealizedPnLPercent)));

    return positionPnLs.map((pnl) => {
      const intensity = maxAbsPnL > 0 ? (Math.abs(pnl.unrealizedPnLPercent) / maxAbsPnL) * 100 : 50;

      return {
        positionId: pnl.positionId,
        symbol: pnl.symbol,
        side: pnl.side,
        pnlPercent: pnl.unrealizedPnLPercent,
        pnlUsd: pnl.unrealizedPnL,
        size: pnl.quantity,
        rMultiple: pnl.rMultiple,
        intensity,
      };
    });
  }, [positionPnLs]);

  // Sort cells by PnL (biggest winners first, then biggest losers)
  const sortedCells = useMemo(() => {
    return [...heatMapCells].sort((a, b) => b.pnlUsd - a.pnlUsd);
  }, [heatMapCells]);

  const stats = useMemo(() => {
    const winners = heatMapCells.filter(c => c.pnlPercent > 0);
    const losers = heatMapCells.filter(c => c.pnlPercent < 0);
    
    return {
      totalPositions: heatMapCells.length,
      winners: winners.length,
      losers: losers.length,
      neutral: heatMapCells.length - winners.length - losers.length,
      avgWinner: winners.length > 0 ? winners.reduce((sum, c) => sum + c.pnlPercent, 0) / winners.length : 0,
      avgLoser: losers.length > 0 ? losers.reduce((sum, c) => sum + c.pnlPercent, 0) / losers.length : 0,
    };
  }, [heatMapCells]);

  if (positions.length === 0) {
    return (
      <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
        <div className="text-center text-gray-500 dark:text-gray-400">
          <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No positions to display</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <span className="text-lg">🔥</span>
            Position Heat Map
          </h3>
          {!isConnected && (
            <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded">
              Offline
            </span>
          )}
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-4 gap-3 text-center">
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total</div>
            <div className="font-mono font-semibold text-gray-900 dark:text-gray-100">
              {stats.totalPositions}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Winners</div>
            <div className="font-mono font-semibold text-green-600 dark:text-green-400">
              {stats.winners}
              {stats.winners > 0 && (
                <span className="text-xs ml-1">({stats.avgWinner.toFixed(1)}%)</span>
              )}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Losers</div>
            <div className="font-mono font-semibold text-red-600 dark:text-red-400">
              {stats.losers}
              {stats.losers > 0 && (
                <span className="text-xs ml-1">({stats.avgLoser.toFixed(1)}%)</span>
              )}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Total P&L</div>
            <div className={`font-mono font-semibold ${totalPnL.unrealized >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              ${totalPnL.unrealized.toFixed(0)}
            </div>
          </div>
        </div>
      </div>

      {/* Heat Map Grid */}
      <div className="p-4">
        {sortedCells.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
            Waiting for price updates...
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {sortedCells.map((cell) => (
              <HeatMapCell key={cell.positionId} cell={cell} />
            ))}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="px-4 pb-4">
        <div className="flex items-center justify-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgba(34, 197, 94, 0.6)' }} />
            <span>Winning</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgba(156, 163, 175, 0.4)' }} />
            <span>Neutral</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.6)' }} />
            <span>Losing</span>
          </div>
          <div className="ml-2 text-xs italic">
            Color intensity = relative P&L magnitude
          </div>
        </div>
      </div>
    </div>
  );
};
