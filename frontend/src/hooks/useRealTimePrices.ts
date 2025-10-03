/**
 * Real-time Price Tracking Hook
 * Subscribes to price updates via WebSocket and calculates live PnL
 */

import { useState, useEffect, useCallback } from 'react';
import { useWebSocketStore } from '../store';
import type { Position } from '../types';

export interface PriceUpdate {
  symbol: string;
  price: number;
  timestamp: number;
  change24h?: number;
  volume24h?: number;
}

export interface PositionPnL {
  positionId: string;
  symbol: string;
  currentPrice: number;
  entryPrice: number;
  quantity: number;
  side: 'long' | 'short';
  unrealizedPnL: number;
  unrealizedPnLPercent: number;
  realizedPnL?: number;
  totalPnL: number;
  rMultiple: number;
  priceHistory: number[]; // Last 100 prices for sparkline
}

export const useRealTimePrices = (positions: Position[] = []) => {
  const { lastMessage, isConnected } = useWebSocketStore();
  const [prices, setPrices] = useState<Map<string, PriceUpdate>>(new Map());
  const [positionPnLs, setPositionPnLs] = useState<Map<string, PositionPnL>>(new Map());

  // Calculate PnL for a position
  const calculatePnL = useCallback((position: Position, currentPrice: number): PositionPnL => {
    const side = position.side.toLowerCase() as 'long' | 'short';
    const entryPrice = position.entry;
    const quantity = position.size;
    const riskAmount = position.riskR ? position.riskR * quantity : 0;

    let unrealizedPnL: number;
    let priceDiff: number;

    if (side === 'long') {
      priceDiff = currentPrice - entryPrice;
      unrealizedPnL = priceDiff * quantity;
    } else {
      priceDiff = entryPrice - currentPrice;
      unrealizedPnL = priceDiff * quantity;
    }

    const unrealizedPnLPercent = (priceDiff / entryPrice) * 100;
    const realizedPnL = 0; // Will be calculated on position close
    const totalPnL = unrealizedPnL + realizedPnL;
    
    // Calculate R-multiple (risk-adjusted return)
    const rMultiple = riskAmount > 0 ? totalPnL / riskAmount : 0;

    // Get existing price history or create new
    const existingPnL = positionPnLs.get(position.id);
    const priceHistory = existingPnL?.priceHistory || [];
    const updatedHistory = [...priceHistory, currentPrice].slice(-100); // Keep last 100 prices

    return {
      positionId: position.id,
      symbol: position.symbol,
      currentPrice,
      entryPrice,
      quantity,
      side,
      unrealizedPnL,
      unrealizedPnLPercent,
      realizedPnL,
      totalPnL,
      rMultiple,
      priceHistory: updatedHistory,
    };
  }, [positionPnLs]);

  // Update position PnLs when prices change
  useEffect(() => {
    if (!isConnected || positions.length === 0) return;

    const newPnLs = new Map<string, PositionPnL>();

    positions.forEach((position) => {
      const priceUpdate = prices.get(position.symbol);
      if (priceUpdate) {
        const pnl = calculatePnL(position, priceUpdate.price);
        newPnLs.set(position.id, pnl);
      } else {
        // Use position's current price if no real-time update yet
        const currentPrice = position.currentPrice || position.entry;
        const pnl = calculatePnL(position, currentPrice);
        newPnLs.set(position.id, pnl);
      }
    });

    setPositionPnLs(newPnLs);
  }, [prices, positions, calculatePnL, isConnected]);

  // Listen for price updates from WebSocket
  useEffect(() => {
    if (!lastMessage || !isConnected) return;

    // Handle PRICE_UPDATE messages
    if (lastMessage.type === 'PRICE_UPDATE' && lastMessage.data) {
      const priceData = lastMessage.data as PriceUpdate;
      
      setPrices((prev) => {
        const updated = new Map(prev);
        updated.set(priceData.symbol, {
          ...priceData,
          timestamp: lastMessage.ts,
        });
        return updated;
      });
    }

    // Handle POSITION_UPDATE messages (may include current price)
    if (lastMessage.type === 'POSITION_UPDATE' && lastMessage.data) {
      const positionUpdate = lastMessage.data as any;
      if (positionUpdate.currentPrice && positionUpdate.symbol) {
        setPrices((prev) => {
          const updated = new Map(prev);
          updated.set(positionUpdate.symbol, {
            symbol: positionUpdate.symbol,
            price: positionUpdate.currentPrice,
            timestamp: lastMessage.ts,
          });
          return updated;
        });
      }
    }
  }, [lastMessage, isConnected]);

  // Get PnL for specific position
  const getPositionPnL = useCallback((positionId: string): PositionPnL | undefined => {
    return positionPnLs.get(positionId);
  }, [positionPnLs]);

  // Get total portfolio PnL
  const getTotalPnL = useCallback((): { unrealized: number; realized: number; total: number } => {
    let unrealizedTotal = 0;
    let realizedTotal = 0;

    positionPnLs.forEach((pnl) => {
      unrealizedTotal += pnl.unrealizedPnL;
      realizedTotal += pnl.realizedPnL || 0;
    });

    return {
      unrealized: unrealizedTotal,
      realized: realizedTotal,
      total: unrealizedTotal + realizedTotal,
    };
  }, [positionPnLs]);

  // Get latest price for symbol
  const getPrice = useCallback((symbol: string): number | undefined => {
    return prices.get(symbol)?.price;
  }, [prices]);

  // Subscribe to specific symbols (for WebSocket)
  const subscribeToSymbols = useCallback((symbols: string[]) => {
    const { sendMessage } = useWebSocketStore.getState();
    sendMessage({
      type: 'SUBSCRIBE_PRICES',
      symbols,
    });
  }, []);

  // Unsubscribe from symbols
  const unsubscribeFromSymbols = useCallback((symbols: string[]) => {
    const { sendMessage } = useWebSocketStore.getState();
    sendMessage({
      type: 'UNSUBSCRIBE_PRICES',
      symbols,
    });
  }, []);

  // Auto-subscribe to all position symbols
  useEffect(() => {
    if (!isConnected || positions.length === 0) return;

    const symbols = [...new Set(positions.map((p) => p.symbol))];
    subscribeToSymbols(symbols);

    return () => {
      unsubscribeFromSymbols(symbols);
    };
  }, [positions, isConnected, subscribeToSymbols, unsubscribeFromSymbols]);

  return {
    prices: Array.from(prices.values()),
    positionPnLs: Array.from(positionPnLs.values()),
    getPositionPnL,
    getTotalPnL,
    getPrice,
    subscribeToSymbols,
    unsubscribeFromSymbols,
    isConnected,
  };
};
